# Hint Architecture

> **⚠️ Superseded for enrichment-lab puzzles.** The enrichment lab's consolidated 3-tier hint generator (`tools/puzzle-enrichment-lab/analyzers/hint_generator.py`) now produces hints for all KataGo-enriched puzzles. That generator adds atari relevance gating, depth-gated Tier 3 coordinate hints, solution-aware fallback with `InferenceConfidence`, and `HintOperationLog` observability. This backend hint architecture remains the canonical reference for the **pipeline-only** hint path (puzzles not processed by the enrichment lab). See [Architecture: KataGo Enrichment — Pipeline Stages](../../architecture/tools/katago-enrichment.md#pipeline-stages) for the lab's hint generation stage.

> **See also**:
>
> - [Concepts: Hints](../../concepts/hints.md) — Hint format, tokens, display rules
> - [Concepts: Teaching Comments](../../concepts/teaching-comments.md) — Post-solve explanations in C[]
> - [Architecture: Enrichment](./enrichment.md) — Overall enrichment pipeline
> - [Architecture: KataGo Enrichment](../../architecture/tools/katago-enrichment.md) — Lab enrichment design decisions
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — YH property spec

**Last Updated**: 2026-03-19

---

## Purpose

The hint system generates **pedagogically-sound progressive hints** that help puzzle solvers without giving away the answer. Hints are pre-computed at build time (Zero Runtime Backend) and stored in the `YH` SGF property.

---

## Design Principles

### Expert-Reviewed Pedagogy

The hint algorithm was designed and reviewed by three 1P-level Go professionals:

| Expert                     | Focus                  | Key Contribution                                                                                |
| -------------------------- | ---------------------- | ----------------------------------------------------------------------------------------------- |
| **Cho Chikun** (9-dan)     | Content quality        | Technique-specific reasoning; liberty analysis gating; improved hint text                       |
| **Lee Changho** (9-dan)    | Algorithm structure    | Tier ordering (Technique → Reasoning → Coordinate); tag priority system; tagger/hint separation |
| **Fujisawa Shuko** (9-dan) | Pedagogical philosophy | "Do No Harm" principle; suppress filler hints; depth-based gating                               |

### Core Principles

1. **Technique → Reasoning → Coordinate** — Name the concept first, explain WHY second, give the answer last
2. **Do No Harm** — A misleading hint is worse than no hint. If the system cannot generate a relevant hint, emit nothing
3. **Technique-Aware** — Liberty analysis, coordinate outcome text, and diagnostic framing all adapt based on the puzzle's technique tags
4. **Transform-Invariant** — Hints use role-based labels ("Your group", not "Black") and `{!xy}` coordinate tokens (not "D16") so they survive flip/rotate/color-swap transforms
5. **Tag-Driven with Confidence-Gated Fallback** — The hint generator is primarily a function of tags and solution tree. When tags are present, all intelligence lives in the tagger. When tags are absent, the `solution_tagger` module infers technique from the correct move's board effect — but only HIGH+ confidence inferences produce hints. MEDIUM (captures) and LOW (unknown) produce coordinate-only hints
6. **Atari Relevance** — Atari hints are only emitted when the correct move actually captures the group in atari. Irrelevant atari (present on the board but unrelated to the solution) is suppressed to prevent misleading guidance

---

## Architecture

### Data Flow

```
                         config/tags.json (28 tags)
                                │
Source SGF ──► Tagger ──► tags[] ──► HintGenerator ──► YH[h1|h2|h3]
                │                        │
                ├─ Comment keywords      ├─ generate_technique_hint(tags)
                ├─ Japanese keywords     ├─ generate_reasoning_hint(tags, game)
                └─ Board patterns        └─ generate_coordinate_hint(game, tags)
                                              │
                                    ┌─────────┘
                                    │
                              tags present?
                              ├─ YES → use tag-driven hints
                              └─ NO  → solution-aware fallback
                                       │
                                       ├─ play correct move on Board copy
                                       ├─ classify effect (ko/connects/captures/unknown)
                                       ├─ assign confidence (CERTAIN/HIGH/MEDIUM/LOW)
                                       └─ HIGH+ → tag hint; below → coordinate only
                                              │
                                        EnrichmentResult.hints[]
```

