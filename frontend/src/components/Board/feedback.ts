// @ts-nocheck
/**
 * Board feedback - visual feedback for correct/incorrect moves
 * @module components/Board/feedback
 *
 * Covers: FR-013 (Correct move feedback), FR-014 (Incorrect move feedback)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Feedback logic separate from rendering
 * - IX. Accessibility: Visual + animation feedback (no audio dependency)
 */

import type { Coordinate } from '../../types';

/**
 * Feedback type
 */
export type FeedbackType = 'correct' | 'incorrect' | 'capture' | 'complete';

/**
 * Feedback state for a coordinate
 */
export interface FeedbackState {
  /** Type of feedback */
  type: FeedbackType;
  /** Coordinate affected */
  coord: Coordinate;
  /** Timestamp when feedback started */
  startTime: number;
  /** Duration of feedback in ms */
  duration: number;
  /** Whether feedback is active */
  active: boolean;
}

/**
 * Animation configuration
 */
export interface AnimationConfig {
  /** Correct move animation duration */
  correctDuration: number;
  /** Incorrect move shake duration */
  incorrectDuration: number;
  /** Capture fade duration */
  captureDuration: number;
  /** Completion celebration duration */
  completeDuration: number;
}

/** Default animation configuration */
export const DEFAULT_ANIMATION_CONFIG: AnimationConfig = {
  correctDuration: 300,
  incorrectDuration: 400,
  captureDuration: 250,
  completeDuration: 1000,
};

/**
 * Feedback manager for tracking active feedback states
 */
export interface FeedbackManager {
  /** Add feedback for a coordinate */
  add: (type: FeedbackType, coord: Coordinate) => void;
  /** Remove feedback for a coordinate */
  remove: (coord: Coordinate) => void;
  /** Clear all feedback */
  clear: () => void;
  /** Get active feedback */
  getActive: () => readonly FeedbackState[];
  /** Check if feedback is active for coordinate */
  isActive: (coord: Coordinate) => boolean;
  /** Update (remove expired feedback) */
  update: () => void;
}

/**
 * Create a feedback manager
 *
 * @param config - Animation configuration
 * @returns Feedback manager
 */
export function createFeedbackManager(
  config: AnimationConfig = DEFAULT_ANIMATION_CONFIG
): FeedbackManager {
  const feedbackStates: Map<string, FeedbackState> = new Map();

  const coordKey = (coord: Coordinate) => `${coord.x},${coord.y}`;

  const getDuration = (type: FeedbackType): number => {
    switch (type) {
      case 'correct':
        return config.correctDuration;
      case 'incorrect':
        return config.incorrectDuration;
      case 'capture':
        return config.captureDuration;
      case 'complete':
        return config.completeDuration;
    }
  };

  return {
    add(type: FeedbackType, coord: Coordinate): void {
      const key = coordKey(coord);
      feedbackStates.set(key, {
        type,
        coord,
        startTime: Date.now(),
        duration: getDuration(type),
        active: true,
      });
    },

    remove(coord: Coordinate): void {
      const key = coordKey(coord);
      feedbackStates.delete(key);
    },

    clear(): void {
      feedbackStates.clear();
    },

    getActive(): readonly FeedbackState[] {
      return Array.from(feedbackStates.values()).filter((s) => s.active);
    },

    isActive(coord: Coordinate): boolean {
      const key = coordKey(coord);
      const state = feedbackStates.get(key);
      return state?.active ?? false;
    },

    update(): void {
      const now = Date.now();
      for (const [key, state] of feedbackStates.entries()) {
        if (now - state.startTime >= state.duration) {
          feedbackStates.delete(key);
        }
      }
    },
  };
}

/**
 * Draw correct move feedback on canvas
 *
 * @param ctx - Canvas context
 * @param coord - Coordinate
 * @param progress - Animation progress (0-1)
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawCorrectFeedback(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  progress: number,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  const x = offsetX + coord.x * cellSize;
  const y = offsetY + coord.y * cellSize;
  const radius = cellSize * 0.5 * progress;

  // Expanding ring effect
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.strokeStyle = `rgba(76, 175, 80, ${1 - progress})`; // Green, fading out
  ctx.lineWidth = 3;
  ctx.stroke();
}

/**
 * Draw incorrect move feedback (shake effect setup)
 *
 * @param coord - Coordinate
 * @param progress - Animation progress (0-1)
 * @returns Offset for shake effect
 */
