// @ts-nocheck
import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useMemo, useCallback } from 'preact/hooks';
import { Modal } from '../shared/Modal';
import { TrainingLevelCard } from './TrainingLevelCard';
import { SKILL_LEVELS, type SkillLevel } from '../../models/collection';

const TRAINING_PROGRESS_KEY = 'yen-go-training-progress';

export interface TrainingProgress {
  byLevel: Record<string, {
    completed: number;
    total: number;
    accuracy: number;
  }>;
  unlockedLevels: string[];
  updatedAt: string;
}

export interface TrainingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectLevel: (level: SkillLevel) => void;
}

/**
 * Modal for selecting training level.
 * Shows all 9 levels with progress and unlock status.
 */
export const TrainingModal: FunctionalComponent<TrainingModalProps> = ({
  isOpen,
  onClose,
  onSelectLevel,
}) => {
  const [progress, setProgress] = useState<TrainingProgress | null>(null);
  const [activeLevel, setActiveLevel] = useState<SkillLevel | null>(null);

  // Load training progress from localStorage
  useEffect(() => {
    if (!isOpen) return;

    try {
      const stored = localStorage.getItem(TRAINING_PROGRESS_KEY);
      if (stored) {
        setProgress(JSON.parse(stored));
      } else {
        // Initialize with first level unlocked
        setProgress({
          byLevel: {},
          unlockedLevels: ['novice'],
          updatedAt: new Date().toISOString(),
        });
      }
    } catch (err) {
      console.error('Error loading training progress:', err);
      setProgress({
        byLevel: {},
        unlockedLevels: ['novice'],
        updatedAt: new Date().toISOString(),
      });
    }
  }, [isOpen]);

  // Calculate which levels are unlocked
  const unlockedLevels = useMemo(() => {
    if (!progress) return new Set(['novice']);

    const unlocked = new Set(progress.unlockedLevels);
    unlocked.add('novice'); // First level always unlocked

    // Check if each level should be unlocked based on previous level completion
    for (let i = 1; i < SKILL_LEVELS.length; i++) {
      const currentLevel = SKILL_LEVELS[i];
      const previousLevel = SKILL_LEVELS[i - 1];
      
      if (!currentLevel || !previousLevel) continue;

      const prevProgress = progress.byLevel[previousLevel.slug];
      if (prevProgress && prevProgress.total > 0) {
        const percentComplete = (prevProgress.completed / prevProgress.total) * 100;
        if (percentComplete >= 70) {
          unlocked.add(currentLevel.slug);
        }
      }
    }

    return unlocked;
  }, [progress]);

  // Find the recommended active level
  useEffect(() => {
    if (!progress) return;

    // Find the highest unlocked level with incomplete progress
    for (let i = SKILL_LEVELS.length - 1; i >= 0; i--) {
      const level = SKILL_LEVELS[i];
      if (!level) continue;
      
      if (unlockedLevels.has(level.slug)) {
        const levelProgress = progress.byLevel[level.slug];
        if (!levelProgress || levelProgress.completed < levelProgress.total) {
          setActiveLevel(level.slug);
          return;
        }
      }
    }
    
    // Default to novice
    setActiveLevel('novice');
  }, [progress, unlockedLevels]);

  const handleSelectLevel = useCallback((levelSlug: string) => {
    onSelectLevel(levelSlug);
    onClose();
  }, [onSelectLevel, onClose]);

  // Calculate overall stats
  const overallStats = useMemo(() => {
    if (!progress) return { completed: 0, total: 0, levelsCompleted: 0 };

    let completed = 0;
    let total = 0;
    let levelsCompleted = 0;

    Object.values(progress.byLevel).forEach((levelProgress) => {
      completed += levelProgress.completed;
      total += levelProgress.total;
      if (levelProgress.total > 0 && levelProgress.completed >= levelProgress.total) {
        levelsCompleted++;
      }
    });

    return { completed, total, levelsCompleted };
  }, [progress]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Training Mode"
      size="lg"
    >
      <div className="flex flex-col gap-6">
        {/* Stats header */}
        <div className="rounded-xl bg-gradient-to-br from-[--color-mode-training-border] to-[--color-mode-training-text] p-5 text-[--color-bg-panel]">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold">
                {overallStats.levelsCompleted}/{SKILL_LEVELS.length}
              </div>
              <div className="text-xs opacity-90">Levels Completed</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {overallStats.completed}
              </div>
              <div className="text-xs opacity-90">Puzzles Solved</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {unlockedLevels.size}
              </div>
              <div className="text-xs opacity-90">Levels Unlocked</div>
            </div>
          </div>
        </div>

        {/* Level list */}
        <div className="flex max-h-[400px] flex-col gap-2 overflow-y-auto p-1">
          {SKILL_LEVELS.map((level) => {
            const levelProgress = progress?.byLevel[level.slug] ?? { completed: 0, total: 0 };
            const isUnlocked = unlockedLevels.has(level.slug);
            const isActive = activeLevel === level.slug;

            return (
              <TrainingLevelCard
                key={level.slug}
                level={level}
                progress={levelProgress}
                isUnlocked={isUnlocked}
                isActive={isActive}
                onSelect={handleSelectLevel}
              />
            );
          })}
        </div>

        {/* Help text */}
        <div className="border-t border-[--color-border] pt-2 text-center text-xs text-[--color-text-muted]">
          Complete 70% of a level to unlock the next one
        </div>
      </div>
    </Modal>
  );
};

/**
 * Save training progress for a level
 */
export function saveTrainingProgress(
  levelSlug: SkillLevel,
  completed: number,
  total: number,
  accuracy: number
): void {
  try {
    const stored = localStorage.getItem(TRAINING_PROGRESS_KEY);
    const progress: TrainingProgress = stored
      ? JSON.parse(stored)
      : { byLevel: {}, unlockedLevels: ['novice'], updatedAt: new Date().toISOString() };

    // Update level progress
    progress.byLevel[levelSlug] = { completed, total, accuracy };
    progress.updatedAt = new Date().toISOString();

    // Check if next level should be unlocked
    const currentLevelIndex = SKILL_LEVELS.findIndex(l => l.slug === levelSlug);
    if (currentLevelIndex >= 0 && currentLevelIndex < SKILL_LEVELS.length - 1) {
      const percentComplete = (completed / total) * 100;
      if (percentComplete >= 70) {
        const nextLevel = SKILL_LEVELS[currentLevelIndex + 1];
        if (nextLevel && !progress.unlockedLevels.includes(nextLevel.slug)) {
          progress.unlockedLevels.push(nextLevel.slug);
        }
      }
    }

    localStorage.setItem(TRAINING_PROGRESS_KEY, JSON.stringify(progress));
  } catch (err) {
    console.error('Error saving training progress:', err);
  }
}

/**
 * Get current training progress
 */
export function getTrainingProgress(): TrainingProgress | null {
  try {
    const stored = localStorage.getItem(TRAINING_PROGRESS_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch (err) {
    console.error('Error loading training progress:', err);
    return null;
  }
}

export default TrainingModal;
