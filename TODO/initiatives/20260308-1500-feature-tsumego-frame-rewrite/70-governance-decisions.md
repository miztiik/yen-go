# Governance Decisions: Tsumego Frame Rewrite

> **Initiative**: `20260308-1500-feature-tsumego-frame-rewrite`  
> **Last Updated**: 2026-03-08

---

## Gate 1: Charter Review

| Field           | Value                  |
| --------------- | ---------------------- |
| **Decision**    | `approve`              |
| **Status Code** | `GOV-CHARTER-APPROVED` |
| **Date**        | 2026-03-08             |
| **Unanimous**   | Yes (6/6)              |

### Member Reviews

| review_id | member           | domain              | vote    | supporting_comment                                                                                                                                                         |
| --------- | ---------------- | ------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Scope well-defined. Wrong attacker color (V1 L96) is most critical bug. AC1+AC3 directly address it. Normalize→frame→denormalize handles standard corner position concept. |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Merged algorithm is correct approach. Ko threats and `offence_to_win=10` are valuable. Charter is clean and focused.                                                       |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | Count-based fill produces strong ownership signals vs V1's 50% density. `offence_to_win` configurable is correct for model-size sensitivity.                               |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Tightly bounded scope. 11 acceptance criteria with verification methods. No BC is correct — V1 logic fundamentally flawed.                                                 |
| GV-5      | Staff Engineer A | Systems architect   | approve | Architecture compliance verified. Typed payloads consistent with codebase. Minor: status.json charter phase should be in_progress.                                         |
| GV-6      | Staff Engineer B | Pipeline engineer   | approve | Evaluation-only change, no downstream contract impact. 19 test references identified for rewrite.                                                                          |

### Handover

- **Next**: Proceed to options phase
- **Blocking items**: None

---

## Gate 2: Options Election

| Field               | Value                                |
| ------------------- | ------------------------------------ |
| **Decision**        | `approve`                            |
| **Status Code**     | `GOV-OPTIONS-APPROVED`               |
| **Date**            | 2026-03-08                           |
| **Unanimous**       | Yes (6/6)                            |
| **Selected Option** | **OPT-2: Merged KaTrain + ghostban** |

### Selection Rationale

Highest weighted score (4.8/5). Fixes all 15 V1 bugs. Best algorithm quality: combines KaTrain's proven attacker inference, normalization, and ko threats with ghostban's more principled non-edge border logic and `offence_to_win=10` (validated on goproblems.com production with b10 model). Single coherent delivery eliminates Phase-2 deprioritization risk.

### Must-Hold Constraints

| ID    | Constraint                                                                   | Source         |
| ----- | ---------------------------------------------------------------------------- | -------------- |
| MHC-1 | Entry point `apply_tsumego_frame(position, ...)` callable with existing args | Charter C4     |
| MHC-2 | `offence_to_win` configurable, default 10                                    | Charter C7, Q2 |
| MHC-3 | No new external dependencies                                                 | Charter C10    |
| MHC-4 | `remove_tsumego_frame()` preserved and functional                            | Charter C5     |
| MHC-5 | _(Recommended)_ Regression comparison V1 vs V2 on ≥5 sample puzzles          | GV-6           |

### Member Reviews

| review_id | member           | domain              | vote    | supporting_comment                                                                                                            |
| --------- | ---------------- | ------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Non-edge border critical. Wall must be attacker-colored. `offence_to_win=10` gives clear reading.                             |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Ko threats important — without them KataGo may not enter ko. Single delivery is simpler.                                      |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | bbox-based territory formula better than total-stone-count. Normalize→frame→denormalize essential.                            |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Every V1 bug degrades pipeline output. ~300-350 lines is modest for a single-file rewrite.                                    |
| GV-5      | Staff Engineer A | Systems architect   | approve | Architecture clean. `FrameConfig`/`FrameResult` good. Plan must preserve `remove_tsumego_frame` (C5).                         |
| GV-6      | Staff Engineer B | Pipeline engineer   | approve | Per-puzzle operation, no batch impact. `offence_to_win` configurable good for calibration. Regression comparison recommended. |

### Re-deliberation

- GV-5 concern (`remove_tsumego_frame` preservation) → MHC-4
- GV-6 concern (regression comparison) → MHC-5 (recommended, not blocking)
- Both resolved without escalation

### Handover

- **Next**: Draft plan (30-plan.md) + tasks (40-tasks.md) + analysis (20-analysis.md)
- **Blocking items**: None

---

## Gate 3: Plan Review

| Field           | Value                                          |
| --------------- | ---------------------------------------------- |
| **Decision**    | `approve_with_conditions`                      |
| **Status Code** | `GOV-PLAN-CONDITIONAL`                         |
| **Date**        | 2026-03-08                                     |
| **Unanimous**   | 5 approve + 1 concern (resolved via RC-1/RC-2) |

### Required Changes (all resolved)

| RC-ID | Severity | Description                                                                                                 | Resolution                                 |
| ----- | -------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| RC-1  | Medium   | Plan §1.5: `ko_type_key` is computed AFTER the call site at line 101. Pass raw `ko_type` parameter instead. | ✅ Fixed in 30-plan.md and 40-tasks.md T17 |
| RC-2  | Low      | T31 referenced `git stash` (FORBIDDEN). Use inline V1 logic for comparison.                                 | ✅ Fixed in 40-tasks.md T31                |
| RC-3  | Info     | `status.json` `analyze` phase should be `complete`.                                                         | ✅ Fixed in status.json                    |

