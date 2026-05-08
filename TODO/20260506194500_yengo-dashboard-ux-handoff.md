# yengo_dashboard UX + IA Handoff

Date: 2026-05-06
Status: Analysis only. No dashboard code changes made.
Estimated implementation scope: Level 3

## What Was Reviewed

- Live app at `http://127.0.0.1:8201/`
- `tools/yengo_dashboard/web/index.html`
- `tools/yengo_dashboard/web/app.js`
- `tools/yengo_dashboard/web/ui.js`
- `tools/yengo_dashboard/server/app.py`
- `tools/yengo_dashboard/server/routes_read.py`
- `tools/yengo_dashboard/server/routes_run.py`
- `tools/yengo_dashboard/server/run_controller.py`
- `tools/yengo_dashboard/server/state_reader.py`
- `tools/yengo_dashboard/PLAN.md`
- `tools/yengo_dashboard/AGENTS.md`
- `docs/architecture/tools/yengo_dashboard.md`
- `docs/how-to/tools/run-yengo-dashboard.md`
- `docs/reference/puzzle-manager-cli.md`
- `tools/yengo_dashboard/docs/ux-critique-2026-05-05.md`

Also consulted: `DevTools-UX` subagent for a redesign brief.

## Direct Answers To The Current Questions

### 1. Why is there a `#` in the URL?

- The current dashboard uses client-side hash navigation.
- Supported forms are `#library`, `#pipeline`, `#workshop`, `#guide`, and `#guide:<doc-path>`.
- `#/pipeline` is not the supported format. If you open that form, the app falls back to `#library` because the router only recognizes names after `#` with no leading slash.
- Hash routing is normal for a tiny SPA, but it is not required here. This localhost tool can switch to clean paths like `/run`, `/sources`, `/operations`, `/logs`, `/history` with minimal server support.

Recommendation: remove hash routing as part of the next UX pass.

### 2. Why does Pipeline only show PM runtime runs at the bottom?

- The History section is hard-wired to `GET /api/runs?limit=50`.
- That endpoint only reads `.pm-runtime/state/runs/*.json`.
- It does not include:
  - `.pm-runtime/logs/*.log`
  - publish-log audit entries
  - maintenance action history as a first-class history source
  - config-lock events

So the current bottom list is not a general activity history. It is only a run-state history.

### 3. Where are the log messages?

There are currently four separate log-ish sources, but the UI only exposes two of them well:

1. Live subprocess output
- Captured by `RunController`
- Streamed over SSE to the Live Run panel
- Only `stdout` and `stderr`

2. Run-state files
- Read from `.pm-runtime/state/runs/*.json`
- Used for the History list
- High-level summaries only

3. Stage log files
- Real files exist in `.pm-runtime/logs/`
- Example files observed:
  - `2026-05-05-ingest.log`
  - `2026-05-05-analyze.log`
  - `2026-05-05-publish.log`
  - `2026-05-05-puzzle_manager.log`
- These are not surfaced anywhere in the dashboard today

4. Publish log audit trail
- Exposed through `publish-log search`
- Currently hidden inside Workshop and rendered as raw JSON

### 4. Why does `Last failure` look wrong?

- The summary card is computed only from the currently loaded run window.
- The current client loads `limit=50` runs.
- The card therefore means: last failure in the shown 50 run-state files.
- It does not mean: last failure across all activity, all logs, or all maintenance actions.

Recommendation: rename it immediately to `Last failure (last 50 runs)` and add a tooltip explaining the scope.

### 5. What is the bottom-left `System` button?

- It opens a dialog showing:
  - version
  - uptime
  - lock state
  - active run
- There is also a bottom status strip that doubles as a system status surface.

Problem: the control is visually buried and not self-explanatory.

Recommendation: move this to a persistent header chip like `healthy · vX.Y · idle` with color by severity, and keep the dialog behind that chip.

### 6. Why does `Workshop` feel wrong?

Because it is the wrong metaphor. The tab contains vacuum, clean, rollback, and audit search. That is operations and maintenance work, not workshop work.

