import math
import numbers

MIN_TIME_STEP = 1
MAX_TIME_STEP = 49


def is_valid_time_step(step) -> bool:
    """Return True if `step` is a whole number from 1 to 49.

    Ints and whole-number floats (7.0) are accepted, including the NumPy
    versions that pandas columns hand over. Pandas can also turn an integer
    column into floats when it has gaps. Bools, strings, NaN and infinity
    are rejected.
    """
    # bool is a subclass of int, so this check has to come before the number one.
    # np.bool_ is not a bool, but it is not a numbers.Real either, so the next
    # check rejects it.
    if isinstance(step, bool):
        return False
    # numbers.Real covers Python and NumPy ints and floats; np.int64 is not an int.
    if not isinstance(step, numbers.Real):
        return False
    # Only non-integers can be NaN, inf or fractional. Ints are skipped because
    # math.isfinite raises OverflowError on ints too big to convert to a float.
    if not isinstance(step, numbers.Integral):
        if not math.isfinite(step) or step != int(step):
            return False
    # bool() because comparing NumPy numbers returns np.bool_, not a real bool.
    return bool(MIN_TIME_STEP <= step <= MAX_TIME_STEP)
