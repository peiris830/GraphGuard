"""Write pipeline output as Parquet, safe to rerun and safe to interrupt."""

import os
import shutil
import uuid
from pathlib import Path

import pandas as pd


def write_partitioned(
    df: pd.DataFrame, out_dir: Path, partition_col: str = "time_step"
) -> None:
    """Write df as one folder per value of `partition_col`.

    Layout: out_dir/time_step=7/part-0.parquet. The partition value lives in
    the folder name (the Hive convention DuckDB and Spark expect), so the
    column is left out of the file.

    Rerunning replaces each step it writes and leaves other steps alone, so
    writing the same data twice gives the same result, never doubled rows.
    """
    out_dir = Path(out_dir)
    if partition_col not in df.columns:
        raise ValueError(f"no {partition_col!r} column to partition by")
    values = df[partition_col]
    # groupby skips null keys, so rows would vanish from the output without this.
    if values.isna().any():
        raise ValueError(f"null values in {partition_col!r}, cannot partition")
    if (values % 1 != 0).any():
        raise ValueError(f"{partition_col!r} must hold whole numbers")

    out_dir.mkdir(parents=True, exist_ok=True)
    for value, rows in df.groupby(partition_col, sort=True):
        _replace_partition(
            rows.drop(columns=partition_col), out_dir, f"{partition_col}={int(value)}"
        )


def _replace_partition(rows: pd.DataFrame, out_dir: Path, name: str) -> None:
    """Swap in a fully written folder, so readers never see a half-written one."""
    final = out_dir / name
    tmp = out_dir / f".tmp-{name}-{uuid.uuid4().hex}"
    old = out_dir / f".old-{name}-{uuid.uuid4().hex}"

    tmp.mkdir()
    try:
        rows.to_parquet(tmp / "part-0.parquet", index=False)
    except BaseException:
        # The previous output at `final` was never touched.
        shutil.rmtree(tmp, ignore_errors=True)
        raise

    # Between these two renames `final` briefly does not exist. A crash there
    # leaves the previous version in `old`, so nothing is lost, only misplaced.
    if final.exists():
        final.rename(old)
    tmp.rename(final)
    shutil.rmtree(old, ignore_errors=True)


def write_quarantine(rejected: pd.DataFrame, path: Path) -> None:
    """Write rejected rows to one Parquet file, replacing any previous one.

    The file is written even when empty: an empty file says "checked, nothing
    rejected", while a missing file says nothing.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        rejected.to_parquet(tmp, index=False)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
