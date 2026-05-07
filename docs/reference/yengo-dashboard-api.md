# yengo_dashboard HTTP API Reference

> **Tier**: Reference (the *what*).
> **See also**: [Architecture: yengo_dashboard](../architecture/tools/yengo_dashboard.md) (the *why*),
> [How-to: run yengo_dashboard](../how-to/tools/run-yengo-dashboard.md) (daily ops),
> [Module map](../../tools/yengo_dashboard/AGENTS.md) (agent-facing layout).

Endpoint catalog for the localhost browser cockpit over `backend/puzzle_manager`.
Live OpenAPI / Swagger UI: `http://127.0.0.1:8201/docs` (FastAPI built-in).

This document is the stable, human-readable index. Pydantic schemas in
`tools/yengo_dashboard/server/models.py` are the canonical source for every shape.

---

## Conventions

- **Base URL**: `http://127.0.0.1:8201` (loopback only — never bind elsewhere).

- **Content-Type**: `application/json` for request bodies and JSON responses.

- **SSE endpoints**: `Content-Type: text/event-stream`; frames carry an

  `event:` line plus a `data:` JSON line.

- **Verbatim passthrough**: routes that mirror a CLI subcommand (`/api/lock`,

  `/api/publish-log/search`, `/api/adapter/{enable,disable}`, `/api/lock/release`)
  do **not** reshape the CLI payload. The CLI owns the schema; the cockpit
  forwards it under a `raw` key (for JSON-emitting subcommands) or as
  `{ok, returncode, stdout, stderr}` (for non-JSON short calls).

- **Single-active-run guard**: every long-running mutation (`run`, `clean`,

  `rollback`, `vacuum-db`) shares one in-process slot. A second POST while
  one is active returns `409 Conflict` with the active run's snapshot in the
  detail body.

- **Path semantics**: paths in responses are POSIX-relative to the repo

  root. Absolute paths leaking through indicate a fixture/configuration bug.

---

## Status code taxonomy

| Code | Meaning in cockpit context |
| ---- | --------------------------------------------------------------------------- |
| 200 | Synchronous success (passthrough JSON, short CLI call completed). |
| 202 | Long-running run accepted; subscribe to SSE for live progress. |
| 400 | CLI rejected the inputs (e.g. `publish-log search` with no filter). |
| 404 | Unknown run handle on `/api/run/{handle}/cancel`. |
| 409 | A pipeline mutation is already active; retry after it ends. |
| 422 | Pydantic validation failure (missing/invalid request body). |
| 500 | Pydantic schema mismatch — CLI JSON contract drift; fix both sides. |

The cockpit deliberately **never** maps a CLI non-zero exit to a `502`. Failed
short calls (`/api/adapter/*`, `/api/lock/release`) return `200` with `ok:false`
so the operator sees the same stdout/stderr they would see at a terminal.

---

## Endpoint index

| Method | Path | Purpose |
| ------ | ------------------------------- | --------------------------------------- |
| GET | `/api/health` | Process liveness + version + uptime |
| GET | `/api/adapters` | Per-source ingest counts (named buckets) |
| GET | `/api/inventory` | Published-corpus aggregate counts |
| GET | `/api/runs` | Past runs (newest-first, header only) |
| GET | `/api/run/active` | Cockpit-managed active run snapshot |
| POST | `/api/run` | Start `puzzle_manager run …` |
| POST | `/api/run/{handle}/cancel` | SIGTERM → SIGKILL escalation |
| GET | `/api/run/{handle}/events` | SSE stream: `line` / `status` / `end` |
| GET | `/api/lock` | `config-lock status --json` passthrough |
| POST | `/api/lock/release` | `config-lock release [--force]` |
| POST | `/api/clean` | Long-running `clean …` |
| POST | `/api/rollback` | Long-running `rollback …` |
| POST | `/api/vacuum-db` | Long-running `vacuum-db …` |
| POST | `/api/adapter/enable` | `enable-adapter ID [--force]` |
| POST | `/api/adapter/disable` | `disable-adapter [--force]` |
| GET | `/api/publish-log/search` | `publish-log search --format json …` |

Static UI is mounted at `/`, `/app.js`, `/styles.css`. The `/api/*` mount
takes precedence over the static catch-all.

---

## Read endpoints

### `GET /api/health`

In-process liveness probe. No subprocess, no I/O.

```json
{ "ok": true, "version": "0.4.0", "uptime_s": 12.873 }
```

### `GET /api/adapters`

Wraps `puzzle_manager source-status --json`. Each row mirrors the CLI's
named buckets — the cockpit never maps status integers to labels itself.

```json
{
  "sources": [
    {
      "id": "ogs",
      "adapter": "ogs",
      "source_root": "external-sources/ogs",
      "db_path": "external-sources/ogs/.yengo-ingest.sqlite",
      "db_exists": true,
      "schema_version": 4,
      "ingested": 8421,
      "skipped": 12,
      "failed": 3,
      "total": 8436,
      "db_size_bytes": 1572864,
      "db_mtime": "2026-05-04T18:22:11Z",
      "error": null
    }
  ]
}
```

