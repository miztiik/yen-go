# Research: Enrichment Lab Logging Scope Regression

**Initiative:** `2026-03-06-fix-enrichment-lab-logging-scope`  
**Last Updated:** 2026-03-06  
**Researcher mode:** Feature-Researcher

---

## 1. Research Question and Boundaries

**Question:** After scoping the log `FileHandler` from the `root` logger to the namespace-scoped `_lab_logger` (`puzzle_enrichment_lab`) in `log_config.py` (Plan 010 / D45), which tests break, why do they break, and what is the lowest-risk structural fix?

**Boundaries:**

- In scope: `tools/puzzle-enrichment-lab/log_config.py`, `tests/test_log_config.py`, `tests/test_sprint5_fixes.py`, `conftest.py` (top-level), `tests/conftest.py`
- Out of scope: KataGo engine integration tests, `backend/puzzle_manager`, frontend

---

## 2. Internal Code Evidence

### 2.1 The Scoping Change (log_config.py)

**File:** [tools/puzzle-enrichment-lab/log_config.py](../../../tools/puzzle-enrichment-lab/log_config.py)

Before the scoping change, the FileHandler was attached to the **root** logger so all log records (any namespace) appeared in the lab's log file. The scoping change (Plan 010, D45) moved it to the **lab-namespace** logger to prevent external library noise:

```python
# CURRENT — file handler attached to _lab_logger (scoped):
_lab_logger = logging.getLogger("puzzle_enrichment_lab")
_lab_logger.addHandler(file_handler)   # ← only puzzle_enrichment_lab.* hits the file

# BEFORE — file handler was attached to root:
root.addHandler(file_handler)          # ← everything hit the file
```

The `stderr_handler` remains on `root`. Because `_lab_logger.propagate = True` (default), lab-namespace log records DO propagate upward to root, reaching both the file handler (via `_lab_logger`) and the stderr handler (via root). This design is correct for runtime.

### 2.2 Bug B-1: test_creates_file_handler checks wrong logger

**File:** [tools/puzzle-enrichment-lab/tests/test_log_config.py](../../../tools/puzzle-enrichment-lab/tests/test_log_config.py) — `TestSetupLogging.test_creates_file_handler`

```python
def test_creates_file_handler(self, tmp_path):
    setup_logging(log_dir=tmp_path)
    root = logging.getLogger()
    file_handlers = [
        h for h in root.handlers          # ← searches root; FileHandler is now on _lab_logger
        if isinstance(h, logging.FileHandler)
    ]
    assert len(file_handlers) >= 1         # ← FAILS: root has 0 FileHandlers after scoping change
```

**Result:** Test FAILS — `root.handlers` contains only the `StreamHandler`; the `FileHandler` is now on `logging.getLogger("puzzle_enrichment_lab")`.

### 2.3 Bug B-2/B-3: teardown_method leaves \_lab_logger file handles open

**File:** `test_log_config.py` — `TestSetupLogging.teardown_method` and `TestFileHandlerOutput.teardown_method`

```python
def teardown_method(self):
    root = logging.getLogger()
    for h in root.handlers[:]:
        root.removeHandler(h)
        h.close()
    # ← _lab_logger.handlers never cleaned up here
```

`_lab_logger.addHandler(file_handler)` in `setup_logging` is never reversed by `teardown_method`. Between tests, stale `FileHandler` objects accumulate on `_lab_logger` until the next `setup_logging()` call resets them. If a test raises before calling `setup_logging()` again, the handles leak.

### 2.4 Bug B-4/B-5: test_log_file_contains_json uses wrong logger namespace

**File:** `test_log_config.py` — `TestFileHandlerOutput.test_log_file_contains_json`

```python
def test_log_file_contains_json(self, tmp_path):
    run_id = "file-test-001"
    setup_logging(run_id=run_id, log_dir=tmp_path)
    test_logger = logging.getLogger("test.file_output")  # ← NOT in puzzle_enrichment_lab.*
    test_logger.info("file log entry")

    # Force flush — but searches root.handlers, which has NO FileHandler
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, logging.FileHandler):            # ← never matches; no flush
            h.flush()

    log_file = tmp_path / f"{run_id}-enrichment.log"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    test_lines = [l for l in lines if "file log entry" in l]
    assert len(test_lines) >= 1    # ← FAILS: "test.file_output" records never reach _lab_logger's file handler
```

**Result:** Two compounding failures: (a) `"test.file_output"` logs go to root → stderr only, never to the scoped file; (b) the flush loop scans `root.handlers` and finds no FileHandler, so flush never executes.

### 2.5 Bug B-6: test_sprint5_fixes uses wrong filename separator

**File:** [tools/puzzle-enrichment-lab/tests/test_sprint5_fixes.py](../../../tools/puzzle-enrichment-lab/tests/test_sprint5_fixes.py) — `TestPerRunLogFiles.test_log_with_run_id_creates_named_file`

```python
log_file = Path(tmp) / "test-abc_enrichment.log"   # ← expects UNDERSCORE before "enrichment"
assert log_file.exists()
```

