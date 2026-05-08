# Backend Architecture

> **See also**:
>
> - [Architecture: System Overview](../system-overview.md) — Repo-level design and constraints
>
> - [How-To: Run Pipeline](../../how-to/backend/run-pipeline.md) — Operate the backend pipeline
>
> - [Reference: CLI Quick Reference](../../reference/cli-quick-ref.md) — Command cheat sheet

**Last Updated**: 2026-05-06

The Yen-Go backend is the **Puzzle Manager** — a Python pipeline that processes puzzles from raw SGF to published collections.

## Overview

```text
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

| Document | Purpose |
| ------------------------------------------------------- | -------------------------------------------- |
| [Puzzle Manager](puzzle-manager.md) | Pipeline architecture, components |
| [Stages](stages.md) | 3-stage pipeline: ingest → analyze → publish |
| [Adapters](adapters.md) | Source adapter patterns |
| [Adapter Design Standards](adapter-design-standards.md) | Interface contracts, naming conventions |
| [Adapter Catalog](../../reference/adapters/README.md) | Per-adapter documentation |
| [Data Flow](data-flow.md) | Sources → staging → collections → views |
| [Enrichment](enrichment.md) | Analyze-stage level, tag, hint, and quality design |
| [Hint Architecture](hint-architecture.md) | Progressive hint generation and pedagogy |
| [Inventory Operations](inventory-operations.md) | Publish, rebuild, reconcile, rollback at scale |
| [Testing](testing.md) | Pytest patterns |
| [SGF Architecture](sgf.md) | SGF design decisions and YenGo extensions |

## Technology Stack

| Layer | Technology |
| ----------- | ------------ |
| Language | Python 3.11+ |
| CLI | Click |
| SGF Parsing | KaTrain (pure-Python) |
| Models | Pydantic |
| Testing | pytest |
| Linting | ruff |

## 3-Stage Pipeline

```text
INGEST → ANALYZE → PUBLISH
   ↓         ↓         ↓
staging/  staging/   yengo-puzzle-
 raw/    analyzed/   collections/
```

| Stage | Purpose |
| ------- | ------------------------ |
| INGEST | Fetch + Parse + Validate |
| ANALYZE | Classify + Tag + Enrich |
| PUBLISH | Index + Daily + Output |

See [Stages](stages.md) for details.

## Component Documentation

See [How-To: Run Pipeline](../../how-to/backend/run-pipeline.md) for setup and execution, and [How-To: Troubleshoot](../../how-to/backend/troubleshoot.md) for recovery workflows.
