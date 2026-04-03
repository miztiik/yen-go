# ADR: Enrichment Lab GUI — Architecture Decision Record

**ADR ID:** ADR-GUI-001  
**Initiative:** 2026-03-07-feature-enrichment-lab-gui  
**Status:** Accepted  
**Date:** 2026-03-07  
**Decision makers:** 8-member governance panel (4 Go professionals, 2 principal engineers, 2 UI/UX specialists)

---

## Context

The KataGo puzzle enrichment lab (`tools/puzzle-enrichment-lab/`) processes Go tsumego puzzles through a 9-step pipeline: parse SGF → extract solution → build query (tsumego frame + crop) → KataGo analysis → validate correct move → tree validation → generate refutations → estimate difficulty → teaching enrichment. This pipeline is currently CLI-only.

A visual GUI is needed so developers can:

1. **Observe** each pipeline step in real time (stage progression, board state changes)
2. **Interact** with the board (click moves, explore sequences, navigate the solution/refutation tree being built)
3. **Verify** enrichment quality visually (eval dots, ownership heatmap, correct/wrong branch coloring)

An existing web-katrain clone (`tools/yen-go-sensei/`) lives in the repo — it is a **direct git clone of `https://github.com/Sir-Teo/web-katrain.git`** (confirmed: `.git/config` remote = Sir-Teo/web-katrain). It provides React + Zustand + Tailwind UI with full interactive Go board, move tree, score/winrate graph, eval dots, ownership heatmap, PV overlay, board themes, region selection, SGF import/export, and all game logic.

---

## Decisions

### D1: Source — Clone from upstream `Sir-Teo/web-katrain` (not from yen-go-sensei)

**Decision:** Clone directly from the public upstream `https://github.com/Sir-Teo/web-katrain` repository into `tools/puzzle-enrichment-lab/gui/`.  Record the SHA in `gui/UPSTREAM_COMMIT.md`.

**Rationale:**

- `tools/yen-go-sensei/` IS a direct clone of Sir-Teo/web-katrain (`.git/config` remote confirms). They are the same codebase.
- Cloning from upstream ensures we get a known version, not a potentially stale local copy.
- Pinning the commit SHA ensures reproducible builds. The exact commit is recorded so any future update is deliberate.
- The local `yen-go-sensei/` directory retains its own `.git/` history, `dist/` build artifacts, and `node_modules/` — we don't want to carry these into the GUI folder.
- Clone command: `git clone --depth 1 https://github.com/Sir-Teo/web-katrain.git gui` then remove `.git/` from the clone. Record the HEAD commit SHA.

**Rejected Alternative:** Copy from `tools/yen-go-sensei/`. Rejected because it adds intermediate indirection — the code is identical to upstream, but the local copy may be stale and carries build artifacts.

### D2: CLI/GUI Complete Isolation

**Decision:** The CLI and GUI are completely independent. The GUI is a self-contained folder that can be deleted without any impact on the CLI.

**Isolation Contract:**

