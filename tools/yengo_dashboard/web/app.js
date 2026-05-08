// yengo_dashboard — vanilla ES module entry/coordinator. No build step.
// Renders raw API payloads. Per principle #6 the dashboard never invents
// domain meaning; this script only transforms wire JSON into HTML.
//
// Cross-cutting helpers (DOM, HTTP, pills, toasts, dialogs, relative time,
// Lucide icon materialization) live in ui.js. The Guide tab lives in
// view-guide.js. Everything else (Overview, Adapters, Live Run, History,
// Maintenance, Status strip, polling, click delegation, boot) is here.

import {
  $, $$,
  getJSON, postJSON,
  escapeHtml, errorBlock,
  PILL_VARIANTS, pill,
  relTime, tagRelTime, refreshRelTimes,
  toast, confirmDialog,
} from "./ui.js";
import { renderGuide, loadGuideDoc } from "./view-guide.js";

// ---------- System state (composed from /api/health + /api/lock + active run) ----------

const SYSTEM = {
  health: { ok: false, version: "?", uptime_s: 0, lastFetch: null },
  lock:   { locked: false, holderPid: null, lastFetch: null },
  active: null,           // RunSnapshot | null
  unreachable: false,
};

async function refreshHealth() {
  try {
    const h = await getJSON("/api/health");
    SYSTEM.health = { ...h, lastFetch: Date.now() };
    SYSTEM.unreachable = false;
  } catch {
    SYSTEM.health.ok = false;
    SYSTEM.unreachable = true;
  }
}

async function refreshLock() {
  try {
    const data = await getJSON("/api/lock");
    SYSTEM.lock = {
      locked: data?.raw?.locked === true,
      holderPid: data?.raw?.holder_pid ?? null,
      lastFetch: Date.now(),
    };
  } catch {
    SYSTEM.lock = { locked: false, holderPid: null, lastFetch: null };
  }
}

async function refreshActive() {
  try {
    const data = await getJSON("/api/run/active");
    SYSTEM.active = data.active;
  } catch {
    SYSTEM.active = null;
  }
}

function paintSystemDialog() {
  const dl = $("#system-readings");
  const rows = [
    ["Version",   `v${SYSTEM.health.version}`],
    ["Uptime",    `${SYSTEM.health.uptime_s.toFixed(1)} s`],
    ["Lock",      SYSTEM.lock.locked ? `held (pid ${SYSTEM.lock.holderPid ?? "?"})` : "free"],
    ["Active run", SYSTEM.active ? `${SYSTEM.active.handle} · ${SYSTEM.active.status}` : "none"],
  ];
  dl.innerHTML = rows.map(([k, v]) => `
    <dt class="text-slate-500 text-xs uppercase tracking-wider self-center">${escapeHtml(k)}</dt>
    <dd class="font-mono text-slate-200">${escapeHtml(v)}</dd>
  `).join("");
  const ages = [SYSTEM.health.lastFetch, SYSTEM.lock.lastFetch].filter(Boolean);
  const newest = ages.length ? Math.max(...ages) : null;
  $("#system-refreshed").textContent = newest
    ? `Last refreshed ${Math.round((Date.now() - newest) / 1000)}s ago`
    : "Never refreshed.";
  _loadFootprint();
}

// ---------- Theme 3b: runtime footprint ----------
//
// `runtime-info` is a subprocess (~300-600ms) so we cache the most recent
// payload and re-render dialogs/decorations from cache. Refetch on demand
// (system dialog open, Clean target focus) — never on the master tick.

const FOOTPRINT = { payload: null, fetchedAt: 0, inflight: null };
const FOOTPRINT_TTL_MS = 10000;

function fmtBytes(n) {
  if (n == null || !Number.isFinite(n)) return "–";
  let v = Number(n);
  for (const u of ["B", "KB", "MB", "GB", "TB"]) {
    if (v < 1024 || u === "TB") {
      return u === "B" ? `${v.toLocaleString()} B` : `${v.toFixed(1)} ${u}`;
    }
    v /= 1024;
  }
  return `${v} B`;
}

async function refreshFootprint(force = false) {
  const now = Date.now();
  if (!force && FOOTPRINT.payload && (now - FOOTPRINT.fetchedAt) < FOOTPRINT_TTL_MS) {
    return FOOTPRINT.payload;
  }
  if (FOOTPRINT.inflight) return FOOTPRINT.inflight;
  FOOTPRINT.inflight = (async () => {
    try {
      const data = await getJSON("/api/runtime-info");
      FOOTPRINT.payload = data?.raw ?? null;
      FOOTPRINT.fetchedAt = Date.now();
      return FOOTPRINT.payload;
    } catch {
      return null;
    } finally {
      FOOTPRINT.inflight = null;
    }
  })();
  return FOOTPRINT.inflight;
}

async function _loadFootprint() {
  const dl = $("#system-footprint");
  const meta = $("#system-footprint-meta");
  if (!dl) return;
  dl.innerHTML = `<dt class="text-slate-500 text-xs">…</dt><dd class="font-mono text-slate-500">loading</dd>`;
  if (meta) meta.textContent = "";
  const fp = await refreshFootprint();
  if (!fp) {
    dl.innerHTML = `<dt class="text-slate-500 text-xs">error</dt><dd class="font-mono text-slate-500">runtime-info unavailable</dd>`;
    return;
  }
  const rows = [
    ["logs",         fmtBytes(fp.logs_bytes)],
    ["state",        fmtBytes(fp.state_bytes)],
    ["staging",      fmtBytes(fp.staging_bytes)],
    ["raw",          fmtBytes(fp.raw_bytes)],
    ["ingest-dbs",   fmtBytes(fp.ingest_dbs_bytes)],
    ["publish-logs", fmtBytes(fp.publish_logs_bytes)],
  ];
  dl.innerHTML = rows.map(([k, v]) => `
    <dt class="text-slate-500 text-xs uppercase tracking-wider self-center">${escapeHtml(k)}</dt>
    <dd class="font-mono text-slate-200">${escapeHtml(v)}</dd>
  `).join("");
  if (Object.keys(fp.by_source || {}).length) {
    const srcRows = Object.entries(fp.by_source).sort()
      .map(([sid, b]) => `
        <dt class="text-slate-500 text-xs pl-3 self-center">${escapeHtml(sid)}</dt>
        <dd class="font-mono text-slate-300 text-xs">${escapeHtml(fmtBytes(b))}</dd>
      `).join("");
    dl.insertAdjacentHTML("beforeend", srcRows);
  }
  if (meta) meta.textContent = `captured ${fp.captured_at}`;
}

// Theme 3b: decorate Clean's target dropdown with per-target byte estimates
// (e.g. "staging — 12.3 MB"). Falls back gracefully when runtime-info fails.
const _CLEAN_TARGET_BYTE_KEYS = {
  staging:               "staging_bytes",
  state:                 "state_bytes",
  logs:                  "logs_bytes",
  "publish-logs":        "publish_logs_bytes",
  "puzzles-collection":  null,  // owned by yengo-puzzle-collections, not runtime-info
};

async function _decorateCleanTargets() {
  const sel = document.querySelector("#mc-target");
  if (!sel) return;
  const fp = await refreshFootprint();
  if (!fp) return;
  for (const opt of sel.options) {
    const key = _CLEAN_TARGET_BYTE_KEYS[opt.value];
    if (!key) continue;
    const bytes = fp[key];
    if (bytes == null) continue;
    opt.textContent = `${opt.value} — ${fmtBytes(bytes)}`;
  }
}

// ---------- Top header system chip (Slice 3) ----------
//
// Always-visible status surface. Severity is derived from the same SYSTEM
// state the bottom strip uses, so the two never disagree. Click delegates
// to the same system dialog the old bottom-left button opened.

function paintSystemChip() {
  const chip = $("#system-chip");
  if (!chip) return;
  const label = $("#system-chip-label");
  const meta  = $("#system-chip-meta");
  // W1.5 — the bottom status strip is the single source of truth for
  // status messaging. The top-right chip is demoted to a colored dot +
  // version so the two surfaces don't duplicate prose. Severity color
  // still flows through `data-sev` (theme tokens in styles.css).
  let sev = "ok";
  if (SYSTEM.unreachable) sev = "error";
  else if (SYSTEM.active && !isTerminal(SYSTEM.active.status)) sev = "running";
  else if (SYSTEM.lock.locked) sev = "warn";
  chip.dataset.sev = sev;
  if (label) {
    label.textContent = "";
    label.classList.add("hidden");
  }
  if (meta) {
    const v = SYSTEM.health.version || "?";
    meta.textContent = `v${v}`;
  }
}

function isTerminal(status) {
  return ["completed", "failed", "cancelled"].includes(status);
}

// True iff the lock is held *because* of the cockpit's own active run. We
// don't have a strict invariant here (the CLI owns lock semantics), but
// when both are true together it's overwhelmingly the same actor.
function isOurRun() {
  return Boolean(SYSTEM.active && !isTerminal(SYSTEM.active.status));
}

// ---------- Status strip (single source of escalation, bottom-pinned) ----------

function paintStatusStrip() {
  const bar = $("#status-strip");
  if (!bar) return;
  // Pick the single most-severe condition; the strip never stacks rows.
  let sev = "ok";
  let msg = "Pipeline idle";
  let action = "";
  let assertive = false;
  if (SYSTEM.unreachable) {
    sev = "error";
    msg = "Cockpit cannot reach the API. Live values are stale.";
    assertive = true;
  } else if (SYSTEM.active && !isTerminal(SYSTEM.active.status)) {
    const sub = SYSTEM.active.command?.[3] || "run";
    const shortHandle = String(SYSTEM.active.handle || "").slice(0, 8);
    sev = "running";
    msg = `${sub} · <span class="font-mono">${escapeHtml(shortHandle)}…</span> · `
        + `<span data-rel-time="${escapeHtml(SYSTEM.active.started_at)}">${relTime(SYSTEM.active.started_at)}</span>`;
    // The "Open Live Run" link only makes sense when we're NOT already on
    // the Pipeline tab (where the live run is visible). Re-clicking when
    // already there does nothing because the hash is already #pipeline; the
    // link would just look broken.
    const onPipeline = $$(".nav-item.active").some((b) => b.dataset.nav === "pipeline");
    if (!onPipeline) {
      action = `<a href="#pipeline" class="strip-action" data-action="open-run">Open Live Run</a>`;
    }
  } else if (SYSTEM.lock.locked) {
    sev = "warn";
    msg = `Config lock held by pid ${escapeHtml(String(SYSTEM.lock.holderPid ?? "?"))}.`;
    action = `<button type="button" data-action="release-lock" class="strip-action">Release…</button>`;
  }
  bar.dataset.sev = sev;
  // role swap: assertive only on the error frame, then back to polite.
  bar.setAttribute("role", assertive ? "alert" : "status");
  bar.setAttribute("aria-live", assertive ? "assertive" : "polite");
  bar.innerHTML = `
    <div class="strip-row">
      <span class="sev-dot"${sev === "ok" ? ' data-static="true"' : ""}></span>
      <span class="strip-msg">${msg}</span>
      ${action}
    </div>`;
  document.body.dataset.runActive = (SYSTEM.active && !isTerminal(SYSTEM.active.status)) ? "true" : "false";
}

// ---------- Master tick (adaptive polling) ----------
// Idle: exponential backoff 5s → 30s, doubling each tick when nothing changes.
// Active run: pinned to 3s while a non-terminal run exists (SSE owns real
// progress; this is just for body[data-run-active] flips and lock state).
// Window blur: paused entirely. Focus: immediate tick + resume.

const POLL_IDLE_MIN_MS = 5000;
const POLL_IDLE_MAX_MS = 30000;
const POLL_ACTIVE_MS   = 3000;

let _pollDelay = POLL_IDLE_MIN_MS;
let _pollTimer = null;
let _pollDigest = "";
let _pollPaused = false;

function _digestSystem() {
  const a = SYSTEM.active;
  return [
    SYSTEM.health.ok ? "1" : "0",
    SYSTEM.unreachable ? "1" : "0",
    SYSTEM.lock.locked ? "1" : "0",
    String(SYSTEM.lock.holderPid ?? ""),
    a ? `${a.handle}:${a.status}:${a.line_count ?? 0}` : "-",
  ].join("|");
}

function _scheduleNextTick() {
  if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
  if (_pollPaused) return;
  _pollTimer = setTimeout(masterTick, _pollDelay);
}

async function masterTick() {
  await Promise.all([refreshHealth(), refreshLock(), refreshActive()]);
  paintStatusStrip();
  paintSystemChip();
  refreshRelTimes();

  const digest = _digestSystem();
  const runActive = SYSTEM.active && !isTerminal(SYSTEM.active.status);
  if (runActive) {
    _pollDelay = POLL_ACTIVE_MS;
  } else if (digest !== _pollDigest) {
    _pollDelay = POLL_IDLE_MIN_MS;
  } else {
    _pollDelay = Math.min(_pollDelay * 2, POLL_IDLE_MAX_MS);
  }
  _pollDigest = digest;
  _scheduleNextTick();
}

// ---------- Overview ----------

// Config maps loaded once from /config-static/. The cockpit reads the same
// JSON the pipeline reads, so level_id 110 always means the same thing on
// both sides (no client-side translation table to drift).
let _levelMeta = null;        // { 110: {slug, name, description}, ... }
let _contentTypeMeta = null;  // { 1: {display_label, description}, ... }
async function loadConfigMaps() {
  if (_levelMeta && _contentTypeMeta) return;
  try {
    const [levels, ctypes] = await Promise.all([
      fetch("/config-static/puzzle-levels.json").then(r => r.ok ? r.json() : null),
      fetch("/config-static/content-types.json").then(r => r.ok ? r.json() : null),
    ]);
    _levelMeta = {};
    for (const lv of (levels?.levels || [])) {
      const range = lv.rankRange ? `${lv.rankRange.min}–${lv.rankRange.max}` : "";
      _levelMeta[lv.id] = {
        slug: lv.slug,
        name: lv.name,
        range,
        label: range ? `${lv.name} (${range})` : lv.name,
        description: lv.description,
      };
    }
    _contentTypeMeta = {};
    // Schema: {types: {"1": {name, display_label, description}, ...}}
    const typesObj = ctypes?.types || {};
    for (const [k, v] of Object.entries(typesObj)) {
      _contentTypeMeta[Number(k)] = {
        name: v.name,
        label: v.display_label || v.name || k,
        description: v.description || "",
      };
    }
  } catch {
    _levelMeta = _levelMeta || {};
    _contentTypeMeta = _contentTypeMeta || {};
  }
}

function statCard(label, value) {
  return `<div class="kvp rounded-lg bg-zinc-900/60 ring-1 ring-white/5 p-4
                       shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04),0_1px_2px_0_rgba(0,0,0,0.4)]">
    <dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd>
  </div>`;
}

async function renderOverview() {
  const root = $("#view-overview");
  root.innerHTML = `<div class="text-slate-400 text-sm">loading inventory…</div>`;
  try {
    // Inventory + adapters + integrity in parallel. Integrity is the slowest
    // (subprocess) but graceful-degrades to a "—" badge if it errors so the
    // rest of the view still renders.
    const [inv, adapters, integrity] = await Promise.all([
      getJSON("/api/inventory"),
      loadConfigMaps().then(() => getJSON("/api/adapters").catch(() => ({ sources: [] }))),
      getJSON("/api/inventory/check").catch(() => null),
    ]);
    const levels = Object.entries(inv.by_level_id).sort((a, b) => Number(a[0]) - Number(b[0]));
    const types = Object.entries(inv.by_content_type).sort((a, b) => Number(a[0]) - Number(b[0]));
    const cats = Object.entries(inv.by_collection_category || {}).sort((a, b) => b[1] - a[1]);
    const empty = inv.puzzles_total === 0;
    const dbVer = inv.db_version
      ? `<span class="text-slate-300 font-mono">${escapeHtml(inv.db_version)}</span>`
      : `<span class="text-slate-600 italic">unbuilt</span>`;
    const schemaPill = inv.schema_version != null
      ? `<span class="ml-2 pill ${PILL_VARIANTS.ok}"><span class="glyph"></span>schema v${inv.schema_version}</span>`
      : "";
    root.innerHTML = `
      ${viewHeader("Published Inventory")}
      <dl class="grid grid-cols-2 md:grid-cols-4 gap-3">
        ${statCard("Puzzles",       inv.puzzles_total.toLocaleString())}
        ${statCard("Collections",   inv.collections_total.toLocaleString())}
        ${statCard("Daily entries", inv.daily_schedule_total.toLocaleString())}
        ${statCard("DB present",    inv.db_exists ? "yes" : "no")}
      </dl>
      ${inv.snapshot_exists === false && inv.advice ? `
        <div class="mt-4 rounded-md ring-1 ring-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-200 flex items-center gap-2">
          <span class="font-semibold uppercase tracking-wider text-amber-300">Snapshot</span>
          <span>${escapeHtml(inv.advice)}</span>
        </div>` : ""}
      ${integrityBlock(integrity)}
      ${empty ? `
        <div class="mt-6 rounded-lg border border-dashed border-slate-700 p-8 text-center">
          <p class="text-sm text-slate-400">No published puzzles yet.</p>
          <a href="#run" class="mt-3 inline-block rounded-md bg-sky-500/10 px-3 py-1.5 text-sm text-sky-300 ring-1 ring-sky-500/30">Start a run</a>
        </div>` : `
        <div class="grid md:grid-cols-2 gap-6 mt-6">
          ${levelsTable(levels)}
          ${contentTypesTable(types)}
        </div>
        ${cats.length ? `
          <div class="mt-6">
            <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">Collections by category</h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-2">
              ${cats.map(([k, v]) => `
                <div class="rounded-md ring-1 ring-slate-800 bg-slate-900/60 px-3 py-2 flex items-center justify-between">
                  <span class="text-xs text-slate-400">${escapeHtml(k)}</span>
                  <span class="font-mono tabular-nums text-sm text-slate-200">${v.toLocaleString()}</span>
                </div>`).join("")}
            </div>
          </div>` : ""}
        ${sourcesMiniTable(adapters)}
      `}
      <div class="mt-6 flex items-center justify-between text-xs text-slate-500">
        <span class="font-mono">${escapeHtml(inv.db_path || "—")}</span>
        <span>db_version: ${dbVer}${schemaPill}</span>
      </div>
      <div id="taxonomy-section" class="mt-8">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Taxonomy</h3>
        <div class="text-xs text-slate-500">loading taxonomy…</div>
      </div>
      <div id="session-panel" class="mt-8" data-session-panel>
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Recent activity</h3>
        <div class="text-xs text-slate-500">loading recent runs…</div>
      </div>
    `;
    _wireInventoryActionButtons(root);
    _loadTaxonomySection().catch(() => {/* graceful — handled below */});
    _loadSessionPanel().catch(() => {/* graceful */});
  } catch (e) { root.innerHTML = errorBlock("/api/inventory", e); }
}

// Theme 5: lazy-load tag/level usage tables and render below the inventory.
async function _loadTaxonomySection() {
  const section = document.getElementById("taxonomy-section");
  if (!section) return;
  try {
    const [tagsResp, levelsResp] = await Promise.all([
      getJSON("/api/tags"),
      getJSON("/api/levels"),
    ]);
    section.innerHTML = `
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 flex items-center gap-1">Taxonomy <span class="help-chip" data-help-id="taxonomy" role="button" tabindex="0" aria-label="What is taxonomy?">?</span></h3>
        <div class="flex items-center gap-2">
          <span id="taxonomy-edit-warning" class="text-[10px] text-amber-400 hidden">edit mode — destructive on published puzzles</span>
          <button type="button" id="taxonomy-edit-toggle" class="text-[10px] uppercase tracking-wider px-2 py-1 rounded ring-1 ring-slate-700 text-slate-400 hover:text-slate-200" aria-pressed="false">Edit taxonomy</button>
          <span class="help-chip" data-help-id="taxonomy-edit" role="button" tabindex="0" aria-label="What does edit mode do?">?</span>
        </div>
      </div>
      <div id="taxonomy-grid" class="grid md:grid-cols-2 gap-6" data-tax-edit="0">
        ${taxonomyTable("Tags", tagsResp.raw, "tag", true)}
        ${taxonomyTable("Levels", levelsResp.raw, "level", false)}
      </div>
    `;
    _wireTaxonomyEditToggle(section);
    // Theme 11: wire inline rename + tag-merge buttons (delegated).
    section.querySelectorAll("[data-taxonomy-rename]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openTaxonomyRenameModal({
          kind: btn.dataset.taxonomyRename,
          oldSlug: btn.dataset.slug,
        });
      });
    });
    section.querySelectorAll("[data-taxonomy-merge='tag']").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        openTagMergeModal();
      });
    });
  } catch (err) {
    section.innerHTML = `
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Taxonomy</h3>
      <div class="text-xs text-rose-300">Failed to load taxonomy: ${escapeHtml(String(err?.message || err))}</div>
    `;
  }
}

// W1.4: gate taxonomy mutations behind an explicit "Edit taxonomy" toggle.
// Rename / merge are destructive on published puzzles (downstream SGFs carry
// the slug); they should not be one click away during normal browsing.
let _taxonomyEditTimer = null;
function _wireTaxonomyEditToggle(section) {
  const btn = section.querySelector("#taxonomy-edit-toggle");
  const grid = section.querySelector("#taxonomy-grid");
  const warn = section.querySelector("#taxonomy-edit-warning");
  if (!btn || !grid) return;
  const setMode = (on) => {
    grid.dataset.taxEdit = on ? "1" : "0";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    btn.textContent = on ? "Exit edit mode" : "Edit taxonomy";
    btn.classList.toggle("ring-amber-500", on);
    btn.classList.toggle("text-amber-400", on);
    if (warn) warn.classList.toggle("hidden", !on);
    if (_taxonomyEditTimer) { clearTimeout(_taxonomyEditTimer); _taxonomyEditTimer = null; }
    if (on) _taxonomyEditTimer = setTimeout(() => setMode(false), 5 * 60 * 1000);
  };
  btn.addEventListener("click", () => setMode(grid.dataset.taxEdit !== "1"));
}

// W4.5 — Library "Recent activity" session panel. Pulls the last 3 runs
// from /api/runs and stamps a localStorage "last visit" so the operator
// can see at a glance what changed since they last opened the dashboard.
const _SESSION_VISIT_KEY = "yengo-dashboard:lastVisit";
async function _loadSessionPanel() {
  const panel = document.getElementById("session-panel");
  if (!panel) return;
  const lastVisit = (() => {
    try { return localStorage.getItem(_SESSION_VISIT_KEY) || ""; } catch (_) { return ""; }
  })();
  try {
    const data = await getJSON("/api/runs?limit=3");
    const runs = data.runs || [];
    if (!runs.length) {
      panel.innerHTML = `
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Recent activity</h3>
        <div class="text-xs text-slate-500">No runs yet.</div>`;
    } else {
      const sinceVisit = lastVisit
        ? runs.filter((r) => (r.started_at || "") > lastVisit).length
        : 0;
      const sinceNote = lastVisit
        ? `<span class="text-[11px] text-slate-500">${sinceVisit} new since your last visit (${escapeHtml(lastVisit.slice(0, 16).replace("T", " "))})</span>`
        : `<span class="text-[11px] text-slate-500">first visit on this device</span>`;
      const rows = runs.map((r) => {
        const sev = r.status === "completed" ? "ok" : r.status === "failed" ? "error" : "neutral";
        return `
          <a href="/runs/${encodeURIComponent(r.run_id)}" class="block rounded-md ring-1 ring-slate-800 bg-slate-900/60 px-3 py-2 hover:ring-slate-600">
            <div class="flex items-baseline justify-between gap-3">
              <span class="font-mono text-xs truncate">${escapeHtml(r.run_id)}</span>
              ${pill(sev, r.status || "?")}
            </div>
            <div class="mt-1 text-[11px] text-slate-500 flex items-center gap-2" data-rel-time="${escapeHtml(r.started_at || "")}">${escapeHtml(r.source || "—")} · ${relTime(r.started_at)}</div>
          </a>`;
      }).join("");
      panel.innerHTML = `
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-xs uppercase tracking-wider text-slate-500">Recent activity</h3>
          ${sinceNote}
        </div>
        <div class="grid md:grid-cols-3 gap-3">${rows}</div>`;
    }
  } catch (err) {
    panel.innerHTML = `
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Recent activity</h3>
      <div class="text-xs text-rose-300">Failed to load runs: ${escapeHtml(String(err?.message || err))}</div>`;
  } finally {
    try { localStorage.setItem(_SESSION_VISIT_KEY, new Date().toISOString()); } catch (_) {/* private mode */}
  }
}

function taxonomyTable(title, rows, key, showCategory) {
  const sorted = [...(rows || [])].sort((a, b) => (b.usage_count || 0) - (a.usage_count || 0));
  // W4.3: max usage drives the inline bar's denominator so even a long-tail
  // distribution shows visible relative weight. Falls back to 1 to avoid /0.
  const maxUsage = Math.max(1, ...sorted.map((r) => r.usage_count || 0));
  const headerCells = showCategory
    ? `<th class="px-2 py-1 text-left">${escapeHtml(key)}</th><th class="px-2 py-1 text-left">category</th><th class="px-2 py-1 text-right">usage <span class="help-chip" data-help-id="tag-usage" role="button" tabindex="0" aria-label="What does usage mean?">?</span></th><th class="px-2 py-1"></th>`
    : `<th class="px-2 py-1 text-left">${escapeHtml(key)}</th><th class="px-2 py-1 text-left">rank <span class="help-chip" data-help-id="level-rank" role="button" tabindex="0" aria-label="What does rank mean?">?</span></th><th class="px-2 py-1 text-right">usage <span class="help-chip" data-help-id="tag-usage" role="button" tabindex="0" aria-label="What does usage mean?">?</span></th><th class="px-2 py-1"></th>`;
  const bodyRows = sorted.map((r) => {
    const slug = r[key] || "";
    const left = escapeHtml(slug || "—");
    const mid = showCategory
      ? escapeHtml(r.category || "—")
      : `${escapeHtml(r.rank_min || "?")}–${escapeHtml(r.rank_max || "?")}`;
    const count = r.usage_count || 0;
    const usage = count.toLocaleString();
    const pct = Math.round((count / maxUsage) * 100);
    const bar = `<span class="tax-bar" aria-hidden="true"><span class="tax-bar-fill" style="width:${pct}%"></span></span>`;
    const renameBtn = slug
      ? `<button type="button" class="tax-mutate text-[10px] uppercase tracking-wider text-amber-400 hover:text-amber-200" data-taxonomy-rename="${escapeHtml(key)}" data-slug="${escapeHtml(slug)}">rename</button>`
      : "";
    return `<tr class="border-t border-slate-800/50">
      <td class="px-2 py-1 font-mono text-slate-200">${left}</td>
      <td class="px-2 py-1 text-slate-400">${mid}</td>
      <td class="px-2 py-1 text-right tabular-nums text-slate-200"><span class="tax-usage-cell">${bar}<span class="tax-usage-num">${usage}</span></span></td>
      <td class="px-2 py-1 text-right">${renameBtn}</td>
    </tr>`;
  }).join("");
  const headerExtra = key === "tag"
    ? `<button type="button" class="tax-mutate text-[10px] uppercase tracking-wider text-amber-400 hover:text-amber-200" data-taxonomy-merge="tag">merge…</button>`
    : "";
  return `
    <div class="rounded-md ring-1 ring-slate-800 bg-slate-900/60 overflow-hidden" data-taxonomy="${escapeHtml(key)}">
      <div class="px-3 py-2 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800 flex items-center justify-between">
        <span>${escapeHtml(title)}</span>
        ${headerExtra}
      </div>
      <div class="max-h-72 overflow-auto">
        <table class="w-full text-xs">
          <thead class="text-slate-500 sticky top-0 bg-slate-900/95">
            <tr>${headerCells}</tr>
          </thead>
          <tbody>${bodyRows || `<tr><td colspan="4" class="px-2 py-3 text-center text-slate-500">no rows</td></tr>`}</tbody>
        </table>
      </div>
    </div>
  `;
}

