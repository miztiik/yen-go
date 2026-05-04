# Plan: Study Mode for Puzzles Without Solutions

**Last Updated**: 2026-05-04 (revision 2 — applied Governance-Panel RCs)
**Correction Level**: Level 3 (Multi-file: frontend + config + tests; backend already supports it)
**Status**: Plan only — research complete, awaiting Governance-Panel re-review (revision 2)

> **Handoff prompt**: This plan is self-contained. An agent picking this up should be able to start at §6 (Implementation Tasks) without re-investigating the existing code. All findings in §3–§5 are verified against the current tree.

> **Revision history**:
> - rev 1 (2026-05-04): initial plan
> - rev 2 (2026-05-04): Governance-Panel RCs applied — parse-time classification (RC-3), verifier purity preserved (RC-4), single `isStudyMode()` predicate (RC-5), product decisions locked in §8 (RC-6/7/8), explicit Option B selection (RC-2)

---

## 1. Objective

Allow the pipeline to ingest puzzle SGFs that contain **no solution variations** (i.e., positions with stones but no `;B[...]C[+]` style answer tree) and let users **browse / study** them in the existing Solver UI without the app treating every click as a wrong move.

The motivating dataset: T-Hero's `capturing-races-unsolved/` folder ships 200 capturing-race study positions with no recorded answers. They are real, useful tsumego problems — they just don't have machine-gradable solutions.

---

## 2. Non-Goals

- Building a *new* page or route. Reuse `SolverView`.
- AI-generated solutions for these positions. Out of scope.
- Allowing user-created annotations on study puzzles. Out of scope.
- Changing what "completion" means for solvable puzzles. Out of scope.
- Backend pipeline changes beyond a config flag flip and validator unit tests. The data plumbing already works.

---

## 3. Current State (verified 2026-05-04)

### 3.1 Backend gate (works as designed; one config flip needed)

