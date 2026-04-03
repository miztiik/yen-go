/**
 * Rush Results component tests.
 *
 * Verifies:
 * - Results renders title based on timedOut flag
 * - Score, accuracy, and streak display
 * - FireIcon on high streaks
 * - Play Again and Home button callbacks
 * - Skipped section visibility
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { Results } from '../../src/components/Rush/Results';
import type { QueueState } from '../../src/lib/rush';

vi.mock('../../src/lib/rush', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../src/lib/rush')>();
  return {
    ...actual,
    calculateRank: (score: number) => ({
      rank: score >= 500 ? 'S' : score >= 300 ? 'A' : 'B',
      title: score >= 500 ? 'Legend' : score >= 300 ? 'Expert' : 'Skilled',
      minScore: 0,
      color: '#000',
    }),
    formatDetailedTime: (ms: number) => `${Math.floor(ms / 1000)}s`,
  };
});

function makeQueueState(overrides: Partial<QueueState> = {}): QueueState {
  return {
    current: null,
    upcoming: [],
    completed: [],
    totalAvailable: 10,
    currentIndex: 0,
    isExhausted: false,
    correctCount: 8,
    skippedCount: 0,
    completedCount: 10,
    ...overrides,
  };
}

describe('Results', () => {
  const baseProps = {
    score: 500,
    longestStreak: 5,
    isPerfect: false,
    timedOut: true,
    totalTimeMs: 180000,
    queueState: makeQueueState(),
  };

  it('renders "Time\'s Up!" when timedOut', () => {
    const { getByText } = render(<Results {...baseProps} timedOut />);
    expect(getByText("Time's Up!")).toBeTruthy();
  });

  it('renders "Rush Complete!" when not timedOut', () => {
    const { getByText } = render(
      <Results {...baseProps} timedOut={false} />
    );
    expect(getByText('Rush Complete!')).toBeTruthy();
  });

  it('renders score value', () => {
    const { getByText } = render(<Results {...baseProps} score={500} />);
    expect(getByText('500')).toBeTruthy();
  });

  it('renders accuracy percentage', () => {
    const { getByText } = render(
      <Results {...baseProps} queueState={makeQueueState({ correctCount: 8, completedCount: 10 })} />
    );
    expect(getByText('80%')).toBeTruthy();
  });

  it('renders streak with FireIcon when >= 3', () => {
    const { container, getByText } = render(
      <Results {...baseProps} longestStreak={5} />
    );
    expect(getByText('5')).toBeTruthy();
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('renders Play Again button and fires callback', () => {
    const onPlayAgain = vi.fn();
    const { getByText } = render(
      <Results {...baseProps} onPlayAgain={onPlayAgain} />
    );
    const button = getByText('Play Again');
    fireEvent.click(button);
    expect(onPlayAgain).toHaveBeenCalledOnce();
  });

  it('renders Home button and fires callback', () => {
    const onHome = vi.fn();
    const { getByText } = render(
      <Results {...baseProps} onHome={onHome} />
    );
    const button = getByText('Home');
    fireEvent.click(button);
    expect(onHome).toHaveBeenCalledOnce();
  });

  it('shows Skipped section when skippedCount > 0', () => {
    const { getByText } = render(
      <Results {...baseProps} queueState={makeQueueState({ skippedCount: 2 })} />
    );
    expect(getByText('Skipped')).toBeTruthy();
    expect(getByText('2')).toBeTruthy();
  });

  it('hides Skipped section when skippedCount is 0', () => {
    const { queryByText } = render(
      <Results {...baseProps} queueState={makeQueueState({ skippedCount: 0 })} />
    );
    expect(queryByText('Skipped')).toBeNull();
  });
});
