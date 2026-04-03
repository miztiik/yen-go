/**
 * ExplanationPanel Component - Display move explanations
 * @module components/Puzzle/ExplanationPanel
 *
 * Covers: FR-038, US6
 *
 * Displays explanatory text for moves when available.
 */

import type { JSX } from 'preact';
import type { Explanation, Coordinate } from '@models/puzzle';

/** Props for ExplanationPanel component */
export interface ExplanationPanelProps {
  /** The current explanation to display */
  readonly explanation?: Explanation | null;
  /** Alternative: just the explanation text */
  readonly text?: string;
  /** Highlight points to show on board (for future use) */
  readonly highlightPoints?: readonly Coordinate[];
  /** Whether to show in compact mode */
  readonly compact?: boolean;
  /** CSS class name */
  readonly className?: string;
}

/**
 * ExplanationPanel - Display move explanations
 */
export function ExplanationPanel({
  explanation,
  text,
  highlightPoints,
  compact = false,
  className,
}: ExplanationPanelProps): JSX.Element | null {
  const displayText = explanation?.text ?? text;
  const points = explanation?.highlightPoints ?? highlightPoints;

  if (!displayText) {
    return null;
  }

  return (
    <div
      className={`explanation-panel ${compact ? 'explanation-panel-compact' : ''} ${className ?? ''}`}
      role="region"
      aria-label="Move explanation"
      style={{
        padding: compact ? '0.75rem' : '1rem',
        backgroundColor: '#f0f7ff',
        borderRadius: '8px',
        border: '1px solid #b3d7ff',
        marginTop: compact ? '0.5rem' : '1rem',
      }}
    >
      <div
        className="explanation-header"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          marginBottom: '0.5rem',
        }}
      >
        <span
          aria-hidden="true"
          style={{ fontSize: compact ? '1rem' : '1.25rem' }}
        >
          💡
        </span>
        <h4
          style={{
            margin: 0,
            fontSize: compact ? '0.85rem' : '0.95rem',
            fontWeight: 600,
            color: '#1a5fb4',
          }}
        >
          Explanation
        </h4>
      </div>

      <p
        className="explanation-text"
        style={{
          margin: 0,
          fontSize: compact ? '0.85rem' : '0.95rem',
          lineHeight: 1.6,
          color: '#333',
        }}
      >
        {displayText}
      </p>

      {points && points.length > 0 && (
        <div
          className="explanation-points"
          style={{
            marginTop: '0.5rem',
            fontSize: '0.8rem',
            color: '#6c757d',
          }}
        >
          Key points: {points.map((p, i) => (
            <span key={i}>
              {i > 0 && ', '}
              ({String.fromCharCode(65 + p.x)}{p.y + 1})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/** Props for ExplanationList component */
export interface ExplanationListProps {
  /** All explanations for the puzzle */
  readonly explanations: readonly Explanation[];
  /** Currently highlighted move index (optional) */
  readonly currentMoveIndex?: number;
  /** CSS class name */
  readonly className?: string;
}

/**
 * ExplanationList - Display all explanations with current highlighted
 */
export function ExplanationList({
  explanations,
  currentMoveIndex,
  className,
}: ExplanationListProps): JSX.Element | null {
  if (explanations.length === 0) {
    return null;
  }

  return (
    <div
      className={`explanation-list ${className ?? ''}`}
      role="list"
      aria-label="All move explanations"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.75rem',
      }}
    >
      {explanations.map((exp, index) => (
        <div
          key={`${exp.move.x}-${exp.move.y}`}
          className={`explanation-item ${index === currentMoveIndex ? 'explanation-item-current' : ''}`}
          role="listitem"
          aria-current={index === currentMoveIndex ? 'true' : undefined}
          style={{
            padding: '0.75rem',
            backgroundColor: index === currentMoveIndex ? '#fff3cd' : '#f8f9fa',
            borderRadius: '6px',
            border: index === currentMoveIndex ? '1px solid #ffc107' : '1px solid #e9ecef',
            transition: 'background-color 0.2s, border-color 0.2s',
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
              className="move-indicator"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '1.5rem',
                height: '1.5rem',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                backgroundColor: index === currentMoveIndex ? '#ffc107' : '#6c757d',
                color: index === currentMoveIndex ? '#000' : '#fff',
                borderRadius: '50%',
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              {index + 1}
            </span>
            <div>
              <div
                className="move-coords"
                style={{
                  fontSize: '0.75rem',
                  color: '#6c757d',
                  marginBottom: '0.25rem',
                }}
              >
                Move at ({String.fromCharCode(65 + exp.move.x)}{exp.move.y + 1})
              </div>
              <p
                style={{
                  margin: 0,
                  fontSize: '0.9rem',
                  lineHeight: 1.5,
                  color: '#333',
                }}
              >
                {exp.text}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/** Props for EmptyExplanation component */
export interface EmptyExplanationProps {
  /** Custom message to display */
  readonly message?: string;
  /** CSS class name */
  readonly className?: string;
}

/**
 * EmptyExplanation - Placeholder when no explanation is available
 */
export function EmptyExplanation({
  message = 'No explanation available for this move.',
  className,
}: EmptyExplanationProps): JSX.Element {
  return (
    <div
      className={`explanation-empty ${className ?? ''}`}
      role="status"
      aria-label="No explanation available"
      style={{
        padding: '1rem',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px',
        border: '1px solid #e9ecef',
        textAlign: 'center',
        color: '#6c757d',
        fontStyle: 'italic',
        fontSize: '0.9rem',
      }}
    >
      {message}
    </div>
  );
}

export default ExplanationPanel;
