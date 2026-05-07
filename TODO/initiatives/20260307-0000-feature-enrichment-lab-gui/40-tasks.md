# Tasks — Enrichment Lab Visual Pipeline Observer

**Initiative ID:** 20260307-0000-feature-enrichment-lab-gui  
**Selected Option:** OPT-1 (Lightweight Canvas Observer)  
**Last Updated:** 2026-03-07

---

## Task Dependency Graph

```
T1 (directory) ──┐
                  ├──► T3 (bridge.py) ──► T7 (progress_cb hook) ──► T13 (SSE smoke test)
T2 (index.html) ─┘         │
  T10 (styles) ─────────────┤
                            │
T4 (board.js) ─────────────┼──► T8 (SSE client wiring) ──► T11 (CLI --gui flag)
T5 (tree.js) ──────────────┤                                       │
T6 (pipeline.js) ──────────┘                                       ▼
                                                              T12 (disconnect cleanup)
T9 (sgf-input.js) ──────► T8                                       │
                                                                    ▼
                                                              T14 (regression check)
                                                                    │
                                                                    ▼
                                                              T15 (docs update)
```

---

## Tasks

### Phase 1: Scaffolding

| ID  | Task                                                                             | Files                   | Depends | Parallel?   | Effort |
| --- | -------------------------------------------------------------------------------- | ----------------------- | ------- | ----------- | ------ |
| T1  | Create `gui/` directory structure                                                | `gui/`, `gui/static/`   | —       | [P] with T2 | 5 min  |
| T2  | Create `index.html` with module imports, dark theme layout grid, panel structure | `gui/static/index.html` | —       | [P] with T1 | 30 min |

### Phase 2: Core Modules (Parallelizable)

| ID  | Task                                                                                                                                                                                                                                                                                                                                                                                                   | Files                    | Depends | Parallel?         | Effort |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------ | ------- | ----------------- | ------ |
| T3  | Implement `bridge.py` — FastAPI app with `/enrich` SSE endpoint, `/cancel`, `/health`, static file serving. Use manual `StreamingResponse` with `text/event-stream` (NOT `sse-starlette`). Include `asyncio.Task` wrapping for enrichment with cancellation support.                                                                                                                                   | `gui/bridge.py`          | T1      | [P] with T4,T5,T6 | 2h     |
| T4  | Implement `board.js` — Canvas Go board renderer. Port rendering math from GoBoard.tsx (grid, hoshi, coordinates, stones with gradients, eval dots sized by visits and colored by loss, ownership heatmap with OWNERSHIP_COLORS/GAMMA, candidate move labels, last move marker). Public API: `createBoard(canvas, boardSize)`, `updatePosition(data)`, `updateAnalysis(data)`, `updateOwnership(data)`. | `gui/static/board.js`    | T2      | [P] with T3,T5,T6 | 4h     |
| T5  | Implement `tree.js` — Solution/refutation tree renderer. Port layout math from MoveTree.tsx's `layoutMoveTree()`. Canvas/SVG rendering with color-coded nodes: green=correct, red=wrong, gray=unclassified. Click handler for node selection. Public API: `createTree(container)`, `updateTree(sgfTreeData)`, `highlightNode(nodeId)`, `onNodeClick(callback)`.                                        | `gui/static/tree.js`     | T2      | [P] with T3,T4,T6 | 3h     |
| T6  | Implement `pipeline.js` — Pipeline stage bar. Horizontal bar with 9 labeled stages. States: pending (gray), active (blue pulse), complete (green check + timing), error (red X). Rich visual UX — stages shown left-to-right with transitions. Public API: `createPipelineBar(container)`, `setStageActive(name)`, `setStageComplete(name, timing)`, `setStageError(name, error)`.                     | `gui/static/pipeline.js` | T2      | [P] with T3,T4,T5 | 2h     |
| T10 | Implement `styles.css` — Dark theme styling inspired by web-katrain. Layout grid (stage bar top, board left, tree right, input/result bottom). Responsive basics. Stage bar animations (pulse for active).                                                                                                                                                                                             | `gui/static/styles.css`  | T2      | [P] with T3-T6    | 1h     |

### Phase 3: Integration

