# 008 — Expert Panel: Test Architecture for Two-Population Split

**Date:** 2026-03-02  
**Panel:** Principal Systems Architect + Staff Engineer  
**Scope:** S.4.2 — Evaluate the two-population testing approach for KataGo puzzle enrichment

---

## 1. Two-Population Split Structure

### Current Implementation

```
tests/fixtures/
├── calibration/              ← Threshold tuning (seed=42, 30/collection)
│   ├── cho-elementary/       30 SGFs
│   ├── cho-intermediate/     30 SGFs
│   └── cho-advanced/         30 SGFs
├── evaluation/               ← Accuracy measurement (seed=99, 10/collection)
│   ├── cho-elementary/       10 SGFs
│   ├── cho-intermediate/     10 SGFs
│   └── cho-advanced/         10 SGFs
└── perf-33/                  ← Smoke tests (synthetic, covers all 9 levels)
```

### Assessment

| Criterion               | Status     | Notes                                                                           |
| ----------------------- | ---------- | ------------------------------------------------------------------------------- |
| Disjoint populations    | ✅ PASS    | `_sample_sgfs_excluding()` with different seed guarantees no overlap            |
| Deterministic sampling  | ✅ PASS    | Fixed seeds (42/99) reproduce identical sets                                    |
| Minimum evaluation size | ✅ PASS    | 30 fixtures ≥ minimum                                                           |
| Level coverage          | ⚠️ PARTIAL | 3 collection levels (elementary/intermediate/advanced), not full 9-level spread |
| Traceability            | ✅ PASS    | All fixtures have C[] root comments                                             |

### Recommendation: Level Coverage Gap

The 3-level coverage (elementary, intermediate, advanced) is adequate for the Cho Chikun validation use case but insufficient for full 9-level difficulty regression.

**Actionable enhancement (post-Phase S):**

- Add evaluation fixtures from other collections:
  - Kano Yoshinori 239 Graded Problems → novice/beginner coverage
  - Go Seigen Tsumego Collection → low-dan/high-dan coverage
  - Gokyo Shumyo → expert coverage
- Target: ≥3 fixtures per level, 9 levels = 27+ additional fixtures
- Priority: P2 (after Phase B). Current 3-level coverage validates the core formula.

---

## 2. What Makes a Good Evaluation Fixture

### Properties

1. **Unseen by tuner** — Must NEVER be used during threshold calibration. The exclusive seed approach (calibration=42, evaluation=99) plus filename exclusion guarantees this.

2. **Same distribution** — From the same source collections as calibration. This avoids distribution shift (e.g., testing on modern AI puzzles when calibration used classical Japanese puzzles).

3. **Known ground truth** — Each fixture has a human-assigned difficulty label (C[Elementary], etc.) from a professional Go player (Cho Chikun 9-dan). This provides the gold standard.

4. **Valid SGF structure** — Must have correct first move, at least one wrong variation with refutation, proper stone placement. Malformed puzzles test error handling, not accuracy.

5. **Representative board sizes** — Mix of 9×9, 13×13, 19×19 boards. Current Cho collection is 19×19 with small local problems (typical tsumego).

### Anti-patterns (Fixtures to Avoid)

| Anti-pattern                           | Why it's bad                           | Mitigation                               |
| -------------------------------------- | -------------------------------------- | ---------------------------------------- |
| Rich SGF with pre-existing YG/YT       | Bypasses AI classification             | Evaluation fixtures use raw SGFs (no YG) |
| Trivially solved (1-move, >90% policy) | Doesn't test difficulty discrimination | Include diverse complexity               |
| Edge-only or center-only               | Bias toward one cropping geometry      | Sample randomly from collection          |
| Duplicate content (same position)      | Inflates accuracy metrics              | Dedup by content hash                    |

---

## 3. Metrics Framework

### Primary Metrics

| Metric                  | Formula                  | Target                         | Notes                               |
| ----------------------- | ------------------------ | ------------------------------ | ----------------------------------- | --- | ------------------------- |
| **Level accuracy**      | `correct_level / total`  | ≥60% exact match               | Within ±1 level is "acceptable"     |
| **Acceptance rate**     | `accepted / total`       | ≥90%                           | Rejected puzzles need investigation |
| **Level ±1 accuracy**   | `within_1_level / total` | ≥85%                           | More forgiving accuracy metric      |
| **Mean absolute error** | `mean(                   | predicted_id - ground_truth_id | )`                                  | ≤15 | Using level IDs (110-230) |

### Per-Level Metrics

For each of the 9 difficulty levels:

