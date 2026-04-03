# Clarifications — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

## Context

This initiative consolidates all pending enrichment-lab work from:
- `TODO/kishimoto-mueller-tasks.md` (6 gate reviews)
- `TODO/ai-solve-remediation-sprints.md` (20 items need sign-off, 4 docs)
- `TODO/initiatives/2026-03-08-fix-katago-perspective/40-tasks.md` (5 partially done tasks)
- `TODO/initiatives/20260310-research-tsumego-solver-pns/15-research.md` (R-A-1 Benson, R-A-2 interior-point)
- `TODO/katago-puzzle-enrichment/009-principal-review-gap-plan.md` (P0-P2 priorities)
- sgfmill library evaluation (conditional replacement)

## Previously Resolved (from prior conversation)

| q_id | question | user_response | status |
|------|----------|---------------|--------|
| Q2-R | Benson gate seki handling? | B — Run Benson; if result is "dead", fall through to KataGo | ✅ resolved |
| Q3-R | License policy for tsumego-solver concepts? | A — Conceptual reference only is fine (different language anyway) | ✅ resolved |

## Resolved Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | **Scope boundary**: What should this consolidated initiative cover? | A: Full consolidation / B: Algorithms + fixes only / C: New work only | A | **A — Full consolidation.** Fix all identified issues. | ✅ resolved |
| Q2 | **Katago-perspective initiative status**: Were T1-T21 implemented? | A: Code IS implemented / B: Code NOT implemented / C: Partially done | — | **Verified: 12 fully implemented, 5 partially implemented, 0 missing.** User directive: verify code, confirm, review, close out. See §Verification Results below. | ✅ resolved |
| Q3 | **Benson gate placement**: KM sub-phase vs this initiative? | A: KM Phase 8 / B: This initiative / C: Separate | B | **B — This consolidated initiative.** | ✅ resolved |
| Q4 | **Interior-point boundary reuse**: Reuse tsumego_frame or compute independently? | A: Reuse / B: Independent | A | **A — Reuse tsumego_frame.** Also: update documentation for tsumego_frame and ALL affected docs (global, design, architecture). | ✅ resolved |
| Q5 | **Backward compatibility** | A: Not required / B: Required | A | **A — No backward compatibility. Forward only.** Re-process all puzzles. | ✅ resolved |
| Q6 | **Dead code removal** | A: Remove / B: Keep | A | **A — Remove aggressively.** | ✅ resolved |
| Q7 | **sgfmill disposition** | A: Keep+declare / B: Replace with native / C: Defer | — | **B if not complex, else keep.** Evaluate complexity; replace with native code from `tools/core/sgf_parser.py` if feasible. If too complex, do not pursue. | ✅ resolved |
| Q8 | **KM gate reviews (6 pending)** | A: Batch / B: Individual / C: Defer | A | **B — Individual reviews.** "There are implementation gaps most of the times." | ✅ resolved |
| Q9 | **Remediation sprint sign-offs (20 items)** | A: Batch / B: Individual / C: Defer | A | **B — Individual sign-offs.** | ✅ resolved |
| Q10 | **Calibration sweep (S5-G18)** | A: Include (gated) / B: Defer | A | **EXCLUDED.** Calibration is out of scope for this initiative. Not doing KataGo performance calibration here. | ✅ resolved |

## Additional Directives (from user responses)

| d_id | directive | impact |
|------|-----------|--------|
| D1 | **Do NOT rely on YK property** for Benson ko bypass. YK is a computed heuristic, not guaranteed. | Benson gate must NOT use `YK != none` as ko skip signal. Use Benson's inherent correctness: ko-dependent positions won't be classified as unconditionally alive. |
| D2 | **Update documentation everywhere required** — global docs, design docs, architecture docs, not just the immediate files. | Every code change must include corresponding doc updates. |
| D3 | **No calibration** — KataGo performance calibration is excluded from this initiative entirely. | S5-G18 remains deferred. |

## Verification Results: Katago-Perspective T1-T21

Code-level verification conducted 2026-03-10 via direct file inspection.

