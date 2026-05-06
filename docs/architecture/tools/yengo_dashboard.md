# yengo_dashboard Architecture

> Localhost browser cockpit over `backend/puzzle_manager`. Helps a human run,
> observe, and maintain ~200K-puzzle pipeline operations without typing CLI
> invocations.

**Tier**: Architecture (the *why*).
**See also**: [How-To: Run yengo_dashboard](../../how-to/tools/run-yengo-dashboard.md),
[Module map: tools/yengo_dashboard/AGENTS.md](../../../tools/yengo_dashboard/AGENTS.md),
[Living plan: tools/yengo_dashboard/PLAN.md](../../../tools/yengo_dashboard/PLAN.md).

---

## Why this tool exists

The puzzle pipeline (`backend/puzzle_manager`) is a CLI-only system. Operators
running ingest/analyze/publish across many adapters were juggling N terminal
windows and `ls .pm-runtime/state/runs/`. The cockpit is a single browser
tab that shows what's happening, with one-click access to the operations
that already exist in the CLI.

It is deliberately **not** a second pipeline.

## Non-negotiable boundary (Principle #6)

```
tools/yengo_dashboard/   ←  presentation only
       │
       │ subprocess calls │ raw SQLite/JSON reads │ static UI
       ▼
backend/puzzle_manager/   ←  every byte of domain logic lives here
```

The cockpit may:

- spawn `python -m backend.puzzle_manager` subprocesses
- read JSON state files (run states, `inventory.json` snapshot) as raw data
- tail log files
- render results in a browser

The cockpit may **not**:

- open `yengo-search.db` (or any SQLite DB the pipeline writes) — even read-only
- parse SGF
- compute hashes or canonical positions
- classify puzzles, assign difficulty, decide what status enums mean
- duplicate any pipeline computation in JavaScript

The "no SQLite handles" rule is what made the Windows file-lock crashes go
away. See *Inventory snapshot pattern (G2)* below.

If the UI needs data the pipeline doesn't expose, the rule is *"add a CLI
subcommand or read-only query method to puzzle_manager first, then the
cockpit calls it."*

This is enforced architecturally: `tools/` may not import from `backend/` for
domain logic (project-level constraint, see root `CLAUDE.md`).

## Component layout

```
┌────────────────────────────────────────────────────────────────────────────┐
│  Browser (vanilla ES module + Tailwind CDN)                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────┐       │
│  │ Overview │ │ Adapters │ │ Live Run │ │ Maintenance │ │ History  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬──────┘ └────┬─────┘       │
└───────┼────────────┼────────────┼──────────────┼─────────────┼────────────┘
        │            │  POST/SSE  │  POST clean  │ POST adapter│
        │ /api/      │ /api/run/* │  rollback    │ enable/disable
        │ inventory  │ /api/lock  │  vacuum-db   │ GET pl/search
        ▼            ▼            ▼              ▼             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  FastAPI app                                                               │
│  ┌──────────────┐ ┌────────────────┐ ┌──────────────────┐                  │
│  │ StateReader  │ │ PipelineRunner │ │ RunController    │                  │
│  │ (raw passthr)│ │ (CLI subproc)  │ │ (long Popen+SSE) │                  │
│  └──────┬───────┘ └────────┬───────┘ └────────┬─────────┘                  │
└─────────┼──────────────────┼──────────────────┼───────────────────────────┘
          │ json passthru    │ subprocess.run   │ Popen + threads
          ▼                  ▼                  ▼
┌────────────────────┐  ┌─────────────────────────────────────────┐
│ inventory.json     │  │ python -m backend.puzzle_manager        │
│ .pm-runtime/state  │  │   source-status / config-lock /         │
│                    │  │   enable-adapter / disable-adapter /    │
│                    │  │   publish-log search /                  │
│                    │  │   run / clean / rollback / vacuum-db    │
└────────────────────┘  └─────────────────────────────────────────┘
```

### `PipelineRunner` (interpretation path, short-lived)

