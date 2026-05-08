# Consolidated Backlog

**Last Updated**: 2026-05-08

This document is the docs-native backlog index for pending work themes that still need execution follow-through.

> **See also**:
>
> - [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) — AI-solve and enrichment design
>
> - [Reference: KataGo Enrichment Status](./katago-enrichment-status.md) — current shipped posture and accepted limitations
>
> - [Architecture: Hint Architecture](../architecture/backend/hint-architecture.md) — Hinting direction
>
> - [Architecture: Inventory Operations](../architecture/backend/inventory-operations.md) — Publish-log and trace-search design
>
> - [Architecture: Frontend Overview](../architecture/frontend/overview.md) — Solver and browsing UX context

## Active Backlog Items

| Priority | Topic | Canonical Context | Current Intent |
| --- | --- | --- | --- |
| P0 | AI-solve implementation hardening | [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) | Keep validator behavior, fallback semantics, tier semantics, and docs aligned with the canonical enrichment design. |
| P1 | Hinting unification transition | [Architecture: Hint Architecture](../architecture/backend/hint-architecture.md) | Align backend and lab hint behavior without letting process notes become the canonical source. |
| P1 | Publish-log trace search optimization | [Architecture: Inventory Operations](../architecture/backend/inventory-operations.md) | Add faster lookup support for large publish-log searches while keeping the documented behavior accurate. |
| P1 | KM search optimization follow-through | [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) | Close the remaining KM-derived search-budget, verification, and observability follow-up. |
| P1 | Frontend performance optimizations | [Architecture: Frontend Overview](../architecture/frontend/overview.md) | Land the remaining route splitting, chunking, and startup performance improvements. |
| P2 | Solver UI polish | [Architecture: Puzzle Solving](../architecture/frontend/puzzle-solving.md) | Finish the remaining solver-view interaction and presentation cleanup. |
| P2 | Frontend quality DRY cleanup | [Concepts: Quality](../concepts/quality.md) | Remove duplicated quality metadata and centralize shared definitions. |
| P2 | Browser prototype graduation decision | [Architecture: KataGo Enrichment](../architecture/tools/katago-enrichment.md) | Decide whether the optional browser prototype remains maintained lab code, graduates, or is retired. |
| P2 | Besogo solution tree renderer swap | [Architecture: Besogo Tree Swap Exploration](../architecture/frontend/exploration-besogo-tree-swap.md) | Re-evaluate phased rollout and rollback safety against the current frontend architecture. |

## Notes

- Execution tracking lives outside canonical docs memory. This page records the work themes and their authoritative documentation context.

- This reference page is the single entry point for backlog triage and prioritization.

- AI-solve threshold defaults remain unvalidated by a live KataGo sweep. That caveat is documented in [Reference: KataGo Enrichment Status](./katago-enrichment-status.md); it is an accepted limitation, not an active backlog item.

- The retired enrichment planning bundle has been decomposed into canonical docs; follow-through now belongs on this page and in the linked architecture/reference docs.

- Once work lands, update the canonical docs first and then trim or retire any external execution notes.
