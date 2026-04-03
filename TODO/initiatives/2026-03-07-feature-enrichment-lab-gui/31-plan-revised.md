# Plan (Revised) — Enrichment Lab GUI (OPT-1R)

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Selected Option:** OPT-1R (yen-go-sensei Fork with Engine Bridge)  
**Supersedes:** Previous `30-plan.md` (OPT-1 based — invalidated by scope change)  
**Last Updated:** 2026-03-07

---

## Architecture

### High-Level Design

```
┌──────────────────────────────────────────────────────────────────────┐
│                  Browser (localhost:5173 — Vite dev)                  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  PipelineStageBar.tsx  [Parse][Frame][Analyze][Validate]...   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐  │
│  │  GoBoard.tsx (UNCHANGED)    │  │  RightPanel.tsx (UNCHANGED)  │  │
│  │  - Interactive play         │  │  - MoveTree.tsx (+ coloring) │  │
│  │  - Eval dots                │  │  - AnalysisPanel.tsx         │  │
│  │  - Ownership heatmap        │  │  - ScoreWinrateGraph.tsx     │  │
│  │  - PV overlay               │  │  - NotesPanel.tsx            │  │
│  │  - Board themes             │  │                              │  │
│  │  - Region selection         │  │                              │  │
│  │  - Coordinates              │  │                              │  │
│  └─────────────────────────────┘  └──────────────────────────────┘  │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  StatusBar + BottomControlBar + TopControlBar (UNCHANGED)     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Zustand gameStore.ts ──── bridge-client.ts ──── EventSource        │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ POST /analyze (JSON)
                                 │ POST /enrich (SSE stream)
                                 │ POST /cancel
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     FastAPI Bridge (bridge.py)                        │
│                                                                      │
│  POST /analyze   → Run KataGo analysis on position → JSON response  │
│  POST /enrich    → Run full pipeline → SSE stream with stage events │
│  POST /cancel    → Cancel running enrichment                         │
│  GET  /health    → Engine status                                     │
│  Proxy: Vite dev server handles static serving                       │
└──────────────────────┬───────────────────────────────────────────────┘
                       │ async callback / direct KataGo query
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  SingleEngineManager ← enrich_single_puzzle() (existing pipeline)   │
└──────────────────────────────────────────────────────────────────────┘
```

### What Changes vs. What Stays

| Component                         | Status                | Lines | Detail                                          |
| --------------------------------- | --------------------- | ----- | ----------------------------------------------- |
| `GoBoard.tsx`                     | **UNCHANGED**         | ~800  | Full interactive board with all visual features |
| `MoveTree.tsx`                    | **+20 lines**         | ~220  | Add correct/wrong node color-coding             |
| `ScoreWinrateGraph.tsx`           | **UNCHANGED**         | ~200  | Score/winrate dual plot                         |
| `AnalysisPanel.tsx`               | **UNCHANGED**         | ~100  | Analysis info display                           |
| `Layout.tsx`                      | **+10 lines**         | ~160  | Add PipelineStageBar slot                       |
| `StatusBar.tsx`                   | **UNCHANGED**         | ~80   | Move/game info bar                              |
| `BottomControlBar.tsx`            | **UNCHANGED**         | ~120  | Navigation controls                             |
| `TopControlBar.tsx`               | **UNCHANGED**         | ~200  | Analysis/view controls                          |
| `RightPanel.tsx`                  | **UNCHANGED**         | ~250  | Tabbed side panel                               |
| `gameStore.ts`                    | **~50 lines changed** | ~3000 | Replace engine client calls with bridge-client  |
| `engine/engine.worker.ts`         | **DELETED**           | -300  | TF.js worker removed                            |
| `engine/katago/`                  | **DELETED**           | -3000 | In-browser KataGo engine removed                |
| `engine/bridge-client.ts`         | **NEW**               | ~150  | Bridge to Python FastAPI                        |
| `components/PipelineStageBar.tsx` | **NEW**               | ~120  | Pipeline stage visualization                    |
| `bridge.py`                       | **NEW**               | ~200  | FastAPI server                                  |
| All `utils/`                      | **UNCHANGED**         | ~1500 | Game logic, SGF, themes, etc.                   |
| All `types.ts`                    | **UNCHANGED**         | ~150  | Type definitions                                |

### File Structure

