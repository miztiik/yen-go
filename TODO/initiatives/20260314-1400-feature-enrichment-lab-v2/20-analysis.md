# Analysis — Enrichment Lab V2 (OPT-3)

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Last Updated**: 2026-03-14

---

## 1. Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 85 |
| `risk_level` | medium |
| `research_invoked` | true |
| `research_artifacts` | 4 (external patterns, lab assessment, pipeline stages, visit counts) |

---

## 2. Consistency & Coverage Findings

| F-ID | Severity | Finding | Charter Ref | Plan Ref | Task Ref | Status |
|------|----------|---------|-------------|----------|----------|--------|
| F1 | Low | G-11 (graceful degradation) spans both Phase 1 (fallback chain T14) and Phase 2 (quality tracking T52-T53). The phasing is correct — Phase 1 establishes the fallback mechanism, Phase 2 adds the quality tracking. | G-11 | §1.2 | T14, T52-T53 | ✅ addressed |
| F2 | Low | G-10 (modular design) is a cross-cutting concern, not a deliverable with a single task. It's enforced by the detector directory structure (T31) and file-per-feature convention. No explicit "verify modularity" task exists. | G-10 | §1.4 | T31 | ✅ addressed (implicit in code review) |
| F3 | Medium | 28 detector files (T33-T49) are bundled into priority groups. Priority 4 (T47) bundles 5 detectors. Priority 5 (T48) bundles 7 detectors. These should have individual task tracking during execution for visibility. | G-1 | §1.4 | T47, T48, T49 | ✅ addressed (executor should decompose) |
| F4 | Low | `config.py` split (mentioned in lab assessment research P4) is NOT in the task list. The plan acknowledges config modifications but doesn't split the 1200-line monolith. This is acceptable — splitting config is orthogonal to enrichment quality improvement and can be a separate initiative. | — | — | — | ✅ addressed (out of scope) |
| F5 | Low | Phase 1 T7 (unify query builder) and T8 (rename QueryStage → AnalyzeStage) are sequential but could cause import-level breakage across many files. Executor should stage these carefully. | G-6 | §1.1 | T7, T8 | ✅ addressed (execution note) |

---

## 3. Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | KataGo engine binary | None | No engine changes — only query parameter changes (config-driven) | T24, T25 | ✅ addressed |
| RE-2 | upstream | `config/katago-enrichment.json` | Low | Schema extension only (new fields, no removals). Existing configs still valid. | T20, T18 | ✅ addressed |
| RE-3 | upstream | `config/tags.json` | None | Read-only dependency. 28 tags are the source of truth. No modifications. | T31-T49 | ✅ addressed |
| RE-4 | downstream | `backend/puzzle_manager/` | None | NG-4: No backend changes. Lab output format (AiAnalysisResult) unchanged. | — | ✅ addressed |
| RE-5 | downstream | Frontend | None | NG-3: No frontend changes. SGF enrichment format unchanged. | — | ✅ addressed |
| RE-6 | lateral | GUI module (`gui/`) | Low | GUI reads PipelineContext. Stage renames (QueryStage → AnalyzeStage) may break GUI imports. | T8 | ✅ addressed (update imports) |
| RE-7 | lateral | CLI (`cli.py`) | Low | CLI invokes `enrich_single_puzzle()`. Interface unchanged. Stage internals transparent. | T3 | ✅ addressed |
| RE-8 | lateral | Bridge (`bridge.py`) | Low | Bridge passes config to orchestrator. Config schema must be backward-compatible (new fields with defaults). | T20 | ✅ addressed |
| RE-9 | lateral | Existing test fixtures | Medium | Removing crop changes query format in test assertions. Golden file tests may need regeneration. | T10(Phase1), T56(Phase2) | ✅ addressed (test gates) |
| RE-10 | lateral | `models/analysis_request.py` | Medium | Adding `reportAnalysisWinratesAs` field. Must have a default value for backward compat in model serialization. | T24 | ✅ addressed |

---

## 4. Coverage Map

### 4.1 Goal → Task Traceability

