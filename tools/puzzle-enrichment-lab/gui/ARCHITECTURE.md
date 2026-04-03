# Architecture — Enrichment Lab GUI

**Last Updated:** 2026-03-08

## Component Diagram

```text
┌──────────────────────────────────────────────────────────────┐
│                         App.tsx                              │
│  ┌──────────────┐  ┌────────────────────────────────────┐   │
│  │   Sidebar     │  │          Main Area                 │   │
│  │              │  │                                    │   │
│  │ SgfInput     │  │  GoBoardPanel (GhostBan + overlay) │   │
│  │ EngineSettings│  │  StatusBar                        │   │
│  │ EnrichPanel  │  │  ControlBar                        │   │
│  │              │  │  AnalysisTable                     │   │
│  │              │  │  SolutionTree                      │   │
│  └──────────────┘  └────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```text
SGF Input ─→ parseSgf() ─→ boardMat + solutionTree signals
                              │
                              ▼
                        GoBoardPanel renders board via GhostBan
                              │
User clicks "Start Analysis" ─┼──→ engine-manager.analyze()
                              │         │
                              │    ┌────┴────────┐
                              │    │   browser    │   bridge
                              │    │ engine.worker│   bridge-client
                              │    │ (TF.js)     │   (HTTP)
                              │    └────┬────────┘
                              │         │
                              ▼         ▼
                       analysisResult signal ─→ overlay + AnalysisTable
```

## State Management

All state uses Preact Signals (`@preact/signals`):

| Signal           | Type                 | Purpose                    |
| ---------------- | -------------------- | -------------------------- |
| `boardMat`       | `number[][]`         | Board position (Ki values) |
| `boardSize`      | `number`             | Board size (9/13/19)       |
| `currentPlayer`  | `'B'/'W'`            | Whose turn                 |
| `solutionTree`   | `TreeNode`           | Parsed solution tree       |
| `currentNode`    | `TreeNode`           | Selected tree node         |
| `analysisResult` | `AnalysisResult`     | Latest analysis            |
| `hoveredPV`      | `string[]`           | PV from hovered row        |
| `showAnalysis`   | `boolean`            | Toggle analysis overlay    |
| `showFrame`      | `boolean`            | Toggle problem frame       |
| `engineMode`     | `'browser'/'bridge'` | Engine selection           |
| `engineError`    | `string/null`        | Last error message         |

## Directory Structure

```text
src/
├── app.tsx              # Root layout + keyboard shortcuts
├── main.tsx             # Preact render entry
├── types.ts             # Shared type definitions
├── utils.ts             # getOpponent, publicUrl utilities
├── styles.css           # Dark theme CSS
├── store/
│   └── state.ts         # Preact Signals state store
├── components/
│   ├── GoBoardPanel.tsx  # GhostBan board + analysis/PV/frame overlays
│   ├── StatusBar.tsx     # Turn, score, winrate, visits
│   ├── ControlBar.tsx    # Action buttons + error banner
│   ├── AnalysisTable.tsx # Sortable candidate moves table
│   ├── EngineSettings.tsx# Engine mode + model + visits
│   ├── SgfInput.tsx      # SGF paste/upload/download
│   ├── SolutionTree.tsx  # Interactive SVG tree + auto-play
│   └── EnrichPanel.tsx   # Enrichment pipeline + results
├── engine/
│   ├── engine-manager.ts # Dual-engine selector
│   ├── engine.worker.ts  # TF.js Web Worker
│   ├── analysis-bridge.ts# Worker → GUI type normalizer
│   ├── bridge-client.ts  # HTTP client for Python bridge
│   └── katago/           # 14 copied KataGo engine files
├── sgf/
│   └── parser.ts         # SGF → boardMat + solution tree
└── lib/
    └── frame.ts          # Problem frame computation
```

## Engine Architecture

### Browser Mode (TF.js)

- Web Worker runs KataGo inference
- Backend cascade: WebGPU → WebGL → WASM → CPU
- Model loaded from `public/models/` (fetched via `fetch-models.mjs`)
- Pako decompresses gzipped models

### Bridge Mode (Python)

- HTTP client talks to Python bridge at `:8999`
- Supports analysis, enrichment (SSE), health check, SGF save
- Vite dev proxy routes `/api/*` to bridge

> **See also:**
>
> - [README.md](./README.md) — Setup and usage
> - [GHOSTBAN_INTEGRATION.md](./GHOSTBAN_INTEGRATION.md) — GhostBan API patterns
