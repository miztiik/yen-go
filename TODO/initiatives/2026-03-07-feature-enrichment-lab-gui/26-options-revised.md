# Revised Options — Enrichment Lab GUI (Post Scope Change)

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Last Updated:** 2026-03-07  
**Revision Reason:** User scope change — interactive play required, 200MB deps acceptable, no custom-canvas-then-refactor

---

## Scope Change Summary

The governance-approved OPT-1 (Lightweight Canvas Observer) was based on two premises now overturned:

1. **"Passive observation only"** → Now: **interactive play** with click-to-move, tree building, branch exploration
2. **"200MB node_modules is too heavy"** → Now: **"200MB is not a problem"**
3. User explicitly warns: **"I don't want a refactor after we build a custom canvas. This has happened in the past."**

This invalidates DD1-D (custom canvas for observation), DD2-C (vanilla JS), and the ~1200 line estimate.

---

## Revised Design Decisions

### DD1-REVISED: Board Rendering (Interactive Play Required)

Interactive play requires: click-to-place stones, capture logic, ko detection, move validation, undo, game tree management, branch creation, PV overlay, eval dots, ownership heatmap, coordinate display, board themes, region selection.

#### Option DD1-R1: Adapt yen-go-sensei (Replace Engine Layer Only)

| Aspect                   | Detail                                                                                                                                                                                                                                                                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**             | Fork `tools/yen-go-sensei/` as-is. Replace the TF.js Web Worker engine with a **Python SSE bridge client** that receives analysis from the enrichment pipeline's KataGo subprocess. Keep ALL UI components (GoBoard, MoveTree, ScoreWinrateGraph, Layout, StatusBar, BottomControlBar, AnalysisPanel, RightPanel) + game logic store unchanged. |
| **What changes**         | (1) Replace `engine/engine.worker.ts` + `engine/katago/client.ts` with a new `engine/bridge-client.ts` that connects to FastAPI SSE. (2) Modify `gameStore.ts`'s `runAnalysis()` to POST to Python bridge instead of sending to Web Worker. (3) Add `pipeline.js` stage bar component. (4) Add SGF paste/upload trigger for enrichment.         |
| **What stays unchanged** | GoBoard.tsx (800 lines), MoveTree.tsx (200 lines), ScoreWinrateGraph.tsx (200 lines), Layout.tsx, StatusBar.tsx, BottomControlBar.tsx, TopControlBar.tsx, RightPanel.tsx, all utils/ (gameLogic, sgf, boardThemes, katrainTheme, sound, etc.), types.ts, all game logic.                                                                        |
| **Benefits**             | Every feature the user asked for is already working: interactive play, eval dots, ownership heatmap, candidate visualization, clickable tree, score/winrate graph, board themes, region selection, PV overlay, coordinates, move numbers. Zero rendering code to write. Proven web-katrain quality.                                             |
| **Drawbacks**            | Carries some unused features (timer, AI play, game report, selfplay) — but these are toggleable/ignorable, not harmful. Requires Vite build step. React + Zustand + Tailwind deps (~200MB node_modules).                                                                                                                                        |
| **Complexity**           | LOW-MEDIUM — engine swap is localized (~200-300 lines changed in store/engine layer)                                                                                                                                                                                                                                                            |
| **Risk**                 | Low — the UI layer is battle-tested; only the engine communication backend changes                                                                                                                                                                                                                                                              |

#### Option DD1-R2: Custom Canvas with Full Interactive Play

| Aspect         | Detail                                                                                                                                                                                                                                                                                                                                                                                                               |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Build everything from scratch in vanilla JS: canvas board with click handling, game logic (captures, ko, scoring), tree management, branch navigation, eval dots, ownership, PV overlay.                                                                                                                                                                                                                             |
| **Benefits**   | Zero framework dependencies. Full control. Lightweight.                                                                                                                                                                                                                                                                                                                                                              |
| **Drawbacks**  | **~2000-3000 lines of custom code.** Must implement: game logic (~300), board rendering (~500), click-to-play with validation (~200), tree management data structures (~300), tree rendering (~200), PV overlay (~100), ownership (~80), branch navigation (~200), SGF parsing/export (~200), undo/redo (~100). This is the exact refactor scenario the user warned about — start simple, then keep adding features. |
| **Complexity** | HIGH — essentially rebuilding yen-go-sensei from scratch without React                                                                                                                                                                                                                                                                                                                                               |
| **Risk**       | **HIGH — user explicitly warned "I don't want a refactor after we build a custom canvas. This has happened in the past."**                                                                                                                                                                                                                                                                                           |

