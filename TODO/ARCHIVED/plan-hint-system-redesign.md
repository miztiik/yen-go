# Plan: Hint System Redesign — Pedagogically-Sound Progressive Hints

**Created:** 2026-02-22
**Status:** Not Started
**Scope:** Backend enrichment (hints.py, tagger.py), frontend HintOverlay, docs
**Expert Review:** Cho Chikun (9-dan), Lee Changho (9-dan), Fujisawa Shuko (9-dan)

---

## Summary

Complete redesign of the YH hint generation algorithm. The current system generates hints that are generically useful for game play but misleading for puzzle solving. Three expert reviews identified: 4 key-mismatch bugs, 15 tags with no hint coverage, liberty analysis applied indiscriminately (misleading for net/ladder/sacrifice problems), wrong tier ordering, and frontend padding with meaningless filler hints.

The redesign reorders hints to **Technique → Reasoning → Coordinate**, gates liberty analysis to only semeai/ko, expands coverage to all 28 tags, and stops the frontend from padding with generated filler.

---

## Decisions (Final)

| Decision | Choice | Rationale | Expert |
|----------|--------|-----------|--------|
| Hint tier order | Technique → Reasoning → Coordinate | Beginners need the technique NAME first, then WHY, then WHERE (Lee + Fujisawa) | Lee |
| Liberty analysis gating | Only for `capture-race` and `ko` | Liberty framing misleads for net/ladder/sacrifice/shape — "a group can have 10 liberties and still be dead" (Cho) | Cho |
| Tag priority for multi-tag puzzles | Specific tesuji > tactical > general > category | Most specific tag should drive the hint (Lee) | Lee |
| Frontend filler hints | Remove — show fewer tiers instead | "Focus near the board" is meaningless; fewer good hints > many bad ones (Fujisawa) | Fujisawa |
| YH3 for depth-1 puzzles | Suppress entirely | Coordinate IS the answer for 1-move puzzles — nothing left to learn (Fujisawa) | Fujisawa |
| Wrong-approach warning | In YH2 reasoning, not YH3 | Tell student what NOT to do as part of technique explanation (Fujisawa) | Fujisawa |
| Atari detection in YH1 | Standalone hint, not appended to region | Atari IS the hint — region is noise when atari is the situation (Fujisawa) | Fujisawa |
| Root C[] as hint source | Future enhancement (not this PR) | Requires parser changes; defer to Phase 5 | All |
| Tagger improvements | Separate scope (Phase 5) | Architecture: tagger produces tags, hint generator consumes — fix each independently (Lee) | Lee |

---

## Bugs (Must Fix)

### B1: Four key mismatches between tags.json slugs and TECHNIQUE_HINTS keys

The tagger assigns tags using `tags.json` slugs, but `generate_yh2()` searches `TECHNIQUE_HINTS` which uses different keys:

| Tag slug (assigned by tagger) | TECHNIQUE_HINTS key (searched) | Result |
|------|------|------|
| `liberty-shortage` | `squeeze` | **Silent failure — no YH2** |
| `connection` | `connect` | **Silent failure — no YH2** |
| `cutting` | `cut` | **Silent failure — no YH2** |
| `capture-race` | `capture` | **Silent failure — no YH2** |

**Fix:** Add the tag slugs as keys in TECHNIQUE_HINTS, remove orphaned old keys.

### B2: Tagger `capture-race` false positives

In `tagger.py` line 109, any move that captures 2+ stones is tagged `capture-race`. But killing a group via nakade captures multiple stones — that's not semeai. This causes misleading liberty hints on non-semeai puzzles.

**Fix:** Require BOTH sides to have groups with ≤4 liberties for `capture-race` tag. Single-direction kills are not semeai.

---

## Phases

### Phase 1: Bug Fixes (F1 + F2 + B1 + B2)

**Files:** `backend/puzzle_manager/core/enrichment/hints.py`, `backend/puzzle_manager/core/tagger.py`

1. Fix the 4 key mismatches in `TECHNIQUE_HINTS`:
   - Add `liberty-shortage`, `connection`, `cutting`, `capture-race` as keys
   - Keep `squeeze`, `connect`, `cut`, `capture` as aliases (both keys map to same hint)
   - File: `hints.py` TECHNIQUE_HINTS dictionary

2. Fix tagger `capture-race` false positive:
   - In `_analyze_tree()`, change the multi-capture detection to verify BOTH sides have low-liberty groups
   - File: `tagger.py` `_analyze_tree()` method

