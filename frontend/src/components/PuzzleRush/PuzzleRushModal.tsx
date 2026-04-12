import type { FunctionalComponent } from 'preact';
import { useState } from 'preact/hooks';
import { Modal } from '../shared/Modal';
import { Button } from '../shared/Button';
import { FireIcon } from '../shared/icons/FireIcon';

export type RushDuration = 3 | 5 | 10;

export interface PuzzleRushModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (duration: RushDuration) => void;
  /** Best score from previous sessions */
  bestScore?: number;
}

const DURATION_OPTIONS: { value: RushDuration; label: string; description: string }[] = [
  { value: 3, label: '3 Minutes', description: 'Quick sprint - best for warmup' },
  { value: 5, label: '5 Minutes', description: 'Standard challenge' },
  { value: 10, label: '10 Minutes', description: 'Extended marathon' },
];

/**
 * Modal for configuring and starting a Puzzle Rush session.
 * Allows selection of duration: 3, 5, or 10 minutes.
 */
export const PuzzleRushModal: FunctionalComponent<PuzzleRushModalProps> = ({
  isOpen,
  onClose,
  onStart,
  bestScore,
}) => {
  const [selectedDuration, setSelectedDuration] = useState<RushDuration>(5);

  const handleStart = () => {
    onStart(selectedDuration);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Puzzle Rush" size="md">
      <div className="flex flex-col gap-6">
        {/* Best score display */}
        <div className="rounded-xl bg-gradient-to-br from-[--color-mode-rush-border] to-[--color-mode-rush-text] p-6 text-center text-[--color-bg-panel]">
          <div className="text-sm opacity-90">
            {bestScore !== undefined ? 'Your Best Score' : 'Ready to Rush?'}
          </div>
          <div className="mt-1 text-[2.5rem] font-bold leading-tight">
            {bestScore !== undefined ? bestScore : <FireIcon size={40} />}
          </div>
          {bestScore !== undefined && (
            <div className="mt-1 text-xs opacity-80">Can you beat it?</div>
          )}
        </div>

        {/* Rules summary */}
        <div className="rounded-lg border border-[--color-mode-rush-border] bg-[--color-mode-rush-light] p-4">
          <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-mode-rush-text]">
            How It Works
          </h3>
          <ul className="m-0 pl-5 text-xs leading-relaxed text-[--color-mode-rush-text]">
            <li>Solve as many puzzles as you can before time runs out</li>
            <li>
              Each correct answer: <strong>+10 points</strong>
            </li>
            <li>3 wrong answers and you're out!</li>
            <li>Skip up to 3 puzzles (no penalty)</li>
            <li>Difficulty increases every 5 correct answers</li>
          </ul>
        </div>

        {/* Duration selection */}
        <div>
          <label className="mb-3 block text-sm font-medium text-[--color-neutral-700]">
            Choose Duration
          </label>

          <div className="flex flex-col gap-2">
            {DURATION_OPTIONS.map((option) => {
              const isSelected = selectedDuration === option.value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setSelectedDuration(option.value)}
                  className={`flex cursor-pointer items-center justify-between rounded-lg p-4 transition-all ${
                    isSelected
                      ? 'border-2 border-[--color-mode-rush-border] bg-[--color-mode-rush-light]'
                      : 'border border-[--color-neutral-200] bg-[--color-bg-panel] hover:border-[--color-mode-rush-border] hover:bg-[--color-mode-rush-light]'
                  }`}
                >
                  <div className="text-left">
                    <div
                      className={
                        isSelected
                          ? 'font-semibold text-[--color-mode-rush-text]'
                          : 'text-[--color-neutral-700]'
                      }
                    >
                      {option.label}
                    </div>
                    <div className="mt-0.5 text-xs text-[--color-neutral-500]">
                      {option.description}
                    </div>
                  </div>
                  {isSelected && (
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[--color-mode-rush-border] text-xs text-[--color-bg-panel]">
                      ✓
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 border-t border-[--color-neutral-200] pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleStart} className="bg-[--color-mode-rush-border]">
            <FireIcon size={14} /> Start Rush ({selectedDuration}min)
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default PuzzleRushModal;