### Component Responsibilities

| Component                                           | Responsibility                                                                                         | Does NOT do                        |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| **Tagger** (`core/tagger.py`)                       | Assigns technique tags from board analysis, comments, patterns                                         | Generate hint text                 |
| **HintGenerator** (`core/enrichment/hints.py`)      | Maps tags → hint text using expert-reviewed templates; delegates to `solution_tagger` when tags absent | N/A                                |
| **enrich_puzzle()** (`core/enrichment/__init__.py`) | Orchestrates hint generation, logs diagnostics                                                         | Store hints — passes to SgfBuilder |
| **SgfBuilder** (`core/sgf_builder.py`)              | Serializes hints to `YH[h1\|h2\|h3]` format in SGF                                                     | Generate or interpret hints        |
| **Frontend HintOverlay**                            | Resolves `{!xy}` tokens, progressive disclosure UI                                                     | Generate or modify hint content    |

### Separation of Concerns (Lee Changho principle)

> "The hint generator should be a pure function of tags and solution tree. The tagger should be where all intelligence lives. If the tagger produces bad tags, fix the tagger. Don't make the hint generator compensate for tagger deficiencies."

This means:

- **Bad hints because wrong tag?** → Fix the tagger
- **Bad hints because bad template?** → Fix TECHNIQUE_HINTS
- **Missing hints because tag not covered?** → Add TECHNIQUE_HINTS entry
- **Missing hints because tag not detected?** → Add tagger pattern

### Exception: Confidence-Gated Solution-Aware Fallback (2026-02-24)

When the tagger assigns **zero tags**, the `solution_tagger` module (`core/enrichment/solution_tagger.py`) applies limited board analysis to avoid emitting no hints at all. This is NOT a replacement for proper tagging — it is a safety net with explicit confidence scoring:

1. Play the correct move on a `Board` copy
2. Classify the move's effect and assign confidence:
   - Creates ko → `ko` (CERTAIN)
   - Connects groups → `connection` (HIGH)
   - Captures stones → _(no tag)_ (MEDIUM — below threshold)
   - Unknown effect → _(no tag)_ (LOW — below threshold)
3. Only HIGH+ confidence produces technique/reasoning hints
4. MEDIUM/LOW confidence produces coordinate-only hints (YH3)

**Principle:** 100% certain the hint is correct, or don't emit it. A correct coordinate with no technique label is better than a misleading technique hint.

```python
# InferenceConfidence enum (solution_tagger.py)
class InferenceConfidence(IntEnum):
    LOW = 0       # Unknown effect — coordinate only
    MEDIUM = 1    # Captures — coordinate only
    HIGH = 2      # Connection — emit technique hint
    CERTAIN = 3   # Ko creation — emit technique hint

_EMIT_THRESHOLD = InferenceConfidence.HIGH
```

---

## Three-Tier Hint Progression

### Tier Design

| Tier    | Name       | Purpose                                 | Input                                             | Example (net problem)                                                                                     |
| ------- | ---------- | --------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| **YH1** | Technique  | Name the concept                        | Tags (highest priority match)                     | "Try surrounding loosely with a net (geta)."                                                              |
| **YH2** | Reasoning  | Explain why + warn about wrong approach | Tags + board state (conditional liberty analysis) | "Direct capture doesn't work — the opponent has too many escape routes. Think about surrounding loosely." |
| **YH3** | Coordinate | Give the answer + what it achieves      | Solution tree + tags                              | "Play at {!cg}. This creates an inescapable enclosure."                                                   |

### Why This Order (Not Region → Technique → Coordinate)

The previous system used Region → Technique → Coordinate. Expert review concluded:

| Old Tier 1             | Problem                                                                                                          |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------- |
| "Focus on the corner." | In a tsumego, the board position IS the problem. The stones are already there. Spatial orientation is redundant. |

| New Tier 1                           | Why Better                                                                                                                        |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| "Try surrounding with a net (geta)." | Gives the student a CONCEPT to think about. Without knowing what technique to look for, they can't even begin productive reading. |

