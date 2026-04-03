/**
 * board.js — BesoGo-based board + tree integration.
 *
 * Uses besogo.create() for the full Go board with rules enforcement,
 * solution tree display, and SGF navigation — all in one widget.
 * After creation, the tree panel is DOM-relocated to the right panel
 * and the .besogo-panels container is hidden so the board fills its grid cell.
 */

import { sgfText } from './state.js';

let editor = null;       // BesoGo editor instance
let containerEl = null;   // DOM container
let postCreateCallbacks = []; // hooks called after each board recreation

/**
 * Initialize BesoGo board + tree inside the given container.
 * Loads the default SGF if present.
 */
export function initBoard(container) {
  containerEl = container;
  const sgf = sgfText.get();
  createBesoGo(container, sgf || undefined);
}

/**
 * (Re-)create BesoGo with a new SGF string.
 * Clears the container and rebuilds everything.
 */
export function loadSgf(sgfString) {
  if (!containerEl) return;
  createBesoGo(containerEl, sgfString);
}

/** Get the BesoGo editor instance (for external listeners, navigation, etc). */
export function getEditor() {
  return editor;
}

/** Register a callback to run after each BesoGo (re-)creation. Used by overlay module. */
export function onPostCreate(callback) {
  postCreateCallbacks.push(callback);
}

/** Get the board container element. */
export function getBoardContainer() {
  return containerEl;
}

/**
 * Get the current board position as an API-ready structure for /api/analyze.
 * Returns { board: string[][], boardSize: number } or null.
 */
export function getCurrentBoard() {
  if (!editor) return null;
  const current = editor.getCurrent();
  if (!current) return null;

  const root = editor.getRoot();
  const sizeX = root.getSize ? root.getSize().x : 19;
  const sizeY = root.getSize ? root.getSize().y : 19;
  const boardSize = sizeX;

  const board = [];
  for (let j = 1; j <= sizeY; j++) {  // rows (1-indexed in BesoGo)
    const row = [];
    for (let i = 1; i <= sizeX; i++) {  // cols
      const stone = current.getStone(i, j);
      row.push(stone === -1 ? 'black' : stone === 1 ? 'white' : null);
    }
    board.push(row);
  }
  return { board, boardSize };
}

// ── Internal ──

function createBesoGo(container, sgfString) {
  // Tear down: remove children and any window resize listeners
  container.innerHTML = '';
  // Strip the 'besogo-container' class that besogo.create appends as an init marker.
  container.className = container.className
    .split(/\s+/)
    .filter(c => c !== 'besogo-container')
    .join(' ');

  const options = {
    panels: ['tree'],
    coord: 'western',
    tool: 'auto',
    nokeys: true,        // We handle keys ourselves
    resize: 'fixed',     // We manage sizing via ResizeObserver
    shadows: 'off',
    variants: 0,         // Show child variants
  };

  if (sgfString && sgfString.trim().startsWith('(;')) {
    options.sgf = sgfString;
  }

  besogo.create(container, options);
  editor = container.besogoEditor || null;

  // Inject radial gradient defs for 3D stone appearance
  const svg = container.querySelector('svg');
  if (svg) {
    const ns = 'http://www.w3.org/2000/svg';
    let defs = svg.querySelector('defs');
    if (!defs) {
      defs = document.createElementNS(ns, 'defs');
      svg.insertBefore(defs, svg.firstChild);
    }

    function makeStop(offset, color) {
      const s = document.createElementNS(ns, 'stop');
      s.setAttribute('offset', offset);
      s.setAttribute('stop-color', color);
      return s;
    }

    // Black stone gradient (specular highlight)
    const gb = document.createElementNS(ns, 'radialGradient');
    gb.id = 'yen-grad-black';
    gb.setAttribute('cx', '0.35'); gb.setAttribute('cy', '0.35'); gb.setAttribute('r', '0.6');
    gb.appendChild(makeStop('0%', '#555'));
    gb.appendChild(makeStop('50%', '#222'));
    gb.appendChild(makeStop('100%', '#0a0a0a'));
    defs.appendChild(gb);

    // White stone gradient (subtle shadow)
    const gw = document.createElementNS(ns, 'radialGradient');
    gw.id = 'yen-grad-white';
    gw.setAttribute('cx', '0.35'); gw.setAttribute('cy', '0.35'); gw.setAttribute('r', '0.6');
    gw.appendChild(makeStop('0%', '#fff'));
    gw.appendChild(makeStop('70%', '#e8e8e8'));
    gw.appendChild(makeStop('100%', '#c8c8c8'));
    defs.appendChild(gw);
  }

  // T5: Relocate the tree panel to the right panel (re-done after every board recreation)
  const treePanel = document.getElementById('solution-tree-panel');
  const panelsDiv = container.querySelector('.besogo-panels');
  if (panelsDiv && treePanel) {
    const treeEl = panelsDiv.querySelector('.besogo-tree');
    if (treeEl) {
      treePanel.innerHTML = '';
      treePanel.appendChild(treeEl);
    }
    // T8: Remove the emptied .besogo-panels from the DOM entirely.
    // BesoGo's fill-mode resizer allocates ~350px for panelsDiv when
    // it's truthy, even if hidden. Removing it from the DOM prevents
    // visual impact. The resizer still holds a reference but setting
    // styles on a detached node is harmless.
    panelsDiv.remove();
  }

  // After removing panels, the board div should fill the container.
  // We use resize:'fixed' + ResizeObserver so there's no BesoGo
  // internal resizer fighting us. The board square fills 100% of the
  // available container dimension (min of width/height).
  const boardDiv = container.querySelector('.besogo-board');
  if (boardDiv) {
    const fitBoard = () => {
      const rect = container.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) return;
      const side = Math.floor(Math.min(rect.width, rect.height));
      boardDiv.style.width = side + 'px';
      boardDiv.style.height = side + 'px';
      // Also resize the SVG viewbox to match
      const bsvg = boardDiv.querySelector('svg');
      if (bsvg) {
        bsvg.setAttribute('width', side);
        bsvg.setAttribute('height', side);
      }
    };
    // Use ResizeObserver for reliable sizing on layout changes
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => requestAnimationFrame(fitBoard));
      ro.observe(container);
    }
    window.addEventListener('resize', () => requestAnimationFrame(fitBoard));
    // Initial fit after layout settles
    requestAnimationFrame(fitBoard);
  }

  // Notify registered callbacks (overlay re-attachment, etc.)
  postCreateCallbacks.forEach(cb => cb(container));
}
