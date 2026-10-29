from pathlib import Path

import pandas as pd

N_FEATURES = 165
FEATURE_COLUMNS = ["tx_id", "time_step"] + [f"feat_{i}" for i in range(1, N_FEATURES + 1)]


def read_features(path: Path) -> pd.DataFrame:
    """Read elliptic_txs_features.csv into a typed DataFrame.

    The file has no header row, so the column names are supplied here.
    """
    # pandas pads short rows with NaN and shifts long ones, so a wrong column
    # count would otherwise load without any error. Check the first row up front.
    first_row = pd.read_csv(path, header=None, nrows=1)
    if first_row.shape[1] != len(FEATURE_COLUMNS):
        raise ValueError(
            f"expected {len(FEATURE_COLUMNS)} columns in {path}, "
            f"found {first_row.shape[1]}"
        )
    return pd.read_csv(path, header=None, names=FEATURE_COLUMNS)


CLASS_COLUMNS = ["tx_id", "class_raw"]
CLASS_TO_LABEL = {"1": 1, "2": 2, "unknown": pd.NA}


def read_classes(path: Path) -> pd.DataFrame:
    """Read elliptic_txs_classes.csv into tx_id, class_raw and label.

    class_raw keeps the original text ("1", "2", "unknown"). label is a
    nullable integer where "unknown" becomes a real null.
    """
    first_row = pd.read_csv(path, nrows=1)
    if first_row.shape[1] != len(CLASS_COLUMNS):
        raise ValueError(
            f"expected {len(CLASS_COLUMNS)} columns in {path}, "
            f"found {first_row.shape[1]}"
        )
    # Read class as text and turn off NA parsing: otherwise an empty cell or
    # the string "NA" would become NaN and slip past the value check below.
    df = pd.read_csv(
        path,
        header=0,
        names=CLASS_COLUMNS,
        dtype={"class_raw": str},
        keep_default_na=False,
    )
    unexpected = sorted(set(df["class_raw"]) - set(CLASS_TO_LABEL))
    if unexpected:
        raise ValueError(
            f"unexpected class values in {path}: {unexpected}; "
            f"expected one of {sorted(CLASS_TO_LABEL)}"
        )
    df["label"] = df["class_raw"].map(CLASS_TO_LABEL).astype("Int64")
    return df


EDGE_COLUMNS = ["src_tx_id", "dst_tx_id"]


def read_edges(path: Path) -> pd.DataFrame:
    """Read elliptic_txs_edgelist.csv into src_tx_id and dst_tx_id.

    Each row is a directed edge from the source transaction to the one it
    funds. Whether both ends exist in the features file is checked
    separately, since that needs two files.
    """
    first_row = pd.read_csv(path, nrows=1)
    if first_row.shape[1] != len(EDGE_COLUMNS):
        raise ValueError(
            f"expected {len(EDGE_COLUMNS)} columns in {path}, "
            f"found {first_row.shape[1]}"
        )
    df = pd.read_csv(path, header=0, names=EDGE_COLUMNS)
    # A blank endpoint makes pandas read the whole column as floats with NaN,
    # which would then compare unequal to every integer tx_id downstream.
    if df.isna().any().any():
        raise ValueError(f"missing transaction ids in {path}")
    return df.astype("int64")