But `log_config.py` generates the filename with a DASH:

```python
log_file = resolved_log_dir / f"{run_id}-enrichment.log"  # dash per plan
# → "test-abc-enrichment.log"  (not "test-abc_enrichment.log")
```

**Result:** Test FAILS — `test-abc_enrichment.log` does not exist; actual file is `test-abc-enrichment.log`.

### 2.6 Bug B-7: test_sprint5_fixes cleanup causes Windows PermissionError

**File:** `test_sprint5_fixes.py` — `TestPerRunLogFiles` (both tests), cleanup block:

```python
root = logging.getLogger()
for h in root.handlers[:]:
    h.close()
    root.removeHandler(h)
# ← _lab_logger file handler not closed; file lock held on Windows
```

Because the `FileHandler` is now on `_lab_logger` (not root), this cleanup misses it. On Windows the open file handle prevents `tempfile.TemporaryDirectory()` from deleting the temp directory, raising `PermissionError` on cleanup.

### 2.7 Bug B-8 (pre-existing): StreamHandler captures old sys.stderr reference

**File:** `tools/puzzle-enrichment-lab/conftest.py` — `pytest_configure`

```python
def pytest_configure(config):
    from log_config import setup_logging
    setup_logging(run_id=run_id, verbose=verbose, console_format="human")
    # ↑ creates StreamHandler(sys.stderr) at pytest_configure time
    # pytest then replaces sys.stderr per-test for capsys/capfd capture
    # handler still holds old reference → log lines escape per-test capture
```

This is a **pre-existing** issue unrelated to the scoping change. It means pytest's `capsys`/`capfd` fixtures cannot capture lab log output. However, `caplog` fixtures work correctly because `caplog` injects a handler directly on the root logger per-test (lab loggers propagate their records to root).

---

## 3. External References

