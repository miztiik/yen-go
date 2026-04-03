/**
 * config-panel.js — Accordion config panel for KataGo enrichment parameters.
 *
 * Renders 7 groups of config widgets. Values are fetched from GET /api/config
 * and user overrides are tracked in configOverrides state.
 */

import { configDefaults, configOverrides, analyzeVisits } from './state.js';
import { escHtml } from './utils.js';

const STORAGE_KEY = 'enrichment-lab-config';
const STORAGE_VERSION = 1;
let containerEl = null;
let expandedGroupId = null;
let saveTimer = null;

/* ── Group / param definitions ── */

const GROUPS = [
  {
    id: 'analysis_engine', title: 'Analysis & Engine', params: [
      { path: 'visit_tiers.T1.visits', label: 'T1 Visits', type: 'slider', min: 50, max: 5000, step: 50, default: 500 },
      { path: 'visit_tiers.T2.visits', label: 'T2 Visits', type: 'slider', min: 100, max: 10000, step: 100, default: 2000 },
      { path: 'deep_enrich.visits', label: 'Deep Enrich Visits', type: 'slider', min: 100, max: 10000, step: 100, default: 2000 },
      { path: 'deep_enrich.root_num_symmetries_to_sample', label: 'Symmetries', type: 'slider', min: 1, max: 8, step: 1, default: 4 },
      { path: 'deep_enrich.escalate_to_referee', label: 'Escalate to Referee', type: 'toggle', default: true },
      { path: 'deep_enrich.escalation_winrate_low', label: 'Escalation WR Low', type: 'slider', min: 0, max: 1, step: 0.05, default: 0.3 },
      { path: 'deep_enrich.escalation_winrate_high', label: 'Escalation WR High', type: 'slider', min: 0, max: 1, step: 0.05, default: 0.7 },
      { path: 'analysis_defaults.default_max_visits', label: 'Default Max Visits', type: 'number', min: 1, max: 100000, default: 200 },
      { path: 'analysis_defaults.puzzle_region_margin', label: 'Region Margin', type: 'slider', min: 0, max: 10, step: 1, default: 2 },
    ],
  },
  {
    id: 'refutations', title: 'Refutations', params: [
      { path: 'refutations.delta_threshold', label: 'Delta Threshold', type: 'slider', min: 0.01, max: 0.5, step: 0.01, default: 0.08 },
      { path: 'refutations.candidate_max_count', label: 'Max Candidates', type: 'number', min: 1, max: 20, default: 5 },
      { path: 'refutations.refutation_max_count', label: 'Max Refutations', type: 'number', min: 1, max: 10, default: 3 },
      { path: 'refutations.refutation_visits', label: 'Refutation Visits', type: 'slider', min: 10, max: 5000, step: 10, default: 100 },
      { path: 'refutations.locality_max_distance', label: 'Locality Distance', type: 'slider', min: 0, max: 10, step: 1, default: 2 },
      { path: 'refutations.max_pv_length', label: 'Max PV Length', type: 'slider', min: 1, max: 20, step: 1, default: 4 },
      { path: 'refutations.candidate_scoring.temperature', label: 'Scoring Temp', type: 'slider', min: 0, max: 5, step: 0.1, default: 1.5 },
      { path: 'refutations.tenuki_rejection.enabled', label: 'Tenuki Rejection', type: 'toggle', default: true },
      { path: 'refutations.tenuki_rejection.manhattan_threshold', label: 'Tenuki Distance', type: 'slider', min: 0, max: 20, step: 1, default: 4 },
      { path: 'refutation_escalation.enabled', label: 'Ref. Escalation', type: 'toggle', default: true },
      { path: 'refutation_escalation.escalation_visits', label: 'Escalation Visits', type: 'slider', min: 100, max: 5000, step: 50, default: 500 },
      { path: 'refutation_escalation.escalation_delta_threshold', label: 'Escalation Delta', type: 'slider', min: 0.01, max: 0.2, step: 0.01, default: 0.03 },
    ],
  },
  {
    id: 'ai_solve', title: 'AI-Solve / Solution Tree', params: [
      { path: 'ai_solve.thresholds.t_good', label: 't_good', type: 'slider', min: 0.01, max: 0.3, step: 0.01, default: 0.05 },
      { path: 'ai_solve.thresholds.t_bad', label: 't_bad', type: 'slider', min: 0.05, max: 0.5, step: 0.01, default: 0.15 },
      { path: 'ai_solve.thresholds.t_hotspot', label: 't_hotspot', type: 'slider', min: 0.1, max: 0.8, step: 0.01, default: 0.30 },
      { path: 'ai_solve.solution_tree.max_total_tree_queries', label: 'Max Tree Queries', type: 'slider', min: 5, max: 200, step: 5, default: 50 },
      { path: 'ai_solve.solution_tree.branch_min_policy', label: 'Branch Min Policy', type: 'slider', min: 0.01, max: 0.3, step: 0.01, default: 0.05 },
      { path: 'ai_solve.solution_tree.max_branch_width', label: 'Max Branch Width', type: 'slider', min: 1, max: 10, step: 1, default: 3 },
      { path: 'ai_solve.solution_tree.tree_visits', label: 'Tree Visits', type: 'slider', min: 50, max: 5000, step: 50, default: 500 },
      { path: 'ai_solve.solution_tree.confirmation_visits', label: 'Confirm Visits', type: 'slider', min: 50, max: 5000, step: 50, default: 500 },
    ],
  },
  {
    id: 'validation', title: 'Validation', params: [
      { path: 'tree_validation.enabled', label: 'Tree Validation', type: 'toggle', default: true },
      { path: 'tree_validation.skip_when_confident', label: 'Skip When Confident', type: 'toggle', default: true },
      { path: 'tree_validation.confidence_winrate', label: 'Confidence WR', type: 'slider', min: 0.5, max: 1.0, step: 0.05, default: 0.85 },
      { path: 'tree_validation.visits_per_depth', label: 'Visits Per Depth', type: 'slider', min: 50, max: 5000, step: 50, default: 500 },
    ],
  },
  {
    id: 'difficulty', title: 'Difficulty', params: [
      { path: 'difficulty.structural_weights.solution_depth', label: 'solution_depth', type: 'weight', min: 0, max: 100, default: 35 },
      { path: 'difficulty.structural_weights.branch_count', label: 'branch_count', type: 'weight', min: 0, max: 100, default: 22 },
      { path: 'difficulty.structural_weights.local_candidates', label: 'local_candidates', type: 'weight', min: 0, max: 100, default: 18 },
      { path: 'difficulty.structural_weights.refutation_count', label: 'refutation_count', type: 'weight', min: 0, max: 100, default: 15 },
      { path: 'difficulty.structural_weights.proof_depth', label: 'proof_depth', type: 'weight', min: 0, max: 100, default: 10 },
      { path: 'difficulty.score_normalization_cap', label: 'Norm Cap', type: 'number', min: 1, max: 100, default: 30 },
      { path: 'difficulty.trap_density_floor', label: 'Trap Density Floor', type: 'slider', min: 0, max: 0.5, step: 0.01, default: 0.05 },
    ],
  },
  {
    id: 'teaching', title: 'Teaching', params: [
      { path: 'teaching.non_obvious_policy', label: 'Non-obvious Policy', type: 'slider', min: 0, max: 0.5, step: 0.01, default: 0.10 },
      { path: 'teaching.ko_delta_threshold', label: 'Ko Delta', type: 'slider', min: 0, max: 0.5, step: 0.01, default: 0.12 },
      { path: 'teaching.significant_loss_threshold', label: 'Sig. Loss', type: 'slider', min: 0, max: 1, step: 0.05, default: 0.5 },
    ],
  },
  {
    id: 'ko_analysis', title: 'Ko Analysis', params: [
      { path: 'ko_analysis.rules_by_ko_type', label: 'Rules by Ko Type', type: 'ko_rules' },
      { path: 'ko_analysis.pv_len_by_ko_type', label: 'PV Length by Ko Type', type: 'ko_pv_len' },
    ],
  },
];

