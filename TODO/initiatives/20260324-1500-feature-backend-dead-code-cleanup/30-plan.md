# Plan — Backend Dead Code Cleanup Post-Recovery

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Selected Option**: OPT-1 (3-Phase Risk-Layered)  
**Last Updated**: 2026-03-24

---

## 0. Pre-Execution Baseline

Before any phase begins, capture the current test baseline:

```bash
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short 2>NUL
```

Record: total tests collected, total passed, total failed (if any), total errors.

This baseline is the "before" snapshot. Each phase gate verifies against it.

---

## 1. Phase 1 — Dead Core Modules + Orphan Tests

### 1.1 Scope

Delete 13 dead production files and 21 orphan test files, plus clean up 2 directories that become empty.

### 1.2 Production Files to Delete (13 files, ~3,225 lines)

| # | File | Lines | Replaced By |
|---|------|-------|-------------|
| P1 | `backend/puzzle_manager/trace_registry.py` | ~166 | `core/trace_map.py` |
| P2 | `backend/puzzle_manager/models/trace.py` | ~95 | (only used by trace_registry) |
| P3 | `backend/puzzle_manager/core/shard_key.py` | ~252 | SQLite DB-1/DB-2 |
| P4 | `backend/puzzle_manager/core/shard_models.py` | ~217 | SQLite DB-1/DB-2 |
| P5 | `backend/puzzle_manager/core/shard_writer.py` | ~367 | `core/db_builder.py` |
| P6 | `backend/puzzle_manager/core/snapshot_builder.py` | ~467 | `core/db_builder.py` |
| P7 | `backend/puzzle_manager/core/dedup_registry.py` | ~262 | `core/content_db.canonical_position_hash()` |
| P8 | `backend/puzzle_manager/maintenance/views.py` | ~166 | SQLite DB-1 |
| P9 | `backend/puzzle_manager/maintenance/migrate_sharding.py` | ~346 | (one-shot migration, completed) |
| P10 | `backend/puzzle_manager/runtime.py` | ~118 | `paths.py` |
| P11 | `backend/puzzle_manager/logging.py` | ~194 | `pm_logging.py` |
| P12 | `backend/puzzle_manager/core/level_mapper.py` | ~422 | `core/classifier.py` |
| P13 | `backend/puzzle_manager/core/position_fingerprint.py` | ~153 | `core/content_db.canonical_position_hash()` |

### 1.3 Orphan Test Files to Delete (21 files, ~5,163 lines)

| # | File | Tests Dead Module(s) |
|---|------|---------------------|
| T1 | `tests/test_cli_trace.py` (~331 lines) | trace_registry, models.trace |
| T2 | `tests/unit/test_trace_registry.py` (~847 lines) | trace_registry, models.trace |
| T3 | `tests/test_trace_registry.py` (~495 lines) | trace_registry, models.trace |
| T4 | `tests/models/test_trace.py` (~303 lines) | models.trace |
| T5 | `tests/unit/test_shard_key.py` (~164 lines) | core.shard_key |
| T6 | `tests/unit/test_shard_models.py` (~234 lines) | core.shard_models |
| T7 | `tests/unit/test_shard_writer.py` (~360 lines) | core.shard_writer |
| T8 | `tests/unit/test_shard_labels.py` (~178 lines) | core.shard_writer, core.shard_models |
| T9 | `tests/unit/test_shard_writer_n_assignment.py` (~165 lines) | core.shard_writer |
| T10 | `tests/unit/test_compact_json_format.py` (~109 lines) | core.snapshot_builder |
| T11 | `tests/unit/test_snapshot_entry_reconstruction.py` (~10 lines) | core.shard_models, core.snapshot_builder |
| T12 | `tests/integration/test_snapshot_builder.py` (~253 lines) | core.shard_models, core.snapshot_builder |
| T13 | `tests/integration/test_publish_snapshot_wiring.py` (~300 lines) | core.shard_models, core.snapshot_builder |
| T14 | `tests/integration/test_snapshot_rollback.py` (~198 lines) | core.shard_models, core.snapshot_builder |
| T15 | `tests/unit/test_dedup_registry.py` (~162 lines) | core.dedup_registry |
| T16 | `tests/unit/test_dedup_metadata_merge.py` (~387 lines) | core.dedup_registry |
| T17 | `tests/unit/test_migrate_sharding.py` (~276 lines) | maintenance.migrate_sharding |
| T18 | `tests/unit/test_runtime.py` (~184 lines) | runtime (RuntimePaths) |
| T19 | `tests/unit/test_level_mapper.py` (~281 lines) | core.level_mapper |
| T20 | `tests/unit/test_position_fingerprint.py` (~222 lines) | core.position_fingerprint |
| T21 | `tests/test_adapters.py` (~65 lines) | adapters.base, adapters.registry (old infra) |