3. Write tests:
   - Test that `generate_yh2(["capture-race"])` returns a hint (not None)
   - Test that `generate_yh2(["connection"])` returns a hint
   - Test that `generate_yh2(["cutting"])` returns a hint
   - Test that `generate_yh2(["liberty-shortage"])` returns a hint
   - Test that multi-stone capture without mutual low-liberty does NOT tag as `capture-race`

**Review checkpoint:** Run `pytest -m unit` — verify no regressions.

---

### Phase 2: TECHNIQUE_HINTS Expansion (E1 + E2 + E3)

**Files:** `backend/puzzle_manager/core/enrichment/hints.py`

1. Add TECHNIQUE_HINTS entries for all 15 missing tags with expert-reviewed hint text:

   | Tag | Hint | Reasoning |
   |-----|------|-----------|
   | `nakade` | "Look for a nakade — the vital point inside" | "Playing the vital point prevents two eyes." |
   | `clamp` | "Consider a clamp (hasami-tsuke)" | "Attach inside to reduce eye space." |
   | `vital-point` | "Find the vital point of the shape" | "One move determines whether the group lives or dies." |
   | `connect-and-die` | "What happens if the opponent connects?" | "Connecting leads to a larger capture." |
   | `under-the-stones` | "Think about playing under the stones" | "After the capture, the vacated space becomes crucial." |
   | `eye-shape` | "Focus on the eye shape" | "Can the group make two real eyes, or is one false?" |
   | `dead-shapes` | "Recognize the shape — is it already dead?" | "Some shapes cannot make two eyes regardless of who plays first." |
   | `corner` | "Corner positions have special properties" | "Reduced liberties and edge effects change the tactics." |
   | `shape` | "Look for the most efficient shape" | "Good shape maximizes liberties and eye potential." |
   | `endgame` | "This is an endgame (yose) problem" | "Which move gains the most points?" |
   | `joseki` | "This tests joseki knowledge" | "Find the standard continuation for this corner pattern." |
   | `fuseki` | "Consider the whole-board balance" | "Which area is most urgent to play?" |
   | `tesuji` | "Look for a sharp tactical move" | "There is a tesuji that changes the outcome." |
   | `living` | "Your group needs to live" | "Find the move that guarantees two eyes." |
   | `seki` | "Mutual life may be the best outcome" | "Neither side can attack without self-destruction." |

2. Improve reasoning templates for existing entries (Cho Chikun review):

   | Tag | Current Reasoning | Improved Reasoning |
   |-----|------|------|
   | `life-and-death` | "Focus on eye shape." | "Can the group make two independent eyes, or can you prevent it?" |
   | `capture` / `capture-race` | "Count liberties - fewer loses." | "Compare liberties: the group with fewer will be captured first." |
   | `sacrifice` | "Giving up stones can gain tempo." | "After the sacrifice, the opponent's shape collapses." |
   | `connect` / `connection` | "Two weak groups become one strong." | "Find the move that links both groups so neither can be cut." |
   | `cut` / `cutting` | "Separating creates two weak groups." | "After separating, can the opponent save both halves?" |
   | `ko` | "Think about who has more ko threats." | "Identify the ko — then look for local threats to win it." |
   | `escape` | "Connect to safety or make eyes." | "Which direction offers the best escape? Consider where friendly stones are." |

3. Implement tag priority ordering in `generate_yh2()`:

   | Priority | Tags |
   |----------|------|
   | 1 (highest) | `snapback`, `double-atari`, `connect-and-die`, `under-the-stones`, `clamp` |
   | 2 | `ladder`, `net`, `throw-in`, `sacrifice`, `nakade`, `vital-point` |
   | 3 | `capture-race`, `liberty-shortage`, `eye-shape`, `connection`, `cutting` |
   | 4 (lowest) | `life-and-death`, `living`, `ko`, `seki`, `shape`, `corner`, `endgame`, `tesuji`, `joseki`, `fuseki`, `dead-shapes` |

   Logic: Sort incoming tags by priority, pick highest-priority match.

4. Write tests:
   - Test each of the 28 tags produces a non-None YH2
   - Test priority ordering: `["life-and-death", "snapback"]` → snapback hint wins
   - Test all reasoning templates are non-empty

**Review checkpoint:** Run `pytest -m unit` — verify all 28 tags produce hints.