/* ── Public API ── */

export async function initConfigPanel(container) {
  containerEl = container;
  // Load persisted state from localStorage
  loadFromStorage();
  try {
    const resp = await fetch('/api/config');
    if (resp.ok) {
      configDefaults.set(await resp.json());
    }
  } catch { /* defaults remain null */ }
  configOverrides.subscribe(() => { renderAll(); scheduleSave(); });
  configDefaults.subscribe(() => renderAll());
  analyzeVisits.subscribe(() => scheduleSave());
  renderAll();
}

export function getConfigOverrides() {
  const overrides = { ...configOverrides.get() };
  // DD-7: If weight sum ≠ 100, exclude weight overrides — server uses defaults
  const weightPrefix = 'difficulty.structural_weights.';
  const weightGroup = GROUPS.find(g => g.id === 'difficulty');
  if (weightGroup) {
    const weightParams = weightGroup.params.filter(p => p.type === 'weight');
    const sum = weightParams.reduce((s, p) => s + Number(resolveValue(p.path, p.default)), 0);
    if (sum !== 100) {
      for (const key of Object.keys(overrides)) {
        if (key.startsWith(weightPrefix)) delete overrides[key];
      }
    }
  }
  return overrides;
}

export function resetToDefaults() {
  configOverrides.set({});
  expandedGroupId = null;
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* ignore */ }
}

