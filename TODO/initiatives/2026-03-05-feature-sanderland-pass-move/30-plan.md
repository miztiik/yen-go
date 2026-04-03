# Plan: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Last Updated**: 2026-03-05

## Architecture

The fix is entirely in the adapter layer. No core module changes needed.

**Change location**: `_build_solution_tree()` method in `backend/puzzle_manager/adapters/sanderland/adapter.py`

### Design

1. Add a private helper `_is_pass_coord(coord: str) -> bool` that returns `True` for `"zz"` or empty string `""`
2. In the **sequential path** of `_build_solution_tree()`, when a pass is detected:
   - Emit `{color}[]` instead of `{color}[{coord}]`
   - Set comment to `"{Color} passes"` (if existing comment is non-empty, append `" — {Color} passes"`)
3. In the **miai path** of `_build_solution_tree()`, apply the same pass detection and comment logic

### Comment Merge Strategy

| SOL comment field            | Result                                              |
| ---------------------------- | --------------------------------------------------- |
| Empty `""`                   | Set comment to `"White passes"` or `"Black passes"` |
| Non-empty (e.g. `"Correct"`) | Append: `"Correct — White passes"`                  |

## Data Model Impact

None. SGF output format unchanged structurally — `B[]` and `W[]` are valid SGF moves already handled by the downstream parser (`Move.from_sgf(color, "")` creates a pass move).

## Risks & Mitigations

| Risk                                                 | Probability                          | Mitigation                                    |
| ---------------------------------------------------- | ------------------------------------ | --------------------------------------------- |
| Other pass-like coordinates exist in Sanderland data | Low (grep found only `zz`)           | Defensive: also treat empty string as pass    |
| Comment clobbers existing comment from SOL data      | Low (pass moves have empty comments) | Append to non-empty, set on empty             |
| Miai with pass moves is semantically odd             | Very Low                             | Still emit correct SGF; nature of source data |

## Rollout

Clean re-run: `python -m backend.puzzle_manager run --source sanderland`

## Rollback

Revert commit. No data migration needed.

> **See also**:
>
> - [Charter](./00-charter.md) — Goals and acceptance criteria
> - [Tasks](./40-tasks.md) — Implementation checklist
> - [Analysis](./20-analysis.md) — Consistency review
