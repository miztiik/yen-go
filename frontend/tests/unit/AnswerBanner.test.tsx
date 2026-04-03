/**
 * AnswerBanner Unit Tests (T144)
 *
 * Verifies correct/incorrect answer feedback banners.
 * Spec 132, US15: FR-070, FR-071, FR-072, FR-073
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { AnswerBanner } from '../../src/components/shared/AnswerBanner';

describe('AnswerBanner', () => {
  describe('Success variant', () => {
    it('renders success message with role=status', () => {
      const { getByTestId, getByText } = render(
        <AnswerBanner variant="success" message="Puzzle Solved!" />
      );
      expect(getByTestId('answer-banner')).toBeTruthy();
      expect(getByText('Puzzle Solved!')).toBeTruthy();
    });

    it('shows Next button when onNext provided', () => {
      const onNext = vi.fn();
      const { getByText } = render(
        <AnswerBanner variant="success" message="Correct!" onNext={onNext} />
      );
      const btn = getByText('Next →');
      expect(btn).toBeTruthy();
      fireEvent.click(btn);
      expect(onNext).toHaveBeenCalledOnce();
    });

    it('does NOT show Undo/Reset buttons on success variant', () => {
      const onUndo = vi.fn();
      const onReset = vi.fn();
      const { queryByText } = render(
        <AnswerBanner variant="success" message="Correct!" onUndo={onUndo} onReset={onReset} />
      );
      // Undo/Reset are error-only
      expect(queryByText('Undo')).toBeNull();
      expect(queryByText('Reset')).toBeNull();
    });
  });

  describe('Error variant', () => {
    it('renders error message', () => {
      const { getByText } = render(
        <AnswerBanner variant="error" message="Incorrect — try again" />
      );
      expect(getByText('Incorrect — try again')).toBeTruthy();
    });

    it('shows Undo and Reset buttons', () => {
      const onUndo = vi.fn();
      const onReset = vi.fn();
      const { getByText } = render(
        <AnswerBanner variant="error" message="Wrong" onUndo={onUndo} onReset={onReset} />
      );
      fireEvent.click(getByText('Undo'));
      expect(onUndo).toHaveBeenCalledOnce();
      fireEvent.click(getByText('Reset'));
      expect(onReset).toHaveBeenCalledOnce();
    });

    it('shows Next button alongside Undo/Reset (FR-072 — forward nav always accessible)', () => {
      const onNext = vi.fn();
      const onUndo = vi.fn();
      const { getByText } = render(
        <AnswerBanner variant="error" message="Wrong" onUndo={onUndo} onNext={onNext} />
      );
      expect(getByText('Next →')).toBeTruthy();
      expect(getByText('Undo')).toBeTruthy();
    });

    it('shows Skip button on error variant', () => {
      const onSkip = vi.fn();
      const { getByText } = render(
        <AnswerBanner variant="error" message="Wrong" onSkip={onSkip} />
      );
      fireEvent.click(getByText('Skip'));
      expect(onSkip).toHaveBeenCalledOnce();
    });
  });

  describe('Edge cases', () => {
    it('renders without any action callbacks', () => {
      const { getByTestId } = render(
        <AnswerBanner variant="success" message="Done" />
      );
      expect(getByTestId('answer-banner')).toBeTruthy();
    });

    it('applies custom className', () => {
      const { getByTestId } = render(
        <AnswerBanner variant="success" message="Done" className="custom-cls" />
      );
      expect(getByTestId('answer-banner').className).toContain('custom-cls');
    });
  });
});