/* ── Rendering ── */

function renderAll() {
  if (!containerEl) return;
  const overrides = configOverrides.get();
  const hasOverrides = Object.keys(overrides).length > 0;
  const resetAllBtn = hasOverrides
    ? '<button class="btn btn-sm config-reset-all" data-reset-all>Reset All to Defaults</button>'
    : '';
  const html = GROUPS.map(g => renderGroup(g)).join('');
  containerEl.innerHTML = `<div class="config-panel">${resetAllBtn}${html}</div>`;
  bindEvents();
}

function renderGroup(group) {
  const isExpanded = expandedGroupId === group.id;
  const modCount = countModified(group);
  const chevronCls = isExpanded ? 'config-chevron expanded' : 'config-chevron';
  const bodyCls = isExpanded ? 'config-group-body' : 'config-group-body hidden';
  const countBadge = modCount > 0
    ? `<span class="config-group-count" style="background:var(--warning);color:#000">${modCount}</span>`
    : `<span class="config-group-count">${group.params.length}</span>`;

  let bodyContent;
  if (group.id === 'difficulty') {
    bodyContent = renderDifficultyGroup(group);
  } else if (group.id === 'ko_analysis') {
    bodyContent = renderKoGroup(group);
  } else {
    bodyContent = group.params.map(p => renderParam(p)).join('');
  }

  return `<div class="config-group" data-group="${group.id}">
    <button class="config-group-header" data-group-toggle="${group.id}">
      <svg class="${chevronCls}" viewBox="0 0 10 10"><path d="M3 1l4 4-4 4" stroke="currentColor" stroke-width="1.5" fill="none"/></svg>
      ${escHtml(group.title)} ${countBadge}
    </button>
    <div class="${bodyCls}">${bodyContent}</div>
  </div>`;
}

function renderParam(p) {
  switch (p.type) {
    case 'slider': return renderSlider(p.path, p.label, p.min, p.max, p.step, p.default);
    case 'toggle': return renderToggle(p.path, p.label, p.default);
    case 'number': return renderNumber(p.path, p.label, p.min, p.max, p.default);
    default: return '';
  }
}

