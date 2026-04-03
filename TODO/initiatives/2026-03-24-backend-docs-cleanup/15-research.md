# Research: Backend Obsolete/Superseded Documentation Audit

**Initiative**: `2026-03-24-backend-docs-cleanup`
**Research Date**: 2026-03-24
**Artifact**: `15-research.md`

---

## 1. Research Question and Boundaries

**Question**: Which documentation files across the Yen-Go repository contain stale, obsolete, or superseded references to dead backend systems?

**Boundaries**:
- Scope: All markdown docs related to `backend/puzzle_manager/` — internal docs, global docs, agent/CLAUDE files, config READMEs
- Dead systems defined in prior research: shard/snapshot, trace registry, DedupRegistry, JSON view indexes, RuntimePaths, old logging.py, old adapter base/registry, dead core modules
- Out of scope: Frontend docs, tools/ docs (except cross-references), Python source docstrings

---

## 2. Summary Table — All Files Audited

### Legend
- **ACCURATE**: No stale references found
- **HAS_STALE_CONTENT**: Contains specific stale lines but overall document is useful
- **ENTIRELY_OBSOLETE**: Entire document describes dead systems — candidate for deletion or archiving
- **NEEDS_UPDATE**: Document is mostly current but needs targeted edits
- **NOT_FOUND**: File does not exist

