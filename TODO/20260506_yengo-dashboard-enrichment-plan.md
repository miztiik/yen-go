# Yen-Go Dashboard Enrichment Plan

> **Created**: 2026-05-06
> **Owner**: dashboard team
> **Scope**: post-redesign (slices 1–6 done) — surfacing missing pipeline-manager
> capabilities through new CLI subcommands + matching UI views.
>
> **Operating principles** (do not violate):
>
> 1. **Principle #6** — `tools/yengo_dashboard/` is a presentation layer.
>    Every theme below adds a CLI subcommand or `--json` flag in
>    `backend/puzzle_manager/` *first*, then surfaces it in the UI. The
>    cockpit MUST NOT invent domain logic.
> 2. **One slice = one PR = one commit** (mirrors the redesign cadence).
> 3. **AGENTS.md updated in the same commit** as any structural change.
> 4. **Real-fixture tests** for new endpoints (no mocks).

---

## Status Board

Update the status column as work progresses. The intent is *all* of these
get done; the order is the prioritization, not the filter.

| #  | Theme                              | Status | Phase | Notes |
| -- | ---------------------------------- | :----: | :---: | ----- |
| 0  | Operations / Logs UI polish        | ◐      |  P0   | viewHeader() helper + responsive Logs aside landed; screenshots TBD |
| 1  | Dry-run preview as first-class     | ☐      |  P0   | De-risk every destructive button. Subsumes structured preview contracts |
| 2  | Failure digest on History          | ☐      |  P0   | #1 operational question |
| 3  | Disk / runtime footprint           | ☐      |  P0   | Cheap, high signal |
| 4  | Logs grep across files             | ☐      |  P0   | One-CLI, one-search-box |
| 13 | Unified activity surface           | ☐      |  P0   | NEW: correlate runs + maintenance + publish-log + audit + lock events into one timeline |
| 14 | Inventory health surface           | ☐      |  P0   | NEW: surface CLI's --rebuild/--reconcile/--check/--fix as actions, not just counts |
| 16 | Reset blast-radius (backend concept)| ☐     |  P0   | NEW: name `clean / run --fresh / rollback / vacuum-db / reconcile` as one taxonomy in CLI + UI |
| 17 | Puzzle-ID rollback audit           | ☑      |  P0   | Dead UI removed (2026-05-07): CLI `--puzzle-id` stripped, dashboard contract slimmed to `run_id`-only |
| 5  | Tag/Level inspector (read-only)    | ☐      |  P1   | Surfaces taxonomy that's invisible today |
| 6  | Adapter detail page                | ☐      |  P1   | Drill-in from existing adapters table. Includes per-source ingest-DB management |
| 7  | Adapter configuration management   | ☐      |  P1   | NEW: scaffold / clone / bulk-bootstrap sources.json + pipeline.json |
| 8  | Daily Challenge management         | ☐      |  P2   | Whole feature is invisible today. Includes daily status surface (rolling-window health + gap detection) |
| 9  | Run diff / compare                 | ☐      |  P2   | "what did run X do differently" |
| 10 | Puzzle Detail page                 | ☐      |  P2   | Headline feature; depends on 4, 5, 9 |
| 11 | Tag/Level mutation (rename, merge) | ☐      |  P3   | After read-only inspector lands |
| 12 | Adapter scaffold (new adapter src) | ☐      |  P3   | Rare; only after #7 sticks |

**Phases**:
- **P0** = quick wins, foundational, ship in the next sprint
- **P1** = medium-effort, build on P0
- **P2** = headline features, take a slice each
- **P3** = nice-to-have, defer until P0–P2 are done

**Status legend**: ☐ not started · ◐ in progress · ☑ done (link commit)

---

## Theme 0 — Operations / Logs UI Polish (P0)

**User pain (verbatim)**: "The maintenance page or whatever logs page is a
messy UI. If you take a screenshot of it you will understand that."

**Jobs covered**: any operator who opens the dashboard.

