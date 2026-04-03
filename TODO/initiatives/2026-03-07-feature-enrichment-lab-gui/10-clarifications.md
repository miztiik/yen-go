# Clarifications — Enrichment Lab GUI

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Last Updated:** 2026-03-07

---

## Confirmed Facts from Research

1. **Enrichment pipeline workflow** (confirmed from `enrich_single.py`):

   ```
   Step 1: Parse SGF → extract metadata (puzzle_id, tags, corner, move_order, ko_type)
   Step 2: Extract correct first move + solution tree (or AI-Solve if position-only)
   Step 3: Build analysis query (apply tsumego frame + tight-board crop)
   Step 4: Run KataGo single-engine analysis (async subprocess)
   Step 4b: Back-translate cropped coordinates to original board
   Step 5: Validate correct move (tag-aware dispatch: L&D, ko, seki, tactical, etc.)
   Step 5a: Deep solution tree validation (multi-move depth check)
   Step 5.5: Extract curated wrong branches + compute nearby moves
   Step 6: Generate wrong-move refutations (with escalation if too few found)
   Step 7: Estimate difficulty (structural formula from KataGo signals)
   Step 8: Assemble AiAnalysisResult (ac_level, goal inference, etc.)
   Step 9: Teaching enrichment (technique classification, comments, hints)
   ```

2. **Existing assets**:
   - FastAPI, uvicorn, pydantic already in `requirements.txt`
   - BesoGo viewer already in `tools/sgf-viewer-besogo/` (MIT, pure HTML+JS)
   - Pipeline is fully async (`async def enrich_single_puzzle()`)
   - All outputs are Pydantic v2 models with `.model_dump_json()`
   - yen-go-sensei is incomplete and architecturally incompatible (browser-side TF.js engine)

3. **Backward compatibility**: Not applicable — this is a new additive tool. No existing code to remove.

---

## Clarification Questions

| q_id | question                                                                        | options                                                                                                                       | recommended | user_response                                                                                                                                                                                                                                                                 | status                              |
| ---- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Q1   | Is KataGo **ownership heatmap** visualization required for the initial version? | A: Yes — colored dots on board showing KataGo territory estimation / B: No — board stones + moves only for now, heatmap later | B           | A — "180 lines is not a big deal. Write it as a module that we can import. Heatmap needed."                                                                                                                                                                                   | ✅ resolved                         |
| Q2   | **Input mode**: How should SGF reach the GUI?                                   | A: CLI flag only / B: Browser paste/upload / C: Both                                                                          | C           | C — Both CLI flag + browser paste/upload                                                                                                                                                                                                                                      | ✅ resolved                         |
| Q3   | **Batch support**: Should the GUI handle a queue of multiple puzzles?           | A: Single puzzle only / B: Queue view                                                                                         | A           | A — "If it works for 1, it will work for N" — start single                                                                                                                                                                                                                    | ✅ resolved                         |
| Q4   | **Board rendering fidelity**: What level of board visual quality is acceptable? | A: BesoGo / B: Custom canvas / C: BesoGo now, upgrade later                                                                   | C           | **More research requested** — Investigate reusing web-katrain React components (GoBoard, MoveTree, ScoreWinrateGraph, StatusBar, BottomControlBar, etc.) from `tools/yen-go-sensei/` or upstream `Sir-Teo/web-katrain`. "There's a lot of UI elements available in the code." | ✅ resolved (see Q4-research below) |
| Q5   | **Stage visualization**: What should each pipeline step show in the GUI?        | A: Simple log / B: Rich panels per stage / C: Log + board updates                                                             | C           | B — Rich visual pipeline bar at top of board. Stages shown left-to-right, visually indicating which stage we're in. Nice UX element.                                                                                                                                          | ✅ resolved                         |
| Q6   | **Where should this tool live in the repo?**                                    | A: Inside `tools/puzzle-enrichment-lab/` / B: New standalone / C: Extend besogo                                               | A           | A — Inside `tools/puzzle-enrichment-lab/` in a subfolder with a nice name (e.g., `gui/` or `engine-gui/`). Lightweight toggle — engine works without GUI. This can serve as debug mode for future pipeline integration.                                                       | ✅ resolved                         |
| Q7   | **Is backward compatibility required, and should old code be removed?**         | A: N/A (new feature) / B: Must preserve CLI                                                                                   | A           | A — Additive feature. Do not change CLI options. Ask before modifying anything. This is throwaway-friendly code that can be removed later.                                                                                                                                    | ✅ resolved                         |
| Q8   | **Solution/refutation tree**: Should the GUI show the tree structure?           | A: Board only / B: Board + tree / C: Board + tree + navigation                                                                | C           | **More research requested** — Must be clickable, navigatable. Investigate whether to use BesoGo tree panel or web-katrain's MoveTree component.                                                                                                                               | ✅ resolved (see Q4-research below) |

