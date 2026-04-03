# Plan — Enrichment Lab Visual Pipeline Observer

**Initiative ID:** 2026-03-07-feature-enrichment-lab-gui  
**Selected Option:** OPT-1 (Lightweight Canvas Observer)  
**Last Updated:** 2026-03-07

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     Browser (localhost:8999)                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Pipeline Stage Bar  [Parse][Frame][Analyze][Validate]  │   │
│  │  [TreeVal][Refute][Difficulty][Assemble][Teaching]      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────┐   │
│  │   Canvas Go Board        │  │  Solution/Refutation     │   │
│  │   - Stones + last move   │  │  Tree (Canvas/SVG)       │   │
│  │   - Eval dots            │  │  - Green = correct       │   │
│  │   - Ownership heatmap    │  │  - Red = wrong           │   │
│  │   - Candidate labels     │  │  - Click to navigate     │   │
│  │   - Coordinates          │  │  - Highlights active     │   │
│  └──────────────────────────┘  └──────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SGF Paste/Upload Area  |  Enrichment Result Panel     │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬────────────────────────────────┘
                                 │ SSE (EventSource)
                                 │ text/event-stream
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Bridge (bridge.py)                   │
│                                                                 │
│  GET  /                 → serve static/index.html               │
│  GET  /static/*         → serve JS/CSS modules                  │
│  POST /enrich           → start enrichment, return SSE stream   │
│  POST /cancel           → cancel running enrichment             │
│  GET  /health           → engine status                         │
│                                                                 │
│  progress_cb(stage, payload) → SSE event push                   │
└──────────────────────┬──────────────────────────────────────────┘
                       │ async callback
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│           enrich_single_puzzle() — existing pipeline            │
│                                                                 │
│  Step 1: Parse SGF                 → cb("sgf_parse", {...})     │
│  Step 2: Extract solution          → cb("solution_extract",{})  │
│  Step 3: Build query (frame+crop)  → cb("query_build", {...})   │
│  Step 4: KataGo analysis           → cb("katago_analyze", {...})│
│  Step 5: Validate correct move     → cb("validate", {...})      │
│  Step 5a: Tree validation          → cb("tree_validate", {...}) │
│  Step 6: Generate refutations      → cb("refutations", {...})   │
│  Step 7: Estimate difficulty       → cb("difficulty", {...})    │
│  Step 8+9: Assemble + Teaching     → cb("complete", {...})      │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
tools/puzzle-enrichment-lab/gui/
├── bridge.py              # FastAPI app (~150 lines)
│   - POST /enrich endpoint with SSE StreamingResponse
│   - Static file serving
│   - Engine lifecycle management
│   - asyncio task cancellation on client disconnect
├── static/
│   ├── index.html         # Main page, module loader (~60 lines)
│   ├── board.js           # Canvas Go board renderer (~450 lines)
│   │   - Grid, hoshi, coordinates
│   │   - Stones with gradients
│   │   - Eval dots (sized by visits, colored by loss)
│   │   - Ownership heatmap (integrated)
│   │   - Candidate move labels (winrate%, visits)
│   │   - Last move marker
│   ├── tree.js            # Solution/refutation tree (~180 lines)
│   │   - Tree layout algorithm (from MoveTree.tsx reference)
│   │   - Color-coded nodes (green/red/gray)
│   │   - Click-to-navigate
│   │   - Highlight active branch during enrichment
│   ├── pipeline.js        # Pipeline stage bar (~120 lines)
│   │   - Horizontal progress indicator
│   │   - Stage states: pending/active/complete/error
│   │   - Timing display per stage
│   ├── sse-client.js      # SSE event handling (~60 lines)
│   │   - EventSource connection
│   │   - Event dispatch to board/tree/pipeline modules
│   │   - Reconnection and error handling
│   ├── sgf-input.js       # SGF paste/upload handling (~80 lines)
│   │   - Textarea paste area
│   │   - File upload drag-drop
│   │   - POST to /enrich endpoint
│   └── styles.css         # Minimal styling (~100 lines)
│       - Dark theme (web-katrain inspired)
│       - Layout grid
│       - Stage bar styling
│       - Responsive basics
```

**Total estimated:** ~1200 lines across all files.

### Module Responsibilities (SRP)

| Module          | Single Responsibility                                | Inputs                                         | Outputs                            |
| --------------- | ---------------------------------------------------- | ---------------------------------------------- | ---------------------------------- |
| `bridge.py`     | Serve GUI + bridge pipeline to SSE                   | HTTP requests, `enrich_single_puzzle()` result | SSE events, static files           |
| `board.js`      | Render Go board with all visual overlays             | Board position data, analysis data, ownership  | Canvas rendering                   |
| `tree.js`       | Render and navigate solution/refutation tree         | SGF tree structure, correctness labels         | Canvas/SVG rendering, click events |
| `pipeline.js`   | Show pipeline stage progression                      | Stage events from SSE                          | DOM updates                        |
| `sse-client.js` | Manage SSE connection and dispatch events            | SSE stream from server                         | Event dispatch to modules          |
| `sgf-input.js`  | Handle SGF input (paste, upload, trigger enrichment) | User input                                     | POST request to /enrich            |

---

## Data Model / Contracts

### SSE Event Format

Each SSE event follows this structure:

```
event: {stage_name}
data: {json_payload}

```

### SSE Event Payloads

| Event Name         | Key Payload Fields                                                                                    | Board Update?                     |
| ------------------ | ----------------------------------------------------------------------------------------------------- | --------------------------------- |
| `sgf_parse`        | `puzzle_id`, `board_size`, `position` (stones), `metadata`                                            | YES — initial board               |
| `solution_extract` | `correct_move_gtp`, `solution_depth`, `has_solution`                                                  | No                                |
| `query_build`      | `framed_position` (stones after frame), `cropped_size`, `crop_offset`                                 | YES — framed board                |
| `katago_analyze`   | `top_moves[]` (gtp, winrate, policy, visits), `ownership[]`, `root_winrate`                           | YES — eval dots + ownership       |
| `validate`         | `status`, `correct_move_gtp`, `katago_agrees`, `validator_used`, `flags`                              | No                                |
| `tree_validate`    | `tree_depth`, `tree_status`                                                                           | No                                |
| `refutations`      | `refutations[]` (wrong_move, refutation_pv, delta), `count`                                           | YES — refutation branches in tree |
| `difficulty`       | `suggested_level`, `level_id`, `composite_score`, `confidence`                                        | No                                |
| `complete`         | `full_result` (AiAnalysisResult dump), `enriched_sgf`, `technique_tags`, `hints`, `teaching_comments` | YES — final enriched SGF in tree  |

### Board Data Format (JSON → Canvas)

```javascript
// Position data sent from Python
{
  "board_size": 19,
  "black_stones": [[2,3], [3,4], ...],  // [x,y] pairs
  "white_stones": [[4,5], [5,6], ...],
  "last_move": [3,4],                    // or null
  "player_to_move": "B"
}

// Analysis overlay data
{
  "candidates": [
    {"gtp": "D4", "x": 3, "y": 15, "winrate": 0.73, "policy": 0.42, "visits": 1200, "points_lost": 0.0},
    {"gtp": "Q16", "x": 15, "y": 3, "winrate": 0.68, "policy": 0.15, "visits": 800, "points_lost": 1.2}
  ],
  "ownership": [0.8, 0.6, -0.3, ...],  // flat array, boardSize*boardSize
  "root_winrate": 0.73
}
```

---

## Risks and Mitigations

| Risk                                               | Severity | Mitigation                                                                                                                                                                                                                           |
| -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| R3: SSE holds KataGo subprocess alive on tab close | Medium   | FastAPI `StreamingResponse` generator checks `asyncio.current_task().cancelled()`. On disconnect, call `SingleEngineManager.stop()`. Wrap enrichment in `asyncio.create_task()` with cleanup handler.                                |
| R4: `progress_cb` affecting pipeline timing        | Low      | Use `if progress_cb is not None: await progress_cb(...)` guard. Async callback is non-blocking. Existing timing measurements use `time.monotonic()` and are unaffected by interleaved awaits. Verify by running existing test suite. |
| R5: Canvas board visual quality gap vs web-katrain | Low      | Extract proven rendering constants and math from GoBoard.tsx (OWNERSHIP_COLORS, OWNERSHIP_GAMMA, eval color thresholds, stone gradient). Reference implementation verifiable side-by-side.                                           |
| R6: Custom tree layout correctness                 | Low      | Use MoveTree.tsx's `layoutMoveTree` algorithm (~40 lines of pure math) as reference. Tree only needs to render ~5-20 nodes for typical tsumego.                                                                                      |

---

## Rollout and Rollback

### Rollout

1. All code in `gui/` subfolder — zero impact on existing functionality
2. `--gui` flag on CLI added via argparse (additive, no existing flags changed)
3. `progress_cb` parameter on `enrich_single_puzzle()` defaults to `None`

### Rollback

1. Delete `tools/puzzle-enrichment-lab/gui/` folder
2. Remove `progress_cb` parameter from `enrich_single_puzzle()` signature
3. Remove `~5` callback call sites in `enrich_single.py`
4. Remove `--gui` flag from CLI argparse

Total rollback: ~10 lines changed in existing files + folder deletion.

---

## Testing Strategy

| Test Type               | Scope                    | Approach                                                                                              |
| ----------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------- |
| Existing test suite     | All enrichment lab tests | Must pass unchanged with `progress_cb=None` (default)                                                 |
| SSE endpoint smoke test | `bridge.py`              | 1 integration test: POST /enrich with fixture SGF, verify SSE events emitted with correct stage names |
| Board/tree rendering    | Visual                   | Manual QA — verify against web-katrain reference screenshot for same position                         |
| Pipeline stage bar      | Visual                   | Manual QA — verify all 9 stages transition correctly                                                  |
| Disconnect cleanup      | `bridge.py`              | Manual test: start enrichment, close browser tab, verify KataGo process stops                         |

---

> **See also:**
>
> - [Charter](./00-charter.md) — Goals, constraints, acceptance criteria
> - [Options](./25-options.md) — Full option analysis
> - [Governance](./70-governance-decisions.md) — Option election decision
> - [Tasks](./40-tasks.md) — Implementation task breakdown
