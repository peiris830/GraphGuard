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

### 2026-10-29: Turn the `unknown` class into a null and keep the raw value
- **Decision:** `read_classes` returns three columns: `tx_id`, `class_raw` (the original
  text: `1`, `2` or `unknown`) and `label` (a nullable `Int64`, where `unknown` becomes
  a real null). Any other class value stops the load with a `ValueError`.
- **Why:** 157,205 of 203,769 transactions (77%) are `unknown`, meaning "not labelled",
  which is exactly what a null means. As text, the column would mix numbers and a word,
  so every query would have to remember that `"unknown"` is not a label, and numeric
  filters would quietly misbehave. A null is handled correctly by DuckDB, pandas and
  Spark. The raw column stays so nothing is lost and any null can be traced to its source.
  `Int64` (not `int64`) is needed because a plain integer column cannot hold nulls, and
  pandas would silently turn 1 and 2 into 1.0 and 2.0.
- **Alternatives considered:** Keeping the string `unknown` (faithful to the file, but
  the column stays mixed-type). Splitting into a labelled and an unlabelled table
  (convenient for modelling, but it duplicates structure and loses the full picture in
  one place). Dropping unknown rows (they are 77% of the data, and the graph needs them
  as neighbours of labelled nodes).
- **Trade-off:** The strict `ValueError` stops the whole load on one bad value, which
  fits the real file (it passes cleanly). Collecting bad rows and continuing is the job
  of the later validation and quarantine stage, so this reader stays simple.

### 2026-10-29: Check cross-file integrity in a separate module that returns the bad rows
- **Decision:** Four table-level checks live in `integrity.py`, apart from the readers:
  orphan edges, edges that cross time steps, class ids that do not match feature ids,
  and duplicate `tx_id`s. Each returns the offending rows (empty means it passed), and
  each problem is reported by exactly one check.
- **Why:** A reader looks at one file, but these questions need two. An edge pointing at
  a transaction that is not in the features file would be dropped silently by a join and
  leave every degree count too low. An edge crossing time steps would break the plan to
  process one step at a time. Returning rows, not a yes or no, lets the later quarantine
  stage isolate and report exactly what failed. Orphan edges are skipped by the
  cross-step check, since their step is unknown, so one bad edge is not counted twice
  when the pipeline fails on a reject threshold.
- **What the real data showed:** All four checks pass. There are 234,355 edges, none
  orphaned, none duplicated, no self-loops, and none crossing time steps, so every time
  step is a self-contained graph (1,168 to 9,164 edges each). Phase 2 relies on that.
  The classes file has exactly the same transaction ids as the features file.
- **Alternatives considered:** Putting the checks inside each reader (simpler call sites,
  but a reader would need to load other files, which makes it hard to test with small
  fixtures). Returning a boolean (less code, but the caller would have to re-find the
  bad rows to quarantine them).
- **Trade-off:** The checks compare whole tables in memory, which is fine at 200k rows
  (0.1 s here) and is another reason Phase 2 moves heavy joins to Spark. They only prove
  the current files are clean, so they must be re-run on any new data version.

### 2026-10-29: Quarantine bad rows and stop the run only above a reject threshold
- **Decision:** `split_valid_rows` splits the features table into clean rows and rejected
  rows (each with a `reason`). If the rejected share is above 1% of all rows, it raises a
  `ValueError` and the run stops. The limit is a parameter, and exactly 1% is allowed.
- **Why:** The readers catch a wrongly shaped file, but one bad row inside a good file
  needs a different answer. Stopping on the first bad row would throw away 200k good
  rows over one, and dropping it silently would hide that the data is dirty. Isolating
  the row with its reason keeps the good data moving and leaves a record to inspect. The
  limit exists because a large share of bad rows usually means something upstream broke,
  such as a shifted column or the wrong file, and loading the rest would hide that.
- **Why 1%:** It is a starting value, not a measured one. The real files have zero
  rejected rows, so there is nothing to tune it against. It is a parameter so tests can
  exercise both sides, and so Airflow can set it per run in Phase 4.
- **Alternatives considered:** Fail on the first bad row (strictest, but one bad row
  blocks everything). Drop silently (never stops, but nobody finds out the data was
  dirty). Quarantine with no limit (never blocks, but would happily load a file where
  half the rows are wrong).
- **Trade-off:** One reason is recorded per rejected row. That is enough while time step
  is the only rule, and a list of reasons can come when more row-level rules exist. The
  function returns the rejected rows and does not write them anywhere; writing the
  quarantine file belongs to the Parquet writer.
- **Gotcha found while building it:** `is_valid_time_step` rejects NumPy integers
  (`np.int64` is not a Python `int`). `Series.map` passes plain ints, so the quarantine
  step is safe, but looping over the NumPy array would reject every row. A test guards
  this, and hardening the validator is tracked as a separate change.