### Likely visual bugs to triage (verify with screenshots)
- Operations page: card grid wraps oddly at narrow widths; the new
  rose-fenced "Destructive" section may dominate visually because of the
  inset shadow + border-color combo.
- Logs page: stage-file list aside is fixed width, eats horizontal space at
  small viewports; sub-tab strip may not align with its underline cleanly
  in light theme.
- Both pages: padding inconsistent vs Library/Pipeline; section headers
  use different size/weight conventions.

### Acceptance criteria
- [ ] Capture screenshots of Operations + Logs at 1280×800 and 1920×1080
      in both light and dark themes; archive in `tools/yengo_dashboard/PLAN.md`
      (or a `screenshots/` folder).
- [x] Pin section header typography (size, weight, color, casing) in
      `styles.css` and reuse across all five views — `viewHeader()` helper
      + `.view-header` / `.view-header-title` / `.view-header-sub` classes.
- [ ] Operations: equal-height cards, consistent gap, destructive section
      visibility tested with operator (no false alarms, no missed signals).
- [x] Logs: stage-file list is collapsible / responsive; tail viewer fills
      remaining width — `.logs-stage-grid` flexes 13–18rem aside across
      breakpoints, stacks below 768px.
- [ ] Light-theme regression sweep: every view checked.
- [x] Add a single test that pins "all five views use the same `.view-header`
      pattern" so future drift is caught — `test_view_header_used_by_every_render_function`
      asserts every `render*` site emits `viewHeader("<title>", ...)`.

### Backend changes
None — pure frontend / CSS.

---

## Theme 1 — Dry-run Preview as First-Class (P0) ◐

**Status (2026-05-07)**: 1a + 1b shipped (rollback / vacuum-db). 1c (clean), 1d (preview endpoints), 1e (UI Preview button) pending.

**Jobs covered**: "Preview before I break something."

### Backend additions
- ☐ `clean --dry-run --json` → `{would_delete: [{path, bytes}, ...], total_files, total_bytes}`.
- ☑ `rollback --dry-run --json` → `RollbackPreview` (`backend/puzzle_manager/models/previews.py`).
- ☑ `vacuum-db --dry-run --json` → `VacuumDbPreview` (same module).
- All three keep stdout structured-only when `--json` is passed (no chatter).

### UI surfaces
- Each Operations card grows a **"Preview"** button beside "Run".
- Preview opens a modal with the structured impact summary (counts, sample
  IDs, byte estimates).
- After preview, the modal offers "Run for real" (which re-issues the same
  request without `--dry-run`).

### Acceptance criteria
- [ ] CLI: `--dry-run --json` returns a stable Pydantic-validated shape for
      all three subcommands; backend tests pin schema.
- [ ] Dashboard: each destructive card has a Preview button; the modal
      shows counts AND a sample (max 20 IDs).
- [ ] Real-fixture test: preview → run real, the affected set matches.

### Dependencies
None.

---

## Theme 2 — Failure Digest on History (P0)

**Jobs covered**: "Why did this run fail / skip puzzles?"

### Backend additions
- `status --failures-summary --last N --json` → grouped:
  `[{error_type, count, sample_message, sample_puzzle_ids[], affected_runs[]}, ...]`.
- Reads existing `RunState.failures[]` across the last N run-state files;
  no new persistence.

### UI surfaces
- Pipeline tab gains a **"Top failure modes (last 10 runs)"** card above
  History.
