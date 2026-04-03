/**
 * board-overlay.js — SVG overlay for score dots and PV hover preview.
 *
 * Creates an absolutely positioned SVG layer over the BesoGo board container.
 * pointer-events: none ensures all clicks pass through to BesoGo.
 * ResizeObserver keeps the overlay dimensions in sync with the board.
 * Re-attaches automatically after each BesoGo (re-)creation via onPostCreate hook.
 */

import { analysisResult } from './state.js';
import { onPostCreate, getBoardContainer } from './board.js';

const NS = 'http://www.w3.org/2000/svg';
const GTP_COLS = 'ABCDEFGHJKLMNOPQRST';
const MAX_SCORE_DOTS = 8;

let overlaySvg = null;
let scoreGroup = null;
let pvGroup = null;
let resizeObserver = null;
let currentBoardSize = 19;

// ── Public API ──

export function initBoardOverlay() {
  onPostCreate(handleBoardRecreated);
  const container = getBoardContainer();
  if (container) {
    createOverlay(container);
  }
  analysisResult.subscribe(onAnalysisUpdate);
}

export function showScoreOverlays(candidates, boardSize) {
  if (!scoreGroup) return;
  scoreGroup.innerHTML = '';
  currentBoardSize = boardSize;

  const top = candidates.slice(0, MAX_SCORE_DOTS);
  top.forEach((m, i) => {
    const pos = gtpToPixel(m.x, m.y, boardSize);
    if (!pos) return;

    // GoProblems-style coloring: green for positive, red/orange for negative
    const score = m.scoreLead;
    const fillColor = score > 0.5 ? '#22c55e'
      : score > -0.5 ? '#f59e0b'   // amber for ~neutral
      : '#ef4444';                   // red for negative
    const strokeColor = i === 0 ? '#fff' : 'rgba(255,255,255,0.5)';
    const radius = pos.cellSize * 0.38;

    // Background circle
    const circle = createSvgEl('circle', {
      cx: pos.x, cy: pos.y,
      r: radius,
      fill: fillColor,
      opacity: '0.88',
      stroke: strokeColor,
      'stroke-width': i === 0 ? 2 : 1,
    });
    scoreGroup.appendChild(circle);

    // Score text (top line)
    const scoreStr = score > 0 ? `+${score.toFixed(1)}` : score.toFixed(1);
    const fontSize = Math.max(9, pos.cellSize * 0.20);
    const scoreText = createSvgEl('text', {
      x: pos.x, y: pos.y - fontSize * 0.35,
      'text-anchor': 'middle',
      'dominant-baseline': 'central',
      'font-size': fontSize,
      'font-weight': '700',
      fill: '#fff',
    });
    scoreText.textContent = scoreStr;
    scoreGroup.appendChild(scoreText);

    // Visits text (bottom line, smaller)
    const visitsFontSize = Math.max(7, pos.cellSize * 0.16);
    const visitsText = createSvgEl('text', {
      x: pos.x, y: pos.y + fontSize * 0.55,
      'text-anchor': 'middle',
      'dominant-baseline': 'central',
      'font-size': visitsFontSize,
      'font-weight': '400',
      fill: 'rgba(255,255,255,0.85)',
    });
    visitsText.textContent = m.visits || '';
    scoreGroup.appendChild(visitsText);
  });
}

export function showPVPreview(pvMoves, boardSize, startColor) {
  if (!pvGroup) return;
  pvGroup.innerHTML = '';
  currentBoardSize = boardSize;

  pvMoves.forEach((move, i) => {
    const coords = parseGtpMove(move, boardSize);
    if (!coords) return;

    const pos = gtpToPixel(coords.x, coords.y, boardSize);
    if (!pos) return;

    const isBlack = (startColor === 'black') ? (i % 2 === 0) : (i % 2 !== 0);
    const stoneFill = isBlack ? '#1a1a1a' : '#f0f0f0';
    const textFill = isBlack ? '#fff' : '#000';
    const strokeColor = i === 0 ? '#f97316' : (isBlack ? '#333' : '#ccc');
    const strokeWidth = i === 0 ? 2.5 : 1;

    // Semi-transparent stone
    const circle = createSvgEl('circle', {
      cx: pos.x, cy: pos.y,
      r: pos.cellSize * 0.42,
      fill: stoneFill,
      opacity: '0.6',
      stroke: strokeColor,
      'stroke-width': strokeWidth,
    });
    pvGroup.appendChild(circle);

    // Move number label
    const label = createSvgEl('text', {
      x: pos.x, y: pos.y + 1,
      'text-anchor': 'middle',
      'dominant-baseline': 'central',
      'font-size': `${Math.max(10, pos.cellSize * 0.32)}`,
      'font-weight': '700',
      fill: textFill,
      opacity: '0.9',
    });
    label.textContent = i + 1;
    pvGroup.appendChild(label);
  });
}

export function clearOverlays() {
  if (scoreGroup) scoreGroup.innerHTML = '';
}

export function clearPVPreview() {
  if (pvGroup) pvGroup.innerHTML = '';
}

// ── Internal ──

function handleBoardRecreated(container) {
  createOverlay(container);
  // Re-render score overlays if analysis data exists
  const result = analysisResult.get();
  if (result && result.moves) {
    showScoreOverlays(result.moves, result.boardSize || 19);
  }
}

