# Options — Enrichment Lab Production Readiness

> Initiative: `20260318-1400-feature-enrichment-lab-production-readiness`
> Last Updated: 2026-03-18

---

## Option Set

| OPT-ID | Title | Approach |
|--------|-------|----------|
| OPT-1 | **Phased Activation with Conservative Thresholds** | Activate features in 6 tiers by risk level. Keep current thresholds. Compute `qk` quality. Consolidate hinting. Calibrate in parallel. |
| OPT-2 | Big Bang — All Features + Tightened Thresholds | Activate all 16 features simultaneously. Tighten thresholds to plan recommendations. |
| OPT-3 | Calibration-First, Evidence-Driven Activation | No activation until golden set fully populated and calibrated. Feature order determined by evidence only. |

---

## OPT-1: Phased Activation with Conservative Thresholds (RECOMMENDED)

| Aspect | Detail |
|--------|--------|
| **Approach** | 6-phase activation (Phase 0→1a→1b→1c→2→3). Each phase has explicit gate condition. Hinting consolidation runs in parallel. `qk` quality algorithm implemented with config-driven weights. OPP-1/2/3 included. |
| **Phase 0** (infrastructure) | Instantiate `ai_solve=AiSolveConfig()`, populate `elo_anchor.calibrated_rank_elo`, wire `policy_entropy` + `correct_move_rank` to result (OPP-1) |
| **Phase 1a** (scoring) | PI-1, PI-3, PI-12 — independent scoring signals, zero interaction risk |
| **Phase 1b** (engine) | PI-5, PI-6, `suboptimal_branches` — engine-behavior changes, budget delta < 20% |
| **Phase 1c** (text) | PI-10, PI-11 — player-visible comment improvements |
| **Phase 2** (budget-sensitive) | PI-2, PI-7, PI-8, PI-9 — requires budget cap ≤4x, monitoring |
| **Phase 3** (calibration-gated) | `instinct_enabled`, `elo_anchor`, PI-4 — requires golden set, macro-F1 ≥ 0.85 |
| **Parallel** | Hinting consolidation (G4), YX extension (G2), `qk` algorithm (G3), OPP-2/3, docs (G9) |
| **Benefits** | Observable, attributable, rollback-friendly. Phase 1a is zero-risk. Each phase validates before next. |
| **Drawbacks** | 6 validation checkpoints. Phase 3 blocked on calibration labeling. |
| **Risks** | Low per-phase. Medium cumulative if Phase 2 compounds budget. Mitigated by budget ceiling (C7). |
| **Test impact** | High — each phase adds phase-gate tests. OPP-2 adds ≥12 detector orientation suites. |
| **Rollback** | Revert config JSON per phase. No schema changes require data migration. |
| **Architecture compliance** | ✅ All work in `tools/puzzle-enrichment-lab/`. Config-driven. No backend imports. |

## OPT-2: Big Bang — All Features + Tightened Thresholds (REJECTED)

| Aspect | Detail |
|--------|--------|
| **Approach** | Activate all 16 features simultaneously. Tighten to `t_good=0.02, t_bad=0.08, t_hotspot=0.25`. |
| **Benefits** | Single deployment. Immediate full feature richness. |
| **Drawbacks** | Impossible to attribute regressions. Budget explosion from PI-2+PI-7+PI-8+PI-9 compounding (~4x). Instinct activates with 0 golden labels — violates AC-4 gate. |
| **Risks** | HIGH — interaction effects between adaptive visits, branch escalation, multi-pass, player alternatives are untested in combination. |
| **Rejection reason** | Unanimously rejected by governance panel (7/7). Violates instinct AC-4 gate. Tightening thresholds without calibration creates unvalidated behavior. Score: 51/100. |

## OPT-3: Calibration-First, Evidence-Driven Activation (REJECTED)

