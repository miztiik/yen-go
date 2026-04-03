# Research Brief: Backend Cleanup Post-Recovery — Dead Code, Duplication, and Architectural Drift

**Date**: 2026-03-24  
**Researcher**: Feature-Researcher agent  
**Status**: research_completed  

---

## 1. Research Question and Boundaries

**Question**: What dead code, duplicate modules, and architectural violations exist in `backend/puzzle_manager/` after the repository recovery incident?

**Scope**: Read-only audit of production code reachability, adapter registry integrity, and module duplication. Limited to `backend/puzzle_manager/` and its test files.

**Out of scope**: Frontend, tools/, config changes, runtime fix implementation.

---

## 2. Dead Code Inventory

### 2.1 Confirmed Dead Production Code (zero production imports)

| R-1 | File | Lines | Evidence | Orphan Test Files | Test Lines |
|-----|------|-------|----------|-------------------|------------|
| R-1 | `trace_registry.py` | 166 | Only imported by 3 test files. `core/trace_map.py` docstring explicitly says "Replaces the heavy trace registry". No production stage/pipeline/cli imports. | `tests/test_cli_trace.py`, `tests/test_trace_registry.py`, `tests/unit/test_trace_registry.py` | 1,670 |
| R-2 | `models/trace.py` | 95 | Only imported by `trace_registry.py` and 4 test files. No production code uses `TraceEntry` or `TraceStatus`. | `tests/models/test_trace.py` | 303 |
| R-3 | `core/shard_key.py` | 252 | Only imported by `shard_writer.py`, `snapshot_builder.py` (both dead), and tests. SQLite DB replaced the shard system. | `tests/unit/test_shard_key.py`, `tests/unit/test_shard_labels.py` | 503 |
| R-4 | `core/shard_models.py` | 217 | Only imported by other shard/snapshot files and tests. | `tests/unit/test_shard_models.py` | 217 |
| R-5 | `core/shard_writer.py` | 367 | Only imported by `snapshot_builder.py` (dead) and tests. `stages/publish.py` uses `core/db_builder.py` instead. | `tests/unit/test_shard_writer.py`, `tests/unit/test_shard_writer_n_assignment.py` | 518 |
| R-6 | `core/snapshot_builder.py` | 467 | Only imported by tests. Depends on shard_key, shard_models, shard_writer (all dead). | `tests/unit/test_snapshot_entry_reconstruction.py`, `tests/unit/test_compact_json_format.py`, `tests/integration/test_publish_snapshot_wiring.py`, `tests/integration/test_snapshot_builder.py`, `tests/integration/test_snapshot_rollback.py` | 980 |
| R-7 | `core/dedup_registry.py` | 262 | Only imported by 2 test files. Production dedup uses `core/content_db.canonical_position_hash()` and inline SQLite queries in `stages/ingest.py` and `stages/publish.py`. | `tests/unit/test_dedup_registry.py`, `tests/unit/test_dedup_metadata_merge.py` | 543 |
| R-8 | `maintenance/views.py` | 166 | Zero production imports. JSON view index system replaced by SQLite DB-1. | (none found) | 0 |
| R-9 | `maintenance/migrate_sharding.py` | 346 | Only imported by 1 test file. References `maintenance/views.py` (dead). One-shot migration script, no longer needed. | `tests/unit/test_migrate_sharding.py` | 275 |
| R-10 | `runtime.py` | 118 | `docs/archive/di-test-isolation.md` explicitly states "The `RuntimePaths` class was deleted." Yet the file still exists. Only imported by its own docstring and 1 test file. Production path resolution now in `paths.py`. | `tests/unit/test_runtime.py` | 184 |
| R-11 | `logging.py` | 194 | Zero imports anywhere (not even tests). `pm_logging.py` is the canonical logging module used by all production code. Name shadows Python's built-in `logging` module. | (none) | 0 |
| R-12 | `core/level_mapper.py` | 422 | Only imported by its own docstring examples and 1 test file. No production code uses it. OGS adapter has its own `LevelMapper` class in `ogs_converter.py`. Adapters use `core/classifier.py` for difficulty assignment. | `tests/unit/test_level_mapper.py` | 280 |
| R-13 | `core/position_fingerprint.py` | 153 | Only imported by 1 test file. Production dedup uses the simpler `content_db.canonical_position_hash()` which sorts AB/AW stones. `position_fingerprint` implements full D4 dihedral group rotation — a more sophisticated algorithm that was never wired into the pipeline. | `tests/unit/test_position_fingerprint.py` | 222 |

