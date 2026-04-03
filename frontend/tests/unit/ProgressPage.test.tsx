/**
 * Unit tests for ProgressPage.
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/preact';
import { ProgressPage } from '@/pages/ProgressPage';
import * as progressAnalytics from '@/services/progressAnalytics';
import * as achievementEngine from '@/services/achievementEngine';
import type { ProgressSummary, TechniqueStats } from '@/services/progressAnalytics';
import type { AchievementNotification } from '@/services/achievementEngine';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('@/services/progressAnalytics', () => ({
  computeProgressSummary: vi.fn(),
  getWeakestTechniques: vi.fn(),
}));

vi.mock('@/services/achievementEngine', () => ({
  evaluateAchievements: vi.fn(),
}));

// ============================================================================
// Mock Data
// ============================================================================

const mockSummary: ProgressSummary = {
  totalSolved: 42,
  overallAccuracy: 78.5,
  currentStreak: 5,
  longestStreak: 12,
  avgTimeMs: 15000,
  techniques: [
    { tagId: 1, tagSlug: 'life-and-death', tagName: 'Life & Death', correct: 20, total: 30, accuracy: 66.67, avgTimeMs: 18000, trend30d: -5.2, lowData: false },
    { tagId: 2, tagSlug: 'ladder', tagName: 'Ladder', correct: 10, total: 12, accuracy: 83.33, avgTimeMs: 12000, trend30d: 10.1, lowData: false },
    { tagId: 3, tagSlug: 'ko', tagName: 'Ko', correct: 2, total: 3, accuracy: 66.67, avgTimeMs: 20000, trend30d: 0, lowData: true },
  ],
  difficulties: [
    { levelId: 110, levelName: 'Novice', correct: 15, total: 15, accuracy: 100 },
    { levelId: 120, levelName: 'Beginner', correct: 18, total: 22, accuracy: 81.82 },
    { levelId: 130, levelName: 'Elementary', correct: 5, total: 10, accuracy: 50 },
  ],
  activityDays: new Map([['2026-03-18', 5], ['2026-03-17', 3], ['2026-03-15', 1]]),
};

const mockWeakest: TechniqueStats[] = [
  mockSummary.techniques[0],
  mockSummary.techniques[2],
];

const mockAchievements: AchievementNotification[] = [
  {
    achievement: { id: 'first-solve', name: 'First Steps', description: 'Solve your first puzzle', target: 1, progress: 42, unlockedAt: '2026-03-01T00:00:00Z' },
    isNew: false,
  },
  {
    achievement: { id: 'solve-10', name: 'Getting Started', description: 'Solve 10 puzzles', target: 10, progress: 42, unlockedAt: '2026-03-10T00:00:00Z' },
    isNew: true,
  },
];

const emptySummary: ProgressSummary = {
  totalSolved: 0,
  overallAccuracy: 0,
  currentStreak: 0,
  longestStreak: 0,
  avgTimeMs: 0,
  techniques: [],
  difficulties: [],
  activityDays: new Map(),
};

// ============================================================================
// Tests
// ============================================================================

describe('ProgressPage', () => {
  let onBack: Mock;
  let onStartSmartPractice: Mock;

  beforeEach(() => {
    vi.clearAllMocks();
    onBack = vi.fn();
    onStartSmartPractice = vi.fn();
  });

  function setup(summary = mockSummary, achievements = mockAchievements, weakest = mockWeakest) {
    (progressAnalytics.computeProgressSummary as Mock).mockResolvedValue(summary);
    (progressAnalytics.getWeakestTechniques as Mock).mockResolvedValue(weakest);
    (achievementEngine.evaluateAchievements as Mock).mockReturnValue(achievements);
    return render(
      <ProgressPage onBack={onBack} onStartSmartPractice={onStartSmartPractice} />,
    );
  }

  it('renders loading state initially', () => {
    (progressAnalytics.computeProgressSummary as Mock).mockReturnValue(new Promise(() => {}));
    (progressAnalytics.getWeakestTechniques as Mock).mockReturnValue(new Promise(() => {}));
    (achievementEngine.evaluateAchievements as Mock).mockReturnValue([]);

    const { getByTestId } = render(
      <ProgressPage onBack={onBack} onStartSmartPractice={onStartSmartPractice} />,
    );
    expect(getByTestId('progress-loading')).toBeTruthy();
  });

  it('renders all sections with mock data', async () => {
    const { getByTestId } = setup();
    await waitFor(() => expect(getByTestId('progress-overview')).toBeTruthy());
    expect(getByTestId('technique-radar')).toBeTruthy();
    expect(getByTestId('difficulty-chart')).toBeTruthy();
    expect(getByTestId('activity-heatmap')).toBeTruthy();
    expect(getByTestId('achievements-grid')).toBeTruthy();
    expect(getByTestId('smart-practice-cta')).toBeTruthy();
  });

  it('renders empty state when totalSolved is 0', async () => {
    const { getByTestId, queryByTestId } = setup(emptySummary, [], []);
    await waitFor(() => expect(getByTestId('progress-empty')).toBeTruthy());
    expect(queryByTestId('progress-overview')).toBeNull();
  });

  it('calls onBack when back button clicked', async () => {
    const { getByTestId, getByText } = setup();
    await waitFor(() => expect(getByTestId('progress-overview')).toBeTruthy());
    const backBtn = getByText('Back');
    fireEvent.click(backBtn);
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('calls onStartSmartPractice when CTA clicked', async () => {
    const { getByTestId } = setup();
    await waitFor(() => expect(getByTestId('smart-practice-cta')).toBeTruthy());
    fireEvent.click(getByTestId('start-smart-practice'));
    expect(onStartSmartPractice).toHaveBeenCalledWith(['life-and-death', 'ko']);
  });

  it('handles single technique with data', async () => {
    const singleTechnique = {
      ...mockSummary,
      techniques: [mockSummary.techniques[0]],
    };
    const { getByTestId } = setup(singleTechnique, [], [mockSummary.techniques[0]]);
    await waitFor(() => expect(getByTestId('technique-radar')).toBeTruthy());
    expect(getByTestId('technique-life-and-death')).toBeTruthy();
  });

  it('handles all techniques at 100%', async () => {
    const perfect: ProgressSummary = {
      ...mockSummary,
      techniques: [
        { tagId: 1, tagSlug: 'life-and-death', tagName: 'Life & Death', correct: 10, total: 10, accuracy: 100, avgTimeMs: 12000, trend30d: 5, lowData: false },
      ],
    };
    const { getByTestId, queryByTestId } = setup(perfect, [], []);
    await waitFor(() => expect(getByTestId('technique-radar')).toBeTruthy());
    // No negative insight when all trends are positive
    expect(queryByTestId('technique-insight')).toBeNull();
  });

  it('handles activityDays empty map', async () => {
    const noActivity = { ...mockSummary, activityDays: new Map<string, number>() };
    const { getByTestId } = setup(noActivity);
    await waitFor(() => expect(getByTestId('activity-heatmap')).toBeTruthy());
  });
});
