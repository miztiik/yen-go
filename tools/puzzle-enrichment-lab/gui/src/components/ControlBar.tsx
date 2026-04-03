/**
 * ControlBar.tsx — Start Analysis / Clear / Hide Analysis / Show Frame buttons.
 */

import { showAnalysis, showFrame, isAnalyzing, analysisResult, boardMat, boardSize, currentPlayer, engineError, framedMat } from '../store/state';
import { analyze, cancelAnalysis } from '../engine/engine-manager';

export function ControlBar() {
  const handleStartAnalysis = async () => {
    if (boardMat.value.length === 0) return;
    // Auto-enable tsumego frame so the engine focuses on the puzzle region
    showFrame.value = true;
    const mat = framedMat.value;

    // Convert number[][] to BoardState (Intersection[][])
    const board = mat.map(row =>
      row.map(cell => {
        if (cell === 1) return 'black' as const;
        if (cell === -1) return 'white' as const;
        return null;
      })
    );

    try {
      await analyze(board, currentPlayer.value === 'B' ? 'black' : 'white', boardSize.value);
      showAnalysis.value = true;
    } catch {
      // Error is already stored in engineError signal
    }
  };

  const handleClear = () => {
    cancelAnalysis();
    showAnalysis.value = false;
  };

  const handleToggleAnalysis = () => {
    showAnalysis.value = !showAnalysis.value;
  };

  const handleToggleFrame = () => {
    showFrame.value = !showFrame.value;
  };

  return (
    <div class="control-bar">
      {engineError.value && (
        <div class="error-banner" onClick={() => { engineError.value = null; }}>
          {engineError.value}
        </div>
      )}
      <button
        onClick={handleStartAnalysis}
        disabled={isAnalyzing.value || boardMat.value.length === 0}
        class="btn btn-primary"
      >
        {isAnalyzing.value ? 'Analyzing...' : 'Start Analysis'}
      </button>

      <button
        onClick={handleClear}
        disabled={!analysisResult.value && !isAnalyzing.value}
        class="btn"
      >
        Clear
      </button>

      <button
        onClick={handleToggleAnalysis}
        disabled={!analysisResult.value}
        class="btn"
      >
        {showAnalysis.value ? 'Hide Analysis' : 'Show Analysis'}
      </button>

      <button
        onClick={handleToggleFrame}
        class="btn"
      >
        {showFrame.value ? 'Hide Frame' : 'Show Frame'}
      </button>
    </div>
  );
}