For anything that requires status-enum interpretation, source resolution, or
config loading, the cockpit subprocesses the CLI with `--json` and
`subprocess.run` (blocking, capture). Cost is ~300–600 ms per cold call —
acceptable at the documented 3 s poll cadence. If finer cadence becomes
necessary, the answer is *"expose a polling daemon in `puzzle_manager`"*,
not *"reach into SQLite from the cockpit"*. Used by `/api/adapters`,
`/api/lock/*`, `/api/adapter/{enable,disable}`, and `/api/publish-log/search`.

For non-JSON short-CLI calls (lock release, adapter enable/disable),
`PipelineRunner._run_capture()` returns `{ok, returncode, stdout, stderr}`
without raising — non-zero exit is a legitimate operator-facing answer (e.g.
"config locked, use --force") that must reach the UI verbatim, not be hidden
behind a 502.

### `StateReader` (passthrough path)

For pure data — JSON file listings under `.pm-runtime/state/runs/`, or the
`inventory.json` snapshot beside `yengo-search.db` — the cockpit reads
files directly. **It never opens `yengo-search.db`.** All puzzle/collection
counts come from `inventory.json`, which the pipeline writes after every
mutation (publish / vacuum-db / rollback). When the snapshot is missing
(fresh checkout, mid-bootstrap), `/api/inventory` returns zeros plus an
`advice` string nudging the operator to run `vacuum-db --rebuild`.

### Inventory snapshot pattern (G2)

**Problem this solves.** On Windows, `os.replace()` (used by `vacuum-db`'s
atomic DB swap) and `Path.unlink()` (used by `clean`) raise `WinError 5/32`
when *any* process holds an open handle on the target file — even a
read-only one. The cockpit's old `sqlite3.connect(uri, mode=ro)` left
handles cached in CPython long enough to collide with the pipeline's
mutations. Unix doesn't notice; Windows refuses.

**Fix.** Pure read/write split. The pipeline owns the SQLite handle
exclusively; the cockpit reads JSON only.

```
backend/puzzle_manager/inventory/snapshot.py
    write_inventory_snapshot(output_dir)
        ├─ opens yengo-search.db RO
        ├─ runs COUNT/GROUP BY queries
        ├─ writes inventory.json.tmp
        └─ os.replace() → inventory.json     ← atomic
              │
              │ called from publish.py, cmd_vacuum_db, cmd_rollback
              ▼
yengo-puzzle-collections/inventory.json       ← snapshot contract

tools/yengo_dashboard/server/state_reader.py
    read_inventory()
        ├─ json.loads(inventory.json)         ← never opens .db
        └─ returns InventoryResponse
```

The JSON shape *is* the contract between pipeline writer and cockpit
reader. Anything else that needs counts (CI dashboards, future TUIs)
should consume this file rather than running its own SQL — single source
of truth, language-agnostic, lock-free.

### `RunController` (long-lived subprocess + live stream)

A single in-process controller manages at most one active pipeline run. It
spawns `python -u -m backend.puzzle_manager …` with `PYTHONUNBUFFERED=1`,
runs two reader threads (stdout/stderr), buffers a tail of the most recent
2000 lines, and publishes line/status/end events to any number of SSE
subscribers. Cancel uses SIGTERM with a 5 s grace before SIGKILL. The
controller deliberately enforces single-active-run (returns 409 to a second
POST) — the cockpit is not a job scheduler; the pipeline is.

The single-active-run guard is shared across **every** mutating endpoint
that touches pipeline state — `/api/run`, `/api/clean`, `/api/rollback`,
`/api/vacuum-db`. The browser cannot launch a clean while a rollback is
in flight; the operator gets a 409 with the active subcommand's identity in
the conflict response. Adapter enable/disable does NOT participate — it
edits `sources.json`, which the CLI's own config-lock already serializes.

### Path resolution

Repo root is auto-detected from `__file__` (3 levels up). Tests inject
`runtime_dir`/`published_dir` overrides so each test can build an
isolated fixture without touching the real `yengo-puzzle-collections/` or
`.pm-runtime/`.

## Wire contracts

The cockpit faithfully passes through the shapes the pipeline owns. It never
renames a field or "improves" a label.