| Goal | Tasks | Coverage |
|------|-------|----------|
| G-1 (28 techniques) | T31, T32, T33-T49 | ✅ Full — 28 detectors = 28 tags |
| G-2 (remove cropping) | T5, T6, T7, T8, T9, T10 | ✅ Full |
| G-3 (entropy ROI) | T11, T12, T13, T14, T15 | ✅ Full |
| G-4 (refutation consistency) | T16, T17, T18, T19 | ✅ Full |
| G-5 (visit tiers) | T20, T21, T22, T23 | ✅ Full |
| G-6 (pipeline cleanup) | T1, T2, T3, T4, T7, T8 | ✅ Full |
| G-7 (board-state detectors) | T33-T49 (detectors using liberty.py) | ✅ Full |
| G-8 (pattern-based ladder) | T35 | ✅ Full |
| G-9 (complexity metric) | T50, T51 | ✅ Full |
| G-10 (modular SRP) | T4, T31 (directory structure) | ✅ Implicit |
| G-11 (graceful degradation) | T14, T52, T53 | ✅ Full |
| G-12 (HumanSL) | T57, T58, T59 | ✅ Full |
| G-13 (KataGo query) | T24, T25, T26, T18 | ✅ Full |

### 4.2 Acceptance Criteria → Task Traceability

| AC# | Description | Tasks |
|-----|-------------|-------|
| 1 | 28 technique tags with tests | T33-T49 |
| 2 | CroppedPosition deleted | T5, T9 |
| 3 | Entropy ROI module with tests | T11-T15 |
| 4 | Refutation framing fix | T16-T19 |
| 5 | Visit tiers configurable | T20-T23 |
| 6 | Solve-paths wrapped | T3 |
| 7 | No double parsing | T7, T8 |
| 8 | BFS frame deleted | T1 |
| 9 | Pattern-based ladder | T35 |
| 10 | Complexity metric | T50, T51 |
| 11 | reportAnalysisWinratesAs=BLACK | T24 |
| 12 | Existing tests pass | T30 (P1 gate), T56 (P2 gate) |
| 13 | New tests per module | Each T includes tests |
| 14 | Docs updated | T27, T28, T29, T54, T55 |
| 15 | HumanSL feature gate | T57-T59 |
| 16 | No enrichment regression | T30, T56 |

### 4.3 Unmapped Tasks

None. All 60 tasks trace to at least one goal or acceptance criterion.

---

## 5. Must-Hold Constraint Verification

| MH-ID | Constraint | Verified In | Status |
|-------|-----------|-------------|--------|
| MH-1 | G-2 + G-3 ship together in Phase 1 | Tasks T5-T10 (crop removal) + T11-T15 (entropy) all in Phase 1 | ✅ verified |
| MH-2 | G-10 in Phase 1 | T4 (stage split) + T31 (detector dir) — T4 is Phase 1, T31 is Phase 2 start. Modular design *established* in Phase 1 via stage splits, *extended* in Phase 2 via detector dir. | ✅ verified |
| MH-3 | Phase 2 prioritizes high-frequency tags | T33-T36 (Priority 1) → T37-T41 (Priority 2) → T42-T46 (Priority 3) → T47-T49 (Priority 4-6) | ✅ verified |
| MH-4 | Plan selects pipeline restructuring approach | Plan §1.1 selects Research Option 8.2 with rationale | ✅ verified |
| MH-5 | Independent test gate per phase | T30 (Phase 1 gate), T56 (Phase 2 gate), T60 (Phase 3 gate) | ✅ verified |
| MH-6 | Phase 3 doesn't block Phase 1/2 | T57-T60 depend only on Phase 2 completion. No reverse dependency. | ✅ verified |

---

## 6. Risk Assessment Update

| Risk | Pre-Plan Level | Post-Plan Level | Change Rationale |
|------|---------------|-----------------|------------------|
| GPL contamination | Medium | Low | Plan specifies clean-room implementation from algorithmic descriptions. Ladder detector (T35) is the only Lizgoban-inspired component. |
| Visit increase slows throughput | Low | Low | T0 (50 visits) pre-classification filters easy puzzles. Only escalation path reaches T3. |
| 28 detectors ambitious | High | Medium | Priority ordering (MH-3) ensures highest-value detectors ship first. Context-dependent tags (joseki, fuseki) have documented quality bar. |
| Removing cropping changes policy | Medium | Low | Entropy ROI ships simultaneously (MH-1). Fallback chain (T14) provides safety net. |
| Config schema drift | Medium | Low | T2 fixes existing 8 failures. New config fields have defaults. |

---

## 7. Phase Metrics

| Phase | Tasks | New Files | Modified Files | Deleted Files | Test Files |
|-------|-------|-----------|----------------|---------------|------------|
| Phase 1 | T1-T30 | ~8 | ~12 | ~3 | ~6 new |
| Phase 2 | T31-T56 | ~30 | ~4 | 0 | ~28 new |
| Phase 3 | T57-T60 | ~2 | ~2 | 0 | ~1 new |
| **Total** | **60** | **~40** | **~18** | **~3** | **~35 new** |
