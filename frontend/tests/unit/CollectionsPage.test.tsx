/**
 * Unit tests for CollectionsBrowsePage (redesigned).
 *
 * Tests:
 * - Catalog loading and section rendering
 * - Featured section with editorial collections
 * - Search functionality
 * - Disabled state for unavailable collections
 * - Navigation wiring
 * - Error/loading states
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/preact';
import { CollectionsBrowsePage } from '@/pages/CollectionsBrowsePage';
import * as collectionService from '@/services/collectionService';
import * as progressTracker from '@/services/progressTracker';
import * as puzzleQueryService from '@/services/puzzleQueryService';
import type { CuratedCollection, CollectionCatalog, CollectionProgressSummary } from '@/models/collection';

// ============================================================================
// Mock Data
// ============================================================================

const mockCollections: CuratedCollection[] = [
  {
    slug: 'beginner-essentials',
    name: 'Beginner Essentials',
    description: 'Curated learning path for beginner players.',
    curator: 'Curated',
    source: 'mixed',
    type: 'graded',
    tier: 'editorial',
    ordering: 'manual',
    aliases: ['beginner course'],
    puzzleCount: 50,
    hasData: true,
    levelHint: 'beginner',
  },
  {
    slug: 'elementary-essentials',
    name: 'Elementary Essentials',
    description: 'Curated learning path for elementary players.',
    curator: 'Curated',
    source: 'mixed',
    type: 'graded',
    tier: 'editorial',
    ordering: 'manual',
    aliases: [],
    puzzleCount: 40,
    hasData: true,
    levelHint: 'elementary',
  },
  {
    slug: 'capture-problems',
    name: 'Capture Problems',
    description: 'Practice capturing stones.',
    curator: 'Curated',
    source: 'mixed',
    type: 'technique',
    tier: 'editorial',
    ordering: 'source',
    aliases: [],
    puzzleCount: 30,
    hasData: true,
  },
  {
    slug: 'life-death-basics',
    name: 'Life & Death Basics',
    description: 'Essential life and death patterns.',
    curator: 'Curated',
    source: 'mixed',
    type: 'technique',
    tier: 'curated',
    ordering: 'source',
    aliases: [],
    puzzleCount: 25,
    hasData: true,
  },
  {
    slug: 'cho-chikun-life-death',
    name: 'Cho Chikun Life & Death',
    description: 'Classic life-and-death problems by Cho Chikun.',
    curator: 'Cho Chikun',
    source: 'kisvadim',
    type: 'author',
    tier: 'editorial',
    ordering: 'source',
    aliases: [],
    puzzleCount: 60,
    hasData: true,
  },
  {
    slug: 'hashimoto-problems',
    name: 'Hashimoto Problems',
    description: 'Problems by Hashimoto sensei.',
    curator: 'Hashimoto',
    source: 'kisvadim',
    type: 'author',
    tier: 'premier',
    ordering: 'source',
    aliases: [],
    puzzleCount: 45,
    hasData: true,
  },
];

const mockCatalog: CollectionCatalog = {
  collections: mockCollections,
  byType: {
    graded: [mockCollections[0], mockCollections[1]],
    technique: [mockCollections[2], mockCollections[3]],
    author: [mockCollections[4], mockCollections[5]],
    reference: [],
    system: [],
  },
};

const mockProgress: CollectionProgressSummary[] = [
  {
    collectionId: 'beginner-essentials',
    status: 'in-progress',
    completedCount: 10,
    totalPuzzles: 50,
    percentComplete: 20,
    lastActivity: '2026-02-10T10:00:00Z',
  },
];

// ============================================================================
// Setup
// ============================================================================

vi.mock('@/services/collectionService', () => ({
  loadCollectionCatalog: vi.fn(),
  getFeaturedCollections: vi.fn(),
  searchCollectionCatalog: vi.fn(),
}));

vi.mock('@/services/progressTracker', () => ({
  getAllCollectionProgress: vi.fn(),
}));

vi.mock('@/services/puzzleQueryService', () => ({
  searchCollectionsByTypes: vi.fn(),
}));

describe('CollectionsBrowsePage', () => {
  const mockNavigateToCollection = vi.fn();
  const mockNavigateHome = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    (collectionService.loadCollectionCatalog as Mock).mockResolvedValue({
      success: true,
      data: mockCatalog,
    });

    (collectionService.getFeaturedCollections as Mock).mockReturnValue([
      mockCollections[0],
      mockCollections[2],
    ]);

    (collectionService.searchCollectionCatalog as Mock).mockReturnValue(mockCollections);

    (progressTracker.getAllCollectionProgress as Mock).mockReturnValue({
      success: true,
      data: mockProgress,
    });

    (puzzleQueryService.searchCollectionsByTypes as Mock).mockReturnValue([]);
  });

  // ==========================================================================
  // Rendering Tests
  // ==========================================================================

  it('renders page title', async () => {
    const { getByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByText('Collections')).toBeTruthy();
    });
  });

  it('renders featured section', async () => {
    const { getByTestId } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('section-featured')).toBeTruthy();
    });
  });

  it('renders category sections', async () => {
    const { getByTestId } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('section-learning-paths')).toBeTruthy();
      expect(getByTestId('section-practice')).toBeTruthy();
      expect(getByTestId('section-books')).toBeTruthy();
    });
  });

  it('renders collection cards with names', async () => {
    const { getAllByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getAllByText('Beginner Essentials').length).toBeGreaterThan(0);
      expect(getAllByText('Capture Problems').length).toBeGreaterThan(0);
    });
  });

  it('renders progress on available collections', async () => {
    const { getAllByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getAllByText('10 of 50 solved').length).toBeGreaterThan(0);
    });
  });

  it('renders stats bar with total and available counts', async () => {
    const { getByTestId } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      const stats = getByTestId('page-stats');
      expect(stats).toBeTruthy();
      expect(stats.textContent).toContain('6');
    });
  });

  it('shows search input', async () => {
    const { getByTestId } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByTestId('collections-search')).toBeTruthy();
    });
  });

  // ==========================================================================
  // Filtering Tests
  // ==========================================================================

  it('filters out collections with fewer than 15 puzzles', async () => {
    // Create a catalog with a small collection that should be hidden
    const smallCollection: CuratedCollection = {
      slug: 'tiny-set',
      name: 'Tiny Set',
      description: 'Very small set.',
      curator: 'Curated',
      source: 'mixed',
      type: 'technique',
      tier: 'curated',
      ordering: 'source',
      aliases: [],
      puzzleCount: 5,
      hasData: true,
    };
    const catalogWithSmall: CollectionCatalog = {
      ...mockCatalog,
      collections: [...mockCollections, smallCollection],
      byType: {
        ...mockCatalog.byType,
        technique: [...mockCatalog.byType.technique, smallCollection],
      },
    };
    (collectionService.loadCollectionCatalog as Mock).mockResolvedValue({
      success: true,
      data: catalogWithSmall,
    });

    const { queryByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(queryByText('Tiny Set')).toBeNull();
    });
  });

  // ==========================================================================
  // Error & Loading State Tests
  // ==========================================================================

  it('shows error state on load failure', async () => {
    (collectionService.loadCollectionCatalog as Mock).mockResolvedValue({
      success: false,
      message: 'Network error',
    });

    const { getByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByText('Network error')).toBeTruthy();
    });
  });

  it('shows loading state initially', () => {
    (collectionService.loadCollectionCatalog as Mock).mockReturnValue(
      new Promise(() => {})
    );

    const { getByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    expect(getByText('Loading collections...')).toBeTruthy();
  });

  // ==========================================================================
  // Navigation Tests
  // ==========================================================================

  it('navigates to collection when available card clicked', async () => {
    const { getAllByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getAllByText('Beginner Essentials').length).toBeGreaterThan(0);
    });

    fireEvent.click(getAllByText('Beginner Essentials')[0]);

    expect(mockNavigateToCollection).toHaveBeenCalledWith('beginner-essentials');
  });

  it('navigates home when back button clicked', async () => {
    const { getByText } = render(
      <CollectionsBrowsePage
        onNavigateToCollection={mockNavigateToCollection}
        onNavigateHome={mockNavigateHome}
      />
    );

    await waitFor(() => {
      expect(getByText('Back')).toBeTruthy();
    });

    fireEvent.click(getByText('Back'));

    expect(mockNavigateHome).toHaveBeenCalledOnce();
  });
});