- **True positive rate**: Puzzles correctly classified at this level
- **Confusion matrix**: Where misclassified puzzles actually land
- **Score distribution**: Mean/std of raw difficulty scores per ground-truth level

### Difficulty Drift Detection

```python
# Run periodically to detect threshold drift:
# If mean evaluation score shifts >5 points from baseline, investigate.
baseline_mean_score = {
    "elementary": 52.0,  # S.3 formula expected range
    "intermediate": 65.0,
    "advanced": 82.0,
}
```

### False Positive / Negative Rates

| Type             | Definition                             | Acceptable Rate |
| ---------------- | -------------------------------------- | --------------- |
| **False easy**   | Expert puzzle rated as novice/beginner | <5%             |
| **False hard**   | Novice puzzle rated as dan-level       | <5%             |
| **False reject** | Valid puzzle rejected by pipeline      | <10%            |
| **False accept** | Invalid puzzle accepted                | <1%             |

---

## 4. Rich SGF Problem

### Issue

Some existing unit tests use "rich SGFs" — fixtures with pre-populated `YT[...]`, `YG[...]`, `YR[...]` properties. These bypass the AI analysis paths:

- Tag detection skipped (tags already present)
- Difficulty classification skipped (level already assigned)
- Refutation generation skipped (wrong moves already in tree)

### Impact on Two-Population Testing

Rich SGFs are appropriate for:

- ✅ Unit testing tag serialization
- ✅ Testing SGF parsing/publishing
- ✅ Verifying corner detection, ko classification

Rich SGFs are NOT appropriate for:

- ❌ Measuring AI classification accuracy
- ❌ Testing difficulty estimation
- ❌ Validating refutation generation

### Recommendation

| Fixture Type           | Population               | Purpose                                  |
| ---------------------- | ------------------------ | ---------------------------------------- |
| Rich SGFs (with YG/YT) | `tests/fixtures/` (root) | Unit tests for parsing, serialization    |
| Raw SGFs (no YG/YT)    | `calibration/`           | Threshold tuning (full AI pipeline)      |
| Raw SGFs (no YG/YT)    | `evaluation/`            | Accuracy measurement (full AI pipeline)  |
| Synthetic SGFs         | `perf-33/`               | Smoke tests, level coverage verification |

**Rule:** No test in `test_fixture_integrity.py` should use rich SGFs for accuracy measurement.

---

## 5. Test Isolation

### Current Structure

```
tests/
├── test_fixture_integrity.py    ← S.4 population validation
├── test_difficulty.py           ← Difficulty formula unit tests
├── test_enrichment_config.py    ← Config loading tests
├── test_query_builder.py        ← KataGo query tests
├── test_tight_board_crop.py     ← S.1 cropping tests
└── test_lab_mode_config.py      ← S.2 lab mode tests
```

### Recommendation: Separate Evaluation Module

```
tests/
├── evaluation/                  ← NEW: Isolated evaluation tests
│   ├── __init__.py
│   ├── test_accuracy.py         ← Per-level accuracy (requires pipeline output)
│   ├── test_acceptance_rate.py  ← Pipeline acceptance rate
│   └── conftest.py              ← Evaluation-only fixtures and helpers
├── test_fixture_integrity.py    ← Population validation (keep at top level)
└── ...
```

**Why separate module?**

1. Evaluation tests have different dependencies (require pre-computed enrichment output, not just unit-test mocks)
2. Prevents accidental import of calibration data in evaluation tests
3. Can be excluded from quick test runs (`-m "not evaluation"`)
4. Clear ownership boundary for test maintenance

**Implementation priority:** P2 (post-Phase S). Current `test_fixture_integrity.py` validates the split; actual evaluation tests require pipeline output from running KataGo on evaluation fixtures.

---

## Summary

| Decision             | Recommendation                                                |
| -------------------- | ------------------------------------------------------------- |
| Two-population split | ✅ Approved — disjoint populations with deterministic seeds   |
| Level coverage       | ⚠️ Adequate for Phase S, extend to 9 levels in Phase B        |
| Metrics              | Implement accuracy/acceptance/drift checks after pipeline run |
| Rich SGFs            | Keep for unit tests only; exclude from evaluation population  |
| Test isolation       | Separate `tests/evaluation/` module for accuracy tests (P2)   |
| Ground truth         | Cho Chikun C[] comment provides professional-grade labels     |

**Gate verdict:** S.4 passes. The two-population architecture is sound and the integrity tests enforce the key invariant (disjointness). Level coverage enhancement is recommended but not blocking.
