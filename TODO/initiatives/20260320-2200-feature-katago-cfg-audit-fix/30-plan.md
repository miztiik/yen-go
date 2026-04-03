# Plan — KataGo .cfg Audit & Fix

**Initiative ID**: `20260320-2200-feature-katago-cfg-audit-fix`
**Selected Option**: OPT-B (Tsumego-Optimized)
**Status**: approved (governance Gate 3)

---

## Implementation Strategy

Apply all 9 parameter changes from OPT-B in a single execution pass across 3 files, organized into 4 parallel lanes by file scope.

### Parallel Lane Plan

| lane_id | task_ids | scope_files | dependencies | status |
|---------|----------|-------------|--------------|--------|
| L1 | T1-T6 | `tsumego_analysis.cfg` | None | ✅ merged |
| L2 | T7 | `test_tsumego_config.py` | L1 (reads .cfg) | ✅ merged |
| L3 | T8 | `AGENTS.md` | None | ✅ merged |
| L4 | T9-T10 | — (test runs) | L1, L2, L3 | ✅ merged |

### Execution Order

1. **Batch 1** (parallel): L1 + L3 — .cfg changes and AGENTS.md (independent files)
2. **Batch 2** (sequential): L2 — test file (depends on .cfg values for validation)
3. **Batch 3** (sequential): L4 — run tests to verify

### Parameter Changes (OPT-B: Tsumego-Optimized)

| # | Change Type | Key | Old Value | New Value | Rationale |
|---|-------------|-----|-----------|-----------|-----------|
| 1 | DELETE | `analysisWideRootNoise` | `0.0` | — | Deprecated; `wideRootNoise` already set |
| 2 | DELETE | `scoreUtilityFactor` | `0.1` | — | Deprecated; replaced by `staticScoreUtilityFactor` |
| 3 | DELETE | `allowSelfAtari` | `true` | — | GTP-only; no-op in analysis mode |
| 4 | DELETE | `cpuctExplorationAtRoot` | `1.3` | — | Not a valid KataGo parameter |
| 5 | ADD | `staticScoreUtilityFactor` | — | `0.1` | Explicit seki detection control |
| 6 | EDIT | `rootPolicyTemperature` | `0.7` | `1.0` | Fix double exploration suppression |
| 7 | EDIT | `rootPolicyTemperatureEarly` | `0.7` | `1.5` | Boost low-prior tesuji discovery |
| 8 | EDIT | `cpuctExploration` | `0.7` | `1.0` | Restore neutral exploration (KataGo default) |
| 9 | EDIT | `subtreeValueBiasFactor` | `0.4` | `0.25` | Reduce value overestimation (KataGo default) |

## Documentation Plan

| doc_id | action | file | why_updated |
|--------|--------|------|-------------|
| DOC-1 | update | `tools/puzzle-enrichment-lab/AGENTS.md` | Add gotcha bullet for .cfg v2 audit changes |
| DOC-2 | add | Version header in `tsumego_analysis.cfg` | Auditability and changelog |

### files_to_update

- `tools/puzzle-enrichment-lab/AGENTS.md` — Section 6 gotcha bullet

### files_to_create

- None (all changes are edits to existing files)

### why_updated

- AGENTS.md: Agent-facing documentation must reflect the 4 removed keys and parameter changes to prevent confusion during future enrichment lab work.

## Validation Plan

| val_id | scope | command | pass_criteria |
|--------|-------|---------|---------------|
| VAL-1 | Config tests | `pytest tests/test_tsumego_config.py -v` | 11/11 pass |
| VAL-2 | Enrichment regression | `pytest tests/ -m "not slow" --ignore=...` | No new failures |
| VAL-3 | Backend unit | `pytest backend/ -m unit -q` | 0 failures |
| VAL-4 | Grep verification | grep for 4 deleted keys | 0 matches in active config lines |

## Risks & Mitigations

| risk_id | risk | mitigation |
|---------|------|------------|
| R-1 | MCTS param changes alter enrichment output | Future runs affected only; published SGFs immutable |
| R-2 | `rootPolicyTemperatureEarly=1.5` too aggressive | Revert to 1.0 if calibration shows regression |
| R-3 | .cfg file reverts (observed 3 times) | Commit to git immediately; add to memory |