---

### Phase 3: Algorithm Redesign (A1–A6)

**Files:** `backend/puzzle_manager/core/enrichment/hints.py`, `backend/puzzle_manager/core/enrichment/__init__.py`

1. **Reorder hint tiers** (A1):
   - YH1 = Technique identification (current YH2 content)
   - YH2 = Diagnostic reasoning (technique-aware thinking prompt + wrong-approach warning)
   - YH3 = Coordinate + technique-specific outcome
   - This means `generate_yh1()` becomes the technique hint, `generate_yh2()` becomes the reasoning, `generate_yh3()` remains coordinate
   - Rename methods for clarity: `generate_technique_hint()`, `generate_reasoning_hint()`, `generate_coordinate_hint()`

2. **Gate liberty analysis** (A2):
   - Liberty analysis ONLY activates for tags `capture-race` and `ko`
   - For all other tags: no liberty counting in hints
   - New parameter: `generate_reasoning_hint(tags, game)` — checks if semeai/ko before running `_analyze_liberties()`

3. **Atari as standalone hint** (A3):
   - When atari is detected and tag is NOT `capture-race`/`ko`, atari becomes the technique hint:
     - "The opponent is in atari! Look for the capturing move."
     - "Your group is in atari! Escape or make eyes immediately."
   - When atari is detected AND tag IS `capture-race`/`ko`, include in reasoning with liberty counts

4. **Technique-aware YH3 templates** (A4):
   - Replace generic "The first move is at {!xy}." with technique-specific outcomes:
     - `ladder`: "The first move is at {!xy}. This begins the chase."
     - `net`: "The first move is at {!xy}. This creates an inescapable enclosure."
     - `snapback`: "The first move is at {!xy}. Let them capture — then take back more."
     - `sacrifice`/`throw-in`: "The first move is at {!xy}. This stone will be sacrificed for the greater good."
     - `nakade`: "The first move is at {!xy}. This is the vital point inside."
     - `ko`: "The first move is at {!xy}. This starts the ko fight."
     - `double-atari`: "The first move is at {!xy}. Two groups are threatened at once."
     - Default: "The first move is at {!xy}."

5. **Solution depth gating** (A5):
   - Depth 1: Suppress YH3 entirely (the technique hint is sufficient)
   - Depth 2–3: Coordinate only, no consequence text
   - Depth 4+: Coordinate + technique-specific outcome

6. **Move wrong-approach into YH2** (A6):
   - Remove `_get_refutation_consequence()` from `generate_coordinate_hint()`
   - Instead, incorporate wrong-approach warnings into the reasoning hint (YH2)
   - Format: "[Reasoning]. [What NOT to do / what fails]."
   - Example: "Direct capture doesn't work here — the opponent has too many escape routes. Think about surrounding loosely."

7. Update `enrich_puzzle()` orchestration in `__init__.py`:
   - Change the hint generation order: technique → reasoning → coordinate
   - Pass tags to all three generators (needed for technique-awareness)

8. Write tests:
   - Test new tier ordering: YH1 is technique, YH2 is reasoning, YH3 is coordinate
   - Test liberty gating: net puzzle does NOT get liberty analysis
   - Test atari standalone: atari puzzle gets "in atari!" as primary hint
   - Test depth-1 suppression: 1-move puzzle generates only 2 hints
   - Test technique-aware YH3: ladder puzzle gets "begins the chase"
   - Test wrong-approach in reasoning: net puzzle explains why direct chase fails

**Review checkpoint:** Run `pytest -m "not (cli or slow)"` — full regression.

---

### Phase 4: Frontend Changes (FE1)

**Files:** `frontend/src/components/Solver/HintOverlay.tsx`, `frontend/tests/unit/compute-hint-display.test.ts`

1. **Stop padding with generated filler** (FE1):
   - Update `computeHintDisplay()`: if fewer than 3 hints, show fewer tiers
   - Remove generated "Focus near the {board}" and "Look at the {board} area" filler
   - If 2 hints: show 2 tiers + board marker at tier 3
   - If 1 hint: show 1 tier + board marker at tier 2
   - If 0 hints: show only board marker at tier 1
   - The board marker (colored circle on correct move) remains always available as the final tier

2. Update `getMaxLevel()` to return `hints.length + 1` (hints + marker) instead of always 3

