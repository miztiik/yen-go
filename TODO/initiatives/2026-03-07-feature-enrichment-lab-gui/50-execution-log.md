# Execution Log — Enrichment Lab GUI (OPT-1R)

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Option:** OPT-1R (yen-go-sensei Fork with Engine Bridge)  
**Executor:** Plan-Executor agent  
**Last Updated:** 2026-03-08

---

## Intake Validation

| EX-1  | Check                                         | Result                                 |
| ----- | --------------------------------------------- | -------------------------------------- |
| EX-1a | Plan approved (Decision 4, GOV-PLAN-APPROVED) | ✅                                     |
| EX-1b | Task graph in `41-tasks-revised.md`           | ✅ 14 tasks, dependency-ordered        |
| EX-1c | Analysis findings resolved                    | ✅ No unresolved CRITICAL findings     |
| EX-1d | Backward compatibility decision               | ✅ Not required (new additive feature) |
| EX-1e | Governance handover consumed                  | ✅ 8-member panel, unanimous approval  |

---

## Per-Task Execution Log

### Phase 1: Fork & Strip

| EX-2  | Task                             | Status      | Evidence                                                                                                                                                                                                                                                                                                                          |
| ----- | -------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-2a | T1: Copy yen-go-sensei into gui/ | ✅ Complete | Cloned from upstream Sir-Teo/web-katrain, pinned SHA `454f3eae37a39912f1799dc5055d2c23f898998b`, recorded in `gui/UPSTREAM_COMMIT.md`. Copied: `src/`, `public/`, `index.html`, `package.json`, `vite.config.ts`, `tsconfig*.json`, `tailwind.config.cjs`, `vitest.config.ts`. Excluded: `.git/`, `node_modules/`, `dist/`.       |
| EX-2b | T2: Strip TF.js engine layer     | ✅ Complete | Deleted: `src/engine/engine.worker.ts`, `src/engine/katago/` (entire directory), `scripts/` (entire directory). Removed from package.json: `@tensorflow/tfjs`, `@tensorflow/tfjs-backend-wasm`, `@tensorflow/tfjs-backend-webgpu`, `pako`, `@types/pako`. Removed scripts: `fetch:model`, `copy:tfjs-wasm`, `predev`, `prebuild`. |

### Phase 2: Bridge Layer

| EX-3  | Task                                 | Status      | Evidence                                                                                                                                                                                                                                                                    |
| ----- | ------------------------------------ | ----------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-3a | T3: Create bridge-client.ts          | ✅ Complete | `gui/src/engine/bridge-client.ts` (~260 lines). Exports: `BridgeCanceledError`, `isBridgeCanceledError()`, `analyzePython()`, `getEngineStatus()`, `streamEnrichment()`. Cancel-previous with AbortController (ADR D12). 2D territory array conversion from flat ownership. |
| EX-3b | T4: Create bridge.py                 | ✅ Complete | `gui/bridge.py` (~300 lines). FastAPI app with 4 endpoints: POST /api/analyze, POST /api/enrich (SSE), POST /api/cancel, GET /api/health. Manual StreamingResponse SSE (ADR D6). Heartbeat every 5s (ADR D13). Lifespan shutdown handler (T12).                             |
| EX-3c | T5: Add progress_cb to enrich_single | ✅ Complete | `analyzers/enrich_single.py` — added `progress_cb: Callable[[str, dict], Awaitable[None]]                                                                                                                                                                                   | None = None`parameter. 9`await \_notify()` calls at step boundaries: parse_sgf, extract_solution, build_query, katago_analysis, validate_move, generate_refutations, estimate_difficulty, assemble_result, teaching_enrichment. Default None = zero overhead. |

### Phase 3: Store & UI Adaptation

