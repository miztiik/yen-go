# Validation Report — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Executor**: Plan-Executor  
**Validated**: 2026-03-06

---

## Test Results

### Initiative Test Files (100 tests)

| Test File                            | Tests   | Result          | Command                                           |
| ------------------------------------ | ------- | --------------- | ------------------------------------------------- |
| `test_teaching_comments_config.py`   | 12      | ✅ PASS         | `pytest tests/test_teaching_comments_config.py`   |
| `test_teaching_comments.py`          | 27      | ✅ PASS         | `pytest tests/test_teaching_comments.py`          |
| `test_hint_generator.py`             | 38      | ✅ PASS         | `pytest tests/test_hint_generator.py`             |
| `test_teaching_comment_embedding.py` | 18      | ✅ PASS         | `pytest tests/test_teaching_comment_embedding.py` |
| `test_cross_validation_tags.py`      | 5       | ✅ PASS         | `pytest tests/test_cross_validation_tags.py`      |
| **Total**                            | **100** | **✅ ALL PASS** | 1.77s                                             |

### Regression Tests (63 tests)

| Test File              | Tests  | Result          | Command                             |
| ---------------------- | ------ | --------------- | ----------------------------------- |
| `test_sgf_enricher.py` | 43     | ✅ PASS         | `pytest tests/test_sgf_enricher.py` |
| `test_sgf_parser.py`   | 20     | ✅ PASS         | `pytest tests/test_sgf_parser.py`   |
| **Total**              | **63** | **✅ ALL PASS** | 1.21s                               |

### Combined: 163 tests, 0 failures

---

## Config Validation

| Check                                                                  | Result |
| ---------------------------------------------------------------------- | ------ |
| 28 canonical tag entries in `config/teaching-comments.json`            | ✅     |
| All entries have `comment`, `hint_text`, `min_confidence` fields       | ✅     |
| joseki/fuseki use `min_confidence: "CERTAIN"` (governance condition 3) | ✅     |
| dead-shapes has 7 alias sub-comments                                   | ✅     |
| tesuji has 6 alias sub-comments                                        | ✅     |
| All alias keys match valid aliases in `config/tags.json`               | ✅     |
| JSON schema exists at `config/schemas/teaching-comments.schema.json`   | ✅     |

---

## Legacy Removal Verification

| Dict                   | File                   | Status     |
| ---------------------- | ---------------------- | ---------- |
| `TECHNIQUE_COMMENTS`   | `teaching_comments.py` | ✅ Removed |
| `WRONG_MOVE_TEMPLATES` | `teaching_comments.py` | ✅ Removed |
| `TECHNIQUE_HINTS`      | `hint_generator.py`    | ✅ Removed |
| `REASONING_HINTS`      | `hint_generator.py`    | ✅ Removed |

Verification: `grep -r "TECHNIQUE_COMMENTS\|WRONG_MOVE_TEMPLATES\|TECHNIQUE_HINTS\|REASONING_HINTS" analyzers/*.py` → Only 1 docstring reference in `technique_classifier.py:6` (not a code reference).

---

## Governance Condition Compliance

| Condition              | Requirement                             | Evidence                                                                                                                    | Status      |
| ---------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------- |
| 1: AD-3/AD-3b conflict | Consolidate on AD-3 (sgfmill)           | T-13 uses `_embed_teaching_comments()` with sgfmill. T-14 cleaned dead `comments` param. No `_compose_node` wiring.         | ✅ Resolved |
| 2: hint_text boundary  | T-11 uses `hint_text` not `comment`     | `_resolve_hint_text()` reads `entry.hint_text` field. Test confirms: "Snapback (uttegaeshi)" not full teaching comment.     | ✅ Resolved |
| 3: V1 limitation docs  | T-18 includes Known Limitations section | `docs/concepts/teaching-comments.md` has "Known Limitations (V1)" section with first-move-only documentation and rationale. | ✅ Resolved |

---

## Documentation Verification

| Doc                                              | Exists     | Cross-references               | Last Updated |
| ------------------------------------------------ | ---------- | ------------------------------ | ------------ |
| `docs/concepts/teaching-comments.md`             | ✅ Created | hint-architecture.md, hints.md | 2026-03-06   |
| `docs/architecture/backend/hint-architecture.md` | ✅ Updated | teaching-comments.md added     | 2026-03-06   |

---

## Scope Completeness

- **Approved tasks**: 20
- **Executed tasks**: 20
- **Skipped tasks**: 0
- **Scope expansion**: None required
- **Deviations**: 3 (UTF-8 encoding, early return removal, alias key format) — all within approved scope, no behavioral changes beyond what was approved

---

## Validation Verdict

**PASS** — All 163 tests pass. All 3 governance conditions satisfied. All 20 tasks executed. Documentation complete. Legacy code removed. No regressions detected.
