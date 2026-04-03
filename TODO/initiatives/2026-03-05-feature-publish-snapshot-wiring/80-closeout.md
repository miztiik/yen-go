# Closeout: Wire SnapshotBuilder into Publish Stage

**Initiative**: 2026-03-05-feature-publish-snapshot-wiring  
**Type**: Feature (wiring regression fix)  
**Closed**: 2026-03-05

---

## Outcome

**SUCCESS** — All acceptance criteria met. Publish stage now produces snapshot-centric shard output consumed by the frontend.

## Deliverables

| Deliverable                                                                                     | Status |
| ----------------------------------------------------------------------------------------------- | ------ |
| SnapshotBuilder wired into publish stage                                                        | Done   |
| Legacy view code removed (\_update_indexes, \_update_indexes_flat, \_update_collection_indexes) | Done   |
| Incremental publish with merge-by-p dedup                                                       | Done   |
| Slug-based inventory counters                                                                   | Done   |
| All 7 snapshot wiring tests pass                                                                | Done   |
| No new test regressions (2030 pass, 9 pre-existing failures)                                    | Done   |

## Files Changed

- `backend/puzzle_manager/stages/publish.py` — sole file modified (−322 net lines)

## Key Decisions

| Decision               | Choice              | Rationale                                                                      |
| ---------------------- | ------------------- | ------------------------------------------------------------------------------ |
| Backward compatibility | Not required        | Frontend is snapshot-only; legacy views consumed by nothing                    |
| Old code removal       | Yes                 | User confirmed; dead code policy: delete, don't deprecate                      |
| Inventory strategy     | Slug-based counters | InventoryUpdate expects slug-keyed dicts; avoid round-trip through numeric IDs |

## Risks Retired

- **Frontend/backend format mismatch** — eliminated (root cause of the initiative)
- **Dead legacy code maintenance burden** — eliminated (−322 lines)

## Known Residual Items (out of scope)

- Manual cleanup of existing `yengo-puzzle-collections/views/by-*` directories (one-time, not automated)
- 9 pre-existing test failures unrelated to this change (adapter registry, tag taxonomy, inventory manager, publish log, publish robustness)

## Governance Trail

| Gate                  | Decision                                          | Code                 |
| --------------------- | ------------------------------------------------- | -------------------- |
| Options election      | approve_with_conditions                           | GOV-PLAN-CONDITIONAL |
| Plan review           | approve_with_conditions (all conditions resolved) | GOV-PLAN-CONDITIONAL |
| Implementation review | approve (unanimous)                               | GOV-REVIEW-APPROVED  |

## Lessons Learned

1. Existing components (SnapshotBuilder, ShardWriter, IdMaps) were fully implemented and tested — the gap was purely a wiring issue in the publish stage orchestrator.
2. Following the proven pattern from `rollback.py` reduced implementation risk to near zero.
3. Slug-based counters alongside numeric ShardEntry construction kept inventory decoupled without round-trip conversion overhead.