| Endpoint                       | Source of truth                                                | Cockpit's transformation                              |
| ------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------- |
| `/api/health`                  | none (in-process)                                              | n/a                                                   |
| `/api/adapters`                | `puzzle_manager source-status --json`                          | `model_validate` only                                 |
| `/api/inventory`               | `inventory.json` snapshot (written by pipeline)                | JSON passthrough; zeros + `advice` if snapshot missing|
| `/api/runs`                    | `.pm-runtime/state/runs/*.json`                                | strip `batches`/`file_results`/`config_snapshot`      |
| `/api/run/active`              | `RunController` in-process state                               | `{active: snapshot|null}`                             |
| `/api/run` (POST)              | spawns `python -u -m backend.puzzle_manager run …`             | 202 on accept, 409 if a run is active                 |
| `/api/run/{handle}/cancel`     | SIGTERM → SIGKILL escalation                                   | 202 idempotent                                        |
| `/api/run/{handle}/events`     | reader threads → asyncio queue                                 | SSE frames `line` / `status` / `end`                  |
| `/api/lock`                    | `puzzle_manager config-lock status --json`                     | `{raw: …}` verbatim                                   |
| `/api/lock/release` (POST)     | `puzzle_manager config-lock release [--force]`                 | 200 with `{ok, returncode, stdout, stderr}` (never 502)|
| `/api/clean` (POST)            | RunController → `puzzle_manager clean …`                       | 202 `RunSnapshot`; 409 if any mutating run is active  |
| `/api/rollback` (POST)         | RunController → `puzzle_manager rollback …`                    | 400 if neither/both id flags; 422 if reason empty     |
| `/api/vacuum-db` (POST)        | RunController → `puzzle_manager vacuum-db …`                   | 202 `RunSnapshot`; 409 shared with other mutations    |
| `/api/adapter/enable` (POST)   | `puzzle_manager enable-adapter ID [--force]`                   | 200 with `{ok, returncode, stdout, stderr}` (never 502)|
| `/api/adapter/disable` (POST)  | `puzzle_manager disable-adapter [--force]`                     | same shape                                            |
| `/api/publish-log/search`      | `puzzle_manager publish-log search --format json …`            | `{raw: …}` verbatim; 400 with hint if CLI rejects    |

When the CLI's JSON contract changes, the cockpit response changes with it
(intentionally). Pydantic schema mismatches surface as HTTP 500 — a loud
signal to update the contract on both sides together.

## Tests are real (no mocks)

Tests spin up the actual FastAPI app via `TestClient` and drive real
subprocesses, real seeded SQLite databases, real on-disk JSON state files.
The adapter test is the slowest (~3 s cold) and is marked
`@pytest.mark.slow`; the others run in well under a second.

This is non-negotiable: a cockpit test that mocks the subprocess teaches us
nothing about whether the wire contract still works.

## What lives where

| Question                                          | Answer                                                |
| ------------------------------------------------- | ----------------------------------------------------- |
| Where do I add a new "show me X" view?            | New `StateReader` method (consume a pipeline-written JSON snapshot) or new `--json` CLI flag. **Never open a live pipeline DB from the cockpit.** |
| Where do I add a new "do X" button?               | If long-running → extend `RunController` and route through `/api/run/*`. If short CLI call → add a method to `PipelineRunner` and a route module. |
| Where does the difficulty enum get translated?    | Nowhere in `yengo_dashboard/`. In `puzzle_manager` only.   |
| The CLI returned a new field — what changes here? | Add it to `models.py`; the route auto-validates it    |
| Why isn't there caching?                          | Cold subprocess is fast enough; cache lies in the CLI |
| What happens to in-flight runs on server restart? | The cockpit forgets them. The pipeline's own state JSON survives — see `/api/runs`. The cockpit is presentation only; truth is on disk. |

## Out of scope

- Authentication: loopback-only; do not bind to non-loopback.
- Multi-user / cross-host: developer tool, not a service.
- Persistent state in the cockpit: every byte of state is in the pipeline's
  files. Refresh the browser, get the truth.
