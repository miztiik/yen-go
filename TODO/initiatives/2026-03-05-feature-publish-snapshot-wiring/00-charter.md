# Charter: Wire SnapshotBuilder into Publish Stage

**Initiative**: 2026-03-05-feature-publish-snapshot-wiring  
**Type**: Feature (wiring regression fix)  
**Last Updated**: 2026-03-05

---

## Problem Statement

The publish stage (`backend/puzzle_manager/stages/publish.py`) writes legacy flat JSON view files (`views/by-level/`, `views/by-tag/`, `views/by-collection/`), but the frontend exclusively consumes the snapshot-centric shard architecture (`active-snapshot.json` → `snapshots/{id}/manifest.json` → `shards/{key}/meta.json` + `page-NNN.json`).

The `SnapshotBuilder` and `ShardWriter` are fully implemented and tested in `core/`, already used by `rollback.py`, but **never wired into the publish stage**. This means every pipeline run produces output the frontend cannot consume.

## Goals

1. Wire `SnapshotBuilder` into publish stage to produce snapshot output
2. Remove legacy view index code (`_update_indexes_flat`, `_update_collection_indexes`, `_update_indexes`)
3. Support incremental publish (merge with existing snapshot entries)
4. Pass existing integration tests (`test_publish_snapshot_wiring.py`)

## Non-Goals

- Cleaning up existing `yengo-puzzle-collections/views/by-*` directories (one-time manual cleanup)
- Modifying `SnapshotBuilder` or `ShardWriter` internals
- Frontend changes (already snapshot-compatible)
- Daily challenge generation (separate flow, untouched)
- Performance optimization of full-rebuild behavior

## Constraints

- Zero runtime backend — maintained (static file output)
- Deterministic builds — maintained
- No new dependencies — all code exists in `core/`
- Follow `rollback.py` pattern for `SnapshotBuilder` usage

## User Decisions

- **Backward compatibility**: NOT required
- **Old code removal**: YES — remove entirely

## Acceptance Criteria

1. `test_publish_snapshot_wiring.py` passes (all 5 tests)
2. `active-snapshot.json` and `snapshots/{id}/` produced after publish
3. `views/by-level/`, `views/by-tag/`, `views/by-collection/` NOT produced
4. Incremental publish merges existing + new entries correctly
5. Inventory statistics still updated correctly
6. `pytest -m "not (cli or slow)"` passes (no regressions)

> **See also**:
>
> - [Architecture: stages](../../../docs/architecture/backend/stages.md) — Expected publish behavior
> - [Concepts: snapshot-shard-terminology](../../../docs/concepts/snapshot-shard-terminology.md) — Shard architecture
> - [Reference: view-index-pagination](../../../docs/architecture/backend/view-index-pagination.md) — Pagination design