**Total dead production code: 3,225 lines**  
**Total orphan test code: 5,695 lines**  
**Grand total removable: ~8,920 lines**

### 2.2 Adapter Flat-File Dead Code (registered into wrong registry)

| R-14 | File | Lines | Status |
|------|------|-------|--------|
| R-14a | `adapters/blacktoplay.py` | 115 | Registers into OLD `registry.py` → invisible to production pipeline |
| R-14b | `adapters/gogameguru.py` | 70 | Same: registers into OLD registry |
| R-14c | `adapters/goproblems.py` | 70 | Same: registers into OLD registry |
| R-14d | `adapters/kisvadim.py` | 130 | **DUPLICATE** of `kisvadim/adapter.py` (subdir version). Registers into OLD registry (dead), subdir version registers into NEW registry (live). |
| R-14e | `adapters/sanderland.py` | 196 | **DUPLICATE** of `sanderland/adapter.py`. Same collision pattern. |
| R-14f | `adapters/travisgk.py` | 107 | **DUPLICATE** of `travisgk/adapter.py`. Same collision pattern. |
| R-14g | `adapters/local.py` | 151 | **DUPLICATE** of `local/adapter.py`. Same collision pattern. |
| R-14h | `adapters/ogs.py` | 987 | Registers into OLD registry. No subdir equivalent exists (`ogs/` directory is empty). |
| R-14i | `adapters/url.py` | 141 | Registers into OLD registry. No subdir equivalent. Not imported by `__init__.py`. |
| R-14j | `adapters/ogs_converter.py` | 407 | Helper for `ogs.py` only. If `ogs.py` is dead, this is dead. |
| R-14k | `adapters/ogs_models.py` | 124 | Same: helper for `ogs.py` only. |
| R-14l | `adapters/ogs_translator.py` | 184 | Same: helper for `ogs.py` only. |

**Total adapter dead/orphan code: ~2,682 lines** (includes the 4 flat duplicates + 5 flat-only adapters + 3 OGS helpers)

### 2.3 OGS Directory Anomaly (R-15)

The `adapters/ogs/` directory exists but contains **only `__pycache__/`** — no `__init__.py`, no `adapter.py`. This is an empty ghost directory. The OGS adapter exists only as the flat-file `ogs.py` which registers into the OLD (dead) registry.

---

## 3. Duplication Inventory

### 3.1 Adapter Registry Duplication (CRITICAL)

| R-16 | Component | Old (dead) | New (canonical) | Divergence |
|------|-----------|-----------|-----------------|------------|
| R-16a | Base protocol | `adapters/base.py` (125 lines) | `adapters/_base.py` (125+ lines) | **Minor divergence**: `_base.py` has v2.0.0 contract reference, 5th checklist item (SGF standards), `ResumableAdapter` protocol. `base.py` lacks these. API shape is identical. |
| R-16b | Registry | `adapters/registry.py` (160 lines) | `adapters/_registry.py` (160+ lines) | **Diverged**: `_registry.py` supports both flat-file and subdirectory discovery, skips `_`-prefixed modules. `registry.py` discovers everything except `base`, `registry`, `__init__`. Both have independent `_adapters` dicts and `_discovered` flags. |