function renderSlider(path, label, min, max, step, defaultVal) {
  const current = Number(resolveValue(path, defaultVal)) || 0;
  const isModified = isValueModified(path, defaultVal);
  const safePath = escHtml(path);
  const modBadge = isModified ? '<span class="config-modified">modified</span>' : '';
  const resetBtn = isModified ? `<button class="config-reset-btn" data-reset="${safePath}" title="Reset to default">&times;</button>` : '';
  const defaultLine = isModified ? `<span class="config-default">default: ${Number(resolveServerDefault(path, defaultVal))}</span>` : '';

  return `<div class="config-item">
    <div class="config-item-header">
      <span class="config-label">${escHtml(label)}</span>${modBadge}${resetBtn}
    </div>
    <div class="config-slider-row">
      <input type="range" class="config-slider" data-path="${safePath}" min="${Number(min)}" max="${Number(max)}" step="${Number(step)}" value="${current}">
      <span class="config-value" data-value-for="${safePath}">${formatNum(current, step)}</span>
    </div>
    <div class="config-range-labels"><span>${Number(min)}</span><span>${Number(max)}</span></div>
    ${defaultLine}
  </div>`;
}

function renderToggle(path, label, defaultVal) {
  const current = Boolean(resolveValue(path, defaultVal));
  const checked = current ? 'checked' : '';
  const isModified = isValueModified(path, defaultVal);
  const safePath = escHtml(path);
  const modBadge = isModified ? '<span class="config-modified">modified</span>' : '';
  const resetBtn = isModified ? `<button class="config-reset-btn" data-reset="${safePath}" title="Reset to default">&times;</button>` : '';
  const defaultLine = isModified ? `<span class="config-default">default: ${Boolean(resolveServerDefault(path, defaultVal))}</span>` : '';

  return `<div class="config-item">
    <div class="config-item-row">
      <label class="config-toggle">
        <input type="checkbox" data-path="${safePath}" ${checked}>
        <span class="toggle-track"></span>
        <span class="toggle-thumb"></span>
      </label>
      <span class="config-label">${escHtml(label)}</span>${modBadge}${resetBtn}
    </div>
    ${defaultLine}
  </div>`;
}

function renderNumber(path, label, min, max, defaultVal) {
  const current = Number(resolveValue(path, defaultVal)) || 0;
  const isModified = isValueModified(path, defaultVal);
  const safePath = escHtml(path);
  const modBadge = isModified ? '<span class="config-modified">modified</span>' : '';
  const resetBtn = isModified ? `<button class="config-reset-btn" data-reset="${safePath}" title="Reset to default">&times;</button>` : '';
  const defaultLine = isModified ? `<span class="config-default">default: ${Number(resolveServerDefault(path, defaultVal))}</span>` : '';

  return `<div class="config-item">
    <div class="config-item-header">
      <span class="config-label">${escHtml(label)}</span>${modBadge}${resetBtn}
    </div>
    <input type="number" class="config-number" data-path="${safePath}" min="${Number(min)}" max="${Number(max)}" value="${current}">
    ${defaultLine}
  </div>`;
}

/* ── Difficulty weight group (special) ── */

function renderDifficultyGroup(group) {
  const weightParams = group.params.filter(p => p.type === 'weight');
  const otherParams = group.params.filter(p => p.type !== 'weight');
  const sum = weightParams.reduce((s, p) => s + Number(resolveValue(p.path, p.default)) || 0, 0);
  const sumCls = sum === 100 ? 'weights-sum' : 'weights-sum invalid';
  const normalizeDisabled = sum === 100 ? 'disabled' : '';

  const weightRows = weightParams.map(p => {
    const val = Number(resolveValue(p.path, p.default)) || 0;
    const safePath = escHtml(p.path);
    return `<div class="weight-row">
      <span class="weight-label">${escHtml(p.label)}</span>
      <input type="range" class="config-slider" data-path="${safePath}" min="${Number(p.min)}" max="${Number(p.max)}" step="1" value="${val}" style="flex:1">
      <span class="weight-value" data-value-for="${safePath}">${val}</span>
    </div>`;
  }).join('');

  const otherHtml = otherParams.map(p => renderParam(p)).join('');

  return `<div class="config-weights">
    <div class="weights-header">
      <span class="config-label">Structural Weights</span>
      <span class="${sumCls}" data-weights-sum>Σ${sum}</span>
      <button class="weights-normalize" data-normalize ${normalizeDisabled}>Normalize</button>
    </div>
    ${weightRows}
  </div>
  ${otherHtml}`;
}

