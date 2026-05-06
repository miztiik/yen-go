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
  let sev = "ok";
  let text = "healthy";
  if (SYSTEM.unreachable) {
    sev = "error"; text = "unreachable";
  } else if (SYSTEM.active && !isTerminal(SYSTEM.active.status)) {
    sev = "running";
    const sub = SYSTEM.active.command?.[3] || "run";
    text = `${sub} running`;
  } else if (SYSTEM.lock.locked) {
    sev = "warn"; text = "lock held";
  }
  chip.dataset.sev = sev;
  if (label) label.textContent = text;
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
    // Inventory + adapters in parallel; adapters powers the per-source mini-table.
    const [inv, adapters] = await Promise.all([
      getJSON("/api/inventory"),
      loadConfigMaps().then(() => getJSON("/api/adapters").catch(() => ({ sources: [] }))),
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
      <h2 class="text-xs uppercase tracking-wider text-slate-500 mb-3">Published Inventory</h2>
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
    `;
  } catch (e) { root.innerHTML = errorBlock("/api/inventory", e); }
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
      <td class="py-2 pl-3 pr-4 font-mono text-sm">${escapeHtml(a.id)}${activeMarker}</td>
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
      <div class="flex items-baseline gap-3 mb-3">
        <h2 class="text-xs uppercase tracking-wider text-slate-500">Adapters</h2>
        <span class="text-xs text-slate-500">${rows.length} source${rows.length === 1 ? "" : "s"}</span>
        <span class="text-xs text-slate-400">·</span>
        <span class="text-xs text-slate-400">${activeNote}</span>
      </div>
      <div class="overflow-x-auto rounded-md border border-slate-800 bg-slate-900">
        <table class="w-full text-sm">
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
    `;
  } catch (e) { root.innerHTML = errorBlock("/api/adapters", e); }
}

function emptyState(headline, hintHtml = "") {
  return `<div class="rounded-lg border border-dashed border-slate-700 p-8 text-center">
    <p class="text-sm text-slate-300">${escapeHtml(headline)}</p>
    ${hintHtml ? `<p class="text-xs text-slate-500 mt-2">${hintHtml}</p>` : ""}
  </div>`;
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
    <div class="flex items-baseline gap-3 mb-4">
      <h2 class="text-xs uppercase tracking-wider text-slate-500">Live Run</h2>
      <span id="run-status">${pill("muted", "idle")}</span>
      <div id="run-stepper" class="stepper ml-2"></div>
    </div>

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
          <label class="flex items-center gap-2 text-xs"><input id="run-fresh" type="checkbox" /> --fresh<span class="text-slate-600 ml-1">(clean staging first)</span></label>
          <label class="flex items-center gap-2 text-xs"><input id="run-dry-run" type="checkbox" /> --dry-run</label>
          <label class="flex items-center gap-2 text-xs"><input id="run-source-override" type="checkbox" /> --source-override</label>
          <label class="flex items-center gap-2 text-xs"><input id="run-no-enrichment" type="checkbox" /> --no-enrichment</label>
        </div>
        <div class="flex gap-2 pt-2">
          <button id="run-start"  class="flex-1 ${PILL_VARIANTS.ok}     hover:bg-emerald-500/20 disabled:opacity-40 disabled:pointer-events-none text-sm rounded-md px-3 py-1.5"${hasActive ? '' : ' disabled title="No active adapter — enable one from the Adapters tab."'}>Start</button>
          <button id="run-cancel" class="flex-1 ${PILL_VARIANTS.warn}   hover:bg-orange-500/20 disabled:opacity-40 disabled:pointer-events-none text-sm rounded-md px-3 py-1.5" disabled>Cancel</button>
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
  const runId = $("#mr-run-id").value.trim();
  const ids = $("#mr-puzzle-ids").value
    .split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
  const body = { reason: $("#mr-reason").value.trim() };
  if (runId) body.run_id = runId;
  if (ids.length) body.puzzle_ids = ids;
  body.dry_run = $("#mr-dry").checked;
  body.yes = $("#mr-yes").checked;
  body.verify = $("#mr-verify").checked;
  return body;
}

