# yengo_dashboard — AGENTS.md

> Dense, agent-facing architecture map. Read before working in this module.
> Update **in the same commit** as any structural code change.

---

## Identity

`tools/yengo_dashboard/` is a localhost browser cockpit over `backend/puzzle_manager`.
It exists so a human can run/observe/maintain ~200K-puzzle pipeline operations
across many adapters without typing CLI invocations.

It is **not** a second pipeline. It owns no domain logic.

## Principle #6 (the rule that decides every disagreement)

> `tools/yengo_dashboard/` is a pure presentation layer over `backend/puzzle_manager/`.
> It may: spawn `python -m backend.puzzle_manager` subprocesses, read JSON
> snapshots and run-state files as raw data, tail log files, render results.
> It may **not**: open `yengo-search.db` (or any pipeline-owned SQLite DB),
> parse SGF, compute hashes, classify puzzles, decide what state means.
>
> If the UI needs data the pipeline doesn't expose, the rule is "add a CLI
> subcommand or write a JSON snapshot from the pipeline first."

This is non-negotiable. `tools/` may NOT import from `backend/` for domain
logic. Imports of pure data types (Pydantic models, IntEnums, schema
constants) are allowed only when the cockpit needs them to *seed test
fixtures* — never to interpret runtime state.

## Layout

```
tools/yengo_dashboard/
  __init__.py           # __version__
  __main__.py           # argparse + uvicorn launcher (default port 8201)
  PLAN.md               # living design doc (phases, decisions, rationale)
  AGENTS.md             # ← this file
  server/
    app.py              # FastAPI factory (create_app); mounts /api + static
    pipeline_runner.py  # subprocess wrapper around `python -m backend.puzzle_manager`
    state_reader.py     # JSON-only passthrough reads (inventory.json snapshot + run state); never opens yengo-search.db
    run_controller.py   # long-lived subprocess + reader threads + SSE pub/sub
    routes_read.py      # GET endpoints (health, adapters, inventory, runs)
    routes_run.py       # POST + SSE endpoints (start/cancel/stream a run)
    routes_lock.py      # GET/POST endpoints (config-lock status/release)
    routes_maintenance.py # POST clean / rollback / vacuum-db (long-running, via RunController)
    routes_admin.py     # POST adapter enable/disable + GET publish-log search (short-running, via PipelineRunner)
    routes_logs.py      # GET stage-log file list + tail (read-only filesystem under .pm-runtime/logs)
    models.py           # Pydantic response schemas
  web/
    index.html          # tab shell (Library / Pipeline / Operations / Logs / Guide)
    app.js              # vanilla ES module — fetch + render + EventSource. Every render* function MUST emit its title via viewHeader() so the .view-header typography stays pinned (Theme 0 invariant). Operations cards expose a Preview button that opens #preview-dialog via openPreviewModal() — GET /api/{op}/preview, render via PREVIEW_RENDERERS, then "Run for real" reuses startMaintenance() with dry_run=false (Theme 1e). Logs/Stage pane has a regex search box (#lg-pattern + #lg-stage/from/to/limit) that calls /api/logs/grep and renders a results table; each row's [Open] button dispatches the matching #stage-files-list button so the existing tail viewer kicks in (Theme 4c). Pipeline (history) view mounts a #failures-summary-card above the run list that loads /api/status/failures-summary?last=10 and renders top failure modes; each `.failures-row` click writes a `yengo-dashboard:logsGrepPrefill` sessionStorage entry then nav→/logs, where _renderLogsStagePane consumes-and-clears the prefill to auto-search (Theme 2b/2c). System dialog grows a Disk-footprint section sourced from /api/runtime-info, and the Operations Clean target dropdown is decorated with per-target byte estimates from the same payload (Theme 3b). Activity tab (`renderActivity`) renders a unified timeline from /api/activity with kind-filter chips (run/maintenance/publish) that drive the CLI's `--kinds` flag — no client-side merge (Theme 13b). Library/Overview view (`renderOverview`) decorates the inventory header with an integrity badge + per-issue table sourced from /api/inventory/check via `integrityBlock()` (Theme 14b). The same block carries Preview→Apply buttons (`data-inv-op` rebuild|reconcile|fix) wired by `_wireInventoryActionButtons()`; clicks open `openInventoryMutationModal()` which reuses `#preview-dialog` for a synchronous two-stage flow — POST /api/inventory/preview → render `InventoryMutationPreview` → POST /api/inventory/apply → morph body to `InventoryMutationResult` (Theme 14c3). Operations page (`renderMaintenance`) is async and awaits `/api/ops/catalog` first; card *bodies* live in `OPS_CARD_SPECS` keyed by op token but section placement (`maintenance`/`destructive`), Preview-button presence, `data-destructive`, and the per-card `title` tooltip are all driven by the catalog row — a backend-only re-classification (e.g., moving `clean` to destructive) reshapes the page without a cockpit release (Theme 16b). A document-level capture-phase click listener `_opsCatalogConfirmGuard` (installed once at boot via `_ensureOpsCatalogGuard()`) intercepts any click on a `[data-op]` button whose catalog row has `reversible === false && preview_supported === false`, blocks the view-local handler with `stopImmediatePropagation`, presents `confirmDialog({verb})` for typed-verb confirm, then re-fires the click with a `data-ops-confirmed="yes"` marker so the second pass falls through to the original handler — works on every view, not just Operations (Theme 16c).
    view-guide.js       # docs-tree viewer for the Guide tab (own layout, no view-header)
    styles.css          # minimal complement to Tailwind CDN. Owns .view-header / .view-header-title / .view-header-sub, the .logs-stage-grid responsive template, and dialog.preview-dialog (Theme 1e impact modal).
  tests/
    test_routes_read.py        # real-fixture TestClient tests (no mocks)
    test_routes_run.py         # real-subprocess SSE tests via TestClient
    test_routes_lock.py        # env-driven shim of config-lock {status,release}
    test_routes_maintenance.py # real-subprocess shim that echoes argv (clean/rollback/vacuum-db)
    test_routes_admin.py       # env-driven shim of enable-adapter / disable-adapter / publish-log search
    test_routes_logs.py        # real-disk fixture for stage-log list + tail (path-traversal safety)
    test_run_controller.py     # direct controller tests + slow `validate` smoke
