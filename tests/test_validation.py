import numpy as np
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


# Pipeline data arrives as pandas columns, so the validator sees NumPy
# scalars as well as plain Python numbers. np.int64 is not a Python int.
@pytest.mark.parametrize(
    "value",
    [np.int64(7), np.int32(1), np.uint8(49), np.float64(7.0), np.float32(7.0)],
    ids=repr,
)
def test_accepts_numpy_numbers_in_range(value):
    assert is_valid_time_step(value) is True


@pytest.mark.parametrize(
    "value",
    [
        np.int64(0),
        np.int64(50),
        np.float64(7.5),
        np.float64("nan"),
        np.float32("inf"),
    ],
    ids=repr,
)
def test_rejects_numpy_numbers_that_are_invalid(value):
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize("value", [np.bool_(True), np.bool_(False)], ids=repr)
def test_rejects_numpy_bools(value):
    # np.bool_ is not a Python bool, so the bool guard alone would miss it.
    assert is_valid_time_step(value) is False


@pytest.mark.parametrize("value", [10**400, -(10**400)], ids=["huge", "-huge"])
def test_huge_ints_are_rejected_not_an_error(value):
    # Too big to convert to float; the finite check must not be applied to ints.
    assert is_valid_time_step(value) is False
