/**
 * StatusBar.tsx — Displays current player, analysis visits, score lead, winrate.
 */

import { currentPlayer, rootScoreLead, rootVisits, rootWinrate, isAnalyzing, modelName } from '../store/state';

export function StatusBar() {
  const player = currentPlayer.value;
  const score = rootScoreLead.value;
  const visits = rootVisits.value;
  const winrate = rootWinrate.value;

  return (
    <div class="status-bar">
      <span class="status-item">
        <strong>Turn:</strong> {player === 'B' ? 'Black' : 'White'}
      </span>
      {isAnalyzing.value && <span class="status-item status-analyzing">Analyzing...</span>}
      {score !== null && (
        <span class="status-item">
          <strong>Score:</strong>{' '}
          <span class={score > 0.5 ? 'score-positive' : score < -0.5 ? 'score-negative' : 'score-neutral'}>
            {score > 0 ? `B+${score.toFixed(1)}` : `W+${Math.abs(score).toFixed(1)}`}
          </span>
        </span>
      )}
      {winrate !== null && (
        <span class="status-item">
          <strong>Win:</strong> {(winrate * 100).toFixed(1)}%
        </span>
      )}
      {visits > 0 && (
        <span class="status-item">
          <strong>Visits:</strong> {visits}
        </span>
      )}
      <span class="status-item">
        <strong>Model:</strong> {modelName.value}
      </span>
    </div>
  );
}
