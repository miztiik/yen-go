# Plan: Analyzer Enhancement — YG Preservation, Comment Cleaning & Enrichment Cleanup

**Created:** 2026-02-22
**Status:** Not Started
**Scope:** Backend analyze stage, frontend ko types, documentation, dead code

---

## Summary

Eight changes to the analyze stage: (1) respect source-provided YG, (2) eliminate post-build string insertion workaround, (3) align frontend ko enum, (4) strip CJK from output comments, (5) standardize move comments to `Correct`/`Wrong`, (6) mark single-move inferred correctness as `Correct [auto-inferred]`, (7) fix stale/contradictory documentation, (8) remove dead code.

---

## Decisions (Final)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Move templates | `Correct` / `Wrong` (first word) | Pipeline prefix matching depends on first word |
| Inferred correctness marker | `Correct [auto-inferred]` | Greppable, distinguishable, future engine cleanup path |
| YG policy | Preserve source → compute → fallback `elementary` | Respect adapter data; classifier failure ~0% probability |
| Ko enum | `direct` / `approach` (update frontend) | Backend values are more semantically accurate for Go |
| CJK | Strip from both root and move comments | Ko detection runs on parsed game before output serialization |
| Fallback level | `elementary` (level 3) | Middle ground; classifier practically never fails |
| Dead code | Explicit cleanup step | Per project dead code policy: delete, don't deprecate |

---

## Workflow

For each step below, follow this cycle:

```
1. IMPLEMENT
   - Write code changes + unit tests
   - Run relevant test suite (pytest -m unit or npm test)
   - Verify no regressions

2. PRINCIPAL STAFF ENGINEER REVIEW
   - Review implementation for:
     □ SOLID/DRY/KISS/YAGNI compliance
     □ Test coverage and edge cases
     □ Error handling and logging
     □ Performance implications
     □ API/interface consistency
   - Fix all issues raised

3. PRINCIPAL SYSTEMS ARCHITECT REVIEW
   - Review implementation for:
     □ Architectural alignment with pipeline design
     □ Data flow correctness (parse → enrich → build → serialize)
     □ Cross-cutting concerns (frontend/backend contract)
     □ Schema evolution and backward compatibility
     □ Ripple effects on other pipeline stages
   - Fix all issues raised

4. COMMIT (Git Safety Standards)
   - Check for untracked files: git status --porcelain | grep "^??"
   - Verify no protected dirs affected (external-sources/, .pm-runtime/)
   - Stage ONLY specific files: git add <explicit paths>
   - Verify staged: git diff --cached --name-only
   - Create feature branch: git checkout -b feature/<step-name>
   - Commit: git commit -m "feat: <description>"
   - Merge: git checkout main && git merge --no-ff feature/<step-name>
   - Delete branch: git branch -d feature/<step-name>
   - NEVER use: git stash, git reset --hard, git clean, git add .
```

---

## Steps

### Step 1: YG Preserve-First Policy

**Status:** Not Started

**What:** Change the analyzer to respect source-provided YG and only compute when missing. Add fallback to `elementary` (level 3) if classification fails.

**Files:**
- `backend/puzzle_manager/stages/analyze.py` (L260–L261) — currently calls `classify_difficulty()` unconditionally

**Changes:**
1. Before calling `classify_difficulty(game)`, check `game.yengo_props.level_slug`
2. Validate against valid slugs from `config/puzzle-levels.json` (novice through expert)
3. If valid source YG exists → preserve it, log `"Preserving source-provided YG: {slug}"`
4. If no valid source YG → call `classify_difficulty(game)` as today
5. Wrap classification in try/except `ClassificationError` → fallback to level=3, slug=`"elementary"`, log warning

**Tests:**
- [ ] Puzzle with existing `YG[intermediate]` → preserved after analyze
- [ ] Puzzle with no YG → classifier runs, YG assigned
- [ ] Puzzle with invalid YG (e.g., `YG[DDK30]`) → classifier overrides
- [ ] Classification failure → fallback to `elementary`

