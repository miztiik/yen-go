# Options — Enrichment Lab Test Audit (Phase 2)

> Last Updated: 2026-03-24

## User Decisions

- **Q2 = A**: Delete `test_feature_activation.py` entirely (overrides governance recommendation to keep C9 guards)
- **Q5 = B**: Merge config test files into 2 files (loading + values)

---

## Option Comparison

| Dimension | OPT-1: Phased Consolidation (Conservative) | OPT-2: Aggressive Merge (Single Pass) |
|-----------|---------------------------------------------|---------------------------------------|
| **Approach** | 4 independent phases, each with its own commit and validation gate. Phase 1 (duplicate deletion) can be fast-tracked immediately. | All changes in 1-2 commits: delete duplicates + consolidate all files simultaneously. |
| **Phases** | Phase 1: Delete 4 duplicates. Phase 2: Delete feature_activation. Phase 3: Merge refutation phases. Phase 4: Merge config files. | Single batch: all deletions + merges + tasks.json update. |
| **Risk** | Minimal — each phase independently validatable | Medium — large diff, harder to bisect if tests break |
| **Rollback** | Per-commit revert | Must revert entire batch |
| **Timeline** | 4 distinct validation points | 1 validation point |
| **Files deleted** | 4 (Phase 1) + 1 (Phase 2) = 5 | 5 |
| **Files merged** | 3→1 (Phase 3) + 6→2 (Phase 4) = 9→3 | Same: 9→3 |
| **Final file count** | 84 → 72 | 84 → 72 |
| **Lines saved** | ~3,500 | ~3,500 |
| **Config snapshot tests** | Deleted in Phase 2 | Deleted with everything else |
| **C9 threshold guards** | Lost (per Q2=A) | Lost (per Q2=A) |
| **tasks.json update** | Per-phase (Phase 3 commit) | Single commit |

### OPT-1: Phased Consolidation (Conservative)

| OPT-1 | Detail |
|--------|--------|
| **Summary** | Execute 4 independent phases with validation between each. Each phase is a separate commit with `pytest --co -q` count verification. |
| **Benefits** | Easy rollback per phase. Each commit is small and reviewable. Phase 1 is zero-risk and can start immediately. |
| **Drawbacks** | More commits. More validation passes. Takes longer. |
| **Risk** | Low |
| **Test impact** | Zero — each phase preserves all non-duplicate assertions |
| **Rollback** | Per-commit `git revert` |
| **Architecture compliance** | No production code changes |
| **Recommendation** | **Recommended** — matches project's correction-levels.md Level 3 workflow |

### OPT-2: Aggressive Merge (Single Pass)

| OPT-2 | Detail |
|--------|--------|
| **Summary** | Combine all changes into 1-2 commits. Delete, merge, and update tasks.json in one shot. |
| **Benefits** | Faster execution. Cleaner git history (fewer commits). |
| **Drawbacks** | Harder to bisect failures. Large diff to review. If config merge introduces import issues, harder to isolate. |
| **Risk** | Medium |
| **Test impact** | Zero if done correctly, but harder to verify incrementally |
| **Rollback** | Revert entire batch — may lose valid changes |
| **Architecture compliance** | No production code changes |
| **Recommendation** | Acceptable for experienced executor, but not preferred for multi-file refactor |

---

## Recommendation

**OPT-1 (Phased Consolidation)** — Preferred. Matches the project's Level 3 correction workflow (`Plan Mode -> Phased Execution`). Phase 1 is independently safe and provides immediate value (2,238 lines removed, 87 duplicate tests eliminated). Each subsequent phase is low-risk with clear validation gates.
