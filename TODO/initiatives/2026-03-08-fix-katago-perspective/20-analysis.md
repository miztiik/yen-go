# Analysis — KataGo Winrate Perspective Fix + Enrichment Reconciliation

Last Updated: 2026-03-08

## Planning Metadata

| Field                     | Value                                                    |
| ------------------------- | -------------------------------------------------------- |
| Planning Confidence Score | 20 → 85 (after research + governance)                    |
| Risk Level                | high → medium (root cause identified, fix is minimal)    |
| Research Invoked          | Yes — Feature-Researcher + Purist Architect consultation |

## Severity-Based Findings

| finding_id | severity | finding                                                                                                                                       | resolution                                                    | task_id |
| ---------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ------- |
| F1         | CRITICAL | KataGo config `reportAnalysisWinratesAs = BLACK` while code assumes SIDETOMOVE — 23+ sites affected                                           | Fix config to SIDETOMOVE (1 line)                             | T1      |
| F2         | CRITICAL | Confirmation queries invert winrates → 0 correct moves for position-only puzzles                                                              | Fixed by T1 (SIDETOMOVE makes L242 normalize_winrate correct) | T1      |
| F3         | HIGH     | `generate_refutations.py` L214 `1.0 - opp_best.winrate` — correct under SIDETOMOVE (opponent perspective flip). Needs explanatory comment.    | Document with comment                                         | T2      |
| F4         | HIGH     | MockConfirmationEngine pre-flips winrates, masking the bug in tests                                                                           | Remove manual flip; mock returns SIDETOMOVE values            | T3      |
| F5         | HIGH     | Zero White-to-play test coverage for winrate classification                                                                                   | Add parametrized B+W tests                                    | T4      |
| F6         | HIGH     | Ko detection uses coordinate recurrence without capture verification (S5/P1.5)                                                                | Add capture-recapture pattern check                           | T16     |
| F7         | MEDIUM   | Difficulty weights 25/25/25/25 — policy and visits are PUCT-coupled (collinearity)                                                            | Rebalance: structural > visits+policy                         | T17     |
| F8         | MEDIUM   | 4/8 analyzer modules have ZERO logging (technique_classifier, ko_validation, estimate_difficulty components, validate_correct_move decisions) | Add comprehensive logging to all modules                      | T7-T13  |
| F9         | MEDIUM   | `enrich` CLI has no run_id — logs go to generic `enrichment.log`                                                                              | Generate and set run_id                                       | T14     |
| F10        | LOW      | Pydantic defaults drift from JSON (DifficultyWeights, TeachingConfig, QualityGates)                                                           | Sync defaults                                                 | T18     |
| F11        | LOW      | `SekiDetectionConfig` missing `score_threshold` field — getattr fallback always fires                                                         | Add field to model + JSON                                     | T18     |
| F12        | LOW      | `difficulty_result.py` backward-compat shim is dead code                                                                                      | Delete                                                        | T19     |
| F13        | LOW      | `level_mismatch` orphan section in JSON — silently dropped by loader                                                                          | Remove                                                        | T19     |
| F14        | LOW      | `ai_solve.enabled` flag has confusing dual behavior                                                                                           | Remove — always-on                                            | T20     |
| F15        | LOW      | `conftest.py` run_id format misaligned with `generate_run_id()`                                                                               | Align format                                                  | T14     |

## Coverage Map

| Goal             | Tasks        | ACs        | Findings | Covered? |
| ---------------- | ------------ | ---------- | -------- | -------- |
| G1 Config fix    | T1           | AC1        | F1, F2   | ✅       |
| G2 L214 fix      | T2           | AC2        | F3       | ✅       |
| G3 White tests   | T4           | AC3        | F5       | ✅       |
| G4 Logging       | T7-T13       | AC4        | F8       | ✅       |
| G5 Log naming    | T14          | AC5, AC6   | F9, F15  | ✅       |
| G6 Dead code     | T19          | AC7        | F12, F13 | ✅       |
| G7 ai_solve flag | T20          | AC8        | F14      | ✅       |
| G8 Mock fix      | T3           | AC9        | F4       | ✅       |
| G9 Validation    | T6           | AC10       | —        | ✅       |
| G10 Ko detection | T16          | AC13       | F6       | ✅       |
| G11 Difficulty   | T17          | AC14       | F7       | ✅       |
| — Regression     | T5, T15, T21 | AC11, AC12 | —        | ✅       |
| — Config sync    | T18          | —          | F10, F11 | ✅       |

**Unmapped tasks**: None.
**Unmapped goals**: None.
**Unmapped ACs**: None.

## Ripple-Effects Table

| impact_id | direction  | area                        | risk                                                                      | mitigation                                                                   | owner_task       | status                  |
| --------- | ---------- | --------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ---------------- | ----------------------- |
| IMP-1     | downstream | Previously enriched puzzles | All Black puzzles with confirmation queries have incorrect classification | Re-enrich affected collections after fix (POST-INITIATIVE — not part of T21) | T6 (validation)  | ✅ addressed (deferred) |
| IMP-2     | downstream | White-to-play puzzles       | All White puzzles were broken across entire pipeline                      | SIDETOMOVE fixes all 23+ sites; test coverage added                          | T1, T4           | ✅ addressed            |
| IMP-3     | lateral    | Difficulty calibration      | Weight rebalancing changes level assignments                              | Compare before/after on golden fixtures                                      | T17              | ✅ addressed            |
| IMP-4     | lateral    | Ko classification           | Capture verification may reject previously-accepted ko detections         | Test against known ko fixtures                                               | T16              | ✅ addressed            |
| IMP-5     | downstream | Test suite                  | MockConfirmationEngine change + new tests                                 | Run full regression at each phase gate                                       | T3, T5, T15, T21 | ✅ addressed            |
| IMP-6     | lateral    | Config JSON                 | Dead sections removed, new field added                                    | Incremental changes, schema version unchanged                                | T18, T19         | ✅ addressed            |
| IMP-7     | upstream   | KataGo engine behavior      | SIDETOMOVE changes how KataGo reports winrates in all queries             | Code was designed for this; P2.4 recommended it                              | T1               | ✅ addressed            |
| IMP-8     | lateral    | Logging volume              | Comprehensive logging increases log file size                             | Log rotation already configured; per-run files scope the impact              | T7-T14           | ✅ addressed            |

## Deferred Items (Out of Scope)

| Item                                                  | Rationale                                    |
| ----------------------------------------------------- | -------------------------------------------- |
| Batch parallelism (M6)                                | Performance optimization, separate scope     |
| KataGo timeout/cancellation (S8)                      | Infrastructure concern, separate initiative  |
| No-solution-resilience Phase II (T14-T19)             | Deferred branching improvements              |
| Threshold calibration sweep (S5-G18)                  | Requires live KataGo with fixture sets       |
| Documentation deliverables (S5-G19)                   | Separate initiative                          |
| Tree-builder opponent-node winrate annotation (L1047) | Affects annotations only, not puzzle solving |

> **See also**:
>
> - [Plan](./30-plan.md) — Phases, risks, rollback
> - [Tasks](./40-tasks.md) — Full task breakdown with dependencies
> - [Charter](./00-charter.md) — Goals, non-goals, constraints
