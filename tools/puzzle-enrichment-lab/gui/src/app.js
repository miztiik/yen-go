/**
 * app.js — Main orchestrator for Enrichment Lab GUI.
 *
 * Wires all components together:
 *   - SGF Input → Enrich / Analyze workflows
 *   - SSE events → stage stepper + board + tree + log
 *   - BesoGo tree click → board navigation
 *   - Keyboard shortcuts
 */

import { boardState, analysisResult, pipelineStages, logLines, enrichResult,
         sgfText, runInfo, isEnriching, isAnalyzing, engineStatus, configOverrides, analyzeVisits } from './state.js';
import { initBoard, getCurrentBoard, loadSgf, getEditor } from './board.js';
import { analyzePython, streamEnrichment, cancelEnrichment, getHealth } from './bridge-client.js';
import { initAnalysisTable } from './analysis-table.js';
import { initStageStepper, resetStepper, advanceStage, markStageError, markAllComplete } from './stage-stepper.js';
import { initConfigPanel, getConfigOverrides } from './config-panel.js';
import { initLogPanel, appendLog, clearLog } from './log-panel.js';
import { initSgfInput } from './sgf-input.js';
import { initPolicyPanel } from './policy-panel.js';
import { initBoardOverlay } from './board-overlay.js';
import { initPlayerIndicator } from './player-indicator.js';

let enrichAbort = null;

// ── Engine status labels ──

function engineStatusLabel(raw) {
  const labels = {
    'not_started': 'Idle',
    'starting': 'Starting...',
    'ready': 'Ready',
    'running': 'Running...',
    'error': 'Error',
    'enriching': 'Enriching...',
    'analyzing': 'Analyzing...',
  };
  return labels[raw] || raw;
}

function engineStatusClass(raw) {
  const classes = {
    'not_started': 'status-idle',
    'starting': 'status-busy',
    'ready': 'status-ready',
    'running': 'status-busy',
    'error': 'status-error',
    'enriching': 'status-busy',
    'analyzing': 'status-busy',
  };
  return classes[raw] || '';
}

async function updateEngineStatus() {
  const health = await getHealth();
  engineStatus.set(health.status);
  const modelEl = document.getElementById('engine-model');
  if (modelEl) {
    modelEl.textContent = health.status === 'ready'
      ? health.modelName || 'Ready'
      : engineStatusLabel(health.status);
    modelEl.className = engineStatusClass(health.status);
  }
}

// ── Bootstrap ──

