# Clarifications — Enrichment Lab V2

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`
**Last Updated**: 2026-03-14

---

## Round 1: Pre-Captured Decisions (from user request)

These decisions were explicitly stated by the user and do not need further clarification:

| q_id | question | user_response | status |
|------|----------|---------------|--------|
| Q0A | Is backward compatibility required? | **No** — "we are willing to throw away the old code" | ✅ resolved |
| Q0B | Should old code be removed? | **Yes** — "we can refactor everything and anything in the puzzle enrichment lab" | ✅ resolved |
| Q0C | Should board cropping be removed? | **Yes** — "we can stop using the cropping... completely avoid resizing the region and then adding a frame" | ✅ resolved |
| Q0D | What replaces cropping? | **Region-of-interest via ownership/entropy** — "use the region of interest or board region... using entropy... force KataGo to choose that area" | ✅ resolved |
| Q0E | Is this for game-play or enrichment? | **Enrichment only** — "all of this is not for game playing... this is for enriching the puzzles" | ✅ resolved |
| Q0F | Primary enrichment focus? | **Correct move validation + refutation generation** — "strong focus of identifying whether the move is correct... if there are no wrong moves, we have to add refutations" | ✅ resolved |
| Q0G | Should the pipeline stages be streamlined? | **Yes** — "if there is an opportunity to streamline it... do that" | ✅ resolved |
| Q0H | Should we learn from Lizgoban/KaTrain? | **Yes** — "take some of the good things that are there here in Lizgoban and KaTrain and improve our puzzle enrichment lab" | ✅ resolved |

---

## Round 2: Blocking Clarification Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | "Techniques not working" — failure mode? | A: Inaccurate tags / B: Doesn't run / C: Some work, some missing | **C** | C — Some detectors exist (6 of 28), most missing. Existing ones PV-based and fragile. User wants ALL techniques detectable. | ✅ resolved |
| Q2 | "Refutations not working" — failure mode? | A: None generated / B: Not convincing / C: Don't persist | **A+B combo** | A+B — Sometimes not generated, sometimes not convincing. Cascading failure: wrong bounding box → strict config → low visit budget. Stage works mechanically but quality depends on visits + candidate selection. | ✅ resolved |
| Q3 | Frame on small boards — approach? | A: allowMoves only / B: Fix GP frame / C: Entropy-ROI replaces both / D: Keep frame + entropy in separate modules | **D** | D — Remove cropping completely. Keep GP frame in its own file. Add entropy/ROI in a SEPARATE new file. Modular/SRP — each feature swappable independently. DRY/SOLID. | ✅ resolved |
| Q4 | HumanSL model availability? | A: Yes / B: Can download / C: Not sure / D: Just profile? | **Defer + feature-gate** | Research: requires separate b18 model file + humanSLProfile query param. Feature-gate behind model availability. Defer to stretch goal. | ✅ resolved |
| Q5 | Pipeline streamlining approach? | A: Keep stages, improve / B: Collapse / C: Rewrite | **A modified** | Keep StageRunner pattern. Reimagine stages: fix bugs (unframed refutations, double-parsing, solve-paths outside StageRunner). Add granular stages where needed. Remove unnecessary complexity. | ✅ resolved |
| Q6 | KataGo visit strategy? | A: Single / B: Tiered / C: Adaptive | **B with higher tiers** | 200/2000 not working. New tiers: T0=50 (policy), T1=500 (standard), T2=2000 (deep), T3=5000 (referee). GoProblems achieves good results with b10 at 500-1000 visits. Better escalation implementation. | ✅ resolved |
| Q7 | Invalid frames? | A: Skip / B: Retry / C: Fallback | **C — entropy fallback** | Graceful degradation: if frame fails → fall back to entropy + ROI + allowMoves. Never skip puzzles. Degrade enrichment quality level gracefully. | ✅ resolved |
| Q8 | Ladder detection approach? | A: Clean-room port / B: Improve PV / C: Hybrid | **C** | Follow Lizgoban's pattern-based algo (clean-room, not GPL code) + PV confirmation for confidence. Board-state for accuracy + PV for verification. | ✅ resolved |
| Q9 | Batch size / concurrency? | A: 1-10 / B: 10-100 / C: 1000+ / D: All | **One file at a time** | Production is always one file at a time. Optimize for single-file throughput. Browser + CLI entry points but same execution path. No batch parallelism needed. | ✅ resolved |

---

## Decision Summary

| Decision | Value | Source |
|----------|-------|--------|
| Backward compatibility | **Not required** | Q0A (user explicit) |
| Remove old code | **Yes** | Q0B (user explicit) |
| Remove board cropping | **Yes, completely** | Q0C (user explicit) |
| Replace with ROI/entropy | **Yes, in separate module** | Q0D + Q3:D (user explicit) |
| Keep GP frame | **Yes, in its own file** | Q3:D (user explicit) |
| Enrichment focus (not game-play) | **Yes** | Q0E (user explicit) |
| Primary focus: correct move + refutations | **Yes** | Q0F (user explicit) |
| Streamline pipeline | **Yes, keep StageRunner, reimagine stages** | Q0G + Q5 |
| Learn from Lizgoban/KaTrain | **Yes** | Q0H (user explicit) |
| Visit tiers | **T0=50, T1=500, T2=2000, T3=5000** | Q6 |
| Technique detection | **All 28 tags detectable** | Q1:C (user explicit) |
| HumanSL | **Feature-gated, deferred** | Q4 |
| Single file throughput | **Optimized** | Q9 |
| SRP / modular design | **Enforced — each feature in separate file** | Q3:D (user explicit) |