// Theme 11: open the inline rename preview modal for a tag or level.
async function openTaxonomyRenameModal({ kind, oldSlug }) {
  const dlg = $("#preview-dialog");
  const title = $("#pv-title");
  const body = $("#pv-body");
  const goBtn = $("#pv-go");
  title.textContent = `${kind} rename: ${oldSlug}`;
  body.innerHTML = `
    <form id="taxonomy-rename-form" class="space-y-2">
      <label class="block text-xs text-slate-400">New ${escapeHtml(kind)} slug
        <input type="text" name="new" required minlength="1" maxlength="64"
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 font-mono text-sm text-slate-100"
               pattern="[a-z0-9][a-z0-9-]{0,63}"
               placeholder="lowercase-with-dashes" />
      </label>
      <div class="text-[11px] text-slate-500">Allowed: a–z, 0–9, dash. Starts with letter/digit. Max 64 chars.</div>
    </form>
    <div id="taxonomy-rename-result" class="mt-3 text-xs text-slate-500">enter a new slug, then preview…</div>
  `;
  goBtn.disabled = false;
  goBtn.textContent = "Preview";
  dlg.showModal();

  const newGoBtn = goBtn.cloneNode(true);
  goBtn.parentNode.replaceChild(newGoBtn, goBtn);
  const endpoint = kind === "tag" ? "/api/tags/rename/preview" : "/api/levels/rename/preview";
  newGoBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    const form = $("#taxonomy-rename-form");
    const newSlug = (new FormData(form).get("new") || "").toString().trim();
    if (!newSlug) {
      $("#taxonomy-rename-result").innerHTML = `<span class="text-rose-300">new slug required</span>`;
      return;
    }
    newGoBtn.disabled = true;
    $("#taxonomy-rename-result").innerHTML = `<span class="text-slate-400">running preview…</span>`;
    try {
      const resp = await postJSON(endpoint, { old: oldSlug, new: newSlug });
      const resultEl = $("#taxonomy-rename-result");
      resultEl.innerHTML = _renderTaxonomyPreviewBody(resp.raw || {});
      const applyEndpoint = kind === "tag" ? "/api/tags/rename/apply" : "/api/levels/rename/apply";
      _wireTaxonomyApplyButton(
        resultEl, applyEndpoint, { old: oldSlug, new: newSlug }, newSlug,
      );
    } catch (err) {
      $("#taxonomy-rename-result").innerHTML = errorBlock(`POST ${endpoint}`, err);
    } finally {
      newGoBtn.disabled = false;
    }
  });
}

// Theme 11: open the tag-merge preview modal (multi-source → target).
async function openTagMergeModal() {
  const dlg = $("#preview-dialog");
  const title = $("#pv-title");
  const body = $("#pv-body");
  const goBtn = $("#pv-go");
  title.textContent = `tags merge`;
  body.innerHTML = `
    <form id="tag-merge-form" class="space-y-2">
      <label class="block text-xs text-slate-400">Source tags (comma-separated, ≥ 2)
        <input type="text" name="sources" required
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 font-mono text-sm text-slate-100"
               placeholder="ko, life-and-death" />
      </label>
      <label class="block text-xs text-slate-400">Target tag (will receive merged puzzles)
        <input type="text" name="target" required
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 font-mono text-sm text-slate-100"
               pattern="[a-z0-9][a-z0-9-]{0,63}"
               placeholder="merged-slug" />
      </label>
    </form>
    <div id="tag-merge-result" class="mt-3 text-xs text-slate-500">enter sources + target, then preview…</div>
  `;
  goBtn.disabled = false;
  goBtn.textContent = "Preview";
  dlg.showModal();

  const newGoBtn = goBtn.cloneNode(true);
  goBtn.parentNode.replaceChild(newGoBtn, goBtn);
  newGoBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    const form = $("#tag-merge-form");
    const fd = new FormData(form);
    const sources = (fd.get("sources") || "").toString().split(",").map((s) => s.trim()).filter(Boolean);
    const target = (fd.get("target") || "").toString().trim();
    if (sources.length < 2 || !target) {
      $("#tag-merge-result").innerHTML = `<span class="text-rose-300">need ≥ 2 sources and a target</span>`;
      return;
    }
    newGoBtn.disabled = true;
    $("#tag-merge-result").innerHTML = `<span class="text-slate-400">running preview…</span>`;
    try {
      const resp = await postJSON("/api/tags/merge/preview", { sources, target });
      const resultEl = $("#tag-merge-result");
      resultEl.innerHTML = _renderTaxonomyPreviewBody(resp.raw || {});
      _wireTaxonomyApplyButton(
        resultEl, "/api/tags/merge/apply", { sources, target }, target,
      );
    } catch (err) {
      $("#tag-merge-result").innerHTML = errorBlock(`POST /api/tags/merge/preview`, err);
    } finally {
      newGoBtn.disabled = false;
    }
  });
}

function _renderTaxonomyPreviewBody(raw) {
  const validBadge = raw.valid
    ? `<span class="pill ${PILL_VARIANTS.ok}"><span class="glyph"></span>valid</span>`
    : `<span class="pill ${PILL_VARIANTS.error}"><span class="glyph"></span>invalid</span>`;
  const errs = Array.isArray(raw.errors) && raw.errors.length
    ? `<ul class="mt-2 list-disc list-inside text-rose-300">${raw.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul>`
    : "";
  const sources = Array.isArray(raw.sources) ? raw.sources.join(", ") : "—";
  const stats = [
    _previewStat("Op", raw.op || "—"),
    _previewStat("Sources", sources),
    _previewStat("Target", raw.target || "—"),
    _previewStat("Affected puzzles", raw.affected_puzzle_count == null ? "—" : raw.affected_puzzle_count),
  ].join("");
  const applyBtn = raw.valid
    ? `<button type="button" data-taxonomy-apply class="ml-2 px-2 py-0.5 rounded bg-rose-600 hover:bg-rose-500 text-white">Apply</button>
       <span class="ml-2 text-[11px] text-slate-500">Destructive: rewrites SGFs + config. You will be asked to type the target slug to confirm.</span>`
    : `<span class="text-[11px] text-slate-500">Fix the errors above, then re-preview.</span>`;
  return `
    <div class="mb-2">${validBadge}</div>
    ${stats}
    ${errs}
    <div class="mt-3">${applyBtn}</div>
  `;
}

// Theme 11 (4d): render the apply payload (after Apply succeeds or is refused).
function _renderTaxonomyApplyBody(raw) {
  const okBadge = raw.ok
    ? `<span class="pill ${PILL_VARIANTS.ok}"><span class="glyph"></span>applied</span>`
    : `<span class="pill ${PILL_VARIANTS.error}"><span class="glyph"></span>refused</span>`;
  const errs = Array.isArray(raw.errors) && raw.errors.length
    ? `<ul class="mt-2 list-disc list-inside text-rose-300">${raw.errors.map((e) => `<li>${escapeHtml(typeof e === "string" ? e : (e.message || JSON.stringify(e)))}</li>`).join("")}</ul>`
    : "";
  const sources = Array.isArray(raw.sources) ? raw.sources.join(", ") : "—";
  const stats = [
    _previewStat("Op", raw.op || "—"),
    _previewStat("Sources", sources),
    _previewStat("Target", raw.target || "—"),
    _previewStat("Files scanned", raw.files_scanned == null ? "—" : raw.files_scanned),
    _previewStat("Files rewritten", raw.files_rewritten == null ? "—" : raw.files_rewritten),
    _previewStat("Config updated", raw.config_updated == null ? "—" : String(raw.config_updated)),
    _previewStat("Audit timestamp", raw.audit_timestamp || "—"),
  ].join("");
  return `
    <div class="mb-2">${okBadge}</div>
    ${stats}
    ${errs}
  `;
}

// Theme 11 (4d): wire the Apply button inside a freshly-rendered preview body.
// Caller passes a `resultEl` (the host of the preview HTML), the apply
// `endpoint`, and the apply-request `body`. After typed-verb confirm against
// `verb`, posts to the endpoint, replaces resultEl's innerHTML with the apply
// payload summary, and refreshes the taxonomy section on success.
function _wireTaxonomyApplyButton(resultEl, endpoint, body, verb) {
  const applyBtn = resultEl.querySelector("[data-taxonomy-apply]");
  if (!applyBtn) return;
  applyBtn.addEventListener("click", async () => {
    if (!await confirmDialog({verb})) return;
    applyBtn.disabled = true;
    resultEl.insertAdjacentHTML("beforeend",
      `<div class="mt-2 text-xs text-slate-400" data-taxonomy-apply-status>applying…</div>`);
    try {
      const resp = await postJSON(endpoint, body);
      resultEl.innerHTML = _renderTaxonomyApplyBody(resp.raw || {});
      if (resp.raw && resp.raw.ok) {
        toast("ok", `${resp.raw.op || "taxonomy mutation"} applied`);
        // Refresh the Library taxonomy block so usage counts reflect the rewrite.
        _loadTaxonomySection().catch(() => { /* graceful */ });
      } else {
        toast("error", `${(resp.raw && resp.raw.op) || "taxonomy mutation"} refused`);
      }
    } catch (err) {
      resultEl.innerHTML = errorBlock(`POST ${endpoint}`, err);
    }
  });
}

// Theme 14b: Inventory health surface — badge + per-issue table.
// `report` is the parsed `/api/inventory/check` payload's `raw` field, or null
// when the endpoint failed (graceful degrade — we still want the rest of the
// Library view to render).
function integrityBlock(resp) {
  if (resp === null) {
    return `
      <div class="mt-4 rounded-md ring-1 ring-slate-700 bg-slate-900/40 px-3 py-2 text-xs text-slate-400 flex items-center gap-2">
        <span class="font-semibold uppercase tracking-wider text-slate-500">Integrity</span>
        <span>check unavailable</span>
      </div>`;
  }
  const r = resp.raw || resp;
  const summary = r.summary || { missing_file: 0, orphan_file: 0 };
  const total = (summary.missing_file || 0) + (summary.orphan_file || 0);
  const variant = r.ok ? "ok" : (total > 50 ? "error" : "warn");
  const label = r.ok ? "healthy" : `${total} issue${total === 1 ? "" : "s"}`;
  const badge = `<span class="pill ${PILL_VARIANTS[variant]}"><span class="glyph"></span>${escapeHtml(label)}</span>`;
  const counts = r.ok ? "" : `
    <span class="ml-3 text-xs text-slate-500 font-mono">
      missing_file: <span class="text-slate-300">${summary.missing_file}</span>
      &nbsp;·&nbsp; orphan_file: <span class="text-slate-300">${summary.orphan_file}</span>
    </span>`;
  const issuesTable = r.ok || !Array.isArray(r.issues) || r.issues.length === 0
    ? ""
    : `
      <div class="mt-3 overflow-x-auto">
        <table class="w-full text-xs">
          <thead><tr class="text-left text-slate-500 uppercase tracking-wider">
            <th class="font-normal pb-1 pr-3">kind</th>
            <th class="font-normal pb-1 pr-3">puzzle_id</th>
            <th class="font-normal pb-1">path</th>
          </tr></thead>
          <tbody class="font-mono">
            ${r.issues.slice(0, 50).map((i) => {
              const kindCls = i.kind === "missing_file"
                ? "text-rose-300"
                : "text-amber-300";
              return `<tr class="border-t border-slate-800/60">
                <td class="py-1 pr-3 ${kindCls}">${escapeHtml(i.kind)}</td>
                <td class="py-1 pr-3 text-slate-300">${escapeHtml(i.puzzle_id || "—")}</td>
                <td class="py-1 text-slate-400">${escapeHtml(i.path || "")}</td>
              </tr>`;
            }).join("")}
          </tbody>
        </table>
        ${r.issues.length > 50
          ? `<div class="mt-2 text-[11px] text-slate-500">… ${r.issues.length - 50} more (run <code class="text-slate-400">inventory --check --json</code> in a terminal for the full list).</div>`
          : ""}
      </div>`;
  return `
    <div id="integrity-block" class="mt-4 rounded-md ring-1 ring-slate-800 bg-slate-900/40 px-3 py-2">
      <div class="flex items-center">
        <span class="font-semibold uppercase tracking-wider text-xs text-slate-500 mr-3">Integrity</span>
        ${badge}${counts}
        <span class="ml-auto flex gap-2">
          <button data-inv-op="reconcile"
                  class="rounded-md px-2 py-0.5 text-xs bg-slate-800/60 hover:bg-slate-700/60 ring-1 ring-slate-700 text-slate-300">
            Reconcile…
          </button>
          <button data-inv-op="rebuild"
                  class="rounded-md px-2 py-0.5 text-xs bg-slate-800/60 hover:bg-slate-700/60 ring-1 ring-slate-700 text-slate-300">
            Rebuild…
          </button>
          ${r.ok ? "" : `
          <button data-inv-op="fix"
                  class="rounded-md px-2 py-0.5 text-xs bg-amber-500/15 hover:bg-amber-500/25 ring-1 ring-amber-500/40 text-amber-200">
            Fix…
          </button>`}
        </span>
      </div>
      ${issuesTable}
    </div>`;
}

// Theme 14c3: wire the Preview→Apply buttons inside `integrityBlock`. We
// rebind on every renderOverview() because the DOM is recreated each time.
function _wireInventoryActionButtons(root) {
  root.querySelectorAll("[data-inv-op]").forEach((btn) => {
    btn.addEventListener("click", () => {
      openInventoryMutationModal({ op: btn.dataset.invOp });
    });
  });
}

function _renderInventoryPreviewBody(raw) {
  const rows = [
    _previewStat("Op", raw.op),
    _previewStat("Snapshot present", raw.snapshot_exists ? "yes" : "no"),
    _previewStat("Snapshot total (before)", raw.snapshot_total_before == null ? "—" : raw.snapshot_total_before),
    _previewStat("Disk total", raw.disk_total),
    _previewStat("Delta", raw.delta > 0 ? `+${raw.delta}` : String(raw.delta)),
    _previewStat("Would rewrite snapshot", raw.would_rewrite_snapshot ? "yes" : "no"),
    _previewStat("Would rebuild search DB", raw.would_rebuild_search_db ? "yes" : "no"),
  ].join("");
  const skip = raw.fix_skip_reason
    ? `<div class="preview-warn">${escapeHtml(raw.fix_skip_reason)}</div>`
    : ``;
  return rows + skip;
}

function _renderInventoryResultBody(raw) {
  const rows = [
    _previewStat("Op", raw.op),
    _previewStat("Executed", raw.executed ? "yes" : "no"),
    _previewStat("Snapshot total (before)", raw.snapshot_total_before == null ? "—" : raw.snapshot_total_before),
    _previewStat("Snapshot total (after)", raw.snapshot_total_after),
    _previewStat("Delta", raw.delta > 0 ? `+${raw.delta}` : String(raw.delta)),
    _previewStat("Rewrote snapshot", raw.rewrote_snapshot ? "yes" : "no"),
    _previewStat("Rebuilt search DB", raw.rebuilt_search_db ? "yes" : "no"),
    _previewStat("Audit timestamp", raw.audit_timestamp || "—"),
  ].join("");
  const skip = raw.fix_skip_reason
    ? `<div class="preview-warn">${escapeHtml(raw.fix_skip_reason)}</div>`
    : ``;
  return rows + skip;
}

// Open the shared <preview-dialog> wired for the two-stage inventory flow:
// Preview (sync POST) → Apply (sync POST that morphs the body to result).
async function openInventoryMutationModal({ op }) {
  const dlg = $("#preview-dialog");
  const title = $("#pv-title");
  const body = $("#pv-body");
  const goBtn = $("#pv-go");
  title.textContent = `inventory --${op}`;
  body.innerHTML = `<div class="text-xs text-slate-500">loading preview…</div>`;
  goBtn.disabled = true;
  goBtn.textContent = "Apply";
  dlg.showModal();

  try {
    const resp = await postJSON("/api/inventory/preview", { op });
    const preview = resp.raw || {};
    body.innerHTML = `<div id="inv-preview-body">${_renderInventoryPreviewBody(preview)}</div>`;
    // ``fix`` may report a skip reason — still allow Apply (the apply path
    // will short-circuit identically and write no audit row).
    goBtn.disabled = false;
  } catch (err) {
    body.innerHTML = errorBlock(`POST /api/inventory/preview {op:${op}}`, err);
    goBtn.disabled = true;
  }

  // Intercept the Apply click so the dialog does not close on the form
  // submit. Replace the button to drop any prior listeners.
  const newGoBtn = goBtn.cloneNode(true);
  goBtn.parentNode.replaceChild(newGoBtn, goBtn);
  newGoBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    newGoBtn.disabled = true;
    body.innerHTML = `<div class="text-xs text-slate-500">applying…</div>`;
    try {
      const resp = await postJSON("/api/inventory/apply", { op });
      const result = resp.raw || {};
      body.innerHTML = `<div id="inv-result-body">${_renderInventoryResultBody(result)}</div>`;
      newGoBtn.style.display = "none";
      toast("ok", `inventory --${op} applied`);
    } catch (err) {
      body.innerHTML = errorBlock(`POST /api/inventory/apply {op:${op}}`, err);
    }
  });

  // On dialog close, refresh the Library view so the integrity badge picks
  // up the post-apply state. Cheap because renderOverview is idempotent.
  dlg.addEventListener("close", function _onClose() {
    dlg.removeEventListener("close", _onClose);
    // Restore the original Apply button shape for the next opener.
    newGoBtn.style.display = "";
    newGoBtn.textContent = "Apply";
    if (location.hash === "#overview" || location.hash === "" || location.hash === "#") {
      renderOverview();
    }
  });
}

function levelsTable(rows) {
  if (rows.length === 0) {
    return `<div>
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">By level</h3>
      <div class="text-sm text-slate-500 italic">no rows</div>
    </div>`;
  }
  return `<div>
    <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">By level</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-500 text-xs uppercase tracking-wider">
        <th class="font-normal pb-1">level</th>
        <th class="font-normal pb-1 text-right tabular-nums">count</th>
      </tr></thead>
      <tbody>${rows.map(([k, v]) => {
        const meta = (_levelMeta || {})[Number(k)];
        const label = meta ? meta.label : `level ${k}`;
        const desc = meta ? meta.description : "";
        return `
        <tr class="border-t border-slate-800">
          <td class="py-1" title="${escapeHtml(desc)}">
            <span class="text-slate-200">${escapeHtml(label)}</span>
            <span class="ml-2 text-xs text-slate-500 font-mono">id=${escapeHtml(k)}</span>
          </td>
          <td class="py-1 text-right font-mono tabular-nums">${v.toLocaleString()}</td>
        </tr>`;
      }).join("")}
      </tbody>
    </table>
  </div>`;
}

function contentTypesTable(rows) {
  if (rows.length === 0) {
    return `<div>
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">By content type</h3>
      <div class="text-sm text-slate-500 italic">no rows</div>
    </div>`;
  }
  return `<div>
    <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">By content type</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-500 text-xs uppercase tracking-wider">
        <th class="font-normal pb-1">type</th>
        <th class="font-normal pb-1 text-right tabular-nums">count</th>
      </tr></thead>
      <tbody>${rows.map(([k, v]) => {
        const meta = (_contentTypeMeta || {})[Number(k)];
        const label = meta ? meta.label : `type ${k}`;
        const desc = meta ? meta.description : "";
        return `
        <tr class="border-t border-slate-800">
          <td class="py-1" title="${escapeHtml(desc)}">
            <span class="text-slate-200">${escapeHtml(label)}</span>
            <span class="ml-2 text-xs text-slate-500 font-mono">id=${escapeHtml(k)}</span>
          </td>
          <td class="py-1 text-right font-mono tabular-nums">${v.toLocaleString()}</td>
        </tr>`;
      }).join("")}
      </tbody>
    </table>
  </div>`;
}

function sourcesMiniTable(adapters) {
  const rows = (adapters?.sources || []);
  if (rows.length === 0) return "";
  const active = adapters?.active_adapter || null;
  return `
    <div class="mt-6">
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">Sources (ingest state)</h3>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-slate-500 text-xs uppercase tracking-wider">
          <th class="font-normal pb-1 pl-2">id</th>
          <th class="font-normal pb-1">db</th>
          <th class="font-normal pb-1 text-right tabular-nums">ingested</th>
          <th class="font-normal pb-1 text-right tabular-nums">skipped</th>
          <th class="font-normal pb-1 text-right tabular-nums">failed</th>
          <th class="font-normal pb-1 text-right tabular-nums">total</th>
        </tr></thead>
        <tbody>${rows.map(s => `
          <tr class="border-t border-slate-800">
            <td class="py-1 pl-2 font-mono text-sm">${escapeHtml(s.id)}${s.id === active ? `<span class="ml-2 pill ${PILL_VARIANTS.okFresh}"><span class="glyph"></span>active</span>` : ""}</td>
            <td class="py-1">${s.db_exists ? `<span class="text-emerald-400 text-xs">yes</span>` : `<span class="text-slate-600 text-xs">no</span>`}</td>
            <td class="py-1 text-right font-mono tabular-nums">${(s.ingested||0).toLocaleString()}</td>
            <td class="py-1 text-right font-mono tabular-nums text-orange-300">${(s.skipped||0).toLocaleString()}</td>
            <td class="py-1 text-right font-mono tabular-nums text-rose-300">${(s.failed||0).toLocaleString()}</td>
            <td class="py-1 text-right font-mono tabular-nums text-slate-300">${(s.total||0).toLocaleString()}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
}

function aggTable(title, keyLabel, rows) {
  if (rows.length === 0) {
    return `<div>
      <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">${escapeHtml(title)}</h3>
      <div class="text-sm text-slate-500 italic">no rows</div>
    </div>`;
  }
  return `<div>
    <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">${escapeHtml(title)}</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-slate-500 text-xs uppercase tracking-wider">
        <th class="font-normal pb-1">${escapeHtml(keyLabel)}</th>
        <th class="font-normal pb-1 text-right tabular-nums">count</th>
      </tr></thead>
      <tbody>${rows.map(([k, v]) => `
        <tr class="border-t border-slate-800">
          <td class="py-1 font-mono">${escapeHtml(k)}</td>
          <td class="py-1 text-right font-mono tabular-nums">${v.toLocaleString()}</td>
        </tr>`).join("")}
      </tbody>
    </table>
  </div>`;
}

// ---------- Adapters ----------

// Cached so the click handler can decide whether --source-override is needed
// without reissuing /api/adapters. Refreshed on every renderAdapters().
let _activeAdapter = null;

function adapterHealthDot(a) {
  if (!a.db_exists) return pill("muted", "no db");
  if (a.failed > 0) return pill("error", `${a.failed} failed`);
  if (a.skipped > 0) return pill("warn", `${a.skipped} skipped`);
  return pill("ok", "ok");
}

function adapterRow(a) {
  const isActive = a.id === _activeAdapter;
  const baseBtn = "px-2 py-1 rounded text-xs ring-1 ring-slate-700 hover:bg-slate-800 text-slate-200 transition";
  const lastRun = a.db_mtime
    ? `<span class="text-xs text-slate-400" data-rel-time="${escapeHtml(a.db_mtime)}">${relTime(a.db_mtime)}</span>`
    : `<span class="text-xs text-slate-600 italic">never</span>`;
  const activeMarker = isActive
    ? `<span class="ml-2 pill ${PILL_VARIANTS.okFresh}" title="active_adapter from sources.json"><span class="glyph"></span>active</span>`
    : "";
  const enableBtn = isActive
    ? `<button class="${baseBtn} opacity-50 cursor-not-allowed" disabled title="Already the active adapter">active</button>`
    : `<button class="${baseBtn}" data-act="enable" data-source="${escapeHtml(a.id)}" title="Set as active adapter (writes sources.json)">Enable</button>`;
  const overrideHint = (!isActive && _activeAdapter)
    ? ` title="Clicking Run will auto-pass --source-override (active is '${escapeHtml(_activeAdapter)}')"`
    : "";
  const fullPath = escapeHtml(a.source_root || "—");
  return `
    <tr class="border-t border-slate-800 align-top hover:bg-slate-800/30">
      <td class="py-2 pl-3 pr-4 font-mono text-sm"><a href="/adapters/${encodeURIComponent(a.id)}" data-adapter-link="${escapeHtml(a.id)}" class="text-sky-300 hover:underline">${escapeHtml(a.id)}</a>${activeMarker}</td>
      <td class="py-2 pr-4">${adapterHealthDot(a)}</td>
      <td class="py-2 pr-4">${lastRun}</td>
      <td class="py-2 pr-4 text-right font-mono tabular-nums text-sm">${a.ingested.toLocaleString()}</td>
      <td class="py-2 pr-4 text-right font-mono tabular-nums text-sm text-orange-300">${a.skipped.toLocaleString()}</td>
      <td class="py-2 pr-4 text-right font-mono tabular-nums text-sm text-rose-300">${a.failed.toLocaleString()}</td>
      <td class="py-2 pr-4 text-right font-mono tabular-nums text-sm text-slate-300">${a.total.toLocaleString()}</td>
      <td class="py-2 pr-4 text-xs text-slate-500 font-mono" title="${fullPath}">${escapeHtml(a.source_root || "—")}</td>
      <td class="py-2 pr-3 whitespace-nowrap">
        <button class="${baseBtn}" data-act="run"    data-source="${escapeHtml(a.id)}"${overrideHint}>Run</button>
        <button class="${baseBtn}" data-act="ingest" data-source="${escapeHtml(a.id)}"${overrideHint}>Ingest</button>
        ${enableBtn}
        <button class="${baseBtn} text-rose-300 hover:text-rose-200" data-act="reset-ingest" data-source="${escapeHtml(a.id)}" title="Wipe this source's .yengo-ingest.sqlite. Use when published files were manually deleted and counts are stale.">Reset DB</button>
      </td>
    </tr>
    ${a.error ? `<tr><td colspan="9" class="py-2 px-3 text-xs text-rose-300 bg-rose-500/5 border-t border-rose-500/20">${escapeHtml(a.error)}</td></tr>` : ""}
  `;
}

async function renderAdapters() {
  const root = $("#view-adapters");
  root.innerHTML = `<div class="text-slate-400 text-sm">loading adapters…</div>`;
  try {
    const data = await getJSON("/api/adapters");
    _activeAdapter = data.active_adapter || null;
    refreshSourceLock();
    const rows = data.sources.slice().sort((a, b) => {
      // active first; then problems float up; then newest mtime first
      if (a.id === _activeAdapter && b.id !== _activeAdapter) return -1;
      if (b.id === _activeAdapter && a.id !== _activeAdapter) return 1;
      const bucket = (x) => x.failed > 0 ? 0 : x.skipped > 0 ? 1 : 2;
      const d = bucket(a) - bucket(b);
      if (d !== 0) return d;
      return (b.db_mtime || "").localeCompare(a.db_mtime || "");
    });
    if (rows.length === 0) {
      root.innerHTML = emptyState("No adapters configured.", "Edit <code>config/sources.json</code> to add one.");
      return;
    }
    const activeNote = _activeAdapter
      ? `active: <span class="font-mono text-lime-300">${escapeHtml(_activeAdapter)}</span>`
      : `<span class="text-orange-300">no active adapter</span>`;
    root.innerHTML = `
      ${viewHeader("Adapters", { metaHtml: `
        <span class="view-header-sub">${rows.length} source${rows.length === 1 ? "" : "s"}</span>
        <span class="view-header-sub">·</span>
        <span class="text-xs text-slate-400">${activeNote}</span>
      ` })}
      ${helpCallout("help-adapters", {
        title: "What active adapter and counts mean",
        bodyHtml: `
          <p>An <strong>adapter</strong> is one source's ingest pipeline
          (one row in <code>config/sources.json</code>). Exactly one
          adapter is <em>active</em> at a time — the active one is what
          <code>run</code> targets unless you pass
          <code>--source-override</code>. Switch active via
          <code>enable-adapter</code> (Operations) or the per-row Run
          button (which auto-passes <code>--source-override</code>).</p>
          <ul class="help-callout-list">
            <li><strong>ingested</strong>: puzzles successfully parsed +
              validated this source's last ingest pass.</li>
            <li><strong>skipped</strong>: already-published puzzles whose
              content hash matched an existing entry.</li>
            <li><strong>failed</strong>: puzzles that errored during
              ingest (parse / validation / fetch). Drill in via
              <em>source-status</em> on the adapter detail page to see
              error messages.</li>
            <li><strong>last activity</strong>: mtime of this source's
              <code>.yengo-ingest.sqlite</code> — proxies last successful
              ingest write.</li>
          </ul>
        `,
      })}
      <div class="flex items-center justify-between gap-3 mt-4 mb-2 px-1">
        <input type="search" id="adapter-filter" placeholder="Filter adapters by id or path…"
               class="w-64 max-w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs font-mono text-slate-200 placeholder:text-slate-600"
               aria-label="Filter adapter list" />
        <span class="text-[11px] text-slate-500">Sorted: active · failures first · most recent activity</span>
      </div>
      <div class="overflow-x-auto rounded-md border border-slate-800 bg-slate-900">
        <table class="w-full text-sm" id="adapter-table">
          <thead class="text-slate-500 text-xs uppercase tracking-wider sticky top-0 bg-slate-900">
            <tr>
              <th class="text-left  font-normal py-2 pl-3">id</th>
              <th class="text-left  font-normal py-2">status</th>
              <th class="text-left  font-normal py-2">last activity</th>
              <th class="text-right font-normal py-2 pr-4">ingested</th>
              <th class="text-right font-normal py-2 pr-4">skipped</th>
              <th class="text-right font-normal py-2 pr-4">failed</th>
              <th class="text-right font-normal py-2 pr-4">total</th>
              <th class="text-left  font-normal py-2">source_root</th>
              <th class="text-left  font-normal py-2 pr-3">actions</th>
            </tr>
          </thead>
          <tbody>${rows.map(adapterRow).join("")}</tbody>
        </table>
      </div>
      <section id="adapter-validation-section" class="mt-6"></section>
      <section id="adapter-bootstrap-section" class="mt-6"></section>
      <section id="adapter-scaffold-section" class="mt-6"></section>
    `;
    _loadAdapterValidationSection();
    _renderAdapterBootstrapSection();
    _renderAdapterScaffoldSection();
    _wireAdapterFilter();
  } catch (e) { root.innerHTML = errorBlock("/api/adapters", e); }
}

