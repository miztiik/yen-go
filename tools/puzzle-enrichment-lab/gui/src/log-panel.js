/**
 * log-panel.js -- Collapsible, drag-resizable streaming log viewer.
 */

import { logLines } from './state.js';

let panelEl = null;
let logContainer = null;
let collapsed = false;

export function initLogPanel(container) {
  panelEl = container;
  render();
  logLines.subscribe(appendLines);
}

export function appendLog(line) {
  const lines = logLines.get();
  const ts = new Date().toLocaleTimeString('en-US', { hour12: false });
  logLines.set([...lines, `[${ts}] ${line}`]);
}

export function clearLog() {
  logLines.set([]);
}

function render() {
  if (!panelEl) return;
  panelEl.innerHTML = `
    <div class="log-resize-handle" id="log-resize-handle"></div>
    <div class="log-header">
      <span class="log-title">Engine Logs</span>
      <button class="btn-sm" id="log-toggle">&#x25BC;</button>
      <button class="btn-sm" id="log-clear">Clear</button>
    </div>
    <pre class="log-content" id="log-content"></pre>
  `;
  logContainer = panelEl.querySelector('#log-content');
  panelEl.querySelector('#log-toggle').addEventListener('click', toggleCollapse);
  panelEl.querySelector('#log-clear').addEventListener('click', () => clearLog());
  initDragResize();
}

function appendLines(lines) {
  if (!logContainer) return;
  logContainer.textContent = lines.join('\n');
  logContainer.scrollTop = logContainer.scrollHeight;
}

function toggleCollapse() {
  collapsed = !collapsed;
  if (panelEl) {
    panelEl.classList.toggle('collapsed', collapsed);
    if (!collapsed) {
      // Restore to last known height or default
      panelEl.style.height = panelEl.dataset.lastHeight || '180px';
    } else {
      panelEl.style.height = '';
    }
  }
  if (logContainer) {
    logContainer.style.display = collapsed ? 'none' : 'block';
  }
  const btn = panelEl?.querySelector('#log-toggle');
  if (btn) btn.textContent = collapsed ? '\u25B6' : '\u25BC';
}

function initDragResize() {
  const handle = panelEl?.querySelector('#log-resize-handle');
  if (!handle) return;

  let startY = 0;
  let startHeight = 0;

  function onMouseDown(e) {
    e.preventDefault();
    if (collapsed) return;
    startY = e.clientY;
    startHeight = panelEl.getBoundingClientRect().height;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  }

  function onMouseMove(e) {
    const delta = startY - e.clientY;
    const newH = Math.max(60, Math.min(window.innerHeight * 0.7, startHeight + delta));
    panelEl.style.height = newH + 'px';
    panelEl.dataset.lastHeight = newH + 'px';
    // Trigger resize so the board adjusts
    window.dispatchEvent(new Event('resize'));
  }

  function onMouseUp() {
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }

  handle.addEventListener('mousedown', onMouseDown);
}