```
tools/puzzle-enrichment-lab/gui/
├── bridge.py                  # FastAPI server (NEW ~200 lines)
├── package.json               # Copied from yen-go-sensei (deps adjusted)
├── vite.config.ts             # Copied (proxy added for FastAPI)
├── tsconfig.json              # Copied
├── tsconfig.app.json          # Copied
├── tsconfig.node.json         # Copied
├── tailwind.config.cjs        # Copied
├── index.html                 # Copied
├── src/
│   ├── App.tsx                # Copied
│   ├── main.tsx               # Copied
│   ├── index.css              # Copied
│   ├── types.ts               # Copied
│   ├── vite-env.d.ts          # Copied
│   ├── components/            # ALL copied from yen-go-sensei
│   │   ├── GoBoard.tsx        # UNCHANGED
│   │   ├── MoveTree.tsx       # +20 lines (correctness coloring)
│   │   ├── Layout.tsx         # +10 lines (PipelineStageBar slot)
│   │   ├── PipelineStageBar.tsx  # NEW (~120 lines)
│   │   ├── AnalysisPanel.tsx  # UNCHANGED
│   │   ├── ScoreWinrateGraph.tsx  # UNCHANGED
│   │   ├── ... (all other components copied unchanged)
│   │   └── layout/            # ALL copied unchanged
│   ├── engine/
│   │   └── bridge-client.ts   # NEW (~150 lines) — replaces engine.worker.ts
│   ├── store/
│   │   └── gameStore.ts       # ~50 lines changed (engine calls → bridge)
│   ├── hooks/                 # Copied
│   ├── lib/                   # Copied
│   └── utils/                 # ALL copied unchanged
└── public/                    # Copied (board themes, sounds, katrain assets)
```

---

## Engine Bridge Design

### `bridge-client.ts` (~150 lines)

Implements the same interface shape as `KataGoEngineClient`:

```typescript
// Replaces getKataGoEngineClient()
export async function analyzePython(request: {
  board: BoardState;
  rules: GameRules;
  komi: number;
  moves: Move[];
  visits: number;
  // ... same shape as KataGoAnalysisPayload
}): Promise<AnalysisResult> {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  const data = await response.json();
  return mapKataGoResponseToAnalysisResult(data);
}
```

### `bridge.py` (~200 lines)

```python
# FastAPI app
app = FastAPI()

@app.post("/api/analyze")
async def analyze_position(request: AnalysisRequest):
    """Interactive analysis: run KataGo on a single position."""
    response = await engine_manager.analyze(build_request(request))
    return response.model_dump()

@app.post("/api/enrich")
async def enrich_puzzle(request: EnrichRequest):
    """Pipeline observation: run full enrichment with SSE progress."""
    async def event_generator():
        async def on_progress(stage, payload):
            yield f"event: {stage}\ndata: {json.dumps(payload)}\n\n"
        result = await enrich_single_puzzle(
            request.sgf, engine_manager, progress_cb=on_progress
        )
        yield f"event: complete\ndata: {result.model_dump_json()}\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### `gameStore.ts` Changes (~50 lines)

Replace all `getKataGoEngineClient()` calls with `analyzePython()`:

```typescript
// BEFORE (TF.js Web Worker):
const client = await getKataGoEngineClient();
const result = await client.analyze(payload);

// AFTER (Python bridge):
import { analyzePython } from "../engine/bridge-client";
const result = await analyzePython(payload);
```

---

## Risks and Mitigations

| Risk                                          | Severity | Mitigation                                                                                                            |
| --------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------- |
| Engine swap introduces data format mismatch   | Medium   | Bridge-client maps KataGo JSON to same `AnalysisResult` type used by UI. Write one mapping function and unit test it. |
| Vite dev server + FastAPI port conflict       | Low      | Vite proxies `/api/*` to FastAPI (port 8999). Standard Vite proxy config.                                             |
| KataGo subprocess leak on disconnect          | Medium   | Same as before: asyncio task cancellation + engine.stop() in bridge.py                                                |
| Unused yen-go-sensei features cause confusion | Low      | Features are dormant/modal-gated. Document which features are active for enrichment use case.                         |
| Node_modules size (~200MB)                    | None     | User explicitly approved: "200 MB is not a problem"                                                                   |

---

## Rollout and Rollback

### Rollout

1. Copy yen-go-sensei into `tools/puzzle-enrichment-lab/gui/`
2. Replace engine layer, add bridge, add pipeline bar
3. Add `--gui` flag to CLI
4. Add `progress_cb` to `enrich_single_puzzle()`

### Rollback

1. Delete `tools/puzzle-enrichment-lab/gui/` folder
2. Remove `progress_cb` parameter from `enrich_single_puzzle()`
3. Remove `--gui` flag from CLI

---

## Testing Strategy

| Test Type               | Scope                    | Approach                                                             |
| ----------------------- | ------------------------ | -------------------------------------------------------------------- |
| Existing pipeline tests | All enrichment lab tests | Must pass unchanged with `progress_cb=None`                          |
| Bridge endpoint test    | `bridge.py`              | 1 smoke test: POST /api/analyze with position, verify response shape |
| Engine mapping test     | `bridge-client.ts`       | 1 unit test: verify KataGo JSON → AnalysisResult mapping             |
| Interactive play        | GoBoard.tsx              | Manual QA: click to play, navigate, verify analysis overlay          |
| Pipeline observation    | PipelineStageBar         | Manual QA: run enrichment, verify stage progression                  |

---

> **See also:**
>
> - [Charter](./00-charter.md) — Updated goals, constraints
> - [Revised Options](./26-options-revised.md) — OPT-1R analysis
> - [Governance](./70-governance-decisions.md) — Three governance decisions
> - [Tasks](./40-tasks.md) — Revised task breakdown
