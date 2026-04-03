# Enrichment Architecture

> **See also**:
>
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — Property reference
> - [Concepts: Hints](../../concepts/hints.md) — Hint system
> - [Concepts: Quality](../../concepts/quality.md) — YQ/YX metrics
> - [Architecture: Pipeline](./pipeline.md) — Pipeline stages
> - [Architecture: Tactical Analyzer](./tactical-analyzer.md) — Board-level pattern detection

**Last Updated**: 2026-03-24

**Implementation**: [`core/enrichment/`](../../../backend/puzzle_manager/core/enrichment/)

Design for the ANALYZE stage enrichment process.

---

## Overview

The enricher transforms raw puzzles into fully-annotated puzzles with:

- **Difficulty level** (YG) — 9-level system
- **Tags** (YT) — Technique classification
- **Hints** (YH) — Progressive hints
- **Quality** (YQ) — Curation metrics
- **Complexity** (YX) — Objective difficulty

---

## Enrichment Pipeline

```text
Raw Puzzle                    Enriched Puzzle
    │                              │
    ├── Level Classification ──────┤ YG[intermediate]
    ├── Tag Detection ─────────────┤ YT[ladder,snapback]
    ├── Collection Assignment ─────┤ YL[cho-chikun-elementary]
    ├── Hint Generation ───────────┤ YH[hint1|hint2|hint3]
    ├── Quality Metrics ───────────┤ YQ[q:4;rc:2;hc:1;ac:0]
    └── Complexity Metrics ────────┤ YX[d:5;r:13;s:24;u:1;w:3;a:0;b:0;t:1]
```

---

## Property Ownership

The enricher is **final authority** for all YenGo properties:

| Property        | Adapter Provides | Enricher Action                                                               |
| --------------- | ---------------- | ----------------------------------------------------------------------------- |
| **GN**          | Optional         | Overwrites to `YENGO-{hash}`                                                  |
| **YV**          | No               | Sets to current version                                                   |
| **YG**          | Optional hint    | Collection `level_hint` wins → preserves source if valid → heuristic fallback |
| **YT**          | Optional initial | **Preserves** source tags; merges with high-precision detection               |
| **YL**          | No               | Assigns from aliases                                                          |
| **YH**          | No               | Generates from analysis                                                       |
| **YQ**          | No               | Computes from tree                                                            |
| **YX**          | No               | Computes from tree                                                            |
| **SO**          | Optional         | **Removes**                                                                   |
| **C[]** (root)  | Optional         | **Cleans HTML/CJK, preserves** (configurable)                                 |
| **C[]** (moves) | Optional         | **Standardizes** (Correct/Wrong prefix, CJK stripped)                         |

### Key Principles

1. Adapter data is used as **hints** but enricher validates
2. Provenance (SO) tracked in pipeline state, not SGF
3. Root comments are cleaned (HTML/CJK stripped) and preserved by default; move comments standardized with Correct/Wrong prefix
4. Source-provided YG levels are preserved if valid; classifier runs only when missing

---

## Level Classification

**Implementation**: [`core/classifier.py`](../../../backend/puzzle_manager/core/classifier.py)

### Algorithm

The analyzer uses a **3-tier resolution** policy (v5.0):

1. **Collection override** — If the puzzle belongs to a collection with a `level_hint` in `config/collections.json`, use that level. When multiple hints conflict, lowest (easiest) level wins.
2. **Source preservation** — If no collection hint but the source provides a valid `YG` slug (from `config/puzzle-levels.json`), **preserve it**
3. **Heuristic classifier** — If no collection hint and no valid source YG, run the structural heuristic
4. **Fallback** — If classification fails (practically unreachable), use `elementary` (level 3)

The collection override is applied in the analyze stage _after_ collection assignment (YL), ensuring the puzzle's collection membership is known before level resolution. See [Concepts: Collections — Level Hint](../../concepts/collections.md#level-hint-collection-based-level-override) for the full design rationale.

### Heuristic Classifier

The classifier computes a composite score from 4 features:

| Feature                 | Score Range | Details                                            |
| ----------------------- | ----------- | -------------------------------------------------- |
| Depth (main line)       | 1–7         | depth≤1→1, depth≤2→2, ..., depth>10→7              |
| Variations (tree count) | 0–3         | var≤2→0, var≤5→1, var≤10→2, var>10→3               |
| Stones                  | 0–3         | stones≤10→0, stones≤20→1, stones≤40→2, stones>40→3 |
| Board size              | -1 to +1    | 9×9→-1, 13×13→0, 19×19→+1                          |

