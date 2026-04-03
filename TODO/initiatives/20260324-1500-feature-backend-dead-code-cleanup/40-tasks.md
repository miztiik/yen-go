# Tasks — Backend Dead Code Cleanup Post-Recovery

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Selected Option**: OPT-1 (3-Phase Risk-Layered)  
**Last Updated**: 2026-03-24

---

## Task Legend

- `[P]` = Can run in parallel with other `[P]` tasks in the same group
- `[S]` = Sequential — must complete before next task starts
- `[G]` = Governance/verification gate — must pass before next phase
- Dependencies listed as `after: T{id}`

---

## Pre-Execution

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T0 | Capture test baseline | [S] | — | — | Run `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short` and record: total collected, passed, failed, errors. This is the "before" snapshot. |
| T0.1 | Create feature branch | [S] | — | after: T0 | `git checkout -b feature/backend-dead-code-cleanup` from current HEAD |

---

## Phase 1 — Dead Core Modules + Orphan Tests

### Phase 1A: Delete Dead Production Files

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T1 | Delete shard/snapshot system (4 files) | [P] | `core/shard_key.py`, `core/shard_models.py`, `core/shard_writer.py`, `core/snapshot_builder.py` | after: T0.1 | Delete the 4 shard/snapshot files. These formed a cohesive subsystem replaced by SQLite. |
| T2 | Delete dedup_registry | [P] | `core/dedup_registry.py` | after: T0.1 | Replaced by `content_db.canonical_position_hash()`. |
| T3 | Delete trace_registry + models/trace | [P] | `trace_registry.py`, `models/trace.py` | after: T0.1 | Replaced by `core/trace_map.py`. Delete `models/trace.py` (the model) and `trace_registry.py` (the consumer). |
| T4 | Delete maintenance/ directory | [P] | `maintenance/views.py`, `maintenance/migrate_sharding.py`, `maintenance/__init__.py` | after: T0.1 | Delete entire `maintenance/` directory. Both files dead, zero production imports. |
| T5 | Delete runtime.py + logging.py | [P] | `runtime.py`, `logging.py` | after: T0.1 | `runtime.py` replaced by `paths.py`. `logging.py` replaced by `pm_logging.py`. |
| T6 | Delete level_mapper + position_fingerprint | [P] | `core/level_mapper.py`, `core/position_fingerprint.py` | after: T0.1 | `level_mapper` replaced by `classifier.py`. `position_fingerprint` replaced by `content_db.canonical_position_hash()`. |

### Phase 1B: Delete Orphan Test Files

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T7 | Delete shard/snapshot orphan tests (7 files) | [P] | `tests/unit/test_shard_key.py`, `tests/unit/test_shard_models.py`, `tests/unit/test_shard_writer.py`, `tests/unit/test_shard_labels.py`, `tests/unit/test_shard_writer_n_assignment.py`, `tests/unit/test_compact_json_format.py`, `tests/unit/test_snapshot_entry_reconstruction.py` | after: T1 | Co-delete with source. All import from dead shard/snapshot modules. |
| T8 | Delete snapshot integration orphan tests (3 files) | [P] | `tests/integration/test_snapshot_builder.py`, `tests/integration/test_publish_snapshot_wiring.py`, `tests/integration/test_snapshot_rollback.py` | after: T1 | Integration tests for dead snapshot system. |
| T9 | Delete dedup orphan tests (2 files) | [P] | `tests/unit/test_dedup_registry.py`, `tests/unit/test_dedup_metadata_merge.py` | after: T2 | Test only dead dedup_registry. |
| T10 | Delete trace orphan tests (3 files) + tests/models/ dir | [P] | `tests/test_cli_trace.py`, `tests/unit/test_trace_registry.py`, `tests/test_trace_registry.py`, `tests/models/test_trace.py`, `tests/models/__init__.py` | after: T3 | 3 trace test files + the `tests/models/` directory (only contained `test_trace.py`). Delete entire `tests/models/` dir. |
| T11 | Delete maintenance orphan test (1 file) | [P] | `tests/unit/test_migrate_sharding.py` | after: T4 | Tests dead migrate_sharding. |
| T12 | Delete runtime orphan test (1 file) | [P] | `tests/unit/test_runtime.py` | after: T5 | Tests dead RuntimePaths. |
| T13 | Delete level_mapper + position_fingerprint orphan tests (2 files) | [P] | `tests/unit/test_level_mapper.py`, `tests/unit/test_position_fingerprint.py` | after: T6 | Tests dead modules. |
| T14 | Delete old adapter infra orphan test (1 file) | [P] | `tests/test_adapters.py` | after: T0.1 | Imports from dead `adapters.base`/`adapters.registry`. Co-delete in Phase 1 to prevent dangles. |

