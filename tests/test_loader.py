import pytest

from graphguard.loader import FEATURE_COLUMNS, read_features


def write_features_csv(path, rows):
    # The real file has no header row, so neither does this fixture.
    path.write_text("\n".join(",".join(str(v) for v in row) for row in rows) + "\n")


def make_row(tx_id, time_step, fill=0.5):
    return [tx_id, time_step] + [fill] * 165


def test_feature_columns_are_tx_id_time_step_and_165_features():
    assert len(FEATURE_COLUMNS) == 167
    assert FEATURE_COLUMNS[:3] == ["tx_id", "time_step", "feat_1"]
    assert FEATURE_COLUMNS[-1] == "feat_165"


def test_first_line_is_data_not_a_header(tmp_path):
    csv = tmp_path / "features.csv"
    write_features_csv(csv, [make_row(111, 1), make_row(222, 2)])

    df = read_features(csv)

    assert len(df) == 2
    assert df["tx_id"].tolist() == [111, 222]


def test_ids_and_time_steps_are_integers(tmp_path):
    csv = tmp_path / "features.csv"
    write_features_csv(csv, [make_row(111, 1), make_row(222, 49)])

    df = read_features(csv)

    assert df["tx_id"].dtype == "int64"
    assert df["time_step"].dtype == "int64"
    assert df["feat_1"].dtype == "float64"


def test_wrong_column_count_raises(tmp_path):
    csv = tmp_path / "features.csv"
    write_features_csv(csv, [[111, 1, 0.5, 0.5]])

    with pytest.raises(ValueError, match="167"):
        read_features(csv)
