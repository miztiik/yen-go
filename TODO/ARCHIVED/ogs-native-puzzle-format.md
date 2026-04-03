# OGS-Native Puzzle Format Migration

> **Created:** 2026-02-16
> **Status:** Implemented (2026-02-16)
> **Branch:** `fix/ogs-native-puzzle-format`
> **Scope:** Major refactor — no backward compatibility. Delete all dead code.
> **Rollback:** Feature branch preserves main. Old code in git history.

---

## Problem Statement

We are using goban's `original_sgf` loading path, which triggers `parseSGF()` →
`hoistFirstBranchToTrunk()`. This moves the first variation from `branches[]` to
`trunk_next` at every node. The `puzzle_place` function in goban **only checks
`branches[]`** for opponent auto-play — it ignores `trunk_next`. Result: after the
player places a correct stone, the opponent never auto-responds. The puzzle is stuck.

We applied 4 post-construction monkey-patches to work around `original_sgf` side effects:
1. `engine.phase = "play"` (goban sets `"finished"`)
2. `enableStonePlacement()` (disabled when phase is "finished")
3. `markTreeFromComments(engine.move_tree)` (flags not set by `original_sgf`)
4. `showFirst()` (cursor left at end of trunk)

And the auto-play bug would require a 5th patch (un-hoisting the tree).

**OGS doesn't have these problems** because it uses the structured `initial_state` +
`move_tree` format. That path doesn't call `hoistFirstBranchToTrunk`, doesn't set
`phase = "finished"`, doesn't move cursor, and has `correct_answer`/`wrong_answer`
baked into the JSON.

## Solution

Switch from `original_sgf` to the OGS-native puzzle loading path:
- Convert SGF → `{ initial_state, move_tree, width, height, initial_player }` via `sgfToPuzzle()`
- Pass structured data to goban — zero monkey-patches needed
- Fix `sgfToPuzzle()`'s correct/wrong marking to use `C[]` comments (not trunk position)
- Delete `mark-tree.ts`, consolidate duplicate parsers, clean up dead code

---

## Git Safety Rules (MANDATORY)

```
FORBIDDEN COMMANDS (NEVER USE):
  git stash, git reset --hard, git clean -fd
  git checkout ., git restore .
  git add ., git add -A

SAFE WORKFLOW:
  1. git status --porcelain | grep "^??"   (check untracked files)
  2. git add path/to/specific/file.ts      (stage by explicit path ONLY)
  3. git diff --cached --name-only          (verify staged files)
  4. git checkout -b fix/ogs-native-puzzle-format
  5. git commit -m "description"
  6. git checkout main
  7. git merge --no-ff fix/ogs-native-puzzle-format

PROTECTED DIRECTORIES (DO NOT DELETE):
  external-sources/*/sgf/    — crawler output
  external-sources/*/logs/   — crawl logs
  .pm-runtime/               — pipeline state
```

---

## E2E Testing Strategy

All tests in `frontend/tests/e2e/` using `playwright.e2e.config.ts`.

**Reusable patterns (DO NOT reinvent):**
- `waitForSolverReady(page)` — from `ui-overhaul-audit.spec.ts` line 16
- `page.screenshot({ path: 'test-screenshots/...' })` — manual reference captures
- `toHaveScreenshot()` — Playwright-managed baseline assertions
- `verify-stones.js` pattern — programmatic stone count verification via `window.__gobanInstance`
- Board selectors: `[data-testid="goban-container"]`, `.goban-board-container canvas`

**Screenshot locations:**
- `test-screenshots/before/` — pre-change reference (manual)
- `test-screenshots/after/` — post-change reference (manual)
- `tests/e2e/` snapshots — Playwright-managed baselines (automated)

**New test file:** `tests/e2e/puzzle-autoplay.spec.ts`
- Verifies opponent auto-play fires after correct move
- Verifies stone counts match SGF at move 0
- Verifies correct/wrong feedback events
- Takes screenshots at each step
- Confirmed by 1P Go professional analysis

---

## Implementation Tasks

### Phase 1: Setup & Safety

