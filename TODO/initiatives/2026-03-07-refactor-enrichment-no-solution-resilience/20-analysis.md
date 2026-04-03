# Analysis: Enrichment Lab No-Solution Resilience

**Initiative ID:** 2026-03-07-refactor-enrichment-no-solution-resilience  
**Last Updated:** 2026-03-07

---

## Planning Confidence

| Metric                    | Value                                           |
| ------------------------- | ----------------------------------------------- |
| Planning Confidence Score | 88                                              |
| Risk Level                | low                                             |
| Research Invoked          | Yes (Feature-Researcher: WebKaTrain comparison) |

---

## Findings

| F-ID | Severity | Category      | Finding                                                                                                                                         | Resolution                                              |
| ---- | -------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| F1   | CRITICAL | Bug           | `enrich_single.py:546` hard-rejects position-only SGFs without ever calling KataGo when `ai_solve.enabled=false`                                | T5: Replace with position scan + tier-2                 |
| F2   | CRITICAL | Bug           | `enrich_single.py:598` discards KataGo analysis data when `pos_analysis.correct_moves` is empty                                                 | T6: Reuse pos_analysis → tier-2                         |
| F3   | HIGH     | Bug           | `solve_position.py:189` derives `root_winrate` from `move_infos[0].winrate` instead of `analysis.root_winrate` (from KataGo `rootInfo.winrate`) | T1: 1-line fix                                          |
| F4   | MEDIUM   | Config        | `ai_solve.enabled=false` means position-only SGFs are blocked from ALL KataGo analysis, not just tree building                                  | T5: Position scan runs independently of `ai_solve` flag |
| F5   | MEDIUM   | Documentation | `enrichment_tier` docstring doesn't reflect tier-2 dual semantics (legacy migration + partial enrichment)                                       | T3: Docstring update (RC-9 condition)                   |
| F6   | LOW      | Consistency   | `25-options.md` says "add enrichment_tier field" but it already exists (v7, D3)                                                                 | Cosmetic — corrected in plan                            |
| F7   | LOW      | Test coverage | No existing tests cover position-only SGFs without ai_solve                                                                                     | T8, T9, T10: New tests                                  |

---

## Coverage Map

| Goal/Requirement                                             | Task IDs                                     |
| ------------------------------------------------------------ | -------------------------------------------- |
| Fix Bug A (position-only + no ai_solve → partial enrichment) | T2, T4, T5, T8, T9                           |
| Fix Bug B (ai_solve + no correct moves → partial enrichment) | T4, T6, T10                                  |
| Fix root_winrate derivation (CA-1)                           | T1, T7, T12                                  |
| Verify correct-moves-only SGFs (no wrong moves) still work   | T11                                          |
| Config-driven scan visits                                    | T2                                           |
| Enrichment tier semantics                                    | T3                                           |
| Pipeline integration readiness                               | T3 (docstring), T4 (enrichment_tier setting) |
| All RC constraints                                           | See RC traceability below                    |

## RC Traceability

| RC-ID | Constraint                                      | Task ID              |
| ----- | ----------------------------------------------- | -------------------- |
| RC-1  | Use `analysis.root_winrate`                     | T1                   |
| RC-2  | try/except for scan                             | T5                   |
| RC-3  | Reuse pos_analysis                              | T6                   |
| RC-4  | Use existing `enrichment_tier` field            | T4                   |
| RC-5  | Configurable scan visits                        | T2                   |
| RC-6  | Mock-based unit tests                           | T7, T8, T9, T10, T11 |
| RC-7  | Observability log for scan                      | T5                   |
| RC-8  | No solution tree injection for tier-1/2         | T4, T5, T6           |
| RC-9  | Update docstring for tier-2 dual semantics      | T3                   |
| RC-10 | Use `estimate_difficulty_policy_only()`         | T4                   |
| RC-11 | Teaching comments conditional on technique tags | T4                   |
| RC-12 | YQ.ac consistent with tier                      | T4                   |

## Unmapped Tasks

None. All 12 tasks map to at least one requirement or RC constraint.

---

## Ripple Effects

| impact_id | direction  | area                                                                | risk   | mitigation                                                                 | owner_task | status       |
| --------- | ---------- | ------------------------------------------------------------------- | ------ | -------------------------------------------------------------------------- | ---------- | ------------ |
| RE-1      | upstream   | `AnalysisResponse.root_winrate` field availability                  | Low    | Verified: populated from `rootInfo.winrate` via `from_katago_json()`       | T1         | ✅ addressed |
| RE-2      | downstream | `classify_move_quality()` delta values shift by <0.005              | Low    | Within MCTS noise; no classification threshold crossings at typical visits | T1, T7     | ✅ addressed |
| RE-3      | downstream | `PositionAnalysis.root_winrate` consumers                           | Low    | Value source changes but magnitude unchanged                               | T1         | ✅ addressed |
| RE-4      | downstream | `sgf_enricher.py` — must accept partial results (empty refutations) | Low    | Already handles empty refutations gracefully (PA3 verified)                | T5, T6     | ✅ addressed |
| RE-5      | lateral    | Concurrent work in `tools/puzzle-enrichment-lab/`                   | Medium | CA-1 (T1) is mergeable independently; main changes in `enrich_single.py`   | T5, T6     | ✅ addressed |
| RE-6      | lateral    | Test mock consistency for `root_winrate`                            | Low    | T12 audits mocks; changes are expected bug-fix behaviors                   | T12        | ✅ addressed |
| RE-7      | downstream | `config.py` `DeepEnrichConfig` model                                | Low    | Additive field with Pydantic default; no breaking change                   | T2         | ✅ addressed |
| RE-8      | downstream | Future `backend/puzzle_manager` consumption                         | Low    | `enrichment_tier` in AiAnalysisResult JSON is the integration contract     | T3, T4     | ✅ addressed |

---

## Constitution/Project-Guideline Compliance

| Rule                                            | Compliance | Evidence                                          |
| ----------------------------------------------- | ---------- | ------------------------------------------------- |
| Zero Runtime Backend                            | ✅         | No backend changes                                |
| Browser AI                                   | ✅         | No frontend changes                               |
| Deterministic Builds                            | ✅         | Config-driven, reproducible                       |
| Type Safety                                     | ✅         | Pydantic models, type hints                       |
| No `backend/puzzle_manager` imports in `tools/` | ✅         | All changes within `tools/puzzle-enrichment-lab/` |
| Config-driven (no hardcoded values)             | ✅         | `position_scan_visits` in config, not hardcoded   |
| Tests required                                  | ✅         | T7-T12 cover all new paths                        |
| Documentation required                          | ✅         | T3 (docstring)                                    |
| Git safety                                      | ✅         | No `git add .`, feature branch workflow           |
