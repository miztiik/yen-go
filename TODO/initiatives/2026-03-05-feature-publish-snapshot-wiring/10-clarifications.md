# Clarifications: Publish Snapshot Wiring

**Last Updated**: 2026-03-05

---

## Q1: Is backward compatibility required, and should old code be removed?

**Answer**: No backward compatibility required. Remove old code entirely.

**Rationale**: The frontend is snapshot-only (`snapshotService.ts`, `useShardFilters`). Legacy view files are not consumed by any component. Architecture docs already describe snapshot output as the expected behavior.

## Q2: Are there any consumers of legacy view files?

**Answer**: No. The frontend consumes snapshots exclusively. No CI scripts or tooling reads `views/by-level/` etc.

## Q3: Should existing `views/` directory in yengo-puzzle-collections be cleaned up?

**Answer**: Out of scope for this initiative. One-time manual cleanup can be done separately.