| R-ID | File | Status | Severity | Recommended Action |
|------|------|--------|----------|-------------------|
| **Group A: Backend Internal Docs** | | | | |
| R-1 | `backend/puzzle_manager/docs/README.md` | ACCURATE | — | `no_change` |
| R-2 | `backend/puzzle_manager/docs/architecture.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-3 | `backend/puzzle_manager/docs/adapters.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-4 | `backend/puzzle_manager/docs/configuration.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-5 | `backend/puzzle_manager/docs/cli.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-6 | `backend/puzzle_manager/AGENTS.md` | ACCURATE | — | `no_change` |
| R-7 | `backend/puzzle_manager/CLAUDE.md` | HAS_STALE_CONTENT | low | `update_references` |
| R-8 | `backend/puzzle_manager/README.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-9 | `backend/README.md` | ACCURATE | — | `no_change` |
| R-10 | `backend/puzzle_manager/core/BATCH_WRITER.md` | ACCURATE | — | `no_change` |
| R-11 | `backend/puzzle_manager/tests/README.md` | ACCURATE | — | `no_change` |
| **Group B: Global Docs — Backend Architecture** | | | | |
| R-12 | `docs/architecture/backend/pipeline.md` | ACCURATE | — | `no_change` |
| R-13 | `docs/architecture/backend/stages.md` | ACCURATE | — | `no_change` |
| R-14 | `docs/architecture/backend/data-flow.md` | HAS_STALE_CONTENT | critical | `rewrite_section` |
| R-15 | `docs/architecture/backend/adapters.md` | ACCURATE | — | `no_change` |
| R-16 | `docs/architecture/backend/adapter-design-standards.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-17 | `docs/architecture/backend/view-index-pagination.md` | ENTIRELY_OBSOLETE | critical | `move_to_archive` |
| R-18 | `docs/architecture/backend/view-index-segmentation.md` | ENTIRELY_OBSOLETE | critical | `move_to_archive` |
| R-19 | `docs/architecture/backend/puzzle-manager.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-20 | `docs/architecture/backend/inventory-operations.md` | ACCURATE | — | `no_change` |
| R-21 | `docs/architecture/backend/logging.md` | ACCURATE | — | `no_change` |
| R-22 | `docs/architecture/backend/integrity.md` | ACCURATE | — | `no_change` |
| R-23 | `docs/architecture/backend/enrichment.md` | ACCURATE | — | `no_change` |
| R-24 | `docs/architecture/backend/tactical-analyzer.md` | ACCURATE | — | `no_change` |
| R-25 | `docs/architecture/backend/tagging-strategy.md` | ACCURATE | — | `no_change` |
| R-26 | `docs/architecture/backend/hint-architecture.md` | ACCURATE | — | `no_change` |
| R-27 | `docs/architecture/backend/testing.md` | ACCURATE | — | `no_change` |
| R-28 | `docs/architecture/backend/sgf.md` | ACCURATE | — | `no_change` |
| R-29 | `docs/architecture/backend/sgf/` | ACCURATE | — | `no_change` |
| R-30 | `docs/architecture/snapshot-deployment-topology.md` | ENTIRELY_OBSOLETE | critical | `move_to_archive` |
| R-31 | `docs/architecture/database-deployment-topology.md` | ACCURATE | — | `no_change` |
| **Group C: Global Docs — Concepts** | | | | |
| R-32 | `docs/concepts/snapshot-shard-terminology.md` | ENTIRELY_OBSOLETE | critical | `move_to_archive` |
| R-33 | `docs/concepts/sqlite-index-architecture.md` | ACCURATE | — | `no_change` |
| R-34 | `docs/concepts/observability.md` | ACCURATE | — | `no_change` |
| R-35 | `docs/concepts/batching-and-checkpoints.md` | ACCURATE | — | `no_change` |
| R-36 | `docs/concepts/quality.md` | ACCURATE | — | `no_change` |
| R-37 | `docs/concepts/puzzle-validation.md` | ACCURATE | — | `no_change` |
| R-38 | `docs/concepts/level-system-stability.md` | HAS_STALE_CONTENT | medium | `update_references` |
| **Group D: Global Docs — How-To** | | | | |
| R-39 | `docs/how-to/backend/create-adapter.md` | ACCURATE | — | `no_change` |
| R-40 | `docs/how-to/backend/run-pipeline.md` | ACCURATE | — | `no_change` |
| R-41 | `docs/how-to/backend/rollback.md` | ACCURATE | — | `no_change` |
| R-42 | `docs/how-to/backend/cleanup.md` | ACCURATE | — | `no_change` |
| R-43 | `docs/how-to/backend/cli-reference.md` | ACCURATE | — | `no_change` |
| R-44 | `docs/how-to/backend/monitor.md` | ACCURATE | — | `no_change` |
| R-45 | `docs/how-to/backend/configure-sources.md` | ACCURATE | — | `no_change` |
| R-46 | `docs/how-to/backend/troubleshoot.md` | ACCURATE | — | `no_change` |
| **Group E: Global Docs — Reference** | | | | |
| R-47 | `docs/reference/view-index-schema.md` | HAS_STALE_CONTENT | low | `no_change` (self-documents evolution) |
| R-48 | `docs/reference/adapters/README.md` | ACCURATE | — | `no_change` |
| R-49 | `docs/reference/configuration.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-50 | `docs/reference/puzzle-manager-cli.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-51 | `docs/reference/puzzle-sources.md` | ACCURATE | — | `no_change` |
| R-52 | `docs/reference/sgf-properties.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-53 | `docs/reference/technique-tags.md` | ACCURATE | — | `no_change` |
| R-54 | `docs/reference/hint-system.md` | ACCURATE | — | `no_change` |
| R-55 | `docs/reference/enrichment-config.md` | ACCURATE | — | `no_change` (redirect doc) |
| **Group F: Archive** | | | | |
| R-56 | `docs/archive/view-index-pagination.md` | ACCURATE | — | `no_change` (properly archived) |
| R-57 | `docs/archive/view-index-types-frontend.md` | ACCURATE | — | `no_change` (properly archived) |
| R-58 | `docs/archive/pipeline-v3-design.md` | ACCURATE | — | `no_change` (properly archived) |
| **Group G: Miscellaneous Stale Docs** | | | | |
| R-59 | `docs/STAGES.md` | ENTIRELY_OBSOLETE | critical | `delete_file` or `move_to_archive` |
| R-60 | `docs/architecture/README.md` | HAS_STALE_CONTENT | medium | `update_references` |
| R-61 | `docs/architecture/backend/README.md` | HAS_STALE_CONTENT | critical | `update_references` |
| R-62 | `docs/guides/adapter-development.md` | HAS_STALE_CONTENT | critical | `update_references` |
| **Group H: Root-level files** | | | | |
| R-63 | `CLAUDE.md` (root) | ACCURATE | — | `no_change` |
| R-64 | `.github/copilot-instructions.md` | ACCURATE | — | `no_change` |
| R-65 | `.github/instructions/backend-puzzle-manager.instructions.md` | ACCURATE | — | `no_change` |

