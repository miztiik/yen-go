/**
 * ProgressBar — shared progress indicator component.
 *
 * Renders a thin horizontal bar showing completion progress.
 * Fill color driven by page mode via CSS custom properties.
 *
 * States:
 * - total === 0: hidden (renders nothing)
 * - solved === 0: "Ready to begin" muted italic text
 * - solved > 0: thin bar + "X of Y solved" label
 *
 * Spec 132 — FR-033, US10
 * @module components/shared/ProgressBar
 */

import type { FunctionalComponent, VNode } from 'preact';
import type { PageMode } from '../../types/page-mode';

// ============================================================================
// Types
// ============================================================================

export interface ProgressBarProps {
  /** Number of solved/completed items. */
  solved: number;
  /** Total available items. */
  total: number;
  /** Page mode determines fill color via CSS var --color-mode-{mode}-border. */
  mode?: PageMode;
  /** Additional CSS classes for outer container. */
  className?: string;
  /** Test data attribute prefix. */
  testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const ProgressBar: FunctionalComponent<ProgressBarProps> = ({
  solved,
  total,
  mode,
  className = '',
  testId = 'progress-bar',
}): VNode | null => {
  // total === 0 → render nothing
  if (total === 0) {
    return null;
  }

  // solved === 0 → show "Ready to begin"
  if (solved === 0) {
    return (
      <div
        className={`text-xs italic text-[var(--color-text-muted)] ${className}`}
        data-testid={testId}
      >
        Ready to begin
      </div>
    );
  }

  // solved > 0 → bar + label
  const percent = Math.min(100, Math.round((solved / total) * 100));

  // Fill color: mode-specific or accent fallback
  const fillColor = mode ? `var(--color-mode-${mode}-border)` : 'var(--color-accent)';

  return (
    <div className={`flex flex-col gap-1 ${className}`} data-testid={testId}>
      {/* Track */}
      <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--color-bg-elevated)]">
        {/* Fill */}
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${percent}%`,
            backgroundColor: fillColor,
          }}
          role="progressbar"
          aria-valuenow={solved}
          aria-valuemin={0}
          aria-valuemax={total}
        />
      </div>
      {/* Label */}
      <span className="text-xs text-[var(--color-text-muted)]">
        {solved} of {total} solved
      </span>
    </div>
  );
};

export default ProgressBar;