- Each row click → opens a Logs view filtered to that error pattern (uses
  Theme 4's `logs grep`).
- History row: failure-count badge per run; click → drilldown.

### Acceptance criteria
- [ ] Backend test with seeded run-state files asserts grouping logic.
- [ ] Dashboard test pins the new card renders even on empty fixture.
- [ ] Click flow from card → Logs view works under SPA routing.

### Dependencies
- Visually depends on Theme 0 (consistent card styling).
- Linked drilldown depends on Theme 4 (`logs grep`).

---

## Theme 3 — Disk / Runtime Footprint (P0)

**Jobs covered**: *"Why is `.pm-runtime/` 2 GB?"*

### Backend additions
- `runtime-info --json` →
  ```json
  {
    "logs_bytes": 0,
    "state_bytes": 0,
    "staging_bytes": 0,
    "ingest_dbs_bytes": 0,
    "by_source": {"sanderland": 0, ...},
    "publish_logs_bytes": 0,
    "captured_at": "ISO-8601"
  }
  ```

### UI surfaces
- System dialog (header chip click) gains a **"Footprint"** tab.
- Operations / Clean card shows a per-target byte estimate next to each
  target option (pulled from `runtime-info`).

### Acceptance criteria
- [ ] CLI test: seeds tmp `.pm-runtime/` with known sizes, asserts response.
- [ ] Dashboard test: chip dialog renders the footprint tab.

---

## Theme 4 — Logs Grep Across Files (P0)

**Jobs covered**: "Find a needle across 30 days of stage logs."

### Backend additions
- `logs grep PATTERN [--stage NAME] [--from DATE] [--to DATE] [--limit N] --json` →
  `[{file, line_no, ts, stream, text, context_before[2], context_after[2]}, ...]`.
- Rejects regex with anchors that scan unbounded; `--limit` defaults to 200.

### UI surfaces
- Logs / Stage tab gets a search box at the top.
- Results table: file • line • timestamp • snippet • [Open] (jumps to that
  file at that offset in the existing tail viewer).

### Acceptance criteria
- [ ] CLI test seeds multi-file logs and verifies grep + ordering.
- [ ] Dashboard test pins the new search field and result row click.

---

## Theme 13 — Unified Activity Surface (P0) — NEW

**User pain (verbatim, paraphrased)**: today the operator has to mentally
fuse five disjoint surfaces — pipeline runs, maintenance ops, publish-log
entries, audit trail, and config-lock events — to answer "what happened
in the last hour?".

**Jobs covered**: "Show me one timeline of everything that touched the
corpus, regardless of which subsystem produced the event."

### Backend additions

- `activity --from TS --to TS [--kinds run,maintenance,publish,audit,lock] --limit N --json` →
  ```json
  [
    {"ts": "ISO-8601", "kind": "run|maintenance|publish|audit|lock",
     "actor": "cli|github-actions|dashboard",
     "subject_id": "run_id|puzzle_id|source_id|...",
     "summary": "human one-liner",
     "details_ref": {"file": "...", "line": N}}
  ]
  ```
- Event sources to merge: `state/runs/*.json` (start/end/failure events),
  `publish-log` daily files, audit-trail (rollback log), config-lock acquire/release,
  maintenance subcommand exit records.
- Pure read-side: no new persistence. Every event already exists on disk —
  the CLI just unions and sorts by `ts`.

### UI surfaces

- New nav item **"Activity"** (top-level, between Pipeline and Operations).
- Single timeline view: filter chips per kind, date-range picker, infinite
  scroll. Each row click → deep-link to the canonical view (run → Pipeline,
  publish → Logs/Audit, lock → Operations).
- Compact mode for the System dialog: "last 10 events" mini-feed.

### Acceptance criteria

- [ ] CLI test seeds one of each event kind, asserts merged ordering + filtering.
- [ ] Dashboard test pins the new nav item + filter chip behavior.
- [ ] Empty-state UX (no events in range) tested.

### Dependencies

- Builds on Theme 4 (logs grep) for the "open underlying log line" affordance.
- Builds on Theme 2's failure digest (failures appear here as `kind=run`
  with severity).

---

## Theme 14 — Inventory Health Surface (P0) — NEW

**User pain (verbatim, paraphrased)**: the dashboard shows an inventory
*count* but hides the operator-grade actions the CLI already supports
(`--rebuild`, `--reconcile`, `--check`, `--fix`). Today an inventory drift
is invisible until a downstream stage breaks.

**Jobs covered**: "Tell me whether the inventory is healthy and let me
heal it without dropping to a terminal."

### Backend additions

