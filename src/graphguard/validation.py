import math

MIN_TIME_STEP = 1
MAX_TIME_STEP = 49


def is_valid_time_step(step) -> bool:
    """Return True if `step` is a whole number from 1 to 49.

    Ints and whole-number floats (7.0) are accepted, since pandas can turn
    an integer column into floats when it has gaps. Bools, strings, NaN and
    infinity are rejected.
    """
    # bool is a subclass of int, so this check has to come before the int one.
    if isinstance(step, bool):
        return False
    if not isinstance(step, (int, float)):
        return False
    # NaN and inf are floats, so they pass the type check above.
    if isinstance(step, float) and not math.isfinite(step):
        return False
    if step != int(step):
        return False
    return MIN_TIME_STEP <= step <= MAX_TIME_STEP
