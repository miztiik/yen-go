# Options

> Initiative: `20260315-2000-feature-refutation-quality`
> Last Updated: 2026-03-15

---

## Planning Confidence Score

- **Score**: 82/100
- **Risk Level**: medium
- Deductions: -10 (test strategy details unclear), -8 (calibration data for ownership_delta_weight unknown)
- Research invoked: Yes (Feature-Researcher codebase audit → 59 findings in 15-research.md)

---

## Options Table

| Dimension | OPT-1: Signal-Quality-First | OPT-2: Compute-Efficiency-First | OPT-3: Parallel Tracks |
|-----------|----------------------------|--------------------------------|----------------------|
| **Approach** | Phase A: PI-1 (ownership) + PI-3 (score delta) → Phase B: PI-2 (adaptive visits) + PI-4 (model routing) → Phase C: PI-5 (noise) + PI-6 (forced visits) + PI-7 (disagreement) + PI-8 (harvesting) | Phase A: PI-2 (adaptive visits) + PI-4 (model routing) → Phase B: PI-1 (ownership) + PI-3 (score delta) → Phase C: PI-5 + PI-6 + PI-7 + PI-8 | Phase A: PI-1 + PI-3 + PI-4 (signal quality + cheapest efficiency win) → Phase B: PI-2 + PI-5 + PI-6 → Phase C: PI-7 + PI-8 |
| **Rationale** | Improve what we measure before optimizing compute. Better signals mean less wasted compute on false refutations. | Reduce compute cost first so signal improvements can be iterated faster. Model routing has immediate ROI. | Mix quick wins from both categories. PI-4 (model routing) is pure config; PI-1/PI-3 are low-effort signal improvements. |
| **Phase A effort** | Low (config + ~70 LOC total) | Medium (algorithm changes for adaptive visits) | Low-Medium (config + ~70 LOC + config mapping) |
| **Phase A impact** | Better refutation quality immediately | 30-50% deeper trees, 2-4x faster easy puzzles | Both signal quality AND compute savings |
| **Calibration risk** | `ownership_delta_weight` needs gold-standard calibration before production. Can start at 0.0. | Low risk — adaptive visits is a mechanical change | Same calibration risk as OPT-1, but model routing adds integration test requirement |
| **Governance alignment** | ✅ Cho Chikun, Ke Jie, Hana Park prefer signal quality first | ⚠️ Shin Jinseo and Staff Eng B prefer compute first but accept signal-first ordering | ✅ Balances both camps. Lee Sedol likes pairing discovery with compute. |
| **Dependencies** | None between PI-1 and PI-3 (parallel-safe) | PI-2 changes tree builder that PI-7/PI-8 also touch (potential merge conflicts) | PI-4 is independent. PI-1 + PI-3 are independent. No Phase A conflicts. |
| **Rollback** | Simple: set `ownership_delta_weight: 0.0`, `score_delta_enabled: false` | Simple: set `visit_allocation_mode: "fixed"` | Simple: each feature individually gated |
| **Test impact** | Low — add scoring tests to `test_generate_refutations.py` | Medium — tree builder changes need `test_solve_position.py` updates | Low-Medium |
| **Benefits** | Immediate puzzle quality improvement. Ownership delta catches "teaching refutations" missed by winrate. Score delta stabilizes detection. | Batch processing speedup. Deeper trees for same budget. Model routing halves compute for 40-50% of puzzles. | Best of both: quick quality AND efficiency wins. Defers only the complex algorithm changes. |
| **Drawbacks** | No compute savings in Phase A. Calibration uncertainty for ownership weight. | Quality improvement delayed to Phase B. Adaptive visits changes touch critical tree builder code. | Phase A has 3 items instead of 2 (slightly larger scope). |
| **Recommendation** | | | **✅ Recommended** |

---

## Recommendation: OPT-3 (Parallel Tracks)

**Why OPT-3 is the best fit:**

1. **Quick wins from both dimensions**: PI-1 (ownership delta, ~50 LOC) and PI-3 (score delta, ~20 LOC) are low-effort signal improvements. PI-4 (model routing) is pure config mapping with no algorithm changes.
2. **No dependency conflicts in Phase A**: All three items touch different code paths — PI-1/PI-3 modify `generate_refutations.py` scoring, PI-4 modifies `single_engine.py` model selection.
3. **Phase B defers the hard stuff**: Adaptive visits (PI-2) and forced minimum visits (PI-6) both modify `solve_position.py` tree builder — better to tackle together after Phase A is stable.
4. **Governance balance**: Satisfies signal-quality advocates (Cho Chikun, Ke Jie, Hana Park) and compute-efficiency advocates (Shin Jinseo, Staff Eng B) simultaneously.
5. **Lowest risk**: Each Phase A item is independently feature-gated. Failure of one doesn't block others.

---

## Evaluation Criteria

| Criterion | Weight | OPT-1 | OPT-2 | OPT-3 |
|-----------|--------|-------|-------|-------|
| EC-1: Immediate puzzle quality | 30% | ✅ High | ❌ Low (delayed) | ✅ High |
| EC-2: Compute efficiency | 20% | ❌ Low (delayed) | ✅ High | ⚠️ Medium (PI-4 only) |
| EC-3: Phase A effort/risk | 20% | ✅ Low | ⚠️ Medium | ✅ Low-Medium |
| EC-4: Dependency safety | 15% | ✅ Safe | ⚠️ Tree builder conflicts | ✅ Safe |
| EC-5: Governance alignment | 15% | ⚠️ Signal-biased | ⚠️ Compute-biased | ✅ Balanced |
| **Weighted Score** | — | 72 | 65 | **83** |

> **See also**:
> - [Charter: 00-charter.md](00-charter.md) — Scope, goals, classification tables
> - [Research: 15-research.md](../starter/15-research.md) — Codebase audit
