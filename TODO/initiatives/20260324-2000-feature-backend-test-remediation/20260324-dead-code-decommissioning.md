# Dead Code Decommissioning Reference

> **Purpose:** Reference artifact for future coding agents to clean up dead code paths identified during the backend test remediation initiative (20260324-2000-feature-backend-test-remediation).

---

## Dead Code Paths

### 1. Trace Map Module (High Priority)

| Item | Detail |
|------|--------|
| **File** | `backend/puzzle_manager/core/trace_map.py` |
| **Functions** | `write_trace_map()`, `read_trace_map()` |
| **Status** | Zero callers in production code |
| **Reason** | Trace data migrated to inline `YM` SGF property (schema v12+). Sidecar `.trace-map-*.json` files are no longer produced or consumed. |
| **Action** | Delete entire module. Remove from `core/__init__.py` if re-exported. |
| **Risk** | None — no import paths reference it in stages/. |
| **Verification** | `grep -r "trace_map" backend/puzzle_manager/stages/` should return 0 hits. |

### 2. Documentation References to Trace Map Sidecars

| Item | Detail |
|------|--------|
| **Files** | `docs/architecture/backend/integrity.md`, possibly `docs/architecture/backend/inventory-operations.md` |
| **Status** | Reference sidecar-based trace map architecture that no longer exists |
| **Action** | Update docs to describe current YM-based tracing, or remove stale sidecar sections. |
| **Risk** | Low — informational only, but misleading for new contributors. |

### 3. Potential Unused Imports

| Item | Detail |
|------|--------|
| **Scope** | Any file importing from `core.trace_map` |
| **Action** | After deleting the module, run `ruff check backend/puzzle_manager/` to catch broken imports. |
| **Verification** | `grep -r "from.*trace_map import\|import.*trace_map" backend/` |

---

## Discovery Context

- **Source initiative:** `TODO/initiatives/20260324-2000-feature-backend-test-remediation/`
- **Evidence:** CR-BETA confirmed `trace_map.py` safe to decommission. 7 sidecar tests deleted (T4, T5) as part of remediation.
- **Code reviewers:** Both CR-ALPHA and CR-BETA agreed on decommissioning.

---

## Cleanup Checklist

- [ ] Delete `backend/puzzle_manager/core/trace_map.py`
- [ ] Remove any re-exports from `core/__init__.py`
- [ ] Update `docs/architecture/backend/integrity.md` — remove sidecar trace map references
- [ ] Update `docs/architecture/backend/inventory-operations.md` if it references trace maps
- [ ] Run `ruff check backend/puzzle_manager/` to verify no broken imports
- [ ] Run `pytest backend/ -m unit -q --no-header --tb=short` to verify no test breakage
- [ ] Update `backend/puzzle_manager/AGENTS.md` if trace_map is mentioned in architecture map

---

## Inventory Check Production Gaps (Medium Priority)

| Item | Detail |
|------|--------|
| **File** | `backend/puzzle_manager/inventory/check.py` |
| **Issue** | `check_integrity()` only invalidates on orphan entries. Does not verify `total_puzzles` or `by_puzzle_level` count mismatches (Spec 107 FR-018, FR-019). |
| **Tests affected** | 3 tests in `test_inventory_check.py` (`test_detects_total_mismatch`, `test_detects_level_mismatch`, `test_fix_flag_calls_rebuild`) |
| **Action** | Implement FR-018/FR-019 validation in `check_integrity()` as a separate initiative. |
| **Risk** | Low — inventory check is a diagnostic tool, not in the publish pipeline critical path. |

_Created: 2026-03-24_
