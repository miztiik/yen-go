# pm-cockpit — Plan

**Last Updated**: 2026-05-05
**Status**: Phase 3 complete (maintenance actions); Phase 4 polish remains
**Correction Level**: 5 (Fundamental — new module + service architecture)

> **Living plan.** Once decisions are locked and the tool is operational end-to-end, the architectural rationale moves to `docs/architecture/tools/pm-cockpit.md` and the operating guide to `docs/how-to/tools/run-pm-cockpit.md`. This file then narrows to "what's next" only.

---

## 0. Operating Principles (non-negotiable)

These override anything else in this doc. If a phase plan or implementation choice conflicts, the principle wins.

1. **No mocks. No samples. No fake data. No stubs.** Every shipped slice runs against the real `puzzle_manager` pipeline, real SQLite databases (`yengo-search.db`, `yengo-content.db`, per-source `.yengo-ingest.sqlite`), real `.pm-runtime/state/*.json` files, and real `.pm-runtime/logs/*.log` streams. No "TODO: replace with real data" code paths. No placeholder JSON. No demo mode. If the data isn't there yet, we either don't render that view or render a real empty state (defined in §5) — never a fabrication.
2. **Every phase is a complete product.** A phase landing means: real users (the operator) can use what shipped, end-to-end, against real pipeline state, without follow-up work to "make it real". No phase exists to lay scaffolding for the next.
3. **Start small in scope per commit, not in fidelity per slice.** Small commits, narrow surface area per change, but each merged change is real and works. We do not ship a fake adapters table that gets replaced in Phase 1.5 by a real one.
4. **Tests use real fixtures.** Integration tests spin up a real ephemeral pipeline state directory (a real adapter run against a tiny corpus checked into `tests/fixtures/`), real SQLite databases (created by the actual `build_content_db` / `build_search_db` calls), and real subprocesses where applicable. No `unittest.mock` patches of pipeline internals to fake out behavior the cockpit depends on. `pytest` fixtures wrap the real thing; they do not impersonate it.
5. **All phases are shipping requirements.** §9's phase list is the order of work, not a scope filter. Phase 4 ("Polish + docs migration") is not optional or future-tense — the project is not done until docs are mirrored to `docs/architecture/tools/pm-cockpit.md` and `docs/how-to/tools/run-pm-cockpit.md` per project standards.
6. **Presentation-only boundary.** `tools/pm_cockpit/` is a pure presentation layer over `backend/puzzle_manager/`. The cockpit is **allowed** to: (a) spawn `python -m backend.puzzle_manager …` subprocesses, (b) read SQLite databases (`yengo-search.db`, `yengo-content.db`, per-source `.yengo-ingest.sqlite`) and JSON state files (`.pm-runtime/state/*.json`) as raw data, (c) tail log files, (d) render results as HTML/JSON/SSE. The cockpit is **not allowed** to: parse SGF, compute hashes, classify puzzles, decide what a run-state field means, judge whether a lock is "stuck", or hold any other domain knowledge. **If the UI needs data or a derived value the pipeline does not already expose, the rule is "add a CLI subcommand or a read-only query method to `puzzle_manager` first, then the cockpit calls it"** — never reach across the boundary by re-implementing inside `tools/pm_cockpit/`. Architecturally this protects (i) the `tools/` → `backend/` no-import rule, (ii) the CLI as canonical interface, (iii) the operator's ability to verify any UI value by running the equivalent CLI command. Concretely: `data_readers.py` does `SELECT … FROM …` and returns rows; it does not interpret them. Interpretation lives in `puzzle_manager`.

---


## 1. Goal

Provide a localhost browser UI + tiny Python server that wraps the existing `backend/puzzle_manager` CLI, so running and monitoring the pipeline across many adapters does not require remembering CLI flags or correlating log files by hand.

Mental model: same posture as `tools/weiqi101/receiver.py` (zero-friction localhost server) but with an HTML UI on top, similar in spirit to `tools/puzzle-enrichment-lab/bridge.py` (FastAPI + SSE).

### Why now

The pipeline will publish ~200,000 puzzles across many adapters. Operating it through CLI alone is the current bottleneck — easy to forget which adapter ran, easy to lose a failed batch in the logs, hard to see "what's the state of the world" at a glance.

## 2. Non-Goals

- Not a replacement for the CLI. Every action in the UI corresponds to a CLI command; CLI remains canonical.
- No multi-user / no auth / no remote access. Localhost-only, single operator, mirroring `weiqi101` posture.
- Not a log archive. Reads live `.pm-runtime/logs/*` and SQLite state; no separate log database.
- Not exposed from the pipeline package itself. Lives under `tools/`, may not be imported by `backend/puzzle_manager/` (architecture rule §2 — operational tooling does not become a pipeline dependency).
- No new pipeline features. Surfaces what already exists.

