/**
 * ChallengeList - Displays list of daily challenges
 * @module components/ChallengeList/ChallengeList
 *
 * Covers: US2 (Browse and Select Daily Challenges)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: List component only renders challenges
 * - IV. Local-First: Uses cached challenge data
 */

import type { JSX } from 'preact';
import type { SkillLevel } from '../../types';
import { ChallengeCard, type ChallengeCardData } from './ChallengeCard';
import { EmptyState } from '../shared/GoQuote';

/**
 * Challenge summary data for list display
 */
export interface ChallengeSummary {
  /** Challenge ID (typically date: YYYY-MM-DD) */
  readonly id: string;
  /** Display date (YYYY-MM-DD) */
  readonly date: string;
  /** Total puzzles in challenge */
  readonly totalPuzzles: number;
  /** Puzzles completed by user */
  readonly completedPuzzles: number;
  /** Whether challenge is unlocked */
  readonly isUnlocked: boolean;
  /** Puzzles per skill level */
  readonly puzzlesByLevel: Readonly<Record<SkillLevel, number>>;
}

/**
 * Props for ChallengeList component
 */
export interface ChallengeListProps {
  /** List of challenges to display */
  readonly challenges: readonly ChallengeSummary[];
  /** Currently selected challenge ID */
  readonly selectedId: string | undefined;
  /** Callback when a challenge is selected */
  readonly onSelect: (challengeId: string) => void;
  /** Whether list is loading */
  readonly isLoading?: boolean;
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Format date for display (e.g., "Jan 20, 2026")
 */
function formatDisplayDate(dateStr: string): string {
  try {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

/**
 * Check if a date is today
 */
function isToday(dateStr: string): boolean {
  const today = new Date().toISOString().split('T')[0];
  return dateStr === today;
}

/**
 * ChallengeList - Renders a scrollable list of challenge cards
 */
export function ChallengeList({
  challenges,
  selectedId,
  onSelect,
  isLoading = false,
  className,
}: ChallengeListProps): JSX.Element {
  // Convert to card data format
  const cardData: ChallengeCardData[] = challenges.map((challenge) => ({
    id: challenge.id,
    displayDate: formatDisplayDate(challenge.date),
    totalPuzzles: challenge.totalPuzzles,
    completedPuzzles: challenge.completedPuzzles,
    isUnlocked: challenge.isUnlocked,
    isToday: isToday(challenge.date),
    puzzlesByLevel: challenge.puzzlesByLevel,
  }));

  // Calculate total completed
  const totalCompleted = challenges.reduce((sum, c) => sum + c.completedPuzzles, 0);
  const totalPuzzles = challenges.reduce((sum, c) => sum + c.totalPuzzles, 0);

  if (isLoading) {
    return (
      <div className={`flex flex-col gap-3 overflow-y-auto p-2 ${className ?? ''}`}>
        <div className="flex items-center justify-center p-8 text-sm text-[--color-text-muted]">
          Loading challenges...
        </div>
      </div>
    );
  }

  if (challenges.length === 0) {
    return (
      <div className={`flex flex-col gap-3 overflow-y-auto p-2 ${className ?? ''}`}>
        <EmptyState message="No challenges available." quoteMode="daily" />
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-3 overflow-y-auto p-2 ${className ?? ''}`}>
      <div className="flex items-center justify-between px-2 pt-2">
        <h2 className="m-0 text-lg font-semibold text-[--color-text-primary]">Daily Challenges</h2>
        <span className="text-sm text-[--color-text-muted]">
          {totalCompleted}/{totalPuzzles} solved
        </span>
      </div>

      <div className="flex flex-col gap-3">
        {cardData.map((card) => (
          <ChallengeCard
            key={card.id}
            data={card}
            isSelected={card.id === selectedId}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}

export default ChallengeList;
