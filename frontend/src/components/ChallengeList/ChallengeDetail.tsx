/**
 * ChallengeDetail - Detailed view of a single challenge with puzzle grid
 * @module components/ChallengeList/ChallengeDetail
 *
 * Covers: US2 Scenario 5 - View puzzles organized by 9 Skill Levels
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Composes SkillLevelTabs and PuzzleGrid
 * - VI. Accessibility: Proper heading hierarchy, ARIA labels
 */

import type { JSX } from 'preact';
import { useState, useCallback } from 'preact/hooks';
import { LEVELS, LEVEL_SLUGS, type LevelSlug } from '../../lib/levels/config';
import { SkillLevelTabs } from './SkillLevelTabs';
import { PuzzleGrid, type PuzzleGridItem } from './PuzzleGrid';
import { UnlockMessage } from './UnlockMessage';

/** SkillLevel is now LevelSlug from config */
type SkillLevel = LevelSlug;

/**
 * Format rank range from config object to display string
 */
function formatRankRange(range: { readonly min: string; readonly max: string }): string {
  return `${range.min}-${range.max}`;
}

/** SKILL_LEVELS derived from config */
const SKILL_LEVELS = Object.fromEntries(
  LEVELS.map((lvl) => [lvl.slug, { name: lvl.name, rankRange: formatRankRange(lvl.rankRange) }])
) as Record<LevelSlug, { name: string; rankRange: string }>;

/**
 * Challenge detail data
 */
export interface ChallengeDetailData {
  /** Challenge ID */
  readonly id: string;
  /** Display date */
  readonly date: string;
  /** Formatted display date */
  readonly displayDate: string;
  /** Whether challenge is unlocked */
  readonly isUnlocked: boolean;
  /** Required challenge ID for unlock (if locked) */
  readonly requiredChallengeId?: string;
  /** Required challenge display date (if locked) */
  readonly requiredChallengeDate?: string;
  /** Puzzles by skill level */
  readonly puzzlesByLevel: Readonly<Record<LevelSlug, readonly PuzzleGridItem[]>>;
  /** Total puzzles */
  readonly totalPuzzles: number;
  /** Completed puzzles */
  readonly completedPuzzles: number;
}

/**
 * Props for ChallengeDetail component
 */
export interface ChallengeDetailProps {
  /** Challenge data */
  readonly challenge: ChallengeDetailData;
  /** Callback when a puzzle is selected */
  readonly onSelectPuzzle: (puzzleId: string) => void;
  /** Callback for back navigation */
  readonly onBack?: () => void;
  /** Initial skill level to show */
  readonly initialLevel?: LevelSlug;
  /** Optional CSS class */
  readonly className?: string;
}

/**
 * Styles for ChallengeDetail component
 */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    background: 'var(--color-bg-elevated)',
  },
  header: {
    padding: '1rem',
    borderBottom: '1px solid var(--color-bg-secondary)',
    background: 'linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-bg-elevated) 100%)',
  },
  headerTop: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '0.75rem',
  },
  backButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    border: 'none',
    background: 'transparent',
    cursor: 'pointer',
    borderRadius: '50%',
    transition: 'background 0.2s ease',
  },
  title: {
    flex: 1,
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
  },
  progress: {
    fontSize: '0.85rem',
    color: 'var(--color-text-muted)',
    fontWeight: '500',
  },
  progressComplete: {
    fontSize: '0.85rem',
    color: 'var(--color-success-solid)',
    fontWeight: '600',
  },
  tabs: {
    padding: '0.75rem 1rem',
  },
  levelInfo: {
    padding: '0.5rem 1rem',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid var(--color-bg-secondary)',
  },
  levelName: {
    fontSize: '0.9rem',
    fontWeight: '600',
    color: 'var(--color-text-primary)',
  },
  levelRange: {
    fontSize: '0.8rem',
    color: 'var(--color-text-muted)',
  },
  content: {
    flex: 1,
    overflow: 'auto',
    padding: '0.5rem',
  },
  locked: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
    textAlign: 'center',
  },
};

/**
 * Back arrow icon
 */
function BackIcon(): JSX.Element {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--color-text-primary)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

/**
 * Calculate completion counts by level
 */
