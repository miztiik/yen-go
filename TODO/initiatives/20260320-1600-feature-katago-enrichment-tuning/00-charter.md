# Charter — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Type**: Feature (config tuning + code fix)
**Date**: 2026-03-20

---

## Goals

1. **Improve move classification accuracy** — Tighten `t_good` (0.05→0.03) and narrow the `t_bad`/`delta_threshold` gap (0.15→0.12) to eliminate the "refutation exists but move isn't labeled bad" inconsistency.
2. **Fix solution tree completeness** — Raise entry-level minimum depth from 2→3 to prevent incomplete solution trees that miss the confirmation move.
3. **Improve refutation tree quality** — Double refutation visits (100→200) to ensure value convergence, raise continuation visits (125→200) for dan-level sequence confirmation.
4. **Fix dead code: adaptive boost override** — Resolve the code defect where `visit_allocation_mode=adaptive` silently overrides corner/ladder visit boosts since v1.24.
5. **Improve seki detection** — Widen `score_lead_seki_max` (2.0→5.0) to catch seki positions with dead stones in territory.
6. **Tune miscellaneous thresholds** — Adjust `t_disagreement`, `score_delta_ko`, `max_total_tree_queries`, `candidate_max_count`, `strong.solution_max_depth` based on expert consensus.

## Non-Goals

- Changing the quick model from b10c128 (adequate for T0 policy screening)
- Changing deep_enrich visits from 2000 (past convergence knee for tsumego)
- Changing T3 referee visits from 5000 (b28 fully converged)
- Changing `delta_threshold` from 0.08 (correctly calibrated for teaching value)
- Changing ownership thresholds (0.7/-0.7 is standard for tsumego)
- Full production calibration run (separate operational concern)

## Constraints

- **C1**: Config version bump to v1.26 with complete changelog entry
- **C2**: All threshold changes must maintain constraint C9 from v1.23 (threshold conservation)
- **C3**: Visit budget changes must stay within ~15% compute increase per batch
- **C4**: Code fix (S-1) must NOT change behavior when `visit_allocation_mode="fixed"` (backward compat for fixed mode)
- **C5**: All changes require test coverage — existing tests must pass, new tests for the code fix

## Acceptance Criteria

| AC-ID | Criterion | Verification |
|-------|-----------|-------------|
| AC-1 | `t_good=0.03`, `t_bad=0.12` correctly classify TE/BM moves in unit tests | Existing solve_position tests + new threshold boundary tests |
| AC-2 | Entry-level solution trees have min depth ≥ 3 | Unit test asserting no depth-2 trees for entry profile |
| AC-3 | `refutation_visits=200` produces stable q-values (noise < delta_threshold/2) | Existing refutation tests pass with updated config value |
| AC-4 | Adaptive allocation compounds with corner/ladder boosts | New test: `effective_visits = branch_visits * corner_visit_boost` when adaptive+corner |
| AC-5 | Seki detection catches positions with score_lead ≤ 5.0 | Existing seki detection tests + new boundary test |
| AC-6 | All existing tests pass with new config values | Full test suite: `pytest tools/puzzle-enrichment-lab/tests/ --ignore=...` |
| AC-7 | Changelog v1.26 documents all changes | Manual verification |

## Scope Summary

| Category | Count | Parameters |
|----------|-------|------------|
| Config value changes | 14 | t_good, t_bad, t_disagreement, entry.min_depth, strong.max_depth, score_lead_seki_max, score_delta_ko, refutation_visits, max_total_tree_queries, continuation_visits, candidate_max_count, branch_disagreement_threshold, curated_pruning.min_depth, calibration.sample_size |
| Code fix | 1 | solve_position.py — adaptive boost compounding |
| Config metadata | 1 | Version bump 1.25→1.26 + changelog |
| Tests | ~3-5 | New tests for code fix + threshold boundary cases |
| Documentation | 1 | AGENTS.md update (adaptive mode note correction) |

> **See also**:
>
> - [Research Brief](./15-research.md) — Four-expert consensus matrix and rejected recommendations
> - [Clarifications](./10-clarifications.md) — Q1-Q6 decision points
