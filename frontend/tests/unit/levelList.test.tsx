/**
 * LevelList Component Tests
 * @module tests/unit/levelList.test
 *
 * Tests for T026: LevelList and PuzzleLoader tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { LevelList } from '@components/Level/LevelList';
import type { LevelManifest } from '@models/level';

// Mock puzzleLoader
vi.mock('@services/puzzleLoader', () => ({
  getLevels: vi.fn(),
  loadManifest: vi.fn(),
}));

import { getLevels } from '@services/puzzleLoader';

const mockGetLevels = vi.mocked(getLevels);

describe('LevelList Component', () => {
  const mockManifest: LevelManifest = {
    version: '1.0',
    generatedAt: '2026-01-20T00:00:00Z',
    levels: [
      {
        id: '2026-01-20',
        date: '2026-01-20',
        name: 'Daily Challenge - January 20',
        puzzleCount: 5,
        byDifficulty: { beginner: 2, intermediate: 2, advanced: 1 },
      },
      {
        id: '2026-01-21',
        date: '2026-01-21',
        name: 'Daily Challenge - January 21',
        puzzleCount: 4,
        byDifficulty: { beginner: 2, intermediate: 1, advanced: 1 },
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Loading state', () => {
    it('should show loading message initially', () => {
      // Use a promise that resolves after a delay (not never-resolving)
      // This allows the test to check loading state synchronously while still allowing cleanup
      mockGetLevels.mockImplementation(() => new Promise((resolve) => {
        // Auto-resolve after test assertion to prevent hanging
        setTimeout(() => resolve({ success: false, message: 'timeout' }), 50);
      }));
      render(<LevelList />);
      
      // Check loading state synchronously (before promise resolves)
      expect(screen.getByText('Loading levels...')).toBeDefined();
    });
  });

  describe('Loaded state', () => {
    it('should render level list when loaded successfully', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByText('Daily Challenges')).toBeDefined();
      });
    });

    it('should display all levels from manifest', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByText('Daily Challenge - January 20')).toBeDefined();
        expect(screen.getByText('Daily Challenge - January 21')).toBeDefined();
      });
    });

    it('should show puzzle count for each level', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByText('5 puzzles')).toBeDefined();
        expect(screen.getByText('4 puzzles')).toBeDefined();
      });
    });

    it('should show progress stats', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList completedLevelIds={['2026-01-20']} />);

      await waitFor(() => {
        expect(screen.getByText('1 / 2 levels completed')).toBeDefined();
      });
    });
  });

  describe('Unlock state', () => {
    it('should show first level as unlocked', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        const firstLevel = screen.getByText('Daily Challenge - January 20').closest('article');
        expect(firstLevel?.className).toContain('level-card--unlocked');
      });
    });

    it('should show second level as locked when first is not completed', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        const secondLevel = screen.getByText('Daily Challenge - January 21').closest('article');
        expect(secondLevel?.className).toContain('level-card--locked');
      });
    });

    it('should show second level as unlocked when first is completed', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList completedLevelIds={['2026-01-20']} />);

      await waitFor(() => {
        const secondLevel = screen.getByText('Daily Challenge - January 21').closest('article');
        expect(secondLevel?.className).toContain('level-card--unlocked');
      });
    });
  });

  describe('Error state', () => {
    it('should show error message when loading fails', async () => {
      mockGetLevels.mockResolvedValue({
        success: false,
        message: 'Network error',
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeDefined();
      });
    });

    it('should show retry button on error', async () => {
      mockGetLevels.mockResolvedValue({
        success: false,
        message: 'Failed to load',
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeDefined();
      });
    });
  });

  describe('Empty state', () => {
    it('should show empty message when no levels available', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: [],
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByText('No levels available yet.')).toBeDefined();
      });
    });
  });

  describe('Level selection', () => {
    it('should call onLevelSelect when clicking unlocked level', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      const onLevelSelect = vi.fn();
      render(<LevelList onLevelSelect={onLevelSelect} />);

      await waitFor(() => {
        expect(screen.getByText('Daily Challenge - January 20')).toBeDefined();
      });

      const firstLevel = screen.getByText('Daily Challenge - January 20').closest('article');
      firstLevel?.click();

      expect(onLevelSelect).toHaveBeenCalledWith('2026-01-20');
    });

    it('should not call onLevelSelect when clicking locked level', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      const onLevelSelect = vi.fn();
      render(<LevelList onLevelSelect={onLevelSelect} />);

      await waitFor(() => {
        expect(screen.getByText('Daily Challenge - January 21')).toBeDefined();
      });

      const secondLevel = screen.getByText('Daily Challenge - January 21').closest('article');
      secondLevel?.click();

      expect(onLevelSelect).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA label on the section', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByRole('region', { name: 'Puzzle Levels' })).toBeDefined();
      });
    });

    it('should have list role on the level grid', async () => {
      mockGetLevels.mockResolvedValue({
        success: true,
        data: mockManifest.levels,
      });

      render(<LevelList />);

      await waitFor(() => {
        expect(screen.getByRole('list')).toBeDefined();
      });
    });
  });
});