### Score → Level Mapping

| Score | Level                  |
| ----- | ---------------------- |
| ≤2    | novice (1)             |
| 3–4   | beginner (2)           |
| 5–6   | elementary (3)         |
| 7–8   | intermediate (4)       |
| 9–10  | upper-intermediate (5) |
| 11–12 | advanced (6)           |
| 13–14 | low-dan (7)            |
| 15–16 | high-dan (8)           |
| 17+   | expert (9)             |

---

## Tag Detection

**Implementation**: [`core/tagger.py`](../../../backend/puzzle_manager/core/tagger.py)

### Pattern Recognition

Tags are detected by analyzing:

1. **Stone patterns** — Dead shapes, eye shapes
2. **Move sequences** — Ladder, ko, snapback
3. **Solution tree** — Variations, refutations
4. **Source metadata** — Tags from original

Detection functions are registered in a detector map. Each detector analyzes the puzzle and returns whether the tag applies. Results are sorted and deduplicated.

---

## Collection Assignment

**Implementation**: [`core/collection_assigner.py`](../../../backend/puzzle_manager/core/collection_assigner.py)

Collections are curated groups of puzzles (e.g., "Cho Chikun Elementary", "Gokyo Shumyo"). Assignment happens automatically by matching source metadata against aliases from `config/collections.json`.

Algorithm:

1. Scan puzzle source path against alias map
2. Merge with existing YL[] (if any)
3. Sort and deduplicate

---

## Hint Generation

**Implementation**: [`core/enrichment/hints.py`](../../../backend/puzzle_manager/core/enrichment/hints.py)

### Design Philosophy

Hints follow a 1P professional Go player's pedagogical approach:

1. **Technique** — Name the concept (what to try)
2. **Reasoning** — Explain why it works (wrong approach warning)
3. **Coordinate** — Specific answer with technique outcome (last resort)

Hints are pipe-delimited in YH property (max 3). See [Concepts: Hints](../../concepts/hints.md) for format details.

---

## Quality Metrics (YQ)

**Implementation**: [`core/quality.py`](../../../backend/puzzle_manager/core/quality.py)
**Config**: `config/puzzle-quality.json` (single source of truth, fail-fast loading — no hardcoded fallbacks)

### Quality Components

| Field | Description         | Computation                                               |
| ----- | ------------------- | --------------------------------------------------------- |
| `q`   | Quality level (1-5) | Weighted sum of factors                                   |
| `rc`  | Refutation count    | Count wrong branches                                      |
| `hc`  | Comment level       | 0=none, 1=correctness markers, 2=teaching text            |
| `ac`  | Analysis complete   | 0=untouched, 1=enriched, 2=ai_solved, 3=verified         |

Quality score factors: depth, refutation count, teaching comments, source quality. Thresholds for each quality level are defined in `config/puzzle-quality.json` under the `levels` key.

---

## Complexity Metrics (YX)

**Implementation**: [`core/complexity.py`](../../../backend/puzzle_manager/core/complexity.py)

### Complexity Components

| Field | Description          | Computation                                               |
| ----- | -------------------- | --------------------------------------------------------- |
| `d`   | Depth                | Moves in main line                                        |
| `r`   | Reading              | Total tree nodes                                          |
| `s`   | Stones               | Stone count on board                                      |
| `u`   | Unique               | 1 if single correct first move                            |
| `w`   | Wrong candidates     | Count of plausible wrong first-move candidates (optional) |
| `a`   | Avg refutation depth | Mean depth of wrong-move branches (optional)              |

---

## Content-Type Classification

**Configuration**: [`config/content-types.json`](../../../config/content-types.json)  
**Schema**: [`config/schemas/content-types.schema.json`](../../../config/schemas/content-types.schema.json)

Content type classifies puzzles into three categories stored in the `content_type` column of DB-1.
All parameters — type IDs, thresholds, teaching patterns — are loaded from `config/content-types.json` (single source of truth, no hardcoded fallbacks).

| Value | Slug | Description | Signal |
|-------|------|-------------|--------|
| 1 | `curated` | Human-reviewed, teaching-quality puzzles | High quality + teaching comments |
| 2 | `practice` | Standard practice puzzles (default) | Most imported puzzles |
| 3 | `training` | Auto-generated or low-quality training material | Low quality or minimal structure |

