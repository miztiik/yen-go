# Clarifications — Enrichment Lab Tactical Hints & Detection Improvements

**Last Updated**: 2026-03-15

---

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | What's the primary goal? Improve existing detectors, add new capabilities, or both? | A: Improve existing / B: Add new / C: Both | **C** — Research suggests both improvements to existing detection and new capabilities (instinct classification, entropy difficulty) | C — user confirmed | ✅ resolved |
| Q2 | Should instinct classification be added for hints and teaching comments? | A: Yes / B: No / C: Research only | **A** — Governance Panel unanimous (7/7): instinct classification adds pedagogical value. Instinct names describe move INTENT (push, hane, cut) which bridges pattern recognition to positional understanding. | A — user confirmed: "improve hinting and teaching comments... identify what moves or what is a game situation" | ✅ resolved |
| Q3 | Board-sim vs KataGo signals: how should external research concepts be integrated? | A: Add board-sim detectors / B: Improve KataGo signal interpretation / C: Both | **B** — Improve how KataGo signals are interpreted. Panel (GV-3 Shin Jinseo): "KataGo's policy distribution already implicitly encodes intent. Use policy direction vectors relative to groups to infer instinct." | B — user confirmed: "understand the AI signal better" | ✅ resolved |
| Q4 | Should multi-orientation testing be added for detectors? | A: Yes / B: No | **A** — Governance Panel (6/7 A, 1 B): "A ladder in the top-left IS a ladder in the bottom-right. If a detector fails on rotation, it's fundamentally broken." Per Cho Chikun: "Non-negotiable for tactical detectors." | A — governance recommends strongly | ✅ resolved (governance) |
| Q5 | Is rank-based move quality (Top-K accuracy) useful for enrichment? | A: Yes / B: No / C: Supplementary | **C** — Governance Panel (6/7 C): "Use as supplementary quality/validation signal. Store correct_move_rank in observability. Measure correlation before weighting." Per Lee Sedol: "Some of my best moves were KataGo's #50." | C — governance recommends supplementary only | ✅ resolved (governance) |
| Q6 | What about the previous backend pipeline initiative? | A: Archive and start fresh / B: Keep paused / C: Repurpose | **A** — User redirected: "the whole intention was for using it in the puzzle enrichment lab, not in the backend pipeline." Old initiative archived. | A — user directed | ✅ resolved |
| Q7 | Should policy entropy be used as a difficulty signal? | A: Yes / B: No / C: Supplementary | **A** — Governance Panel unanimous (7/7 A): "Strongest signal in this consultation." Per Cho Chikun: "The hardest problems are those where MANY moves look plausible but only one works. This is EXACTLY what high policy entropy measures." | A — governance unanimous | ✅ resolved (governance) |
| Q8 | Should game phase taxonomy be added? | A: Yes / B: Partial / C: No | **C** — Governance Panel (6/7): "Existing detectors (fuseki, joseki, endgame, life-and-death) + YC corner already cover this. Adding a separate taxonomy is redundant." | C — governance recommends skip | ✅ resolved (governance) |
| Q9 | Is backward compatibility required for enrichment lab output? | A: Yes / B: No | **A** — AiAnalysisResult schema v9 is consumed by downstream pipeline. New signals are additive. Existing output fields must remain stable. | A — schema stability required | ✅ resolved |
| Q10 | Should hint content be level-adaptive? | A: Yes / B: No | **A** — Governance Panel unanimous: "Novice→tactical consequence, Intermediate→intent+position, Dan→reading guidance." Per Ke Jie: "Make hint content level-adaptive, not one-size-fits-all." | A — governance recommends | ✅ resolved (governance) |

---

## Key Governance Guidance (Pre-Charter Consultation)

The Governance Panel provided domain expertise before charter drafting. Key findings:

1. **Instinct classification** — Filter to tsumego-relevant instincts: push, hane, cut, descent, extend. Allow multi-instinct with tie-breaking. Config-driven templates.
2. **Hint priorities by level** — Beginner: (B) consequence + (D) position. Intermediate: (A) intent + (D) position. Dan: (C) reading guidance.
3. **Multi-orientation testing** — Priority for tactical detectors (ladder, net, snapback, ko, throw-in). Create `Position.rotate()`/`reflect()` methods. Pytest parametrize.
4. **Policy entropy** — Shannon entropy over policy distribution. ~5 lines of code. Calibrate before weighting in difficulty model.
5. **Calibration-first** — Every new signal needs golden set validation (50-100 puzzles) BEFORE production weighting.
6. **Zero new KataGo queries** — All features derive from existing `AnalysisResponse` data.
