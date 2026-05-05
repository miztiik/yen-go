# pm_cockpit Architecture

> Localhost browser cockpit over `backend/puzzle_manager`. Helps a human run,
> observe, and maintain ~200K-puzzle pipeline operations without typing CLI
> invocations.

**Tier**: Architecture (the *why*).
**See also**: [How-To: Run pm_cockpit](../../how-to/tools/run-pm-cockpit.md),
[Module map: tools/pm_cockpit/AGENTS.md](../../../tools/pm_cockpit/AGENTS.md),
[Living plan: tools/pm_cockpit/PLAN.md](../../../tools/pm_cockpit/PLAN.md).

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
tools/pm_cockpit/   ←  presentation only
       │
       │ subprocess calls │ raw SQLite/JSON reads │ static UI
       ▼
backend/puzzle_manager/   ←  every byte of domain logic lives here
```

The cockpit may:

- spawn `python -m backend.puzzle_manager` subprocesses
- read SQLite/JSON state files as raw data
- tail log files
- render results in a browser

The cockpit may **not**:

- parse SGF
- compute hashes or canonical positions
- classify puzzles, assign difficulty, decide what status enums mean
- duplicate any pipeline computation in JavaScript

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
          │ sqlite3 RO+json  │ subprocess.run   │ Popen + threads
          ▼                  ▼                  ▼
┌────────────────────┐  ┌─────────────────────────────────────────┐
│ yengo-search.db    │  │ python -m backend.puzzle_manager        │
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

For pure data — SQL `COUNT`/`GROUP BY` on `yengo-search.db`, or JSON file
listings under `.pm-runtime/state/runs/` — the cockpit reads directly. The
SQLite handle uses a read-only URI (`file:…?mode=ro`) so the cockpit cannot
accidentally write to a published file or create WAL sidecar files.

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
| `/api/inventory`               | `yengo-search.db` (`puzzles`, `collections`, `daily_schedule`) | `COUNT(*)`/`GROUP BY` only; counts keyed by raw value |
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
| Where do I add a new "show me X" view?            | New `StateReader` method or new `--json` CLI flag     |
| Where do I add a new "do X" button?               | If long-running → extend `RunController` and route through `/api/run/*`. If short CLI call → add a method to `PipelineRunner` and a route module. |
| Where does the difficulty enum get translated?    | Nowhere in `pm_cockpit/`. In `puzzle_manager` only.   |
| The CLI returned a new field — what changes here? | Add it to `models.py`; the route auto-validates it    |
| Why isn't there caching?                          | Cold subprocess is fast enough; cache lies in the CLI |
| What happens to in-flight runs on server restart? | The cockpit forgets them. The pipeline's own state JSON survives — see `/api/runs`. The cockpit is presentation only; truth is on disk. |

## Out of scope

- Authentication: loopback-only; do not bind to non-loopback.
- Multi-user / cross-host: developer tool, not a service.
- Persistent state in the cockpit: every byte of state is in the pipeline's
  files. Refresh the browser, get the truth.
