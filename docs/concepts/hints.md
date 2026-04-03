# Hints System

> **See also**:
>
> - [Concepts: SGF Properties](./sgf-properties.md) — YH property format
> - [Architecture: Enrichment](../architecture/backend/enrichment.md) — Hint generation
> - [Architecture: Hint Architecture](../architecture/backend/hint-architecture.md) — Full design, expert reviews, tag coverage

**Last Updated**: 2026-03-19

The YenGo hint system provides progressive **pedagogical** hints that guide puzzle solvers toward the correct technique without giving away the answer. Hints are pre-computed at build time and stored in the `YH` SGF property.

---

## Hint Format

Hints are stored in the `YH` property using compact pipe-delimited format:

```sgf
YH[hint1|hint2|hint3]
```

**Maximum 3 hints** per puzzle. Puzzles may have 0–3 hints depending on what the system can generate meaningfully.

---

## Hint Progression

Hints follow a **Technique → Reasoning → Coordinate** progression (concept first, answer last):

| Order | Type       | Description                             | Example                                                                  |
| ----- | ---------- | --------------------------------------- | ------------------------------------------------------------------------ |
| 1     | Technique  | Name the concept to apply               | "Try surrounding loosely with a net (geta)."                             |
| 2     | Reasoning  | Explain why + warn about wrong approach | "Direct capture doesn't work — the opponent has too many escape routes." |
| 3     | Coordinate | Give the answer + what it achieves      | "Play at {!cg}. This creates an inescapable enclosure."                  |

### Example (net problem)

```sgf
YH[Try surrounding loosely with a net (geta).|Direct capture doesn't work — the opponent has too many escape routes.|Play at {!bg}. This creates an inescapable enclosure.]
```

- Hint 1: Technique — tells the solver WHAT concept to think about
- Hint 2: Reasoning — explains WHY that technique and warns against the wrong approach
- Hint 3: Coordinate — gives the answer with a technique-aware outcome description

### Design Rationale

The key decision is to **name the technique first**. In a tsumego the board position is already visible, so a vague location hint adds less value than identifying the solving concept that unlocks the reading.

---

## Transform Awareness

Board transforms (flip, rotate, color swap) are applied at runtime. Hints are designed to remain correct under all transforms:

### Inherently Transform-Invariant

- **Technique hints (YH1)**: Reference patterns ("ladder", "net") and solving concepts, not colors or coordinates. A ladder is a ladder regardless of board orientation.
- **Reasoning hints (YH2)**: Use role-based labels ("Your group", "the opponent") instead of color names ("Black", "White"). Technique reasoning is orientation-independent.

### Transform-Aware via Tokens

- **Coordinate hints (YH3)**: Use `{!xy}` tokens instead of human-readable coordinates. The display layer resolves these after applying transforms.
- **Liberty analysis (YH2)**: When included (only for capture-race/ko), uses role-based labels ("Your group", "the opponent") instead of color names.

### `{!xy}` Token Format

Tokens embed SGF coordinates that the display layer resolves at render time:

| Token   | SGF Coordinate | Meaning                             |
| ------- | -------------- | ----------------------------------- |
| `{!aa}` | `aa`           | Point (0,0) — top-left              |
| `{!jj}` | `jj`           | Point (9,9) — board center on 19x19 |
| `{!cg}` | `cg`           | Point (2,6)                         |
| `{!ss}` | `ss`           | Point (18,18) — bottom-right        |

These tokens let hint text stay stable in SGF while rendered coordinates adapt to the current board orientation.

---

## Hint Types

### Technique Hints (YH1)

Name the concept or pattern to apply (transform-invariant). **Config-driven**: hint text is read from `config/teaching-comments.json` `hint_text` field, which includes standard Japanese/Korean terms. All 28 tags in `config/tags.json` have a corresponding hint:

- "Ladder (shicho)."
- "Net (geta)."
- "Snapback (uttegaeshi)."
- "Capture Race (semeai)."
- "Nakade."

When atari is detected, the primary tag is NOT capture-race/ko, **and the correct move actually captures the atari group**, atari becomes a standalone technique hint:

- "The opponent is in atari! Look for the capturing move."
- "Your group is in atari! Escape or make eyes immediately."

