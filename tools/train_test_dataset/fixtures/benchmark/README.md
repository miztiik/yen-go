# Benchmark Fixtures

49 curated SGF puzzles spanning all difficulty levels and canonical techniques.
Merged from `perf-33/` (34 files) + `perf-50/` (15 files) with governance panel corrections applied.

## Naming Convention

```
L{level_id}_{seq:03d}_{technique}.sgf
```

| Component    | Description                                    | Example          |
|-------------|------------------------------------------------|------------------|
| `L{id}`     | Numeric level ID from `config/puzzle-levels.json` | `L220` = high-dan |
| `{seq:03d}` | Original fixture sequence number (001-049)     | `037`            |
| `{technique}`| Technique/objective slug                       | `ld_nose_tesuji` |

### Level ID Reference

| Level              | ID  | Count |
|-------------------|-----|-------|
| Novice            | 110 | 3     |
| Beginner          | 120 | 2     |
| Elementary        | 130 | 8     |
| Intermediate      | 140 | 14    |
| Upper-Intermediate| 150 | 4     |
| Advanced          | 160 | 5     |
| Low-Dan           | 210 | 4     |
| High-Dan          | 220 | 4     |
| Expert            | 230 | 4     |

## Usage with Calibration

```bash
# Run calibration on all benchmark puzzles
python scripts/run_calibration.py --input-dir tests/fixtures/benchmark

# Run on specific level range using glob
python scripts/run_calibration.py --input-dir tests/fixtures/benchmark --glob "L2*.sgf"

# Filter dan-level puzzles only (L210+)
ls tests/fixtures/benchmark/L2*.sgf
```

Or add `"benchmark"` to `fixture_dirs` in `config/katago-enrichment.json`.

## Provenance

- **#001–#034**: From `perf-33/` (goproblems.com + tsumego-hero.com)
- **#035–#049**: From `perf-50/` (goproblems.com, dan-level gap fills)

### Governance Overrides

Three files have levels corrected per expert governance panel (SGF `YG` properties not patched, only filenames reflect the ruling):

| Seq | Ruling                            | File                          |
|-----|-----------------------------------|-------------------------------|
| 037 | high-dan → advanced (RC-1)        | `L160_037_ld_nose_tesuji.sgf` |
| 043 | upper-intermediate → low-dan (RC-2)| `L210_043_ld_side.sgf`        |
| 044 | upper-intermediate → high-dan (RC-5)| `L220_044_ld_live.sgf`       |

Full mapping: `_name_mapping.json`

## Expert Review

See [expert-review.md](expert-review.md) for the full consolidated expert assessment of all 49 puzzles — per-puzzle notes from 3 domain experts, governance panel rulings, calibration tier rankings, and open gap analysis.

Last Updated: 2026-03-22
