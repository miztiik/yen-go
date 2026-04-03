# D2: Difficulty Classifier Improvement — Research & Audit

**Created:** 2026-03-04  
**Status:** Research complete  
**Related:** [puzzle-quality-scorer/implementation-plan.md](../puzzle-quality-scorer/implementation-plan.md) — Full implementation plan (Phases 1–4)  
**Scope:** Audit current `core/classifier.py`, document bugs and limitations, propose calibration strategy using collection `level_hint` data.

---

## 1. Current Classifier Audit

### 1.1 Architecture

File: `backend/puzzle_manager/core/classifier.py` (268 lines)

The classifier uses an **additive scoring** approach with 4 features summed into a raw score, then mapped to 9 difficulty levels (1=novice through 9=expert).

```
score = depth_score + variation_score + stone_count_score + board_size_adj
```

The code itself comments: _"This is a placeholder — real implementation would use more sophisticated analysis"_.

### 1.2 Feature Analysis

| Feature         | Score range | Thresholds      | Assessment                                            |
| --------------- | ----------- | --------------- | ----------------------------------------------------- |
| Solution depth  | 1–7         | 1/2/3/5/7/10+   | Crude — follows `children[0]` not correct child (BUG) |
| Variation count | 0–3         | 2/5/10+         | Counts all branches, not reading-relevant ones        |
| Stone count     | 0–3         | 10/20/40+       | Weak proxy — more stones ≠ harder                     |
| Board size adj  | -1 to +1    | 9×9/13×13/19×19 | Minor but reasonable                                  |

**Total score range:** 0–14, mapped to levels via `score ≤ 2 → 1` through `score > 16 → 9`.

### 1.3 Known Bugs

#### Bug 1: `_get_solution_depth()` follows wrong child

```python
def _get_solution_depth(root: SolutionNode) -> int:
    depth = 0
    current = root
    while current and current.children:
        depth += 1
        current = current.children[0]  # ← BUG: follows FIRST child, not CORRECT child
    return depth
```

**Impact:** When the first child is a wrong-answer refutation branch, the measured depth reflects the wrong variation, not the main solution line. This can both over-count (if refutation branch is deeper) and under-count (if it terminates early).

**Fix exists:** `core/complexity.py` has `compute_solution_depth()` that correctly follows `child.is_correct`:

```python
def compute_solution_depth(node: SolutionNode) -> int:
    depth = 0
    current = node
    while current.children:
        for child in current.children:
            if child.is_correct:
                depth += 1
                current = child
                break
        else:
            break
    return depth
```

**Priority:** High — this is a correctness bug. Should be fixed immediately by replacing the call with `core.complexity.compute_solution_depth()`.

#### Bug 2: Score-to-level mapping has gaps

Score range 15–16 maps to level 8, but the additive features max out at 14. Levels 8 (high-dan) and 9 (expert) are unreachable. All hard puzzles collapse into level 7 (low-dan).

**Impact:** The classifier can never output levels 8 or 9 from heuristic scoring alone.

### 1.4 Fundamental Limitations

1. **No technique awareness** — A 3-move ladder and a 3-move ko fight score identically, despite vastly different reading difficulty.

2. **No spatial analysis** — Stone count is a poor proxy for position complexity. 6 stones in a tight corner group may be harder than 40 stones in a simple capture.

3. **No liberty analysis** — Liberty counts are the single strongest predictor of tactical complexity in Go. Groups with 1–2 liberties create forced sequences; groups with 5+ liberties are flexible. The classifier doesn't consider this.

4. **No reading depth estimation** — The solution tree depth measures the _author's_ answer depth, not the _reader's_ required calculation. A puzzle with many short refutation branches may require more reading than one with a long main line.

5. **Linear additive model** — Features interact (e.g., high depth + few variations = straightforward sequence; moderate depth + many variations = complex reading). The additive model misses these interactions.

---

## 2. Collection-Based Level Hints (Calibration Data)

### 2.1 Available Ground Truth

`config/collections.json` provides `level_hint` for 16 collections:

| Collection                     | level_hint           | Estimated puzzles |
| ------------------------------ | -------------------- | ----------------- |
| Various advanced collections   | `advanced`           | ~200+             |
| Cho Chikun Elementary          | `elementary`         | ~200+             |
| Cho-Chikun Intermediate        | `intermediate`       | ~200+             |
| Various beginner collections   | `beginner`           | ~150+             |
| High-dan collections           | `high-dan`           | ~100+             |
| Low-dan collections            | `low-dan`            | ~100+             |
| Expert collections             | `expert`             | ~50+              |
| Novice collections             | `novice`             | ~50+              |
| Upper-intermediate collections | `upper-intermediate` | ~100+             |

**Total calibration data:** ~1,200+ puzzles with expert-assigned difficulty levels across all 9 levels. This is sufficient for both training and validation of an improved classifier.

### 2.2 Calibration Strategy

1. **Extract features** from all puzzles in level-hinted collections using `complexity.py` metrics (`compute_solution_depth`, `count_total_nodes`, `count_stones`, `is_unique_first_move`, `compute_avg_refutation_depth`) plus new tactical features.

2. **Analyze distribution** of each feature per level. Identify which features best discriminate between adjacent levels.

3. **Fit thresholds** using the ground-truth levels. This can be:
   - **Decision tree** — simple, interpretable, config-driven thresholds
   - **Weighted linear model** — learned weights instead of hand-tuned ones
   - **Ordinal regression** — proper statistical model for ordered categories

