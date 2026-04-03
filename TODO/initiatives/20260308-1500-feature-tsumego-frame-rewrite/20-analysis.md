# Analysis: Tsumego Frame Rewrite (OPT-2)

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08

---

## Planning Confidence

| Metric                    | Value                                                                  |
| ------------------------- | ---------------------------------------------------------------------- |
| Planning Confidence Score | **100**                                                                |
| Risk Level                | **low**                                                                |
| Research invoked?         | No (prior research sufficient — 63 findings from verbatim MIT sources) |

---

## 1. Cross-Artifact Consistency

| finding_id | artifact_a                               | artifact_b                                | check                                                | status  |
| ---------- | ---------------------------------------- | ----------------------------------------- | ---------------------------------------------------- | ------- |
| F1         | Charter G1 (correct implementation)      | Plan §1.4 (algorithm detail)              | Plan implements merged KaTrain+ghostban as specified | ✅ pass |
| F2         | Charter G2 (fix 15 bugs)                 | Tasks T6-T13 (core functions)             | Each V1 bug maps to a specific function replacement  | ✅ pass |
| F3         | Charter G3 (modular design)              | Plan §1.2 (data types) + §1.3 (functions) | 4 dataclasses + 11 functions, each ≤40 lines         | ✅ pass |
| F4         | Charter G4 (wire query_builder)          | Tasks T17 (caller update)                 | `ko_type` threading explicitly tasked                | ✅ pass |
| F5         | Charter G5 (test coverage)               | Tasks T18-T29 (tests)                     | 12 test tasks covering all 11 acceptance criteria    | ✅ pass |
| F6         | Charter C4 (entry point preserved)       | Plan §1.3 `apply_tsumego_frame`           | Same name, keyword args with defaults, MHC-1         | ✅ pass |
| F7         | Charter C5 (remove preserved)            | Tasks T16, T26, T32                       | Implementation + test + verification checklist       | ✅ pass |
| F8         | Charter C7 (offence_to_win configurable) | Plan §1.2 `FrameConfig.offence_to_win=10` | Parameterized, default 10, test in T27               | ✅ pass |
| F9         | Charter C10 (no new deps)                | Plan + Tasks                              | Only stdlib dataclass + existing Pydantic models     | ✅ pass |
| F10        | Options OPT-2 (non-edge border)          | Tasks T12 + Plan §1.4 Step 5              | ghostban border logic explicitly implemented         | ✅ pass |
| F11        | Options OPT-2 (ko threats)               | Tasks T13 + Plan §1.4 Step 6              | KaTrain ko patterns, gated on ko_type                | ✅ pass |
| F12        | Clarification Q-BC (no backward compat)  | Tasks T34-T35 (legacy cleanup)            | Grep for removed V1 internals, clean up              | ✅ pass |
| F13        | MHC-4 (remove_tsumego_frame preserved)   | Tasks T16, T26, T32                       | Triple-verified: implement + test + checklist gate   | ✅ pass |
| F14        | MHC-5 (regression comparison)            | Tasks T31                                 | Recommended task with V1 vs V2 comparison            | ✅ pass |

---

## 2. Coverage Map

| acceptance_criterion                  | tasks       | test_tasks  | status                             |
| ------------------------------------- | ----------- | ----------- | ---------------------------------- |
| AC1 (attacker color)                  | T6          | T19         | ✅ covered                         |
| AC2 (fill density 65-75%)             | T11         | T22         | ✅ covered                         |
| AC3 (wall = attacker color)           | T12         | T23         | ✅ covered                         |
| AC4 (border on non-edge sides)        | T9, T12     | T21, T23    | ✅ covered                         |
| AC5 (normalize→frame→denormalize)     | T7, T8, T14 | T20         | ✅ covered                         |
| AC6 (ko threats when ko_type != none) | T13         | T24         | ✅ covered                         |
| AC7 (offence_to_win configurable)     | T2, T11     | T27         | ✅ covered                         |
| AC8 (query_builder passes ko_type)    | T17         | T28         | ✅ covered                         |
| AC9 (all tests pass)                  | T30         | T30         | ✅ covered                         |
| AC10 (functions ≤40 lines)            | T6-T16      | Code review | ✅ covered (plan §1.3 line counts) |
| AC11 (documentation updated)          | T33         | —           | ✅ covered                         |

### Unmapped Tasks

| task_id | reason_not_mapped                                        | justified |
| ------- | -------------------------------------------------------- | --------- |
| T1      | Infrastructure (clean slate) — no AC, enables all others | ✅        |
| T2-T5   | Data types — no AC, but required by all functions        | ✅        |
| T18     | Test infrastructure — no AC, enables all test tasks      | ✅        |
| T29     | Backward-compat integration test — maps to MHC-1         | ✅        |
| T31     | MHC-5 regression comparison — recommended, not required  | ✅        |
| T32     | MHC-4 verification gate — checklist, not code            | ✅        |
| T34-T35 | Legacy cleanup — no AC, supports Q-BC decision           | ✅        |

