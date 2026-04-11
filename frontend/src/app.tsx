import { useState, useEffect, useCallback } from 'preact/hooks';
import type { FunctionComponent, JSX } from 'preact';
import { initializeProgressSystem, getStreakData } from '@services/progressTracker';
import { AppHeader } from './components/Layout/AppHeader';
import { HomePageGrid } from './pages/HomePageGrid';
import { CollectionViewPage } from './pages/CollectionViewPage';
import { TechniqueViewPage } from './pages/TechniqueViewPage';
import { DailyChallengePage } from './pages/DailyChallengePage';
import { DailyBrowsePage } from './pages/DailyBrowsePage';
import type { DailyChallengeMode } from './models/dailyChallenge';
import { PuzzleRushPage } from './pages/PuzzleRushPage';
import { RushBrowsePage } from './pages/RushBrowsePage';
import { CollectionsBrowsePage } from './pages/CollectionsBrowsePage';
import { TechniqueBrowsePage } from './pages/TechniqueBrowsePage';
import { TrainingViewPage } from './pages/TrainingViewPage';
import { TrainingBrowsePage } from './pages/TrainingBrowsePage';
import { RandomChallengePage } from './pages/RandomChallengePage';
import { RandomPage } from './pages/RandomPage';
import { LearningPage } from './pages/LearningPage';
import { ProgressPage } from './pages/ProgressPage';
import { SmartPracticePage } from './pages/SmartPracticePage';
import type { RushDuration } from './types/goban';
import { type SkillLevel } from './models/collection';
import { getRushHighScore } from './services/progress';

import { audioService } from './services/audioService';
import { parseRoute, navigateTo, isPuzzleSolvingRoute } from './lib/routing/routes';
import type { Route } from './lib/routing/routes';

// Preload all sound effects for instant playback (no first-play latency)
audioService.preload();