- `inventory check --json` (already wired internally; expose as a top-level
  read-only call) →
  ```json
  {
    "ok": false,
    "issues": [
      {"kind": "missing_file", "puzzle_id": "...", "expected_path": "..."},
      {"kind": "orphan_file",  "path": "...", "size_bytes": N},
      {"kind": "hash_mismatch","puzzle_id": "...", "stored": "...", "actual": "..."}
    ],
    "summary": {"missing": N, "orphan": N, "hash_mismatch": N}
  }
  ```
- `inventory rebuild --dry-run --json`, `inventory reconcile --dry-run --json`,
  `inventory fix --dry-run --json` — all three return the same impact-summary
  shape as Theme 1's preview contract.
- All three are write operations behind `config-lock`; without `--dry-run`
  they perform the action and return a result delta.

### UI surfaces

- Library nav grows an **"Inventory health"** sub-section above the existing
  count tile.
- Health badge: green = `ok: true`, amber = orphans only, rose = missing
  or hash-mismatch.
- Per-issue table with [Preview Fix] → [Apply Fix] flow (re-uses Theme 1's
  modal pattern).
- Footer link to the full audit-trail entry created by each healing action.

### Acceptance criteria

- [ ] CLI test seeds a corpus with one missing + one orphan + one hash
      mismatch; check reports all three; reconcile dry-run lists exact
      affected files; reconcile real heals them.
- [ ] Dashboard test pins the new sub-section + badge state transitions.
- [ ] Healing actions appear in the unified activity surface (Theme 13).

### Dependencies

- Theme 1 (preview pattern reused).
- Theme 13 (healing events flow into the timeline).

---

## Theme 16 — Reset Blast-Radius as a Backend Concept (P0) — NEW

**User pain (verbatim)**: "Reset is not one operation. Clean, run --fresh,
rollback, vacuum-db --rebuild, and inventory reconcile each touch different
layers, and the system does not yet expose that blast radius as a
first-class operator concept."

Slice 6 grouped destructive *cards* visually, but the underlying CLI does
not name the taxonomy — operators have to learn it by reading source.
This theme makes the taxonomy explicit in the CLI and machine-readable,
so the UI can present consistent guardrails everywhere a destructive
action appears (not just on the Operations page).

### Backend additions

- `ops catalog --json` → enumerates every mutating subcommand with its
  blast-radius classification:
  ```json
  [
    {"op": "clean",            "scope": ["staging"],                       "reversible": true,  "preview_supported": true},
    {"op": "run --fresh",      "scope": ["staging", "ingest_state"],       "reversible": false, "preview_supported": false},
    {"op": "rollback",         "scope": ["published_corpus", "search_db"], "reversible": "by-audit-trail", "preview_supported": true},
    {"op": "vacuum-db",        "scope": ["search_db"],                     "reversible": true,  "preview_supported": true},
    {"op": "inventory fix",    "scope": ["inventory_snapshot", "files"],   "reversible": false, "preview_supported": true}
  ]
  ```
- The catalog is the single source of truth for: which buttons need a
  Preview step, which need a typed-confirm, which group/section they
  belong to in the UI. The frontend MUST consume `ops catalog` rather
  than re-encode the classification.

### UI surfaces

- Operations page is regenerated from `ops catalog` instead of hard-coded
  cards. Slice 6's three sections (diagnostics / maintenance / destructive)
  derive from `scope` + `reversible`.
- Every destructive button anywhere in the app (not just Operations)
  consults the catalog to decide whether to require a typed-verb confirm.
- Tooltip on each button shows `scope` + `reversible` honestly.

### Acceptance criteria

- [ ] CLI: `ops catalog --json` is Pydantic-validated; every mutating
      subcommand registered. Adding a new mutating command without
      registering it fails a backend test.