- [ ] **T1: Create feature branch**
  ```bash
  cd yen-go
  git status --porcelain | grep "^??"
  git checkout -b fix/ogs-native-puzzle-format
  ```

- [ ] **T2: Take "before" screenshots**
  Run E2E screenshot capture for:
  - `/collections/curated-cho-chikun-life-death-intermediate/1`
  - `/collections/curated-cho-chikun-life-death-intermediate/2`
  - `/collections/curated-beginner-essentials/1`
  - `/level/beginner/1`
  Save to `test-screenshots/before/ogs-migration/`

- [ ] **T3: Record baseline test results**
  ```bash
  cd frontend
  npx vitest run 2>&1 | tail -5        # record pass count
  npx tsc --noEmit                      # must be clean
  ```

### Phase 2: Fix sgfToPuzzle() Correct/Wrong Marking

- [ ] **T4: Replace trunk-based marking with comment-based marking**
  File: `frontend/src/lib/sgf-to-puzzle.ts`
  - DELETE: `markSolutionFlags()`, `markRootBranches()`, `markWrongSubtree()`
  - ADD: New `markCorrectWrongFromComments(root: MoveTreeJson)` function:
    1. Walk tree, find leaf nodes where `text?.toLowerCase().includes('correct')`
    2. Walk parent chain from each correct leaf → set `correct_answer = true`
    3. Walk tree again: any non-root node without `correct_answer` → `wrong_answer = true` recursively
  - This supports multiple correct paths (not just trunk)

- [ ] **T5: Consolidate duplicate parsers**
  - `sgf-to-puzzle.ts` has its own `parseSgfToTree()` — DELETE it
  - Import `parseSgfToTree` from `sgf-metadata.ts` instead
  - `sgf-metadata.ts` is the canonical parser (used by `sgf-preprocessor.ts`)

- [ ] **T6: Add parent references to MoveTreeJson traversal**
  The new comment-based marking needs to walk from leaf to root.
  Options:
  a) Build a parent map during traversal: `Map<MoveTreeJson, MoveTreeJson>`
  b) Pass parent as parameter during recursive walk
  Choose (b) — simpler, no extra data structure.

- [ ] **T7: Unit tests for new marking logic**
  File: `frontend/tests/unit/sgf-to-puzzle.test.ts`
  - Test: SGF with `C[Correct!]` on branch → that branch marked correct
  - Test: SGF with `C[Wrong]` on trunk → trunk marked wrong
  - Test: Multiple correct paths → both marked correct
  - Test: No comments → all leaves marked wrong (no correct path)
  - Test: Case-insensitive ("CORRECT", "correct!", "Correct")

### Phase 3: Rewrite Config & Hook

- [ ] **T8: Rewrite `buildPuzzleConfig()` to accept PuzzleObject**
  File: `frontend/src/lib/puzzle-config.ts`
  - Change: `buildPuzzleConfig(rawSgf, options)` → `buildPuzzleConfig(puzzle: PuzzleObject, options)`
  - Set: `initial_state`, `move_tree`, `width`, `height`, `initial_player` from puzzle object
  - Remove: `original_sgf` field
  - Keep: `display_width: 320`, `square_size: "auto"`, `mode: "puzzle"`, all other defaults

- [ ] **T9: Simplify `useGoban()` — delete all monkey-patches**
  File: `frontend/src/hooks/useGoban.ts`
  - ADD: `import { sgfToPuzzle } from '@lib/sgf-to-puzzle'`
  - ADD: `const puzzle = sgfToPuzzle(rawSgf)` before `buildPuzzleConfig`
  - CHANGE: `buildPuzzleConfig(preprocessed.cleanedSgf, opts)` → `buildPuzzleConfig(puzzle, opts)`
  - DELETE: `import { markTreeFromComments } from '@lib/mark-tree'`
  - DELETE: `engine.phase = "play"` workaround (lines ~186-188)
  - DELETE: `enableStonePlacement()` call (lines ~189-191)
  - DELETE: `markTreeFromComments(engine.move_tree)` (lines ~193-195)
  - DELETE: `showFirst()` call (lines ~197-201)
  - DELETE: The entire `try { ... } catch { /* noop */ }` post-construction block
  - Keep: `preprocessSgf()` call for sidebar metadata, event wiring, renderer selection