export const App: FunctionComponent = (): JSX.Element => {
  // Route state
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.pathname, window.location.search));
  
  // Get current streak for header display
  const [streak, setStreak] = useState<number>(0);
  
  // Puzzle Rush state
  const [rushDuration, setRushDuration] = useState<RushDuration | null>(null);
  const [rushLevelId, setRushLevelId] = useState<number | null>(null);
  const [rushTagId, setRushTagId] = useState<number | null>(null);

  // T065: Initialize progress system inside component (deferred from module scope
  // so boot can parallelize config fetch and app import without ordering issues)
  useEffect(() => {
    initializeProgressSystem();
  }, []);
  
  // Load streak on mount
  useEffect(() => {
    try {
      const streakData = getStreakData();
      setStreak(streakData.currentStreak);
    } catch {
      // Ignore errors, streak defaults to 0
    }
  }, []);
  
  // Handle browser back/forward for routes
  useEffect(() => {
    const handlePopState = (): void => {
      setRoute(parseRoute(window.location.pathname, window.location.search));
    };
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Reset Rush session state when navigating away from Rush mode.
  // Without this, returning to /modes/rush re-enters the stale game session
  // instead of showing the browse/setup page.
  useEffect(() => {
    if (route.type !== 'modes-rush' && rushDuration !== null) {
      setRushDuration(null);
      setRushLevelId(null);
      setRushTagId(null);
    }
  }, [route.type, rushDuration]);
  
  const handleBackToHome = useCallback(() => {
    const newRoute: Route = { type: 'home' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  // Navigation handlers for HomePageGrid
  const handleNavigateDaily = useCallback((mode?: DailyChallengeMode, date?: string) => {
    if (date) {
      const newRoute: Route = { type: 'modes-daily-date', date, ...(mode === 'timed' ? { mode } : {}) };
      setRoute(newRoute);
      navigateTo(newRoute);
    } else {
      const newRoute: Route = { type: 'modes-daily' };
      setRoute(newRoute);
      navigateTo(newRoute);
    }
  }, []);

  const handleNavigateCollection = useCallback((collectionId: string) => {
    if (collectionId) {
      const newRoute: Route = { type: 'context', dimension: 'collection', slug: collectionId, filters: {} };
      setRoute(newRoute);
      navigateTo(newRoute);
    } else {
      // From home tile — go to collections browse page
      const newRoute: Route = { type: 'collections-browse' };
      setRoute(newRoute);
      navigateTo(newRoute);
    }
  }, []);

  const handleNavigateRush = useCallback(() => {
    const newRoute: Route = { type: 'modes-rush' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateTraining = useCallback(() => {
    const newRoute: Route = { type: 'training-browse' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateTechnique = useCallback(() => {
    const newRoute: Route = { type: 'technique-browse' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleSelectTechnique = useCallback((techniqueId: string) => {
    const newRoute: Route = { type: 'context', dimension: 'technique', slug: techniqueId, filters: {} };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateRandom = useCallback(() => {
    const newRoute: Route = { type: 'modes-random' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateLearning = useCallback(() => {
    const newRoute: Route = { type: 'learning-browse' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateProgress = useCallback(() => {
    const newRoute: Route = { type: 'progress' };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  const handleNavigateSmartPractice = useCallback((techniques?: readonly string[]) => {
    const newRoute: Route = { type: 'smart-practice', ...(techniques?.length ? { techniques: [...techniques] } : {}) };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  // Training navigation handlers
  const handleSelectTrainingLevel = useCallback((level: SkillLevel) => {
    const newRoute: Route = { type: 'context', dimension: 'training', slug: level, filters: {} };
    setRoute(newRoute);
    navigateTo(newRoute);
  }, []);

  // Random challenge navigation handlers
  // C1: Accept optional tagSlug so RandomPage tag filter is functional
  const handleSelectRandomPuzzle = useCallback((level: SkillLevel, tagSlug?: string) => {
    // Navigate to random-solving view with selected level
    // RandomChallengePage handles the actual puzzle loading
    const newRoute: Route = { type: 'modes-random' };
    setRoute(newRoute);
    // Store selected level + tag for RandomChallengePage
    setRandomLevel(level);
    setRandomTagSlug(tagSlug ?? null);
  }, []);

  // Random level/tag state (set when user picks from RandomPage)
  const [randomLevel, setRandomLevel] = useState<SkillLevel | null>(null);
  const [randomTagSlug, setRandomTagSlug] = useState<string | null>(null);

  // Puzzle Rush handlers
  const handleRushStart = useCallback((duration: RushDuration, levelId: number | null = null, tagId: number | null = null) => {
    setRushDuration(duration);
    setRushLevelId(levelId);
    setRushTagId(tagId);
  }, []);

  const handleRushNewGame = useCallback(() => {
    setRushDuration(null);
    setRushLevelId(null);
    setRushTagId(null);
  }, []);

  // ============================================================================
  // Route Content Rendering
  // ============================================================================

  const renderRouteContent = (): JSX.Element => {
    // Home page
    if (route.type === 'home') {
      return (
        <HomePageGrid
          onNavigateDaily={handleNavigateDaily}
          onNavigateCollection={handleNavigateCollection}
          onNavigateRush={handleNavigateRush}
          onNavigateTraining={handleNavigateTraining}
          onNavigateTechnique={handleNavigateTechnique}
          onNavigateLearning={handleNavigateLearning}
        />
      );
    }

    // Context routes (collection, technique, training, quality)
    if (route.type === 'context') {
      if (route.dimension === 'collection') {
        return (
          <CollectionViewPage
            collectionId={route.slug}
            startIndex={route.offset}
            onBack={() => {
              const browseRoute: Route = { type: 'collections-browse' };
              setRoute(browseRoute);
              navigateTo(browseRoute);
            }}
          />
        );
      }

      if (route.dimension === 'technique') {
        return (
          <TechniqueViewPage
            techniqueId={route.slug}
            startIndex={route.offset}
            onBack={() => {
              const browseRoute: Route = { type: 'technique-browse' };
              setRoute(browseRoute);
              navigateTo(browseRoute);
            }}
          />
        );
      }

      if (route.dimension === 'training') {
        return (
          <TrainingViewPage
            level={route.slug}
            {...(route.offset !== undefined && { startIndex: route.offset })}
            onNavigateHome={handleBackToHome}
            onNavigateTraining={() => {
              const newRoute: Route = { type: 'training-browse' };
              setRoute(newRoute);
              navigateTo(newRoute);
            }}
          />
        );
      }

      if (route.dimension === 'quality') {
        // Future: quality browsing. For now, fallback to home
        return (
          <HomePageGrid
            onNavigateDaily={handleNavigateDaily}
            onNavigateCollection={handleNavigateCollection}
            onNavigateRush={handleNavigateRush}
            onNavigateTraining={handleNavigateTraining}
            onNavigateTechnique={handleNavigateTechnique}
            onNavigateLearning={handleNavigateLearning}
          />
        );
      }
    }

    // Daily challenge browse page (mode selection)
    if (route.type === 'modes-daily') {
      return (
        <DailyBrowsePage
          onStartChallenge={handleNavigateDaily}
          onNavigateHome={handleBackToHome}
        />
      );
    }

    // Daily challenge puzzle solving (specific date)
    if (route.type === 'modes-daily-date') {
      return (
        <DailyChallengePage
          date={route.date}
          mode={route.mode}
          onBack={handleBackToHome}
        />
      );
    }

    // Puzzle Rush mode
    if (route.type === 'modes-rush') {
      if (rushDuration === null) {
        const bestScoreValue = getRushHighScore();
        return (
          <RushBrowsePage
            onStartRush={handleRushStart}
            onNavigateHome={handleBackToHome}
            bestScore={bestScoreValue}
          />
        );
      }

      return (
        <PuzzleRushPage
          durationSeconds={rushDuration}
          selectedLevelId={rushLevelId}
          selectedTagId={rushTagId}
          onNavigateHome={handleBackToHome}
          onNewRush={handleRushNewGame}
        />
      );
    }

    // Collections browse page
    if (route.type === 'collections-browse') {
      return (
        <CollectionsBrowsePage
          onNavigateToCollection={handleNavigateCollection}
          onNavigateHome={handleBackToHome}
        />
      );
    }

    // Technique focus page (tag category browsing)
    if (route.type === 'technique-browse') {
      return (
        <TechniqueBrowsePage
          onNavigateBack={handleBackToHome}
          onSelectTechnique={handleSelectTechnique}
        />
      );
    }

    // Training — level selection browse page
    if (route.type === 'training-browse') {
      return (
        <TrainingBrowsePage
          onSelectLevel={handleSelectTrainingLevel}
          onNavigateHome={handleBackToHome}
          onNavigateRandom={handleNavigateRandom}
        />
      );
    }

    // Random Challenge
    if (route.type === 'modes-random') {
      if (randomLevel === null) {
        return (
          <RandomPage
            onSelectRandomPuzzle={handleSelectRandomPuzzle}
            onNavigateHome={handleBackToHome}
          />
        );
      }

      return (
        <RandomChallengePage
          level={randomLevel}
          tagSlug={randomTagSlug}
          onNavigateHome={handleBackToHome}
        />
      );
    }

    // Learn Go — topic browse
    if (route.type === 'learning-browse') {
      return (
        <LearningPage
          onNavigateHome={handleBackToHome}
        />
      );
    }

    // Progress dashboard
    if (route.type === 'progress') {
      return (
        <ProgressPage
          onBack={handleBackToHome}
          onStartSmartPractice={handleNavigateSmartPractice}
        />
      );
    }

    // Smart practice — adaptive technique-focused puzzles
    if (route.type === 'smart-practice') {
      return (
        <SmartPracticePage
          onBack={handleNavigateProgress}
          {...(route.techniques ? { techniques: route.techniques } : {})}
        />
      );
    }

    // Fallback: home
    return (
      <HomePageGrid
        onNavigateDaily={handleNavigateDaily}
        onNavigateCollection={handleNavigateCollection}
        onNavigateRush={handleNavigateRush}
        onNavigateTraining={handleNavigateTraining}
        onNavigateTechnique={handleNavigateTechnique}
        onNavigateLearning={handleNavigateLearning}
      />
    );
  };

  // ============================================================================
  // Global Layout: AppHeader always visible on every page
  // ============================================================================

  // Compact header (icon-only logo) on puzzle-solving pages to maximize board space
  const isPuzzlePlayerRoute = isPuzzleSolvingRoute(route) || route.type === 'modes-rush';

  return (
    <div className="flex min-h-screen flex-col bg-[var(--color-bg-primary)]">
      <AppHeader streak={streak} compact={isPuzzlePlayerRoute} onClickProfile={handleNavigateProgress} />
      <div class="route-fade-in" key={route.type}>
        {renderRouteContent()}
      </div>
    </div>
  );
};
