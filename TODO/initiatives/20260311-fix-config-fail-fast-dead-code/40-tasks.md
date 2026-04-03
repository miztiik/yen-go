# Tasks

**Last Updated**: 2026-03-11

## Task Graph

| ID | Task | File | Depends | Parallel |
|----|------|------|---------|----------|
| T1 | Fail-fast `_load_teaching_comments()` | hints.py | — | — |
| T2 | Remove dead code fallback paths | hints.py | T1 | — |
| T3 | Update legacy `generate_yh2()` | hints.py | T1 | [P] with T2 |
| T4 | Add/update tests | test_enrichment.py | T1, T2, T3 | — |
| T5 | Documentation: update docstrings | hints.py | T2 | [P] with T4 |
| T6 | Validation: run test suite | — | T4 | — |

## Task Details

### T1: Fail-fast _load_teaching_comments()
- Replace `if config_path.exists()` → raise `ConfigFileNotFoundError` when missing
- Replace `except ... logger.warning()` → `logger.error()` + raise `ConfigurationError`
- Remove `_teaching_comments_cache = {}` fallback
- Update docstring

### T2: Remove dead code fallback paths
- `_try_tag_hint()`: Remove lines 495-498 (hardcoded TECHNIQUE_HINTS fallback)
- `_try_solution_aware_hint()`: Remove lines 517-519 (hardcoded fallback)
- `generate_reasoning_hint()`: Simplify secondary tag L582-583 to use config directly

### T3: Update legacy generate_yh2()
- Read hint text from config instead of TECHNIQUE_HINTS tuple[0]
- Keep reasoning from TECHNIQUE_HINTS tuple[1]
- Maintain `"hint. reasoning"` return format
- **L672-677 loop body change**:
  - Before: `base_hint, reasoning = self.TECHNIQUE_HINTS[tag_lower]` → uses tuple[0] for base_hint
  - After: Look up config `_load_teaching_comments()` for hint text; fall back to tuple[0] only if config has no entry for that tag
  - Same change for L681: `base_hint, reasoning = self.TECHNIQUE_HINTS[primary_tag]`

### T4: Add/update tests
- Test config-missing → ConfigFileNotFoundError
- Test corrupt config → ConfigurationError
- Test `generate_yh2()` returns config-driven hint text (not TECHNIQUE_HINTS tuple[0]) with reasoning suffix
- Verify existing test_technique_hints_dictionary still valid
- Run full suite: 226+ tests pass

### T5: Update docstrings
- `_load_teaching_comments()`: "Returns empty dict on failure" → "Raises on failure"
- `_try_tag_hint()`: Remove "Falls back to hardcoded TECHNIQUE_HINTS"

### T6: Validation
- `pytest backend/puzzle_manager/tests/unit/test_enrichment.py`
- `pytest -m "not (cli or slow)"`
