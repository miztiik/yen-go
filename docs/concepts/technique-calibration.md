# Technique Calibration

**Last Updated:** 2026-03-22

## Overview

Technique calibration is the process of validating that the KataGo enrichment pipeline correctly handles each of the 25 active Go technique categories. It answers the question: *"When we feed a known snapback puzzle through enrichment, does the output have the right correct move, the right tags, a reasonable difficulty, proper refutations, and teaching comments?"*

This is distinct from **difficulty calibration** (Cho Chikun collections, `test_calibration.py`), which validates that difficulty scores land in the right range across a reference set. Technique calibration validates per-technique enrichment quality across multiple dimensions.

## The 5 Calibration Dimensions

Each technique is validated against 5 measurable dimensions:

| # | Dimension | What It Checks | Example |
|---|-----------|----------------|---------|
| CD-1 | **Correct move** | Pipeline extracts the right first move (GTP format) | Snapback puzzle → K10 |
| CD-2 | **Technique tags** | Pipeline detects the expected technique tag(s) | Snapback puzzle → `["snapback"]` |
| CD-3 | **Difficulty range** | Assigned level falls within an acceptable band | Elementary snapback → 110–180 |
| CD-4 | **Refutations** | Pipeline generates enough wrong-move refutations | ≥1 refutation for puzzles with branches |
| CD-5 | **Teaching comments** | Teaching text is generated when expected | Currently `False` for all fixtures |

Difficulty ranges are intentionally wide (±2 levels) because KataGo's difficulty estimation varies by model size and visit count.

## The 25 Technique Tags

The system recognizes 28 tags in `config/tags.json`. Three are excluded from calibration because they are not tsumego (life-and-death) puzzles:

**Excluded (non-tsumego):** joseki, fuseki, endgame

The remaining 25 active tags fall into three groups:

### Objectives (what the puzzle asks)

| Tag | Description | Fixture Source |
|-----|-------------|----------------|
| `life-and-death` | Kill or save a group | yengo-source 1042 |
| `living` | Make a group alive (two eyes) | yengo-source 1121 |
| `ko` | Win a ko fight | Lab-built |
| `seki` | Create mutual life | Lab-built |
| `capture-race` | Race to capture first | Lab-built |

### Tesuji (tactical tricks)

| Tag | Description | Fixture Source |
|-----|-------------|----------------|
| `snapback` | Sacrifice, then recapture larger group | Lab-built |
| `double-atari` | Threaten two groups at once | Lab-built |
| `ladder` | Diagonal chase across the board | Lab-built |
| `net` | Loose surrounding (geta) | Lab-built |
| `throw-in` | Sacrifice inside an eye | Lab-built |
| `clamp` | Pinch to restrict liberties | Lab-built |
| `nakade` | Play inside dead shape | Lab-built |
| `connect-and-die` | Force connect, then capture (oiotoshi) | Lab-built |
| `under-the-stones` | Sacrifice, let capture, play into space | Lab-built |
| `liberty-shortage` | Exploit insufficient liberties | Lab-built |
| `vital-point` | The one key point for life/death | Lab-built |
| `sacrifice` | Give up stones for tactical gain | Lab-built |
| `tesuji` | General clever tactical move | yengo-source 968 |

### Shape/Pattern categories

| Tag | Description | Fixture Source |
|-----|-------------|----------------|
| `eye-shape` | Recognize eye formations | Lab-built |
| `dead-shapes` | Identify inherently dead shapes | Lab-built |
| `escape` | Run away with a threatened group | Lab-built |
| `connection` | Connect two groups | yengo-source 106 |
| `cutting` | Cut opponent's groups apart | yengo-source 129 |
| `corner` | Corner-specific positions | Lab-built |
| `shape` | Good shape / efficient placement | yengo-source 108 |

## TechniqueSpec Structure

Each technique's ground truth is defined as a `TechniqueSpec` (TypedDict) with these fields:

**Required fields (5 calibration dimensions):**

| Field | Type | Description |
|-------|------|-------------|
| `fixture` | `str` | SGF filename in `tests/fixtures/` |
| `correct_move_gtp` | `str` | Expected correct first move in GTP format (e.g., "B2") |
| `expected_tags` | `list[str]` | Tags the pipeline should detect (subset check) |
| `min_level_id` | `int` | Lower bound of acceptable difficulty (110=novice, 230=expert) |
| `max_level_id` | `int` | Upper bound of acceptable difficulty |
| `min_refutations` | `int` | Minimum wrong-move refutations expected |
| `expect_teaching_comments` | `bool` | Whether teaching comments should be generated |