#### Option DD1-R3: Stripped-Down yen-go-sensei Fork

| Aspect         | Detail                                                                                                                                                                                                        |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Fork yen-go-sensei but actively remove unused features: delete timer, AI play modes, game analysis/report modals, selfplay, teach mode. Keep only: board, tree, analysis panel, SGF load/save, engine bridge. |
| **Benefits**   | Smaller codebase than full yen-go-sensei. All needed features remain.                                                                                                                                         |
| **Drawbacks**  | Active deletion is extra work with risk of breaking references. "Dead code" in the fork isn't harmful — it just sits there unused. Stripping is premature optimization.                                       |
| **Complexity** | MEDIUM — more work than DD1-R1 for marginal benefit                                                                                                                                                           |
| **Risk**       | Medium — may break inter-component references during deletion                                                                                                                                                 |

### DD1-REVISED Recommendation

**DD1-R1 (Adapt yen-go-sensei, replace engine layer only).** The user wants interactive play with web-katrain visual quality. yen-go-sensei IS web-katrain ported to this repo. The engine swap is the only change needed. Unused features (timer, AI play) are harmless toggleable UI that doesn't bloat the runtime. Don't strip — YAGNI applies to deletion too.

---

### DD2-REVISED: Frontend Framework

With 200MB acceptable, only one viable option:

**DD2-R1: React + Vite (from existing yen-go-sensei setup)**

yen-go-sensei already has: `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.cjs`, `postcss.config.cjs`. Zero build toolchain setup needed.

---

### DD3-REVISED: Communication Pattern

**Unchanged: DD3-A (SSE)** — but now dual-purpose:

1. **Pipeline progress events** — same as before (9 stage events for pipeline observation)
2. **Analysis response events** — when user clicks "Analyze" in the GUI, the store sends position to Python bridge, bridge runs KataGo, returns analysis via SSE/POST response

The bridge needs both:

- `POST /enrich` → SSE stream (pipeline observation)
- `POST /analyze` → JSON response (interactive analysis for a single position)

---

### DD4-REVISED: Solution/Refutation Tree

**Unchanged: MoveTree.tsx from yen-go-sensei** — already has clickable SVG tree with node navigation. Add correct/wrong color-coding by extending the node rendering (check `node.properties` for correctness marker).

---

### DD5-DD7: Unchanged

- DD5-A: Async callback on `enrich_single_puzzle()`
- DD6-A: Ownership integrated in GoBoard.tsx (already built)
- DD7-A: Code in `tools/puzzle-enrichment-lab/gui/`

---

## Revised Composite Options

### OPT-1R: yen-go-sensei Fork with Engine Bridge (Recommended)

| Aspect                    | Detail                                                                                                                                                                                                                           |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**              | Copy yen-go-sensei into `tools/puzzle-enrichment-lab/gui/`. Replace engine layer with Python SSE bridge. Add pipeline stage bar component. Add enrichment-specific features (correct/wrong tree coloring, pipeline observation). |
| **Board**                 | GoBoard.tsx — unchanged, full interactive play, eval dots, ownership, PV overlay, board themes                                                                                                                                   |
| **Tree**                  | MoveTree.tsx — unchanged + add correct/wrong node coloring                                                                                                                                                                       |
| **Analysis**              | AnalysisPanel.tsx + ScoreWinrateGraph.tsx — unchanged                                                                                                                                                                            |
| **Layout**                | Layout.tsx + StatusBar + BottomControlBar + TopControlBar + RightPanel — unchanged                                                                                                                                               |
| **Engine**                | NEW `bridge-client.ts` (~150 lines) replacing `engine.worker.ts` + `katago/client.ts`                                                                                                                                            |
| **Pipeline bar**          | NEW `PipelineStageBar.tsx` component (~120 lines)                                                                                                                                                                                |
| **Python bridge**         | `bridge.py` (~200 lines) — FastAPI with `/enrich` (SSE), `/analyze` (JSON), `/health`                                                                                                                                            |
| **Framework deps**        | React, Zustand, Tailwind, Vite, react-icons (~200MB node_modules) — user-approved                                                                                                                                                |
| **Build step**            | Yes (Vite) — user-approved                                                                                                                                                                                                       |
| **Total new code**        | ~500 lines (bridge.py + bridge-client.ts + PipelineStageBar + tree coloring)                                                                                                                                                     |
| **Total modified code**   | ~100 lines (gameStore.ts engine calls, remove TF.js references)                                                                                                                                                                  |
| **Code reused as-is**     | ~5000+ lines (entire yen-go-sensei UI layer)                                                                                                                                                                                     |
| **Implementation effort** | 2-3 days                                                                                                                                                                                                                         |
| **Disposability**         | Medium — delete gui/ folder, but it's a React app not a single HTML file                                                                                                                                                         |
| **Risk**                  | Low — only engine communication changes; all UI proven                                                                                                                                                                           |

