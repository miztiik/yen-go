# Source Ingest Database

> Per-external-source SQLite database that owns ingest state, resume, content-aware skip, and rename detection. Replaces the legacy positional `AdapterCheckpoint` JSON.

Last Updated: 2026-05-03

## Why

The pipeline previously tracked per-source ingest progress in a positional JSON file (`AdapterCheckpoint`) plus several in-memory sets (`_processed_ids`, `_processed_files`) and a config-signature MD5 for drift warnings. That design has four real problems:

1. **Positional, not content-aware.** Reordering `include_folders` silently invalidates the cursor.
2. **Repeated work on resume.** Even if a file was already processed, re-running re-reads, re-hashes, and (without other guards) re-publishes it.
3. **Windows file-locking workarounds.** A per-batch JSON checkpoint flush has special-cased intervals to avoid antivirus/indexer locking.
4. **No queryable history.** "Which files failed and why?" is invisible.

A small, co-located SQLite per source solves all four with one well-known mechanism (SQLite + WAL) and lets us delete code rather than add to it.

## Non-goals

- Cross-source dedup. That stays at publish time via `yengo-content.db` and `position_hash` (see `docs/concepts/dedup-hashing.md`).
- Run history / cross-source state. The global `current_run.json` keeps that.
- Frontend impact. The browser never reads this DB.

## Placement and lifecycle

One file per external source, co-located with the source data:

```
external-sources/<source-dir>/.yengo-ingest.sqlite
external-sources/<source-dir>/.yengo-ingest.sqlite-wal   (transient)
external-sources/<source-dir>/.yengo-ingest.sqlite-shm   (transient)
```

Properties:

- Travels with the source folder (copy/move/share is portable).
- Dotfile prefix → ignored by the adapter walk (already filters `name.startswith(".")`).
- `.gitignore` adds `**/.yengo-ingest.sqlite*`.
- Created on first ingest. Wiped by `--fresh`. Otherwise long-lived.

Alternative considered: `.pm-runtime/sources/<id>/ingest.sqlite`. Rejected because it loses portability and is destroyed by runtime cleanup.

## Schema (v1)

```sql
-- File: <source.path>/.yengo-ingest.sqlite
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE files (
    rel_path     TEXT PRIMARY KEY,    -- POSIX, source-root relative
    content_hash TEXT NOT NULL,       -- SHA256(raw_sgf)[:16]
    size_bytes   INTEGER NOT NULL,
    mtime_ns     INTEGER NOT NULL,
    status       INTEGER NOT NULL,    -- 0=ingested, 1=skipped, 2=failed
    skip_reason  TEXT,                -- nullable, only meaningful when status != 0
    run_id       TEXT NOT NULL        -- run that last touched this row
) WITHOUT ROWID;

CREATE INDEX idx_files_hash   ON files(content_hash);
CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_files_run    ON files(run_id);
```

Required `meta` rows on creation:

| key | value |
|---|---|
| `schema_version` | `"1"` |
| `ingest_db_format` | `"yengo-source-ingest"` |
| `source_id` | `<source.id>` |
| `created_run_id` | first `run_id` |
| `last_run_id` | latest `run_id` |
| `last_run_at` | ISO 8601 UTC |

No denormalized counters. Progress queries run live against `files` (sub-ms with `idx_files_status` even at 100k rows).

Per-row size ≈ 70 bytes. 100k rows ≈ 7 MB on disk including indexes.

## Hash choice

`content_hash` here is the **same** hash the rest of the pipeline uses for `GN`/filename — `core.naming.generate_content_hash()`, which is `SHA256(raw_sgf_bytes)[:16]` ([core/naming.py](../../../backend/puzzle_manager/core/naming.py)).

Not `position_hash` — that requires parsing the SGF first, which defeats the cheap-path goal here. `position_hash` remains the cross-source dedup key at publish time.

## Skip logic (correctness-first)

For each file walked under `include_folders` / `exclude_folders`:

1. `stat()` → `(size_bytes, mtime_ns)`.
2. Look up `rel_path` in `files`. If missing → check rename (see below); else proceed as new.
3. If `(size_bytes, mtime_ns)` match the stored row → **still re-read the file and recompute `content_hash`**.
4. If recomputed hash matches stored → confirmed unchanged → skip downstream stages, update `last_run_id` only.
5. Otherwise → treat as changed → re-ingest.

The Tier-3 always-rehash policy is the v1 default. It eliminates platform-dependent mtime precision concerns (NTFS, FAT32, NFS, copies that preserve mtime, etc.). Cost on 100k files is ~25 MB of sequential reads — bounded and dwarfed by the analyze/enrich work it lets us skip. A `--trust-mtime` fast path may be added later if measurement shows it matters.

## Rename detection

When a walked file's `rel_path` is not in `files`, before treating as new:

1. Look up by `content_hash`.
2. If a row exists for an old `rel_path` and that path no longer exists on disk → it is a rename. Update the row's `rel_path` to the new value, set `last_run_id`. Do not re-ingest.
3. If multiple rows match the hash → tiebreak by most recent `run_id`.
4. If both old and new paths exist on disk with the same hash → it is a copy, not a rename. Treat the new path as a new file (publish dedup will drop it as a duplicate position later).

