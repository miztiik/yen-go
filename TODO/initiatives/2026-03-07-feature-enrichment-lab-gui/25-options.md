# Options — Enrichment Lab Visual Pipeline Observer

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Last Updated:** 2026-03-07

---

## Planning Confidence

| Field                        | Value                                                                   |
| ---------------------------- | ----------------------------------------------------------------------- |
| Pre-research confidence      | 35 / 100                                                                |
| Post-research confidence     | 85 / 100                                                                |
| Post-Q4-deep-dive confidence | 78 / 100 (dropped due to component reuse complexity discovery)          |
| Risk level                   | Medium                                                                  |
| Research invoked             | Yes — `15-research.md` + Q4 deep dive on web-katrain component coupling |

---

## Design Decision Matrix

Seven interrelated design decisions must be resolved. Each is analyzed below with options, tradeoffs, and a recommendation candidate.

---

## DD1: Board Rendering Approach

**Question:** How should the Go board be rendered — what gives us stones, eval dots, ownership heatmap, and candidate move visualization?

### Option DD1-A: BesoGo SVG Viewer + Canvas Overlay

| Aspect         | Detail                                                                                                                                                                                                                                                                                                |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Use existing `tools/sgf-viewer-besogo/` (pure HTML+JS, SVG board). Add a `<canvas>` overlay for ownership heatmap and eval dots.                                                                                                                                                                      |
| **Benefits**   | Zero build step. Already in repo. SGF-native — tree panel, comments, navigation built-in. ~80 lines for ownership overlay.                                                                                                                                                                            |
| **Drawbacks**  | BesoGo is a static SGF viewer, not a live analysis display. No eval dots on candidates. No policy visualization. Ownership overlay is a hack on top of SVG. BesoGo's `create()` API is one-shot — dynamic reload requires re-creating the widget. Visual quality is functional but not KaTrain-level. |
| **Complexity** | LOW                                                                                                                                                                                                                                                                                                   |
| **Risk**       | BesoGo's internal API for live SGF reload is undocumented (R-4 from research). Canvas overlay z-index coordination with SVG is fragile.                                                                                                                                                               |

### Option DD1-B: Reuse yen-go-sensei React Components (GoBoard.tsx + MoveTree.tsx)

| Aspect         | Detail                                                                                                                                                                                                                                                                                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Approach**   | Extract `GoBoard.tsx`, `MoveTree.tsx`, `ScoreWinrateGraph.tsx`, `StatusBar.tsx`, `BottomControlBar.tsx` from `tools/yen-go-sensei/`. Decouple from Zustand `gameStore.ts` and TF.js engine. Create a thin "bridge store" that receives data from Python SSE instead of browser engine.                                                                                                                       |
| **Benefits**   | KaTrain-quality board rendering with eval dots, ownership heatmap, candidate moves, PV overlay, coordinate display, board themes. MoveTree.tsx has canvas-based tree layout. ScoreWinrateGraph has score/winrate graph. All the visual polish already exists.                                                                                                                                                |
| **Drawbacks**  | Deep coupling: `GoBoard.tsx` has 5 direct `useGameStore` imports, 800+ lines, 9 utility imports. `gameStore.ts` imports engine client, KataGo types, MCTS limits. Extraction requires: (1) defining new prop interfaces, (2) removing all store coupling, (3) removing engine-specific code, (4) creating a bridge store. This is essentially a partial rewrite. Also requires React + Vite build toolchain. |
| **Complexity** | HIGH — estimated 3-5 days for extraction + bridge store + build setup                                                                                                                                                                                                                                                                                                                                        |
| **Risk**       | The components were designed for interactive play, not passive observation. Many features (click-to-play, region selection, AI move, selfplay) don't apply. We'd be carrying dead code surface or spending time pruning it. The yen-go-sensei app is also _incomplete_ (per its own product scope doc).                                                                                                      |

### Option DD1-C: Fork web-katrain Upstream Components

