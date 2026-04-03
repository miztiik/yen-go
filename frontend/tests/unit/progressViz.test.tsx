/**
 * Progress Visualization Tests (T105)
 *
 * Tests:
 * - StreakBadge rendering + pulse animation
 * - PuzzleCollectionCard completion badges
 * - PuzzleCarousel dot indicator statuses
 * - Collection progress bar percentage
 *
 * Spec 129 — FR-028
 */

import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/preact';
import { StreakBadge } from '../../src/components/Streak/StreakDisplay';
import { PuzzleCollectionCard } from '../../src/components/shared/PuzzleCollectionCard';
import { PuzzleCarousel } from '../../src/components/PuzzleNavigation/PuzzleCarousel';
import type { PuzzleIndicator } from '../../src/components/PuzzleNavigation/PuzzleCarousel';

describe('StreakBadge', () => {
  it('should render lightning bolt icon and streak count when streak > 0', () => {
    const { container } = render(<StreakBadge streak={5} />);
    expect(container.textContent).toContain('5');
    // Lightning bolt is rendered as an SVG icon, not an emoji
    const svg = container.querySelector('svg');
    expect(svg).toBeTruthy();
  });

  it('should be hidden when streak is 0', () => {
    const { container } = render(<StreakBadge streak={0} />);
    const span = container.querySelector('span');
    expect(span?.style.display).toBe('none');
  });

  it('should have aria-label with streak count', () => {
    const { container } = render(<StreakBadge streak={7} />);
    const span = container.querySelector('[aria-label]');
    expect(span?.getAttribute('aria-label')).toBe('7 day streak');
  });
});

describe('PuzzleCollectionCard — completion badges', () => {
  it('should display completion count', () => {
    const { container } = render(
      <PuzzleCollectionCard
        title="Life & Death"
        progress={{ completed: 3, total: 10 }}
      />,
    );
    expect(container.textContent).toContain('3 of 10 solved');
  });

  it('should render mastery badge with correct label', () => {
    const { container } = render(
      <PuzzleCollectionCard
        title="Ladder Techniques"
        mastery="proficient"
      />,
    );
    expect(container.textContent).toContain('Proficient');
  });

  it('should render progress bar', () => {
    const { container } = render(
      <PuzzleCollectionCard
        title="Ko Fights"
        progress={{ completed: 7, total: 10 }}
      />,
    );
    // Progress bar element
    const progressBar = container.querySelector('[style*="width"]');
    expect(progressBar).toBeTruthy();
  });

  it('should show "Ready to begin" when total is 0', () => {
    const { container } = render(
      <PuzzleCollectionCard
        title="New Collection"
        progress={{ completed: 0, total: 0 }}
      />,
    );
    expect(container.textContent).toContain('Ready to begin');
  });
});

describe('PuzzleCarousel — dot indicators', () => {
  const indicators: PuzzleIndicator[] = [
    { index: 0, id: 'p1', status: 'correct' },
    { index: 1, id: 'p2', status: 'incorrect' },
    { index: 2, id: 'p3', status: 'current' },
    { index: 3, id: 'p4', status: 'unsolved' },
  ];

  it('should render all puzzle indicators', () => {
    const { container } = render(
      <PuzzleCarousel
        puzzles={indicators}
        currentIndex={2}
        onPuzzleClick={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBe(4);
  });

  it('should show ✓ for correct puzzles', () => {
    const { container } = render(
      <PuzzleCarousel
        puzzles={indicators}
        currentIndex={2}
        onPuzzleClick={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons[0]?.textContent).toBe('✓');
  });

  it('should show ✗ for incorrect puzzles', () => {
    const { container } = render(
      <PuzzleCarousel
        puzzles={indicators}
        currentIndex={2}
        onPuzzleClick={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons[1]?.textContent).toBe('✗');
  });

  it('should show puzzle number for current puzzle', () => {
    const { container } = render(
      <PuzzleCarousel
        puzzles={indicators}
        currentIndex={2}
        onPuzzleClick={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons[2]?.textContent).toBe('3');
  });

  it('should have aria-labels on each indicator', () => {
    const { container } = render(
      <PuzzleCarousel
        puzzles={indicators}
        currentIndex={2}
        onPuzzleClick={vi.fn()}
      />,
    );
    const buttons = container.querySelectorAll('button');
    expect(buttons[0]?.getAttribute('aria-label')).toContain('correct');
    expect(buttons[1]?.getAttribute('aria-label')).toContain('incorrect');
    expect(buttons[2]?.getAttribute('aria-label')).toContain('current');
    expect(buttons[3]?.getAttribute('aria-label')).toContain('unsolved');
  });
});
