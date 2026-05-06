// ui.js — DOM helpers, HTTP, escaping, pills, toasts, dialogs, relative time.
// Pure cross-cutting utilities. No domain knowledge, no polling, no state
// beyond a small icon-paint debounce flag.

// ---------- DOM helpers ----------

export const $  = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ---------- Lucide icon materialization ----------
//
// Lazily materialize Lucide SVG icons after innerHTML mutations. Called
// from showTab() after each render and via MutationObserver for dynamic
// content like toasts and status strip updates.

export function paintIcons() {
  if (window.lucide?.createIcons) {
    try { window.lucide.createIcons(); } catch (_) { /* ignore */ }
  }
}

// Observe the whole document for added <i data-lucide> elements and
// materialize them on the next animation frame (rAF-throttled). Idempotent —
// importing this module installs exactly one observer.
let _iconRafPending = false;
new MutationObserver(() => {
  if (_iconRafPending) return;
  _iconRafPending = true;
  requestAnimationFrame(() => {
    _iconRafPending = false;
    paintIcons();
  });
}).observe(document.body, { childList: true, subtree: true });

// ---------- HTTP helpers ----------

export async function getJSON(url) {
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  const body = await r.text();
  let parsed;
  try { parsed = JSON.parse(body); } catch { parsed = body; }
  if (!r.ok) throw { status: r.status, body: parsed };
  return parsed;
}

export async function postJSON(url, body) {
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body || {}),
  });
  const text = await r.text();
  let parsed;
  try { parsed = JSON.parse(text); } catch { parsed = text; }
  if (!r.ok) throw { status: r.status, body: parsed };
  return parsed;
}

// ---------- HTML escaping + error block ----------

export const escapeHtml = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]),
  );

export function errorBlock(label, err) {
  const detail = typeof err.body === "object"
    ? `<pre class="text-xs text-rose-300 whitespace-pre-wrap mt-2">${escapeHtml(JSON.stringify(err.body, null, 2))}</pre>`
    : `<pre class="text-xs text-rose-300 mt-2">${escapeHtml(err.body || err.message || err)}</pre>`;
  return `<div class="rounded-md border border-rose-500/30 bg-rose-500/10 p-4">
    <div class="font-semibold text-rose-300">${escapeHtml(label)} failed${err.status ? ` (HTTP ${err.status})` : ""}</div>
    ${detail}
  </div>`;
}

// ---------- Cross-cutting UI helpers (per colors.md tokens) ----------

export const PILL_VARIANTS = {
  ok:          "bg-emerald-500/10 text-emerald-300 ring-1 ring-emerald-500/30",  // success-steady
  okFresh:     "bg-lime-500/10    text-lime-300    ring-1 ring-lime-500/30",     // success-fresh ("look here")
  info:        "bg-sky-500/10     text-sky-300     ring-1 ring-sky-500/30",
  running:     "bg-teal-500/15    text-teal-300    ring-1 ring-teal-400/40",     // refreshed: was sky
  warn:        "bg-orange-500/10  text-orange-300  ring-1 ring-orange-500/30",   // refreshed: was amber
  error:       "bg-rose-500/10    text-rose-300    ring-1 ring-rose-500/30",
  destructive: "bg-rose-500/10    text-rose-300    ring-1 ring-rose-500/30",
  stale:       "bg-slate-900/60   text-slate-500   ring-1 ring-slate-700",
  muted:       "bg-slate-800/50   text-slate-500   ring-1 ring-slate-800",
  neutral:     "bg-slate-800      text-slate-300   ring-1 ring-slate-700",
};

// Lucide icon name per pill variant. Replaces the old colored dot glyph.
// Icons are materialized on render via window.lucide.createIcons().
export const PILL_ICONS = {
  ok:          "check-circle-2",
  okFresh:     "check-circle-2",
  info:        "info",
  running:     "loader-2",      // CSS spins this when data-pulse="true"
  warn:        "alert-triangle",
  error:       "x-circle",
  destructive: "x-circle",
  stale:       "clock-4",
  muted:       "minus-circle",
  neutral:     "circle",
};

export function pill(variant, label, opts = {}) {
  const cls = PILL_VARIANTS[variant] || PILL_VARIANTS.neutral;
  const iconName = PILL_ICONS[variant] || "circle";
  const pulse = variant === "running" || opts.pulse ? `data-pulse="true"` : "";
  return `<span class="pill ${cls}" ${pulse}>
    <i data-lucide="${iconName}"></i>${escapeHtml(label)}
  </span>`;
}

// ---------- Relative time ----------

const RTF = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

export function relTime(iso) {
  if (!iso) return "—";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const dSec = (t - Date.now()) / 1000;
  const abs = Math.abs(dSec);
  const units = [
    [60, "second"], [60, "minute"], [24, "hour"],
    [7, "day"], [4.345, "week"], [12, "month"], [Infinity, "year"],
  ];
  let value = dSec;
  let unit = "second";
  let acc = 1;
  for (const [step, name] of units) {
    if (Math.abs(value / acc) < step) { unit = name; break; }
    acc *= step;
  }
  return RTF.format(Math.round(value / acc), unit);
}

export function tagRelTime(node, iso) {
  // Attach data attrs so the master tick can refresh in place.
  node.dataset.relTime = iso;
  node.title = iso;
  node.textContent = relTime(iso);
}

export function refreshRelTimes() {
  $$("[data-rel-time]").forEach((el) => { el.textContent = relTime(el.dataset.relTime); });
}

// ---------- Toast + confirm dialog ----------

export function toast(severity, msg) {
  const region = $("#toast-region");
  const node = document.createElement("div");
  node.className = `toast sev-${severity}`;
  node.textContent = msg;
  region.appendChild(node);
  setTimeout(() => {
    node.classList.add("fade-out");
    setTimeout(() => node.remove(), 220);
  }, 4200);
}

// Promise-based <dialog> confirmation. Resolves true on OK, false on cancel.
export function confirmDialog({ title, body, verb }) {
  return new Promise((resolve) => {
    const d = $("#confirm-dialog");
    $("#cd-title").textContent = title;
    $("#cd-body").textContent = body;
    $("#cd-verb").textContent = verb;
    const input = $("#cd-input");
    const go = $("#cd-go");
    input.value = "";
    go.disabled = true;
    const onInput = () => { go.disabled = input.value.trim() !== verb; };
    input.addEventListener("input", onInput);
    const onClose = () => {
      input.removeEventListener("input", onInput);
      d.removeEventListener("close", onClose);
      resolve(d.returnValue === "ok");
    };
    d.addEventListener("close", onClose);
    d.showModal();
    setTimeout(() => input.focus(), 50);
  });
}
