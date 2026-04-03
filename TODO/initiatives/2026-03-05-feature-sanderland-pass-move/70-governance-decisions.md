# Governance Decisions: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Last Updated**: 2026-03-05

## Plan Review Gate

- **Decision**: `approve_with_conditions`
- **Status Code**: `GOV-PLAN-CONDITIONAL`
- **Unanimous**: Yes (6/6)

### Conditions (Non-Blocking)

1. **Write initiative artifacts to disk** before beginning execution — **DONE**
2. **Make comment merge strategy explicit** in T2/T3: if SOL move's comment is non-empty, append `" — {Color} passes"`; if empty, set to `"{Color} passes"` — **DONE** (updated in plan and tasks)

### Member Reviews

| Member                     | Domain              | Vote    | Supporting Comment                                                                                                   |
| -------------------------- | ------------------- | ------- | -------------------------------------------------------------------------------------------------------------------- |
| Cho Chikun (9p)            | Classical tsumego   | approve | Pass-as-correct-answer is semantically valid in tesuji dictionaries. `"White passes"` comment is clear for students. |
| Lee Sedol (9p)             | Intuitive fighter   | approve | Converting at adapter boundary is clean. Defensive empty-string check is appropriate at data boundary.               |
| Shin Jinseo (9p)           | AI-era professional | approve | Classic encoding mismatch at adapter boundary. Pass moves are valid SGF and won't break enrichment.                  |
| Ke Jie (9p)                | Strategic thinker   | approve | Pass-answer puzzle has pedagogical value. Scope is well-bounded.                                                     |
| Principal Staff Engineer A | Systems architect   | approve | Architecturally clean. Suggested explicit comment merge strategy (addressed).                                        |
| Principal Staff Engineer B | Data pipeline       | approve | Added comment serves as audit marker. Required artifacts on disk (addressed).                                        |

### Evidence Verified by Panel

- `adapter.py` L588-L604: both sequential and miai paths write raw coords (confirmed)
- `coordinates.py` L77: `is_pass_move("")` returns `True` (confirmed)
- Grep: single `"zz"` occurrence in Sanderland data (confirmed)
- Charter↔Plan↔Tasks traceability: complete (confirmed)

## Handover

- **from_agent**: `Governance-Panel`
- **to_agent**: `Plan-Executor`
- **message**: Plan approved with conditions (both now satisfied). Execute T1→T2+T3→T4→T5. Fix localized to `backend/puzzle_manager/adapters/sanderland/adapter.py` with tests in `tests/adapters/test_sanderland.py`.
- **required_next_actions**:
  1. Implement T1: `_is_pass_coord` helper
  2. Implement T2+T3: update sequential and miai paths
  3. Implement T4: write unit tests
  4. Execute T5: run `pytest -m "not (cli or slow)"` to validate
- **artifacts_to_update**: `status.json` (advance to execute phase)
- **blocking_items**: None (conditions satisfied)

---

## Implementation Review Gate

- **Decision**: `approve`
- **Status Code**: `GOV-REVIEW-APPROVED`
- **Unanimous**: Yes (6/6)
- **Required Changes**: None

### Member Votes

| Member                     | Vote    | Key Comment                                                                                                     |
| -------------------------- | ------- | --------------------------------------------------------------------------------------------------------------- |
| Cho Chikun (9p)            | approve | Pass-as-correct-answer is valid tsumego pedagogy. Comments provide clear instruction.                           |
| Lee Sedol (9p)             | approve | Both code paths handle passes consistently. No hidden logic gap.                                                |
| Shin Jinseo (9p)           | approve | Classic encoding mismatch at adapter boundary. Downstream pipeline already handles `B[]`/`W[]`.                 |
| Ke Jie (9p)                | approve | Pass-answer puzzles have pedagogical value. Zero over-engineering.                                              |
| Principal Staff Engineer A | approve | Architecturally clean. Comment merge strategy explicit and consistent. 9 tests cover decision matrix.           |
| Principal Staff Engineer B | approve | No regressions. 13 pre-existing failures all unrelated. `_is_pass_coord` prevents malformed coords propagating. |

### Evidence Verified

- [x] Implementation matches approved plan (zero deviations)
- [x] 42/42 Sanderland tests pass (9 new + 33 existing)
- [x] 0 new failures in backend suite (2026 pass, 13 pre-existing)
- [x] All 7 acceptance criteria verified by tests
- [x] Only 2 files changed (adapter.py + test_sanderland.py)
- [x] No core module changes
