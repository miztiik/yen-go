# Clarifications — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Round 1

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Fixture directory structure: (A) Keep current names, add new alongside, (B) Can rename/delete freely, update imports | A / B | B — fixtures are internal test infra | **B** — Can rename/delete, update test imports | ✅ resolved |
| Q2 | Benchmark integration: (A) Best-per-technique into benchmark, surplus elsewhere, (B) Keep parallel, (C) Replace benchmark wholesale | A / B / C | A — benchmark is gold copy | **A with extension** — One best per technique in benchmark; extras in new "extended-benchmark" directory | ✅ resolved |
| Q3 | Calibration depth: (A) Technique tags only, (B) Tags + correct move, (C) Tags + difficulty, (D) Full pipeline | A / B / C / D | D — full pipeline validation | **D** — Full pipeline: correct move, wrong moves, difficulty, technique tags, teaching comments | ✅ resolved |
| Q4 | Test execution mode: (A) Mocked engine (fast), (B) Live KataGo (slow but real), (C) Both tiers | A / B / C | C — both tiers | **B** — LIVE KataGo only. Re-read README/AGENTS to understand what we're calibrating. Define it. | ✅ resolved |
| Q5 | Source priority for replacements | goproblems / ogs / kisvadim / tsumegodragon / All | All from go problems first | **All external sources**, start with goproblems, ogs, tsumegodragon, kisvadim | ✅ resolved |
| Q6 | Backward compatibility: preserve old fixture paths/test imports? | A: preserve / B: break freely | B — internal test infra only | **B** (implied by Q1:B) — No backward compat, remove old fixtures | ✅ resolved |
| Q7 | Target fixture pass rate against quality criteria? | 85% / 95% / 100% | 95% | TBD — user wants criteria defined first, then target emerges | ✅ resolved (deferred to criteria definition) |

## Key User Directives (Verbatim)

1. **"Don't fix SGF bugs — find replacements from external-sources instead."**
2. **"Benchmark is gold copy — don't overwrite. Can extend."**
3. **"Domain experts (Cho Chikun governance panel) should arbitrate best puzzle selection."**
4. **"Need to structurally define + measure calibration quality criteria."**
5. **"Need Python test cases that run through KataGo (LIVE)."**
6. **"Stage 1+3 converged: find from external sources, don't fix broken ones."**
7. **"Perhaps you want to use a custom agent for a planning feature, feature planner, so that we can structurally proceed through this."**

## Backward Compatibility Decision

**Question asked**: "Is backward compatibility required, and should old code be removed?"
**Answer**: No backward compatibility required. Old fixtures with structural bugs (7 REMOVE, 1 REPLACE per audit) should be deleted and replaced with sourced alternatives. Test imports should be updated accordingly.

> **See also**:
> - [Research: External Sources Inventory](../../20260322-research-external-sources-fixture-sourcing/15-research.md)
> - [Audit: Technique Fixture Audit](../../../../tools/puzzle-enrichment-lab/tests/fixtures/TECHNIQUE_FIXTURE_AUDIT.md)
