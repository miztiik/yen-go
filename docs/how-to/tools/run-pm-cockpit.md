# How to Run pm_cockpit

> Browser cockpit over `backend/puzzle_manager`. Read-only in Phase 1 — see
> `tools/pm_cockpit/PLAN.md` for the mutation roadmap.

**Tier**: How-to (the *do this*).
**See also**: [Architecture: pm_cockpit](../../architecture/tools/pm_cockpit.md).

---

## Quick start

From the repo root:

```bash
python -m tools.pm_cockpit
```

Open <http://127.0.0.1:8201/> in your browser.

## Flags

| Flag       | Default     | Description                              |
| ---------- | ----------- | ---------------------------------------- |
| `--host`   | `127.0.0.1` | Bind address. Loopback only by default.  |
| `--port`   | `8201`      | TCP port.                                |

The cockpit auto-detects the repo root from its own location; there is no
`--repo-root` flag. To point it at a different config directory, use the
`puzzle_manager` CLI's own `--config` (Phase 2 will surface this in the UI;
in Phase 1, the cockpit always uses the pipeline's default).

## What you'll see

- **Overview** — published inventory: total puzzles, collections, daily
  schedule entries, distribution by `level_id` and `content_type`.
- **Adapters** — one row per source from `sources.json`, with named buckets
  (`ingested` / `skipped` / `failed` / `total`) read from each source's
  `.yengo-ingest.sqlite`. Run/Ingest/Clean buttons are present but disabled
  with the tooltip *"Mutations enabled in Phase 2"*.
- **History** — the last 50 run-state files from
  `.pm-runtime/state/runs/`, newest first, with stage status pills.

The header badge in the top right shows the cockpit's own health and uptime.

## Sanity-check the API directly

```bash
curl -s http://127.0.0.1:8201/api/health
curl -s http://127.0.0.1:8201/api/adapters | python -m json.tool
curl -s http://127.0.0.1:8201/api/inventory | python -m json.tool
curl -s "http://127.0.0.1:8201/api/runs?limit=5" | python -m json.tool
```

The shapes are documented in `tools/pm_cockpit/server/models.py`.

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

**Port 8201 is taken.** Pass `--port <other>`.
