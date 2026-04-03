/**
 * HomeTile Component
 * @module components/Home/HomeTile
 *
 * Tile for home screen grid with hover effects and accent border.
 *
 * Covers: T045 - Home tile design from ui_mocks/home_01.html
 */

import type { JSX, ComponentChildren } from 'preact';

export type TileVariant = 'daily' | 'rush' | 'collections' | 'training' | 'technique' | 'random' | 'learning';

export interface HomeTileProps {
  /** Tile variant for styling */
  variant: TileVariant;
  /** Main title */
  title: string;
  /** Description text */
  description: string;
  /** Icon content (emoji or component) */
  icon: ComponentChildren;
  /** Stat label (e.g., "Streak: 5 Days") */
  statLabel?: string | undefined;
  /** Stat value (e.g., "Best: 2400") */
  statValue?: string | undefined;
  /** Progress percentage (0-100) */
  progress?: number | undefined;
  /** Progress label left */
  progressLabelLeft?: string | undefined;
  /** Progress label right */
  progressLabelRight?: string | undefined;
  /** Tags to display */
  tags?: readonly string[] | undefined;
  /** Whether tile is featured (shows "NEW" badge) */
  isFeatured?: boolean | undefined;
  /** Click handler */
  onClick?: () => void;
  /** Custom className */
  className?: string | undefined;
}

const variantColors: Record<TileVariant, { border: string; bg: string; text: string; light: string }> = {
  daily: { border: 'var(--color-mode-daily-border)', bg: 'var(--color-mode-daily-bg)', text: 'var(--color-mode-daily-text)', light: 'var(--color-mode-daily-light)' },
  rush: { border: 'var(--color-mode-rush-border)', bg: 'var(--color-mode-rush-bg)', text: 'var(--color-mode-rush-text)', light: 'var(--color-mode-rush-light)' },
  collections: { border: 'var(--color-mode-collections-border)', bg: 'var(--color-mode-collections-bg)', text: 'var(--color-mode-collections-text)', light: 'var(--color-mode-collections-light)' },
  training: { border: 'var(--color-mode-training-border)', bg: 'var(--color-mode-training-bg)', text: 'var(--color-mode-training-text)', light: 'var(--color-mode-training-light)' },
  technique: { border: 'var(--color-mode-technique-border)', bg: 'var(--color-mode-technique-bg)', text: 'var(--color-mode-technique-text)', light: 'var(--color-mode-technique-light)' },
  random: { border: 'var(--color-mode-random-border)', bg: 'var(--color-mode-random-bg)', text: 'var(--color-mode-random-text)', light: 'var(--color-mode-random-light)' },
  learning: { border: 'var(--color-mode-learning-border)', bg: 'var(--color-mode-learning-bg)', text: 'var(--color-mode-learning-text)', light: 'var(--color-mode-learning-light)' },
};

const styles = {
  tile: {
    position: 'relative',
    backgroundColor: 'white',
    borderRadius: '24px',
    padding: '24px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
    borderBottom: '6px solid',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    overflow: 'hidden',
  } as JSX.CSSProperties,

  tileHover: {
    transform: 'translateY(-4px)',
    boxShadow: '0 12px 24px rgba(0, 0, 0, 0.15)',
  } as JSX.CSSProperties,

  featuredBadge: {
    position: 'absolute',
    top: '20px',
    right: '-32px',
    backgroundColor: 'var(--color-mode-daily-border)',
    color: 'var(--color-mode-daily-text)',
    fontSize: '0.625rem',
    fontWeight: 700,
    padding: '4px 40px',
    transform: 'rotate(45deg)',
    letterSpacing: '0.05em',
  } as JSX.CSSProperties,

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
  } as JSX.CSSProperties,

  titleSection: {
    flex: 1,
  } as JSX.CSSProperties,

  statBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '0.75rem',
    fontWeight: 700,
    padding: '6px 10px',
    borderRadius: '8px',
    marginBottom: '8px',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  } as JSX.CSSProperties,

  title: {
    fontSize: '1.5rem',
    fontWeight: 800,
    color: 'var(--color-text-primary)',
    margin: 0,
    lineHeight: 1.2,
  } as JSX.CSSProperties,

  iconContainer: {
    width: '72px',
    height: '72px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '2rem',
    flexShrink: 0,
    marginLeft: '12px',
  } as JSX.CSSProperties,

  description: {
    fontSize: '1rem',
    color: 'var(--color-text-muted)',
    fontWeight: 500,
    marginBottom: '16px',
    lineHeight: 1.5,
  } as JSX.CSSProperties,

  progressContainer: {
    width: '100%',
  } as JSX.CSSProperties,

  progressBar: {
    height: '10px',
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: '5px',
    overflow: 'hidden',
  } as JSX.CSSProperties,

  progressFill: {
    height: '100%',
    borderRadius: '5px',
    transition: 'width 0.3s ease',
  } as JSX.CSSProperties,

  progressLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: '6px',
    fontSize: '0.75rem',
    fontWeight: 700,
    color: 'var(--color-neutral-400)',
  } as JSX.CSSProperties,

  tagsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  } as JSX.CSSProperties,

  tag: {
    padding: '6px 12px',
    borderRadius: '8px',
    backgroundColor: 'var(--color-neutral-100)',
    color: 'var(--color-text-secondary)',
    fontSize: '0.75rem',
    fontWeight: 700,
  } as JSX.CSSProperties,
};

/**
 * HomeTile - Tile for home screen grid
 */
export function HomeTile({
  variant,
  title,
  description,
  icon,
  statLabel,
  statValue,
  progress,
  progressLabelLeft,
  progressLabelRight,
  tags,
  isFeatured = false,
  onClick,
  className = '',
}: HomeTileProps): JSX.Element {
  const colors = variantColors[variant];

  return (
    <div
      class={`home-tile home-tile--${variant} ${className}`}
      style={{
        ...styles.tile,
        borderBottomColor: colors.border,
      }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
    >
      {/* Featured Badge */}
      {isFeatured && (
        <div style={styles.featuredBadge}>NEW</div>
      )}

      {/* Header with icon */}
      <div style={styles.header}>
        <div style={styles.titleSection}>
          {/* Stat Badge */}
          {(statLabel || statValue) && (
            <div style={{ ...styles.statBadge, backgroundColor: colors.bg, color: colors.text }}>
              {statLabel && <span>{statLabel}</span>}
              {statValue && <span>{statValue}</span>}
            </div>
          )}
          <h2 style={styles.title}>{title}</h2>
        </div>

        {/* Icon */}
        <div style={{ ...styles.iconContainer, backgroundColor: colors.light }}>
          {icon}
        </div>
      </div>

      {/* Description */}
      <p style={styles.description}>{description}</p>

      {/* Progress Bar */}
      {progress !== undefined && (
        <div style={styles.progressContainer}>
          <div style={styles.progressBar}>
            <div
              style={{
                ...styles.progressFill,
                width: `${progress}%`,
                backgroundColor: colors.border,
              }}
            />
          </div>
          {(progressLabelLeft || progressLabelRight) && (
            <div style={styles.progressLabels}>
              <span>{progressLabelLeft ?? ''}</span>
              <span>{progressLabelRight ?? ''}</span>
            </div>
          )}
        </div>
      )}

      {/* Tags */}
      {tags && tags.length > 0 && (
        <div style={styles.tagsContainer}>
          {tags.map((tag) => (
            <span key={tag} style={styles.tag}>{tag}</span>
          ))}
        </div>
      )}
    </div>
  );
}

export default HomeTile;