// W2.2 — pure-JS filter over rendered rows. Match against id (col 1) and
// source_root path (col 8). Empty query restores all rows.
function _wireAdapterFilter() {
  const input = document.getElementById("adapter-filter");
  const table = document.getElementById("adapter-table");
  if (!input || !table) return;
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  input.addEventListener("input", () => {
    const q = input.value.trim().toLowerCase();
    rows.forEach((tr) => {
      if (!q) { tr.style.display = ""; return; }
      const text = tr.textContent.toLowerCase();
      tr.style.display = text.includes(q) ? "" : "none";
    });
  });
}

// Theme 7a: Adapter Configuration Management — read-only validation roll-up.
// Surfaces the `adapter-config validate-all` health pill + per-source FAIL
// rows above the existing adapter table. The full Add/Edit/Bootstrap UI lands
// in subsequent Theme 7 slices and reuses this section for "Validate" feedback.
async function _loadAdapterValidationSection() {
  const section = document.getElementById("adapter-validation-section");
  if (!section) return;
  try {
    const resp = await getJSON("/api/adapter-config/validate");
    const raw = resp.raw || {};
    section.innerHTML = adapterValidationBlock(raw);
  } catch (e) {
    section.innerHTML = errorBlock("/api/adapter-config/validate", e);
  }
}

function adapterValidationBlock(raw) {
  const rows = Array.isArray(raw.rows) ? raw.rows : [];
  const failing = rows.filter(r => !r.ok);
  const ok = raw.ok === true;
  const pillClass = ok
    ? "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40"
    : "bg-rose-500/15 text-rose-300 ring-rose-500/40";
  const pillLabel = ok
    ? `all ${rows.length} sources valid`
    : `${failing.length} of ${rows.length} sources failing`;
  const issuesTable = failing.length === 0 ? "" : `
    <table class="w-full text-sm mt-3" data-adapter-validation>
      <thead class="text-slate-500 text-xs uppercase tracking-wider">
        <tr>
          <th class="text-left font-normal py-1 pl-3">source</th>
          <th class="text-left font-normal py-1">code</th>
          <th class="text-left font-normal py-1 pr-3">message</th>
        </tr>
      </thead>
      <tbody>
        ${failing.flatMap(r => (r.errors || []).map(err => `
          <tr class="border-t border-slate-800">
            <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(r.id)}</td>
            <td class="py-1 font-mono text-xs text-amber-300">${escapeHtml(err.code || "")}</td>
            <td class="py-1 pr-3 text-xs text-slate-300">${escapeHtml(err.message || "")}</td>
          </tr>
        `)).join("")}
      </tbody>
    </table>
  `;
  return `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <h3 class="text-xs uppercase tracking-wider text-slate-500">Adapter validation</h3>
          <span class="help-chip" data-help-id="adapter-validate" role="button" tabindex="0" aria-label="What does validate check?">?</span>
          <span class="pill ring-1 px-2 py-0.5 rounded text-xs ${pillClass}">${pillLabel}</span>
        </div>
        <span class="text-xs text-slate-500 font-mono">adapter-config validate-all</span>
      </div>
      <p class="text-[11px] text-slate-500 mt-1">Checks each source in <code class="font-mono">config/sources.json</code>: schema fields are present and well-typed; <code class="font-mono">config.path</code> exists on disk; <code class="font-mono">adapter</code> kind is registered. Does not run the adapter or read SGFs.</p>
      ${issuesTable}
    </div>
  `;
}

// Theme 7c: Bootstrap wizard — folder scan → preview table → apply selected.
function _renderAdapterBootstrapSection() {
  const section = document.getElementById("adapter-bootstrap-section");
  if (!section) return;
  section.innerHTML = `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-3"
         data-adapter-bootstrap>
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-xs uppercase tracking-wider text-slate-500">Import existing folder <span class="help-chip" data-help-id="adapter-import-folder" role="button" tabindex="0" aria-label="What does import-folder do?">?</span></h3>
          <p class="text-[11px] text-slate-500 mt-0.5">Scan a folder of SGF subdirectories and append each as a source entry. Existing files are not modified.</p>
        </div>
        <span class="text-xs text-slate-500 font-mono">adapter-config bootstrap</span>
      </div>
      <form class="mt-2 grid grid-cols-1 sm:grid-cols-4 gap-2"
            data-adapter-bootstrap-form>
        <input type="text" name="from_folder"
          placeholder="external-sources/my-folder"
          class="sm:col-span-2 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm font-mono">
        <input type="text" name="adapter" value="local"
          class="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm font-mono">
        <input type="text" name="id_prefix" placeholder="(prefix)"
          class="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm font-mono">
        <div class="sm:col-span-4 flex gap-2">
          <button type="submit"
            class="px-3 py-1 text-xs rounded bg-sky-700 hover:bg-sky-600">Preview</button>
          <button type="button" data-adapter-bootstrap-apply
            class="px-3 py-1 text-xs rounded bg-emerald-700 hover:bg-emerald-600 hidden">Apply selected</button>
        </div>
      </form>
      <div class="mt-3" data-adapter-bootstrap-result></div>
    </div>
  `;
  const form = section.querySelector("[data-adapter-bootstrap-form]");
  const result = section.querySelector("[data-adapter-bootstrap-result]");
  const applyBtn = section.querySelector("[data-adapter-bootstrap-apply]");
  let lastPreview = null;
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const data = new FormData(form);
    const body = {
      from_folder: String(data.get("from_folder") || "").trim(),
      adapter: String(data.get("adapter") || "local").trim(),
      id_prefix: String(data.get("id_prefix") || "").trim(),
      dry_run: true,
    };
    if (!body.from_folder) return;
    try {
      const resp = await postJSON("/api/adapter-config/bootstrap", body);
      lastPreview = body;
      result.innerHTML = adapterBootstrapBlock(resp.raw || {});
      applyBtn.classList.toggle("hidden",
        !(resp.raw && resp.raw.entries && resp.raw.entries.some(e => !e.conflicts_with_existing)));
    } catch (e) {
      result.innerHTML = errorBlock("/api/adapter-config/bootstrap", e);
      applyBtn.classList.add("hidden");
    }
  });
  applyBtn.addEventListener("click", async () => {
    if (!lastPreview) return;
    const ok = await confirmDialog({
      title: "Apply bootstrap entries",
      message: `Append all fresh entries from ${lastPreview.from_folder}.`,
      verb: "apply",
    });
    if (!ok) return;
    try {
      const resp = await postJSON("/api/adapter-config/bootstrap",
                                   { ...lastPreview, dry_run: false });
      result.innerHTML = adapterBootstrapBlock(resp.raw || {});
      applyBtn.classList.add("hidden");
      toast(`bootstrap applied: ${(resp.raw.applied_ids || []).length}`, "ok");
    } catch (e) {
      result.innerHTML = errorBlock("/api/adapter-config/bootstrap", e);
    }
  });
}

// Theme 12: Adapter Scaffold — generate a new local adapter package +
// sources.json stub from a small inline form. Preview is read-only; Apply
// writes to disk + sources.json behind a typed-verb confirmation.
function _renderAdapterScaffoldSection() {
  const section = document.getElementById("adapter-scaffold-section");
  if (!section) return;
  section.innerHTML = `
    <div class="flex items-baseline justify-between mb-3">
      <h3 class="text-xs uppercase tracking-wider text-slate-500">Create new adapter from template <span class="help-chip" data-help-id="adapter-scaffold" role="button" tabindex="0" aria-label="What does scaffold do?">?</span></h3>
      <span class="text-xs text-slate-500 font-mono">adapter-scaffold</span>
    </div>
    <p class="text-[11px] text-slate-500 -mt-2 mb-2">Generates a new Python adapter package under <code class="font-mono">backend/puzzle_manager/adapters/</code> and appends a sources.json entry. Use this when the source needs a custom parser; for a plain folder of SGFs use <em>Import existing folder</em>.</p>
    <form data-adapter-scaffold-form class="rounded-md ring-1 ring-slate-800 bg-slate-900/60 p-3 grid md:grid-cols-2 gap-3">
      <label class="block text-xs text-slate-400">Adapter id (lowercase, dashes/underscores)
        <input type="text" name="id" required minlength="1" maxlength="64"
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 font-mono text-sm text-slate-100"
               pattern="[a-z][a-z0-9_-]{0,63}"
               placeholder="my-new-source" />
      </label>
      <label class="block text-xs text-slate-400">Display name (optional)
        <input type="text" name="name"
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-100"
               placeholder="defaults to id" />
      </label>
      <label class="block text-xs text-slate-400 md:col-span-2">SGF folder path (optional, used by the local kind)
        <input type="text" name="path"
               class="mt-1 w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 font-mono text-sm text-slate-100"
               placeholder="data/sources/my-new-source" />
      </label>
      <div class="md:col-span-2 flex items-center gap-2">
        <button type="submit" class="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-xs text-slate-200">Preview</button>
        <span data-adapter-scaffold-status class="text-[11px] text-slate-500"></span>
      </div>
    </form>
    <div data-adapter-scaffold-result class="mt-3"></div>
  `;
  const form = section.querySelector("[data-adapter-scaffold-form]");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const status = section.querySelector("[data-adapter-scaffold-status]");
    const result = section.querySelector("[data-adapter-scaffold-result]");
    const fd = new FormData(form);
    const body = {
      id: (fd.get("id") || "").toString().trim(),
      kind: "local",
      name: ((fd.get("name") || "").toString().trim()) || null,
      path: ((fd.get("path") || "").toString().trim()) || null,
    };
    if (!body.id) {
      result.innerHTML = `<div class="text-xs text-rose-300">id required</div>`;
      return;
    }
    status.textContent = "running preview…";
    try {
      const resp = await postJSON("/api/adapter-scaffold/preview", body);
      result.innerHTML = _renderAdapterScaffoldPreview(resp.raw || {}, body);
      const apply = result.querySelector("[data-adapter-scaffold-apply]");
      if (apply) {
        apply.addEventListener("click", async () => {
          if (!await confirmDialog({verb: body.id})) return;
          status.textContent = "applying…";
          try {
            const r2 = await postJSON("/api/adapter-scaffold/apply", body);
            result.innerHTML = _renderAdapterScaffoldPreview(r2.raw || {}, body);
            toast("ok", `scaffolded adapter ${body.id}`);
          } catch (err) {
            result.innerHTML = errorBlock("POST /api/adapter-scaffold/apply", err);
          } finally {
            status.textContent = "";
          }
        });
      }
    } catch (err) {
      result.innerHTML = errorBlock("POST /api/adapter-scaffold/preview", err);
    } finally {
      status.textContent = "";
    }
  });
}

function _renderAdapterScaffoldPreview(raw, body) {
  const ok = !!raw.ok;
  const okBadge = ok
    ? `<span class="pill ${PILL_VARIANTS.ok}"><span class="glyph"></span>${raw.dry_run ? "preview ok" : "applied"}</span>`
    : `<span class="pill ${PILL_VARIANTS.error}"><span class="glyph"></span>invalid</span>`;
  const errs = Array.isArray(raw.errors) && raw.errors.length
    ? `<ul class="mt-2 list-disc list-inside text-rose-300 text-xs">${raw.errors.map((e) => `<li>${escapeHtml(e.code || "?")}: ${escapeHtml(e.message || "")}</li>`).join("")}</ul>`
    : "";
  const files = Array.isArray(raw.files_created) && raw.files_created.length
    ? `<div class="mt-2 text-xs text-slate-400">Files: <span class="font-mono text-slate-200">${raw.files_created.map(escapeHtml).join("</span>, <span class='font-mono text-slate-200'>")}</span></div>`
    : "";
  const entry = raw.sources_entry
    ? `<pre class="mt-2 bg-slate-950/60 p-2 rounded text-xs font-mono text-slate-300 overflow-auto">${escapeHtml(JSON.stringify(raw.sources_entry, null, 2))}</pre>`
    : "";
  const applyBtn = ok && raw.dry_run
    ? `<button type="button" data-adapter-scaffold-apply class="mt-3 px-3 py-1 rounded bg-rose-700 hover:bg-rose-600 text-xs text-white">Apply (writes ${escapeHtml(body.id)})</button>`
    : "";
  return `
    <div class="rounded-md ring-1 ring-slate-800 bg-slate-900/60 p-3">
      <div class="flex items-center justify-between">
        <div>${okBadge}</div>
        <div class="text-[11px] text-slate-500">${escapeHtml(raw.message || "")}</div>
      </div>
      ${entry}
      ${files}
      ${errs}
      ${applyBtn}
    </div>
  `;
}

