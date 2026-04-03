/**
 * Explanation component for displaying move explanations.
 * Shows contextual information about the current move in review mode.
 * @module components/Review/Explanation
 */

import type { FunctionalComponent } from 'preact';
import type { ReviewMove } from '../../lib/review/controller';
import './Explanation.css';

/**
 * Props for Explanation component.
 */
export interface ExplanationProps {
  /** Current move (null if at initial position) */
  move: ReviewMove | null;
  /** Move number for display */
  moveNumber: number;
  /** Total moves in the solution */
  totalMoves: number;
  /** Optional CSS class */
  className?: string;
}

/**
 * Format the move coordinate for display.
 */
function formatCoordinate(coord: string): string {
  // Convert SGF coordinates to display format
  // SGF uses a-s (lowercase), we convert to A-T (uppercase, excluding I)
  const col = coord.charCodeAt(0) - 'a'.charCodeAt(0);
  const row = coord.charCodeAt(1) - 'a'.charCodeAt(0);

  // Standard Go notation uses letters A-T (no I) for columns
  const colLetter = String.fromCharCode('A'.charCodeAt(0) + col + (col >= 8 ? 1 : 0));
  // Rows are numbered from bottom (19 = top in standard 19x19)
  const rowNumber = 19 - row;

  return `${colLetter}${rowNumber}`;
}

/**
 * Move explanation display component.
 */
export const Explanation: FunctionalComponent<ExplanationProps> = ({
  move,
  moveNumber,
  totalMoves,
  className = '',
}) => {
  // Initial position state
  if (!move) {
    return (
      <div className={`explanation explanation--initial ${className}`}>
        <p className="explanation__text">
          Initial position. Use the controls to step through the solution.
        </p>
        <p className="explanation__hint">
          Press → or click Next to see the first move.
        </p>
      </div>
    );
  }

  const colorName = move.color === 'B' ? 'Black' : 'White';
  const coordinate = formatCoordinate(move.coord);
  const isLastMove = moveNumber === totalMoves;

  return (
    <div className={`explanation ${isLastMove ? 'explanation--complete' : ''} ${className}`}>
      <div className="explanation__header">
        <span className="explanation__move-info">
          <span className={`explanation__color explanation__color--${move.color.toLowerCase()}`}>
            {colorName}
          </span>
          <span className="explanation__coordinate">{coordinate}</span>
        </span>
        <span className="explanation__move-number">
          Move {moveNumber}/{totalMoves}
        </span>
      </div>

      {move.explanation && (
        <p className="explanation__text">{move.explanation}</p>
      )}

      {isLastMove && (
        <div className="explanation__complete">
          <span className="explanation__complete-icon" aria-hidden="true">✓</span>
          <span className="explanation__complete-text">Solution complete!</span>
        </div>
      )}
    </div>
  );
};

export default Explanation;