function createOverlay(container) {
  // Remove existing overlay if any
  if (overlaySvg && overlaySvg.parentNode) {
    overlaySvg.parentNode.removeChild(overlaySvg);
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
  }

  overlaySvg = document.createElementNS(NS, 'svg');
  overlaySvg.setAttribute('class', 'board-overlay');
  overlaySvg.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;';

  scoreGroup = document.createElementNS(NS, 'g');
  scoreGroup.setAttribute('class', 'score-overlays');
  overlaySvg.appendChild(scoreGroup);

  pvGroup = document.createElementNS(NS, 'g');
  pvGroup.setAttribute('class', 'pv-preview');
  overlaySvg.appendChild(pvGroup);

  // Place overlay inside .besogo-board (the div sized by fitBoard) so it
  // tracks the board square automatically — not inside #besogo-container
  // which is wider than the board when the window is landscape.
  const boardDiv = container.querySelector('.besogo-board') || container;
  boardDiv.style.position = 'relative'; // anchor for absolute overlay

  const boardSvg = boardDiv.querySelector('svg');
  if (boardSvg) {
    syncOverlayViewBox(boardSvg);
  }

  boardDiv.appendChild(overlaySvg);

  // Re-sync viewBox whenever the board div resizes (e.g. fitBoard)
  resizeObserver = new ResizeObserver(() => {
    const bs = boardDiv.querySelector('svg:not(.board-overlay)');
    if (bs) syncOverlayViewBox(bs);
  });
  resizeObserver.observe(boardDiv);
}

function syncOverlayViewBox(boardSvg) {
  if (!overlaySvg) return;
  // Copy BesoGo's viewBox so both SVGs share the same coordinate space.
  // The overlay already fills .besogo-board via CSS width/height:100%,
  // so no manual pixel positioning is needed.
  const viewBox = boardSvg.getAttribute('viewBox');
  if (viewBox) {
    overlaySvg.setAttribute('viewBox', viewBox);
  }
}

function onAnalysisUpdate(result) {
  if (!result || !result.moves || result.moves.length === 0) {
    clearOverlays();
    return;
  }
  showScoreOverlays(result.moves, result.boardSize || 19);
  annotateTreeNodes(result);
}

/**
 * Convert GTP board coordinates to pixel position in the overlay SVG.
 * x = column (0-indexed, 0=A), y = row (0-indexed, 0=top row in KataGo output)
 *
 * Uses BesoGo's exact coordinate constants (boardDisplay.js) so the overlay
 * aligns perfectly with the board grid.
 */
function gtpToPixel(x, y, boardSize) {
  if (!overlaySvg || x < 0 || y < 0) return null;

  // BesoGo constants (boardDisplay.js): CELL_SIZE=88, COORD_MARGIN=75, EXTRA_MARGIN=6
  const CELL_SIZE = 88;
  const BOARD_MARGIN = 75 + 6; // COORD_MARGIN + EXTRA_MARGIN (coord='western')

  // BesoGo svgPos(n) = BOARD_MARGIN + CELL_SIZE/2 + (n-1)*CELL_SIZE  (1-indexed)
  // Our x,y are 0-indexed, so n = x+1 → offset = BOARD_MARGIN + CELL_SIZE/2 + x*CELL_SIZE
  return {
    x: BOARD_MARGIN + CELL_SIZE / 2 + x * CELL_SIZE,
    y: BOARD_MARGIN + CELL_SIZE / 2 + y * CELL_SIZE,
    cellSize: CELL_SIZE,
  };
}

/**
 * Parse a GTP move string like "D4" to {x, y} board coordinates.
 */
function parseGtpMove(moveStr, boardSize) {
  if (!moveStr || moveStr.toLowerCase() === 'pass') return null;
  const col = moveStr[0].toUpperCase();
  const row = parseInt(moveStr.slice(1), 10);
  const colIdx = GTP_COLS.indexOf(col);
  if (colIdx < 0 || isNaN(row)) return null;
  const rowIdx = boardSize - row;
  return { x: colIdx, y: rowIdx };
}

function createSvgEl(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, String(v));
  }
  return el;
}

/**
 * T15: Annotate solution tree node SVG circles with score tooltips.
 * Adds <title> elements to tree node circles in #solution-tree-panel.
 */
function annotateTreeNodes(result) {
  const treePanel = document.getElementById('solution-tree-panel');
  if (!treePanel || !result || !result.moves) return;

  const boardSize = result.boardSize || 19;
  // Build a lookup from GTP move string to analysis data
  const moveLookup = {};
  result.moves.forEach((m, i) => {
    const gtp = gtpDisplayStr(m.x, m.y, boardSize);
    moveLookup[gtp] = m;
  });

  // Find tree node circles and add tooltips
  const circles = treePanel.querySelectorAll('circle');
  circles.forEach(circle => {
    const titleEl = circle.querySelector('title');
    // Check if this circle has associated move data
    // BesoGo tree nodes may have data attributes or we annotate all with top-level stats
    const tooltip = titleEl ? titleEl.textContent : '';
    if (!tooltip) {
      // Add aggregate analysis tooltip to tree node circles
      const topMove = result.moves[0];
      if (topMove) {
        const title = document.createElementNS(NS, 'title');
        const score = topMove.scoreLead > 0
          ? `+${topMove.scoreLead.toFixed(1)}`
          : topMove.scoreLead.toFixed(1);
        title.textContent = `Best: ${gtpDisplayStr(topMove.x, topMove.y, boardSize)} | Score: ${score} | Visits: ${topMove.visits} | Prior: ${(topMove.prior * 100).toFixed(1)}%`;
        circle.appendChild(title);
      }
    }
  });
}

function gtpDisplayStr(x, y, boardSize) {
  if (x < 0 || y < 0) return 'Pass';
  const col = GTP_COLS[x] || '?';
  const row = boardSize - y;
  return `${col}${row}`;
}
