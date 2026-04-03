/**
 * analysis-bridge.ts — Normalize engine.worker.ts AnalysisPayload → AnalysisResult.
 */

import type { AnalysisResult } from '../types';
import type { AnalysisPayload } from './engine.worker';

/** Convert flat index → SGF coordinate (e.g., 0,0 → "aa") */
function toSgfCoord(x: number, y: number): string {
  if (x < 0 || y < 0) return 'tt'; // pass
  return String.fromCharCode(97 + x) + String.fromCharCode(97 + y);
}

/**
 * Convert a GTP coordinate (e.g. "D4", "Q16") to an SGF coordinate (e.g. "dd", "qq").
 * GTP uses 1-based rows from bottom, letters A-T skipping I.
 */
export function gtpToSgf(gtp: string, boardSize: number = 19): string {
  if (!gtp || gtp.toLowerCase() === 'pass') return 'tt';
  const col = gtp[0].toUpperCase();
  const row = parseInt(gtp.slice(1), 10);
  // GTP columns: A=0, B=1, ..., H=7, J=8 (I is skipped)
  let x = col.charCodeAt(0) - 65; // A=0
  if (x > 7) x--; // skip I
  // GTP rows: 1=bottom → SGF y = boardSize - row
  const y = boardSize - row;
  if (x < 0 || x >= boardSize || y < 0 || y >= boardSize) return 'tt';
  return String.fromCharCode(97 + x) + String.fromCharCode(97 + y);
}

/** Normalize a TF.js worker analysis payload to the GUI's AnalysisResult */
export function normalizeWorkerAnalysis(payload: AnalysisPayload, boardSize: number = 19): AnalysisResult {
  return {
    moveInfos: payload.moves.map((m, i) => ({
      move: toSgfCoord(m.x, m.y),
      x: m.x,
      y: m.y,
      prior: m.prior,
      winrate: m.winRate,
      scoreLead: m.scoreLead,
      visits: m.visits,
      order: m.order ?? i,
      pv: (m.pv ?? []).map(coord => {
        // PV coords from KataGo MCTS are GTP strings (e.g. "D4")
        if (coord.length >= 2 && coord[0] >= 'A' && coord[0] <= 'T') {
          return gtpToSgf(coord, boardSize);
        }
        return coord; // already SGF
      }),
    })),
    rootInfo: {
      currentPlayer: 'B', // Caller should override if needed
      scoreLead: payload.rootScoreLead,
      visits: payload.rootVisits,
      winrate: payload.rootWinRate,
    },
    ownership: payload.ownership,
    policy: payload.policy,
  };
}