function readVacuumForm() {
  return { rebuild: $("#mv-rebuild").checked, dry_run: $("#mv-dry").checked };
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
  // opts: { title, group, body, button: {label, id, variant, destructive} }
  const variantCls = PILL_VARIANTS[opts.button.variant] || PILL_VARIANTS.info;
  const destructive = opts.button.destructive ? `data-destructive` : ``;
  return `
    <section data-maint-card data-maint-verb="${escapeHtml(opts.button.label)}"
             class="maint-card rounded-md border border-slate-800 bg-slate-900 p-4 space-y-3
                    ${opts.group === 'destructive' ? 'border-l-2 border-l-rose-500/40' : ''}">
      <header class="flex items-baseline justify-between">
        <h3 class="text-sm font-semibold text-slate-200">${escapeHtml(opts.title)}</h3>
        <span class="text-[10px] uppercase tracking-wider text-slate-500">${escapeHtml(opts.group)}</span>
      </header>
      ${opts.body}
      <button id="${opts.button.id}" ${destructive}
              class="w-full ${variantCls} hover:brightness-125 text-sm rounded-md px-3 py-1.5">
        ${escapeHtml(opts.button.label)}
      </button>
      <div class="card-status"></div>
    </section>`;
}

function renderMaintenance() {
  const root = $("#view-maintenance");
  root.innerHTML = `
    <div class="flex items-baseline gap-3 mb-3">
      <h2 class="text-xs uppercase tracking-wider text-slate-500">Operations</h2>
      <span class="text-xs text-slate-500">three groups, increasing blast radius</span>
    </div>
    <div id="maint-error" class="mb-3"></div>

    <div class="grid lg:grid-cols-3 gap-4">
      ${maintCard({
        title: "Vacuum DB",
        group: "maintenance",
        body: `
          <label class="flex items-center gap-2 text-xs"><input id="mv-rebuild" type="checkbox" /> --rebuild (full rebuild from disk)</label>
          <label class="flex items-center gap-2 text-xs"><input id="mv-dry" type="checkbox" /> --dry-run</label>
          <p class="text-[11px] text-slate-500">Reclaims free space in <code>yengo-search.db</code>. Rebuild is slow (minutes).</p>
        `,
        button: { id: "mv-go", label: "Run vacuum-db", variant: "info" },
      })}

      ${maintCard({
        title: "Clean",
        group: "maintenance",
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
      })}

      ${maintCard({
        title: "Rollback",
        group: "destructive",
        body: `
          <label class="block text-xs text-slate-400">Run ID
            <input id="mr-run-id" type="text" placeholder="20260505-deadbeef" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm font-mono" />
          </label>
          <div class="text-[10px] text-slate-500 -my-1">— or —</div>
          <label class="block text-xs text-slate-400">Puzzle IDs <span class="text-slate-500">(comma/space separated)</span>
            <textarea id="mr-puzzle-ids" rows="2" class="w-full mt-1 bg-slate-950 border border-slate-700 rounded px-2 py-1 text-sm font-mono"></textarea>
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
        button: { id: "mr-go", label: "Run rollback", variant: "destructive", destructive: true },
      })}
    </div>
    <p class="mt-4 text-[11px] text-slate-500">
      Looking for publish-log search? It moved to the
      <a href="/logs" data-internal-nav="logs" class="text-teal-300 hover:text-teal-200 underline">Logs</a>
      tab (Audit sub-section) so all read-only investigation lives in one place.
    </p>
  `;

  $("#mv-go").addEventListener("click", (e) => startMaintenance("/api/vacuum-db", readVacuumForm(), "vacuum-db", e.currentTarget));
  $("#mc-go").addEventListener("click", (e) => startMaintenance("/api/clean", readCleanForm(), "clean", e.currentTarget));
  $("#mr-go").addEventListener("click", async (e) => {
    const originBtn = e.currentTarget;
    const body = readRollbackForm();
    if (!body.reason) { toast("warn", "rollback reason is required"); return; }
    if (!body.run_id && !(body.puzzle_ids?.length)) {
      toast("warn", "provide a run ID or puzzle IDs"); return;
    }
    if (body.run_id && body.puzzle_ids?.length) {
      toast("warn", "provide a run ID OR puzzle IDs, not both"); return;
    }
    const ok = await confirmDialog({
      title: "Confirm rollback",
      body: body.dry_run
        ? `Dry-run: simulate rollback of ${body.run_id ? `run ${body.run_id}` : `${body.puzzle_ids.length} puzzles`}.`
        : `Permanently roll back ${body.run_id ? `run ${body.run_id}` : `${body.puzzle_ids.length} puzzles`}. This is destructive.`,
      verb: "rollback",
    });
    if (!ok) return;
    startMaintenance("/api/rollback", body, "rollback", originBtn);
  });
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
    <div class="flex items-baseline gap-3 mb-3">
      <h2 class="text-xs uppercase tracking-wider text-slate-500">Logs</h2>
      <span class="text-xs text-slate-500">read-only investigation</span>
    </div>
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
      <div class="grid lg:grid-cols-[20rem,1fr] gap-4">
        <aside class="rounded-md border border-slate-800 bg-slate-900 p-2 max-h-[70vh] overflow-y-auto">
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
  } catch (err) {
    pane.innerHTML = errorBlock("/api/logs/stage-files", err);
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
    return `
      <div class="rounded-md border border-slate-800 bg-slate-900 p-3
                  ${failed ? 'border-l-2 border-l-rose-500/60' : ''}">
        <div class="flex items-baseline gap-3 flex-wrap">
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
}

