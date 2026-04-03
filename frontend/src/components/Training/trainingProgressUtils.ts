/**
 * Training Progress Utilities
 * @module components/Training/trainingProgressUtils
 *
 * localStorage-backed training progress persistence.
 * Extracted from TrainingModal.tsx during modal-to-page cleanup (Spec 132, Phase 9).
 */

import { SKILL_LEVELS, type SkillLevel } from '../../models/collection';
import { FIRST_LEVEL } from '../../lib/levels/level-defaults';

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

/**
 * Save training progress for a level.
 * Automatically unlocks the next level if completion >= 70%.
 */
export function saveTrainingProgress(
  levelSlug: SkillLevel,
  completed: number,
  total: number,
  accuracy: number,
): void {
  try {
    const stored = localStorage.getItem(TRAINING_PROGRESS_KEY);
    const progress: TrainingProgress = stored
      ? JSON.parse(stored)
      : { byLevel: {}, unlockedLevels: [FIRST_LEVEL], updatedAt: new Date().toISOString() };

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
 * Get current training progress from localStorage.
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