**Impact**: Two completely independent registries exist at runtime:
- `_registry._adapters` contains: `kisvadim`, `local`, `sanderland`, `travisgk` (subdir adapters)
- `registry._adapters` contains: `blacktoplay`, `gogameguru`, `goproblems`, `ogs`, `url` (flat-file adapters)
- Production code (`stages/ingest.py`, `pipeline/coordinator.py`, `pipeline/prerequisites.py`) exclusively uses `_registry.py`
- `adapters/__init__.py` exports from `_registry.py` and imports only subdir adapter packages

**Consequence**: `blacktoplay`, `gogameguru`, `goproblems`, `ogs`, and `url` adapters are **unreachable from the production pipeline**. Calling `create_adapter("blacktoplay")` from `stages/ingest.py` will raise `AdapterNotFoundError`.

### 3.2 Adapter Implementation Duplication

| R-17 | Adapter Name | Flat-file (old) | Subdir (canonical) | Both exist? |
|------|-------------|-----------------|-------------------|-------------|
| R-17a | `kisvadim` | `adapters/kisvadim.py` (130 lines) | `adapters/kisvadim/adapter.py` | Yes — duplicate |
| R-17b | `sanderland` | `adapters/sanderland.py` (196 lines) | `adapters/sanderland/adapter.py` | Yes — duplicate. Subdir version is more evolved (has `collection_assigner`, `move_alternation` imports, folder filtering). |
| R-17c | `travisgk` | `adapters/travisgk.py` (107 lines) | `adapters/travisgk/adapter.py` | Yes — duplicate |
| R-17d | `local` | `adapters/local.py` (151 lines) | `adapters/local/adapter.py` | Yes — subdir version has checkpoint support, PuzzleValidator |
| R-17e | `blacktoplay` | `adapters/blacktoplay.py` (115 lines) | (none) | **No subdir version — adapter is orphaned** |
| R-17f | `gogameguru` | `adapters/gogameguru.py` (70 lines) | (none) | **No subdir version — adapter is orphaned** |
| R-17g | `goproblems` | `adapters/goproblems.py` (70 lines) | (none) | **No subdir version — adapter is orphaned** |
| R-17h | `ogs` | `adapters/ogs.py` (987 lines) | Empty `ogs/` dir | **No subdir version — adapter is orphaned** |
| R-17i | `url` | `adapters/url.py` (141 lines) | (none) | **No subdir version — adapter is orphaned** |

### 3.3 Dedup Logic Duplication

| R-18 | Implementation | Location | Status |
|------|---------------|----------|--------|
| R-18a | `DedupRegistry` (JSON-based) | `core/dedup_registry.py` | Dead — not used by any production code |
| R-18b | `canonical_position_hash()` (simpler, sort-based) | `core/content_db.py` | **Canonical** — used by `stages/ingest.py`, `stages/publish.py` |
| R-18c | `compute_position_fingerprint()` (rotation-aware) | `core/position_fingerprint.py` | Dead — never wired into pipeline. More mathematically rigorous but unused. |

### 3.4 StageContext `views_dir` Property (R-19)

`stages/protocol.py` line 66 has a `views_dir` property returning `output_dir / "views"`. **Zero production code references `.views_dir`**. This is a vestige of the JSON views system.

---

## 4. Architectural Violations

### 4.1 YAGNI Violations

| R-20 | Violation | Location | Description |
|------|-----------|----------|-------------|
| R-20a | Dead rotation-aware dedup | `core/position_fingerprint.py` | Implements D4 dihedral group symmetry normalization — sophisticated but never used. `content_db.canonical_position_hash` (sort-only) is sufficient for current needs. |
| R-20b | Dead DI pattern | `runtime.py` | `RuntimePaths` was explicitly deleted per `docs/archive/di-test-isolation.md` but file survived recovery. |
| R-20c | Empty `ogs/` directory | `adapters/ogs/` | Ghost directory with only `__pycache__`. Should be deleted. |

### 4.2 DRY Violations