| Aspect | Detail |
|--------|--------|
| **Approach** | No activation until golden set fully populated, calibration run completed, and macro-F1 ≥ 0.85 validated. Feature order determined purely by calibration evidence. |
| **Benefits** | Highest confidence. Every activation justified by data. Zero risk of premature activation. |
| **Drawbacks** | Blocks ALL activation on golden set population (0 labels today). No timeline for labeling. |
| **Risks** | Medium delay risk. Blocks proven-safe features (PI-1/3/12 have no calibration dependency). |
| **Rejection reason** | Rejected by 5/7 panel members. Too conservative — blocks zero-risk Phase 1a activations unnecessarily. Score: 78/100. |

---

## Evaluation Criteria & Tradeoff Matrix

| CRT-ID | Criterion | Weight | OPT-1 | OPT-2 | OPT-3 |
|--------|-----------|--------|-------|-------|-------|
| CRT-1 | Feature activation speed | 20 | 16 | 20 | 6 |
| CRT-2 | Regression risk | 25 | 22 | 8 | 25 |
| CRT-3 | Attribution / observability | 15 | 14 | 3 | 15 |
| CRT-4 | Budget predictability | 15 | 12 | 5 | 15 |
| CRT-5 | Calibration confidence | 15 | 10 | 5 | 15 |
| CRT-6 | User-visible value velocity | 10 | 8 | 10 | 2 |
| **Total** | | **100** | **82** | **51** | **78** |

---

## Feature Gate Interaction Analysis

### Compounding Budget Effects (Phase 2)

| Combination | Interaction | Severity |
|-------------|------------|----------|
| PI-2 + PI-7 | Adaptive visits × escalation doubles | HIGH — multiplicative budget |
| PI-7 + PI-8 | Escalation × multi-pass | HIGH — O(branches × 2) |
| PI-5 + PI-8 | Board-scaled noise × secondary multiplier | MEDIUM |
| PI-9 + PI-2 | Player alternatives × adaptive budget | MEDIUM |

**Worst case**: ~4x current budget (210 effective queries vs 50). Ceiling enforced in C7.

### Safe Concurrent Activation (No Interactions)

| Features | Why safe |
|----------|---------|
| PI-1 + PI-3 + PI-12 | Independent scoring signals; additive only |
| PI-10 + PI-11 | Text-only + calibration-only; no engine interaction |
| PI-5 + PI-6 | Independent mechanisms |
| suboptimal_branches | Fully independent; post-refutation |

### Calibration-Gated

| Feature | Gate | Current State |
|---------|------|---------------|
| instinct_enabled | ≥70% accuracy on golden set | 0 labels — BLOCKED |
| elo_anchor | Populated calibrated_rank_elo | Empty list — BLOCKED |
| PI-4 (model_by_category) | Multi-model KataGo setup | Empty dict — BLOCKED |

---

## Must-Hold Constraints for Selected Option

| MHC-ID | Constraint |
|--------|------------|
| MHC-1 | Phase 0 infrastructure completes before any feature activation |
| MHC-2 | No feature activates without its explicit gate condition met |
| MHC-3 | Non-circular labeling methodology for golden set (C+A hybrid) |
| MHC-4 | Budget ceiling ≤4x for Phase 2 |
| MHC-5 | Player-visible impact in every phase |
| MHC-6 | `qk` weights config-driven, visit-count gated |
| MHC-7 | All work in `tools/puzzle-enrichment-lab/` unless authorized |
| MHC-8 | Hinting consolidation: copy from backend, don't import |

---

## Recommendation

| Field | Value |
|-------|-------|
| **Recommended option** | OPT-1 |
| **Score** | 82/100 |
| **Panel endorsement** | Unanimous (7/7 advisory) |
| **Selection rationale** | Lowest risk per phase. Observable and attributable. Respects instinct AC-4 gate. Supports parallel calibration. Only option that addresses all charter goals (G1-G9) without violating constraints. |

> **See also**:
>
> - [Charter](./00-charter.md) — Goals, constraints, acceptance criteria
> - [Governance Decisions](./70-governance-decisions.md) — Panel reviews (Gates 1-3)
> - [Research](./15-research.md) — Full gap synthesis
