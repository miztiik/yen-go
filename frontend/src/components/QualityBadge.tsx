/**
 * QualityBadge component for displaying puzzle quality level as stars.
 *
 * Provides visual quality indicator with level-specific colors and tooltips.
 *
 * @module components/QualityBadge
 */

import { FunctionalComponent } from 'preact';
import { useState } from 'preact/hooks';
import { PuzzleQualityLevel, PUZZLE_QUALITY_INFO } from '@/lib/quality/config';
import { StarDisplay } from './QualityFilter';

/**
 * Level-specific colors (T046)
 * Scale: 1=worst (Unverified), 5=best (Premium)
 */
const LEVEL_COLORS: Record<PuzzleQualityLevel, { primary: string; secondary: string }> = {
  1: { primary: 'var(--color-quality-1)', secondary: 'var(--color-quality-1-bg)' }, // Light Gray - Unverified
  2: { primary: 'var(--color-quality-2)', secondary: 'var(--color-quality-2-bg)' }, // Gray - Basic
  3: { primary: 'var(--color-quality-3)', secondary: 'var(--color-quality-3-bg)' }, // Bronze - Standard
  4: { primary: 'var(--color-quality-4)', secondary: 'var(--color-quality-4-bg)' }, // Silver - High
  5: { primary: 'var(--color-quality-5)', secondary: 'var(--color-quality-5-bg)' }, // Gold - Premium
};

/**
 * Props for QualityBadge component
 */
export interface QualityBadgeProps {
  /** Puzzle quality level (1-5): 1=worst (Unverified), 5=best (Premium) */
  tier: PuzzleQualityLevel;
  /** Display mode */
  variant?: 'stars' | 'compact' | 'full';
  /** Size (small, medium, large) */
  size?: 'small' | 'medium' | 'large';
  /** Whether to show tooltip on hover */
  showTooltip?: boolean;
  /** CSS class for container */
  className?: string;
}

/**
 * Size configurations
 */
const SIZE_CONFIG = {
  small: { starSize: 10, fontSize: '11px', padding: '2px 4px' },
  medium: { starSize: 14, fontSize: '13px', padding: '3px 6px' },
  large: { starSize: 18, fontSize: '15px', padding: '4px 8px' },
};

/**
 * Tooltip component for showing level details
 */
const Tooltip: FunctionalComponent<{
  tier: PuzzleQualityLevel;
  visible: boolean;
  position: { x: number; y: number };
}> = ({ tier, visible, position }) => {
  if (!visible) return null;

  const info = PUZZLE_QUALITY_INFO[tier];
  const levelLabel = info?.displayLabel || 'Unknown';
  const description = getLevelDescription(tier);

  return (
    <div
      className="quality-badge-tooltip"
      style={{
        position: 'fixed',
        left: `${position.x}px`,
        top: `${position.y - 40}px`,
        backgroundColor: 'var(--color-neutral-800)',
        color: 'var(--color-text-inverse)',
        padding: '6px 10px',
        borderRadius: '4px',
        fontSize: '12px',
        zIndex: 9999,
        pointerEvents: 'none',
        whiteSpace: 'nowrap',
        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
      }}
    >
      <strong>{levelLabel}</strong>
      <div style={{ opacity: 0.9, fontSize: '11px', marginTop: '2px' }}>{description}</div>
    </div>
  );
};

/**
 * Get description for level (T047)
 * Scale: 1=worst (Unverified), 5=best (Premium)
 */
function getLevelDescription(level: PuzzleQualityLevel): string {
  switch (level) {
    case 1:
      return 'Single solution, no tree';
    case 2:
      return 'Basic solution tree';
    case 3:
      return 'Solution with refutation';
    case 4:
      return '2+ refutations with comments';
    case 5:
      return '3+ refutations with comments';
    default:
      return '';
  }
}

/**
 * QualityBadge component
 *
 * Displays quality tier as visual stars with color coding.
 *
 * Usage:
 * ```tsx
 * <QualityBadge tier={2} />
 * <QualityBadge tier={1} variant="full" showTooltip />
 * ```
 */
export const QualityBadge: FunctionalComponent<QualityBadgeProps> = ({
  tier,
  variant = 'stars',
  size = 'medium',
  showTooltip = true,
  className = '',
}) => {
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });

  const info = PUZZLE_QUALITY_INFO[tier] || PUZZLE_QUALITY_INFO[1];
  const levelLabel = info.displayLabel;
  const colors = LEVEL_COLORS[tier] || LEVEL_COLORS[1];
  const sizeConfig = SIZE_CONFIG[size];

  const handleMouseEnter = (e: MouseEvent) => {
    if (showTooltip) {
      setTooltipPosition({ x: e.clientX, y: e.clientY });
      setTooltipVisible(true);
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (showTooltip && tooltipVisible) {
      setTooltipPosition({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseLeave = () => {
    setTooltipVisible(false);
  };

  // Compact variant - just colored dot with tier number
  if (variant === 'compact') {
    return (
      <span
        className={`quality-badge quality-badge--compact ${className}`}
        onMouseEnter={handleMouseEnter}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: sizeConfig.starSize + 4,
          height: sizeConfig.starSize + 4,
          borderRadius: '50%',
          backgroundColor: colors.primary,
          color: tier <= 2 ? 'var(--color-neutral-900)' : 'var(--color-text-inverse)',
          fontSize: sizeConfig.fontSize,
          fontWeight: 'bold',
          cursor: 'default',
        }}
        title={levelLabel}
      >
        {tier}
        <Tooltip tier={tier} visible={tooltipVisible} position={tooltipPosition} />
      </span>
    );
  }

  // Full variant - stars + label
  if (variant === 'full') {
    return (
      <span
        className={`quality-badge quality-badge--full ${className}`}
        onMouseEnter={handleMouseEnter}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          padding: sizeConfig.padding,
          backgroundColor: colors.secondary,
          borderRadius: '4px',
          border: `1px solid ${colors.primary}`,
          cursor: 'default',
        }}
      >
        <StarDisplay tier={tier} size={sizeConfig.starSize} />
        <span
          style={{
            fontSize: sizeConfig.fontSize,
            fontWeight: 500,
            color: 'var(--color-text-primary)',
          }}
        >
          {levelLabel}
        </span>
        <Tooltip tier={tier} visible={tooltipVisible} position={tooltipPosition} />
      </span>
    );
  }

  // Default: stars only
  return (
    <span
      className={`quality-badge quality-badge--stars ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        cursor: 'default',
      }}
      title={levelLabel}
    >
      <StarDisplay tier={tier} size={sizeConfig.starSize} />
      <Tooltip tier={tier} visible={tooltipVisible} position={tooltipPosition} />
    </span>
  );
};

export default QualityBadge;
