# How-To Guides

> **See also**:
>
> - [Architecture](../architecture/) — Design decisions and rationale
> - [Concepts](../concepts/) — Cross-cutting knowledge
> - [Reference](../reference/) — Configuration lookup

**Last Updated**: 2026-02-01

Step-by-step guides for common tasks.

---

## I want to...

### Backend / Pipeline

| Task                         | Guide                                             |
| ---------------------------- | ------------------------------------------------- |
| Run the puzzle pipeline      | [Run Pipeline](backend/run-pipeline.md)           |
| Create a new source adapter  | [Create Adapter](backend/create-adapter.md)       |
| Configure puzzle sources     | [Configure Sources](backend/configure-sources.md) |
| Monitor the collection       | [Monitor](backend/monitor.md)                     |
| Troubleshoot pipeline errors | [Troubleshoot](backend/troubleshoot.md)           |
| Rollback published puzzles   | [Rollback](backend/rollback.md)                   |
| Clean up staging files       | [Cleanup](backend/cleanup.md)                     |

### Frontend

| Task                     | Guide                                                              |
| ------------------------ | ------------------------------------------------------------------ |
| Set up local development | [Local Development](frontend/local-development.md)                 |
| Build for production     | [Build & Deploy](frontend/build-deploy.md)                         |
| Create UI components     | [Add Components](frontend/add-components.md)                       |
| Visual regression tests  | [Playwright Visual Testing](frontend/playwright-visual-testing.md) |

---

## Guide Index

### Backend Guides

- [Run Pipeline](backend/run-pipeline.md) — Execute the 3-stage pipeline (ingest → analyze → publish)
- [Create Adapter](backend/create-adapter.md) — Build a new source adapter
- [Configure Sources](backend/configure-sources.md) — Set active sources and override settings
- [Monitor](backend/monitor.md) — Inventory, metrics, and audit trail
- [Troubleshoot](backend/troubleshoot.md) — Diagnose and fix common errors
- [Rollback](backend/rollback.md) — Revert published puzzles using publish logs
- [Cleanup](backend/cleanup.md) — Remove staging files and logs
- [Import PDF](backend/import-pdf.md) — *(Future)* Import puzzles from PDF books

### Frontend Guides

- [Local Development](frontend/local-development.md) — Dev server, testing, debugging
- [Build & Deploy](frontend/build-deploy.md) — Production builds, GitHub Pages
- [Add Components](frontend/add-components.md) — Create and test UI components
- [Playwright Visual Testing](frontend/playwright-visual-testing.md) — Visual regression test setup

---

## Guide Conventions

All guides follow this structure:

1. **See also** callout — Related docs
2. **Prerequisites** — What you need before starting
3. **Quick Start** — Fastest path to success
4. **Detailed Steps** — Complete walkthrough
5. **Common Issues** — Troubleshooting tips