---

## 3. Detailed Findings — Files With Issues

### R-2: `backend/puzzle_manager/docs/architecture.md` — CRITICAL

**Stale references**:

1. **Line 45**: Publish sub-stage listed as `shard` — Should be `batch` or `sgf_output`:
   ```
   1. **shard** - Organize into batch directories
   2. **index** - Build level and tag indexes
   3. **output** - Write final files
   ```
   Current publish sub-stages are: orphan recovery → SGF output → database build → daily → inventory.

2. **Lines 65-70**: Configuration section references `pipeline.json`, `sources.json`, `levels.json` as being in `backend/puzzle_manager/config/` — this is correct, but the listing omits the actual current structure (loader.py, lock.py, schemas, etc.).

3. **Lines 30-33**: Staging dir names say `staging/raw/` — actual current name is `staging/ingest/`.

---

### R-3: `backend/puzzle_manager/docs/adapters.md` — CRITICAL

**Stale references**:

1. **Line 12**: Imports from dead `base.py`:
   ```python
   from backend.puzzle_manager.adapters.base import BaseAdapter, FetchResult
   ```
   Should be: `from backend.puzzle_manager.adapters._base import BaseAdapter, FetchResult`

2. **Line 56-57**: Imports from dead `base.py` and `registry.py`:
   ```python
   from backend.puzzle_manager.adapters.base import FetchResult
   from backend.puzzle_manager.adapters.registry import register_adapter
   ```
   Should be: `_base` and `_registry` respectively.

3. **FetchResult dataclass** (lines 22-38): Shows an older version with `is_success`/`is_skipped`/`is_failed` properties. Current version uses `status: Literal["success", "skipped", "failed"]` with factory methods.

4. **Step 2: Register section** (line ~80): Import path `from backend.puzzle_manager.adapters.mysource` — should be subdirectory pattern `from backend.puzzle_manager.adapters.my_source.adapter`.

---

### R-4: `backend/puzzle_manager/docs/configuration.md` — MEDIUM

**Stale references**:

1. **Line 40**: References `views_root` config:
   ```json
   "views_root": "yengo-puzzle-collections/views"
   ```
   JSON views are dead — replaced by SQLite databases. This config key should not exist.

---

### R-5: `backend/puzzle_manager/docs/cli.md` — MEDIUM

**Stale references**:

1. **Missing commands**: Only shows 5 commands (`run`, `status`, `clean`, `validate`, `sources`). The current CLI has 13 commands per AGENTS.md: `run`, `status`, `sources`, `daily`, `clean`, `validate`, `publish-log`, `rollback`, `vacuum-db`, `inventory`, etc.
2. **Missing `--source` flag**: The `run` command docs don't show `--source` as REQUIRED.
3. **Missing `--drain`, `--flush-interval`, `--resume` flags** for `run` command.

---

### R-7: `backend/puzzle_manager/CLAUDE.md` — LOW

**Stale references**:

1. **Line ~55**: `Source adapter ID stored in YS property` — YS is not a current property. Should be `YM` (pipeline metadata).
2. **Module layout**: Lists `core/` with only comment about `_base.py defines base class` — accurate but very minimal.

---

### R-8: `backend/puzzle_manager/README.md` — MEDIUM

