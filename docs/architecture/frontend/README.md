# Frontend Architecture

> **See also**:
>
> - [Architecture: System Overview](../system-overview.md) — High-level architecture
> - [How-To: Frontend Development](../../how-to/frontend/) — Development guides
> - [Getting Started: Development](../../getting-started/develop.md) — Setup

**Last Updated**: 2026-02-01

The Yen-Go frontend is built with **Preact + TypeScript + Vite**.

## Overview

```
frontend/
├── src/
│   ├── app.tsx           # App entry point
│   ├── components/       # UI components
│   ├── lib/              # Core logic
│   ├── pages/            # Page components
│   ├── services/         # Data services
│   ├── models/           # TypeScript interfaces
│   └── styles/           # CSS
├── public/               # Static assets
└── tests/                # Test suites
```

## Key Documents

| Document                                | Purpose                                    |
| --------------------------------------- | ------------------------------------------ |
| [Overview](overview.md)                 | Technology stack, data flow, PWA features  |
| [Structure](structure.md)               | Component architecture, services pattern   |
| [Puzzle Solving](puzzle-solving.md)     | Move validation against solution trees     |
| [State Management](state-management.md) | localStorage, versioned schemas            |
| [Puzzle Modes](puzzle-modes.md)         | Practice, Daily, Rush, Survival modes      |
| [Testing](testing.md)                   | Vitest unit tests, Playwright visual tests |

## Technology Stack

| Layer     | Technology                         |
| --------- | ---------------------------------- |
| Framework | Preact (React-compatible, lighter) |
| Language  | TypeScript (strict mode)           |
| Build     | Vite                               |
| State     | localStorage                       |
| Styling   | CSS with custom properties         |
| Testing   | Vitest + Playwright                |

## Core Responsibilities

The frontend does:

- Fetch static SGF/DB from configurable data URL (`VITE_DATA_BASE_URL` in production, local path in dev)
- Parse SGF in browser (~5KB parser)
- Render Go board (Canvas, not WebGL)
- Validate moves against solution trees
- Track progress in localStorage

The frontend does NOT:

- Call any backend APIs
- Calculate Go moves
- Run AI inference
- Store data on servers
- Bundle puzzle data into the Pages artifact

## Component Documentation

See [frontend/README.md](../../../frontend/README.md) for detailed setup and development.
