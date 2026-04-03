/**
 * Rush mode skip functionality with penalty.
 * @module lib/rush/skip
 */

/**
 * Skip result with penalty info.
 */
export interface SkipResult {
  /** Whether skip was allowed */
  readonly allowed: boolean;
  /** Points deducted as penalty */
  readonly penaltyPoints: number;
  /** Remaining skips (if limited) */
  readonly skipsRemaining: number | null;
  /** Reason if skip was not allowed */
  readonly reason?: string;
}

/**
 * Skip configuration.
 */
export interface SkipConfig {
  /** Maximum skips allowed (null = unlimited) */
  readonly maxSkips?: number | null;
  /** Penalty points per skip (default: 10) */
  readonly penaltyPoints?: number;
  /** Allow skip on first puzzle */
  readonly allowFirstPuzzleSkip?: boolean;
  /** Cooldown between skips in ms (default: 0) */
  readonly skipCooldownMs?: number;
}

/**
 * Skip state.
 */
export interface SkipState {
  /** Total skips used */
  readonly skipsUsed: number;
  /** Maximum skips allowed (null = unlimited) */
  readonly maxSkips: number | null;
  /** Last skip timestamp */
  readonly lastSkipTime: number | null;
  /** Total penalty points from skips */
  readonly totalPenalty: number;
}

/**
 * Default skip configuration.
 */
export const DEFAULT_SKIP_CONFIG: Required<SkipConfig> = {
  maxSkips: null, // Unlimited
  penaltyPoints: 10,
  allowFirstPuzzleSkip: true,
  skipCooldownMs: 0,
};

/**
 * Create initial skip state.
 */
export function createSkipState(maxSkips: number | null = null): SkipState {
  return {
    skipsUsed: 0,
    maxSkips,
    lastSkipTime: null,
    totalPenalty: 0,
  };
}

/**
 * Skip manager for rush mode.
 */
export class SkipManager {
  private state: SkipState;
  private config: Required<SkipConfig>;

  constructor(config: SkipConfig = {}) {
    this.config = { ...DEFAULT_SKIP_CONFIG, ...config };
    this.state = createSkipState(this.config.maxSkips);
  }

  /**
   * Get current skip state.
   */
  getState(): SkipState {
    return this.state;
  }

  /**
   * Get number of skips used.
   */
  getSkipsUsed(): number {
    return this.state.skipsUsed;
  }

  /**
   * Get remaining skips (null if unlimited).
   */
  getSkipsRemaining(): number | null {
    if (this.state.maxSkips === null) {
      return null;
    }
    return Math.max(0, this.state.maxSkips - this.state.skipsUsed);
  }

  /**
   * Check if skip is currently available.
   */
  canSkip(isFirstPuzzle: boolean = false): boolean {
    // Check first puzzle restriction
    if (isFirstPuzzle && !this.config.allowFirstPuzzleSkip) {
      return false;
    }

    // Check max skips
    if (this.state.maxSkips !== null) {
      if (this.state.skipsUsed >= this.state.maxSkips) {
        return false;
      }
    }

    // Check cooldown
    if (this.config.skipCooldownMs > 0 && this.state.lastSkipTime) {
      const elapsed = Date.now() - this.state.lastSkipTime;
      if (elapsed < this.config.skipCooldownMs) {
        return false;
      }
    }

    return true;
  }

  /**
   * Get cooldown remaining (0 if no cooldown).
   */
  getCooldownRemaining(): number {
    if (this.config.skipCooldownMs <= 0 || !this.state.lastSkipTime) {
      return 0;
    }

    const elapsed = Date.now() - this.state.lastSkipTime;
    return Math.max(0, this.config.skipCooldownMs - elapsed);
  }

  /**
   * Attempt to skip current puzzle.
   */
  trySkip(isFirstPuzzle: boolean = false): SkipResult {
    // Check first puzzle restriction
    if (isFirstPuzzle && !this.config.allowFirstPuzzleSkip) {
      return {
        allowed: false,
        penaltyPoints: 0,
        skipsRemaining: this.getSkipsRemaining(),
        reason: 'Cannot skip the first puzzle',
      };
    }

    // Check max skips
    if (this.state.maxSkips !== null) {
      if (this.state.skipsUsed >= this.state.maxSkips) {
        return {
          allowed: false,
          penaltyPoints: 0,
          skipsRemaining: 0,
          reason: 'No skips remaining',
        };
      }
    }

    // Check cooldown
    const cooldownRemaining = this.getCooldownRemaining();
    if (cooldownRemaining > 0) {
      return {
        allowed: false,
        penaltyPoints: 0,
        skipsRemaining: this.getSkipsRemaining(),
        reason: `Please wait ${Math.ceil(cooldownRemaining / 1000)} seconds before skipping`,
      };
    }

    // Execute skip
    const penalty = this.config.penaltyPoints;

    this.state = {
      ...this.state,
      skipsUsed: this.state.skipsUsed + 1,
      lastSkipTime: Date.now(),
      totalPenalty: this.state.totalPenalty + penalty,
    };

    return {
      allowed: true,
      penaltyPoints: penalty,
      skipsRemaining: this.getSkipsRemaining(),
    };
  }

  /**
   * Get skip button text with status.
   */
  getSkipButtonText(): string {
    const remaining = this.getSkipsRemaining();

    if (remaining === null) {
      return `Skip (-${this.config.penaltyPoints}pts)`;
    }

    if (remaining === 0) {
      return 'No skips left';
    }

    return `Skip (${remaining} left, -${this.config.penaltyPoints}pts)`;
  }

  /**
   * Reset skip state.
   */
  reset(): void {
    this.state = createSkipState(this.config.maxSkips);
  }
}

/**
 * Create a skip manager.
 */
export function createSkipManager(config?: SkipConfig): SkipManager {
  return new SkipManager(config);
}

/**
 * Format skip penalty for display.
 */
export function formatSkipPenalty(points: number): string {
  return points > 0 ? `-${points}pts` : '0pts';
}

/**
 * Get skip status info.
 */
export function getSkipStatusInfo(
  skipsUsed: number,
  maxSkips: number | null
): {
  text: string;
  isLimited: boolean;
  percentUsed: number;
} {
  if (maxSkips === null) {
    return {
      text: `${skipsUsed} skips used`,
      isLimited: false,
      percentUsed: 0,
    };
  }

  const remaining = Math.max(0, maxSkips - skipsUsed);
  return {
    text: `${remaining}/${maxSkips} skips remaining`,
    isLimited: true,
    percentUsed: (skipsUsed / maxSkips) * 100,
  };
}