/* ── Ko analysis group (special) ── */

const KO_TYPES = ['none', 'direct', 'approach'];
const RULES_OPTIONS = ['chinese', 'tromp-taylor', 'japanese'];
const KO_PV_DEFAULTS = { none: 15, direct: 30, approach: 30 };
const KO_RULES_DEFAULTS = { none: 'chinese', direct: 'chinese', approach: 'chinese' };

function renderKoGroup(group) {
  // Rules by ko type
  const rulesRows = KO_TYPES.map(kt => {
    const path = `ko_analysis.rules_by_ko_type.${kt}`;
    const safePath = escHtml(path);
    const current = String(resolveValue(path, KO_RULES_DEFAULTS[kt]));
    const defaultVal = KO_RULES_DEFAULTS[kt];
    const isModified = isValueModified(path, defaultVal);
    const modBadge = isModified ? '<span class="config-modified">modified</span>' : '';
    const resetBtn = isModified ? `<button class="config-reset-btn" data-reset="${safePath}" title="Reset to default">&times;</button>` : '';
    const opts = RULES_OPTIONS.map(r => `<option value="${escHtml(r)}" ${r === current ? 'selected' : ''}>${escHtml(r)}</option>`).join('');
    return `<div class="config-item-row">
      <span class="config-label" style="width:60px">${escHtml(kt)}</span>${modBadge}${resetBtn}
      <select class="config-select" data-path="${safePath}">${opts}</select>
    </div>`;
  }).join('');

  // PV len by ko type
  const pvRows = KO_TYPES.map(kt => {
    const path = `ko_analysis.pv_len_by_ko_type.${kt}`;
    const safePath = escHtml(path);
    const current = Number(resolveValue(path, KO_PV_DEFAULTS[kt])) || 0;
    const defaultVal = KO_PV_DEFAULTS[kt];
    const isModified = isValueModified(path, defaultVal);
    const modBadge = isModified ? '<span class="config-modified">modified</span>' : '';
    const resetBtn = isModified ? `<button class="config-reset-btn" data-reset="${safePath}" title="Reset to default">&times;</button>` : '';
    return `<div class="config-item-row">
      <span class="config-label" style="width:60px">${escHtml(kt)}</span>${modBadge}${resetBtn}
      <input type="number" class="config-number" data-path="${safePath}" min="1" max="60" value="${current}">
    </div>`;
  }).join('');

  return `<div class="config-item">
    <span class="config-label" style="font-weight:600">Rules by Ko Type</span>
    ${rulesRows}
  </div>
  <div class="config-item">
    <span class="config-label" style="font-weight:600">PV Length by Ko Type</span>
    ${pvRows}
  </div>`;
}

/* ── Event binding ── */

function bindEvents() {
  if (!containerEl) return;

  // Reset All button
  const resetAllBtn = containerEl.querySelector('[data-reset-all]');
  if (resetAllBtn) {
    resetAllBtn.addEventListener('click', () => resetToDefaults());
  }

  // Accordion toggle
  containerEl.querySelectorAll('[data-group-toggle]').forEach(btn => {
    btn.addEventListener('click', () => {
      const gid = btn.dataset.groupToggle;
      expandedGroupId = expandedGroupId === gid ? null : gid;
      renderAll();
      scheduleSave();
    });
  });

  // Sliders
  containerEl.querySelectorAll('input.config-slider').forEach(el => {
    el.addEventListener('input', () => {
      const path = el.dataset.path;
      const val = parseFloat(el.value);
      setOverride(path, val);
      const display = containerEl.querySelector(`[data-value-for="${path}"]`);
      if (display) display.textContent = formatNum(val, parseFloat(el.step));
    });
  });

  // Number inputs
  containerEl.querySelectorAll('input.config-number').forEach(el => {
    el.addEventListener('change', () => {
      const path = el.dataset.path;
      const val = parseFloat(el.value);
      if (!isNaN(val)) setOverride(path, val);
    });
  });

  // Toggles
  containerEl.querySelectorAll('.config-toggle input[type="checkbox"]').forEach(el => {
    el.addEventListener('change', () => {
      setOverride(el.dataset.path, el.checked);
    });
  });

  // Selects
  containerEl.querySelectorAll('select.config-select').forEach(el => {
    el.addEventListener('change', () => {
      setOverride(el.dataset.path, el.value);
    });
  });

  // Reset buttons
  containerEl.querySelectorAll('[data-reset]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const path = btn.dataset.reset;
      removeOverride(path);
    });
  });

  // Normalize weights
  const normBtn = containerEl.querySelector('[data-normalize]');
  if (normBtn) {
    normBtn.addEventListener('click', () => normalizeWeights());
  }
}

