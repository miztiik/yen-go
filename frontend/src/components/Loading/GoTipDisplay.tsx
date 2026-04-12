/**
 * GoTipDisplay — renders a random level-filtered Go tip during loading.
 *
 * Shows a random tip from the boot-cached GoTipsConfig, filtered by the
 * current level context. No artificial delay — content renders immediately
 * when children resolve. CSS opacity transition (300ms ease-out) when dissolving.
 *
 * Spec 127: FR-032, FR-033, T006
 * @module components/Loading/GoTipDisplay
 */

import { useState, useEffect } from 'preact/hooks';
import type { JSX } from 'preact';

/** Go tip entry. */
export interface GoTip {
  text: string;
  category: 'tip' | 'proverb' | 'definition';
  levels: string[];
}

export interface GoTipDisplayProps {
  /** All available tips (from boot config). */
  tips: GoTip[];
  /** Current level context for filtering (optional). */
  level?: string;
  /** Whether data has arrived and tip should fade out. */
  dataReady?: boolean;
}

/**
 * Select a random tip from the list, filtered by level.
 */
function selectTip(tips: GoTip[], level?: string): GoTip | null {
  if (tips.length === 0) return null;

  const filtered = level ? tips.filter((t) => t.levels.includes(level)) : tips;

  const pool = filtered.length > 0 ? filtered : tips;
  return pool[Math.floor(Math.random() * pool.length)] ?? null;
}

/**
 * GoTipDisplay — shown in the board area during loading.
 */
export function GoTipDisplay({
  tips,
  level,
  dataReady = false,
}: GoTipDisplayProps): JSX.Element | null {
  const [tip] = useState(() => selectTip(tips, level));
  const [visible, setVisible] = useState(true);
  const [minTimeElapsed, setMinTimeElapsed] = useState(false);

  // No artificial delay — render content immediately (T056)
  useEffect(() => {
    setMinTimeElapsed(true);
  }, []);

  // Fade out when both data is ready AND minimum time elapsed
  useEffect(() => {
    if (dataReady && minTimeElapsed) {
      setVisible(false);
    }
  }, [dataReady, minTimeElapsed]);

  if (!tip) return null;

  const categoryLabel =
    tip.category === 'proverb'
      ? 'Go Proverb'
      : tip.category === 'definition'
        ? 'Go Term'
        : 'Go Tip';

  return (
    <div
      className="flex flex-col items-center justify-center p-6 text-center w-full"
      style={{
        opacity: visible ? 1 : 0,
        transition: 'opacity 300ms ease-out',
      }}
      aria-hidden={!visible}
    >
      <span className="text-xs uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
        {categoryLabel}
      </span>
      <p className="text-lg text-[var(--color-text-primary)] italic w-full max-w-md leading-relaxed">
        "{tip.text}"
      </p>
    </div>
  );
}
