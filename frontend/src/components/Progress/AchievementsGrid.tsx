/**
 * AchievementsGrid — Badge tiles for unlocked/locked achievements.
 * @module components/Progress/AchievementsGrid
 */

import type { FunctionalComponent } from 'preact';
import type { AchievementNotification } from '../../services/achievementEngine';
import { TrophyIcon } from '../shared/icons';

export interface AchievementsGridProps {
  achievements: readonly AchievementNotification[];
}

export const AchievementsGrid: FunctionalComponent<AchievementsGridProps> = ({ achievements }) => {
  if (achievements.length === 0) return null;

  return (
    <section data-testid="achievements-grid" className="mb-6">
      <h2 className="mb-3 text-lg font-bold text-[var(--color-text-primary)]">Achievements</h2>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
        {achievements.map(({ achievement, isNew }) => {
          const unlocked =
            achievement.unlockedAt != null ||
            (achievement.progress != null && achievement.progress >= achievement.target);
          return (
            <div
              key={achievement.id}
              className={`flex flex-col items-center gap-1 rounded-xl p-3 text-center transition-colors ${
                unlocked
                  ? 'bg-[var(--color-bg-elevated)] shadow-sm'
                  : 'bg-[var(--color-bg-secondary)] opacity-50'
              }`}
              data-testid={`achievement-${achievement.id}`}
            >
              <div className={unlocked ? 'text-yellow-500' : 'text-[var(--color-text-muted)]'}>
                <TrophyIcon size={28} />
              </div>
              <span className="text-xs font-bold text-[var(--color-text-primary)]">
                {achievement.name}
              </span>
              {unlocked ? (
                <span className="text-[10px] text-[var(--color-text-muted)]">
                  {achievement.description}
                </span>
              ) : (
                <span className="text-[10px] text-[var(--color-text-muted)]">
                  {achievement.progress ?? 0}/{achievement.target}
                </span>
              )}
              {isNew && unlocked && (
                <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-700">
                  New
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};
