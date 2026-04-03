# Plan

**Last Updated**: 2026-03-11

## Implementation Plan

### Phase 1: Fail-Fast Config Loading (T1)
Change `_load_teaching_comments()` to:
- Raise `ConfigFileNotFoundError` when config file doesn't exist
- Raise `ConfigurationError` on JSON decode or OS errors
- Log error before raising
- Remove `_teaching_comments_cache = {}` fallback paths

### Phase 2: Remove Dead Code Fallbacks (T2)
- `_try_tag_hint()`: Remove lines 495-498 (fallback to TECHNIQUE_HINTS tuple[0])
- `_try_solution_aware_hint()`: Remove lines 517-519 (fallback to tuple[0])
- `generate_reasoning_hint()`: Simplify secondary tag handling (L582-583) — use config directly, no tuple[0] fallback

### Phase 3: Update Legacy generate_yh2() (T3)
- Update `generate_yh2()` to use config-driven hint text for YH1 portion
- Keep backward compatibility: still returns `"hint. reasoning"` format

### Phase 4: Tests (T4)
- Add test: missing config raises `ConfigFileNotFoundError`
- Add test: corrupt config raises `ConfigurationError`
- Verify all existing 226+ tests pass

## Documentation Plan

| Item | Action | Why |
|------|--------|-----|
| `hints.py` docstring | Update `_load_teaching_comments()` docstring | Reflects new fail-fast behavior |
| `_try_tag_hint()` docstring | Remove "Falls back to hardcoded" | No longer true |

No external docs affected (internal code change only).

## Validation Plan

1. Run `pytest -m unit` for fast feedback
2. Run full enrichment test suite
3. Verify no regressions in 226+ tests