export function calculateShakeOffset(
  progress: number
): { x: number; y: number } {
  // Shake animation: oscillates with decreasing amplitude
  const amplitude = 5 * (1 - progress);
  const frequency = 30;
  const offset = Math.sin(progress * frequency) * amplitude;

  return { x: offset, y: 0 };
}

/**
 * Draw incorrect move feedback on canvas
 *
 * @param ctx - Canvas context
 * @param coord - Coordinate
 * @param progress - Animation progress (0-1)
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawIncorrectFeedback(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  progress: number,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  const shakeOffset = calculateShakeOffset(progress);
  const x = offsetX + coord.x * cellSize + shakeOffset.x;
  const y = offsetY + coord.y * cellSize + shakeOffset.y;
  const radius = cellSize * 0.45;

  // Red flash effect
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(244, 67, 54, ${0.3 * (1 - progress)})`; // Red, fading
  ctx.fill();

  // X mark
  if (progress < 0.5) {
    const alpha = 1 - progress * 2;
    const markSize = cellSize * 0.25;
    ctx.strokeStyle = `rgba(244, 67, 54, ${alpha})`;
    ctx.lineWidth = 3;
    ctx.lineCap = 'round';

    ctx.beginPath();
    ctx.moveTo(x - markSize, y - markSize);
    ctx.lineTo(x + markSize, y + markSize);
    ctx.moveTo(x + markSize, y - markSize);
    ctx.lineTo(x - markSize, y + markSize);
    ctx.stroke();
  }
}

/**
 * Draw all active feedback on canvas
 *
 * @param ctx - Canvas context
 * @param feedbackManager - Feedback manager
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawFeedback(
  ctx: CanvasRenderingContext2D,
  feedbackManager: FeedbackManager,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  feedbackManager.update();

  for (const state of feedbackManager.getActive()) {
    const elapsed = Date.now() - state.startTime;
    const progress = Math.min(elapsed / state.duration, 1);

    switch (state.type) {
      case 'correct':
        drawCorrectFeedback(ctx, state.coord, progress, cellSize, offsetX, offsetY);
        break;
      case 'incorrect':
        drawIncorrectFeedback(ctx, state.coord, progress, cellSize, offsetX, offsetY);
        break;
      // capture and complete handled by animations.ts
    }
  }
}

/**
 * CSS class names for feedback states (for React/Preact components)
 */
export const FEEDBACK_CLASSES = {
  correct: 'feedback-correct',
  incorrect: 'feedback-incorrect',
  capture: 'feedback-capture',
  complete: 'feedback-complete',
} as const;

/**
 * Get CSS animation for feedback type
 */
export function getFeedbackAnimation(type: FeedbackType): string {
  switch (type) {
    case 'correct':
      return 'feedback-pulse 0.3s ease-out';
    case 'incorrect':
      return 'feedback-shake 0.4s ease-out';
    case 'capture':
      return 'feedback-fade 0.25s ease-out';
    case 'complete':
      return 'feedback-celebrate 1s ease-out';
  }
}

/**
 * CSS keyframes for feedback animations
 */
export const FEEDBACK_KEYFRAMES = `
@keyframes feedback-pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0.7);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 0 10px rgba(76, 175, 80, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
  }
}

@keyframes feedback-shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}

@keyframes feedback-fade {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  100% {
    opacity: 0;
    transform: scale(0.5);
  }
}

@keyframes feedback-celebrate {
  0% {
    transform: scale(1);
  }
  25% {
    transform: scale(1.2);
  }
  50% {
    transform: scale(1);
  }
  75% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}
`;

/**
 * Haptic feedback helper (if available)
 */
