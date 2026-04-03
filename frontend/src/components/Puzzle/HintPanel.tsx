/**
 * Hint Panel Component
 * @module components/Puzzle/HintPanel
 *
 * Displays progressive hints for puzzle solving.
 *
 * Covers: FR-032 to FR-035, US5
 */

import { useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import { useHints, type UseHintsResult } from '../../hooks/useHints';
import type { Puzzle } from '../../models/puzzle';

/** Props for the HintPanel component */
export interface HintPanelProps {
  /** The puzzle containing hints */
  readonly puzzle: Puzzle | null;
  /** Whether hints are enabled */
  readonly enabled?: boolean;
  /** Callback when a hint is requested */
  readonly onHintRequested?: (hint: string, hintIndex: number) => void;
  /** Callback when hints are reset */
  readonly onHintsReset?: () => void;
  /** Whether to show in compact mode */
  readonly compact?: boolean;
  /** CSS class name */
  readonly className?: string;
}

/** Props for controlled hint panel (external state) */
export interface ControlledHintPanelProps {
  /** Hint state from useHints hook */
  readonly hintState: UseHintsResult;
  /** Callback when a hint is requested */
  readonly onHintRequested?: (hint: string, hintIndex: number) => void;
  /** Whether to show in compact mode */
  readonly compact?: boolean;
  /** CSS class name */
  readonly className?: string;
}

/**
 * Single hint card display
 */
function HintCard({
  hint,
  index,
  isLatest,
}: {
  hint: string;
  index: number;
  isLatest: boolean;
}): JSX.Element {
  return (
    <div
      className={`hint-card ${isLatest ? 'hint-card-latest' : ''}`}
      role="listitem"
      aria-label={`Hint ${index + 1}`}
      style={{
        padding: '0.75rem 1rem',
        marginBottom: '0.5rem',
        borderRadius: '8px',
        backgroundColor: isLatest ? '#fff3cd' : '#f8f9fa',
        border: isLatest ? '1px solid #ffc107' : '1px solid #e9ecef',
        animation: isLatest ? 'fadeIn 0.3s ease-in' : undefined,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.5rem',
        }}
      >
        <span
          className="hint-number"
          style={{
            fontWeight: 'bold',
            color: '#6c757d',
            minWidth: '1.5rem',
          }}
          aria-hidden="true"
        >
          {index + 1}.
        </span>
        <span className="hint-text">{hint}</span>
      </div>
    </div>
  );
}

/**
 * HintPanel - Display and request hints for a puzzle
 *
 * Uses internal useHints hook for state management.
 */
export function HintPanel({
  puzzle,
  enabled = true,
  onHintRequested,
  onHintsReset,
  compact = false,
  className,
}: HintPanelProps): JSX.Element | null {
  const hintState = useHints(puzzle, enabled);

  const handleRequestHint = useCallback(() => {
    const hint = hintState.requestHint();
    if (hint && onHintRequested) {
      onHintRequested(hint, hintState.hintsUsed);
    }
  }, [hintState, onHintRequested]);

  const handleReset = useCallback(() => {
    hintState.resetHints();
    if (onHintsReset) {
      onHintsReset();
    }
  }, [hintState, onHintsReset]);

  if (!enabled || !puzzle) {
    return null;
  }

  // T2.7: Stable layout - minimum height prevents layout shift when hints shown/hidden
  const minHeight = compact ? '80px' : '120px';

  return (
    <div
      className={`hint-panel ${compact ? 'hint-panel-compact' : ''} ${className ?? ''}`}
      role="region"
      aria-label="Puzzle hints"
      style={{
        padding: compact ? '0.5rem' : '1rem',
        borderRadius: '12px',
        backgroundColor: '#ffffff',
        border: '1px solid #dee2e6',
        maxWidth: compact ? '300px' : '400px',
        minHeight, // Reserve space to prevent CLS
        transition: 'opacity 0.2s ease', // Fade instead of height change
      }}
    >
      {/* Header */}
      <div
        className="hint-panel-header"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '0.75rem',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: compact ? '0.9rem' : '1.1rem',
            color: '#333',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <span aria-hidden="true">💡</span>
          Hints
          <span
            style={{
              fontSize: '0.8rem',
              color: '#6c757d',
              fontWeight: 'normal',
            }}
          >
            ({hintState.hintsUsed}/{hintState.totalHints})
          </span>
        </h3>
      </div>

      {/* Revealed hints */}
      {hintState.revealedHints.length > 0 && (
        <div
          className="hint-list"
          role="list"
          aria-label="Revealed hints"
          style={{
            marginBottom: '0.75rem',
            maxHeight: compact ? '150px' : '200px',
            overflowY: 'auto',
          }}
        >
          {hintState.revealedHints.map((hint, index) => (
            <HintCard
              key={index}
              hint={hint}
              index={index}
              isLatest={index === hintState.revealedHints.length - 1}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {hintState.revealedHints.length === 0 && (
        <p
          style={{
            margin: '0 0 0.75rem 0',
            color: '#6c757d',
            fontSize: '0.9rem',
            fontStyle: 'italic',
          }}
        >
          No hints used yet. Try solving it yourself first!
        </p>
      )}

      {/* Actions */}
      <div
        className="hint-actions"
        style={{
          display: 'flex',
          gap: '0.5rem',
          flexWrap: 'wrap',
        }}
      >
        <button
          type="button"
          onClick={handleRequestHint}
          disabled={!hintState.hasMoreHints}
          aria-label={
            hintState.hasMoreHints
              ? `Get hint ${hintState.hintsUsed + 1} of ${hintState.totalHints}`
              : 'No more hints available'
          }
          style={{
            padding: '0.5rem 1rem',
            fontSize: '0.9rem',
            borderRadius: '6px',
            border: 'none',
            backgroundColor: hintState.hasMoreHints ? '#4a90d9' : '#e9ecef',
            color: hintState.hasMoreHints ? '#ffffff' : '#6c757d',
            cursor: hintState.hasMoreHints ? 'pointer' : 'not-allowed',
            transition: 'background-color 0.2s',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
        >
          <span aria-hidden="true">💡</span>
          {hintState.hasMoreHints ? 'Get Hint' : 'No More Hints'}
        </button>

        {hintState.hintsUsed > 0 && (
          <button
            type="button"
            onClick={handleReset}
            aria-label="Reset all hints"
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.9rem',
              borderRadius: '6px',
              border: '1px solid #dee2e6',
              backgroundColor: 'transparent',
              color: '#6c757d',
              cursor: 'pointer',
              transition: 'background-color 0.2s',
            }}
          >
            Reset
          </button>
        )}
      </div>

      {/* Hint progress indicator */}
      {hintState.totalHints > 0 && (
        <div
          className="hint-progress"
          role="progressbar"
          aria-valuenow={hintState.hintsUsed}
          aria-valuemin={0}
          aria-valuemax={hintState.totalHints}
          aria-label={`${hintState.hintsUsed} of ${hintState.totalHints} hints used`}
          style={{
            marginTop: '0.75rem',
            height: '4px',
            backgroundColor: '#e9ecef',
            borderRadius: '2px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${(hintState.hintsUsed / hintState.totalHints) * 100}%`,
              height: '100%',
              backgroundColor: '#4a90d9',
              transition: 'width 0.3s ease',
            }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Controlled HintPanel - Use with external state management
 *
 * For cases where hint state needs to be shared across components.
 */
export function ControlledHintPanel({
  hintState,
  onHintRequested,
  compact = false,
  className,
}: ControlledHintPanelProps): JSX.Element {
  const handleRequestHint = useCallback(() => {
    const hint = hintState.requestHint();
    if (hint && onHintRequested) {
      onHintRequested(hint, hintState.hintsUsed);
    }
  }, [hintState, onHintRequested]);

  return (
    <div
      className={`hint-panel controlled ${compact ? 'hint-panel-compact' : ''} ${className ?? ''}`}
      role="region"
      aria-label="Puzzle hints"
      style={{
        padding: compact ? '0.5rem' : '1rem',
        borderRadius: '12px',
        backgroundColor: '#ffffff',
        border: '1px solid #dee2e6',
      }}
    >
      {/* Compact inline display for integration */}
      {compact ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <button
            type="button"
            onClick={handleRequestHint}
            disabled={!hintState.hasMoreHints}
            aria-label="Get hint"
            style={{
              padding: '0.5rem 0.75rem',
              fontSize: '0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: hintState.hasMoreHints ? '#4a90d9' : '#e9ecef',
              color: hintState.hasMoreHints ? '#ffffff' : '#6c757d',
              cursor: hintState.hasMoreHints ? 'pointer' : 'not-allowed',
            }}
          >
            💡 Hint ({hintState.hintsUsed}/{hintState.totalHints})
          </button>
          {hintState.revealedHints.length > 0 && (
            <span
              style={{
                fontSize: '0.85rem',
                color: '#333',
                flex: 1,
              }}
            >
              {hintState.revealedHints[hintState.revealedHints.length - 1]}
            </span>
          )}
        </div>
      ) : (
        // Full display (same as HintPanel)
        <>
          <div
            className="hint-panel-header"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: '0.75rem',
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
              💡 Hints ({hintState.hintsUsed}/{hintState.totalHints})
            </h3>
          </div>
          {hintState.revealedHints.length > 0 && (
            <div role="list" style={{ marginBottom: '0.75rem' }}>
              {hintState.revealedHints.map((hint, index) => (
                <HintCard
                  key={index}
                  hint={hint}
                  index={index}
                  isLatest={index === hintState.revealedHints.length - 1}
                />
              ))}
            </div>
          )}
          <button
            type="button"
            onClick={handleRequestHint}
            disabled={!hintState.hasMoreHints}
            aria-label="Get hint"
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: hintState.hasMoreHints ? '#4a90d9' : '#e9ecef',
              color: hintState.hasMoreHints ? '#ffffff' : '#6c757d',
              cursor: hintState.hasMoreHints ? 'pointer' : 'not-allowed',
            }}
          >
            {hintState.hasMoreHints ? 'Get Hint' : 'No More Hints'}
          </button>
        </>
      )}
    </div>
  );
}

export default HintPanel;