## 3. Constraints (from CLAUDE.md and architecture rules)

- POSIX relative paths in any persisted/serialized output (logs, JSON responses where paths appear).
- TypeScript/Python type safety (Python: hints + ruff; frontend: strict TS *only if* we adopt TS — see §6).
- `tools/` may not import from `backend/`. The server invokes `puzzle_manager` as a **subprocess** (`python -m backend.puzzle_manager …`), and reads SQLite databases / log files **directly** as data files. It does not import pipeline modules.
- Buy-don't-build: use FastAPI + uvicorn (already in tree via bridge.py), Tailwind CDN, vanilla JS. No SPA framework, no bundler.
- Update `AGENTS.md` for `backend/puzzle_manager/` if any pipeline-side change ships (e.g. SIGTERM hardening).

## 4. Architecture (Option C — adopted)

```
┌────────────────┐  HTTP/SSE  ┌─────────────────┐  Popen  ┌──────────────────────────┐
│  Browser UI    │ ─────────► │ pm-cockpit      │ ──────► │ python -m puzzle_manager │
│  (vanilla JS,  │ ◄───SSE─── │ FastAPI server  │ ◄─pipe─ │   run / ingest / clean / │
│   Tailwind CDN)│            │ (localhost:8201)│         │   rollback / …           │
└────────────────┘            └────────┬────────┘         └──────────┬───────────────┘
                                       │  reads (no writes)          │  writes
                                       ▼                              ▼
                          ┌───────────────────────────┐   ┌─────────────────────────────┐
                          │ .pm-runtime/logs/*.log    │   │ external-sources/*/         │
                          │ .pm-runtime/state/*.json  │   │   .yengo-ingest.sqlite      │
                          │ yengo-puzzle-collections/ │   │ yengo-puzzle-collections/   │
                          │   yengo-search.db         │   │   yengo-content.db          │
                          └───────────────────────────┘   └─────────────────────────────┘
```

### Two execution paths

| Action class | How it runs | Why |
|---|---|---|
| **Read — interpretation-heavy** (adapters/source-status, run-state-summary, anything that maps stored integers to domain meanings or aggregates per-source state) | Server spawns `python -m backend.puzzle_manager <cmd> --json` and parses stdout JSON | Per §0.6, all interpretation lives in `puzzle_manager`. CLI is canonical. Cost: ~300–600 ms per call → fine at 3 s poll cadence. |
| **Read — pure data passthrough** (publish log raw lines, JSON state file contents, log tail) | Server reads files directly with stdlib (`sqlite3`, `json`, file I/O) and returns raw rows / strings | Zero interpretation = no boundary violation. Faster than subprocess. |
| **Mutate** (run, ingest, clean, rollback, vacuum-db, enable-adapter) | Server spawns `subprocess.Popen([..."python", "-m", "backend.puzzle_manager", cmd, ...])` and streams stdout + tails the per-stage JSONL log into one SSE channel | Crash isolation; respects existing `config-lock`; CLI remains source of truth |

### Why subprocess + SSE (resolved tradeoff)

User question: "why can't we have both?" — we can. Compromises accepted:

1. **Log latency ≈ 200–500 ms** (file flush + tail interval). For runs measured in minutes-to-hours, irrelevant.
2. **`PYTHONUNBUFFERED=1`** set on the child process so stdout is line-buffered.
3. **Cancel = SIGTERM**. Pipeline must (a) release `config-lock`, (b) flush per-source `.yengo-ingest.sqlite`, (c) write a final `state.json` snapshot. **Pre-flight task: audit current shutdown path; harden if needed (likely a small commit in `backend/puzzle_manager/`).**
4. **Two log streams merged in the server**: child stdout (human-readable) + `.pm-runtime/logs/{stage}.log` JSONL (structured per-puzzle events). UI shows them in one scrolling pane with tags distinguishing source.
5. **Orphaned-lock recovery**: if a child crashes leaving `config-lock` claimed, server detects it on next status query and surfaces a "stuck — release?" affordance that maps to `puzzle_manager config-lock release`.

## 5. UI Surface (v0.1)

> **UX consultation pass 1 integrated** (DevTools-UX / Mika Chen, 2026-05-05). Six required changes incorporated below; see §15 for the change log.

Three tabs, single-page, no routing library. **Default tab on open**: Live Run if a run is currently active (detect via `.pm-runtime/state/`); otherwise Adapters. **Default theme**: dark (operator tool, long sessions); light toggle in top bar, persisted in `localStorage["pm_cockpit.theme"]`. Minimum supported width: 1280 px; not designed for mobile.