---

## Round 1 Summary

The core decision space is:

1. **Simplicity** — FastAPI + BesoGo + SSE is the clear minimum-cost path
2. **Visual quality** — BesoGo is functional but not KaTrain-quality; custom canvas is Phase 2
3. **Scope** — Single puzzle, log panel + board at key steps, tree navigation in BesoGo

Once Q1–Q8 are resolved, we can proceed to charter, options, and task decomposition.

---

## Round 2: Scope Change (2026-03-07)

User raised critical scope change AFTER governance approved OPT-1 (custom canvas observer):

| q_id | question                                                                                                                                                                                                                                        | options                                                                                                              | recommended | user_response                                                                                                                                                                                                       | status      |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| Q9   | **Interactive play**: Should the user be able to click on the board to play moves and explore sequences interactively (like web-katrain), or just passively observe the pipeline?                                                               | A: Passive observation only / B: Interactive play with click-to-move, tree building, branch exploration              | —           | **B — Interactive play required.** User wants to see solution tree being _built_ move by move, play candidate moves, see each successive move in the tree. "There has to be interactive play with visual elements." | ✅ resolved |
| Q10  | **Framework size**: Is 200MB of node_modules (React + Zustand + Tailwind + Vite) acceptable? Previous governance rejected this as "too heavy."                                                                                                  | A: Still unacceptable / B: 200MB is fine                                                                             | —           | **B — "200 MB of size is not a problem."** Explicitly overriding the "lightweight" constraint on framework dependencies.                                                                                            | ✅ resolved |
| Q11  | **Refactor risk**: User warns "I don't want a refactor after we build a custom canvas. This has happened in the past." Does this mean OPT-1 (custom canvas) should be reconsidered in favor of reusing yen-go-sensei's proven React components? | A: Keep custom canvas, add interactivity / B: Switch to React components from yen-go-sensei / C: New hybrid approach | —           | **Implicit B/C** — User is signaling that building custom canvas + later needing to add interactive features = refactor. They want the interactive features from the start, and yen-go-sensei already has them.     | ✅ resolved |

### Impact on Governance-Approved Plan

| Decision           | Previous (OPT-1)                                       | New Requirement                                                 | Impact                                                                                                   |
| ------------------ | ------------------------------------------------------ | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| DD1 (Board)        | DD1-D: Custom canvas (observation only)                | Interactive play needed                                         | **OVERTURNED** — custom canvas for interactive play is ~2000 lines, same refactor risk user warned about |
| DD2 (Framework)    | DD2-C: Vanilla JS (no build step)                      | 200MB is fine                                                   | **RELAXED** — React + Vite is now acceptable                                                             |
| DD4 (Tree)         | DD4-B: Custom SVG tree (150 lines)                     | Must show tree being built move-by-move, interactive navigation | **NEEDS UPGRADE** — but custom tree could still work with richer data                                    |
| DD3, DD5, DD6, DD7 | SSE, async callback, integrated ownership, gui/ folder | No change                                                       | **UNCHANGED**                                                                                            |

**Conclusion:** OPT-1 must be revised or replaced. The "lightweight, disposable" constraint on framework size is relaxed. The new constraint is: "interactive play from day one, no refactoring later."
