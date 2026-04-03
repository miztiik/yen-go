# Charter — Backend Dead Code Cleanup Post-Recovery

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Last Updated**: 2026-03-24  
**Correction Level**: Level 4 (Large Scale — 4+ files, structure changes)

---

## 1. Goals

1. **Delete all confirmed dead production code** (~3,225 lines across 13 modules) that was reintroduced during the repository recovery incident.
2. **Delete orphaned adapter flat-files** (~2,682 lines across 12 files) and the old adapter infrastructure (`base.py`, `registry.py`), eliminating the dual-registry DRY violation.
3. **Delete all orphan test files** (~5,695 lines across ~18 files) that only test dead code.
4. **Delete/archive 5 entirely obsolete documentation files** and fix stale content in 18 documentation files.
5. **Fix AGENTS.md inaccuracy** (says "Typer CLI" but `cli.py` uses `argparse`).
6. **Remove vestigial code** (`StageContext.views_dir` property).
7. **Ensure all currently-passing tests continue to pass** at each phase gate. No regressions.

## 2. Non-Goals

- Migrating orphaned adapters (blacktoplay, gogameguru, goproblems, ogs, url) to the new registry — they're being deleted. Future consolidation in tools/ is separate.
- Changing the CLI framework (argparse → Typer) — out of scope.
- Refactoring live production code — only deleting dead code and fixing docs.
- Adding new features or test coverage.
- Frontend changes of any kind.

## 3. Constraints

- **Zero production behavior change** — only dead code removal and docs fixes.
- **All live tests must pass after each phase** — verified by running `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short`.
- **Git safety** — Never `git add .`, never `git stash`, never `git reset --hard`. Stage only specific files.
- **No new files created** (except initiative artifacts) — this is a deletion/edit-only initiative.
- **Dead code policy** — "Delete, don't deprecate. Git history preserves everything." (source: `.github/copilot-instructions.md` L441, `frontend/CLAUDE.md` L185).
- **Multi-phase execution** — each phase is independently verifiable and reversible.
- **Documentation obligation** — every code change includes corresponding doc updates per project policy.

## 4. Acceptance Criteria

| AC-ID | Criterion | Verification |
|-------|-----------|-------------|
| AC-1 | All 13 dead production modules deleted | `ls` confirms files absent |
| AC-2 | All ~18 orphan test files deleted | `pytest --collect-only` shows reduced test count |
| AC-3 | Old adapter infrastructure (`base.py`, `registry.py`) deleted | `ls adapters/` shows only `_base.py`, `_registry.py`, subdirectory adapters |
| AC-4 | All orphaned flat-file adapters deleted (blacktoplay.py, gogameguru.py, goproblems.py, ogs.py, url.py, ogs_*.py, plus 4 flat duplicates) | `ls adapters/` confirms |
| AC-5 | `adapters/ogs/` ghost directory deleted | Directory absent |
| AC-6 | 5 obsolete docs deleted or moved to archive | File system check |
| AC-7 | 13 critical + 5 medium stale docs fixed | Content review |
| AC-8 | AGENTS.md says `argparse`, not `Typer`; dependency table has no `typer` | `grep -n typer AGENTS.md` returns nothing |
| AC-9 | `StageContext.views_dir` property removed from `stages/protocol.py` | `grep views_dir stages/protocol.py` returns nothing |
| AC-10 | `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=short` passes with 0 failures | Test run output |
| AC-11 | `ruff check backend/puzzle_manager/` passes with 0 errors | Lint output |
| AC-12 | No production code behavior change — pipeline `run`, `status`, `daily`, `publish-log` all function identically | Manual smoke test or integration test pass |
| AC-13 | `adapters/__init__.py` edited: `UrlAdapter` import (line 27) and `__all__` entry removed | `grep UrlAdapter adapters/__init__.py` returns nothing |

## 5. Scope Inventory

### Dead Production Code (13 files, ~3,225 lines)

