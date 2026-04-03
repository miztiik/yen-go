# Analysis: Publish Snapshot Wiring

**Last Updated**: 2026-03-05

---

## Findings

### Severity: BLOCKER (resolved)

| #   | Finding                            | Status                                    |
| --- | ---------------------------------- | ----------------------------------------- |
| F1  | Initiative artifacts did not exist | Resolved — created in this planning phase |

### Severity: MEDIUM

| #   | Finding                                                              | Resolution                                                                                                                                                                                                         |
| --- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F2  | Inventory adaptation unspecified                                     | **Resolved**: Committed to slug-based counters approach. Keep `level_slug_counts: dict[str, int]` and `tag_slug_counts: dict[str, int]` alongside ShardEntry construction. Pass to existing `_update_inventory()`. |
| F3  | Integration tests depend on real `config/` files for `IdMaps.load()` | **Accepted**: Tests run from repo root where `config/` is accessible. Document in tasks. If isolated CI is needed later, use `IdMaps.load(config_dir=...)`.                                                        |

### Severity: LOW

| #   | Finding                                      | Resolution                                                                                   |
| --- | -------------------------------------------- | -------------------------------------------------------------------------------------------- |
| F4  | Full snapshot rebuild on every publish run   | **Accepted**: Correctness > speed. Same pattern as rollback. Monitor at scale (>5K puzzles). |
| F5  | Stale comments referencing legacy view paths | Out of scope — cosmetic cleanup can be batched separately.                                   |

## Coverage Map

| Component                              | Covered by Plan      | Covered by Tests                                              |
| -------------------------------------- | -------------------- | ------------------------------------------------------------- |
| ShardEntry construction from SGF props | T3                   | test_first_publish_creates_snapshot                           |
| IdMaps numeric ID resolution           | T2, T3               | test_first_publish_creates_snapshot                           |
| SnapshotBuilder wiring                 | T4                   | test_first_publish_creates_snapshot, test_incremental_publish |
| Incremental merge (dedup by p)         | T4                   | test_incremental_publish                                      |
| Legacy code removal                    | T5                   | test_old_views_not_produced                                   |
| Inventory update compatibility         | T6                   | Existing inventory tests                                      |
| Empty batch handling                   | T4                   | test_empty_batch_no_snapshot                                  |
| Array-of-arrays format                 | T4 (via ShardWriter) | test_shard_pages_array_format                                 |
| Dry-run mode                           | T4                   | Not explicitly tested — existing dry-run tests cover behavior |

## Unmapped Tasks

None. All plan tasks map to charter acceptance criteria.

## Constitution Compliance

| Rule            | Status                                                                     |
| --------------- | -------------------------------------------------------------------------- |
| SOLID (SRP)     | Pass — publish.py delegates to SnapshotBuilder, doesn't implement sharding |
| DRY             | Pass — reuses SnapshotBuilder, ShardWriter, IdMaps, parse_yx               |
| KISS            | Pass — follows exact pattern from rollback.py                              |
| YAGNI           | Pass — no new abstractions or features                                     |
| Buy don't build | Pass — all components pre-existing                                         |
| Tests required  | Pass — pre-written integration tests                                       |
| Config-driven   | Pass — IdMaps loads from config/                                           |