4. **Cross-validate** using leave-one-collection-out to avoid overfitting to any single source's grading style.

5. **Report confusion matrix** — where does the classifier under/over-estimate? Are certain techniques systematically misclassified?

### 2.3 Feature Candidates for Improved Classifier

From existing `core/complexity.py`:

| Feature              | Code                             | Available | Discriminative power                     |
| -------------------- | -------------------------------- | --------- | ---------------------------------------- |
| Solution depth       | `compute_solution_depth()`       | ✅        | Medium — correlates with level but noisy |
| Total nodes          | `count_total_nodes()`            | ✅        | High — reading workload                  |
| Stone count          | `count_stones()`                 | ✅        | Low — weak proxy                         |
| Unique first move    | `is_unique_first_move()`         | ✅        | Low — binary flag                        |
| Avg refutation depth | `compute_avg_refutation_depth()` | ✅        | **High** — measures defensive reading    |

From proposed `core/tactical_analyzer.py` (see implementation plan):

| Feature                | Code                            | Available    | Discriminative power                     |
| ---------------------- | ------------------------------- | ------------ | ---------------------------------------- |
| Tactical complexity    | `compute_tactical_complexity()` | ❌ (Phase 1) | **Very high** — counts active techniques |
| Min liberty count      | `find_weak_groups()`            | ❌ (Phase 1) | **Very high** — urgency indicator        |
| Group status mix       | `assess_group_status()`         | ❌ (Phase 1) | High — alive/dead/unsettled balance      |
| Ladder presence        | `detect_ladder()`               | ❌ (Phase 1) | Medium — known technique                 |
| Snapback presence      | `detect_snapback()`             | ❌ (Phase 1) | Medium — known technique                 |
| Eye count in key group | `count_eyes()`                  | ❌ (Phase 1) | High — life/death complexity             |

---

## 3. Improvement Roadmap

### Phase 0: Bug Fixes (Immediate, ~1 hour)

1. **Replace `_get_solution_depth()` with `complexity.compute_solution_depth()`** in `classify_difficulty()`. This is a one-line fix that improves correctness.

2. **Fix score-to-level mapping** — extend score thresholds or change feature scoring so levels 8–9 are reachable.

### Phase 1: Feature Enrichment (~1 week)

Use existing `core/complexity.py` features that the classifier currently ignores:

- `compute_avg_refutation_depth()` — already computed for YX but not used in classification
- `count_total_nodes()` — measures total reading workload
- `is_unique_first_move()` — miai positions are generally harder

This requires NO new code — just consuming existing functions.

### Phase 2: Calibration (~1 week)

1. Extract features for all level-hinted collection puzzles
2. Compute optimal thresholds per feature
3. Replace hand-tuned additive scoring with calibrated weights
4. Validate against leave-one-collection-out cross-validation
5. Store thresholds in `config/classifier-thresholds.json` (config-driven, not hardcoded)

### Phase 3: Tactical Analysis Integration (~2–3 weeks)

Implement `core/tactical_analyzer.py` per the [implementation plan](../puzzle-quality-scorer/implementation-plan.md):

- Ladder/snapback/capture detection
- Eye counting and group status
- Weak group analysis
- Feed tactical complexity into classifier

### Phase 4: Professional Review

Have puzzles classified by the improved system reviewed by a Go professional (1P+). Focus on:

- Boundary cases between adjacent levels
- Technique-specific difficulty (is a 5-move ladder easier than a 3-move ko?)
- Collection-specific grading bias

---

## 4. Recommended Approach

**Start with Phase 0 + Phase 1** — fix the bugs and use already-available features. This requires minimal code changes (~20 lines total) and provides immediate improvement.

**Then Phase 2** — calibrate against collection level_hints. The calibration data exists and the infrastructure (`resolve_level_from_collections()` in classifier.py) already supports collection-based overrides. The calibration step determines whether the heuristic classifier, after bug fixes and feature enrichment, is "good enough" or requires tactical analysis (Phase 3).

**Phase 3 only if needed** — tactical analysis is a significant engineering effort. If calibrated features achieve >70% accuracy against ground-truth levels, the marginal improvement from tactical analysis may not justify the cost. Run the calibration first to decide.

---

## 5. References

| Document                              | Location                                                                                                  |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Strategy D implementation plan        | [002-implementation-plan-strategy-d.md](../puzzle-quality-strategy/002-implementation-plan-strategy-d.md) |
| Quality landscape research            | [001-research-quality-landscape.md](../puzzle-quality-strategy/001-research-quality-landscape.md)         |
| Tactical analyzer implementation plan | [puzzle-quality-scorer/implementation-plan.md](../puzzle-quality-scorer/implementation-plan.md)           |
| Tactical reference: GoGoGo tactics    | [puzzle-quality-scorer/reference/gogogo-tactics.md](../puzzle-quality-scorer/reference/gogogo-tactics.md) |
| Collections config (level_hints)      | `config/collections.json`                                                                                 |
| Current classifier                    | `backend/puzzle_manager/core/classifier.py`                                                               |
| Complexity metrics                    | `backend/puzzle_manager/core/complexity.py`                                                               |
| Board simulation                      | `backend/puzzle_manager/core/board.py`                                                                    |

---

_Last Updated: 2026-03-04_