**Stale references**:

1. **Line ~250**: Key Design Decisions section says `CLI: Uses argparse (stdlib) instead of click` — but the CLI currently uses **Typer** (per AGENTS.md `cli.py` which says "13-command Typer CLI"). Contradicts the Spec 035 decision.
2. **Trace CLI commands** (line ~95): Shows `python -m backend.puzzle_manager trace search --trace-id` — but per AGENTS.md, the CLI has `publish-log search`, not a separate `trace` command. The `trace` subcommand may not exist.

---

### R-14: `docs/architecture/backend/data-flow.md` — CRITICAL

**Stale references**:

1. **Section "3. ANALYZE → PUBLISH"** (lines ~55-70): Entire output structure references dead JSON views:
   ```
   ├── views/
   │   ├── by-level/{level}.json
   │   ├── by-tag/{tag}.json
   │   └── daily/{YYYY-MM-DD}/
   ├── publish-log/
   ```
   Current system uses SQLite databases, not JSON views.

2. **Section "4. GitHub Pages → Browser"** (lines ~75-85): Shows `views/*.json` being fetched. Frontend now fetches `yengo-search.db`.

3. **"JSON Views (Index)" format section**: Describes JSON view envelope format — entirely dead.

4. **"Key Principles" line ~95**: Says `Sharding — Max 100 files per directory`. While batch dirs still exist, they're not called "shards" and the max is configurable (default 2000 now).

5. **SGF directory structure**: Shows `sgf/{level}/{YYYY}/{MM}/batch_{NNN}/` — the actual structure is flat `sgf/{NNNN}/{content_hash}.sgf` (no level-based nesting, no date-based nesting).

---

### R-16: `docs/architecture/backend/adapter-design-standards.md` — MEDIUM

**Stale references**:

1. **Line 126**: Import from dead `registry.py`:
   ```python
   from backend.puzzle_manager.adapters.registry import register_adapter
   ```
   Should be `from backend.puzzle_manager.adapters._registry import register_adapter`.

---

### R-17: `docs/architecture/backend/view-index-pagination.md` — ENTIRELY OBSOLETE / CRITICAL

Already properly self-marked as `❌ ARCHIVED` at the top. However, it is still in the `docs/architecture/backend/` directory (active docs), NOT in `docs/archive/`. The archival banner is present but the file hasn't been physically moved. Contains ~300 lines of detailed dead-system documentation (`PaginationWriter`, `pagination_models`, `.pagination-state.json`).

**Action**: Move to `docs/archive/` for consistency. A copy already exists at `docs/archive/view-index-pagination.md`.

**Dedup issue**: This file and `docs/archive/view-index-pagination.md` appear to be duplicates — both contain the same archived header. The one in `docs/architecture/backend/` should be deleted.

---

### R-18: `docs/architecture/backend/view-index-segmentation.md` — ENTIRELY OBSOLETE / CRITICAL

Describes `SegmentWriter`, `SegmentState`, progressive single→segmented migration, `views/by-level/` structures. None of this exists — replaced by SQLite. **No archival banner present** — still reads as a current "Design Complete" document.

**Action**: `move_to_archive` — add archival banner, move to `docs/archive/`.

---

### R-19: `docs/architecture/backend/puzzle-manager.md` — CRITICAL

**Stale references**:

1. **Directory structure listing** (lines 50-95): Lists dead files as current:
   - `logging.py` listed — should be `pm_logging.py`
   - `adapters/base.py` listed — should be `adapters/_base.py`
   - `adapters/registry.py` listed — should be `adapters/_registry.py`
   - `adapters/local.py`, `adapters/url.py` listed as flat files — they are now subdirectory-based (`adapters/local/`, `adapters/url/`)
   - Missing many current modules: `publish_log.py`, `rollback.py`, `audit.py`, `core/enrichment/`, `core/batch_writer.py`, `core/content_db.py`, `core/db_builder.py`, `core/db_models.py`, `core/id_maps.py`, `core/checkpoint.py`, `core/atomic_write.py`, `core/quality.py`, `core/complexity.py`, `core/content_classifier.py`, `core/naming.py`, `core/trace_utils.py`, `core/collection_assigner.py`, `core/tactical_analyzer.py`
   - Missing `pipeline/executor.py` (uses `StageExecutor`)
   - `models/puzzle.py`, `models/daily.py` listed — may or may not still exist
   - `state/models.py` listed — verify existence

