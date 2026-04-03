/**
 * Time tracking for puzzle solving sessions.
 * @module lib/progress/timing
 */

/**
 * Timer state for a puzzle solving session.
 */
export interface TimerState {
  /** Puzzle ID being timed */
  readonly puzzleId: string;
  /** Start timestamp (performance.now()) */
  readonly startTime: number;
  /** Total elapsed time in milliseconds (if paused) */
  readonly elapsedMs: number;
  /** Whether the timer is currently running */
  readonly isRunning: boolean;
  /** Pause history for tracking interruptions */
  readonly pauseTimes: readonly number[];
}

/**
 * Create a new timer for a puzzle.
 *
 * @param puzzleId - Puzzle ID being solved
 * @returns Initial timer state
 */
export function createTimer(puzzleId: string): TimerState {
  return {
    puzzleId,
    startTime: performance.now(),
    elapsedMs: 0,
    isRunning: true,
    pauseTimes: [],
  };
}

/**
 * Pause the timer.
 *
 * @param timer - Current timer state
 * @returns Updated timer state
 */
export function pauseTimer(timer: TimerState): TimerState {
  if (!timer.isRunning) {
    return timer;
  }

  const now = performance.now();
  const sessionTime = now - timer.startTime;

  return {
    ...timer,
    elapsedMs: timer.elapsedMs + sessionTime,
    isRunning: false,
    pauseTimes: [...timer.pauseTimes, now],
  };
}

/**
 * Resume the timer.
 *
 * @param timer - Current timer state
 * @returns Updated timer state
 */
export function resumeTimer(timer: TimerState): TimerState {
  if (timer.isRunning) {
    return timer;
  }

  return {
    ...timer,
    startTime: performance.now(),
    isRunning: true,
  };
}

/**
 * Stop the timer and get final elapsed time.
 *
 * @param timer - Current timer state
 * @returns Final elapsed time in milliseconds
 */
export function stopTimer(timer: TimerState): number {
  if (!timer.isRunning) {
    return timer.elapsedMs;
  }

  const now = performance.now();
  const sessionTime = now - timer.startTime;
  return Math.round(timer.elapsedMs + sessionTime);
}

/**
 * Get current elapsed time without stopping.
 *
 * @param timer - Current timer state
 * @returns Current elapsed time in milliseconds
 */
export function getElapsedTime(timer: TimerState): number {
  if (!timer.isRunning) {
    return timer.elapsedMs;
  }

  const now = performance.now();
  const sessionTime = now - timer.startTime;
  return Math.round(timer.elapsedMs + sessionTime);
}

/**
 * Reset the timer to zero.
 *
 * @param timer - Current timer state
 * @returns Reset timer state
 */
export function resetTimer(timer: TimerState): TimerState {
  return {
    ...timer,
    startTime: performance.now(),
    elapsedMs: 0,
    isRunning: true,
    pauseTimes: [],
  };
}

/**
 * PuzzleTimer class for stateful time tracking.
 * Provides an object-oriented interface to timer functions.
 */
export class PuzzleTimer {
  private state: TimerState;
  private callbacks: Set<(elapsed: number) => void>;
  private intervalId: ReturnType<typeof setInterval> | null;

  constructor(puzzleId: string, autoStart: boolean = true) {
    this.state = {
      puzzleId,
      startTime: autoStart ? performance.now() : 0,
      elapsedMs: 0,
      isRunning: autoStart,
      pauseTimes: [],
    };
    this.callbacks = new Set();
    this.intervalId = null;
  }

  /**
   * Start the timer.
   */
  start(): void {
    if (this.state.isRunning) return;

    this.state = {
      ...this.state,
      startTime: performance.now(),
      isRunning: true,
    };
  }

  /**
   * Pause the timer.
   */
  pause(): void {
    this.state = pauseTimer(this.state);
  }

  /**
   * Resume the timer.
   */
  resume(): void {
    this.state = resumeTimer(this.state);
  }

  /**
   * Stop the timer and return final time.
   */
  stop(): number {
    this.stopTicking();
    const elapsed = stopTimer(this.state);
    this.state = {
      ...this.state,
      isRunning: false,
      elapsedMs: elapsed,
    };
    return elapsed;
  }

  /**
   * Reset the timer.
   */
  reset(): void {
    this.state = resetTimer(this.state);
  }

  /**
   * Get current elapsed time.
   */
  getElapsed(): number {
    return getElapsedTime(this.state);
  }

  /**
   * Check if timer is running.
   */
  isRunning(): boolean {
    return this.state.isRunning;
  }

  /**
   * Subscribe to elapsed time updates.
   *
   * @param callback - Function called with elapsed time
   * @param intervalMs - Update interval in milliseconds
   * @returns Unsubscribe function
   */
  onTick(callback: (elapsed: number) => void, intervalMs: number = 1000): () => void {
    this.callbacks.add(callback);

    // Start interval if not already running
    if (!this.intervalId && this.state.isRunning) {
      this.intervalId = setInterval(() => {
        const elapsed = this.getElapsed();
        for (const cb of this.callbacks) {
          cb(elapsed);
        }
      }, intervalMs);
    }

    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback);
      if (this.callbacks.size === 0) {
        this.stopTicking();
      }
    };
  }

  /**
   * Stop the tick interval.
   */
  private stopTicking(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  /**
   * Clean up resources.
   */
  dispose(): void {
    this.stopTicking();
    this.callbacks.clear();
  }
}

/**
 * Format elapsed time for display.
 *
 * @param ms - Time in milliseconds
 * @returns Formatted string (e.g., "1:23", "45:30")
 */
export function formatElapsedTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Format elapsed time with milliseconds for precision display.
 *
 * @param ms - Time in milliseconds
 * @returns Formatted string (e.g., "1:23.456")
 */
export function formatElapsedTimePrecise(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const millis = ms % 1000;

  return `${minutes}:${seconds.toString().padStart(2, '0')}.${millis.toString().padStart(3, '0')}`;
}

/**
 * Parse time string back to milliseconds.
 *
 * @param timeStr - Time string (e.g., "1:23")
 * @returns Time in milliseconds
 */
export function parseTimeString(timeStr: string): number {
  const parts = timeStr.split(':');
  if (parts.length !== 2) return 0;

  const minutesPart = parts[0] ?? '0';
  const secondsAndMillis = parts[1] ?? '0';
  
  const minutes = parseInt(minutesPart, 10) || 0;
  const secondsPart = secondsAndMillis.split('.');
  const seconds = parseInt(secondsPart[0] ?? '0', 10) || 0;
  const millis = secondsPart.length > 1 ? parseInt(secondsPart[1] ?? '0', 10) || 0 : 0;

  return minutes * 60 * 1000 + seconds * 1000 + millis;
}
