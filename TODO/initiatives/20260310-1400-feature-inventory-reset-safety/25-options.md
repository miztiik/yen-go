# Options: Inventory Reset Transaction Safety

**Last Updated**: 2026-03-10

## Context

The `cleanup_target("puzzles-collection")` path resets inventory to zero BEFORE writing the audit entry. This creates a window where inventory is zeroed but no audit record exists — the exact scenario observed on 2026-03-09.

## Options Matrix

| ID | Title | Approach | Complexity | Files Changed | Risk |
|----|-------|----------|------------|---------------|------|
| OPT-A | Transaction Safety (Audit-Before-Reset) | Reorder operations: write audit entry first, then reset inventory. If audit fails, inventory preserved. | Low | 1 file (cleanup.py) | Low |
| OPT-B | CLI Confirmation Guard | Add `--confirm-reset-inventory` flag and/or `YENGO_ALLOW_COLLECTION_CLEAN` env var | Medium | 2 files (cli.py, cleanup.py) | Low |
| OPT-C | Auto-Heal on Startup | Detect inventory/disk mismatch on pipeline startup and auto-reconcile | High | 3+ files | Medium |
| OPT-D | Forensic Provenance | Add actor, host, pid, cwd, argv, git SHA to every inventory mutation | Medium-High | 3+ files (manager.py, models.py, cleanup.py) | Low-Medium |

---

### OPT-A: Transaction Safety (Audit-Before-Reset)

**Approach**: Swap the order of operations in `cleanup_target()` so that the audit entry is written BEFORE `_reset_inventory()` is called. Wrap both in a try/except so that if audit write fails, inventory is preserved.

**Benefits**:
- Directly fixes the root cause (inventory zeroed without audit trail)
- Minimal code change (~20-30 lines, single file)
- No interface changes (CLI, schema, models all untouched)
- Easy to test (mock audit write failure → verify inventory preserved)
- Structurally correct: operations happen in dependency order

**Drawbacks**:
- Audit entry may record cleanup that then fails at inventory reset (unlikely but possible)
- Does not prevent the cleanup from being invoked accidentally (existing `--dry-run false` handles this)

**Risks**: Very low. The reorder is a logic fix, not a behavior change.

**Test Impact**: Add 1 regression test. All existing tests continue to pass.

**Rollback**: Trivially revertible (swap two code blocks back).

---

### OPT-B: CLI Confirmation Guard

**Approach**: Add an explicit `--confirm-reset-inventory` flag requirement when targeting puzzles-collection, plus an environment variable `YENGO_ALLOW_COLLECTION_CLEAN` for CI.

**Benefits**:
- Defense-in-depth: additional confirmation before destructive action
- Environment variable allows CI automation

**Drawbacks**:
- `--dry-run false` already serves as the confirmation gate
- Adds CLI complexity for a case that already requires explicit opt-in
- Does NOT fix the root cause (audit/reset ordering)
- User explicitly stated this is unnecessary: "we already have some hardening with --dry-run false"

**Risks**: Low technical risk, but over-engineering risk.

**Test Impact**: Update CLI tests, add new tests for flag parsing.

---

### OPT-C: Auto-Heal on Startup

**Approach**: On pipeline startup, detect inventory/disk count mismatch and trigger automatic reconciliation.

**Benefits**:
- Self-healing: system recovers automatically from any state corruption
- Catches issues regardless of cause

**Drawbacks**:
- Adds startup latency (disk scan)
- Hides problems rather than preventing them
- Significant implementation effort (3+ files, startup hooks)
- User explicitly deferred this: "let us not complicate things"

**Risks**: Medium — could mask other bugs if reconciliation runs silently.

---

### OPT-D: Forensic Provenance

**Approach**: Add metadata (actor, hostname, PID, working directory, CLI args, git SHA) to every inventory mutation.

**Benefits**:
- Makes future forensic investigations trivial
- Provides full audit trail for all mutations

**Drawbacks**:
- Model schema change required (new fields in inventory/audit)
- Multiple files changed (models.py, manager.py, cleanup.py, audit.py)
- Does NOT fix the root cause (audit/reset ordering still wrong)
- Better as a separate enhancement

**Risks**: Low-Medium. Schema evolution required.

---

## Evaluation Summary

| Criterion | OPT-A | OPT-B | OPT-C | OPT-D |
|-----------|-------|-------|-------|-------|
| Fixes root cause | ✅ Yes | ❌ No | ❌ No (masks) | ❌ No |
| Simplicity | ✅ ~20 lines, 1 file | ⚠️ 2 files | ❌ 3+ files | ⚠️ 3+ files |
| User preference | ✅ Preferred | ❌ Declined | ❌ Deferred | ❌ Deferred |
| Structural fix | ✅ Dependency ordering | ⚠️ Defense layer | ⚠️ Recovery | ⚠️ Observability |
| Interface change | ✅ None | ❌ CLI flag | ❌ Startup hook | ❌ Schema |
| Can stand alone | ✅ Yes | ❌ Needs OPT-A too | ❌ Needs OPT-A too | ❌ Needs OPT-A too |

## Recommendation

**OPT-A** is the clear structural winner. It directly addresses the root cause with minimal change, no interface evolution, and easy testability. Options B/C/D may have value as separate follow-up initiatives but none of them fix the actual bug — they're layered protections that only matter if OPT-A isn't done.

> **See also**:
> - [Charter](./00-charter.md) — Problem statement and goals
> - [Clarifications](./10-clarifications.md) — User decisions on scope
