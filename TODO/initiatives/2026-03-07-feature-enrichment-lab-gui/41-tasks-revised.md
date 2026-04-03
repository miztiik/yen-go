# Tasks (Revised) — Enrichment Lab GUI (OPT-1R)

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Selected Option:** OPT-1R (yen-go-sensei Fork with Engine Bridge)  
**Supersedes:** Previous `40-tasks.md` (OPT-1 based — invalidated)  
**Last Updated:** 2026-03-07

---

## Task Dependency Graph

```
T1 (copy yen-go-sensei) ──► T2 (strip TF.js engine) ──► T3 (bridge-client.ts)
                                                              │
T4 (bridge.py) ────────────────────────────────────────────── ┤
                                                              │
T5 (progress_cb hook) ────────────────────────────────────────┤
                                                              │
                                                              ▼
                                                        T6 (gameStore.ts engine swap)
                                                              │
T7 (PipelineStageBar.tsx) ────────────────────────────────────┤
T8 (MoveTree correctness coloring) ──────────────────────────┤
T9 (Vite proxy config) ──────────────────────────────────────┤
                                                              │
                                                              ▼
                                                        T10 (integration test)
                                                              │
                                                              ▼
                                                        T11 (CLI --gui flag)
                                                              │
                                                              ▼
                                                        T12 (disconnect cleanup)
                                                              │
                                                              ▼
                                                        T13 (test existing pipeline)
                                                              │
                                                              ▼
                                                        T14 (docs + README)
```

---

## Tasks

### Phase 1: Fork & Strip

| ID  | Task                                                                                                                                                                                                                                                                                                                                                                                                  | Files                                 | Depends | Parallel? | Effort |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------- | --------- | ------ |
| T1  | **Copy yen-go-sensei** into `tools/puzzle-enrichment-lab/gui/`. Copy: `src/`, `public/`, `index.html`, `package.json`, `vite.config.ts`, `tsconfig*.json`, `tailwind.config.cjs`, `vitest.config.ts`. Do NOT copy: `.git/`, `node_modules/`, `dist/`, `test-results/`, `.vite/`.                                                                                                                      | `gui/` (new directory)                | —       | —         | 15 min |
| T2  | **Strip TF.js engine layer.** Delete `src/engine/engine.worker.ts`, `src/engine/katago/` directory entirely. Remove `@tensorflow/tfjs`, `@tensorflow/tfjs-backend-wasm`, `@tensorflow/tfjs-backend-webgpu`, `pako` from `package.json` dependencies. Remove `predev`/`prebuild` scripts that reference `fetch:model` and `copy:tfjs-wasm`. Remove `scripts/` directory (model fetching/WASM copying). | `gui/package.json`, `gui/src/engine/` | T1      | —         | 30 min |

### Phase 2: Bridge Layer (Parallelizable)

| ID  | Task                                                                                                                                                                                                                                                                                                                                                              | Files                                                                                                                                                                                                           | Depends                      | Parallel?      | Effort         |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------------- | -------------- | --- |
| T3  | **Create `bridge-client.ts`** (~150 lines). Implement `analyzePython(request)` function that POSTs position to `/api/analyze` and maps response to `AnalysisResult` type (same shape as `kaTrainAnalysisToAnalysisResult`). Implement `getEngineStatus()` that GETs `/api/health`. Export as drop-in replacement for `getKataGoEngineClient()`.                   | `gui/src/engine/bridge-client.ts`                                                                                                                                                                               | T2                           | [P] with T4,T5 | 2h             |
| T4  | **Create `bridge.py`** (~200 lines). FastAPI app with: `POST /api/analyze` (run KataGo on position, return JSON), `POST /api/enrich` (run full pipeline with SSE progress), `POST /api/cancel` (cancel enrichment), `GET /api/health` (engine status). Use `SingleEngineManager` for KataGo lifecycle. Use manual `StreamingResponse` for SSE (no sse-starlette). | `gui/bridge.py`                                                                                                                                                                                                 | —                            | [P] with T3,T5 | 2.5h           |
| T5  | **Add `progress_cb` to `enrich_single_puzzle()`**. Add `progress_cb: Callable[[str, dict], Awaitable[None]]                                                                                                                                                                                                                                                       | None = None`parameter. Insert`if progress_cb is not None: await progress_cb(stage, payload)` at each of the 9 step boundaries. Build payload dicts from existing Pydantic models. Default None = zero overhead. | `analyzers/enrich_single.py` | —              | [P] with T3,T4 | 2h  |

### Phase 3: Store & UI Adaptation

