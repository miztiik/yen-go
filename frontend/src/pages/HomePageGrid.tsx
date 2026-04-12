/**
 * HomePageGrid - Modern home page with tile grid layout
 * @module pages/HomePageGrid
 *
 * Main landing page with 6-tile grid for all game modes.
 * Uses modal-first navigation pattern.
 *
 * Covers: T048, T049, T050 - Home screen implementation
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { HomeTile, HomeGrid, getTileIcon } from '../components/Home';
import { PageLayout } from '../components/Layout';
import type { StreakData } from '../models/progress';
import { loadProgress, getStatistics } from '../services/progressTracker';
import { getTodaysChallenge } from '../services/dailyChallengeService';
import { loadCollectionIndex, estimateUserLevel } from '../services/collectionService';
import { LEVELS } from '../lib/levels/config';
import { DEFAULT_LEVEL } from '../lib/levels/level-defaults';
import { getTrainingProgress } from '../components/Training';

// ============================================================================
// Types
// ============================================================================

export interface HomePageGridProps {
  /** Callback when navigating to daily challenge */
  onNavigateDaily?: () => void;
  /** Callback when navigating to collection */
  onNavigateCollection?: (collectionId: string) => void;
  /** Callback when navigating to puzzle rush */
  onNavigateRush?: () => void;
  /** Callback when navigating to training */
  onNavigateTraining?: () => void;
  /** Callback when navigating to technique */
  onNavigateTechnique?: () => void;
  /** Callback when navigating to learn */
  onNavigateLearning?: () => void;
  /** Custom className */
  className?: string | undefined;
}

interface HomeState {
  /** Streak data */
  streakData: StreakData;
  /** Daily challenge progress */
  dailyProgress: { completed: number; total: number };
  /** Training progress */
  trainingProgress: { level: string; percent: number };
  /** Rush high score */
  rushHighScore: number;
  /** Number of available collection sets */
  collectionCount: number | null;
  /** User rank label derived from progress */
  rankLabel: string | null;
  /** Next training level label */
  nextLevelLabel: string | null;
}

// Legacy styles object removed — Spec 127, T028/T076. All styling via Tailwind + PageLayout.

// ============================================================================
// Default Data
// ============================================================================

const DEFAULT_STREAK: StreakData = {
  currentStreak: 0,
  longestStreak: 0,
  lastPlayedDate: null,
  streakStartDate: null,
};

// ============================================================================
// Component
// ============================================================================

/**
 * HomePageGrid - Modern home page with tile grid
 */