If the opponent is in atari but the correct move does **not** capture that group, the atari hint is suppressed ("Do No Harm" — prevents misleading guidance toward an irrelevant capture).

### Reasoning Hints (YH2)

Explain WHY the technique works and warn about wrong approaches (transform-invariant):

- "Direct capture doesn't work — the opponent has too many escape routes."
- "The opponent can only escape in one direction."
- "Letting opponent capture leads to recapture."
- "Compare liberties: the group with fewer will be captured first." _(only for capture-race/ko)_

**Liberty gating**: Liberty analysis is only included when the primary tag is `capture-race` or `ko`. For all other techniques, liberty information is suppressed because it frames the problem incorrectly.

**Dynamic reasoning enrichment**: When a solution tree is available, YH2 is enriched with:

- **Solution depth** (depth ≥ 2): "The solution requires N moves of reading." — tells the solver how deep to read.
- **Refutation count** (> 0 wrong first moves): "There are N tempting wrong moves." — calibrates the solver's expectations.
- **Secondary tag** (when 2+ tags): "Also consider: Net (geta)." — cross-references related techniques using Japanese terms from `config/teaching-comments.json`.

Example composite YH2:
> "The opponent can only escape in one direction. The solution requires 5 moves of reading. There are 2 tempting wrong moves."

### Coordinate Hints (YH3)

Specific move with technique-aware outcome (uses `{!xy}` tokens):

- "Play at {!cg}. This creates an inescapable enclosure." _(net)_
- "Play at {!cg}. This begins the chase." _(ladder)_
- "Play at {!cg}. Let them capture — then take back more." _(snapback)_

**Depth gating for outcome text**: The coordinate is always generated when a solution exists. Technique-specific outcome text (e.g., "This begins the chase.") is only appended for depth 4+ puzzles.

---

## Generation Rules

The enricher generates hints based on:

1. **Tags (highest-priority match)** → Technique hint (YH1)
2. **Tags + board state (conditional liberty analysis)** → Reasoning hint (YH2)
3. **First correct move + tags** → Coordinate hint (YH3, depth-gated)

### Tag Priority

When a puzzle has multiple tags, the most specific one drives hint generation:

| Priority    | Tags                                                                         |
| ----------- | ---------------------------------------------------------------------------- |
| 1 (highest) | `snapback`, `double-atari`, `connect-and-die`, `under-the-stones`, `clamp`   |
| 2           | `ladder`, `net`, `throw-in`, `sacrifice`, `nakade`, `vital-point`            |
| 3           | `capture-race`, `liberty-shortage`, `eye-shape`, `connection`, `cutting`     |
| 4 (lowest)  | `life-and-death`, `living`, `ko`, `seki`, `shape`, `corner`, `endgame`, etc. |

### Quality Requirements

- **Do No Harm** — A misleading hint is worse than no hint. If the system cannot generate a relevant hint, emit nothing
- **Atari relevance** — Atari hints are only emitted when the correct move captures the atari group
- Technique hints should match actual solving method
- Liberty analysis only for capture-race/ko puzzles
- Coordinate hints always generated when solution exists; outcome text only for depth 4+

### Solution-Aware Fallback (No Tags)

When the tagger assigns zero tags but a solution exists, the hint generator infers technique from the correct move's board effect via the `solution_tagger` module. Only HIGH+ confidence inferences produce hints:

| Move Effect     | Confidence | Inferred Tag | Hint                          |
| --------------- | ---------- | ------------ | ----------------------------- |
| Creates ko      | CERTAIN    | `ko`         | "This involves a ko fight."   |
| Connects groups | HIGH       | `connection` | "Try to connect your groups." |
| Captures stones | MEDIUM     | _(none)_     | Coordinate-only (YH3)         |
| Unknown         | LOW        | _(none)_     | Coordinate-only (YH3)         |

Principle: **100% certain or don't emit.** If the system cannot confidently identify the technique, it provides only the coordinate hint. A correct coordinate with no technique label is better than a misleading technique hint.

---

## Presentation Guidance

Hints are revealed progressively. The number of text tiers adapts to how many hints the backend provides — **no padding with filler**:

