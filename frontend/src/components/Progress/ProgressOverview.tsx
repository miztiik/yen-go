/**
 * ProgressOverview — 4-stat summary cards (total solved, accuracy, current/longest streak).
 * @module components/Progress/ProgressOverview
 */

import type { FunctionalComponent } from 'preact';
import { CheckIcon, StarIcon, StreakIcon, TrophyIcon } from '../shared/icons';

export interface ProgressOverviewProps {
  totalSolved: number;
  overallAccuracy: number;
  currentStreak: number;
  longestStreak: number;
}

interface StatCardProps {
  icon: preact.ComponentChildren;
  label: string;
  value: string | number;
  testId: string;
}

function StatCard({ icon, label, value, testId }: StatCardProps) {
  return (
    <div
      className="flex flex-col items-center gap-1 rounded-xl bg-[var(--color-bg-elevated)] p-4 shadow-sm"
      data-testid={testId}
    >
      <div className="text-[var(--color-accent)]">{icon}</div>
      <span className="text-2xl font-bold text-[var(--color-text-primary)]">{value}</span>
      <span className="text-xs font-medium text-[var(--color-text-muted)]">{label}</span>
    </div>
  );
}

export const ProgressOverview: FunctionalComponent<ProgressOverviewProps> = ({
  totalSolved,
  overallAccuracy,
  currentStreak,
  longestStreak,
}) => {
  return (
    <section data-testid="progress-overview" className="mb-6">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={<CheckIcon size={24} />}
          label="Solved"
          value={totalSolved}
          testId="stat-solved"
        />
        <StatCard
          icon={<StarIcon size={24} />}
          label="Accuracy"
          value={`${Math.round(overallAccuracy)}%`}
          testId="stat-accuracy"
        />
        <StatCard
          icon={<StreakIcon size={24} />}
          label="Current Streak"
          value={currentStreak}
          testId="stat-current-streak"
        />
        <StatCard
          icon={<TrophyIcon size={24} />}
          label="Longest Streak"
          value={longestStreak}
          testId="stat-longest-streak"
        />
      </div>
    </section>
  );
};
