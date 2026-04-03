/**
 * StreakDisplay component - shows current and longest streak.
 * @module components/Stats/StreakDisplay
 */

import type { JSX } from 'preact';
import type { StreakData } from '../../types/progress';
import { FireIcon } from '../shared/icons/FireIcon';

/**
 * StreakDisplay props
 */
export interface StreakDisplayProps {
  /** Streak data to display */
  readonly streakData: StreakData;
  /** Optional compact mode */
  readonly compact?: boolean;
}

/**
 * Styles for the StreakDisplay component.
 */
const styles = {
  container: `
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px;
    background: linear-gradient(135deg, #f97316 0%, #fb923c 100%);
    border-radius: 12px;
    color: white;
  `,
  containerCompact: `
    padding: 12px;
    gap: 12px;
  `,
  fireIcon: `
    font-size: 2.5rem;
  `,
  fireIconCompact: `
    font-size: 1.5rem;
  `,
  content: `
    flex: 1;
  `,
  currentStreak: `
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
    margin: 0;
  `,
  currentStreakCompact: `
    font-size: 1.5rem;
  `,
  streakLabel: `
    font-size: 0.875rem;
    opacity: 0.9;
    margin: 4px 0 0 0;
  `,
  longestStreak: `
    text-align: right;
  `,
  longestValue: `
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  `,
  longestLabel: `
    font-size: 0.75rem;
    opacity: 0.8;
    margin: 2px 0 0 0;
  `,
  noStreak: `
    opacity: 0.7;
    font-style: italic;
  `,
};

/**
 * Format streak count with proper pluralization.
 */
function formatStreakDays(count: number): string {
  if (count === 1) return '1 day';
  return `${count} days`;
}

/**
 * StreakDisplay component - shows streak information.
 */
export function StreakDisplay({
  streakData,
  compact = false,
}: StreakDisplayProps): JSX.Element {
  const { currentStreak, longestStreak } = streakData;

  const containerStyle = compact
    ? `${styles.container} ${styles.containerCompact}`
    : styles.container;

  const fireStyle = compact
    ? `${styles.fireIcon} ${styles.fireIconCompact}`
    : styles.fireIcon;

  const currentStyle = compact
    ? `${styles.currentStreak} ${styles.currentStreakCompact}`
    : styles.currentStreak;

  // No streak yet
  if (currentStreak === 0 && longestStreak === 0) {
    return (
      <div class="streak-display" style={containerStyle}>
        <span style={fireStyle}><FireIcon size={compact ? 20 : 28} /></span>
        <div style={styles.content}>
          <p style={`${currentStyle} ${styles.noStreak}`}>No streak yet</p>
          <p style={styles.streakLabel}>Solve a puzzle to start your streak!</p>
        </div>
      </div>
    );
  }

  return (
    <div class="streak-display" style={containerStyle}>
      <span style={fireStyle}><FireIcon size={compact ? 20 : 28} /></span>
      <div style={styles.content}>
        <p style={currentStyle}>{currentStreak}</p>
        <p style={styles.streakLabel}>
          {currentStreak === 0 ? 'Streak broken' : formatStreakDays(currentStreak)}
        </p>
      </div>
      {longestStreak > 0 && (
        <div style={styles.longestStreak}>
          <p style={styles.longestValue}>{longestStreak}</p>
          <p style={styles.longestLabel}>Best</p>
        </div>
      )}
    </div>
  );
}

export default StreakDisplay;