### `GET /api/inventory`

JSON passthrough of the `inventory.json` snapshot the pipeline writes
beside `yengo-search.db`. **The cockpit never opens the SQLite DB itself**
— see [yengo_dashboard architecture › Inventory snapshot pattern (G2)](../architecture/tools/yengo_dashboard.md#inventory-snapshot-pattern-g2)
for the why (Windows file-lock contention with `vacuum-db` / `clean`).

When the snapshot is missing (fresh checkout, mid-bootstrap), the response
returns zero counts plus an `advice` string nudging the operator to run
`python -m backend.puzzle_manager vacuum-db --rebuild`.

```json
{
  "db_path": "yengo-puzzle-collections/yengo-search.db",
  "db_exists": true,
  "snapshot_exists": true,
  "snapshot_path": "yengo-puzzle-collections/inventory.json",
  "advice": null,
  "puzzles_total": 9132,
  "collections_total": 47,
  "daily_schedule_total": 365,
  "by_level_id": { "110": 412, "120": 530, "130": 1104 },
  "by_content_type": { "1": 1820, "2": 5641, "3": 1671 },
  "by_collection_category": { "lnd": 18, "shape": 12, "uncategorised": 17 },
  "schema_version": 2,
  "db_version": "20260505-abc12345"
}
```

### `GET /api/runs`

Reads `.pm-runtime/state/runs/*.json`, strips heavy fields (`batches`,
`file_results`, `config_snapshot`), returns newest-first.

```json
{
  "runs": [
    {
      "run_id": "20260505-abc12345",
      "status": "completed",
      "started_at": "2026-05-05T07:18:02Z",
      "completed_at": "2026-05-05T07:24:51Z",
      "stages": [
        { "name": "ingest",  "status": "completed", "started_at": "...", "completed_at": "...", "processed_count": 412, "failed_count": 0, "skipped_count": 3 },
        { "name": "analyze", "status": "completed", "started_at": "...", "completed_at": "...", "processed_count": 412, "failed_count": 0, "skipped_count": 0 },
        { "name": "publish", "status": "completed", "started_at": "...", "completed_at": "...", "processed_count": 412, "failed_count": 0, "skipped_count": 0 }
      ],
      "failure_count": 0,
      "state_file": ".pm-runtime/state/runs/20260505-abc12345.json"
    }
  ],
  "total": 134
}
```

### `GET /api/run/active`

In-process snapshot of the cockpit's currently-managed subprocess. `null`
when nothing has run since process start.

```json
{
  "active": {
    "handle": "r-7f3c1",
    "command": ["python", "-u", "-m", "backend.puzzle_manager", "run", "--source", "ogs"],
    "cwd": "/repo",
    "started_at": "2026-05-05T09:01:14Z",
    "status": "running",
    "pid": 12480,
    "exit_code": null,
    "completed_at": null,
    "line_count": 174,
    "cancel_requested": false
  }
}
```

`status` is one of: `starting | running | completed | failed | cancelled`.

---

## Run lifecycle

### `POST /api/run`

Spawns `python -u -m backend.puzzle_manager run …` and returns the snapshot.

Request body (`RunStartRequest` — all fields optional):

```json
{
  "source": "ogs",
  "stage": "publish",
  "fresh": false,
  "dry_run": false,
  "source_override": false,
  "no_enrichment": false
}
```

- `202` with `RunSnapshot` on accept.

- `409` with the active snapshot in `detail` if any pipeline mutation is

  already in flight.

### `POST /api/run/{handle}/cancel`

Idempotent. Sends `SIGTERM`; escalates to `SIGKILL` after 5 s.

- `202` with the updated snapshot.

- `404` if the handle doesn't match the current/last run.

### `GET /api/run/{handle}/events` (SSE)

Live log stream. Three event types:

```text
event: line
data: {"ts":"2026-05-05T09:01:15.123Z","stream":"stdout","text":"[ingest] starting …","seq":1}

event: status
data: { "handle":"r-7f3c1", "status":"running", … }   // same shape as RunSnapshot

event: end
data: { "handle":"r-7f3c1", "status":"completed", "exit_code":0, … }
```

- `stream` is exactly `"stdout"` or `"stderr"`.

- `seq` is monotonic per run.

- On connect, the most recent 2000 buffered lines are replayed before live

  frames begin (so a late subscriber doesn't miss early chatter).

- 15 s keepalive comments (`: keep-alive`) prevent proxy timeouts even

  though the cockpit is loopback-only.

- `event: end` is always last; the connection then closes.

---

## Maintenance (long-running mutations)

All three return the standard `RunSnapshot` and stream live output via the
shared `/api/run/{handle}/events` endpoint. The single-active-run guard
means a second POST returns `409` regardless of which subcommand is live.

### `POST /api/clean`

```json
{
  "target": "logs",            // or staging | state | puzzles-collection | publish-logs | null
  "retention_days": 30,         // omit for CLI default (45)
  "dry_run": true               // omit for CLI default (true for puzzles-collection, else false)
}
```

`target: null` runs retention-based cleanup across all targets. `dry_run`
is tri-state: `null` (omit flag entirely), `true`, `false`.

### `POST /api/rollback`

```json
{
  "run_id": "20260505-abc12345",
  "reason": "duplicate ingest from sanderland adapter",
  "dry_run": false,
  "yes": true,
  "verify": true
}
```

- `run_id` is required (`min_length: 1`); missing or empty returns `422`.

- `reason` is required (`min_length: 1`); empty string returns `422`.

- Per-puzzle rollback (`puzzle_ids`) was removed in Theme 17 (2026-05).
  The CLI never implemented `RollbackManager.rollback_by_puzzle`, so the
  prior `--puzzle-id` argparse arm was dead UI that rejected every
  invocation. Use `publish-log search` to identify the run that
  introduced an unwanted puzzle, then roll the whole run back.

### `POST /api/vacuum-db`

```json
{ "rebuild": false, "dry_run": true }
```

`rebuild: true` rebuilds `yengo-search.db` from `yengo-content.db` after the
`VACUUM`. Slow — expect minutes.

---

## Short-running CLI passthroughs

These wrap CLI commands that finish in well under a second and return their
result synchronously. Non-zero exit is **not** mapped to a 5xx — it returns
`200` with `ok: false` so the UI can show what the operator would see at a
terminal.

### `GET /api/lock`

Verbatim passthrough of `config-lock status --json`.

```json
{ "raw": { "locked": true, "holder_pid": 12480, "acquired_at": "..." } }
```

The `raw` envelope is intentional — extra fields the CLI adds flow through
without a coordinated cockpit release.

### `POST /api/lock/release`

```json
{ "force": false }
```

Response (`LockReleaseResponse`):

```json
{ "ok": false, "returncode": 1, "stdout": "", "stderr": "lock held by pid 12480; use --force" }
```

A locked-by-other-process result is a legitimate operator-facing answer,
not an error.

### `POST /api/adapter/enable`

```json
{ "adapter_id": "ogs", "force": false }
```

Response (`CliInvocationResponse`):

```json
{ "ok": true, "returncode": 0, "stdout": "active adapter set to ogs\n", "stderr": "" }
```

`adapter_id` is required and must be non-empty (`422` otherwise). A locked
config returns `200` with `ok: false` and the CLI's hint in `stderr`.

### `POST /api/adapter/disable`

```json
{ "force": false }
```

Same response shape as enable. Clears the `active_adapter` field in
`sources.json`.

### `GET /api/publish-log/search`

Wraps `publish-log search --format json [filters…]`.

Query parameters (all optional, but the CLI rejects a no-filter call):

| Param | CLI flag | Notes |
| ------------ | -------------- | ---------------------------------- |
| `run_id` | `--run-id` |  |
| `puzzle_id` | `--puzzle-id` |  |
| `trace_id` | `--trace-id` |  |
| `from` | `--from` | ISO date (`YYYY-MM-DD`) |
| `to` | `--to` | ISO date |
| `date` | `--date` | Single ISO date (shorthand) |
| `event` | `--event` | e.g. `published`, `rolled_back` |
| `limit` | `--limit` | Forwarded as string |

Response on success:

```json
{ "raw": { "results": [ { "trace_id": "abc", "puzzle_id": "deadbeef", … } ] } }
```

`raw` may be a list or a dict — schema is owned by the publish-log
subcommand.

On CLI rejection (no filter, parse error, etc.) the cockpit returns `400`
with the CLI's actual hint (it goes to stdout, not stderr — both are
surfaced):

```json
{
  "detail": {
    "message": "publish-log search failed",
    "returncode": 2,
    "stderr": "",
    "stdout": "Use one of: --run-id, --puzzle-id, --trace-id, --from/--to, --date"
  }
}
```

---

## Schema drift policy

Pydantic models in `tools/yengo_dashboard/server/models.py` validate every
response that isn't `raw`-wrapped. When the CLI's JSON contract changes:

1. The cockpit's `model_validate` either accepts the new shape (additive

   change with `extra = ignore`) or raises `500`.

1. A `500` from a passthrough route is a **loud signal** to update the

   cockpit's schema in the same commit as the CLI change.

1. The cockpit deliberately does **not** silently swallow unknown fields by

   reformatting — that would mask drift.

For verbatim-passthrough routes (`/api/lock`, `/api/publish-log/search`,
`/api/adapter/*`, `/api/lock/release`), the cockpit forwards the CLI's
output as-is. The frontend reads the `raw` envelope and renders defensively.