| R-ID | Source                                                                                                               | Relevance                                                                                                                                                                                    |
| ---- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1  | [Python logging HOWTO — Logger hierarchy and propagation](https://docs.python.org/3/howto/logging.html#logging-flow) | Confirms `propagate=True` means records flow from child to root; root handlers still see all lab records via propagation; placing FileHandler on root is valid                               |
| R-2  | [Python logging.handlers.FileHandler](https://docs.python.org/3/library/logging.handlers.html#logging.FileHandler)   | File is opened at handler construction, not at first write; file exists even before any records are written                                                                                  |
| R-3  | [pytest docs — `caplog` fixture](https://docs.pytest.org/en/stable/how-to/logging.html#caplog-fixture)               | caplog installs a `LogCaptureHandler` on the root logger per-test; if propagate=True on child loggers, caplog sees all downstream records — so B-8 does NOT affect caplog, only capsys/capfd |
| R-4  | [pytest docs — log_level and live logging](https://docs.pytest.org/en/stable/how-to/logging.html#live-logs)          | `setup_logging()` in `pytest_configure` wipes root handlers installed by pytest's own logging plugin (--log-cli handlers); this breaks `--log-cli` live output                               |
| R-5  | [Python logging Filter](https://docs.python.org/3/library/logging.html#logging.Filter)                               | A `Filter` attached to a handler can gate records by logger name prefix — allows FileHandler to remain on root while only writing lab-namespace records                                      |

---

## 4. Candidate Adaptations for Yen-Go

### Option A — Namespace-filter the FileHandler; restore it to root

Move `file_handler` back to `root`. Add a `_LabNamespaceFilter` that passes only records whose `name` starts with `puzzle_enrichment_lab`:

```python
class _LabNamespaceFilter(logging.Filter):
    """Pass only records from the puzzle_enrichment_lab.* hierarchy."""
    def filter(self, record: logging.LogRecord) -> bool:
        return record.name.startswith(LOGGER_NAMESPACE)

file_handler.addFilter(_LabNamespaceFilter())
root.addHandler(file_handler)         # back on root
# No handler on _lab_logger; no change to propagate
```

**Impact on tests:**

- `test_creates_file_handler` → passes (FileHandler found on root ✓)
- `test_no_duplicate_handlers_on_repeated_calls` → passes (counts root handlers ✓)
- `test_log_file_contains_json` → still FAILS (uses `test.file_output` namespace → filtered out by `_LabNamespaceFilter`)
- `teardown_method` fully cleans up root handlers → no leaks ✓
- `test_sprint5_fixes.py` cleanup → fully cleans up root handlers → no Windows PermissionError ✓

Still requires fixing `test_log_file_contains_json` and `test_sprint5_fixes.py` separately.

### Option B — Fix tests to match current \_lab_logger placement

Leave `log_config.py` unchanged. Update all affected tests:

1. `test_creates_file_handler`: check `logging.getLogger("puzzle_enrichment_lab").handlers` for FileHandler
2. `test_log_file_contains_json`: use `logging.getLogger(f"{LOGGER_NAMESPACE}.test_output")` as logger + fix flush loop to iterate `_lab_logger.handlers`
3. Both `teardown_method`s: also close and remove `_lab_logger` handlers
4. `test_sprint5_fixes`: fix filename separator + fix cleanup to close `_lab_logger` handlers

**Impact:** No `log_config.py` changes; tests become coupled to handler placement (internal implementation detail).

### Option C — Option A + fix remaining test bugs (recommended)

Combines Option A with targeted test fixes:

1. Add `_LabNamespaceFilter` class to `log_config.py`, attach to `file_handler`, restore handler to root
2. Fix `test_log_file_contains_json` logger namespace → `puzzle_enrichment_lab.test_output`
3. Fix `test_log_file_contains_json` flush loop → search root.handlers (works after Option A)
4. Fix `test_sprint5_fixes.py` filename → `test-abc-enrichment.log`
5. Fix `test_sprint5_fixes.py` cleanup → no change needed (handler on root, cleanup already iterates root.handlers)

**Result:** All 5 bugs fully fixed; `log_config.py` gets a net +7 lines (the filter class); tests get targeted corrections.

### Option D — Expose `get_lab_logger()` public API, fix tests

Keep file handler on `_lab_logger`. Export `get_lab_logger()` from `log_config.py`. Tests import and inspect the lab logger directly. Teardown also cleans `_lab_logger` handlers.

**Drawback:** Tests become coupled to the two-logger architecture. If placement changes again, tests break. Does not reduce risk of future regressions.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-ID | Risk/Note                                                                                                                                                                                                                                                                                                                     | Affects         |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| R-1  | **Option B fragility**: tests asserting on `_lab_logger.handlers` would break again if handler placement changes                                                                                                                                                                                                              | Long-term       |
| R-2  | **\_LabNamespaceFilter side-effect**: `root.info(...)` call in `setup_logging()` itself (the "Logging initialised" message) will NOT appear in the log file after Option A/C, since `root` is not in `puzzle_enrichment_lab` namespace — currently it also does not appear in the file (same behavior in current scoped code) | No regression   |
| R-3  | **B-8 (pre-existing) low-risk for agents**: Agents use `caplog` or file-based inspection, not `capsys`/`capfd` — so the stderr capture bypass rarely matters in practice                                                                                                                                                      | Low             |
| R-4  | **test_sprint5_fixes.py Windows PermissionError** (B-7): On CI running Linux this is masked; will manifest on developer Windows machines or any CI with Windows runners                                                                                                                                                       | High on Windows |
| R-5  | No license concerns; all changes are internal to the lab's test infrastructure                                                                                                                                                                                                                                                | N/A             |

---

## 6. Planner Recommendations

1. **Adopt Option C (A + targeted test fixes).** Add `_LabNamespaceFilter` to `log_config.py` (restores file handler to root with scoping preserved via filter) and fix the three test-side bugs: `test_log_file_contains_json` (namespace + flush), `test_sprint5_fixes.py` (filename separator + no Windows file-lock issue if on root). Correction Level: **1 (Minor)** — 2 files, ~20 lines net change, bug fix only.

2. **Fix B-7 (Windows PermissionError) as the highest priority item.** Even before a structural refactor, the `test_sprint5_fixes.py` cleanup bug causes hard failures on Windows because an unclosed file handle prevents `tempfile.TemporaryDirectory` from deleting the temp directory.

3. **Do NOT pursue Option B.** Tests coupled to internal logger hierarchy placement are fragile. Any future refactor of `log_config.py` would silently break them again.

4. **Defer B-8 (pytest capsys bypass).** The pre-existing `sys.stderr` capture bypass has no reported impact on agents (who use `caplog` or read log files). If needed later, the fix is to call `setup_logging()` from a session-scoped pytest fixture instead of `pytest_configure`, so the handler is created after pytest installs its per-test capture.

---

## 7. Confidence and Risk Update for Planner

| Metric                           | Value                                                           |
| -------------------------------- | --------------------------------------------------------------- |
| `post_research_confidence_score` | 92                                                              |
| `post_research_risk_level`       | low                                                             |
| `research_completed`             | true                                                            |
| `initiative_path`                | `TODO/initiatives/2026-03-06-fix-enrichment-lab-logging-scope/` |
| `artifact`                       | `15-research.md`                                                |

**Top recommendations (ordered):**

1. Option C: `_LabNamespaceFilter` on root FileHandler + fix test namespace + fix filename separator
2. Fix B-7 (Windows handler leak in test_sprint5_fixes) as immediate unblock
3. Defer B-8 (pytest capsys bypass — pre-existing, no current agent impact)

**Open questions for planner:**

| q_id | question                                                                                                      | options                                                         | recommended | status     |
| ---- | ------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ----------- | ---------- |
| Q1   | Should `_LabNamespaceFilter` also allow `root` logger records in the file (e.g., "Logging initialised" line)? | A: lab namespace only, B: lab namespace + root, C: all records  | A           | ❌ pending |
| Q2   | Should B-8 (pytest capsys bypass) be addressed in this initiative or a follow-up?                             | A: this initiative, B: follow-up, C: accept as known limitation | C           | ❌ pending |