## Resume semantics

There is no separate checkpoint table. The `files` rows are the checkpoint:

```sql
-- Progress (live)
SELECT status, COUNT(*) FROM files GROUP BY status;

-- Resume cursor (informational only — walk is content-driven, not positional)
SELECT rel_path, run_id FROM files ORDER BY rowid DESC LIMIT 1;
```

A crash mid-batch loses at most one transaction's worth of inserts (we commit per batch, not per file, with a default flush interval). On restart the walker re-stats everything; previously committed rows skip cheaply.

The global `--resume` flag on `run` is unaffected — it still restores `current_run.json` for cross-source pipeline state.

## CLI surface

| Command | Effect |
|---|---|
| `run --source <id>` | Default. Always resumes from the SQLite. |
| `run --source <id> --fresh` | Wipes `.yengo-ingest.sqlite` for the selected source(s) AND `.pm-runtime/state`, then runs from scratch. |
| `run --resume` | Silent no-op. Resume is always-on; flag retained for backward compatibility / muscle memory. |
| `source-status [<id>]` | Prints per-source counts by status (ingested/skipped/failed), DB size, schema version, last modified. Text only — open `.yengo-ingest.sqlite` directly with `sqlite3` for ad-hoc queries. |

The `resume: true/false` key in `sources.json` is removed (always-on). The Pydantic loader strips the field with a one-time WARNING per source on first load after upgrade.

## Read/write boundaries

