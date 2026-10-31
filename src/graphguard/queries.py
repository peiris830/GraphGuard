"""Query the Parquet output with DuckDB, reading the files in place.

    python -m graphguard.queries                  # summary of every time step
    python -m graphguard.queries --step 7         # busiest transactions in step 7
"""

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

from graphguard.pipeline import DEFAULT_OUT_DIR


def _scan(processed_dir: Path, table: str) -> str:
    """SQL for reading every time step of one table.

    hive_partitioning turns the time_step=7 folder name back into a
    time_step column, so a WHERE on it only opens the matching folders.
    """
    folder = Path(processed_dir) / table
    if not any(folder.glob("*/*.parquet")):
        raise FileNotFoundError(
            f"no Parquet files under {folder}; run python -m graphguard.pipeline first"
        )
    pattern = (folder / "*" / "*.parquet").as_posix().replace("'", "''")
    return f"read_parquet('{pattern}', hive_partitioning = true)"


def step_summary(processed_dir: Path) -> pd.DataFrame:
    """Transactions, edges and label counts for every time step.

    A step with no edges shows 0 (a left join), so it is not mistaken for
    missing data.
    """
    sql = f"""
        WITH f AS (
            SELECT time_step, count(*) AS transactions
            FROM {_scan(processed_dir, "features")} GROUP BY time_step
        ),
        e AS (
            SELECT time_step, count(*) AS edges
            FROM {_scan(processed_dir, "edges")} GROUP BY time_step
        ),
        c AS (
            SELECT time_step,
                   count(*) FILTER (WHERE label = 1) AS illicit,
                   count(*) FILTER (WHERE label = 2) AS licit,
                   count(*) FILTER (WHERE label IS NULL) AS unlabelled
            FROM {_scan(processed_dir, "classes")} GROUP BY time_step
        )
        SELECT f.time_step, f.transactions, coalesce(e.edges, 0) AS edges,
               c.illicit, c.licit, c.unlabelled
        FROM f
        LEFT JOIN e USING (time_step)
        JOIN c USING (time_step)
        ORDER BY f.time_step
    """
    with duckdb.connect() as con:
        return con.execute(sql).df()


def node_degrees(processed_dir: Path, step: int) -> pd.DataFrame:
    """In-degree and out-degree of every transaction in one time step.

    Edges never cross time steps, so one step's edges are all that is needed.
    This is the answer Phase 2's Spark job must reproduce exactly.
    """
    sql = f"""
        WITH nodes AS (
            SELECT tx_id FROM {_scan(processed_dir, "features")} WHERE time_step = ?
        ),
        out_d AS (
            SELECT src_tx_id AS tx_id, count(*) AS out_degree
            FROM {_scan(processed_dir, "edges")} WHERE time_step = ? GROUP BY src_tx_id
        ),
        in_d AS (
            SELECT dst_tx_id AS tx_id, count(*) AS in_degree
            FROM {_scan(processed_dir, "edges")} WHERE time_step = ? GROUP BY dst_tx_id
        )
        SELECT n.tx_id,
               coalesce(in_d.in_degree, 0) AS in_degree,
               coalesce(out_d.out_degree, 0) AS out_degree
        FROM nodes n
        LEFT JOIN in_d USING (tx_id)
        LEFT JOIN out_d USING (tx_id)
        ORDER BY n.tx_id
    """
    step = int(step)
    with duckdb.connect() as con:
        return con.execute(sql, [step, step, step]).df()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query the GraphGuard Parquet output.")
    parser.add_argument("--processed", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--step", type=int, help="show the busiest transactions of this time step")
    args = parser.parse_args(argv)

    try:
        if args.step is None:
            print(step_summary(args.processed).to_string(index=False))
        else:
            degrees = node_degrees(args.processed, args.step)
            degrees["total"] = degrees["in_degree"] + degrees["out_degree"]
            print(degrees.nlargest(10, "total").to_string(index=False))
    except FileNotFoundError as error:
        print(f"query failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
