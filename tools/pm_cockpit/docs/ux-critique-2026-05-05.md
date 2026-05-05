# pm_cockpit — UX critique 2026-05-05

> Reviewer: Mika Chen (DevTools-UX agent persona).
> Source files reviewed: `web/{index.html,app.js,styles.css}`, `colors.md`,
> `docs/architecture/tools/pm_cockpit.md`, `AGENTS.md`.
> Status: critique adopted as the basis for the Phase 4 UI/UX refinement.

This document is the *raw* critique as delivered. The implementation may
deviate from individual recommendations where ground-truth code already does
the right thing (noted inline below). Track refinement progress against
this document; archive once Phase 4 closes.

---

## 1. Top 5 issues, ranked by impact

### 1. The Live Run log is a flat `<pre>`-style dump

**Where**: `index.html` `#run-log`; `app.js` `logPanelAppend()` and the SSE
handler in `attachStream()`.

**What's wrong**: every line is the same monospace gray. INFO, WARN, ERROR,
stage transitions and stack traces look identical. No level filter, no
search, no row cap (DOM grows unbounded as a single text node).

**Operator impact**: in 50K-line streams, finding a single WARN requires
Cmd+F or luck.

**Note vs current code**: auto-scroll-respect is already correct
(`logPanelAppend` lines 195–198 only scrolls when `nearBottom`). The
critique's "single most disrespectful behavior" point applies to most log
viewers but not this one. The rest of the recommendation (level parsing,
filter chips, in-DOM cap, structured columns) stands.

**Fix sketch**:

```html
<div class="grid grid-cols-[6rem_4rem_8rem_1fr] gap-2 px-2 py-0.5 text-xs font-mono
            border-l-2 border-transparent
            data-[level=warn]:border-amber-400
            data-[level=error]:border-rose-400
            hover:bg-slate-800/40">
  <span class="text-slate-500 tabular-nums">14:02:11</span>
  <span class="text-amber-300">WARN</span>
  <span class="text-slate-400">analyze</span>
  <span class="text-slate-200">…</span>
</div>
```

Toolbar above: level chips, stream toggle, search, pin-bottom toggle, row
counter. Cap at ~5000 in-DOM rows; offer "download full log".

### 2. No global "run in flight" affordance outside Live Run

**Where**: header chips; `renderLockBadge()`. Lock-held is the only signal
that anything is going on.

**Operator impact**: an operator who switches to Maintenance can fire a
destructive button while a real run is mid-stage.

**Fix**: sticky alarm bar above the nav; `data-locked="true"` on `<body>`
gating destructive buttons via CSS.

### 3. Maintenance buttons are equally weighted

**Where**: `renderMaintenance()`.

**What's wrong**: clean, vacuum, rollback, force-release all look alike.
No grouping by blast radius. Confirmation is `alert()`/`confirm()`.

**Fix**: three labeled sections (Diagnostics / Maintenance / Destructive).
Native `<dialog>` confirmation requiring the operator to type the verb
(`vacuum`, `rollback`, `release`).

### 4. Header chips don't distinguish alarms from references

**Where**: `index.html` header; `renderHealth()`, `renderLockBadge()`.

**What's wrong**: schema, version, lock, health are visually equal pills.
Real alarms (lock held) are buried with reference data (version).

**Fix**: collapse health + version into a single "System" pill that opens
a popover; promote only true alarms into the sticky bar from #2.

### 5. History is a JSON-shaped list with zero aggregate insight

**Where**: `renderHistory()`.

**What's wrong**: ISO-8601 timestamps, no summary strip, no failure
highlight, no per-stage bar.

**Fix**: 3-card summary strip (last 24h ok%, last failure, throughput),
relative time via `Intl.RelativeTimeFormat`, failed rows get
`border-l-2 border-rose-400`, per-row 6-segment stage bar, date-range
chips.

---

## 2. Per-tab notes

### Overview
- Replace four metric cards with two rows: sparklines + "what's notable now".
- Move schema/version chips here from the header.
- `tabular-nums` on every numeric cell.
- Empty-state UX when `db_exists === false`.

