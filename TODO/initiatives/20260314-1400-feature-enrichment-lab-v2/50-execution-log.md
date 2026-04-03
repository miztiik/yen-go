# Execution Log — Enrichment Lab V2 (OPT-3)

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Last Updated**: 2026-03-14

---

## Intake Validation

| Item | Status | Evidence |
|------|--------|----------|
| Charter approved | ✅ | GOV-CHARTER-CONDITIONAL, all 8 RCs applied |
| Options approved | ✅ | GOV-OPTIONS-APPROVED, OPT-3 unanimously selected |
| Plan approved | ✅ | GOV-PLAN-CONDITIONAL, all 5 RCs applied |
| Amendment approved | ✅ | GOV-PLAN-CONDITIONAL, 4 Lizgoban concepts added |
| Tasks approved | ✅ | 63 tasks across 3 phases |
| Analysis findings resolved | ✅ | All F1-F5 addressed |
| Backward compat decision | ✅ | Not required (user explicit) |
| Governance handover consumed | ✅ | from=Governance-Panel, to=Plan-Executor |
| Docs plan present | ✅ | §5 in 30-plan.md with files_to_create/update |
| status.json valid | ✅ | All pre-execute phases approved |

## Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1 | `analyzers/tsumego_frame.py`, `tests/test_tsumego_frame.py` | none | ✅ merged |
| L2 | T2 | 4 test files | none | ✅ merged |
| L3 | T2B | `models/validation.py` (new), 9 files | none | ✅ merged |
| L4 | T3 | `solve_path_stage.py` (new), `enrich_single.py` | none | ✅ merged |
| L5 | T4 | `technique_stage.py`, `sgf_writeback_stage.py` (new), `teaching_stage.py` | none | ✅ merged |
| L6 | T5 | `models/position.py` | none | ✅ merged |
| L7 | T11 | `analyzers/entropy_roi.py` (new) | none | ✅ merged |
| L8 | T20, T24 | `config.py`, `katago-enrichment.json`, `analysis_request.py` | none | ✅ merged |
| L9 | T6-T10 | crop removal chain (7 files) | L6 | ✅ merged |
| L10 | T12-T15 | entropy ROI chain (8 files) | L7 | ✅ merged |
| L11 | T16-T19,T16B,T18B | refutation fixes (8 files) | L9 | ✅ merged |
| L12 | T4B,T21-T23,T25-T26 | pruning + tiers + symmetries (8 files) | L9,L8 | ✅ merged |
| L13 | T27-T29 | Phase 1 docs (3 files) | L12 | ✅ merged |
| L14 | T31-T32 | detector infrastructure (4 files) | P1 gate | ✅ merged |
| L15 | T33-T36 | priority 1 detectors (5 files) | L14 | ✅ merged |
| L16 | T37-T41 | priority 2 detectors (6 files) | L14 | ✅ merged |
| L17 | T42-T46 | priority 3 detectors (6 files) | L14 | ✅ merged |
| L18 | T47-T49 | priority 4-6 detectors (15 files) | L14 | ✅ merged |
| L19 | T50-T53,T56B,T61-T63 | complexity + degradation (11 files) | P1 gate | ✅ merged |
| L20 | T54-T55 | Phase 2 docs (2 files) | L18 | ✅ merged |
| L21 | T57-T60 | HumanSL (4 files) | P2 gate | ✅ merged |

## Execution Progress

### Phase 1 — Foundation (T1-T30) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-1 | T1: Delete BFS frame | ✅ | 2 files deleted, grep: 0 deps |
| EX-2 | T2: Fix 8 test failures | ✅ | 8 fixes, 47 tests pass |
| EX-3 | T2B: Extract ValidationStatus | ✅ | 10 files updated, V-1 fixed |
| EX-4 | T3: SolvePathStage | ✅ | New stage, 304 tests pass |
| EX-5 | T4: Split TeachingStage | ✅ | 3 stages, 911 tests pass |
| EX-6 | T5: Remove CroppedPosition | ✅ | Class + method deleted |
| EX-7 | T6-T10: Crop removal chain | ✅ | 1658 pass, 0 failures |
| EX-8 | T11-T15: Entropy ROI chain | ✅ | Module + tests + fallback |
| EX-9 | T16-T19,T16B,T18B: Refutations | ✅ | 1691 pass, tenuki rejector added |
| EX-10 | T4B,T21-T23,T25-T26: Wiring | ✅ | 1713 pass, visit tiers wired |
| EX-11 | T27-T29: Phase 1 docs | ✅ | 3 docs created/updated |
| EX-12 | T30: Phase 1 gate | ✅ | 1713 passed, 36 skipped, RC=0 |

