/**
 * Explore Mode Controls Component
 * @module components/Review/ExploreControls
 *
 * Provides controls for explore mode (FR-007, FR-008, FR-009, FR-010).
 * Shows valid/invalid moves, allows move exploration, returns to solution.
 *
 * Constitution Compliance:
 * - V. No Browser AI: Uses pre-computed solution tree only
 * - IX. Accessibility: Clear feedback, keyboard support
 */

import type { JSX } from 'preact';
import type { ExploreModeState, ExploreHint } from '@models/SolutionPresentation';

/**
 * Props for ExploreControls component.
 */
export interface ExploreControlsProps {
  /** Current explore mode state */
  state: ExploreModeState;
  /** Toggle explore mode callback */
  onToggle: () => void;
  /** Make move callback (for testing a move) */
  onMakeMove?: (coord: { x: number; y: number }) => void;
  /** Undo last exploration move callback */
  onUndo?: () => void;
  /** Return to solution callback */
  onReturnToSolution?: () => void;
  /** Whether controls are disabled */
  disabled?: boolean;
  /** CSS class override */
  className?: string;
  /** Compact mode */
  compact?: boolean;
}

/**
 * Icons for explore controls.
 */
const ExploreIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M8 4v4h4" fill="none" stroke="currentColor" strokeWidth="2" />
  </svg>
);

const UndoIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M2 8l4-4v3h4a4 4 0 0 1 0 8H6v-2h4a2 2 0 0 0 0-4H6v3l-4-4z" />
  </svg>
);

const ReturnIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M7 2l-5 6 5 6v-4h6V6H7V2z" />
  </svg>
);

/**
 * ExploreStatusBadge - shows current exploration status.
 */
function ExploreStatusBadge({
  isActive,
  depth,
  isOnSolution,
}: {
  isActive: boolean;
  depth: number;
  isOnSolution: boolean;
}): JSX.Element | null {
  if (!isActive) {
    return null;
  }

  const statusText = isOnSolution
    ? 'On solution path'
    : depth > 0
    ? `Exploring (${depth} moves)`
    : 'Ready to explore';

  const statusClass = isOnSolution
    ? 'explore-status--on-path'
    : 'explore-status--exploring';

  return (
    <span className={`explore-status ${statusClass}`} aria-live="polite">
      {statusText}
    </span>
  );
}

/**
 * HintLegend - shows what the hint markers mean.
 */
function HintLegend({
  colorblindMode: _colorblindMode,
}: {
  colorblindMode?: boolean | undefined;
}): JSX.Element {
  return (
    <div className="explore-legend" aria-label="Move hint legend">
      <span className="explore-legend__item explore-legend__item--valid">
        <span className="explore-legend__marker" aria-hidden="true">●</span>
        <span className="explore-legend__text">Correct</span>
      </span>
      <span className="explore-legend__item explore-legend__item--invalid">
        <span className="explore-legend__marker" aria-hidden="true">✕</span>
        <span className="explore-legend__text">Wrong</span>
      </span>
    </div>
  );
}

/**
 * ExploreControls component - controls for explore mode.
 */
export function ExploreControls({
  state,
  onToggle,
  onUndo,
  onReturnToSolution,
  disabled = false,
  className,
  compact = false,
}: ExploreControlsProps): JSX.Element {
  const { isActive, exploreDepth, hints, isOnSolutionPath } = state;

  const validMoves = hints.filter((h: ExploreHint) => h.isValid).length;
  const invalidMoves = hints.filter((h: ExploreHint) => !h.isValid).length;

  return (
    <div
      className={`explore-controls ${compact ? 'explore-controls--compact' : ''} ${className ?? ''}`}
      role="group"
      aria-label="Explore mode controls"
    >
      {/* Toggle explore mode */}
      <button
        type="button"
        className={`explore-controls__btn ${isActive ? 'explore-controls__btn--active' : ''}`}
        onClick={onToggle}
        disabled={disabled}
        aria-label={isActive ? 'Exit explore mode' : 'Enter explore mode'}
        aria-pressed={isActive}
        title={isActive ? 'Exit explore (E)' : 'Explore variations (E)'}
      >
        <ExploreIcon />
        {!compact && (
          <span className="explore-controls__label">
            {isActive ? 'Exit' : 'Explore'}
          </span>
        )}
      </button>

      {/* Only show these when exploring */}
      {isActive && (
        <>
          {/* Undo */}
          {onUndo && exploreDepth > 0 && (
            <button
              type="button"
              className="explore-controls__btn"
              onClick={onUndo}
              disabled={disabled || exploreDepth === 0}
              aria-label="Undo exploration move"
              title="Undo (Z)"
            >
              <UndoIcon />
            </button>
          )}

          {/* Return to solution */}
          {onReturnToSolution && !isOnSolutionPath && (
            <button
              type="button"
              className="explore-controls__btn"
              onClick={onReturnToSolution}
              disabled={disabled}
              aria-label="Return to solution path"
              title="Back to solution (Esc)"
            >
              <ReturnIcon />
              {!compact && <span className="explore-controls__label">Back</span>}
            </button>
          )}

          {/* Status badge */}
          <ExploreStatusBadge
            isActive={isActive}
            depth={exploreDepth}
            isOnSolution={isOnSolutionPath}
          />

          {/* Move count info */}
          {!compact && hints.length > 0 && (
            <span className="explore-controls__hint-count">
              <span className="explore-controls__valid-count">{validMoves} valid</span>
              {' / '}
              <span className="explore-controls__invalid-count">{invalidMoves} wrong</span>
            </span>
          )}
        </>
      )}
    </div>
  );
}

/**
 * ExplorePanel - expanded panel with legend and detailed info.
 */
export function ExplorePanel({
  state,
  colorblindMode,
  className,
}: {
  state: ExploreModeState;
  colorblindMode?: boolean | undefined;
  className?: string;
}): JSX.Element | null {
  if (!state.isActive) {
    return null;
  }

  return (
    <div className={`explore-panel ${className ?? ''}`} role="complementary">
      <HintLegend colorblindMode={colorblindMode ?? false} />
      <p className="explore-panel__instructions">
        Click on a highlighted point to explore that move.
        Green/blue points follow the correct solution.
        Red/orange points lead to failure.
      </p>
    </div>
  );
}

export default ExploreControls;