Recommended replacement: `Operations`

Fallback if needed: `Maintenance`

Do not use: `Admin`, `Toolbox`, `Manage`

### 7. How should help be surfaced?

The current `Guide` tab already exposes a read-only docs tree from `docs/`, but it is generic and detached from the operator workflow.

The useful help that should be surfaced in-product is:

- `run --help`
  - what `--fresh`, `--source-override`, `--dry-run`, `--no-enrichment` do
- `source-status --help`
  - what adapter stats mean
- `vacuum-db --help`
  - what rebuild does
- `publish-log search --help`
  - what filters exist
- `config-lock --help`
  - what lock status and release do

Recommendation:

- Keep the docs viewer, but demote it from primary nav.
- Add contextual help directly inside each section.
- Add a live `CLI equivalent` block on the Run screen that updates as the form changes.

## Verified Gaps Between Plan And Current Implementation

### Gap 1. Planned merged logs were not fully implemented

`PLAN.md` says the Live Run experience should merge:

- subprocess stdout
- subprocess stderr
- `.pm-runtime/logs/*.log`

Current reality:

- `RunController` only captures `stdout` and `stderr`
- it does not tail `.pm-runtime/logs/*.log`

This is the single biggest operational gap.

### Gap 2. History is named too broadly for what it actually shows

The current `Pipeline` page visually implies a general operational timeline. It is not. It is only the last 50 run-state files.

### Gap 3. `Workshop` and `Guide` are structurally mismatched with operator intent

- `Workshop` is really Operations
- `Guide` is really contextual help / docs, but it occupies a full primary nav slot instead of supporting the active task

### Gap 4. The URL model is fragile and confusing

- `#pipeline` works
- `#/pipeline` does not
- there is no user-facing explanation
- there is no reason to keep this model for a localhost FastAPI tool

## Information Architecture Options

### Surgical Triage

Use when the goal is one short polish pass with low risk.

Changes:

- rename `Workshop` to `Operations`
- keep hash URLs
- keep current nav skeleton
- make summary labels more honest
- add small inline help blocks
- lightly brighten the current dark theme

Tradeoff:

- fastest to ship
- does not solve the larger IA problem

### Bright Ops Cockpit

Use when the goal is a strong but still practical redesign.

Recommended nav:

- `Sources`
- `Run`
- `Logs`
- `History`
- `Operations`

Key changes:

- move to clean path routing
- give logs their own first-class home
- separate source management from published inventory
- move docs into contextual help / right drawer rather than a full primary tab
- make light theme the default and keep dark as optional

Tradeoff:

- medium implementation cost
- best balance of clarity and feasibility

### Activity-Stream First

Use only if the long-term goal is a full event-driven operator console.

Changes:

- replace most tabs with a unified timeline
- blend run stream, stage logs, maintenance output, and lock events into one event feed
- use filters rather than pages

Tradeoff:

- strongest operational model
- too large for the current pain level

## Recommended Direction

Use `Bright Ops Cockpit`.

Why:

1. It directly solves every current complaint without requiring a full product rethink.
2. It gives logs a real home instead of cramming them into Run History or Operations.
3. It lets the UI use normal URLs.
4. It gives the dashboard a clearer operator vocabulary.
5. It supports a bright, high-legibility look without turning the log panes into unreadable white boxes.

## Recommended Navigation Model

### `Sources`

Purpose:

- active adapter
- per-source status
- enable / disable adapter
- run launch entry points

Should not also carry a long inventory dashboard.

### `Run`

Purpose:

- launch a run
- watch the live subprocess stream
- see the stage stepper
- cancel a run
- copy the exact CLI equivalent

### `Logs`

Purpose:

- live run stream
- stage log files from `.pm-runtime/logs/`
- maintenance action tails
- publish-log audit search

Suggested sub-tabs:

- `Run stream`
- `Stage logs`
- `Maintenance`
- `Audit`

### `History`

Purpose:

- show the last N run-state files
- summarize run outcomes honestly
- show provenance clearly

Important: keep this separate from detailed logs.

### `Operations`

Purpose:

