# Analysis — config.py SRP Decomposition

> Initiative: `20260314-2200-refactor-config-py-decomposition`
> Last Updated: 2026-03-14

## Planning Confidence

| Metric | Value |
|--------|-------|
| planning_confidence_score | 82 |
| risk_level | medium |
| research_invoked | yes |

## Cross-Artifact Consistency

| check_id | Check | Status | Evidence |
|-----------|-------|--------|----------|
| CC-1 | Charter goals traced to plan | ✅ | Goal 1 (SRP) → OPT-3 domain split. Goal 2 (ISP) → per-domain imports. Goal 3 (DRY) → single __init__ loader. Goal 4 (maintainability) → AC-6 ≤250 lines. Goal 5 (clean imports) → T12-T36 rewrite. |
| CC-2 | All 8 ACs covered by tasks | ✅ | AC-1→T37, AC-2→T1-T9, AC-3→T10, AC-4→T12-T36, AC-5→T38, AC-6→T40, AC-7→T41, AC-8→dependency table |
| CC-3 | 71 models assigned to modules | ✅ | Symbol mapping table in 40-tasks.md covers all 71 |
| CC-4 | 10 functions assigned | ✅ | Loaders in __init__, business logic in helpers, teaching loader in teaching |
| CC-5 | Backward compat = false reflected | ✅ | No facade in plan. All imports rewritten (Phase 2-5). |
| CC-6 | Legacy removal = true reflected | ✅ | T37 deletes config.py. |
| CC-7 | Option OPT-3 matches plan | ✅ | 10 files, difficulty+validation combined, ai_solve/solution_tree split, analysis/infrastructure split |

## Coverage Map

| Scope Item | Covered By |
|------------|------------|
| Create config/ package | T1-T10 |
| Analyzer import rewrites | T12-T27 |
| Detector import rewrites | T28 |
| Top-level import rewrites | T29-T34 |
| Test import rewrites | T35-T36 |
| Monolith deletion | T37 |
| Test verification | T38 |
| Grep verification | T39 |
| Line count verification | T40 |
| AGENTS.md update | T41 |
| README update | T42 |

## Unmapped Tasks

None identified. All charter scope items have task coverage.

## Severity-Based Findings

| finding_id | Severity | Finding | Mitigation |
|------------|----------|---------|------------|
| F-1 | Low | `__init__.py` at ~246 lines is at AC-6 boundary. EnrichmentConfig (91 lines) is hard to reduce further. | Accept as structural necessity. EnrichmentConfig is the composition root — its size is proportional to the number of composed sub-configs. |
| F-2 | Low | `analysis.py` at ~246 lines is also at boundary. Could grow if new engine config is added. | Future additions should consider whether new models belong in analysis or a new sub-module. |
| F-3 | Medium | Phase 2-5 involves ~120 import site rewrites. One missed site causes `ImportError`. | T39 grep verification catches any missed sites after T37 (deletion). T38 full test suite is the primary safety net. |
| F-4 | Low | `config/` directory name shadows a common Python package name. | No conflict — Python resolves package imports via sys.path. The lab tool uses sys.path-relative imports. Already validated by existing `from config import` pattern. |
| F-5 | Info | `conftest.py` may need `clear_cache()` import update. | Covered by T36. |

## Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| R-1 | lateral | `analyzers/detectors/` (26 files) | Low — all import only `EnrichmentConfig` | Same import path: `from config import EnrichmentConfig` | T28 | ✅ addressed |
| R-2 | lateral | `analyzers/` (16 files) | Medium — varied imports per file | Symbol mapping table drives mechanical rewrite | T12-T27 | ✅ addressed |
| R-3 | lateral | `tests/` (~30 files) | Medium — many import `clear_cache` + model classes | Same mechanical rewrite; `clear_cache` stays at `from config import clear_cache` | T35-T36 | ✅ addressed |
| R-4 | upstream | `config/katago-enrichment.json` | None — JSON structure unchanged | N/A | — | ✅ addressed |
| R-5 | upstream | `config/teaching-comments.json` | None — JSON structure unchanged | N/A | — | ✅ addressed |
| R-6 | downstream | `AGENTS.md` | Low — must update file inventory | Updated in same commit | T41 | ✅ addressed |
| R-7 | lateral | `engine/local_subprocess.py` | Low — imports `load_enrichment_config`, `resolve_path` | Same path: `from config import ...` | T33 | ✅ addressed |
| R-8 | lateral | `scripts/run_calibration.py` | Low — imports `EnrichmentConfig`, `load_enrichment_config`, `clear_cache`, `resolve_path` | Mix of __init__ and infrastructure imports | T34 | ✅ addressed |
| R-9 | downstream | `backend/puzzle_manager/` | None — separate config system | N/A | — | ✅ addressed |
| R-10 | downstream | `frontend/` | None — no dependency | N/A | — | ✅ addressed |
