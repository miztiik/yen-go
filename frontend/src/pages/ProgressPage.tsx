/**
 * ProgressPage — Main scrollable progress dashboard.
 * @module pages/ProgressPage
 *
 * Shows overall stats, technique breakdown, difficulty chart,
 * activity heatmap, achievements, and smart practice CTA.
 */

import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { PageLayout } from '../components/Layout/PageLayout';
import { PageHeader } from '../components/shared/PageHeader';
import { TrendUpIcon } from '../components/shared/icons';
import { ProgressOverview } from '../components/Progress/ProgressOverview';
import { TechniqueRadar } from '../components/Progress/TechniqueRadar';
import { DifficultyChart } from '../components/Progress/DifficultyChart';
import { ActivityHeatmap } from '../components/Progress/ActivityHeatmap';
import { AchievementsGrid } from '../components/Progress/AchievementsGrid';
import { SmartPracticeCTA } from '../components/Progress/SmartPracticeCTA';
import { computeProgressSummary, getWeakestTechniques } from '../services/progressAnalytics';
import type { ProgressSummary, TechniqueStats } from '../services/progressAnalytics';
import { evaluateAchievements } from '../services/achievementEngine';
import type { AchievementNotification } from '../services/achievementEngine';

export interface ProgressPageProps {
  onBack: () => void;
  onStartSmartPractice: (techniques?: string[]) => void;
}

export const ProgressPage: FunctionalComponent<ProgressPageProps> = ({
  onBack,
  onStartSmartPractice,
}) => {
  const [summary, setSummary] = useState<ProgressSummary | null>(null);
  const [achievements, setAchievements] = useState<AchievementNotification[]>([]);
  const [weakest, setWeakest] = useState<TechniqueStats[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [summaryResult, weakestResult] = await Promise.all([
        computeProgressSummary(),
        getWeakestTechniques(3),
      ]);
      const achievementResult = evaluateAchievements();

      if (!cancelled) {
        setSummary(summaryResult);
        setAchievements(achievementResult);
        setWeakest(weakestResult);
        setIsLoading(false);
      }
    }

    void load();
    return () => { cancelled = true; };
  }, []);

  const handleBack = useCallback(() => onBack(), [onBack]);

  if (isLoading) {
    return (
      <PageLayout variant="single-column">
        <PageLayout.Content>
          <PageHeader
            title="My Progress"
            icon={<TrendUpIcon size={36} />}
            onBack={handleBack}
            testId="progress-header"
          />
          <div className="flex items-center justify-center py-16" data-testid="progress-loading">
            <span className="text-sm text-[var(--color-text-muted)]">Loading progress...</span>
          </div>
        </PageLayout.Content>
      </PageLayout>
    );
  }

  if (!summary || summary.totalSolved === 0) {
    return (
      <PageLayout variant="single-column">
        <PageLayout.Content>
          <PageHeader
            title="My Progress"
            icon={<TrendUpIcon size={36} />}
            onBack={handleBack}
            testId="progress-header"
          />
          <div className="flex flex-col items-center gap-4 py-16" data-testid="progress-empty">
            <p className="text-center text-sm text-[var(--color-text-muted)]">
              No puzzles solved yet. Start solving to see your progress here.
            </p>
          </div>
        </PageLayout.Content>
      </PageLayout>
    );
  }

  return (
    <PageLayout variant="single-column">
      <PageLayout.Content>
        <PageHeader
          title="My Progress"
          subtitle={`${summary.totalSolved} puzzles solved`}
          icon={<TrendUpIcon size={36} />}
          stats={[
            { label: 'Accuracy', value: `${Math.round(summary.overallAccuracy)}%` },
            { label: 'Streak', value: summary.currentStreak },
          ]}
          onBack={handleBack}
          testId="progress-header"
        />

        <div className="mx-auto max-w-3xl px-4 py-6">
          <ProgressOverview
            totalSolved={summary.totalSolved}
            overallAccuracy={summary.overallAccuracy}
            currentStreak={summary.currentStreak}
            longestStreak={summary.longestStreak}
          />

          <TechniqueRadar techniques={summary.techniques} />

          <DifficultyChart difficulties={summary.difficulties} />

          <ActivityHeatmap activityDays={summary.activityDays} />

          <AchievementsGrid achievements={achievements} />

          <SmartPracticeCTA
            weakestTechniques={weakest}
            onStart={onStartSmartPractice}
          />
        </div>
      </PageLayout.Content>
    </PageLayout>
  );
};
