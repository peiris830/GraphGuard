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
- **Update (2026-10-28):** Checked against the real files. Time steps are plain
  integers 1 to 49 with no gaps, so the rule fits the data as it stands. The float
  case is kept as protection, not because the current files need it.

### 2026-10-28: Use pandas for the Phase 1 CSV loading
- **Decision:** The Phase 1 loader reads the Elliptic CSVs with pandas.
- **Why:** The features file has 203,769 rows and 167 columns (about 690 MB as CSV, 272 MB
  in memory), so it fits comfortably in RAM on one machine. pandas reads and types
  it in one call (0.7 s here) and the result feeds straight into validation and
  Parquet output. Phase 1 is about getting the data trustworthy, not about scale.
- **Alternatives considered:** The standard `csv` module (no dependency, but I would
  hand-write the typing and column handling pandas gives me). Spark right away
  (the right tool once joins and degree counts get heavy, but a cluster framework
  for a file that fits in memory would hide what Phase 1 is meant to teach). DuckDB
  for reading (a good fit later for querying the Parquet output).
- **Trade-off:** pandas loads the whole file at once. That is fine at this size, and
  it is the reason Phase 2 moves the heavy transforms to Spark.

### 2026-10-28: Supply column names and check the column count when reading features
- **Decision:** `read_features` passes `header=None` with an explicit list of 167
  names (`tx_id`, `time_step`, `feat_1` to `feat_165`), and it checks the first
  row's column count before reading the whole file.
- **Why:** `elliptic_txs_features.csv` has no header row, so a plain `pd.read_csv`
  would treat the first transaction as the header and silently lose it. pandas also
  pads short rows with NaN and shifts long ones instead of raising, so a wrongly
  shaped file would load without any error and corrupt every value after it. Checking
  the count up front turns a silent failure into a clear `ValueError`.
- **Alternatives considered:** Trusting the file shape (shorter, but the failure
  would be silent and found late). Validating the count after loading (it works, but
  by then pandas has already read the whole file).
- **Trade-off:** The first-row check only samples one row, so it catches a wrong
  schema but not a single malformed row deep in the file. Row-level problems are the
  job of the validation and quarantine stage.