/* ── Weight normalization ── */

function normalizeWeights() {
  const group = GROUPS.find(g => g.id === 'difficulty');
  if (!group) return;
  const weightParams = group.params.filter(p => p.type === 'weight');
  const total = weightParams.reduce((s, p) => s + resolveValue(p.path, p.default), 0);
  if (total === 0 || total === 100) return;
  const overrides = { ...configOverrides.get() };
  for (const p of weightParams) {
    const raw = resolveValue(p.path, p.default);
    overrides[p.path] = Math.round((raw / total) * 100);
  }
  // Adjust rounding to hit exactly 100
  const newTotal = weightParams.reduce((s, p) => s + overrides[p.path], 0);
  if (newTotal !== 100) {
    overrides[weightParams[0].path] += (100 - newTotal);
  }
  configOverrides.set(overrides);
}

/* ── Value resolution helpers ── */

function resolveValue(path, defaultVal) {
  const overrides = configOverrides.get();
  if (path in overrides) return overrides[path];

  // Try to resolve from server defaults via dotted path
  const defaults = configDefaults.get();
  if (defaults) {
    const val = getNestedValue(defaults, path);
    if (val !== undefined) return val;
  }
  return defaultVal;
}

function getNestedValue(obj, path) {
  const parts = path.split('.');
  let cur = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = cur[p];
  }
  return cur;
}

function isValueModified(path, defaultVal) {
  const overrides = configOverrides.get();
  if (!(path in overrides)) return false;
  const serverDefault = resolveServerDefault(path, defaultVal);
  return overrides[path] !== serverDefault;
}

/** Resolve the actual server default for a path, falling back to hardcoded default. */
function resolveServerDefault(path, fallback) {
  const defaults = configDefaults.get();
  if (defaults) {
    const val = getNestedValue(defaults, path);
    if (val !== undefined) return val;
  }
  return fallback;
}

function setOverride(path, value) {
  const overrides = { ...configOverrides.get(), [path]: value };
  configOverrides.set(overrides);
}

function removeOverride(path) {
  const overrides = { ...configOverrides.get() };
  delete overrides[path];
  configOverrides.set(overrides);
}

function countModified(group) {
  return group.params.filter(p => p.default !== undefined && isValueModified(p.path, p.default)).length;
}

function formatNum(val, step) {
  if (step !== undefined && step < 1) {
    const decimals = String(step).split('.')[1]?.length || 2;
    return Number(val).toFixed(decimals);
  }
  return String(val);
}

// escHtml imported from utils.js

/* ── localStorage persistence (T22, T23) ── */

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.version !== STORAGE_VERSION) return;
    if (data.overrides && typeof data.overrides === 'object') {
      configOverrides.set(data.overrides);
    }
    if (typeof data.analyze_visits === 'number') {
      analyzeVisits.set(data.analyze_visits);
    }
    if (data.accordion_state && typeof data.accordion_state === 'string') {
      expandedGroupId = data.accordion_state;
    }
  } catch { /* corrupted storage — ignore */ }
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveToStorage, 500);
}

function saveToStorage() {
  try {
    const data = {
      version: STORAGE_VERSION,
      overrides: configOverrides.get(),
      analyze_visits: analyzeVisits.get(),
      accordion_state: expandedGroupId,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch { /* quota exceeded — ignore */ }
}