---

## Teaching Comments vs. Hints vs. Tips

Yen-Go has three distinct pedagogical text systems. They share the same `config/teaching-comments.json` config file but serve different purposes:

| System                | When                    | Purpose                           | Storage               | Config field used                                                     |
| --------------------- | ----------------------- | --------------------------------- | --------------------- | --------------------------------------------------------------------- |
| **Teaching comments** | After move is played    | Explain the technique & mechanism | `C[]` on move nodes   | `technique_phrase` + `signal_templates` (V2), `comment` (V1 fallback) |
| **Hints** (YH)        | Before move, on request | Guide toward the technique        | Root `YH[h1\|h2\|h3]` | `hint_text` (Tier 1)                                                  |
| **Go tips**           | Session ambient         | General Go knowledge              | Frontend display      | `config/go-tips.json`                                                 |

### Shared Config: `config/teaching-comments.json`

The `hint_text` field (technique name + Japanese term only) feeds Tier 1 hints. Teaching comments V2 use `technique_phrase` (Layer 1) composed with engine-detected `signal_templates` (Layer 2) to produce rich post-solve explanations. The V1 `comment` field is retained as the fallback when no signal is detected. See [Concepts: Teaching Comments](../../concepts/teaching-comments.md) for the full two-layer architecture.

### Config Migration History

- **v1.0**: Migrated hardcoded `TECHNIQUE_HINTS` and `REASONING_HINTS` to config-driven lookup. Tier 2 reasoning hints are analysis-based.
- **v2.0**: Added `technique_phrase`, `vital_move_comment`, `signal_templates`, `assembly_rules`, `annotation_policy`. Two-layer composition model. 8 wrong-move condition templates.

---

## Tag Coverage

### Complete Coverage: All 28 Tags → Hint Text

Every tag in `config/tags.json` MUST have a corresponding entry in `TECHNIQUE_HINTS`. No silent failures.

#### Tag Priority Ordering

When a puzzle has multiple tags, the most specific one drives the hint:

| Priority    | Category            | Tags                                                                                                                |
| ----------- | ------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 1 (highest) | Specific tesuji     | `snapback`, `double-atari`, `connect-and-die`, `under-the-stones`, `clamp`                                          |
| 2           | Tactical techniques | `ladder`, `net`, `throw-in`, `sacrifice`, `nakade`, `vital-point`                                                   |
| 3           | General techniques  | `capture-race`, `liberty-shortage`, `eye-shape`, `connection`, `cutting`                                            |
| 4 (lowest)  | Category labels     | `life-and-death`, `living`, `ko`, `seki`, `shape`, `corner`, `endgame`, `tesuji`, `joseki`, `fuseki`, `dead-shapes` |

**Rationale:** A puzzle tagged `[life-and-death, snapback]` should hint about snapback (the specific solving technique), not life-and-death (the generic category).

### TECHNIQUE_HINTS Dictionary (All 28 Tags)

