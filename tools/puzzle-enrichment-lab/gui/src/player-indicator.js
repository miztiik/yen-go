/**
 * player-indicator.js — Shows player-to-move and aggregate analysis stats.
 *
 * Renders inside #player-indicator in the right panel.
 * Subscribes to analysisResult for stats and boardState for player turn.
 */

import { analysisResult, boardState } from './state.js';

let containerEl = null;

export function initPlayerIndicator() {
  containerEl = document.getElementById('player-indicator');
  if (!containerEl) return;
  render(null);
  analysisResult.subscribe(render);
}

function render(result) {
  if (!containerEl) return;

  // Determine player to move from analysis or default
  const player = result?.playerToMove || 'black';
  const isBlack = player === 'black';
  const circleFill = isBlack ? '#1a1a1a' : '#f0f0f0';
  const circleStroke = isBlack ? '#555' : '#999';
  const label = isBlack ? 'Black to play' : 'White to play';

  let statsHtml = '';
  if (result && result.rootVisits != null) {
    const score = result.rootScoreLead != null
      ? (result.rootScoreLead > 0 ? `+${result.rootScoreLead.toFixed(1)}` : result.rootScoreLead.toFixed(1))
      : '-';
    statsHtml = `
      <span class="pi-stat">Visits: <strong>${result.rootVisits}</strong></span>
      <span class="pi-stat">Score: <strong>${score}</strong></span>
    `;
  }

  containerEl.innerHTML = `
    <div class="player-indicator">
      <svg width="18" height="18" viewBox="0 0 18 18">
        <circle cx="9" cy="9" r="8" fill="${circleFill}" stroke="${circleStroke}" stroke-width="1.5"/>
      </svg>
      <span class="pi-label">${label}</span>
      ${statsHtml}
    </div>
  `;
}