---

## 3. Ripple-Effects Analysis

| impact_id | direction  | area                                                                         | risk     | mitigation                                                                                                                            | owner_task          | status       |
| --------- | ---------- | ---------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ------------ |
| RE-1      | downstream | `query_builder.py` — primary caller of `apply_tsumego_frame()`               | Low      | Keyword args with defaults preserve existing call. T17 adds `ko_type`. T28+T29 verify.                                                | T17, T28, T29       | ✅ addressed |
| RE-2      | downstream | `enrich_single.py` — log string references "tsumego_frame"                   | None     | Log string only (line 924). No code dependency. No change needed.                                                                     | —                   | ✅ addressed |
| RE-3      | downstream | `solve_position.py` — calls `prepare_tsumego_query()` which calls frame      | Low      | Indirect dependency via `query_builder.py`. `prepare_tsumego_query` signature unchanged.                                              | T17                 | ✅ addressed |
| RE-4      | downstream | `tests/test_query_builder.py` — tests `prepare_tsumego_query()`              | Low      | New integration tests T28+T29 added. Existing tests should pass since `prepare_tsumego_query` signature unchanged.                    | T28, T29            | ✅ addressed |
| RE-5      | lateral    | `tests/test_solve_position.py` — indirectly uses frame via query_builder     | Very Low | No direct frame assertions in solve tests. Frame is an implementation detail.                                                         | T30 (full test run) | ✅ addressed |
| RE-6      | lateral    | `tests/test_enrich_single.py` — indirectly uses frame                        | Very Low | Same as RE-5. No direct frame assertions.                                                                                             | T30                 | ✅ addressed |
| RE-7      | upstream   | `models/position.py` — provides Position, Stone, Color                       | None     | No changes to upstream models. Read-only dependency.                                                                                  | —                   | ✅ addressed |
| RE-8      | upstream   | `config.py` / `EnrichmentConfig`                                             | None     | Not modified. Frame uses its own `FrameConfig` dataclass.                                                                             | —                   | ✅ addressed |
| RE-9      | lateral    | Other analyzers (`estimate_difficulty.py`, `validate_correct_move.py`, etc.) | None     | No dependency on frame module. Verified by grep: only `query_builder.py` and `enrich_single.py` reference `tsumego_frame`.            | T34                 | ✅ addressed |
| RE-10     | lateral    | `backend/puzzle_manager/`                                                    | None     | Architecture rule: `tools/` does NOT import from `backend/`, and `backend/` does not import from `tools/`. Verified by C9 constraint. | —                   | ✅ addressed |

---

## 4. Severity Findings

| finding_id | severity | description                                                                                        | resolution                                 |
| ---------- | -------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| F-SEV-1    | Info     | `status.json` charter phase was `not_started` when reviewed — cosmetic inconsistency noted by GV-5 | Fixed: now `approved`                      |
| F-SEV-2    | Info     | `remove_tsumego_frame` not mentioned in options doc — caught by GV-5                               | Added as MHC-4, implemented in T16/T26/T32 |
| F-SEV-3    | Info     | Regression comparison is recommended but optional (MHC-5)                                          | T31 is marked recommended. Not blocking.   |

No critical or high-severity findings. All medium/info findings resolved.

---

## 5. Task Dependency Validation

| check                                  | status                                                                                             |
| -------------------------------------- | -------------------------------------------------------------------------------------------------- |
| No circular dependencies               | ✅ — DAG verified (T1 → T2-T5 → T6 → T7-T13 → T14 → T15 → T17 → T18 → T19-T29 → T30 → T34-T35)     |
| All [P] tasks have shared predecessor  | ✅ — Each parallel group shares a common dependency                                                |
| Critical path identified               | ✅ — T1→T2→T6→T10→T11→T14→T15→T17→T18→T30 (10 sequential steps)                                    |
| No task references files outside scope | ✅ — Only `tsumego_frame.py`, `query_builder.py`, `test_tsumego_frame.py`, `test_query_builder.py` |
| Legacy removal tasks included          | ✅ — T34 (grep for removed names), T35 (clean up test fixtures)                                    |

---

## 6. Summary

- **Planning Confidence**: 100 (low risk)
- **Consistency findings**: 14 cross-artifact checks, all pass
- **Coverage**: 11/11 acceptance criteria mapped to tasks and tests
- **Ripple effects**: 10 impacts analyzed, all addressed or no-risk
- **Severity findings**: 3 info-level, 0 critical/high/medium
- **Task graph**: 35 tasks, no circular dependencies, 6 parallel groups
- **Ready for governance plan review**: Yes
