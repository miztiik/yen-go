# Tagging Strategy Architecture

> **See also**:
>
> - [Concepts: Tags](../../concepts/tags.md) — Tag taxonomy and definitions
> - [Architecture: Enrichment](./enrichment.md) — Enrichment pipeline overview
> - [Architecture: Tactical Analyzer](./tactical-analyzer.md) — Board-level pattern detection
> - [Architecture: Pipeline](./pipeline.md) — Pipeline stages
> - [Config: tags.json](../../../config/tags.json) — Canonical tag definitions (28 tags)

**Last Updated**: 2026-03-09

---

## Design Principle: Precision Over Recall

**A misleading tag is worse than no tag.** The tagger only assigns tags when it has HIGH confidence in the detection. An empty tag list is a perfectly valid result.

This principle was established after expert review by two 9-dan professional Go players who identified that the previous tagger had excessive false positives — particularly with `life-and-death` being used as a catch-all fallback, `snapback` being assigned to every single-stone capture, and `ko` being triggered by any single stone in atari.

### Why No Fallback

The previous tagger defaulted to `life-and-death` when no technique was detected. This was wrong because:

1. **Not every tsumego is life-and-death** — Many puzzles are tesuji, capture, connection, or endgame problems
2. **Pedagogically misleading** — A student browsing "life-and-death" expects "make two eyes" or "kill the corner," not "find the clever tactical move"
3. **Source tags exist** — When source adapters provide category metadata, those tags are preserved and provide the primary classification

**Current behavior:** `detect_techniques()` returns an empty list when no technique is confidently detected. Source-provided tags are preserved separately by the analyze stage.

---

## Evidence-Based Confidence Scoring

Each detector produces a confidence level. Only tags at HIGH or CERTAIN are emitted.

```text
Confidence.NONE     = 0   # No evidence
Confidence.WEAK     = 1   # Heuristic match, likely false positive
Confidence.MODERATE = 2   # Pattern match but not verified
Confidence.HIGH     = 3   # Comment keyword OR verified board pattern
Confidence.CERTAIN  = 4   # Multiple signals agree (comment + board)
```

**Emission threshold:** `>= HIGH` (confidence 3+)

When multiple independent sources detect the same tag (e.g., comment says "ladder" AND board simulation confirms ladder chase), confidence is upgraded to CERTAIN.

---

## Detection Sources

### Phase 1: Comment Keywords (HIGH confidence)

Comment keywords are HIGH confidence because the puzzle author explicitly named the technique. Both English and Japanese keywords are scanned.

**Word boundary matching** uses plain string operations (no regex) via `_contains_word()`:

```text
"cut" matches in "make the cut" but NOT in "execute" or "shortcut"
"ko" matches in "this is a ko fight" but NOT in "kono te wa"
"eye" matches in "make an eye" but NOT in "eyebrow"
```

| English Keyword      | Tag                | Japanese Keyword | Tag            |
| -------------------- | ------------------ | ---------------- | -------------- |
| ladder               | `ladder`           | シチョウ         | `ladder`       |
| net, geta            | `net`              | ゲタ             | `net`          |
| snapback, snap back  | `snapback`         | ウッテガエシ     | `snapback`     |
| ko                   | `ko`               | コウ             | `ko`           |
| throw-in, throw in   | `throw-in`         | ホウリコミ       | `throw-in`     |
| sacrifice            | `sacrifice`        | セキ             | `seki`         |
| eye                  | `eye-shape`        | 攻め合い         | `capture-race` |
| connect              | `connection`       | ナカデ           | `nakade`       |
| cut                  | `cutting`          |                  |                |
| squeeze              | `liberty-shortage` |                  |                |
| under the stones     | `under-the-stones` |                  |                |
| seki                 | `seki`             |                  |                |
| nakade               | `nakade`           |                  |                |
| capture race, semeai | `capture-race`     |                  |                |
| double + atari       | `double-atari`     |                  |                |

### Phase 2: Board Pattern Analysis (varies by technique)

Only three techniques have board-level detectors, each with strict verification:

#### Ko Detection — HIGH confidence

Uses the Board class's built-in ko detection. `Board.play()` sets `_ko_point` when a genuine ko shape is created: single stone captured AND the capturer has exactly 1 liberty (meaning the opponent could recapture). This is verified by actual Go rules, not a heuristic.

```text
After Board.play():
  if board._ko_point is not None → ko confirmed (HIGH)
  if ValueError("Ko violation") → ko also confirmed (MODERATE)
```

**Why this is reliable:** The Board implements actual ko rules. A `_ko_point` is only set when the mathematical conditions for ko are met.

#### Ladder Detection — HIGH confidence (3+ chase simulation)

Verified by simulating the chase in pure Python:

```text
1. Find opponent group in atari adjacent to the move
2. Simulate: runner extends at single liberty
3. After extension: runner should have exactly 2 liberties
4. Chaser plays at one liberty to create atari again
5. Repeat steps 2-4 for ≥3 iterations
6. If chase continues ≥3 forced atari-extend cycles → LADDER
```

**Why 3 moves:** A single atari with a diagonal escape is extremely common and NOT indicative of a ladder. The defining property of a ladder is that the chase continues in a forced diagonal direction. Three iterations is the minimum to confirm this pattern while avoiding false positives.

**Pure Python:** Uses `Board.play()`, `Board.copy()`, `Board.get_group()` — no external solver or AI engine.

#### Snapback Detection — HIGH confidence (sacrifice-recapture geometry)

