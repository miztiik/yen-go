# Validation Report

**Last Updated**: 2026-03-12

---

## 1. Test Results

| val_id | command | exit_code | result | scope |
|--------|---------|-----------|--------|-------|
| VAL-1 | `pytest tests/test_tsumego_frame.py -q --no-header --tb=short` | 0 | 72 passed | Frame unit tests (was 63, +9 remediation) |
| VAL-2 | `pytest tests/test_sgf_enricher.py tests/test_enrich_single.py -q --no-header --tb=short` | 0 | 72 passed, 1 skipped | Enricher + single enrichment (+1 vital embed) |
| VAL-3 | `pytest tests/test_teaching_comments_config.py -q --no-header --tb=short` | 1 | 12 passed, 2 FAILED (pre-existing) | Config loader tests |
| VAL-4 | Full regression: 10 test files | 0 | **419 passed, 1 skipped** | Full enrichment lab suite |
| VAL-5 | Remediation 6-file suite | 1 | **212 passed, 2 FAILED (pre-existing)** | 19 new tests all pass; only pre-existing alias count mismatches fail |

### Pre-existing Failures (NOT caused by our changes)

| val_id | test | expected | actual | root_cause |
|--------|------|----------|--------|------------|
| VAL-3a | `test_dead_shapes_has_alias_comments` | 7 aliases | 9 aliases | Prior config update added 2 aliases without updating test |
| VAL-3b | `test_tesuji_has_alias_comments` | 6 aliases | 11 aliases | Prior config update added 5 aliases without updating test |

---

## 2. Must-Hold Constraint Verification

| mh_id | constraint | verified | evidence |
|-------|-----------|----------|----------|
| MH-1 | Extract to liberty.py if helpers > 120 lines | ✅ verified | Helper lines = 153 > 120; extracted to `analyzers/liberty.py` |
| MH-2 | Skip counters in FrameResult | ✅ verified | `stones_skipped_illegal`, `stones_skipped_puzzle_protect`, `stones_skipped_eye` fields in FrameResult |
| MH-3 | PL disagreement logging | ✅ verified | `logger.info("Attacker heuristic tie-break (BLACK) disagrees with PL-based inference...")` in `guess_attacker()` |
| MH-4 | Density metric logged | ✅ verified | `fill_density` computed in `build_frame()`, logged via `logger.debug` |
| MH-5 | almost_correct_threshold configurable | ✅ verified | `WrongMoveComments.almost_correct_threshold = 0.05` in config model + JSON |
| MH-6 | Vital suppression CERTAIN-only | ✅ verified | Guard: `if vital_result.move_index > 0 and tag_confidence == "CERTAIN"` |
| MH-7 | New conditions in priority order | ✅ verified | 3 new conditions in `CONDITION_PRIORITY` with corresponding templates |

---

## 3. Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| R1-F | Frame: validate-and-skip improves KataGo input | Guards skip illegal placements without degrading frame quality | ✅ verified | — | ✅ verified |
| R2-F | FrameResult new fields backward-compatible | Existing consumers use positional args; defaults=0 ensure compatibility | ✅ verified | — | ✅ verified |
| R3-F | PL tie-breaker replaces arbitrary Color.BLACK | `guess_attacker()` returns PL-based result on tie; test confirms | ✅ verified | — | ✅ verified |
| R4-F | Existing 63 frame tests pass | 63 passed (was 62; split 1 test into 2) | ✅ verified | — | ✅ verified |
| R1-C | Delta gate prevents "Wrong" on near-correct moves | `almost_threshold` gate in `generate_teaching_comments()` | ✅ verified | — | ✅ verified |
| R2-C | sgf_enricher interface backward-compatible | `vital_comment=""` and `vital_node_index=None` defaults | ✅ verified | — | ✅ verified |
| R3-C | New classifier conditions no-op when data absent | Check functions use `.get()` with False defaults | ✅ verified | — | ✅ verified |
| R4-C | "almost correct" moves get own prefix (not "Wrong.") | `_embed_teaching_comments` checks `text.startswith("Good move")` | ✅ verified | — | ✅ verified |

---

## 4. Files Modified

| file | initiative | changes |
|------|-----------|---------|
| `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` | Init-1 | PL tie-breaker, validation guards, FrameResult extension, inviolate comment, density metric |
| `tools/puzzle-enrichment-lab/analyzers/liberty.py` | Init-1 | NEW — extracted legality helpers per MH-1 |
| `tools/puzzle-enrichment-lab/tests/test_tsumego_frame.py` | Init-1 | Updated for tuple returns, PL tie-breaker tests |
| `tools/puzzle-enrichment-lab/analyzers/refutation_classifier.py` | Init-2 | 3 new conditions + check functions |
| `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` | Init-2 | Delta gate, vital move suppression, vital_node_index |
| `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py` | Init-2 | Vital node embedding, almost-correct prefix |
| `tools/puzzle-enrichment-lab/config.py` | Init-2 | `almost_correct_threshold` field |
| `config/teaching-comments.json` | Init-2 | 4 new templates, `almost_correct_threshold` |
