/**
 * Rush mode scoring system.
 * Calculates scores based on correctness, time, and streaks.
 * @module lib/rush/scoring
 */

/**
 * Score breakdown for a single puzzle.
 */
export interface PuzzleScore {
  /** Base points for solving correctly */
  readonly basePoints: number;
  /** Time bonus points */
  readonly timeBonus: number;
  /** Streak bonus points */
  readonly streakBonus: number;
  /** Penalty for skip (negative) */
  readonly skipPenalty: number;
  /** Total points for this puzzle */
  readonly total: number;
}

/**
 * Scoring state.
 */
export interface ScoringState {
  /** Total accumulated score */
  readonly totalScore: number;
  /** Current correct streak */
  readonly currentStreak: number;
  /** Longest streak achieved */
  readonly longestStreak: number;
  /** Perfect run (no skips, all correct) */
  readonly isPerfect: boolean;
  /** Number of puzzles scored */
  readonly puzzleCount: number;
  /** All individual puzzle scores */
  readonly puzzleScores: readonly PuzzleScore[];
}

/**
 * Scoring configuration.
 */
export interface ScoringConfig {
  /** Base points per correct puzzle (default: 100) */
  readonly basePoints?: number;
  /** Maximum time bonus points (default: 50) */
  readonly maxTimeBonus?: number;
  /** Time threshold for max bonus in ms (default: 5000) */
  readonly timeBonusThreshold?: number;
  /** Streak milestone for bonus (default: 3) */
  readonly streakMilestone?: number;
  /** Bonus points per streak milestone (default: 25) */
  readonly streakBonusPoints?: number;
  /** Penalty points for skipping (default: -10) */
  readonly skipPenalty?: number;
}

/**
 * Default scoring configuration.
 */
export const DEFAULT_SCORING_CONFIG: Required<ScoringConfig> = {
  basePoints: 100,
  maxTimeBonus: 50,
  timeBonusThreshold: 5000,
  streakMilestone: 3,
  streakBonusPoints: 25,
  skipPenalty: -10,
};

/**
 * Create initial scoring state.
 */
export function createScoringState(): ScoringState {
  return {
    totalScore: 0,
    currentStreak: 0,
    longestStreak: 0,
    isPerfect: true,
    puzzleCount: 0,
    puzzleScores: [],
  };
}

/**
 * Calculate time bonus based on solve time.
 * Faster solves get more bonus points.
 */
export function calculateTimeBonus(
  timeMs: number,
  config: ScoringConfig = {}
): number {
  const { maxTimeBonus, timeBonusThreshold } = {
    ...DEFAULT_SCORING_CONFIG,
    ...config,
  };

  if (timeMs >= timeBonusThreshold) {
    return 0;
  }

  // Linear interpolation: faster = more points
  const ratio = 1 - (timeMs / timeBonusThreshold);
  return Math.round(maxTimeBonus * ratio);
}

/**
 * Calculate streak bonus.
 * Bonus awarded at each streak milestone (3, 6, 9, etc.)
 */
export function calculateStreakBonus(
  streak: number,
  config: ScoringConfig = {}
): number {
  const { streakMilestone, streakBonusPoints } = {
    ...DEFAULT_SCORING_CONFIG,
    ...config,
  };

  // Award bonus when hitting milestone
  if (streak > 0 && streak % streakMilestone === 0) {
    return streakBonusPoints;
  }

  return 0;
}

/**
 * Rush mode scoring system.
 */
export class RushScoring {
  private state: ScoringState;
  private config: Required<ScoringConfig>;

  constructor(config: ScoringConfig = {}) {
    this.config = { ...DEFAULT_SCORING_CONFIG, ...config };
    this.state = createScoringState();
  }

  /**
   * Get current scoring state.
   */
  getState(): ScoringState {
    return this.state;
  }

  /**
   * Get current total score.
   */
  getTotalScore(): number {
    return this.state.totalScore;
  }

  /**
   * Get current streak.
   */
  getCurrentStreak(): number {
    return this.state.currentStreak;
  }

  /**
   * Check if run is still perfect.
   */
  isPerfectRun(): boolean {
    return this.state.isPerfect;
  }