| Aspect         | Detail                                                                                                                                                                                                                                                                                       |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Clone select components directly from `Sir-Teo/web-katrain` on GitHub (React + Zustand), adapt them.                                                                                                                                                                                         |
| **Benefits**   | Same visual quality as yen-go-sensei (which is a port). Potentially cleaner source since upstream may be more actively maintained.                                                                                                                                                           |
| **Drawbacks**  | Same coupling problems as DD1-B — upstream web-katrain uses the same Zustand+TF.js architecture. Additionally: introduces external code with unknown license terms, requires ongoing sync decisions, and is architecturally identical to DD1-B since yen-go-sensei IS a port of web-katrain. |
| **Complexity** | HIGH+ (same as DD1-B plus license/attribution overhead)                                                                                                                                                                                                                                      |
| **Risk**       | Same as DD1-B plus dependency on external project's API stability.                                                                                                                                                                                                                           |

### Option DD1-D: Custom Lightweight Canvas Board (Purpose-Built)

| Aspect         | Detail                                                                                                                                                                                                                                                                                                     |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Write a minimal canvas-based Go board renderer in vanilla JS/TS (~300-400 lines). Purpose-built for _observation_ (not play). Supports: stones, last-move marker, eval dots, ownership heatmap, candidate moves with winrate/policy labels. No click-to-play, no game logic.                               |
| **Benefits**   | Zero coupling to any framework or store. Exactly the features needed, nothing more. Lightweight — no React, no Zustand, no build step. Can render KaTrain-quality visuals (the rendering math from GoBoard.tsx is pure canvas geometry — extractable as plain functions). Disposable — easy to throw away. |
| **Drawbacks**  | Must write board rendering from scratch (grid, stones, hoshi, coordinates, eval dots, ownership). ~300-400 lines of canvas drawing code. No tree panel built-in (handled by DD4).                                                                                                                          |
| **Complexity** | MEDIUM — 1-2 days for a solid canvas board with all visual features                                                                                                                                                                                                                                        |
| **Risk**       | Low — canvas rendering is well-understood; the math is visible in GoBoard.tsx as reference.                                                                                                                                                                                                                |

### DD1 Recommendation Candidate

**DD1-D (Custom Lightweight Canvas Board)** — aligned with the "lightweight, disposable" mandate. BesoGo (DD1-A) can't render eval dots or ownership natively. Extracting yen-go-sensei (DD1-B/C) is 3-5 days for components designed for a different use case. A purpose-built canvas board uses GoBoard.tsx's rendering _math_ as reference without its framework coupling.

---

## DD2: Frontend Framework

**Question:** Should the GUI use vanilla HTML+JS, or React with a build step?

### Option DD2-A: Vanilla HTML + JS (No Build Step)

| Aspect         | Detail                                                                                                                                                                              |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Single `index.html` with `<script>` tags. Canvas board, SSE client, DOM manipulation — all vanilla JS. Served as static files by FastAPI.                                           |
| **Benefits**   | Zero build step. Served directly by FastAPI's `StaticFiles`. No `npm install`, no `node_modules`, no Vite config. Truly lightweight and disposable. Fast iteration — edit, refresh. |
| **Drawbacks**  | No component model. DOM manipulation for pipeline stage bar, tree panel, SGF input area requires more manual code. No TypeScript type safety.                                       |
| **Complexity** | LOW                                                                                                                                                                                 |

### Option DD2-B: React + Vite (Build Step Required)

| Aspect         | Detail                                                                                                                                                                                                                           |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | React app with Vite dev server. Components for board, tree, stage bar. Could reuse yen-go-sensei's Tailwind setup.                                                                                                               |
| **Benefits**   | Component model makes UI composition cleaner. TypeScript. Could theoretically reuse yen-go-sensei components (but see DD1-B risks).                                                                                              |
| **Drawbacks**  | Requires `npm install` (200+ MB node_modules). Build step. Vite dev server must proxy to FastAPI. More moving parts. Contradicts "lightweight, disposable" goal. Can't just delete a folder — need to clean up build config too. |
| **Complexity** | MEDIUM-HIGH                                                                                                                                                                                                                      |

