# Instinct Calibration Golden Set

Ground-truth fixture set for validating the instinct classifier, technique tag detectors, and the enrichment pipeline end-to-end.

Last Updated: 2026-03-25

---

## Purpose

This directory contains curated SGF puzzles with expert-verified labels covering instinct classification, technique tags, difficulty, and objective. The golden set enables:

- **Regression testing** — detect accuracy drops in the instinct classifier or technique detectors.
- **Calibration** — measure precision/recall per instinct category and technique tag.
- **Pipeline validation** — verify the full enrichment pipeline produces correct output for known inputs.

## Naming Convention

Files follow the pattern: `{instinct}_{level}_{serial:03d}.sgf`

| Segment   | Values                                                                                          | Example        |
|-----------|-------------------------------------------------------------------------------------------------|----------------|
| instinct  | `push`, `hane`, `cut`, `descent`, `extend`, `null`                                              | `hane`         |
| level     | `novice`, `beginner`, `elementary`, `intermediate`, `upper-intermediate`, `advanced`, `low-dan`, `high-dan`, `expert` | `elementary`   |
| serial    | 3-digit zero-padded sequential number per instinct category                                     | `007`          |

**Example**: `hane_elementary_007.sgf` — the 7th hane puzzle at elementary level.

The `null` instinct category is reserved for puzzles where no first-move instinct dominates (e.g., reading-heavy life-and-death with no clear shape pattern).

## Labels Schema (`labels.json`)

The `labels.json` file in this directory maps each SGF filename to its ground-truth labels.

### Top-level fields

| Field            | Type   | Description                                |
|------------------|--------|--------------------------------------------|
| `schema_version` | string | Schema version (currently `"1.0"`)         |
| `description`    | string | Human-readable description of the dataset  |
| `last_updated`   | string | ISO date of last modification              |
| `puzzles`        | object | Dict keyed by standardized filename        |

### Per-puzzle fields (inside `puzzles`)

| Field              | Type     | Description                                                                 |
|--------------------|----------|-----------------------------------------------------------------------------|
| `instinct_primary` | string   | Primary instinct: `push`, `hane`, `cut`, `descent`, `extend`, or `null`     |
| `instinct_labels`  | string[] | Array of instinct labels (empty `[]` for `null` category)                   |
| `technique_tag`    | string   | Primary technique tag from `config/tags.json`                               |
| `objective`        | string   | Puzzle objective (`life-and-death`, `living`, `ko`, `seki`, etc.)           |
| `human_difficulty` | string   | 9-level difficulty slug (e.g., `elementary`, `intermediate`)                |
| `source`           | string   | Source directory path relative to `external-sources/`                       |
| `original_filename`| string   | Original SGF filename before rename                                         |
| `labeled_by`       | string   | `"auto-filename"`, `"expert"`, or `"human"`                                |
| `notes`            | string   | Optional notes (empty string if none)                                       |

### Example entry

```json
{
  "hane_elementary_001.sgf": {
    "instinct_primary": "hane",
    "instinct_labels": ["hane"],
    "technique_tag": "hane",
    "objective": "life-and-death",
    "human_difficulty": "elementary",
    "source": "manual-imports/sakata-eio-tesuji",
    "original_filename": "problem_042.sgf",
    "labeled_by": "expert",
    "notes": ""
  }
}
```

## Source Material

| Collection                  | Est. Puzzles | Coverage Focus                        |
|-----------------------------|--------------|---------------------------------------|
| Sakata Eio Tesuji           | ~107         | Broad instinct coverage (push, hane, cut, descent, extend) |
| Lee Changho Tesuji          | ~10–15       | Intermediate/advanced instinct variety |
| Cho Chikun Life & Death     | ~5–10        | Null-instinct reading puzzles          |

## Coverage Requirements

| ID   | Requirement                                      | Target  |
|------|--------------------------------------------------|---------|
| AC-5 | Total puzzles with complete labels                | ≥ 120   |
| C-4  | Minimum per instinct category                     | ≥ 10    |
| AC-6 | Minimum per technique tag (top 10 tags)           | ≥ 5     |

## How to Add Puzzles

1. **Search** for candidate puzzles using `tools/puzzle_search.py`.
2. **Copy & rename** selected puzzles into this directory using `tools/puzzle_copy_rename.py`, which applies the naming convention automatically.
3. **Add labels** for each new file in `labels.json` following the per-puzzle schema above.
4. **Verify** coverage requirements are still met after additions.

---

> **See also**:
>
> - [docs/how-to/backend/enrichment-calibration.md](../../../../../../../docs/how-to/backend/enrichment-calibration.md) — Calibration workflow guide
> - [tools/puzzle-enrichment-lab/AGENTS.md](../../../../AGENTS.md) — Module architecture map