- vacuum-db
- clean
- rollback

Suggested visual grouping:

- Diagnostics
- Maintenance
- Destructive

## Log Strategy Recommendation

Do not force everything into one panel.

Use this split:

### Live run stream

- keep on the `Run` page
- source: `RunController` SSE
- scope: current command only

### Run-state history

- keep on `History`
- source: `.pm-runtime/state/runs/*.json`
- scope: high-level summaries

### Stage logs

- add to `Logs > Stage logs`
- source: `.pm-runtime/logs/*.log`
- scope: detailed stage output, including non-run diagnostics if those logs are written there

### Publish log audit

- move to `Logs > Audit`
- source: `publish-log search`
- render as a table, not raw JSON

### Maintenance action results

- show in `Logs > Maintenance`
- use existing maintenance handles and `/api/run/{handle}/tail`

## URL Strategy Recommendation

Replace hash fragments with normal paths.

Suggested mapping:

- `/sources`
- `/run`
- `/logs`
- `/history`
- `/operations`
- `/docs?file=reference/puzzle-manager-cli.md`

Backward compatibility:

- on boot, detect old hashes and rewrite them once with `history.replaceState()`

## Contextual Help Recommendation

### Keep

- the docs browser machinery
- the existing markdown serving endpoints

### Change

- remove `Guide` from the primary nav
- add a global `?` button that opens a right-side help drawer
- auto-open a relevant doc based on the active page

### Add

#### Run page help

- `What this does`
- `Equivalent CLI`
- short explanations for each flag

#### Sources page help

- what active adapter means
- what source-status counts represent

#### Operations page help

- one-line plain-language summary for vacuum, clean, rollback
- explicit risk text for rollback

## Visual Direction

Use a bright ops aesthetic.

Recommendation:

- default page background: light
- cards: white / very light gray
- primary text: slate-900
- secondary text: slate-500
- semantic pills: strong but restrained
- keep terminal/log surfaces dark regardless of theme

This gives:

- better daylight readability
- cleaner hierarchy
- strong contrast between forms/cards and actual log panes

Avoid:

- all-dark zinc/slate sludge everywhere
- purple accents for the sake of “dashboard style”
- visually equal treatment of safe and destructive actions

## Naming Recommendation

Primary label replacements:

- `Library` -> `Sources` or `Inventory`
- `Pipeline` -> `Run`
- `Workshop` -> `Operations`
- `Guide` -> remove from primary nav, keep as `Help`

Preferred final set:

- `Sources`
- `Run`
- `Logs`
- `History`
- `Operations`

## Suggested Implementation Slices For The Next Coding Agent

### Slice 1. Truthful labels

- rename `Workshop` to `Operations`
- rename `Last failure` to `Last failure (last 50 runs)`
- add provenance tooltip

### Slice 2. Bright theme

- make light theme the default
- keep dark as toggle
- keep log panels dark in both themes

### Slice 3. System chip

- replace the bottom-left `System` button with a visible header status chip
- keep current dialog behind it

### Slice 4. Clean paths

- replace hash routing with normal paths
- rewrite old hashes on boot

### Slice 5. Logs section

- add a first-class `Logs` nav item
- surface `.pm-runtime/logs/*.log`
- move publish-log search into `Logs > Audit`
- render audit data as a table

### Slice 6. Operations hierarchy

- group vacuum, clean, rollback by blast radius
- add stronger visual differentiation and confirmations

## Low-Risk Immediate Fixes

These can ship first even before the larger redesign:

1. Rename `Workshop` to `Operations`.
2. Rename `Last failure` to clarify window scope.
3. Explain the current hash URL model in-product until routing changes.
4. Promote `System` status out of the bottom-left corner.
5. Replace raw publish-log JSON with a readable table.

## Notes For The Next Agent

- The current app already has useful pieces. This is not a rewrite problem.
- The highest-value missing capability is stage log visibility.
- The next agent should not treat Run History as the universal log source.
- The docs viewer should be kept, but repositioned as contextual help.
- If only one structural change is chosen, add `Logs` as a first-class area.