### Option DD2-C: Vanilla HTML + JS Modules (ES Modules, No Bundler)

| Aspect         | Detail                                                                                                                                                                                                    |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | HTML with `<script type="module">` tags. Code split into `.js` module files (board.js, tree.js, pipeline.js, sse-client.js). No build step, but clean module boundaries.                                  |
| **Benefits**   | Clean module boundaries like a framework, but zero build step. Each module is a single-purpose file. ES module `import/export` works natively in all modern browsers. Easy to understand, easy to delete. |
| **Drawbacks**  | No JSX, no TypeScript (unless using JSDoc type annotations). Manual DOM manipulation.                                                                                                                     |
| **Complexity** | LOW-MEDIUM                                                                                                                                                                                                |

### DD2 Recommendation Candidate

**DD2-C (Vanilla HTML + JS Modules)** — Clean module structure without build toolchain. Aligns with "lightweight, disposable" mandate. Each module (board, tree, pipeline, sse) is a single-purpose file. Easy to understand, easy to throw away.

---

## DD3: Communication Pattern (Python → Browser)

**Question:** How should pipeline stage progress and analysis data stream to the browser?

### Option DD3-A: Server-Sent Events (SSE)

| Aspect         | Detail                                                                                                                                                                                                                                                    |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | FastAPI endpoint returns `StreamingResponse` with `text/event-stream` content type. Browser uses native `EventSource` API. Each pipeline step emits an SSE event with stage name + JSON payload.                                                          |
| **Benefits**   | Native browser API — zero client library. One-way push (server→client) is exactly what the pipeline needs. Auto-reconnect built-in. `StreamingResponse` in FastAPI is trivial. Works with the async pipeline (`enrich_single_puzzle()` is already async). |
| **Drawbacks**  | One-way only — browser can't send control messages (e.g., "cancel enrichment"). But cancellation can use a separate POST endpoint.                                                                                                                        |
| **Complexity** | LOW                                                                                                                                                                                                                                                       |

### Option DD3-B: WebSocket

| Aspect         | Detail                                                                                                                                                                                                            |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | FastAPI WebSocket endpoint. Bidirectional communication.                                                                                                                                                          |
| **Benefits**   | Bidirectional — browser could send control commands (cancel, change config, restart). Lower latency for high-frequency updates.                                                                                   |
| **Drawbacks**  | More complex server-side code. Need to handle connection lifecycle (open, close, error). No auto-reconnect in browser — must implement manually. Overkill for a sequential pipeline that pushes ~10 events total. |
| **Complexity** | MEDIUM                                                                                                                                                                                                            |

### Option DD3-C: Polling

| Aspect         | Detail                                                                           |
| -------------- | -------------------------------------------------------------------------------- |
| **Approach**   | FastAPI stores state in memory. Browser polls `/status` every 500ms.             |
| **Benefits**   | Simplest server implementation.                                                  |
| **Drawbacks**  | Wastes cycles. Latency up to 500ms per update. More code on both sides than SSE. |
| **Complexity** | LOW (but wasteful)                                                               |

### DD3 Recommendation Candidate

**DD3-A (SSE)** — The pipeline is strictly sequential, server-push, ~10 events total. SSE is the exact right tool. Native browser API, zero library, trivial FastAPI implementation. Add a separate `POST /cancel` endpoint for the rare cancellation case.

---

## DD4: Solution/Refutation Tree Rendering

**Question:** How should the clickable, navigatable solution/refutation tree be rendered?

### Option DD4-A: BesoGo Tree Panel (Embedded)

