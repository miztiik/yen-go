# Charter: Sanderland Pass Move Handling

**Initiative**: `2026-03-05-feature-sanderland-pass-move`  
**Type**: Feature (Level 1 — Minor)  
**Last Updated**: 2026-03-05

## Goals

1. Sanderland adapter correctly converts `"zz"` coordinates to SGF-standard pass moves (`B[]`/`W[]`)
2. Pass moves include a descriptive comment ("White passes" / "Black passes")
3. Previously failing puzzle (Suteishi02_17-18) successfully ingests after fix

## Non-Goals

- Handling `"tt"` detection in the adapter (not present in Sanderland data; already handled by the SGF parser)
- Modifying core SGF parser or `Point` validation logic
- Changing any other adapter
- Re-processing historical data (clean re-run is acceptable)

## Constraints

- Fix is localized to `backend/puzzle_manager/adapters/sanderland/adapter.py`
- Must not change core modules (`coordinates.py`, `primitives.py`, `sgf_parser.py`)
- Must follow existing `is_pass_move()` conventions from `core/coordinates.py` (empty string = pass)
- Must include unit tests (project non-negotiable)

## Acceptance Criteria

1. `_build_solution_tree([["W", "zz", "", ""]])` produces `;W[]C[White passes]`
2. `_build_solution_tree([["B", "zz", "", ""]])` produces `;B[]C[Black passes]`
3. `_build_solution_tree([["B", "cd"], ["W", "zz"], ["B", "ef"]])` produces `;B[cd];W[]C[White passes];B[ef]`
4. Multi-move solutions containing pass moves are preserved in full
5. The puzzle `Suteishi02_17-18.json` successfully ingests instead of failing
6. Existing tests still pass
7. New unit tests cover pass detection in both sequential and miai paths

> **See also**:
>
> - [Clarifications](./10-clarifications.md) — User decisions
> - [Plan](./30-plan.md) — Technical design
> - [Tasks](./40-tasks.md) — Implementation checklist
