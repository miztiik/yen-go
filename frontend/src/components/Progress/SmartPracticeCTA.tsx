/**
 * SmartPracticeCTA — Call-to-action card for starting smart practice.
 * @module components/Progress/SmartPracticeCTA
 */

import type { FunctionalComponent } from 'preact';
import type { TechniqueStats } from '../../services/progressAnalytics';
import { LightningIcon } from '../shared/icons';

export interface SmartPracticeCTAProps {
  weakestTechniques: readonly TechniqueStats[];
  onStart: (techniques?: string[]) => void;
}

export const SmartPracticeCTA: FunctionalComponent<SmartPracticeCTAProps> = ({
  weakestTechniques,
  onStart,
}) => {
  const top3 = weakestTechniques.slice(0, 3);
  if (top3.length === 0) return null;

  const slugs = top3.map((t) => t.tagSlug);

  return (
    <section
      data-testid="smart-practice-cta"
      className="rounded-xl border border-[var(--color-accent-border,#e0e7ff)] bg-[var(--color-bg-elevated)] p-5"
    >
      <div className="mb-3 flex items-center gap-2">
        <LightningIcon size={20} />
        <h2 className="text-lg font-bold text-[var(--color-text-primary)]">Smart Practice</h2>
      </div>
      <p className="mb-3 text-sm text-[var(--color-text-muted)]">
        Focus on your weakest areas: {top3.map((t) => t.tagName).join(', ')}
      </p>
      <button
        type="button"
        className="rounded-lg bg-[var(--color-accent,#4f8cff)] px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90"
        onClick={() => onStart(slugs)}
        data-testid="start-smart-practice"
      >
        Start Smart Practice
      </button>
    </section>
  );
};
