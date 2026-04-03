# Validation Report: Teaching Comments Quality V3

**Last Updated**: 2026-03-12

---

## 1. Test Results

| val_id | command | exit_code | result |
|--------|---------|-----------|--------|
| VAL-1 | Full regression: 10 test files | 0 | **419 passed, 1 skipped** |
| VAL-3 | Remediation 6-file suite | 1 | **212 passed, 2 FAILED (pre-existing)** — 10 new tests all pass |
| VAL-2 | `test_teaching_comments_config.py` | 1 | 12 passed, 2 FAILED (pre-existing alias count mismatches) |

## 2. Must-Hold Constraint Verification

| mh_id | constraint | verified | evidence |
|-------|-----------|----------|----------|
| MH-5 | almost_correct_threshold configurable | ✅ | `WrongMoveComments.almost_correct_threshold = 0.05` in config model + JSON |
| MH-6 | CERTAIN-only vital suppression | ✅ | Guard: `vital_result.move_index > 0 and tag_confidence == "CERTAIN"` |
| MH-7 | Priority-ordered conditions + templates | ✅ | 3 conditions in `CONDITION_PRIORITY` + 4 templates in config |

## 3. Files Modified

| file | changes |
|------|---------|
| `tools/puzzle-enrichment-lab/analyzers/refutation_classifier.py` | 3 new conditions + check functions |
| `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` | Delta gate, vital move suppression, vital_node_index |
| `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | Vital node embedding, almost-correct prefix |
| `tools/puzzle-enrichment-lab/config.py` | `almost_correct_threshold` field |
| `config/teaching-comments.json` | 4 new templates, `almost_correct_threshold` |
| `docs/concepts/teaching-comments.md` | V3 Enhancements section |
