# Teaching Comments

> **See also**:
>
> - [Concepts: Hints](./hints.md) — Pre-solve progressive hints (YH property)
> - [Architecture: Hint Architecture](../architecture/backend/hint-architecture.md) — Hint generation pipeline
> - [Concepts: SGF Properties](./sgf-properties.md) — C[] property in SGF
> - [Concepts: Tags](./tags.md) — 28 canonical technique tags

**Last Updated**: 2026-03-19

---

## Purpose

Teaching comments are **post-solve explanations** embedded as `C[]` properties on solution tree nodes in SGF files. They explain _why_ the correct move works and _what went wrong_ with incorrect moves, using precise technique terminology.

Teaching comments are distinct from **hints** (pre-solve, in `YH`) and **go tips** (ambient, in `config/go-tips.json`).

---

## Three-System Separation

| System                | When shown                  | Purpose                       | Storage                        |
| --------------------- | --------------------------- | ----------------------------- | ------------------------------ |
| **Teaching comments** | After the move is played    | Explain technique & mechanism | SGF `C[]` on move nodes        |
| **Hints** (YH)        | Before the move, on request | Guide toward the technique    | Root `YH[h1\|h2\|h3]` property |
| **Go tips**           | Session ambient             | General Go knowledge          | `config/go-tips.json`          |

---

## Design Principles

### 1. Precision Over Emission

Never emit a false, vague, or misleading comment. A missing comment is always preferable to a wrong one. If the system cannot confidently identify the technique, the teaching comment is suppressed entirely.

### 2. Technique-Grounded

Every comment names the specific technique and its key mechanism. Comments follow the pattern:

```
{Technique} ({japanese_term}) — {one key mechanism}.
```

Maximum 15 words. No filler text, no generic encouragement.

### 3. Confidence-Gated

Comments are only emitted when tag classification confidence meets the tag's minimum threshold:

| Tag                | Required Confidence |
| ------------------ | ------------------- |
| Most tags          | HIGH                |
| `joseki`, `fuseki` | CERTAIN             |

When confidence is insufficient, the `correct_comment` is suppressed to an empty string. Wrong-move comments are still emitted (they depend on PV quality, not tag confidence).

### 4. One Insight Rule

Each comment delivers exactly **one** actionable insight per move. Multi-sentence explanations are avoided — the student should learn one concept per interaction.

### 5. Student Learning

Comments exist to teach. Japanese/Korean terms are included where they are standard Go terminology (e.g., "uttegaeshi" for snapback, "shicho" for ladder). This helps students recognize and name patterns using the universal vocabulary of Go.

---

## Configuration

Source of truth: `config/teaching-comments.json`

### Correct-Move Comments

Each of the 28 canonical tags has an entry with:

| Field                | Type    | Description                                               |
| -------------------- | ------- | --------------------------------------------------------- |
| `comment`            | string  | V1 full teaching comment (max 15 words, used as fallback) |
| `technique_phrase`   | string  | V2 Layer 1 technique name (2-4 words)                     |
| `vital_move_comment` | string  | V2 comment for the vital (decisive) move                  |
| `hint_text`          | string  | Technique name only (used by hint generator Tier 1)       |
| `min_confidence`     | enum    | `HIGH` or `CERTAIN` — confidence gate threshold           |
| `alias_comments`     | object? | Specific comments for tag aliases                         |

### Alias Sub-Comments

Some tags have aliases with more specific comments:

- **dead-shapes**: 9 aliases (bent-four, bulky-five, rabbity-six, l-group, straight-three, flower-six, table-shape, pyramid-four, crossed-five)
- **tesuji**: 11 aliases (hane, crane's nest, wedge, tiger's mouth, kosumi, keima, warikomi, nose tesuji, descent, sagari, atekomi)
- **cutting**: 3 aliases (crosscut, peep, nozoki)

Alias resolution order:

