import pytest

from graphguard.validation import is_valid_time_step


@pytest.mark.parametrize(
    "value",
    [1, 7, 49, 1.0, 7.0, 49.0],
    ids=repr,
)
def test_accepts_whole_numbers_in_range(value):
    assert is_valid_time_step(value) is True


@pytest.mark.parametrize(
    "value",
    [0, 50, -3, 0.9, 49.1],
    ids=repr,
)
def test_rejects_numbers_out_of_range(value):
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize("value", [7.5, 1.1, 48.9], ids=repr)
def test_rejects_fractional_floats(value):
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize("value", [True, False], ids=repr)
def test_rejects_bools(value):
    # bool is a subclass of int, so True == 1 unless the function guards it.
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=repr,
)
def test_rejects_non_finite_floats(value):
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize("value", ["7", "", "abc", None, [7]], ids=repr)
def test_rejects_non_numeric_types(value):
    # Strings are converted by the loader, never accepted here.
    assert is_valid_time_step(value) is False
