# Study Puzzles

> Last Updated: 2026-05-04

A *study puzzle* is a board position that ships without a recorded solution
tree. The user is meant to look at it, place stones to explore the shape, and
think -- not to "solve" it against a known answer.

## Why they exist

Some collections (notably T-Hero `capturing-races-unsolved/`) ship hundreds of
real, useful tsumego positions that simply have no machine-gradable solution.
Rejecting them would lose pedagogical value. Treating them as normal puzzles
would mean every click registers as "wrong".

## How they get into the pipeline

The validator gates puzzles by `min_solution_depth`
(`config/puzzle-validation.json`). With the default value `0`, a puzzle whose
SGF has no answer variations is accepted, hashed, classified, tagged, and
published like any other. Its `cx_solution_len`, `cx_depth`, and
`cx_unique_resp` are all `0`.

Set `min_solution_depth: 1` to revert to strict-only ingest.

## How the frontend recognises them

`sgfToPuzzle()` (`frontend/src/lib/sgf-to-puzzle.ts`) inspects the parsed
move-tree. If the root sentinel has no `trunk_next` and no `branches`, the
returned `PuzzleObject` carries `mode: 'study'`. Otherwise `mode: 'solve'`.

The exported `isStudyMode(puzzle)` predicate is the single canonical check.

## How the solver renders them

When `mode === 'study'`:

- `usePuzzleState` initial status is `'study'` instead of `'solving'`.

- Stone placements only fire stone-click sound + `MOVE_PLACED`. No

  wrong/correct/complete dispatch, no shake animation, no red/green overlay,
  no failure or success sound.

- A neutral inline banner reads `Study position -- explore freely. No

  recorded solution.`

- Undo and reset still work and keep status at `'study'`.

## Future work

- Hint/Review buttons are still rendered as in solve mode. They have nothing

  to act on for study puzzles; revisit when a real friction point appears.

- Daily picker, rush mode, and stats counters do not yet exclude study

  puzzles. Add `cx_solution_len > 0` filters there if/when those modes start
  surfacing them in user-visible ways.

- AI-generated solutions could promote a study puzzle into a solve puzzle

  by adding a `trunk_next` -- no schema change needed; `mode` flips
  automatically on next parse.

## See also

- `config/puzzle-validation.json` -- the gate

- `frontend/src/lib/sgf-to-puzzle.ts` -- the parser + predicate

- `frontend/src/hooks/usePuzzleState.ts` -- the state machine

- `docs/architecture/backend/source-ingest-db.md` -- ingest skip-reason persistence
