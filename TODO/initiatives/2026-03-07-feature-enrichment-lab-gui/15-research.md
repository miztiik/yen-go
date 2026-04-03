# Research Brief: Lightweight GUI for Puzzle Enrichment Lab

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Research role:** Feature-Researcher  
**Last Updated:** 2026-03-07

---

## 1. Research Question and Boundaries

**Core question:** Which GUI architecture best provides real-time visual pipeline observability for `tools/puzzle-enrichment-lab/` — showing each enrichment step, the Go board state, solution/refutation tree, and KataGo outputs — while staying lightweight, fast to implement, and isolated from `backend/puzzle_manager/`?

**In-scope:**

- GUI for `tools/puzzle-enrichment-lab/` (developer tool, not the puzzle player)
- Real-time stage progress visualization
- Go board rendering with stones, markers, and tree navigation
- Python→Browser communication pattern

**Out-of-scope:**

- Full web-katrain feature parity
- Production/public deployment
- Integration with `backend/puzzle_manager/` internals

---

## 2. Internal Code Evidence

### 2.1 FastAPI Is Already a Declared Dependency

| Evidence | File                                                                                                                           | Detail                                                                                                                                                                                  |
| -------- | ------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E-1      | [tools/puzzle-enrichment-lab/requirements.txt](../../../tools/puzzle-enrichment-lab/requirements.txt)                          | `fastapi>=0.100`, `uvicorn>=0.20`, `pydantic>=2.0` — all present, no new Python deps needed for Option A                                                                                |
| E-2      | [tools/puzzle-enrichment-lab/analyzers/enrich_single.py](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L438) | `async def enrich_single_puzzle(...)` — already async; maps directly to FastAPI async endpoint with SSE streaming                                                                       |
| E-3      | [tools/puzzle-enrichment-lab/analyzers/enrich_single.py](../../../tools/puzzle-enrichment-lab/analyzers/enrich_single.py#L793) | 9 labeled pipeline steps with explicit `t_*_start`/`timings` instrumentation — each is a natural SSE checkpoint                                                                         |
| E-4      | [tools/puzzle-enrichment-lab/models/ai_analysis_result.py](../../../tools/puzzle-enrichment-lab/models/ai_analysis_result.py)  | All outputs are Pydantic v2 models (`AiAnalysisResult`, `MoveValidation`, `RefutationEntry`, `DifficultySnapshot`) — `.model_dump_json()` for zero-overhead JSON serialization over SSE |
| E-5      | [tools/puzzle-enrichment-lab/cli.py](../../../tools/puzzle-enrichment-lab/cli.py)                                              | Pipeline entry is a standalone Python module; a FastAPI bridge can wrap `enrich_single_puzzle()` directly without touching CLI                                                          |

### 2.2 BesoGo Viewer Is Already in the Repo

| Evidence | File                                                                                  | Detail                                                                                                                                     |
| -------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| E-6      | [tools/sgf-viewer-besogo/index.html](../../../tools/sgf-viewer-besogo/index.html)     | Pure HTML + vanilla JS, no build step. `besogo.create(div, { sgf: ... })` call. SGF loadable via query param `?sgf=<url>`                  |
| E-7      | [tools/sgf-viewer-besogo/index.html](../../../tools/sgf-viewer-besogo/index.html#L22) | Tree panel (`panels: "control+tool+file+names+comment+tree"`) and board display already built-in — shows stones + solution tree navigation |
| E-8      | [tools/sgf-viewer-besogo/js/](../../../tools/sgf-viewer-besogo/js/)                   | Self-contained bundle with `boardDisplay.js`, `treePanel.js`, `parseSgf.js` — can be served statically by FastAPI with no JS bundler       |

### 2.3 yen-go-sensei Architecture Mismatch

| Evidence | File                                                                                                 | Detail                                                                                                                                                                                      |
| -------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E-9      | [tools/yen-go-sensei/package.json](../../../tools/yen-go-sensei/package.json)                        | Depends on `@tensorflow/tfjs`, `@tensorflow/tfjs-backend-wasm`, `@tensorflow/tfjs-backend-webgpu` — architecturally designed for **in-browser KataGo (WASM)**, not Python subprocess KataGo |
| E-10     | [tools/yen-go-sensei/src/store/gameStore.ts](../../../tools/yen-go-sensei/src/store/gameStore.ts#L1) | `getKataGoEngineClient` lives inside the Zustand store — analysis is driven browser-side via worker; there is no concept of a "receive results from Python server" pathway                  |
| E-11     | [tools/yen-go-sensei/README.md](../../../tools/yen-go-sensei/README.md)                              | "A Web Worker runs KataGo-style evaluation/search on the current position" — confirms browser-native engine, not bridgeable                                                                 |
| E-12     | [TODO/lab-web-katrain/01-product-scope.md](../../../TODO/lab-web-katrain/01-product-scope.md)        | "Product Completion Bar: This lab is considered complete only when all mandatory features are implemented and tested" — app is **incomplete**                                               |

### 2.4 GoBoard.tsx Extraction Feasibility

| Evidence | File                                                                                                           | Detail                                                                                                                                                                                                     |
| -------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| E-13     | [tools/yen-go-sensei/src/components/GoBoard.tsx](../../../tools/yen-go-sensei/src/components/GoBoard.tsx#L1)   | Imports `useGameStore` (Zustand), `useCallback`, `useEffect`; 600+ lines — deeply coupled to game loop state (analysis, AI, selfplay, ROI selection, tree version). Not extractable without major refactor |
| E-14     | [tools/yen-go-sensei/src/components/MoveTree.tsx](../../../tools/yen-go-sensei/src/components/MoveTree.tsx#L1) | Canvas-based SVG tree renderer, also Zustand-coupled. The layout algorithm (`layoutMoveTree`) is self-contained, but the render is store-driven                                                            |

### 2.5 Pipeline Checkpoint Inventory

The 9 pipeline steps in `enrich_single_puzzle()` map cleanly to SSE events:

| Step | Stage Name         | Payload for GUI                                              |
| ---- | ------------------ | ------------------------------------------------------------ |
| 1    | `sgf_parse`        | Board position, metadata (puzzle_id, tags, corner)           |
| 2    | `solution_extract` | Correct first move (GTP coord), solution tree depth          |
| 3    | `query_build`      | Tsumego frame, cropped board size, board state SGF           |
| 4    | `katago_analyze`   | Top-N moves with winrate/policy, ownership map               |
| 4b   | `coord_uncrop`     | Translated move coords (GTP on original board)               |
| 5    | `validate_correct` | Validation status, flags, validator used                     |
| 5a   | `tree_validate`    | Tree completeness metrics                                    |
| 6    | `refutations`      | List of `RefutationEntry` (wrong_move, refutation_pv, delta) |
| 7    | `difficulty`       | `DifficultySnapshot` (level, scores, confidence)             |
| 8    | `assemble`         | Full `AiAnalysisResult` summary                              |
| 9    | `teaching`         | Technique tags, teaching comments, hints                     |

---

## 3. External References

### 3.1 FastAPI SSE Patterns

| Ref | Source                                                                                                                          | Relevance                                                                                                                                           |
| --- | ------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1 | [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) + `sse-starlette` library | `sse-starlette` adds `EventSourceResponse` to FastAPI, which works with Python `async def` generators — directly compatible with the async pipeline |
| R-2 | [Server-Sent Events spec (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)   | Native browser `EventSource` API — plain JS, no framework, no bundler. Events are one-way (server→client) with auto-reconnect                       |
| R-3 | [Gradio streaming docs](https://www.gradio.app/guides/streaming-outputs)                                                        | `yield`-based streaming in pure Python — but Gradio has no native Go board and requires 40MB+ install on top of existing deps                       |
| R-4 | [Streamlit st.status / progress](https://docs.streamlit.io/develop/api-reference/status)                                        | Python-native progress UI with `with st.status("Running..."):` blocks — no Go board, but renders JSON/text stage outputs cleanly                    |

### 3.2 Go Board Rendering Options

| Ref | Source                                                                        | Relevance                                                                                                                                                                                                                            |
| --- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R-5 | [BesoGo GitHub](https://github.com/yewang/besogo)                             | Pure JS, SGF-native, SVG-based board, tree panel built-in. No npm, no build step. The existing `tools/sgf-viewer-besogo/` is exactly this                                                                                            |
| R-6 | [wgo.js](https://github.com/waltheri/wgo.js)                                  | Lightweight JS Go board library. Canvas or SVG mode. No SGF tree — board only. No npm needed                                                                                                                                         |
| R-7 | [Eidogo](https://github.com/jkk/eidogo)                                       | Older JS SGF viewer. Predecessor to BesoGo. No meaningful advantage over BesoGo for this use case                                                                                                                                    |
| R-8 | [KaTrain desktop source](https://github.com/sanderland/katrain) (Python/Kivy) | Analysis loop: analysis results arrive via subprocess stdout → `AnalysisNode.set_analysis()` → Kivy property triggers board redraw. Shows the pattern works well for Python-native desktop but Kivy is heavyweight (requires OpenGL) |
| R-9 | [web-katrain (Sir-Teo)](https://sir-teo.github.io/web-katrain/)               | Confirms TF.js + Web Worker analysis loop works well in browser. However, this is the source architecture for yen-go-sensei — which is designed for in-browser engine, not bridging to Python subprocess                             |

### 3.3 WebSocket vs SSE for Pipeline Streaming

| Ref  | Source                                                                               | Relevance                                                                                                                                                                                                     |
| ---- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-10 | [SSE vs WebSocket comparison (web.dev)](https://web.dev/articles/eventsource-basics) | SSE: native browser, plain HTTP, auto-reconnect, one-way push, ~0 client-side code. WebSocket: bidirectional, requires `ws://`, more client code. For a sequential one-way pipeline SSE is the correct choice |
| R-11 | FastAPI `sse-starlette` docs                                                         | `pip install sse-starlette` → `EventSourceResponse(generator)` — one function call, zero boilerplate                                                                                                          |

---

## 4. Candidate Adaptations for Yen-Go

### Option A: FastAPI Bridge + BesoGo Viewer (Recommended)

**Architecture:**

```
cli.py enrich --serve   →  FastAPI app  →  SSE stream  →  plain HTML page
                                ↓                              ↓
                        enrich_single_puzzle()          BesoGo board + stage log
```

**Key adaptation choices:**

- FastAPI already in `requirements.txt` — no new deps except `sse-starlette` (~5KB)
- New file: `tools/puzzle-enrichment-lab/bridge.py` (FastAPI app, ~100 lines)
- New file: `tools/puzzle-enrichment-lab/static/index.html` (BesoGo embed + SSE client, ~150 lines HTML/JS)
- `enrich_single.py` needs a **callback/observer pattern** added: a `on_step(name, payload)` async callback parameter that bridge.py injects; CLI passes `None`
- BesoGo board is updated by injecting the current board position SGF into `besogo.create()` at key steps (Step 1, Step 3 crop, Step 6 refutations)
- Stage log panel shows each step status in real time (spinner → checkmark → timing)
- All stage payloads use `.model_dump_json()` — zero serialization work

**Complexity:** LOW  
**New Python deps:** 1 (`sse-starlette`)  
**JS build step:** None  
**Time to MVP:** 1–2 days  
**Visual quality:** Moderate (BesoGo is functional but not KaTrain-level polish)

**Limitation:** BesoGo cannot render ownership heatmap or eval dots (it's a static SGF viewer). For ownership visualization an additional canvas overlay would be required.

---

### Option B: FastAPI Bridge + yen-go-sensei React (Not Recommended)

**Why rejected:**

- yen-go-sensei uses **in-browser TF.js/WASM KataGo** — the analysis engine runs in the browser, not via a Python bridge. There is no data pathway to receive Python-side analysis results.
- Adapting yen-go-sensei to consume Python SSE events would require replacing the entire engine layer (Worker + TF.js) with a simple `EventSource` client — essentially discarding the most complex part of the app while keeping its complexity surface (React + Zustand + Tailwind + 1900-line store).
- The app is **incomplete** (per `01-product-scope.md`) and the GoBoard.tsx + MoveTree.tsx are tightly coupled to the Zustand store.
- **Verdict:** This option multiplies implementation risk with no clear payoff for the goal of pipeline observability.

---

### Option C: Pure Python GUI — tkinter / PyQt (Rejected)

**Why rejected:**

- No built-in Go board widget in any Python GUI framework
- Kivy (used by KaTrain desktop) requires OpenGL, is heavyweight, and has known Windows packaging issues
- tkinter board would require canvas-drawing a full 19×19 grid from scratch — more work than the HTML approach
- Poor development iteration speed vs. browser-based approaches

---

### Option D: Streamlit or Gradio (Viable for Stage Log, Not for Board)

**Viability:**

- Streamlit's `st.status`, `st.progress`, `st.json` give excellent pipeline progress visualization with ~10 lines of Python
- Can embed BesoGo as an `st.components.html()` iframe for the board
- `yield`-based streaming: no need for explicit SSE
- **Tradeoff:** Adds ~40MB Streamlit or Gradio install; iframe-based BesoGo board is awkward; full ownership heatmap impossible
- **Best use case:** If the planner wants zero JS custom code at all, Streamlit + `st.components.html()` BesoGo is viable and faster to build than Option A. However, it's less composable long-term.

**Verdict:** Valid fallback if the team wants pure Python, but Option A is preferred.

---

### Option A+: FastAPI + Minimal Vanilla HTML + BesoGo + Ownership Canvas Overlay

Extension of Option A that adds:

- A `<canvas>` overlay on top of BesoGo's SVG board for ownership heatmap (alpha-blended colored dots, same as E-14's `OWNERSHIP_COLORS` constants in GoBoard.tsx)
- KataGo's `ownership` array (returned in `AnalysisResponse.move_infos`) painted as colored semi-transparent circles per intersection
- ~80 extra lines of vanilla JS

This delivers the key "delta vs BesoGo" feature (ownership map) without React/build toolchain.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| Row | Risk                                                                                                                      | Severity         | Mitigation                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------- | ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- |
| R-1 | SSE connections hold the KataGo process alive; if browser tab is closed mid-run, the subprocess may leak                  | Medium           | Use `asyncio` task cancellation in FastAPI; `SingleEngineManager.stop()` in cleanup                                                 |
| R-2 | Pipeline `enrich_single.py` currently has no callback/hook mechanism; inserting `on_step()` touches the main orchestrator | Low              | Add optional `progress_cb: Callable                                                                                                 | None = None`parameter; zero impact when`None` |
| R-3 | `sse-starlette` is a third-party library (MIT license) vs. manual `StreamingResponse` with `text/event-stream`            | Low              | Could use plain FastAPI `StreamingResponse` with manual `data: ...\n\n` formatting; `sse-starlette` just wraps this                 |
| R-4 | BesoGo cannot be updated via script after initial `besogo.create()` call (designed as a one-shot viewer)                  | Medium           | Call `besogo.create()` again on a fresh div to reload board at each major step, or use BesoGo's `loadSgf.js` internal API to reload |
| R-5 | yen-go-sensei GoBoard.tsx is impossible to extract without full Zustand decoupling                                        | High (if chosen) | Confirmed rejection of Option B                                                                                                     |
| R-6 | BesoGo license is MIT                                                                                                     | ✅ Fine          | Already used in the repo                                                                                                            |
| R-7 | Concurrent enrichment runs on same FastAPI server could share a KataGo process                                            | Low              | Out of scope for single-user dev tool; document as "single-session-only"                                                            |

---

## 6. Planner Recommendations

1. **Choose Option A (FastAPI + BesoGo + SSE).** FastAPI and all Pydantic models are already present in `requirements.txt`. BesoGo is already in the repo. The pipeline is already async. This is the minimum viable path: add `bridge.py` (~100 lines), a static HTML page (~150 lines), and a `progress_cb` hook to `enrich_single_puzzle()`. Estimated effort: 1–2 days.

2. **Use SSE (Server-Sent Events) over WebSocket or polling.** The enrichment pipeline is strictly sequential and server-push only. SSE is native to the browser (`EventSource`), trivial to implement in FastAPI (`StreamingResponse`), and requires zero client-side library. Polling is acceptable but wastes cycles; WebSockets add bidirectional overhead not needed here.

3. **Do not attempt to reuse yen-go-sensei components.** The GoBoard.tsx and MoveTree.tsx are tightly coupled to a Zustand store that drives an in-browser TF.js engine. Decoupling them would cost more time than building the Option A page from scratch. The yen-go-sensei codebase is also incomplete and architecturally mismatched.

4. **Extend to Option A+ (ownership canvas overlay) if visual parity with KaTrain is a requirement.** The ownership array is already present in `AnalysisResponse.move_infos` from the enrichment models. Painting it on a `<canvas>` overlay on top of BesoGo adds ~80 lines of vanilla JS and delivers the most visually compelling delta vs. a plain text log. Planner should decide whether the MVP needs ownership heatmap or if it's deferred.

---

## 7. Confidence and Risk Update

| Field                              | Value                                                                                                                                                                                                                                           |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Post-research confidence score** | 85 / 100                                                                                                                                                                                                                                        |
| **Post-research risk level**       | Low                                                                                                                                                                                                                                             |
| **Key uncertainty**                | BesoGo's internal API for dynamic SGF reload (R-4 above) — needs a quick prototype to confirm whether `besogo.create()` can be called on a fresh target `div` at each stage, or if the `loadSgf.js` module exposes a programmatic reload method |
| **Second-order uncertainty**       | Whether inserting `progress_cb` into `enrich_single_puzzle()` unintentionally affects timing measurements or introduces async race conditions in the pipeline — low probability, easily verified by running existing tests                      |

---

## Handoff Summary

| Key                              | Value                                                                                                                                                                                                                                                      |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `research_completed`             | true                                                                                                                                                                                                                                                       |
| `initiative_path`                | `TODO/initiatives/2026-03-07-feature-enrichment-lab-gui/`                                                                                                                                                                                                  |
| `artifact`                       | `15-research.md`                                                                                                                                                                                                                                           |
| `top_recommendations`            | (1) Option A: FastAPI+BesoGo+SSE, (2) SSE not WebSocket, (3) Reject yen-go-sensei reuse, (4) Option A+ ownership overlay if visual quality required                                                                                                        |
| `open_questions`                 | Q1: Is ownership heatmap in scope for MVP? Q2: Does the GUI need to accept arbitrary SGF drops (drag-and-drop), or is CLI invocation (`--serve --sgf foo.sgf`) sufficient? Q3: Should the bridge support batch mode (queue of SGFs) or single-puzzle only? |
| `post_research_confidence_score` | 85                                                                                                                                                                                                                                                         |
| `post_research_risk_level`       | low                                                                                                                                                                                                                                                        |
