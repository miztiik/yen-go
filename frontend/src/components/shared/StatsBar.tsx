/**
 * StatsBar — shared flat stats summary row.
 * @module components/shared/StatsBar
 *
 * Replaces gradient banners with a flat, elevated background.
 * Monochrome text stats — no gradient, no inverse text.
 *
 * Spec 129, T063 — FR-045
 */

import type { FunctionalComponent, ComponentChildren } from 'preact';

// ============================================================================
// Types
// ============================================================================

export interface StatItem {
  /** Numeric or text value. */
  value: string | number;
  /** Label displayed below value. */
  label: string;
}

export interface StatsBarProps {
  /** Array of stat items to display. */
  stats: readonly StatItem[];
  /** Optional extra content (e.g., action buttons). */
  children?: ComponentChildren;
  /** Optional CSS class. */
  className?: string;
  /** Test ID. */
  testId?: string;
}

// ============================================================================
// Component
// ============================================================================

export const StatsBar: FunctionalComponent<StatsBarProps> = ({
  stats,
  children,
  className = '',
  testId,
}) => {
  if (stats.length === 0 && !children) return null;

  return (
    <div
      className={`
        bg-[var(--color-bg-elevated)] px-4 py-3
        ${className}
      `}
      data-testid={testId}
    >
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-around gap-4 text-center">
        {stats.map((stat) => (
          <div key={stat.label} className="flex flex-col items-center">
            <span className="text-xl font-semibold text-[var(--color-text-primary)]">
              {stat.value}
            </span>
            <span className="text-xs text-[var(--color-text-muted)]">
              {stat.label}
            </span>
          </div>
        ))}
        {children}
      </div>
    </div>
  );
};

export default StatsBar;