| Component | Reads | Writes |
|---|---|---|
| `core/source_ingest_db.py` (new) | — | owns the schema, `open()`, `upsert()`, `mark_failed()`, `find_by_hash()`, `progress()`, `wipe()` |
| `stages/ingest.py` | passes `run_id` and `source.id` into adapter config (see [Identity injection](#identity-injection)) | — |
| Local + Sanderland adapters | per-file lookup, rename probe | per-file upsert (batched commit) |
| CLI `source-status` | `progress()` + `meta` | — |
| `yengo-content.db` / publish | unaffected | unaffected |

Adapter → `core/` import is allowed by `.claude/rules/03-architecture-rules.md`. `core/` does not depend on adapters. No layering violation.

## Identity injection

The per-source DB stamps `meta.source_id` on creation. That value MUST equal
`source.id` from `sources.json` so that `source-status <id>` can re-open it
without `SourceIdMismatchError`.

This is non-trivial because some adapters serve multiple sources. For example,
`LocalAdapter` is used by `t-hero`, `ogs`, `kisvadim-goproblems`,
`harada-tsumego`, etc. The adapter's own `source_id` property returns its
hardcoded short name (`"local"`, `"sanderland"`) — not the per-instance
identity.

So `IngestStage.run()` injects two private keys into adapter config before
calling `create_adapter(...)`:

| Key | Source | Purpose |
|---|---|---|
| `_run_id` | `context.run_id` | Stamps the `run_id` column on every upserted row. |
| `_source_id` | `source.id` (from `sources.json`) | Stamps `meta.source_id` on DB creation; resolves which DB to open. |

Adapters honor `config["_source_id"]` first, fall back to `config["id"]`
(legacy override used by some test fixtures), and finally to the hardcoded
default. The `_source_id_override` instance attribute then takes priority in
the `source_id` property.

**Pitfall:** Calling `SourceIngestDB.open(path, source_id=self.source_id, ...)`
directly with the adapter's hardcoded property silently creates a DB stamped
with the wrong identity. The CLI later fails with
`DB belongs to source_id='local', but caller passed source_id='t-hero'`.
Always pass through the IngestStage-injected value.

## Up-to-date detection

A steady-state re-run — the user already ingested everything for a source —
used to surface as `[FAIL] Pipeline failed` because the analyze stage's
prerequisite check fired "No puzzles in staging/ingest/". This was wrong
classification: the pipeline did exactly what it should, there was just nothing
new to do.

The pipeline now distinguishes "no-op success" from "failure":

| Layer | Behavior |
|---|---|
| Adapter `fetch()` | When `yielded == 0` AND `progress.ingested > 0`, logs `"source '<id>' is up to date — 0 new files (DB: ingested=N, skipped=M, failed=K). Use --fresh to reprocess."`. Returns normally. |
| `IngestStage` | Returns `StageResult.partial_result(processed=0, ...)` — success, but with no work done. |
| `PipelineCoordinator` | Detects that the prior executed stage succeeded with `processed == 0, failed == 0`. Short-circuits the next stage with `StageResult.noop_result(reason)` instead of letting its prerequisite check fire. Records the no-op in run state so `status` doesn't show PENDING. |
| `PipelineResult.up_to_date` | True iff every executed stage succeeded with `processed == 0, failed == 0`. |
| CLI summary | When `up_to_date`, prints `[OK] '<id>' is already up to date — no new puzzles found.` plus a `--fresh` tip. **Exit code 0** (was 1 before — critical for CI/scripts). |

Duplicate handling on re-run is a non-event: files whose `(rel_path,
content_hash)` already exist in the per-source DB are passed over before they
reach the global dedup logic. Only `--fresh` (which wipes the per-source DB)
forces them through dedup again.

## What this lets us delete

- `AdapterCheckpoint` module (positional JSON checkpoint writer/reader).
- `_processed_ids: set[str]` and `_processed_files: set[str]` in adapters (the latter is already dead code).
- `_compute_config_signature()` MD5 + drift warnings.
- Per-batch JSON checkpoint flush + Windows PermissionError mitigations (`checkpoint_interval = 10`).
- `resume` config key plumbing in `config/loader.py` and `sources.schema.json`.

Estimated removal: 150–200 lines across both adapters and the checkpoint module.

## One-shot migration

On first run after upgrade, for each source:

1. If `.yengo-ingest.sqlite` already exists → no migration needed.
2. Else if `.pm-runtime/state/<source_id>_checkpoint.json` exists → create the SQLite, seed `meta` from the JSON's `total_processed` / `total_failed` counts as historical context (no per-file rows; future walks will populate them on hash verification), then delete the JSON.
3. Else → fresh DB.

Migrator is idempotent. `--fresh` short-circuits step 2 by wiping both artifacts.

## Schema evolution

- New JSON Schema: `config/schemas/db-source-ingest.schema.json` (mirrors `db-content.schema.json` and `db-search.schema.json`).
- In-DB `meta.schema_version` is checked on `open()`. If older, a migrator chain runs: `migrate_v1_to_v2`, etc. If newer than the code knows, refuse to open and ask the user to upgrade puzzle_manager.

## Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Windows AV/indexer locking SQLite WAL files | Medium | `PRAGMA busy_timeout=5000`. Tested in Phase 6 on Windows. |
| Third-party tools globbing `*.sqlite` in `external-sources/` | Low | Dotfile prefix (`.yengo-`) + `.gitignore`. Documented in ops guide. |
| Migrator partial failure leaves both old and new state | Low | Idempotent migrator; `meta.created_run_id` acts as completion marker. |
| `content_hash` collision (64-bit) at 50k files | ~10⁻¹⁰ | Negligible. Same hash already used pipeline-wide. |
| Concurrent two-process access to one source DB | Low | WAL mode + `busy_timeout`. Concurrency test covers this in Phase 1. |

## Phased plan

- **Phase 0 — Governance** (complete; approved with conditions, conditions resolved here).
- **Phase 1** — `core/source_ingest_db.py`, `db-source-ingest.schema.json`, unit tests (open, migrate, upsert, rename, mtime fallback, concurrent reader). No wiring.
- **Phase 2a** — Wire **local** adapter to `SourceIngestDB`. Update local adapter tests. Add resume-after-Ctrl-C / resume-after-rename / resume-after-folder-reorder integration tests against the local adapter.
- **Phase 2b** — Wire **sanderland** adapter (mirror of 2a). Update sanderland adapter tests.
- **Phase 2c** — Delete obsolete code paths now that both adapters are wired:
  - `AdapterCheckpoint` module and its test file `backend/puzzle_manager/tests/integration/test_adapters.py::TestAdapterCheckpoint` (the test asserts on `_checkpoint`/`_processed_files` which no longer exist).
  - `_processed_ids` and `_processed_files` in both adapters.
  - `_compute_config_signature` MD5 + drift warnings.
  - Per-batch JSON checkpoint flush + Windows `PermissionError` mitigations (`checkpoint_interval = 10`).
- **Phase 3** — CLI + config cleanup:
  - `--fresh` plumbing.
  - `source-status` command (with `--json`).
  - Remove `resume` key from `sources.json` and `sources.schema.json`.
  - Strip + one-time deprecation warning in `config/loader.py`.
  - Remove the `adapter_config["resume"] = True` injection block in `IngestStage.run()` (now redundant — DB is always-on).
- **Phase 4** — Docs and meta updates: this file (already), `docs/how-to/backend/manage-source-ingest-db.md` (new), `docs/concepts/sqlite-index-architecture.md` (mention third DB), `backend/puzzle_manager/AGENTS.md`, root + backend `CLAUDE.md`, `.gitignore`, `/memories/repo/source-ingest-db.md`.
- **Phase 5** — One-shot migrator for legacy JSON.
- **Phase 6** — Validation: `pytest backend/ -m "not (cli or slow)"`, manual t-hero `--fresh` then Ctrl-C resume test (covers Windows AV/indexer risk).

## See also

- [Concepts: SQLite Index Architecture](../../concepts/sqlite-index-architecture.md) — terminology, the three databases.
- [Concepts: Dedup Hashing](../../concepts/dedup-hashing.md) — why `position_hash` (not `content_hash`) is the cross-source dedup key.
- [Architecture: Adapter Design Standards](./adapter-design-standards.md) — adapter contract that this work preserves.
- [Architecture: Pipeline](./pipeline.md) — where ingest sits in the 3-stage flow.
- [Reference: Documentation Structure](../../reference/documentation-structure.md) — placement rules for this doc.