function getCompletedByLevel(
  puzzlesByLevel: Readonly<Record<LevelSlug, readonly PuzzleGridItem[]>>
): Record<LevelSlug, number> {
  return Object.fromEntries(
    LEVEL_SLUGS.map((slug) => [
      slug,
      puzzlesByLevel[slug]?.filter((p) => p.isCompleted).length ?? 0,
    ])
  ) as Record<LevelSlug, number>;
}

/**
 * Calculate puzzle counts by level
 */
function getPuzzleCountsByLevel(
  puzzlesByLevel: Readonly<Record<LevelSlug, readonly PuzzleGridItem[]>>
): Record<LevelSlug, number> {
  return Object.fromEntries(
    LEVEL_SLUGS.map((slug) => [slug, puzzlesByLevel[slug]?.length ?? 0])
  ) as Record<LevelSlug, number>;
}

/**
 * Find first level with puzzles (for default selection)
 */
function findFirstLevelWithPuzzles(
  puzzlesByLevel: Readonly<Record<LevelSlug, readonly PuzzleGridItem[]>>
): LevelSlug {
  for (const slug of LEVEL_SLUGS) {
    if (puzzlesByLevel[slug]?.length > 0) {
      return slug;
    }
  }
  return 'novice';
}

/**
 * ChallengeDetail - Shows challenge with skill level tabs and puzzle grid
 */
export function ChallengeDetail({
  challenge,
  onSelectPuzzle,
  onBack,
  initialLevel,
  className,
}: ChallengeDetailProps): JSX.Element {
  // Default to first level with puzzles or initialLevel
  const defaultLevel = initialLevel ?? findFirstLevelWithPuzzles(challenge.puzzlesByLevel);
  const [selectedLevel, setSelectedLevel] = useState<SkillLevel>(defaultLevel);

  const puzzleCounts = getPuzzleCountsByLevel(challenge.puzzlesByLevel);
  const completedCounts = getCompletedByLevel(challenge.puzzlesByLevel);

  const currentPuzzles = challenge.puzzlesByLevel[selectedLevel];
  const currentLevelInfo = SKILL_LEVELS[selectedLevel];

  const isComplete = challenge.completedPuzzles >= challenge.totalPuzzles;

  const handleSelectPuzzle = useCallback(
    (puzzleId: string) => {
      if (challenge.isUnlocked) {
        onSelectPuzzle(puzzleId);
      }
    },
    [challenge.isUnlocked, onSelectPuzzle]
  );

  // Handle locked challenge
  if (!challenge.isUnlocked) {
    return (
      <div style={styles.container} className={className}>
        <div style={styles.header}>
          <div style={styles.headerTop}>
            {onBack && (
              <button
                style={styles.backButton}
                onClick={onBack}
                aria-label="Back to challenge list"
              >
                <BackIcon />
              </button>
            )}
            <h2 style={styles.title}>{challenge.displayDate}</h2>
          </div>
        </div>
        <div style={styles.locked}>
          <UnlockMessage
            requiredChallengeId={challenge.requiredChallengeId ?? ''}
            requiredChallengeDate={challenge.requiredChallengeDate ?? 'previous challenge'}
            variant="modal"
          />
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container} className={className}>
      <div style={styles.header}>
        <div style={styles.headerTop}>
          {onBack && (
            <button
              style={styles.backButton}
              onClick={onBack}
              aria-label="Back to challenge list"
            >
              <BackIcon />
            </button>
          )}
          <h2 style={styles.title}>{challenge.displayDate}</h2>
          <span style={isComplete ? styles.progressComplete : styles.progress}>
            {challenge.completedPuzzles}/{challenge.totalPuzzles}
            {isComplete && ' ✓'}
          </span>
        </div>

        <div style={styles.tabs}>
          <SkillLevelTabs
            selectedLevel={selectedLevel}
            onSelectLevel={setSelectedLevel}
            puzzleCounts={puzzleCounts}
            completedCounts={completedCounts}
          />
        </div>
      </div>

      <div style={styles.levelInfo}>
        <span style={styles.levelName}>
          Level {selectedLevel}: {currentLevelInfo.name}
        </span>
        <span style={styles.levelRange}>{currentLevelInfo.rankRange}</span>
      </div>

      <div style={styles.content}>
        <PuzzleGrid
          puzzles={currentPuzzles}
          onSelectPuzzle={handleSelectPuzzle}
          showBadges={true}
        />
      </div>
    </div>
  );
}

export default ChallengeDetail;
