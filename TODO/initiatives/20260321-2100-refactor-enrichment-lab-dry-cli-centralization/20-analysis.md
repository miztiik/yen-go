# Analysis — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-21  
> Selected Option: OPT-3 (Hybrid Bootstrap + Targeted CLI Absorption)  
> Planning Confidence Score: **88**  
> Risk Level: **low**  
> Research Invoked: **yes** (trigger: initial score 65 < 70)

---

## 1. Planning Confidence Assessment

| Deduction | Applied | Points | Rationale |
|-----------|---------|--------|-----------|
| Architecture seams unclear | No | 0 | Single tool, clear module boundaries |
| 2+ approaches unknown tradeoffs | Yes (pre-research) | -20 | 3 options evaluated, tradeoffs now clear |
| External precedent needed | No | 0 | Standard Python patterns (PEP 492, lru_cache) |
| Quality/perf/security uncertain | Partially | -5 | lru_cache + clear_cache interaction identified |
| Test strategy unclear | No | 0 | Existing suite with agreed regression command |
| Rollout/rollback unclear | Partially | -7 | Phased plan with per-phase rollback |
| **Post-research adjustments** | | +20 | Research resolved 2+ approach uncertainty |
| **Total** | | **88** | |

---

## 2. Severity-Based Findings

| finding_id | severity | category | description | task_mapping | status |
|------------|----------|----------|-------------|-------------|--------|
| F1 | HIGH | DRY | `setup_logging()` called with different signatures in 5 locations | T1.1–T1.6 | ✅ addressed |
| F2 | HIGH | DRY | `_resolve_katago_config()` duplicated in cli.py + run_calibration.py | T3.1–T3.4 | ✅ addressed |
| F3 | MEDIUM | DRY | `load_enrichment_config()` called 20+ times with 4 patterns | T1.1 (bootstrap standardizes), T4.1 (lazy) | ✅ addressed |
| F4 | MEDIUM | DRY | KataGo engine lifecycle try/finally duplicated 3x | T2.1–T2.3 | ✅ addressed |
| F5 | MEDIUM | DRY | Regex SGF parsers copy-pasted in 2 test utilities | T5.1–T5.4 | ✅ addressed |
| F6 | MEDIUM | KISS | `_model_paths.py` executes config I/O at import time (non-lazy) | T4.1–T4.2 | ✅ addressed |
| F7 | LOW | DRY | Run ID generation: `generate_run_id()` vs `secrets.token_hex(8)` | T1.5 (bootstrap standardizes) | ✅ addressed |
| F8 | LOW | DRY | `--verbose`, `--log-dir` argparse flags duplicated | T6.1 (_add_common_args) | ✅ addressed |
| F9 | INFO | CONSTRAINT | MH-1: Calibrate must preserve engine restart cadence | T6.4 | ✅ addressed |
| F10 | INFO | CONSTRAINT | MH-2: clear_cache() must invalidate _model_paths lru_cache | T4.2 | ✅ addressed |
| F11 | INFO | CONSTRAINT | MH-3: Calibrate flags must align with enrich/batch naming | T6.6 | ✅ addressed |

---

## 3. Coverage Map

| Charter Goal | Finding(s) | Task(s) | Phase | Covered? |
|-------------|-----------|---------|-------|----------|
| G1: Centralize logging | F1, F7 | T1.1–T1.7 | Phase 1 | ✅ |
| G2: Centralize config | F3, F6 | T1.1, T4.1–T4.4 | Phase 1, 4 | ✅ |
| G3: Eliminate katago config dup | F2 | T3.1–T3.5 | Phase 3 | ✅ |
| G4: Engine lifecycle CM | F4 | T2.1–T2.4 | Phase 2 | ✅ |
| G5: Remove regex SGF parsers | F5 | T5.1–T5.5 | Phase 5 | ✅ |
| G6: CLI absorption (partial) | F8 | T6.1–T6.8 | Phase 6 | ✅ |
| G7: Zero regressions | — | T0.1, T1.7, T2.4, T3.5, T4.3, T5.5, T6.8, T7.2 | All | ✅ |

### Unmapped Tasks
None. All 44 tasks trace to charter goals.

### Unmapped Findings
None. All 11 findings trace to tasks.

---

