/**
 * sgf-input.js — SGF paste/upload/download panel + Enrich/Analyze/Cancel buttons.
 */

import { sgfText, isEnriching, isAnalyzing, boardState, engineStatus, analyzeVisits } from './state.js';

let containerEl = null;
let onEnrich = null;
let onAnalyze = null;
let onCancel = null;

export function initSgfInput(container, handlers) {
  containerEl = container;
  onEnrich = handlers.onEnrich;
  onAnalyze = handlers.onAnalyze;
  onCancel = handlers.onCancel;
  render();

  isEnriching.subscribe(updateButtons);
  isAnalyzing.subscribe(updateButtons);
  engineStatus.subscribe(updateButtons);
}

function render() {
  if (!containerEl) return;
  containerEl.innerHTML = `
    <div class="sgf-input-panel">
      <label class="sgf-label">SGF Input</label>
      <textarea id="sgf-textarea" rows="6" placeholder="Paste SGF here..."></textarea>
      <div class="sgf-buttons">
        <label class="btn btn-sm btn-file">
          Upload <input type="file" id="sgf-file" accept=".sgf" hidden>
        </label>
        <button class="btn btn-sm" id="sgf-download" disabled>Download</button>
      </div>
      <div class="action-buttons">
        <button class="btn btn-primary" id="btn-enrich" title="Run full 10-stage pipeline: parse → validate → refute → difficulty → teach → build SGF">Enrich</button>
        <button class="btn" id="btn-analyze" title="Quick KataGo analysis of current board position (~1-3s)">Analyze</button>
        <button class="btn btn-danger" id="btn-cancel" disabled title="Cancel the current enrichment pipeline run">Cancel</button>
        <select class="config-select" id="visits-select" title="KataGo analysis visits">
          <option value="200">200v</option>
          <option value="500">500v</option>
          <option value="1000">1000v</option>
          <option value="2000">2000v</option>
          <option value="5000">5000v</option>
        </select>
      </div>
    </div>
  `;

  const textarea = containerEl.querySelector('#sgf-textarea');
  // Set initial value from state (e.g. default SGF)
  const initialSgf = sgfText.get();
  if (initialSgf) textarea.value = initialSgf;
  textarea.addEventListener('input', () => { sgfText.set(textarea.value); });

  containerEl.querySelector('#sgf-file').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      textarea.value = reader.result;
      sgfText.set(reader.result);
    };
    reader.readAsText(file);
  });

  containerEl.querySelector('#sgf-download').addEventListener('click', () => {
    const text = sgfText.get();
    if (!text) return;
    const blob = new Blob([text], { type: 'application/x-go-sgf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'enriched.sgf';
    a.click();
    URL.revokeObjectURL(url);
  });

  containerEl.querySelector('#btn-enrich').addEventListener('click', () => onEnrich?.());
  containerEl.querySelector('#btn-analyze').addEventListener('click', () => onAnalyze?.());
  containerEl.querySelector('#btn-cancel').addEventListener('click', () => onCancel?.());

  const visitsSelect = containerEl.querySelector('#visits-select');
  visitsSelect.value = String(analyzeVisits.get());
  visitsSelect.addEventListener('change', (e) => {
    analyzeVisits.set(parseInt(e.target.value, 10));
  });

  // Sync textarea when sgfText changes externally (e.g., after enrichment)
  sgfText.subscribe((text) => {
    if (textarea.value !== text) textarea.value = text;
    containerEl.querySelector('#sgf-download').disabled = !text;
  });
}

function updateButtons() {
  if (!containerEl) return;
  const enrichStatus = isEnriching.get();
  const analyzing = isAnalyzing.get();
  const engStatus = engineStatus.get();
  const busy = enrichStatus !== 'idle' || analyzing;
  const engineReady = engStatus === 'ready';

  const btnEnrich = containerEl.querySelector('#btn-enrich');
  const btnAnalyze = containerEl.querySelector('#btn-analyze');
  const btnCancel = containerEl.querySelector('#btn-cancel');

  if (btnEnrich) {
    btnEnrich.disabled = busy;
    btnEnrich.textContent = enrichStatus === 'running' ? 'Enriching...' : 'Enrich';
  }
  if (btnAnalyze) {
    btnAnalyze.disabled = busy || !engineReady;
    btnAnalyze.textContent = analyzing ? 'Analyzing...' : 'Analyze';
  }
  if (btnCancel) {
    btnCancel.disabled = enrichStatus !== 'running';
    btnCancel.textContent = enrichStatus === 'cancelling' ? 'Cancelling...' : 'Cancel';
  }
}