- [ ] **T10: Update puzzle-config tests**
  File: `frontend/tests/unit/puzzle-config.test.ts`
  - Rewrite all tests for `buildPuzzleConfig(puzzleObj, options)` signature
  - Test: `initial_state` passed through to config
  - Test: `move_tree` passed through to config
  - Test: `width`/`height`/`initial_player` passed through
  - Test: `original_sgf` is NOT in the config
  - Test: `display_width` and `square_size` defaults still present

### Phase 4: Delete Dead Code

- [ ] **T11: Delete `mark-tree.ts`**
  File: `frontend/src/lib/mark-tree.ts` — DELETE entire file
  No longer needed — `correct_answer`/`wrong_answer` baked into `MoveTreeJson`,
  loaded by goban's `unpackMoveTree()` → `loadJsonForThisNode()`.

- [ ] **T12: Delete mark-tree tests**
  Find and delete any test file for `mark-tree.ts`.

- [ ] **T13: Delete temp debug scripts**
  Files in `frontend/test-screenshots/`:
  - DELETE: `inspect-board.js`, `inspect-dom.js`, `inspect-pixels.js`,
    `read-board.js`, `verify-stones.js`, `capture-board.js`, `check-errors.js`
  These were ad-hoc debug scripts, not production tests.

- [ ] **T14: Clean up dead imports**
  Verify no remaining imports of:
  - `markTreeFromComments` from `mark-tree`
  - `original_sgf` usage in puzzle-config
  - Old `parseSgfToTree` from `sgf-to-puzzle` (should now import from `sgf-metadata`)
  Run `npx tsc --noEmit` to catch any broken references.

### Phase 5: E2E Verification

- [ ] **T15: Create puzzle auto-play E2E test**
  File: `frontend/tests/e2e/puzzle-autoplay.spec.ts`
  Tests:
  1. Load Cho Chikun puzzle 1 → verify initial stone count (9 black, 5 white)
  2. Expose goban on window via `addInitScript` → click B19 (correct first move)
  3. Wait 2s → verify opponent auto-played (stone count increased)
  4. Verify `puzzle-correct-answer` event fired (capture via console listener)
  5. Load puzzle again → click wrong move (e.g., C19)
  6. Verify `puzzle-wrong-answer` event fired immediately
  7. Take screenshot at each step

- [ ] **T16: Run full test suite**
  ```bash
  cd frontend
  npx tsc --noEmit                                    # zero type errors
  npx vitest run                                      # all unit tests pass
  npx playwright test --config=playwright.e2e.config.ts  # all E2E pass
  ```

- [ ] **T17: Take "after" screenshots**
  Same pages as T2. Save to `test-screenshots/after/ogs-migration/`
  Visual comparison with before screenshots.

- [ ] **T18: Console error check**
  Verify zero console errors on:
  - `/collections/curated-cho-chikun-life-death-intermediate/1`
  - `/collections/curated-cho-chikun-life-death-intermediate/2`
  - `/collections/curated-beginner-essentials/1`
  - `/level/beginner/1`

- [ ] **T19: 1P Go professional verification**
  For Cho Chikun puzzle 1:
  - Confirm 9 black + 5 white stones at initial position
  - Confirm correct first move is B19 (hane in top-left corner)
  - Confirm opponent auto-responds with W at F18 (blocking)
  - Confirm full sequence plays out to completion
  - Confirm wrong moves are immediately rejected

### Phase 6: Documentation & Commit

- [ ] **T20: Update TODO/ui-ux-overhaul.md**
  - Update UI-032 Phase 0 section: mark `original_sgf` approach as superseded
  - Update pipeline description: `SGF → sgfToPuzzle() → initial_state + move_tree → goban`
  - Mark relevant items as DONE with date

