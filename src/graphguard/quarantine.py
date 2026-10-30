"""Split rows into clean and rejected instead of failing on the first bad one."""

import pandas as pd

from graphguard.validation import is_valid_time_step

DEFAULT_MAX_REJECT_RATE = 0.01


def split_valid_rows(
    features: pd.DataFrame, max_reject_rate: float = DEFAULT_MAX_REJECT_RATE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (clean, rejected) rows of the features table.

    Rejected rows keep all their columns and gain a `reason`. If more than
    `max_reject_rate` of the rows are rejected the run stops, because a large
    share of bad rows usually means something upstream broke (a shifted
    column, the wrong file) and loading the rest would hide that.
    """
    # Series.map hands the validator plain Python ints. Iterating the NumPy
    # array instead would pass np.int64, which the validator rejects.
    is_valid = features["time_step"].map(is_valid_time_step).astype(bool)
    clean = features[is_valid]
    # copy() consolidates the 167 column blocks; assign() on a fragmented frame warns.
    rejected = features[~is_valid].copy().assign(reason="invalid_time_step")

    if len(features) and len(rejected) / len(features) > max_reject_rate:
        raise ValueError(
            f"rejected {len(rejected)} of {len(features)} rows "
            f"({len(rejected) / len(features):.1%}), above the "
            f"{max_reject_rate:.1%} limit; first rejected tx_ids: "
            f"{rejected['tx_id'].head(5).tolist()}"
        )
    return clean, rejected