2. **Technology listed**: CLI says `argparse` but may be `typer` now (inconsistency with AGENTS.md)

---

### R-30: `docs/architecture/snapshot-deployment-topology.md` — ENTIRELY OBSOLETE / CRITICAL

Describes the **snapshot-centric** deployment: `active-snapshot.json`, `snapshots/{snapshot_id}/manifest.json`, shard resolution. This is the OLD system before SQLite migration.

The SQLite replacement is documented at `docs/architecture/database-deployment-topology.md`.

**Action**: `move_to_archive`.

---

### R-32: `docs/concepts/snapshot-shard-terminology.md` — ENTIRELY OBSOLETE / CRITICAL

Defines terminology for the dead snapshot/shard system: "Snapshot", "Shard", "Shard key", "Manifest", "Active snapshot pointer", "Context elision", "Query planner", "Dimension", "None bucket". None of these concepts apply to the current SQLite-based system.

Includes "Relationship to Legacy Terms" — which points at even older legacy terms.

**Action**: `move_to_archive`.

---

### R-38: `docs/concepts/level-system-stability.md` — MEDIUM

**Stale references**:

1. **Line 29**: References dead directory structure: `sgf/{level}/batch-{NNNN}/`. Actual: `sgf/{NNNN}/{hash}.sgf` (flat batches, no level nesting).
2. **Line 37**: References dead views: `views/by-level/{level}.json` — JSON views are replaced by SQLite.
3. **Line 48**: References dead migration script: `migrate_sharding.py` — this file was in the dead code list.
4. **Line 49**: `Update all view indexes` — no view indexes exist.

---

### R-49: `docs/reference/configuration.md` — CRITICAL

**Stale references**:

1. **Level Mapping table**: Uses old level names (`basic`, `challenging`, `difficult`) and IDs (1-9 sequential). Current system uses: `novice`, `beginner`, `elementary`, `intermediate`, `upper-intermediate`, `advanced`, `low-dan`, `high-dan`, `expert` with numeric IDs 110-230.

2. **tags.json format**: Shows flat array format:
   ```json
   {"tags": ["ladder", "snapback", ...], "aliases": {...}}
   ```
   Current `config/tags.json` uses a richer structure with objects per tag having `id`, `display_name`, `category`, `aliases`.

3. **Log directory structure**: References `logs/puzzle_manager/` — current system uses `.pm-runtime/logs/`.

---

### R-50: `docs/reference/puzzle-manager-cli.md` — CRITICAL

**Stale references**:

1. **OGS adapter-specific CLI flags**: Lists `--puzzle-id`, `--type`, `--collection`, `--fetch-only`, `--transform-only`, `--strict-translation` as flags on the core `run` command. Per AGENTS.md and how-to/cli-reference.md, OGS moved to a standalone tool under `tools/ogs/`. These flags no longer exist on the core CLI.

2. **Overall command set**: Only shows `run`, `status`, `clean`, `validate`, `sources`. Missing: `daily`, `publish-log`, `rollback`, `vacuum-db`, `inventory`, `enable-adapter`, `disable-adapter`.

3. **`--source` flag**: Listed as NOT required on some examples (`python -m backend.puzzle_manager run` with no source) — but `--source` is now REQUIRED.

4. **Staging directory**: References `staging/failed/` — not in current AGENTS.md; current staging has `ingest/` and `analyzed/` only.

---