| Aspect         | Detail                                                                                                                                                                                                                                        |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Embed BesoGo with `panels: "tree+comment+control"`. BesoGo's `treePanel.js` provides clickable tree navigation. Load final enriched SGF into BesoGo for tree exploration.                                                                     |
| **Benefits**   | Zero custom tree code. Full SGF tree navigation including variations, comments. Already in the repo.                                                                                                                                          |
| **Drawbacks**  | BesoGo tree is basic (circles + lines, no color coding for correct/wrong). No eval coloring on nodes. The tree panel is visually dated. The board and tree are coupled in one widget — can't show the pipeline stage bar between them easily. |
| **Complexity** | LOW                                                                                                                                                                                                                                           |

### Option DD4-B: Custom Canvas/SVG Tree (Minimal)

| Aspect         | Detail                                                                                                                                                                                                      |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Build a minimal tree renderer (~150-200 lines) that reads the SGF tree structure. Nodes colored by correctness (green=correct, red=wrong). Click to navigate — updates the board.                           |
| **Benefits**   | Purpose-built for enrichment observation. Can color-code correct vs. wrong vs. refutation branches. Can highlight the branch being actively enriched during pipeline execution. Lightweight and disposable. |
| **Drawbacks**  | Must implement tree layout algorithm and click handling. ~150-200 lines of canvas/SVG code.                                                                                                                 |
| **Complexity** | MEDIUM                                                                                                                                                                                                      |

### Option DD4-C: Extract MoveTree.tsx from yen-go-sensei

| Aspect         | Detail                                                                                                                                                                                                                          |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Port `MoveTree.tsx` (canvas-based, ~100 lines of layout algorithm) to vanilla JS.                                                                                                                                               |
| **Benefits**   | Proven layout algorithm. KaTrain-style node rendering.                                                                                                                                                                          |
| **Drawbacks**  | Requires React→vanilla port. The tree component needs game node data format — must bridge from SGF parse output. Layout algorithm (`layoutMoveTree`) is extractable but the rendering uses React hooks (`useEffect`, `useRef`). |
| **Complexity** | MEDIUM                                                                                                                                                                                                                          |

### Option DD4-D: BesoGo for Tree + Custom Board

| Aspect         | Detail                                                                                                                                                                                                                                         |
| -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Use BesoGo in a side panel purely for tree navigation and comments. Use custom canvas board in the main panel for visual analysis (eval dots, ownership, etc.). Connect them: when user clicks a tree node in BesoGo, update the canvas board. |
| **Benefits**   | Best of both worlds — BesoGo's mature tree navigation + custom board's visual quality. No custom tree code needed.                                                                                                                             |
| **Drawbacks**  | Two rendering systems side by side. Synchronization between BesoGo's internal state and the canvas board requires hooking into BesoGo's event system (it has a listener/subscriber pattern). More complex integration.                         |
| **Complexity** | MEDIUM-HIGH                                                                                                                                                                                                                                    |

### DD4 Recommendation Candidate

**DD4-B (Custom Canvas/SVG Tree)** — Aligned with lightweight/disposable mandate. The tree layout algorithm from MoveTree.tsx (~40 lines of pure math) can be used as reference without importing the React component. Color-coding correct/wrong/refutation branches adds value that none of the other options provide. ~150-200 lines total.

---

## DD5: Pipeline Integration Hook

**Question:** How does the GUI receive real-time stage updates from `enrich_single_puzzle()`?

### Option DD5-A: Async Callback Parameter

| Aspect         | Detail                                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Add `progress_cb: Callable[[str, dict], Awaitable[None]]                                                                                          | None = None`parameter to`enrich_single_puzzle()`. At each stage boundary, call `await progress_cb(stage_name, payload)` if not None. CLI passes None (zero impact). Bridge.py injects a callback that pushes to SSE. |
| **Benefits**   | Zero impact on existing behavior (None=no-op). Clean interface. Each stage emits structured data. Testable — can inject a mock callback in tests. |
| **Drawbacks**  | Touches `enrich_single_puzzle()` signature (one function). Must ensure callback doesn't slow down the pipeline (async so it won't block).         |
| **Complexity** | LOW                                                                                                                                               |

### Option DD5-B: Event Emitter / Observable

