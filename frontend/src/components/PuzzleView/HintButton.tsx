/**
 * Hint button component for requesting puzzle hints.
 * Shows progressive hints when clicked.
 * @module components/PuzzleView/HintButton
 */

import { type FunctionalComponent } from 'preact';
import type { HintState, HintLevel } from '../../lib/hints/progressive';
import './HintButton.css';

/**
 * Props for HintButton component.
 */
export interface HintButtonProps {
  /** Current hint state */
  hintState: HintState;
  /** Whether hints are enabled in settings */
  hintsEnabled: boolean;
  /** Whether puzzle is completed */
  isCompleted: boolean;
  /** Callback when hint is requested */
  onRequestHint: () => void;
}

/**
 * Get button text based on hint level.
 */
function getButtonText(level: HintLevel, canAdvance: boolean): string {
  if (!canAdvance && level === 3) {
    return 'Max Hints';
  }
  switch (level) {
    case 0:
      return 'Hint';
    case 1:
      return 'More Hint';
    case 2:
      return 'Show Move';
    case 3:
      return 'Max Hints';
    default:
      return 'Hint';
  }
}

/**
 * Get accessibility label for screen readers.
 */
function getAriaLabel(level: HintLevel, canAdvance: boolean): string {
  if (!canAdvance) {
    return 'Maximum hint level reached';
  }
  switch (level) {
    case 0:
      return 'Request a hint';
    case 1:
      return 'Request a more specific hint';
    case 2:
      return 'Show the solution area';
    default:
      return 'Request a hint';
  }
}

/**
 * Hint button with progressive hint display.
 */
export const HintButton: FunctionalComponent<HintButtonProps> = ({
  hintState,
  hintsEnabled,
  isCompleted,
  onRequestHint,
}) => {
  // Don't show if hints are disabled
  if (!hintsEnabled) {
    return null;
  }

  // Don't show if puzzle is completed
  if (isCompleted) {
    return null;
  }

  const { level, canAdvance } = hintState;
  const buttonText = getButtonText(level, canAdvance);
  const ariaLabel = getAriaLabel(level, canAdvance);
  const isDisabled = !canAdvance;

  return (
    <button
      type="button"
      className={`hint-button hint-button--level-${level}`}
      onClick={onRequestHint}
      disabled={isDisabled}
      aria-label={ariaLabel}
      title={ariaLabel}
    >
      <span className="hint-button__icon" aria-hidden="true">
        💡
      </span>
      <span className="hint-button__text">{buttonText}</span>
      {level > 0 && (
        <span className="hint-button__level" aria-label={`Hint level ${level} of 3`}>
          {level}/3
        </span>
      )}
    </button>
  );
};

export default HintButton;
