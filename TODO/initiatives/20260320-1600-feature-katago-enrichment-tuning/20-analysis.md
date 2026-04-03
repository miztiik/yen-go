# Analysis — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20

---

## 1. Scope

### Files to Modify

| A-ID | File | Change Type | Risk |
|------|------|-------------|------|
| A-1 | `config/katago-enrichment.json` | 14 value changes + version bump + changelog | Low — config-only |
| A-2 | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | Code fix ~5 lines: adaptive boost compounding | Medium — behavioral change |
| A-3 | `tools/puzzle-enrichment-lab/AGENTS.md` | Doc update: adaptive mode note | Low — documentation |
| A-4 | `tools/puzzle-enrichment-lab/tests/test_remediation_sprints.py` | New test: adaptive+boost interaction | Low — test addition |

### No CRITICAL Findings

All four experts agree on direction for every consensus-backed change. No unresolved critical analysis findings.

## 2. Backward Compatibility

- **Required**: No (D-1). Config changes affect future enrichment runs only.
- **Code fix**: Backward compatible — `visit_allocation_mode="fixed"` behavior unchanged (boosts applied then no adaptive override).

## 3. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test failures from config value changes | Medium | Low | Run full test suite; adjust test assertions if thresholds changed |
| Adaptive+boost compound creates excessive visits | Low | Low | Cap: `min(boosted, T2 visits)` |
| Classification changes (t_bad 0.15→0.12) reclassify edge moves | Medium | Low | Narrow scope: only ~5% moves in 0.12-0.15 delta range affected |

## 4. Dependencies

None. All changes are internal to the enrichment lab tool and its config.

## 5. Threshold Interaction Analysis (RC-6)

### Classification Threshold Cluster
- `t_bad` 0.15→0.12 + `t_disagreement` 0.10→0.07 + `branch_disagreement_threshold` 0.10→0.07
- **Combined effect**: The t_bad/delta_threshold gap narrows from 0.07 to 0.04 (still preserving 4% buffer for "interesting wrong" moves). The disagreement thresholds tighten in parallel, meaning branch-local escalation (PI-7) fires earlier (7% vs 10% winrate swing). This is coherent: tighter t_bad classification paired with earlier disagreement detection ensures moves near the new BM boundary get extra scrutiny via escalation.
- **Interaction risk**: Low. The thresholds serve different pipeline stages — t_bad is classification (solve_position), branch_disagreement is tree-building escalation (PI-7). They don't compete.

### Visit Budget Cluster
- `refutation_visits` 100→200 + `continuation_visits` 125→200
- **Combined effect**: Both reach 200, creating a uniform "standard analysis" tier within the tree. The visit hierarchy becomes: forced (125) ≤ continuation/refutation (200) < branch (500). This is analytically correct per MCTS theory — refutation and continuation queries have comparable difficulty (both evaluate opponent responses).
- **Budget impact**: With `max_total_tree_queries=65` and average ~35 queries per puzzle, the per-puzzle visit increase is approximately: 35 queries × (200-125) = ~2625 visits → ~0.4s on b18. Modest.

### No adverse cross-cluster interaction
The classification and visit clusters are independent: classification uses winrate deltas (dimensionless), visits control search depth. Changing t_bad doesn't affect how many visits refutations get, and vice versa.
