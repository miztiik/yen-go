# Charter — Enrichment Lab V2: Comprehensive Puzzle Enrichment Rewrite

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Type**: Feature  
**Last Updated**: 2026-03-14

---

## 1. Problem Statement

The puzzle enrichment lab (`tools/puzzle-enrichment-lab/`) has accumulated significant technical debt across multiple sprint iterations (v1.0–v1.17). While the stage pipeline architecture (StageRunner pattern) is sound, the analyzer modules that power technique detection, refutation generation, difficulty estimation, and board preparation are producing unreliable results:

1. **Technique detection detects only 6 of 28 tags (21%)** — using fragile PV-based heuristics instead of board-state analysis
2. **Refutations are unreliable** — sometimes not generated (cascading failure from wrong bounding box + strict config + low visit budget), sometimes unconvincing
3. **Board cropping causes cascading failures** — 19×19→9/13 cropping leads to policy dilution, frame misalignment, dropped stones, and coordinate back-translation complexity
4. **Tsumego frame for small boards doesn't work** — GP frame was designed for 19×19, fails on cropped boards
5. **Refutation queries use unframed position** — KataGo sees a different board state than the main analysis (critical correctness bug)
6. **Double SGF parsing** — QueryStage re-parses what ParseStage already parsed
7. **Solve-path dispatch runs outside StageRunner** — no timing, no error-policy wrapping, builds its own queries
8. **Visit budget too low** — 200/2000 visits insufficient for tsumego (KaTrain uses 500 standard, GoProblems gets good results at 500-1000)
9. **Hinting and teaching tags broken** — downstream of technique detection failures
10. **Difficulty estimation lacks complexity metric** — missing KaTrain's prior-weighted loss formula

## 1B. Phasing Recommendation

The options phase MUST evaluate phased delivery vs monolithic delivery as a required comparison axis:
- **Phase 1 (Correctness)**: G-2, G-4, G-6, G-13 — remove cropping, fix refutation consistency, pipeline cleanup, KataGo query fixes
- **Phase 2 (Features)**: G-1, G-3, G-5, G-7, G-8, G-9, G-10, G-11, G-12 — new technique detectors, entropy ROI, visit tiers, pattern-based ladder, etc.

This phasing ensures correctness fixes are not blocked by feature development.

## 2. Goals

| G-ID | Goal | Acceptance Criteria |
|------|------|---------------------|
| G-1 | **All 28 technique tags detectable** | Technique classifier has a detector for every tag in `config/tags.json`. Each detector has ≥1 positive and ≥1 negative unit test. Context-dependent tags (`joseki`, `fuseki`, `endgame`) accepted at heuristic quality with documented limitations. |
| G-2 | **Remove board cropping entirely** | No `crop_to_tight_board()` calls. All analysis on original board size. `CroppedPosition` model deleted. No coordinate back-translation. |
| G-3 | **Entropy-based Region of Interest (ROI)** | New `entropy_roi.py` module computes ownership entropy per intersection, identifies contested region. Used as `allowMoves` restriction. In separate file from frame logic. |
| G-4 | **Fix refutation consistency** | Refutation queries use same framed/ROI-restricted position as main analysis. Visit budget increased. Refutation quality validated by tests. |
| G-5 | **Increase visit tiers** | T0=50 (policy-only), T1=500 (standard), T2=2000 (deep), T3=5000 (referee). Config-driven. Escalation logic clean and tested. |
| G-6 | **Pipeline stage cleanup** | Solve-paths formalized as a stage. Double-parsing eliminated. Technique classification isolated. Dead code (BFS frame) deleted. |
| G-7 | **Board-state technique detectors** | Detectors use `liberty.py` for group analysis (liberty count, eye detection, connectivity) instead of only PV patterns. |
| G-8 | **Pattern-based ladder detector** | Clean-room implementation of 3×3 pattern matching with 8-symmetry transforms (inspired by Lizgoban, not copied). Hybrid with PV confirmation. |
| G-9 | **Complexity metric** | KaTrain's `Σ(prior × max(score_delta, 0)) / Σ(prior)` added as difficulty signal |
| G-10 | **Modular SRP design** | Every feature in its own file. Frame, entropy, each technique detector testable independently. No SOLID/DRY/SRP violations. |
| G-11 | **Graceful degradation** | Frame failure → entropy ROI fallback → `allowMoves` only. Never skip puzzles. Quality level tracked per puzzle. |
| G-12 | **HumanSL feature-gated** | Query parameter support for `humanSLProfile`. Feature-gated behind model file existence. Deferred to stretch. |
| G-13 | **KataGo query improvements** | Explicit `reportAnalysisWinratesAs=BLACK`. Refutation-specific `overrideSettings` (rootPolicyTemperature, wideRootNoise). `rootNumSymmetriesToSample` increased 2→4. |

