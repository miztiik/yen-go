# Research Brief — Backend Dead Code Cleanup (Consolidated)

**Sources**:
- Code audit: `TODO/initiatives/20260324-research-backend-cleanup-post-recovery/15-research.md`
- Docs audit: `TODO/initiatives/2026-03-24-backend-docs-cleanup/15-research.md`
**Date**: 2026-03-24 (two research passes)

---

## Pass 1: Dead Code Inventory

| ID | Finding | Severity | Lines |
|----|---------|----------|-------|
| R-1..R-13 | 13 dead production modules (shard/snapshot, trace_registry, dedup_registry, runtime.py, logging.py, maintenance/*, level_mapper, position_fingerprint) | HIGH | ~3,225 prod + ~5,695 test |
| R-14..R-15 | Dual adapter registry: 5 adapters invisible to production (blacktoplay, gogameguru, goproblems, ogs, url) | CRITICAL | ~2,682 |
| R-16..R-17 | 4 duplicated adapter implementations (flat + subdir) | HIGH | ~584 (duplicates) |
| R-18 | 3 dedup implementations, only 1 used | MEDIUM | ~415 (dead) |
| R-19 | `StageContext.views_dir` property — zero references | LOW | ~3 |
| R-20..R-21 | DRY/YAGNI violations (dual registries, dead DI pattern, empty dir) | MEDIUM | — |

## Pass 2: Documentation Audit (65 files audited)

### Entirely Obsolete Files (5 → delete/archive)

| D-ID | File | Reason |
|------|------|--------|
| D-1 | `docs/architecture/backend/view-index-pagination.md` | Duplicate of archived copy, dead pagination system |
| D-2 | `docs/architecture/backend/view-index-segmentation.md` | Dead segmentation system, no archival banner |
| D-3 | `docs/architecture/snapshot-deployment-topology.md` | Dead snapshot system |
| D-4 | `docs/concepts/snapshot-shard-terminology.md` | Dead shard/snapshot terminology |
| D-5 | `docs/STAGES.md` | Massively outdated: wrong CLI, wrong levels, wrong output structure; superseded by `docs/architecture/backend/stages.md` |

### Critical Stale Content (13 files → targeted edits)

| D-ID | File | Issue |
|------|------|-------|
| D-6 | `docs/architecture/backend/data-flow.md` | Shows JSON views, level-nested SGF dirs; all replaced by SQLite/flat |
| D-7 | `docs/architecture/backend/puzzle-manager.md` | Lists `logging.py`, `base.py`, `registry.py`, flat adapter files — all dead |
| D-8 | `backend/puzzle_manager/docs/adapters.md` | Imports from dead `base.py`/`registry.py`, old FetchResult shape |
| D-9 | `backend/puzzle_manager/docs/architecture.md` | Calls publish sub-stage "shard", uses old staging dir names |
| D-10 | `docs/reference/configuration.md` | Old level names (basic/challenging), old tag format, wrong log directory |
| D-11 | `docs/reference/puzzle-manager-cli.md` | Dead OGS CLI flags, missing 8+ commands, --source not shown as required |
| D-12 | `docs/architecture/backend/README.md` | Wrong directory path (`src/`), CLI says "Click" not argparse |
| D-13 | `docs/guides/adapter-development.md` | Dead import path from `base.py`, wrong fetch() return type |
| D-14 | **`backend/puzzle_manager/AGENTS.md`** | **Says "Typer CLI" (lines 26, 175) but `cli.py` actually uses `argparse`** |
| D-15 | `backend/puzzle_manager/README.md` | Says argparse but also has dead trace CLI commands |
| D-16 | `docs/reference/sgf-properties.md` | Schema says v8 (current is v15); YI instead of YM; root C[] behavior wrong |
| D-17 | `docs/architecture/README.md` | Output says "JSON views" |
| D-18 | `docs/architecture/backend/adapter-design-standards.md` | Import from dead `registry.py` |

### Medium Stale Content (5 files → minor edits)

| D-ID | File | Issue |
|------|------|-------|
| D-19 | `backend/puzzle_manager/docs/configuration.md` | References `views_root` config (dead) |
| D-20 | `backend/puzzle_manager/docs/cli.md` | Missing 8 commands, missing --source flag |
| D-21 | `docs/concepts/level-system-stability.md` | References dead path format, dead views, dead migration script |
| D-22 | `backend/puzzle_manager/CLAUDE.md` | References `YS` property (doesn't exist; should be YM) |
| D-23 | `docs/architecture/backend/adapter-design-standards.md` | Import from dead `registry.py` |

### Confirmed Accurate (43 files, 66% — no changes needed)

Includes: AGENTS.md (except Typer claim), pipeline.md, stages.md, enrichment.md, integrity.md, all how-to/ files, CLAUDE.md root, copilot-instructions.md, backend-puzzle-manager.instructions.md.

## Planning Confidence

| Metric | Pre-Research | After Pass 1 | After Pass 2 |
|--------|-------------|--------------|--------------|
| Confidence Score | 72 | 92 | 95 |
| Risk Level | medium | medium | medium |
| Research Triggered? | Yes | Complete | Complete |

## Combined Scope Summary

| Category | Items | Lines Affected |
|----------|-------|---------------|
| Dead production code to delete | 13 files | ~3,225 |
| Dead/orphan test code to delete | ~18 test files | ~5,695 |
| Adapter flat-file dead code | 12 files | ~2,682 |
| Old adapter infrastructure (base.py, registry.py) | 2 files | ~285 |
| Vestigial code (`views_dir` property) | 1 property | ~3 |
| Entirely obsolete docs to delete/archive | 5 files | ~1,500 est. |
| Docs with critical stale content | 13 files | targeted edits |
| Docs with medium stale content | 5 files | targeted edits |
| Empty ghost directory | `adapters/ogs/` | 0 (delete dir) |
| **TOTAL dead code** | **~48 files** | **~13,390 lines** |
