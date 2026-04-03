/**
 * Review controls component for solution playback.
 * Provides navigation buttons for stepping through moves.
 * @module components/Review/Controls
 */

import type { FunctionalComponent, JSX } from 'preact';
import type { ReviewState } from '../../lib/review/controller';
import './Controls.css';

/**
 * Props for ReviewControls component.
 */
export interface ReviewControlsProps {
  /** Current review state */
  state: ReviewState;
  /** Callback when previous is clicked */
  onPrevious: () => void;
  /** Callback when next is clicked */
  onNext: () => void;
  /** Callback when beginning is clicked */
  onBeginning: () => void;
  /** Callback when end is clicked */
  onEnd: () => void;
  /** Callback to go to specific move */
  onGoTo?: (index: number) => void;
  /** Optional auto-play state */
  isAutoPlaying?: boolean;
  /** Callback for auto-play toggle */
  onToggleAutoPlay?: () => void;
  /** Optional CSS class */
  className?: string;
}

/**
 * Icon button component.
 */
interface IconButtonProps {
  label: string;
  icon: string;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
}

function IconButton({
  label,
  icon,
  onClick,
  disabled = false,
  title,
}: IconButtonProps): JSX.Element {
  return (
    <button
      type="button"
      className={`review-btn ${disabled ? 'review-btn--disabled' : ''}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={title || label}
    >
      <span className="review-btn__icon" aria-hidden="true">
        {icon}
      </span>
    </button>
  );
}

/**
 * Review controls with navigation buttons.
 */
export const ReviewControls: FunctionalComponent<ReviewControlsProps> = ({
  state,
  onPrevious,
  onNext,
  onBeginning,
  onEnd,
  onGoTo,
  isAutoPlaying = false,
  onToggleAutoPlay,
  className = '',
}) => {
  const { currentIndex, totalMoves, canGoBack, canGoForward } = state;
  const moveDisplay = currentIndex < 0 ? 'Start' : `${currentIndex + 1}/${totalMoves}`;

  const handleSliderChange = (e: Event): void => {
    const target = e.target as HTMLInputElement;
    const value = parseInt(target.value, 10);
    onGoTo?.(value);
  };

  return (
    <div className={`review-controls ${className}`}>
      <div className="review-controls__buttons">
        <IconButton
          label="Go to beginning"
          icon="⏮"
          onClick={onBeginning}
          disabled={!canGoBack}
          title="Go to beginning (Home)"
        />
        <IconButton
          label="Previous move"
          icon="◀"
          onClick={onPrevious}
          disabled={!canGoBack}
          title="Previous move (←)"
        />
        {onToggleAutoPlay && (
          <IconButton
            label={isAutoPlaying ? 'Pause' : 'Auto-play'}
            icon={isAutoPlaying ? '⏸' : '▶'}
            onClick={onToggleAutoPlay}
            title={isAutoPlaying ? 'Pause (Space)' : 'Auto-play (Space)'}
          />
        )}
        <IconButton
          label="Next move"
          icon="▶"
          onClick={onNext}
          disabled={!canGoForward}
          title="Next move (→)"
        />
        <IconButton
          label="Go to end"
          icon="⏭"
          onClick={onEnd}
          disabled={!canGoForward}
          title="Go to end (End)"
        />
      </div>

      <div className="review-controls__progress">
        <span className="review-controls__move-display">{moveDisplay}</span>
        {totalMoves > 0 && onGoTo && (
          <input
            type="range"
            className="review-controls__slider"
            min={-1}
            max={totalMoves - 1}
            value={currentIndex}
            onChange={handleSliderChange}
            aria-label="Move position"
            title={`Move ${currentIndex + 1} of ${totalMoves}`}
          />
        )}
      </div>
    </div>
  );
};

export default ReviewControls;
