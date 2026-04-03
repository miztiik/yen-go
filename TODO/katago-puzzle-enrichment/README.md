# KataGo Lab — Tsumego Enrichment Workbench

> **Location:** `tools/puzzle-enrichment-lab/`  
> **Status:** Phase A — Planning  
> **Isolation:** This tool is completely independent from `backend/puzzle_manager/`. No cross-imports.

An interactive workbench for testing KataGo-powered puzzle enrichment. Paste an SGF, click Analyze, get validation + refutations + difficulty rating.

## What It Does

| Task            | Description                                              | Output                                |
| --------------- | -------------------------------------------------------- | ------------------------------------- |
| **Validate**    | Confirms KataGo agrees with the SGF's correct first move | ✓/✗ + policy + winrate                |
| **Refutations** | Finds 1-3 plausible wrong moves + punishment sequences   | Wrong moves + refutation PV           |
| **Difficulty**  | Estimates puzzle difficulty from KataGo signals          | Level (novice → expert) + raw metrics |

## Architecture

```
┌──────────────┐     HTTP      ┌──────────────┐    stdin/stdout    ┌──────────────┐
│  Browser UI  │ ──────────►   │  bridge.py   │ ────────────────►  │  KataGo      │
│  (index.html)│   JSON        │  (FastAPI)   │   Analysis JSON    │  (local)     │
│  + BesoGo    │ ◄──────────   │              │ ◄────────────────  │              │
└──────────────┘               └──────────────┘                    └──────────────┘
                                      │
                               ┌──────┴──────┐
                               │  analyzers/ │
                               │  - validate │
                               │  - refute   │
                               │  - difficulty│
                               └─────────────┘
```

## Prerequisites

1. **KataGo binary** — Download from [github.com/lightvector/KataGo/releases](https://github.com/lightvector/KataGo/releases)
2. **KataGo model** — Download from [katagotraining.org/networks/](https://katagotraining.org/networks/)
   - Recommended: `kata1-b15c192` (~40MB) for good accuracy
   - Minimum: `kata1-b10c128` (~15MB) for faster analysis
   - Browser-only: `kata1-b6c96` (~4MB) via TF.js (stretch goal)
3. **Python 3.11+** with `pydantic`, `fastapi`, `uvicorn`, `sgfmill`

## Quick Start

```bash
# 1. Install dependencies
cd tools/puzzle-enrichment-lab
pip install -r requirements.txt

# 2. Configure engine path
cp config.example.json config.json
# Edit config.json: set katago_path and model_path

# 3. Start the bridge
python bridge.py
# → Serving on http://localhost:8999

# 4. Open UI
# Navigate to http://localhost:8999 in your browser
```

## API Endpoints

```
POST /analyze       — Full analysis (validate + refutations + difficulty)
POST /validate      — Correct move validation only
POST /refutations   — Wrong moves + refutation sequences
POST /difficulty    — Difficulty estimate only
GET  /health        — Engine status check
```

All request/response bodies are Pydantic-typed JSON. See `models/` for schemas.

## Design Principles

- **Isolated** — No imports from `backend/puzzle_manager/`
- **Structured payloads** — Pydantic models everywhere; API-ready
- **Clean interfaces** — Every function boundary uses typed models
- **Dual-backend ready** — Same protocol for local engine + browser TF.js
- **Future integration** — Designed so `backend/` can call these functions via adapter

> **See also:**
>
> - [Research Document](../../TODO/katago-puzzle-enrichment/001-research-browser-and-local-katago-for-tsumego.md)
> - [Implementation Plan](../../TODO/katago-puzzle-enrichment/002-implementation-plan-katago-enrichment.md)