- [ ] Dashboard: Operations page rendering is data-driven from the catalog
      (a backend-only edit can re-classify a button's blast-radius).
- [ ] Test: a button declared `reversible: false` and `preview_supported: false`
      always presents a typed-confirm dialog regardless of which view hosts it.

### Dependencies

- Slice 6 (visual fence) → this theme generalizes that pattern.
- Theme 1 (dry-run preview) → buttons with `preview_supported: true` get
  the Preview step automatically.

---

## Theme 17 — Puzzle-ID Rollback Audit (P0) — NEW

The dashboard exposes a "rollback by puzzle-ID" affordance, but the
backend's primary rollback path is by `run_id`. We need to confirm
which (if any) puzzle-ID-targeted rollback API actually exists end-to-end.

### Audit findings (2026-05-07)

**Status: dead UI confirmed.** Evidence:

- `backend/puzzle_manager/cli.py:709` — argparse accepts `--puzzle-id ID...`
  inside a `required=True` mutually-exclusive group with `--run-id`. Help
  text and module-level docstring both advertise the flag.
- `backend/puzzle_manager/cli.py:1853-1855` — `cmd_rollback()` immediately
  rejects anything without `--run-id`:

  ```python
  if not args.run_id:
      print("Error: --run-id is required for rollback")
      return 1
  ```

  The implementation has no branch consuming `args.puzzle_id`.
- `tools/yengo_dashboard/server/routes_maintenance.py:48-68` — the dashboard
  happily builds `--puzzle-id ID1 ID2…` argv when the operator fills in
  the textarea. The CLI then rejects it with the cryptic `--run-id is
  required` error, surfacing to the SSE log only.
- `RollbackManager` has no public `rollback_by_puzzle_ids()` method;
  every rollback path joins through `rollback_by_run()`.

### Decision required

Two paths:

- **(a) Implement properly** — add `RollbackManager.rollback_by_puzzle_ids()`,
  wire it through `cmd_rollback`, audit the publish-log writer to ensure
  per-puzzle rollback emits the right event rows. Substantial — touches
  manager, CLI, audit-trail, tests.
- **(b) Remove the dead surface** — strip `--puzzle-id` from the rollback
  argparser, drop the textarea from the dashboard form, update the help
  text + docs. Small, clean, restores honesty.

**Recommendation: (b)** — there is no operator demand for puzzle-ID
rollback today, and the misleading affordance has been silently failing
for an unknown duration. Fix the lie now; revisit (a) under a real
feature request.

### Acceptance criteria
- [ ] One of (a) or (b) executed.
- [ ] `tools/yengo_dashboard/server/routes_maintenance.py` no longer
      builds the broken `--puzzle-id` argv path (or builds it correctly
      against a working backend).
- [ ] Outcome documented in `docs/architecture/backend/inventory-operations.md`.
- [ ] Real-fixture test: if (a), rollback by puzzle-id reduces published
      corpus by exactly the requested set; if (b), no `--puzzle-id`
      reachable code path remains.

### Dependencies

- None to start. Resolution should land before Theme 1 (Preview button)
  ships for rollback, otherwise we'd be wiring a Preview button onto a
  dead form.

---

## Theme 5 — Tag / Level Inspector (read-only) (P1)

**Jobs covered**: "Tune the taxonomy."

### Backend additions
- `tags list --with-usage --json` → `[{tag, usage_count, aliases[], first_seen_run, last_seen_run}, ...]`.
- `levels list --with-usage --json` → same shape.
- Reads from `inventory.json` snapshot + `config/tags.json` + `config/puzzle-levels.json`.

### UI surfaces
- Library nav grows a **"Taxonomy"** sub-section: two tables (Tags / Levels)
  with usage counts and search box.
- Click a tag → cross-link to publish-log search filtered to puzzles with
  that tag (via Theme 10 once landed; for now, link to a stub).

### Acceptance criteria
- [ ] CLI tests against seeded inventory + config.
- [ ] Dashboard test pins the new sub-section.

---

## Theme 6 — Adapter Detail Page (P1)

**Jobs covered**: "Per-source last-run, error trend, sample failures."

### Backend additions
- `source-status SOURCE_ID --details --json` →
  ```json
  {
    "id": "sanderland",
    "summary": {"ingested": N, "skipped": N, "failed": N},
    "recent_runs": [{run_id, started_at, ingested, failed}, ...10 max],
    "recent_failures": [{puzzle_id, error_type, message, ts}, ...10 max],
    "config": {... echo of sources.json entry ...}
  }
  ```

### UI surfaces
- Click an adapter row → SPA route `/adapters/{id}` (clean-path routing
  already supports this; just add to `parsePath`).
- Detail view: summary tile, recent-runs sparkline, recent-failures table,
  a "Run this adapter only" button (passes `--source ID`).

### Acceptance criteria
- [ ] Backend route test against seeded fixture.
- [ ] Dashboard route test asserts `/adapters/{id}` resolves.

### Theme 6b — Per-source ingest-DB management (folded into Theme 6)

Every source carries its own `.yengo-ingest.sqlite` recording which inputs
have already been seen. Today there's no UI for this; operators have to
edit / delete the file by hand to re-ingest a source.

**Backend additions**:

- `source-ingest-state SOURCE_ID --json` →
  `{path, rows, last_modified, failed_rows: [...], status: "healthy|stale|empty"}`.
- `source-ingest-state SOURCE_ID --reset --dry-run --json` →
  `{would_delete_path, row_count_lost: N, requires_full_reingest: true}`.
- `source-ingest-state SOURCE_ID --reset` → atomically removes the per-source
  ingest DB after a typed-confirm (or `--force`).

**UI surfaces**:

- Adapter detail view (Theme 6) gains an "Ingest state" tile showing
  status badge + row count + last-modified.
- "Reset ingest state" button uses the Theme 1 preview pattern. Surfaces
  failed rows from `failed_rows` so the operator sees what they're losing.

**Acceptance**:
- [ ] Tests: seed a `.yengo-ingest.sqlite` with both successful + failed rows;
      assert query returns counts; assert reset --dry-run never writes;
      assert reset removes the file atomically.
- [ ] Dashboard test pins the reset flow and the typed-confirm requirement.

---

## Theme 7 — Adapter Configuration Management (P1) — NEW

**User pain (verbatim)**: "There should be a new adapter configuration also
possible, meaning we pass on the information, the new adapter goes and sits
into [sources.json], or copy an existing adapter into a new adapter, or
bootstrap it once for all adapters."

**Jobs covered**: "I want to add a new source / clone an existing one /
re-validate every adapter at once."

### Backend additions

These are config mutators. They MUST validate against
`config/sources.schema.json` before writing, MUST go through
`config-lock` (existing single-writer guard), and MUST atomically replace
the file (write-tmp + os.replace).

- `adapter-config list --json` → returns `{active_adapter, sources: [...]}`
  (read-only echo of `sources.json`, but routed through the CLI so the
  cockpit never opens config files directly).
- `adapter-config show ID --json` → `{...one source entry...}` plus
  `{adapter_kind, schema_for_kind, available_kinds}` so the UI can render
  a schema-driven form.
- `adapter-config add --id ID --name NAME --adapter KIND --config-json '...'` →
  appends to `sources.json` after schema validation.
- `adapter-config clone SRC_ID --new-id NEW_ID --new-name NAME [--config-overrides KEY=VAL ...]` →
  copy an existing entry as the starting point.
- `adapter-config update ID --set KEY=VAL ...` → patch a single source's
  config block (validated).
- `adapter-config remove ID` → delete (refuses if it's the active adapter
  unless `--force`, refuses if any pending run references it).
- `adapter-config validate-all --json` → run schema validation on every
  source AND verify the per-adapter `config.path` exists / is reachable.
  Returns `[{id, ok, errors[]}, ...]`.
- `adapter-config bootstrap --from-folder PATH [--adapter local] [--id-prefix STR]` →
  scan a folder, propose one source entry per immediate subdirectory, with
  `--dry-run` returning the proposal as JSON (does NOT write).
- `pipeline-config show --json`, `pipeline-config set KEY=VAL` (similar
  surface for `pipeline.json`; same lock + atomic-write rules).

### UI surfaces

- New nav item under Operations called **"Adapters"** (or sub-tab in
  Library). Three panes:
  1. **List** — table of every source, columns: id · name · adapter ·
     active? · path-exists? · puzzle count (from inventory). Each row
     has [Edit] [Clone] [Disable] [Delete].
  2. **Add / Edit form** — schema-driven (consume `available_kinds` and
     `schema_for_kind` from `adapter-config show`). The form renders a
     different field set per adapter kind (`local` shows path picker /
     include / exclude folder lists, `sanderland` shows API base + auth, etc.).
  3. **Bootstrap wizard** — point at a folder, preview proposed entries
     in a table, [Apply selected] writes them in one batch.
- Pipeline-config section: read-only at first (show current values),
  edit-key dialog gated by a confirmation.

### Acceptance criteria
- [ ] All `adapter-config` subcommands return validated JSON + atomic-write
      to disk. Schema-violation returns rc != 0 + error list on stderr.
- [ ] Backend tests: add → validate-all sees it; clone preserves config
      block; remove refuses when active; bootstrap dry-run never writes.
- [ ] Dashboard tests pin: schema-driven form for `local` adapter; clone
      flow; bootstrap preview → apply.
- [ ] All mutators flow through `config-lock`; concurrent edits return 409.
- [ ] `sources.schema.json` is the single source of truth — UI never
      re-encodes the schema, always fetches it via the CLI.

### Dependencies
- Visually depends on Theme 0 (consistent form styling).
- Re-uses confirmDialog + lock-aware UX from existing Operations cards.

---

## Theme 8 — Daily Challenge Management (P2)

**Jobs covered**: the entire daily-challenge surface, currently invisible.

### Backend additions
- `daily list [--from --to] --json` → `[{date, technique, attrs, puzzle_count, generated_at}, ...]`.
- `daily status --json` → rolling-window health:
  ```json
  {
    "window": {"from": "2026-04-07", "to": "2026-05-07"},
    "expected_dates": 30,
    "generated_dates": 28,
    "missing_dates": ["2026-04-19", "2026-04-26"],
    "stale_dates": [{"date": "2026-04-12", "regenerated_at": "...", "age_days": 25}],
    "last_regenerated_at": "ISO-8601",
    "last_workflow_run": {"id": "...", "status": "success|failed|running"},
    "next_scheduled_at": "ISO-8601 (from cron)"
  }
  ```
  Reads existing `daily_schedule` + `daily_puzzles` tables and the
  `daily-generation.yml` workflow last-run via gh CLI (best-effort).
- `daily preview --date DATE --json` → what *would* be generated, no write.
- `daily cancel --date DATE` / `daily cancel --from --to` → removes from
  `daily_schedule` + `daily_puzzles`.
- `daily regenerate --date DATE --force` (already exists; pin JSON shape).

### UI surfaces
- New nav item **"Daily"** between Pipeline and Operations.
- **Status header**: green/amber/rose health badge driven by `daily status`,
  showing missing/stale dates count + "next scheduled at" + "last regenerated"
  + last workflow run status (links to GitHub Actions run).
- Month-view calendar; click date → puzzles for that day in a side panel.
  Missing dates are visually flagged on the calendar.
- "Generate next 30 days" wraps `daily --from --to`; preview required first.
- "Backfill missing" action — surfaces the gap list from `daily status` and
  offers a one-click preview-then-apply.

### Acceptance criteria
- [ ] Calendar renders from `/api/daily/list`.
- [ ] Status badge derives correctly from seeded `daily_schedule` rows
      with deliberate gaps.
- [ ] Preview → commit flow with the same dialog pattern as Theme 1.
- [ ] Cancel requires typed confirmation (destructive).
- [ ] Backfill flow respects the preview-then-apply pattern.

---

## Theme 9 — Run Diff / Compare (P2)

**Jobs covered**: "What did run X do differently from run Y?"

### Backend additions
- `runs diff RUN_A RUN_B --json` →
  `{added_puzzles[], removed_puzzles[], changed_puzzles[{id, fields_changed[]}], stats_diff{...}}`.

### UI surfaces
- History page rows gain checkboxes; selecting two enables **"Compare"**
  in the page header.
- Diff view: three columns (added / removed / changed) with sample IDs
  and counts.

### Acceptance criteria
- [ ] CLI test against two seeded run-state JSONs.
- [ ] Dashboard test pins the checkbox + Compare flow.

---

## Theme 10 — Puzzle Detail Page (P2) — headline feature

**Jobs covered**: "Show me everything about puzzle YENGO-abc."

### Backend additions
- `puzzle-info ID --json` joins:
  - publish-log entries (search by puzzle_id),
  - current SGF on disk + parsed metadata,
  - rollback history,
  - daily-schedule appearances,
  - source / first-ingest run.

### UI surfaces
- Global search box in the top header (already has space).
- New SPA route `/puzzle/{id}` → tabs for Lineage · SGF preview · Audit ·
  Daily appearances. "Open in browser app" deep link, "Rollback" button
  (uses Theme 1 preview).

### Acceptance criteria
- [ ] CLI test joins seeded fixtures across all five sources.
- [ ] Dashboard test pins route resolution + global search submit.

### Dependencies
- Theme 4 (logs grep) for "show pipeline log lines mentioning this trace_id".
- Theme 5 (taxonomy) for clickable tag chips.
- Theme 9 (run diff) — optional, for "what changed about this puzzle in
  run X vs Y".

---

## Theme 11 — Tag / Level Mutation (P3)

Build only after Theme 5's read-only inspector ships and is in use.

### Backend additions
- `tags rename OLD NEW --dry-run` (re-tags every puzzle).
- `tags merge A B --into C --dry-run`.
- `levels rename` (rare).

### UI surfaces
- Inline rename / merge actions on the Taxonomy tables, behind a
  typed-verb confirmation.

---

## Theme 12 — Adapter Scaffold (P3)

After Theme 7 lands and we know what shape new adapters take.

### Backend additions
- `adapter scaffold --kind local --id NEW_ID` → generates
  `backend/puzzle_manager/adapters/NEW_ID/{__init__.py, adapter.py}`
  from a template + adds a stub entry to `sources.json`.

### UI surfaces
- Bootstrap wizard (Theme 7) gains a "Generate adapter code" checkbox
  for kinds that don't already exist.

---

## Cross-cutting work

Track these alongside the themes — they don't deserve their own slice
but every theme touches them:

- [ ] **AGENTS.md update discipline** — every new endpoint must add a row
      to the Endpoints table in `tools/yengo_dashboard/AGENTS.md` in the
      same commit.
- [ ] **Schema discipline** — every new `--json` flag returns a
      Pydantic-validated shape; the cockpit's `models.py` mirrors it.
- [ ] **Lock discipline** — every config-mutating CLI flows through
      `config-lock`; the cockpit surfaces 409 cleanly.
- [ ] **Ops-catalog discipline** (Theme 16) — every new mutating CLI
      command MUST register itself in `ops catalog` with explicit
      `scope` + `reversible` + `preview_supported`. A backend test fails
      if a mutating subcommand is unregistered.
- [ ] **Activity-event discipline** (Theme 13) — every new mutating CLI
      command MUST emit an event row consumable by the activity surface.
- [ ] **Light-theme parity** — every new UI element has a
      `body[data-theme="light"]` override checked at landing.
- [ ] **Real-fixture tests** — no mocks; tmp filesystem fixtures only.

---

## How to use this doc

1. Pick the next ☐ theme by phase order.
2. Open a planning sub-doc if the theme is large enough (Themes 7, 8, 10 are);
   otherwise plan in-conversation and ship.
3. Follow one-slice-per-commit. Mark the row ☑ with the commit SHA when done.
4. When all P0 themes are ☑, re-evaluate priorities — Theme 0 + 1 may
   reshape what feels urgent in P1.

Goal: every row ☑ before declaring "dashboard v2 complete".