| ID  | Task                                                                                                                                                                                                                                                                                                                                                | Files                        | Depends     | Parallel? | Effort |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ----------- | --------- | ------ |
| T7  | Add `progress_cb` parameter to `enrich_single_puzzle()`. Insert `if progress_cb is not None: await progress_cb(stage_name, payload_dict)` at each of the 9 step boundaries (using existing `timings` instrumentation points). Ensure default is `None` with zero overhead. Build payload dicts from existing Pydantic models using `.model_dump()`. | `analyzers/enrich_single.py` | T3          | —         | 2h     |
| T8  | Implement `sse-client.js` — Browser SSE client. Connect to `/enrich` SSE stream. Parse events and dispatch to `pipeline.js` (stage updates), `board.js` (position/analysis/ownership), `tree.js` (tree structure updates). Handle connection errors and reconnection.                                                                               | `gui/static/sse-client.js`   | T3,T4,T5,T6 | —         | 1.5h   |
| T9  | Implement `sgf-input.js` — SGF paste textarea + file upload drag-drop. POST to `/enrich` with SGF text. Toggle between input view and observation view.                                                                                                                                                                                             | `gui/static/sgf-input.js`    | T8          | —         | 1h     |

### Phase 4: CLI Integration

| ID  | Task                                                                                                                                                                                                                                     | Files    | Depends  | Parallel? | Effort |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------- | --------- | ------ |
| T11 | Add `--gui` flag to CLI argparse. When set: import `bridge.py`, start FastAPI server on port 8999, open browser. When not set: existing behavior unchanged. Guard import with `if args.gui:` to avoid importing FastAPI when not needed. | `cli.py` | T7,T8,T9 | —         | 1h     |

### Phase 5: Safety & Quality

| ID  | Task                                                                                                                                                                                                                                                                        | Files                      | Depends | Parallel? | Effort |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | ------- | --------- | ------ |
| T12 | Implement disconnect cleanup in `bridge.py` — detect SSE client disconnect via `asyncio.CancelledError`, cancel enrichment task, call `SingleEngineManager.stop()`. Test manually: start enrichment, close tab, verify engine stops.                                        | `gui/bridge.py`            | T11     | —         | 1h     |
| T13 | Write SSE endpoint smoke test — POST `/enrich` with a fixture SGF (use `tests/fixtures/simple_life_death.sgf`), verify SSE events are emitted with correct stage names (`sgf_parse`, `validate`, `refutations`, `difficulty`, `complete`). Verify event data is valid JSON. | `tests/test_gui_bridge.py` | T11     | —         | 1h     |
| T14 | Run existing test suite (`pytest -m "not (cli or slow)"`) and verify all tests pass with the new `progress_cb=None` default. Fix any regressions.                                                                                                                           | —                          | T7      | —         | 30 min |

### Phase 6: Documentation

| ID  | Task                                                                                                                                                                                                         | Files       | Depends | Parallel? | Effort |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ------- | --------- | ------ |
| T15 | Update `tools/puzzle-enrichment-lab/README.md` — add GUI section with usage instructions: `python cli.py enrich --sgf puzzle.sgf --gui`, screenshots of pipeline bar and board, module architecture diagram. | `README.md` | T14     | —         | 30 min |

---

## Effort Summary

| Phase                  | Tasks               | Total Effort |
| ---------------------- | ------------------- | ------------ |
| Phase 1: Scaffolding   | T1, T2              | 35 min       |
| Phase 2: Core Modules  | T3, T4, T5, T6, T10 | 12h          |
| Phase 3: Integration   | T7, T8, T9          | 4.5h         |
| Phase 4: CLI           | T11                 | 1h           |
| Phase 5: Safety & QA   | T12, T13, T14       | 2.5h         |
| Phase 6: Documentation | T15                 | 30 min       |
| **Total**              | **15 tasks**        | **~21h**     |

---

## Parallel Execution Map

```
Time ──────────────────────────────────────────────────────►

Phase 1:  [T1, T2] ████

Phase 2:  [T3] ████████          (bridge.py — Python)
          [T4] ████████████████  (board.js — largest module)
          [T5] ████████████      (tree.js)
          [T6] ████████          (pipeline.js)
          [T10] ████             (styles.css)

Phase 3:              [T7] ████████  (progress_cb hook — after T3)
                          [T8] ██████  (SSE client — after T3-T6)
                              [T9] ████  (SGF input — after T8)

Phase 4:                          [T11] ████  (CLI flag)

Phase 5:                              [T12] ████  (cleanup)
                                      [T13] ████  (smoke test)
                                      [T14] ██    (regression check)

Phase 6:                                      [T15] ██  (docs)
```

---

## Compatibility Strategy

- **No legacy removal** — all changes are additive
- **No backward compatibility concern** — new feature, new files
- **CLI unchanged** — `--gui` flag is opt-in, import guarded
- **Pipeline unchanged** — `progress_cb=None` default, zero overhead
- **Tests unchanged** — existing tests continue to pass
