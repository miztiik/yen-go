# Charter — config.py SRP Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Summary

Decompose `tools/puzzle-enrichment-lab/config.py` (1,003 lines, 71 Pydantic models, 10 functions) into a `config/` package with domain-organized sub-modules. Rewrite all 100+ consumer import sites. Delete the monolith.

## Goals

1. **SRP compliance** — Each config sub-module owns models for exactly one domain (difficulty, AI-solve, technique detection, teaching comments, etc.).
2. **ISP compliance** — Consumers import only the models they need, not the entire 1,003-line module.
3. **DRY compliance** — Eliminate the 4× copy-pasted load+cache pattern.
4. **Maintainability** — Each sub-module is 80-200 lines, readable in one screen, independently testable.
5. **Clean imports** — All consumer files use explicit sub-module imports (`from config.ai_solve import AiSolveConfig`).

## Non-Goals

1. **Caching redesign** — Global `_cached_*` pattern stays (Q3=C). Moved to respective sub-modules but not redesigned.
2. **Config JSON restructuring** — `config/katago-enrichment.json` keeps its current flat structure. Only the Python schema code is decomposed.
3. **`EnrichmentConfig` flattening** — The top-level god-object stays as the root Pydantic model. It composes sub-models, which is correct Pydantic practice.
4. **Moving config outside tools/** — No architectural boundary change. Config package stays at `tools/puzzle-enrichment-lab/config/`.
5. **Backend config unification** — `backend/puzzle_manager/` has its own separate `EnrichmentConfig`. No cross-system merge.

## Constraints

- **No runtime behavior change** — All config loading, caching, and validation must produce identical results.
- **Atomic delivery** — All import rewrites + model moves + test updates in one PR/commit.
- **AGENTS.md update** — Required in same commit per project rules.
- **Zero new dependencies** — Pure Python refactor, no new libraries.
- **config/katago-enrichment.json untouched** — The JSON file structure is not touched.

## Acceptance Criteria

| AC | Criterion |
|----|-----------|
| AC-1 | `config.py` file deleted. `config/` directory exists with `__init__.py` + sub-modules. |
| AC-2 | All 71 Pydantic models importable from their domain sub-module (e.g. `from config.ai_solve import AiSolveConfig`). |
| AC-3 | `load_enrichment_config()`, `clear_cache()`, `resolve_path()` importable from `config` (top-level package). |
| AC-4 | All 100+ consumer import sites updated. Zero `from config import` referencing the old monolith. |
| AC-5 | Full test suite passes: `python -m pytest tests/ --cache-clear -x` from puzzle-enrichment-lab/. |
| AC-6 | No sub-module exceeds 250 lines. |
| AC-7 | `AGENTS.md` updated in same commit. |
| AC-8 | No circular imports between sub-modules. |

## Scope Boundary

| In Scope | Out of Scope |
|----------|--------------|
| `tools/puzzle-enrichment-lab/config.py` → `config/` package | `backend/puzzle_manager/` config code |
| All `from config import` consumer sites in tools/puzzle-enrichment-lab/ | `config/katago-enrichment.json` structure |
| All test files that import from config | Caching mechanism redesign |
| AGENTS.md update | Frontend code |

## Correction Level

**Level 3 — Multiple Files**: 40+ files touched (1 deleted, 6-8 created, 30+ import rewrites, 30+ test files). SOLID/SRP refactor with no behavior change.