| R-21 | Violation | Files | Description |
|------|-----------|-------|-------------|
| R-21a | Dual adapter registries | `registry.py` + `_registry.py` | Two independent registries with separate `_adapters` dicts |
| R-21b | Dual adapter protocols | `base.py` + `_base.py` | Nearly identical `BaseAdapter` and `FetchResult` |
| R-21c | 4 duplicate adapter implementations | flat + subdir versions of kisvadim, sanderland, travisgk, local | Same adapters exist twice, diverged |

### 4.3 Documentation Drift (R-22)

| R-22 | Location | Issue |
|------|----------|-------|
| R-22a | `backend/puzzle_manager/docs/architecture.md` L45 | References "shard" in publish stage description |
| R-22b | `backend/puzzle_manager/docs/adapters.md` L12,56,57 | Examples import from `adapters.base` and `adapters.registry` (dead modules) |
| R-22c | `docs/guides/adapter-development.md` L26 | Imports `from backend.puzzle_manager.adapters.base import BaseAdapter` (wrong import) |
| R-22d | `docs/how-to/backend/create-adapter.md` L58,126 | Correctly references `_base.py` |
| R-22e | `AGENTS.md` | Does not mention the dual registry issue or list dead modules. Uses "sharded" wording for `batch_writer.py` but this is actually the current correct behavior (batch dirs). Mostly accurate. |

---

## 5. Risk Assessment

### 5.1 What Will Break if Dead Code is Removed

| R-23 | Action | Breakage | Severity | Mitigation |
|------|--------|----------|----------|------------|
| R-23a | Delete shard/snapshot files | ~11 test files fail (1,238 test lines) | Low | Delete test files in same commit |
| R-23b | Delete trace_registry + models/trace | 3 test files fail (1,670 lines) + 1 model test | Low | Delete in same commit |
| R-23c | Delete dedup_registry | 2 test files fail (543 lines) | Low | Delete in same commit |
| R-23d | Delete runtime.py | 1 test file fails (184 lines) | Low | Delete in same commit |
| R-23e | Delete flat-file adapters (kisvadim.py, sanderland.py, etc.) | Some adapter tests may import from flat files | Medium | Audit each adapter test file for import source |
| R-23f | Delete `adapters/base.py` + `adapters/registry.py` | Flat-file adapters can't import — but they're being deleted too | Low | Delete all together atomically |
| R-23g | Delete orphaned adapters (blacktoplay, gogameguru, goproblems, ogs, url) | Adapter tests reference these | Medium | Need decision: migrate to subdir + `_registry.py` OR delete |

### 5.2 Runtime Risk: Adapter Silently Missing

| R-24 | Adapter | Currently Discoverable? | Impact |
|------|---------|------------------------|--------|
| R-24a | `blacktoplay` | ❌ No (old registry only) | Cannot be used via pipeline CLI |
| R-24b | `gogameguru` | ❌ No | Same |
| R-24c | `goproblems` | ❌ No | Same |
| R-24d | `ogs` | ❌ No | Same — 987 lines of OGS adapter unreachable |
| R-24e | `url` | ❌ No | Same |
| R-24f | `kisvadim` | ✅ Yes (subdir) | Flat duplicate is dead weight |
| R-24g | `sanderland` | ✅ Yes (subdir) | Flat duplicate is dead weight |
| R-24h | `travisgk` | ✅ Yes (subdir) | Flat duplicate is dead weight |
| R-24i | `local` | ✅ Yes (subdir) | Flat duplicate is dead weight |

---

## 6. Candidate Adaptations for Yen-Go

### Option A: Pure Deletion (Conservative)
Delete all dead code and tests. Orphaned adapters (blacktoplay, gogameguru, goproblems, ogs, url) are deleted entirely since they're unreachable.
- **Pros**: Maximum cleanup (~8,920 lines production + tests), simplest
- **Cons**: Loses OGS adapter (987 lines), blacktoplay, goproblems adapters permanently

