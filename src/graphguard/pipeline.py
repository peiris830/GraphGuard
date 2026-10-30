"""Run the whole Phase 1 batch pipeline: read, check, quarantine, write.

    python -m graphguard.pipeline --raw data/raw/elliptic_bitcoin_dataset --out data/processed
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from graphguard.integrity import (
    find_cross_step_edges,
    find_duplicate_tx_ids,
    find_orphan_edges,
    find_unmatched_class_ids,
)
from graphguard.loader import read_classes, read_edges, read_features
from graphguard.quarantine import DEFAULT_MAX_REJECT_RATE, split_valid_rows
from graphguard.writer import write_partitioned, write_quarantine

DEFAULT_RAW_DIR = Path("data/raw/elliptic_bitcoin_dataset")
DEFAULT_OUT_DIR = Path("data/processed")


class IntegrityError(ValueError):
    """The three files do not agree with each other, so nothing is written."""


@dataclass
class PipelineSummary:
    features_read: int
    features_written: int
    features_rejected: int
    classes_written: int
    classes_dropped: int
    edges_written: int
    edges_dropped: int


def run_pipeline(
    raw_dir: Path,
    out_dir: Path,
    max_reject_rate: float = DEFAULT_MAX_REJECT_RATE,
) -> PipelineSummary:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    features = read_features(raw_dir / "elliptic_txs_features.csv")
    classes = read_classes(raw_dir / "elliptic_txs_classes.csv")
    edges = read_edges(raw_dir / "elliptic_txs_edgelist.csv")

    # Everything that can stop the run happens before the first write, so a
    # failed run leaves the previous good output untouched.
    _check_integrity(features, classes, edges)
    clean, rejected = split_valid_rows(features, max_reject_rate)

    # Rows of the other two tables that belong to a quarantined transaction
    # cannot be partitioned (their step is invalid), so they are dropped and
    # counted. Edges never cross steps, so an edge takes its source's step.
    step_of = clean.set_index("tx_id")["time_step"]
    kept_classes = classes[classes["tx_id"].isin(step_of.index)]
    kept_classes = kept_classes.assign(time_step=kept_classes["tx_id"].map(step_of))
    kept_edges = edges[edges["src_tx_id"].isin(step_of.index)]
    kept_edges = kept_edges.assign(time_step=kept_edges["src_tx_id"].map(step_of))

    write_partitioned(clean, out_dir / "features")
    write_partitioned(kept_classes, out_dir / "classes")
    write_partitioned(kept_edges, out_dir / "edges")
    write_quarantine(rejected, out_dir / "quarantine" / "features.parquet")

    return PipelineSummary(
        features_read=len(features),
        features_written=len(clean),
        features_rejected=len(rejected),
        classes_written=len(kept_classes),
        classes_dropped=len(classes) - len(kept_classes),
        edges_written=len(kept_edges),
        edges_dropped=len(edges) - len(kept_edges),
    )


def _check_integrity(
    features: pd.DataFrame, classes: pd.DataFrame, edges: pd.DataFrame
) -> None:
    # (name, offending rows, columns worth showing as examples)
    checks = [
        ("duplicate tx_ids in features", find_duplicate_tx_ids(features), ["tx_id"]),
        ("duplicate tx_ids in classes", find_duplicate_tx_ids(classes), ["tx_id"]),
        ("unmatched class ids", find_unmatched_class_ids(classes, features), None),
        ("orphan edges", find_orphan_edges(edges, features), None),
        ("cross-step edges", find_cross_step_edges(edges, features), None),
    ]
    problems = [
        f"{name}: {len(rows)} (e.g. "
        f"{(rows if columns is None else rows[columns]).head(3).values.tolist()})"
        for name, rows, columns in checks
        if len(rows)
    ]
    if problems:
        raise IntegrityError("; ".join(problems))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the GraphGuard batch pipeline.")
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW_DIR, help="folder with the three Elliptic CSVs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_DIR, help="folder for the Parquet output")
    parser.add_argument("--max-reject-rate", type=float, default=DEFAULT_MAX_REJECT_RATE)
    args = parser.parse_args(argv)

    try:
        summary = run_pipeline(args.raw, args.out, args.max_reject_rate)
    except (ValueError, FileNotFoundError) as error:
        print(f"pipeline failed: {error}", file=sys.stderr)
        return 1

    print(
        f"features: read {summary.features_read}, written {summary.features_written}, "
        f"rejected {summary.features_rejected}"
    )
    print(f"classes: written {summary.classes_written}, dropped {summary.classes_dropped}")
    print(f"edges: written {summary.edges_written}, dropped {summary.edges_dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