function adapterBootstrapBlock(raw) {
  const entries = Array.isArray(raw.entries) ? raw.entries : [];
  if (entries.length === 0) {
    return `<div class="text-xs text-slate-500 italic">no proposals</div>`;
  }
  const head = raw.applied
    ? `<div class="text-xs text-emerald-300 mb-2">Applied ${raw.applied_ids ? raw.applied_ids.length : 0}.</div>`
    : `<div class="text-xs text-slate-400 mb-2">${escapeHtml(raw.message || "preview")}</div>`;
  return head + `
    <table class="w-full text-sm" data-adapter-bootstrap-table>
      <thead class="text-slate-500 text-xs uppercase tracking-wider">
        <tr>
          <th class="text-left font-normal py-1 pl-3">id</th>
          <th class="text-left font-normal py-1">name</th>
          <th class="text-left font-normal py-1">path</th>
          <th class="text-left font-normal py-1 pr-3">status</th>
        </tr>
      </thead>
      <tbody>
        ${entries.map(e => {
          const status = e.conflicts_with_existing
            ? `<span class="text-amber-300">conflict</span>`
            : `<span class="text-emerald-300">fresh</span>`;
          return `<tr class="border-t border-slate-800">
            <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(e.id)}</td>
            <td class="py-1 text-xs">${escapeHtml(e.name)}</td>
            <td class="py-1 font-mono text-xs text-slate-400">${escapeHtml(e.config && e.config.path || "")}</td>
            <td class="py-1 pr-3 text-xs">${status}</td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>
  `;
}

// ---------- Theme 10: Puzzle Detail Page ----------
//
// Deep link: /puzzle/{id}. Joined view across publish-log + SGF + daily +
// audit. Backed by /api/puzzle/{id} (CLI passthrough). Tabs:
// Lineage / SGF / Audit / Daily.

function _normalizePuzzleId(raw) {
  if (!raw) return "";
  let pid = String(raw).trim();
  if (pid.toUpperCase().startsWith("YENGO-")) pid = pid.slice("YENGO-".length);
  return pid.toLowerCase();
}

function showPuzzleDetail(puzzleId, opts = {}) {
  const pid = _normalizePuzzleId(puzzleId);
  if (!pid) return;
  const targetPath = `/puzzle/${encodeURIComponent(pid)}`;
  if (!opts.skipPush && location.pathname !== targetPath) {
    history.pushState({ puzzleId: pid }, "", targetPath);
  }
  $$(".view").forEach((v) => v.classList.add("hidden"));
  const detail = $("#view-puzzle-detail");
  detail.classList.remove("hidden");
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.nav === "library"));
  const crumb = $("#page-breadcrumb");
  if (crumb) crumb.textContent = `library / puzzle / ${pid}`;
  renderPuzzleDetail(pid);
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

async function renderPuzzleDetail(puzzleId) {
  const root = $("#view-puzzle-detail");
  root.innerHTML = `<div class="text-slate-400 text-sm">loading puzzle ${escapeHtml(puzzleId)}…</div>`;
  try {
    const resp = await getJSON(`/api/puzzle/${encodeURIComponent(puzzleId)}`);
    const d = resp.raw || {};
    if (!d.found) {
      root.innerHTML = `
        ${viewHeader(`Puzzle · ${escapeHtml(puzzleId)}`, {
          metaHtml: `<span class="view-header-sub">not found</span>`,
        })}
        <p class="text-sm text-slate-400">No publish-log entries reference this ID.
          Check the ID format (16-hex without the YENGO- prefix) or that the puzzle
          has shipped through publish at least once.</p>
      `;
      return;
    }
    root.innerHTML = `
      ${viewHeader(`Puzzle · ${escapeHtml(d.puzzle_id)}`, {
        metaHtml: `
          <span class="view-header-sub">${escapeHtml(d.source_id || "")}</span>
          <span class="view-header-sub">·</span>
          <span class="view-header-sub">${escapeHtml(d.level || "—")}</span>
        `,
      })}
      <section class="grid md:grid-cols-4 gap-3 mb-4">
        ${summaryTile("publish entries", (d.publish_entries || []).length, "text-slate-100")}
        ${summaryTile("daily appearances", (d.daily_appearances || []).length, "text-slate-300")}
        ${summaryTile("audit rows", (d.audit || []).length, "text-amber-300")}
        ${summaryTile("tags", (d.tags || []).length, "text-sky-300")}
      </section>
      <section class="mb-4">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">Lineage (publish-log chain)</h3>
        ${puzzleLineageTable(d)}
      </section>
      <section class="mb-4">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">SGF</h3>
        ${puzzleSgfBlock(d.sgf)}
      </section>
      <section class="mb-4">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">Daily appearances</h3>
        ${puzzleDailyTable(d.daily_appearances || [])}
      </section>
      <section>
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">Audit trail</h3>
        ${puzzleAuditTable(d.audit || [])}
      </section>
    `;
  } catch (e) {
    root.innerHTML = errorBlock(`/api/puzzle/${puzzleId}`, e);
  }
}

function puzzleLineageTable(d) {
  const entries = Array.isArray(d.publish_entries) ? d.publish_entries : [];
  if (!entries.length) return `<p class="text-xs text-slate-500">no publish-log entries.</p>`;
  const latestRunId = (d.latest && d.latest.run_id) || "";
  const firstRunId = (d.first_publish && d.first_publish.run_id) || "";
  const rows = entries.map((e) => {
    const tag = e.run_id === latestRunId ? `<span class="text-emerald-300">latest</span>`
              : e.run_id === firstRunId ? `<span class="text-sky-300">first</span>`
              : `<span class="text-slate-500">—</span>`;
    return `<tr class="border-t border-slate-800">
      <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(e.run_id || "")}</td>
      <td class="py-1 text-xs">${tag}</td>
      <td class="py-1 font-mono text-xs text-slate-400">${escapeHtml(e.source_id || "")}</td>
      <td class="py-1 text-xs">${escapeHtml(String(e.quality ?? ""))}</td>
      <td class="py-1 pr-3 font-mono text-xs text-slate-400">${escapeHtml(e.path || "")}</td>
    </tr>`;
  }).join("");
  return `<table class="w-full text-sm" data-puzzle-lineage>
    <thead class="text-slate-500 text-xs uppercase tracking-wider">
      <tr>
        <th class="text-left font-normal py-1 pl-3">run_id</th>
        <th class="text-left font-normal py-1">role</th>
        <th class="text-left font-normal py-1">source</th>
        <th class="text-left font-normal py-1">q</th>
        <th class="text-left font-normal py-1 pr-3">path</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>`;
}

function puzzleSgfBlock(sgf) {
  if (!sgf) return `<p class="text-xs text-slate-500">no SGF on disk.</p>`;
  const exists = sgf.exists ? `<span class="text-emerald-300">exists</span>`
                            : `<span class="text-rose-300">missing</span>`;
  const size = sgf.size_bytes != null ? `${sgf.size_bytes} bytes` : "—";
  const preview = sgf.preview
    ? `<pre class="text-xs bg-slate-900 ring-1 ring-slate-800 rounded p-3 overflow-x-auto mt-2">${escapeHtml(sgf.preview)}</pre>`
    : `<p class="text-xs text-slate-500 mt-2">no preview available.</p>`;
  return `
    <div class="text-xs text-slate-400">
      path: <span class="font-mono text-slate-300">${escapeHtml(sgf.path || "")}</span>
      · ${exists} · ${escapeHtml(size)}
    </div>
    ${preview}
  `;
}

function puzzleDailyTable(rows) {
  if (!rows.length) return `<p class="text-xs text-slate-500">never scheduled in any daily.</p>`;
  const body = rows.map((r) => `<tr class="border-t border-slate-800">
    <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(r.date || "")}</td>
    <td class="py-1 text-xs">${escapeHtml(r.section || "")}</td>
    <td class="py-1 text-xs">${escapeHtml(String(r.position ?? ""))}</td>
    <td class="py-1 pr-3 text-xs text-slate-400">${escapeHtml(r.technique || "")}</td>
  </tr>`).join("");
  return `<table class="w-full text-sm" data-puzzle-daily>
    <thead class="text-slate-500 text-xs uppercase tracking-wider">
      <tr>
        <th class="text-left font-normal py-1 pl-3">date</th>
        <th class="text-left font-normal py-1">section</th>
        <th class="text-left font-normal py-1">pos</th>
        <th class="text-left font-normal py-1 pr-3">technique</th>
      </tr>
    </thead>
    <tbody>${body}</tbody>
  </table>`;
}

function puzzleAuditTable(rows) {
  if (!rows.length) return `<p class="text-xs text-slate-500">no audit-log rows reference this puzzle.</p>`;
  const body = rows.map((r) => `<tr class="border-t border-slate-800">
    <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(r.ts || "")}</td>
    <td class="py-1 text-xs">${escapeHtml(r.op || "")}</td>
    <td class="py-1 pr-3 text-xs text-slate-400">${escapeHtml(r.reason || "")}</td>
  </tr>`).join("");
  return `<table class="w-full text-sm" data-puzzle-audit>
    <thead class="text-slate-500 text-xs uppercase tracking-wider">
      <tr>
        <th class="text-left font-normal py-1 pl-3">ts</th>
        <th class="text-left font-normal py-1">op</th>
        <th class="text-left font-normal py-1 pr-3">reason</th>
      </tr>
    </thead>
    <tbody>${body}</tbody>
  </table>`;
}

// ---------- Theme 6a: Adapter Detail Page ----------
//
// Deep link: /adapters/{id}. The SPA shell (server returns index.html for the
// route) reads location.pathname on boot; we reach this via showAdapterDetail()
// either at boot or when the user clicks an adapter id link in the table.
// Hides every other view section so #view-adapter-detail owns the page.

function showAdapterDetail(adapterId, opts = {}) {
  const targetPath = `/adapters/${encodeURIComponent(adapterId)}`;
  if (!opts.skipPush && location.pathname !== targetPath) {
    history.pushState({ adapterId }, "", targetPath);
  }
  $$(".view").forEach((v) => v.classList.add("hidden"));
  const detail = $("#view-adapter-detail");
  detail.classList.remove("hidden");
  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.nav === "library"));
  const crumb = $("#page-breadcrumb");
  if (crumb) crumb.textContent = `library / adapters / ${adapterId}`;
  renderAdapterDetail(adapterId);
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

async function renderAdapterDetail(adapterId) {
  const root = $("#view-adapter-detail");
  root.innerHTML = `<div class="text-slate-400 text-sm">loading ${escapeHtml(adapterId)}…</div>`;
  try {
    const resp = await getJSON(`/api/adapters/${encodeURIComponent(adapterId)}/details`);
    const d = resp.raw || {};
    const summary = d.summary || {};
    const recentRuns = d.recent_runs || [];
    const recentFailures = d.recent_failures || [];
    root.innerHTML = `
      ${viewHeader(`Adapter · ${escapeHtml(d.id || adapterId)}`, {
        metaHtml: `
          <span class="view-header-sub">${escapeHtml(d.adapter || "")}</span>
          <span class="view-header-sub">·</span>
          <a href="/library" class="text-xs text-sky-300 hover:underline" data-back-to-library>← all adapters</a>
        `,
      })}
      <section class="grid md:grid-cols-4 gap-3 mb-4">
        ${summaryTile("ingested", summary.ingested, "text-slate-100")}
        ${summaryTile("skipped", summary.skipped, "text-orange-300")}
        ${summaryTile("failed", summary.failed, "text-rose-300")}
        ${summaryTile("total", summary.total, "text-slate-300")}
      </section>
      <section id="ingest-state-section" class="mb-4" data-adapter-id="${escapeHtml(adapterId)}">
        <div class="text-xs text-slate-500">loading ingest state…</div>
      </section>
      <section class="mb-4">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">recent runs</h3>
        ${adapterDetailRunsTable(recentRuns)}
      </section>
      <section class="mb-4">
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">recent failures</h3>
        ${adapterDetailFailuresTable(recentFailures)}
      </section>
      <section>
        <h3 class="text-xs uppercase tracking-wider text-slate-500 mb-2">config (sources.json)</h3>
        <pre class="text-xs bg-slate-900 ring-1 ring-slate-800 rounded p-3 overflow-x-auto">${escapeHtml(JSON.stringify(d.config || {}, null, 2))}</pre>
      </section>
      <section id="adapter-config-schema-section" data-adapter-id="${escapeHtml(adapterId)}"></section>
    `;
    _loadIngestStateSection(adapterId);
    _loadAdapterConfigSchemaSection(adapterId);
  } catch (e) {
    root.innerHTML = errorBlock(`/api/adapters/${adapterId}/details`, e);
  }
}

// Theme 6b: per-source ingest-DB tile + reset button.
async function _loadIngestStateSection(adapterId) {
  const section = document.getElementById("ingest-state-section");
  if (!section) return;
  try {
    const resp = await getJSON(`/api/adapters/${encodeURIComponent(adapterId)}/ingest-state`);
    const s = resp.raw || {};
    section.innerHTML = ingestStateBlock(s, adapterId);
  } catch (e) {
    section.innerHTML = errorBlock(`/api/adapters/${adapterId}/ingest-state`, e);
  }
}

// Theme 7a: schema-aware adapter-config preview on the Adapter Detail page.
// Surfaces adapter_kind + available_kinds + schema fragment so the operator
// can see what fields the future Edit form will render. Read-only here —
// the Edit form ships in Theme 7b.
async function _loadAdapterConfigSchemaSection(adapterId) {
  const section = document.getElementById("adapter-config-schema-section");
  if (!section) return;
  try {
    const resp = await getJSON(`/api/adapter-config/${encodeURIComponent(adapterId)}`);
    const raw = resp.raw || {};
    section.innerHTML = adapterConfigSchemaBlock(raw, adapterId);
    _wireAdapterConfigForm(adapterId);
  } catch (e) {
    section.innerHTML = errorBlock(`/api/adapter-config/${adapterId}`, e);
  }
}

function adapterConfigSchemaBlock(raw, adapterId) {
  const kind = raw.adapter_kind || "(unknown)";
  const kinds = Array.isArray(raw.available_kinds) ? raw.available_kinds : [];
  const schema = raw.schema_for_kind;
  const props = (schema && schema.properties) || {};
  const required = new Set(Array.isArray(schema && schema.required) ? schema.required : []);
  const propRows = Object.keys(props).map(name => {
    const def = props[name] || {};
    const type = Array.isArray(def.type) ? def.type.join("|") : (def.type || "?");
    const req = required.has(name) ? `<span class="text-amber-300">required</span>` : `<span class="text-slate-500">optional</span>`;
    const desc = escapeHtml(def.description || "");
    return `<tr class="border-t border-slate-800">
      <td class="py-1 pl-3 font-mono text-xs">${escapeHtml(name)}</td>
      <td class="py-1 font-mono text-xs text-slate-400">${escapeHtml(type)}</td>
      <td class="py-1 text-xs">${req}</td>
      <td class="py-1 pr-3 text-xs text-slate-300">${desc}</td>
    </tr>`;
  }).join("");
  const propsTable = propRows
    ? `<table class="w-full text-sm mt-2" data-adapter-config-schema>
        <thead class="text-slate-500 text-xs uppercase tracking-wider">
          <tr>
            <th class="text-left font-normal py-1 pl-3">field</th>
            <th class="text-left font-normal py-1">type</th>
            <th class="text-left font-normal py-1">requirement</th>
            <th class="text-left font-normal py-1 pr-3">description</th>
          </tr>
        </thead>
        <tbody>${propRows}</tbody>
      </table>`
    : `<p class="text-xs text-slate-500 mt-2">No per-kind schema fragment — generic key/value editor will be used in Edit form.</p>`;
  return `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-3 mt-3" data-adapter-config-form-host>
      <div class="flex items-center justify-between">
        <h3 class="text-xs uppercase tracking-wider text-slate-500">Configuration schema</h3>
        <span class="text-xs text-slate-500 font-mono">adapter-config show ${escapeHtml(adapterId)}</span>
      </div>
      <div class="mt-2 text-xs text-slate-400">
        kind: <span class="font-mono text-sky-300">${escapeHtml(kind)}</span>
        · available: <span class="font-mono">${escapeHtml(kinds.join(", "))}</span>
      </div>
      ${propsTable}
      <div class="mt-3 flex items-center gap-2">
        <button type="button"
          class="px-2 py-1 text-xs rounded border border-slate-700 hover:bg-slate-800"
          data-adapter-config-edit-toggle>Edit config</button>
        <button type="button"
          class="px-2 py-1 text-xs rounded border border-rose-800 text-rose-300 hover:bg-rose-900/30"
          data-adapter-config-remove>Remove source</button>
      </div>
      <form class="mt-3 hidden space-y-2" data-adapter-config-edit-form>
        <label class="block text-xs text-slate-400">
          Display name
          <input type="text" name="display_name"
            class="mt-1 block w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm font-mono"
            placeholder="(unchanged)" data-adapter-config-edit-name>
        </label>
        ${Object.keys(props).map(name => {
          const def = props[name] || {};
          const type = Array.isArray(def.type) ? def.type[0] : (def.type || "string");
          return `<label class="block text-xs text-slate-400">
            <span class="font-mono text-slate-300">${escapeHtml(name)}</span>
            <span class="text-slate-500"> (${escapeHtml(String(type))})</span>
            <input type="text" name="${escapeHtml(name)}"
              data-adapter-config-edit-field="${escapeHtml(name)}"
              data-adapter-config-edit-type="${escapeHtml(String(type))}"
              class="mt-1 block w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-sm font-mono"
              placeholder="(JSON value or leave blank)">
          </label>`;
        }).join("")}
        <div class="flex gap-2 pt-1">
          <button type="submit"
            class="px-3 py-1 text-xs rounded bg-sky-700 hover:bg-sky-600">Save</button>
          <button type="button"
            class="px-3 py-1 text-xs rounded border border-slate-700 hover:bg-slate-800"
            data-adapter-config-edit-cancel>Cancel</button>
        </div>
      </form>
    </div>
  `;
}

async function _wireAdapterConfigForm(adapterId) {
  const host = document.querySelector("[data-adapter-config-form-host]");
  if (!host) return;
  const toggle = host.querySelector("[data-adapter-config-edit-toggle]");
  const cancel = host.querySelector("[data-adapter-config-edit-cancel]");
  const form = host.querySelector("[data-adapter-config-edit-form]");
  const removeBtn = host.querySelector("[data-adapter-config-remove]");
  if (toggle && form) {
    toggle.addEventListener("click", () => form.classList.toggle("hidden"));
  }
  if (cancel && form) {
    cancel.addEventListener("click", () => form.classList.add("hidden"));
  }
  if (form) {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const setPairs = [];
      form.querySelectorAll("[data-adapter-config-edit-field]").forEach((inp) => {
        const k = inp.getAttribute("data-adapter-config-edit-field");
        const v = inp.value.trim();
        if (v !== "") setPairs.push(`${k}=${v}`);
      });
      const nameInp = form.querySelector("[data-adapter-config-edit-name]");
      const payload = { set_pairs: setPairs };
      if (nameInp && nameInp.value.trim() !== "") payload.name = nameInp.value.trim();
      try {
        await postJSON(
          `/api/adapter-config/${encodeURIComponent(adapterId)}/update`, payload,
        );
        toast(`saved ${adapterId}`, "ok");
        _loadAdapterConfigSchemaSection(adapterId);
      } catch (e) {
        toast(`update failed: ${e.message || e}`, "error");
      }
    });
  }
  if (removeBtn) {
    removeBtn.addEventListener("click", async () => {
      const ok = await confirmDialog({
        title: `Remove source ${adapterId}`,
        message: `This deletes ${adapterId} from sources.json. Type the source ID to confirm.`,
        verb: adapterId,
      });
      if (!ok) return;
      try {
        await postJSON(
          `/api/adapter-config/${encodeURIComponent(adapterId)}/remove`,
          { force: false },
        );
        toast(`removed ${adapterId}`, "ok");
        location.hash = "#/adapters";
      } catch (e) {
        toast(`remove failed: ${e.message || e}`, "error");
      }
    });
  }
}

function ingestStateBlock(s, adapterId) {
  const status = s.status || "missing";
  const statusClass = {
    healthy: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/40",
    stale:   "bg-amber-500/15 text-amber-300 ring-amber-500/40",
    empty:   "bg-slate-500/15 text-slate-300 ring-slate-500/40",
    missing: "bg-slate-700/40 text-slate-400 ring-slate-700",
  }[status] || "bg-slate-700/40 text-slate-400 ring-slate-700";
  const rows = Number(s.rows || 0).toLocaleString();
  const failed = Number(s.failed || 0).toLocaleString();
  const lastMod = s.last_modified || "—";
  const dbPath = s.db_path || "—";
  const failedRows = (s.failed_rows || []);
  const failedTable = failedRows.length === 0
    ? `<div class="text-xs text-slate-500 italic mt-2">no failed rows recorded</div>`
    : `
      <details class="mt-2">
        <summary class="text-xs text-slate-400 cursor-pointer hover:text-slate-200">
          show ${failedRows.length} failed row${failedRows.length === 1 ? "" : "s"}
        </summary>
        <div class="mt-2 overflow-x-auto rounded border border-slate-800">
          <table class="w-full text-xs">
            <thead class="text-slate-500 uppercase tracking-wider">
              <tr>
                <th class="text-left font-normal py-1 pl-2">rel_path</th>
                <th class="text-left font-normal py-1">skip_reason</th>
                <th class="text-left font-normal py-1 pr-2">run_id</th>
              </tr>
            </thead>
            <tbody>${failedRows.map((r) => `
              <tr class="border-t border-slate-800">
                <td class="py-1 pl-2 pr-3 font-mono">${escapeHtml(r.rel_path || "")}</td>
                <td class="py-1 pr-3">${escapeHtml(r.skip_reason || "—")}</td>
                <td class="py-1 pr-2 font-mono text-slate-500">${escapeHtml(r.run_id || "")}</td>
              </tr>
            `).join("")}</tbody>
          </table>
        </div>
      </details>
    `;
  const resetEnabled = s.db_exists ? "" : "disabled";
  return `
    <div class="rounded-md bg-slate-900 ring-1 ring-slate-800 p-3">
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-xs uppercase tracking-wider text-slate-500">ingest state</h3>
        <button type="button"
                data-ingest-reset="${escapeHtml(adapterId)}"
                ${resetEnabled}
                class="text-xs px-2 py-1 rounded bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/40
                       hover:bg-rose-500/25 disabled:opacity-40 disabled:pointer-events-none">
          Reset ingest state
        </button>
      </div>
      <div class="grid md:grid-cols-4 gap-3 text-xs">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500">status</div>
          <span class="inline-block mt-1 px-2 py-0.5 rounded ring-1 ${statusClass}">${escapeHtml(status)}</span>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500">rows</div>
          <div class="font-mono tabular-nums text-slate-200">${rows}</div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500">failed</div>
          <div class="font-mono tabular-nums text-rose-300">${failed}</div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-slate-500">last modified</div>
          <div class="text-slate-300">${escapeHtml(lastMod)}</div>
        </div>
      </div>
      <div class="mt-2 text-[11px] text-slate-500 font-mono">${escapeHtml(dbPath)}</div>
      ${failedTable}
    </div>
  `;
}

// Two-stage modal: GET /preview → typed-confirm → POST /reset. Mirrors the
// inventory-mutation flow (Theme 14c3) but per-source.
async function openIngestStateResetModal(adapterId) {
  const dlg = document.getElementById("preview-dialog");
  const title = document.getElementById("pv-title");
  const body = document.getElementById("pv-body");
  const goBtn = document.getElementById("pv-go");
  title.textContent = `source-ingest-state ${adapterId} --reset`;
  body.innerHTML = `<div class="text-xs text-slate-500">loading preview…</div>`;
  goBtn.disabled = true;
  goBtn.textContent = "Reset";
  dlg.showModal();

  let preview = {};
  try {
    const resp = await getJSON(
      `/api/adapters/${encodeURIComponent(adapterId)}/ingest-state/preview`
    );
    preview = resp.raw || {};
  } catch (err) {
    body.innerHTML = errorBlock(
      `GET /api/adapters/${adapterId}/ingest-state/preview`,
      err,
    );
    return;
  }

  body.innerHTML = `
    <div class="text-sm text-slate-200">
      This will permanently delete the per-source ingest DB at:
      <pre class="mt-1 text-xs bg-slate-900 ring-1 ring-slate-800 rounded p-2 overflow-x-auto">${escapeHtml(preview.would_delete_path || "—")}</pre>
    </div>
    <div class="grid grid-cols-3 gap-3 mt-3 text-xs">
      <div>
        <div class="text-[10px] uppercase tracking-wider text-slate-500">rows lost</div>
        <div class="font-mono tabular-nums text-rose-300">${Number(preview.row_count_lost || 0).toLocaleString()}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider text-slate-500">failed rows lost</div>
        <div class="font-mono tabular-nums text-amber-300">${Number(preview.failed_rows_lost || 0).toLocaleString()}</div>
      </div>
      <div>
        <div class="text-[10px] uppercase tracking-wider text-slate-500">requires full re-ingest</div>
        <div class="text-slate-200">${preview.requires_full_reingest ? "yes" : "no"}</div>
      </div>
    </div>
    <p class="text-xs text-slate-500 mt-3">
      The next pipeline run for this source will re-walk every file from scratch.
    </p>
  `;
  goBtn.disabled = false;

  // Replace the button to drop any prior listeners.
  const newGoBtn = goBtn.cloneNode(true);
  goBtn.parentNode.replaceChild(newGoBtn, goBtn);
  newGoBtn.addEventListener("click", async (e) => {
    e.preventDefault();
    dlg.close();
    const ok = await confirmDialog({
      title: "Reset ingest state",
      body: `This wipes the per-source ingest DB for "${adapterId}". The next run will reprocess every file from scratch.`,
      verb: `reset ${adapterId}`,
    });
    if (!ok) return;
    try {
      const resp = await postJSON(
        `/api/adapters/${encodeURIComponent(adapterId)}/ingest-state/reset`,
        {},
      );
      const result = resp.raw || {};
      if (result.removed) {
        toast("ok", `ingest DB removed (${Number(result.rows_lost || 0).toLocaleString()} rows lost)`);
      } else {
        toast("warn", "no ingest DB to remove");
      }
      _loadIngestStateSection(adapterId);
    } catch (err) {
      toast("error", `reset failed: ${err && err.message ? err.message : err}`);
    }
  });
}

function summaryTile(label, value, valueClass) {
  const v = (value === undefined || value === null) ? "—" : Number(value).toLocaleString();
  return `
    <div class="rounded-md bg-slate-900 ring-1 ring-slate-800 px-3 py-2">
      <div class="text-[10px] uppercase tracking-wider text-slate-500">${escapeHtml(label)}</div>
      <div class="text-2xl font-mono tabular-nums ${valueClass}">${v}</div>
    </div>
  `;
}

function adapterDetailRunsTable(rows) {
  if (!rows.length) return `<div class="text-xs text-slate-500 italic">no runs recorded for this source</div>`;
  return `
    <div class="overflow-x-auto rounded-md border border-slate-800 bg-slate-900">
      <table class="w-full text-sm">
        <thead class="text-slate-500 text-xs uppercase tracking-wider">
          <tr>
            <th class="text-left  font-normal py-2 pl-3">run_id</th>
            <th class="text-left  font-normal py-2">started</th>
            <th class="text-left  font-normal py-2">status</th>
            <th class="text-right font-normal py-2 pr-4">ingested</th>
            <th class="text-right font-normal py-2 pr-4">failed</th>
            <th class="text-right font-normal py-2 pr-3">skipped</th>
          </tr>
        </thead>
        <tbody>${rows.map((r) => `
          <tr class="border-t border-slate-800">
            <td class="py-2 pl-3 pr-4 font-mono text-xs">${escapeHtml(r.run_id || "")}</td>
            <td class="py-2 pr-4 text-xs text-slate-400">${escapeHtml(r.started_at || "—")}</td>
            <td class="py-2 pr-4 text-xs">${escapeHtml(r.status || "")}</td>
            <td class="py-2 pr-4 text-right font-mono tabular-nums text-xs">${Number(r.ingested || 0).toLocaleString()}</td>
            <td class="py-2 pr-4 text-right font-mono tabular-nums text-xs text-rose-300">${Number(r.failed || 0).toLocaleString()}</td>
            <td class="py-2 pr-3 text-right font-mono tabular-nums text-xs text-orange-300">${Number(r.skipped || 0).toLocaleString()}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

function adapterDetailFailuresTable(rows) {
  if (!rows.length) return `<div class="text-xs text-slate-500 italic">no failures in recent runs</div>`;
  return `
    <div class="overflow-x-auto rounded-md border border-slate-800 bg-slate-900">
      <table class="w-full text-sm">
        <thead class="text-slate-500 text-xs uppercase tracking-wider">
          <tr>
            <th class="text-left font-normal py-2 pl-3">item_id</th>
            <th class="text-left font-normal py-2">stage</th>
            <th class="text-left font-normal py-2">error_type</th>
            <th class="text-left font-normal py-2 pr-3">message</th>
          </tr>
        </thead>
        <tbody>${rows.map((r) => `
          <tr class="border-t border-slate-800">
            <td class="py-2 pl-3 pr-4 font-mono text-xs">${escapeHtml(r.item_id || "")}</td>
            <td class="py-2 pr-4 text-xs">${escapeHtml(r.stage || "")}</td>
            <td class="py-2 pr-4 text-xs text-rose-300">${escapeHtml(r.error_type || "")}</td>
            <td class="py-2 pr-3 text-xs text-slate-300">${escapeHtml(r.error_message || "")}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  `;
}

// Intercept clicks on adapter id links in the table — keep them as <a> for
// middle-click / right-click ergonomics, but hijack normal clicks so we don't
// reload the SPA shell.
document.addEventListener("click", (e) => {
  const link = e.target.closest("a[data-adapter-link]");
  if (link && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
    e.preventDefault();
    showAdapterDetail(link.dataset.adapterLink);
    return;
  }
  const back = e.target.closest("a[data-back-to-library]");
  if (back && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
    e.preventDefault();
    showTab("library");
  }
  const reset = e.target.closest("button[data-ingest-reset]");
  if (reset && !reset.disabled) {
    e.preventDefault();
    openIngestStateResetModal(reset.dataset.ingestReset);
  }
});

function emptyState(headline, hintHtml = "") {
  return `<div class="rounded-lg border border-dashed border-slate-700 p-8 text-center">
    <p class="text-sm text-slate-300">${escapeHtml(headline)}</p>
    ${hintHtml ? `<p class="text-xs text-slate-500 mt-2">${hintHtml}</p>` : ""}
  </div>`;
}

// Single source of truth for top-of-view headers. Every render* function MUST
// emit its title via this helper so the five views stay visually aligned —
// before this existed, Overview was bare, LiveRun used mb-4, the rest used
// mb-3, and the subtext slot was inlined inconsistently. The accompanying
// .view-header CSS rule pins the wrapper.
//
// `metaHtml` is rendered raw on purpose so callers can pass a status pill or
// a counter span; `subtext` is plain text (escaped). Pass one or neither.
function viewHeader(title, { subtext = "", metaHtml = "" } = {}) {
  const trailing = metaHtml
    ? metaHtml
    : (subtext ? `<span class="view-header-sub">${escapeHtml(subtext)}</span>` : "");
  return `<div class="view-header">
    <h2 class="view-header-title">${escapeHtml(title)}</h2>
    ${trailing}
  </div>`;
}

// Inline contextual help block. Per UX-handoff: every primary view should
// expose short page-level guidance the operator can read without leaving.
// Uses <details> so it stays unobtrusive — open by default the first time
// the page renders, collapsed by user preference (sessionStorage key per id).
function helpCallout(id, { title, bodyHtml }) {
  const stored = sessionStorage.getItem(`yengo-dashboard:help-open:${id}`);
  const openAttr = stored === "0" ? "" : " open";
  return `<details id="${escapeHtml(id)}" class="help-callout"${openAttr}
                   data-help-callout="${escapeHtml(id)}">
    <summary class="help-callout-summary">
      <span class="help-callout-icon" aria-hidden="true">?</span>
      <span class="help-callout-title">${escapeHtml(title)}</span>
    </summary>
    <div class="help-callout-body">${bodyHtml}</div>
  </details>`;
}

// One delegate persists the open/closed preference per callout id so the
// layout doesn't re-expand on every navigation. Cheap; called once at boot.
function _wireHelpCallouts() {
  document.addEventListener("toggle", (e) => {
    const el = e.target.closest("[data-help-callout]");
    if (!el) return;
    sessionStorage.setItem(
      `yengo-dashboard:help-open:${el.dataset.helpCallout}`,
      el.open ? "1" : "0",
    );
  }, true);
}

// Slice 3: contextual help drawer. Per-route mapping → docs/ path served
// by the existing /api/docs/file endpoint. The Guide tab was demoted from
// the primary nav; users now reach contextual docs via the `?` toggle in
// the top header. The /guide/{path} deep-link route stays wired.
const _HELP_ROUTE_MAP = {
  library:    { path: "how-to/tools/run-yengo-dashboard.md",      title: "Library — Sources & inventory" },
  pipeline:   { path: "reference/puzzle-manager-cli.md",          title: "Pipeline — Run & history" },
  daily:      { path: "architecture/backend/puzzle-manager.md",   title: "Daily — Daily challenge surface" },
  activity:   { path: "architecture/tools/yengo_dashboard.md",    title: "Activity — Unified timeline" },
  operations: { path: "reference/puzzle-manager-cli.md",          title: "Operations — Vacuum / clean / rollback" },
  logs:       { path: "architecture/backend/logging.md",          title: "Logs — Stage logs & audit" },
  guide:      { path: "architecture/tools/yengo_dashboard.md",    title: "Guide — Docs viewer" },
};

function _activeNavName() {
  const active = document.querySelector(".nav-item.active");
  return active?.dataset.nav || "library";
}

async function openHelpDrawer(routeKey) {
  const drawer  = document.getElementById("help-drawer");
  const backdrop = document.getElementById("help-drawer-backdrop");
  const toggle   = document.getElementById("help-drawer-toggle");
  if (!drawer) return;
  const key = routeKey || _activeNavName();
  const entry = _HELP_ROUTE_MAP[key] || _HELP_ROUTE_MAP.library;
  drawer.hidden = false;
  backdrop.hidden = false;
  // Force reflow so the slide-in transition runs on the next frame.
  void drawer.offsetWidth;
  drawer.dataset.open = "true";
  backdrop.dataset.open = "true";
  drawer.setAttribute("aria-hidden", "false");
  toggle?.setAttribute("aria-expanded", "true");
  document.getElementById("help-drawer-title-text").textContent = entry.title;
  document.getElementById("help-drawer-meta").innerHTML =
    `Source: <code>docs/${escapeHtml(entry.path)}</code> · ` +
    `<a href="/guide/${entry.path.split("/").map(encodeURIComponent).join("/")}">open in Guide</a>`;
  const body = document.getElementById("help-drawer-body");
  body.innerHTML = `<div class="text-zinc-500 text-sm">Loading <code>${escapeHtml(entry.path)}</code>…</div>`;
  try {
    const r = await fetch(`/api/docs/file?path=${encodeURIComponent(entry.path)}`);
    if (!r.ok) {
      body.innerHTML = `<div class="text-rose-400 text-sm">Failed to load (${r.status}).</div>`;
      return;
    }
    const md = await r.text();
    if (window.marked) {
      window.marked.setOptions({ gfm: true, breaks: false });
      body.innerHTML = window.marked.parse(md);
    } else {
      body.innerHTML = `<pre>${escapeHtml(md)}</pre>`;
    }
    body.scrollTop = 0;
  } catch (err) {
    body.innerHTML = `<div class="text-rose-400 text-sm">${escapeHtml(String(err))}</div>`;
  }
}

function closeHelpDrawer() {
  const drawer = document.getElementById("help-drawer");
  const backdrop = document.getElementById("help-drawer-backdrop");
  const toggle = document.getElementById("help-drawer-toggle");
  if (!drawer) return;
  drawer.dataset.open = "false";
  backdrop.dataset.open = "false";
  drawer.setAttribute("aria-hidden", "true");
  toggle?.setAttribute("aria-expanded", "false");
  setTimeout(() => {
    if (drawer.dataset.open === "false") {
      drawer.hidden = true;
      backdrop.hidden = true;
    }
  }, 220);
}

function _wireHelpDrawer() {
  const toggle   = document.getElementById("help-drawer-toggle");
  const closeBtn = document.getElementById("help-drawer-close");
  const backdrop = document.getElementById("help-drawer-backdrop");
  if (toggle) {
    toggle.addEventListener("click", () => {
      const drawer = document.getElementById("help-drawer");
      if (drawer?.dataset.open === "true") closeHelpDrawer();
      else openHelpDrawer();
    });
  }
  closeBtn?.addEventListener("click", closeHelpDrawer);
  backdrop?.addEventListener("click", closeHelpDrawer);
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const drawer = document.getElementById("help-drawer");
    if (drawer?.dataset.open === "true") closeHelpDrawer();
  });
}

// ---------- Live Run ----------

let _es = null;
let _activeHandle = null;
const LOG_BUFFER_CAP = 5000;
const LOG_FILTER = { level: "all", stream: "all", search: "" };
let _autoScroll = true;
let _stages = { ingest: "pending", analyze: "pending", publish: "pending" };

function detectLogLevel(text) {
  // Lightweight heuristic — the cockpit doesn't classify, but visual
  // grouping needs *something*. Order matters (error > warn > info).
  if (/\b(ERROR|FATAL|Traceback|exception|failed|✕)\b/i.test(text)) return "error";
  if (/\b(WARN|WARNING|skipped|retry|⚠)\b/i.test(text)) return "warn";
  if (/\b(INFO|DEBUG)\b/.test(text)) return "info";
  return "info";
}

function detectStageTransition(text) {
  // CLI emits stage banners like "[stage:ingest] starting" or "stage analyze complete".
  const m = text.match(/\b(ingest|analyze|publish)\b/i);
  if (!m) return null;
  const stage = m[1].toLowerCase();
  if (/\b(start|begin|enter|starting)\b/i.test(text)) return [stage, "active"];
  if (/\b(complete|finished|done)\b/i.test(text))     return [stage, "done"];
  if (/\b(fail|error)\b/i.test(text))                 return [stage, "failed"];
  return null;
}

function applyRowFilter(node, ev) {
  const matches =
    (LOG_FILTER.level === "all" || node.dataset.level === LOG_FILTER.level) &&
    (LOG_FILTER.stream === "all" || node.dataset.stream === LOG_FILTER.stream) &&
    (LOG_FILTER.search === "" || ev.text.toLowerCase().includes(LOG_FILTER.search));
  node.classList.toggle("filter-hidden", !matches);
}

function logPanelAppend(panel, ev) {
  const level = detectLogLevel(ev.text || "");
  const node = document.createElement("div");
  node.className = "log-row";
  node.dataset.stream = ev.stream || "stdout";
  node.dataset.level = level;
  const seq = String(ev.seq ?? "").padStart(5, " ");
  node.innerHTML = `
    <span class="lr-seq">${escapeHtml(seq)}</span>
    <span class="lr-stream">${escapeHtml(ev.stream || "stdout")}</span>
    <span class="lr-text">${escapeHtml(ev.text || "")}</span>
  `;
  applyRowFilter(node, ev);
  panel.appendChild(node);

  // Cap the in-DOM buffer so the cockpit doesn't OOM on a 200K-line run.
  while (panel.childElementCount > LOG_BUFFER_CAP) {
    panel.firstElementChild.remove();
  }

  // Stage stepper update.
  const trans = detectStageTransition(ev.text || "");
  if (trans) {
    _stages[trans[0]] = trans[1];
    paintStepper();
  }

  if (_autoScroll) {
    const nearBottom = panel.scrollHeight - panel.scrollTop - panel.clientHeight < 80;
    if (nearBottom) panel.scrollTop = panel.scrollHeight;
  }
  updateLogCount();
}

function updateLogCount() {
  const panel = $("#run-log");
  const counter = $("#run-log-count");
  if (!panel || !counter) return;
  const total = panel.childElementCount;
  const visible = panel.querySelectorAll(".log-row:not(.filter-hidden)").length;
  counter.textContent = visible === total
    ? `${total.toLocaleString()} lines`
    : `${visible.toLocaleString()} / ${total.toLocaleString()} lines`;
}

function paintStepper() {
  const stepper = $("#run-stepper");
  if (!stepper) return;
  stepper.innerHTML = ["ingest", "analyze", "publish"].map((s) => `
    <span class="step" data-state="${_stages[s]}">${s}</span>
  `).join("");
}

function resetLogState() {
  _stages = { ingest: "pending", analyze: "pending", publish: "pending" };
  $("#run-log").innerHTML = "";
  paintStepper();
  updateLogCount();
}

function setRunStatusBadge(status, exitCode) {
  const badge = $("#run-status");
  if (!badge) return;
  const variantMap = {
    starting:  ["info", "starting…"],
    running:   ["running", "running"],
    completed: ["ok", `completed${exitCode != null ? ` · exit ${exitCode}` : ""}`],
    failed:    ["error", `failed${exitCode != null ? ` · exit ${exitCode}` : ""}`],
    cancelled: ["warn", "cancelled"],
  };
  const [variant, label] = variantMap[status] || ["muted", status || "idle"];
  badge.outerHTML = `<span id="run-status">${pill(variant, label)}</span>`;
}

function attachStream(handle) {
  if (_es) { try { _es.close(); } catch {} _es = null; }
  _activeHandle = handle;
  const panel = $("#run-log");
  if (!panel) return;
  const cancelBtn = $("#run-cancel");
  if (cancelBtn) cancelBtn.disabled = false;
  const es = new EventSource(`/api/run/${encodeURIComponent(handle)}/events`);
  _es = es;
  es.addEventListener("line", (e) => {
    try { logPanelAppend(panel, JSON.parse(e.data)); } catch {}
  });
  es.addEventListener("status", (e) => {
    try {
      const snap = JSON.parse(e.data);
      setRunStatusBadge(snap.status, snap.exit_code);
      if (isTerminal(snap.status)) paintMaintCardTerminal(snap.handle, snap);
    } catch {}
  });
  es.addEventListener("end", () => {
    if (cancelBtn) cancelBtn.disabled = true;
    es.close();
    if (_es === es) _es = null;
    refreshActiveSnapshot();
    masterTick();  // refresh body[data-run-active]
    // If the Pipeline tab is currently visible the History tile ("Last
    // failure", success rate, recent runs) was painted from a snapshot taken
    // when the user navigated in. Re-render it so the just-ended run shows
    // up without requiring a tab switch.
    if ($("#view-history") && !$("#view-history").classList.contains("hidden")) {
      renderHistory().catch(() => {});
    }
  });
  es.onerror = () => { /* browser auto-reconnects */ };
}

async function refreshActiveSnapshot() {
  try {
    const data = await getJSON("/api/run/active");
    const a = data.active;
    const meta = $("#run-meta");
    const cancelBtn = $("#run-cancel");
    if (!a) {
      setRunStatusBadge("idle");
      if (meta) { meta.innerHTML = ""; meta.classList.add("hidden"); }
      if (cancelBtn) cancelBtn.disabled = true;
      return;
    }
    setRunStatusBadge(a.status, a.exit_code);
    if (meta) {
      // Compact horizontal strip: handle · pid · lines · started · [details].
      // The full command is collapsed inside a <details> so it doesn't push
      // the layout when the path is long. The whole strip wraps gracefully.
      const cmdStr = a.command.join(" ");
      meta.classList.remove("hidden");
      meta.innerHTML = `
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono">
          <span><span class="text-slate-600">handle</span> ${escapeHtml(a.handle)}</span>
          <span><span class="text-slate-600">pid</span> ${a.pid ?? "—"}</span>
          <span><span class="text-slate-600">lines</span> <span class="tabular-nums">${a.line_count.toLocaleString()}</span></span>
          <span><span class="text-slate-600">started</span> <span data-rel-time="${escapeHtml(a.started_at)}">${relTime(a.started_at)}</span></span>
          <details class="ml-auto">
            <summary class="cursor-pointer text-slate-500 hover:text-slate-300 select-none">command</summary>
            <pre class="mt-1 text-slate-400 whitespace-pre-wrap break-all max-w-full">${escapeHtml(cmdStr)}</pre>
          </details>
        </div>`;
    }
    if (cancelBtn) cancelBtn.disabled = isTerminal(a.status) || a.cancel_requested;
  } catch { /* swallow */ }
}

async function startRun(payload) {
  resetLogState();
  $("#run-error") && ($("#run-error").innerHTML = "");
  try {
    const snap = await postJSON("/api/run", payload || {});
    attachStream(snap.handle);
    refreshActiveSnapshot();
    masterTick();
    toast("ok", `run started · ${snap.handle}`);
  } catch (err) {
    if (err.status === 409) {
      toast("warn", "another run is already active");
    } else {
      $("#run-error") && ($("#run-error").innerHTML = errorBlock("POST /api/run", err));
      toast("error", "run failed to start");
    }
  }
}

async function cancelActiveRun() {
  if (!_activeHandle) return;
  try {
    await postJSON(`/api/run/${encodeURIComponent(_activeHandle)}/cancel`, {});
    toast("warn", "cancel requested");
  } catch (err) {
    $("#run-error") && ($("#run-error").innerHTML = errorBlock("cancel", err));
    toast("error", "cancel failed");
  }
}

function readRunForm() {
  const get = (id) => {
    const v = $(id);
    if (!v) return null;
    if (v.type === "checkbox") return v.checked;
    return v.value.trim() === "" ? null : v.value.trim();
  };
  return {
    source: _activeAdapter || get("#run-source"),
    stage: get("#run-stage"),
    fresh: get("#run-fresh"),
    dry_run: get("#run-dry-run"),
    source_override: get("#run-source-override"),
    no_enrichment: get("#run-no-enrichment"),
  };
}

// Build the literal CLI invocation for the current Run form. Pure function:
// no DOM reads beyond the passed snapshot, so tests can exercise it directly.
function buildCliEquivalent(snap) {
  const parts = ["python", "-m", "backend.puzzle_manager", "run"];
  if (snap.source) parts.push("--source", snap.source);
  if (snap.stage)  parts.push("--stage",  snap.stage);
  if (snap.fresh)           parts.push("--fresh");
  if (snap.dry_run)         parts.push("--dry-run");
  if (snap.source_override) parts.push("--source-override");
  if (snap.no_enrichment)   parts.push("--no-enrichment");
  return parts.join(" ");
}

function paintCliEquivalent() {
  const el = $("#run-cli-equiv");
  if (!el) return;
  el.textContent = buildCliEquivalent(readRunForm());
}

// Re-paint the locked Source field if the Live Run pane is mounted. Called
// whenever _activeAdapter changes (after enable/disable, or after the
// background fetch completes). Cheap no-op if the user is on another tab.
function refreshSourceLock() {
  const input = $("#run-source");
  if (!input) return;
  const hasActive = !!_activeAdapter;
  input.value = _activeAdapter || "";
  input.placeholder = hasActive ? "" : "no active adapter — enable one first";
  const hint = $("#run-source-hint");
  if (hint) {
    hint.innerHTML = hasActive
      ? 'change the active adapter from the Adapters tab to run a different one.'
      : '<span class="text-orange-300">No active adapter.</span> Enable one from the Adapters tab.';
  }
  const startBtn = $("#run-start");
  if (startBtn) {
    startBtn.disabled = !hasActive;
    if (!hasActive) startBtn.title = "No active adapter — enable one from the Adapters tab.";
    else startBtn.removeAttribute("title");
  }
  paintCliEquivalent();
}

function renderLiveRun() {
  const root = $("#view-run");
  // Pre-populate _activeAdapter if we don't have it yet — non-blocking; the
  // form remains usable (greys to "no active adapter") until the cache fills.
  if (_activeAdapter === null) {
    getJSON("/api/adapters").then(d => { _activeAdapter = d.active_adapter || null; refreshSourceLock(); }).catch(() => {});
  }
  const hasActive = !!_activeAdapter;
  root.innerHTML = `
    ${viewHeader("Live Run", { metaHtml: `
      <span id="run-status">${pill("muted", "idle")}</span>
      <div id="run-stepper" class="stepper ml-2"></div>
    ` })}

    ${helpCallout("help-run", {
      title: "What this page does",
      bodyHtml: `
        <p>Launch a pipeline run against the active adapter, watch the live
        subprocess output, and cancel mid-flight. The literal command is
        always visible in the <strong>Equivalent CLI</strong> block — copy it
        to reproduce the run from a terminal.</p>
        <ul class="help-callout-list">
          <li><code>--fresh</code>: wipe the source's ingest DB + runtime
            state before running. Forces a full re-ingest. <em>Destructive.</em></li>
          <li><code>--dry-run</code>: rehearse without writing published
            outputs. Safe.</li>
          <li><code>--source-override</code>: route the active adapter
            through a different source ID for this run only.</li>
          <li><code>--no-enrichment</code>: skip the analyze stage's KataGo
            enrichment pass. Faster; produces less complete metadata.</li>
          <li><code>--stage</code>: run only one of <code>ingest</code> /
            <code>analyze</code> / <code>publish</code> instead of the full
            pipeline.</li>
        </ul>
      `,
    })}

    <div class="grid lg:grid-cols-[18rem,1fr] gap-6">
      <aside class="rounded-md border border-slate-800 bg-slate-900 p-4 space-y-3 self-start">
        <div>
          <label class="block text-xs uppercase tracking-wider text-slate-500 mb-1">Source <span class="text-slate-600 normal-case">· locked to active adapter</span></label>
          <input id="run-source" type="text"
                 value="${escapeHtml(_activeAdapter || '')}"
                 placeholder="${hasActive ? '' : 'no active adapter — enable one first'}"
                 class="w-full bg-slate-950/60 border border-slate-800 rounded px-2 py-1 text-sm font-mono text-slate-300 cursor-not-allowed"
                 disabled aria-readonly="true" />
          <p id="run-source-hint" class="mt-1 text-[11px] text-slate-500">
            ${hasActive
              ? 'change the active adapter from the Adapters tab to run a different one.'
              : '<span class="text-orange-300">No active adapter.</span> Enable one from the Adapters tab.'}
          </p>
        </div>
        <div>
          <label class="block text-xs uppercase tracking-wider text-slate-500 mb-1">Stage</label>
          <select id="run-stage" class="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm">
            <option value="">(full pipeline)</option>
            <option value="ingest">ingest</option>
            <option value="analyze">analyze</option>
            <option value="publish">publish</option>
          </select>
        </div>
        <div class="space-y-1.5 pt-1">
          <label class="flex items-center gap-2 text-xs" title="Wipes this source's .yengo-ingest.sqlite + .pm-runtime/state. Forces full re-ingest."><input id="run-fresh" type="checkbox" /> --fresh<span class="text-rose-400 ml-1 font-semibold">(destructive: wipes ingest DB + runtime state)</span> <span class="help-chip" data-help-id="fresh-flag" role="button" tabindex="0" aria-label="What does --fresh do?">?</span></label>
          <label class="flex items-center gap-2 text-xs"><input id="run-dry-run" type="checkbox" /> --dry-run</label>
          <label class="flex items-center gap-2 text-xs"><input id="run-source-override" type="checkbox" /> --source-override</label>
          <label class="flex items-center gap-2 text-xs"><input id="run-no-enrichment" type="checkbox" /> --no-enrichment</label>
        </div>
        <div class="flex gap-2 pt-2">
          <button id="run-start"  class="flex-1 ${PILL_VARIANTS.ok}     hover:bg-emerald-500/20 disabled:opacity-40 disabled:pointer-events-none text-sm rounded-md px-3 py-1.5"${hasActive ? '' : ' disabled title="No active adapter — enable one from the Adapters tab."'}>Start</button>
          <button id="run-cancel" class="flex-1 ${PILL_VARIANTS.warn}   hover:bg-orange-500/20 disabled:opacity-40 disabled:pointer-events-none text-sm rounded-md px-3 py-1.5" disabled>Cancel</button>
        </div>
        <div id="run-cli-equiv-block" class="pt-3 mt-2 border-t border-slate-800 space-y-1.5">
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500">Equivalent CLI</span>
            <button id="run-cli-copy" type="button"
                    class="ml-auto text-[10px] uppercase tracking-wider text-slate-400 hover:text-slate-200 px-1.5 py-0.5 rounded border border-slate-800"
                    aria-label="Copy CLI command to clipboard">Copy</button>
          </div>
          <pre id="run-cli-equiv"
               class="font-mono text-[11px] text-emerald-300 whitespace-pre-wrap break-all bg-slate-950/60 border border-slate-800 rounded px-2 py-1.5"
               aria-live="polite">python -m backend.puzzle_manager run</pre>
        </div>
      </aside>

      <div class="space-y-3 min-w-0">
        <!-- Log toolbar -->
        <div class="flex flex-wrap items-center gap-2 text-xs">
          <span class="text-slate-500 uppercase tracking-wider">Filter:</span>
          <div class="inline-flex rounded-md ring-1 ring-slate-700 overflow-hidden" id="log-level">
            <button data-level="all"   class="px-2 py-1 bg-slate-800 text-slate-200">all</button>
            <button data-level="info"  class="px-2 py-1 hover:bg-slate-800">info</button>
            <button data-level="warn"  class="px-2 py-1 hover:bg-slate-800 text-orange-300">warn</button>
            <button data-level="error" class="px-2 py-1 hover:bg-slate-800 text-rose-300">error</button>
          </div>
          <div class="inline-flex rounded-md ring-1 ring-slate-700 overflow-hidden" id="log-stream">
            <button data-stream="all"    class="px-2 py-1 bg-slate-800 text-slate-200">both</button>
            <button data-stream="stdout" class="px-2 py-1 hover:bg-slate-800">stdout</button>
            <button data-stream="stderr" class="px-2 py-1 hover:bg-slate-800">stderr</button>
          </div>
          <input id="log-search" type="search" placeholder="search…" class="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs w-48" />
          <label class="ml-auto inline-flex items-center gap-1.5 text-slate-400">
            <input id="log-pin" type="checkbox" checked /> pin to bottom
          </label>
          <span id="run-log-count" class="text-slate-500 tabular-nums">0 lines</span>
        </div>

        <div id="run-error"></div>
        <div id="run-log" class="log-panel"></div>
        <!-- Compact run metadata: handle / pid / lines / started.
             Lives below the log so the long command path can wrap freely
             without pushing the form panel taller than the log area. -->
        <div id="run-meta" class="text-[11px] text-slate-500 mt-2 hidden"></div>
      </div>
    </div>
  `;
  paintStepper();
  updateLogCount();

  $("#run-start") .addEventListener("click", () => startRun(readRunForm()));
  $("#run-cancel").addEventListener("click", cancelActiveRun);

  // Equivalent-CLI block: paint once, then re-paint on any form change so
  // the operator can see the literal command they're about to launch.
  paintCliEquivalent();
  ["#run-stage", "#run-fresh", "#run-dry-run", "#run-source-override", "#run-no-enrichment"]
    .forEach((sel) => {
      const el = $(sel);
      if (el) el.addEventListener("change", paintCliEquivalent);
    });
  const copyBtn = $("#run-cli-copy");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      const text = $("#run-cli-equiv")?.textContent || "";
      try {
        await navigator.clipboard.writeText(text);
        const orig = copyBtn.textContent;
        copyBtn.textContent = "Copied";
        setTimeout(() => { copyBtn.textContent = orig; }, 1200);
      } catch {
        copyBtn.textContent = "Copy failed";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
      }
    });
  }

  // Toolbar wiring
  $("#log-level").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-level]"); if (!b) return;
    LOG_FILTER.level = b.dataset.level;
    $$("#log-level button").forEach((x) => x.classList.toggle("bg-slate-800", x === b));
    $$("#log-level button").forEach((x) => x.classList.toggle("text-slate-200", x === b));
    rerunFilter();
  });
  $("#log-stream").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-stream]"); if (!b) return;
    LOG_FILTER.stream = b.dataset.stream;
    $$("#log-stream button").forEach((x) => x.classList.toggle("bg-slate-800", x === b));
    $$("#log-stream button").forEach((x) => x.classList.toggle("text-slate-200", x === b));
    rerunFilter();
  });
  let searchT;
  $("#log-search").addEventListener("input", (e) => {
    clearTimeout(searchT);
    searchT = setTimeout(() => {
      LOG_FILTER.search = e.target.value.toLowerCase();
      rerunFilter();
    }, 120);
  });
  $("#log-pin").addEventListener("change", (e) => { _autoScroll = e.target.checked; });

  refreshActiveSnapshot();
  // Best-effort: if there is an active run not yet streamed, attach now.
  getJSON("/api/run/active").then((d) => {
    if (d.active && !_es) attachStream(d.active.handle);
  }).catch(() => {});
}

