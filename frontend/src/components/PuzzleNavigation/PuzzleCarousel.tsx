/**
 * PuzzleCarousel Component
 * @module components/PuzzleNavigation/PuzzleCarousel
 *
 * Bottom navigation carousel for puzzle collections.
 * Shows circular indicators for each puzzle with status.
 *
 * Covers: FR-008, FR-010, FR-011
 */

import type { JSX } from 'preact';
import { useRef, useEffect } from 'preact/hooks';

export type PuzzleStatus = 'unsolved' | 'correct' | 'incorrect' | 'current';

export interface PuzzleIndicator {
  /** Puzzle index */
  index: number;
  /** Puzzle ID */
  id: string;
  /** Status of the puzzle */
  status: PuzzleStatus;
}

export interface PuzzleCarouselProps {
  /** Puzzle indicators */
  puzzles: PuzzleIndicator[];
  /** Current puzzle index */
  currentIndex: number;
  /** Handler when a puzzle is clicked */
  onPuzzleClick: (index: number) => void;
  /** Whether to auto-scroll to current */
  autoScrollToCurrent?: boolean | undefined;
  /** Size of indicators */
  size?: 'sm' | 'md' | 'lg' | undefined;
}

const sizeConfig: Record<'sm' | 'md' | 'lg', { diameter: number; gap: number; fontSize: string }> =
  {
    sm: { diameter: 24, gap: 4, fontSize: '0.625rem' },
    md: { diameter: 32, gap: 6, fontSize: '0.75rem' },
    lg: { diameter: 40, gap: 8, fontSize: '0.875rem' },
  };

/**
 * Get indicator style based on status
 */
function getStatusStyle(status: PuzzleStatus, isCurrent: boolean, size: number): JSX.CSSProperties {
  const baseStyle: JSX.CSSProperties = {
    width: `${size}px`,
    height: `${size}px`,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    flexShrink: 0,
    fontWeight: isCurrent ? 600 : 400,
  };

  if (isCurrent) {
    return {
      ...baseStyle,
      backgroundColor: 'var(--color-info-solid)',
      color: 'white',
      boxShadow: '0 0 0 3px rgba(66, 153, 225, 0.3)',
      transform: 'scale(1.1)',
    };
  }

  switch (status) {
    case 'correct':
      return {
        ...baseStyle,
        backgroundColor: 'var(--color-success-bg-solid)',
        color: 'var(--color-success-text)',
        border: '2px solid var(--color-success-solid)',
      };
    case 'incorrect':
      return {
        ...baseStyle,
        backgroundColor: 'var(--color-level-low-dan-bg)',
        color: 'var(--color-error)',
        border: '2px solid var(--color-error)',
      };
    case 'unsolved':
    default:
      return {
        ...baseStyle,
        backgroundColor: 'var(--color-neutral-100)',
        color: 'var(--color-neutral-500)',
        border: '1px solid var(--color-neutral-200)',
      };
  }
}

/**
 * Get indicator content based on status
 */
function getIndicatorContent(index: number, status: PuzzleStatus, isCurrent: boolean): string {
  if (isCurrent) {
    return String(index + 1);
  }
  switch (status) {
    case 'correct':
      return '✓';
    case 'incorrect':
      return '✗';
    default:
      return String(index + 1);
  }
}

/**
 * Horizontal carousel of puzzle indicators
 */
export function PuzzleCarousel({
  puzzles,
  currentIndex,
  onPuzzleClick,
  autoScrollToCurrent = true,
  size = 'md',
}: PuzzleCarouselProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const currentRef = useRef<HTMLButtonElement>(null);

  const config = sizeConfig[size];

  // Auto-scroll to current puzzle
  useEffect(() => {
    if (autoScrollToCurrent && currentRef.current && containerRef.current) {
      const container = containerRef.current;
      const current = currentRef.current;
      const containerWidth = container.offsetWidth;
      const currentLeft = current.offsetLeft;
      const currentWidth = current.offsetWidth;

      // Center the current indicator
      const scrollLeft = currentLeft - containerWidth / 2 + currentWidth / 2;
      if (typeof container.scrollTo === 'function') {
        container.scrollTo({ left: scrollLeft, behavior: 'smooth' });
      } else {
        container.scrollLeft = scrollLeft;
      }
    }
  }, [currentIndex, autoScrollToCurrent]);

  const containerStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: `${config.gap}px`,
    overflowX: 'auto',
    padding: '0.75rem 1rem',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    scrollbarWidth: 'none',
    msOverflowStyle: 'none',
  };

  return (
    <div ref={containerRef} style={containerStyle} role="navigation" aria-label="Puzzle navigation">
      {puzzles.map((puzzle, i) => {
        const isCurrent = i === currentIndex;
        return (
          <button
            key={puzzle.id}
            ref={isCurrent ? currentRef : null}
            type="button"
            style={{
              ...getStatusStyle(puzzle.status, isCurrent, config.diameter),
              fontSize: config.fontSize,
              border: 'none',
              padding: 0,
            }}
            onClick={() => onPuzzleClick(i)}
            aria-label={`Puzzle ${i + 1}${isCurrent ? ' (current)' : ''}, ${puzzle.status}`}
            aria-current={isCurrent ? 'step' : undefined}
          >
            {getIndicatorContent(i, puzzle.status, isCurrent)}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Summary bar showing progress
 */
export interface ProgressSummaryBarProps {
  /** Total puzzles */
  total: number;
  /** Correct count */
  correct: number;
  /** Incorrect count */
  incorrect: number;
  /** Current puzzle number (1-based) */
  currentNumber: number;
}

export function ProgressSummaryBar({
  total,
  correct,
  incorrect,
  currentNumber,
}: ProgressSummaryBarProps): JSX.Element {
  const barStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.5rem 1rem',
    fontSize: '0.75rem',
    color: 'var(--color-neutral-600)',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '8px',
    marginBottom: '0.5rem',
  };

  const statStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: '0.25rem',
  };

  return (
    <div style={barStyle}>
      <span style={statStyle}>
        <strong>{currentNumber}</strong> / {total}
      </span>
      <span style={{ ...statStyle, color: 'var(--color-success-solid)' }}>✓ {correct}</span>
      <span style={{ ...statStyle, color: 'var(--color-error)' }}>✗ {incorrect}</span>
    </div>
  );
}

export default PuzzleCarousel;