| EX-4  | Task                              | Status      | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ----- | --------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-4a | T6: Adapt gameStore.ts            | ✅ Complete | Replaced imports: `analyzePython`, `isBridgeCanceledError`, `getEngineStatus` from bridge-client. 6 analyze call sites converted (selfplay, evaluateBatch, fast analysis, full analysis, runAnalysis, AI move). 3 error handler swaps. Inline constants `ENGINE_MAX_VISITS = 1_000_000`, `ENGINE_MAX_TIME_MS = 300_000`. Also fixed `GameAnalysisModal.tsx` and `SettingsModal.tsx` importing from deleted katago/limits. |
| EX-4b | T7: PipelineStageBar.tsx          | ✅ Complete | ~95 line component. 9 stages array matching pipeline steps. 4 status states (pending/active/complete/error) with Tailwind classes. `createInitialStages()` helper. Integrated into Layout.tsx with `pipelineStages`/`pipelineVisible` state.                                                                                                                                                                              |
| EX-4c | T8: MoveTree correctness coloring | ✅ Complete | Extended MoveTree.tsx node rendering. Reads `node.properties?.C?.[0]`. Green (#16A34A) for "Correct", Red (#DC2626) for "Wrong", Orange (#EA580C) for "Refutation". Falls back to default black/white per player.                                                                                                                                                                                                         |
| EX-4d | T9: Vite proxy config             | ✅ Complete | `proxy: { '/api': 'http://localhost:8999' }` added to server config in `gui/vite.config.ts`.                                                                                                                                                                                                                                                                                                                              |

### Phase 4: Integration & CLI

| EX-5  | Task                        | Status      | Evidence                                                                                                                                                                                                                  |
| ----- | --------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-5a | T10: Integration smoke test | ✅ Complete | Created `gui/test/bridge-integration.test.ts` with vitest tests: bridge-client exports, BridgeCanceledError identification, PipelineStageBar 9 stages with correct keys.                                                  |
| EX-5b | T11: CLI --gui subcommand   | ✅ Complete | Added `gui` subcommand to argparse with --katago (required), --katago-config, --config, --host, --port args. `run_gui()` handler with lazy import of `gui.bridge`. Opens browser via `webbrowser.open()`, starts uvicorn. |

### Phase 5: Safety & Quality

| EX-6  | Task                    | Status      | Evidence                                                                                                                                                                                       |
| ----- | ----------------------- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-6a | T12: Disconnect cleanup | ✅ Complete | `_lifespan()` async context manager in bridge.py. On shutdown: cancels running enrichment task, stops engine manager. Attached via `lifespan=_lifespan` parameter.                             |
| EX-6b | T13: Verify tests pass  | ✅ Complete | `pytest tests/test_enrich_single.py tests/test_cli_overrides.py` — 34 passed, 3 warnings (Pydantic serialization, pre-existing), 0 failures. progress_cb=None default confirmed zero overhead. |

### Phase 6: Documentation

| EX-7  | Task               | Status      | Evidence                                                                                                                                                    |
| ----- | ------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-7a | T14: Docs + README | ✅ Complete | Created `gui/README.md` with Quick Start, Architecture diagram, Key Files table, Pipeline Stages list, MoveTree Coloring docs, Upstream Tracking reference. |

---

## Deviations and Resolutions

| EX-8  | Deviation                                                                                                                 | Resolution                                                                                                                                        |
| ----- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| EX-8a | bridge-client.ts grew to ~260 lines (plan estimated ~150) due to SSE async generator and complete type mapping            | Acceptable — all functionality is needed, no bloat                                                                                                |
| EX-8b | bridge.py grew to ~300 lines (plan estimated ~200) due to lifespan handler and complete position conversion helpers       | Acceptable — lifespan was T12 requirement                                                                                                         |
| EX-8c | T6 required fixing 2 additional files (GameAnalysisModal.tsx, SettingsModal.tsx) that imported from deleted katago/limits | Fixed inline — replaced imports with local constants                                                                                              |
| EX-8d | D11 (isObserving flag) described in ADR but not tasked in T1-T14                                                          | Fixed in remediation RT-4 + RT-5. `isObserving` added to gameStore.ts, `startEnrichmentObservation()` wires SSE→board, GoBoard click guard added. |

---

## Remediation Execution (Decision 6 — RT-1 through RT-6)

### RT-1: CLI --gui flag on enrich (GAP-1 / AC1)

| EX-9  | Change                                                        | Evidence                                                                                               |
| ----- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| EX-9a | Removed `gui` subparser from `build_parser()`                 | `gui` subcommand no longer recognized (test: `test_no_gui_subcommand`)                                 |
| EX-9b | Added `--gui`, `--host`, `--port` flags to `enrich` subparser | Parser tests pass: `test_gui_flag_parsed`, `test_gui_flag_with_output`, `test_gui_flag_host_port`      |
| EX-9c | Made `--output` default=None (conditionally required)         | Dispatcher validates `--output` required when `--gui` absent. Test: `test_output_required_without_gui` |
| EX-9d | Updated CLI docstring with 3 invocation modes                 | Docstring shows `enrich --gui`, `enrich --output`, `enrich --gui --output`                             |

### RT-2: Subprocess isolation (GAP-3 / D2)

| EX-10  | Change                                                                            | Evidence                                                                          |
| ------ | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| EX-10a | Removed `run_gui()` function (direct `from gui.bridge import app`)                | `run_gui` no longer exists in cli.py                                              |
| EX-10b | Added `_run_enrich_with_gui()` using `subprocess.Popen`                           | Test: `test_run_enrich_with_gui_uses_popen` confirms Popen called                 |
| EX-10c | Added `atexit.register(proc.terminate)` + SIGTERM handler                         | Cleanup code present in `_run_enrich_with_gui()`                                  |
| EX-10d | Updated bridge.py `__main__` with argparse for --katago, --config, --host, --port | bridge.py accepts CLI args via `argparse.ArgumentParser`                          |
| EX-10e | Updated bridge.py `get_engine()` to use CLI overrides                             | `_cli_katago_path`, `_cli_katago_config`, `_cli_config_path` module-level vars    |
| EX-10f | Verified no direct import of gui.bridge in cli.py source                          | Test: `test_no_gui_import_in_run_enrich` confirms `from gui.bridge import` absent |

### RT-3: Enrich \_notify payloads (GAP-2 / AC3)

| EX-11  | Change                                               | Evidence                                                                                 |
| ------ | ---------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| EX-11a | Added `board_state` notify after position extraction | Sends `puzzle_id`, `board_size`, `player_to_move`, `black_stones`, `white_stones`, `sgf` |
| EX-11b | Enriched `build_query` notify                        | Sends `puzzle_id`, `board_size`, `player_to_move`, `num_stones`                          |
| EX-11c | Enriched `generate_refutations` notify               | Sends `puzzle_id`, `correct_move`, `solution_depth`                                      |
| EX-11d | Enriched `teaching_enrichment` notify                | Sends `puzzle_id`, `validation_status`, `refutation_count`, `difficulty_level`           |

### RT-4: isObserving + SSE wiring (GAP-2 / D11)

| EX-12  | Change                                                 | Evidence                                                                                                          |
| ------ | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| EX-12a | Added `isObserving: boolean` to GameStore interface    | gameStore.ts interface extends with field (default false)                                                         |
| EX-12b | Added `enrichmentStage: string \| null` to GameStore   | Tracks current pipeline stage for UI                                                                              |
| EX-12c | Added `startEnrichmentObservation(sgfText)` action     | Uses `streamEnrichment()` SSE async generator, loads board on `board_state` event via `parseSgf()` → `loadGame()` |
| EX-12d | Added `stopEnrichmentObservation()` action             | Sets `isObserving: false`, `enrichmentStage: null`                                                                |
| EX-12e | try/finally ensures `isObserving=false` on exit (RC-3) | In `startEnrichmentObservation()` try/finally block                                                               |
| EX-12f | Imported `streamEnrichment` from bridge-client.ts      | Added to gameStore.ts import                                                                                      |
| EX-12g | Imported `parseSgf` from utils/sgf.ts                  | Added to gameStore.ts import                                                                                      |

### RT-5: GoBoard click guard (D11)

| EX-13  | Change                                                  | Evidence                                                               |
| ------ | ------------------------------------------------------- | ---------------------------------------------------------------------- |
| EX-13a | Added `isObserving` to GoBoard store selector           | Extracted from `useGameStore` selector object                          |
| EX-13b | Added `if (isObserving) return;` guard in `handleClick` | First guard check in handleClick, before `isSelectingRegionOfInterest` |

### RT-6: Tests + Validation

| EX-14  | Change                          | Evidence                                                                       |
| ------ | ------------------------------- | ------------------------------------------------------------------------------ |
| EX-14a | 7 new test cases in test_cli.py | TestGuiFlag (5 tests) + TestSubprocessIsolation (2 tests)                      |
| EX-14b | All 41 CLI tests pass           | `pytest tests/test_cli.py tests/test_cli_overrides.py -v` → 41 passed in 1.83s |
| EX-14c | TypeScript compilation clean    | No errors in gameStore.ts or GoBoard.tsx                                       |
| EX-14d | No Python lint errors           | cli.py, bridge.py, enrich_single.py all clean                                  |

---

## Files Created

| File                                      | Lines | Purpose                                       |
| ----------------------------------------- | ----- | --------------------------------------------- |
| `gui/UPSTREAM_COMMIT.md`                  | 8     | Pinned upstream SHA (ADR D1)                  |
| `gui/src/engine/bridge-client.ts`         | ~260  | Bridge client replacing TF.js engine (ADR D3) |
| `gui/bridge.py`                           | ~300  | FastAPI bridge server (ADR D4)                |
| `gui/src/components/PipelineStageBar.tsx` | ~95   | Pipeline visualization (ADR D8)               |
| `gui/test/bridge-integration.test.ts`     | ~40   | Smoke tests                                   |
| `gui/README.md`                           | ~80   | Documentation                                 |

## Files Modified

| File                                       | Change                                   | Purpose               |
| ------------------------------------------ | ---------------------------------------- | --------------------- |
| `gui/package.json`                         | Removed TF.js deps and scripts           | ADR D3                |
| `gui/src/store/gameStore.ts`               | 6 analyze calls, error handlers, imports | ADR D3                |
| `gui/src/components/GameAnalysisModal.tsx` | Inline constant                          | TF.js removal cleanup |
| `gui/src/components/SettingsModal.tsx`     | Inline constant                          | TF.js removal cleanup |
| `gui/src/components/Layout.tsx`            | PipelineStageBar integration             | ADR D8                |
| `gui/src/components/MoveTree.tsx`          | Correctness coloring                     | ADR D9                |
| `gui/vite.config.ts`                       | Proxy config                             | ADR D10               |
| `analyzers/enrich_single.py`               | progress_cb parameter + 9 notify calls   | ADR D5                |
| `cli.py`                                   | gui subcommand                           | T11                   |

## Files Deleted

| File                                        | Reason                                         |
| ------------------------------------------- | ---------------------------------------------- |
| `gui/src/engine/engine.worker.ts`           | TF.js engine replaced by bridge (ADR D3)       |
| `gui/src/engine/katago/` (entire directory) | TF.js engine replaced by bridge (ADR D3)       |
| `gui/scripts/` (entire directory)           | Model fetch/WASM copy scripts no longer needed |