function rerunFilter() {
  const panel = $("#run-log");
  if (!panel) return;
  $$(".log-row", panel).forEach((node) => {
    const text = node.querySelector(".lr-text")?.textContent || "";
    applyRowFilter(node, { text, stream: node.dataset.stream });
  });
  updateLogCount();
}

// ---------- Maintenance ----------

// Per-handle bookkeeping so the originating maintenance card can paint its
// own terminal state without yanking the operator over to Live Run. The map
// is keyed by run handle; entries persist after termination so the "View
// live" link keeps working.
const _maintCards = new Map();

const MAINT_TAIL_LINES = 6;
const MAINT_TAIL_POLL_MS = 1200;

function _renderTailLines(lines) {
  if (!lines || lines.length === 0) return "";
  // Newest at the bottom; trim long lines so a runaway path doesn't push the
  // card to absurd width. Streams are colored via the data-stream attribute.
  return `<pre class="inline-log" aria-label="last ${lines.length} log lines">` +
    lines.map((ln) => {
      const cls = ln.stream === "stderr" ? "log-stderr" : "log-stdout";
      return `<span class="${cls}">${escapeHtml(ln.text)}</span>`;
    }).join("\n") +
    `</pre>`;
}

async function _pollMaintCardTail(handle) {
  const entry = _maintCards.get(handle);
  if (!entry || entry.stopped) return;
  try {
    const data = await getJSON(`/api/run/${encodeURIComponent(handle)}/tail?n=${MAINT_TAIL_LINES}`);
    const tailEl = entry.cardStatus.querySelector(".card-tail");
    if (tailEl) tailEl.innerHTML = _renderTailLines(data.lines);
    if (isTerminal(data.status)) {
      _stopMaintCardTail(handle);
      return;
    }
  } catch {
    // 404 means the controller moved on; stop polling silently.
    _stopMaintCardTail(handle);
    return;
  }
  entry.timer = setTimeout(() => _pollMaintCardTail(handle), MAINT_TAIL_POLL_MS);
}

function _stopMaintCardTail(handle) {
  const entry = _maintCards.get(handle);
  if (!entry) return;
  entry.stopped = true;
  if (entry.timer) { clearTimeout(entry.timer); entry.timer = null; }
}

function paintMaintCardTerminal(handle, snap) {
  const entry = _maintCards.get(handle);
  if (!entry) return;
  const { card, cardStatus, verb } = entry;
  _stopMaintCardTail(handle);
  card.removeAttribute("data-pending");
  const exit = snap.exit_code != null ? ` · exit ${snap.exit_code}` : "";
  let pillHtml;
  if (snap.status === "completed") {
    pillHtml = pill("okFresh", `${verb} completed${exit}`);
  } else if (snap.status === "failed") {
    pillHtml = pill("error", `${verb} failed${exit}`);
  } else if (snap.status === "cancelled") {
    pillHtml = pill("warn", `${verb} cancelled`);
  } else {
    return;
  }
  // Preserve any final tail content so the operator can read the last lines
  // without teleporting to Live Run. Tail rendered above the action row.
  const existingTail = cardStatus.querySelector(".card-tail")?.outerHTML || `<div class="card-tail"></div>`;
  cardStatus.innerHTML = `${existingTail}
    <div class="card-status-row">${pillHtml}
      <a class="view-live" data-handle="${escapeHtml(handle)}" role="button" tabindex="0">View full log →</a>
    </div>`;
  // Final tail fetch so the card shows the *terminal* tail, not whatever
  // arrived before the SSE end event.
  getJSON(`/api/run/${encodeURIComponent(handle)}/tail?n=${MAINT_TAIL_LINES}`)
    .then((data) => {
      const tailEl = cardStatus.querySelector(".card-tail");
      if (tailEl) tailEl.innerHTML = _renderTailLines(data.lines);
    })
    .catch(() => { /* controller moved on; keep what we had */ });
}

async function startMaintenance(url, payload, verbForToast, originBtn) {
  $("#maint-error") && ($("#maint-error").innerHTML = "");
  // Live Run owns the SSE log panel. If the operator hasn't visited that tab
  // yet its DOM doesn't exist, and attachStream() would no-op silently —
  // leaving the maint card stuck on "running…" forever. Render it now into
  // its hidden container so the SSE pipeline has somewhere to write.
  if (!$("#run-log")) renderLiveRun();
  const card = originBtn?.closest("section[data-maint-card]") || null;
  const cardStatus = card?.querySelector(".card-status") || null;
  if (card) card.dataset.pending = "true";
  if (cardStatus) cardStatus.innerHTML = `${pill("running", `${verbForToast}…`)}`;
  try {
    const snap = await postJSON(url, payload || {});
    if (card && cardStatus) {
      _maintCards.set(snap.handle, { card, cardStatus, verb: verbForToast, timer: null, stopped: false });
      cardStatus.innerHTML = `
        <div class="card-tail"></div>
        <div class="card-status-row">
          ${pill("running", `${verbForToast} · ${escapeHtml(snap.handle.slice(0, 8))}`)}
          <a class="view-live" data-handle="${escapeHtml(snap.handle)}" role="button" tabindex="0">View full log →</a>
        </div>
      `;
      _pollMaintCardTail(snap.handle);
    }
    // Pre-attach the SSE so log accumulates even if the operator never
    // visits Live Run. Resetting log state is safe — Live Run is hidden.
    resetLogState();
    attachStream(snap.handle);
    refreshActiveSnapshot();
    masterTick();
    toast("ok", `${verbForToast} started · ${snap.handle.slice(0, 8)}`);
  } catch (err) {
    if (card) card.removeAttribute("data-pending");
    if (cardStatus) cardStatus.innerHTML = "";
    if (err.status === 409) {
      toast("warn", "another mutation is already active");
    } else {
      $("#maint-error") && ($("#maint-error").innerHTML = errorBlock(`POST ${url}`, err));
      toast("error", `${verbForToast} failed to start`);
    }
  }
}

function readCleanForm() {
  const target = $("#mc-target").value;
  const days = $("#mc-days").value.trim();
  const dryRaw = $("#mc-dry").value;
  const body = {};
  if (target) body.target = target;
  if (days !== "") body.retention_days = Number(days);
  if (dryRaw !== "") body.dry_run = (dryRaw === "true");
  return body;
}

function readRollbackForm() {
  const body = {
    reason: $("#mr-reason").value.trim(),
    run_id: $("#mr-run-id").value.trim(),
  };
  body.dry_run = $("#mr-dry").checked;
  body.yes = $("#mr-yes").checked;
  body.verify = $("#mr-verify").checked;
  return body;
}

function readVacuumForm() {
  return { rebuild: $("#mv-rebuild").checked, dry_run: $("#mv-dry").checked };
}

// ---------- Theme 1e: dry-run preview modal ----------
//
// Each Operations card grows a "Preview" button next to "Run". Clicking
// it fetches GET /api/{op}/preview synchronously, renders a structured
// impact summary (counts + sample rows) into the shared <dialog>, and
// offers a "Run for real" button that re-uses startMaintenance() with
// dry_run=false so the operator never has to retype the form.
//
// The dashboard is the consumer side of principle #6: it renders the
// CLI's preview payload as-is and never re-derives counts or labels.

const PREVIEW_SAMPLE_LIMIT = 20;

function _formatPreviewBytes(n) {
  if (n == null) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
  if (n < 1024 * 1024 * 1024) return `${(n / 1024 / 1024).toFixed(1)} MiB`;
  return `${(n / 1024 / 1024 / 1024).toFixed(2)} GiB`;
}

function _previewStat(label, value) {
  return `<div class="preview-stat">
    <span class="preview-stat-label">${escapeHtml(label)}</span>
    <span class="preview-stat-value">${escapeHtml(String(value))}</span>
  </div>`;
}

function _previewSampleList(items, formatter) {
  if (!items || items.length === 0) {
    return `<div class="text-xs text-slate-500 italic">none</div>`;
  }
  const sample = items.slice(0, PREVIEW_SAMPLE_LIMIT);
  const more = items.length > PREVIEW_SAMPLE_LIMIT
    ? `<div class="preview-list-row text-slate-500">… and ${items.length - PREVIEW_SAMPLE_LIMIT} more</div>`
    : ``;
  return `<div class="preview-list">
    ${sample.map(it => `<div class="preview-list-row" title="${escapeHtml(formatter(it))}">${escapeHtml(formatter(it))}</div>`).join("")}
    ${more}
  </div>`;
}

function _previewErrors(errors) {
  if (!errors || errors.length === 0) return ``;
  return `<div class="preview-warn">
    <div class="font-semibold mb-1">CLI warnings</div>
    ${errors.map(e => `<div>${escapeHtml(e)}</div>`).join("")}
  </div>`;
}

function _renderCleanPreview(raw) {
  const target = raw.target == null ? "(retention default)" : raw.target;
  return [
    _previewStat("Target", target),
    _previewStat("Retention days", raw.retention_days),
    _previewStat("Files to delete", raw.total_files),
    _previewStat("Bytes to free", _formatPreviewBytes(raw.total_bytes)),
    `<div class="text-xs text-slate-500 uppercase tracking-wider">Sample (first ${PREVIEW_SAMPLE_LIMIT})</div>`,
    _previewSampleList(raw.would_delete, (it) => `${it.path}  ·  ${_formatPreviewBytes(it.bytes)}`),
    _previewErrors(raw.errors),
  ].join("");
}

function _renderRollbackPreview(raw) {
  const reversibleNote = raw.reversible
    ? ``
    : `<div class="preview-warn">
         <strong>Irreversible</strong> — rollback deletes SGF files and
         rebuilds the search DB. The publish-log entries remain so the
         operator can re-run the ingest, but the original SGF bytes are
         gone unless backed up.
       </div>`;
  return [
    _previewStat("Puzzles affected", raw.puzzles_affected),
    _previewStat("Runs touched", (raw.affected_runs || []).join(", ") || "—"),
    `<div class="text-xs text-slate-500 uppercase tracking-wider">Affected puzzle IDs (first ${PREVIEW_SAMPLE_LIMIT})</div>`,
    _previewSampleList(raw.affected_puzzles, (id) => id),
    reversibleNote,
    _previewErrors(raw.errors),
  ].join("");
}

function _renderVacuumPreview(raw) {
  const dbNote = raw.has_content_db
    ? ``
    : `<div class="preview-warn">No <code>yengo-content.db</code> on disk — vacuum would be a no-op.</div>`;
  return [
    dbNote,
    _previewStat("Orphan rows", raw.orphan_rows),
    _previewStat("On-disk SGF files", raw.on_disk_files),
    _previewStat("Estimated bytes freed", _formatPreviewBytes(raw.freed_bytes_estimate)),
    _previewStat("Rebuild requested", raw.rebuild ? "yes" : "no"),
  ].join("");
}

const PREVIEW_RENDERERS = {
  clean:       _renderCleanPreview,
  rollback:    _renderRollbackPreview,
  "vacuum-db": _renderVacuumPreview,
};

// Open the preview modal for one op. The caller passes the GET query
// params, the POST runUrl + bodyForReal that "Run for real" should use,
// and an optional confirm step (for destructive ops).
async function openPreviewModal({
  op,                // "clean" | "rollback" | "vacuum-db"
  previewUrl,        // full URL incl. query string
  runUrl,            // POST URL (e.g. "/api/clean")
  buildRunBody,      // () => body for the real run (already has dry_run=false)
  verb,              // human label for toasts ("clean", "rollback", ...)
  originBtn,         // the card's Run button — startMaintenance() uses it for the status pill
  confirmRun,        // optional () => Promise<boolean> to gate "Run for real"
}) {
  const dlg = $("#preview-dialog");
  const title = $("#pv-title");
  const body = $("#pv-body");
  const goBtn = $("#pv-go");
  title.textContent = `${verb} preview`;
  body.innerHTML = `<div class="text-xs text-slate-500">loading preview…</div>`;
  goBtn.disabled = true;
  dlg.showModal();

  let payload = null;
  try {
    const resp = await getJSON(previewUrl);
    payload = resp.raw || {};
    const renderer = PREVIEW_RENDERERS[op];
    body.innerHTML = renderer
      ? renderer(payload)
      : `<pre class="text-xs whitespace-pre-wrap">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`;
    goBtn.disabled = false;
  } catch (err) {
    body.innerHTML = errorBlock(`GET ${previewUrl}`, err);
    goBtn.disabled = true;
  }

  const onClose = async () => {
    dlg.removeEventListener("close", onClose);
    if (dlg.returnValue !== "ok") return;
    if (confirmRun) {
      const ok = await confirmRun();
      if (!ok) return;
    }
    startMaintenance(runUrl, buildRunBody(), verb, originBtn);
  };
  dlg.addEventListener("close", onClose);
}

function _previewQueryFromClean() {
  const params = new URLSearchParams();
  const target = $("#mc-target").value;
  const days = $("#mc-days").value.trim();
  if (target) params.set("target", target);
  if (days !== "") params.set("retention_days", days);
  return params;
}

function _previewQueryFromRollback() {
  const params = new URLSearchParams();
  const runId = $("#mr-run-id").value.trim();
  const reason = $("#mr-reason").value.trim();
  if (runId) params.set("run_id", runId);
  if (reason) params.set("reason", reason);
  return params;
}

function _previewQueryFromVacuum() {
  const params = new URLSearchParams();
  if ($("#mv-rebuild").checked) params.set("rebuild", "true");
  return params;
}

async function runPublishLogSearch() {
  const params = new URLSearchParams();
  for (const [id, key] of [
    ["#pl-run-id", "run_id"], ["#pl-puzzle-id", "puzzle_id"],
    ["#pl-source", "source"], ["#pl-trace-id", "trace_id"],
    ["#pl-date", "date"], ["#pl-from", "from"], ["#pl-to", "to"],
    ["#pl-limit", "limit"],
  ]) {
    const v = $(id).value.trim();
    if (v) params.set(key, v);
  }
  const out = $("#pl-results");
  if (params.toString() === "") {
    out.innerHTML = `<div class="text-xs text-orange-300">Provide at least one filter.</div>`;
    return;
  }
  out.innerHTML = `<div class="text-xs text-slate-500">searching…</div>`;
  try {
    const res = await getJSON(`/api/publish-log/search?${params.toString()}`);
    out.innerHTML = renderPublishLogResults(res.raw);
  } catch (err) { out.innerHTML = errorBlock("publish-log search", err); }
}

// Slice 5: render the publish-log search payload as a structured table so
// operators can scan columns instead of squinting at JSON. The CLI returns
// either a list of entries or a {results: [...]} envelope; treat both.
function renderPublishLogResults(raw) {
  const rows = Array.isArray(raw) ? raw : (raw?.results || raw?.entries || []);
  if (!Array.isArray(rows) || rows.length === 0) {
    const detailsBlock = `<details class="mt-2"><summary class="cursor-pointer text-xs text-slate-500">raw JSON</summary>
      <pre class="mt-1 text-xs text-slate-400 whitespace-pre-wrap font-mono bg-slate-950 border border-slate-800 rounded p-2 max-h-60 overflow-auto">${escapeHtml(JSON.stringify(raw, null, 2))}</pre>
    </details>`;
    return `<div class="text-xs text-slate-400 italic">no entries match the filter.</div>${detailsBlock}`;
  }
  // Discover columns from the first row, with a stable lead order for the
  // common keys so the table is recognizable across pipeline schema bumps.
  const lead = ["timestamp", "ts", "date", "run_id", "puzzle_id", "source", "trace_id", "action", "status"];
  const seen = new Set(lead);
  const extras = [];
  for (const k of Object.keys(rows[0] || {})) {
    if (!seen.has(k)) { extras.push(k); seen.add(k); }
  }
  const cols = lead.filter(c => rows.some(r => c in r)).concat(extras);
  return `
    <div class="overflow-x-auto rounded-md border border-slate-800 bg-slate-900">
      <table class="w-full text-xs">
        <thead class="text-slate-500 uppercase tracking-wider sticky top-0 bg-slate-900">
          <tr>${cols.map(c => `<th class="font-normal text-left py-1.5 px-2">${escapeHtml(c)}</th>`).join("")}</tr>
        </thead>
        <tbody>${rows.map(r => `
          <tr class="border-t border-slate-800 align-top">
            ${cols.map(c => {
              const v = r[c];
              const cell = v == null ? "" : (typeof v === "object" ? JSON.stringify(v) : String(v));
              return `<td class="py-1 px-2 font-mono text-slate-200 break-all">${escapeHtml(cell)}</td>`;
            }).join("")}
          </tr>`).join("")}
        </tbody>
      </table>
    </div>
    <div class="mt-2 text-[11px] text-slate-500">${rows.length.toLocaleString()} entr${rows.length === 1 ? "y" : "ies"}</div>
  `;
}

