/**
 * HomeGrid Component
 * @module components/Home/HomeGrid
 *
 * Responsive grid for home screen tiles.
 * - Desktop: 2 columns
 * - Tablet: 2 columns
 * - Mobile: 1 column
 *
 * Covers: T047 - NFR-006/007 responsive layout
 */

import type { JSX, ComponentChildren } from 'preact';

export interface HomeGridProps {
  /** Grid children (HomeTile components) */
  children: ComponentChildren;
  /** Custom className */
  className?: string | undefined;
}

const styles = {
  grid: {
    display: 'grid',
    gap: '24px',
    width: '100%',
    margin: '0 auto',
  } as JSX.CSSProperties,
};

/**
 * HomeGrid - Responsive grid layout for home tiles
 */
export function HomeGrid({ children, className = '' }: HomeGridProps): JSX.Element {
  return (
    <div class={`home-grid ${className}`} style={styles.grid}>
      {children}
    </div>
  );
}

export default HomeGrid;
