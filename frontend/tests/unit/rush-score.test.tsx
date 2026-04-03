/**
 * Rush Score component tests.
 *
 * Verifies:
 * - Score renders total score value
 * - Streak display with FireIcon threshold (≥3)
 * - CompactScore rendering
 * - Breakdown items when showBreakdown is true
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { Score, CompactScore } from '../../src/components/Rush/Score';
import type { ScoringState, PuzzleScore } from '../../src/lib/rush';

function makeScoringState(overrides: Partial<ScoringState> = {}): ScoringState {
  return {
    totalScore: 100,
    currentStreak: 0,
    longestStreak: 0,
    isPerfect: false,
    puzzleCount: 0,
    history: [],
    ...overrides,
  };
}

describe('Score', () => {
  it('renders total score value', () => {
    const state = makeScoringState({ totalScore: 250 });
    const { getByText } = render(<Score state={state} />);
    expect(getByText('250')).toBeTruthy();
  });

  it('renders Score label', () => {
    const state = makeScoringState();
    const { getByText } = render(<Score state={state} />);
    expect(getByText('Score')).toBeTruthy();
  });

  it('renders Streak label', () => {
    const state = makeScoringState({ currentStreak: 5 });
    const { getByText } = render(<Score state={state} />);
    expect(getByText('Streak')).toBeTruthy();
  });

  it('renders streak value', () => {
    const state = makeScoringState({ currentStreak: 7 });
    const { container } = render(<Score state={state} />);
    expect(container.textContent).toContain('7');
  });

  it('shows FireIcon when streak >= 3', () => {
    const state = makeScoringState({ currentStreak: 3 });
    const { container } = render(<Score state={state} />);
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('hides FireIcon when streak < 3', () => {
    const state = makeScoringState({ currentStreak: 2 });
    const { container } = render(<Score state={state} />);
    const streakSection = container.querySelector('.rush-score__streak');
    const svgs = streakSection?.querySelectorAll('svg') ?? [];
    expect(svgs.length).toBe(0);
  });

  it('renders breakdown when showBreakdown and lastScore', () => {
    const state = makeScoringState({ totalScore: 150 });
    const lastScore: PuzzleScore = {
      basePoints: 100,
      timeBonus: 25,
      streakBonus: 10,
      skipPenalty: 0,
      total: 135,
    };
    const { getByText } = render(
      <Score state={state} lastScore={lastScore} showBreakdown />
    );
    expect(getByText('+100')).toBeTruthy();
    expect(getByText('+25 time')).toBeTruthy();
    expect(getByText('+10 streak')).toBeTruthy();
  });
});

describe('CompactScore', () => {
  it('renders score value', () => {
    const { getByText } = render(<CompactScore score={150} streak={0} />);
    expect(getByText('150')).toBeTruthy();
  });

  it('shows streak multiplier when > 0', () => {
    const { container } = render(<CompactScore score={200} streak={5} />);
    expect(container.textContent).toContain('x5');
  });

  it('shows FireIcon at streak >= 3', () => {
    const { container } = render(<CompactScore score={200} streak={3} />);
    const svgs = container.querySelectorAll('svg');
    expect(svgs.length).toBeGreaterThan(0);
  });

  it('hides streak when 0', () => {
    const { container } = render(<CompactScore score={100} streak={0} />);
    expect(container.textContent).not.toContain('x0');
  });
});