  /**
   * Score a correct answer.
   */
  scoreCorrect(timeMs: number): PuzzleScore {
    const newStreak = this.state.currentStreak + 1;

    const basePoints = this.config.basePoints;
    const timeBonus = calculateTimeBonus(timeMs, this.config);
    const streakBonus = calculateStreakBonus(newStreak, this.config);
    const total = basePoints + timeBonus + streakBonus;

    const score: PuzzleScore = {
      basePoints,
      timeBonus,
      streakBonus,
      skipPenalty: 0,
      total,
    };

    this.state = {
      ...this.state,
      totalScore: this.state.totalScore + total,
      currentStreak: newStreak,
      longestStreak: Math.max(this.state.longestStreak, newStreak),
      puzzleCount: this.state.puzzleCount + 1,
      puzzleScores: [...this.state.puzzleScores, score],
    };

    return score;
  }

  /**
   * Score a skipped puzzle.
   */
  scoreSkip(): PuzzleScore {
    const score: PuzzleScore = {
      basePoints: 0,
      timeBonus: 0,
      streakBonus: 0,
      skipPenalty: this.config.skipPenalty,
      total: this.config.skipPenalty,
    };

    this.state = {
      ...this.state,
      totalScore: Math.max(0, this.state.totalScore + this.config.skipPenalty),
      currentStreak: 0, // Reset streak
      isPerfect: false,
      puzzleCount: this.state.puzzleCount + 1,
      puzzleScores: [...this.state.puzzleScores, score],
    };

    return score;
  }

  /**
   * Score time expiry (forfeit).
   */
  scoreForfeit(): void {
    this.state = {
      ...this.state,
      isPerfect: false,
    };
  }

  /**
   * Get final results summary.
   */
  getResults(): {
    totalScore: number;
    puzzlesSolved: number;
    puzzlesSkipped: number;
    longestStreak: number;
    isPerfect: boolean;
    averageTimeBonus: number;
  } {
    const correctScores = this.state.puzzleScores.filter(s => s.basePoints > 0);
    const skippedScores = this.state.puzzleScores.filter(s => s.skipPenalty < 0);

    const totalTimeBonus = correctScores.reduce((sum, s) => sum + s.timeBonus, 0);
    const averageTimeBonus = correctScores.length > 0
      ? totalTimeBonus / correctScores.length
      : 0;

    return {
      totalScore: this.state.totalScore,
      puzzlesSolved: correctScores.length,
      puzzlesSkipped: skippedScores.length,
      longestStreak: this.state.longestStreak,
      isPerfect: this.state.isPerfect && correctScores.length > 0,
      averageTimeBonus: Math.round(averageTimeBonus),
    };
  }

  /**
   * Reset scoring state.
   */
  reset(): void {
    this.state = createScoringState();
  }
}

/**
 * Create a scoring system.
 */
export function createRushScoring(config?: ScoringConfig): RushScoring {
  return new RushScoring(config);
}

/**
 * Calculate rank based on score.
 */
export function calculateRank(score: number): {
  rank: string;
  title: string;
  minScore: number;
  nextRank: string | null;
  nextRankScore: number | null;
} {
  const ranks = [
    { rank: 'S', title: 'Master', minScore: 2000 },
    { rank: 'A', title: 'Expert', minScore: 1500 },
    { rank: 'B', title: 'Advanced', minScore: 1000 },
    { rank: 'C', title: 'Intermediate', minScore: 500 },
    { rank: 'D', title: 'Beginner', minScore: 200 },
    { rank: 'F', title: 'Novice', minScore: 0 },
  ];

  for (let i = 0; i < ranks.length; i++) {
    const currentRank = ranks[i];
    if (currentRank && score >= currentRank.minScore) {
      const nextRankData = i > 0 ? ranks[i - 1] : null;
      return {
        rank: currentRank.rank,
        title: currentRank.title,
        minScore: currentRank.minScore,
        nextRank: nextRankData?.rank ?? null,
        nextRankScore: nextRankData?.minScore ?? null,
      };
    }
  }

  // Default to lowest rank
  return {
    rank: 'F',
    title: 'Novice',
    minScore: 0,
    nextRank: 'D',
    nextRankScore: 200,
  };
}