> **Note**: T21 tests the old adapter infra (`adapters.base`, `adapters.registry`). It's co-deleted in Phase 1 because the test file imports only dead modules. The adapter files themselves are deleted in Phase 2.

### 1.4 Directory Cleanup

| Directory | Action | Reason |
|-----------|--------|--------|
| `backend/puzzle_manager/maintenance/` | Delete entire directory (including `__init__.py`) | Only contained `views.py` + `migrate_sharding.py` (both dead). `__init__.py` has only a docstring. Zero production imports of `maintenance`. |
| `backend/puzzle_manager/tests/models/` | Delete entire directory (including `__init__.py`) | Only contained `test_trace.py` (orphan). No other test files. |

### 1.5 Verification Gate

```bash
# 1. Run test suite — expect FEWER tests collected (orphan tests removed) but ZERO failures
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short

# 2. Verify deleted files are gone
ls backend/puzzle_manager/trace_registry.py 2>/dev/null && echo "FAIL" || echo "OK"
ls backend/puzzle_manager/core/shard_key.py 2>/dev/null && echo "FAIL" || echo "OK"
# ... (all 13 production files)

# 3. Verify no remaining imports of dead modules
grep -r "from backend.puzzle_manager.trace_registry" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.shard_key" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.shard_models" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.shard_writer" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.snapshot_builder" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.dedup_registry" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.runtime import" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.logging import" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.level_mapper" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
grep -r "from backend.puzzle_manager.core.position_fingerprint" backend/puzzle_manager/ --include="*.py" | grep -v __pycache__
# All should return empty

# 4. Lint check
ruff check backend/puzzle_manager/
```

### 1.6 Expected Test Delta

- **Tests collected**: Decrease by ~21 files worth of tests (orphan tests no longer collected)
- **Tests passed**: All remaining tests pass (zero failures)
- **Tests failed**: Zero. No production code changed.

---

## 2. Phase 2 — Adapter Cleanup

### 2.1 Scope

Delete old adapter infrastructure, all orphaned/duplicate flat-file adapters, ghost directory, and edit `adapters/__init__.py`.

### 2.2 Files to Delete (14 files + 1 directory)

| # | File | Lines | Status |
|---|------|-------|--------|
| A1 | `adapters/base.py` | ~125 | Old infra, replaced by `_base.py` |
| A2 | `adapters/registry.py` | ~160 | Old infra, replaced by `_registry.py` |
| A3 | `adapters/blacktoplay.py` | ~115 | Orphaned (old registry only) |
| A4 | `adapters/gogameguru.py` | ~70 | Orphaned (old registry only) |
| A5 | `adapters/goproblems.py` | ~70 | Orphaned (old registry only) |
| A6 | `adapters/ogs.py` | ~987 | Orphaned (ghost `ogs/` dir exists) |
| A7 | `adapters/ogs_converter.py` | ~407 | Helper for dead ogs.py |
| A8 | `adapters/ogs_models.py` | ~124 | Helper for dead ogs.py |
| A9 | `adapters/ogs_translator.py` | ~184 | Helper for dead ogs.py |
| A10 | `adapters/kisvadim.py` | ~130 | Duplicate of `kisvadim/adapter.py` |
| A11 | `adapters/sanderland.py` | ~196 | Duplicate of `sanderland/adapter.py` |
| A12 | `adapters/travisgk.py` | ~107 | Duplicate of `travisgk/adapter.py` |
| A13 | `adapters/local.py` | ~151 | Duplicate of `local/adapter.py` |
| A14 | `adapters/url.py` | ~141 | Orphaned (no subdir version) |
| A15 | `adapters/ogs/` (directory) | 0 | Ghost directory with only `__pycache__` |

### 2.3 File to Edit: `adapters/__init__.py`

**Current content (lines 26-30)**:
```python
from backend.puzzle_manager.adapters.local import LocalAdapter
from backend.puzzle_manager.adapters.url import UrlAdapter
from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter
from backend.puzzle_manager.adapters.travisgk import TravisGKAdapter
from backend.puzzle_manager.adapters.kisvadim import KisvadimAdapter
```

**Target content (remove `url` import, keep others)**:
```python
from backend.puzzle_manager.adapters.local import LocalAdapter
from backend.puzzle_manager.adapters.sanderland import SanderlandAdapter
from backend.puzzle_manager.adapters.travisgk import TravisGKAdapter
from backend.puzzle_manager.adapters.kisvadim import KisvadimAdapter
```

