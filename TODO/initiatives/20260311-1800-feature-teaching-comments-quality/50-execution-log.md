# Execution Log: Teaching Comments Quality V3

**Last Updated**: 2026-03-12

---

## Tasks

| task_id | title | status | evidence |
|---------|-------|--------|----------|
| T1 | Config model update | completed | `WrongMoveComments.almost_correct_threshold: float = 0.05` in config.py |
| T2 | Config JSON templates | completed | 4 new templates + `almost_correct_threshold` in teaching-comments.json |
| T3 | Classifier expansion | completed | 3 new conditions + 3 check functions in refutation_classifier.py |
| T4 | Delta gate logic | completed | `almost_threshold` gate in `generate_teaching_comments()` |
| T5 | Vital-move root suppression | completed | Suppress root when `vital_node_index > 0` AND `confidence == CERTAIN` |
| T6 | Return dict extension | completed | `vital_node_index` added to return dict |
| T7 | SGF enricher vital embedding | completed | `_embed_teaching_comments()` walks main line to vital node |
| T8 | Wire in enrich_sgf | completed | `vital_comment` + `vital_node_index` passed from `enrich_sgf()` |
| T9-T14 | Unit tests (original plan) | completed | 419 passed, 0 failed |
| T9a-T14a | Test remediation (10 tests) | completed | 10 new tests: opponent_reduces_liberties x3, self_atari x2, wrong_direction x2, delta_below_threshold, delta_above_threshold, vital_suppresses_root, vital_non_certain_preserves_root, embed_vital_comment_on_deeper_node, almost_correct_template, almost_correct_threshold_from_config. All pass. |
| T15 | Regression | completed | 419 passed, 0 failed (full enrichment lab suite) |

## Deviations

| dev_id | description | resolution |
|--------|-------------|------------|
| D1 | 2 pre-existing test failures in `test_teaching_comments_config.py` | `alias_comments` count mismatches from prior config update — NOT caused by our changes |
