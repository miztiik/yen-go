# Governance Decisions — KataGo Winrate Perspective Fix

Last Updated: 2026-03-08

## Gate 1: Options Election

| Field           | Value                    |
| --------------- | ------------------------ |
| Date            | 2026-03-08               |
| Decision        | **approve**              |
| Status Code     | **GOV-OPTIONS-APPROVED** |
| Unanimous       | Yes (7/7)                |
| Selected Option | OPT-1: Config-First Fix  |

### Panel Votes

| review_id | member                     | domain                      | vote    |
| --------- | -------------------------- | --------------------------- | ------- |
| GV-1      | Cho Chikun 9p              | Classical tsumego authority | approve |
| GV-2      | Lee Sedol 9p               | Intuitive fighter           | approve |
| GV-3      | Shin Jinseo 9p             | AI-era professional         | approve |
| GV-4      | Ke Jie 9p                  | Strategic thinker           | approve |
| GV-5      | Principal Staff Engineer A | Systems architect           | approve |
| GV-6      | Principal Staff Engineer B | Data pipeline engineer      | approve |
| GV-7      | Principal Staff Engineer C | Purist KISS/DRY/SOLID       | approve |

### Selection Rationale

Code was written for SIDETOMOVE across all 8 analyzer modules (23+ sites). The config mismatch is the sole root cause. OPT-1 fixes the perspective bug with 1 config line and 0 code changes. P2.4 in consolidated review already recommended this exact change.

### Must-Hold Constraints

1. Both `tsumego_analysis.cfg` AND `analysis_example.cfg` must be updated to SIDETOMOVE
2. `generate_refutations.py` L214 must be fixed independently (broken under any mode)
3. `normalize_winrate()` must NOT be deleted — actively used at L242
4. Plan must define independent execution phases so G10/G11 cannot block G1-G9
5. White-to-play parametrized tests are mandatory (AC3)

### Panel Clarifications Resolved

- `normalize_winrate()`: KEEP — used at L242 for confirmation queries
- `analysis_example.cfg`: Update both config files to prevent regression via fallback
- Tree-builder opponent-node issue (L1047): DEFER — affects annotations only, not puzzle-solving logic

## Gate 2: Plan Review

| Field       | Value                                |
| ----------- | ------------------------------------ |
| Date        | 2026-03-08                           |
| Decision    | **approve** (after 1 revision round) |
| Status Code | **GOV-PLAN-APPROVED**                |
| Unanimous   | Yes (7/7)                            |

### Initial Review: GOV-PLAN-REVISE

4 blocking issues identified:

- RC-1 (CRITICAL): Charter G2 contradicted research — L214 is correct under SIDETOMOVE, not broken
- RC-2 (HIGH): T17 weight specification contradicted between plan and tasks
- RC-3 (HIGH): T17→T18 missing dependency creating desync risk
- RC-4 (MEDIUM): status.json stale fields (confidence, risk, rationale)

4 non-blocking improvements: RC-5 (T18 stale ref), RC-6 (T7-T13 format over-spec), RC-7 (T6 manual), RC-8 (IMP-1 deferral)

### Re-Review: GOV-PLAN-APPROVED

All 8 RCs resolved and verified. Cross-artifact consistency clean. Zero unmapped goals/ACs/tasks. KISS/DRY/SOLID/YAGNI compliant.

### Key Decisions

1. L214 is CORRECT under SIDETOMOVE — document with comment, do NOT change code
2. Difficulty weights: constraint-based (policy+visits < 40%, structural > 35%), 15/15/25/45 provisional
3. T6 (re-run puzzle) is manual validation, does not gate Phase 2
4. IMP-1 (re-enrichment of collections) is post-initiative
5. T7-T13: log WHAT decisions, not HOW (executor chooses format)

### Handover

Execute Phase 1 first (T1-T6). Regression gate at T5. Phase 2 (T7-T15) can start after T5. Phase 3 (T16-T21) can overlap with Phase 2 except T18 depends on T17.

## Gate 3: Implementation Review

| Field       | Value                                |
| ----------- | ------------------------------------ |
| Date        | 2026-03-08                           |
| Decision    | **approve** (after 1 revision round) |
| Status Code | **GOV-REVIEW-APPROVED**              |
| Unanimous   | Yes (7/7)                            |

### Initial Review: GOV-REVIEW-REVISE

7 required changes identified:

- RC-1 (HIGH): Missing `50-execution-log.md`
- RC-2 (HIGH): Missing `60-validation-report.md`
- RC-3 (HIGH): Stale `status.json` phase state
- RC-4 (MEDIUM): Ghost `AiSolveConfig(enabled=True)` parameter
- RC-5 (MEDIUM): Ko adjacency uses Chebyshev (should be Manhattan)
- RC-6 (MEDIUM): Duplicate `_status_from_classification` call (DRY violation)
- RC-7 (LOW): Stale JSON descriptions don't match 15/15/25/45 weights

### Re-Review: GOV-REVIEW-APPROVED

All 7 RCs resolved and verified. Key fixes:

- Manhattan distance for Go capture adjacency (orthogonal only)
- Single `_status_from_classification` call with result reused
- Ghost parameter removed
- 3 governance artifacts created
- JSON descriptions match actual weight values

### Deferred Items

- AC10/T6: Manual KataGo validation (requires live engine)
- IMP-1: Re-enrichment of previously processed collections

> **See also**:
>
> - [Execution Log](./50-execution-log.md) — Per-task evidence
> - [Validation Report](./60-validation-report.md) — AC verification + ripple effects
