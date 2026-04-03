# Architecture Overview

> **See also**:
>
> - [How-To](../how-to/) — Step-by-step guides
> - [Concepts](../concepts/) — Cross-cutting topics
> - [Reference](../reference/) — Configuration lookup

**Last Updated**: 2026-03-14

Yen-Go is a **static-first, zero backend** Go (Baduk) tsumego puzzle platform.

## Target Architecture

The SQLite-based query architecture establishes these contracts for routing and replay:

- Canonical routes: `/contexts` and `/search`.
- No standalone `/puzzles/{id}` canonical route.
- Compact filter keys: `l`, `t`, `c`, `q`.
- Pagination/navigation term: `offset` (not `cursor`).
- `id` query param identifies the currently rendered puzzle for troubleshooting/replay.
- Public `id` must be a stable identifier; raw storage hashes are not part of the public URL contract.
- DB version is required for deterministic replay as datasets evolve.
- Quality dimension `q` is in-scope.

## System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BUILD TIME (CI/Local)                       │
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│  │   Sources   │────▶│   Puzzle    │────▶│   Static    │          │
│  │ (SGF files) │     │   Manager   │     │   Output    │          │
│  └─────────────┘     └─────────────┘     └─────────────┘          │
│                             │                   │                  │
│                             ▼                   ▼                  │
│                      staging/ingest/    yengo-puzzle-collections/    │
│                      staging/analyzed/       sgf/, views/          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │ GitHub Pages Deploy
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         RUNTIME (Browser)                           │
│                                                                     │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐          │
│  │   Frontend  │────▶│ SGF Parser  │────▶│   Board     │          │
│  │   (Preact)  │     │  (Browser)  │     │  Renderer   │          │
│  └─────────────┘     └─────────────┘     └─────────────┘          │
│         │                                        │                 │
│         ▼                                        ▼                 │
│  ┌─────────────┐                         ┌─────────────┐          │
│  │ localStorage│                         │   Canvas    │          │
│  │  (Progress) │                         │   Board     │          │
│  └─────────────┘                         └─────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Principles ("Holy Laws")

| Principle                | Description                                                 |
| ------------------------ | ----------------------------------------------------------- |
| **Zero Runtime Backend** | Static files only. No APIs, databases, or servers.          |
| **Local-First**          | User data in `localStorage` only.                           |
| **Centralized Config**   | All config in `config/` (levels, tags, logging).            |

## Components

| Component      | Location                    | Technology                 |
| -------------- | --------------------------- | -------------------------- |
| Frontend       | `frontend/`                 | Preact + TypeScript + Vite |
| Puzzle Manager | `puzzle_manager/`           | Python 3.11+               |
| Configuration  | `config/`                   | JSON files                 |
| Output         | `yengo-puzzle-collections/` | SGF + JSON views           |

## Documentation

### System-Wide

- [System Overview](system-overview.md) — Static-first design, data flow, principles
- [Database Deployment Topology](database-deployment-topology.md) — Database deployment contract (DECIDED: Repo-static)

### Backend

- [Backend Overview](backend/README.md) — Pipeline architecture index
- [Pipeline](backend/pipeline.md) — 3-stage design (ingest→analyze→publish)
- [Adapters](backend/adapters.md) — Source-specific fetch logic
- [SGF](backend/sgf.md) — SGF handling and Y\* properties
- [Integrity](backend/integrity.md) — Validation, rollback, cleanup
- [Enrichment](backend/enrichment.md) — Level/tag/hint generation

### Frontend

- [Frontend Overview](frontend/README.md) — Preact structure index
- [Overview](frontend/overview.md) — Technology stack, PWA, data flow
- [Structure](frontend/structure.md) — Component architecture, services
- [Puzzle Solving](frontend/puzzle-solving.md) — Move validation logic
- [State Management](frontend/state-management.md) — localStorage patterns
- [Puzzle Modes](frontend/puzzle-modes.md) — Practice, Daily, Rush, Survival
- [Testing](frontend/testing.md) — Vitest + Playwright

## Data Flow

```
Sources (SGF) → Ingest → Analyze → Publish → GitHub Pages → Browser
                  ↓         ↓          ↓
              staging/   staging/   yengo-puzzle-
               raw/     analyzed/   collections/
```

See [Backend: Pipeline](backend/pipeline.md) for details.
