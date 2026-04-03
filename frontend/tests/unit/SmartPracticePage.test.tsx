/**
 * Unit tests for SmartPracticePage.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { SmartPracticePage } from '@/pages/SmartPracticePage';
import type { TechniqueStats } from '@/services/progressAnalytics';

// ============================================================================
// Mocks
// ============================================================================

vi.mock('@/services/progressAnalytics', () => ({
  getWeakestTechniques: vi.fn(),
}));

vi.mock('@/services/puzzleQueryService', () => ({
  getPuzzlesByTag: vi.fn(),
}));

vi.mock('@/services/sqliteService', () => ({
  init: vi.fn().mockResolvedValue(undefined),
}));

vi.mock('@/services/configService', () => ({
  tagSlugToId: vi.fn(),
}));

vi.mock('@/services/progressTracker', () => ({
  isPuzzleCompleted: vi.fn(),
}));

vi.mock('@/services/retryQueue', () => ({
  addToRetryQueue: vi.fn(),
}));

vi.mock('@/services/puzzleLoaders', () => ({
  puzzleRowToEntry: vi.fn(),
}));

vi.mock('@/services/puzzleLoader', () => ({
  fetchSGFContent: vi.fn(),
}));

// Mock PuzzleSetPlayer to avoid deep rendering
vi.mock('@/components/PuzzleSetPlayer', () => ({
  PuzzleSetPlayer: vi.fn(({ onBack, onPuzzleComplete, onAllComplete }: {
    onBack?: () => void;
    onPuzzleComplete?: (id: string, correct: boolean) => void;
    onAllComplete?: () => void;
  }) => (
    <div data-testid="puzzle-set-player">
      <button data-testid="player-back" onClick={onBack}>Back</button>
      <button data-testid="player-complete-wrong" onClick={() => onPuzzleComplete?.('p1', false)}>Wrong</button>
      <button data-testid="player-all-complete" onClick={onAllComplete}>AllDone</button>
    </div>
  )),
}));

vi.mock('@/components/Layout/PageLayout', () => ({
  PageLayout: ({ children }: { children: preact.ComponentChildren }) => <div>{children}</div>,
}));

vi.mock('@/components/shared/PageHeader', () => ({
  PageHeader: ({ title, onBack }: { title: string; onBack?: () => void }) => (
    <div>
      <h1>{title}</h1>
      {onBack && <button data-testid="back-button" onClick={onBack}>Back</button>}
    </div>
  ),
}));

vi.mock('@/components/shared/Button', () => ({
  Button: ({ children, onClick }: { children: preact.ComponentChildren; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
}));

// ============================================================================
// Helpers
// ============================================================================

import { getWeakestTechniques } from '@/services/progressAnalytics';
import { getPuzzlesByTag } from '@/services/puzzleQueryService';
import { tagSlugToId } from '@/services/configService';
import { isPuzzleCompleted } from '@/services/progressTracker';
import { puzzleRowToEntry } from '@/services/puzzleLoaders';

const mockGetWeakest = getWeakestTechniques as ReturnType<typeof vi.fn>;
const mockGetByTag = getPuzzlesByTag as ReturnType<typeof vi.fn>;
const mockTagSlugToId = tagSlugToId as ReturnType<typeof vi.fn>;
const mockIsPuzzleCompleted = isPuzzleCompleted as ReturnType<typeof vi.fn>;
const mockPuzzleRowToEntry = puzzleRowToEntry as ReturnType<typeof vi.fn>;

const makeTechStat = (slug: string, tagId: number): TechniqueStats => ({
  tagId,
  tagSlug: slug,
  tagName: slug.replace(/-/g, ' '),
  correct: 3,
  total: 10,
  accuracy: 30,
  avgTimeMs: 15000,
  trend30d: -5,
  lowData: false,
});

function setupMocksWithPuzzles() {
  const weakest = [makeTechStat('life-and-death', 1), makeTechStat('ladder', 2)];
  mockGetWeakest.mockResolvedValue(weakest);
  mockTagSlugToId.mockImplementation((slug: string) => {
    if (slug === 'life-and-death') return 1;
    if (slug === 'ladder') return 2;
    return undefined;
  });
  mockGetByTag.mockImplementation((tagId: number) => {
    if (tagId === 1) return [{ content_hash: 'aaa1', batch: '0001', level_id: 120, content_type: 1 }];
    if (tagId === 2) return [{ content_hash: 'bbb2', batch: '0001', level_id: 130, content_type: 1 }];
    return [];
  });
  mockPuzzleRowToEntry.mockImplementation((row: { content_hash: string; batch: string }) => ({
    id: row.content_hash,
    path: `sgf/${row.batch}/${row.content_hash}.sgf`,
    level: 'beginner',
    tags: [],
    sgf: '',
  }));
  mockIsPuzzleCompleted.mockReturnValue(false);
}

function setupMocksEmpty() {
  mockGetWeakest.mockResolvedValue([makeTechStat('ko', 3)]);
  mockTagSlugToId.mockReturnValue(3);
  mockGetByTag.mockReturnValue([{ content_hash: 'ccc3', batch: '0001', level_id: 110, content_type: 1 }]);
  mockPuzzleRowToEntry.mockReturnValue({
    id: 'ccc3',
    path: 'sgf/0001/ccc3.sgf',
    level: 'novice',
    tags: [],
    sgf: '',
  });
  // All puzzles already solved
  mockIsPuzzleCompleted.mockReturnValue(true);
}

// ============================================================================
// Tests
// ============================================================================

describe('SmartPracticePage', () => {
  const defaultProps = { onBack: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    mockGetWeakest.mockReturnValue(new Promise(() => {})); // never resolves
    render(<SmartPracticePage {...defaultProps} />);
    expect(screen.getByText('Analyzing your progress...')).toBeDefined();
  });

  it('renders empty state when no unsolved puzzles', async () => {
    setupMocksEmpty();
    render(<SmartPracticePage {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('All caught up!')).toBeDefined();
    });
  });

  it('renders PuzzleSetPlayer when puzzles found', async () => {
    setupMocksWithPuzzles();
    render(<SmartPracticePage {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByTestId('puzzle-set-player')).toBeDefined();
    });
  });

  it('calls onBack when back button clicked in loading state', () => {
    mockGetWeakest.mockReturnValue(new Promise(() => {}));
    render(<SmartPracticePage {...defaultProps} />);
    fireEvent.click(screen.getByTestId('back-button'));
    expect(defaultProps.onBack).toHaveBeenCalled();
  });

  it('uses techniques prop when provided', async () => {
    const techniques = ['life-and-death', 'ladder'];
    const allWeak = [makeTechStat('life-and-death', 1), makeTechStat('ladder', 2), makeTechStat('ko', 3)];
    mockGetWeakest.mockResolvedValue(allWeak);
    mockTagSlugToId.mockImplementation((slug: string) => {
      if (slug === 'life-and-death') return 1;
      if (slug === 'ladder') return 2;
      return undefined;
    });
    mockGetByTag.mockReturnValue([{ content_hash: 'xxx1', batch: '0001', level_id: 120, content_type: 1 }]);
    mockPuzzleRowToEntry.mockReturnValue({
      id: 'xxx1',
      path: 'sgf/0001/xxx1.sgf',
      level: 'beginner',
      tags: [],
      sgf: '',
    });
    mockIsPuzzleCompleted.mockReturnValue(false);

    render(<SmartPracticePage {...defaultProps} techniques={techniques} />);
    await waitFor(() => {
      expect(screen.getByTestId('puzzle-set-player')).toBeDefined();
    });
    // Should have called getWeakestTechniques(10) for filtering, not getWeakestTechniques(3)
    expect(mockGetWeakest).toHaveBeenCalledWith(10);
  });

  it('shows page title "Smart Practice"', () => {
    mockGetWeakest.mockReturnValue(new Promise(() => {}));
    render(<SmartPracticePage {...defaultProps} />);
    expect(screen.getByText('Smart Practice')).toBeDefined();
  });
});
