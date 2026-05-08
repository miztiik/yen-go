# How to Run yengo_dashboard

> Browser cockpit over `backend/puzzle_manager`. Mutations are live: pipeline
> runs, taxonomy rename/merge, adapter config edits, source-ingest-state reset,
> rollback, vacuum-db, and daily-schedule generation are all driven from the UI.

**Tier**: How-to (the *do this*).
**See also**: [Architecture: yengo_dashboard](../../architecture/tools/yengo_dashboard.md).

---

## Quick start

From the repo root:

```bash
python -m tools.yengo_dashboard
```

Open <http://127.0.0.1:8201/> in your browser.

## Flags

| Flag | Default | Description |
| ---------- | ----------- | ---------------------------------------- |
| `--host` | `127.0.0.1` | Bind address. Loopback only by default. |
| `--port` | `8201` | TCP port. |

The cockpit auto-detects the repo root from its own location; there is no
`--repo-root` flag. The cockpit always uses the pipeline's default config.

## What you'll see

- **Library** — published inventory plus taxonomy. Tag and level usage
  counts come from `yengo-search.db`. With *Edit taxonomy* mode enabled,
  rename/merge mutations are exposed (auto-disables after 5 minutes).

- **Pipeline** — adapter list (filterable, sortable), Run/Ingest/Reset DB
  per row, and live-run progress via SSE. The active adapter is the row
  with `active: true` in `config/sources.json`.

- **Daily** — daily-challenge schedule and on-demand generation.

- **Activity** — unified timeline of pipeline runs, mutations, and audits.

- **Operations** — clean / rollback / vacuum-db / source-ingest-state reset,
  each with a dry-run preview before commit.

- **Logs** — pipeline stage logs and publish-log audit search.

The header chip surfaces dashboard health and DB version; the bottom
status strip is the source of truth for severity.

## Universal search

Press <kbd>⌘K</kbd> (or <kbd>Ctrl+K</kbd>, or `/`) to open the command
palette. Searches sources, tags, levels, and 16-hex puzzle hashes. Hash
matches navigate to the puzzle detail page; everything else routes to the
relevant view.

## Contextual help

Click any `?` chip next to a heading or column to open an inline popover
with a concept explanation. Strings live in
`tools/yengo_dashboard/web/help-strings.json`; update them in the same
commit as any UI label change.

## Sanity-check the API directly

```bash
curl -s http://127.0.0.1:8201/api/health
curl -s http://127.0.0.1:8201/api/adapters | python -m json.tool
curl -s http://127.0.0.1:8201/api/inventory | python -m json.tool
curl -s "http://127.0.0.1:8201/api/runs?limit=5" | python -m json.tool
```

The shapes are documented in `tools/yengo_dashboard/server/models.py`.

## Stopping it

`Ctrl+C` in the terminal. The cockpit holds no persistent state — it's safe
to restart at any time, including during a live pipeline run (it never
writes to pipeline files).

## Troubleshooting

**`/api/adapters` returns 502.** The puzzle_manager CLI exited non-zero. The
`detail.stderr` field in the response carries the first 500 characters of
the subprocess's traceback. Reproduce the failure directly with:

```bash
python -m backend.puzzle_manager source-status --json
```

**`/api/inventory` says `db_exists: false`.** You haven't run a `publish`
stage yet, or `yengo-puzzle-collections/yengo-search.db` is missing. Run the
pipeline once to populate it.

**`/api/inventory` says `snapshot_exists: false` (zeros + advice banner).**
The SQLite DB exists but the `inventory.json` snapshot has not been written
yet. The cockpit deliberately never opens `yengo-search.db` (Windows
file-lock contention with `vacuum-db` / `clean`); it only reads the JSON
snapshot the pipeline emits. Seed it once with:

```bash
python -m backend.puzzle_manager vacuum-db --rebuild
```

The snapshot refreshes automatically after every subsequent `publish`,
`vacuum-db`, or `rollback` run.

**Port 8201 is taken.** Pass `--port <other>`.