export function HomePageGrid({
  onNavigateDaily,
  onNavigateCollection,
  onNavigateRush,
  onNavigateTraining,
  onNavigateTechnique,
  onNavigateLearning,
  className = '',
}: HomePageGridProps): JSX.Element {
  const [state, setState] = useState<HomeState>({
    streakData: DEFAULT_STREAK,
    dailyProgress: { completed: 0, total: 3 },
    trainingProgress: {
      level: LEVELS.find((l) => l.slug === DEFAULT_LEVEL)?.name ?? DEFAULT_LEVEL,
      percent: 0,
    },
    rushHighScore: 0,
    collectionCount: null,
    rankLabel: null,
    nextLevelLabel: null,
  });

  // Load user data on mount
  useEffect(() => {
    const loadUserData = async (): Promise<void> => {
      const progressResult = loadProgress();
      if (progressResult.success && progressResult.data) {
        const progress = progressResult.data;
        const stats = getStatistics();

        // Get rush high score
        const rushScores = stats.rushHighScores;
        const rushHighScore = rushScores.length > 0 ? rushScores[0]!.score : 0;

        // Derive training level from progress
        const userLevel = estimateUserLevel();
        const trainingData = getTrainingProgress();
        const levelDisplayName =
          userLevel.charAt(0).toUpperCase() + userLevel.slice(1).replace(/-/g, ' ');

        setState((prev) => ({
          ...prev,
          streakData: progress.streakData,
          rushHighScore,
          trainingProgress: {
            level: levelDisplayName,
            percent: trainingData?.byLevel[userLevel]?.completed ?? 0,
          },
          rankLabel: levelDisplayName,
        }));
      }

      // Load collection count
      const indexResult = await loadCollectionIndex();
      if (indexResult.success && indexResult.data) {
        setState((prev) => ({
          ...prev,
          collectionCount: indexResult.data!.collections.length,
        }));
      }

      // Load daily challenge info
      const dailyResult = getTodaysChallenge();
      if (dailyResult.success && dailyResult.data) {
        const puzzles = dailyResult.data.standard?.puzzles ?? [];
        setState((prev) => ({
          ...prev,
          dailyProgress: { completed: 0, total: puzzles.length },
        }));
      }
    };

    void loadUserData();
  }, []);

  // Navigation handlers
  const handleDailyClick = useCallback(() => {
    onNavigateDaily?.();
  }, [onNavigateDaily]);

  const handleCollectionsClick = useCallback(() => {
    // Navigate to collections browse page
    // Use a dummy collection ID to trigger the collections route
    // Actually, we just navigate to the collections page
    onNavigateCollection?.('');
  }, [onNavigateCollection]);

  const handleRushClick = useCallback(() => {
    onNavigateRush?.();
  }, [onNavigateRush]);

  const handleTrainingClick = useCallback(() => {
    onNavigateTraining?.();
  }, [onNavigateTraining]);

  const handleTechniqueClick = useCallback(() => {
    onNavigateTechnique?.();
  }, [onNavigateTechnique]);

  const handleLearningClick = useCallback(() => {
    onNavigateLearning?.();
  }, [onNavigateLearning]);

  const { streakData, dailyProgress, trainingProgress, rushHighScore } = state;

  return (
    <PageLayout variant="single-column">
      <PageLayout.Content className={`mx-auto w-full max-w-7xl px-4 py-6 md:px-8 ${className}`}>
        {/* Hero */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-[var(--color-text-primary)] md:text-3xl">
            Ready for Go, <span className="text-[var(--color-accent)]">Sensei?</span>
          </h1>
          <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
            Pick a mode to sharpen your skills today.
          </p>
        </div>

        {/* Tile Grid */}
        <HomeGrid>
          {/* Daily Challenge */}
          <HomeTile
            variant="daily"
            title="Daily Challenge"
            description="Solve today's puzzles to keep your streak burning!"
            icon={getTileIcon('daily', { size: 'lg' })}
            statLabel={
              streakData.currentStreak > 0 ? `Streak: ${streakData.currentStreak} Days` : undefined
            }
            progress={
              dailyProgress.total > 0
                ? Math.round((dailyProgress.completed / dailyProgress.total) * 100)
                : undefined
            }
            progressLabelLeft={`${dailyProgress.completed}/${dailyProgress.total} Solved`}
            progressLabelRight="Keep it up!"
            isFeatured={streakData.currentStreak === 0}
            onClick={handleDailyClick}
          />

          {/* Puzzle Rush */}
          <HomeTile
            variant="rush"
            title="Puzzle Rush"
            description="Race against the clock. How many can you solve?"
            icon={getTileIcon('rush', { size: 'lg' })}
            statValue={rushHighScore > 0 ? `Best: ${rushHighScore}` : undefined}
            onClick={handleRushClick}
          />

          {/* Collections */}
          <HomeTile
            variant="collections"
            title="Collections"
            description="Browse curated puzzles by topic, shape, or technique."
            icon={getTileIcon('collections', { size: 'lg' })}
            statLabel={state.collectionCount ? `${state.collectionCount} Sets` : 'Sets'}
            tags={['Tesuji', 'Life & Death', 'Endgame']}
            onClick={handleCollectionsClick}
          />

          {/* Training */}
          <HomeTile
            variant="training"
            title="Training"
            description={`Progress through levels. Currently mastering ${trainingProgress.level}.`}
            icon={getTileIcon('training', { size: 'lg' })}
            statValue={state.rankLabel ? `Level: ${state.rankLabel}` : undefined}
            progress={trainingProgress.percent}
            progressLabelLeft={trainingProgress.level}
            progressLabelRight={state.nextLevelLabel ? `Next: ${state.nextLevelLabel}` : undefined}
            onClick={handleTrainingClick}
          />

          {/* Technique of the Day */}
          <HomeTile
            variant="technique"
            title="Technique"
            description="Master specific Go techniques with focused practice."
            icon={getTileIcon('technique', { size: 'lg' })}
            tags={['Net', 'Ladder', 'Snapback', 'Ko']}
            onClick={handleTechniqueClick}
          />

          {/* Learn Go */}
          <HomeTile
            variant="learning"
            title="Learn Go"
            description="Master Go from beginner to dan — interactive lessons and puzzles."
            icon={getTileIcon('learning', { size: 'lg' })}
            tags={['Beginner', 'Tesuji', 'Life & Death']}
            onClick={handleLearningClick}
          />
        </HomeGrid>
      </PageLayout.Content>
    </PageLayout>
  );
}

export default HomePageGrid;