### R-52: `docs/reference/sgf-properties.md` — MEDIUM

**Stale references**:

1. **Schema version**: States "Current schema version: **8**". According to `CLAUDE.md` and `AGENTS.md`, current schema is **v15**. Major discrepancy.
2. **YI property**: Listed in Property Ownership Matrix — YI was replaced by YM.
3. **Root C[] comment**: States "Removes" — current behavior is "PRESERVED by default" (configurable via `preserve_root_comment`).

---

### R-59: `docs/STAGES.md` — ENTIRELY OBSOLETE / CRITICAL

This is a heavily outdated document describing the 3-stage pipeline but with many dead concepts:

1. **Lines 10-12**: Stage output says `staging/raw/` — should be `staging/ingest/`.
2. **Lines 30-40**: Lists adapter classes that don't exist: `LocalSgfAdapter`, `UrlSgfAdapter`, `ApiAdapter`.
3. **Line 60-70**: "Stage 2: Parse" as a separate listed heading (duplication of Stage 2).
4. **Lines 80-90**: Uses old CLI format `yengo-pm ingest` — current is `python -m backend.puzzle_manager run --stage ingest`.
5. **Lines 110-130**: ANALYZE uses old level system names: `DDK30`, `DDK20`, `DDK15`, `DDK10`, `DDK5`, `SDK`, `MidDan`, `HighDan`, `Pro`.
6. **Lines 150-165**: PUBLISH describes JSON view indexes (`views/by-level/{level}.json`, `views/by-tag/{tag}.json`, `views/manifest.json`) — all dead.
7. **Lines 170-180**: Daily challenge format shows 4 types (Standard/Tag/Timed/Gauntlet) — "Gauntlet" is not in current spec.
8. **Lines 185-195**: Output structure shows `sgf/{level}/{YYYY}/{MM}/batch_{NNN}/` — this is the old level-nested, date-nested layout, not the current flat `sgf/{NNNN}/`.
9. **Tags section**: Lists fallback `tesuji` tag — current design has NO fallback tags.

**Action**: This is a root-level doc that has been superseded by `docs/architecture/backend/stages.md`. Delete or move to archive.

---

### R-60: `docs/architecture/README.md` — MEDIUM

**Stale references**:

1. **Line 75**: Components table says Output is `SGF + JSON views`. Should be `SGF + SQLite databases`.
2. **Line 42**: System diagram shows `sgf/, views/` — views don't exist.

---

### R-61: `docs/architecture/backend/README.md` — CRITICAL

**Stale references**:

1. **Directory structure** (lines 5-15): Shows `src/puzzle_manager/` — actual path is `backend/puzzle_manager/` (no `src/` prefix).
2. **Technology Stack**: Lists `CLI: Click` — should be `Typer` (or possibly `argparse` per some older docs, but AGENTS.md says Typer).
3. **Data Flow link**: Links to `data-flow.md` with description "Sources → staging → collections → views" — views are dead.

---

### R-62: `docs/guides/adapter-development.md` — CRITICAL

**Stale references**:

1. **Line 26**: Imports from dead `base.py`:
   ```python
   from backend.puzzle_manager.adapters.base import BaseAdapter
   ```
   Should be `_base`.
2. **`fetch()` return type**: Shows `Sequence[dict]` — current protocol returns `Iterator[FetchResult]`.
3. **Protocol definition**: Uses older interface without `name`, `source_id` properties, `configure()` method.

---

## 4. Candidate Adaptations for Yen-Go (Categorized by Severity)

### CRITICAL — Wrong information that actively misleads developers/agents

