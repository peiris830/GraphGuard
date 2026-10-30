import pandas as pd
import pytest

from graphguard.quarantine import split_valid_rows


def features(time_steps):
    return pd.DataFrame({"tx_id": range(len(time_steps)), "time_step": time_steps})


def test_all_valid_rows_pass_through_and_nothing_is_rejected():
    # The column is int64, so this also guards against the validator being
    # fed NumPy integers, which it rejects (np.int64 is not a Python int).
    clean, rejected = split_valid_rows(features([1, 7, 49]))

    assert len(clean) == 3
    assert rejected.empty


def test_invalid_time_steps_are_rejected_with_a_reason():
    clean, rejected = split_valid_rows(features([1, 0, 50, 49]), max_reject_rate=1.0)

    assert clean["tx_id"].tolist() == [0, 3]
    assert rejected["tx_id"].tolist() == [1, 2]
    assert rejected["reason"].tolist() == ["invalid_time_step", "invalid_time_step"]


def test_clean_and_rejected_together_account_for_every_input_row():
    df = features([1, 0, 50, 49, 7])

    clean, rejected = split_valid_rows(df, max_reject_rate=1.0)

    assert sorted(clean["tx_id"].tolist() + rejected["tx_id"].tolist()) == df["tx_id"].tolist()


def test_original_columns_are_kept_and_clean_rows_get_no_reason_column():
    clean, rejected = split_valid_rows(features([1, 0]), max_reject_rate=1.0)

    assert clean.columns.tolist() == ["tx_id", "time_step"]
    assert rejected.columns.tolist() == ["tx_id", "time_step", "reason"]


def test_a_missing_time_step_is_rejected():
    # NaN forces the column to float; 7.0 is still valid, NaN is not.
    clean, rejected = split_valid_rows(features([7.0, float("nan")]), max_reject_rate=1.0)

    assert clean["tx_id"].tolist() == [0]
    assert rejected["tx_id"].tolist() == [1]


def test_rejects_exactly_at_the_threshold_are_allowed():
    steps = [1] * 99 + [0]  # 1 bad row out of 100 = 1%

    clean, rejected = split_valid_rows(features(steps), max_reject_rate=0.01)

    assert len(clean) == 99
    assert len(rejected) == 1


def test_rejects_above_the_threshold_stop_the_run():
    steps = [1] * 98 + [0, 0]  # 2 bad rows out of 100 = 2%

    with pytest.raises(ValueError, match="2 of 100"):
        split_valid_rows(features(steps), max_reject_rate=0.01)


def test_default_threshold_is_one_percent():
    steps = [1] * 98 + [0, 0]

    with pytest.raises(ValueError):
        split_valid_rows(features(steps))


def test_empty_input_returns_two_empty_tables_without_dividing_by_zero():
    clean, rejected = split_valid_rows(features([]))

    assert clean.empty
    assert rejected.empty
