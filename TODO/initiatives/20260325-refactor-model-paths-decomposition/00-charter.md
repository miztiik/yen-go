# Charter: model_paths.py Decomposition

**Initiative**: 20260325-refactor-model-paths-decomposition
**Type**: refactor
**Date**: 2026-03-24

---

## Goals

1. **Break the circular dependency** between `model_paths.py` and `config/__init__.py`
2. **Enforce SRP**: Each concern (path constants, model resolution, test defaults) in its single canonical location
3. **Align with existing patterns**: `model_path()` should follow the `resolve_path()` and `get_effective_max_visits()` patterns already in `config/helpers.py`
4. **Update all 20+ import sites** to use direct imports from `config.helpers` and `tests/conftest.py` (full decomposition, no permanent facade)

## Non-Goals

- Restructuring `config/` package internals (already well-decomposed)
- Changing production runtime code (`cli.py`, `bridge.py`, `engine/`, `analyzers/`) — they don't import model_paths
- Adding new features or capabilities
- Changing test behavior or coverage

## Constraints

- `tools/puzzle-enrichment-lab/` is self-contained — no `backend/` imports
- 20+ importers must continue working throughout transition
- `clear_cache()` in `config/__init__.py` must still invalidate model resolution cache
- `conftest.py` auto-discovery must not be broken

## Acceptance Criteria

| ac_id | criterion |
|---|---|
| AC-1 | No circular import between config/ and model resolution code |
| AC-2 | `model_path(label)` callable from `config.helpers` |
| AC-3 | Path constants (KATAGO_PATH, TSUMEGO_CFG, etc.) defined in one canonical location |
| AC-4 | TEST_* defaults live in test infrastructure (conftest.py or tests/test_defaults.py) |
| AC-5 | `model_paths.py` deleted after verification |
| AC-6 | `clear_cache()` invalidates model resolution cache without cross-package imports |
| AC-7 | All existing tests pass |
| AC-8 | AGENTS.md updated to reflect new structure |

## Scope Boundary

- **In scope**: `model_paths.py`, `config/__init__.py`, `config/helpers.py`, `tests/conftest.py`, AGENTS.md
- **In scope (mechanical)**: All 20+ test/script importers — updated to use direct imports from `config.helpers`