| Tag                | Hint Text                                    | Reasoning                                                                     |
| ------------------ | -------------------------------------------- | ----------------------------------------------------------------------------- |
| `ladder`           | "Look for a ladder (shicho) pattern"         | "The opponent can only escape in one direction."                              |
| `net`              | "Try surrounding loosely with a net (geta)"  | "Direct capture isn't possible, but escape routes are limited."               |
| `snapback`         | "Consider a snapback sequence"               | "Letting opponent capture leads to recapture."                                |
| `ko`               | "This involves a ko fight"                   | "Identify the ko — then look for local threats to win it."                    |
| `liberty-shortage` | "Look for a liberty shortage (damezumari)"   | "Reducing liberties forces bad shape."                                        |
| `throw-in`         | "A throw-in might be useful"                 | "Sacrificing inside reduces eye space."                                       |
| `sacrifice`        | "Consider sacrificing stones"                | "After the sacrifice, the opponent's shape collapses."                        |
| `connection`       | "Try to connect your groups"                 | "Find the move that links both groups so neither can be cut."                 |
| `cutting`          | "Look for a cutting point"                   | "After separating, can the opponent save both halves?"                        |
| `capture-race`     | "This is a capturing race (semeai)"          | "Compare liberties: the group with fewer will be captured first."             |
| `life-and-death`   | "This is a life-and-death problem"           | "Can the group make two independent eyes, or can you prevent it?"             |
| `escape`           | "Look for an escape route"                   | "Which direction offers the best escape? Consider where friendly stones are." |
| `double-atari`     | "Look for a double atari"                    | "One move threatening two groups."                                            |
| `nakade`           | "Look for a nakade — the vital point inside" | "Playing the vital point prevents two eyes."                                  |
| `clamp`            | "Consider a clamp (hasami-tsuke)"            | "Attach inside to reduce eye space."                                          |
| `vital-point`      | "Find the vital point of the shape"          | "One move determines whether the group lives or dies."                        |
| `connect-and-die`  | "What happens if the opponent connects?"     | "Connecting leads to a larger capture."                                       |
| `under-the-stones` | "Think about playing under the stones"       | "After the capture, the vacated space becomes crucial."                       |
| `eye-shape`        | "Focus on the eye shape"                     | "Can the group make two real eyes, or is one false?"                          |
| `dead-shapes`      | "Recognize the shape — is it already dead?"  | "Some shapes cannot make two eyes regardless of who plays first."             |
| `corner`           | "Corner positions have special properties"   | "Reduced liberties and edge effects change the tactics."                      |
| `shape`            | "Look for the most efficient shape"          | "Good shape maximizes liberties and eye potential."                           |
| `endgame`          | "This is an endgame (yose) problem"          | "Which move gains the most points?"                                           |
| `joseki`           | "This tests joseki knowledge"                | "Find the standard continuation for this corner pattern."                     |
| `fuseki`           | "Consider the whole-board balance"           | "Which area is most urgent to play?"                                          |
| `tesuji`           | "Look for a sharp tactical move"             | "There is a tesuji that changes the outcome."                                 |
| `living`           | "Your group needs to live"                   | "Find the move that guarantees two eyes."                                     |
| `seki`             | "Mutual life may be the best outcome"        | "Neither side can attack without self-destruction."                           |

---

## Liberty Analysis Gating

### The Problem

Liberty counting is the correct mental framework for capture races (semeai), but actively misleading for other techniques:

| Technique        | Liberty hint effect                                          |
| ---------------- | ------------------------------------------------------------ |
| `capture-race`   | **Correct** — counting IS the skill                          |
| `ko`             | **Correct** — ko threat counting is relevant                 |
| `net`            | **Misleading** — nets work by NOT chasing liberties directly |
| `ladder`         | **Misleading** — ladders are about direction, not count      |
| `sacrifice`      | **Misleading** — you intentionally lose liberties            |
| `life-and-death` | **Misleading** — a group with 10 liberties can still be dead |

### Gating Rule

Liberty analysis is **only** included in the reasoning hint (YH2) when the puzzle's primary tag is `capture-race` or `ko`. For all other tags, liberty information is suppressed.

Exception: **Atari detection** generates a standalone technique hint — but only when the correct move **actually captures the atari group**. This prevents misleading hints where an atari exists on the board but is irrelevant to the solution.

### Atari Relevance Gating (2026-02-24)

Before emitting an atari hint, the system verifies:

1. The puzzle has a solution (`game.has_solution` is True)
2. The correct move captures stones (via `Board.play()` simulation)
3. The captured stones include the group in atari

If the atari is **irrelevant** to the solution (e.g., an atari exists elsewhere on the board but the correct move is a shape/connection move), the atari hint is suppressed and logged as a diagnostic.

**Triggering example:** Puzzle `214a85a0be6a3d96` — White stone at N19 (ma) has 1 liberty (atari), but the correct move B[pb] (Q18) is about securing eye shape, not capturing. The old system said "Look for the capturing move" which was misleading.