function maintCard(opts) {
  // opts: { title, group, body, button: {label, id, variant, destructive},
  //         preview?: {id, label}, op?: string, tooltip?: string }
  //         ↑ Theme 16b: op + tooltip carry the catalog row's op token and
  //         a "scope: …; reversible: …" hint for hover-to-explain.
  const variantCls = PILL_VARIANTS[opts.button.variant] || PILL_VARIANTS.info;
  const destructive = opts.button.destructive ? `data-destructive` : ``;
  const opAttr = opts.op ? ` data-op="${escapeHtml(opts.op)}"` : ``;
  const titleAttr = opts.tooltip ? ` title="${escapeHtml(opts.tooltip)}"` : ``;
  const previewBtn = opts.preview
    ? `<button id="${opts.preview.id}" type="button"
              class="maint-preview-btn shrink-0 text-xs rounded-md px-3 py-1.5
                     bg-sky-500/10 text-sky-300 ring-1 ring-sky-500/30 hover:brightness-125">
         ${escapeHtml(opts.preview.label || "Preview")}
       </button>`
    : ``;
  return `
    <section data-maint-card${opAttr} data-maint-verb="${escapeHtml(opts.button.label)}"
             class="maint-card flex flex-col rounded-md border border-slate-800 bg-slate-900 p-4 space-y-3
                    ${opts.group === 'destructive' ? 'border-l-2 border-l-rose-500/40' : ''}"${titleAttr}>
      <header class="flex items-baseline justify-between">
        <h3 class="text-sm font-semibold text-slate-200">${escapeHtml(opts.title)}</h3>
        <span class="text-[10px] uppercase tracking-wider text-slate-500">${escapeHtml(opts.group)}</span>
      </header>
      <div class="flex-1">${opts.body}</div>
      <div class="flex gap-2 mt-auto">
        ${previewBtn}
        <button id="${opts.button.id}" ${destructive}
                class="flex-1 ${variantCls} hover:brightness-125 text-sm rounded-md px-3 py-1.5">
          ${escapeHtml(opts.button.label)}
        </button>
      </div>
      <div class="card-status"></div>
    </section>`;
}

// Theme 16b: card-body specs keyed by catalog `op` token. The catalog drives
// section placement (maintenance / destructive); these specs only describe
// the form fields + button IDs the existing handlers depend on.
const OPS_CARD_SPECS = {
  "vacuum-db": {
    title: "Vacuum DB",
    body: `
      <label class="flex items-center gap-2 text-xs"><input id="mv-rebuild" type="checkbox" /> --rebuild (full rebuild from disk)</label>
      <label class="flex items-center gap-2 text-xs"><input id="mv-dry" type="checkbox" /> --dry-run</label>
      <p class="text-[11px] text-slate-500">Reclaims free space in <code>yengo-search.db</code>. Rebuild is slow (minutes).</p>
    `,
    button: { id: "mv-go", label: "Run vacuum-db", variant: "info" },
    preview: { id: "mv-preview", label: "Preview" },
  },
  "clean": {
    title: "Clean",
    body: `
      <label class="block text-xs text-slate-400">Target
        <select id="mc-target" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm">
          <option value="">(retention-based)</option>
          <option value="staging">staging</option>
          <option value="state">state</option>
          <option value="logs">logs</option>
          <option value="puzzles-collection">puzzles-collection</option>
          <option value="publish-logs">publish-logs</option>
        </select>
      </label>
      <label class="block text-xs text-slate-400">Retention days
        <input id="mc-days" type="number" min="0" placeholder="(CLI default: 45)" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm font-mono" />
      </label>
      <label class="block text-xs text-slate-400">Dry run
        <select id="mc-dry" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm">
          <option value="">(let CLI decide)</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </label>
    `,
    button: { id: "mc-go", label: "Run clean", variant: "info" },
    preview: { id: "mc-preview", label: "Preview" },
  },
  "rollback": {
    title: "Rollback",
    body: `
      <label class="block text-xs text-slate-400">Run ID <span class="text-rose-400">*</span>
        <input id="mr-run-id" type="text" placeholder="20260505-deadbeef" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm font-mono" />
      </label>
      <label class="block text-xs text-slate-400">Reason <span class="text-rose-400">*</span>
        <input id="mr-reason" type="text" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm" />
      </label>
      <div class="space-y-1.5">
        <label class="flex items-center gap-2 text-xs"><input id="mr-dry" type="checkbox" checked /> --dry-run</label>
        <label class="flex items-center gap-2 text-xs"><input id="mr-yes" type="checkbox" /> --yes (skip prompt)</label>
        <label class="flex items-center gap-2 text-xs"><input id="mr-verify" type="checkbox" /> --verify</label>
      </div>
    `,
    button: { id: "mr-go", label: "Run rollback", variant: "destructive" },
    preview: { id: "mr-preview", label: "Preview" },
  },
};

function _formatReversible(rev) {
  if (rev === true) return "yes";
  if (rev === false) return "no";
  return String(rev); // "by-audit-trail"
}

function _opsCardTooltip(entry) {
  const scope = (entry.scope || []).join(", ") || "—";
  return `scope: ${scope}\nreversible: ${_formatReversible(entry.reversible)}`;
}

async function _fetchOpsCatalog() {
  // Returns the raw list of catalog entries, or [] if the cockpit is offline /
  // the CLI errors. The Operations page falls back to the hardcoded layout
  // when the catalog is empty so an offline backend never wipes the page.
  try {
    const res = await fetch("/api/ops/catalog");
    if (!res.ok) return [];
    const payload = await res.json();
    const entries = Array.isArray(payload?.raw) ? payload.raw : [];
    return entries;
  } catch {
    return [];
  }
}

// Theme 16c: cross-cutting typed-confirm guard. A button declared
// `reversible: false && preview_supported: false` in the catalog must
// always present a typed-confirm dialog before its handler runs — no
// matter which view hosts it, no matter which event listener wired the
// click. The capture-phase listener intercepts before any bubble-phase
// handler fires and re-dispatches the click only after the operator
// types the verb. Marker on the element keeps re-dispatch from looping.
let _opsCatalogCache = null;
let _opsCatalogGuardInstalled = false;

async function _ensureOpsCatalogGuard() {
  if (_opsCatalogGuardInstalled) return _opsCatalogCache || [];
  _opsCatalogGuardInstalled = true;
  _opsCatalogCache = await _fetchOpsCatalog();
  document.addEventListener("click", _opsCatalogConfirmGuard, true); // capture
  return _opsCatalogCache;
}

async function _opsCatalogConfirmGuard(ev) {
  const btn = ev.target?.closest?.("[data-op]");
  if (!btn) return;
  if (btn.dataset.opsConfirmed === "yes") return; // user already cleared
  const op = btn.dataset.op;
  const catalog = _opsCatalogCache || [];
  const entry = catalog.find((e) => e.op === op);
  if (!entry) return; // unknown op → no enforcement
  // Strict criterion (acceptance criterion verbatim):
  // "a button declared `reversible: false` and `preview_supported: false`
  //  always presents a typed-confirm dialog regardless of which view hosts it."
  if (!(entry.reversible === false && entry.preview_supported === false)) return;

  // Block the original handler from seeing this event.
  ev.stopImmediatePropagation();
  ev.preventDefault();

  // Verb for typed confirm — first whitespace-delimited token of the op.
  // ("run --fresh" → "run", "inventory fix" → "inventory")
  const verb = op.split(/\s+/)[0];
  const ok = await confirmDialog({
    title: `Confirm ${op}`,
    body: `${entry.summary}\n\nScope: ${(entry.scope || []).join(", ") || "—"}\n` +
          `Reversible: ${_formatReversible(entry.reversible)}\n` +
          `Preview supported: ${entry.preview_supported ? "yes" : "no"}`,
    verb,
  });
  if (!ok) return;

  // Re-fire the click; capture handler short-circuits via the marker.
  btn.dataset.opsConfirmed = "yes";
  btn.click();
  // Reset for the next interaction so a future click re-prompts.
  setTimeout(() => { delete btn.dataset.opsConfirmed; }, 0);
}

async function renderMaintenance() {
  const root = $("#view-maintenance");
  // Theme 16b: catalog is fetched first so a backend re-classification (e.g.,
  // moving "clean" from maintenance → destructive) reshapes the page without
  // a coordinated cockpit release. Cards we know how to render are placed
  // by `entry.section`; entries with no card spec are skipped silently —
  // the catalog can carry CLI-only ops (e.g., enable-adapter) without
  // forcing a UI surface for each one.
  const catalog = await _ensureOpsCatalogGuard();
  const byOp = Object.fromEntries(catalog.map((e) => [e.op, e]));

  const cardForOp = (op) => {
    const spec = OPS_CARD_SPECS[op];
    const entry = byOp[op];
    if (!spec || !entry) return "";
    return maintCard({
      ...spec,
      op,
      group: entry.section,
      tooltip: _opsCardTooltip(entry),
      preview: entry.preview_supported ? spec.preview : undefined,
      button: {
        ...spec.button,
        // destructive flag is catalog-driven so 16c's typed-confirm logic can
        // key off `data-destructive` everywhere consistently.
        destructive: entry.section === "destructive",
        // override variant so destructive pill colour matches the section.
        variant: entry.section === "destructive" ? "destructive" : (spec.button.variant || "info"),
      },
    });
  };

  // Group renderable cards by catalog section. Order within each section
  // follows OPS_CARD_SPECS declaration order for a stable layout.
  const renderableOps = Object.keys(OPS_CARD_SPECS).filter((op) => byOp[op]);
  const cardsBySection = { maintenance: [], destructive: [] };
  for (const op of renderableOps) {
    const section = byOp[op].section;
    if (cardsBySection[section]) cardsBySection[section].push(cardForOp(op));
  }

  root.innerHTML = `
    ${viewHeader("Operations", {
      subtext: "grouped by blast radius — diagnose first, mutate second, destroy last",
    })}
    ${helpCallout("help-operations", {
      title: "Reading the blast-radius taxonomy",
      bodyHtml: `
        <p>Every action on this page is classified by what it touches and
        whether it can be undone. The grouping is data-driven from
        <code>ops catalog --json</code> — sections, Preview affordances, and
        typed-confirm gates are all derived from one source of truth in
        <code>backend/puzzle_manager/models/ops_catalog.py</code>.</p>
        <ul class="help-callout-list">
          <li><strong>vacuum-db</strong>: compact <code>yengo-search.db</code>
            (the browser-shipped index). <code>--rebuild</code> reconstructs
            it from the published corpus. Reversible.</li>
          <li><strong>clean</strong>: remove <code>.pm-runtime/</code>
            staging / logs / runtime-state by target. Reversible (no
            published data is touched).</li>
          <li><strong>rollback</strong>: <em>destructive</em> — removes a
            published run's puzzles from the corpus + search DB. Recoverable
            only by replaying the publish log. Always requires a typed-verb
            confirm.</li>
          <li><strong>inventory fix</strong>: deletes orphan SGFs / DB rows
            flagged by <code>inventory --check</code>. Irreversible. Always
            preview first.</li>
          <li><strong>run --fresh</strong>: wipes the active source's
            ingest DB + runtime state before running. Forces a full
            re-ingest of every puzzle.</li>
        </ul>
        <p class="help-callout-foot">Buttons in the rose-fenced
        <em>Destructive</em> section all require typed confirmation. Buttons
        with a Preview button are guaranteed safe to inspect — Preview is
        a read-only dry-run that returns the impact set without writing.</p>
      `,
    })}
    <div id="maint-error" class="mb-3"></div>

    <!-- ===== Diagnostics (read-only) =================================== -->
    <section data-ops-group="diagnostics" class="ops-group ops-group--diagnostics mb-6">
      <header class="ops-group-header">
        <h3 class="ops-group-title">Diagnostics</h3>
        <span class="ops-group-sub">read-only — look before you leap</span>
      </header>
      <div class="grid lg:grid-cols-3 gap-4">
        <a href="/pipeline" data-internal-nav="pipeline" class="ops-link-card">
          <div class="ops-link-icon"><i data-lucide="activity"></i></div>
          <div>
            <div class="ops-link-title">Active run</div>
            <p class="ops-link-body">Watch the live SSE stream of any in-flight pipeline run.</p>
          </div>
        </a>
        <a href="/logs" data-internal-nav="logs" class="ops-link-card">
          <div class="ops-link-icon"><i data-lucide="scroll-text"></i></div>
          <div>
            <div class="ops-link-title">Stage logs</div>
            <p class="ops-link-body">Tail <code>.pm-runtime/logs/*.log</code> or search the publish-log audit table.</p>
          </div>
        </a>
        <a href="/library" data-internal-nav="library" class="ops-link-card">
          <div class="ops-link-icon"><i data-lucide="layers"></i></div>
          <div>
            <div class="ops-link-title">Library snapshot</div>
            <p class="ops-link-body">Confirm current puzzle counts before clean / rollback / vacuum-db.</p>
          </div>
        </a>
      </div>
    </section>

    <!-- ===== Maintenance (reversible) ================================== -->
    <section data-ops-group="maintenance" class="ops-group ops-group--maintenance mb-6">
      <header class="ops-group-header">
        <h3 class="ops-group-title">Maintenance</h3>
        <span class="ops-group-sub">reversible — safe to dry-run, safe to retry</span>
      </header>
      <div class="grid lg:grid-cols-2 gap-4">
        ${cardsBySection.maintenance.join("\n")}
      </div>
    </section>

    <!-- ===== Destructive (irreversible) ================================ -->
    <section data-ops-group="destructive" class="ops-group ops-group--destructive">
      <header class="ops-group-header ops-group-header--destructive">
        <div class="flex items-center gap-2">
          <i data-lucide="alert-triangle" class="ops-warn-icon"></i>
          <h3 class="ops-group-title ops-group-title--destructive">Destructive</h3>
        </div>
        <span class="ops-group-sub ops-group-sub--destructive">irreversible — dry-run first, type to confirm</span>
      </header>
      <div class="grid lg:grid-cols-2 gap-4">
        ${cardsBySection.destructive.join("\n")}
      </div>
    </section>

    <!-- ===== Pipeline Config (Theme 7d) ================================= -->
    <section id="pipeline-config-section" class="mt-6"
             data-pipeline-config></section>
  `;

  // Wire each rendered button defensively — a card is absent when its
  // catalog row is missing or its op was re-classified out of the renderable
  // section set, so guard every getElementById.
  const wire = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener("click", fn); };

  wire("mv-go", (e) => startMaintenance("/api/vacuum-db", readVacuumForm(), "vacuum-db", e.currentTarget));
  wire("mc-go", (e) => startMaintenance("/api/clean", readCleanForm(), "clean", e.currentTarget));
  _decorateCleanTargets();
  wire("mr-go", async (e) => {
    const originBtn = e.currentTarget;
    const body = readRollbackForm();
    if (!body.reason) { toast("warn", "rollback reason is required"); return; }
    if (!body.run_id) { toast("warn", "run ID is required"); return; }
    const ok = await confirmDialog({
      title: "Confirm rollback",
      body: body.dry_run
        ? `Dry-run: simulate rollback of run ${body.run_id}.`
        : `Permanently roll back run ${body.run_id}. This is destructive.`,
      verb: "rollback",
    });
    if (!ok) return;
    startMaintenance("/api/rollback", body, "rollback", originBtn);
  });

  // Theme 1e: Preview buttons. Each opens the impact modal against the
  // GET /api/<op>/preview endpoint; "Run for real" inside the modal hands
  // off to the same startMaintenance() path, with dry_run forced false.
  // Theme 16b: catalog drives whether a card has a Preview button (via
  // entry.preview_supported) — if absent, the wire is a no-op.
  wire("mv-preview", () => {
    const params = _previewQueryFromVacuum();
    openPreviewModal({
      op: "vacuum-db",
      previewUrl: `/api/vacuum-db/preview?${params}`,
      runUrl: "/api/vacuum-db",
      buildRunBody: () => ({ ...readVacuumForm(), dry_run: false }),
      verb: "vacuum-db",
      originBtn: $("#mv-go"),
    });
  });

  wire("mc-preview", () => {
    const params = _previewQueryFromClean();
    openPreviewModal({
      op: "clean",
      previewUrl: `/api/clean/preview?${params}`,
      runUrl: "/api/clean",
      buildRunBody: () => ({ ...readCleanForm(), dry_run: false }),
      verb: "clean",
      originBtn: $("#mc-go"),
    });
  });

  wire("mr-preview", () => {
    const body = readRollbackForm();
    if (!body.run_id) { toast("warn", "run ID is required"); return; }
    if (!body.reason) { toast("warn", "rollback reason is required"); return; }
    const params = _previewQueryFromRollback();
    openPreviewModal({
      op: "rollback",
      previewUrl: `/api/rollback/preview?${params}`,
      runUrl: "/api/rollback",
      buildRunBody: () => ({ ...readRollbackForm(), dry_run: false }),
      verb: "rollback",
      originBtn: $("#mr-go"),
      confirmRun: () => confirmDialog({
        title: "Confirm rollback",
        body: `Permanently roll back run ${body.run_id}. This is destructive.`,
        verb: "rollback",
      }),
    });
  });

  if (window.lucide?.createIcons) window.lucide.createIcons();
  _renderPipelineConfigSection();
}

// Theme 7d: pipeline-config show + dotted-path set, presented as read-only
// JSON pre + a small "Edit key" form. Stays presentation-only — every change
// round-trips through `pipeline-config set --json`.
function _renderPipelineConfigSection() {
  const section = document.getElementById("pipeline-config-section");
  if (!section) return;
  section.innerHTML = `
    <div class="rounded border border-slate-200 dark:border-slate-700 p-4"
         data-pipeline-config-card>
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-base font-semibold">Pipeline config</h3>
        <button type="button" data-pipeline-config-refresh
                class="px-2 py-1 text-xs rounded border">Refresh</button>
      </div>
      <pre class="text-xs overflow-auto bg-slate-50 dark:bg-slate-900 p-2 rounded"
           data-pipeline-config-show>(loading…)</pre>
      <form class="mt-3 flex flex-wrap items-end gap-2"
            data-pipeline-config-set-form>
        <label class="text-xs">
          <div class="text-slate-500">Dotted key</div>
          <input type="text" placeholder="batch.size"
                 class="border rounded px-2 py-1 w-48"
                 data-pipeline-config-set-key>
        </label>
        <label class="text-xs">
          <div class="text-slate-500">Value (JSON or string)</div>
          <input type="text" placeholder="4000"
                 class="border rounded px-2 py-1 w-40"
                 data-pipeline-config-set-value>
        </label>
        <button type="submit"
                class="px-3 py-1 text-xs rounded bg-blue-600 text-white"
                data-pipeline-config-set-apply>Apply</button>
      </form>
      <div class="mt-2 text-xs" data-pipeline-config-result></div>
    </div>
  `;
  const pre = section.querySelector("[data-pipeline-config-show]");
  const refresh = section.querySelector("[data-pipeline-config-refresh]");
  const form = section.querySelector("[data-pipeline-config-set-form]");
  const result = section.querySelector("[data-pipeline-config-result]");

  const reload = async () => {
    try {
      const r = await fetch("/api/pipeline-config");
      const j = await r.json();
      pre.textContent = JSON.stringify(j.raw?.pipeline ?? j.raw, null, 2);
    } catch (e) { pre.textContent = `error: ${e}`; }
  };
  refresh.addEventListener("click", reload);
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const key = form.querySelector("[data-pipeline-config-set-key]").value.trim();
    const value = form.querySelector("[data-pipeline-config-set-value]").value;
    if (!key) { toast("warn", "key required"); return; }
    const ok = await confirmDialog({
      title: "Apply pipeline-config change",
      body: `Set ${key} = ${value}`,
      verb: "apply",
    });
    if (!ok) return;
    try {
      const r = await fetch("/api/pipeline-config", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ set_pairs: [`${key}=${value}`], force: false }),
      });
      const j = await r.json();
      if (!r.ok) {
        result.textContent = `error: ${JSON.stringify(j.detail || j)}`;
        return;
      }
      result.textContent = j.raw?.message || "applied";
      reload();
    } catch (e) { result.textContent = `error: ${e}`; }
  });
  reload();
}

// ---------- Logs (Slice 5) ----------
//
// Three sub-sections under one nav: stage logs (file list + tail viewer),
// audit (publish-log search), and a pointer to the live SSE log on Pipeline.
// Sub-tabs are persisted in sessionStorage so a tab switch + return lands
// the operator back where they were.

const LOGS_SUBTAB_KEY = "yengo-dashboard:logsSubtab";
const LOGS_DEFAULT_SUBTAB = "stage";
const LOGS_TAIL_DEFAULT = 500;

function _readLogsSubtab() {
  try {
    const v = sessionStorage.getItem(LOGS_SUBTAB_KEY);
    if (v === "stage" || v === "audit" || v === "live") return v;
  } catch { /* ignore */ }
  return LOGS_DEFAULT_SUBTAB;
}

function _writeLogsSubtab(v) {
  try { sessionStorage.setItem(LOGS_SUBTAB_KEY, v); } catch { /* ignore */ }
}