**Drawer model** (cross-cutting): the right-side drawer is a single shared component. **At most one drawer open at any time** — opening a new drawer (e.g. failed-run drill-in from History) closes the current one. Switching tabs closes any open drawer. `Esc` closes the drawer. The drawer never overlays the Live Run log pane (when a run is active and Live Run is mounted, the drawer pushes content left rather than covering it).

**Loading state** (cross-cutting): tables render skeleton rows (3 placeholder rows, animated `slate-700/50` shimmer) while initial SQLite reads resolve. Spinners only for action-triggered async operations >300 ms. Never blank panes during load.

**Read-side error state** (cross-cutting): if a backing data source is unreadable (corrupted SQLite, missing `.pm-runtime/state/`, etc.), the affected row/section renders an inline error chip ("Read failed — [Retry] [View error]") in `rose` text, not silently empty. Tab-level errors (entire data source missing) render a top-of-pane banner with the same controls.

**Keyboard map** (v0.1):
- `1` / `2` / `3` — switch to Adapters / Live Run / History
- `j` / `k` — row nav (down / up) in Adapters and History tables
- `Enter` — expand currently-focused row (Adapters) or open drill-in drawer (History)
- `o` — open drawer for focused row
- `Esc` — close drawer / dismiss inline confirm
- `/` — focus filter search (Live Run, History)
- All shortcuts disabled while focus is in a text input

### 5.1 Adapters tab

One row per source. **Compressed for scan-ability** — operator must identify a failing adapter in ≤3 seconds even with 20 rows.

Always-visible row content (left → right):
- `DEFAULT` pill (only on the active source — leftmost gutter)
- Adapter name (bold, truncated with ellipsis at 32 chars; full name in `title` tooltip — names like `cho-chikun-life-and-death-elementary` are real and must not break the row)
- Status dot (8px, semantic color — see §5.4) — **also carries a state glyph for colorblind users**: idle = `○`, running = `●` pulsing, succeeded = `✓`, failed = `✕`, stuck = `▲`. Glyph rendered inside the dot at 6px, not next to it.
- Compound count chip: `Pending · Ingested · Skipped · Failed` as one monospaced 4-numeral chip; **Failed** colored rose **and bold** when `>0` (color + weight, not color alone)
- Primary action: **Run** button (icon + label, solid). The 90% action.

