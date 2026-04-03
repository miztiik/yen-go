/**
 * Comment Panel Tests
 * @module tests/unit/comment-panel.test.ts
 *
 * Unit tests for CommentPanel component.
 * Covers: T025-T028 (comments display)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { CommentPanel, EmptyCommentPanel } from '../../src/components/SolutionTree';

// ============================================================================
// Tests
// ============================================================================

describe('CommentPanel', () => {
  describe('FR-012: Basic Comment Display', () => {
    it('should render comment text', () => {
      render(<CommentPanel comment="This is a test comment." />);

      expect(screen.getByText(/This is a test comment/)).toBeTruthy();
    });

    it('should have accessible heading', () => {
      render(<CommentPanel comment="Test comment" />);

      const heading = screen.getByRole('heading', { name: /comment/i });
      expect(heading).toBeTruthy();
    });

    it('should use semantic region role', () => {
      render(<CommentPanel comment="Test comment" />);

      const region = screen.getByRole('region');
      expect(region).toBeTruthy();
    });
  });

  describe('FR-013: Correct/Wrong Indicators', () => {
    it('should show correct indicator when isCorrect is true', () => {
      render(<CommentPanel comment="Good move!" isCorrect={true} />);

      expect(screen.getByText('✓')).toBeTruthy();
    });

    it('should show wrong indicator when isCorrect is false', () => {
      render(<CommentPanel comment="Try again" isCorrect={false} />);

      expect(screen.getByText('✗')).toBeTruthy();
    });

    it('should not show indicator when isCorrect is undefined', () => {
      render(<CommentPanel comment="Neutral comment" />);

      expect(screen.queryByText('✓')).toBeNull();
      expect(screen.queryByText('✗')).toBeNull();
    });
  });

  describe('FR-014: Line Break Preservation', () => {
    it('should preserve line breaks in comments', () => {
      render(<CommentPanel comment={'Line 1\nLine 2\nLine 3'} />);

      // Check that each line is rendered
      expect(screen.getByText(/Line 1/)).toBeTruthy();
      expect(screen.getByText(/Line 2/)).toBeTruthy();
      expect(screen.getByText(/Line 3/)).toBeTruthy();
    });
  });

  describe('FR-015: Empty State', () => {
    it('should show empty state when no comment', () => {
      render(<EmptyCommentPanel />);

      expect(screen.getByText(/no comment/i)).toBeTruthy();
    });

    it('should accept custom message', () => {
      render(<EmptyCommentPanel message="Select a node" />);

      expect(screen.getByText('Select a node')).toBeTruthy();
    });
  });

  describe('Accessibility', () => {
    it('should have correct ARIA attributes', () => {
      render(<CommentPanel comment="Test" />);

      const region = screen.getByRole('region');
      expect(region.getAttribute('aria-labelledby')).toBeTruthy();
    });

    it('should announce live updates', () => {
      const { container } = render(<CommentPanel comment="Updated comment" />);

      const text = container.querySelector('.solution-tree-comment-text');
      expect(text?.getAttribute('aria-live')).toBe('polite');
    });
  });

  describe('Security', () => {
    it('should escape HTML in comments', () => {
      render(<CommentPanel comment="<script>alert('xss')</script>" />);

      // Should render escaped text, not execute script
      expect(screen.getByText(/&lt;script/)).toBeTruthy();
    });

    it('should escape special characters', () => {
      render(<CommentPanel comment="Test & <special> 'chars'" />);

      expect(screen.getByText(/Test &amp; &lt;special&gt;/)).toBeTruthy();
    });
  });

  describe('Styling', () => {
    it('should apply correct class when isCorrect is true', () => {
      const { container } = render(<CommentPanel comment="Good!" isCorrect={true} />);

      expect(container.querySelector('.solution-tree-comment--correct')).toBeTruthy();
    });

    it('should apply wrong class when isCorrect is false', () => {
      const { container } = render(<CommentPanel comment="Wrong" isCorrect={false} />);

      expect(container.querySelector('.solution-tree-comment--wrong')).toBeTruthy();
    });

    it('should accept custom className', () => {
      const { container } = render(<CommentPanel comment="Test" className="custom-class" />);

      expect(container.querySelector('.custom-class')).toBeTruthy();
    });
  });
});
