/**
 * Side To Move Indicator Component
 * @module components/shared/SideToMove
 * 
 * Shows "Black to play" or "White to play" (FR-037).
 * 
 * Constitution Compliance:
 * - III. Separation of Concerns: Display only
 * - IX. Accessibility: Screen reader friendly
 */

import { h, type FunctionComponent, type JSX } from 'preact';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for SideToMove component
 */
export interface SideToMoveProps {
  /** Which color is to play */
  color: 'black' | 'white';
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Show stone icon */
  showIcon?: boolean;
  /** Additional CSS class */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Size configurations
 */
const SIZE_CONFIG = {
  small: { fontSize: '0.75rem', stoneSize: 12, gap: '0.25rem' },
  medium: { fontSize: '0.875rem', stoneSize: 16, gap: '0.375rem' },
  large: { fontSize: '1rem', stoneSize: 20, gap: '0.5rem' },
};

// ============================================================================
// Component
// ============================================================================

/**
 * Stone icon as SVG
 */
const StoneIcon: FunctionComponent<{ color: 'black' | 'white'; size: number }> = ({ 
  color, 
  size 
}) => {
  const fill = color === 'black' ? 'var(--color-stone-black)' : 'var(--color-stone-white)';
  const stroke = color === 'black' ? 'none' : 'var(--color-neutral-300)';

  return h('svg', {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    'aria-hidden': 'true',
  }, h('circle', {
    cx: 12,
    cy: 12,
    r: 10,
    fill,
    stroke,
    strokeWidth: stroke ? 1 : 0,
  }));
};

/**
 * SideToMove - shows which color is to play
 */
export const SideToMove: FunctionComponent<SideToMoveProps> = ({
  color,
  size = 'medium',
  showIcon = true,
  className = '',
}) => {
  const config = SIZE_CONFIG[size];
  const label = color === 'black' ? 'Black to play' : 'White to play';

  const containerStyle: JSX.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    gap: config.gap,
    fontSize: config.fontSize,
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif',
    fontWeight: 500,
    color: 'var(--color-text, #374151)',
  };

  return h('div', {
    className: `side-to-move ${className}`.trim(),
    style: containerStyle,
    role: 'status',
    'aria-live': 'polite',
    'aria-label': label,
  }, [
    showIcon && h(StoneIcon, { key: 'icon', color, size: config.stoneSize }),
    h('span', { key: 'label' }, label),
  ]);
};

export default SideToMove;