| Atari Detected    | Correct Move Captures It? | Primary Tag           | Hint Behavior                                                         |
| ----------------- | ------------------------- | --------------------- | --------------------------------------------------------------------- |
| Opponent in atari | **Yes**                   | Not semeai/ko         | YH1: "The opponent is in atari! Look for the capturing move."         |
| Opponent in atari | **No**                    | Not semeai/ko         | Atari hint **suppressed** — falls through to tag/solution-aware hints |
| Player in atari   | N/A                       | Not semeai/ko         | YH1: "Your group is in atari! Escape or make eyes immediately."       |
| Any atari         | N/A                       | `capture-race` / `ko` | Included in YH2 reasoning with liberty counts                         |

---

## Solution Depth Gating

### Design Decision

The coordinate hint (YH3) is **always generated** when a solution exists, ensuring every solvable puzzle has the correct move available as a last-resort hint. Depth gating only controls whether **technique-specific outcome text** is appended — not whether the coordinate itself appears.

### Gating Rule

| Solution Depth | YH3 Behavior                                                                |
| -------------- | --------------------------------------------------------------------------- |
| 1–3            | Coordinate only (e.g., "Play at {!cg}.")                                    |
| 4+             | Coordinate + technique-specific outcome (e.g., "...This begins the chase.") |

### Last-Resort Fallback

If all three hint generators fail (no tags matched, reasoning failed, coordinate failed) but a solution exists, the orchestrator (`enrich_puzzle()`) bypasses the generators and emits a bare coordinate hint directly. This guarantees every solvable puzzle has at least one hint.

---

## Technique-Aware YH3 Templates

Instead of the generic "Play at {!xy}.", YH3 adds what the move ACHIEVES:

| Primary Tag                 | YH3 Template                                                         |
| --------------------------- | -------------------------------------------------------------------- |
| `ladder`                    | "Play at {!xy}. This begins the chase."                              |
| `net`                       | "Play at {!xy}. This creates an inescapable enclosure."              |
| `snapback`                  | "Play at {!xy}. Let them capture — then take back more."             |
| `sacrifice` / `throw-in`    | "Play at {!xy}. This stone will be sacrificed for the greater good." |
| `nakade` / `vital-point`    | "Play at {!xy}. This is the vital point inside."                     |
| `life-and-death` / `living` | "Play at {!xy}. This determines the group's fate."                   |
| `ko`                        | "Play at {!xy}. This starts the ko fight."                           |
| `double-atari`              | "Play at {!xy}. Two groups are threatened at once."                  |
| `connect-and-die`           | "Play at {!xy}. The opponent's connection becomes a trap."           |
| `under-the-stones`          | "Play at {!xy}. After the capture, play in the space below."         |
| `escape`                    | "Play at {!xy}. This is the escape route."                           |
| `connection`                | "Play at {!xy}. This links the groups."                              |
| `cutting`                   | "Play at {!xy}. This separates the opponent's stones."               |
| `capture-race`              | "Play at {!xy}. Win the liberty race."                               |
| Default                     | "Play at {!xy}."                                                     |

---

## Frontend Display Contract

### What the Backend Provides

- 0 to 3 hints in `YH[h1|h2|h3]` format
- Each hint is self-contained text with optional `{!xy}` tokens
- Hints are ordered: technique → reasoning → coordinate

### What the Frontend Does

1. Parse `YH` property → `string[]`
2. Resolve `{!xy}` tokens via `resolveHintTokens()` after board transforms
3. Display hints progressively (one tier per button click)
4. After all text hints are shown, place board marker on correct move
5. **Never pad with generated filler** — if backend provides 2 hints, show 2 text tiers + marker

### Dynamic Tier Count

| Backend hints | Frontend tiers                                       |
| ------------- | ---------------------------------------------------- |
| 3 hints       | T1: hint[0], T2: hint[1], T3: hint[2] + board marker |
| 2 hints       | T1: hint[0], T2: hint[1] + board marker              |
| 1 hint        | T1: hint[0] + board marker                           |
| 0 hints       | T1: board marker only                                |

---

## Error Handling

