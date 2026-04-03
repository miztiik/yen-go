/**
 * Animation Controls Component
 * @module components/Review/AnimationControls
 *
 * Provides playback controls for solution animation (FR-004, FR-005, FR-006).
 * Features: play/pause, speed control, step forward/backward, reset.
 *
 * Constitution Compliance:
 * - IX. Accessibility: Keyboard accessible, aria labels, focus management
 * - X. Design Philosophy: Clean, minimal interface
 */

import type { JSX } from 'preact';
import type { SolutionAnimationState } from '@models/SolutionPresentation';

/**
 * Speed presets for animation (FR-006).
 */
export const ANIMATION_SPEED_PRESETS = [
  { label: '0.5×', value: 2000 },
  { label: '1×', value: 1000 },
  { label: '1.5×', value: 667 },
  { label: '2×', value: 500 },
  { label: '3×', value: 333 },
] as const;

/**
 * Props for AnimationControls component.
 */
export interface AnimationControlsProps {
  /** Current animation state */
  state: SolutionAnimationState;
  /** Play callback */
  onPlay: () => void;
  /** Pause callback */
  onPause: () => void;
  /** Reset callback */
  onReset: () => void;
  /** Step forward callback */
  onStepForward: () => void;
  /** Step backward callback */
  onStepBackward: () => void;
  /** Go to specific frame callback */
  onGoToFrame: (frame: number) => void;
  /** Set delay callback */
  onSetDelay: (delayMs: number) => void;
  /** Whether controls are disabled */
  disabled?: boolean;
  /** CSS class override */
  className?: string;
  /** Compact mode (fewer controls) */
  compact?: boolean;
}

/**
 * Icon components for controls.
 */
const PlayIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M4 2.5v11l9-5.5L4 2.5z" />
  </svg>
);

const PauseIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <rect x="3" y="2" width="4" height="12" />
    <rect x="9" y="2" width="4" height="12" />
  </svg>
);

const StepBackIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <rect x="2" y="2" width="2" height="12" />
    <path d="M14 2.5v11l-9-5.5 9-5.5z" />
  </svg>
);

const StepForwardIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <rect x="12" y="2" width="2" height="12" />
    <path d="M2 2.5v11l9-5.5L2 2.5z" />
  </svg>
);

const ResetIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 2a6 6 0 1 0 6 6h-2a4 4 0 1 1-4-4V2z" />
    <path d="M8 0v6l4-3-4-3z" />
  </svg>
);

/**
 * AnimationControls component - playback controls for solution animation.
 */
export function AnimationControls({
  state,
  onPlay,
  onPause,
  onReset,
  onStepForward,
  onStepBackward,
  onGoToFrame,
  onSetDelay,
  disabled = false,
  className,
  compact = false,
}: AnimationControlsProps): JSX.Element {
  const { isPlaying, currentFrame, totalFrames, delayMs } = state;

  // Find current speed preset
  const currentSpeedIndex = ANIMATION_SPEED_PRESETS.findIndex(
    (preset) => preset.value === delayMs
  );
  // Keep for future speed display/aria label
  void currentSpeedIndex;

  const handlePlayPause = (): void => {
    if (isPlaying) {
      onPause();
    } else {
      onPlay();
    }
  };

  const handleSliderChange = (e: Event): void => {
    const target = e.target as HTMLInputElement;
    onGoToFrame(parseInt(target.value, 10));
  };

  const handleSpeedChange = (e: Event): void => {
    const target = e.target as HTMLSelectElement;
    onSetDelay(parseInt(target.value, 10));
  };

  return (
    <div
      className={`animation-controls ${compact ? 'animation-controls--compact' : ''} ${className ?? ''}`}
      role="group"
      aria-label="Animation playback controls"
    >
      {/* Main controls row */}
      <div className="animation-controls__buttons">
        {/* Reset */}
        <button
          type="button"
          className="animation-controls__btn"
          onClick={onReset}
          disabled={disabled || currentFrame === 0}
          aria-label="Reset animation"
          title="Reset (Home)"
        >
          <ResetIcon />
        </button>

        {/* Step backward */}
        <button
          type="button"
          className="animation-controls__btn"
          onClick={onStepBackward}
          disabled={disabled || currentFrame === 0}
          aria-label="Previous move"
          title="Previous (←)"
        >
          <StepBackIcon />
        </button>

        {/* Play/Pause */}
        <button
          type="button"
          className="animation-controls__btn animation-controls__btn--primary"
          onClick={handlePlayPause}
          disabled={disabled}
          aria-label={isPlaying ? 'Pause animation' : 'Play animation'}
          title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </button>

        {/* Step forward */}
        <button
          type="button"
          className="animation-controls__btn"
          onClick={onStepForward}
          disabled={disabled || currentFrame >= totalFrames - 1}
          aria-label="Next move"
          title="Next (→)"
        >
          <StepForwardIcon />
        </button>

        {/* Speed selector (only in full mode) */}
        {!compact && (
          <select
            className="animation-controls__speed"
            value={delayMs}
            onChange={handleSpeedChange}
            disabled={disabled}
            aria-label="Animation speed"
            title="Playback speed"
          >
            {ANIMATION_SPEED_PRESETS.map((preset) => (
              <option key={preset.value} value={preset.value}>
                {preset.label}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Progress slider */}
      <div className="animation-controls__progress">
        <input
          type="range"
          min="0"
          max={Math.max(0, totalFrames - 1)}
          value={currentFrame}
          onChange={handleSliderChange}
          disabled={disabled}
          className="animation-controls__slider"
          aria-label={`Move ${currentFrame + 1} of ${totalFrames}`}
          aria-valuemin={0}
          aria-valuemax={totalFrames - 1}
          aria-valuenow={currentFrame}
          aria-valuetext={`Move ${currentFrame + 1} of ${totalFrames}`}
        />
        <span className="animation-controls__frame-info" aria-live="polite">
          {currentFrame + 1} / {totalFrames}
        </span>
      </div>
    </div>
  );
}

export default AnimationControls;
