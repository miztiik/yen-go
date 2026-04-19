# System Overview: Static-First Architecture

> **See also**:
>
> - [Architecture: Backend](./backend/) — Pipeline and adapters
> - [Architecture: Frontend](./frontend/) — Browser application
> - [Architecture: Database Deployment Topology](./database-deployment-topology.md) — Database deployment contract (DECIDED: Repo-static)
> - [Architecture: Index](./README.md) — Architecture documentation map
> - [Concepts: SQLite Index Architecture](../concepts/sqlite-index-architecture.md) — Canonical terminology reference
> - [Getting Started](../getting-started/) — Setup guides

**Last Updated**: 2026-03-14

Yen-Go follows a **static-first, zero backend** architecture. This document explains why and how.

## Target Architecture

The following contracts are established for the SQLite-based query architecture:

- Canonical routes are `/contexts` and `/search`.
- No standalone `/puzzles/{id}` canonical route.
- Compact filter keys are `l`, `t`, `c`, `q`.
- URL navigation uses `offset` (not `cursor`).
- `id` query param is for currently rendered puzzle identity in troubleshooting/replay.
- Public `id` must remain a stable identifier; raw storage hashes are not exposed as URL contract.
- DB version enables deterministic replay across evolving datasets.
- Quality dimension `q` is in-scope.

## Why Static-First?

| Benefit                 | Explanation                                 |
| ----------------------- | ------------------------------------------- |
| **Free hosting**        | GitHub Pages costs $0                       |
| **Zero infrastructure** | No servers, databases, or DevOps            |
| **Offline capable**     | Works as a PWA without internet             |
| **Fast**                | CDN-served static files are inherently fast |
| **Reliable**            | No backend = no backend failures            |

## Build-Time vs Runtime

### Build-Time (CI/Local)

Everything that can be pre-computed is pre-computed:

- Puzzle validation
- Solution tree generation
- Difficulty classification
- Technique tagging
- Hint generation
- Index creation

### Runtime (Browser)

The browser only does:

- Fetch static files (SGF, JSON)
- Parse SGF (~5KB parser)
- Render Go board (Canvas)
- Validate moves against solution tree
- Track progress (localStorage)

## What's NOT Allowed at Runtime

| ❌ Forbidden               | ✅ Alternative                         |
| -------------------------- | -------------------------------------- |
| Server API calls           | Pre-fetch static JSON                  |
| Database queries           | localStorage                           |
| Move calculation           | Pre-computed solution trees            |
| Neural network inference   | Heuristic classification at build time |

## Configuration

All configuration is centralized in `config/`:

| File                 | Purpose                    |
| -------------------- | -------------------------- |
| `puzzle-levels.json` | 9-level difficulty system  |
| `tags.json`          | Technique tags and aliases |
| `logging.json`       | Logging configuration      |

Both frontend and backend read from these files — single source of truth.

## Puzzle Storage

SQLite-based storage layout (Deployment Topology: **Repo-static**, decided 2026-02-21):

```
yengo-puzzle-collections/
├── sgf/                          # Puzzle SGF files (content-addressed)
│   ├── 0001/
│   │   └── {hash}.sgf
│   └── 0002/
├── yengo-search.db               # Frontend search + daily schedule index
├── yengo-content.db              # Backend content + dedup
└── db-version.json               # Version pointer
```

Each pipeline publish reads existing entries from `yengo-content.db`, merges with new entries, and rebuilds `yengo-search.db`. The `db-version.json` file is updated atomically with version, puzzle count, and timestamp. Rollback and reconcile operations also trigger a search DB rebuild from remaining content DB entries.

See [SGF Architecture](backend/sgf.md) for format details.

## Performance Targets

| Metric              | Target          |
| ------------------- | --------------- |
| Initial load        | <500KB gzipped  |
| Time to interactive | <3s on 3G       |
| Lighthouse score    | >90             |
| Puzzle file size    | <500 bytes each |
| Index file size     | <50KB each      |

## Scaling

Target architecture supports up to 500,000 puzzles:

- SQLite queries are O(log n) with proper indexes — fast even at scale
- Single DB file (~500 KB for 9K puzzles) loaded once into browser memory
- SGF files are content-addressed and append-only — no duplication
- `db-version.json` enables deterministic versioning across evolving datasets
- Daily challenges stored in `daily_schedule` + `daily_puzzles` tables within `yengo-search.db`