### Phase 2 — Detection (T31-T56B, T61-T63) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-13 | T31-T32: Infrastructure | ✅ | Protocol + dispatcher, 1713 pass |
| EX-14 | T33-T36: Priority 1 detectors | ✅ | 4 detectors, 13 tests |
| EX-15 | T37-T41: Priority 2 detectors | ✅ | 5 detectors, 18 tests |
| EX-16 | T42-T46: Priority 3 detectors | ✅ | 5 detectors, 21 tests |
| EX-17 | T47-T49: Priority 4-6 detectors | ✅ | 14 detectors, 29 tests |
| EX-18 | T50-T53,T56B,T61-T63: Complexity | ✅ | 5th metric, arch guard, 1818 pass |
| EX-19 | T54-T55: Phase 2 docs | ✅ | 2 concept docs |
| EX-20 | T56: Phase 2 gate | ✅ | 1818 passed, 36 skipped, RC=0 |

### Phase 3 — Stretch (T57-T60) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-21 | T57-T59: HumanSL | ✅ | Module + tests, 11 tests pass |
| EX-22 | T60: Phase 3 gate | ✅ | 1829 passed, 36 skipped, RC=0 |

### Governance RC Remediation (T64-T70) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-23 | T64: Wire 28 detectors into TechniqueStage | ✅ | `TechniqueStage.run()` calls `run_detectors()` with `get_all_detectors()`. All 28 detector classes imported, instantiated, and invoked via typed Position/AnalysisResponse/SolutionNode objects. Old dict-based `classify_techniques()` no longer the active path. |
| EX-24 | T65: Fix stale docstring (RC-2) | ✅ | `generate_refutations()` docstring updated: "position: Board position (framed if available, original otherwise)" replaces "UNFRAMED — puzzle stones only" |
| EX-25 | T66: Fix monkey-patched _temperature_score (RC-4) | ✅ | `identify_candidates()` uses `temp_scores: dict[str, float]` instead of `m._temperature_score` monkey-patch. Type-safe. |
| EX-26 | T67: Pass typed objects to detectors (CRA-4) | ✅ | `TechniqueStage` passes `ctx.position` (Position), `ctx.response` (AnalysisResponse), and `solution_tree=None` (SolutionNode | None) directly to `run_detectors()`. No more `model_dump()` dict serialization. |
| EX-27 | T68: Golden-set difficulty spot-check (RC-3) | ✅ | 50 profiles tested via TestGoldenSetCalibration: 50/50 within expected range, monotonic group averages verified, 0 extreme tier shifts. VAL-7 added. |
| EX-28 | T69: Integration test for detector wiring | ✅ | TestGetAllDetectors (3 tests: 28 count, protocol check, unique classes), TestRunDetectorsIntegration (3 tests: result type, produces tags, explicit list). All 6 pass. |
| EX-29 | T70: RC remediation gate | ✅ | 1887 passed, 36 skipped, RC=0. Backend: 1969 passed, RC=0. |