| Scenario                         | Behavior                                                                                                                                                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| No tags detected                 | Confidence-gated fallback via `solution_tagger`: infer technique from correct move's board effect. Only HIGH+ confidence (ko, connection) produces hints; MEDIUM/LOW (captures, unknown) produces coordinate-only. |
| No tags + no solution            | No hints generated (`EnrichmentResult.hints = []`); frontend shows board marker only                                                                                                                               |
| Tag has no TECHNIQUE_HINTS entry | **Must never happen** — validated by test (all 28 tags covered)                                                                                                                                                    |
| No solution tree                 | YH3 suppressed; YH1 + YH2 still generated if tags available                                                                                                                                                        |
| Board analysis fails             | Liberty analysis skipped gracefully; region hint omitted; technique hint still works                                                                                                                               |
| Irrelevant atari detected        | Atari hint suppressed (move doesn't capture atari group); falls through to tag-based or solution-aware hints                                                                                                       |
| All hint generation fails        | `EnrichmentResult.hints = []`; frontend shows board marker only                                                                                                                                                    |

---

## Testing Strategy

| Layer                            | What to Test                                         | How                                              |
| -------------------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| Unit: TECHNIQUE_HINTS            | All 28 tags → non-None hint                          | Parametrized test over `config/tags.json` keys   |
| Unit: Priority                   | Multi-tag puzzles → highest priority wins            | `["life-and-death", "snapback"]` → snapback      |
| Unit: Liberty gating             | Net puzzle → no liberty text in hints                | Assert "liberties" not in YH1 or YH2 for net tag |
| Unit: Depth gating               | Depth-1 → coordinate only (no outcome text)          | Mock solution tree with 1 child                  |
| Unit: Atari standalone           | Atari + non-semeai + move captures → standalone hint | Assert "in atari" is YH1, not appended           |
| Unit: Atari irrelevant           | Atari exists but move doesn't capture → suppressed   | Assert "atari" NOT in YH1                        |
| Unit: Solution-aware capture     | No tags + move captures → inferred hint              | Assert "life-and-death" in YH1                   |
| Unit: Solution-aware no capture  | No tags + no capture → safe default                  | Assert "life-and-death" (default)                |
| Unit: Solution-aware reasoning   | No tags → reasoning still generated                  | Assert YH2 contains reasoning text               |
| Unit: Solution-aware no solution | No tags + no solution → None                         | Assert hints empty                               |
| Integration: Pipeline            | Full enrichment → valid YH                           | Parse real SGF → enrich → validate YH format     |
| Frontend: Display                | N hints → N tiers (no padding)                       | Update `compute-hint-display.test.ts`            |

---

## Constitution Compliance

| Holy Law                 | How Hints Comply                                                 |
| ------------------------ | ---------------------------------------------------------------- |
| **Zero Runtime Backend** | All hints pre-computed at build time, stored in static SGF files |
| **Local-First**          | Hint usage tracked in localStorage (optional gamification)       |

---

## Historical Context

### Previous Design (pre-2026-02-22)

The original hint system used Region → Technique → Coordinate ordering:

| Tier | Content                                   | Problem                                                                                           |
| ---- | ----------------------------------------- | ------------------------------------------------------------------------------------------------- |
| YH1  | "Focus on the corner." + liberty analysis | Redundant (stones are already visible) and misleading (liberty framing wrong for most techniques) |
| YH2  | Technique name + reasoning                | Only covered 9 of 28 tags; 4 key mismatches caused silent failures                                |
| YH3  | Coordinate + refutation consequence       | Generic "Play at X" with no technique context                                                     |

The frontend padded missing hints with generated filler ("Focus near the board", "Look at the board area") which added no pedagogical value.

### Why It Changed

A net (geta) puzzle from the Fujisawa Tsumego collection showed all three problems at once:

1. YH1 said "Your weakest group has 3 liberties, the opponent's has 2 — who needs to act first?" — framing the puzzle as a capturing race when it was a net problem
2. YH2 was missing because `net` tag worked but `capture-race` didn't match `capture` in the dictionary
3. The student was guided to think about the WRONG concept (liberty counting instead of loose surrounding)

Three expert reviews confirmed the system needed architectural changes, not just template updates.
