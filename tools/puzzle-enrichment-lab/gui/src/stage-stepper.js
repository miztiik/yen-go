/**
 * stage-stepper.js — Vertical 10-stage enrichment pipeline stepper.
 *
 * Replaces the horizontal pill bar with a compact vertical stepper
 * that tracks timing and stage status.
 */

import { pipelineStages } from './state.js';
import { escHtml } from './utils.js';

const STAGES = [
  { id: 'parse_sgf', label: 'Parse SGF' },
  { id: 'extract_solution', label: 'Extract Solution' },
  { id: 'solve_paths', label: 'Solve Paths' },
  { id: 'build_query', label: 'Tsumego Frame' },
  { id: 'katago_analysis', label: 'KataGo Analysis' },
  { id: 'validate_move', label: 'Validate Move' },
  { id: 'generate_refutations', label: 'Refutations' },
  { id: 'estimate_difficulty', label: 'Level ID' },
  { id: 'assemble_result', label: 'Assemble' },
  { id: 'teaching_enrichment', label: 'Hints + Comments' },
  { id: 'enriched_sgf', label: 'Build SGF' },
];

/** Timing map: stageId → { start: number, elapsed: number|null } */
const timings = new Map();
let containerEl = null;

export function createInitialStages() {
  return STAGES.map(s => ({ ...s, status: 'pending', detail: '' }));
}

export function initStageStepper(container) {
  containerEl = container;
  pipelineStages.subscribe(render);
  render(pipelineStages.get());
}

export function resetStepper() {
  timings.clear();
  pipelineStages.set(createInitialStages());
}

export function advanceStage(stageId, detail = '') {
  const stages = pipelineStages.get().map(s => ({ ...s }));
  let found = false;
  for (const s of stages) {
    if (s.id === stageId) {
      s.status = 'active';
      s.detail = detail;
      found = true;
      // Record start time
      if (!timings.has(stageId) || timings.get(stageId).elapsed !== null) {
        timings.set(stageId, { start: performance.now(), elapsed: null });
      }
    } else if (!found) {
      // Complete prior stages and finalize their timing
      if (s.status !== 'error' && s.status !== 'complete') {
        s.status = 'complete';
      }
      if (s.status === 'complete') {
        finalizeTime(s.id);
      }
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
    finalizeTime(stageId);
  }
  pipelineStages.set(stages);
}

export function markAllComplete() {
  const stages = pipelineStages.get().map(s => ({
    ...s,
    status: s.status === 'error' ? 'error' : 'complete',
  }));
  for (const s of stages) { finalizeTime(s.id); }
  pipelineStages.set(stages);
}

function finalizeTime(stageId) {
  const t = timings.get(stageId);
  if (t && t.elapsed === null) {
    t.elapsed = performance.now() - t.start;
  }
}

function formatTime(stageId) {
  const t = timings.get(stageId);
  if (!t || t.elapsed === null) return '';
  const ms = t.elapsed;
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function render(stages) {
  if (!containerEl) return;
  if (!stages || stages.length === 0) {
    stages = createInitialStages();
  }
  const items = stages.map((s) => {
    const timeStr = formatTime(s.id);
    const title = s.detail ? escHtml(s.detail) : '';
    return `<div class="stage-item stage-${s.status}" data-stage="${s.id}" title="${title}">
      <div class="stage-dot"></div>
      <div class="stage-line"></div>
      <div class="stage-content">
        <span class="stage-name">${s.label}</span>
        <span class="stage-time">${timeStr}</span>
      </div>
    </div>`;
  }).join('');

  containerEl.innerHTML = `<div class="stage-stepper">${items}</div>`;

  // Placeholder click handlers (noop for Phase A)
  containerEl.querySelectorAll('.stage-item').forEach(el => {
    el.addEventListener('click', () => {
      // Reserved for future: click-to-inspect stage details
    });
  });
}

// escHtml imported from utils.js