### Governance RC Remediation 2 (T71-T80) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-30 | T71: Rewrite ladder detector — board-state 3×3 pattern matching | ✅ | `LadderDetector` now uses `_simulate_ladder_chase()` as primary: BFS group/liberty computation, recursive atari-extend simulation on actual board. PV diagonal ratio retained as secondary fallback with reduced confidence (≤0.6). Clean-room docstring added. 3 new synthetic tests: shicho→True, breaker→False, net→False. |
| EX-31 | T72: Fix stale import in probe_frame.py | ✅ | `from analyzers.tsumego_frame import apply_tsumego_frame` → `from analyzers.frame_adapter import apply_frame`. Call site adapted. |
| EX-32 | T73: Update stages/README.md | ✅ | `QueryStage` → `AnalyzeStage`, `solve_paths` → `SolvePathStage`, "crop" references removed. |
| EX-33 | T74: Clean-room documentation in ladder detector | ✅ | Module docstring explicitly declares independent clean-room implementation with no GPL source code referenced. |
| EX-34 | T75: Add warning log for config fallback | ✅ | `pass` → `logger.warning("Config load failed — using hardcoded defaults (test mode only)")` in `query_builder.py`. |
| EX-35 | T76: Deprecate classify_techniques() | ✅ | Added deprecation docstring. NOT deleted: `result_builders.py` and 17 test sites actively call it. Follow-up needed to migrate callers. |
| EX-36 | T77: Wire referee_symmetries for T3 | ✅ | `build_query_from_sgf(referee=True)` param added. When True, uses `config.deep_enrich.referee_symmetries` (8) instead of standard (4). |
| EX-37 | T78: Fix entropy ROI column bounds | ✅ | Fallback `"A"` → `continue` for out-of-range `col >= len(letters)`. |
| EX-38 | T79: Cache HumanSL feature gate | ✅ | Module-level `_humansl_available_cache: dict[str, bool]` caches `os.path.exists()` result by model path. |
| EX-39 | T80: RC remediation 2 gate | ✅ | 1890 passed, 36 skipped, RC=0. Backend: 1969 passed, RC=0. Architecture guard: 11 passed. |

## Parallel Lane Plan (RC Remediation 2)

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L22 | T72,T73,T75,T76,T77,T78,T79 | 6 files | T60 | ✅ merged |
| L23 | T71,T74 | 2 files | T60 | ✅ merged |

## Parallel Lane Plan (RC Remediation 3)

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L24 | T81 | `analyzers/detectors/ladder_detector.py`, `tests/test_detectors_priority1.py` | T80 | ✅ merged |
| L25 | T82 | `analyzers/detectors/snapback_detector.py`, `config.py`, `tests/test_detectors_priority1.py` | T80 | ✅ merged |
| L26 | T83,T84,T85 | `config.py`, `config/katago-enrichment.json`, `analyzers/entropy_roi.py`, `tests/test_architecture.py` | T80 | ✅ merged |
| L27 | T86,T87 | `analyzers/result_builders.py`, `analyzers/stages/solve_paths.py` | L24-L26 | ✅ merged |
| L28 | T88 | `AGENTS.md`, `docs/reference/katago-enrichment-config.md` | L27 | ✅ merged |

### Governance RC Remediation 3 (T81-T89) ✅

| EX-ID | Task | Status | Evidence |
|-------|------|--------|----------|
| EX-40 | T81: Ladder detector capture logic | ✅ | `_remove_captured_stones()` added. Scans adjacent opponent groups after each stone placement, removes groups with 0 liberties. Integrated at 3 points in `_simulate_ladder_chase()`. |
| EX-41 | T82: Snapback detector PV verification | ✅ | `_parse_gtp()` and `_pv_has_recapture_pattern()` added. PV-confirmed snapbacks get confidence 0.85+, signal-only detection reduced to 0.45. `min_pv_length` config added. |
| EX-42 | T83: Seki winrate band tightened | ✅ | `SekiDetectionConfig` defaults: `winrate_low=0.40`, `winrate_high=0.60`. Updated in config.py and katago-enrichment.json. |
| EX-43 | T84: Entropy contest threshold configurable | ✅ | `entropy_contest_threshold: float = 0.5` added to `FrameEntropyQualityConfig`. Added to katago-enrichment.json. `compute_entropy_roi()` accepts threshold param. |
| EX-44 | T85: TestNoBackendImports architecture guard | ✅ | `TestNoBackendImports` class added to `test_architecture.py`. Scans all lab `.py` files for `backend.puzzle_manager` imports via AST. |
| EX-45 | T86: Migrate result_builders to run_detectors | ✅ | `build_partial_result()` now uses `run_detectors()` with typed Position/AnalysisResponse when available, falls back to `classify_techniques()` only for null-analysis cases. `position` param added to function signature. Callers in `solve_paths.py` updated. |
| EX-46 | T87: Reduce Any imports | ✅ | `result_builders.py` now imports `run_detectors` and `get_all_detectors` from typed path. `Any` usage reduced — primary code path is fully typed. |
| EX-47 | T88: Documentation updates | ✅ | AGENTS.md updated (28 detectors, no cropping). docs updated for seki thresholds and entropy config. |
| EX-48 | T89: RC remediation 3 gate | ✅ | 1894 lab + 1969 backend = 3863 tests, 0 failures. |

---
