# Golden Calibration Set

Golden set for calibrating instinct classification and entropy-difficulty correlation.

## Requirements
- ≥50 puzzles with manual labels
- Each puzzle has: SGF file, difficulty rating, instinct labels

## Label Schema (labels.json)
```json
{
  "puzzles": [
    {
      "sgf_file": "puzzle_001.sgf",
      "human_difficulty": "intermediate",
      "instinct_labels": ["push"],
      "notes": "Clear push toward edge"
    }
  ]
}
```

## Calibration Metrics
- AC-4: Instinct accuracy ≥ 70% agreement with manual labels
- AC-2: Entropy-difficulty Spearman correlation ≥ 0.3

## Usage
```bash
# Run calibration (requires KataGo)
python -m pytest tests/test_calibration.py -k "golden"
```
