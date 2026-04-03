# Charter: Fail-Fast Config Loading + Dead Code Removal

**Initiative ID**: 20260311-fix-config-fail-fast-dead-code
**Type**: Fix (Level 2 — Medium Single)
**Last Updated**: 2026-03-11

## Problem Statement

`_load_teaching_comments()` in `hints.py` silently returns `{}` when `config/teaching-comments.json` is missing or corrupt. This creates a hidden failure mode where the pipeline runs with degraded hint quality instead of failing loudly.

The silent `{}` fallback was the original justification for keeping TECHNIQUE_HINTS tuple[0] (hardcoded YH1 technique text) as dead code. With fail-fast config loading, this dead code has no purpose and should be removed.

## Goals

1. **Fail-fast on config load failure** — raise `ConfigFileNotFoundError`/`ConfigurationError` instead of returning `{}`
2. **Remove dead code** — eliminate unreachable TECHNIQUE_HINTS tuple[0] fallback paths in `_try_tag_hint()`, `_try_solution_aware_hint()`, and `generate_reasoning_hint()` secondary tag
3. **Update legacy `generate_yh2()`** — uses both tuple elements; must be updated for new structure
4. **Add test coverage** — test that config-missing raises exception

## Non-Goals

- Refactoring TECHNIQUE_HINTS from `tuple[str, str]` to `str` — invasive change, defer
- Fixing `_load_quality_config()` / `_load_content_type_config()` (same anti-pattern in other files)
- Removing `generate_yh2()` entirely (it's deprecated but may have callers)

## Scope

| File | Changes |
|------|---------|
| `hints.py` | Fail-fast `_load_teaching_comments()`, remove dead fallback code paths, update `generate_yh2()` |
| `test_enrichment.py` | Add config-missing test, verify existing tests pass |

## Constraints

- Must follow existing `ConfigFileNotFoundError` / `ConfigurationError` exception pattern from `ConfigLoader._load_json()`
- TECHNIQUE_HINTS reasoning templates (tuple[1]) remain active for YH2
- All 226+ enrichment tests must pass
