# Clarifications — Mark Sibling Refutations

> Initiative: `20260321-1000-feature-mark-sibling-refutations`
> Last Updated: 2026-03-21

## Clarification Table

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Scope of "sub-variation" — first-move depth only, or all depths? | A: First-move depth only / B: First two depths / C: All player-move depths recursively | C — the pattern occurs at all depths, not just first-move. Opponent-response nodes don't have correctness semantics. | **C: All player-move depths recursively** | ✅ resolved |
| Q2 | How to handle miai edge case (2+ genuinely correct alternatives)? | A: Always mark None siblings as wrong / B: Skip nodes where 2+ siblings are already marked correct / C: Require KataGo confirmation | B — only mark `None` siblings as wrong when exactly 1 sibling at that depth is explicitly correct. Safe, avoids false positives. | **B: Skip when 2+ siblings marked correct** | ✅ resolved |
| Q3 | Should YQ refutation count (rc) and YR be updated? | A: Yes, metrics update automatically / B: No, leave metrics alone | A — downstream `count_refutation_moves()` and `compute_avg_refutation_depth()` already depend on `is_correct` values. Fixing correctness first means metrics improve automatically. | **A: Yes, automatic via existing dependency** | ✅ resolved |
| Q4 | Correction Level? | A: Level 2 (Medium Single) / B: Level 3 (Multiple Files) / C: Level 4 (Large Scale) | B — 2-3 files, touches pipeline logic + tests + frontend test, affects ~25% of corpus. Not Level 4 since no architectural changes. | **B: Level 3** | ✅ resolved |
| Q5 | Where should the heuristic live? | A: Inline in analyze.py / B: Separate `mark_sibling_refutations()` in `core/correctness.py` / C: New file `core/sibling_marker.py` | B — clean SRP. Correctness logic belongs in correctness.py. Called from analyze stage. | **B: `mark_sibling_refutations()` in `core/correctness.py`** | ✅ resolved |
| Q6 | Is backward compatibility required, and should old code be removed? | A: Yes, backward compat required / B: No, this is a bug fix — update in place / C: Keep old code path as fallback | B — the old behavior (unmarked wrong moves accepted as correct) is a bug, not a feature. No deprecated path exists. | **B: Not required, no removal needed (additive)** | ✅ resolved |

## Resolution Summary

All 6 clarification questions are resolved. Key decisions:

1. **Recursive all-depth scope** — the heuristic walks the entire solution tree, not just first-move children.
2. **Miai guard** — when ≥2 siblings at a given depth already have `is_correct=True`, `None` siblings are left unchanged (avoids false positives on puzzles with multiple correct answers).
3. **Automatic metric updates** — no additional work needed; `count_refutation_moves()` and `compute_avg_refutation_depth()` already read `is_correct`.
4. **Level 3 correction** — 2-3 files modified, pipeline logic + tests + frontend test.
5. **`core/correctness.py`** — single function added, following SRP and existing module cohesion.
6. **No backward compatibility needed** — additive fix, no legacy code to remove.