function refreshHistoryView() {
  if (!_historyData) return;
  const filtered = applyHistoryFilter(_historyData.runs, _historyFilter);
  const counter = $("#history-shown-count");
  if (counter) counter.textContent = `showing ${filtered.length} of ${_historyData.runs.length} (disk: ${_historyData.total})`;
  renderHistoryRows(filtered);
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
      <div class="flex items-baseline gap-3 mb-3">
        <h2 class="text-xs uppercase tracking-wider text-slate-500">Run History</h2>
        <span id="history-shown-count" class="text-xs text-slate-500">showing ${_historyData.runs.length} of ${_historyData.runs.length} (disk: ${_historyData.total})</span>
      </div>
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
  } catch (e) { root.innerHTML = errorBlock("/api/runs", e); }
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

document.addEventListener("click", async (e) => {
  // History row: click-to-copy run_id
  const copyBtn = e.target.closest("button.copy-run-id");
  if (copyBtn) { copyToClipboard(copyBtn.dataset.runId, copyBtn); return; }

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
  operations: ["maintenance"],
  logs:       ["logs"],
  guide:      ["guide"],
};

const RENDERERS = {
  overview:    renderOverview,
  adapters:    renderAdapters,
  run:         renderLiveRun,
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
    return { nav: "guide", guidePath: sub || null };
  }
  if (NAV_VIEWS[head]) return { nav: head, guidePath: null };
  if (LEGACY_NAV_ALIASES[head]) return { nav: LEGACY_NAV_ALIASES[head], guidePath: null };
  return { nav: "library", guidePath: null };
}

let initialNav = "library";
let initialGuidePath = null;
const initialHash = location.hash.slice(1);
if (location.pathname !== "/" && location.pathname !== "") {
  const parsed = parsePath(location.pathname);
  initialNav = parsed.nav;
  initialGuidePath = parsed.guidePath;
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
masterTick();
setInterval(refreshRelTimes, 30_000);   // relative-time labels tick every 30s

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
