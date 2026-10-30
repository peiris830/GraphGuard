"""Checks that need more than one table to answer.

Each function returns the offending rows (empty means the check passed),
not a yes/no, so the caller can quarantine or report exactly what failed.
"""

import pandas as pd


def find_orphan_edges(edges: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Edges where the source or destination is not a known transaction."""
    known = features["tx_id"]
    missing = ~edges["src_tx_id"].isin(known) | ~edges["dst_tx_id"].isin(known)
    return edges[missing]


def find_cross_step_edges(edges: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Edges whose two ends sit in different time steps.

    Orphan edges are skipped here (their step is unknown) so each problem
    is reported by exactly one check. Transactions listed more than once are
    skipped too: they have no single step, and find_duplicate_tx_ids reports
    them. The lookup would raise on a repeated id otherwise.
    """
    unique = features.drop_duplicates(subset="tx_id", keep=False)
    step_of = unique.set_index("tx_id")["time_step"]
    src_step = edges["src_tx_id"].map(step_of)
    dst_step = edges["dst_tx_id"].map(step_of)
    known = src_step.notna() & dst_step.notna()
    return edges[known & (src_step != dst_step)]


def find_unmatched_class_ids(classes: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Transaction ids present in only one of the classes and features tables."""
    only_in_classes = classes.loc[~classes["tx_id"].isin(features["tx_id"]), "tx_id"]
    only_in_features = features.loc[~features["tx_id"].isin(classes["tx_id"]), "tx_id"]
    return pd.concat(
        [
            pd.DataFrame({"tx_id": only_in_classes, "problem": "missing_from_features"}),
            pd.DataFrame({"tx_id": only_in_features, "problem": "missing_from_classes"}),
        ],
        ignore_index=True,
    )


def find_duplicate_tx_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Every row whose tx_id appears more than once (all copies, not just extras)."""
    return df[df["tx_id"].duplicated(keep=False)]
