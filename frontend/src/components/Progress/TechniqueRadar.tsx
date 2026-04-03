/**
 * TechniqueRadar — Horizontal accuracy bars per technique with trend indicators.
 * @module components/Progress/TechniqueRadar
 */

import type { FunctionalComponent } from 'preact';
import type { TechniqueStats } from '../../services/progressAnalytics';

export interface TechniqueRadarProps {
  techniques: readonly TechniqueStats[];
}

function TrendArrow({ trend }: { trend: number }) {
  if (trend > 0) {
    return <span className="text-xs font-medium text-green-600" aria-label={`Up ${Math.abs(trend).toFixed(1)}%`}>+{Math.abs(trend).toFixed(1)}%</span>;
  }
  if (trend < 0) {
    return <span className="text-xs font-medium text-red-600" aria-label={`Down ${Math.abs(trend).toFixed(1)}%`}>-{Math.abs(trend).toFixed(1)}%</span>;
  }
  return <span className="text-xs text-[var(--color-text-muted)]" aria-label="No change">--</span>;
}

export const TechniqueRadar: FunctionalComponent<TechniqueRadarProps> = ({ techniques }) => {
  if (techniques.length === 0) return null;

  const sorted = [...techniques].sort((a, b) => b.total - a.total).slice(0, 10);

  const weakest = sorted.reduce<TechniqueStats | null>(
    (prev, curr) => (!prev || curr.accuracy < prev.accuracy) ? curr : prev,
    null,
  );

  return (
    <section data-testid="technique-radar" className="mb-6">
      <h2 className="mb-3 text-lg font-bold text-[var(--color-text-primary)]">Techniques</h2>
      <div className="space-y-2">
        {sorted.map(t => (
          <div key={t.tagId} className="flex items-center gap-3" data-testid={`technique-${t.tagSlug}`}>
            <span className="w-28 shrink-0 truncate text-sm font-medium text-[var(--color-text-primary)]">
              {t.tagName}
            </span>
            <div className="relative h-5 flex-1 overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
              <div
                className="absolute left-0 top-0 h-full rounded-full bg-[var(--color-accent,#4f8cff)] transition-all"
                style={{ width: `${Math.min(t.accuracy, 100)}%` }}
              />
            </div>
            <span className="w-12 text-right text-sm font-medium text-[var(--color-text-primary)]">
              {Math.round(t.accuracy)}%
            </span>
            <span className="w-10 text-right text-xs text-[var(--color-text-muted)]">{t.total}</span>
            <div className="w-14 text-right">
              <TrendArrow trend={t.trend30d} />
            </div>
            {t.lowData && (
              <span className="shrink-0 rounded bg-yellow-100 px-1.5 py-0.5 text-[10px] font-medium text-yellow-700">
                Low data
              </span>
            )}
          </div>
        ))}
      </div>
      {weakest && weakest.trend30d < 0 && (
        <p className="mt-3 text-sm text-[var(--color-text-muted)]" data-testid="technique-insight">
          Your {weakest.tagName} dropped {Math.abs(weakest.trend30d).toFixed(1)}% — try more puzzles
        </p>
      )}
    </section>
  );
};