**Branch:** `feature/step1-yg-preserve-first`

---

### Step 2: Eliminate `_enrich_sgf` Post-Build Workaround

**Status:** Not Started

**What:** The post-build string insertion for YC/YK/YO/YR (analyze.py L425–458) is a legacy workaround. `SGFBuilder` already supports all four properties via `set_corner()`, `set_ko_context()`, `set_move_order()`, `set_refutation_count()`.

**The problem:** Stale comment says "YC, YK, YO, YR not yet supported by SGFBuilder" — this is false. The workaround does fragile string scanning and could create duplicate properties.

**Files:**
- `backend/puzzle_manager/stages/analyze.py` — `_enrich_sgf` method

**Changes:**
1. After `builder = SGFBuilder.from_game(game)`, before `builder.build()`, set enrichment properties:
   ```python
   if enrichment.region:
       builder.set_corner(enrichment.region)
   if enrichment.ko_context:
       builder.set_ko_context(enrichment.ko_context)
   if enrichment.move_order:
       builder.set_move_order(enrichment.move_order)
   if enrichment.refutations:
       builder.set_refutation_count(enrichment.refutations)
   ```
2. Delete stale comment (L425–427)
3. Delete entire post-build string insertion block (L435–458)

**Tests:**
- [ ] YC/YK/YO/YR appear exactly once in output SGF (no duplicates)
- [ ] Enrichment properties in correct position (grouped with other Y* properties)
- [ ] Ko puzzles retain `YK[direct]`

**Branch:** `feature/step2-enrich-workaround-elimination`

---

### Step 3: Align Frontend Ko Enum to Backend

**Status:** Not Started

**What:** Frontend types use `simple`/`complex` but backend emits `direct`/`approach`. All 3 published ko puzzles have `YK[direct]` which silently falls to `none` in the frontend.

**Files:**
- `frontend/src/types/goban.ts` (L18) — `"simple" | "complex"` → `"direct" | "approach"`
- `frontend/src/lib/sgf-metadata.ts` (L256) — validation update
- `frontend/src/types/puzzle-internal.ts` (L158) — `KoContext.type` update
- `frontend/src/lib/sgf-preprocessor.ts` (L124) — default stays `'none'`

**Tests:**
- [ ] Frontend parses `YK[direct]` correctly (no longer falls to `none`)
- [ ] Frontend parses `YK[approach]` correctly
- [ ] `YK[none]` still works
- [ ] Update any existing frontend tests referencing `simple`/`complex`

**Branch:** `feature/step3-ko-enum-alignment`

---

### Step 4: CJK Stripping in Final Output

**Status:** Not Started

**What:** Strip CJK characters from both root C[] and move C[] comments in the final output SGF. Ko detection runs on the parsed `SGFGame` object (before output), so no conflict.

**Files:**
- `backend/puzzle_manager/core/text_cleaner.py` — add `strip_cjk()` function
- `backend/puzzle_manager/stages/analyze.py` (L373–376) — root comment already passes through `clean_for_correctness()`
- `backend/puzzle_manager/core/sgf_builder.py` (L593–607) — apply CJK stripping in `_build_node()`

**CJK Unicode ranges to strip:**
- CJK Unified Ideographs: U+4E00–U+9FFF
- Katakana: U+30A0–U+30FF
- Hiragana: U+3040–U+309F
- Hangul: U+AC00–U+D7AF
- CJK Compatibility: U+3300–U+33FF, U+FE30–U+FE4F

**Tests:**
- [ ] CJK-only comment → empty string
- [ ] Mixed CJK+English → English preserved
- [ ] Ko detection still works on parsed game (CJK present in memory, stripped only in output)
- [ ] Root comment with CJK → stripped in output
- [ ] Move comment with CJK → stripped in output

**Branch:** `feature/step4-cjk-stripping`

---

### Step 5: Move Comment Standardization — `Correct` / `Wrong`

**Status:** Not Started

