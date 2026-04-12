/**
 * ComplexityIndicator component showing puzzle complexity metrics.
 *
 * Displays solution depth, reading count, stone count, and uniqueness score.
 *
 * @module components/ComplexityIndicator
 */

import { FunctionalComponent } from 'preact';
import { ComplexityMetrics } from '@/lib/quality/config';

/**
 * Props for ComplexityIndicator component
 */
export interface ComplexityIndicatorProps {
  /** Complexity metrics */
  metrics: ComplexityMetrics;
  /** Display variant */
  variant?: 'compact' | 'full' | 'inline';
  /** CSS class for container */
  className?: string;
}

/**
 * Individual metric display
 */
const MetricItem: FunctionalComponent<{
  icon: string;
  label: string;
  value: number | string;
  description?: string;
}> = ({ icon, label, value, description }) => (
  <div className="flex items-center gap-2 py-1.5" title={description}>
    <span className="text-base">{icon}</span>
    <span className="flex-1 text-[13px] text-[--color-text-secondary]">{label}</span>
    <span className="min-w-[32px] text-right text-sm font-semibold text-[--color-text-primary]">
      {value}
    </span>
  </div>
);

/**
 * Get complexity level label based on metrics
 */
function getComplexityLevel(metrics: ComplexityMetrics): {
  label: string;
  color: string;
} {
  const depth = metrics.solutionDepth || 0;
  const reading = metrics.readingCount || 0;

  // Simple heuristic for complexity level
  const score = depth * 2 + reading;

  if (score < 5) return { label: 'Simple', color: 'var(--color-complexity-simple)' };
  if (score < 10) return { label: 'Moderate', color: 'var(--color-complexity-moderate)' };
  if (score < 20) return { label: 'Complex', color: 'var(--color-complexity-complex)' };
  return { label: 'Very Complex', color: 'var(--color-complexity-very-complex)' };
}

/**
 * ComplexityIndicator component
 *
 * Shows puzzle complexity metrics (depth, reading, stones).
 *
 * Usage:
 * ```tsx
 * <ComplexityIndicator
 *   metrics={{ solutionDepth: 5, readingCount: 3, stoneCount: 12 }}
 * />
 * ```
 */
export const ComplexityIndicator: FunctionalComponent<ComplexityIndicatorProps> = ({
  metrics,
  variant = 'full',
  className = '',
}) => {
  const complexityLevel = getComplexityLevel(metrics);

  // Inline variant - single line summary
  if (variant === 'inline') {
    return (
      <span
        className={`inline-flex items-center gap-2 text-xs text-[--color-text-secondary] ${className}`}
      >
        <span title="Solution depth">📏 {metrics.solutionDepth || 0}</span>
        <span title="Reading variations">🧠 {metrics.readingCount || 0}</span>
        <span title="Stones on board">⚫ {metrics.stoneCount || 0}</span>
      </span>
    );
  }

  // Compact variant - badge with level
  if (variant === 'compact') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-xl px-2.5 py-1 text-xs font-medium ${className}`}
        style={{
          backgroundColor: `${complexityLevel.color}22`,
          color: complexityLevel.color,
        }}
        title={`Depth: ${metrics.solutionDepth || 0}, Reading: ${metrics.readingCount || 0}`}
      >
        🧩 {complexityLevel.label}
      </span>
    );
  }

  // Full variant - detailed breakdown
  return (
    <div
      className={`rounded-lg border border-[--color-border] bg-[--color-bg-secondary] px-4 py-3 ${className}`}
    >
      <div className="mb-2 flex items-center justify-between border-b border-[--color-border] pb-2">
        <span className="font-semibold text-[--color-text-primary]">Complexity</span>
        <span
          className="rounded-lg px-2 py-0.5 text-xs font-medium"
          style={{
            backgroundColor: `${complexityLevel.color}22`,
            color: complexityLevel.color,
          }}
        >
          {complexityLevel.label}
        </span>
      </div>

      <MetricItem
        icon="📏"
        label="Solution Depth"
        value={metrics.solutionDepth || 0}
        description="Number of moves in the main solution line"
      />
      <MetricItem
        icon="🧠"
        label="Reading Variations"
        value={metrics.readingCount || 0}
        description="Number of alternative lines to consider"
      />
      <MetricItem
        icon="⚫"
        label="Stones on Board"
        value={metrics.stoneCount || 0}
        description="Total stones in the starting position"
      />
      {metrics.uniqueness !== undefined && (
        <MetricItem
          icon="✨"
          label="Uniqueness"
          value={metrics.uniqueness === 1 ? 'Unique' : 'Multiple solutions'}
          description="Whether there is a single correct first move"
        />
      )}
    </div>
  );
};

export default ComplexityIndicator;