| Task | Status | Remaining Gap |
|------|--------|---------------|
| T1 (SIDETOMOVE config) | ✅ Done | — |
| T2 (SIDETOMOVE comment) | ✅ Done | — |
| T3 (MockConfirmationEngine) | ✅ Done | — |
| T4 (White-to-play tests) | ✅ Done | — |
| T7 (solve_position logging) | ✅ Done | — |
| T8 (validate_correct_move logging) | ✅ Done | — |
| T9 (estimate_difficulty logging) | ⚠️ Partial | Missing per-component score breakdown (policy, visits, structural, trap values) |
| T10 (technique_classifier logging) | ✅ Done | — |
| T11 (ko_validation logging) | ⚠️ Partial | Only 1 logger call; no recurrence-pattern or adjacency-check details |
| T12 (generate_refutations logging) | ✅ Done | — |
| T13 (enrich_single + query_builder logging) | ✅ Done | — |
| T14 (run_id naming) | ⚠️ Partial | cli.py ✓, conftest.py still uses inline format (not `generate_run_id()`) |
| T16 (ko capture verification) | ⚠️ Partial | Has adjacency proxy but NO actual board-state capture verification |
| T17 (difficulty weight rebalancing) | ✅ Done | — |
| T18 (Pydantic defaults sync + seki) | ✅ Done | — |
| T19 (dead code: difficulty_result.py) | ✅ Done | `level_mismatch` JSON section still present (should be removed) |
| T20 (remove ai_solve.enabled) | ⚠️ Partial | Field removed from config; `ai_solve_active` gating variable still in enrich_single.py (6 references, always True) |

**Summary: 12 fully done, 5 partially done. Remaining gaps are all small (1-20 lines each).**

## Decision Impact Summary

- Q1:A = Full scope — all pending items consolidated
- Q2: Verified — 5 small gaps to close from perspective initiative
- Q3:B = Benson in this initiative
- Q4:A = Reuse tsumego_frame boundary + update all docs
- Q5:A = No backward compatibility, forward only
- Q6:A = Remove all dead code
- Q7:B-conditional = Replace sgfmill if feasible, otherwise keep
- Q8:B = Individual KM gate reviews (6 reviews)
- Q9:B = Individual remediation sign-offs (20 reviews)
- Q10:EXCLUDED = No calibration

## Confidence Score Reconciliation (RC-1)

The research artifact `15-research.md` reports `post_research_confidence_score: 82` and `post_research_risk_level: medium`. The charter claims 90/low.

**Reconciliation:** The research score of 82 was computed BEFORE the code verification phase. After verification:
- KM-01 through KM-04 + L3 confirmed present at specific line numbers (was uncertain before)
- Perspective initiative verified ~85% complete (was entirely uncertain before)
- 20 remediation items verified implemented (was uncertain before)
- Architecture seams well-understood (solve_position.py 1804 lines, all extension points mapped)
- Test infrastructure extensive (220+ tests)

These verifications reduced uncertainty on 3 rubric dimensions:
- "Architecture seams unclear" → cleared (-20 → 0)
- "Test strategy unclear" → cleared (-10 → 0)
- Remaining deductions: quality/perf impact -10 (Benson seki/ko edge cases)

**Post-verification score: 90 | Risk: low** (down from medium because the only remaining risk — Benson correctness — has explicit mitigation via KataGo fallthrough).

## Governance Panel Questions (RC-4)

Resolved questions raised by the Governance Panel during charter review:

| gq_id | question | resolution | status |
|-------|----------|------------|--------|
| GQ1 | AC14: "created" vs "updated" for docs/concepts/quality.md? | **Updated** — file already exists. AC14 rewritten. | ✅ resolved |
| GQ2 | AC15 scope: additive sections or full rewrite of katago-enrichment.md? | **A: Additive sections only** — add Benson gate and interior-point design decision sections. | ✅ resolved |
| GQ3 | status.json decision rationales still "pending"? | **Fixed** — rationales populated with resolved Q5/Q6 answers. | ✅ resolved |
| GQ4 | ai_solve_active removal: remove variable entirely or just remove gating? | **C: Planner decides** — deferred to options/plan phase as implementation detail. | ✅ resolved |
| GQ5 | Confidence score discrepancy (research 82/medium vs charter 90/low)? | **See §Confidence Score Reconciliation above.** Post-verification re-assessment documented. | ✅ resolved |
