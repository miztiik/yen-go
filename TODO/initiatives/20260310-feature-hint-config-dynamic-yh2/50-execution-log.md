# Execution Log — Config-Driven YH1 + Dynamic YH2 Reasoning

**Initiative ID:** 20260310-feature-hint-config-dynamic-yh2  
**Last Updated:** 2026-03-10

---

## Task Execution Record

### T1: Config-Driven YH1 — `_load_teaching_comments()` (Prior Session)

| EX-1 | Field | Detail |
|------|-------|--------|
| EX-1a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-1b | Change | Added `_teaching_comments_cache` module-level var + `_load_teaching_comments()` function |
| EX-1c | Behavior | Reads `config/teaching-comments.json`, extracts `{tag: hint_text}` map, caches after first load |
| EX-1d | Config path | `Path(__file__).resolve().parents[4] / "config" / "teaching-comments.json"` |
| EX-1e | Fallback | Returns `{}` on config missing/corrupt — falls through to `TECHNIQUE_HINTS` |

### T2: Config-Driven YH1 — `_try_tag_hint()` Priority (Prior Session)

| EX-2 | Field | Detail |
|------|-------|--------|
| EX-2a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-2b | Change | Modified `_try_tag_hint()` to check config first, fallback to `TECHNIQUE_HINTS` |
| EX-2c | Behavior | Config entry → `"{config_text}."` ; no config → `"{hardcoded_text}."` |

### T3: Config-Driven YH1 — `_try_solution_aware_hint()` Priority (Prior Session)

| EX-3 | Field | Detail |
|------|-------|--------|
| EX-3a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-3b | Change | Modified `_try_solution_aware_hint()` to check config first, fallback to `TECHNIQUE_HINTS` |

### T4: Dynamic YH2 — `_count_refutations()` Helper (Prior Session)

| EX-4 | Field | Detail |
|------|-------|--------|
| EX-4a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-4b | Change | Added `_count_refutations(solution_tree)` — counts wrong first-move children |
| EX-4c | Guard | Returns 0 if no solution tree |

### T5: Dynamic YH2 — `_get_secondary_tag()` Helper (Prior Session)

| EX-5 | Field | Detail |
|------|-------|--------|
| EX-5a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-5b | Change | Added `_get_secondary_tag(tags, primary_tag)` — returns next-priority tag from TAG_PRIORITY |
| EX-5c | Guard | Returns None if only 1 tag or no match in TECHNIQUE_HINTS |

### T6: Dynamic YH2 — `generate_reasoning_hint()` Enhancement (Prior Session)

| EX-6 | Field | Detail |
|------|-------|--------|
| EX-6a | File | `backend/puzzle_manager/core/enrichment/hints.py` |
| EX-6b | Change | Enhanced YH2 with depth (≥2), refutation count (>0), secondary tag append |
| EX-6c | Gate | Gated on `game.has_solution` |
| EX-6d | Secondary tag name | Config-driven (prefers `teaching-comments.json` name over hardcoded) |

### T7: New Tests — 14 Tests (Prior Session)

| EX-7 | Field | Detail |
|------|-------|--------|
| EX-7a | File | `backend/puzzle_manager/tests/unit/test_enrichment.py` |
| EX-7b | Tests added | 14 new tests covering config loading, config-driven hints, dynamic reasoning |
| EX-7c | Coverage | Config happy path, config fallback, config for all 28 tags, depth context, refutation count, secondary tag, refutation helper, secondary tag helper |

### T8: Documentation Update (Prior Session)

| EX-8 | Field | Detail |
|------|-------|--------|
| EX-8a | File | `docs/concepts/hints.md` |
| EX-8b | Changes | Updated YH1 section (config-driven), added dynamic reasoning subsection under YH2, date to 2026-03-10 |

### T9: Test Defect Fixes — D-1, D-2 (Prior Session)

| EX-9 | Field | Detail |
|------|-------|--------|
| EX-9a | Defect | D-1: `test_reasoning_includes_secondary_tag` missing `has_solution=True` |
| EX-9b | Defect | D-2: `test_reasoning_no_secondary_for_single_tag` missing `has_solution=True` |
| EX-9c | Fix | Added `has_solution=True` to both test mock game constructors |

### T10: R5 Test Assertion Fixes (This Session)