1. `enrich_single_puzzle()` receives an **optional** `progress_cb` parameter (default `None`). When `None`, zero overhead — no GUI code is imported or executed.
2. CLI `cli.py` does NOT import any GUI modules. The `--gui` flag, if added, is a convenience that starts `bridge.py` as a subprocess — NOT an import.
3. `bridge.py` imports from `analyzers/` and `engine/` (the enrichment lab's own modules), but the enrichment lab NEVER imports from `gui/`.
4. **Deletion test:** `rm -rf tools/puzzle-enrichment-lab/gui/` → all CLI commands work identically. All existing tests pass.
5. The GUI folder contains its own `package.json`, `vite.config.ts`, `node_modules/` — completely self-contained JavaScript/TypeScript toolchain.
6. No shared state files between CLI and GUI. The bridge communicates via HTTP (FastAPI) only.

**Dependency direction:**

```
gui/bridge.py ──imports──► analyzers/ (enrichment lab Python code)
gui/bridge.py ──imports──► engine/ (KataGo subprocess manager)
analyzers/ ──does NOT import──► gui/
cli.py ──does NOT import──► gui/
```

### D3: Engine Swap Architecture — Replace Web Worker TF.js with Python Bridge

**Decision:** Replace the in-browser TF.js/WASM KataGo engine (`engine/engine.worker.ts` + `engine/katago/`) with a bridge client (`engine/bridge-client.ts`) that sends analysis requests to the Python FastAPI server.

**Rationale:**

- The enrichment lab already has a production-grade KataGo subprocess manager (`SingleEngineManager`) with proper lifecycle management. Using the same engine ensures analysis results are identical between GUI and CLI.
- TF.js browser engine uses ~4MB b6c96 model (weak). The enrichment lab uses b15c192 (~40MB) or b18c384 (~160MB) models — far stronger. GUI analysis quality matches CLI quality.
- Engine coupling in web-katrain is localized: `getKataGoEngineClient()` called only in `gameStore.ts` (12 call sites). TF.js imports exclusively in `engine/` directory — zero in `components/` or `utils/`.
- The bridge-client implements the same request/response shape: position → analysis result. UI components don't know or care whether analysis came from browser WASM or Python subprocess.

**Interface:**

```typescript
// bridge-client.ts — replaces engine.worker.ts
export async function analyzePython(
  request: AnalysisRequest,
): Promise<AnalysisResult> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    body: JSON.stringify(request),
  });
  return mapToAnalysisResult(await response.json());
}
```

### D4: Dual-Purpose Bridge Server

**Decision:** The FastAPI bridge serves two purposes via separate endpoints:

| Endpoint            | Purpose                                       | Protocol                     |
| ------------------- | --------------------------------------------- | ---------------------------- |
| `POST /api/analyze` | Interactive analysis (user clicks "Analyze")  | JSON request → JSON response |
| `POST /api/enrich`  | Pipeline observation (full 9-step enrichment) | JSON request → SSE stream    |
| `POST /api/cancel`  | Cancel running enrichment                     | JSON                         |
| `GET /api/health`   | Engine status check                           | JSON                         |

**Rationale:** Interactive analysis and pipeline observation have different communication patterns. Single-position analysis is request/response (user requests, waits for result). Pipeline observation is a stream of ~10 events over seconds — SSE (Server-Sent Events) is the correct pattern for sequential server-push.

### D5: Pipeline Progress Hook — Async Callback

**Decision:** Add `progress_cb: Callable[[str, dict], Awaitable[None]] | None = None` parameter to `enrich_single_puzzle()`.

**Contract:**

- Default `None` = zero overhead. No GUI code imported or executed.
- When provided, called at 9 step boundaries: `await progress_cb("stage_name", payload_dict)`
- Payload is built from existing Pydantic models via `.model_dump()`.
- Bridge.py injects a callback that pushes to SSE stream.
- CLI passes nothing (parameter absent = `None`).

**Why not an Event Emitter / Observer Protocol?** YAGNI. One callback parameter serves the single use case. If multiple observers are needed in the future, the callback can be replaced with an emitter — but that's a bridge we don't need to cross today.

### D6: SSE via Manual StreamingResponse (No sse-starlette)

**Decision:** Use FastAPI's built-in `StreamingResponse` with `text/event-stream` content type instead of adding the `sse-starlette` library.

**Rationale:** Zero new Python dependencies. The SSE format is trivially simple (`event: name\ndata: json\n\n`). The enrichment lab's `requirements.txt` already includes `fastapi` and `uvicorn`. Adding `sse-starlette` for ~10 lines of boilerplate savings isn't worth a dependency for a throwaway dev tool.

### D7: Unused Features Are Dormant, Not Stripped

**Decision:** Keep web-katrain features we don't need (timer, AI play, selfplay, game analysis, game report) as-is. Do not actively delete them.

**Rationale:**

- All unused features are modal/tab-gated: they only execute if the user explicitly opens a modal or toggles a mode.
- Zero runtime cost when dormant.
- Active deletion risks breaking inter-component references (components import from each other).
- YAGNI applies to deletion too — stripping unused code is premature optimization.
- If we ever want these features (e.g., AI play for testing refutations), they're already there.

### D8: Pipeline Stage Bar — New React Component

**Decision:** Add `PipelineStageBar.tsx` component (~120 lines) showing all 9 enrichment stages as a horizontal bar above the board. Each stage has states: pending (gray), active (blue pulse), complete (green + timing), error (red).

**Rationale:** This is the only enrichment-specific UI element not present in web-katrain. It's a small, self-contained component that receives stage events via props from SSE and renders a visual progress indicator. Integrates into `Layout.tsx` with ~10 lines of slot placement.

### D9: MoveTree Correctness Coloring — Minimal Extension

**Decision:** Extend `MoveTree.tsx` node rendering (~20 lines) to color-code nodes by correctness: green (correct), red (wrong), orange (refutation). Detection via SGF `C[]` property content ("Correct" prefix → green, "Wrong" prefix → red).

**Rationale:** This is the key enrichment-specific visual feature — distinguishing correct from incorrect paths at a glance. The extension is minimal (checking node properties, changing fill color) and doesn't alter the tree layout algorithm or interaction model.

### D10: Vite Dev Server with FastAPI Proxy

**Decision:** Use Vite's built-in proxy (`vite.config.ts`) to forward `/api/*` requests to the FastAPI bridge on port 8999. The GUI is served by Vite's dev server on port 5173.

**Rationale:** Standard development pattern. Vite handles hot module reload for the React frontend. FastAPI handles Python enrichment pipeline. No CORS issues (same origin via proxy). Production build can use Vite's static output served by FastAPI directly.

### D11: Observation vs. Interactive Mode

**Decision:** Add an `isObserving` flag to `gameStore.ts`. When `true` (pipeline SSE stream active), the board is read-only — click-to-play is disabled, board updates come from SSE events. When `false` (pipeline complete or ad-hoc interactive analysis), full click-to-play is restored.

**Rationale:** During active pipeline enrichment, if the user clicks to play a move on the board, it would conflict with SSE pipeline board updates creating an inconsistent state. Observation mode prevents this. The flag is ~15 lines in gameStore + ~5 lines in GoBoard click handler (check `isObserving` before `playMove`).

### D12: Concurrent Request Handling — Cancel-Previous

**Decision:** When a new `/api/analyze` request arrives while a previous analysis is in-flight, cancel the previous request. This matches the KaTrain desktop pattern.

**Rationale:** The KataGo subprocess (`SingleEngineManager`) handles one query at a time. Queuing would create unpredictable latency. Rejecting would force the user to wait. Cancel-previous gives immediate responsiveness — the user's latest click is always what gets analyzed.

### D13: SSE Heartbeat for Long-Running Analysis

**Decision:** The `/api/enrich` SSE endpoint emits a `heartbeat` event every 5 seconds during long KataGo analysis phases. This prevents browser `EventSource` timeout on positions that take 30+ seconds to analyze.

**Rationale:** Without heartbeat, the browser may close the SSE connection during extended KataGo analysis (e.g., complex positions at 500+ visits). A periodic heartbeat keeps the connection alive with zero overhead.

---

## Consequences

### Positive

- GUI gets full interactive play + KaTrain-quality visuals with ~500 lines of changes
- CLI continues to work identically — `rm -rf gui/` is a complete rollback
- Analysis quality in GUI matches CLI (same KataGo model, same engine)
- All web-katrain features available immediately: board themes, score graph, PV overlay, etc.

### Negative

- ~200MB node_modules directory (user explicitly approved)
- Vite build step needed for frontend development
- Some dormant features may confuse developers unfamiliar with web-katrain

### Risks

- KataGo subprocess leak on browser tab close → mitigated by asyncio task cancellation
- Analysis response format mismatch between Python and TypeScript → mitigated by mapping function with unit test
- Upstream web-katrain API breaking changes → mitigated by using a specific commit snapshot

---

> **See also:**
>
> - [Charter](./00-charter.md) — Goals, constraints, acceptance criteria
> - [Plan](./31-plan-revised.md) — Architecture and task breakdown
> - [Governance](./70-governance-decisions.md) — Panel review decisions
