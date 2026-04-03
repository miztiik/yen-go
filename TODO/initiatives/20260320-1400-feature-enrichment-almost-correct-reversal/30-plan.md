# Plan — Enrichment Almost-Correct Reversal

**Initiative**: `20260320-1400-feature-enrichment-almost-correct-reversal`
**Date**: 2026-03-20
**Selected Option**: OPT-1 (Surgical reversal)
**Governance**: GOV-OPTIONS-APPROVED (7/7)

## Architecture & Design Decisions

### AD-1: Remove RC-5 All-Skip Gate (P1 fix)

**Current code** (`sgf_enricher.py` lines 414–440):
```python
skipped_all_almost = False

if result.refutations and not _has_existing_refutation_branches(root):
    almost_threshold = 0.05  # hardcoded
    all_almost = all(abs(ref.delta) < almost_threshold for ref in result.refutations)
    if all_almost:
        skipped_all_almost = True
        # logs + skips all branches
    else:
        refutation_branches = _build_refutation_branches(result, player_color)
```

**Change**: Remove the `skipped_all_almost` variable, the `all_almost` check, and the `not skipped_all_almost` guard on YR fallback (line 459). The code simplifies to: if refutations exist, build branches. Per-move `almost_correct` handling is already correct in `teaching_comments.py`.

**Lines to remove/modify**:
1. Line 414: Remove `skipped_all_almost = False`
2. Lines 420–430: Remove entire `all_almost` check block
3. Line 459: Remove `and not skipped_all_almost` from YR fallback condition

### AD-2: Remove Curated Gate + Add Cap (P3 fix)

**Current code** (`sgf_enricher.py` line 416):
```python
if result.refutations and not _has_existing_refutation_branches(root):
```

**Change**: Remove the `not _has_existing_refutation_branches(root)` condition. Add explicit cap logic:
```python
if result.refutations:
    existing_count = _count_existing_refutation_branches(root)
    max_total = <from config: max_refutation_root_trees>  # 3
    budget = max(0, max_total - existing_count)
    refutation_branches = _build_refutation_branches(result, player_color)[:budget]
```

**New helper**: `_count_existing_refutation_branches(root) -> int` — counts (not just detects) existing wrong branches. Reuses the same detection logic as `_has_existing_refutation_branches` but returns count.

**Config access**: Read `max_refutation_root_trees` from `katago-enrichment.json` → `ai_solve.solution_tree.max_refutation_root_trees` (default=3). The enricher already loads this config file at `_ENRICHMENT_CONFIG_PATH`.

### AD-3: Fix Spoiler Template (P2 fix)

**Current** (`config/teaching-comments.json` line 309):
```json
{"condition": "almost_correct", "comment": "Close — {!xy} is slightly better."}
```

**Change to**:
```json
{"condition": "almost_correct", "comment": "Close, but not the best move."}
```

### AD-4: Stop Passing `correct_first_coord` for almost_correct

**Current** (`teaching_comments.py` lines 300–303, 316–319):
```python
wrong_comments[ref.wrong_move] = assemble_wrong_comment(
    condition="almost_correct",
    coord=correct_first_coord,  # ← SPOILER: passes the ANSWER coordinate
    ...
)
```

**Change**: Pass `coord=""` for `almost_correct` condition. Defense-in-depth: even if someone later adds `{!xy}` back to the template, it won't render the correct answer coordinate.

### AD-5: `_has_existing_refutation_branches` fate

The function itself is NOT deleted — it may be useful for other purposes (e.g., observability logging). However, it is no longer used as a gate in the enrichment flow. The new `_count_existing_refutation_branches` replaces its role. If `_has_existing_refutation_branches` has no other callers, it can be removed (dead code policy).

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cap logic off-by-one: count existing curated wrong as 0 when they have different format | Medium | AI adds too many branches | Test with multiple curated formats (WV, BM, comment-based) |
| Template change breaks existing tests checking exact comment text | Low | Test failures | Grep for "Close —" and "slightly better" in test files |
| `assemble_wrong_comment()` crashes without coord for almost_correct | Low | Pipeline error | Test explicitly: assemble with condition="almost_correct", no coord |
| Removing curated gate exposes bugs in branch deduplication (AI branch same coord as curated) | Medium | Duplicate branches in SGF | Add dedup logic: skip AI branch if coord already exists in curated |

## Data Model Impact

None. No schema changes. No new SGF properties. No database changes.

## Contracts/Interfaces

- `enrich_sgf()` — public API unchanged. Same signature, same return type.
- `_build_refutation_branches()` — unchanged.
- `_count_existing_refutation_branches()` — new internal helper.
- `teaching-comments.json` — template text change only. no structural change.

## Documentation Plan

| Action | File | Why |
|--------|------|-----|
| Update | `tools/puzzle-enrichment-lab/AGENTS.md` | Reflect removal of curated gate and all-skip logic |

No new docs files needed. This is a regression fix, not a new feature.

> **See also**:
> - [Charter](./00-charter.md) — Scope and success criteria
> - [Options](./25-options.md) — Governance-selected option
> - [Tasks](./40-tasks.md) — Implementation checklist

Last Updated: 2026-03-20