| Stored hints | Presentation tiers                                   |
| ------------ | ---------------------------------------------------- |
| 3 hints      | T1: hint[0], T2: hint[1], T3: hint[2] + board marker |
| 2 hints      | T1: hint[0], T2: hint[1] + board marker              |
| 1 hint       | T1: hint[0] + board marker                           |
| 0 hints      | T1: board marker only                                |

Consumers should reveal hints one at a time and avoid inserting filler text when only one or two hints are available.

---

## Legacy Format

**Deprecated**: YH1/YH2/YH3 format

```sgf
# OLD (deprecated)
YH1[Focus on corner]
YH2[Ladder pattern]
YH3[bg]

# NEW
YH[Focus on the corner.|Look for a ladder pattern.|Play at {!bg}.]
```

The pipeline automatically migrates old format during enrichment.

---

## Validation

Hints are validated by the enricher:

- Maximum 3 hints
- Non-empty strings
- Pipe character (`|`) not allowed within hint text
- Coordinate tokens must use valid SGF coordinates (`{!` + two chars in a-s range + `}`)

---

## Instinct Classification (Tier 1 Enrichment)

The enrichment pipeline now classifies the **instinct** (move shape/intent) of the correct first move using purely geometric analysis of the board position. This classification prefixes Tier 1 hints with a move-intent descriptor.

### Instinct Types

| Instinct   | Description                                      | Example Hint Prefix                        |
| ---------- | ------------------------------------------------ | ------------------------------------------ |
| `push`     | Extends influence along an existing direction     | "Push to extend your influence."           |
| `hane`     | Wraps around opponent stones at a diagonal        | "Hane at the head of the opponent's group."|
| `cut`      | Separates opponent stones by playing between them | "Cut to disconnect the opponent."          |
| `descent`  | Plays one line closer to the edge                 | "Descend toward the edge."                 |
| `extend`   | Extends along a group's side                      | "Extend your group."                       |

Instinct classification depends only on stone geometry (adjacency, direction) — **zero KataGo engine queries** are used. This means classification is instant and deterministic.

### Integration with Tier 1

When instinct classification succeeds with sufficient confidence, the Tier 1 hint is enriched with a prefix that names the move shape before the technique:

- **Without instinct**: "Look for a net (geta)."
- **With instinct**: "Hane to surround — look for a net (geta)."

The instinct prefix gives the solver an immediate physical intuition for the first move, while the technique name provides the strategic context.

---

## Detection Evidence in Tier 2

Tier 2 (reasoning) hints are now enriched with **specific detection evidence** from `TechniqueStage` rather than relying solely on generic depth/refutation text.

### Before (Generic)

> "The solution requires 3 moves of reading. There are 2 tempting wrong moves."

### After (Evidence-Enriched)

> "The opponent's group has only 2 liberties — a direct approach works. The solution requires 3 moves of reading."

Detection results (from the 28 technique detectors) now flow through `PipelineContext.detection_results` and are read by `TeachingStage` to generate evidence-specific reasoning. This replaces the prior approach where detection evidence was discarded after tag generation.

---

## Level-Adaptive Content (Tier 2)

Tier 2 hints now vary their language and detail based on the puzzle's difficulty level. The system uses three level categories:

| Level Category | Levels                                            | Hint Style                                        |
| -------------- | ------------------------------------------------- | ------------------------------------------------- |
| `entry`        | novice, beginner, elementary                      | Simple language, focus on what to look for         |
| `core`         | intermediate, upper-intermediate, advanced        | Standard depth, include reading hints + refutations|
| `strong`       | low-dan, high-dan, expert                         | Concise/terse, assume familiarity with techniques  |

Level categorization is determined by `get_level_category()` in `config/helpers.py`, using the puzzle's `YG` level slug. Templates for each category are defined in `LevelAdaptiveTemplates` within `config/teaching.py`.

### Examples by Level

**Entry (elementary):**
> "Look carefully at the corner stones. Can you see which group has fewer liberties?"

**Core (intermediate):**
> "The opponent's corner group has 3 liberties. A direct approach via the first line reduces them fastest."

**Strong (low-dan):**
> "L3 shortage; first-line approach."

---

## Enrichment Lab: Consolidated 3-Tier Hint Generator