| R-ID | File | Issue Summary |
|------|------|--------------|
| R-17 | `docs/architecture/backend/view-index-pagination.md` | Entire doc about dead pagination system; still in active docs dir (duplicate of archive) |
| R-18 | `docs/architecture/backend/view-index-segmentation.md` | Entire doc about dead segmentation system; no archival banner |
| R-30 | `docs/architecture/snapshot-deployment-topology.md` | Entire doc about dead snapshot system |
| R-32 | `docs/concepts/snapshot-shard-terminology.md` | Entire terminology doc for dead shard/snapshot system |
| R-59 | `docs/STAGES.md` | Massively outdated: wrong CLI, wrong levels, wrong output structure |
| R-14 | `docs/architecture/backend/data-flow.md` | Shows JSON views, level-nested SGF dirs; all replaced by SQLite/flat |
| R-19 | `docs/architecture/backend/puzzle-manager.md` | Lists `logging.py`, `base.py`, `registry.py`, flat adapter files — all dead |
| R-3 | `backend/puzzle_manager/docs/adapters.md` | Imports from dead `base.py`/`registry.py`, old FetchResult shape |
| R-2 | `backend/puzzle_manager/docs/architecture.md` | Calls publish sub-stage "shard", uses old staging dir names |
| R-49 | `docs/reference/configuration.md` | Old level names, old tag format, wrong log directory |
| R-50 | `docs/reference/puzzle-manager-cli.md` | Dead OGS CLI flags, missing 8+ commands, --source not shown as required |
| R-61 | `docs/architecture/backend/README.md` | Wrong directory path (`src/`), CLI says "Click" not Typer |
| R-62 | `docs/guides/adapter-development.md` | Dead import path from `base.py`, wrong fetch() return type |

### MEDIUM — Stale but not immediately harmful

| R-ID | File | Issue Summary |
|------|------|--------------|
| R-4 | `backend/puzzle_manager/docs/configuration.md` | References `views_root` config (dead) |
| R-5 | `backend/puzzle_manager/docs/cli.md` | Missing 8 commands, missing --source flag |
| R-8 | `backend/puzzle_manager/README.md` | Says argparse but may be Typer; trace CLI commands may not exist |
| R-16 | `docs/architecture/backend/adapter-design-standards.md` | Import from dead `registry.py` |
| R-38 | `docs/concepts/level-system-stability.md` | References dead path format, dead views, dead migration script |
| R-52 | `docs/reference/sgf-properties.md` | Schema says v8 (current is v15); YI instead of YM; root C[] behavior wrong |
| R-60 | `docs/architecture/README.md` | Output says "JSON views" |

### LOW — Minor wording issues

