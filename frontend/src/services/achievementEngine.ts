/**
 * Achievement Engine Service
 * @module services/achievementEngine
 *
 * Evaluates achievement thresholds against current user progress
 * and tracks newly unlocked achievements in localStorage.
 */

import type { UserProgress, Achievement } from '../models/progress';
import { loadProgress } from './progressTracker';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AchievementDefinition {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly target: number;
  readonly evaluate: (progress: UserProgress) => number;
}

export interface AchievementNotification {
  readonly achievement: Achievement;
  readonly isNew: boolean;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STORAGE_KEY = 'yen-go-achievement-progress';

const ACHIEVEMENT_DEFINITIONS: readonly AchievementDefinition[] = [
  // Puzzle milestones
  { id: 'first-solve', name: 'First Steps', description: 'Solve your first puzzle', target: 1, evaluate: p => p.statistics.totalSolved },
  { id: 'solve-10', name: 'Getting Started', description: 'Solve 10 puzzles', target: 10, evaluate: p => p.statistics.totalSolved },
  { id: 'solve-50', name: 'Dedicated', description: 'Solve 50 puzzles', target: 50, evaluate: p => p.statistics.totalSolved },
  { id: 'solve-100', name: 'Centurion', description: 'Solve 100 puzzles', target: 100, evaluate: p => p.statistics.totalSolved },
  { id: 'solve-500', name: 'Scholar', description: 'Solve 500 puzzles', target: 500, evaluate: p => p.statistics.totalSolved },
  { id: 'solve-1000', name: 'Master', description: 'Solve 1000 puzzles', target: 1000, evaluate: p => p.statistics.totalSolved },

  // Perfect solves
  { id: 'perfect-5', name: 'Sharp Eye', description: '5 perfect solves', target: 5, evaluate: p => p.statistics.perfectSolves },
  { id: 'perfect-25', name: 'Precision', description: '25 perfect solves', target: 25, evaluate: p => p.statistics.perfectSolves },
  { id: 'perfect-100', name: 'Flawless', description: '100 perfect solves', target: 100, evaluate: p => p.statistics.perfectSolves },

  // Streak achievements
  { id: 'streak-3', name: 'On a Roll', description: '3-day streak', target: 3, evaluate: p => p.streakData.currentStreak },
  { id: 'streak-7', name: 'Weekly Warrior', description: '7-day streak', target: 7, evaluate: p => p.streakData.currentStreak },
  { id: 'streak-30', name: 'Monthly Master', description: '30-day streak', target: 30, evaluate: p => p.streakData.currentStreak },
  { id: 'streak-longest-14', name: 'Consistency', description: '14-day longest streak', target: 14, evaluate: p => p.streakData.longestStreak },
  { id: 'streak-longest-60', name: 'Unwavering', description: '60-day longest streak', target: 60, evaluate: p => p.streakData.longestStreak },

  // Rush achievements
  { id: 'rush-50', name: 'Speed Reader', description: 'Rush score of 50+', target: 50, evaluate: p => maxRushScore(p) },
  { id: 'rush-100', name: 'Lightning', description: 'Rush score of 100+', target: 100, evaluate: p => maxRushScore(p) },

  // Time milestones
  { id: 'time-1h', name: 'Committed', description: 'Spend 1 hour solving', target: 3600000, evaluate: p => p.statistics.totalTimeMs },
  { id: 'time-10h', name: 'Devoted', description: 'Spend 10 hours solving', target: 36000000, evaluate: p => p.statistics.totalTimeMs },

  // Hint discipline
  { id: 'no-hints-10', name: 'Self-Reliant', description: '10 solves without hints', target: 10, evaluate: p => countNoHintSolves(p) },
  { id: 'no-hints-50', name: 'Independent', description: '50 solves without hints', target: 50, evaluate: p => countNoHintSolves(p) },
  { id: 'no-hints-100', name: 'Unassisted', description: '100 solves without hints', target: 100, evaluate: p => countNoHintSolves(p) },
];

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function maxRushScore(p: UserProgress): number {
  const scores = p.statistics.rushHighScores;
  if (scores.length === 0) return 0;
  return Math.max(...scores.map(s => s.score));
}

function countNoHintSolves(p: UserProgress): number {
  return Object.values(p.completedPuzzles).filter(c => c.hintsUsed === 0).length;
}

function loadUnlocked(): Set<string> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const ids = JSON.parse(raw) as string[];
    return new Set(ids);
  } catch {
    return new Set();
  }
}

function saveUnlocked(ids: Set<string>): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Evaluate all achievement definitions against current progress.
 * Returns notifications for all unlocked achievements, with `isNew: true`
 * for those unlocked since the last evaluation.
 */
export function evaluateAchievements(): AchievementNotification[] {
  const progressResult = loadProgress();
  if (!progressResult.success || !progressResult.data) {
    return [];
  }

  const progress = progressResult.data;
  const previouslyUnlocked = loadUnlocked();
  const currentlyUnlocked = new Set<string>(previouslyUnlocked);
  const notifications: AchievementNotification[] = [];
  const now = new Date().toISOString();

  for (const def of ACHIEVEMENT_DEFINITIONS) {
    const value = def.evaluate(progress);
    if (value >= def.target) {
      const isNew = !previouslyUnlocked.has(def.id);
      currentlyUnlocked.add(def.id);

      notifications.push({
        achievement: {
          id: def.id,
          name: def.name,
          description: def.description,
          target: def.target,
          progress: value,
          ...(isNew ? { unlockedAt: now } : {}),
        },
        isNew,
      });
    }
  }

  saveUnlocked(currentlyUnlocked);
  return notifications;
}