**What:** Normalize move comment formats. First word must be `Correct` or `Wrong` — pipeline prefix matching (`correctness.py` Layer 2) depends on this.

**Overwrite rules:**
1. Existing comment starts with known correctness signal (`wrong`, `incorrect`, `right`, `correct`, `+`, `ok`) → **replace signal word** with `Correct` or `Wrong`, preserve pedagogical suffix
   - `"RIGHT — good tesuji"` → `"Correct — good tesuji"`
   - `"Incorrect; leads to ko"` → `"Wrong — leads to ko"`
   - `"+"` → `"Correct"`
2. Existing comment has no correctness signal but `node.is_correct` is known → **prepend** `Correct — ` or `Wrong — ` before existing text
   - `"Threatens the corner"` with `is_correct=True` → `"Correct — Threatens the corner"`
3. Empty comment and `is_correct` is known → set to `"Correct"` or `"Wrong"`
4. After CJK stripping, if remaining text is empty → just `"Correct"` or `"Wrong"`

**Separator:** Use ` — ` (em-dash with spaces) for consistency.

**Files:**
- `backend/puzzle_manager/core/sgf_builder.py` — `_build_node()` (L593–607)
- Consider: new helper function `standardize_move_comment(comment, is_correct)` in `text_cleaner.py` or a new module

**Tests:**
- [ ] `"Correct!"` → `"Correct"`
- [ ] `"RIGHT"` → `"Correct"`
- [ ] `"+"` → `"Correct"`
- [ ] `"Wrong; this leads to ko"` → `"Wrong — this leads to ko"`
- [ ] `"Incorrect; leads to ko"` → `"Wrong — leads to ko"`
- [ ] `"Threatens the corner"` (no signal, is_correct=True) → `"Correct — Threatens the corner"`
- [ ] Empty comment, is_correct=True → `"Correct"`
- [ ] Empty comment, is_correct=False → `"Wrong"`

**Branch:** `feature/step5-move-comment-standardization`

---

### Step 6: Single-Move Inferred Correctness

**Status:** Not Started

**What:** For puzzles with exactly one first-level move (one stone, no alternative first moves) and no explicit correctness signal (no SGF markers, no comment signal), mark as `Correct [auto-inferred]`.

**Go player consultation (Cho Chikun style):**
> "If there is only one first move and no refutation branches, it is the correct answer. In professional problem collections, the absence of alternatives means the author presented only the winning line. Mark it Correct with confidence."

**Files:**
- `backend/puzzle_manager/core/sgf_builder.py` — `_build_node()` — if node has no comment, is_correct=True (from default), and is the sole first-level child → comment = `"Correct [auto-inferred]"`
- Consider adding `TE[1]` marker for correct leaf nodes (SGF standard)

**Future cleanup path:**
```bash
grep -r 'auto-inferred' yengo-puzzle-collections/
# → Find all inferred puzzles
# → Validate with KataGo or similar engine
# → Replace "Correct [auto-inferred]" with "Correct" when confirmed
```

**Tests:**
- [ ] Single first-level move, no comments → `"Correct [auto-inferred]"`
- [ ] Single first-level move, existing `"Correct"` comment → preserved as `"Correct"` (not overwritten)
- [ ] Multiple first-level moves → no auto-inference applied
- [ ] Single first-level move with explicit `BM[1]` marker → respected as wrong (not overridden)

**Branch:** `feature/step6-single-move-auto-inferred`

---

### Step 7: Documentation Fixes

**Status:** Not Started

**What:** Fix stale, contradictory, and missing documentation across enrichment docs.

**Files and fixes:**

