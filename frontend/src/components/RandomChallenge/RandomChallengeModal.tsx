import type { FunctionalComponent } from 'preact';
import { useState, useEffect } from 'preact/hooks';
import { Modal } from '../shared/Modal';
import { Button } from '../shared/Button';
import { RandomizeIcon } from '../shared/icons/RandomizeIcon';
import type { SkillLevel } from '../../models/collection';
import { SKILL_LEVELS, getSkillLevelInfo } from '../../models/collection';

export interface RandomChallengeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStart: (level: SkillLevel) => void;
  /** Estimated user level from progress history */
  estimatedLevel: SkillLevel;
}

/**
 * Modal for starting a random challenge with level selection.
 * Shows estimated skill level based on user's history.
 */
export const RandomChallengeModal: FunctionalComponent<RandomChallengeModalProps> = ({
  isOpen,
  onClose,
  onStart,
  estimatedLevel,
}) => {
  const [selectedLevel, setSelectedLevel] = useState<SkillLevel>(estimatedLevel);

  // Update selected level when estimated level changes
  useEffect(() => {
    setSelectedLevel(estimatedLevel);
  }, [estimatedLevel]);

  const levelInfo = getSkillLevelInfo(selectedLevel);

  const handleStart = () => {
    onStart(selectedLevel);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Random Challenge"
      size="md"
    >
      <div className="flex flex-col gap-6">
        {/* Estimated level display */}
        <div className="rounded-xl bg-gradient-to-br from-[--color-mode-random-border] to-[--color-mode-random-text] p-6 text-center text-[--color-bg-panel]">
          <div className="mb-1 text-sm opacity-90">
            Your Estimated Level
          </div>
          <div className="text-2xl font-bold">
            {getSkillLevelInfo(estimatedLevel)?.name ?? estimatedLevel}
          </div>
          <div className="mt-1 text-xs opacity-80">
            {getSkillLevelInfo(estimatedLevel)?.rankRange.min} - {getSkillLevelInfo(estimatedLevel)?.rankRange.max}
          </div>
        </div>

        {/* Level selection */}
        <div>
          <label className="mb-2 block text-sm font-medium text-[--color-text-primary]">
            Challenge Level
          </label>
          <p className="mb-3 mt-0 text-xs text-[--color-text-secondary]">
            Start at your estimated level or choose a different difficulty
          </p>
          
          <div className="grid grid-cols-3 gap-2">
            {SKILL_LEVELS.map((level) => {
              const isSelected = selectedLevel === level.slug;
              const isEstimated = estimatedLevel === level.slug;
              
              return (
                <button
                  key={level.slug}
                  type="button"
                  onClick={() => setSelectedLevel(level.slug)}
                  className={`relative cursor-pointer rounded-lg px-2 py-3 transition-all duration-200 ${
                    isSelected
                      ? 'border-2 border-[--color-mode-random-border] bg-[--color-mode-random-light]'
                      : 'border border-[--color-border] bg-[--color-bg-panel]'
                  }`}
                >
                  <div className={`text-sm ${isSelected ? 'font-semibold text-[--color-mode-random-text]' : 'text-[--color-text-primary]'}`}>
                    {level.shortName}
                  </div>
                  <div className="mt-0.5 text-[0.625rem] text-[--color-text-muted]">
                    {level.rankRange.min}
                  </div>
                  {isEstimated && (
                    <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full bg-[--color-mode-random-border]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Selected level info */}
        {levelInfo && (
          <div className="rounded-lg bg-[--color-bg-secondary] p-4 text-sm">
            <div className="mb-1 font-semibold text-[--color-text-primary]">
              {levelInfo.name} ({levelInfo.rankRange.min} - {levelInfo.rankRange.max})
            </div>
            <div className="text-[--color-text-secondary]">
              {levelInfo.description}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 border-t border-[--color-border] pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleStart}>
            <RandomizeIcon size={14} /> Start Random Challenge
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default RandomChallengeModal;
