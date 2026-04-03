# Backend Architecture

The Yen-Go backend is the **Puzzle Manager** — a Python pipeline that processes puzzles from raw SGF to published collections.

## Overview

```
puzzle_manager/
├── src/puzzle_manager/
│   ├── adapters/         # Source adapters
│   ├── core/             # Core utilities
│   ├── models/           # Data models
│   ├── stages/           # Pipeline stages
│   ├── cli.py            # CLI entry point
│   └── pipeline.py       # Orchestrator
├── config/               # Local config overrides
├── staging/              # Processing directories
├── state/                # Pipeline state
└── tests/                # Test suite
```

## Key Documents

| Document                                                | Purpose                                      |
| ------------------------------------------------------- | -------------------------------------------- |
| [Puzzle Manager](puzzle-manager.md)                     | Pipeline architecture, components            |
| [Stages](stages.md)                                     | 3-stage pipeline: ingest → analyze → publish |
| [Adapters](adapters.md)                                 | Source adapter patterns                      |
| [Adapter Design Standards](adapter-design-standards.md) | Interface contracts, naming conventions      |
| [Adapter Catalog](adapters/README.md)                   | Per-adapter documentation                    |
| [Data Flow](data-flow.md)                               | Sources → staging → collections → views      |
| [Testing](testing.md)                                   | Pytest patterns                              |
| [SGF Architecture](sgf.md)                              | SGF design decisions and YenGo extensions    |

## Technology Stack

| Layer       | Technology   |
| ----------- | ------------ |
| Language    | Python 3.11+ |
| CLI         | Click        |
| SGF Parsing | KaTrain (pure-Python) |
| Models      | Pydantic     |
| Testing     | pytest       |
| Linting     | ruff         |

## 3-Stage Pipeline

```
INGEST → ANALYZE → PUBLISH
   ↓         ↓         ↓
staging/  staging/   yengo-puzzle-
 raw/    analyzed/   collections/
```

| Stage   | Purpose                  |
| ------- | ------------------------ |
| INGEST  | Fetch + Parse + Validate |
| ANALYZE | Classify + Tag + Enrich  |
| PUBLISH | Index + Daily + Output   |

See [Stages](stages.md) for details.

## Component Documentation

See [puzzle_manager/README.md](../../puzzle_manager/README.md) for setup and development.