1. Look up canonical tag in `correct_move_comments`
2. Within that entry, check all technique tags for `alias_comments` match
3. If no canonical match, scan alias tables across all entries
4. Fallback to `life-and-death`

### Wrong-Move Comments

V2+ uses 12 priority-ordered conditions (first-match-wins), governed by voice principles VP-1 through VP-5 (see D73 ADR):

#### Voice Principles

| # | Principle | Rule |
|---|-----------|------|
| VP-1 | Board speaks first | Show opponent action + consequence. Never narrate student error. |
| VP-2 | Action → consequence | `{who} {action} — {result}.` Dash separates cause from effect. |
| VP-3 | Verb-forward, article-light | Drop "The"/"A"/"This" when subject is obvious. |
| VP-4 | 15 words maximum | Combined wrong-move + opponent-response ≤ 15 words. |
| VP-5 | Warm on near-misses only | Only `almost_correct` gets warmth; all others: zero sentiment. |

#### Wrong-Move Templates

| Priority | Condition              | Comment                                                   | Guard                           | Opponent-Response |
| -------- | ---------------------- | --------------------------------------------------------- | ------------------------------- | ----------------- |
| 1        | `immediate_capture`    | "Captured immediately."                                   | PV depth ≤ 1 + capture verified | ✅ `{opp} {!move} — captures the stone.` |
| 2        | `opponent_escapes`     | "Opponent escapes at {!xy}."                              | Escape detected in PV           | ❌ suppress |
| 3        | `opponent_lives`       | "Opponent makes two eyes — lives."                        | Ownership flip                  | ❌ suppress |
| 4        | `capturing_race_lost`  | "Loses the race."                                         | Liberty comparison              | ✅ `{opp} {!move} — fills the last liberty.` |
| 5        | `opponent_takes_vital` | "Opponent takes vital point {!xy} first."                 | PV[0] == correct coord          | ❌ suppress |
| 6        | `opponent_reduces_liberties` | "Opponent reduces liberties at {!xy}."               | Liberty reduction detected      | ❌ suppress |
| 7        | `self_atari`           | "Ends in atari."                                          | Self-atari detected             | ✅ `{opp} {!move} — captures the stone.` |
| 8        | `shape_death_alias`    | "Creates {alias} — unconditionally dead."                 | tag=dead-shapes + alias         | ❌ suppress |
| 9        | `ko_involved`          | "Leads to ko — direct path avoids it."                    | Ko in PV                        | ❌ suppress |
| 10       | `wrong_direction`      | "Doesn't address the key area."                           | Wrong direction detected        | ✅ `{opp} {!move} — claims the vital area.` |
| 11       | `almost_correct`       | "Close — {!xy} is slightly better."                       | Delta < threshold               | ❌ suppress |
| 12       | `default`              | "Opponent has a strong response."                         | Always matches                  | ✅ `{opp} {!move} — responds decisively.` |

**Opponent-response**: 5 of 12 conditions emit an opponent-response phrase using PV[0] from refutation analysis. The other 7 suppress because the wrong-move template already fully describes the opponent's action. Feature-gated via `use_opponent_policy` in `TeachingConfig` (default: off).

**Conditional dash rule**: If the wrong-move template already contains `—`, the opponent-response uses no additional dash (one dash per comment maximum).

Delta annotations append loss context:

- Significant loss (>50%): "Loses approximately {N}% of the position."
- Moderate loss (>20%): "Results in a significant disadvantage."

---

## V2 Architecture: Two-Layer Composition

V2 introduces a two-layer composition model that separates _what_ (technique) from _how_ (signal):

### Layer 1: Technique Phrase

The technique name from config (`technique_phrase` field). Examples:

- "Snapback (uttegaeshi)"
- "Life & Death (shikatsu)"
- "Ko (kō)"

### Layer 2: Signal Phrase

Detected from engine analysis data. 6 signal types:

| Signal                 | Template                              | Trigger                            |
| ---------------------- | ------------------------------------- | ---------------------------------- |
| `vital_point`          | "vital point {!xy}"                   | Engine identifies vital coordinate |
| `forcing`              | "only move — all alternatives fail"   | Zero alternative correct moves     |
| `non_obvious`          | "surprising move — decisive at {!xy}" | Correct move has low policy        |
| `unique_solution`      | "only path to success"                | Single solution branch             |
| `sacrifice_setup`      | "sacrifice now, exploit the response" | Sacrifice tag present              |
| `opponent_takes_vital` | "opponent takes vital point {!xy}"    | Refutation targets vital coord     |

### Assembly Rules

- Composition: `{technique_phrase} — {signal_phrase}.`
- 15-word cap (parenthetical Japanese terms count as 1 word per RC-4)
- Overflow strategy: signal replaces mechanism suffix
- V1 fallback: when no signal detected, emit V1 `comment` field verbatim

### Vital Move Detection

For puzzles with `move_order=strict`, V2 walks the solution tree to find the decisive move (branching decision point or ownership-change inflection). The vital move gets its own `vital_move_comment`.

### Wrong-Move Classification

Refutations are classified into 12 conditions by priority (first-match-wins). Top 3 by refutation depth get causal annotations; remainder get default. 5 of 12 conditions emit opponent-response phrases (see table above).

### Quality Levels (hc)

| hc  | Meaning                          |
| --- | -------------------------------- |
| 0   | Suppressed (confidence gate)     |
| 2   | V1 fallback (no signal detected) |
| 3   | Signal-enriched (Layer 2 active) |

---

## SGF Embedding (Phase 3)

Teaching comments are embedded via KaTrain's SGFNode in `enrich_sgf()` Phase 3:

1. **Correct first move node** (`root[0]`): Gets the technique teaching comment as `C[]`
2. **Wrong-move branches**: Each refutation branch root whose move matches a `wrong_comments` key gets the wrong-move comment appended to its existing `C[]`
3. **Append, never overwrite**: If a node already has `C[]` content, the teaching comment is appended with `\n\n` separator
4. **Confidence gate**: If `teaching_comments` is empty (suppressed upstream), Phase 3 is a no-op

---

## V3 Enhancements

### Delta Gate and Almost-Correct Template (F17, F23)

Wrong-move comments now apply a **delta gate** before classification. When a wrong move's winrate loss (`abs(delta)`) is below `almost_correct_threshold` (default: 0.05, configurable in `config/teaching-comments.json`), it receives the "almost correct" template instead of "Wrong":

> "Close — {!xy} is slightly better."

This uses the `"Close"` prefix instead of `"Wrong."` to acknowledge the player was on the right track while redirecting to the correct move via the `{!xy}` coordinate token.

### Vital Move Placement (F16)

For multi-move solution sequences, the teaching comment is now placed on the **decisive tesuji node** rather than the root. When all conditions are met, the root comment is suppressed and the comment appears at the vital node:

- `vital_result.move_index > 0` (vital move differs from the first move)
- `tag_confidence == "CERTAIN"` (high classification confidence)

The SGF embedder (`_embed_teaching_comments()`) walks the main line to the vital node index. If the tree is shorter than expected, vital placement is skipped with a warning.

### Expanded Wrong-Move Classifier (F15)

Three new refutation conditions were added to `CONDITION_PRIORITY`:

| Condition | Template | Data Field |
|-----------|----------|------------|
| `opponent_reduces_liberties` | "The opponent reduces your liberties at {!xy}." | `ref.liberty_reduction` |
| `self_atari` | "This stone ends up in atari." | `ref.self_atari` |
| `wrong_direction` | "This move doesn't address the key area." | `ref.wrong_direction` |

These conditions fire only when the corresponding engine PV data fields are present; they are no-ops on puzzles without these fields.

---

## Known Limitations (V2)

1. **Single technique per puzzle**: The teaching comment reflects the primary tag only. Puzzles tagged with multiple techniques get a comment for the highest-priority tag.

