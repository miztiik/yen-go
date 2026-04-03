# Governance Decisions

**Last Updated**: 2026-03-30

---

## Initiative History

This initiative supersedes `20260330-1400-feature-cross-source-collection-editions` which went through 8 governance rounds, grew to 32 tasks, and was found to be over-engineered (simplicity score: 38/100).

Key learnings from the old initiative:
- Runtime detection is correct approach (not config-defined editions) — scales to 1000+ collections
- Auto-best / richness scoring is YAGNI — defer to v2
- All collection types should be treated identically — no type-based branching
- Add `collection_slug` to content DB for efficient collision detection via SQL
- Shared utility for publish + rollback — prevents permanent interleaving after rollback

## Round 1: Plan Review

- **Date**: 2026-03-30
- **Score**: 87/100 → fixed to 95+ (5 RCs resolved)
- **Decision**: `approve_with_conditions` → all conditions met
- **Status**: `GOV-PLAN-APPROVED`

### Issues Found & Fixed

| RC | Severity | Issue | Fix |
|----|----------|-------|-----|
| RC-1 | High | Regex `[^\]:]+` doesn't stop at commas — captures `"a,b"` instead of `"a"` | Changed to `[^\]:,]+` |
| RC-2 | High | Caller location wrong (`_process_puzzle` → should be `run()` line ~128) | Fixed in plan §3 and T5 |
| RC-3 | Medium | Plan converted `@staticmethod` to instance method — breaks test calling | Kept `@staticmethod`, removed `self` |
| RC-4 | Medium | `getAllCollections()` missing from query audit | Added full query checklist to T17 |
| RC-5 | Medium | Rollback fix vague | T13 specifies: delete `db_path.unlink()` at line ~246 |

### KISS/SOLID/DRY Scores

| Principle | Score |
|-----------|:-----:|
| KISS | 9/10 |
| SRP | 10/10 |
| OCP | 9/10 |
| DRY | 10/10 |
| YAGNI | 10/10 |
| DI | 9/10 |

### Panel Votes

7 approve, 2 concern (both resolved via RCs). No change_requested.

---

## Round 2: Implementation Review

- **Date**: 2026-03-30
- **Decision**: `approve`
- **Status**: `GOV-REVIEW-APPROVED`
- **Unanimous**: Yes (9/9)

### Summary

All 22 tasks executed per approved plan. No scope expansion. 24 new tests + 5 updated across 4 new + 2 modified test files. All backend (1594 unit + 2388 integration) and frontend (37 relevant) tests green. Documentation updated (T19-T22). Ruff lint clean.

### Member Votes

| ID | Member | Domain | Vote |
|----|--------|--------|------|
| GV-1 | Cho Chikun (9p) | Tsumego & Go domain | approve |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve |
| GV-4 | Principal Staff Engineer A | Systems architect | approve |
| GV-5 | Principal Staff Engineer B | Data pipeline | approve |
| GV-6 | Hana Park (1p) | Player experience | approve |
| GV-7 | Mika Chen | DevTools UX | approve |
| GV-8 | Dr. David Wu | KataGo/MCTS | approve |
| GV-9 | Dr. Shin Jinseo | Tsumego correctness | approve |

### Minor Findings (Non-Blocking, Recommended for v1.1)

| ID | Finding | Recommendation |
|----|---------|----------------|
| CRA-1 | `assert eid not in config_ids` can be stripped by `-O` | Convert to `ValueError` |
| CRA-2 | `window.location.hash` coupling in EditionPicker | Use router navigation |
| CRB-1 | Lazy imports in publish.py/rollback.py | Move to top-level |
| F4 | Progress orphaning on edition split | Add progress migration utility |

### Handover

- **from**: Governance-Panel
- **to**: Plan-Executor
- **required_next_actions**: Update status.json, prepare closeout audit
- **blocking_items**: None

---

## Round 3: Closeout Audit

- **Date**: 2026-03-30
- **Decision**: `approve_with_conditions` → condition resolved
- **Status**: `GOV-CLOSEOUT-APPROVED`
- **Unanimous**: Yes (9/9)

### Closure Verification

| Gate | Status |
|------|--------|
| Artifact completeness (9/9) | ✅ |
| Scope completion (22/22 tasks) | ✅ |
| Tests pass (24 new + 5 updated) | ✅ |
| Documentation updated (T19-T22) | ✅ |
| Implementation review passed | ✅ |
| No unresolved blockers | ✅ |
| Superseded initiative documented | ✅ |

### Condition Resolved

| RC | Issue | Resolution |
|----|-------|------------|
| RC-1 | Missing reverse cross-reference in sqlite-index-architecture.md | Added `See also: Collection Editions` link in Edition Sub-Collections section |

### v1.1 Backlog (Non-Blocking)

| ID | Item |
|----|------|
| CRA-1 | Convert `assert eid not in config_ids` to `ValueError` |
| CRA-2 | Use router navigation instead of `window.location.hash` |
| CRB-1 | Move lazy imports to top-level |
| F4 | Add progress migration utility for edition splits |