| ID  | Task                                                                                                                                                                                                                                                                                                                                                                                            | Files                                     | Depends | Parallel?         | Effort |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- | ------- | ----------------- | ------ |
| T6  | **Adapt `gameStore.ts`** (~50 lines changed). Replace all `getKataGoEngineClient()` calls with `analyzePython()` from bridge-client. Replace `isKataGoCanceledError()` with bridge error handling. Remove `KataGoAnalysisPayload` import. Remove `ENGINE_MAX_TIME_MS`, `ENGINE_MAX_VISITS` imports (inline constants or remove). Update `engineStatus` management to use `/api/health` polling. | `gui/src/store/gameStore.ts`              | T3      | —                 | 2h     |
| T7  | **Create `PipelineStageBar.tsx`** (~120 lines). React component showing horizontal pipeline with 9 labeled stages. Each stage: pending (gray), active (blue pulse animation), complete (green + timing), error (red). Receives stage updates via props from SSE events. Uses Tailwind for styling. Place above the board in Layout.tsx.                                                         | `gui/src/components/PipelineStageBar.tsx` | T1      | [P] with T6,T8    | 1.5h   |
| T8  | **Add correctness coloring to MoveTree.tsx** (~20 lines). Extend node rendering: if node has `properties.C` containing "Correct" → green fill. If "Wrong" → red fill. If refutation branch → orange fill. Default remains black/white per player.                                                                                                                                               | `gui/src/components/MoveTree.tsx`         | T1      | [P] with T6,T7    | 30 min |
| T9  | **Configure Vite proxy**. Add proxy rule in `vite.config.ts`: `/api` → `http://localhost:8999`. This lets the Vite dev server forward API calls to the FastAPI bridge.                                                                                                                                                                                                                          | `gui/vite.config.ts`                      | T1      | [P] with T6,T7,T8 | 15 min |

### Phase 4: Integration & CLI

| ID  | Task                                                                                                                                                                                                                                                                                                                             | Files    | Depends     | Parallel? | Effort |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------- | --------- | ------ |
| T10 | **Integration test.** Run `npm install && npm run dev` in `gui/`. Start `bridge.py` on port 8999. Open browser. Verify: board renders, click-to-play works, eval dots appear when analysis runs, ownership heatmap renders, MoveTree navigation works, pipeline stage bar updates when enrichment runs. Fix any breaking issues. | —        | T6,T7,T8,T9 | —         | 2h     |
| T11 | **Add `--gui` flag to CLI.** Add argparse flag. When set: start FastAPI bridge on port 8999 in background thread, print URL. When not set: existing behavior unchanged. Guard import with `if args.gui:` to avoid importing FastAPI/uvicorn when not needed.                                                                     | `cli.py` | T10         | —         | 1h     |

### Phase 5: Safety & Quality

| ID  | Task                                                                                                                                                                                                                                        | Files           | Depends | Parallel?    | Effort |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ------- | ------------ | ------ |
| T12 | **Disconnect cleanup in bridge.py.** Detect SSE client disconnect via `asyncio.CancelledError`. Cancel enrichment task. Call `SingleEngineManager.stop()`. Test manually: start enrichment, close browser tab, verify KataGo process stops. | `gui/bridge.py` | T11     | —            | 1h     |
| T13 | **Verify existing pipeline tests pass.** Run `pytest -m "not (cli or slow)"`. Verify `progress_cb=None` default has zero impact. Fix any regressions.                                                                                       | —               | T5      | [P] with T10 | 30 min |

### Phase 6: Documentation

| ID  | Task                                                                                                                                                                                                                              | Files       | Depends | Parallel? | Effort |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------- | --------- | ------ |
| T14 | **Update README.md** — add GUI section with usage: start bridge (`python bridge.py`), start Vite dev (`cd gui && npm run dev`), open browser. Document `--gui` CLI flag. Note which yen-go-sensei features are active vs dormant. | `README.md` | T13     | —         | 30 min |

---

## Effort Summary

| Phase                      | Tasks          | Total Effort |
| -------------------------- | -------------- | ------------ |
| Phase 1: Fork & Strip      | T1, T2         | 45 min       |
| Phase 2: Bridge Layer      | T3, T4, T5     | 6.5h         |
| Phase 3: Store & UI        | T6, T7, T8, T9 | 4.25h        |
| Phase 4: Integration & CLI | T10, T11       | 3h           |
| Phase 5: Safety & QA       | T12, T13       | 1.5h         |
| Phase 6: Documentation     | T14            | 30 min       |
| **Total**                  | **14 tasks**   | **~16.5h**   |

---

## Parallel Execution Map

```
Time ─────────────────────────────────────────────────────────►

Phase 1:  [T1] ██  [T2] ████

Phase 2:  [T3] ████████          (bridge-client.ts)
          [T4] ██████████        (bridge.py — Python)
          [T5] ████████          (progress_cb hook)

Phase 3:              [T6] ████████    (gameStore.ts engine swap)
                      [T7] ██████      (PipelineStageBar.tsx)
                      [T8] ██          (MoveTree coloring)
                      [T9] █           (Vite proxy)

Phase 4:                      [T10] ████████  (integration)
                                  [T11] ████  (CLI flag)

Phase 5:                              [T12] ████  (cleanup)
          [T13] ██  (pipeline tests — parallel with Phase 4)

Phase 6:                                      [T14] ██  (docs)
```

---

## Key Differences from Previous Plan (OPT-1)

| Aspect            | OPT-1 (Previous)               | OPT-1R (Current)                         |
| ----------------- | ------------------------------ | ---------------------------------------- |
| Board             | Custom canvas (~450 lines new) | GoBoard.tsx (800 lines REUSED)           |
| Tree              | Custom SVG (~180 lines new)    | MoveTree.tsx (200 lines REUSED + 20 new) |
| Framework         | Vanilla JS (no build)          | React + Vite (existing setup)            |
| Total new code    | ~1200 lines                    | ~500 lines                               |
| Total reused code | 0 lines                        | ~5000+ lines                             |
| Interactive play  | No                             | Yes (built-in)                           |
| Tasks             | 15                             | 14                                       |
| Effort            | ~21h                           | ~16.5h                                   |
| Refactor risk     | HIGH (user warned)             | LOW (proven components)                  |