```

## Endpoints (Phase 1 + Phase 2 + Phase 3)

| Method | Path                          | Source                                | Notes                                           |
| ------ | ----------------------------- | ------------------------------------- | ----------------------------------------------- |
| GET    | `/api/health`                 | in-process                            | uptime, version                                 |
| GET    | `/api/adapters`               | subprocess `source-status --json`     | named buckets only (no enum ints)               |
| GET    | `/api/inventory`              | reads `yengo-puzzle-collections/inventory.json` snapshot | JSON passthrough; `snapshot_exists=false` returns zeros + `advice` (cockpit MUST NOT open the SQLite DB) |
| GET    | `/api/runs`                   | direct read of `.pm-runtime/state/runs/*.json` | strips heavy fields, newest-first      |
| GET    | `/api/run/active`             | `RunController` in-process state      | `{active: snapshot|null}`                       |
| POST   | `/api/run`                    | spawns `python -u -m backend.puzzle_manager run …` | 202 on accept, 409 if a run is active |
| POST   | `/api/run/{handle}/cancel`    | SIGTERM (escalates to KILL)           | 202 idempotent; 404 if handle unknown           |
| GET    | `/api/run/{handle}/events`    | SSE: `line` / `status` / `end`        | replays tail backlog, 15 s keepalive            |
| GET    | `/api/lock`                   | subprocess `config-lock status --json`| verbatim passthrough as `{raw: …}`              |
| POST   | `/api/lock/release`           | subprocess `config-lock release [--force]` | non-zero rc returns 200 with `ok:false` (UI shows it) |
| POST   | `/api/clean`                  | RunController → `clean [--target …] [--retention-days N] [--dry-run BOOL]` | 202; 409 shared with /api/run |
| POST   | `/api/rollback`               | RunController → `rollback --run-id ID --reason TEXT [--dry-run] [--yes] [--verify]` | 422 if `run_id`/`reason` missing or empty (per-puzzle rollback was removed in Theme 17 — the CLI never supported it) |
| POST   | `/api/vacuum-db`              | RunController → `vacuum-db [--rebuild] [--dry-run]` | 202; 409 shared                       |
| GET    | `/api/clean/preview`          | subprocess `clean --dry-run --json [--target …] [--retention-days N]` | 200 with `{raw: CleanPreview}`; 502 on CLI failure |
| GET    | `/api/rollback/preview`       | subprocess `rollback --dry-run --json --run-id ID --reason TEXT` | 200 with `{raw: RollbackPreview}`; 422 if `run_id` missing; 502 on CLI failure. `reason` defaults to `"preview-only"` (CLI requires it even in dry-run) |
| GET    | `/api/vacuum-db/preview`      | subprocess `vacuum-db --dry-run --json [--rebuild]` | 200 with `{raw: VacuumDbPreview}`; 502 on CLI failure |
| POST   | `/api/adapter/enable`         | subprocess `enable-adapter ID [--force]` | 200 with `{ok, returncode, stdout, stderr}` even on non-zero |
| POST   | `/api/adapter/disable`        | subprocess `disable-adapter [--force]`| same shape; clears active adapter                |
| GET    | `/api/publish-log/search`     | subprocess `publish-log search --format json …` | 400 if CLI rejects (no filter, etc.); raw payload otherwise |
| GET    | `/api/logs/stage-files`       | direct read of `.pm-runtime/logs/*.log`         | name + size + mtime, newest-first; empty `files:[]` if dir missing |
| GET    | `/api/logs/stage-files/{name}`| direct tail of one log file                     | 404 on bad name (regex / outside logs dir); 422 if `lines>5000` |
| GET    | `/api/logs/grep`              | subprocess `logs grep --json PATTERN [--stage] [--from] [--to] [--limit]` | 200 with `{raw: list[LogsGrepHit]}`; 400 on CLI failure (e.g. invalid regex); 422 if `pattern` missing |
| GET    | `/api/status/failures-summary`| subprocess `status --failures-summary --last N --json` (Theme 2b) | 200 with `{raw: list[FailureGroup]}`; 400 on CLI failure; 422 if `last` outside [1,200] |
| GET    | `/api/runtime-info`           | subprocess `runtime-info --json` (Theme 3b)     | 200 with `{raw: RuntimeInfo}`; 400 on CLI failure |
| GET    | `/api/activity`               | subprocess `activity --json [--from] [--to] [--kinds CSV] [--limit]` (Theme 13b) | 200 with `{raw: list[ActivityEvent]}`; 400 on CLI failure (e.g. unknown kind); 422 if `limit` outside [1,1000] |
| GET    | `/api/inventory/check`        | subprocess `inventory --check --json` (Theme 14b) | 200 with `{raw: IntegrityReport}`; 400 only on hard CLI failure (returncode 0 *or* 1 are both treated as success — exit 1 just means "issues present", which is a valid report) |
| GET    | `/api/ops/catalog`            | subprocess `ops catalog --json` (Theme 16b)     | 200 with `{raw: list[OpsCatalogEntry]}`; 400 on CLI failure. Single source of truth for blast-radius classification — Operations page consumes it to drive section grouping (`maintenance`/`destructive`/`diagnostic`) and Preview-button gating |
| POST   | `/api/inventory/preview`      | subprocess `inventory --{op} --dry-run --json` (Theme 14c3) | 200 with `{raw: InventoryMutationPreview}`; body `{op: rebuild\|reconcile\|fix}`; 502 on CLI failure |
| POST   | `/api/inventory/apply`        | subprocess `inventory --{op} --json` (Theme 14c3) | 200 with `{raw: InventoryMutationResult}`; CLI takes `PipelineLock` and writes `inventory_{op}` to audit.jsonl; 502 on CLI failure |
| GET    | `/`, `/app.js`, `/styles.css` | StaticFiles                           | mounted at `/`, `/api/*` precedes               |
| GET    | `/library`, `/pipeline`, `/activity`, `/operations`, `/logs`, `/guide`, `/guide/{rest:path}` | SPA shell | All return `index.html` so deep-link refresh works under clean-path routing |

The single-active-run guard is shared across **every** mutating endpoint
(`run`, `clean`, `rollback`, `vacuum-db`). One run at a time, regardless of
which subcommand spawned it. Adapter enable/disable does NOT participate —
the CLI's own config-lock is the right serialization point for `sources.json`
edits.

## Wire contracts

The cockpit **never reformats** pipeline-owned shapes:

- `/api/adapters` → mirrors `puzzle_manager source-status --json` 1:1.
  If the CLI ever changes a field name, the cockpit response changes with it
  (intentionally — the cockpit is a thin projection).
- `/api/runs` → `RunSummary.model_validate` of the run-state JSON file with
  heavy fields (`batches`, `file_results`, `config_snapshot`) stripped.
- `/api/inventory` → JSON passthrough of `yengo-puzzle-collections/inventory.json`,
  written by `backend/puzzle_manager/inventory/snapshot.py` after every
  pipeline mutation (publish / vacuum-db / rollback). The cockpit **never
  opens `yengo-search.db`** — even read-only — because Windows file-lock
  contention with `vacuum-db`'s atomic `os.replace()` and `clean`'s
  `Path.unlink()` was the original WinError 5/32 root cause. When the
  snapshot is missing the response carries `snapshot_exists=false`, zero
  counts, and an `advice` string (it MUST NOT silently fall back to
  opening the DB). Counts are keyed by stored column values — the cockpit
  does not translate `level_id` → human label or `content_type` →
  "curated/practice/training".
- `/api/lock` → wraps `raw` around the verbatim CLI JSON. Extra fields the
  CLI adds (e.g., `holder_pid`) flow through without a cockpit-side schema
  bump.
- `/api/lock/release`, `/api/adapter/enable`, `/api/adapter/disable` → never
  raise 502 on non-zero exit. The CLI's stdout / stderr / returncode are
  surfaced together so the operator sees what they would see at a terminal.
- `/api/clean`, `/api/rollback`, `/api/vacuum-db` → return the same
  `RunSnapshot` as `/api/run`. The UI subscribes to `/api/run/{handle}/events`
  regardless of which subcommand spawned the run; `command[3:]` carries
  the subcommand identifier (e.g. `["vacuum-db", "--dry-run"]`).
- `/api/clean/preview`, `/api/rollback/preview`, `/api/vacuum-db/preview`
  → wrap `raw` around the verbatim CLI JSON (CleanPreview / RollbackPreview /
  VacuumDbPreview from `backend.puzzle_manager.models.previews`). The
  cockpit MUST NOT re-validate the shape — the schema is owned by the
  backend and is allowed to evolve without a coordinated cockpit release.
  GET because previews are idempotent; the operator can poll without
  side effects. Synchronous (no `RunController`) because dry-run is fast
  and the operator wants the impact summary inline before deciding whether
  to commit. CLI failure → 502 with `{message, returncode, stderr}`.
- `/api/publish-log/search` → wraps `raw` around the verbatim CLI JSON
  (list or dict — the schema is owned by the publish-log subcommand). On
  CLI failure (no filter, parse error, etc.) the route returns 400 with
  `{message, returncode, stdout, stderr}` so the operator sees the CLI's
  hint message verbatim — the hint goes to stdout, not stderr.
- `/api/logs/stage-files` and `/api/logs/stage-files/{name}` → pure
  filesystem reads under `.pm-runtime/logs/`. Names must match
  `^[A-Za-z0-9._-]+\.log$` AND the resolved path must stay inside the logs
  dir (path-traversal defense). Tail uses `deque(maxlen=lines)` so the
  whole file never lives in memory. `lines` is capped at 5000 by FastAPI's
  `Query(le=…)`. The cockpit reads files directly because log files are
  the pipeline's own observable artifact — no domain interpretation needed.
- `/api/logs/grep` → subprocess `logs grep --json …` (Theme 4b). Returns
  `{raw: list[LogsGrepHit]}` verbatim from the CLI; PATTERN is positional
  (placed last in argv so flags don't swallow it). Invalid regex / unknown
  stage → CLI exit 2, cockpit translates `PipelineCommandError` to 400
  with `{message, returncode, stdout, stderr}`.
- SSE frames on `/api/run/{handle}/events`:
  - `event: line` carries `{ts, stream, text, seq}` — `stream` is exactly
    `"stdout"` or `"stderr"`, `seq` is monotonic per run.
  - `event: status` carries the same `RunSnapshot` shape `/api/run/active`
    returns.
  - `event: end` is always last; the connection then closes.
  - Lines emitted before the SSE was opened are replayed from a tail buffer
    (default 2000 lines) so the UI doesn't miss early chatter.

## Tests

Real fixtures only — see `PLAN.md §0.4`.

- Adapter tests seed a real `.yengo-ingest.sqlite` via `SourceIngestDB.upsert`
  and a real `sources.json`, then drive the **actual subprocess**.
- Inventory tests build a real `yengo-search.db` (matching the publisher's
  schema) and call `write_inventory_snapshot()` to seed `inventory.json`,
  then assert the cockpit reads counts from the snapshot only — including
  a regression test that the cockpit returns zeros when the SQLite DB is
  present but the snapshot is missing (the architectural guarantee).
- Runs tests write real run-state JSON files in the same shape the pipeline
  emits, including the heavy fields the cockpit must strip.
- Run-controller tests spawn a tmp `backend/puzzle_manager` package shim
  (real subprocess, real Popen, real reader threads, real asyncio queues).
- HTTP/SSE route tests use the same shim pattern via `TestClient` —
  the wire path is FastAPI → `RunController` → real subprocess.
- `test_routes_lock.py` and `test_routes_admin.py` shim the relevant
  subcommands and drive behavior via env vars
  (`YENGO_FAKE_LOCKED`, `YENGO_FAKE_RC`, `YENGO_FAKE_PL_JSON`, …).
- `test_routes_maintenance.py` uses an argv-echoing shim and asserts
  against `RunSnapshot.command` to pin flag translation; one test exercises
  cross-subcommand 409 (clean → rollback/vacuum-db) for the shared guard.
- `test_run_controller.py` includes one `@pytest.mark.slow` smoke test
  against the **real** `python -m backend.puzzle_manager validate`.

Run with `pytest tools/yengo_dashboard/tests/ -q` from the repo root (uses the
top-level `pytest.ini`, not the backend's `pyproject.toml`).

## Adding a new endpoint

Decide which side of principle #6 the data lives on:

1. **Interpretation needed** (status enums, classification, anything that
   reads as domain meaning) → add a CLI subcommand or `--json` flag to
   `backend/puzzle_manager`, write its tests there, then call it from
   `pipeline_runner.py`.
2. **Pure passthrough** (counts, file listings, JSON shape projection) →
   add a method to `state_reader.py`, a Pydantic model in `models.py`, a
   route in `routes_read.py`, and a real-fixture TestClient test.
3. **Long-running mutation** (ingest, analyze, publish, fresh-rebuild) →
   route through `RunController`. The controller already enforces
   single-active-run, captures stdout/stderr, and publishes via SSE. Do
   NOT spawn a second subprocess manager; extend `RunController` if a new
   transport (e.g. WebSocket) is needed.

If you find yourself writing `if status == 0: bucket = "ingested"` in this
tool, you are violating principle #6. Stop and add the named buckets to the
CLI instead.

## Path conventions

`StateReader._rel_posix` returns repo-relative POSIX paths. Absolute paths
in API responses are a sign that fixture roots live outside `repo_root` —
fine for tests, never acceptable for the production response.

## Defaults

- Port: `8201` (CLI flag: `--port`)
- Host: `127.0.0.1` (CLI flag: `--host`)
- Repo root: auto-detected from `__file__` (3 levels up)
- Config dir: `None` → CLI uses `backend/puzzle_manager/config/`

## Out of scope (today)

- Authentication. Loopback only; do not bind to non-loopback.
- Cross-host deployment. The cockpit is a developer tool.
- Caching. Cold subprocesses are ~300–600 ms; the 3 s poll cadence in PLAN.md
  is the budget. If cadence ever needs to drop below that, the right answer
  is "expose a polling daemon in puzzle_manager", not "cache in the cockpit".
