/**
 * Unit tests for TrainingBrowsePage (T085).
 *
 * Tests:
 * - Level card rendering with PuzzleCollectionCard
 * - Category filtering
 * - Combined filtering
 * - Empty results state
 * - Navigation to training levels
 * - Hero section rendering
 * - Disabled state for empty levels
 * - Progress display from localStorage
 *
 * Spec 129, Phase 9 â€” FR-028
 * Updated: Standardized to PuzzleCollectionCard
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/preact';
import { TrainingBrowsePage } from '@/pages/TrainingBrowsePage';

// ============================================================================
// Mock SQLite service and puzzle query service
// ============================================================================

const MOCK_LEVEL_COUNTS: Record<number, number> = {
  110: 10,   // novice
  120: 1035, // beginner
  130: 38,   // elementary
  140: 0,    // intermediate
  150: 0,    // upper-intermediate
  160: 0,    // advanced
  210: 0,    // low-dan
  220: 0,    // high-dan
  230: 0,    // expert
};

vi.mock('@/services/sqliteService', () => ({
  init: () => Promise.resolve(),
}));

vi.mock('@/services/puzzleQueryService', () => ({
  getLevelCounts: () => MOCK_LEVEL_COUNTS,
  getTagCounts: () => ({}),
  getFilterCounts: () => ({ levels: {}, tags: {}, collections: {}, depthPresets: {} }),
}));

// ============================================================================
// Mock localStorage
// ============================================================================

const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
    removeItem: (key: string) => {
      delete store[key];
    },
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// ============================================================================
// Tests
// ============================================================================

describe('TrainingBrowsePage', () => {
  const mockSelectLevel = vi.fn();
  const mockNavigateHome = vi.fn();
  const mockNavigateRandom = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockLocalStorage.clear();
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  it('renders hero title with page heading', async () => {
    const { getByText } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByText('Training')).toBeTruthy();
    });
  });

  it('renders all 9 skill levels as cards', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      // Check that level cards exist
      expect(getByTestId('training-level-novice')).toBeTruthy();
      expect(getByTestId('training-level-beginner')).toBeTruthy();
      expect(getByTestId('training-level-elementary')).toBeTruthy();
      expect(getByTestId('training-level-intermediate')).toBeTruthy();
      expect(getByTestId('training-level-upper-intermediate')).toBeTruthy();
      expect(getByTestId('training-level-advanced')).toBeTruthy();
      expect(getByTestId('training-level-low-dan')).toBeTruthy();
      expect(getByTestId('training-level-high-dan')).toBeTruthy();
      expect(getByTestId('training-level-expert')).toBeTruthy();
    });
  });

  it('renders filter bar with category options', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-filter-all')).toBeTruthy();
      expect(getByTestId('training-filter-beginner')).toBeTruthy();
      expect(getByTestId('training-filter-intermediate')).toBeTruthy();
      expect(getByTestId('training-filter-advanced')).toBeTruthy();
    });
  });

  it('renders stats badges with level count', async () => {
    const { container } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      // Stats badges show "9 Levels" in the hero section
      expect(container.textContent).toContain('9 Levels');
    });
  });

  // ==========================================================================
  // Filter Tests
  // ==========================================================================

  it('filters to beginner levels when Beginner selected', async () => {
    const { getByTestId, queryByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-filter-beginner')).toBeTruthy();
    });

    fireEvent.click(getByTestId('training-filter-beginner'));

    await waitFor(() => {
      // Should show beginner levels
      expect(getByTestId('training-level-novice')).toBeTruthy();
      expect(getByTestId('training-level-beginner')).toBeTruthy();
      expect(getByTestId('training-level-elementary')).toBeTruthy();
      // Should NOT show advanced levels
      expect(queryByTestId('training-level-low-dan')).toBeNull();
      expect(queryByTestId('training-level-expert')).toBeNull();
    });
  });

  it('filters to advanced levels when Advanced selected', async () => {
    const { getByTestId, queryByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-filter-advanced')).toBeTruthy();
    });

    fireEvent.click(getByTestId('training-filter-advanced'));

    await waitFor(() => {
      // "Advanced (1d+)" category includes dan-level levels: low-dan, high-dan, expert
      // Note: 'advanced' level slug (5kâ€“1k) is kyu-level â†’ falls in 'intermediate' category
      expect(getByTestId('training-level-low-dan')).toBeTruthy();
      expect(getByTestId('training-level-high-dan')).toBeTruthy();
      expect(getByTestId('training-level-expert')).toBeTruthy();
      // Should NOT show beginner levels
      expect(queryByTestId('training-level-novice')).toBeNull();
      expect(queryByTestId('training-level-beginner')).toBeNull();
    });
  });

  it('shows all levels when All Levels selected', async () => {
    const { getByTestId, container } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    // First filter to advanced only
    await waitFor(() => {
      expect(getByTestId('training-filter-advanced')).toBeTruthy();
    });
    fireEvent.click(getByTestId('training-filter-advanced'));

    // Then click All Levels
    await waitFor(() => {
      expect(getByTestId('training-filter-all')).toBeTruthy();
    });
    fireEvent.click(getByTestId('training-filter-all'));

    await waitFor(() => {
      // Should show all 9 levels again
      const cards = container.querySelectorAll('[data-testid^="training-level-"]');
      expect(cards.length).toBe(9);
    });
  });

  // ==========================================================================
  // Navigation Tests
  // ==========================================================================

  it('calls onSelectLevel when level card clicked', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-level-novice')).toBeTruthy();
    });

    fireEvent.click(getByTestId('training-level-novice'));

    expect(mockSelectLevel).toHaveBeenCalledWith('novice');
  });

  it('navigates home when back button clicked', async () => {
    const { getByText } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByText('Back')).toBeTruthy();
    });

    fireEvent.click(getByText('Back'));

    expect(mockNavigateHome).toHaveBeenCalledOnce();
  });

  it('levels with puzzles are clickable, empty levels are disabled', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-level-novice')).toBeTruthy();
    });

    // Novice has 10 puzzles â€” should be clickable
    fireEvent.click(getByTestId('training-level-novice'));
    expect(mockSelectLevel).toHaveBeenCalledWith('novice');

    // Expert has 0 puzzles â€” should be disabled (aria-disabled)
    const expertCard = getByTestId('training-level-expert');
    expect(expertCard.getAttribute('aria-disabled')).toBe('true');
  });

  // ==========================================================================
  // Progress Display Tests
  // ==========================================================================

  it('shows progress from localStorage using shared ProgressBar', async () => {
    // Set some progress data
    mockLocalStorage.setItem(
      'yen-go-training-progress',
      JSON.stringify({
        byLevel: {
          novice: { completed: 5, total: 10, accuracy: 80 },
        },
        unlockedLevels: ['novice', 'beginner'],
      }),
    );

    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      const noviceCard = getByTestId('training-level-novice');
      // PuzzleCollectionCard uses shared ProgressBar which shows "X of Y solved"
      expect(noviceCard.textContent).toContain('5 of 10 solved');
    });
  });

  // ==========================================================================
  // Random Challenge Button Tests
  // ==========================================================================

  it('renders Random Challenge button when onNavigateRandom provided', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
        onNavigateRandom={mockNavigateRandom}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-random-challenge')).toBeTruthy();
    });
  });

  it('calls onNavigateRandom when Random Challenge button clicked', async () => {
    const { getByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
        onNavigateRandom={mockNavigateRandom}
      />
    );

    await waitFor(() => {
      expect(getByTestId('training-random-challenge')).toBeTruthy();
    });

    fireEvent.click(getByTestId('training-random-challenge'));
    expect(mockNavigateRandom).toHaveBeenCalledOnce();
  });

  it('does not render Random Challenge button when onNavigateRandom not provided', async () => {
    const { queryByTestId } = render(
      <TrainingBrowsePage
        onSelectLevel={mockSelectLevel}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(queryByTestId('training-random-challenge')).toBeNull();
    });
  });
});