document.addEventListener('DOMContentLoaded', async () => {
  // Initialize BesoGo board + tree (handles Go rules, SGF, navigation)
  initBoard(document.getElementById('besogo-container'));

  initStageStepper(document.getElementById('stage-stepper'));
  initConfigPanel(document.getElementById('config-panel'));
  initAnalysisTable(document.getElementById('analysis-table'));
  initPolicyPanel(); // Subscribes to analysisResult; resolves DOM by ID each render
  initBoardOverlay(); // SVG overlay for score dots and PV preview
  initPlayerIndicator(); // Player-to-move + aggregate stats
  initLogPanel(document.getElementById('log-panel'));
  initSgfInput(document.getElementById('sgf-input'), {
    onEnrich: handleEnrich,
    onAnalyze: handleAnalyze,
    onCancel: handleCancel,
  });

  // Re-load SGF into BesoGo when sgfText changes (debounced)
  let sgfLoadTimer = null;
  sgfText.subscribe((text) => {
    clearTimeout(sgfLoadTimer);
    if (text && text.trim().startsWith('(;')) {
      sgfLoadTimer = setTimeout(() => loadSgf(text), 300);
    }
  });

  // Check engine health (initial + periodic polling every 5s)
  updateEngineStatus();
  setInterval(updateEngineStatus, 5000);

  // Wire run-info bottom zone — show run_id and trace_id after enrichment
  runInfo.subscribe((info) => {
    const container = document.getElementById('run-info');
    if (!container) return;
    if (info) {
      document.getElementById('run-id-val').textContent = info.run_id || '';
      document.getElementById('trace-id-val').textContent = info.trace_id || '';
      container.classList.remove('hidden');
    } else {
      container.classList.add('hidden');
    }
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyboard);

  appendLog('GUI initialized. Paste SGF and click Enrich or Analyze.');
});

// ── Enrich workflow ──

async function handleEnrich() {
  const sgf = sgfText.get();
  if (!sgf.trim()) { appendLog('No SGF to enrich.'); return; }

  isEnriching.set('running');
  resetStepper();
  clearLog();
  appendLog('Starting enrichment pipeline...');

  enrichAbort = new AbortController();
  const overrides = getConfigOverrides();

  try {
    for await (const { event, data } of streamEnrichment(sgf, enrichAbort.signal, overrides)) {
      processSSEEvent(event, data);
      // Yield to browser render cycle so UI updates (pills, logs, board) paint
      // between events instead of batching all updates until stream ends.
      await new Promise(r => setTimeout(r, 0));
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      appendLog(`Error: ${err.message}`);
      markStageError('enriched_sgf', err.message);
    }
  } finally {
    isEnriching.set('idle');
    enrichAbort = null;
  }
}

function processSSEEvent(event, data) {
  // Log events are handled inside the switch to show a clean message.
  if (event !== 'log') {
    appendLog(`[${event}] ${JSON.stringify(data).substring(0, 200)}`);
  }

  switch (event) {
    case 'parse_sgf':
    case 'extract_solution':
    case 'solve_paths':
    case 'build_query':
    case 'katago_analysis':
    case 'validate_move':
    case 'generate_refutations':
    case 'estimate_difficulty':
    case 'assemble_result':
      advanceStage(event, data.puzzle_id || '');
      if (data.analysis) {
        analysisResult.set(data.analysis);
      }
      break;

    case 'board_state':
      advanceStage('build_query');
      appendLog(`Board: ${data.board_size}×${data.board_size}, ${data.player_to_move} to move`);
      if (data.sgf) {
        sgfText.set(data.sgf);
      }
      break;

    case 'teaching_enrichment': {
      const detail = [
        data.validation_status,
        data.difficulty_level ? `level: ${data.difficulty_level}` : '',
        data.refutation_count != null ? `refutations: ${data.refutation_count}` : '',
      ].filter(Boolean).join(', ');
      advanceStage('teaching_enrichment', detail);
      break;
    }

    case 'enriched_sgf':
      if (data.status === 'complete') {
        advanceStage('enriched_sgf', 'complete');
        if (data.sgf) {
          sgfText.set(data.sgf); // subscriber will load tree + board
        }
      } else if (data.status === 'failed') {
        markStageError('enriched_sgf', data.error || 'failed');
      } else {
        advanceStage('enriched_sgf', data.status || 'building');
      }
      break;

    case 'complete':
      markAllComplete();
      enrichResult.set(data);
      runInfo.set({
        run_id: data.run_id || '',
        trace_id: data.trace_id || '',
        ac_level: data.ac_level ?? 0,
      });
      appendLog(`Enrichment complete. ac_level=${data.ac_level}, run_id=${data.run_id}`);
      break;

    case 'log':
      appendLog(`${data.level || 'INFO'}: ${data.msg || ''}`);
      break;

    case 'error':
      appendLog(`Pipeline error: ${data.message || JSON.stringify(data)}`);
      break;

    case 'cancelled':
      appendLog('Enrichment cancelled.');
      break;
  }
}

// ── Analyze workflow ──

async function handleAnalyze() {
  const current = getCurrentBoard();
  if (!current) { appendLog('No board position to analyze.'); return; }

  isAnalyzing.set(true);
  appendLog('Analyzing position...');

  try {
    const result = await analyzePython(current.board, 'black', { visits: analyzeVisits.get() });
    analysisResult.set({
      ...result,
      boardSize: current.boardSize,
    });
    appendLog(`Analysis complete: ${result.moves?.length || 0} candidates, visits=${result.rootVisits}`);
  } catch (err) {
    appendLog(`Analysis error: ${err.message}`);
  } finally {
    isAnalyzing.set(false);
  }
}

// ── Cancel ──

function handleCancel() {
  if (enrichAbort) {
    isEnriching.set('cancelling');
    enrichAbort.abort();
    appendLog('Cancelling enrichment...');
  }
  cancelEnrichment();
}

// ── Keyboard shortcuts ──

function handleKeyboard(e) {
  const editor = getEditor();
  if (!editor) return;
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') return;

  switch (e.key) {
    case 'ArrowLeft':
      editor.prevNode(1);
      e.preventDefault();
      break;
    case 'ArrowRight':
      editor.nextNode(1);
      e.preventDefault();
      break;
    case 'Home':
      editor.prevNode(999);
      e.preventDefault();
      break;
    case 'End':
      editor.nextNode(999);
      e.preventDefault();
      break;
  }
}
