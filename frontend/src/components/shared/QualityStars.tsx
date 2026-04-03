/**
 * QualityStars — compact 1–5 star rating display.
 * @module components/shared/QualityStars
 *
 * Colors from config/puzzle-quality.json display.star_colors:
 *   filled: #FFD700 (gold), empty: #CCCCCC (gray)
 */

import type { FunctionalComponent, JSX } from 'preact';
import { StarIcon } from './icons/StarIcon';

// Star colors from puzzle-quality.json display config
const FILLED_COLOR = '#FFD700';
const EMPTY_COLOR = '#CCCCCC';
const MAX_STARS = 5;

export interface QualityStarsProps {
  /** Quality level (1–5). Values outside this range are clamped. */
  quality: number;
  /** Icon size in pixels. Default: 14. */
  size?: number;
  /** Optional CSS class. */
  className?: string;
  /** Optional inline styles. */
  style?: JSX.CSSProperties;
}

/**
 * Renders a row of 1–5 stars indicating puzzle quality level.
 * Filled stars are gold (#FFD700), empty stars are gray (#CCCCCC).
 *
 * Returns null if quality is 0 (unscored).
 */
export const QualityStars: FunctionalComponent<QualityStarsProps> = ({
  quality,
  size = 14,
  className = '',
  style,
}) => {
  if (quality <= 0) return null;

  const filled = Math.min(Math.max(Math.round(quality), 1), MAX_STARS);
  const stars: JSX.Element[] = [];

  for (let i = 1; i <= MAX_STARS; i++) {
    const isFilled = i <= filled;
    stars.push(
      <StarIcon
        key={i}
        size={size}
        filled={isFilled}
        style={{ color: isFilled ? FILLED_COLOR : EMPTY_COLOR }}
      />
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-0.5 ${className}`}
      style={style}
      role="img"
      aria-roledescription="rating"
      aria-label={`Quality: ${filled} out of ${MAX_STARS}`}
      data-testid="quality-stars"
    >
      {stars}
    </span>
  );
};
