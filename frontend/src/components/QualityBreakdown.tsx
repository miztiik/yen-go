/**
 * QualityBreakdown component showing puzzle quality level factors.
 * 
 * Displays why a puzzle has its quality rating with checkmarks/X for requirements.
 * 
 * @module components/QualityBreakdown
 */

import { FunctionalComponent } from 'preact';
import { useState } from 'preact/hooks';
import { PuzzleQualityLevel, QualityMetrics, PUZZLE_QUALITY_INFO } from '@/lib/quality/config';
import { StarDisplay } from './QualityFilter';

/**
 * Props for QualityBreakdown component
 */
export interface QualityBreakdownProps {
  /** Puzzle quality level (1-5) */
  tier: PuzzleQualityLevel;
  /** Quality metrics (refutation count, comments, etc.) */
  metrics?: QualityMetrics;
  /** Whether to start expanded */
  initiallyExpanded?: boolean;
  /** CSS class for container */
  className?: string;
}

/**
 * Requirement status indicator
 */
const RequirementStatus: FunctionalComponent<{
  label: string;
  met: boolean;
  value?: string | number;
}> = ({ label, met, value }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '6px 0',
      borderBottom: '1px solid var(--color-neutral-200)',
    }}
  >
    <span
      style={{
        color: met ? 'var(--color-success-solid)' : 'var(--color-error)',
        fontSize: '16px',
      }}
    >
      {met ? '✓' : '✗'}
    </span>
    <span style={{ flex: 1, color: 'var(--color-text-primary)' }}>{label}</span>
    {value !== undefined && (
      <span style={{ color: 'var(--color-text-secondary)', fontSize: '13px' }}>{value}</span>
    )}
  </div>
);

/**
 * Level requirement definitions
 * Scale: 1=worst (Unverified), 5=best (Premium)
 */
const LEVEL_REQUIREMENTS: Record<PuzzleQualityLevel, Array<{
  key: string;
  label: string;
  check: (metrics: QualityMetrics) => boolean;
  value?: (metrics: QualityMetrics) => string;
}>> = {
  1: [
    {
      key: 'solution',
      label: 'Solution verified',
      check: () => false, // Level 1 (Unverified) means not verified
    },
  ],
  2: [
    {
      key: 'solution',
      label: 'Has solution tree',
      check: () => true, // If we have metrics, we have a solution
    },
  ],
  3: [
    {
      key: 'refutations',
      label: '1+ refutation branch',
      check: (m) => (m.refutationCount ?? 0) >= 1,
      value: (m) => `${m.refutationCount ?? 0} branches`,
    },
  ],
  4: [
    {
      key: 'refutations',
      label: '2+ refutation branches',
      check: (m) => (m.refutationCount ?? 0) >= 2,
      value: (m) => `${m.refutationCount ?? 0} branches`,
    },
    {
      key: 'comments',
      label: 'Has explanatory comments',
      check: (m) => m.hasComments === true,
      value: (m) => m.hasComments ? 'Yes' : 'No',
    },
  ],
  5: [
    {
      key: 'refutations',
      label: '3+ refutation branches',
      check: (m) => (m.refutationCount ?? 0) >= 3,
      value: (m) => `${m.refutationCount ?? 0} branches`,
    },
    {
      key: 'comments',
      label: 'Has explanatory comments',
      check: (m) => m.hasComments === true,
      value: (m) => m.hasComments ? 'Yes' : 'No',
    },
  ],
};

/**
 * QualityBreakdown component
 * 
 * Shows expandable quality tier breakdown with met/unmet requirements.
 * 
 * Usage:
 * ```tsx
 * <QualityBreakdown 
 *   tier={2}
 *   metrics={{ refutationCount: 3, hasComments: true }}
 * />
 * ```
 */
export const QualityBreakdown: FunctionalComponent<QualityBreakdownProps> = ({
  tier,
  metrics,
  initiallyExpanded = false,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(initiallyExpanded);

  const info = PUZZLE_QUALITY_INFO[tier] || PUZZLE_QUALITY_INFO[5];
  const levelLabel = info.displayLabel;
  const requirements = LEVEL_REQUIREMENTS[tier] || [];

  // Default metrics if not provided
  const effectiveMetrics: QualityMetrics = metrics || {
    level: tier,
    refutationCount: 0,
    hasComments: false,
  };

  return (
    <div
      className={`quality-breakdown ${className}`}
      style={{
        backgroundColor: 'var(--color-neutral-50)',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid var(--color-neutral-200)',
      }}
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          display: 'flex',
          alignItems: 'center',
          width: '100%',
          padding: '12px 16px',
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          gap: '12px',
        }}
        aria-expanded={isExpanded}
        aria-label={`Quality: ${levelLabel}. Click to ${isExpanded ? 'collapse' : 'expand'} details.`}
      >
        <StarDisplay tier={tier} size={16} />
        <span style={{ flex: 1, textAlign: 'left', fontWeight: 500, color: 'var(--color-text-primary)' }}>
          {levelLabel} Quality
        </span>
        <span style={{ color: 'var(--color-text-secondary)', fontSize: '14px' }}>
          {isExpanded ? '▼' : '▶'}
        </span>
      </button>

      {/* Expandable content */}
      {isExpanded && (
        <div
          style={{
            padding: '0 16px 16px',
            borderTop: '1px solid var(--color-neutral-200)',
          }}
        >
          <p style={{ margin: '12px 0', fontSize: '13px', color: 'var(--color-text-secondary)' }}>
            {info.description || `Level ${tier} quality`}
          </p>

          {requirements.length > 0 ? (
            <div style={{ marginTop: '8px' }}>
              {requirements.map((req) => {
                const computedValue = req.value?.(effectiveMetrics);
                return (
                  <RequirementStatus
                    key={req.key}
                    label={req.label}
                    met={req.check(effectiveMetrics)}
                    {...(computedValue !== undefined && { value: computedValue })}
                  />
                );
              })}
            </div>
          ) : (
            <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
              No specific requirements for this level
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default QualityBreakdown;