| Aspect         | Detail                                                                                                                                                                                  |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | Create an `EnrichmentObserver` protocol class. `enrich_single_puzzle()` receives an optional observer. Observer has methods like `on_parse()`, `on_validate()`, `on_refutation()`, etc. |
| **Benefits**   | Strongly typed interface. Can have multiple observers (logging, GUI, metrics).                                                                                                          |
| **Drawbacks**  | More abstraction than needed for a single-use case. Creates a new protocol/interface when a simple callback suffices. YAGNI violation.                                                  |
| **Complexity** | MEDIUM                                                                                                                                                                                  |

### DD5 Recommendation Candidate

**DD5-A (Async Callback)** — Simplest possible integration. One parameter, zero impact when None. No new abstractions. KISS/YAGNI aligned.

---

## DD6: Ownership Heatmap Approach

**Question:** How should the KataGo ownership heatmap be rendered?

### Option DD6-A: Integrated in Custom Canvas Board

| Aspect         | Detail                                                                                                                                                                                                                  |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**   | The custom canvas board (DD1-D) renders ownership as semi-transparent colored circles per intersection. Same rendering math as GoBoard.tsx's `OWNERSHIP_COLORS` and `OWNERSHIP_GAMMA`. Part of the board's paint cycle. |
| **Benefits**   | Single rendering pass. No z-index issues. Clean code. The ownership rendering from GoBoard.tsx is ~30 lines of canvas math — directly portable.                                                                         |
| **Drawbacks**  | Only available if DD1-D is selected.                                                                                                                                                                                    |
| **Complexity** | LOW (included in DD1-D's ~300-400 lines)                                                                                                                                                                                |

### Option DD6-B: Separate Canvas Overlay

| Aspect         | Detail                                                                                                          |
| -------------- | --------------------------------------------------------------------------------------------------------------- |
| **Approach**   | A `<canvas>` element positioned on top of the board (whatever board renderer is chosen). Paints ownership dots. |
| **Benefits**   | Works with any board renderer (BesoGo, custom, etc.).                                                           |
| **Drawbacks**  | Z-index coordination. Must match board grid sizing exactly. Two canvas coordinate systems.                      |
| **Complexity** | LOW-MEDIUM                                                                                                      |

### DD6 Recommendation Candidate

**DD6-A (Integrated)** — if DD1-D is selected. Otherwise DD6-B.

---

## DD7: Code Organization

**Question:** Where does the GUI code live and how is it structured?

### Option DD7-A: `tools/puzzle-enrichment-lab/gui/`

| Aspect        | Detail                                                                                                               |
| ------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Approach**  | Subdirectory `gui/` inside the enrichment lab. Contains `bridge.py` (FastAPI server), `static/` (HTML/JS/CSS files). |
| **Benefits**  | Contained. Clear naming. Easy to delete entirely.                                                                    |
| **Drawbacks** | None significant.                                                                                                    |

### Option DD7-B: `tools/puzzle-enrichment-lab/observer/`

| Aspect        | Detail                                                                          |
| ------------- | ------------------------------------------------------------------------------- |
| **Approach**  | Name it "observer" to reflect its purpose (observe pipeline, don't control it). |
| **Benefits**  | Semantically accurate — this isn't a general GUI, it's a pipeline observer.     |
| **Drawbacks** | Less immediately obvious what it does.                                          |

### DD7 Recommendation Candidate

**DD7-A (`gui/`)** — immediately clear what it is. User requested "a nice name inside a folder."

---

## Composite Options (Full Proposals)

### OPT-1: Lightweight Canvas Observer (Recommended)

| Aspect              | Detail                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Board**           | DD1-D: Custom lightweight canvas board (~300-400 lines vanilla JS)                                                                  |
| **Framework**       | DD2-C: Vanilla HTML + JS Modules (no build step)                                                                                    |
| **Communication**   | DD3-A: SSE (Server-Sent Events)                                                                                                     |
| **Tree**            | DD4-B: Custom canvas/SVG tree with correct/wrong coloring (~150-200 lines)                                                          |
| **Integration**     | DD5-A: Async callback parameter on `enrich_single_puzzle()`                                                                         |
| **Ownership**       | DD6-A: Integrated in canvas board                                                                                                   |
| **Organization**    | DD7-A: `tools/puzzle-enrichment-lab/gui/`                                                                                           |
| **Total new code**  | ~800-1000 lines (bridge.py ~150, index.html ~50, board.js ~400, tree.js ~150, pipeline.js ~100, sse-client.js ~50, styles.css ~100) |
| **New Python deps** | 0 (FastAPI + uvicorn already in requirements.txt)                                                                                   |
| **Build step**      | None                                                                                                                                |
| **Disposability**   | Delete `gui/` folder + remove ~5 lines from `enrich_single.py` (callback parameter)                                                 |
| **Risk**            | Low — all proven technologies, no framework coupling                                                                                |

### OPT-2: BesoGo + Canvas Overlay Hybrid

| Aspect              | Detail                                                                                                                                              |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Board**           | DD1-A: BesoGo SVG viewer + canvas overlay for ownership                                                                                             |
| **Framework**       | DD2-A: Vanilla HTML + JS (no build step)                                                                                                            |
| **Communication**   | DD3-A: SSE                                                                                                                                          |
| **Tree**            | DD4-A: BesoGo's built-in tree panel                                                                                                                 |
| **Integration**     | DD5-A: Async callback                                                                                                                               |
| **Ownership**       | DD6-B: Separate canvas overlay on top of BesoGo                                                                                                     |
| **Organization**    | DD7-A: `gui/`                                                                                                                                       |
| **Total new code**  | ~400-500 lines (bridge.py ~150, index.html ~100, ownership-overlay.js ~80, pipeline-bar.js ~100, sse-client.js ~50)                                 |
| **New Python deps** | 0                                                                                                                                                   |
| **Build step**      | None                                                                                                                                                |
| **Disposability**   | Very high — even less custom code to delete                                                                                                         |
| **Risk**            | Medium — BesoGo dynamic reload is undocumented; no eval dots on candidates; ownership overlay z-index fragility; tree has no correct/wrong coloring |

### OPT-3: React + Yen-Go-Sensei Components

| Aspect             | Detail                                                                                                                                                                                                                                                      |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Board**          | DD1-B: Extract GoBoard.tsx from yen-go-sensei                                                                                                                                                                                                               |
| **Framework**      | DD2-B: React + Vite                                                                                                                                                                                                                                         |
| **Communication**  | DD3-A: SSE                                                                                                                                                                                                                                                  |
| **Tree**           | DD4-C: Extract MoveTree.tsx from yen-go-sensei                                                                                                                                                                                                              |
| **Integration**    | DD5-A: Async callback                                                                                                                                                                                                                                       |
| **Ownership**      | DD6-A: Already built into GoBoard.tsx                                                                                                                                                                                                                       |
| **Organization**   | DD7-A: `gui/`                                                                                                                                                                                                                                               |
| **Total new code** | ~600-800 lines new + ~1500 lines extracted/modified                                                                                                                                                                                                         |
| **New deps**       | React, React-DOM, Zustand, react-icons, Tailwind, Vite (200+ MB node_modules)                                                                                                                                                                               |
| **Build step**     | Required (Vite)                                                                                                                                                                                                                                             |
| **Disposability**  | LOW — React app with build toolchain is hard to "just delete"                                                                                                                                                                                               |
| **Risk**           | HIGH — GoBoard.tsx has 5 Zustand store imports, 9 utility imports, 800+ lines tightly coupled to game loop state. Decoupling is estimated at 3-5 days. yen-go-sensei is incomplete. Components were designed for interactive play, not passive observation. |

---

## Comparison Summary

| Criterion                   | OPT-1 (Canvas Observer)               | OPT-2 (BesoGo Hybrid)         | OPT-3 (React Extract)                    |
| --------------------------- | ------------------------------------- | ----------------------------- | ---------------------------------------- |
| Visual quality              | High (KaTrain-quality rendering math) | Medium (functional but dated) | High (identical to web-katrain)          |
| Eval dots / candidates      | Yes (purpose-built)                   | No (BesoGo can't render them) | Yes (built-in)                           |
| Ownership heatmap           | Yes (integrated)                      | Yes (overlay hack)            | Yes (built-in)                           |
| Correct/wrong tree coloring | Yes (purpose-built)                   | No (BesoGo has no coloring)   | No (MoveTree has no correctness concept) |
| Build step required         | No                                    | No                            | Yes (Vite)                               |
| Implementation effort       | 2-3 days                              | 1-2 days                      | 5-7 days                                 |
| Disposability               | High (delete folder)                  | Very high (less code)         | Low (React app)                          |
| Framework dependencies      | Zero                                  | Zero                          | React + Zustand + Vite + Tailwind        |
| Pipeline stage bar          | Custom (purpose-built)                | Custom (must add)             | Custom (must add)                        |
| Future maintainability      | Self-contained                        | Depends on BesoGo             | Depends on yen-go-sensei evolution       |

---

## Why Not Reuse Web-KaTrain Components (Deep Analysis)

The user specifically asked for deeper investigation. Here are the findings:

### Coupling Analysis of `GoBoard.tsx` (from `tools/yen-go-sensei/src/components/`)

| Import                                 | Type                  | Required for Observation?                               |
| -------------------------------------- | --------------------- | ------------------------------------------------------- |
| `useGameStore` (Zustand)               | State management      | NO — we receive data from Python SSE, not browser store |
| `getKaTrainEvalColors`                 | Pure utility (colors) | YES — **extractable** (~20 lines of color math)         |
| `publicUrl`                            | Asset path helper     | NO — different asset setup                              |
| `getBoardTheme`                        | Theme colors          | YES — **extractable** (~30 lines of theme data)         |
| `getHoshiPoints`, `normalizeBoardSize` | Board geometry        | YES — **extractable** (~40 lines of pure math)          |
| `parseGtpMove`                         | Coordinate conversion | YES — **extractable** (~10 lines)                       |

**Key insight:** The _rendering math_ in GoBoard.tsx IS reusable — hoshi points, stone drawing, eval dot sizing, ownership coloring, coordinate labels. But it's interleaved with React hooks, Zustand store subscriptions, event handlers for play/analysis/selfplay, region selection, and timer integration. The rendering math totals ~200 lines of pure canvas geometry; the React/Zustand integration is another ~600 lines we don't need.

**Recommendation:** Port the ~200 lines of rendering _math_ (not the React component) into OPT-1's vanilla canvas board. This gives us KaTrain-quality visuals without any framework coupling.

### What the Rendering Math Gives Us (Extractable)

| Feature                                      | Lines    | Source in GoBoard.tsx                     |
| -------------------------------------------- | -------- | ----------------------------------------- |
| Grid drawing (lines, hoshi, coordinates)     | ~40      | Canvas grid rendering section             |
| Stone rendering (with gradient)              | ~30      | `drawStone()` equivalent                  |
| Eval dots (sized by visits, colored by loss) | ~50      | `evaluationClass()`, dot rendering        |
| Ownership heatmap                            | ~30      | `OWNERSHIP_COLORS`, `OWNERSHIP_GAMMA`     |
| Last move marker                             | ~10      | Circle/square on last played intersection |
| Candidate move labels (winrate%, visits)     | ~40      | Text overlay rendering                    |
| **Total extractable**                        | **~200** | Pure functions, no framework dependency   |

---

## Governance Review Request

This options document requests governance review on:

1. Selection between OPT-1, OPT-2, OPT-3
2. Validation that the "lightweight, disposable" constraint is correctly weighted
3. Confirmation that NOT reusing yen-go-sensei React components is the right call
4. Agreement on SSE as the communication pattern
5. Agreement on async callback as the pipeline integration hook
