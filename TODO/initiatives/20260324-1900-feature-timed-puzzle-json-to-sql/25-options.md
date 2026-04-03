# Options — Timed Puzzle JSON-to-SQL Migration

**Initiative**: `20260324-1900-feature-timed-puzzle-json-to-sql`
**Last Updated**: 2026-03-24
**Planning Confidence Score**: 92
**Risk Level**: low

---

## Options Table

| Field | OPT-1: Single-Commit Deletion | OPT-2: Phased Deletion (2 commits) |
|-------|-------------------------------|-------------------------------------|
| **Title** | Atomic cleanup | Two-phase cleanup |
| **Approach** | Delete all 7 files, edit all 5 files, update AGENTS.md in a single commit. Run `tsc --noEmit` + `vitest run` once. | Phase 1: Delete D1-D7 files only. Phase 2: Edit E1-E5 files + AGENTS.md update. Two separate commits with verification between. |
| **Benefits** | Simplest execution. One commit = one revert if needed. Fewer test runs. Atomically consistent codebase. | Isolates file deletion risk from edit risk. If E3 (interface field removal) causes unexpected TS errors, D1-D7 deletion is already safe. |
| **Drawbacks** | Single larger commit. If any edit fails TS check, must debug both deletions and edits together. | More overhead (2x test runs, 2 commits). Intermediate state has vestigial references (stale comments, dead types) which is mildly untidy. |
| **Risks** | Low — all files have 0 consumers, so deletion cannot break TS. Edits are well-scoped. | Very low — phase 1 is pure deletion of 0-consumer files. Phase 2 is cleanup. |
| **Complexity** | Low | Low (marginally more process overhead) |
| **Test Impact** | 1 vitest + 1 tsc run | 2 vitest + 2 tsc runs |
| **Rollback** | `git revert <commit>` — single operation | `git revert <phase-2>` or `git revert <phase-1>..<phase-2>` — slightly more complex |
| **Architecture compliance** | ✅ Dead code policy, AGENTS.md sync | ✅ Dead code policy, AGENTS.md sync |
| **Recommendation** | **★ Recommended** | Viable alternative |

---

## Recommendation Rationale

**OPT-1** is recommended because:

1. **All 7 files have 0 active consumers** — deletion is risk-free. There is no scenario where Phase 1 succeeds but Phase 2 fails in a way that phasing would have caught.
2. **The edits (E1-E5) are trivial** — removing a comment, an interface field, vestigial strings, and orphan types. These do not benefit from separate verification.
3. **Single-commit semantics** align with the project's "dead code policy: delete, don't deprecate" and simplify rollback.
4. **Phasing adds process overhead** with no meaningful risk reduction for this specific initiative's scope.
