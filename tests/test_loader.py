import pytest

from graphguard.loader import FEATURE_COLUMNS, read_classes, read_edges, read_features


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


def write_classes_csv(path, rows):
    # Unlike the features file, the classes file has a header row.
    lines = ["txId,class"] + [f"{tx_id},{label}" for tx_id, label in rows]
    path.write_text("\n".join(lines) + "\n")


def test_classes_have_raw_text_and_numeric_label(tmp_path):
    csv = tmp_path / "classes.csv"
    write_classes_csv(csv, [(111, "1"), (222, "2"), (333, "unknown")])

    df = read_classes(csv)

    assert df.columns.tolist() == ["tx_id", "class_raw", "label"]
    assert df["tx_id"].tolist() == [111, 222, 333]
    assert df["class_raw"].tolist() == ["1", "2", "unknown"]


def test_unknown_becomes_null_and_known_labels_stay_numbers(tmp_path):
    csv = tmp_path / "classes.csv"
    write_classes_csv(csv, [(111, "1"), (222, "2"), (333, "unknown")])

    df = read_classes(csv)

    assert df["label"].tolist()[:2] == [1, 2]
    assert df["label"].isna().tolist() == [False, False, True]


def test_label_is_a_nullable_integer_not_a_float(tmp_path):
    # A plain int column cannot hold nulls, so pandas would silently turn
    # 1 and 2 into 1.0 and 2.0. Int64 keeps them as integers.
    csv = tmp_path / "classes.csv"
    write_classes_csv(csv, [(111, "1"), (333, "unknown")])

    df = read_classes(csv)

    assert str(df["label"].dtype) == "Int64"


@pytest.mark.parametrize("bad_value", ["3", "0", "illicit", "", "NA"], ids=repr)
def test_unexpected_class_value_raises(tmp_path, bad_value):
    csv = tmp_path / "classes.csv"
    write_classes_csv(csv, [(111, "1"), (222, bad_value)])

    with pytest.raises(ValueError, match="class"):
        read_classes(csv)


def test_classes_wrong_column_count_raises(tmp_path):
    csv = tmp_path / "classes.csv"
    csv.write_text("txId,class,extra\n111,1,x\n")

    with pytest.raises(ValueError, match="2"):
        read_classes(csv)


def write_edges_csv(path, rows):
    lines = ["txId1,txId2"] + [f"{src},{dst}" for src, dst in rows]
    path.write_text("\n".join(lines) + "\n")


def test_edges_use_directional_column_names(tmp_path):
    csv = tmp_path / "edges.csv"
    write_edges_csv(csv, [(111, 222), (222, 333)])

    df = read_edges(csv)

    assert df.columns.tolist() == ["src_tx_id", "dst_tx_id"]
    assert df["src_tx_id"].tolist() == [111, 222]
    assert df["dst_tx_id"].tolist() == [222, 333]


def test_edge_ids_are_integers(tmp_path):
    csv = tmp_path / "edges.csv"
    write_edges_csv(csv, [(111, 222)])

    df = read_edges(csv)

    assert df["src_tx_id"].dtype == "int64"
    assert df["dst_tx_id"].dtype == "int64"


def test_edges_wrong_column_count_raises(tmp_path):
    csv = tmp_path / "edges.csv"
    csv.write_text("txId1,txId2,weight\n111,222,0.5\n")

    with pytest.raises(ValueError, match="2"):
        read_edges(csv)


def test_edges_with_missing_ids_raise(tmp_path):
    # A blank endpoint would make pandas turn the whole column into floats.
    csv = tmp_path / "edges.csv"
    csv.write_text("txId1,txId2\n111,222\n333,\n")

    with pytest.raises(ValueError, match="missing"):
        read_edges(csv)