export function triggerHapticFeedback(type: FeedbackType): void {
  if ('vibrate' in navigator) {
    switch (type) {
      case 'correct':
        navigator.vibrate(50); // Short tap
        break;
      case 'incorrect':
        navigator.vibrate([50, 50, 50]); // Three short taps
        break;
      case 'capture':
        navigator.vibrate([30, 30]); // Two quick taps
        break;
      case 'complete':
        navigator.vibrate([50, 50, 100]); // Pattern
        break;
    }
  }
}

// ============================================================================
// Wrong Move Feedback (FR-038 to FR-042a)
// ============================================================================

/**
 * Configuration for wrong move visual feedback.
 * Per FR-042a: Red circle only for 1.5s - NO shake/flash/glow.
 */
export interface WrongMoveFeedbackConfig {
  /** Duration to show overlay in milliseconds */
  displayDuration: number;
  /** Whether to play sound effect */
  playSound: boolean;
  /** Opacity of the red circle overlay (0-1) */
  overlayOpacity: number;
  /** Border width of the red circle */
  borderWidth: number;
  /** Border color (CSS color value) */
  borderColor: string;
}

/**
 * Default wrong move feedback configuration per FR-042a:
 * - Red circle only for 1.5s
 * - NO shake/flash/glow effects
 */
export const DEFAULT_WRONG_MOVE_CONFIG: WrongMoveFeedbackConfig = {
  displayDuration: 1500, // 1.5 seconds
  playSound: true,
  overlayOpacity: 0.7,
  borderWidth: 3,
  borderColor: '#DC2626', // Red-600
};

/**
 * Draw wrong move indicator on canvas.
 * Renders a simple red circle outline - NO animations per FR-042a.
 * 
 * @param ctx - Canvas 2D context
 * @param coord - Board position of wrong move
 * @param cellSize - Size of each board cell
 * @param offsetX - Board offset X
 * @param offsetY - Board offset Y
 * @param config - Feedback configuration
 */
export function drawWrongMoveIndicator(
  ctx: CanvasRenderingContext2D,
  coord: Coordinate,
  cellSize: number,
  offsetX: number,
  offsetY: number,
  config: WrongMoveFeedbackConfig = DEFAULT_WRONG_MOVE_CONFIG
): void {
  const centerX = offsetX + coord.x * cellSize;
  const centerY = offsetY + coord.y * cellSize;
  const radius = cellSize * 0.45; // Slightly smaller than stone

  ctx.save();
  ctx.globalAlpha = config.overlayOpacity;

  // Draw red circle outline
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.strokeStyle = config.borderColor;
  ctx.lineWidth = config.borderWidth;
  ctx.stroke();

  // Add semi-transparent fill for visibility
  ctx.fillStyle = `${config.borderColor}20`; // 20 = 12.5% opacity
  ctx.fill();

  ctx.restore();
}

/**
 * Calculate CSS styles for an overlay wrong move indicator element.
 * Used for DOM-based indicators outside canvas.
 * 
 * @param coord - Board position
 * @param cellSize - Size of each board cell
 * @param offsetX - Board offset X
 * @param offsetY - Board offset Y
 * @param config - Feedback configuration
 * @returns CSS styles object
 */
export function getWrongMoveIndicatorStyle(
  coord: Coordinate,
  cellSize: number,
  offsetX: number,
  offsetY: number,
  config: WrongMoveFeedbackConfig = DEFAULT_WRONG_MOVE_CONFIG
): Record<string, string> {
  const size = cellSize * 0.9;
  const centerX = offsetX + coord.x * cellSize;
  const centerY = offsetY + coord.y * cellSize;

  return {
    position: 'absolute',
    width: `${size}px`,
    height: `${size}px`,
    left: `${centerX}px`,
    top: `${centerY}px`,
    transform: 'translate(-50%, -50%)',
    borderRadius: '50%',
    border: `${config.borderWidth}px solid ${config.borderColor}`,
    backgroundColor: `${config.borderColor}20`,
    opacity: String(config.overlayOpacity),
    pointerEvents: 'none',
    zIndex: '100',
    // Per FR-042a: NO shake, flash, or glow - just red circle
  };
}