- [ ] **T21: Update frontend/CLAUDE.md**
  Pipeline: `Raw SGF → sgfToPuzzle() → PuzzleObject → goban (initial_state + move_tree)`
  Delete references to `original_sgf`, `markTreeFromComments`, monkey-patches.

- [ ] **T22: Update CLAUDE.md (root)**
  Same pipeline description update.

- [ ] **T23: Update .github/copilot-instructions.md**
  Same pipeline description update.

- [ ] **T24: Commit and merge**
  ```bash
  # Stage ONLY changed files (by explicit path)
  git add frontend/src/lib/sgf-to-puzzle.ts
  git add frontend/src/lib/puzzle-config.ts
  git add frontend/src/hooks/useGoban.ts
  git add frontend/tests/unit/puzzle-config.test.ts
  git add frontend/tests/unit/sgf-to-puzzle.test.ts
  git add frontend/tests/e2e/puzzle-autoplay.spec.ts
  git add TODO/ui-ux-overhaul.md TODO/ogs-native-puzzle-format.md
  git add frontend/CLAUDE.md CLAUDE.md .github/copilot-instructions.md
  # Stage deleted files
  git add frontend/src/lib/mark-tree.ts   # git detects deletion
  # Verify
  git diff --cached --name-only
  # Commit
  git commit -m "fix: switch to OGS-native puzzle format (initial_state + move_tree)

  Replace original_sgf loading with structured PuzzleObject format.
  Eliminates all 4 post-construction monkey-patches.
  Fixes opponent auto-play bug (hoistFirstBranchToTrunk).
  Fixes correct/wrong marking to use C[] comments (not trunk position).
  Deletes mark-tree.ts, consolidates parsers, cleans dead code."

  # Merge to main
  git checkout main
  git merge --no-ff fix/ogs-native-puzzle-format -m "Merge fix/ogs-native-puzzle-format"
  ```

---

## Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `src/lib/sgf-to-puzzle.ts` | MODIFY | Fix correct/wrong marking, import canonical parser |
| `src/lib/puzzle-config.ts` | REWRITE | Accept `PuzzleObject` instead of `rawSgf` |
| `src/hooks/useGoban.ts` | SIMPLIFY | Delete 4 monkey-patches, add `sgfToPuzzle()` call |
| `src/lib/mark-tree.ts` | DELETE | Replaced by baked-in flags in MoveTreeJson |
| `src/lib/sgf-metadata.ts` | KEEP | Canonical parser — no changes |
| `src/lib/sgf-preprocessor.ts` | KEEP | Sidebar metadata — no changes |
| `tests/unit/puzzle-config.test.ts` | REWRITE | New PuzzleObject signature |
| `tests/unit/sgf-to-puzzle.test.ts` | ADD/UPDATE | Comment-based marking tests |
| `tests/e2e/puzzle-autoplay.spec.ts` | CREATE | Auto-play + stone count verification |
| `test-screenshots/*.js` | DELETE | Temp debug scripts |
| `TODO/ui-ux-overhaul.md` | UPDATE | Mark Phase 0 approach as superseded |
| `frontend/CLAUDE.md` | UPDATE | Pipeline description |
| `CLAUDE.md` | UPDATE | Pipeline description |
| `.github/copilot-instructions.md` | UPDATE | Pipeline description |

---

## Why This Is the Right Fix

| Aspect | `original_sgf` (current, broken) | `initial_state + move_tree` (OGS way) |
|--------|----------------------------------|---------------------------------------|
| `hoistFirstBranchToTrunk` | Called → breaks `branches[]` | NOT called |
| `engine.phase` | Set to `"finished"` → needs patch | Stays `"play"` |
| Cursor position | End of trunk → needs `showFirst()` | Stays at root |
| Solution flags | Not set → needs `markTreeFromComments` | Baked in JSON |
| Stone placement | Disabled → needs `enableStonePlacement` | Works out of box |
| Opponent auto-play | BROKEN (branches empty after hoisting) | Works correctly |
| Monkey-patches needed | **5** (including un-hoist) | **0** |

---

*Last Updated: 2026-02-16*
