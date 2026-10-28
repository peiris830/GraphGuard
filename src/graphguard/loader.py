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
