# Manage Per-Source Ingest DB

How to inspect, reset, and troubleshoot the per-source ingest state database
(`.yengo-ingest.sqlite`).

**Last Updated:** 2026-05-03

> **See also:**
>
> - [Architecture: Source Ingest Database](../../architecture/backend/source-ingest-db.md) — design rationale, schema, lifecycle.
>
> - [Concepts: SQLite Index Architecture](../../concepts/sqlite-index-architecture.md) — terminology, the three databases.
>
> - [How-To: CLI Reference](./cli-reference.md) — full pipeline commands.

## What it is

Each external source folder gets its own SQLite file at
`<source.path>/.yengo-ingest.sqlite`. It tracks every file the ingest stage
has seen, its content hash, and its status (`ingested` / `skipped` / `failed`).
This is the single source of truth for resume and content-aware skip — no other
state is consulted.

It is created automatically on first ingest. There is no manual init step.

## Inspect status

```bash
# All sources
python -m backend.puzzle_manager source-status

# One source
python -m backend.puzzle_manager source-status t-hero
```

Output (text):

```text
Per-Source Ingest DB Status
==============================================================================
  t-hero (local)
    db: external-sources/t-hero/sgf/.yengo-ingest.sqlite  (412.0 KB, schema v1)
    files: total=4823  ingested=4823  skipped=0  failed=0
    last modified: 2026-05-03T11:42:17
Tip: open .yengo-ingest.sqlite directly with sqlite3 for ad-hoc queries.
```

For ad-hoc queries (per-row history, failed reasons, last `run_id`) open the
file directly:

```bash
sqlite3 external-sources/t-hero/sgf/.yengo-ingest.sqlite \
  "SELECT status, COUNT(*) FROM files GROUP BY status;"

sqlite3 external-sources/t-hero/sgf/.yengo-ingest.sqlite \
  "SELECT rel_path, skip_reason FROM files WHERE status = 2 LIMIT 20;"
```

## Force a full re-ingest (`--fresh`)

`--fresh` wipes the per-source ingest DB **and** `.pm-runtime/state` (since the
in-flight pipeline state is meaningless once the ingest cursor is gone) before
running:

```bash
python -m backend.puzzle_manager run --source t-hero --fresh
```

Output starts with:

```text
[fresh] wiped SourceIngestDB for 't-hero' at .../external-sources/t-hero/sgf
[fresh] wiped 3 runtime state file(s) under .pm-runtime/state
```

Without a `--source`, `--fresh` wipes the DB for every configured source.

## Resume after Ctrl-C / crash

Just re-run the same command. Resume is always-on; the next walk re-stats every
file, recomputes `content_hash`, and skips anything whose hash matches the stored
row.

```bash
python -m backend.puzzle_manager run --source t-hero
```

The `--resume` flag exists for backward compatibility but is a no-op.

## Detect renames

If a file moves within the source folder (no content change), the next ingest
detects it via `content_hash` lookup and updates the row in place — no
re-publish, no duplicate.

This works automatically. No flag needed. See the
[architecture doc](../../architecture/backend/source-ingest-db.md#rename-detection)
for the exact tiebreak rules.

## Common issues

| Symptom | Cause | Fix |
| --- | --- | --- |
| `SourceIdMismatchError` on open | DB was created for a different `source_id` (e.g. you renamed the source). | Move or wipe the DB: `python -m backend.puzzle_manager run --source <id> --fresh`. |
| `SchemaVersionError: db is newer than code` | You downgraded `puzzle_manager`. | Upgrade back, or wipe with `--fresh` (loses skip history). |
| `database is locked` warnings on Windows | AV/indexer holding WAL files. | The DB uses `busy_timeout=5000` and retries. If persistent, exclude `external-sources/` from your AV scanner. |
| Stale rows after deleting files from disk | Tier-3 rehash never sees the file again, so the row stays. | Cosmetic only — rows do not affect publish. Wipe via `--fresh` if you care. |
| First run after legacy migration re-processes every file | Migrator seeds `meta` only, not per-file rows. The next walk re-stats, re-hashes, and re-records every file. | **Expected behavior.** One-time cost (~10 min for 50k files). Publish-stage dedup against `yengo-content.db` prevents any duplicate output. |
| Re-run reports `[OK] '<id>' is already up to date — no new puzzles found.` and exits without analyze/publish | The per-source ingest DB has matching rows for every file on disk. Ingest finds 0 new, downstream stages short-circuit as no-ops. | **Expected.** Add new files to the source folder, or use `--fresh` to wipe the DB and reprocess. See [Up-to-date detection](../../architecture/backend/source-ingest-db.md#up-to-date-detection). |

## Backup and portability

The DB lives next to the source data. Copy or move the source folder and the DB
travels with it. There is no global registry to keep in sync.

For backup, snapshot `external-sources/<source-dir>/` as a whole. WAL/SHM
sidecars (`.yengo-ingest.sqlite-wal`, `.yengo-ingest.sqlite-shm`) are transient
and safe to skip.

## Removed surface

These options no longer exist as of the SourceIngestDB migration:

- `resume: true` / `resume: false` in `sources.json` config — stripped on load

  with a one-time WARNING.

- `core.checkpoint.AdapterCheckpoint` and the legacy

  `.pm-runtime/state/<source_id>_checkpoint.json` files.

- The `_compute_config_signature()` MD5 drift warning (was never actionable).
