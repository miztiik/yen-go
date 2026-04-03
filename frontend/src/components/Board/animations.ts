/**
 * Board animations - capture animations and other visual effects
 * @module components/Board/animations
 *
 * Covers: FR-015 (Capture animation)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Animation logic separate from rendering
 */

import type { Coordinate } from '../../types';

/**
 * Animation state for a single stone
 */
export interface StoneAnimation {
  /** Coordinate of the stone */
  coord: Coordinate;
  /** Animation type */
  type: 'capture' | 'place' | 'remove' | 'highlight';
  /** Start time of animation */
  startTime: number;
  /** Duration in milliseconds */
  duration: number;
  /** Stone color (for capture/place) */
  color?: 'black' | 'white';
}

/**
 * Animation manager for tracking active animations
 */
export interface AnimationManager {
  /** Add a new animation */
  add: (animation: Omit<StoneAnimation, 'startTime'>) => void;
  /** Add multiple capture animations */
  addCaptures: (coords: readonly Coordinate[], color: 'black' | 'white') => void;
  /** Clear all animations */
  clear: () => void;
  /** Get all active animations */
  getActive: () => readonly StoneAnimation[];
  /** Check if any animation is active */
  isAnimating: () => boolean;
  /** Update animations (remove completed) */
  update: () => boolean; // Returns true if any animation active
}

/** Default capture animation duration */
const DEFAULT_CAPTURE_DURATION = 250;

/**
 * Create an animation manager
 *
 * @param onUpdate - Callback when animations change
 * @returns Animation manager
 */
export function createAnimationManager(
  onUpdate?: () => void
): AnimationManager {
  const animations: StoneAnimation[] = [];

  return {
    add(anim: Omit<StoneAnimation, 'startTime'>): void {
      animations.push({
        ...anim,
        startTime: Date.now(),
      });
      onUpdate?.();
    },

    addCaptures(coords: readonly Coordinate[], color: 'black' | 'white'): void {
      const now = Date.now();
      for (const coord of coords) {
        animations.push({
          coord,
          type: 'capture',
          startTime: now,
          duration: DEFAULT_CAPTURE_DURATION,
          color,
        });
      }
      onUpdate?.();
    },

    clear(): void {
      animations.length = 0;
    },

    getActive(): readonly StoneAnimation[] {
      const now = Date.now();
      return animations.filter((a) => now - a.startTime < a.duration);
    },

    isAnimating(): boolean {
      const now = Date.now();
      return animations.some((a) => now - a.startTime < a.duration);
    },

    update(): boolean {
      const now = Date.now();
      // Remove completed animations
      for (let i = animations.length - 1; i >= 0; i--) {
        const anim = animations[i];
        if (anim && now - anim.startTime >= anim.duration) {
          animations.splice(i, 1);
        }
      }
      return animations.length > 0;
    },
  };
}

/**
 * Calculate capture animation progress
 *
 * @param animation - Animation state
 * @returns Progress value 0-1 (1 = complete)
 */
export function getCaptureProgress(animation: StoneAnimation): number {
  const elapsed = Date.now() - animation.startTime;
  return Math.min(elapsed / animation.duration, 1);
}

