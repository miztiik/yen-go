/**
 * DifficultyChart — SVG bar chart showing accuracy per difficulty level.
 * @module components/Progress/DifficultyChart
 */

import type { FunctionalComponent } from 'preact';
import type { DifficultyStats } from '../../services/progressAnalytics';

export interface DifficultyChartProps {
  difficulties: readonly DifficultyStats[];
}

const BAR_WIDTH = 40;
const BAR_GAP = 12;
const CHART_HEIGHT = 160;
const LABEL_HEIGHT = 40;
const TOP_PAD = 24;

export const DifficultyChart: FunctionalComponent<DifficultyChartProps> = ({ difficulties }) => {
  if (difficulties.length === 0) return null;

  const sorted = [...difficulties].sort((a, b) => a.levelId - b.levelId);
  const chartWidth = sorted.length * (BAR_WIDTH + BAR_GAP) - BAR_GAP + 20;
  const svgHeight = CHART_HEIGHT + LABEL_HEIGHT + TOP_PAD;

  return (
    <section data-testid="difficulty-chart" className="mb-6">
      <h2 className="mb-3 text-lg font-bold text-[var(--color-text-primary)]">
        Difficulty Breakdown
      </h2>
      <div className="overflow-x-auto">
        <svg
          width={chartWidth}
          height={svgHeight}
          viewBox={`0 0 ${chartWidth} ${svgHeight}`}
          role="img"
          aria-label="Difficulty accuracy chart"
        >
          {sorted.map((d, i) => {
            const x = 10 + i * (BAR_WIDTH + BAR_GAP);
            const barHeight = (d.accuracy / 100) * CHART_HEIGHT;
            const y = TOP_PAD + CHART_HEIGHT - barHeight;
            return (
              <g key={d.levelId}>
                {/* Count label */}
                <text
                  x={x + BAR_WIDTH / 2}
                  y={y - 4}
                  textAnchor="middle"
                  className="fill-[var(--color-text-muted)]"
                  fontSize="11"
                >
                  {d.total}
                </text>
                {/* Bar */}
                <rect
                  x={x}
                  y={y}
                  width={BAR_WIDTH}
                  height={barHeight}
                  rx={4}
                  className="fill-[var(--color-accent,#4f8cff)]"
                />
                {/* Label */}
                <text
                  x={x + BAR_WIDTH / 2}
                  y={TOP_PAD + CHART_HEIGHT + 16}
                  textAnchor="middle"
                  className="fill-[var(--color-text-primary)]"
                  fontSize="10"
                >
                  {shortenLabel(d.levelName)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </section>
  );
};

/** Shorten long level names for bar labels. */
function shortenLabel(name: string): string {
  if (name.length <= 8) return name;
  const map: Record<string, string> = {
    'Upper-Intermediate': 'Upper-Int.',
    Intermediate: 'Inter.',
    Elementary: 'Elem.',
  };
  return map[name] ?? name.slice(0, 8);
}
