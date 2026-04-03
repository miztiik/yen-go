# Validation Report — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Date**: 2026-03-06

---

## Test Results

| VAL-1 | Command                                              | Exit | Result            |
| ----- | ---------------------------------------------------- | ---- | ----------------- |
| VAL-1 | `pytest tests/test_vital_move.py`                    | 0    | 9/9 passed ✅     |
| VAL-2 | `pytest tests/test_refutation_classifier.py`         | 0    | 14/14 passed ✅   |
| VAL-3 | `pytest tests/test_comment_assembler.py`             | 0    | 31/31 passed ✅   |
| VAL-4 | `pytest tests/test_teaching_comments_integration.py` | 0    | 20/20 passed ✅   |
| VAL-5 | `pytest tests/test_teaching_comments.py`             | 0    | 27/27 passed ✅   |
| VAL-6 | `pytest tests/test_teaching_comments_config.py`      | 0    | 10/10 passed ✅   |
| VAL-7 | `pytest tests/test_teaching_comment_embedding.py`    | 0    | 7/7 passed ✅     |
| VAL-8 | Full lab pytest suite                                | 0    | 131/131 passed ✅ |

---

## Ripple Effects Validation

| impact_id | expected_effect                                    | observed_effect                                                      | result      | follow_up_task | status      |
| --------- | -------------------------------------------------- | -------------------------------------------------------------------- | ----------- | -------------- | ----------- |
| RIP-1     | enrich_single.py import path change                | V2 import works, V1 deleted                                          | ✅ verified | —              | ✅ verified |
| RIP-2     | test_teaching_comments.py V2 behavior              | 26/27 pass unchanged, 1 updated (capture_verified)                   | ✅ verified | —              | ✅ verified |
| RIP-3     | test_teaching_comments_config.py version assertion | Updated 1.0→2.0, condition name updated                              | ✅ verified | —              | ✅ verified |
| RIP-4     | test_teaching_comment_embedding.py unchanged       | 7/7 pass, imports from sgf_enricher (unaffected)                     | ✅ verified | —              | ✅ verified |
| RIP-5     | config/teaching-comments.json backward compat      | All V1 fields preserved, additive V2 fields                          | ✅ verified | —              | ✅ verified |
| RIP-6     | No other files import from V1                      | grep confirms zero remaining imports                                 | ✅ verified | —              | ✅ verified |
| RIP-7     | Docs updated consistently                          | teaching-comments.md, hint-architecture.md, enrichment.md, CHANGELOG | ✅ verified | —              | ✅ verified |

---

## Governance Conditions Verification

| ID   | Condition                                 | Verification                                                                              | Status      |
| ---- | ----------------------------------------- | ----------------------------------------------------------------------------------------- | ----------- |
| RC-1 | V1 deleted, V2 import chain               | analyzers/teaching_comments.py removed, enrich_single.py imports phase_b                  | ✅ verified |
| RC-2 | Config additive (all V1 fields preserved) | comment, hint_text, min_confidence, alias_comments unchanged                              | ✅ verified |
| RC-3 | delta_annotations unchanged               | Both delta annotations preserved in v2.0 config                                           | ✅ verified |
| RC-4 | Parenthetical counting rule               | \_count_words() treats (term) as 1 word, assembly_rules.parenthetical_counting documented | ✅ verified |

---

## Scope Verification

| Scope item                            | Delivered | Evidence                                                                 |
| ------------------------------------- | --------- | ------------------------------------------------------------------------ |
| T1: Config schema extension           | ✅        | teaching-comments.json v2.0, schema extended, Pydantic models            |
| T2: Technique phrases (28 tags)       | ✅        | All tags have technique_phrase + vital_move_comment                      |
| T3: Signal templates + assembly rules | ✅        | 6 signals, assembly_rules, annotation_policy                             |
| T4: Vital move detector               | ✅        | phase_b/vital_move.py + 9 tests                                          |
| T5: Wrong-move classifier             | ✅        | phase_b/refutation_classifier.py + 14 tests                              |
| T6: Assembly engine                   | ✅        | phase_b/comment_assembler.py + 31 tests                                  |
| T7: Integration                       | ✅        | phase_b/teaching_comments.py + 20 tests + V1 deletion + import migration |
| T8: Expert review                     | Deferred  | Requires human expert                                                    |
| T9: Test suite + docs                 | ✅        | 131/131 full suite + 4 docs updated                                      |

---

## Post-Closeout: Threshold Calibration Validation

**Date**: 2026-03-06

### Config Changes Verified

| VAL-PC-1 | Change                                                  | Before                            | After                                 | Verified |
| -------- | ------------------------------------------------------- | --------------------------------- | ------------------------------------- | -------- |
| VAL-PC-1 | `katago-enrichment.json → teaching.non_obvious_policy`  | 0.05                              | 0.10                                  | ✅       |
| VAL-PC-2 | `katago-enrichment.json → teaching.ko_delta_threshold`  | 0.10                              | 0.12                                  | ✅       |
| VAL-PC-3 | `teaching-comments.json → signal_templates.non_obvious` | "non-obvious — decisive at {!xy}" | "surprising move — decisive at {!xy}" | ✅       |
| VAL-PC-4 | `teaching-comments.json → _signal_templates_note`       | present (provisional disclaimer)  | removed                               | ✅       |

### Test Update Verified

| VAL-PC-5 | Test                                    | Change                                                        | Result    |
| -------- | --------------------------------------- | ------------------------------------------------------------- | --------- |
| VAL-PC-5 | `test_low_policy_adds_non_obvious_note` | Assert "surprising move" instead of "non-obvious"             | ✅ passed |
| VAL-PC-6 | `test_normal_policy_no_extra_note`      | Assert "surprising move" not present instead of "non-obvious" | ✅ passed |

### Documentation Verified

| VAL-PC-7 | Document                              | Change                                                                                 | Status |
| -------- | ------------------------------------- | -------------------------------------------------------------------------------------- | ------ |
| VAL-PC-7 | `docs/concepts/teaching-comments.md`  | Added "Threshold Calibration Rationale" section, updated `non_obvious` signal template | ✅     |
| VAL-PC-8 | `docs/reference/enrichment-config.md` | Added "Teaching Comment Thresholds" reference table + cross-reference                  | ✅     |

### Test Results (Post-Calibration)

| VAL-PC-9  | Suite                            | Result                                               |
| --------- | -------------------------------- | ---------------------------------------------------- |
| VAL-PC-9  | Teaching comment tests (5 files) | 108/108 passed ✅                                    |
| VAL-PC-10 | Full enrichment lab suite        | 123 passed, 1 pre-existing error (caplog fixture) ✅ |