### Adapters
- "Last run" column with relative time + status dot.
- Default sort: last-run-age desc (problems float up).
- Inline `Run` action pre-fills the form and switches tabs.
- Disabled adapters: `opacity-50 + disabled tag`, never omit.

### Live Run
- During a run, collapse the form to a sticky right rail; show a one-line
  summary header (`analyze · batch=500 · dry-run · 14m elapsed`).
- Rebuild log viewer per #1.
- Stage stepper above the log: 6 horizontal pills, current one pulses.
- Move "Force release lock" out of this tab into Maintenance/Destructive.

### Maintenance
- Three groups (see #3).
- Replace per-card `<pre>` with one shared activity log + inline last-result
  per card.
- Standardize dry-run pattern: every destructive action gets `[Preview] [Run]`.

### History
- Summary strip + per-row stage breakdown (#5).
- Click row → expand inline (`<details>`) to show last log tail + stage
  durations + "replay this config".
- Filter chips: `status: all | ok | failed`.
- Paginate at 50 rows.

---

## 3. Cross-cutting patterns

### Status pill (color + glyph + label)

```html
<span class="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5
             text-xs font-medium bg-emerald-500/10 text-emerald-300
             ring-1 ring-emerald-500/30">
  <svg class="h-3 w-3" aria-hidden="true">
    <circle cx="6" cy="6" r="3" fill="currentColor"/>
  </svg>
  Ready
</span>
```

Variants: `ok=emerald`, `info=sky`, `warn=amber`, `error=rose`,
`running=sky + animate-pulse`, `stale=slate-500`.

### Table density

`text-sm`, `tabular-nums` numeric cells, sticky header
`sticky top-0 bg-slate-950/90 backdrop-blur`, hover `hover:bg-slate-800/60`,
zebra `[&>tr:nth-child(even)]:bg-slate-900/40`. Hard cap 7 visible columns.

### Empty state — always present

```html
<div class="rounded-lg border border-dashed border-slate-700 p-8 text-center">
  <p class="text-sm text-slate-400">No runs in the last 24 hours.</p>
  <button class="mt-3 rounded-md bg-sky-500/10 px-3 py-1.5 text-sm
                 text-sky-300 ring-1 ring-sky-500/30">Start a run</button>
</div>
```

### Destructive action — segregated, confirmed

```html
<button data-destructive
        class="rounded-md bg-rose-500/10 px-3 py-1.5 text-sm text-rose-300
               ring-1 ring-rose-500/30 hover:bg-rose-500/20">
  Force release lock
</button>
```

Click opens `<dialog>` requiring the operator to type the verb.

### In-flight feedback

On click: disable button, swap label to `Running…` with inline spinner SVG,
post the result via a single `<div id="toast-region" role="status"
aria-live="polite" class="fixed bottom-4 right-4">`.

### Sticky alarm bar

One `<div id="alarm-bar">` above the nav. Conditions stack as bullets.
Maximum one bar. Color = highest severity present (rose > amber).

### Relative time everywhere

`Intl.RelativeTimeFormat` for display, real ISO in `title`. Single 30 s
master tick refreshes all `[data-relative-time]`.

---

## 4. Anti-patterns to remove

- Per-action `<pre>` blocks in Maintenance — one shared log instead.
- `confirm()` / `alert()` modals — replace with native `<dialog>`.
- Tab labels with identical weight when a run is active — fade non-active
  tabs during a run.
- Schema and version pills in the global header — they're reference data.
- ISO-8601 timestamps in tables.
- Multiple uncoordinated `setInterval` loops — one master tick.

---

## 5. Palette adjustments (incorporated into `colors.md`)

1. **Downgrade success intensity** — emerald should not match rose for
   alarm strength. Use `emerald-300` text on `emerald-500/10`, ring
   `emerald-500/30`.
2. **Add a `running` token distinct from `info`** — sky with `animate-pulse`
   ring; flat sky-300 reserved for static info.
3. **Add a `stale` token** — `slate-500` text + reduced opacity for
   stale-data signaling.
4. **Reserve rose strictly for failure/destructive intent** — never use
   for "stopped" or "skipped" (use slate / amber-300 muted).
5. **Standardize dividers at `slate-800`** — single low-contrast border
   token; modern ops dashboards (Linear, Vercel, Grafana) all read clean
   because of this.