3. Update frontend tests:
   - `compute-hint-display.test.ts`: update expectations for new behavior
   - `hints.test.tsx`: update integration test expectations

**Review checkpoint:** Run `npx vitest run tests/unit/compute-hint-display.test.ts` + `npx vitest run tests/integration/hints.test.tsx`

---

### Phase 5: Future Enhancements (Separate PRs)

These are out of scope for this plan but documented for future work:

| # | Enhancement | Expert | Priority |
|---|---|---|---|
| T1 | Add cutting-point detection to tagger board analysis | Lee | Medium |
| T2 | Add eye-space detection to tagger board analysis | Lee | Medium |
| T3 | Add enclosed-group detection to tagger | Lee | Medium |
| T4 | Add connection vulnerability detection to tagger | Lee | Low |
| FE2 | Root C[] comment as hint source (if substantive text, use as YH1) | Fujisawa | Low |
| FE3 | Solution depth influences hint verbosity display | Lee | Low |

---

## Workflow

For each phase, follow this cycle:

```
1. IMPLEMENT
   - Write code changes + unit tests
   - Run relevant test suite
   - Verify no regressions

2. REVIEW (1P Go Professional persona)
   - Is the hint pedagogically sound?
   - Does it teach the RIGHT concept for this technique?
   - Would it mislead a beginner?
   - Does the "Do No Harm" principle hold? (bad hint > no hint)

3. PRINCIPAL ENGINEER REVIEW
   - SOLID/DRY/KISS/YAGNI compliance
   - Test coverage and edge cases
   - No key mismatches or silent failures
   - All 28 tags covered

4. PIPELINE VALIDATION
   - Run pipeline on small batch: python -m backend.puzzle_manager run --source sanderland --batch-size 5
   - Inspect generated YH properties in output SGF
   - Verify hints are technique-appropriate (not misleading)
   - Compare before/after for same puzzles

5. COMMIT (Git Safety Standards)
   - git status --porcelain | grep "^??"
   - Stage ONLY specific files
   - git diff --cached --name-only
   - Feature branch → merge --no-ff
```

---

## Verification

### After Phase 1 (Bug Fixes)
```bash
cd backend/puzzle_manager
pytest -m unit -k "hint" --tb=short
```

### After Phase 2 (Expansion)
```bash
cd backend/puzzle_manager
pytest -m unit -k "hint or technique" --tb=short
# Verify: all 28 tags produce non-None YH2
```

### After Phase 3 (Algorithm Redesign)
```bash
cd backend/puzzle_manager
pytest -m "not (cli or slow)" --tb=short -q
```

### After Phase 4 (Frontend)
```bash
cd frontend
npx vitest run tests/unit/compute-hint-display.test.ts
npx vitest run tests/integration/hints.test.tsx
npx tsc --noEmit
```

### End-to-end Pipeline Validation
```bash
# Run pipeline on a small batch and inspect YH output
python -m backend.puzzle_manager run --source sanderland --batch-size 5
# Inspect generated SGF files for YH property content
```

---

## Files Changed

| Phase | File | Change |
|-------|------|--------|
| 1 | `backend/puzzle_manager/core/enrichment/hints.py` | Fix key mismatches in TECHNIQUE_HINTS |
| 1 | `backend/puzzle_manager/core/tagger.py` | Fix capture-race false positive |
| 1 | `backend/puzzle_manager/tests/unit/test_enrichment.py` | Add key-mismatch tests |
| 2 | `backend/puzzle_manager/core/enrichment/hints.py` | Add 15 new entries, improve reasoning, add priority |
| 2 | `backend/puzzle_manager/tests/unit/test_enrichment.py` | Test all 28 tags coverage |
| 3 | `backend/puzzle_manager/core/enrichment/hints.py` | Reorder tiers, gate liberty, technique-aware templates |
| 3 | `backend/puzzle_manager/core/enrichment/__init__.py` | Update orchestration order |
| 3 | `backend/puzzle_manager/tests/unit/test_enrichment.py` | Test new algorithm behavior |
| 4 | `frontend/src/components/Solver/HintOverlay.tsx` | Remove filler, dynamic tier count |
| 4 | `frontend/tests/unit/compute-hint-display.test.ts` | Update expectations |
| 4 | `frontend/tests/integration/hints.test.tsx` | Update expectations |
| All | `docs/architecture/backend/hint-architecture.md` | New architecture doc |
| All | `docs/concepts/hints.md` | Update to reflect new design |