Expand-on-click section (per row):
- Secondary actions (icon-only with `aria-label` + tooltip): **Ingest**, **Clean** (no Status — that role is served by the row's status dot + drawer trigger; pass-2 cleanup)
- Last run (relative + absolute on hover) and duration
- Source URL / config path (truncated; full path on hover)
- Active tag filters

Right-side drawer (opens from a row "details" affordance — the chevron at the row's far right):
- Per-adapter recent run history (last 5)
- Raw config JSON (read-only, syntax-highlighted)
- Per-stage counts breakdown
- "Set as default" button (with confirm) — rare action, kept out of the row

**Stuck-state recovery**: clicking an amber stuck dot opens the drawer **scrolled to a "Pipeline lock held by orphaned process [PID 12345] since 14:22 — [Release lock]" callout at the top**. Release-lock action wraps `puzzle_manager config-lock release` and refreshes the row.

Top of pane: published-corpus headline ("9,124 puzzles published — 8,201 curated, 923 practice") from `yengo-search.db`. If any adapter is in stuck state, the tab label itself shows a count badge: `Adapters (2 stuck)`.

**Empty state** (no adapters configured in `sources.json`): centered card "No adapters configured. Edit `config/sources.json` and refresh." with a copy-path button. **First-time state** (adapters configured, zero runs ever): show all rows with `—` in count chip + `Never run` in last-run column; floating tooltip on the first row's Run button: "Click Run to start your first ingest."

Counts come from `SELECT status, COUNT(*) FROM files GROUP BY status` against each source's `.yengo-ingest.sqlite`. Active indicator from `sources.json` `active_adapter`.

### 5.2 Live Run tab

Activated when a run is in flight (Adapters tab indicator points here).

- **Sticky top bar**: stage progress bar (Ingest → Analyze → Publish, status from `RunState` snapshots). Right-aligned **Cancel** button — outline-rose, disabled when no run active. Click triggers **inline morph confirm** ("Cancel run? [Confirm] [Keep running]" for 4s, then reverts). `Esc` dismisses, `Enter` fires. **No modal** — modals interrupt log reading on a streaming view.
- **Single merged log pane** (not split). JSONL events from `.pm-runtime/logs/{stage}.log` and subprocess stdout share one stream, distinguished by a 4 px **left-edge color stripe**: `sky` for structured JSONL, `slate` for stdout text.
- **Default density**: one line per event, monospace 12px: `HH:MM:SS.mmm  STAGE  LEVEL  source-tag  message  …meta`. Click to expand into a full-payload card (precedent: `log-viewer/`).
- **Auto-scroll**: on by default, **pauses when user scrolls up >100 px**, resumes when they return to bottom. Floating "▼ Resume tail (N new)" pill while paused. Never rip scroll position out from under the operator.
- **Filter bar** (sticky above stream): stage chips (multi-select), level (`debug` off by default; `info`/`warn`/`error` on), source-tag (search + autocomplete), text search (`/` to focus, DevTools idiom). Active-filter badge on a "Clear filters" button.
- **Empty state — filters yield zero**: centered "No events match these filters — [Clear filters]". Never blank pane.
- **Empty state — no active run**: centered card "No run in progress. [Go to Adapters]" with a brief explainer "Live Run streams logs while a pipeline run is active." Tab is still reachable (e.g., for keyboard nav) but encourages return to Adapters.

### 5.3 History tab

Past runs from `.pm-runtime/state/*.json`. **Default sort**: Started DESC. **Default filter**: last 30 days, all statuses.

Columns (left → right): Started (relative + absolute on hover), Duration, Adapter, Stage(s), Status (semantic pill), Puzzles in→out (`1.2k → 1.18k`), Trigger (manual/scheduled/cli — derived from `RunState.trigger` field; if the field is absent on a run, render `—` rather than guessing). Seven columns max.

Click a row → **right-side drawer** (preserves table context for comparison; not a new page; shares the cross-cutting drawer described in §5):
- Run summary card at top
- Horizontal **stage stepper** (ingest → analyze → publish), each step colored by outcome and clickable to scroll to that stage's logs
- Full log stream (Live Run viewer in frozen/historical mode)
- **For failed runs**: first-error event surfaced as a callout card at the top of the drawer ("Failed at stage `analyze`, event 4,231: `KeyError: 'YL'`") with a "Jump to event" button. **Single most important UX in the whole tool** — when a 200K publish fails at hour 3, root cause must be visible within 5s of opening the run.

**Empty state** (no runs ever): centered card "No history yet. Past pipeline runs will appear here." with secondary copy "Start a run from the Adapters tab." Filter-cleared empty state: "No runs match these filters — [Clear filters]."

Search across `publish-log` → wraps `puzzle_manager publish-log search`.

### 5.4 Color semantics (Tailwind palette)

Single source of truth — no other semantic colors permitted in v0.1. Will be mirrored to `tools/pm_cockpit/colors.md` when implementation starts; CI grep can fail the build on out-of-palette hex codes in state-bearing classes.

| State | Tailwind | Hex | Glyph (colorblind backup) | Use |
|---|---|---|---|---|
| idle | `slate-400` | `#94a3b8` | `○` | dot, neutral chip text |
| running | `sky-500` + `animate-pulse` | `#0ea5e9` | `●` | dot, progress bar |
| succeeded | `emerald-500` | `#10b981` | `✓` | dot, success badge |
| failed | `rose-500` | `#f43f5e` | `✕` | dot, failed count (also bold), error log lines |
| stuck (orphaned lock) | `amber-500` + diagonal-stripe SVG bg | `#f59e0b` | `▲` | dot — distinct from running and failed |

`rose` (not `red-500`) so failure can coexist with `amber` warnings without vibrating. Never reuse `emerald` for "increased count" or any non-success meaning. **Color is never the sole carrier of state**: every state pairs with a glyph (above) plus, where applicable, a text-weight emphasis (failed counts are bold). Verified roughly against deuteranopia simulation: the glyph + weight differences make rose vs amber distinguishable even when hue collapses.

### 5.5 Iconography

Keep the project's no-emoji rule (CLAUDE.md). Reasoning extends to pm_cockpit: emoji rendering varies by OS, breaks alignment in monospace log views, can't be styled. Use the existing SVG icon set from `frontend/src/components/shared/icons/` if statically importable; otherwise inline a minimal Heroicons subset (MIT, Tailwind-native). v0.1 needs ~6–8 icons: `play`, `square` (cancel), `broom` (clean), `info`, `chevron-down`, `circle` (status dot), `download` (export later), `filter`.

## 6. Tech Choices

| Concern | Choice | Rationale |
|---|---|---|
| Server framework | **FastAPI + uvicorn** | Already a project dep via `bridge.py`; SSE is one decorator; Pydantic models give us schema-validated responses for free. Stdlib `http.server` rejected — manual SSE + manual JSON validation is busywork. |
| UI framework | **Vanilla JS, no bundler, no build** | Matches `tools/puzzle-enrichment-lab/log-viewer/` precedent. Lifetime of this tool may exceed the half-life of any framework choice; zero-build means it just keeps working. |
| Styling | **Tailwind via CDN + small `styles.css`** | Same pattern as log-viewer; zero build step; CLAUDE.md mentions reusing Tailwind. |
| Charts (later) | **Chart.js via CDN** if/when we add timing charts | Already used by log-viewer. Optional. |
| Process invocation | **`subprocess.Popen` with `PYTHONUNBUFFERED=1`** | See §4. |
| Live updates | **SSE** for log streams; polling (every 3s) for adapter counts | SSE for one-direction streaming is simpler than WebSocket and matches `bridge.py`. Counts change slowly enough that polling is fine. |
| State persistence | **None of its own** | Server is stateless across restarts. All data lives in existing SQLite + JSON files. |
| Default port | **8201** | Picked to be distinct from weiqi101 (8101) and bridge.py. Configurable via `--port`. |

## 7. API Surface (v0.1, draft)

Naming convention follows `bridge.py`. All under `/api/`.

### Read endpoints (GET)

| Path | Returns |
|---|---|
| `/api/health` | `{ ok: true, version, uptime_s }` |
| `/api/adapters` | List of adapters with per-source counts (queries each `.yengo-ingest.sqlite`) |
| `/api/adapters/{id}/status` | Detailed source status (wraps `cmd_source_status` data) |
| `/api/inventory` | Published-corpus summary (wraps `InventoryManager.summary()` data via direct DB read) |
| `/api/runs` | List of past runs (`.pm-runtime/state/*.json`) |
| `/api/runs/{run_id}` | One run's detail + stage logs |
| `/api/publish-log/search?q=…` | Wraps `cmd_publish_log` search |
| `/api/config-lock` | Current lock state (read `.pm-runtime/state/config.lock` or equivalent) |

### Mutate endpoints (POST, SSE-streamed where long-running)

| Path | Body | Streams |
|---|---|---|
| `/api/run` | `{ source?, stages?: ["ingest","analyze","publish"], opts? }` | SSE: stage-start, log-line, stage-end, complete/error |
| `/api/ingest` | `{ source }` | SSE |
| `/api/clean` | `{ target: "staging"\|"state"\|"logs"\|… }` | SSE (short) |
| `/api/rollback` | `{ run_id?, puzzle_id? }` | SSE |
| `/api/vacuum-db` | `{ rebuild?: bool }` | SSE |
| `/api/enable-adapter` | `{ source }` | JSON (instant) |
| `/api/disable-adapter` | `{ source }` | JSON (instant) |
| `/api/cancel/{run_token}` | `—` | JSON (sends SIGTERM) |
| `/api/config-lock/release` | `—` | JSON (wraps `config-lock release`) |

Pydantic models for every request and response. OpenAPI lives at `/docs` for free (FastAPI built-in) — satisfies the project's "OpenAPI compliant API design" preference.

### Concurrency rule

Server enforces "one mutating run at a time" by checking `config-lock` before issuing any subprocess that touches it. UI button states reflect lock status.

## 8. Repository Layout (proposed)

```
tools/pm_cockpit/
├── PLAN.md                    ← this file
├── AGENTS.md                  ← architecture map (added before v0.1 lands)
├── README.md                  ← short pointer to docs/how-to/tools/run-pm-cockpit.md
├── server/
│   ├── __init__.py
│   ├── __main__.py            ← `python -m tools.pm_cockpit` entry
│   ├── app.py                 ← FastAPI app factory
│   ├── routes_read.py         ← GET endpoints
│   ├── routes_mutate.py       ← POST endpoints + SSE streams
│   ├── pipeline_runner.py     ← Popen wrapper, SIGTERM handling, log multiplexing
│   ├── data_readers.py        ← SQLite + state-file readers (no pipeline imports)
│   └── models.py              ← Pydantic request/response schemas
├── ui/
│   ├── index.html
│   ├── app.js                 ← view router + fetch + SSE client
│   ├── views/                 ← adapters.js, live-run.js, history.js
│   └── styles.css
└── tests/
    ├── test_data_readers.py
    ├── test_pipeline_runner.py  ← uses a fake CLI script as the subprocess
    └── test_routes.py           ← FastAPI TestClient
```

## 9. Phases

Phases are **the order of work**, not a scope filter. Per §0.5, all phases ship — the project is not done until Phase 4 (docs migration) lands. Each phase ships **real, working functionality against real pipeline state** (§0.1) and is independently mergeable.

The colors-line "MVP" or "v0.1" appearing anywhere else in this doc means "the smallest **real** working slice", never "a placeholder slice".

| Phase | Scope (real, no mocks) | Acceptance | Status |
|---|---|---|---|
| **0 — Pre-flight: pipeline shutdown safety** | Two pipeline-side fixes inside `backend/puzzle_manager/`, each with a real-DB regression test: (a) `PRAGMA journal_mode=WAL` in `core/content_db.py`, (b) `f.flush()` in `publish_log.py:write_batch()`. See §14 for evidence and exact lines. | Both fixes merged. New tests pass. Full pipeline test suite passes. | ✅ done (2026-05-05) |
| **1 — Read-only operator surface** | FastAPI server (`tools/pm_cockpit/server/`), Adapters tab + History tab + headline. All read endpoints in §7 wired to real `.yengo-ingest.sqlite`, `.pm-runtime/state/*.json`, and published `yengo-search.db`. Real empty/loading/error states from §5. **No mutations yet** — the Run / Ingest / Clean buttons render as **disabled with a tooltip "Mutations enabled in Phase 2"**. They do not call any endpoint, do not show optimistic state. | Operator opens `http://localhost:8201` against the real repo, sees real adapter counts, real published-corpus headline, real run history pulled from `.pm-runtime/state/`. Visual parity with §5. Ten-puzzle real ingest run beforehand → counts update on poll. | ✅ done (2026-05-05). Live against real repo: 7 sources, 799 puzzles, 21 runs. AGENTS.md + architecture + how-to docs published. |
| **2 — Live mutating runs** | `/api/run` and `/api/ingest` POST endpoints, real `subprocess.Popen` against `python -m backend.puzzle_manager`, real SSE stream multiplexing real subprocess stdout + real `.pm-runtime/logs/*.log` JSONL. Live Run tab with Cancel (real SIGTERM). Orphaned-lock detection + Release-lock action (wraps real `python -m backend.puzzle_manager config-lock release`). Buttons in Adapters tab become enabled. | Operator launches a real adapter ingest from the UI against real source data, sees real log lines stream in <500 ms latency, cancels mid-run, observes lock released cleanly, can re-run immediately. | ✅ done (2026-05-05). 5 slices: A=`RunController`, B=`/api/run/*` + SSE, C=`/api/lock/*`, D=Live Run tab + adapter buttons, E=real-pipeline smoke. 33 pm_cockpit tests pass; SSE stream verified end-to-end against real `python -m backend.puzzle_manager run`. |
| **3 — Maintenance actions** | `/api/clean`, `/api/rollback`, `/api/vacuum-db`, `/api/adapter/enable`, `/api/adapter/disable`, `/api/publish-log/search` — all wrapping real CLI commands against real DBs. UI affordances per §5. | Each maintenance action invokable from UI executes the real CLI command end-to-end and reflects results without page reload. Full real-CLI feature parity for the operator-relevant subset. | ✅ done (2026-05-05). 5 slices: F=`routes_maintenance.py` (clean/rollback/vacuum-db via shared RunController), G=`routes_admin.py` (adapter enable/disable + publish-log search via PipelineRunner), H=Maintenance tab UI + per-adapter Enable button, I=real-pipeline smoke (`vacuum-db --dry-run` exit 0; real `publish-log search` returns 2 entries; no-filter call → 400 with hint), J=docs (this row). 55 pm_cockpit tests pass. |
| **4 — Docs migration + polish** | `docs/architecture/tools/pm-cockpit.md`, `docs/how-to/tools/run-pm-cockpit.md`, `docs/reference/pm-cockpit-api.md`, `tools/pm_cockpit/AGENTS.md`, `tools/pm_cockpit/colors.md`, `tools/pm_cockpit/README.md`. Final tightening: keyboard shortcuts shake-down, accessibility audit pass, perf check on `/api/adapters` against the real corpus. | All four docs published per `docs/reference/documentation-structure.md` rules (Diataxis tier, Last Updated, See Also). AGENTS.md complete and dense. PLAN.md trimmed to "Status: Stable" mode. | partial — architecture + how-to + AGENTS.md landed in Phase 1; reference/api + colors.md + README.md remain |

**No phase ships behind a feature flag, behind a `MOCK_DATA` env var, or with stubbed endpoints. If a phase isn't ready to be the operator's real tool that day, the phase isn't ready.**

## 10. Locked Decisions (2026-05-05)

1. **Port** — default `8201`, configurable via `--port`.
2. **Directory + module** — `tools/pm_cockpit/` (underscore). Invoked as `python -m tools.pm_cockpit`. Pipeline subprocesses are `python -m backend.puzzle_manager` (matches `backend/puzzle_manager/CLAUDE.md`). No launcher script. Don't fight the system.
3. **Phase 0 SIGTERM audit** — runs first as a standalone investigation. If it surfaces a bug, that's a worthwhile commit on its own and de-risks Phase 2.
4. **Confirmation modals** — defer. Iterate after a working UI exists; don't pre-design.
5. **UX design** — done in collaboration with the `DevTools-UX` custom agent (Mika Chen). All UI decisions in §5 (layout, color, defaults, collapsibility, control types — toggle vs checkbox vs pill, information hierarchy, what's hidden by default) go through a UX consultation pass before implementation. UX findings recorded in §5 as they crystallize.
6. **AGENTS.md** — match `backend/puzzle_manager/AGENTS.md` density. No separate decision needed.

### Still open (deferred, not blocking)

- Historical metrics (puzzles/min over 7d, etc.) — out of scope for v0.1; reconsider in Phase 4 if real demand emerges.

---

## 14. Phase 0 Audit Findings (2026-05-05)

Investigation: does `python -m backend.puzzle_manager` shut down cleanly under SIGTERM mid-run?

### Risk table

| Area | Behavior | Safe under SIGTERM? | Evidence |
|---|---|---|---|
| Config-lock release | Acquired in try/finally; finally blocks fire on SIGTERM-induced SystemExit | **Yes** | `cli.py:235–250` |
| Per-source `.yengo-ingest.sqlite` | WAL mode on; try/finally close → commit; per-100 batch commits | **Yes** | `source_ingest_db.py:218`; `local/adapter.py:294–369` |
| `yengo-search.db` | Built to temp file with transaction context, atomically swapped via `os.replace()` | **Yes** | `publish.py:647–656`; `db_builder.py:254–264` |
| `yengo-content.db` | Explicit `commit()` per batch; **no WAL mode** | **Conditional — must fix** | `content_db.py:192,247` |
| Publish log entries | `write()` flushes; `write_batch()` does not | **Partial** | `backend/puzzle_manager/publish_log.py:70` vs `:89` |
| Batch state JSON | `atomic_write_text()` with `.tmp` + rename | **Yes** | `batch_writer.py:144`; `atomic_write.py:73–77` |
| Rollback lock | Same try/finally pattern | **Yes** | `rollback.py:137–187` |

### Must-fix before Phase 2

1. **WAL on `yengo-content.db`** — `core/content_db.py:192`, add `conn.execute("PRAGMA journal_mode=WAL")`. **Reason**: pm_cockpit will read concurrently while the pipeline writes. Without WAL, readers and writers block each other and reader isolation is weak. Mirror the pattern from `source_ingest_db.py:218`.
2. **Flush in `PublishLogWriter.write_batch()`** — `backend/puzzle_manager/publish_log.py:89` (note: this file lives at the root of `puzzle_manager/`, not under `core/`), add `f.flush()` after the loop. **Reason**: OS buffer holds 100 ms–1 s of entries; SIGTERM in that window loses the batch. `write()` already flushes; this is consistency.

Both are 1-line changes inside `backend/puzzle_manager/`. Each gets its own commit on a feature branch, lands before any pm_cockpit Phase 2 work begins.

### Nice-to-have hardening (post-Phase 2)

- Explicit `signal.signal(SIGTERM, …)` handler in `cli.py:main()` — finally blocks already work, but explicit is safer than implicit.
- `os.fsync()` after publish-log batch flush — maximum durability for auditing; resumability already covers loss.

---

## 15. UX Pass Log

### Pass 1 — DevTools-UX (Mika Chen), 2026-05-05

Six required changes, all incorporated into §5 above:

| # | Concern | Resolution |
|---|---|---|
| RC-1 | Adapters row over-loaded (4 buttons × 4 badges × 20 rows) | §5.1: 1 chip + 1 primary `Run` + expand-on-click for secondary actions + drawer for rarely-used config |
| RC-2 | Pipeline state palette undefined → drift risk | §5.4: Tailwind mapping (slate / sky / emerald / rose / amber); colors.md to be added at implementation time; CI grep guard |
| RC-3 | Cancel-run affordance unspecified → too-easy or too-hard | §5.2: sticky top-bar, outline-rose, inline morph confirm (4 s), `Esc`/`Enter`, disabled when idle |
| RC-4 | Live Run streaming defaults missing | §5.2: single merged stream with origin stripes; auto-scroll-pause-on-user-scroll; default filters; empty state |
| RC-5 | History drill-in for failed runs | §5.3: right-side drawer; first-error callout card with "Jump to event"; horizontal stage stepper |
| RC-6 | First-open + theme defaults | §5: open to Live Run if active, else Adapters; dark default with `localStorage` persistence; min width 1280 px |

**Caveat noted**: Mika worked from this PLAN's prompt summary + the `log-viewer/` precedent files, not from this file directly (her tool environment failed mid-session). Recommendations are still grounded in real precedent. **A pass-2 re-review against the now-updated §5 is queued for after the must-fix audit commits land** — verifies wording and catches anything the summary lost in translation.

### Pass 2 — Self-review (DevTools-UX subagent unavailable), 2026-05-05

The DevTools-UX subagent stalled twice (filesystem sandbox could not see this PLAN.md, then the second invocation failed to issue tool calls at all). Rather than block the plan, the plan author ran a self-review against §5 honestly, with a low-confidence flag. Findings should be re-validated by Mika once the subagent environment is fixed.

**Pass-1 RC verification:**

| RC | Status | Note |
|---|---|---|
| RC-1 | Resolved | §5.1 row compresses cleanly |
| RC-2 | Resolved | §5.4 palette + planned `colors.md` + CI grep guard |
| RC-3 | Resolved | §5.2 sticky outline-rose with morph confirm |
| RC-4 | Resolved | §5.2 stripes, scroll-pause, default filters, `/` shortcut |
| RC-5 | Resolved | §5.3 drawer + first-error callout + stage stepper |
| RC-6 | Resolved with new RC-7 | Theme + default tab present; **Adapters empty state** was missing — added in pass 2 |

**New RCs from pass 2 (all applied to §5 in this same edit):**

| RC | Concern | Resolution |
|---|---|---|
| RC-7 | First-load empty states for Adapters / Live Run / History undefined | §5.1, §5.2, §5.3: added explicit empty-state copy + CTAs for both "no data ever" and "filters cleared" |
| RC-8 | Stuck-state recovery flow location undefined | §5.1: clicking the amber dot opens drawer scrolled to a "Release lock" callout that wraps `puzzle_manager config-lock release` |
| RC-9 | Drawer model collisions across §5.1 / §5.2 / §5.3 undefined | §5 preamble: shared component, at most one open, tab switch closes it, never overlays Live Run pane |
| RC-10 | Loading state undefined (SQLite cold reads = ~200 ms) | §5 preamble: skeleton rows during initial load; spinners only for action-triggered async >300 ms |
| RC-11 | Read-side error state undefined (corrupt DB / missing state dir) | §5 preamble: row-level error chip with retry; tab-level banner for entire-source failures |
| RC-12 | Color is sole carrier of state in §5.4 (colorblind risk) | §5.4: every state pairs with a glyph (`○●✓✕▲`) inside the dot; failed counts also bold |
| RC-13 | Keyboard nav under-defined | §5 preamble: minimal map (`1`/`2`/`3` tabs, `j`/`k` rows, `Enter` expand, `o` drawer, `Esc` close, `/` search) |
| RC-14 | `Status` button in §5.1 row redundant with status dot + drawer trigger | §5.1: removed `Status` from secondary actions; drawer chevron is the only "details" entry point |
| RC-15 | Long adapter names break row layout (`cho-chikun-life-and-death-elementary` is real) | §5.1: 32-char ellipsis truncation, full name in `title` tooltip |

**Verdict**: Approved with minor follow-ups (all applied above). No blockers for Phase 1 (read-only MVP doesn't render Live Run or mutations). Mika should re-validate when her subagent environment is restored — flag in code review if anything contradicts professional UX intuition.

## 11. Doc-mirroring Plan

Once Phase 1 ships and the architecture is stable:

- `docs/architecture/tools/pm-cockpit.md` — this file's §3, §4, §6, §7 (rationale + diagrams), with the See Also block per docs structure rules.
- `docs/how-to/tools/run-pm-cockpit.md` — start the server, what each tab does, common operations.
- `docs/reference/pm-cockpit-api.md` — endpoint table (or rely on FastAPI's `/docs` and link to it).
- `tools/pm-cockpit/PLAN.md` — trimmed to "current phase + next steps" only; older content moved to `docs/archive/` if historically interesting.
- This PLAN.md gains a "Status: Stable" header like `tools/puzzle-enrichment-lab/PLAN.md`.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Pipeline doesn't release `config-lock` on SIGTERM → cockpit deadlocks | Phase 0 audit; add explicit signal handler if missing; UI surfaces "release lock" affordance |
| Reading `.yengo-ingest.sqlite` while pipeline writes to it | SQLite handles concurrent readers via WAL; verify pipeline opens DB with `journal_mode=WAL`. If not, set it (one-line change in pipeline) or open read-only with shared cache |
| SSE connections piling up if user opens many tabs | Cap concurrent SSE subscribers per run; new subscribers replay last N lines from log file |
| Subprocess output massive on full publish (200K puzzles) | Log tail throttled to N lines/sec server-side; full log always available via "open log file" link |
| Frontend complexity creep ("just one more chart") | YAGNI hard-line: anything not in §5 needs a PLAN.md update first |

## 13. What this is NOT (anti-scope)

- Not a build of `backend/puzzle_manager` features. If a needed action doesn't have a CLI command yet, we add the CLI command first (in `puzzle_manager/cli.py`), then surface it.
- Not a place to put pipeline business logic. The server is a thin RPC + tail facade.
- Not an excuse to bypass `config-lock`. The lock exists for good reasons; cockpit honors it like any CLI invocation.
