/**
 * AnalysisTable.tsx — Sortable table of candidate moves (Order, Move, Prior, Score, Visits, PV).
 */

import { candidateMoves, boardMat } from '../store/state';
import type { CandidateMove } from '../types';

interface Props {
  onMoveHover?: (move: CandidateMove | null) => void;
}

/** Convert SGF coord to human-readable (e.g. "dd" → "D16" for 19x19) */
function sgfToDisplay(sgf: string, boardSize: number): string {
  if (sgf === 'tt' || sgf === '') return 'Pass';
  const x = sgf.charCodeAt(0) - 97;
  const y = sgf.charCodeAt(1) - 97;
  const col = 'ABCDEFGHJKLMNOPQRST'[x] ?? '?';
  const row = boardSize - y;
  return `${col}${row}`;
}

export function AnalysisTable({ onMoveHover }: Props) {
  const moves = candidateMoves.value;
  const bs = boardMat.value.length || 19;

  if (moves.length === 0) {
    return <div class="analysis-table-empty">No analysis results</div>;
  }

  return (
    <div class="analysis-table-container">
      <table class="analysis-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Move</th>
            <th>Prior</th>
            <th>Win%</th>
            <th>Score</th>
            <th>Visits</th>
            <th>PV</th>
          </tr>
        </thead>
        <tbody>
          {moves.map((m, i) => (
            <tr
              key={m.move}
              onMouseEnter={() => onMoveHover?.(m)}
              onMouseLeave={() => onMoveHover?.(null)}
              class="analysis-row"
            >
              <td>{i + 1}</td>
              <td class="move-col">{sgfToDisplay(m.move, bs)}</td>
              <td>{(m.prior * 100).toFixed(1)}%</td>
              <td>{(m.winrate * 100).toFixed(1)}%</td>
              <td class={m.scoreLead > 0.5 ? 'score-positive' : m.scoreLead < -0.5 ? 'score-negative' : 'score-neutral'}>
                {m.scoreLead > 0 ? `+${m.scoreLead.toFixed(1)}` : m.scoreLead.toFixed(1)}
              </td>
              <td>{m.visits}</td>
              <td class="pv-col">{m.pv.slice(0, 5).map((p, j) => <span key={j} class="pv-move">{sgfToDisplay(p, bs)}</span>)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
