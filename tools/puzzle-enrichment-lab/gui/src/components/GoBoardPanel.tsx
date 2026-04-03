/**
 * GoBoardPanel.tsx — GhostBan-based Go board with analysis dots overlay.
 *
 * GhostBan renders stones/grid on a canvas. We overlay a second canvas
 * for analysis visualization (colored dots showing candidate moves).
 */

import { useEffect, useRef } from 'preact/hooks';
import { GhostBan, Ki, Theme } from 'ghostban';
import { boardMat, boardSize, currentPlayer, analysisResult, showAnalysis, hoveredPV, showFrame, framedMat } from '../store/state';
import { computeFrame } from '../lib/frame';
import type { CandidateMove } from '../types';

/** Read GhostBan's actual grid geometry, scaled to overlay canvas size. */
function getGridGeometry(gb: GhostBan, overlayWidth: number) {
  const { space, scaledPadding } = gb.calcSpaceAndPadding();
  const gbWidth = gb.canvas?.width ?? overlayWidth;
  const scale = overlayWidth / gbWidth;
  return { padding: scaledPadding * scale, cellSize: space * scale };
}

interface Props {
  onIntersectionClick?: (x: number, y: number) => void;
}

/** Color for analysis dots based on score loss relative to top move (GoProblems palette) */
function dotColor(move: CandidateMove, topScore: number): string {
  const loss = Math.abs((topScore - move.scoreLead));
  if (loss < 0.5) return '#4caf50'; // green — best
  if (loss < 2) return '#66bb6a'; // light green — good
  if (loss < 5) return '#fdd835'; // yellow — ok
  return '#ef5350'; // red — bad
}

function dotAlpha(move: CandidateMove, topVisits: number): number {
  const ratio = topVisits > 0 ? move.visits / topVisits : 0;
  return Math.max(0.45, Math.min(0.92, 0.3 + ratio * 0.62));
}

export function GoBoardPanel({ onIntersectionClick }: Props) {
  const boardRef = useRef<HTMLDivElement>(null);
  const gbRef = useRef<GhostBan | null>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);

  // Initialize GhostBan once
  useEffect(() => {
    if (!boardRef.current) return;
    const gb = new GhostBan({
      boardSize: boardSize.value,
      size: 560,
      interactive: true,
      coordinate: true,
      padding: 18,
      extend: 2,
    });
    gb.init(boardRef.current);
    // Must NOT set theme in constructor — setTheme early-exits if already matching.
    // setTheme loads board/stone images async, then re-renders.
    gb.setTheme(Theme.Subdued);
    gbRef.current = gb;

    // Detect clicks via GhostBan cursor
    const handler = () => {
      const gb = gbRef.current;
      if (!gb || !onIntersectionClick) return;
      const [x, y] = gb.cursor;
      if (x >= 0 && y >= 0 && x < boardSize.value && y < boardSize.value) {
        onIntersectionClick(x, y);
      }
    };
    boardRef.current.addEventListener('click', handler);
    return () => {
      boardRef.current?.removeEventListener('click', handler);
    };
  }, []);

  // Re-render board when mat changes (use framed board when frame is active)
  useEffect(() => {
    const gb = gbRef.current;
    if (!gb) return;
    const mat = showFrame.value ? framedMat.value : boardMat.value;
    if (mat.length > 0) {
      // GhostBan uses mat[col][row] (column-major), our data is mat[row][col]
      const transposed = mat[0].map((_, x) => mat.map(row => row[x]));
      gb.render(transposed);
    }
  }, [boardMat.value, showFrame.value]);

  // Unified overlay: analysis dots + PV stones + frame dimming.
  // Consolidated into one effect so streaming analysis updates don't wipe the frame.
  useEffect(() => {
    const canvas = overlayRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const size = canvas.width;
    ctx.clearRect(0, 0, size, size);

    const bs = boardSize.value;
    const gb = gbRef.current;
    if (!gb) return;
    const { padding, cellSize } = getGridGeometry(gb, size);

    // 1. Draw frame dimming (behind everything)
    if (showFrame.value && boardMat.value.length > 0) {
      const frame = computeFrame(boardMat.value);
      // Fill the entire overlay with a dim wash, then clear the inside-frame area.
      ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      ctx.fillRect(0, 0, size, size);

      // Cut out the frame region
      for (let y = 0; y < bs; y++) {
        for (let x = 0; x < bs; x++) {
          if (frame[y]?.[x]) {
            const cx = padding + x * cellSize;
            const cy = padding + y * cellSize;
            ctx.clearRect(cx - cellSize / 2, cy - cellSize / 2, cellSize, cellSize);
          }
        }
      }
    }

    // 2. Draw analysis dots (GoProblems-style: score + visits, sized by visits)
    if (showAnalysis.value && analysisResult.value) {
      const moves = analysisResult.value.moveInfos;
      const topScore = moves[0]?.scoreLead ?? 0;
      const topVisits = moves[0]?.visits ?? 1;
      for (const move of moves.slice(0, 10)) {
        if (move.x < 0 || move.y < 0) continue;
        const cx = padding + move.x * cellSize;
        const cy = padding + move.y * cellSize;
        const visitRatio = topVisits > 0 ? move.visits / topVisits : 0;
        const radius = cellSize * (0.28 + visitRatio * 0.15);
        const color = dotColor(move, topScore);
        const alpha = dotAlpha(move, topVisits);

        // Filled circle
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.globalAlpha = alpha;
        ctx.fill();

        // Border ring
        ctx.globalAlpha = Math.min(1, alpha + 0.2);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Score lead text (top line)
        ctx.globalAlpha = 1;
        const scoreTxt = move.scoreLead >= 0 ? `+${move.scoreLead.toFixed(1)}` : move.scoreLead.toFixed(1);
        const fontSize = Math.max(9, radius * 0.55);
        ctx.font = `bold ${fontSize}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#fff';
        ctx.fillText(scoreTxt, cx, cy - fontSize * 0.45);

        // Visit count (bottom line)
        ctx.font = `${Math.max(8, fontSize * 0.85)}px sans-serif`;
        ctx.fillText(String(move.visits), cx, cy + fontSize * 0.55);
      }
    }

    // 3. Draw PV stones on top
    const pv = hoveredPV.value;
    if (pv.length > 0) {
      let turn = currentPlayer.value === 'B' ? 1 : -1;
      for (let i = 0; i < pv.length; i++) {
        const coord = pv[i];
        if (!coord || coord === 'tt' || coord.length < 2) continue;
        const x = coord.charCodeAt(0) - 97;
        const y = coord.charCodeAt(1) - 97;
        if (x < 0 || x >= bs || y < 0 || y >= bs) continue;

        const cx = padding + x * cellSize;
        const cy = padding + y * cellSize;
        const radius = cellSize * 0.42;

        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = turn === 1 ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.6)';
        ctx.fill();
        ctx.strokeStyle = '#888';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = turn === 1 ? '#fff' : '#000';
        ctx.font = `bold ${Math.max(11, radius * 0.7)}px sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(String(i + 1), cx, cy);

        turn *= -1;
      }
    }
  }, [analysisResult.value, showAnalysis.value, boardSize.value, hoveredPV.value, currentPlayer.value, showFrame.value, boardMat.value]);

  return (
    <div class="go-board-panel" style={{ position: 'relative', display: 'inline-block' }}>
      <div ref={boardRef} class="go-board-container" />
      <canvas
        ref={overlayRef}
        class="analysis-overlay"
        width={560}
        height={560}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '560px',
          height: '560px',
          pointerEvents: 'none',
        }}
      />
    </div>
  );
}
