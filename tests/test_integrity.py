import pandas as pd

from graphguard.integrity import (
    find_cross_step_edges,
    find_duplicate_tx_ids,
    find_orphan_edges,
    find_unmatched_class_ids,
)


def features(*pairs):
    return pd.DataFrame(pairs, columns=["tx_id", "time_step"])


def edges(*pairs):
    return pd.DataFrame(pairs, columns=["src_tx_id", "dst_tx_id"])


def classes(*tx_ids):
    return pd.DataFrame({"tx_id": list(tx_ids)})


def test_orphan_edges_empty_when_every_endpoint_exists():
    result = find_orphan_edges(edges((1, 2), (2, 3)), features((1, 1), (2, 1), (3, 1)))

    assert result.empty


def test_orphan_edges_flags_a_missing_source_or_destination():
    f = features((1, 1), (2, 1))
    e = edges((1, 2), (9, 2), (1, 8))

    result = find_orphan_edges(e, f)

    assert result.values.tolist() == [[9, 2], [1, 8]]


def test_cross_step_edges_empty_when_endpoints_share_a_step():
    f = features((1, 5), (2, 5), (3, 6))

    result = find_cross_step_edges(edges((1, 2)), f)

    assert result.empty


def test_cross_step_edges_flags_edges_between_steps():
    f = features((1, 5), (2, 5), (3, 6))

    result = find_cross_step_edges(edges((1, 2), (2, 3)), f)

    assert result.values.tolist() == [[2, 3]]


def test_cross_step_edges_ignores_orphans_so_each_problem_is_reported_once():
    f = features((1, 5), (2, 5))

    result = find_cross_step_edges(edges((1, 9)), f)

    assert result.empty


def test_unmatched_class_ids_empty_when_the_id_sets_match():
    result = find_unmatched_class_ids(classes(1, 2), features((1, 1), (2, 1)))

    assert result.empty


def test_unmatched_class_ids_says_which_file_is_missing_the_id():
    result = find_unmatched_class_ids(classes(1, 2), features((2, 1), (3, 1)))

    assert sorted(result.values.tolist()) == [[1, "missing_from_features"], [3, "missing_from_classes"]]


def test_duplicate_tx_ids_returns_every_copy():
    df = pd.DataFrame({"tx_id": [1, 2, 2, 3], "time_step": [1, 1, 1, 1]})

    result = find_duplicate_tx_ids(df)

    assert result["tx_id"].tolist() == [2, 2]


def test_duplicate_tx_ids_empty_when_unique():
    assert find_duplicate_tx_ids(classes(1, 2, 3)).empty


def test_cross_step_check_does_not_crash_on_duplicate_tx_ids():
    # Duplicates are reported by their own check; this one must still run.
    # A duplicated id has no single time step, so edges touching it are skipped.
    f = features((1, 5), (1, 6), (2, 5), (3, 6))

    result = find_cross_step_edges(edges((1, 2), (2, 3)), f)

    assert result.values.tolist() == [[2, 3]]
