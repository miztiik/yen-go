/**
 * PageHeader — Shared page header component following the Technique Focus pattern.
 * @module components/shared/PageHeader
 *
 * Provides: back button + icon circle (colorful SVG) + title + subtitle + stat badges
 * on an accent-tinted background. Used by all browse pages for visual consistency.
 *
 * Apple HIG: clean typography hierarchy (800 title, 500 subtitle),
 * generous whitespace, rounded badges, warm accent colors.
 *
 * Spec 132, T-U28
 */

import type { FunctionalComponent, ComponentChildren } from 'preact';
import { ChevronLeftIcon } from './icons';

export interface StatBadge {
  label: string;
  value?: string | number;
}

export interface PageHeaderProps {
  /** Page title (bold, 1.75rem, weight 800) */
  title: string;
  /** Subtitle text (muted, sm) */
  subtitle?: string;
  /** Icon element rendered in the accent circle */
  icon?: ComponentChildren;
  /** Stat badges displayed below the title */
  stats?: StatBadge[];
  /** Back button click handler */
  onBack?: () => void;
  /** Back label (defaults to "Back") */
  backLabel?: string;
  /** Accent color palette — uses CSS cascade vars with mode fallbacks */
  accent?: {
    text: string;
    light: string;
    bg: string;
    border: string;
  };
  /** Custom className for the header container */
  className?: string;
  /** Test ID */
  testId?: string;
}

const DEFAULT_ACCENT = {
  text: 'var(--color-accent, var(--color-mode-technique-text))',
  light: 'var(--color-accent-light, var(--color-mode-technique-light))',
  bg: 'var(--color-accent-bg, var(--color-mode-technique-bg))',
  border: 'var(--color-accent-border, var(--color-mode-technique-border))',
} as const;

export const PageHeader: FunctionalComponent<PageHeaderProps> = ({
  title,
  subtitle,
  icon,
  stats,
  onBack,
  backLabel = 'Back',
  accent = DEFAULT_ACCENT,
  className = '',
  testId,
}) => {
  return (
    <div
      className={`px-4 pb-4 pt-4 ${className}`}
      style={{ backgroundColor: accent.light }}
      data-testid={testId}
    >
      <div className="mx-auto max-w-5xl">
        {/* Back button */}
        {onBack && (
          <button
            type="button"
            onClick={onBack}
            className="mb-3 inline-flex cursor-pointer items-center gap-1 rounded-lg border-none bg-transparent px-2 py-1.5 text-sm font-medium text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-elevated)] hover:text-[var(--color-text-primary)]"
          >
            <ChevronLeftIcon size={14} /> {backLabel}
          </button>
        )}

        {/* Title row: icon circle + title */}
        <div className="flex items-center gap-4">
          {icon && (
            <div
              className="flex shrink-0 items-center justify-center rounded-full"
              style={{
                width: '72px',
                height: '72px',
                backgroundColor: accent.bg,
              }}
            >
              {icon}
            </div>
          )}
          <div>
            <h1
              className="m-0 text-[var(--color-text-primary)]"
              style={{ fontSize: '1.75rem', fontWeight: 800, lineHeight: 1.2 }}
            >
              {title}
            </h1>
            {subtitle && (
              <p
                className="m-0 mt-1 text-sm text-[var(--color-text-muted)]"
                style={{ fontWeight: 500 }}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Stat badges */}
        {stats && stats.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-3" data-testid="page-stats">
            {stats.map((stat) => (
              <span
                key={stat.label}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wider"
                style={{ backgroundColor: accent.bg, color: accent.text }}
              >
                {stat.value !== undefined ? `${stat.value} ${stat.label}` : stat.label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PageHeader;