## 3. Non-Goals

| NG-ID | Non-Goal | Rationale |
|-------|----------|-----------|
| NG-1 | Game-play analysis | This is for offline puzzle enrichment only |
| NG-2 | Multi-file batch parallelism | One file at a time. Optimize single-file throughput |
| NG-3 | Frontend changes | No UI modifications — enrichment lab output format unchanged |
| NG-4 | Backend pipeline manager changes | Changes scoped to `tools/puzzle-enrichment-lab/` only |
| NG-5 | New config file formats | Extend existing `katago-enrichment.json`, don't create new formats |
| NG-6 | KataGo binary/model changes | Use existing engine; only change query parameters |
| NG-7 | Backward compatibility | Old code can be deleted. No migration path needed. |
| NG-8 | HumanSL implementation (this initiative) | Feature-gated interface only. Full implementation deferred. |

## 4. Constraints

| C-ID | Constraint | Rationale |
|------|-----------|-----------|
| C-1 | GPL-3.0 compliance for Lizgoban | Algorithm inspiration only — no code copying. Clean-room implementations. |
| C-2 | MIT compliance for KaTrain | Attribution in source files. Algorithm adoption is clear. |
| C-3 | `tools/` isolation | Lab must NOT import from `backend/puzzle_manager/`. Self-contained. |
| C-4 | Python 3.11+ | Type hints everywhere. Pydantic v2 models. |
| C-5 | Config-driven thresholds | All numeric thresholds in `katago-enrichment.json`, never hardcoded. |
| C-6 | Existing test infrastructure | pytest, no new test frameworks. |
| C-7 | SRP / modular files | Each feature (frame, entropy, each detector) in its own file. |

## 5. Acceptance Criteria (Definition of Done)

1. All 28 technique tags have a detector with ≥1 unit test each
2. Board cropping code and `CroppedPosition` model deleted
3. Entropy ROI module exists in its own file with tests
4. Refutation queries use framed position (no P-5.1 bug)
5. Visit tiers configurable (T0/T1/T2/T3) with escalation
6. Solve-paths wrapped in StageRunner
7. No double SGF parsing
8. BFS frame dead code deleted
9. Pattern-based ladder detector with tests
10. Complexity metric added to difficulty formula
11. `reportAnalysisWinratesAs=BLACK` explicit in queries
12. All existing passing enrichment-lab tests continue to pass (~270+ lab tests). Backend tests (~1,251) unaffected (no `backend/` changes).
13. New tests for each new/modified analyzer module
14. Documentation updated in `docs/`
15. HumanSL query parameter support exists behind feature gate. Feature gate checks for model file existence.
16. No regression in existing enrichment output for puzzles that currently enrich successfully.

## 6. Stakeholders

| Role | Perspective |
|------|------------|
| Developer | Code quality, testability, maintainability |
| Go Domain Expert | Technique detection accuracy, difficulty calibration, hint quality |
| End User (puzzle solver) | Correct difficulty labels, accurate hints, convincing wrong-move feedback |
| Pipeline Operator | Reliability, clear error messages, graceful degradation |

## 7. Research Artifacts

| Artifact | Path | Key Findings |
|----------|------|--------------|
| External repos research | `TODO/initiatives/20260314-research-lizgoban-katrain-patterns/15-research.md` | Lizgoban ladder.js (pattern-based detection), area.js (ownership clustering), KaTrain ai.py (complexity metric, ELO mapping) |
| Current lab assessment | `TODO/initiatives/20260314-research-enrichment-lab-rewrite/15-research.md` | 99.5% test pass rate, 8 config-drift failures, GP frame active, BFS dead code |
| Pipeline stage analysis | `TODO/initiatives/20260314-1400-feature-enrichment-lab-v2/15-research.md` | 2 high-severity cross-stage bugs (P-5.1, F-X.1), 6/28 technique detection, stage flow diagram |
| Visit count research | `TODO/initiatives/20260314-research-lizgoban-katrain-patterns/15-research-visit-counts.md` | KaTrain 500 standard, recommended T0=50/T1=500/T2=2000/T3=5000 |

## 8. Risk Summary

| Risk | Level | Mitigation |
|------|-------|------------|
| GPL contamination from Lizgoban | Medium | Clean-room algorithm implementation from descriptions |
| Visit increase slows enrichment throughput | Low | Tiered approach: quick pass filters easy puzzles |
| Removing cropping changes all coordinate systems | Medium | Single code path (original board coords only) is actually simpler |
| 28-technique detection is ambitious | High | Prioritize by frequency in corpus. Accept "unknown" for rare techniques. Context-dependent tags (joseki, fuseki, endgame) may only achieve heuristic-level detection — document limitations per tag. |
| Config schema changes break existing tests | Medium | Fix 8 known failing tests as part of this work |
