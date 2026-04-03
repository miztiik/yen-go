/**
 * Rush mode timer with pause support.
 * @module lib/rush/timer
 */

/**
 * Timer state.
 */
export interface TimerState {
  /** Remaining time in milliseconds */
  readonly remaining: number;
  /** Whether timer is running */
  readonly isRunning: boolean;
  /** Whether timer is paused */
  readonly isPaused: boolean;
  /** Whether timer has expired */
  readonly isExpired: boolean;
  /** Start time (Date.now()) */
  readonly startTime: number | null;
  /** Pause time (Date.now()) */
  readonly pauseTime: number | null;
  /** Total paused duration */
  readonly pausedDuration: number;
}

/**
 * Timer configuration.
 */
export interface TimerConfig {
  /** Initial duration in milliseconds */
  readonly duration: number;
  /** Callback when timer expires */
  readonly onExpire?: () => void;
  /** Callback on each tick (every second) */
  readonly onTick?: (remaining: number) => void;
}

/**
 * Default timer durations in milliseconds.
 */
export const TIMER_DURATIONS = {
  short: 3 * 60 * 1000, // 3 minutes
  medium: 5 * 60 * 1000, // 5 minutes
  long: 10 * 60 * 1000, // 10 minutes
} as const;

export type TimerDuration = keyof typeof TIMER_DURATIONS;

/**
 * Create initial timer state.
 */
export function createTimerState(duration: number): TimerState {
  return {
    remaining: duration,
    isRunning: false,
    isPaused: false,
    isExpired: false,
    startTime: null,
    pauseTime: null,
    pausedDuration: 0,
  };
}

/**
 * Rush mode timer with pause/resume support.
 */
export class RushTimer {
  private state: TimerState;
  private config: TimerConfig;
  private tickInterval: number | null = null;
  private lastTickTime: number = 0;

  constructor(config: TimerConfig) {
    this.config = config;
    this.state = createTimerState(config.duration);
  }

  /**
   * Get current timer state.
   */
  getState(): TimerState {
    return this.state;
  }

  /**
   * Start the timer.
   */
  start(): void {
    if (this.state.isRunning || this.state.isExpired) return;

    this.state = {
      ...this.state,
      isRunning: true,
      isPaused: false,
      startTime: Date.now(),
    };

    this.lastTickTime = Date.now();
    this.startTicking();
  }

  /**
   * Pause the timer.
   */
  pause(): void {
    if (!this.state.isRunning || this.state.isPaused) return;

    this.stopTicking();

    this.state = {
      ...this.state,
      isPaused: true,
      pauseTime: Date.now(),
    };
  }

  /**
   * Resume the timer after pause.
   */
  resume(): void {
    if (!this.state.isPaused || !this.state.pauseTime) return;

    const pauseDuration = Date.now() - this.state.pauseTime;

    this.state = {
      ...this.state,
      isPaused: false,
      pauseTime: null,
      pausedDuration: this.state.pausedDuration + pauseDuration,
    };

    this.lastTickTime = Date.now();
    this.startTicking();
  }

  /**
   * Stop the timer (can't be resumed).
   */
  stop(): void {
    this.stopTicking();
    this.state = {
      ...this.state,
      isRunning: false,
      isPaused: false,
    };
  }

  /**
   * Reset the timer to initial state.
   */
  reset(): void {
    this.stopTicking();
    this.state = createTimerState(this.config.duration);
  }

  /**
   * Add bonus time.
   */
  addTime(ms: number): void {
    this.state = {
      ...this.state,
      remaining: this.state.remaining + ms,
    };
  }

  /**
   * Subtract time (for penalties).
   */
  subtractTime(ms: number): void {
    const newRemaining = Math.max(0, this.state.remaining - ms);
    this.state = {
      ...this.state,
      remaining: newRemaining,
    };

    if (newRemaining === 0) {
      this.expire();
    }
  }

  /**
   * Get remaining time in milliseconds.
   */
  getRemaining(): number {
    return this.state.remaining;
  }

  /**
   * Format remaining time as MM:SS.
   */
  formatRemaining(): string {
    const totalSeconds = Math.ceil(this.state.remaining / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }

  /**
   * Cleanup timer resources.
   */
  destroy(): void {
    this.stopTicking();
  }

  private startTicking(): void {
    if (this.tickInterval) return;

    this.tickInterval = window.setInterval(() => {
      this.tick();
    }, 100); // Update every 100ms for smooth countdown
  }

  private stopTicking(): void {
    if (this.tickInterval) {
      clearInterval(this.tickInterval);
      this.tickInterval = null;
    }
  }

  private tick(): void {
    if (!this.state.isRunning || this.state.isPaused) return;

    const now = Date.now();
    const elapsed = now - this.lastTickTime;
    this.lastTickTime = now;

    const newRemaining = Math.max(0, this.state.remaining - elapsed);

    this.state = {
      ...this.state,
      remaining: newRemaining,
    };

    // Call tick callback every second
    if (Math.floor(newRemaining / 1000) !== Math.floor((newRemaining + elapsed) / 1000)) {
      this.config.onTick?.(newRemaining);
    }

    if (newRemaining === 0) {
      this.expire();
    }
  }

  private expire(): void {
    this.stopTicking();
    this.state = {
      ...this.state,
      isRunning: false,
      isExpired: true,
      remaining: 0,
    };
    this.config.onExpire?.();
  }
}

/**
 * Create a rush timer with the given duration.
 */
export function createRushTimer(
  duration: number,
  onExpire?: () => void,
  onTick?: (remaining: number) => void
): RushTimer {
  return new RushTimer({
    duration,
    ...(onExpire !== undefined && { onExpire }),
    ...(onTick !== undefined && { onTick }),
  });
}

/**
 * Format milliseconds as MM:SS string.
 */
export function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Format milliseconds as detailed time string (for results).
 */
export function formatDetailedTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }
  return `${minutes}m ${seconds}s`;
}