**Also edit `__all__` list**: Remove `"UrlAdapter"` entry.

**Python package-vs-module resolution note** (RC-2): When both `local.py` (module) and `local/` (package) exist, Python resolves the package first. After deleting `local.py`, the import `from backend.puzzle_manager.adapters.local import LocalAdapter` continues to work because it resolves to `local/__init__.py` → `local/adapter.py`. Same for `sanderland`, `travisgk`, `kisvadim`. Only `url.py` has no package counterpart, hence the `__init__.py` edit.

### 2.4 Verification Gate

```bash
# 1. Test suite — same test count as post-Phase-1, zero failures
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short

# 2. Adapter discovery — must list only live adapters
python -m backend.puzzle_manager sources

# 3. Verify __init__.py has no UrlAdapter reference
grep -n "UrlAdapter" backend/puzzle_manager/adapters/__init__.py
# Should return empty

# 4. Verify flat files are gone
ls backend/puzzle_manager/adapters/base.py 2>/dev/null && echo "FAIL" || echo "OK"
ls backend/puzzle_manager/adapters/registry.py 2>/dev/null && echo "FAIL" || echo "OK"
ls backend/puzzle_manager/adapters/url.py 2>/dev/null && echo "FAIL" || echo "OK"
# ... (all 14 files)

# 5. Verify ghost directory is gone
ls -d backend/puzzle_manager/adapters/ogs/ 2>/dev/null && echo "FAIL" || echo "OK"

# 6. Lint check
ruff check backend/puzzle_manager/
```

### 2.5 Expected Test Delta

- **Tests collected**: Same as post-Phase-1 (T21 `test_adapters.py` was already deleted in Phase 1)
- **Tests passed**: All remaining tests pass (zero failures)
- **Tests failed**: Zero. Production `__init__.py` edit only removes import of dead module.

---

## 3. Phase 3 — Vestigial Code + Documentation

### 3.1 Code Edit: Remove `views_dir` Property

**File**: `backend/puzzle_manager/stages/protocol.py`  
**Lines 65-68**:
```python
@property
def views_dir(self) -> Path:
    """Get views output directory (output_dir/views/)."""
    return self.output_dir / "views"
```

**Action**: Delete these 4 lines.

### 3.2 Docs to Delete (2 files)

| # | File | Action |
|---|------|--------|
| D1 | `docs/architecture/backend/view-index-pagination.md` | Delete (duplicate of archive) |
| D2 | `docs/STAGES.md` | Delete (massively outdated, per Q8:A) |

### 3.3 Docs to Move to Archive (3 files)

| # | File | Target |
|---|------|--------|
| D3 | `docs/architecture/backend/view-index-segmentation.md` | `docs/archive/` |
| D4 | `docs/architecture/snapshot-deployment-topology.md` | `docs/archive/` |
| D5 | `docs/concepts/snapshot-shard-terminology.md` | `docs/archive/` |

### 3.4 Docs to Fix (Stale Content — Critical)

| # | File | Issue | Fix |
|---|------|-------|-----|
| D6 | `backend/puzzle_manager/AGENTS.md` | Says "Typer CLI" (lines 26, 175) | Change to "argparse" |
| D7 | `backend/puzzle_manager/AGENTS.md` | References `adapters/url/` ghost directory | Remove reference |
| D8 | `backend/puzzle_manager/AGENTS.md` | Dependency table lists `typer` | Remove `typer` entry |
| D9 | `docs/how-to/backend/create-adapter.md` | References old `base.py`/`registry.py` | Update to `_base.py`/`_registry.py` |
| D10 | `docs/architecture/backend/pipeline-architecture.md` | May reference shard/snapshot system | Remove stale references |
| D11 | `docs/concepts/sgf-custom-properties.md` | May reference old schema versions | Verify against current schema v15 |
| D12 | `docs/getting-started/quickstart.md` | May reference obsolete commands | Verify against current CLI |
| D13 | `docs/reference/adapters/` | May reference deleted adapters | Remove stale adapter entries |
| D14 | `docs/guides/adapter-development.md` | Consolidate or redirect per Q9:C/B | Simplify or delete, redirect to how-to |

> **Note**: D10-D14 require targeted content review during execution. The executor should read each file and make only the stale content fixes, not full rewrites.

### 3.5 Verification Gate

```bash
# 1. Test suite — same as post-Phase-2, zero failures
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short

# 2. Verify views_dir removed
grep -n "views_dir" backend/puzzle_manager/stages/protocol.py
# Should return empty

# 3. Verify AGENTS.md accuracy
grep -ni "typer" backend/puzzle_manager/AGENTS.md
# Should return empty

# 4. Verify deleted docs are gone
ls docs/STAGES.md 2>/dev/null && echo "FAIL" || echo "OK"
ls docs/architecture/backend/view-index-pagination.md 2>/dev/null && echo "FAIL" || echo "OK"

# 5. Lint check
ruff check backend/puzzle_manager/
```

