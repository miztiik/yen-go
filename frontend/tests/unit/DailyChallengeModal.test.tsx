/**
 * DailyChallengeModal Component Tests
 * @module tests/unit/DailyChallengeModal.test
 *
 * Tests for DailyChallengeModal v2.0 timed sets selection (T115).
 * @jsxImportSource preact
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, waitFor, cleanup } from '@testing-library/preact';
import { DailyChallengeModal } from '../../src/components/DailyChallenge/DailyChallengeModal';
import * as dailyChallengeService from '../../src/services/dailyChallengeService';
import * as progressTracker from '../../src/services/progressTracker';
import type { DailyIndex } from '../../src/types/indexes';

// ============================================================================
// Test Data Fixtures
// ============================================================================

/** v1.0 format challenge (single timed queue) */
const v1Challenge: DailyIndex = {
  indexVersion: '1.0',
  date: '2026-01-28',
  generatedAt: '2026-01-28T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'std-1', level: 'beginner', path: 'sgf/beginner/std-1.sgf' },
      { id: 'std-2', level: 'beginner', path: 'sgf/beginner/std-2.sgf' },
    ],
    total: 2,
  },
  timed: {
    queue: [
      { id: 'timed-1', level: 'beginner', path: 'sgf/beginner/timed-1.sgf' },
    ],
    queue_size: 1,
    suggested_durations: [180],
    scoring: { beginner: 10, basic: 15, intermediate: 25, advanced: 40, expert: 60 },
  },
};

/** v2.0 format challenge (multiple timed sets) */
const v2Challenge: DailyIndex = {
  version: '2.0',
  date: '2026-01-28',
  generated_at: '2026-01-28T00:00:00Z',
  standard: {
    puzzles: [
      { id: 'std-1', level: 'beginner', path: 'sgf/beginner/std-1.sgf' },
      { id: 'std-2', level: 'beginner', path: 'sgf/beginner/std-2.sgf' },
    ],
    total: 2,
    technique_of_day: 'snapback',
    distribution: { beginner: 2 },
  },
  timed: {
    sets: [
      {
        set_number: 1,
        puzzles: [
          { id: 'set1-1', level: 'beginner', path: 'sgf/beginner/set1-1.sgf' },
          { id: 'set1-2', level: 'beginner', path: 'sgf/beginner/set1-2.sgf' },
        ],
      },
      {
        set_number: 2,
        puzzles: [
          { id: 'set2-1', level: 'intermediate', path: 'sgf/intermediate/set2-1.sgf' },
          { id: 'set2-2', level: 'intermediate', path: 'sgf/intermediate/set2-2.sgf' },
          { id: 'set2-3', level: 'intermediate', path: 'sgf/intermediate/set2-3.sgf' },
        ],
      },
      {
        set_number: 3,
        puzzles: [
          { id: 'set3-1', level: 'advanced', path: 'sgf/advanced/set3-1.sgf' },
        ],
      },
    ],
    set_count: 3,
    puzzles_per_set: 2, // Average or nominal
    suggested_durations: [180, 300, 600],
    scoring: { beginner: 10, basic: 15, intermediate: 25, advanced: 40, expert: 60 },
  },
  by_tag: {
    ladder: {
      puzzles: [{ id: 'ladder-1', level: 'beginner', path: 'sgf/beginner/ladder-1.sgf' }],
      total: 1,
    },
  },
};

// ============================================================================
// Tests
// ============================================================================

