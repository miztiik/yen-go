# Board State & Coordinate System Design (Deprecated)

> **See also**:
>
> - [Architecture: Goban Integration](./goban-integration.md) - Canonical frontend board architecture (current standard)
> - [Architecture: Go Rules Engine](./go-rules-engine.md) - Move validation and rules behavior
> - [Architecture: SVG Board](./svg-board.md) - Rendering details for non-goban board layers

**Last Updated**: 2026-03-09
**Spec Reference**: 122-frontend-comprehensive-refactor (historical)

---

## Status

This document is deprecated and retained only as a historical record.

- Active authority: `docs/architecture/frontend/goban-integration.md`
- Do not use this file as implementation guidance for new frontend work
- Legacy coordinate/state decisions previously documented here are superseded by the goban-based architecture

---

## Historical Scope

This document previously described a pre-goban board-state model, including custom coordinate conventions, board-grid storage patterns, and migration guidance.

Those details are intentionally removed to avoid conflict with the current architecture.

For any active implementation or refactor decision, follow:

- `docs/architecture/frontend/goban-integration.md`
- `docs/architecture/frontend/go-rules-engine.md`

---

## Migration Note

If you encounter references to this file in older specs, comments, or TODOs, treat them as historical context only and migrate decisions to the goban integration model.