### Classification Decision Tree

Evaluated in order by `classify_content_type()` in `content_classifier.py`:

1. **Trivial capture** → training (opponent group at 1 liberty, first move captures)
2. **No solution tree** → training
3. **Teaching root comment** → training (regex patterns from `teaching_patterns` in config)
4. **Single-move tutorial** → training (depth ≤ `max_depth` AND hc ≥ `min_comment_level` from `training_thresholds`)
5. **Curated check** → curated (quality ≥ `min_quality` AND refutations ≥ `min_refutations` AND optionally unique first move, from `curated_thresholds`)
6. **Default** → practice

### Config-Driven Architecture

The classifier uses **fail-fast loading** — if `config/content-types.json` is missing or corrupt, a `FileNotFoundError` is raised immediately. Type IDs are loaded from the `types` object in config via `get_content_type_id(name)`, not hardcoded.

### Pipeline Wiring

Content-type classification is implemented in the **analyze** stage via `classify_content_type()`. The result is stored in the `YM` pipeline metadata property as `ct` (e.g., `YM[{"t":"...","ct":1}]`). During **publish**, the `ct` value is read from `YM` and written to DB-1's `content_type` column. If no `ct` is present in `YM`, the default is `practice` (loaded from config).

> **See also**:
>
> - [Config: content-types.json](../../../config/content-types.json) — Classification thresholds
> - [Concepts: Quality](../../concepts/quality.md) — YQ metrics that feed classification

---

## Pipeline Metadata (YM)

**Implementation**: [`core/trace_utils.py`](../../../backend/puzzle_manager/core/trace_utils.py)

YM stores pipeline metadata as embedded JSON:

```sgf
YM[{"t":"a1b2c3d4e5f67890","i":"20260220-abc12345"}]
```

| Field | Description                  | Example             | Publish behavior        |
| ----- | ---------------------------- | ------------------- | ----------------------- |
| `t`   | Trace ID (16-hex)            | `a1b2c3d4e5f67890`  | Kept                    |
| `i`   | Run ID                       | `20260220-abc12345` | Kept                    |
| `f`   | Original filename (optional) | `puzzle001.sgf`     | **Stripped at publish** |

**Transient field (`f`)**: Set at ingest for cross-stage correlation. At publish, `f` is extracted and recorded in the publish log, then **stripped from the published SGF**. This avoids embedding source provenance in published files (same rationale as `SO` removal).

**Transient field (`s`)**: During pipeline processing, `context.source_id` is available as `s`, but it is **NOT embedded** in the final YM JSON. Source adapter ID flows via CLI `--source` flag and is recorded in the publish log.

---

## Removed Properties (v13)

### SO (Source) Property

Source tracking moved to pipeline state. Not included in published SGF. Provenance is recorded in the publish log instead.

### YS (Source Adapter ID) and YI (Run ID)

These were separate properties in v9-v12. Both are now consolidated into YM.i (run ID). Source adapter ID is tracked via CLI `--source` flag and publish log, not embedded in SGF.

---

## Comment Processing

**Implementation**: [`core/text_cleaner.py`](../../../backend/puzzle_manager/core/text_cleaner.py)

### Root C[] Comments

Root comments are **cleaned and preserved** by default (configurable via `EnrichmentConfig.preserve_root_comment`).

**Cleaning pipeline**:

1. **Strip HTML** — Remove `<h1>`, `<b>`, etc. tags
2. **Decode HTML entities** — `&amp;` → `&`, `&gt;` → `>`
3. **Normalize whitespace** — Collapse multiple spaces to single space

### Move C[] Comments

Move comments are **standardized** via `standardize_move_comment()` to start with a `Correct` or `Wrong` prefix. CJK text is stripped, HTML is cleaned, and pedagogical suffixes are preserved after an em-dash separator. Correctness inference uses `clean_for_correctness()` to detect signal prefixes before standardization.

---

## Configuration

Enrichment uses these config files:

| File                                        | Purpose               |
| ------------------------------------------- | --------------------- |
| `config/puzzle-levels.json`                 | Level definitions     |
| `config/tags.json`                          | Tag taxonomy, aliases |
| `config/source-quality.json`                | Source credibility    |
| `config/schemas/sgf-properties.schema.json` | Property validation   |

Never hardcode values — always read from config.