### Option B: Migrate + Delete (Recommended)
1. Migrate orphaned adapters (blacktoplay, gogameguru, goproblems, url) to subdir format + `_registry.py`
2. For OGS: migrate to `ogs/adapter.py` + move helpers into `ogs/` package
3. Delete all other dead code
- **Pros**: Preserves all adapter functionality, fixes the registry split
- **Cons**: More work, OGS adapter may need testing

### Option C: Staged Cleanup (Phased)
Phase 1: Delete unambiguously dead code (shard/snapshot, trace_registry, dedup_registry, runtime, logging.py, maintenance/*)
Phase 2: Resolve adapter duplication (migrate orphans, delete flat duplicates)
Phase 3: Clean up protocol.py views_dir, docs drift
- **Pros**: Lower risk per phase, easier code review
- **Cons**: Multiple PRs needed

---

## 7. Planner Recommendations

1. **[CRITICAL] Fix the adapter registry split immediately.** The dual-registry issue means 5 adapters (including the 987-line OGS adapter) are completely invisible to the production pipeline. Any attempt to `run --source blacktoplay` will fail with `AdapterNotFoundError`. This is not just dead code — it's a latent production bug. Migrate orphaned flat-file adapters to subdir format using `_base.py` / `_registry.py`, then delete `base.py` and `registry.py`.

2. **[HIGH] Delete confirmed dead modules in a single atomic commit.** The shard/snapshot system (4 files, 1,303 lines), trace_registry (2 files, 261 lines), dedup_registry (262 lines), runtime.py (118 lines), logging.py (194 lines), maintenance/* (512 lines), level_mapper (422 lines), position_fingerprint (153 lines) — total ~3,225 production lines + ~5,695 test lines. All are verified to have zero production imports.

3. **[MEDIUM] Remove `StageContext.views_dir` property** from `stages/protocol.py`. Zero production references. Vestige of JSON views system.

4. **[LOW] Fix documentation drift.** Update `docs/adapters.md`, `docs/guides/adapter-development.md`, and `docs/architecture.md` to reference `_base.py` / `_registry.py` and remove shard/snapshot references.

---

## 8. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | medium |

**Confidence notes**: High confidence on dead code identification (verified via grep across entire codebase). Medium confidence on adapter migration complexity — the OGS adapter (987 lines) with pydantic models, translator, and converter may require non-trivial validation after migration.

**Risk notes**: The adapter registry split is the highest-risk finding. Remaining risk is test breakage, which is mitigatable by deleting orphan tests atomically with their production code.

---

## Appendix: Internal References

| Ref | File | Relevance |
|-----|------|-----------|
| I-1 | `backend/puzzle_manager/adapters/__init__.py` | Canonical adapter exports — uses `_base.py` / `_registry.py` |
| I-2 | `backend/puzzle_manager/stages/ingest.py` L17-18 | Production pipeline uses `_registry.create_adapter()` |
| I-3 | `backend/puzzle_manager/pipeline/coordinator.py` L272 | Production pipeline uses `_registry.list_adapters()` |
| I-4 | `backend/puzzle_manager/core/trace_map.py` L1-15 | Docstring explicitly states it replaces trace_registry |
| I-5 | `docs/archive/di-test-isolation.md` L36 | States "`RuntimePaths` class was deleted" |
| I-6 | `backend/puzzle_manager/stages/publish.py` L27-43 | Uses `content_db`, `db_builder` — no shard/snapshot imports |

## Appendix: External References

| Ref | Source | Relevance |
|-----|--------|-----------|
| E-1 | Python packaging best practice (PEP 420, importlib) | Subdir adapter pattern (`{name}/adapter.py`) is standard plugin architecture |
| E-2 | YAGNI principle (Martin Fowler) | Dead code that was replaced should be deleted, not preserved "just in case" |
| E-3 | Git as version control | All deleted code is recoverable from git history — no need to keep dead modules |
| E-4 | Registry pattern (GoF) | Single registry is the correct pattern; dual registries violate Single Responsibility |