function _formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KiB`;
  return `${(n / 1024 / 1024).toFixed(1)} MiB`;
}

function renderLogs() {
  const root = $("#view-logs");
  const sub = _readLogsSubtab();
  root.innerHTML = `
    ${viewHeader("Logs", { subtext: "read-only investigation" })}
    <nav id="logs-subtabs" role="tablist" class="flex gap-1 mb-4 border-b border-slate-800">
      <button role="tab" data-subtab="stage" class="logs-subtab px-3 py-1.5 text-xs uppercase tracking-wider">Stage logs</button>
      <button role="tab" data-subtab="audit" class="logs-subtab px-3 py-1.5 text-xs uppercase tracking-wider">Audit · publish-log</button>
      <button role="tab" data-subtab="live"  class="logs-subtab px-3 py-1.5 text-xs uppercase tracking-wider">Live run</button>
    </nav>
    <section id="logs-pane-stage" data-pane="stage" class="logs-pane"></section>
    <section id="logs-pane-audit" data-pane="audit" class="logs-pane hidden"></section>
    <section id="logs-pane-live"  data-pane="live"  class="logs-pane hidden"></section>
  `;

  function activate(name) {
    _writeLogsSubtab(name);
    $$("#logs-subtabs button").forEach((b) =>
      b.classList.toggle("active", b.dataset.subtab === name));
    $$(".logs-pane", root).forEach((p) =>
      p.classList.toggle("hidden", p.dataset.pane !== name));
    if (name === "stage") _renderLogsStagePane();
    if (name === "audit") _renderLogsAuditPane();
    if (name === "live")  _renderLogsLivePane();
  }
  $("#logs-subtabs").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-subtab]");
    if (b) activate(b.dataset.subtab);
  });
  activate(sub);
}

async function _renderLogsStagePane() {
  const pane = $("#logs-pane-stage");
  pane.innerHTML = `<div class="text-xs text-slate-500">loading log files…</div>`;
  try {
    const data = await getJSON("/api/logs/stage-files");
    if (!data.files.length) {
      pane.innerHTML = emptyState(
        "No stage logs on disk yet.",
        `The pipeline writes per-day, per-stage logs into <code>${escapeHtml(data.logs_dir)}</code> when a run executes.`,
      );
      return;
    }
    pane.innerHTML = `
      <section id="logs-grep-form" class="rounded-md border border-slate-800 bg-slate-900 p-3 mb-4 space-y-2">
        <div class="grid md:grid-cols-5 gap-2 text-xs">
          <label class="md:col-span-2">Pattern <span class="text-slate-500">(regex; <code>(?i)</code> for case-insensitive)</span>
            <input id="lg-pattern" type="text" placeholder="ERROR|rate-limited" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" />
          </label>
          <label>Stage
            <select id="lg-stage" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1">
              <option value="">any</option>
              <option value="ingest">ingest</option>
              <option value="analyze">analyze</option>
              <option value="publish">publish</option>
              <option value="puzzle_manager">puzzle_manager</option>
            </select>
          </label>
          <label>From <span class="text-slate-500">(YYYY-MM-DD)</span>
            <input id="lg-from" type="text" placeholder="2026-05-01" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" />
          </label>
          <label>To
            <input id="lg-to" type="text" placeholder="2026-05-31" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" />
          </label>
          <label>Limit
            <input id="lg-limit" type="number" min="1" max="5000" value="200" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" />
          </label>
          <div class="flex items-end">
            <button id="lg-go" class="${PILL_VARIANTS.info} hover:brightness-125 text-sm rounded-md px-3 py-1.5">Search</button>
          </div>
        </div>
        <div id="lg-results" class="text-xs"></div>
      </section>
      <div class="grid gap-4 logs-stage-grid">
        <aside class="rounded-md border border-slate-800 bg-slate-900 p-2 max-h-[70vh] overflow-y-auto logs-stage-aside">
          <div class="text-[10px] uppercase tracking-wider text-slate-500 px-2 py-1">${data.files.length} files</div>
          <ul id="stage-files-list" class="text-xs">
            ${data.files.map((f) => `
              <li>
                <button data-file="${escapeHtml(f.name)}"
                        class="stage-file-btn w-full text-left px-2 py-1 rounded hover:bg-slate-800/60 font-mono">
                  <span class="block">${escapeHtml(f.name)}</span>
                  <span class="block text-[10px] text-slate-500">
                    ${escapeHtml(_formatBytes(f.size_bytes))} ·
                    <span data-rel-time="${escapeHtml(f.mtime_iso)}">${relTime(f.mtime_iso)}</span>
                  </span>
                </button>
              </li>`).join("")}
          </ul>
        </aside>
        <div>
          <div class="flex items-center gap-2 mb-2 text-xs">
            <span class="text-slate-500">Tail</span>
            <select id="stage-tail-lines" class="bg-slate-950 border border-slate-700 rounded px-2 py-1 text-xs">
              <option value="100">100</option>
              <option value="500" selected>500</option>
              <option value="2000">2000</option>
              <option value="5000">5000</option>
            </select>
            <span id="stage-tail-meta" class="text-slate-500"></span>
          </div>
          <div id="stage-tail-output" class="log-panel min-h-[60vh]"></div>
        </div>
      </div>
    `;
    $("#stage-files-list").addEventListener("click", (e) => {
      const b = e.target.closest("button.stage-file-btn");
      if (!b) return;
      $$(".stage-file-btn", pane).forEach((x) => x.classList.toggle("active", x === b));
      _loadStageTail(b.dataset.file);
    });
    $("#stage-tail-lines").addEventListener("change", () => {
      const active = $(".stage-file-btn.active", pane);
      if (active) _loadStageTail(active.dataset.file);
    });
    $("#lg-go").addEventListener("click", _runLogsGrep);
    $("#lg-pattern").addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); _runLogsGrep(); }
    });
    // Theme 2c: consume sessionStorage prefill set by the failures-summary
    // card on the Pipeline tab. One-shot: read, clear, auto-search.
    try {
      const raw = sessionStorage.getItem("yengo-dashboard:logsGrepPrefill");
      if (raw) {
        sessionStorage.removeItem("yengo-dashboard:logsGrepPrefill");
        const pre = JSON.parse(raw);
        if (pre?.pattern) {
          $("#lg-pattern").value = pre.pattern;
          if (pre.stage) $("#lg-stage").value = pre.stage;
          _runLogsGrep();
        }
      }
    } catch { /* ignore malformed prefill */ }
  } catch (err) {
    pane.innerHTML = errorBlock("/api/logs/stage-files", err);
  }
}

async function _runLogsGrep() {
  const pattern = $("#lg-pattern").value.trim();
  const out = $("#lg-results");
  if (!pattern) {
    out.innerHTML = `<div class="text-amber-300 px-2 py-1">Pattern is required.</div>`;
    return;
  }
  const params = new URLSearchParams({ pattern });
  const stage = $("#lg-stage").value;
  const from = $("#lg-from").value.trim();
  const to = $("#lg-to").value.trim();
  const limit = $("#lg-limit").value;
  if (stage) params.set("stage", stage);
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  if (limit) params.set("limit", limit);
  out.innerHTML = `<div class="text-slate-500 px-2 py-1">searching…</div>`;
  try {
    const data = await getJSON(`/api/logs/grep?${params.toString()}`);
    const hits = data.raw || [];
    if (!hits.length) {
      out.innerHTML = `<div class="text-slate-500 px-2 py-1">no matches</div>`;
      return;
    }
    out.innerHTML = `
      <table class="w-full text-xs font-mono mt-2">
        <thead class="text-[10px] uppercase tracking-wider text-slate-500">
          <tr>
            <th class="text-left px-2 py-1">File</th>
            <th class="text-right px-2 py-1">Line</th>
            <th class="text-left px-2 py-1">Timestamp</th>
            <th class="text-left px-2 py-1">Snippet</th>
            <th class="px-2 py-1"></th>
          </tr>
        </thead>
        <tbody>
          ${hits.map((h) => {
            const fname = (h.file || "").split("/").pop() || h.file;
            const snippet = (h.text || "").length > 160 ? h.text.slice(0, 160) + "…" : h.text;
            return `
              <tr class="border-t border-slate-800/60 hover:bg-slate-800/40">
                <td class="px-2 py-1 text-slate-300">${escapeHtml(fname)}</td>
                <td class="px-2 py-1 text-right text-slate-400">${escapeHtml(String(h.line_no))}</td>
                <td class="px-2 py-1 text-slate-400">${escapeHtml(h.ts || "—")}</td>
                <td class="px-2 py-1 text-slate-200 max-w-md truncate" title="${escapeHtml(h.text || "")}">${escapeHtml(snippet)}</td>
                <td class="px-2 py-1">
                  <button data-grep-open="${escapeHtml(fname)}" class="lg-open-btn ${PILL_VARIANTS.muted} text-[10px] rounded px-2 py-0.5">Open</button>
                </td>
              </tr>`;
          }).join("")}
        </tbody>
      </table>
      <div class="text-[10px] text-slate-500 px-2 py-1">${hits.length.toLocaleString()} hit${hits.length === 1 ? "" : "s"}</div>
    `;
    out.querySelectorAll("button.lg-open-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const fname = btn.dataset.grepOpen;
        const target = document.querySelector(`button.stage-file-btn[data-file="${fname}"]`);
        if (target) {
          target.click();
          target.scrollIntoView({ block: "nearest" });
        }
      });
    });
  } catch (err) {
    out.innerHTML = errorBlock("/api/logs/grep", err);
  }
}

async function _loadStageTail(filename) {
  const out = $("#stage-tail-output");
  const meta = $("#stage-tail-meta");
  if (!out) return;
  const lines = Number($("#stage-tail-lines")?.value || LOGS_TAIL_DEFAULT);
  out.innerHTML = `<div class="text-xs text-slate-500 px-2 py-1">tailing ${escapeHtml(filename)}…</div>`;
  try {
    const data = await getJSON(`/api/logs/stage-files/${encodeURIComponent(filename)}?lines=${lines}`);
    out.innerHTML = data.lines.map((ln) =>
      `<div class="log-row"><span class="lr-text">${escapeHtml(ln)}</span></div>`,
    ).join("") || `<div class="text-xs text-slate-500 px-2 py-1">file is empty</div>`;
    out.scrollTop = out.scrollHeight;
    if (meta) {
      meta.textContent = data.truncated
        ? `showing last ${data.lines.length.toLocaleString()} of ${data.total_lines.toLocaleString()} lines`
        : `${data.lines.length.toLocaleString()} lines`;
    }
  } catch (err) {
    out.innerHTML = errorBlock(`tail ${filename}`, err);
  }
}

function _renderLogsAuditPane() {
  const pane = $("#logs-pane-audit");
  pane.innerHTML = `
    <section class="rounded-md border border-slate-800 bg-slate-900 p-4 space-y-3">
      <div class="grid md:grid-cols-4 gap-3 text-xs">
        <label>Run ID<input    id="pl-run-id"    type="text" placeholder="20260505-deadbeef" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>Puzzle ID<input id="pl-puzzle-id" type="text" placeholder="abc123def456 (16-hex)" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>Source<input    id="pl-source"    type="text" placeholder="sanderland" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>Trace ID<input  id="pl-trace-id"  type="text" placeholder="a1b2c3d4e5f67890 (16-hex)" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>Date <span class="text-slate-500">(YYYY-MM-DD)</span><input id="pl-date" type="text" placeholder="2026-05-05" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>From<input id="pl-from" type="text" placeholder="2026-05-01" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>To<input   id="pl-to"   type="text" placeholder="2026-05-31" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
        <label>Limit<input id="pl-limit" type="number" min="1" placeholder="50" class="block w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 font-mono" /></label>
      </div>
      <button id="pl-go" class="${PILL_VARIANTS.info} hover:brightness-125 text-sm rounded-md px-3 py-1.5">Search</button>
      <div id="pl-results"></div>
    </section>
  `;
  $("#pl-go").addEventListener("click", runPublishLogSearch);
}

function _renderLogsLivePane() {
  const pane = $("#logs-pane-live");
  pane.innerHTML = `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-6">
      <p class="text-sm text-slate-300 mb-2">Live run output streams via SSE on the
        <a href="/pipeline" data-internal-nav="pipeline" class="text-teal-300 hover:text-teal-200 underline">Pipeline</a>
        tab.</p>
      <p class="text-xs text-slate-500">The log panel there owns its own filters
        (level, stream, search) and stage stepper. This pane links there rather
        than duplicating the SSE subscription.</p>
    </div>
  `;
}

// ---------- History ----------

const stagePill = (s) => {
  const variants = {
    completed: "ok",
    failed:    "error",
    running:   "running",
    skipped:   "muted",
    pending:   "muted",
  };
  return `<span class="pill ${PILL_VARIANTS[variants[s.status] || "neutral"]}" ${s.status === "running" ? `data-pulse="true"` : ""}>
    <span class="glyph"></span>${escapeHtml(s.name)}
    ${s.processed_count ? `<span class="opacity-60 font-mono tabular-nums ml-1">${s.processed_count}</span>` : ""}
  </span>`;
};

function summarizeRuns(runs) {
  const total = runs.length;
  if (total === 0) return null;
  const ok     = runs.filter(r => r.status === "completed").length;
  const failed = runs.filter(r => r.status === "failed").length;
  const lastFail = runs.find(r => r.status === "failed");
  const okPct = ((ok / total) * 100).toFixed(0);
  return { total, ok, failed, okPct, lastFail };
}

// History filter state — persisted across tab switches but not reloads.
const HISTORY_FILTER_KEY = "yengo-dashboard:historyFilter";
function loadHistoryFilter() {
  try {
    const raw = sessionStorage.getItem(HISTORY_FILTER_KEY);
    if (raw) return { q: "", status: "all", failuresOnly: false, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return { q: "", status: "all", failuresOnly: false };
}
function saveHistoryFilter(f) {
  try { sessionStorage.setItem(HISTORY_FILTER_KEY, JSON.stringify(f)); } catch { /* ignore */ }
}
function applyHistoryFilter(runs, f) {
  const q = (f.q || "").trim().toLowerCase();
  return runs.filter(r => {
    if (q && !r.run_id.toLowerCase().includes(q)) return false;
    if (f.status && f.status !== "all" && r.status !== f.status) return false;
    if (f.failuresOnly && !(r.failure_count > 0)) return false;
    return true;
  });
}
let _historyData = null;     // cached /api/runs response
let _historyFilter = null;
let _historySearchTimer = null;

function copyIcon() {
  // 12px SVG copy glyph (no emojis per project convention)
  return `<svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <rect x="5" y="5" width="9" height="9" rx="1.5"/>
    <path d="M3.5 11V3a.5.5 0 0 1 .5-.5h7"/>
  </svg>`;
}

async function copyToClipboard(text, sourceBtn) {
  try {
    await navigator.clipboard.writeText(text);
    if (sourceBtn) {
      const original = sourceBtn.innerHTML;
      sourceBtn.innerHTML = `<span class="text-emerald-300 text-[10px]">copied</span>`;
      setTimeout(() => { sourceBtn.innerHTML = original; }, 1200);
    } else {
      toast("ok", "copied to clipboard");
    }
  } catch {
    toast("error", "clipboard write blocked");
  }
}

function renderHistoryRows(runs) {
  const list = $("#history-rows");
  if (!list) return;
  if (runs.length === 0) {
    list.innerHTML = `<div class="text-sm text-slate-500 italic px-3 py-4">no runs match the filter</div>`;
    return;
  }
  list.innerHTML = runs.map((r) => {
    const failed = r.status === "failed";
    const checked = _runsDiffSelection.has(r.run_id) ? "checked" : "";
    return `
      <div class="rounded-md border border-slate-800 bg-slate-900 p-3
                  ${failed ? 'border-l-2 border-l-rose-500/60' : ''}">
        <div class="flex items-baseline gap-3 flex-wrap">
          <input type="checkbox" class="runs-diff-check accent-teal-500"
                 data-run-id="${escapeHtml(r.run_id)}" ${checked}
                 aria-label="Select ${escapeHtml(r.run_id)} for comparison" />
          <span class="font-mono text-sm">${escapeHtml(r.run_id)}</span>
          <button class="copy-run-id text-slate-500 hover:text-slate-200 transition"
                  data-run-id="${escapeHtml(r.run_id)}"
                  title="Copy run ID" aria-label="Copy run ID ${escapeHtml(r.run_id)}">
            ${copyIcon()}
          </button>
          ${pill(r.status === "completed" ? "ok" : r.status === "failed" ? "error" : "neutral", r.status)}
          <span class="text-xs text-slate-400" data-rel-time="${escapeHtml(r.started_at || "")}">${relTime(r.started_at)}</span>
          ${r.failure_count > 0 ? `<span class="text-xs text-rose-300">${r.failure_count} failure${r.failure_count === 1 ? "" : "s"}</span>` : ""}
        </div>
        <div class="flex gap-2 mt-2 flex-wrap">${r.stages.map(stagePill).join("")}</div>
        <div class="text-xs text-slate-500 font-mono mt-2 truncate" title="Source: run-state JSON at ${escapeHtml(r.state_file)}">${escapeHtml(r.state_file)}</div>
      </div>`;
  }).join("");
  _refreshRunsDiffBar();
}

function refreshHistoryView() {
  if (!_historyData) return;
  const filtered = applyHistoryFilter(_historyData.runs, _historyFilter);
  const counter = $("#history-shown-count");
  if (counter) counter.textContent = `showing ${filtered.length} of ${_historyData.runs.length} (disk: ${_historyData.total})`;
  renderHistoryRows(filtered);
}

// ---------- Theme 9: Run Diff / Compare ----------
const _runsDiffSelection = new Set();

function _refreshRunsDiffBar() {
  const bar = $("#runs-diff-bar");
  if (!bar) return;
  const ids = [..._runsDiffSelection];
  const enabled = ids.length === 2;
  bar.innerHTML = `
    <span class="text-xs text-slate-400">selected: ${ids.length} / 2</span>
    ${ids.map((id) => `<span class="font-mono text-xs px-2 py-0.5 rounded bg-slate-800">${escapeHtml(id)}</span>`).join("")}
    <button id="runs-diff-compare-btn"
            class="ml-auto px-3 py-1 rounded text-xs font-medium ${enabled ? 'bg-teal-600 hover:bg-teal-500 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}"
            ${enabled ? '' : 'disabled'}
            data-runs-diff-compare>Compare runs</button>
    <button class="px-2 py-1 text-xs text-slate-400 hover:text-slate-200"
            data-runs-diff-clear>clear</button>
  `;
}

async function _runRunsDiff(runA, runB) {
  const card = $("#runs-diff-result");
  if (!card) return;
  card.innerHTML = `<div class="text-sm text-slate-400">loading diff…</div>`;
  try {
    const params = new URLSearchParams({ run_a: runA, run_b: runB, max_samples: "20" });
    const resp = await getJSON(`/api/runs/diff?${params.toString()}`);
    const r = resp.raw;
    const sd = r.stats_diff || {};
    const fmtDelta = (n) => (n > 0 ? `+${n}` : String(n));
    card.innerHTML = `
      <div class="rounded-md border border-slate-800 bg-slate-900 p-4">
        <div class="flex items-baseline gap-3 mb-3 flex-wrap">
          <span class="text-xs uppercase tracking-wider text-slate-500">runs-diff</span>
          <span class="font-mono text-sm">${escapeHtml(runA)} → ${escapeHtml(runB)}</span>
        </div>
        <div class="grid grid-cols-3 gap-3 mb-4">
          <div class="rounded bg-slate-950 border border-slate-800 p-3">
            <div class="text-[10px] uppercase text-slate-500">Δ ingested</div>
            <div class="text-xl font-semibold tabular-nums">${fmtDelta(sd.ingested ?? 0)}</div>
          </div>
          <div class="rounded bg-slate-950 border border-slate-800 p-3">
            <div class="text-[10px] uppercase text-slate-500">Δ failed</div>
            <div class="text-xl font-semibold tabular-nums">${fmtDelta(sd.failed ?? 0)}</div>
          </div>
          <div class="rounded bg-slate-950 border border-slate-800 p-3">
            <div class="text-[10px] uppercase text-slate-500">Δ skipped</div>
            <div class="text-xl font-semibold tabular-nums">${fmtDelta(sd.skipped ?? 0)}</div>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3">
          ${_diffColumn("Added", r.added_puzzles, "text-emerald-300")}
          ${_diffColumn("Removed", r.removed_puzzles, "text-rose-300")}
          ${_diffColumn("Common", { count: r.common_count, samples: [] }, "text-slate-300")}
        </div>
      </div>
    `;
  } catch (e) {
    card.innerHTML = errorBlock("/api/runs/diff", e);
  }
}

function _diffColumn(label, bucket, accent) {
  const samples = (bucket && bucket.samples) || [];
  return `
    <div class="rounded bg-slate-950 border border-slate-800 p-3">
      <div class="text-[10px] uppercase text-slate-500">${label}</div>
      <div class="text-xl font-semibold tabular-nums ${accent}">${bucket ? bucket.count : 0}</div>
      ${samples.length ? `<ul class="mt-2 text-xs font-mono text-slate-400 space-y-0.5">${samples.map((s) => `<li class="truncate">${escapeHtml(s)}</li>`).join("")}</ul>` : ""}
    </div>
  `;
}

async function renderHistory() {
  const root = $("#view-history");
  root.innerHTML = `<div class="text-slate-400 text-sm">loading runs…</div>`;
  try {
    _historyData = await getJSON("/api/runs?limit=50");
    _historyFilter = loadHistoryFilter();
    if (_historyData.runs.length === 0) {
      root.innerHTML = emptyState("No runs on disk.", "Start one from the Live Run tab.");
      return;
    }
    const sum = summarizeRuns(_historyData.runs);
    root.innerHTML = `
      ${viewHeader("Run History", { metaHtml: `
        <span id="history-shown-count" class="view-header-sub">showing ${_historyData.runs.length} of ${_historyData.runs.length} (disk: ${_historyData.total})</span>
      ` })}
      <div class="grid grid-cols-3 gap-3 mb-5">
        <div class="rounded-md border border-slate-800 bg-slate-900 p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500">Recent runs</div>
          <div class="text-2xl font-semibold tabular-nums mt-1">${sum.total}</div>
          <div class="text-xs text-slate-400 mt-0.5">${sum.ok} ok · ${sum.failed} failed</div>
        </div>
        <div class="rounded-md border border-slate-800 bg-slate-900 p-4">
          <div class="text-[10px] uppercase tracking-wider text-slate-500">Success rate</div>
          <div class="text-2xl font-semibold tabular-nums mt-1 ${sum.okPct >= 90 ? "text-emerald-300" : sum.okPct >= 70 ? "text-orange-300" : "text-rose-300"}">${sum.okPct}%</div>
          <div class="text-xs text-slate-400 mt-0.5">across ${sum.total} runs</div>
        </div>
        <div class="rounded-md border border-slate-800 bg-slate-900 p-4"
             title="Computed only from the most recent ${_historyData.runs.length} run-state files loaded into this view. Older failures on disk are not considered.">
          <div class="text-[10px] uppercase tracking-wider text-slate-500">Last failure <span class="text-slate-600">(last ${_historyData.runs.length} runs)</span></div>
          ${sum.lastFail ? `
            <div class="text-sm font-mono mt-1 truncate" title="${escapeHtml(sum.lastFail.run_id)}">${escapeHtml(sum.lastFail.run_id)}</div>
            <div class="text-xs text-slate-400 mt-0.5" data-rel-time="${escapeHtml(sum.lastFail.started_at || "")}">${relTime(sum.lastFail.started_at)}</div>
          ` : `
            <div class="text-2xl font-semibold text-emerald-300 mt-1">none</div>
            <div class="text-xs text-slate-400 mt-0.5">in last ${_historyData.runs.length} runs</div>
          `}
        </div>
      </div>

      <div id="failures-summary-card" class="mb-5"></div>

      <div id="runs-diff-bar"
           class="flex items-center gap-2 mb-3 px-2 py-2 rounded border border-slate-800 bg-slate-900/40"
           data-runs-diff-bar></div>
      <div id="runs-diff-result" class="mb-5"></div>

      <div class="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-2 mb-3">
        <input id="history-q" type="search" placeholder="filter by run_id substring…"
               value="${escapeHtml(_historyFilter.q)}"
               class="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-teal-500/50" />
        <select id="history-status" class="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm">
          <option value="all">all statuses</option>
          <option value="running">running</option>
          <option value="completed">completed</option>
          <option value="failed">failed</option>
          <option value="cancelled">cancelled</option>
        </select>
        <label class="inline-flex items-center gap-2 text-xs text-slate-300 px-2">
          <input id="history-failures-only" type="checkbox" ${_historyFilter.failuresOnly ? "checked" : ""} />
          failures only
        </label>
      </div>

      <div id="history-rows" class="space-y-2"></div>
    `;
    $("#history-status").value = _historyFilter.status;
    refreshHistoryView();
    // Wire filter inputs.
    $("#history-q").addEventListener("input", (e) => {
      clearTimeout(_historySearchTimer);
      _historySearchTimer = setTimeout(() => {
        _historyFilter.q = e.target.value;
        saveHistoryFilter(_historyFilter);
        refreshHistoryView();
      }, 150);
    });
    $("#history-status").addEventListener("change", (e) => {
      _historyFilter.status = e.target.value;
      saveHistoryFilter(_historyFilter);
      refreshHistoryView();
    });
    $("#history-failures-only").addEventListener("change", (e) => {
      _historyFilter.failuresOnly = e.target.checked;
      saveHistoryFilter(_historyFilter);
      refreshHistoryView();
    });
    _loadFailuresSummaryCard();
  } catch (e) { root.innerHTML = errorBlock("/api/runs", e); }
}

// ---------- Theme 2b: Top failure modes card ----------
//
// Renders an aggregated digest of RunState.failures[] for the most recent N
// runs above the History list. Each row is a (stage, error_type) bucket from
// the pipeline's `status --failures-summary` CLI; clicking jumps to the Logs
// view filtered to that error pattern (Theme 2c).

async function _loadFailuresSummaryCard() {
  const root = document.getElementById("failures-summary-card");
  if (!root) return;
  const last = 10;
  root.innerHTML = `<div class="text-xs text-slate-500">loading top failure modes…</div>`;
  let groups;
  try {
    const resp = await getJSON(`/api/status/failures-summary?last=${last}`);
    groups = Array.isArray(resp?.raw) ? resp.raw : [];
  } catch (e) {
    root.innerHTML = errorBlock("/api/status/failures-summary", e);
    return;
  }
  if (groups.length === 0) {
    root.innerHTML = `
      <div class="rounded-md border border-slate-800 bg-slate-900 p-4">
        <div class="text-[11px] uppercase tracking-wider text-slate-500">Top failure modes (last ${last} runs)</div>
        <div class="text-sm text-emerald-300 mt-2">No failures recorded.</div>
      </div>`;
    return;
  }
  const rows = groups.map((g) => {
    const sample = g.sample_message ? escapeHtml(g.sample_message).slice(0, 160) : "";
    const ids = (g.sample_puzzle_ids || []).map(escapeHtml).join(", ");
    return `
      <button type="button"
              class="failures-row w-full text-left grid grid-cols-[6rem_1fr_auto] gap-3 items-center px-3 py-2 rounded hover:bg-slate-800/60 focus:outline-none focus:ring-1 focus:ring-teal-500/50"
              data-stage="${escapeHtml(g.stage)}"
              data-error-type="${escapeHtml(g.error_type)}"
              title="Click to search logs for ${escapeHtml(g.error_type)}">
        <span class="text-[11px] uppercase tracking-wider text-slate-400 font-mono">${escapeHtml(g.stage)}</span>
        <span class="min-w-0">
          <span class="text-sm text-slate-100 font-mono">${escapeHtml(g.error_type)}</span>
          ${sample ? `<span class="block text-xs text-slate-500 truncate">${sample}</span>` : ""}
          ${ids ? `<span class="block text-[11px] text-slate-600 truncate font-mono">ids: ${ids}</span>` : ""}
        </span>
        <span class="text-sm tabular-nums text-rose-300">×${g.count}</span>
      </button>`;
  }).join("");
  root.innerHTML = `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-3">
      <div class="flex items-center justify-between mb-2 px-1">
        <div class="text-[11px] uppercase tracking-wider text-slate-500">Top failure modes (last ${last} runs)</div>
        <div class="text-[11px] text-slate-600">click a row to search logs</div>
      </div>
      <div class="divide-y divide-slate-800/60">${rows}</div>
    </div>`;
  // Theme 2c: row click → navigate to /logs with grep prefilled.
  root.querySelectorAll(".failures-row").forEach((btn) => {
    btn.addEventListener("click", () => {
      const stage = btn.dataset.stage || "";
      const errType = btn.dataset.errorType || "";
      try {
        sessionStorage.setItem(
          "yengo-dashboard:logsGrepPrefill",
          JSON.stringify({ pattern: errType, stage, ts: Date.now() }),
        );
      } catch { /* sessionStorage may be disabled */ }
      // Use the same internal-nav path the rest of the app uses.
      const a = document.createElement("a");
      a.href = "/logs";
      a.dataset.internalNav = "logs";
      a.click();
      // Fallback if anchor click was swallowed.
      if (location.pathname !== "/logs") location.href = "/logs";
    });
  });
}

// ---------- Theme 13b: Activity timeline ----------
//
// Unified view of run/maintenance/publish events from `activity --json`.
// Kind-filter chips drive the CLI's --kinds flag so the cockpit never
// reinterprets the merge order; that lives in
// `backend.puzzle_manager.models.activity.compute_activity`.

const _ACTIVITY_KIND_VARIANTS = {
  run:         "info",
  maintenance: "warn",
  publish:     "ok",
};
let _activityKinds = new Set(["run", "maintenance", "publish"]);

function _activityRow(ev) {
  const variant = _ACTIVITY_KIND_VARIANTS[ev.kind] || "neutral";
  return `
    <div class="rounded-md border border-slate-800 bg-slate-900 p-3">
      <div class="flex items-baseline gap-3 flex-wrap">
        ${pill(variant, ev.kind)}
        <span class="font-mono text-sm">${escapeHtml(ev.subject_id)}</span>
        <span class="text-xs text-slate-400" data-rel-time="${escapeHtml(ev.ts || "")}">${relTime(ev.ts)}</span>
        <span class="text-[11px] text-slate-500 font-mono">by ${escapeHtml(ev.actor)}</span>
      </div>
      <div class="text-sm text-slate-200 mt-1.5">${escapeHtml(ev.summary)}</div>
    </div>`;
}

async function _loadActivityRows() {
  const list = $("#activity-rows");
  if (!list) return;
  const kinds = [..._activityKinds];
  if (kinds.length === 0) {
    list.innerHTML = `<div class="text-sm text-slate-500 italic px-3 py-4">No event kinds selected.</div>`;
    return;
  }
  list.innerHTML = `<div class="text-slate-400 text-sm">loading activity…</div>`;
  let raw;
  try {
    const params = new URLSearchParams({ limit: "100", kinds: kinds.join(",") });
    const resp = await getJSON(`/api/activity?${params.toString()}`);
    raw = Array.isArray(resp?.raw) ? resp.raw : [];
  } catch (e) {
    list.innerHTML = errorBlock("/api/activity", e);
    return;
  }
  if (raw.length === 0) {
    list.innerHTML = emptyState(
      "No activity yet.",
      "Run the pipeline or perform a maintenance op (clean / rollback / vacuum-db) to populate the timeline.",
    );
    return;
  }
  list.innerHTML = raw.map(_activityRow).join("");
  refreshRelTimes(list);
  if (window.lucide) window.lucide.createIcons({ container: list });
}

// Theme 8a: Daily Challenge view (read-only). Renders rolling-window
// status badge + recent schedule rows table. Calendar + mutation actions
// arrive in later 8 slices.
async function renderDaily() {
  const root = $("#view-daily");
  root.innerHTML = `
    ${viewHeader("Daily", { subtext: "rolling-window status + generated schedule rows" })}
    <section id="daily-status-section" class="mb-4"
             data-daily-status>(loading status…)</section>
    <section id="daily-list-section"
             data-daily-list>(loading schedule…)</section>
  `;
  try {
    const [s, l] = await Promise.all([
      fetch("/api/daily/status?window_days=30").then((r) => r.json()),
      fetch("/api/daily/list").then((r) => r.json()),
    ]);
    _renderDailyStatusBlock(s.raw || {});
    _renderDailyListBlock(l.raw || {});
  } catch (e) {
    root.querySelector("[data-daily-status]").innerHTML = errorBlock("/api/daily", e);
  }
}

function _renderDailyStatusBlock(raw) {
  const host = document.querySelector("[data-daily-status]");
  if (!host) return;
  const expected = raw.expected_dates ?? 0;
  const generated = raw.generated_dates ?? 0;
  const missing = (raw.missing_dates || []).length;
  const stale = (raw.stale_dates || []).length;
  const healthy = missing === 0 && stale === 0;
  const badge = healthy
    ? `<span class="px-2 py-1 text-xs rounded bg-emerald-500/20 text-emerald-300">healthy</span>`
    : (missing > 0
        ? `<span class="px-2 py-1 text-xs rounded bg-rose-500/20 text-rose-300">${missing} missing</span>`
        : `<span class="px-2 py-1 text-xs rounded bg-amber-500/20 text-amber-300">${stale} stale</span>`);
  host.innerHTML = `
    <div class="rounded border border-slate-200 dark:border-slate-700 p-4"
         data-daily-status-card>
      <div class="flex items-center justify-between">
        <h3 class="text-base font-semibold">Daily status</h3>
        ${badge}
      </div>
      <div class="mt-2 text-sm grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div><span class="text-slate-500">window:</span>
             ${escapeHtml(raw.window?.from || "?")} → ${escapeHtml(raw.window?.to || "?")}</div>
        <div><span class="text-slate-500">expected:</span> ${expected}</div>
        <div><span class="text-slate-500">generated:</span> ${generated}</div>
        <div><span class="text-slate-500">last regen:</span>
             ${escapeHtml(raw.last_regenerated_at || "—")}</div>
      </div>
      ${missing > 0 ? `<details class="mt-2 text-xs">
        <summary>Missing dates (${missing})</summary>
        <pre class="overflow-auto">${escapeHtml((raw.missing_dates || []).join("\n"))}</pre>
      </details>` : ""}
      ${stale > 0 ? `<details class="mt-2 text-xs">
        <summary>Stale dates (${stale})</summary>
        <pre class="overflow-auto">${escapeHtml(JSON.stringify(raw.stale_dates, null, 2))}</pre>
      </details>` : ""}
      ${missing > 0 ? `<div class="mt-3 flex items-center gap-2">
        <button type="button" class="text-xs underline text-sky-600 dark:text-sky-300"
                data-daily-backfill-btn data-window="${raw.window?.days || 30}">Backfill missing</button>
        <span class="text-xs text-slate-500">Generates ${missing} missing date(s) inside one PipelineLock.</span>
      </div>` : ""}
    </div>
  `;
  const btn = host.querySelector("[data-daily-backfill-btn]");
  if (btn) {
    btn.addEventListener("click", () => _runDailyBackfill(parseInt(btn.dataset.window, 10) || 30));
  }
}

async function _runDailyBackfill(window_days) {
  // Theme 8d: preview-then-confirm-then-apply backfill.
  let preview;
  try {
    preview = await postJSON("/api/daily/backfill/preview",
      { window_days, force: false });
  } catch (err) {
    toast("error", `backfill preview failed: ${err.body?.detail?.message || err.message}`);
    return;
  }
  const raw = preview.raw || {};
  const missing = raw.missing_dates || [];
  if (!missing.length) {
    toast("info", "no missing dates");
    return;
  }
  const ok = await confirmDialog({
    title: `Backfill ${missing.length} missing date(s)`,
    body: `Will generate daily challenges for: ${missing.slice(0, 10).join(", ")}` +
          (missing.length > 10 ? ` … and ${missing.length - 10} more` : "") +
          `. This acquires the pipeline lock and may take a while.`,
    verb: "backfill",
  });
  if (!ok) return;
  try {
    const res = await postJSON("/api/daily/backfill/apply",
      { window_days, force: false });
    const r = res.raw || {};
    toast("ok", `backfilled ${r.generated_count || 0} of ${missing.length} date(s)`);
    renderDaily();
  } catch (err) {
    toast("error", `backfill failed: ${err.body?.detail?.message || err.message}`);
  }
}

function _renderDailyListBlock(raw) {
  const host = document.querySelector("[data-daily-list]");
  if (!host) return;
  const rows = raw.rows || [];
  if (!rows.length) {
    host.innerHTML = `<div class="text-sm text-slate-500">No daily schedules found.</div>`;
    return;
  }
  host.innerHTML = `
    <table class="w-full text-sm" data-daily-table>
      <thead><tr class="text-left text-slate-500">
        <th class="py-1">Date</th><th>Technique</th>
        <th class="text-right">Puzzles</th><th>Generated at</th>
        <th class="text-right">Action</th>
      </tr></thead>
      <tbody>
        ${rows.map((r) => `
          <tr class="border-t border-slate-200 dark:border-slate-700">
            <td class="py-1 font-mono text-xs">${escapeHtml(r.date)}</td>
            <td>${escapeHtml(r.technique || "—")}</td>
            <td class="text-right">${r.puzzle_count}</td>
            <td class="text-xs text-slate-500">${escapeHtml(r.generated_at || "")}</td>
            <td class="text-right">
              <button type="button" class="text-xs underline text-sky-600 dark:text-sky-300"
                      data-daily-preview-btn data-date="${escapeHtml(r.date)}">Preview</button>
              <button type="button" class="ml-2 text-xs underline text-rose-600 dark:text-rose-300"
                      data-daily-cancel-btn data-date="${escapeHtml(r.date)}">Cancel</button>
            </td>
          </tr>
        `).join("")}
      </tbody>
    </table>
    <div data-daily-preview-target class="mt-3"></div>
  `;
  host.querySelectorAll("[data-daily-preview-btn]").forEach((btn) => {
    btn.addEventListener("click", () => _runDailyPreview(btn.dataset.date));
  });
  host.querySelectorAll("[data-daily-cancel-btn]").forEach((btn) => {
    btn.addEventListener("click", () => _runDailyCancel(btn.dataset.date));
  });
}

async function _runDailyCancel(date) {
  // Theme 8c: preview-then-confirm-then-apply.
  let preview;
  try {
    preview = await postJSON("/api/daily/cancel/preview",
      { date, force: false });
  } catch (err) {
    toast("error", `cancel preview failed: ${err.body?.detail?.message || err.message}`);
    return;
  }
  const raw = preview.raw || {};
  const ok = await confirmDialog({
    title: `Cancel daily ${date}`,
    body: `Will delete ${raw.dates_affected?.length || 0} schedule row(s) ` +
          `and ${raw.puzzle_rows_affected || 0} puzzle row(s) from ` +
          `daily_schedule + daily_puzzles. This is irreversible.`,
    verb: `cancel ${date}`,
  });
  if (!ok) return;
  try {
    const res = await postJSON("/api/daily/cancel/apply",
      { date, force: false });
    const r = res.raw || {};
    toast("ok", `cancelled ${r.schedule_rows_deleted || 0} day(s), ` +
                `${r.puzzle_rows_affected || 0} puzzle row(s)`);
    renderDaily();
  } catch (err) {
    toast("error", `cancel failed: ${err.body?.detail?.message || err.message}`);
  }
}

async function _runDailyPreview(date) {
  const target = document.querySelector("[data-daily-preview-target]");
  if (!target) return;
  target.innerHTML = `<div class="text-xs text-slate-500">loading preview for ${escapeHtml(date)}…</div>`;
  try {
    const res = await getJSON(`/api/daily/preview?date=${encodeURIComponent(date)}`);
    const raw = res.raw || {};
    const ch = raw.challenge;
    if (!ch) {
      target.innerHTML = `<div class="text-sm text-slate-500">No challenge would be generated for ${escapeHtml(date)} (db_exists=${raw.db_exists}).</div>`;
      return;
    }
    const std = ch.standard || {};
    target.innerHTML = `
      <div class="rounded border border-slate-300 dark:border-slate-700 p-3 text-sm" data-daily-preview-card>
        <div class="font-semibold mb-1">Preview: ${escapeHtml(date)}</div>
        <div class="text-xs text-slate-500">Read-only dry-run — nothing was written.</div>
        <dl class="grid grid-cols-[8rem_1fr] gap-y-1 text-xs mt-2">
          <dt class="text-slate-500">Technique</dt><dd>${escapeHtml(std.technique_of_day || "—")}</dd>
          <dt class="text-slate-500">Standard total</dt><dd>${std.total ?? 0}</dd>
          <dt class="text-slate-500">Version</dt><dd>${escapeHtml(ch.version || "")}</dd>
          <dt class="text-slate-500">By-tag</dt><dd>${Object.keys(ch.by_tag || {}).length} tag(s)</dd>
        </dl>
      </div>`;
  } catch (err) {
    target.innerHTML = `<div class="text-sm text-rose-500">preview failed: ${escapeHtml(err.body?.detail?.message || err.message || String(err))}</div>`;
  }
}

async function renderActivity() {
  const root = $("#view-activity");
  const chips = ["run", "maintenance", "publish"].map((k) => {
    const on = _activityKinds.has(k);
    const cls = on
      ? "bg-teal-500/15 text-teal-200 ring-teal-500/40"
      : "bg-slate-900 text-slate-500 ring-slate-700";
    return `<button type="button" data-kind="${k}"
                    class="activity-chip px-2.5 py-1 rounded-full text-xs font-mono ring-1 ${cls}"
                    aria-pressed="${on}">${k}</button>`;
  }).join("");
  root.innerHTML = `
    ${viewHeader("Activity", { subtext: "Unified timeline of run, maintenance, and publish events." })}
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <span class="text-[11px] uppercase tracking-wider text-slate-500">filter</span>
      ${chips}
    </div>
    <div id="activity-rows" class="grid gap-2"></div>`;
  root.querySelectorAll(".activity-chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      const k = btn.dataset.kind;
      if (_activityKinds.has(k)) _activityKinds.delete(k); else _activityKinds.add(k);
      renderActivity();
    });
  });
  await _loadActivityRows();
}

// ---------- Lock release (from alarm bar action) ----------

async function tryReleaseLock() {
  let status;
  try { status = await getJSON("/api/lock"); } catch { return; }
  if (!status?.raw?.locked) { toast("info", "lock is already free"); return; }
  const ok = await confirmDialog({
    title: "Release config lock",
    body: `Holder pid: ${status.raw.holder_pid ?? "(unknown)"}. ` +
          `If the normal release fails the cockpit will offer --force.`,
    verb: "release",
  });
  if (!ok) return;
  try {
    let res = await postJSON("/api/lock/release", { force: false });
    if (!res.ok) {
      const okForce = await confirmDialog({
        title: "Force-release lock",
        body: `Normal release failed (rc=${res.returncode}). Force-release will override the holder process. ${res.stderr || res.stdout || ""}`.trim(),
        verb: "force",
      });
      if (!okForce) return;
      res = await postJSON("/api/lock/release", { force: true });
    }
    toast(res.ok ? "ok" : "error", res.ok ? "lock released" : `release failed (rc=${res.returncode})`);
  } catch (err) {
    toast("error", `release errored: ${err.body?.detail || err.message || err}`);
  } finally {
    masterTick();
  }
}

// ---------- Click delegation (adapter actions, alarm-bar buttons) ----------

// Theme 9: runs-diff selection (history page checkboxes).
document.addEventListener("change", (e) => {
  const cb = e.target.closest("input.runs-diff-check");
  if (!cb) return;
  const id = cb.dataset.runId;
  if (!id) return;
  if (cb.checked) {
    if (_runsDiffSelection.size >= 2) {
      cb.checked = false;
      toast("warn", "select exactly 2 runs to compare");
      return;
    }
    _runsDiffSelection.add(id);
  } else {
    _runsDiffSelection.delete(id);
  }
  _refreshRunsDiffBar();
});

document.addEventListener("click", async (e) => {
  // History row: click-to-copy run_id
  const copyBtn = e.target.closest("button.copy-run-id");
  if (copyBtn) { copyToClipboard(copyBtn.dataset.runId, copyBtn); return; }

  // Theme 9: runs-diff Compare / clear buttons.
  const cmpBtn = e.target.closest("[data-runs-diff-compare]");
  if (cmpBtn && !cmpBtn.disabled) {
    const ids = [..._runsDiffSelection];
    if (ids.length === 2) await _runRunsDiff(ids[0], ids[1]);
    return;
  }
  const clrBtn = e.target.closest("[data-runs-diff-clear]");
  if (clrBtn) {
    _runsDiffSelection.clear();
    refreshHistoryView();
    const card = $("#runs-diff-result");
    if (card) card.innerHTML = "";
    return;
  }

  // Slice 5: in-app cross-tab links (e.g. Operations → Logs/Audit) must
  // route via showTab + pushState so we don't trigger a full page reload.
  const internalNav = e.target.closest("a[data-internal-nav]");
  if (internalNav) {
    e.preventDefault();
    showTab(internalNav.dataset.internalNav);
    return;
  }

  // Alarm-bar release-lock action
  const alarmBtn = e.target.closest("button[data-action='release-lock']");
  if (alarmBtn) { tryReleaseLock(); return; }

  // Status-strip "Open Live Run" link → switch to Pipeline tab AND scroll
  // the run section into view + briefly highlight. Without the explicit
  // scroll the user already on Pipeline would see no visible feedback.
  const openRun = e.target.closest("a[data-action='open-run']");
  if (openRun) {
    e.preventDefault();
    showTab("pipeline");
    const runView = $("#view-run");
    if (runView) {
      runView.scrollIntoView({ behavior: "smooth", block: "start" });
      runView.classList.add("flash-highlight");
      setTimeout(() => runView.classList.remove("flash-highlight"), 1200);
    }
    return;
  }

  // Maintenance card "View live →" link → switch tab + (re)attach SSE.
  const liveLink = e.target.closest(".view-live");
  if (liveLink) {
    const handle = liveLink.dataset.handle;
    showTab("run");
    if (handle && _activeHandle !== handle) {
      // Different run since the maint card fired — re-subscribe so the log
      // panel reflects the historical handle the operator clicked, not the
      // one currently streaming.
      resetLogState();
      attachStream(handle);
    }
    return;
  }

  // Status strip (bottom) → open System dialog. Action buttons inside the strip
  // (release-lock, "Open Live Run") have their own handlers above; we only open
  // the dialog when the click landed on bare strip surface.
  const stripHit = e.target.closest("#status-strip");
  if (stripHit && !e.target.closest(".strip-action")) {
    paintSystemDialog();
    $("#system-dialog").showModal();
    return;
  }

  // Top-header system chip → same target as the bottom strip (single dialog).
  const chipHit = e.target.closest("#system-chip");
  if (chipHit) {
    paintSystemDialog();
    $("#system-dialog").showModal();
    return;
  }

  // Adapter row actions
  const btn = e.target.closest("button[data-act]");
  if (!btn) return;
  const act = btn.dataset.act;
  const source = btn.dataset.source;
  if (act === "reset-ingest") {
    await openIngestStateResetModal(source);
    return;
  }
  if (act === "enable") {
    btn.disabled = true;
    const original = btn.textContent;
    btn.textContent = "…";
    try {
      const res = await postJSON("/api/adapter/enable", { adapter_id: source });
      if (res.ok) {
        // Re-render immediately so the row gets its lime "active" pill and
        // the action button collapses to the disabled "active" stub. Going
        // through a setTimeout here would flicker the text back to "Enable"
        // for ~1.5s before the new state lands.
        toast("ok", `${source} enabled`);
        await renderAdapters();
      } else {
        btn.textContent = "× failed";
        btn.title = (res.stderr || res.stdout || "").slice(0, 200);
        toast("error", `${source} enable failed (rc=${res.returncode})`);
        setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 2500);
      }
    } catch (err) {
      btn.textContent = "× error";
      toast("error", `enable errored: ${err.body?.detail || err.message || err}`);
      setTimeout(() => { btn.textContent = original; btn.disabled = false; }, 2500);
    }
    return;
  }
  const payload = { source };
  if (act === "ingest") payload.stage = "ingest";
  // W4.2: per-row Run / Ingest used to fire instantly. The implicit
  // --source-override path made it easy to clobber the active adapter by
  // accident. Require a typed-verb confirm naming the source + stage.
  const stageLabel = act === "ingest" ? "ingest stage" : "full pipeline";
  const overrideNote = (_activeAdapter && source !== _activeAdapter)
    ? ` This will auto-pass --source-override (active is '${_activeAdapter}').`
    : "";
  const ok = await confirmDialog({
    title: `Run ${stageLabel} on ${source}?`,
    body: `Starts the ${stageLabel} for source '${source}'.${overrideNote} You can monitor and cancel from the Pipeline tab.`,
    verb: source,
  });
  if (!ok) return;
  // Auto-pass --source-override when the chosen source disagrees with the
  // active adapter recorded in sources.json. The pipeline rejects mismatches
  // by design; the cockpit makes the override explicit and surfaces it via
  // a toast so the operator knows what just happened.
  if (_activeAdapter && source !== _activeAdapter) {
    payload.source_override = true;
    toast("warn", `auto-passed --source-override (active is '${_activeAdapter}')`);
  }
  showTab("run");
  await startRun(payload);
});

// ---------- Sidebar nav plumbing (2026 redesign) ----------
//
// Sidebar maps 4 nav items → "compound" views (multiple sections shown
// stacked under one nav button). The 5 legacy view IDs (overview, adapters,
// run, maintenance, history) remain in the DOM so the existing render
// functions don't need to change.
//
// Library    = overview + adapters       (KPIs above source list)
// Pipeline   = run + history             (active run above past runs)
// Operations = maintenance               (single view)
// Guide      = guide                     (markdown docs viewer)

// Legacy hash names that should be remapped to current nav names. Kept here
// (rather than as a one-shot rewrite at boot) so deep links shared during the
// rename window keep working.
const LEGACY_NAV_ALIASES = { workshop: "operations" };

const NAV_VIEWS = {
  library:    ["overview", "adapters"],
  pipeline:   ["run", "history"],
  activity:   ["activity"],
  daily:      ["daily"],
  operations: ["maintenance"],
  logs:       ["logs"],
  guide:      ["guide"],
};

const RENDERERS = {
  overview:    renderOverview,
  adapters:    renderAdapters,
  run:         renderLiveRun,
  activity:    renderActivity,
  daily:       renderDaily,
  maintenance: renderMaintenance,
  history:     renderHistory,
  logs:        renderLogs,
  guide:       renderGuide,
};

// Back-compat: legacy code calls showTab("run") to focus the live-run view.
// Translate single view names to their owning nav section.
const VIEW_TO_NAV = Object.fromEntries(
  Object.entries(NAV_VIEWS).flatMap(([nav, views]) => views.map((v) => [v, nav])),
);

function showTab(name) {
  // Accept either a nav name (library/pipeline/operations/guide), a legacy
  // alias (workshop), or a legacy view name (overview/adapters/run/...).
  const aliased = LEGACY_NAV_ALIASES[name] || name;
  const nav = NAV_VIEWS[aliased] ? aliased : (VIEW_TO_NAV[aliased] || "library");
  const visibleViews = new Set(NAV_VIEWS[nav]);

  $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.nav === nav));
  $$(".view").forEach((v) => {
    const viewId = v.id.replace(/^view-/, "");
    v.classList.toggle("hidden", !visibleViews.has(viewId));
  });
  // Slice 4: clean path routing. pushState only when path actually changes
  // so we don't pile duplicate entries into history on tab re-clicks.
  const targetPath = `/${nav}`;
  if (location.pathname !== targetPath && !location.pathname.startsWith(`${targetPath}/`)) {
    history.pushState({ nav }, "", targetPath);
  }
  const crumb = $("#page-breadcrumb");
  if (crumb) crumb.textContent = nav;

  // Render every visible section.
  for (const viewId of visibleViews) {
    RENDERERS[viewId]?.();
  }
  // Materialize Lucide icons for any newly-rendered <i data-lucide>.
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

const navList = $("#nav-list");
if (navList) {
  navList.addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-item");
    if (btn) showTab(btn.dataset.nav);
  });
}

// Keyboard activation for the status strip (tabindex=0, role=status doesn't
// fire click on Enter/Space by itself). Skip when the active element is a
// strip-action button — it owns its own keyboard semantics.
$("#status-strip").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" && e.key !== " ") return;
  if (e.target.closest(".strip-action")) return;
  e.preventDefault();
  paintSystemDialog();
  $("#system-dialog").showModal();
});

// React to in-app navigation by hash. Slice 4 moved primary routing to clean
// paths, but this handler stays so that legacy `#workshop`, `#operations`,
// `#guide:path` hashes shared during the rename window still work — we
// rewrite them to the clean path and re-render.
window.addEventListener("hashchange", () => {
  const raw = location.hash.slice(1);
  if (!raw) return;
  if (raw.startsWith("guide:")) {
    const sub = raw.slice("guide:".length);
    showTab("guide");
    if (sub) loadGuideDoc(decodeURIComponent(sub));
    return;
  }
  if (NAV_VIEWS[raw] || RENDERERS[raw] || LEGACY_NAV_ALIASES[raw]) showTab(raw);
});