2. **Signal detection is heuristic**: Layer 2 signals are detected from engine data fields (policy, PV, ownership). Not all puzzles have the engine data needed to trigger signals — these fall back to V1 comments (hc:2).

3. **Vital move depth limit**: Vital move detection walks the solution tree linearly. In trees with complex branching, the vital move may not be the one with the highest pedagogical value.

---

## Threshold Calibration Rationale

All teaching-comment thresholds are externalized in `config/katago-enrichment.json` under the `teaching` key and in `config/teaching-comments.json` for signal templates. This section documents the **reasoning** behind each calibrated value.

### Signal Detection Thresholds (`config/katago-enrichment.json → teaching`)

| Key                          | Value | Rationale                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `non_obvious_policy`         | 0.10  | KataGo's policy prior represents how "expected" a move is. A threshold of 0.05 was too aggressive — it flagged moves that were merely uncommon but not genuinely surprising, producing noise. At 0.10, a move must be outside KataGo's top-probability consideration (below 10% policy) to qualify as "surprising". This balances pedagogical signal (the student learns the move is worth studying because it's unintuitive) against false positives. The value was chosen based on Go domain expertise: professional-level "trick moves" and tesuji typically have policy priors between 1-8%, while routine correct moves sit above 15%. |
| `ko_delta_threshold`         | 0.12  | This threshold determines how much ownership must shift to label a wrong move as "leading to ko". At 0.10, borderline ownership fluctuations — often noise from engine visits rather than genuine ko fights — triggered false ko annotations. At 0.12, only moves where the board state genuinely pivots between players qualify. This 2-percentage-point increase removes edge-case noise while still catching all real ko complications (which typically produce ownership deltas of 0.15+).                                                                                                                                              |
| `capture_depth_threshold`    | 1     | A PV depth of 1 means the capture happens immediately (the very next move). This is unambiguous and matches the "immediate capture" wrong-move condition. Raising it would conflate multi-step captures with immediate captures, losing specificity. Confirmed correct.                                                                                                                                                                                                                                                                                                                                                                     |
| `significant_loss_threshold` | 0.50  | Losses exceeding 50% of the position are genuinely game-losing errors. This is the standard boundary for delta annotations that say "Loses approximately N% of the position." At 50%, the move is effectively resigning a portion of the board. This aligns with KataGo's winrate semantics where a 0.50 drop means going from winning to even or worse. Confirmed correct.                                                                                                                                                                                                                                                                 |
| `moderate_loss_threshold`    | 0.20  | Losses between 20-50% represent significant positional damage — enough to trigger "Results in a significant disadvantage" annotations. Below 20%, the loss may be recoverable or within engine noise. Above 20% is where a kyu-level student should understand the move is seriously suboptimal. Confirmed correct.                                                                                                                                                                                                                                                                                                                         |

### Signal Template Wording (`config/teaching-comments.json → signal_templates`)

| Signal                 | Template                              | Rationale                                                                                                                                                                                                                                                                  |
| ---------------------- | ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vital_point`          | "vital point {!xy}"                   | Standard Go term. No ambiguity.                                                                                                                                                                                                                                            |
| `forcing`              | "only move — all alternatives fail"   | Pedagogically clear: the student understands there is no alternative.                                                                                                                                                                                                      |
| `non_obvious`          | "surprising move — decisive at {!xy}" | Changed from "non-obvious" because "surprising" is more emotionally engaging for a student and more precise in Go pedagogy. "Non-obvious" is clinical; "surprising" communicates that even an AI didn't predict this as the top move, which heightens the learning moment. |
| `unique_solution`      | "only path to success"                | Communicates single-solution constraint clearly.                                                                                                                                                                                                                           |
| `sacrifice_setup`      | "sacrifice now, exploit the response" | Captures the two-phase nature of sacrifice sequences.                                                                                                                                                                                                                      |
| `opponent_takes_vital` | "opponent takes vital point {!xy}"    | Mirror of vital_point for wrong-move branches.                                                                                                                                                                                                                             |

### Confidence Gating

Signal detection is further gated by per-tag `min_confidence` thresholds (see [Configuration](#configuration) above). Signals are only attached when the primary tag classification confidence meets or exceeds the tag's threshold (`HIGH` for most tags, `CERTAIN` for joseki/fuseki). This two-tier gating — confidence first, then signal thresholds — ensures the teaching comment is both technique-accurate and signal-accurate.

### Signal Priority Order

Signals are detected in a fixed priority order: `vital_point` → `forcing` → `sacrifice_setup` → `non_obvious` → `unique_solution`. This order ensures the most pedagogically valuable signal wins when multiple signals are present. For example, if a move is both a vital point and non-obvious, "vital point" is more actionable for the student than "surprising move". The priority was chosen based on Go pedagogy: spatial signals (vital point) > constraint signals (forcing, sacrifice) > surprise signals (non_obvious) > structural signals (unique_solution).

---

## Validation

A cross-validation test ensures all 28 tags from `config/tags.json` have entries in `config/teaching-comments.json`. This test prevents drift between the tag taxonomy and teaching content.

Each comment is validated to be ≤15 words at config load time.

---

## Enrichment Lab: Teaching Comment Assembly

The enrichment lab (`tools/puzzle-enrichment-lab/`) generates teaching comments from KataGo analysis signals during the `TeachingStage` pipeline stage.

### Comment Assembly Pipeline

Teaching comments are assembled by `comment_assembler.py`, which composes technique phrases (Layer 1) with engine-detected signal phrases (Layer 2):

1. **TechniqueStage** → 28 detectors produce `detection_results` with tag classifications
2. **TeachingStage** reads detection results + KataGo analysis data
3. **`assemble_correct_comment()`** → V2 two-layer composition: `{technique_phrase} — {signal_phrase}.`
4. **`assemble_wrong_comment()`** → 12-condition first-match classification + optional opponent-response

### Opponent-Response Teaching Comments (PI-10)

When `use_opponent_policy=True` in `TeachingConfig`, wrong-move comments are enriched with the opponent's best response from refutation PV[0]:

```
Wrong-move template + " " + Opponent-response phrase
```

**5 active conditions** emit opponent-response:

| Condition | Opponent-Response Template |
|-----------|--------------------------|
| `immediate_capture` | `{opp} {!move} — captures the stone.` |
| `capturing_race_lost` | `{opp} {!move} — fills the last liberty.` |
| `self_atari` | `{opp} {!move} — captures the stone.` |
| `wrong_direction` | `{opp} {!move} — claims the vital area.` |
| `default` | `{opp} {!move} — responds decisively.` |

**7 suppressed conditions**: `opponent_escapes`, `opponent_lives`, `opponent_takes_vital`, `opponent_reduces_liberties`, `shape_death_alias`, `ko_involved`, `almost_correct` — the wrong-move template already fully describes the opponent's action, so appending more would be redundant.

**Conditional dash rule**: If the wrong-move template already contains `—`, the opponent-response omits the dash (one dash per comment maximum).

### Terse Label Replacement

When embedding teaching comments into SGF `C[]` properties via `_embed_teaching_comments()` in `sgf_enricher.py`, bare correctness markers ("Wrong", "Incorrect.", "-", "+") are **replaced** by richer teaching comments. Substantive author comments (containing text beyond the marker) are preserved via append. Detection uses the canonical `infer_correctness_from_comment()` from `tools/core/sgf_correctness.py`.

> **See also:**
>
> - [Architecture: KataGo Enrichment — Pipeline Stages](../architecture/tools/katago-enrichment.md#pipeline-stages) — TeachingStage details
> - [Reference: Enrichment Config](../reference/katago-enrichment-config.md) — `teaching` config section