### 3.6 Expected Test Delta

- **Tests collected**: Same as post-Phase-2 (no test files changed)
- **Tests passed**: All remaining tests pass
- **Tests failed**: Zero. `views_dir` is unused.

---

## 4. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| R-1: Hidden import of dead module breaks collection | Very Low | High (test failure) | All dead modules verified via grep — zero production imports |
| R-2: `__init__.py` edit breaks adapter discovery | Low | High (pipeline fails) | Phase 2 gate explicitly validates `sources` command |
| R-3: Orphan test imports a live module too | Low | Medium (wrong test deleted) | Each orphan test verified — imports only dead modules |
| R-4: `maintenance/` directory deletion breaks import | Very Low | Medium | Verified zero imports of `maintenance` package |
| R-5: Flat-file adapter deletion changes Python resolution | Very Low | High | Package-vs-module resolution verified for all 4 duplicates |
| R-6: Doc fix introduces incorrect information | Low | Low | Code review of each doc edit against source code |

---

## 5. Rollback Strategy

Each phase is committed as a separate git branch. Rollback is:

```bash
# If Phase N fails:
git log --oneline -5  # Find commit before Phase N
git checkout -b rollback/phase-N HEAD~1  # Create rollback branch
# Verify tests pass on rollback branch
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short
```

No destructive git commands needed. Each phase is independently reversible.

---

## 6. Documentation Plan

### Files to Update

| File | Why Updated | Phase |
|------|-------------|-------|
| `backend/puzzle_manager/AGENTS.md` | Fix "Typer"→"argparse", remove `url/` ghost ref, remove `typer` dep | Phase 3 |
| `docs/how-to/backend/create-adapter.md` | Update `base.py`→`_base.py` references | Phase 3 |
| `docs/architecture/backend/pipeline-architecture.md` | Remove shard/snapshot references | Phase 3 |
| `docs/guides/adapter-development.md` | Consolidate/simplify or redirect | Phase 3 |

### Files to Create

None. (Initiative artifacts don't count.)

### Files to Delete

| File | Why | Phase |
|------|-----|-------|
| `docs/architecture/backend/view-index-pagination.md` | Obsolete (duplicate of archive) | Phase 3 |
| `docs/STAGES.md` | Massively outdated | Phase 3 |

### Files to Move

| File | Target | Phase |
|------|--------|-------|
| `docs/architecture/backend/view-index-segmentation.md` | `docs/archive/` | Phase 3 |
| `docs/architecture/snapshot-deployment-topology.md` | `docs/archive/` | Phase 3 |
| `docs/concepts/snapshot-shard-terminology.md` | `docs/archive/` | Phase 3 |

### Cross-References

- `docs/concepts/sqlite-index-architecture.md` — canonical replacement for shard/snapshot docs
- `docs/concepts/numeric-id-scheme.md` — ID scheme reference
- `backend/puzzle_manager/AGENTS.md` — agent-facing architecture map (must reflect actual code)

---

## 7. Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| AD-1: Delete `maintenance/` directory entirely | Zero production imports. Only contained dead modules. `__init__.py` had only a docstring. |
| AD-2: Delete `tests/models/` directory entirely | Only contained `test_trace.py` (orphan). `models/` production directory retains 6 live files. |
| AD-3: Keep `models/trace.py` deletion in Phase 1 (not Phase 2) | It's a core model used by `trace_registry.py`, not an adapter. Semantically belongs with core module cleanup. |
| AD-4: Delete T21 (`test_adapters.py`) in Phase 1 | Despite testing adapter infrastructure, it imports only from dead `adapters.base`/`adapters.registry`. Co-deleting prevents the orphan-after-source problem. |
| AD-5: Archive 3 docs vs delete | Snapshot/segmentation docs have historical value for understanding past architecture. Archive per community convention. |
| AD-6: Edit `__init__.py` only for `UrlAdapter` | Other flat-file imports (local, sanderland, travisgk, kisvadim) resolve to their package counterparts automatically. Only `url` has no package. |

---

## 8. Constraints Recap

From governance must-hold constraints:
1. ✅ Phase 1 co-deletes orphan tests with source modules
2. ✅ Phase 2 edits `__init__.py` in same phase as `url.py` deletion
3. ✅ Each phase runs `pytest backend/ -m "not (cli or slow)"` gate
4. ✅ Phase 2 validates `python -m backend.puzzle_manager sources`
