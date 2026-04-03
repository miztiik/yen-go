/**
 * StatGrid component - grid layout for stat cards.
 * @module components/Stats/StatGrid
 */

import type { JSX, ComponentChildren } from 'preact';

/**
 * StatGrid props
 */
export interface StatGridProps {
  /** Child stat cards */
  readonly children: ComponentChildren;
  /** Number of columns (1-4) */
  readonly columns?: 1 | 2 | 3 | 4;
  /** Gap between cards */
  readonly gap?: 'small' | 'medium' | 'large';
}

/**
 * Styles for the StatGrid component.
 */
const styles = {
  grid: `
    display: grid;
    width: 100%;
  `,
  columns: {
    1: 'grid-template-columns: 1fr;',
    2: 'grid-template-columns: repeat(2, 1fr);',
    3: 'grid-template-columns: repeat(3, 1fr);',
    4: 'grid-template-columns: repeat(4, 1fr);',
  },
  gap: {
    small: 'gap: 8px;',
    medium: 'gap: 16px;',
    large: 'gap: 24px;',
  },
};

/**
 * StatGrid component - grid layout for statistics.
 */
export function StatGrid({
  children,
  columns = 2,
  gap = 'medium',
}: StatGridProps): JSX.Element {
  const style = [
    styles.grid,
    styles.columns[columns],
    styles.gap[gap],
  ].join(' ');

  return (
    <div class="stat-grid" style={style}>
      {children}
    </div>
  );
}

export default StatGrid;
