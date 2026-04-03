# AI-Solve Calibration Fixtures

**Last Updated:** 2026-03-04

## Purpose

These fixtures are used for calibrating AI-Solve move classification thresholds
(`t_good`, `t_bad`, `t_hotspot`) and verifying that the classifier achieves
acceptable macro-F1 scores across different models and visit counts.

## Source & Provenance

| Directory           | Source                               | Count | Level        |
| ------------------- | ------------------------------------ | ----- | ------------ |
| `cho-elementary/`   | Cho Chikun Elementary Life & Death   | 30    | elementary   |
| `cho-intermediate/` | Cho Chikun Intermediate Life & Death | 30    | intermediate |
| `cho-advanced/`     | Cho Chikun Advanced Life & Death     | 30    | advanced     |
| `ko/`               | Mixed ko puzzle sources              | 5     | various      |

## Held-Out Guarantee

These fixtures are **held-out** from the main pipeline processing:

- They are NOT in `yengo-puzzle-collections/`
- They are NOT imported via any adapter in `external-sources/`
- They exist solely for calibration/testing in `tools/puzzle-enrichment-lab/`

## Stratification

For AI-Solve calibration (DD-9), samples should be stratified by move
classification (TE/BM/neutral), not just difficulty level. The classification
labels are determined by running KataGo analysis and applying the delta-based
thresholds defined in `config/katago-enrichment.json → ai_solve.thresholds`.

## Requirements (Phase 11)

- Minimum 30 samples per classification class (TE, BM, neutral)
- Macro-F1 >= `ai_solve.calibration.target_macro_f1` (default: 0.85)
- Threshold stability verified across visit counts: [500, 1000, 2000]
- No overlap with pipeline collections
