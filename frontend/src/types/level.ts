/**
 * Level (Daily Challenge) type definitions
 * Matching: specs/001-core-platform/contracts/level.schema.json
 * @module types/level
 */

/**
 * Puzzle IDs grouped by skill level (10-30 per level)
 */
export interface LevelPuzzles {
  /** Skill Level 1: Elementary (30k-15k) */
  readonly level1: readonly string[];
  /** Skill Level 2: SDK (14k-8k) */
  readonly level2: readonly string[];
  /** Skill Level 3: Advanced SDK (7k-1k) */
  readonly level3: readonly string[];
  /** Skill Level 4: Dan (1d-4d) */
  readonly level4: readonly string[];
  /** Skill Level 5: Expert (5d+) */
  readonly level5: readonly string[];
}

/**
 * A Daily Challenge (collection of puzzles for one day)
 */
export interface Level {
  /** Schema version */
  readonly version: string;
  /** Date identifier (YYYY-MM-DD) - unique */
  readonly date: string;
  /** Display name (e.g., 'Day 42: Corner Battles') */
  readonly name: string;
  /** Puzzles organized by skill level */
  readonly puzzles: LevelPuzzles;
  /** Optional daily theme */
  readonly theme?: string;
}

/**
 * Level metadata for list display (without full puzzle data)
 */
export interface LevelSummary {
  /** Date identifier */
  readonly date: string;
  /** Display name */
  readonly name: string;
  /** Total puzzle count across all skill levels */
  readonly totalPuzzles: number;
  /** Puzzles per skill level */
  readonly puzzlesByLevel: {
    readonly level1: number;
    readonly level2: number;
    readonly level3: number;
    readonly level4: number;
    readonly level5: number;
  };
  /** Optional theme */
  readonly theme?: string;
  /** Whether this level is unlocked for the user */
  readonly isUnlocked?: boolean;
  /** Whether this level is completed */
  readonly isCompleted?: boolean;
}

/**
 * Calculate total puzzle count in a level
 */
export function getLevelPuzzleCount(puzzles: LevelPuzzles): number {
  return (
    puzzles.level1.length +
    puzzles.level2.length +
    puzzles.level3.length +
    puzzles.level4.length +
    puzzles.level5.length
  );
}

/**
 * Get puzzle IDs for a specific skill level
 */
export function getPuzzlesBySkillLevel(
  puzzles: LevelPuzzles,
  level: 1 | 2 | 3 | 4 | 5
): readonly string[] {
  const key = `level${level}` as keyof LevelPuzzles;
  return puzzles[key];
}

/**
 * Create level summary from full level data
 */
export function createLevelSummary(level: Level): Omit<LevelSummary, 'isUnlocked' | 'isCompleted'> {
  const result: Omit<LevelSummary, 'isUnlocked' | 'isCompleted'> = {
    date: level.date,
    name: level.name,
    totalPuzzles: getLevelPuzzleCount(level.puzzles),
    puzzlesByLevel: {
      level1: level.puzzles.level1.length,
      level2: level.puzzles.level2.length,
      level3: level.puzzles.level3.length,
      level4: level.puzzles.level4.length,
      level5: level.puzzles.level5.length,
    },
  };
  if (level.theme !== undefined) {
    return { ...result, theme: level.theme };
  }
  return result;
}
