/**
 * ActivityHeatmap — SVG 90-day activity grid (7 rows x 13 cols).
 * @module components/Progress/ActivityHeatmap
 */

import type { FunctionalComponent } from 'preact';

export interface ActivityHeatmapProps {
  activityDays: ReadonlyMap<string, number>;
}

const CELL_SIZE = 14;
const CELL_GAP = 2;
const ROWS = 7;
const COLS = 13;

/** Map puzzle count to opacity level. */
function intensityLevel(count: number): string {
  if (count === 0) return 'var(--color-bg-secondary, #eee)';
  if (count <= 2) return 'var(--color-accent-light, #b3d4ff)';
  if (count <= 5) return 'var(--color-accent, #4f8cff)';
  return 'var(--color-accent-text, #1a56db)';
}

/** Format date as YYYY-MM-DD. */
function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export const ActivityHeatmap: FunctionalComponent<ActivityHeatmapProps> = ({ activityDays }) => {
  const today = new Date();
  // Find the last Saturday (end of the grid)
  const endDate = new Date(today);
  endDate.setDate(endDate.getDate() + (6 - endDate.getDay()));

  const svgWidth = COLS * (CELL_SIZE + CELL_GAP);
  const svgHeight = ROWS * (CELL_SIZE + CELL_GAP);

  const cells: preact.VNode[] = [];
  for (let col = 0; col < COLS; col++) {
    for (let row = 0; row < ROWS; row++) {
      const dayOffset = (COLS - 1 - col) * 7 + (6 - row);
      const cellDate = new Date(endDate);
      cellDate.setDate(cellDate.getDate() - dayOffset);
      const dateKey = formatDate(cellDate);
      const count = activityDays.get(dateKey) ?? 0;

      cells.push(
        <rect
          key={dateKey}
          x={col * (CELL_SIZE + CELL_GAP)}
          y={row * (CELL_SIZE + CELL_GAP)}
          width={CELL_SIZE}
          height={CELL_SIZE}
          rx={2}
          fill={intensityLevel(count)}
          data-date={dateKey}
          data-count={count}
        >
          <title>{`${dateKey}: ${count} puzzle${count !== 1 ? 's' : ''}`}</title>
        </rect>
      );
    }
  }

  return (
    <section data-testid="activity-heatmap" className="mb-6">
      <h2 className="mb-3 text-lg font-bold text-[var(--color-text-primary)]">Activity</h2>
      <div className="overflow-x-auto">
        <svg
          width={svgWidth}
          height={svgHeight}
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          role="img"
          aria-label="90-day activity heatmap"
        >
          {cells}
        </svg>
      </div>
    </section>
  );
};