### Phase 1 Gate

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T15 | Phase 1 verification gate | [G] | — | after: T7-T14 | (1) `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short` — zero failures, fewer tests collected. (2) Verify all 13 production files absent. (3) Grep for dead module imports (all empty). (4) `ruff check backend/puzzle_manager/`. (5) Record post-Phase-1 test count. |
| T15.1 | Commit Phase 1 | [S] | — | after: T15 | `git add` only the specific deleted files. `git commit -m "refactor: delete 13 dead core modules + 21 orphan tests (Phase 1)"` |

---

## Phase 2 — Adapter Cleanup

### Phase 2A: Delete Dead Adapter Files

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T16 | Delete old adapter infrastructure | [P] | `adapters/base.py`, `adapters/registry.py` | after: T15.1 | Old adapter infra replaced by `_base.py`/`_registry.py`. |
| T17 | Delete orphaned adapters (5 files) | [P] | `adapters/blacktoplay.py`, `adapters/gogameguru.py`, `adapters/goproblems.py`, `adapters/url.py`, `adapters/ogs.py` | after: T15.1 | Registered only in dead registry. No production usage. |
| T18 | Delete OGS helper modules (3 files) | [P] | `adapters/ogs_converter.py`, `adapters/ogs_models.py`, `adapters/ogs_translator.py` | after: T17 | Helpers used only by dead `ogs.py`. |
| T19 | Delete duplicate flat-file adapters (4 files) | [P] | `adapters/kisvadim.py`, `adapters/sanderland.py`, `adapters/travisgk.py`, `adapters/local.py` | after: T15.1 | Duplicates of `{name}/adapter.py`. Python resolves packages first. |
| T20 | Delete ghost `ogs/` directory | [P] | `adapters/ogs/` (entire dir) | after: T15.1 | Contains only `__pycache__`. Ghost directory. |

### Phase 2B: Edit `__init__.py`

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T21 | Edit `adapters/__init__.py` — remove UrlAdapter | [S] | `adapters/__init__.py` | after: T17 | Remove line 27 (`from backend.puzzle_manager.adapters.url import UrlAdapter`) and `"UrlAdapter"` from `__all__`. Must be atomic with `url.py` deletion. |

### Phase 2 Gate

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T22 | Phase 2 verification gate | [G] | — | after: T16-T21 | (1) `pytest backend/ -m "not (cli or slow)"` — zero failures, same test count as post-Phase-1. (2) `python -m backend.puzzle_manager sources` — lists only live adapters. (3) `grep UrlAdapter adapters/__init__.py` — empty. (4) All 14 flat files absent. (5) `adapters/ogs/` absent. (6) `ruff check backend/puzzle_manager/`. (7) Record post-Phase-2 test count (should match Phase-1). |
| T22.1 | Commit Phase 2 | [S] | — | after: T22 | `git add` specific files. `git commit -m "refactor: delete old adapter infra + 14 flat-file adapters (Phase 2)"` |

---

## Phase 3 — Vestigial Code + Documentation

### Phase 3A: Code Edit

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T23 | Remove `views_dir` property from protocol.py | [S] | `stages/protocol.py` (lines 65-68) | after: T22.1 | Delete the 4-line `views_dir` property. Unused — views system is dead. |

### Phase 3B: Delete/Archive Obsolete Docs

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T24 | Delete obsolete docs (2 files) | [P] | `docs/architecture/backend/view-index-pagination.md`, `docs/STAGES.md` | after: T22.1 | Pagination doc is duplicate of archive. STAGES.md massively outdated (Q8:A). |
| T25 | Move docs to archive (3 files) | [P] | `docs/architecture/backend/view-index-segmentation.md` → `docs/archive/`, `docs/architecture/snapshot-deployment-topology.md` → `docs/archive/`, `docs/concepts/snapshot-shard-terminology.md` → `docs/archive/` | after: T22.1 | Historical value preserved in archive. |

