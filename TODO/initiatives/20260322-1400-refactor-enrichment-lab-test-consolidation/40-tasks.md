# Tasks — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Task Breakdown

### Lane 2: Rename (1 task)

| Task ID | Title | Status | Depends On | Files |
|---------|-------|--------|-----------|-------|
| L2-T1 | Rename test_remediation_sprints.py → test_ai_solve_remediation.py | not_started | — | tests/test_remediation_sprints.py |

**Acceptance:** File renamed. `pytest --co -q` count unchanged. No broken imports.

---

### Lane 3: sys.path DRY Fix (3 tasks)

| Task ID | Title | Status | Depends On | Files |
|---------|-------|--------|-----------|-------|
| L3-T1 | Add pythonpath to pyproject.toml | not_started | L2-T1 | pyproject.toml |
| L3-T2 | Verify pythonpath with 4 representative files | not_started | L3-T1 | 4 test files (1 per pattern) |
| L3-T3 | Automated removal of sys.path boilerplate from all test files | not_started | L3-T2 | 61 test files |

**L3-T1 Detail:**
```toml
# In [tool.pytest.ini_options]
pythonpath = ["."]
```

**L3-T2 Detail:**
Test each of the 4 variable patterns by removing sys.path from one file and running its tests:
- `_LAB_DIR` pattern → pick test_sprint1_fixes.py
- `_LAB` pattern → pick one file using this
- `_lab_root` pattern → pick one file using this
- `_TOOLS_ROOT` pattern → pick one file using this

**L3-T3 Detail:**
Script approach — regex replace to remove the 3-4 line boilerplate block:
```python
import re, glob
for f in glob.glob("tests/test_*.py"):
    content = open(f).read()
    # Remove the sys.path block (all 4 variable patterns)
    content = re.sub(r'\n_(?:LAB_DIR|LAB|lab_root|TOOLS_ROOT)\s*=.*\nif str\(.*\) not in sys\.path:\n\s+sys\.path\.insert.*\n', '\n', content)
    # Remove orphaned imports if sys/pathlib no longer used
    # ... (careful: check if Path or sys used elsewhere in file)
    open(f, 'w').write(content)
```
After: verify with `pytest --co -q` and `grep -r "sys.path.insert" tests/ | grep -v conftest`.

**Acceptance:** Zero sys.path.insert in test files (except conftest.py). All tests pass.

---

### Lane 1: Sprint Migration (10 tasks)

| Task ID | Title | Status | Depends On | Files |
|---------|-------|--------|-----------|-------|
| L1-T1 | Record baseline test count | not_started | L3-T3 | — |
| L1-T2 | Migrate test_sprint1_fixes.py classes | not_started | L1-T1 | 7 files |
| L1-T3 | Delete test_sprint1_fixes.py + verify count | not_started | L1-T2 | 1 file |
| L1-T4 | Migrate test_sprint2_fixes.py classes | not_started | L1-T3 | 4 files |
| L1-T5 | Delete test_sprint2_fixes.py + verify count | not_started | L1-T4 | 1 file |
| L1-T6 | Migrate test_sprint3_fixes.py classes | not_started | L1-T5 | 4 files |
| L1-T7 | Delete test_sprint3_fixes.py + verify count | not_started | L1-T6 | 1 file |
| L1-T8 | Migrate test_sprint4_fixes.py + delete + verify | not_started | L1-T7 | 2 files |
| L1-T9 | Migrate test_sprint5_fixes.py + delete + verify | not_started | L1-T8 | 3 files |
| L1-T10 | Final verification: count + full test run | not_started | L1-T9 | — |

**Per-task workflow:**
1. Copy test class(es) to target file(s) — append at end
2. Preserve docstrings with gap IDs (P0.x, G.x, etc.)
3. Adjust imports if needed (sys.path already removed by L3)
4. Run target file tests: `pytest tests/<target_file>.py -q`
5. Delete source sprint file
6. Verify: `pytest --co -q` count unchanged

---

### Lane 4: Perf Helpers (2 tasks)

| Task ID | Title | Status | Depends On | Files |
|---------|-------|--------|-----------|-------|
| L4-T1 | Extract _get_referee_model and _parse_statuses to _perf_helpers.py | not_started | L1-T10 | 5 files |
| L4-T2 | Update perf test imports + verify | not_started | L4-T1 | 4 files |

---

## Summary

| Lane | Tasks | Estimated Test Files Touched | Risk |
|------|-------|------------------------------|------|
| L2 | 1 | 1 | Very Low |
| L3 | 3 | 62 | Medium (wide blast radius, scripted) |
| L1 | 10 | 18 | Medium (class relocation) |
| L4 | 2 | 5 | Low |
| **Total** | **16** | — | — |
