# Decisions

One short entry per real decision: what was chosen and why.

## Template

### YYYY-MM-DD: Title
- **Decision:**
- **Why:**
- **Alternatives considered:**

---

### 2026-10-27: Use a src layout for the package
- **Decision:** Code lives in `src/graphguard/`, not in a top-level `graphguard/` folder.
- **Why:** With a top-level package, `pytest` can import the code straight from the
  working directory even if the package was never installed, so tests can pass on my
  machine and fail on a clean checkout. The src layout forces an install
  (`pip install -e ".[dev]"`), so tests exercise the package the way a user would.
  This backs the rule that every phase must run from a clean checkout.
- **Alternatives considered:** A flat layout (simpler, no install step, but hides
  packaging mistakes) and a single script (fine for a one-off, but it won't hold a
  multi-phase pipeline).

### 2026-10-28: What counts as a valid time step
- **Decision:** `is_valid_time_step` accepts ints and whole-number floats from 1 to 49
  (`1`, `7`, `49`, `7.0`). It rejects bools (`True`, `False`), strings (`"7"`),
  `None` and other types, `nan`/`inf`, fractional floats (`7.5`), and anything out of
  range (`0`, `50`, `-3`).
- **Why:**
  - Bools: `True == 1` in Python because `bool` subclasses `int`, but `True` means
    "yes", not "week 1". A bool reaching this check points to a bug upstream, and a
    validator should catch that instead of passing it as step 1.
  - Whole-number floats: pandas turns an integer column into floats when it has
    missing values, so rejecting `7.0` would break loading for no good reason.
  - Strings: converting CSV text to numbers is the loader's job. Keeping the
    validator narrow means it has one rule and one place to look when it fails.
  - `nan`/`inf`: they are floats, so they pass the type check, and `int(nan)` would
    raise instead of returning a clean "invalid".
- **Alternatives considered:** A lenient version (accept `True` and numeric strings)
  would load more input without complaint, at the cost of hiding upstream mistakes.
  Strictly ints only would be simpler but would trip over pandas float promotion.
- **Trade-off:** Strictness may reject real data in Phase 1. If the Elliptic files
  turn out to store time steps in an unexpected form, I will either convert the values
  in the loader or loosen this rule on purpose and record the change here.