// Slice 4: browser back/forward should re-render the appropriate tab. The
// catch-all backend routes serve index.html for /library /pipeline /operations
// /guide(/...), so popstate is the only signal we get on navigation.
window.addEventListener("popstate", () => {
  const parsed = parsePath(location.pathname);
  if (parsed.nav === "guide" && parsed.guidePath) {
    showTab("guide");
    loadGuideDoc(parsed.guidePath);
  } else if (parsed.puzzleId) {
    showPuzzleDetail(parsed.puzzleId, { skipPush: true });
  } else if (parsed.adapterId) {
    showAdapterDetail(parsed.adapterId, { skipPush: true });
  } else {
    showTab(parsed.nav);
  }
});

// ---------- Theme toggle (light default, dark opt-in) ----------
//
// The pre-paint inline <script> in index.html sets body[data-theme] before
// CSS renders to avoid a flash. This block owns the toggle button + the
// localStorage persistence; both must agree on the same key + values.

const THEME_KEY = "yengo-dashboard:theme";

function readTheme() {
  return document.body.dataset.theme === "dark" ? "dark" : "light";
}

function applyTheme(theme) {
  const next = theme === "dark" ? "dark" : "light";
  document.body.dataset.theme = next;
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem(THEME_KEY, next); } catch (_) { /* private mode */ }
  paintThemeToggle();
}

function paintThemeToggle() {
  const btn = $("#theme-toggle");
  if (!btn) return;
  const cur = readTheme();
  const icon = $("#theme-toggle-icon");
  const label = $("#theme-toggle-label");
  // Toggle says "switch to <other>" — clearer than "currently <this>".
  if (cur === "light") {
    if (icon) icon.setAttribute("data-lucide", "moon");
    if (label) label.textContent = "Dark theme";
  } else {
    if (icon) icon.setAttribute("data-lucide", "sun");
    if (label) label.textContent = "Light theme";
  }
  if (window.lucide?.createIcons) window.lucide.createIcons();
}

const themeToggleBtn = $("#theme-toggle");
if (themeToggleBtn) {
  themeToggleBtn.addEventListener("click", () => {
    applyTheme(readTheme() === "light" ? "dark" : "light");
  });
}
paintThemeToggle();

// ---------- Boot ----------

// Slice 4: clean-path router. Resolve the current navigation target from
// (1) location.pathname, falling back to (2) the legacy hash format. Legacy
// hashes are immediately rewritten via replaceState so the URL bar matches
// the new format on the very first paint.
function parsePath(pathname) {
  const parts = pathname.split("/").filter(Boolean);
  const head = parts[0] || "";
  if (head === "guide") {
    const sub = parts.slice(1).map(decodeURIComponent).join("/");
    return { nav: "guide", guidePath: sub || null, adapterId: null };
  }
  // Theme 6a: /adapters/{id} resolves to library nav, adapterId triggers detail render.
  if (head === "adapters" && parts[1]) {
    return { nav: "library", guidePath: null, adapterId: decodeURIComponent(parts[1]) };
  }
  // Theme 10: /puzzle/{id} resolves to library nav with puzzle detail.
  if (head === "puzzle" && parts[1]) {
    return { nav: "library", guidePath: null, adapterId: null,
             puzzleId: decodeURIComponent(parts[1]) };
  }
  if (NAV_VIEWS[head]) return { nav: head, guidePath: null, adapterId: null };
  if (LEGACY_NAV_ALIASES[head]) return { nav: LEGACY_NAV_ALIASES[head], guidePath: null, adapterId: null };
  return { nav: "library", guidePath: null, adapterId: null };
}

let initialNav = "library";
let initialGuidePath = null;
let initialAdapterId = null;
let initialPuzzleId = null;
const initialHash = location.hash.slice(1);
if (location.pathname !== "/" && location.pathname !== "") {
  const parsed = parsePath(location.pathname);
  initialNav = parsed.nav;
  initialGuidePath = parsed.guidePath;
  initialAdapterId = parsed.adapterId;
  initialPuzzleId = parsed.puzzleId || null;
} else if (initialHash) {
  // Legacy hash → clean path. Rewrite the URL bar so screenshots and copies
  // immediately use the new format.
  if (initialHash.startsWith("guide:")) {
    initialNav = "guide";
    initialGuidePath = decodeURIComponent(initialHash.slice("guide:".length));
  } else if (NAV_VIEWS[initialHash]) {
    initialNav = initialHash;
  } else if (LEGACY_NAV_ALIASES[initialHash]) {
    initialNav = LEGACY_NAV_ALIASES[initialHash];
  } else if (VIEW_TO_NAV[initialHash]) {
    initialNav = VIEW_TO_NAV[initialHash];
  }
  const cleanPath = initialNav === "guide" && initialGuidePath
    ? `/guide/${initialGuidePath.split("/").map(encodeURIComponent).join("/")}`
    : `/${initialNav}`;
  history.replaceState(null, "", cleanPath);
}
showTab(initialNav);
if (initialGuidePath) loadGuideDoc(initialGuidePath);
if (initialAdapterId) showAdapterDetail(initialAdapterId, { skipPush: true });
if (initialPuzzleId) showPuzzleDetail(initialPuzzleId, { skipPush: true });

// Theme 10: global puzzle search box (top header).
const _puzzleSearchForm = $("#puzzle-search-form");
if (_puzzleSearchForm) {
  _puzzleSearchForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const input = $("#puzzle-search-input");
    const raw = input ? input.value : "";
    const pid = _normalizePuzzleId(raw);
    if (!pid) return;
    showPuzzleDetail(pid);
  });
}

// W3.1 — inline help chips. Click a [data-help-id="key"] anchor to open a
// small popover sourced from web/help-strings.json. Strings are loaded once
// and cached. Missing keys fail loud (console.warn) rather than silently
// rendering blanks — keeps drift visible.
let _HELP_STRINGS = null;
async function _loadHelpStrings() {
  if (_HELP_STRINGS !== null) return _HELP_STRINGS;
  try {
    const r = await fetch("/help-strings.json", { cache: "no-cache" });
    _HELP_STRINGS = await r.json();
  } catch (e) {
    console.warn("help-strings.json failed to load", e);
    _HELP_STRINGS = {};
  }
  return _HELP_STRINGS;
}
function _wireHelpChips() {
  document.addEventListener("click", async (e) => {
    const trigger = e.target.closest("[data-help-id]");
    if (!trigger) return;
    e.preventDefault();
    const key = trigger.dataset.helpId;
    const strings = await _loadHelpStrings();
    const entry = strings[key];
    if (!entry) {
      console.warn(`help-strings: missing key '${key}'`);
      return;
    }
    _showHelpPopover(trigger, entry);
  });
}
function _showHelpPopover(anchor, entry) {
  document.querySelectorAll(".help-popover").forEach(n => n.remove());
  const pop = document.createElement("div");
  pop.className = "help-popover";
  pop.setAttribute("role", "tooltip");
  pop.innerHTML = `
    <div class="help-popover-title">${escapeHtml(entry.title || "")}</div>
    <div class="help-popover-body">${escapeHtml(entry.body || "")}</div>
  `;
  document.body.appendChild(pop);
  const r = anchor.getBoundingClientRect();
  pop.style.left = `${Math.max(8, Math.min(window.innerWidth - 280, r.left))}px`;
  pop.style.top = `${r.bottom + 6}px`;
  const close = (ev) => {
    if (ev && pop.contains(ev.target)) return;
    pop.remove();
    document.removeEventListener("click", close, true);
    document.removeEventListener("keydown", esc);
  };
  const esc = (ev) => { if (ev.key === "Escape") close(); };
  setTimeout(() => {
    document.addEventListener("click", close, true);
    document.addEventListener("keydown", esc);
  }, 0);
}

// W3.3 — universal search palette. Opens on Cmd/Ctrl-K or "/" (when not
// already typing into an input). Queries adapters, tags, levels, and treats
// 16-hex / YENGO-* tokens as puzzle id lookups. Frontend-only filter — data
// already loaded by the relevant views or fetched lazily on first open.
let _PALETTE_INDEX = null;
async function _ensurePaletteIndex() {
  if (_PALETTE_INDEX) return _PALETTE_INDEX;
  const out = [];
  try {
    const adapters = await getJSON("/api/adapters");
    (adapters.sources || []).forEach((a) => out.push({
      kind: "adapter", id: a.id, label: a.id,
      hint: a.source_root || "",
      go: () => location.assign(`/adapters/${encodeURIComponent(a.id)}`),
    }));
  } catch {}
  try {
    const tags = await getJSON("/api/tags");
    (tags.raw || []).forEach((t) => out.push({
      kind: "tag", id: t.tag, label: t.tag,
      hint: `${t.category || "tag"} · ${t.usage_count || 0} uses`,
      go: () => location.assign(`/library`),
    }));
  } catch {}
  try {
    const levels = await getJSON("/api/levels");
    (levels.raw || []).forEach((l) => out.push({
      kind: "level", id: l.level, label: l.level,
      hint: `${l.rank_min}–${l.rank_max} · ${l.usage_count || 0} uses`,
      go: () => location.assign(`/library`),
    }));
  } catch {}
  _PALETTE_INDEX = out;
  return out;
}
function _wireCommandPalette() {
  document.addEventListener("keydown", (e) => {
    const isMod = e.ctrlKey || e.metaKey;
    const inField = e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA");
    if (isMod && (e.key === "k" || e.key === "K")) {
      e.preventDefault(); _openPalette();
    } else if (e.key === "/" && !inField) {
      e.preventDefault(); _openPalette();
    }
  });
  const trigger = document.getElementById("palette-trigger");
  if (trigger) trigger.addEventListener("click", _openPalette);
}
async function _openPalette() {
  let dlg = document.getElementById("command-palette");
  if (!dlg) {
    dlg = document.createElement("dialog");
    dlg.id = "command-palette";
    dlg.className = "command-palette";
    dlg.innerHTML = `
      <input type="search" id="palette-input" placeholder="Search sources, tags, levels, or paste a puzzle id (16-hex / YENGO-…)" autocomplete="off" />
      <ul id="palette-results" role="listbox"></ul>
      <div class="palette-foot"><span>↑↓ to move</span><span>↵ to open</span><span>esc to close</span></div>
    `;
    document.body.appendChild(dlg);
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
  }
  const input = dlg.querySelector("#palette-input");
  const list = dlg.querySelector("#palette-results");
  const index = await _ensurePaletteIndex();
  let active = 0;
  const render = () => {
    const q = input.value.trim().toLowerCase();
    const hashLike = /^(yengo-)?[a-f0-9]{6,16}$/i.test(input.value.trim());
    let results = !q ? index.slice(0, 25) : index.filter(it =>
      it.label.toLowerCase().includes(q) || (it.hint || "").toLowerCase().includes(q),
    ).slice(0, 25);
    if (hashLike) {
      const pid = _normalizePuzzleId(input.value.trim());
      if (pid) results = [{ kind: "puzzle", id: pid, label: pid, hint: "open puzzle detail",
        go: () => showPuzzleDetail(pid) }, ...results];
    }
    list.innerHTML = results.map((r, i) => `
      <li role="option" data-i="${i}" class="${i === active ? "active" : ""}">
        <span class="palette-kind">${escapeHtml(r.kind)}</span>
        <span class="palette-label">${escapeHtml(r.label)}</span>
        <span class="palette-hint">${escapeHtml(r.hint || "")}</span>
      </li>
    `).join("");
    list._results = results;
  };
  const move = (delta) => {
    const n = (list._results || []).length;
    if (!n) return;
    active = (active + delta + n) % n;
    render();
  };
  const choose = () => {
    const r = (list._results || [])[active];
    if (!r) return;
    dlg.close();
    r.go();
  };
  input.value = "";
  active = 0;
  render();
  input.addEventListener("input", () => { active = 0; render(); });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); move(+1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(-1); }
    else if (e.key === "Enter") { e.preventDefault(); choose(); }
    else if (e.key === "Escape") { dlg.close(); }
  });
  list.addEventListener("click", (e) => {
    const li = e.target.closest("li[data-i]");
    if (!li) return;
    active = Number(li.dataset.i);
    choose();
  });
  dlg.showModal();
  setTimeout(() => input.focus(), 0);
}

masterTick();
setInterval(refreshRelTimes, 30_000);   // relative-time labels tick every 30s

// Theme 16c: install the typed-confirm guard at boot so any destructive
// button rendered later (Operations, Library, Pipeline, anywhere) is
// already covered when it appears in the DOM. The capture-phase listener
// is idempotent — the cache + installed-flag prevent double registration.
_ensureOpsCatalogGuard();
_wireHelpCallouts();
_wireHelpDrawer();
_wireHelpChips();
_wireCommandPalette();

// Pause polling while the tab is hidden; immediate tick + resume on focus.
document.addEventListener("visibilitychange", () => {
  _pollPaused = document.hidden;
  if (_pollPaused) {
    if (_pollTimer) { clearTimeout(_pollTimer); _pollTimer = null; }
  } else {
    _pollDelay = POLL_IDLE_MIN_MS;
    masterTick();
  }
});