describe('DailyChallengeModal', () => {
  const mockOnClose = vi.fn();
  const mockOnStartChallenge = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock progress tracker to return no progress
    vi.spyOn(progressTracker, 'getDailyProgress').mockReturnValue({
      success: true,
      data: null,
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe('v1.0 format', () => {
    beforeEach(() => {
      vi.spyOn(dailyChallengeService, 'getTodaysChallenge').mockResolvedValue({
        success: true,
        data: v1Challenge,
      });
    });

    it('should show standard and timed buttons for v1 format', async () => {
      const { getByText, queryByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Standard')).toBeTruthy();
        expect(getByText('Timed')).toBeTruthy();
        // Should NOT show "Timed Sets" section for v1
        expect(queryByText('Timed Sets')).toBeNull();
      });
    });

    it('should call onStartChallenge with mode and date for standard', async () => {
      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Standard')).toBeTruthy();
      });

      fireEvent.click(getByText('Standard'));

      expect(mockOnStartChallenge).toHaveBeenCalledWith('standard', '2026-01-28');
      expect(mockOnStartChallenge).toHaveBeenCalledTimes(1);
    });

    it('should call onStartChallenge with mode and date for timed (no set number)', async () => {
      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Timed')).toBeTruthy();
      });

      fireEvent.click(getByText('Timed'));

      expect(mockOnStartChallenge).toHaveBeenCalledWith('timed', '2026-01-28');
      expect(mockOnStartChallenge).toHaveBeenCalledTimes(1);
    });
  });

  describe('v2.0 format', () => {
    beforeEach(() => {
      vi.spyOn(dailyChallengeService, 'getTodaysChallenge').mockResolvedValue({
        success: true,
        data: v2Challenge,
      });
    });

    it('should show standard button and timed sets selection for v2 format', async () => {
      const { getByText, queryByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Standard')).toBeTruthy();
        // Should show timed sets section for v2
        expect(getByText('⏱️ Timed Sets')).toBeTruthy();
        // Should NOT show single "Timed" button
        expect(queryByText(/^Timed$/)).toBeNull();
      });
    });

    it('should display all timed sets with puzzle counts', async () => {
      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Set 1')).toBeTruthy();
        expect(getByText('2 puzzles')).toBeTruthy(); // Set 1 has 2 puzzles
        expect(getByText('Set 2')).toBeTruthy();
        expect(getByText('3 puzzles')).toBeTruthy(); // Set 2 has 3 puzzles
        expect(getByText('Set 3')).toBeTruthy();
        expect(getByText('1 puzzles')).toBeTruthy(); // Set 3 has 1 puzzle
      });
    });

    it('should call onStartChallenge with set number when selecting timed set', async () => {
      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Set 2')).toBeTruthy();
      });

      // Click on Set 2
      fireEvent.click(getByText('Set 2'));

      expect(mockOnStartChallenge).toHaveBeenCalledWith('timed', '2026-01-28', 2);
      expect(mockOnStartChallenge).toHaveBeenCalledTimes(1);
    });

    it('should call onStartChallenge without set number for standard mode in v2', async () => {
      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        expect(getByText('Standard')).toBeTruthy();
      });

      fireEvent.click(getByText('Standard'));

      expect(mockOnStartChallenge).toHaveBeenCalledWith('standard', '2026-01-28');
      expect(mockOnStartChallenge).toHaveBeenCalledTimes(1);
    });
  });

  describe('loading and error states', () => {
    it('should show loading state initially', () => {
      // Use a promise that resolves after a delay (not never-resolving)
      // This allows the test to check loading state synchronously while still allowing cleanup
      let resolvePromise: (value: unknown) => void;
      vi.spyOn(dailyChallengeService, 'getTodaysChallenge').mockImplementation(
        () => new Promise((resolve) => { 
          resolvePromise = resolve;
          // Auto-resolve after test assertions to prevent hanging
          setTimeout(() => resolve({ success: false, message: 'timeout' }), 50);
        })
      );

      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      // Check loading state synchronously (before promise resolves)
      expect(getByText('Loading...')).toBeTruthy();
    });

    it('should show error state when challenge fails to load', async () => {
      vi.spyOn(dailyChallengeService, 'getTodaysChallenge').mockResolvedValue({
        success: false,
        message: 'Network error',
      });

      const { getByText } = render(
        <DailyChallengeModal
          isOpen={true}
          onClose={mockOnClose}
          onStartChallenge={mockOnStartChallenge}
        />
      );

      await waitFor(() => {
        // Component shows "Coming Soon" for unavailable challenges
        // Note: Actual error message is not displayed in the UI - it's a graceful fallback
        expect(getByText('Coming Soon')).toBeTruthy();
        // The component shows a generic message about puzzle masters
        expect(getByText(/puzzle masters.*hard at work/i)).toBeTruthy();
      });
    });
  });
});