### OPT-2R: Custom Canvas with Full Interactivity (Not Recommended)

| Aspect                      | Detail                                                                                                                              |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Everything from scratch** | Canvas board + game logic + tree + captures + ko + undo + eval dots + ownership + PV overlay + branch management + SGF parse/export |
| **Total new code**          | ~2500-3000 lines                                                                                                                    |
| **Implementation effort**   | 5-8 days                                                                                                                            |
| **Disposability**           | High — vanilla JS, delete folder                                                                                                    |
| **Risk**                    | **HIGH — user explicitly warned against this pattern. "This has happened in the past."**                                            |

### OPT-3R: BesoGo + Interactive Extensions (Not Recommended)

| Aspect             | Detail                                                                                                                                            |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**       | BesoGo for board + tree, extend with click handling and analysis overlay                                                                          |
| **Total new code** | ~800-1200 lines                                                                                                                                   |
| **Risk**           | HIGH — BesoGo was not designed for interactive analysis. Adding eval dots, ownership, and pipeline observation requires hacking its internal API. |

---

## Comparison

| Criterion              | OPT-1R (yen-go-sensei fork)  | OPT-2R (custom canvas)     | OPT-3R (BesoGo)      |
| ---------------------- | ---------------------------- | -------------------------- | -------------------- |
| Interactive play       | ✅ Full (existing)           | ⚠️ Must build from scratch | ⚠️ Limited by BesoGo |
| Eval dots / candidates | ✅ Built-in                  | ⚠️ Must build              | ❌ Not supported     |
| Ownership heatmap      | ✅ Built-in                  | ⚠️ Must build              | ⚠️ Overlay hack      |
| Tree with navigation   | ✅ Built-in (MoveTree.tsx)   | ⚠️ Must build              | ✅ Built-in (basic)  |
| Score/winrate graph    | ✅ Built-in                  | ⚠️ Must build              | ❌ Not available     |
| Board themes           | ✅ 9 themes (KaTrain parity) | ❌ Must build              | ❌ Not available     |
| Region selection       | ✅ Built-in                  | ⚠️ Must build              | ❌ Not available     |
| PV overlay             | ✅ Built-in                  | ⚠️ Must build              | ❌ Not available     |
| New code to write      | ~500 lines                   | ~2500-3000 lines           | ~800-1200 lines      |
| Refactor risk          | LOW                          | **HIGH (user warned)**     | MEDIUM               |
| Implementation         | 2-3 days                     | 5-8 days                   | 3-4 days             |
| Build step             | Yes (Vite)                   | No                         | No                   |
| Framework size         | ~200MB (user-approved)       | 0                          | 0                    |

---

## Governance Re-Review Request

This document supersedes the OPT-1 selection in the previous governance decision. The scope change (interactive play required, 200MB acceptable, no refactor risk) fundamentally alters the option landscape. Request:

1. **Validate scope change** — confirm interactive play + framework size relaxation changes the optimal selection
2. **Select between OPT-1R, OPT-2R, OPT-3R** — with evidence
3. **Assess whether yen-go-sensei's unused features (timer, AI play) are harmful** or merely dormant
4. **Validate the engine-swap-only approach** — is replacing `engine.worker.ts` with `bridge-client.ts` truly localized?