| File | Fix |
|------|-----|
| `docs/architecture/backend/enrichment.md` L68–96 | Replace pseudocode with actual 4-feature composite score algorithm |
| `docs/architecture/backend/enrichment.md` L48 | Change YG row to "Preserves if valid; computes if missing; fallback: elementary" |
| `docs/architecture/backend/enrichment.md` L49 | Version 10 → 13 |
| `docs/concepts/sgf-properties.md` L302–305 | Fix root C[] to "Cleaned (HTML stripped, CJK stripped) and preserved by default" |
| `docs/concepts/sgf-properties.md` | Fix YK values to `direct`/`approach` |
| `CLAUDE.md` | Fix YK values to `direct`/`approach` |
| `.github/copilot-instructions.md` | Fix YK values to `direct`/`approach` |
| `docs/architecture/backend/enrichment.md` | Add section: Correctness inference 3-layer system |
| `docs/architecture/backend/enrichment.md` | Add section: `Correct`/`Wrong` comment templates |
| `docs/architecture/backend/enrichment.md` | Add section: `Correct [auto-inferred]` convention |
| `docs/architecture/backend/enrichment.md` | Add section: Single-move marking |

**Branch:** `feature/step7-documentation-fixes`

---

### Step 8: Dead Code Cleanup

**Status:** Not Started

**What:** Remove dead code surfaced during this work.

**Known items:**
- [ ] `KoContext` interface in `frontend/src/types/puzzle-internal.ts` (L158) — dead type, `threats: { black, white }` never populated
- [ ] Stale `simple`/`complex` enum values from frontend types (removed in Step 3, verify no references remain)
- [ ] Stale CJK non-stripping comment in `backend/puzzle_manager/core/text_cleaner.py` (L130–131)
- [ ] Any unused imports from deleted post-build insertion code (Step 2)
- [ ] Audit for other dead code surfaced during implementation

**Branch:** `feature/step8-dead-code-cleanup`

---

## Verification (After All Steps)

1. `cd backend/puzzle_manager && pytest -m "not (cli or slow)" --tb=short -q` — no regressions
2. `cd frontend && npm test` — no regressions
3. Re-analyze 347 published puzzles: `python -m backend.puzzle_manager run --stage analyze --stage publish`
4. Verify:
   - [ ] Puzzles with source YG retain their original level
   - [ ] Ko puzzles still have `YK[direct]`
   - [ ] No CJK characters in any output comments
   - [ ] Move comments use `Correct`/`Wrong` as first word
   - [ ] Single-move puzzles have `Correct [auto-inferred]`
   - [ ] No duplicate Y* properties in any output file
5. Spot-check 3 ko puzzles:
   - `yengo-puzzle-collections/sgf/0001/74065fba75d35c74.sgf`
   - `yengo-puzzle-collections/sgf/0001/a468d7b5b47228c9.sgf`
   - `yengo-puzzle-collections/sgf/0001/b2d1e9c525646fda.sgf`

---

## Context & Research

### Classifier Failure Probability: ~0%

The classifier uses 4 safe operations (list lengths, tree walks, integer arithmetic) on dataclass fields with safe defaults. Upstream ingest validation filters out malformed SGF. In 347 published puzzles, zero ClassificationErrors have occurred. The `elementary` fallback is pure defensive programming — it should never trigger.

### Ko Detection Uses CJK (No Conflict)

Ko detection (`enrichment/ko.py`) scans for CJK terms (コウ, 패, 劫) on the **parsed SGFGame object**. CJK stripping happens during **output serialization** (`SGFBuilder._build_node()`). These are independent — ko detection reads from memory, CJK stripping writes to output.

### Backend/Frontend Ko Enum Mismatch (Pre-existing Bug)

Backend emits `YK[direct]`/`YK[approach]`. Frontend validates against `simple`/`complex`. Result: all 3 published ko puzzles silently lose their ko context in the frontend.

### `_enrich_sgf` Workaround (Stale Code)

The comment at analyze.py L425–427 says "YC, YK, YO, YR not yet supported by SGFBuilder". This is false — `SGFBuilder.build()` has full support (L521–536) with setter methods (`set_corner`, `set_ko_context`, `set_move_order`, `set_refutation_count`). The workaround was written before these setters existed and never cleaned up.

---

*Last Updated: 2026-02-22*
