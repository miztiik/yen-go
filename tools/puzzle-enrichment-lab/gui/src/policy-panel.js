/**
 * policy-panel.js — Policy prior visualization in the right panel.
 *
 * Shows a compact bar chart of move priors from KataGo analysis,
 * updating in real-time as analysis results arrive.
 * Resolves the DOM element by ID each render to survive besogo re-creation.
 */

import { analysisResult } from './state.js';

const GTP_COLS = 'ABCDEFGHJKLMNOPQRST';
const MAX_BARS = 10;
const PANEL_ID = 'policy-priors';

export function initPolicyPanel() {
  analysisResult.subscribe(render);
}

function getPanel() {
  return document.getElementById(PANEL_ID);
}

function render(result) {
  const panelEl = getPanel();
  if (!panelEl) return;

  if (!result || !result.moves || result.moves.length === 0) {
    panelEl.innerHTML = '<div class="policy-empty">Awaiting analysis…</div>';
    return;
  }

  const boardSize = result.boardSize || 19;
  const sorted = [...result.moves]
    .sort((a, b) => b.prior - a.prior)
    .slice(0, MAX_BARS);

  const maxPrior = sorted[0]?.prior || 1;

  const bars = sorted.map((m, i) => {
    const move = gtpDisplay(m.x, m.y, boardSize);
    const pct = (m.prior * 100).toFixed(1);
    const barWidth = Math.max(2, (m.prior / maxPrior) * 100);
    const opacity = 0.4 + 0.6 * (m.prior / maxPrior);
    const rank = i + 1;
    return `
      <div class="prior-row">
        <span class="prior-rank">${rank}</span>
        <span class="prior-move">${move}</span>
        <div class="prior-bar-track">
          <div class="prior-bar-fill" style="width:${barWidth}%;opacity:${opacity}"></div>
        </div>
        <span class="prior-pct">${pct}%</span>
      </div>`;
  });

  panelEl.innerHTML = `
    <div class="policy-header">Policy Priors</div>
    <div class="prior-bars">${bars.join('')}</div>`;
}

function gtpDisplay(x, y, boardSize) {
  if (x < 0 || y < 0) return 'Pass';
  const col = GTP_COLS[x] || '?';
  const row = boardSize - y;
  return `${col}${row}`;
}
