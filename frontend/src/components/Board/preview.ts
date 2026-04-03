/**
 * Board preview - hover stone hover effect
 * @module components/Board/preview
 *
 * Covers: FR-006 (Hover preview for desktop, disabled on touch devices)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Preview logic separate from rendering
 * - IX. Accessibility: Touch devices get direct placement without preview
 */

import type { Coordinate, BoardSize, ReadonlyBoardState } from '../../types';
import { isTouchDevice, isWithinBounds, isOccupied } from './interaction';

/**
 * Hover stone state for preview display
 */
export interface HoverStone {
  /** Coordinate to show hover stone */
  coord: Coordinate;
  /** Color of the hover stone */
  color: 'black' | 'white';
  /** Whether this move would be self-atari */
  isSelfAtari?: boolean;
}

/**
 * Preview configuration
 */
export interface PreviewConfig {
  /** Board size */
  boardSize: BoardSize;
  /** Current board state */
  stones: ReadonlyBoardState;
  /** Current player color */
  currentColor: 'black' | 'white';
  /** Whether preview is enabled */
  enabled: boolean;
}

/**
 * Create a preview manager for handling hover stone state
 */
export interface PreviewManager {
  /** Update preview position */
  update: (coord: Coordinate | null) => HoverStone | null;
  /** Clear preview */
  clear: () => void;
  /** Check if preview is enabled */
  isEnabled: () => boolean;
}

/**
 * Check if preview should be enabled based on device type
 * Per FR-006: Disable on touch devices
 */
export function shouldEnablePreview(): boolean {
  return !isTouchDevice();
}

/**
 * Calculate hover stone from hover position
 *
 * @param coord - Hover coordinate (or null if not hovering)
 * @param config - Preview configuration
 * @returns Hover stone or null if no preview should be shown
 */
export function calculateHoverStone(
  coord: Coordinate | null,
  config: PreviewConfig
): HoverStone | null {
  // No coord means not hovering
  if (!coord) {
    return null;
  }

  // Preview disabled
  if (!config.enabled) {
    return null;
  }

  // Check if position is valid
  if (!isWithinBounds(coord, config.boardSize)) {
    return null;
  }

  // Don't show preview on occupied positions
  if (isOccupied(coord, config.stones)) {
    return null;
  }

  return {
    coord,
    color: config.currentColor,
  };
}

/**
 * Create a preview manager
 *
 * @param initialConfig - Initial configuration
 * @returns Preview manager instance
 */
export function createPreviewManager(
  initialConfig: PreviewConfig
): PreviewManager {
  const config = { ...initialConfig };
  let currentHover: HoverStone | null = null;

  return {
    update(coord: Coordinate | null): HoverStone | null {
      currentHover = calculateHoverStone(coord, config);
      return currentHover;
    },

    clear(): void {
      currentHover = null;
    },

    isEnabled(): boolean {
      return config.enabled && shouldEnablePreview();
    },
  };
}

/**
 * Hook-friendly state for hover stone preview
 */
export interface PreviewState {
  /** Current hover stone (if any) */
  hoverStone: HoverStone | null;
  /** Whether preview is active */
  isActive: boolean;
}

/**
 * Calculate preview state from hover and configuration
 *
 * @param hoverCoord - Current hover coordinate
 * @param boardSize - Board size
 * @param stones - Board state
 * @param currentColor - Current player color
 * @returns Preview state
 */
export function getPreviewState(
  hoverCoord: Coordinate | null,
  boardSize: BoardSize,
  stones: ReadonlyBoardState,
  currentColor: 'black' | 'white'
): PreviewState {
  const enabled = shouldEnablePreview();

  if (!enabled || !hoverCoord) {
    return {
      hoverStone: null,
      isActive: false,
    };
  }

  const hoverStone = calculateHoverStone(hoverCoord, {
    boardSize,
    stones,
    currentColor,
    enabled,
  });

  return {
    hoverStone,
    isActive: hoverStone !== null,
  };
}

/**
 * Debounce helper for smooth preview updates
 *
 * @param fn - Function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 */
export function debouncePreview<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number = 16 // ~1 frame at 60fps
): T {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return ((...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, delay);
  }) as T;
}

/**
 * Throttle helper for preview updates (better for mouse move)
 *
 * @param fn - Function to throttle
 * @param limit - Minimum time between calls in ms
 * @returns Throttled function
 */
export function throttlePreview<T extends (...args: unknown[]) => void>(
  fn: T,
  limit: number = 16
): T {
  let inThrottle = false;
  let lastArgs: Parameters<T> | null = null;

  return ((...args: Parameters<T>) => {
    if (inThrottle) {
      lastArgs = args;
      return;
    }

    fn(...args);
    inThrottle = true;

    setTimeout(() => {
      inThrottle = false;
      if (lastArgs) {
        fn(...lastArgs);
        lastArgs = null;
      }
    }, limit);
  }) as T;
}
