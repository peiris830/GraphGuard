import pandas as pd
import pytest

from graphguard.pipeline import IntegrityError, main, run_pipeline
from graphguard.quarantine import DEFAULT_MAX_REJECT_RATE


def write_raw(raw, features, classes, edges):
    raw.mkdir(parents=True, exist_ok=True)
    # The features file has no header; the other two do.
    feature_lines = [",".join(str(v) for v in [tx, step] + [0.5] * 165) for tx, step in features]
    (raw / "elliptic_txs_features.csv").write_text("\n".join(feature_lines) + "\n")
    class_lines = ["txId,class"] + [f"{tx},{label}" for tx, label in classes]
    (raw / "elliptic_txs_classes.csv").write_text("\n".join(class_lines) + "\n")
    edge_lines = ["txId1,txId2"] + [f"{src},{dst}" for src, dst in edges]
    (raw / "elliptic_txs_edgelist.csv").write_text("\n".join(edge_lines) + "\n")


@pytest.fixture
def raw(tmp_path):
    path = tmp_path / "raw"
    write_raw(
        path,
        features=[(1, 1), (2, 1), (3, 2)],
        classes=[(1, "unknown"), (2, "1"), (3, "2")],
        edges=[(1, 2)],
    )
    return path


def read_part(out, table, step):
    return pd.read_parquet(out / table / f"time_step={step}" / "part-0.parquet")


def test_pipeline_writes_every_table_partitioned_by_time_step(raw, tmp_path):
    out = tmp_path / "out"

    run_pipeline(raw, out)

    assert sorted(p.name for p in (out / "features").iterdir()) == ["time_step=1", "time_step=2"]
    assert sorted(p.name for p in (out / "classes").iterdir()) == ["time_step=1", "time_step=2"]
    assert sorted(read_part(out, "classes", 1)["tx_id"]) == [1, 2]
    assert (out / "quarantine" / "features.parquet").exists()


def test_edges_are_partitioned_by_the_time_step_of_their_source(raw, tmp_path):
    out = tmp_path / "out"

    run_pipeline(raw, out)

    assert [p.name for p in (out / "edges").iterdir()] == ["time_step=1"]
    assert read_part(out, "edges", 1)[["src_tx_id", "dst_tx_id"]].values.tolist() == [[1, 2]]


def test_unknown_labels_stay_null_through_the_whole_pipeline(raw, tmp_path):
    out = tmp_path / "out"

    run_pipeline(raw, out)

    labels = read_part(out, "classes", 1).set_index("tx_id")["label"]
    assert labels.isna().loc[1]
    assert labels.loc[2] == 1


def test_summary_reports_what_was_read_written_and_rejected(raw, tmp_path):
    summary = run_pipeline(raw, tmp_path / "out")

    assert summary.features_read == 3
    assert summary.features_written == 3
    assert summary.features_rejected == 0
    assert summary.classes_written == 3
    assert summary.edges_written == 1


def test_rerunning_gives_the_same_output_not_doubled_rows(raw, tmp_path):
    out = tmp_path / "out"

    run_pipeline(raw, out)
    second = run_pipeline(raw, out)

    assert second.features_written == 3
    assert len(read_part(out, "features", 1)) == 2
    assert len(read_part(out, "classes", 1)) == 2


@pytest.mark.parametrize(
    "features, classes, edges, expected",
    [
        ([(1, 1), (2, 1)], [(1, "1"), (2, "1")], [(1, 99)], "orphan edges"),
        ([(1, 1), (2, 2)], [(1, "1"), (2, "1")], [(1, 2)], "cross-step edges"),
        ([(1, 1), (1, 1)], [(1, "1")], [], "duplicate tx_ids in features"),
        ([(1, 1), (2, 1)], [(1, "1")], [], "unmatched class ids"),
    ],
    ids=["orphan", "cross-step", "duplicate", "unmatched-class"],
)
def test_integrity_problems_stop_the_run_before_anything_is_written(
    tmp_path, features, classes, edges, expected
):
    raw = tmp_path / "raw"
    out = tmp_path / "out"
    write_raw(raw, features, classes, edges)

    with pytest.raises(IntegrityError, match=expected):
        run_pipeline(raw, out)

    assert not out.exists() or not any(out.iterdir())


def test_a_failed_run_leaves_the_previous_good_output_untouched(raw, tmp_path):
    out = tmp_path / "out"
    run_pipeline(raw, out)
    write_raw(
        tmp_path / "bad",
        features=[(1, 1), (2, 1)],
        classes=[(1, "1"), (2, "1")],
        edges=[(1, 99)],
    )

    with pytest.raises(IntegrityError):
        run_pipeline(tmp_path / "bad", out)

    assert len(read_part(out, "features", 1)) == 2
    assert len(read_part(out, "features", 2)) == 1


def test_rejected_feature_rows_are_quarantined_and_their_dependents_dropped(tmp_path):
    raw = tmp_path / "raw"
    out = tmp_path / "out"
    write_raw(
        raw,
        features=[(1, 1), (2, 1), (3, 0)],  # time step 0 is invalid
        classes=[(1, "1"), (2, "2"), (3, "1")],
        edges=[(1, 2)],
    )

    summary = run_pipeline(raw, out, max_reject_rate=1.0)

    quarantined = pd.read_parquet(out / "quarantine" / "features.parquet")
    assert quarantined["tx_id"].tolist() == [3]
    assert quarantined["reason"].tolist() == ["invalid_time_step"]
    assert not (out / "features" / "time_step=0").exists()
    assert summary.features_rejected == 1
    assert summary.classes_dropped == 1
    assert summary.classes_written == 2


def test_too_many_rejected_rows_stop_the_run_and_write_nothing(tmp_path):
    raw = tmp_path / "raw"
    out = tmp_path / "out"
    write_raw(
        raw,
        features=[(1, 1), (2, 0)],
        classes=[(1, "1"), (2, "1")],
        edges=[],
    )

    with pytest.raises(ValueError, match="rejected 1 of 2"):
        run_pipeline(raw, out, max_reject_rate=DEFAULT_MAX_REJECT_RATE)

    assert not out.exists() or not any(out.iterdir())


def test_integrity_error_message_names_the_check_and_shows_examples(tmp_path):
    raw = tmp_path / "raw"
    write_raw(raw, [(1, 1)], [(1, "1")], [(1, 99)])

    with pytest.raises(IntegrityError) as error:
        run_pipeline(raw, tmp_path / "out")

    assert "orphan edges: 1" in str(error.value)
    assert "99" in str(error.value)


def test_command_line_returns_zero_on_success(raw, tmp_path, capsys):
    code = main(["--raw", str(raw), "--out", str(tmp_path / "out")])

    assert code == 0
    assert "features" in capsys.readouterr().out


def test_command_line_returns_one_and_explains_on_failure(tmp_path, capsys):
    raw = tmp_path / "raw"
    write_raw(raw, [(1, 1)], [(1, "1")], [(1, 99)])

    code = main(["--raw", str(raw), "--out", str(tmp_path / "out")])

    assert code == 1
    assert "orphan edges" in capsys.readouterr().err