| Component | File | Behavior |
|---|---|---|
| Validator | [`backend/puzzle_manager/core/puzzle_validator.py`](../backend/puzzle_manager/core/puzzle_validator.py#L382-L395) | When `min_solution_depth > 0`, rejects any puzzle where `puzzle.has_solution == False` with `RejectionReason.NO_SOLUTION` (`"Puzzle has no solution"`). |
| Default config | [`config/puzzle-validation.json`](../config/puzzle-validation.json#L22) | `"min_solution_depth": 1` — strict gate is the current default. |
| Schema | [`config/schemas/puzzle-validation.schema.json`](../config/schemas/puzzle-validation.schema.json#L55) | `min_solution_depth: integer >= 0` already supported. |
| Existing test | [`backend/puzzle_manager/tests/unit/test_puzzle_validator.py`](../backend/puzzle_manager/tests/unit/test_puzzle_validator.py#L278) | T009a confirms `min_solution_depth=0` accepts solution-less puzzles. |
| Per-source DB record | `external-sources/<src>/sgf/.yengo-ingest.sqlite` | 200 t-hero rows currently `status=1 (SKIPPED)` with `skip_reason='Puzzle has no solution'`. Verified via `SELECT skip_reason, COUNT(*) FROM files WHERE status=1 GROUP BY skip_reason`. |

**Bottom line**: Backend already supports this. Set `min_solution_depth: 0` and the puzzles get ingested, hashed, classified, tagged (current YT will be `[capture-race]`), and published like any other.

### 3.2 Frontend behavior with empty `move_tree` (the actual problem)

This is what blocks shipping. Two layers behave differently:

#### Goban / `sgfToPuzzle()` — fine

[`frontend/src/lib/sgf-to-puzzle.ts`](../frontend/src/lib/sgf-to-puzzle.ts#L347) builds a valid `PuzzleObject` even when the SGF has zero children. The returned `move_tree` is:

```ts
{ x: -1, y: -1 }   // root sentinel; no trunk_next, no branches
```

The Goban renders the initial position normally and accepts clicks.

#### Solver — broken

| File | Lines | Issue |
|---|---|---|
| [`SolverView.tsx`](../frontend/src/components/Solver/SolverView.tsx#L306-L308) | status enum is `loading | solving | wrong | complete | review`. No `study` / `view` / `browse` status. |
| [`solutionVerifier.ts`](../frontend/src/services/solutionVerifier.ts#L67-L118) | `verifyMove()` walks `currentNode.move` + `currentNode.branches`. With an empty tree both are absent, so every click hits the final `return { isCorrect: false, feedback: 'incorrect' }`. |
| [`SolverView.tsx`](../frontend/src/components/Solver/SolverView.tsx#L656-L660) | A click→`'wrong'` transition triggers shake animation, red marker, "wrong" sound. |
| Solve-only chrome | Hint button, Review button, completion card — all assume a solution exists. No conditional render path skips them today. |

**Result if we ingest as-is**: 200 puzzles where the user cannot do anything useful — every click is "wrong", review tree is empty, hints crash or show nothing.

### 3.3 What CSS / icons / sounds already exist

These are reusable assets, no new ones needed:

- `--color-correct`, `--color-incorrect` in `frontend/src/styles/colors.css`
- Goban native marker rendering (used today for correct/wrong overlays)
- `audioService` already has stone-place + ambient sounds; we'd just suppress the success/failure sounds

---

## 4. Proposed Approach

### 4.1 Data model — discriminator

Tag study puzzles at publish time with a property the frontend can read. Two options:

| Option | Where the flag lives | Pros | Cons |
|---|---|---|---|
| **A.** New SGF custom property `YS_TYPE[study]` (or extend `YQ`) | In the SGF | Travels with the file; survives any rebuild of `yengo-search.db` | Schema bump + parser update + docs |
| **B.** Derive at runtime from `move_tree` shape after `sgfToPuzzle()` | Frontend only | Zero schema impact; works retroactively for any tree-less SGF | Re-derived on every load (negligible cost) |

**Recommendation: B.** It's a structural fact (no children = no solution = study). Schema-free, no migration, no schema-version bump. If we later want to add metadata (e.g., "study because solution exists but is too long"), we can graduate to A.

#### **Selected: Option B (rev 2)**

**Rationale**: zero schema impact; works retroactively for any tree-less SGF; the structural fact (`move_tree` has no children) is the discriminator. No SGF property bump means no parser update, no schema-version bump, no migration of already-published SGFs.

**Must-hold constraints**:
1. Detection happens **once** at parse time inside `sgfToPuzzle()` and is exposed as `puzzle.mode: 'solve' | 'study'`. Downstream consumers MUST NOT re-derive the discriminator.
2. The `puzzle.mode` field is the only canonical source. A single exported predicate `isStudyMode(puzzle): boolean` wraps it for ergonomic use.
3. If a future need for metadata (e.g., "study because solution too long") arises, graduate to Option A then — not now.

### 4.2 Frontend state — parse-time classification + new status `'study'`

**Where the classification happens (rev 2)**: inside `sgfToPuzzle()` in `frontend/src/lib/sgf-to-puzzle.ts`. After the move tree is built, compute `mode` from tree shape and attach it to the returned `PuzzleObject` extension. This gives every downstream consumer (verifier dispatch, stats, daily picker, rush picker, UI chrome) a single source of truth without re-derivation.

Detection logic (executed once, in the parser):

```ts
const isStudy =
  puzzle.move_tree.x === -1 &&
  puzzle.move_tree.y === -1 &&
  !puzzle.move_tree.trunk_next &&
  !(puzzle.move_tree.branches?.length);

puzzle.mode = isStudy ? 'study' : 'solve';
```

A single exported predicate lives next to the type:

```ts
// frontend/src/types/puzzle-internal.ts (or wherever PuzzleObject lives)
export const isStudyMode = (puzzle: PuzzleObject): boolean =>
  puzzle.mode === 'study';
```

Extend the puzzle status enum:

```ts
type PuzzleStatus = 'loading' | 'solving' | 'wrong' | 'complete' | 'review' | 'study';
```

The loader hook reads `puzzle.mode` and sets initial status to `'study'` when applicable — but it does not derive the discriminator itself.

### 4.3 Solver behavior in `'study'` mode

| Behavior | Solving (today) | Study (new) |
|---|---|---|
| Click on board | Verify against tree → correct/wrong | Place stone, allow free undo |
| **Side to move** (rev 2) | Determined by SGF/tree | **Honor SGF `PL[]` if present; alternate from there. If `PL[]` absent, alternate starting from Black.** |
| Wrong-move shake / red marker | Yes | No |
| Success sound on correct | Yes | No |
| **Hint button** (rev 2) | Enabled | **Visible but disabled**, with `aria-label`/tooltip "Study position — no recorded solution" |
| **Review button** (rev 2) | Enabled (after wrong/complete) | **Visible but disabled**, with `aria-label`/tooltip "Study position — no recorded solution" |
| Solution reveal | Available | Hidden (no tree to reveal) |
| "Complete" detection | When tree exhausted | Never — study mode has no completion |
| Undo / step back | Yes | Yes (more important here) |
| Tag/level reveal timing | After wrong/solved | Visible immediately (no spoiler concern) |
| Status badge in UI | "Solving" / "Solved" | "Study position" badge next to title |

**Why disabled-state instead of hidden (RC-8)**: hidden buttons cause "did the app break?" confusion and break screen-reader navigation continuity. Disabled-with-tooltip preserves the UI rhythm and gives an explicit, discoverable explanation.

**Why honor `PL[]` (RC-7)**: T-Hero capturing-race SGFs encode side-to-move via `PL[]`; ignoring it would invert the puzzle for ~half the corpus. Alternating-from-Black is only the fallback for SGFs that don't specify.

### 4.4 Routing / browsing

No new routes. Study puzzles appear in:

- Collection / source browse pages (T-Hero collection includes them naturally once published)
- Direct puzzle URL (`/p/{content_hash}`)

The browse pages already pull from `yengo-search.db`. Study puzzles will have `cx_solution_len = 0`, `cx_depth = 0`, `cx_unique_resp = 0`. Filters that require depth > 0 (e.g., daily challenge selection, training) should naturally exclude them — verify in §6.

---

## 5. Risk & Edge Cases

| Risk | Severity | Mitigation |
|---|---|---|
| Daily challenge picker accidentally selects a study puzzle | Med | Daily query already filters by `cx_solution_len >= N`; verify and add explicit `> 0` if needed. |
| Rush mode timer + study puzzles | Med | Rush is solve-only; exclude `'study'` puzzles from rush set queries. |
| Stats page counts a study puzzle as "attempted but failed" | Low | Don't write progress entries for study mode (skip the localStorage write). |
| Tag/classify stage produces nonsense for empty trees | Low | Verify in §6.1 that classify doesn't crash on `solution_depth=None`. |
| Search filters by quality/complexity hide all study puzzles | Low | Acceptable — they're a niche; users find them via collection browse. |
| Existing 200 t-hero rows still marked `SKIPPED` after flip | Med | Run `--fresh` for t-hero only; or add a one-shot CLI subcommand to re-evaluate skipped rows (probably overkill — `--fresh` is fine). |

---

## 6. Implementation Tasks

> Pick these up in order. Each task block has a clear acceptance check.

### Task 1 — Backend: enable solution-less ingest (Level 1, ~5 LoC)

**Files**: [`config/puzzle-validation.json`](../config/puzzle-validation.json), changelog entry per project schema-evolution rule.

1. Change `min_solution_depth: 1` → `0`.
2. Bump version + add changelog entry inside the JSON.
3. Run validator unit tests:
   ```powershell
   python -m pytest backend/puzzle_manager/tests/unit/test_puzzle_validator.py -q --no-header --tb=short
   ```
4. Run quick backend regression:
   ```powershell
   python -m pytest backend/ -m "not (cli or slow)" -q --no-header --tb=line
   ```
5. Re-ingest t-hero: `python -m backend.puzzle_manager run --source t-hero --fresh`. Expect ingested ≈ 1000, skipped 0.
6. Confirm published SGFs for the unsolved positions have `YS_TYPE` absent (we're using runtime detection per §4.1) and `cx_solution_len=0`.

**Acceptance**: t-hero `source-status` reports 0 skipped after `--fresh`; full backend test suite green.

### Task 2 — Frontend: parse-time classification + `'study'` status (Level 2, ~30 LoC)

**Files**:
- `frontend/src/lib/sgf-to-puzzle.ts` — compute `mode` from final tree shape, attach to returned `PuzzleObject`
- `frontend/src/types/puzzle-internal.ts` (or wherever `PuzzleObject` / `PuzzleStatus` live) — add `mode: 'solve' | 'study'` to the type, extend `PuzzleStatus` union with `'study'`, export `isStudyMode(puzzle)` predicate
- The loader hook that sets `puzzleState.state.status` — read `puzzle.mode` (do NOT re-derive)
- `frontend/src/components/Solver/SolverView.tsx` — `const isStudyMode = puzzleState.puzzle && isStudyMode(puzzleState.puzzle);`

1. Extend `PuzzleObject` with `mode: 'solve' | 'study'` (required field, set in parser).
2. In `sgfToPuzzle()`, after the move tree is built, compute and attach `mode` per §4.2 logic. Single derivation site.
3. Export `isStudyMode(puzzle)` predicate co-located with the type. This is the ONLY way other modules query the discriminator.
4. Extend `PuzzleStatus` union with `'study'`.
5. Loader hook reads `puzzle.mode` and sets initial status. No re-derivation in the hook.
6. Unit test in `frontend/src/lib/__tests__/sgf-to-puzzle.test.ts` — feed a stones-only SGF, assert `puzzle.mode === 'study'`. Feed a normal SGF, assert `puzzle.mode === 'solve'`.

**Acceptance**:
- New unit test passes.
- Loading a stones-only SGF sets `puzzle.mode === 'study'` and initial status `'study'`.
- Loading a normal SGF leaves `puzzle.mode === 'solve'` and initial status `'solving'`.
- A `grep` for the structural discriminator (`x === -1 && y === -1 && !trunk_next && !branches`) finds it in **only** `sgf-to-puzzle.ts`.

### Task 3 — Frontend: dispatch study mode at the verifier call site (Level 2, ~15 LoC)

**Files**: `frontend/src/components/Solver/SolverView.tsx` (only the post-move handler).

> **Verifier stays untouched** (RC-4). `solutionVerifier.verifyMove()` keeps its current contract — it walks `currentNode.move` + `currentNode.branches` and returns correct/wrong as it does today. Adding a "neutral return" path inside the verifier would be a permanent footgun every future verifier change must remember.

1. In `SolverView.tsx`'s post-move handler (the function that calls `verifyMove()`), add an early branch:
   ```ts
   if (isStudyMode) {
     // Place the stone, swap turn, do not transition status, do not play sounds
     applyStoneToBoard(move);
     return;
   }
   const result = verifyMove(...);  // unchanged
   ```
2. Suppress success/failure sounds when `isStudyMode` is true (gate the existing `audioService` calls).
3. No change to `solutionVerifier.ts`. No new methods, no neutral-result type.

**Acceptance**:
- Click on a study puzzle places a stone, no shake, no red marker, no sound flips, status stays `'study'`.
- `git diff frontend/src/services/solutionVerifier.ts` is empty.
- Existing verifier tests still pass without modification.

### Task 4 — Frontend: chrome behavior in study mode (Level 2, ~40 LoC)

**File**: `frontend/src/components/Solver/SolverView.tsx`.

For each control, gate behavior on `isStudyMode` per the §4.3 table:

- Hint button (around line 916) — render with `disabled={isStudyMode}` and add `aria-label="Study position — no recorded solution"` when disabled. Do NOT hide.
- Review button (around line 927-931) — same treatment as Hint.
- Solution reveal (around line 1091) — hide entirely (no tree to reveal, nothing to disable).
- Completion card / next-puzzle CTA (around line 656) — hide when `isStudyMode` (study has no completion).
- Tag-revealed-on-complete logic (around line 759) — reveal tags immediately when `isStudyMode` (no spoiler concern).
- Side-to-move initialization — honor SGF `PL[]` when `isStudyMode` (RC-7). If `PL[]` absent, default to Black-to-play and alternate.

Add a "Study position" badge next to the title when `isStudyMode`. Reuse existing badge styling.

**Acceptance**: Visual review on a study puzzle URL — Hint and Review buttons present but disabled with tooltip; no Solution reveal; tags visible immediately; "Study position" badge shown; undo + free play work; first stone respects `PL[]`.

### Task 5 — Stats / progress / rush / daily exclusions via single predicate (Level 2, ~20 LoC)

> **Single predicate, multiple imports** (RC-5). All exclusion sites import the same exported `isStudyMode(puzzle)` function. No duplicated checks for `cx_solution_len === 0` or `puzzle.mode === 'study'` scattered across services.

**Files**:
- Wherever localStorage puzzle progress is written (search for `localStorage.setItem` near solver state) — gate write on `!isStudyMode(puzzle)`
- Rush set selection query (`frontend/src/services/...`) — filter via `isStudyMode`
- Daily challenge query — filter via `isStudyMode` or equivalent SQL filter (`cx_solution_len > 0` is the DB-side analogue)
- Stats display: separate "studied" counter (RC-6 / §8 decision) — increment on study-puzzle close instead of writing to "solved"

1. Verify `isStudyMode` is exported from the puzzle type module (Task 2).
2. Each of rush/daily/stats imports the same predicate. Zero duplicated structural checks.
3. Stats writes a separate "studied" counter when `isStudyMode(puzzle)` is true; no entry in the solve-history list.
4. Daily/rush queries that work over `yengo-search.db` filter by `cx_solution_len > 0` (the DB-side analogue, since the parser hasn't run on those rows).

**Acceptance**:
- Solving a study puzzle does not appear in "solved" stats.
- "Studied" counter increments separately.
- Rush sessions never include study puzzles.
- Daily picker never selects a study puzzle.
- A `grep` for the structural discriminator across `frontend/src/services/` and `frontend/src/components/` returns ONLY imports of `isStudyMode`, never the inline `puzzle.mode === 'study'` check (except in the predicate itself).

### Task 6 — Documentation (Level 1)

**Files**:
- [`docs/concepts/`](../docs/concepts/) — new short doc `study-puzzles.md` (cross-cutting concept; both backend ingest behavior and frontend rendering)
- Update [`frontend/src/AGENTS.md`](../frontend/src/AGENTS.md) puzzle-status table and "Recent learnings" section with the `'study'` status
- Update [`docs/architecture/backend/source-ingest-db.md`](../docs/architecture/backend/source-ingest-db.md) note on the validator gate change
- Per project policy: every doc has a "Last Updated" date and a "See also" cross-reference block

**Acceptance**: Concept doc explains: what is a study puzzle, when does the pipeline produce one, what does the user see. Cross-references both architecture and how-to docs.

### Task 7 — End-to-end validation (Level 1)

1. Backend: full test suite green (`pytest backend/ -m "not (cli or slow)"`).
2. Frontend: vitest suite green (`cd frontend; npm test -- --run`).
3. Manual: visit a t-hero study puzzle URL, confirm UX matches §4.3 table.
4. Manual: visit a normal solvable puzzle, confirm zero regression in solving behavior.

---

## 7. Estimated Scope

| Task | LoC | Risk |
|---|---|---|
| 1. Backend flip + tests | ~5 + tests | Low |
| 2. Parse-time `mode` + status enum + predicate | ~30 | Low |
| 3. Call-site dispatch in SolverView (verifier untouched) | ~15 | Low (rev 2: was Med — verifier no longer touched) |
| 4. UI chrome behavior (disabled-with-tooltip + PL[]) | ~40 | Low |
| 5. Stats/rush/daily exclusions via single predicate | ~20 | Low |
| 6. Docs | n/a | Low |
| 7. Validation | n/a | n/a |

**Total**: ~110 LoC across ~7 frontend files + 1 config file. **Single PR.** No schema bump (because we chose Option B in §4.1). Verifier service untouched (RC-4).

---

## 8. Decisions Already Made (don't re-litigate)

- **No SGF schema bump.** Detect study mode at runtime from tree shape (§4.1 Option B).
- **Reuse `SolverView`.** No new page, no new route.
- **Keep `min_solution_depth = 0` global**, not per-source. If we later get a high-quality unsolved-positions source we don't want admitted, we add a per-source override at that point — YAGNI now.
- **Runtime detection over property tagging.** No `YS_TYPE`, no `YQ` extension.
- **Parse-time classification, not loader-time** (rev 2 / RC-3). `puzzle.mode` is computed once inside `sgfToPuzzle()` and is the single source of truth.
- **Verifier stays pure** (rev 2 / RC-4). Study-mode dispatch happens at the call site in `SolverView.tsx`. No neutral-result type, no special return path inside `solutionVerifier.verifyMove()`.
- **One predicate, multiple imports** (rev 2 / RC-5). `isStudyMode(puzzle)` is exported once, co-located with the type. Rush, daily, stats, UI all import the same function.
- **Separate "studied" counter, not "seen" or "solved"** (rev 2 / RC-6). Study-puzzle engagement is tracked in its own metric, distinct from solve-rate analytics. No pollution of solve stats.
- **Honor SGF `PL[]` for side-to-move in study mode** (rev 2 / RC-7). T-Hero capturing-races encode side-to-move; ignoring it would invert the puzzle for the corpus. Alternating-from-Black is the fallback for SGFs without `PL[]`.
- **Disabled-with-tooltip for hint/review buttons in study mode** (rev 2 / RC-8). Preserves UI rhythm, gives discoverable explanation, avoids "did the app break?" confusion.

---

## 9. Open Questions

1. **Should hints be supported in study mode via AI later?** Out of scope, but could plug into the existing `tools/puzzle-enrichment-lab/` pipeline. Mention in the concept doc as future work.
2. **Color marker policy in study mode?** Goban shows last-move marker by default. Keep it. Just don't add green/red overlays.
3. **Future: enrich the 200 T-Hero capturing-races-unsolved positions with KataGo?** (Surfaced by Shin Jinseo persona.) Out of scope for this plan; if pursued, those positions would migrate from `mode='study'` to `mode='solve'` automatically once a solution tree is published. No code change needed to support that migration.

---

## 10. Reproduction Commands (for the next agent)

```powershell
# See the current state of the t-hero ingest DB
python -c "import sqlite3; c=sqlite3.connect('external-sources/t-hero/sgf/.yengo-ingest.sqlite'); [print(repr(r), n) for r,n in c.execute('SELECT skip_reason, COUNT(*) FROM files WHERE status=1 GROUP BY skip_reason')]"

# Inspect one study SGF (no children)
Get-Content external-sources/t-hero/sgf/capturing-races-unsolved/th-11981.sgf -Raw

# Compare with a normal solvable SGF (has child variations with C[+])
Get-ChildItem external-sources/t-hero/sgf/capture-problems | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -Raw }

# Re-ingest after flipping the validator flag
python -m backend.puzzle_manager run --source t-hero --fresh

# Confirm new counts
python -m backend.puzzle_manager source-status t-hero
```

---

## 11. Files the Next Agent Will Touch

```
config/puzzle-validation.json                       # Task 1
backend/puzzle_manager/tests/unit/test_puzzle_validator.py  # may need t-hero scenario

frontend/src/lib/sgf-to-puzzle.ts                   # Task 2 — compute puzzle.mode at parse time
frontend/src/lib/__tests__/sgf-to-puzzle.test.ts    # Task 2 — new unit test
frontend/src/types/puzzle-internal.ts               # Task 2 — extend type, export isStudyMode()
frontend/src/hooks/<loaderHook>.ts                  # Task 2 — read puzzle.mode (CONFIRM exact path during execution; loader logic itself does not derive)

frontend/src/components/Solver/SolverView.tsx       # Tasks 3, 4 — call-site dispatch + chrome behavior
                                                    # NOTE: solutionVerifier.ts is NOT touched (RC-4)

frontend/src/services/<rush>                        # Task 5 — import isStudyMode predicate
frontend/src/services/<daily>                       # Task 5 — import isStudyMode predicate (or filter cx_solution_len > 0 in SQL)
frontend/src/services/<stats>                       # Task 5 — separate "studied" counter

frontend/src/AGENTS.md                              # Task 6
docs/concepts/study-puzzles.md                      # Task 6 (NEW)
docs/architecture/backend/source-ingest-db.md       # Task 6 (small update)
```

**Files explicitly NOT touched** (rev 2):
- `frontend/src/services/solutionVerifier.ts` — verifier purity is non-negotiable (RC-4).

---

## 13. Executor-Time Conditions (from Governance-Panel rev-2 approval)

**Panel decision**: `approve_with_conditions` (status_code: `GOV-PLAN-CONDITIONAL`). All 8 rev-1 RCs verified. Plan-Executor proceeds with the following three additional gates.

### RC-P1 — Timed/streak mode exclusion (Hana Park, 1p)
**During Task 5**: grep `frontend/src/services` for `timer`, `streak`, `countdown`. If any timed-solve mode exists, add the same `isStudyMode` filter used for rush. If none exists, document N/A in the validation section appended at Task 7.

### RC-P2 — Collection-browse card check (Hana Park, 1p)
**During Task 4 / Task 7 manual review**: visually confirm that collection-browse cards do not display completion-style indicators (solved-checkmark, score, etc.) on study puzzles. If they do, gate the indicator render on `!isStudyMode(puzzle)`.

### RC-DEF1 — Defense-in-depth daily-picker guard (panel Q3)
**During Task 5**: in addition to the SQL `cx_solution_len > 0` filter, add a one-line app-level guard inside the daily-picker function that calls `isStudyMode(puzzle)`. Belt-and-suspenders against future SQL drift.

### Mandatory pre-commit gates (already in tasks; restated for executor)
- Task 2 grep acceptance: structural discriminator (`x === -1 && y === -1 && !trunk_next && !branches`) appears ONLY in `frontend/src/lib/sgf-to-puzzle.ts`.
- Task 3 git-diff acceptance: `git diff frontend/src/services/solutionVerifier.ts` is empty.
- Task 5 grep acceptance: structural discriminator appears in NO file under `frontend/src/services/` or `frontend/src/components/` except as imports of `isStudyMode`.

### Post-execution
On Task 7 completion, route back to **Governance-Panel `review` mode** with a validation section appended to this same file (this initiative opted into the flat single-file shape per the panel's RC-B note from rev 1).

---

## 12. References

- Validator gate: [`backend/puzzle_manager/core/puzzle_validator.py`](../backend/puzzle_manager/core/puzzle_validator.py#L382-L395)
- Existing test for `min_solution_depth=0`: [`backend/puzzle_manager/tests/unit/test_puzzle_validator.py`](../backend/puzzle_manager/tests/unit/test_puzzle_validator.py#L278)
- SGF parser entry point: [`frontend/src/lib/sgf-to-puzzle.ts`](../frontend/src/lib/sgf-to-puzzle.ts#L347)
- Move verifier: [`frontend/src/services/solutionVerifier.ts`](../frontend/src/services/solutionVerifier.ts#L67-L118)
- Solver view (status + chrome): [`frontend/src/components/Solver/SolverView.tsx`](../frontend/src/components/Solver/SolverView.tsx#L306-L308)
- SourceIngestDB skip_reason persistence: [`docs/architecture/backend/source-ingest-db.md`](../docs/architecture/backend/source-ingest-db.md)
- Project conventions for new features: [`.github/copilot-instructions.md`](../.github/copilot-instructions.md), [`CLAUDE.md`](../CLAUDE.md)