**Optional edge-case fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ko_context` | `str` | — | `"none"`, `"direct"`, or `"approach"` |
| `move_order` | `str` | — | `"strict"`, `"flexible"`, or `"miai"` |
| `board_size` | `int` | 19 | Board size (9 or 19) |
| `notes` | `str` | — | Human-readable audit notes |

## How Calibration Works

### Test organization

Technique calibration tests are in `test_technique_calibration.py`:

- **3 unit tests** (no KataGo needed, run in ~1s):
  - `test_all_tags_have_registry_entry` — Every active tag in `config/tags.json` has a registry entry
  - `test_registry_entries_reference_existing_fixtures` — Every referenced fixture file exists on disk
  - `test_no_excluded_tags_in_registry` — Excluded tags aren't accidentally present

- **5 parametrized integration tests** (require live KataGo):
  - `test_correct_move` — CD-1: correct move matches expected GTP coord
  - `test_technique_tags` — CD-2: expected tags are detected (subset check)
  - `test_difficulty_range` — CD-3: difficulty within `[min_level_id, max_level_id]`
  - `test_refutations` — CD-4: refutation count ≥ `min_refutations`
  - `test_teaching_comments` — CD-5: teaching comments present when expected

### Execution flow

```
For each technique (25 entries):
  1. Load fixture SGF from tests/fixtures/
  2. Start KataGo engine (class-scoped, shared across all tests)
  3. Run full enrichment pipeline: enrich_single_puzzle()
  4. Assert on all 5 calibration dimensions
```

The engine uses `quick_only` mode (200 visits) with the best available model (prefers b10, falls back to b6). If KataGo binary or model files are not found, all integration tests auto-skip.

### Running technique calibration

```bash
# Unit tests only (no KataGo needed)
cd tools/puzzle-enrichment-lab
pytest tests/test_technique_calibration.py -m unit -v

# Full calibration (requires KataGo)
pytest tests/test_technique_calibration.py -v --tb=short

# Single technique
pytest tests/test_technique_calibration.py -k "snapback" -v
```

## Calibration vs Other Test Suites

| Suite | Purpose | KataGo? | Puzzles | Time |
|-------|---------|---------|---------|------|
| **Technique calibration** | Per-tag enrichment quality gates | Yes | 25 (one per technique) | ~5–10 min |
| **Golden 5** (`test_golden5.py`) | Core capability smoke test | Yes | 5 canonical puzzles | ~2–3 min |
| **Difficulty calibration** (`test_calibration.py`) | Difficulty score accuracy | Yes | 15 (Cho Chikun collections) | ~15–30 min |
| **AI-Solve calibration** (`test_ai_solve_calibration.py`) | Structural enrichment checks | No | Varies | ~20s |

## Extended Benchmark

Beyond the 25 primary fixtures (one per technique), an **extended benchmark** directory contains difficulty-stratified variants for the 5 most common techniques:

```
tests/fixtures/extended-benchmark/
├── README.md
├── life-and-death_elem_1001.sgf    # Elementary L&D
├── life-and-death_int_102.sgf      # Intermediate L&D
├── life-and-death_adv_1042.sgf     # Advanced L&D
├── ko_elem_1028.sgf                # Elementary Ko
├── ko_int_1022.sgf                 # Intermediate Ko
├── ko_adv_1118.sgf                 # Advanced Ko
├── snapback_elem_1134.sgf          # Elementary Snapback
├── snapback_int_5.sgf              # Intermediate Snapback
├── ladder_elem_189.sgf             # Elementary Ladder
├── ladder_int_220.sgf              # Intermediate Ladder
├── nakade_elem_4774.sgf            # Elementary Nakade
├── nakade_int_588.sgf              # Intermediate Nakade
└── nakade_adv_6421.sgf             # Advanced Nakade
```

Naming convention: `{technique}_{difficulty}_{source_id}.sgf`

All sourced from `external-sources/yengo-source/` collections.

## Fixture Quality Criteria

Calibration fixtures must meet these quality criteria (from the technique calibration initiative charter):

1. **Valid SGF** — Parseable by sgfmill, no structural bugs
2. **Correct solution** — At least one `RIGHT`-marked or `C[Correct]` branch
3. **Proper tagging** — YT property matches the intended technique
4. **Realistic position** — From a real game or established problem collection
5. **Appropriate difficulty** — YG level matches the fixture's actual complexity
6. **Wrong branches** — At least one wrong variation for refutation testing (preferred)
7. **Standard board** — 9x9 or 19x19 (no non-standard sizes)
8. **Clean metadata** — No leftover debug properties or conflicting tags

> **See also:**
>
> - [Concepts: Technique Detection](./technique-detection.md) — How detectors work
> - [Concepts: Quality](./quality.md) — AC quality levels and metrics
> - [Concepts: Tags](./tags.md) — Full tag taxonomy
> - [How-To: KataGo Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — Running the enrichment lab
> - [Reference: KataGo Enrichment Config](../reference/katago-enrichment-config.md) — Configuration reference
