import pytest

from graphguard.pipeline import run_pipeline
from graphguard.queries import node_degrees, step_summary


def write_raw(raw, features, classes, edges):
    raw.mkdir(parents=True, exist_ok=True)
    feature_lines = [",".join(str(v) for v in [tx, step] + [0.5] * 165) for tx, step in features]
    (raw / "elliptic_txs_features.csv").write_text("\n".join(feature_lines) + "\n")
    class_lines = ["txId,class"] + [f"{tx},{label}" for tx, label in classes]
    (raw / "elliptic_txs_classes.csv").write_text("\n".join(class_lines) + "\n")
    edge_lines = ["txId1,txId2"] + [f"{src},{dst}" for src, dst in edges]
    (raw / "elliptic_txs_edgelist.csv").write_text("\n".join(edge_lines) + "\n")


@pytest.fixture
def processed(tmp_path):
    # Step 1: transactions 1, 2, 3 with edges 1->2, 1->3, 2->3.
    # Step 2: transaction 4 alone, so it has no edges at all.
    raw = tmp_path / "raw"
    write_raw(
        raw,
        features=[(1, 1), (2, 1), (3, 1), (4, 2)],
        classes=[(1, "1"), (2, "2"), (3, "unknown"), (4, "2")],
        edges=[(1, 2), (1, 3), (2, 3)],
    )
    out = tmp_path / "processed"
    run_pipeline(raw, out)
    return out


def test_step_summary_counts_each_table_per_time_step(processed):
    summary = step_summary(processed)

    assert summary.columns.tolist() == [
        "time_step", "transactions", "edges", "illicit", "licit", "unlabelled",
    ]
    assert summary.values.tolist() == [
        [1, 3, 3, 1, 1, 1],
        [2, 1, 0, 0, 1, 0],
    ]


def test_a_step_with_no_edges_shows_zero_not_a_missing_row(processed):
    summary = step_summary(processed).set_index("time_step")

    assert summary.loc[2, "edges"] == 0


def test_node_degrees_counts_in_and_out_edges_for_one_step(processed):
    degrees = node_degrees(processed, step=1)

    assert degrees.columns.tolist() == ["tx_id", "in_degree", "out_degree"]
    assert degrees.values.tolist() == [
        [1, 0, 2],
        [2, 1, 1],
        [3, 2, 0],
    ]


def test_node_degrees_includes_transactions_with_no_edges(processed):
    degrees = node_degrees(processed, step=2)

    assert degrees.values.tolist() == [[4, 0, 0]]


def test_node_degrees_for_an_unknown_step_is_empty(processed):
    assert node_degrees(processed, step=30).empty


def test_degrees_only_count_edges_of_the_requested_step(processed):
    # Transaction 3's two incoming edges are in step 1; step 2 must not see them.
    degrees = node_degrees(processed, step=2).set_index("tx_id")

    assert degrees.loc[4, "in_degree"] == 0


def test_missing_output_folder_explains_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="graphguard.pipeline"):
        step_summary(tmp_path / "nothing-here")