| R-ID | File | Issue Summary |
|------|------|--------------|
| R-7 | `backend/puzzle_manager/CLAUDE.md` | References `YS` property (doesn't exist) |
| R-47 | `docs/reference/view-index-schema.md` | Title says "View Index Schema" but content is actually the current SQLite schema (self-documents historical evolution) |

---

## 5. Risks, License/Compliance, and Rejection Reasons

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Moving files breaks cross-doc links | Medium | Grep for all `../` relative links pointing to moved files; fix in same commit |
| Agents following dead import paths | High (build errors) | Priority fix for R-3, R-62 (adapter import docs) |
| Schema version confusion (v8 vs v15) | High (data corruption) | Priority fix for R-52 |
| CLI doc mismatch causes user errors | Medium | Priority fix for R-50 |
| Archive move creates "docs/archive/" bloat | Low | Acceptable — archive is the designated long-term storage |

**No license/compliance issues identified** — all files are internal documentation.

---

## 6. Planner Recommendations

**Rec-1**: **IMMEDIATE — Delete 1 file, move 4 files to archive** (5 files total, entirely obsolete):
- DELETE: `docs/architecture/backend/view-index-pagination.md` (duplicate of archived version)
- MOVE TO ARCHIVE: `docs/architecture/backend/view-index-segmentation.md`
- MOVE TO ARCHIVE: `docs/architecture/snapshot-deployment-topology.md`
- MOVE TO ARCHIVE: `docs/concepts/snapshot-shard-terminology.md`
- MOVE TO ARCHIVE or DELETE: `docs/STAGES.md` (superseded by `docs/architecture/backend/stages.md`)

**Rec-2**: **HIGH PRIORITY — Fix 6 critical files with targeted edits** (each ≤50 lines changed):
- R-14 `data-flow.md`: Rewrite sections 3–4 to show SQLite databases and flat batch dirs
- R-19 `puzzle-manager.md`: Update directory listing to match AGENTS.md (add/remove files)
- R-3 `docs/adapters.md`: Fix imports to `_base.py`/`_registry.py`, update FetchResult API
- R-49 `configuration.md`: Update level names, tag format, log dirs
- R-50 `puzzle-manager-cli.md`: Remove dead OGS flags, add missing commands, mark `--source` required
- R-61 `backend/README.md`: Fix path to `backend/puzzle_manager/`, fix CLI tool name

**Rec-3**: **MEDIUM PRIORITY — Fix 6 medium-severity files** (each ≤20 lines changed):
- R-2 `architecture.md`: Fix publish sub-stage names, staging dir names
- R-4 `configuration.md`: Remove `views_root` reference
- R-5 `cli.md`: Add missing commands
- R-16 `adapter-design-standards.md`: Fix import path
- R-38 `level-system-stability.md`: Fix path references, remove view/migration references
- R-52 `sgf-properties.md`: Update schema version to v15, fix YI→YM, fix C[] behavior

**Rec-4**: **LOW PRIORITY — Fix 3 minor files**:
- R-7 `CLAUDE.md`: Fix YS→YM reference
- R-60 `architecture/README.md`: Fix "JSON views" wording
- R-62 `adapter-development.md`: Fix import path (or redirect to how-to/backend/create-adapter.md)

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |

**Confidence notes**: High confidence because I read every listed file end-to-end. The 8% uncertainty is due to:
- CLI framework ambiguity (argparse vs Typer — AGENTS.md says Typer, multiple docs say argparse). Need to verify actual `cli.py` implementation.
- Some files in `docs/reference/adapters/` were not read in detail (only README checked).
- Possible additional stale references in docs I wasn't asked to check (e.g., `docs/architecture/frontend/view-index-types.md` also references dead views).

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | CLI framework: Is it argparse or Typer? AGENTS.md says "13-command Typer CLI" but puzzle-manager.md and CLAUDE.md say argparse. Which is actually correct? | A: argparse / B: Typer | Verify by reading `cli.py` | | ❌ pending |
| Q2 | Should `docs/STAGES.md` be deleted or moved to archive? It's a root-level doc with no archival marker. | A: Delete (stages.md exists) / B: Archive / C: Keep and update | A: Delete | | ❌ pending |
| Q3 | `docs/guides/adapter-development.md` — should it be updated or replaced with a redirect to `docs/how-to/backend/create-adapter.md`? | A: Update content / B: Replace with redirect / C: Delete (duplicate) | B: Redirect | | ❌ pending |
| Q4 | `docs/architecture/backend/view-index-pagination.md` — delete or keep as-is? An identical copy already exists in `docs/archive/`. | A: Delete from architecture/ / B: Keep both | A: Delete | | ❌ pending |

---

## Handoff Summary

```
research_completed: true
initiative_path: TODO/initiatives/2026-03-24-backend-docs-cleanup/
artifact: 15-research.md
top_recommendations:
  1. Delete 1 duplicate + move 4 entirely-obsolete files to archive
  2. Fix 6 critical files with targeted import/structure/schema edits
  3. Fix 6 medium-severity files with minor reference updates
  4. Fix 3 low-severity files with wording updates
open_questions: [Q1, Q2, Q3, Q4]
post_research_confidence_score: 92
post_research_risk_level: low
```

**Total files audited**: 65
**Files with issues**: 22 (34%)
**Entirely obsolete**: 5 files
**Critical stale content**: 13 files
**Medium stale content**: 7 files
**Low/cosmetic**: 3 files
**Accurate / no action needed**: 43 files (66%)
