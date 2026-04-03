/**
 * analysis-table.js — Sortable candidate moves table (Order, Move, Prior, Score, Visits, PV).
 * Includes PV hover preview: mouseenter on a row shows numbered stones on the board overlay.
 * PV column is clickable: click pins the PV preview on the board; click again unpins.
 */

import { analysisResult } from './state.js';
import { showPVPreview, clearPVPreview } from './board-overlay.js';

const GTP_COLS = 'ABCDEFGHJKLMNOPQRST';

let tableEl = null;
let hoverDebounce = null;
let pinnedRowIdx = -1; // -1 = nothing pinned

export function initAnalysisTable(container) {
  tableEl = container;
  tableEl.innerHTML = '<div class="analysis-empty">No analysis results</div>';
  analysisResult.subscribe(render);
}

function render(result) {
  if (!tableEl) return;
  pinnedRowIdx = -1; // reset pin on new data
  if (!result || !result.moves || result.moves.length === 0) {
    tableEl.innerHTML = '<div class="analysis-empty">No analysis results</div>';
    return;
  }

  const boardSize = result.boardSize || 19;
  const rows = result.moves.map((m, i) => {
    const move = gtpDisplay(m.x, m.y, boardSize);
    const prior = (m.prior * 100).toFixed(1);
    const score = m.scoreLead > 0 ? `+${m.scoreLead.toFixed(1)}` : m.scoreLead.toFixed(1);
    const scoreClass = m.scoreLead > 0.5 ? 'score-pos' : m.scoreLead < -0.5 ? 'score-neg' : '';
    const pvMoves = (m.pv || []).slice(0, 5);
    const pvHtml = pvMoves.length > 0
      ? `<span class="pv-link" data-row="${i}">${pvMoves.join(' ')}</span>`
      : '';
    return `<tr data-row="${i}">
      <td>${i + 1}</td>
      <td class="move-col">${move}</td>
      <td>${prior}%</td>
      <td class="${scoreClass}">${score}</td>
      <td>${m.visits}</td>
      <td class="pv-col">${pvHtml}</td>
    </tr>`;
  });

  tableEl.innerHTML = `
    <table class="analysis-table">
      <thead><tr>
        <th>#</th><th>Move</th><th>Prior</th><th>Score</th><th>Visits</th><th>PV</th>
      </tr></thead>
      <tbody>${rows.join('')}</tbody>
    </table>`;

  // Attach hover + click handlers to each row
  const tbody = tableEl.querySelector('tbody');
  if (tbody) {
    const trs = tbody.querySelectorAll('tr');
    trs.forEach((tr, i) => {
      const move = result.moves[i];
      if (!move || !move.pv || move.pv.length === 0) return;

      // Hover: show PV preview (unless a different row is pinned)
      tr.addEventListener('mouseenter', () => {
        if (pinnedRowIdx >= 0 && pinnedRowIdx !== i) return;
        clearTimeout(hoverDebounce);
        hoverDebounce = setTimeout(() => {
          showPVPreview(move.pv, boardSize, 'black');
        }, 50);
      });
      tr.addEventListener('mouseleave', () => {
        if (pinnedRowIdx >= 0) return; // keep pinned preview
        clearTimeout(hoverDebounce);
        clearPVPreview();
      });
    });

    // Click on PV link: pin/unpin the PV preview
    const pvLinks = tableEl.querySelectorAll('.pv-link');
    pvLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        e.stopPropagation();
        const rowIdx = parseInt(link.dataset.row, 10);
        const move = result.moves[rowIdx];
        if (!move || !move.pv) return;

        if (pinnedRowIdx === rowIdx) {
          // Unpin
          pinnedRowIdx = -1;
          clearPVPreview();
          tableEl.querySelectorAll('.pv-link').forEach(l => l.classList.remove('pv-pinned'));
        } else {
          // Pin this row
          pinnedRowIdx = rowIdx;
          showPVPreview(move.pv, boardSize, 'black');
          tableEl.querySelectorAll('.pv-link').forEach(l => l.classList.remove('pv-pinned'));
          link.classList.add('pv-pinned');
        }
      });
    });
  }
}

function gtpDisplay(x, y, boardSize) {
  if (x < 0 || y < 0) return 'Pass';
  const col = GTP_COLS[x] || '?';
  const row = boardSize - y;
  return `${col}${row}`;
}
