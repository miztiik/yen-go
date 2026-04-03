# Validation Report — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

---

## Validation Results

| val_id | check | command | result | status |
|--------|-------|---------|--------|--------|
| VAL-1 | Tool tests pass | `pytest tools/core/tests/test_puzzle_search.py test_puzzle_copy_rename.py` | 24 passed | ✅ |
| VAL-2 | Fixture files ≥120 | `ls instinct-calibration/*.sgf \| wc -l` | 134 | ✅ |
| VAL-3 | Labels complete ≥120 | `jq '.puzzles \| length' labels.json` | 134 | ✅ |
| VAL-4 | Calibration tests executable | `pytest test_instinct_calibration.py` | 2 passed, 2 skipped, 4 xfailed (exit 0) | ✅ |
| VAL-5 | Enrichment regression | `pytest tools/puzzle-enrichment-lab/tests/ (non-engine subset)` | 293 passed, 2 skipped, 4 xfailed (exit 0) | ✅ |
| VAL-6 | Backend unit regression | `pytest backend/ -m unit` | 1580 passed, 824 deselected (exit 0) | ✅ |

## Calibration Results (Baseline)

| cal_id | test | AC | threshold | actual | status |
|--------|------|----|-----------|--------|--------|
| CAL-1 | test_instinct_macro_accuracy | AC-1 | ≥70% | 15.9% (11/69) | xfail (expected per R-4) |
| CAL-2 | test_per_instinct_accuracy | AC-2 | ≥60% each | cut:9.5%, descent:0%, extend:0%, hane:53.8%, push:20% | xfail (expected per R-4) |
| CAL-3 | test_high_tier_precision | AC-3 | ≥85% | 18.1% (17/94) | xfail (expected per R-4) |
| CAL-4 | test_null_false_positive | AC-4 | 0% | 21 false positives | xfail (expected per R-4) |

## Coverage Counts

| cov_id | metric | threshold | actual | status |
|--------|--------|-----------|--------|--------|
| COV-1 | Total puzzles (AC-5) | ≥120 | 134 | ✅ |
| COV-2 | Per-instinct min (C-4) | ≥10 | cut:21, descent:15, extend:10, hane:13, null:65, push:10 | ✅ |
| COV-3 | Technique tag coverage (AC-6) | ≥5 per top-10 | Verified in T14 | ✅ |

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|----------------|-----------------|--------|----------------|--------|
| RI-1 | tools.core.sgf_parser unchanged | 24 tool tests pass, 293 enrichment tests pass | Match | — | ✅ verified |
| RI-2 | tools.core.paths unchanged | Path resolution works in tool tests | Match | — | ✅ verified |
| RI-3 | instinct_classifier API unchanged | Calibration tests call classify_instinct() successfully | Match | — | ✅ verified |
| RI-4 | ascii_board API unchanged | Used during labeling phase (no test breakage) | Match | — | ✅ verified |
| RI-5 | test_instinct_calibration.py extended (not replaced) | Existing golden_labels fixture untouched; new instinct_labels fixture added | Match | — | ✅ verified |
| RI-6 | InstinctConfig.enabled unchanged | Not modified (NG-1) | Match | Separate initiative | ✅ verified |
| RI-7 | golden-calibration/ untouched | Directory unchanged | Match | — | ✅ verified |
| RI-8 | benchmark/ fixtures unaffected | No test breakage | Match | — | ✅ verified |
| RI-9 | external-sources/ read-only | No modifications to source directories | Match | — | ✅ verified |
| RI-10 | config/tags.json unchanged | Tags verified in coverage check, no modifications | Match | — | ✅ verified |

## Notes

- Classifier accuracy (15.9%) is well below the 70% threshold per Risk R-4 and Finding F-5. This is expected — the golden set reveals that the geometric classifier needs significant improvement. The initiative succeeds by producing the verified golden set, not by achieving the accuracy threshold.
- All 4 AC tests (AC-1 through AC-4) are marked `xfail(strict=False)` so they don't block CI while preserving the threshold assertions for when the classifier improves.
- When classifier accuracy crosses thresholds, `xfail` markers should be removed.