| File | Lines | Replaced By |
|------|-------|-------------|
| `trace_registry.py` | 166 | `core/trace_map.py` |
| `models/trace.py` | 95 | (only used by trace_registry) |
| `core/shard_key.py` | 252 | SQLite DB-1/DB-2 |
| `core/shard_models.py` | 217 | SQLite DB-1/DB-2 |
| `core/shard_writer.py` | 367 | `core/db_builder.py` |
| `core/snapshot_builder.py` | 467 | `core/db_builder.py` |
| `core/dedup_registry.py` | 262 | `core/content_db.canonical_position_hash()` |
| `maintenance/views.py` | 166 | SQLite DB-1 |
| `maintenance/migrate_sharding.py` | 346 | (one-shot migration, completed) |
| `runtime.py` | 118 | `paths.py` |
| `logging.py` | 194 | `pm_logging.py` |
| `core/level_mapper.py` | 422 | `core/classifier.py` |
| `core/position_fingerprint.py` | 153 | `core/content_db.canonical_position_hash()` |

### Dead Adapter Code (12 files, ~2,682 lines)

| File | Lines | Status |
|------|-------|--------|
| `adapters/base.py` | 125 | Old, replaced by `_base.py` |
| `adapters/registry.py` | 160 | Old, replaced by `_registry.py` |
| `adapters/blacktoplay.py` | 115 | Orphaned (no subdir version, old registry) |
| `adapters/gogameguru.py` | 70 | Orphaned |
| `adapters/goproblems.py` | 70 | Orphaned |
| `adapters/ogs.py` | 987 | Orphaned (empty `ogs/` dir) |
| `adapters/ogs_converter.py` | 407 | Helper for dead ogs.py |
| `adapters/ogs_models.py` | 124 | Helper for dead ogs.py |
| `adapters/ogs_translator.py` | 184 | Helper for dead ogs.py |
| `adapters/kisvadim.py` | 130 | Duplicate of `kisvadim/adapter.py` |
| `adapters/sanderland.py` | 196 | Duplicate of `sanderland/adapter.py` |
| `adapters/travisgk.py` | 107 | Duplicate of `travisgk/adapter.py` |
| `adapters/local.py` | 151 | Duplicate of `local/adapter.py` |
| `adapters/url.py` | 141 | Orphaned (no subdir version) |
| `adapters/ogs/` (dir) | 0 | Ghost directory with only `__pycache__` |

### Vestigial Code (1 edit)

| File | Change |
|------|--------|
| `stages/protocol.py` | Remove `views_dir` property (~3 lines) |

### Obsolete Docs (5 files → delete/archive)

| File | Action |
|------|--------|
| `docs/architecture/backend/view-index-pagination.md` | Delete (duplicate of archive) |
| `docs/architecture/backend/view-index-segmentation.md` | Move to archive |
| `docs/architecture/snapshot-deployment-topology.md` | Move to archive |
| `docs/concepts/snapshot-shard-terminology.md` | Move to archive |
| `docs/STAGES.md` | Delete |

### Docs with Critical/Medium Stale Content (18 files → targeted edits)

See `15-research.md` findings D-6 through D-23 for detailed per-file issues.

## 6. Phasing Strategy

| Phase | Scope | Risk | Gate |
|-------|-------|------|------|
| **Phase 1**: Dead core modules | Delete 13 dead production files + their ~18 orphan test files | Low — zero production imports | `pytest backend/ -m "not (cli or slow)"` all pass |
| **Phase 2**: Adapter cleanup | Delete old adapter infra + 14 flat-file adapters + ghost dir + edit `adapters/__init__.py` (remove `UrlAdapter` import/export) | Low — production uses only `_registry.py`; Python resolves packages before modules for 4 duplicates | Same test gate + `python -m backend.puzzle_manager sources` works |
| **Phase 3**: Vestigial code + docs | Remove `views_dir`, fix 18 stale docs, delete/archive 5 obsolete docs, fix AGENTS.md | Zero risk — docs-only + 3-line code edit | Same test gate + doc content review |

## 7. Research References

- Code audit: `TODO/initiatives/20260324-research-backend-cleanup-post-recovery/15-research.md`
- Docs audit: `TODO/initiatives/2026-03-24-backend-docs-cleanup/15-research.md`
- Consolidated: `TODO/initiatives/20260324-1500-feature-backend-dead-code-cleanup/15-research.md`