| EX-10 | Field | Detail |
|-------|-------|--------|
| EX-10a | File | `backend/puzzle_manager/tests/unit/test_enrichment.py` |
| EX-10b | Issue | Two pre-existing R5 tests asserted `"life-and-death"` in hint output, but config now returns `"Life & Death (shikatsu)"` |
| EX-10c | Tests fixed | `test_atari_suppressed_when_irrelevant` (line 516), `test_player_atari_suppressed_when_move_does_not_save` (line 565) |
| EX-10d | Fix | Changed `"life-and-death" in hint.lower()` → `"life" in hint.lower() and "death" in hint.lower()` |

---

## Deviations

| DEV-1 | Description |
|-------|-------------|
| DEV-1a | Two additional test fixes (T10) were needed beyond the governance-identified D-1/D-2. These R5 tests had assertions matching old hardcoded text format that now differs under config-driven YH1. |
| DEV-1b | `TECHNIQUE_HINTS` dict retained as fallback — first tuple element (YH1 text) is now dead code for all 28 config-covered tags, but second element (reasoning template) is actively used by `generate_reasoning_hint()`. This matches the plan's "Fallback: if config missing, keep existing hardcoded values." |

---

## Audit: Old Hardcoded YH1 vs New Config-Driven YH1

All 28 tags now read `hint_text` from `config/teaching-comments.json` at runtime. The old verbose hardcoded text in `TECHNIQUE_HINTS` tuple[0] is retained as fallback but **never executed** for any of the 28 config tags.

### Comparison Table

| Tag | New Config YH1 (Active) | Old Hardcoded YH1 (Dead Code Fallback) |
|-----|-------------------------|---------------------------------------|
| snapback | Snapback (uttegaeshi) | Consider a snapback sequence |
| double-atari | Double Atari (ryō-atari) | Look for a double atari |
| connect-and-die | Connect & Die (oiotoshi) | What happens if the opponent connects? |
| under-the-stones | Under the Stones (ishi no shita) | Think about playing under the stones |
| clamp | Clamp (hasami-tsuke) | Consider a clamp (hasami-tsuke) |
| ladder | Ladder (shicho) | Look for a ladder (shicho) pattern |
| net | Net (geta) | Try surrounding loosely with a net (geta) |
| throw-in | Throw-in (horikomi) | A throw-in might be useful |
| sacrifice | Sacrifice (suteishi) | Consider sacrificing stones |
| nakade | Nakade | Look for a nakade — the vital point inside |
| vital-point | Vital Point (oki) | Find the vital point of the shape |
| capture-race | Capture Race (semeai) | This is a capturing race (semeai) |
| liberty-shortage | Liberty Shortage (damezumari) | Look for a liberty shortage (damezumari) |
| eye-shape | Eye Shape | Focus on the eye shape |
| connection | Connection (tsugu) | Try to connect your groups |
| cutting | Cutting (kiri) | Look for a cutting point |
| escape | Escape | Look for an escape route |
| life-and-death | Life & Death (shikatsu) | This is a life-and-death problem |
| living | Living (ikiru) | Your group needs to live |
| ko | Ko (kō) | This involves a ko fight |
| seki | Seki | Mutual life may be the best outcome |
| shape | Shape (katachi) | Look for the most efficient shape |
| corner | Corner (sumi) | Corner positions have special properties |
| endgame | Endgame (yose) | This is an endgame (yose) problem |
| tesuji | Tesuji | Look for a sharp tactical move |
| joseki | Joseki | This tests joseki knowledge |
| fuseki | Fuseki | Consider the whole-board balance |
| dead-shapes | Dead Shapes | Recognize the shape — is it already dead? |

### 4 Alias Entries (squeeze, connect, cut, capture)

These are backward-compatibility aliases in `TECHNIQUE_HINTS` that duplicate other entries. They have no config entries but their canonical tags do, so they are only reached if old tagger keys are used.

### Key Finding: TECHNIQUE_HINTS Dual Purpose

The `TECHNIQUE_HINTS` dict stores `(technique_hint, reasoning_template)` tuples:
- **tuple[0] (technique_hint)**: NOW DEAD CODE for YH1 — config always wins for all 28 tags. Kept as fallback for resilience.
- **tuple[1] (reasoning_template)**: ACTIVELY USED by `generate_reasoning_hint()` for YH2 base reasoning text. Cannot be removed.

> **See also**: [Charter](./00-charter.md) — [Plan](./30-plan.md)