### Phase 3C: Fix Stale Documentation

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T26 | Fix AGENTS.md — Typer→argparse + url/ ghost + typer dep | [S] | `backend/puzzle_manager/AGENTS.md` | after: T22.1 | Change "Typer CLI" to "argparse CLI" (lines 26, 175). Remove `url/` directory reference. Remove `typer` from dependency table. Add `argparse` (stdlib). |
| T27 | Fix adapter docs — update base→_base references | [P] | `docs/how-to/backend/create-adapter.md` | after: T22.1 | Update `base.py`→`_base.py`, `registry.py`→`_registry.py` references. |
| T28 | Fix pipeline architecture doc — remove shard/snapshot refs | [P] | `docs/architecture/backend/pipeline-architecture.md` | after: T22.1 | Remove any references to shard/snapshot/views system. Update to reflect SQLite architecture. |
| T29 | Consolidate/redirect adapter development guide | [P] | `docs/guides/adapter-development.md` | after: T22.1 | Per Q9:C/B — simplify or redirect to `docs/how-to/backend/create-adapter.md`. |
| T30 | Review and fix remaining stale docs | [S] | Various docs from `15-research.md` D-list | after: T27, T28, T29 | Targeted content review: verify SGF schema version refs, CLI command refs, directory structure refs against actual code. Fix only stale content. |

### Phase 3 Gate

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T31 | Phase 3 verification gate | [G] | — | after: T23-T30 | (1) `pytest backend/ -m "not (cli or slow)"` — zero failures, same test count as post-Phase-2. (2) `grep views_dir stages/protocol.py` — empty. (3) `grep -ni typer AGENTS.md` — empty. (4) Deleted docs absent. (5) Archived docs present in `docs/archive/`. (6) `ruff check backend/puzzle_manager/`. (7) Record final test count. |
| T31.1 | Commit Phase 3 | [S] | — | after: T31 | `git add` specific files. `git commit -m "refactor: remove views_dir + fix stale docs (Phase 3)"` |

---

## Post-Execution

| Task ID | Title | Type | Files | Dependencies | Description |
|---------|-------|------|-------|-------------|-------------|
| T32 | Final regression test | [S] | — | after: T31.1 | Run full test suite: `pytest backend/ -q --no-header --tb=short`. Compare against T0 baseline. All remaining tests must pass. |
| T33 | Full lint check | [S] | — | after: T31.1 | `ruff check backend/puzzle_manager/` — zero errors. |
| T34 | Update initiative status | [S] | `status.json` | after: T32, T33 | Set `current_phase: "validate"`, all planning phases `"approved"`, execution `"approved"`. |

---

## Task Dependency Graph

```
T0 → T0.1 ─┬─> T1 ─> T7, T8
            ├─> T2 ─> T9
            ├─> T3 ─> T10
            ├─> T4 ─> T11
            ├─> T5 ─> T12
            ├─> T6 ─> T13
            └─> T14
                    ↓
            T15 (gate) → T15.1
                    ↓
            ┌─> T16
            ├─> T17 ─> T18, T21
            ├─> T19
            └─> T20
                    ↓
            T22 (gate) → T22.1
                    ↓
            ┌─> T23
            ├─> T24, T25
            ├─> T26
            ├─> T27, T28, T29 ─> T30
                    ↓
            T31 (gate) → T31.1
                    ↓
            T32, T33 → T34
```

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total tasks | 35 (T0-T34) |
| Phase 1 tasks | 16 (T0-T15.1) |
| Phase 2 tasks | 8 (T16-T22.1) |
| Phase 3 tasks | 11 (T23-T31.1) |
| Post-execution tasks | 3 (T32-T34) |
| Parallel groups | 8 |
| Sequential gates | 3 |
| Files deleted | ~36 production + test files |
| Files edited | 2 (`adapters/__init__.py`, `stages/protocol.py`) |
| Docs deleted/archived/fixed | ~14 files |
| Directories removed | 3 (`maintenance/`, `tests/models/`, `adapters/ogs/`) |