The enrichment lab (`tools/puzzle-enrichment-lab/analyzers/hint_generator.py`) implements a consolidated hint generator that extends the backend hint system with additional gating, inference, and observability features.

### Tier Architecture

| Tier | Name | Source | Gating |
|------|------|--------|--------|
| **Tier 1** | Technique | `hint_text` from `config/teaching-comments.json` via tag lookup | Always emitted when tags present; inference-based when tags absent |
| **Tier 2** | Reasoning | Detection evidence + analysis data + level-adaptive templates | Liberty analysis only for `capture-race`/`ko` tags |
| **Tier 3** | Coordinate | Correct move with `{!xy}` token + technique-specific outcome text | Depth-gated: outcome text only for depth ≥ `TIER3_DEPTH_THRESHOLD` (3) |

### Atari Relevance Gating

Atari hints are suppressed when:
- The primary tag is in `ATARI_SKIP_TAGS` (`capture-race`, `ko`, `sacrifice`, `snapback`, `throw-in`) — the technique IS the point, so naming "atari" would obscure it
- The correct move does NOT capture the group in atari — prevents misleading guidance toward an irrelevant capture

### Depth-Gated Tier 3 (Spoiler Prevention)

The coordinate hint always includes the `{!xy}` token when a solution exists. However, the **technique-specific outcome text** (e.g., "This begins the chase.") is only appended when solution depth ≥ 3 (`TIER3_DEPTH_THRESHOLD`). For shallow puzzles (depth 1–2), giving both the coordinate and the outcome description is too much spoiler.

### Solution-Aware Fallback with InferenceConfidence

When the tagger assigns zero tags, the hint generator infers technique from the analysis data via `infer_technique_from_solution()`:

```python
class InferenceConfidence(IntEnum):
    LOW = 0       # No detectable effect — coordinate only
    MEDIUM = 1    # Ambiguous but plausible (long PV, multi-move reading)
    HIGH = 2      # Verifiable from analysis data (refutations + depth)
```

| Analysis Signal | Inferred Tag | Confidence | Hint Output |
|----------------|-------------|------------|-------------|
| Refutations > 0 AND depth ≥ 2 | `life-and-death` | HIGH | Full 3-tier hints |
| PV length ≥ 6 | `ko` | MEDIUM | Coordinate only |
| Depth ≥ 3 | `tesuji` | MEDIUM | Coordinate only |
| Insufficient evidence | _(none)_ | LOW | Coordinate only |

Only HIGH+ confidence produces technique/reasoning hints. MEDIUM and LOW produce coordinate-only (Tier 3) hints.

### HintOperationLog (Observability)

Every hint generation produces a structured `HintOperationLog` capturing decisions per tier:

| Field | Values | Purpose |
|-------|--------|---------|
| `tier1_source` | `"config"`, `"inference"`, `"none"` | Where Tier 1 text came from |
| `tier2_source` | `"detection"`, `"analysis"`, `"none"` | Where Tier 2 reasoning came from |
| `tier3_source` | `"coordinate"`, `"suppressed_atari"`, `"depth_gated"`, `"none"` | Coordinate generation outcome |
| `tier3_depth_gated` | `true`/`false` | Whether outcome text was suppressed due to depth |
| `tier3_atari_suppressed` | `true`/`false` | Whether atari hint was suppressed due to irrelevance |
| `inference_used` | `true`/`false` | Whether solution-aware fallback was triggered |
| `inference_confidence` | `"LOW"`/`"MEDIUM"`/`"HIGH"` | Confidence level of the inference |

Enable via `return_log=True` parameter in `generate_hints()`.

### Liberty Analysis for Ko/Capture-Race

Tier 2 reasoning includes liberty analysis **only** when the primary tag is in `SEMEAI_KO_TAGS` (`capture-race`, `ko`). For all other techniques, liberty information is suppressed because it frames the problem incorrectly. This gating prevents generating misleading reasoning like "Compare liberties" for a ladder problem.

> **See also:**
>
> - [Architecture: KataGo Enrichment — Pipeline Stages](../architecture/tools/katago-enrichment.md#pipeline-stages) — TeachingStage in the enrichment pipeline
> - [Architecture: Hint Architecture](../architecture/backend/hint-architecture.md) — Backend pipeline hint system (superseded for enriched puzzles)