## 4. Ripple Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|-----------|--------|
| RE-1 | downstream | `cli.py` callers (enrich, validate, batch) | Low | bootstrap() is called once in main(), subcommands unaffected | T1.2 | ✅ addressed |
| RE-2 | downstream | `bridge.py` FastAPI lifespan | Low | Bootstrap for logging only; engine stays in _lifespan() | T1.3 | ✅ addressed |
| RE-3 | downstream | Test conftest.py logging init | Low | conftest uses bootstrap() with console_format="human" | T1.4 | ✅ addressed |
| RE-4 | downstream | `scripts/run_calibration.py` engine restart loop | Medium | Phase 6 preserves _run_all_puzzles() restart logic (MH-1) | T6.4 | ✅ addressed |
| RE-5 | lateral | `_model_paths.py` importers (tests/conftest.py, scripts) | Low | Lazy load defers WHEN not IF; path constants stay eager | T4.1 | ✅ addressed |
| RE-6 | lateral | `config/__init__.py::clear_cache()` | Medium | Must call `_get_cfg.cache_clear()` (MH-2) | T4.2 | ✅ addressed |
| RE-7 | upstream | `analyzers/single_engine.py` API surface | Low | __aenter__/__aexit__ is additive; existing start/shutdown unchanged | T2.1 | ✅ addressed |
| RE-8 | lateral | `tests/test_cli.py` mocking | Low | Mocks SingleEngineManager — CM addition doesn't break mocks | T2.1 | ✅ addressed |
| RE-9 | downstream | `tests/render_fixtures.py` render pipeline | Low | Imports change from local to _sgf_render_utils; behavior identical | T5.2 | ✅ addressed |
| RE-10 | downstream | `tests/generate_review_report.py` HTML report generation | Low | Same import change; report output identical | T5.3 | ✅ addressed |
| RE-11 | lateral | `scripts/diagnose_chase_puzzle.py` | Low | Only bootstrap() adoption; core diagnostic logic untouched | T1.6 | ✅ addressed |
| RE-12 | upstream | `log_config.py` API surface | Low | bootstrap() is a new convenience function, not replacing anything | T1.1 | ✅ addressed |

---

## 5. Cross-Artifact Consistency

| check_id | charter_item | options_item | plan_item | tasks_item | consistent? |
|----------|-------------|-------------|-----------|-----------|-------------|
| CC-1 | G1 | OPT-3 Phase 1 | AD-1 | T1.1–T1.7 | ✅ |
| CC-2 | G2 | OPT-3 Phase 4 | AD-4 | T4.1–T4.4 | ✅ |
| CC-3 | G3 | OPT-3 Phase 3 | AD-3 | T3.1–T3.5 | ✅ |
| CC-4 | G4 | OPT-3 Phase 2 | AD-2 | T2.1–T2.4 | ✅ |
| CC-5 | G5 | OPT-3 Phase 5 | AD-5 | T5.1–T5.5 | ✅ |
| CC-6 | G6 | OPT-3 Phase 6 | AD-6, AD-7 | T6.1–T6.8 | ✅ |
| CC-7 | G7 | All phases | All gates | T0.1, T*.7/T*.8 | ✅ |
| CC-8 | C4 (no probe_frame) | Excluded | Not in plan | No tasks | ✅ |
| CC-9 | C5 (AGENTS.md) | Phase 7 | DOC-1 | T7.1 | ✅ |
| CC-10 | MH-1 (restart cadence) | OPT-3 Phase 6 | AD-6 | T6.4 | ✅ |
| CC-11 | MH-2 (clear_cache) | OPT-3 Phase 4 | AD-4 | T4.2 | ✅ |
| CC-12 | MH-3 (flag naming) | OPT-3 Phase 6 | AD-6 | T6.6 | ✅ |

---

## 6. Test Strategy Verification

### Regression Command (from 10-clarifications.md)
```bash
python -B -m pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" \
  --ignore=tools/puzzle-enrichment-lab/tests/test_golden5.py \
  --ignore=tools/puzzle-enrichment-lab/tests/test_calibration.py \
  --ignore=tools/puzzle-enrichment-lab/tests/test_ai_solve_calibration.py \
  -q --no-header --tb=short -p no:cacheprovider
```

### Test Gates
| Phase | Before | After | Extra |
|-------|--------|-------|-------|
| Phase 1 | ✅ T0.1 baseline | ✅ T1.7 | — |
| Phase 2 | T1.7 | ✅ T2.4 | — |
| Phase 3 | T2.4 | ✅ T3.5 | — |
| Phase 4 | T3.5 | ✅ T4.3 | T4.4: clear_cache interaction |
| Phase 5 | T4.3 | ✅ T5.5 | — |
| Phase 6 | T5.5 | ✅ T6.8 | Verify calibration test subset |
| Phase 7 | T6.8 | ✅ T7.2 | Final baseline comparison |

> **See also:**
> - [Charter](./00-charter.md) — Goals and constraints
> - [Plan](./30-plan.md) — Architecture decisions
> - [Tasks](./40-tasks.md) — Execution checklist
> - [Governance](./70-governance-decisions.md) — Panel decisions