Verified by checking the specific geometry after a single-stone capture:

```text
After capturing exactly 1 stone:
  1. Check our capturing group
  2. If our group has exactly 1 liberty AND >1 stone:
     → Opponent could recapture at the captured point
     → But would lose MORE than 1 stone (our entire group)
     → This is snapback geometry, not ko
```

**Why the old check was wrong:** The previous tagger tagged EVERY single-stone capture as "maybe snapback." Capturing single stones is the most common move in Go. A snapback requires the specific sacrifice-then-recapture pattern where capturing our bait stone causes the opponent to lose their own group.

### Tags Never Detected From Board Analysis

These techniques are too subtle for algorithmic detection without full-position solving. They are ONLY tagged from comment keywords:

- `net` — Requires reading all possible escape routes
- `throw-in` — Requires understanding sacrifice intent
- `sacrifice` — Requires understanding strategic purpose
- `nakade` — Requires vital point reasoning
- `eye-shape` — Too ambiguous without context
- `connection`, `cutting` — Too common as moves
- `double-atari` — Possible but current detection unreliable
- `liberty-shortage` — Requires understanding squeeze sequence
- `under-the-stones` — Requires capture-and-replay sequence
- `seki` — Requires mutual-life reading

---

## Capture-Race (Semeai) — Special Handling

Capture-race is assigned MODERATE confidence from board analysis (not emitted alone). It requires:

1. **Localized check** — Only examines groups adjacent to the capture site (not the entire board)
2. **Mutual low-liberty** — Both sides must have groups with ≤3 liberties near the capture
3. **Only emitted at HIGH** — Requires comment confirmation to reach emission threshold, OR multiple board signals upgrading to CERTAIN

**Why localized:** The old tagger scanned the entire board for any groups with ≤4 liberties. In real game positions, there are almost always low-liberty groups somewhere. The localized check only considers groups relevant to the actual problem.

---

## Tagging Order in the Analyze Pipeline

The tagger runs on the **original, unmodified** SGFGame object:

```text
parse_sgf(content)          → SGFGame with raw comments
    ↓
classify_difficulty(game)   → No comment modification
    ↓
detect_techniques(game)     → Tags from ORIGINAL comments ← HERE
    ↓
enrich_puzzle(game, config) → Reads original comments for hints
    ↓
_enrich_sgf(...)            → Comment cleaning happens HERE (output only)
    ↓
builder.build()             → standardize_move_comment() for serialization
```

**Critical:** The tagger MUST run before comment cleaning/standardization. The current pipeline already ensures this — `detect_techniques()` receives the parsed game with original comments intact. Comment cleaning only occurs during output serialization in `_enrich_sgf()` and `builder.build()`.

---

## Tag Source Priority

When source-provided tags and detected tags coexist:

| Priority | Source                            | Handling                                        |
| -------- | --------------------------------- | ----------------------------------------------- |
| 1        | Source-provided tags (adapter YT) | Preserved if present — human curation signal    |
| 2        | High-confidence detected tags     | Merged with source tags                         |
| 3        | No tags from either source        | Empty YT — honest, can be tagged manually later |

---

## Architectural Decisions Record

| Decision                                        | Rationale                                                                                        | Date       |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------ | ---------- |
| Remove `life-and-death` fallback                | Misleading; not all tsumego are L&D; source tags provide primary classification                  | 2026-02-22 |
| Word-boundary matching without regex            | Plain string ops; avoids regex complexity; `_contains_word()` prevents substring false positives | 2026-02-22 |
| Ko from Board.\_ko_point only                   | Go-rules-verified; eliminates "single stone in atari = ko" false positives                       | 2026-02-22 |
| Ladder requires 3+ chase simulation             | Single-atari diagonal escape is too common; chase simulation confirms actual ladder pattern      | 2026-02-22 |
| Snapback requires sacrifice-recapture geometry  | Single-stone capture is ubiquitous; snapback needs our-group-in-atari-with-multiple-stones shape | 2026-02-22 |
| Net detection comment-only (no board heuristic) | "Opponent at distance 2 with few liberties" matches too many normal positions                    | 2026-02-22 |
| Capture-race localized to capture site          | Whole-board scan for low-liberty groups produced massive false positives                         | 2026-02-22 |
| Confidence enum for evidence scoring            | Enables future multi-signal fusion; makes emission threshold explicit                            | 2026-02-22 |
| Preserve source-provided tags                   | Adapter tags from source metadata carry human curation signal                                    | 2026-02-22 |

---

## Impact Assessment

| Previous Behavior                               | New Behavior                                       | Effect                                 |
| ----------------------------------------------- | -------------------------------------------------- | -------------------------------------- |
| ~70% puzzles tagged `life-and-death` (fallback) | Many become untagged (source tags still preserved) | Honest classification                  |
| Every single-stone capture → `snapback`         | Only sacrifice-recapture geometry → `snapback`     | Eliminates majority of false positives |
| Every single-stone-in-atari → `ko`              | Only Board-verified ko shape → `ko`                | Near-zero false positives              |
| Diagonal atari escape → `ladder`                | 3+ chase simulation → `ladder`                     | Very low false positive rate           |
| Distance-2 weak group → `net`                   | Comment only → `net`                               | No board false positives               |
| Whole-board low-liberty scan → `capture-race`   | Localized scan near capture site                   | Relevant detection only                |
| `"cut"` matches `"execute"`                     | Word-boundary matching                             | No substring false positives           |
