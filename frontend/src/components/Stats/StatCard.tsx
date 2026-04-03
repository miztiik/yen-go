/**
 * StatCard component - displays a single statistic with label and value.
 * @module components/Stats/StatCard
 */

import type { JSX } from 'preact';

/**
 * StatCard props
 */
export interface StatCardProps {
  /** Label for the statistic */
  readonly label: string;
  /** Value to display */
  readonly value: string | number;
  /** Optional icon (emoji or SVG) */
  readonly icon?: string;
  /** Optional subtitle/description */
  readonly subtitle?: string;
  /** Optional trend indicator */
  readonly trend?: 'up' | 'down' | 'neutral';
  /** Optional trend value (e.g., "+5%") */
  readonly trendValue?: string;
  /** Optional accent color */
  readonly accent?: 'primary' | 'success' | 'warning' | 'danger';
  /** Optional size variant */
  readonly size?: 'small' | 'medium' | 'large';
  /** Optional click handler */
  readonly onClick?: () => void;
}

/**
 * Styles for the StatCard component.
 */
const styles = {
  card: {
    base: `
      background: var(--color-card-bg, #ffffff);
      border: 1px solid var(--color-card-border, #e5e7eb);
      border-radius: 12px;
      padding: 16px;
      transition: all 0.2s ease;
    `,
    clickable: `
      cursor: pointer;
    `,
    small: `
      padding: 12px;
    `,
    large: `
      padding: 24px;
    `,
  },
  icon: `
    font-size: 24px;
    margin-bottom: 8px;
  `,
  label: `
    font-size: 0.875rem;
    color: var(--color-text-muted, #6b7280);
    margin: 0 0 4px 0;
    font-weight: 500;
  `,
  value: {
    base: `
      font-size: 1.75rem;
      font-weight: 700;
      color: var(--color-text-primary, #1f2937);
      margin: 0;
      line-height: 1.2;
    `,
    small: `
      font-size: 1.25rem;
    `,
    large: `
      font-size: 2.5rem;
    `,
  },
  subtitle: `
    font-size: 0.75rem;
    color: var(--color-text-disabled, #9ca3af);
    margin: 4px 0 0 0;
  `,
  trend: {
    base: `
      display: inline-flex;
      align-items: center;
      gap: 2px;
      font-size: 0.75rem;
      font-weight: 500;
      margin-top: 8px;
      padding: 2px 6px;
      border-radius: 4px;
    `,
    up: `
      color: var(--color-mode-technique-text, #059669);
      background: var(--color-success-bg-solid, #d1fae5);
    `,
    down: `
      color: var(--color-error, #dc2626);
      background: var(--color-error-bg, #fee2e2);
    `,
    neutral: `
      color: var(--color-text-muted, #6b7280);
      background: var(--color-neutral-100, #f3f4f6);
    `,
  },
  accent: {
    primary: `
      border-left: 4px solid var(--color-info-border, #3b82f6);
    `,
    success: `
      border-left: 4px solid var(--color-success, #10b981);
    `,
    warning: `
      border-left: 4px solid var(--color-warning-border, #f59e0b);
    `,
    danger: `
      border-left: 4px solid var(--color-error, #ef4444);
    `,
  },
};

/**
 * Trend arrow component.
 */
function TrendArrow({ direction }: { direction: 'up' | 'down' | 'neutral' }): JSX.Element {
  if (direction === 'up') {
    return <span aria-hidden="true">↑</span>;
  }
  if (direction === 'down') {
    return <span aria-hidden="true">↓</span>;
  }
  return <span aria-hidden="true">→</span>;
}

/**
 * StatCard component - displays a single statistic.
 */
export function StatCard({
  label,
  value,
  icon,
  subtitle,
  trend,
  trendValue,
  accent,
  size = 'medium',
  onClick,
}: StatCardProps): JSX.Element {
  const cardStyle = [
    styles.card.base,
    onClick ? styles.card.clickable : '',
    size === 'small' ? styles.card.small : '',
    size === 'large' ? styles.card.large : '',
    accent ? styles.accent[accent] : '',
  ]
    .filter(Boolean)
    .join(' ');

  const valueStyle = [
    styles.value.base,
    size === 'small' ? styles.value.small : '',
    size === 'large' ? styles.value.large : '',
  ]
    .filter(Boolean)
    .join(' ');

  const trendStyle = trend
    ? [styles.trend.base, styles.trend[trend]].join(' ')
    : '';

  const handleClick = onClick
    ? (e: Event) => {
        e.preventDefault();
        onClick();
      }
    : undefined;

  const handleKeyDown = onClick
    ? (e: KeyboardEvent) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }
    : undefined;

  return (
    <div
      class="stat-card"
      style={cardStyle}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {icon && (
        <div class="stat-card-icon" style={styles.icon}>
          {icon}
        </div>
      )}
      <p class="stat-card-label" style={styles.label}>
        {label}
      </p>
      <p class="stat-card-value" style={valueStyle}>
        {value}
      </p>
      {subtitle && (
        <p class="stat-card-subtitle" style={styles.subtitle}>
          {subtitle}
        </p>
      )}
      {trend && trendValue && (
        <div class="stat-card-trend" style={trendStyle}>
          <TrendArrow direction={trend} />
          <span>{trendValue}</span>
        </div>
      )}
    </div>
  );
}

export default StatCard;
