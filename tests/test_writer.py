import pandas as pd
import pytest

from graphguard.writer import write_partitioned, write_quarantine


def features(rows):
    return pd.DataFrame(rows, columns=["tx_id", "time_step", "feat_1"])


def read_step(out_dir, step):
    return pd.read_parquet(out_dir / f"time_step={step}" / "part-0.parquet")


def test_writes_one_folder_per_time_step(tmp_path):
    df = features([(1, 1, 0.5), (2, 1, 0.6), (3, 2, 0.7)])

    write_partitioned(df, tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["time_step=1", "time_step=2"]
    assert len(read_step(tmp_path, 1)) == 2
    assert len(read_step(tmp_path, 2)) == 1


def test_partition_column_lives_in_the_folder_name_not_the_file(tmp_path):
    write_partitioned(features([(1, 7, 0.5)]), tmp_path)

    assert read_step(tmp_path, 7).columns.tolist() == ["tx_id", "feat_1"]


def test_types_survive_the_round_trip_including_nullable_labels(tmp_path):
    df = pd.DataFrame(
        {
            "tx_id": [1, 2, 3],
            "time_step": [5, 5, 5],
            "label": pd.array([1, 2, None], dtype="Int64"),
        }
    )

    write_partitioned(df, tmp_path)
    back = read_step(tmp_path, 5)

    assert back["tx_id"].dtype == "int64"
    assert str(back["label"].dtype) == "Int64"
    assert back["label"].isna().tolist() == [False, False, True]


def test_running_twice_gives_the_same_data_not_doubled_rows(tmp_path):
    df = features([(1, 1, 0.5), (2, 1, 0.6)])

    write_partitioned(df, tmp_path)
    write_partitioned(df, tmp_path)

    assert len(read_step(tmp_path, 1)) == 2
    assert [p.name for p in tmp_path.iterdir()] == ["time_step=1"]


def test_rewriting_a_step_replaces_it_and_leaves_other_steps_alone(tmp_path):
    write_partitioned(features([(1, 1, 0.5), (2, 2, 0.6)]), tmp_path)

    write_partitioned(features([(9, 1, 0.9)]), tmp_path)

    assert read_step(tmp_path, 1)["tx_id"].tolist() == [9]
    assert read_step(tmp_path, 2)["tx_id"].tolist() == [2]


def test_a_failed_write_keeps_the_previous_output_and_leaves_no_temp_files(
    tmp_path, monkeypatch
):
    write_partitioned(features([(1, 1, 0.5)]), tmp_path)

    def explode(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", explode)
    with pytest.raises(OSError, match="disk full"):
        write_partitioned(features([(9, 1, 0.9)]), tmp_path)
    monkeypatch.undo()

    assert read_step(tmp_path, 1)["tx_id"].tolist() == [1]
    assert [p.name for p in tmp_path.iterdir()] == ["time_step=1"]


def test_missing_partition_column_raises(tmp_path):
    with pytest.raises(ValueError, match="time_step"):
        write_partitioned(pd.DataFrame({"tx_id": [1]}), tmp_path)


def test_null_time_step_raises_instead_of_silently_dropping_rows(tmp_path):
    # groupby skips NaN keys, so without a check these rows would vanish.
    df = features([(1, 1, 0.5), (2, float("nan"), 0.6)])

    with pytest.raises(ValueError, match="null"):
        write_partitioned(df, tmp_path)


def test_fractional_time_step_raises(tmp_path):
    with pytest.raises(ValueError, match="whole"):
        write_partitioned(features([(1, 7.5, 0.5)]), tmp_path)


def test_whole_number_floats_become_clean_folder_names(tmp_path):
    write_partitioned(features([(1, 7.0, 0.5)]), tmp_path)

    assert [p.name for p in tmp_path.iterdir()] == ["time_step=7"]


def test_quarantine_file_keeps_rows_and_reasons(tmp_path):
    rejected = features([(1, 0, 0.5)]).assign(reason="invalid_time_step")
    path = tmp_path / "quarantine" / "features.parquet"

    write_quarantine(rejected, path)

    back = pd.read_parquet(path)
    assert back["reason"].tolist() == ["invalid_time_step"]
    assert back["tx_id"].tolist() == [1]


def test_quarantine_file_is_written_even_when_nothing_was_rejected(tmp_path):
    # An empty file says "checked, nothing wrong"; a missing one says nothing.
    empty = features([]).assign(reason="invalid_time_step")
    path = tmp_path / "features.parquet"

    write_quarantine(empty, path)

    assert path.exists()
    assert pd.read_parquet(path).empty


def test_quarantine_rerun_replaces_the_previous_file(tmp_path):
    path = tmp_path / "features.parquet"
    write_quarantine(features([(1, 0, 0.5)]).assign(reason="a"), path)

    write_quarantine(features([(2, 50, 0.5)]).assign(reason="b"), path)

    assert pd.read_parquet(path)["tx_id"].tolist() == [2]
