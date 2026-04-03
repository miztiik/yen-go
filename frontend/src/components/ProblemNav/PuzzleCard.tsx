/**
 * Puzzle Card Component
 * @module components/ProblemNav/PuzzleCard
 *
 * Spec 118 - T3.1: PuzzleCard Component
 * Individual card in carousel navigation
 */

import type { JSX } from 'preact';

export type PuzzleCardStatus = 'unsolved' | 'correct' | 'wrong' | 'current';

export interface PuzzleCardProps {
  /** Card number (1-based) */
  number: number;
  /** Puzzle status */
  status: PuzzleCardStatus;
  /** Click handler */
  onClick?: () => void;
  /** Whether this is the current puzzle */
  isCurrent?: boolean;
}

/**
 * PuzzleCard - Individual card in carousel
 *
 * Features:
 * - Status indicator (○/✓/✗)
 * - Current card emphasis
 * - Click to navigate
 */
export function PuzzleCard({ number, status, onClick, isCurrent = false }: PuzzleCardProps): JSX.Element {
  const getStatusSymbol = (s: PuzzleCardStatus): string => {
    switch (s) {
      case 'correct':
        return '✓';
      case 'wrong':
        return '✗';
      case 'unsolved':
      case 'current':
      default:
        return '○';
    }
  };

  const getStatusClass = (s: PuzzleCardStatus): string => {
    switch (s) {
      case 'correct':
        return 'status-correct';
      case 'wrong':
        return 'status-wrong';
      case 'unsolved':
        return 'status-unsolved';
      case 'current':
        return 'status-current';
      default:
        return 'status-unsolved';
    }
  };

  return (
    <button
      className={`puzzle-card ${getStatusClass(status)} ${isCurrent ? 'is-current' : ''}`}
      onClick={onClick}
      role="tab"
      aria-label={`Puzzle ${number}${status === 'correct' ? ', completed' : status === 'wrong' ? ', incorrect' : ', unsolved'}`}
      aria-selected={isCurrent}
      aria-current={isCurrent ? 'true' : undefined}
      tabIndex={isCurrent ? 0 : -1}
    >
      <div className="card-number" aria-hidden="true">{number}</div>
      <div className="card-status" aria-hidden="true">{getStatusSymbol(status)}</div>
    </button>
  );
}

export default PuzzleCard;
