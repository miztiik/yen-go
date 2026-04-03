/**
 * pipeline-bar.js — 10-stage enrichment pipeline progress bar.
 *
 * Pill states: gray (pending) → blue-pulse (active) → green (complete) → red (error)
 * Shows run_id, trace_id, ac_level after enrichment completes.
 */

import { pipelineStages, runInfo } from './state.js';

const STAGES = [
  { id: 'parse_sgf', label: 'Parse SGF' },
  { id: 'extract_solution', label: 'Extract Solution' },
  { id: 'build_query', label: 'Tsumego Frame' },
  { id: 'katago_analysis', label: 'KataGo Analysis' },
  { id: 'validate_move', label: 'Validate Move' },
  { id: 'generate_refutations', label: 'Refutations' },
  { id: 'estimate_difficulty', label: 'Level ID' },
  { id: 'assemble_result', label: 'Assemble' },
  { id: 'teaching_enrichment', label: 'Hints + Comments' },
  { id: 'enriched_sgf', label: 'Build SGF' },
];

const AC_LABELS = ['UNTOUCHED', 'ENRICHED', 'AI_SOLVED', 'VERIFIED'];

let barEl = null;

export function initPipelineBar(container) {
  barEl = container;
  renderBar(createInitialStages());
  pipelineStages.subscribe(renderBar);
  runInfo.subscribe(renderRunInfo);
}

export function createInitialStages() {
  return STAGES.map(s => ({ ...s, status: 'pending', detail: '' }));
}

export function resetPipeline() {
  pipelineStages.set(createInitialStages());
  runInfo.set(null);
}

/**
 * Update a single stage status. Marks the stage as active and
 * all prior stages as complete.
 */
export function advanceStage(stageId, detail = '') {
  const stages = pipelineStages.get().map(s => ({ ...s }));
  let found = false;
  for (const s of stages) {
    if (s.id === stageId) {
      s.status = 'active';
      s.detail = detail;
      found = true;
    } else if (!found) {
      if (s.status !== 'error') s.status = 'complete';
    }
  }
  pipelineStages.set(stages);
}

export function markStageError(stageId, message) {
  const stages = pipelineStages.get().map(s => ({ ...s }));
  const stage = stages.find(s => s.id === stageId);
  if (stage) {
    stage.status = 'error';
    stage.detail = message;
  }
  pipelineStages.set(stages);
}

export function markAllComplete() {
  const stages = pipelineStages.get().map(s => ({ ...s, status: s.status === 'error' ? 'error' : 'complete' }));
  pipelineStages.set(stages);
}

function renderBar(stages) {
  if (!barEl) return;
  const pills = stages.map(s => {
    const cls = `pill pill-${s.status}`;
    const title = s.detail ? `${s.label}: ${s.detail}` : s.label;
    return `<div class="${cls}" title="${escHtml(title)}"><span class="pill-label">${s.label}</span></div>`;
  }).join('');

  const runInfoHtml = barEl.querySelector('.run-info-bar')?.outerHTML || '<div class="run-info-bar hidden"></div>';
  barEl.innerHTML = `<div class="pipeline-pills">${pills}</div>${runInfoHtml}`;
}

function renderRunInfo(info) {
  if (!barEl) return;
  let el = barEl.querySelector('.run-info-bar');
  if (!el) {
    el = document.createElement('div');
    el.className = 'run-info-bar hidden';
    barEl.appendChild(el);
  }
  if (!info) {
    el.classList.add('hidden');
    return;
  }
  el.classList.remove('hidden');
  const acLabel = AC_LABELS[info.ac_level] || `ac:${info.ac_level}`;
  const acClass = info.ac_level >= 2 ? 'ac-solved' : info.ac_level === 1 ? 'ac-enriched' : 'ac-untouched';
  el.innerHTML = `
    <span class="label">run_id:</span> <code>${escHtml(info.run_id || '-')}</code>
    <span class="label">trace:</span> <code>${escHtml(info.trace_id || '-')}</code>
    <span class="ac-badge ${acClass}">${acLabel}</span>
  `;
}

function escHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}
