# Analysis: enrich_single.py SRP Decomposition

**Last Updated:** 2026-03-07  
**Planning Confidence Score:** 72  
**Risk Level:** Medium  
**Research Invoked:** Yes (Feature-Researcher)

---

## 1. Consistency Checks

| finding_id | severity | area          | finding                                                                                                                                            | resolution                               |
| ---------- | -------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| F1         | LOW      | Terminology   | Charter says "functional groups" (G-META, G-RESULT, etc.) but plan uses "phases" (P1–P4). No conflict — charter was pre-research, plan supersedes. | ✅ No action needed                      |
| F2         | LOW      | Task coverage | T4/T5/T6 are marked parallel but depend on T2. Correct — they depend on T2 (shared module exists) but are independent of each other.               | ✅ Correctly specified                   |
| F3         | MEDIUM   | Must-hold     | MH-4 requires "one commit per phase" but T4/T5/T6 could generate 3 sub-commits.                                                                    | ✅ Squash into single phase commit at T8 |
| F4         | LOW      | Plan vs tasks | Plan says Phase 3 extracts functions "within enrich_single.py" — tasks confirm this. No new file created for code paths. Consistent.               | ✅ Aligned                               |

---

## 2. Coverage Map (Charter Goals → Tasks)

| goal_id | goal                         | task_ids                                                           | covered                                                 |
| ------- | ---------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------- |
| CG-1    | Enable independent iteration | T2, T10, T13–T16                                                   | ✅ Config, state, each code path independently editable |
| CG-2    | SRP compliance per module    | T2 (config=1 resp), T10 (state=1 resp), T13–T15 (path=1 resp each) | ✅                                                      |
| CG-3    | Reduce cognitive load        | T16 (orchestrator → 200 lines)                                     | ✅                                                      |
| CG-4    | Preserve all behavior        | T8, T12, T18, T21 (validation gates each phase)                    | ✅                                                      |

---

## 3. Must-Hold Constraint Traceability

| mh_id | constraint                               | task_id           | verified_by                                        |
| ----- | ---------------------------------------- | ----------------- | -------------------------------------------------- |
| MH-1  | `clear_config_caches()` exposed          | T2                | T1 (test exists before implementation)             |
| MH-2  | Path resolution test in Phase 1          | T1                | T1 explicitly requires path resolution test        |
| MH-3  | `@dataclass` for state carrier           | T10               | T9 (test enforces `@dataclass` usage)              |
| MH-4  | Each phase independently deployable      | T8, T12, T18, T21 | Each is a validation gate requiring all tests pass |
| MH-5  | `ai_solve_failed` fall-through preserved | T11, T14          | T9 (test for fall-through), T17 (integration test) |
| MH-6  | Zero functional changes                  | T8, T12, T18, T21 | Test oracle at each phase boundary                 |

---

## 4. Unmapped Tasks

| task_id | purpose                            | mapped_to_goal                                           |
| ------- | ---------------------------------- | -------------------------------------------------------- |
| T7      | Test import redirect               | CG-4 (preserve behavior)                                 |
| T17     | New unit tests for extracted paths | CG-1/CG-2 (enable independent iteration via testability) |
| T20     | Test for moved `uncrop_response`   | CG-4 (preserve behavior)                                 |

All tasks mapped. No orphan tasks.

---

## 5. Ripple-Effects Analysis

| impact_id | direction  | area                                                                    | risk                                            | mitigation                            | owner_task | status       |
| --------- | ---------- | ----------------------------------------------------------------------- | ----------------------------------------------- | ------------------------------------- | ---------- | ------------ |
| RE-1      | downstream | `cli.py` imports `enrich_single_puzzle`                                 | None — public API unchanged (thin façade)       | N/A                                   | T3         | ✅ addressed |
| RE-2      | downstream | `gui/bridge.py` imports `enrich_single_puzzle`                          | None — public API unchanged                     | N/A                                   | T3         | ✅ addressed |
| RE-3      | downstream | `scripts/run_calibration.py` imports `enrich_single_puzzle`             | None — public API unchanged                     | N/A                                   | T3         | ✅ addressed |
| RE-4      | lateral    | `test_enrich_single.py` imports private symbols                         | High — `ImportError` if not updated             | T7 redirects imports                  | T7         | ✅ addressed |
| RE-5      | lateral    | `test_enrich_single.py` `autouse` fixture resets `_TAG_SLUG_TO_ID`      | High — fixture breaks if cache moves            | T7 updates to `clear_config_caches()` | T7         | ✅ addressed |
| RE-6      | upstream   | `estimate_difficulty.py` owns its own level loader                      | Medium — removal may break if signature differs | T4 verifies function compatibility    | T4         | ✅ addressed |
| RE-7      | upstream   | `sgf_enricher.py` owns its own level loader                             | Medium — same as RE-6                           | T5 verifies                           | T5         | ✅ addressed |
| RE-8      | upstream   | `validate_correct_move.py` tag loader                                   | Medium — different return type possible         | T6 verifies type compatibility        | T6         | ✅ addressed |
| RE-9      | lateral    | `query_builder.py` does not currently import `MoveAnalysis`             | Low — need to add import                        | T19 adds import                       | T19        | ✅ addressed |
| RE-10     | lateral    | `conftest.py` may have shared fixtures that interact with module caches | Low — check and update if needed                | T7 audit                              | T7         | ✅ addressed |

---

## 6. Constitution/Project Guideline Compliance

| check_id | guideline                                       | compliance | notes                                                                                                            |
| -------- | ----------------------------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------- |
| CC-1     | `tools/` must NOT import from `backend/`        | ✅         | No backend imports introduced                                                                                    |
| CC-2     | "Delete, don't deprecate" dead code policy      | ✅         | Old code removed at each phase (T3, T4–T6, T11, T13–T15, T19)                                                    |
| CC-3     | Test-first (Red-Green-Refactor)                 | ✅         | T1/T9 write tests before implementation (T2/T10)                                                                 |
| CC-4     | No new external dependencies                    | ✅         | Only stdlib `dataclasses` used                                                                                   |
| CC-5     | Correction level compliance                     | ✅         | Level 3 declared (2-3+ files, logic restructuring) — matches 6-file scope                                        |
| CC-6     | Documentation updates for architectural changes | ⚠️         | May need `README.md` update for new module (`config_lookup.py`). Not a blocker — can be added in Phase 1 commit. |
| CC-7     | SOLID/DRY/KISS/YAGNI                            | ✅         | Mapped in plan. No over-engineering.                                                                             |

---

## 7. Findings Summary

| Severity | Count | Details                                                                                             |
| -------- | ----- | --------------------------------------------------------------------------------------------------- |
| CRITICAL | 0     | —                                                                                                   |
| HIGH     | 0     | —                                                                                                   |
| MEDIUM   | 1     | F3: Sub-commits within phase should be squashed                                                     |
| LOW      | 3     | F1: Terminology evolution (expected). F2: Parallel dep correctly specified. F4: Plan/tasks aligned. |

**Overall assessment:** Plan is consistent, complete, and governance-compliant. All must-hold constraints have task-level traceability. All ripple effects are identified and mitigated. No critical or high findings.

> **See also:**
>
> - [Plan](./30-plan.md) — Phase details
> - [Tasks](./40-tasks.md) — Task breakdown
> - [Governance](./70-governance-decisions.md) — Must-hold constraints
> - [Research](./15-research.md) — Evidence base
