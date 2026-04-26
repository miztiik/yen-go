# How To: Run Enrichment Calibration

> Last Updated: 2026-03-25

Guide for running instinct classifier calibration against the human-labeled golden set, interpreting results, and adding new puzzles.

---

## Prerequisites

- Python 3.11+ with project virtualenv activated
- No KataGo engine required (instinct calibration is purely geometric)

## Run Calibration Tests

```bash
# From project root
cd tools/puzzle-enrichment-lab
python -B -m pytest tests/test_instinct_calibration.py -v --log-cli-level=INFO -p no:cacheprovider
```

The 4 instinct calibration tests (AC-1 through AC-4) are marked `xfail` — they report accuracy baselines without blocking CI:

| Test | AC | Threshold | What It Measures |
|------|-----|-----------|------------------|
| `test_instinct_macro_accuracy` | AC-1 | ≥70% | Overall classifier primary matches human labels |
| `test_per_instinct_accuracy` | AC-2 | ≥60% each | Accuracy per instinct category (cut/push/hane/descent/extend) |
| `test_high_tier_precision` | AC-3 | ≥85% | Precision of HIGH-confidence classifications |
| `test_null_false_positive` | AC-4 | 0% | No false instinct on null-category puzzles |

## Interpreting Results

- **xfail** = test ran, accuracy below threshold (expected during calibration iteration)
- **xpass** = test passed threshold (classifier improved enough — remove xfail marker)
- Check INFO log output for per-instinct breakdowns and mismatch samples

## Calibration Set Location

```
tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration/
├── labels.json         # Multi-dimensional labels (instinct, technique, objective)
├── README.md           # Schema and naming conventions
└── *.sgf               # 134 labeled puzzles
```

## Add New Puzzles

### 1. Find candidates

```bash
python tools/puzzle_search.py --source "yengo-source" --pattern "*.sgf" --board-size 19
```

### 2. Copy and rename

```bash
python tools/puzzle_copy_rename.py --dry-run \
  --input "external-sources/yengo-source/SOME COLLECTION/puzzle.sgf" \
  --target "tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration" \
  --instinct cut --level intermediate --serial 22
```

Remove `--dry-run` to execute.

### 3. Add label to labels.json

Add an entry under `"puzzles"` keyed by the new filename:

```json
"cut_intermediate_022.sgf": {
  "instinct_primary": "cut",
  "instinct_labels": ["cut"],
  "technique_tag": "cutting",
  "objective": "life-and-death",
  "human_difficulty": "intermediate",
  "source": "yengo-source/SOME COLLECTION",
  "original_filename": "puzzle.sgf",
  "labeled_by": "expert",
  "notes": ""
}
```

### 4. Re-run calibration

```bash
python -B -m pytest tests/test_instinct_calibration.py -v --log-cli-level=INFO -p no:cacheprovider
```

## Naming Convention

`{instinct}_{level}_{serial:03d}.sgf`

- **instinct**: push, hane, cut, descent, extend, null
- **level**: novice, beginner, elementary, intermediate, upper-intermediate, advanced, low-dan, high-dan, expert
- **serial**: 3-digit zero-padded, per-instinct sequential

## Coverage Requirements

- AC-5: ≥120 puzzles total
- C-4: ≥10 per instinct category
- AC-6: ≥5 per top-10 technique tag

---

> **See also**:
>
> - [Architecture: Enrichment Pipeline](../../architecture/backend/pipeline.md) — Pipeline design
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — SGF schema
> - [tools/puzzle-enrichment-lab/AGENTS.md](../../../tools/puzzle-enrichment-lab/AGENTS.md) — Module architecture map
> - [Fixture README](../../../tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration/README.md) — Labels schema and naming details
