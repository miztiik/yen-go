/**
 * Rush mode visibility handling.
 * Pauses timer when tab is hidden, handles resume/forfeit.
 * @module lib/rush/visibility
 */

/**
 * Visibility state.
 */
export interface VisibilityState {
  /** Whether the page is currently visible */
  readonly isVisible: boolean;
  /** When the page became hidden (null if visible) */
  readonly hiddenAt: number | null;
  /** Total hidden duration in milliseconds */
  readonly totalHiddenDuration: number;
  /** Whether auto-forfeit threshold has been exceeded */
  readonly shouldForfeit: boolean;
}

/**
 * Visibility handler configuration.
 */
export interface VisibilityConfig {
  /** Auto-forfeit threshold in milliseconds (default: 5 minutes) */
  readonly forfeitThreshold?: number;
  /** Callback when page becomes hidden */
  readonly onHidden?: () => void;
  /** Callback when page becomes visible */
  readonly onVisible?: (hiddenDuration: number) => void;
  /** Callback when forfeit threshold is exceeded */
  readonly onForfeit?: () => void;
}

/**
 * Default forfeit threshold (5 minutes).
 */
export const DEFAULT_FORFEIT_THRESHOLD = 5 * 60 * 1000;

/**
 * Create initial visibility state.
 */
export function createVisibilityState(): VisibilityState {
  return {
    isVisible: !document.hidden,
    hiddenAt: document.hidden ? Date.now() : null,
    totalHiddenDuration: 0,
    shouldForfeit: false,
  };
}

/**
 * Visibility handler for rush mode.
 * Tracks page visibility and handles pause/resume/forfeit logic.
 */
export class VisibilityHandler {
  private state: VisibilityState;
  private config: VisibilityConfig;
  private boundHandler: () => void;
  private forfeitCheckInterval: number | null = null;

  constructor(config: VisibilityConfig = {}) {
    this.config = {
      forfeitThreshold: DEFAULT_FORFEIT_THRESHOLD,
      ...config,
    };
    this.state = createVisibilityState();
    this.boundHandler = this.handleVisibilityChange.bind(this);
  }

  /**
   * Get current visibility state.
   */
  getState(): VisibilityState {
    return this.state;
  }

  /**
   * Start listening for visibility changes.
   */
  start(): void {
    document.addEventListener('visibilitychange', this.boundHandler);

    // Check current state
    if (document.hidden) {
      this.handleHidden();
    }
  }

  /**
   * Stop listening for visibility changes.
   */
  stop(): void {
    document.removeEventListener('visibilitychange', this.boundHandler);
    this.stopForfeitCheck();
  }

  /**
   * Reset state.
   */
  reset(): void {
    this.stopForfeitCheck();
    this.state = createVisibilityState();
  }

  /**
   * Check if the page is currently visible.
   */
  isVisible(): boolean {
    return this.state.isVisible;
  }

  /**
   * Get total time the page has been hidden.
   */
  getTotalHiddenDuration(): number {
    let total = this.state.totalHiddenDuration;
    if (this.state.hiddenAt) {
      total += Date.now() - this.state.hiddenAt;
    }
    return total;
  }

  /**
   * Manually trigger resume (for modal confirmation).
   */
  confirmResume(): void {
    this.handleVisible();
  }

  /**
   * Manually trigger forfeit (for modal confirmation).
   */
  confirmForfeit(): void {
    this.state = {
      ...this.state,
      shouldForfeit: true,
    };
    this.config.onForfeit?.();
  }

  private handleVisibilityChange(): void {
    if (document.hidden) {
      this.handleHidden();
    } else {
      this.handleVisible();
    }
  }

  private handleHidden(): void {
    if (!this.state.isVisible) return;

    this.state = {
      ...this.state,
      isVisible: false,
      hiddenAt: Date.now(),
    };

    this.config.onHidden?.();
    this.startForfeitCheck();
  }

  private handleVisible(): void {
    if (this.state.isVisible) return;

    const hiddenDuration = this.state.hiddenAt
      ? Date.now() - this.state.hiddenAt
      : 0;

    const shouldForfeit = hiddenDuration >= (this.config.forfeitThreshold || DEFAULT_FORFEIT_THRESHOLD);

    this.state = {
      ...this.state,
      isVisible: true,
      hiddenAt: null,
      totalHiddenDuration: this.state.totalHiddenDuration + hiddenDuration,
      shouldForfeit,
    };

    this.stopForfeitCheck();

    if (shouldForfeit) {
      this.config.onForfeit?.();
    } else {
      this.config.onVisible?.(hiddenDuration);
    }
  }

  private startForfeitCheck(): void {
    if (this.forfeitCheckInterval) return;

    // Check every 10 seconds while hidden
    this.forfeitCheckInterval = window.setInterval(() => {
      if (this.state.hiddenAt) {
        const hiddenDuration = Date.now() - this.state.hiddenAt;
        if (hiddenDuration >= (this.config.forfeitThreshold || DEFAULT_FORFEIT_THRESHOLD)) {
          this.state = {
            ...this.state,
            shouldForfeit: true,
          };
          this.stopForfeitCheck();
          // Note: onForfeit will be called when page becomes visible
        }
      }
    }, 10000);
  }

  private stopForfeitCheck(): void {
    if (this.forfeitCheckInterval) {
      clearInterval(this.forfeitCheckInterval);
      this.forfeitCheckInterval = null;
    }
  }
}

/**
 * Create a visibility handler.
 */
export function createVisibilityHandler(config?: VisibilityConfig): VisibilityHandler {
  return new VisibilityHandler(config);
}

/**
 * Hook-style visibility state (for use with useState).
 */
export function getVisibilityInfo(): { isVisible: boolean; hiddenSince: number | null } {
  return {
    isVisible: !document.hidden,
    hiddenSince: document.hidden ? Date.now() : null,
  };
}