/**
 * Draw a capturing stone (fading out and shrinking)
 *
 * @param ctx - Canvas context
 * @param animation - Animation state
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawCapturingStone(
  ctx: CanvasRenderingContext2D,
  animation: StoneAnimation,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  const progress = getCaptureProgress(animation);
  const x = offsetX + animation.coord.x * cellSize;
  const y = offsetY + animation.coord.y * cellSize;

  // Calculate animated values
  const scale = 1 - progress * 0.5; // Shrink to 50%
  const alpha = 1 - progress; // Fade out
  const radius = cellSize * 0.46 * scale;

  if (alpha <= 0 || radius <= 0) return;

  ctx.save();
  ctx.globalAlpha = alpha;

  // Draw stone with gradient (simplified from stones.ts)
  const isBlack = animation.color === 'black';
  const gradient = ctx.createRadialGradient(
    x - radius * 0.3,
    y - radius * 0.3,
    0,
    x,
    y,
    radius
  );

  if (isBlack) {
    gradient.addColorStop(0, '#4a4a4a');
    gradient.addColorStop(1, '#000000');
  } else {
    gradient.addColorStop(0, '#ffffff');
    gradient.addColorStop(0.9, '#e0e0e0');
    gradient.addColorStop(1, '#c0c0c0');
  }

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  // Border for white stones
  if (!isBlack) {
    ctx.strokeStyle = `rgba(128, 128, 128, ${alpha * 0.5})`;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  ctx.restore();
}

/**
 * Draw all capture animations
 *
 * @param ctx - Canvas context
 * @param manager - Animation manager
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawCaptureAnimations(
  ctx: CanvasRenderingContext2D,
  manager: AnimationManager,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  for (const anim of manager.getActive()) {
    if (anim.type === 'capture') {
      drawCapturingStone(ctx, anim, cellSize, offsetX, offsetY);
    }
  }
}

/**
 * Draw placement animation (stone appearing)
 *
 * @param ctx - Canvas context
 * @param animation - Animation state
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawPlacingStone(
  ctx: CanvasRenderingContext2D,
  animation: StoneAnimation,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  const progress = getCaptureProgress(animation);
  const x = offsetX + animation.coord.x * cellSize;
  const y = offsetY + animation.coord.y * cellSize;

  // Ease-out bounce effect
  const easeOutBounce = (t: number): number => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) {
      return n1 * t * t;
    } else if (t < 2 / d1) {
      return n1 * (t -= 1.5 / d1) * t + 0.75;
    } else if (t < 2.5 / d1) {
      return n1 * (t -= 2.25 / d1) * t + 0.9375;
    } else {
      return n1 * (t -= 2.625 / d1) * t + 0.984375;
    }
  };

  const scale = easeOutBounce(progress);
  const radius = cellSize * 0.46 * scale;

  if (radius <= 0) return;

  const isBlack = animation.color === 'black';
  const gradient = ctx.createRadialGradient(
    x - radius * 0.3,
    y - radius * 0.3,
    0,
    x,
    y,
    radius
  );

  if (isBlack) {
    gradient.addColorStop(0, '#4a4a4a');
    gradient.addColorStop(1, '#000000');
  } else {
    gradient.addColorStop(0, '#ffffff');
    gradient.addColorStop(0.9, '#e0e0e0');
    gradient.addColorStop(1, '#c0c0c0');
  }

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = gradient;
  ctx.fill();

  if (!isBlack) {
    ctx.strokeStyle = 'rgba(128, 128, 128, 0.5)';
    ctx.lineWidth = 1;
    ctx.stroke();
  }
}

/**
 * Draw highlight animation
 *
 * @param ctx - Canvas context
 * @param animation - Animation state
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawHighlightAnimation(
  ctx: CanvasRenderingContext2D,
  animation: StoneAnimation,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  const progress = getCaptureProgress(animation);
  const x = offsetX + animation.coord.x * cellSize;
  const y = offsetY + animation.coord.y * cellSize;

  // Pulsing highlight
  const pulse = Math.sin(progress * Math.PI);
  const radius = cellSize * 0.4 * (1 + pulse * 0.2);
  const alpha = 0.5 * (1 - progress);

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fillStyle = `rgba(100, 180, 255, ${alpha})`;
  ctx.fill();
}

/**
 * Draw all animations
 *
 * @param ctx - Canvas context
 * @param manager - Animation manager
 * @param cellSize - Cell size
 * @param offsetX - X offset
 * @param offsetY - Y offset
 */
export function drawAllAnimations(
  ctx: CanvasRenderingContext2D,
  manager: AnimationManager,
  cellSize: number,
  offsetX: number,
  offsetY: number
): void {
  for (const anim of manager.getActive()) {
    switch (anim.type) {
      case 'capture':
        drawCapturingStone(ctx, anim, cellSize, offsetX, offsetY);
        break;
      case 'place':
        drawPlacingStone(ctx, anim, cellSize, offsetX, offsetY);
        break;
      case 'highlight':
        drawHighlightAnimation(ctx, anim, cellSize, offsetX, offsetY);
        break;
    }
  }
}

/**
 * Create an animation frame loop
 *
 * @param manager - Animation manager
 * @param render - Render function to call each frame
 * @returns Stop function
 */
export function createAnimationLoop(
  manager: AnimationManager,
  render: () => void
): () => void {
  let frameId: number | null = null;

  const tick = (): void => {
    if (manager.isAnimating()) {
      manager.update();
      render();
      frameId = requestAnimationFrame(tick);
    } else {
      frameId = null;
    }
  };

  // Start the loop
  frameId = requestAnimationFrame(tick);

  // Return stop function
  return () => {
    if (frameId !== null) {
      cancelAnimationFrame(frameId);
      frameId = null;
    }
  };
}

/**
 * Ease functions for animations
 */
export const easing = {
  linear: (t: number): number => t,

  easeOutQuad: (t: number): number => t * (2 - t),

  easeOutCubic: (t: number): number => --t * t * t + 1,

  easeOutElastic: (t: number): number => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0
      ? 0
      : t === 1
        ? 1
        : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1;
  },

  easeOutBounce: (t: number): number => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) {
      return n1 * t * t;
    } else if (t < 2 / d1) {
      return n1 * (t -= 1.5 / d1) * t + 0.75;
    } else if (t < 2.5 / d1) {
      return n1 * (t -= 2.25 / d1) * t + 0.9375;
    } else {
      return n1 * (t -= 2.625 / d1) * t + 0.984375;
    }
  },
};
