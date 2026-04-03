# Analysis

**Last Updated**: 2026-03-11

## Current Behavior

`_load_teaching_comments()` (hints.py L62-88):
- If config file missing: silently sets `_teaching_comments_cache = {}` and returns
- If JSON decode / OS error: logs warning, sets `_teaching_comments_cache = {}` and returns
- Result: pipeline continues with degraded hints (no config-driven YH1)

## TECHNIQUE_HINTS Access Points (20 matches)

| Location | Access | Status | Action |
|----------|--------|--------|--------|
| L176 (dict definition) | Both elements | Active | Keep (reasoning used by YH2) |
| L340 `_get_primary_tag()` | Existence check only | Active | Keep unchanged |
| L400 `_get_secondary_tag()` | Existence check only | Active | Keep unchanged |
| L495-498 `_try_tag_hint()` | tuple[0] fallback | **Dead code** | Remove |
| L517-519 `_try_solution_aware_hint()` | tuple[0] fallback | **Dead code** | Remove |
| L557 `generate_reasoning_hint()` | tuple[1] (reasoning) | Active | Keep |
| L582-583 `generate_reasoning_hint()` secondary | tuple[0] then config override | **Dead code** | Simplify |
| L676, 681 `generate_yh2()` | Both elements | Legacy | Update to use config |

## Exception Infrastructure

Available in `exceptions.py`:
- `ConfigFileNotFoundError(message, context={"path": str(path)})` — for missing config file
- `ConfigurationError(message, context={"path": str(path)})` — for corrupt config file

Reference pattern: `ConfigLoader._load_json()` in `config/loader.py` uses these with fail-fast semantics.

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Tests that rely on silent fallback | Low | Investigation found no such tests |
| `generate_yh2()` callers break | Low | Method still works, just reads config for YH1 text |
| Config path resolution fails in test environment | Medium | Tests use mocked HintGenerator, not config loading |