### Member Reviews

| review_id | member           | domain              | vote            | supporting_comment                                                                                                                                                |
| --------- | ---------------- | ------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve         | Algorithm sound. Edge-proximity heuristic correct. Non-edge border correct. ko_type_key scope error is plan-text bug, not design flaw.                            |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve         | Ko threats essential. KaTrain's fixed 2-pattern approach pragmatic. Gating on ko_type correct.                                                                    |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve         | bbox territory formula superior to total-stone-count. offence_to_win=10 validated on goproblems.com b10 model. Count-based fill provides strong ownership signal. |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve         | High-leverage single-file rewrite. Task decomposition clean with testable boundaries. ko_type_key scope trivial to fix.                                           |
| GV-5      | Staff Engineer A | Systems architect   | concern→approve | Architecture solid. RC-1 factual error in plan text must be fixed before handoff. RC-2 git stash forbidden. Both easily fixable.                                  |
| GV-6      | Staff Engineer B | Pipeline engineer   | approve         | Per-puzzle ephemeral operation. TsumegoQueryBundle shape unchanged. Single-commit rollback. git stash reference must be removed (RC-2).                           |

### Handover

- **Next**: Execute plan (Plan-Executor)
- **Blocking items**: RC-1, RC-2, RC-3 — all resolved
- **Re-review**: Not requested

---

## Gate 4: Implementation Review

| Field           | Value                 |
| --------------- | --------------------- |
| **Decision**    | `approve`             |
| **Status Code** | `GOV-REVIEW-APPROVED` |
| **Date**        | 2026-03-08            |
| **Unanimous**   | Yes (6/6)             |

### Implementation Summary

- 3 files modified: `tsumego_frame.py` (rewrite), `query_builder.py` (1 line), `test_tsumego_frame.py` (rewrite) + `test_query_builder.py` (2 tests added)
- 271 tests pass, 0 failures
- 11/11 acceptance criteria met
- 5 deviations, all justified (stone-count heuristic, board-size scaling, overlap fix, offense_color wiring, MHC-5 skip)

### Member Reviews

| review_id | member           | domain              | vote    | supporting_comment                                                                                                                         |
| --------- | ---------------- | ------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Attacker inference correct for both standard corners and heavy enclosures. Non-edge border, ko threats, normalize/denormalize all sound.   |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Stone-count heuristic pragmatic improvement. Ko wiring clean. MHC-5 skip acceptable — real KataGo test is stronger evidence.               |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | Board-size-proportional scaling critical for multi-board operation. Count-based fill produces strong ownership signals.                    |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Tightly scoped rewrite. 271/271 tests pass. All deviations are improvements. Single-commit rollback available.                             |
| GV-5      | Staff Engineer A | Systems architect   | approve | Architecture compliant. Typed dataclasses, no new deps, frozenset improvement. Occupied tracking (DEV-3) prevents duplicate stone defects. |
| GV-6      | Staff Engineer B | Pipeline engineer   | approve | Per-puzzle ephemeral operation. Fast tests (61s total). V1 internal names confirmed removed.                                               |

### Handover

- **From**: Governance-Panel
- **To**: Plan-Executor
- **Next**: Proceed to closeout
- **Blocking items**: None

---

## Gate 5: Closeout Audit

| Field           | Value                   |
| --------------- | ----------------------- |
| **Decision**    | `approve`               |
| **Status Code** | `GOV-CLOSEOUT-APPROVED` |
| **Date**        | 2026-03-08              |
| **Unanimous**   | Yes (6/6)               |

### Closure Evidence

- Scope: 11/11 AC met, 4/4 required MHCs, 5 justified deviations
- Tests: 271/271 pass, 48 new tests, V1 references eliminated
- Docs: Module docstring + MIT attribution. No global docs needed.
- Governance: 5-gate chain complete. All RCs resolved and traced.

### Member Reviews

| review_id | member           | domain              | vote    | supporting_comment                                                                   |
| --------- | ---------------- | ------------------- | ------- | ------------------------------------------------------------------------------------ |
| GV-1      | Cho Chikun (9p)  | Classical tsumego   | approve | Algorithm correctness demonstrated. Stone-count heuristic handles enclosure puzzles. |
| GV-2      | Lee Sedol (9p)   | Intuitive fighter   | approve | Ko threat gating correct. MHC-5 skip justified by real KataGo integration test.      |
| GV-3      | Shin Jinseo (9p) | AI-era professional | approve | Board-size-proportional scaling essential for multi-board operation.                 |
| GV-4      | Ke Jie (9p)      | Strategic thinker   | approve | Clean end-to-end closure. No scope creep. All deviations are improvements.           |
| GV-5      | Staff Engineer A | Systems architect   | approve | Architecture compliant. Typed dataclasses, no new deps, occupied tracking.           |
| GV-6      | Staff Engineer B | Pipeline engineer   | approve | Rigorous validation: 271 tests, 6 ripple effects, all RCs traced.                    |

### Handover

- **From**: Governance-Panel
- **To**: Caller (initiative owner)
- **Next**: Set `closeout: approved`, `current_phase: closeout`
- **Blocking items**: None
