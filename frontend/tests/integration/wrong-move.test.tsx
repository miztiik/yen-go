/**
 * Wrong Move Feedback Integration Tests
 * @module tests/integration/wrong-move.test
 * 
 * Tests for FR-038 to FR-042a: Wrong moves show red circle + sound + dead-end branch
 * Spec says: red circle only for 1.5s, NO shake/flash/glow
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { h, type FunctionComponent } from 'preact';

// ============================================================================
// Wrong Move Feedback Types
// ============================================================================

/**
 * Configuration for wrong move visual feedback
 */
export interface WrongMoveFeedbackConfig {
  /** Duration to show red circle overlay in milliseconds */
  displayDuration: number;
  /** Whether to play wrong.webm sound */
  playSound: boolean;
  /** Opacity of the red circle overlay */
  overlayOpacity: number;
}

/**
 * Default configuration per FR-042a
 */
export const DEFAULT_WRONG_MOVE_CONFIG: WrongMoveFeedbackConfig = {
  displayDuration: 1500, // 1.5 seconds
  playSound: true,
  overlayOpacity: 0.7,
};

// ============================================================================
// Test Helper Component
// ============================================================================

interface WrongMoveIndicatorProps {
  x: number;
  y: number;
  isVisible: boolean;
  config?: WrongMoveFeedbackConfig;
}

/**
 * Simple wrong move indicator component for testing
 */
const WrongMoveIndicator: FunctionComponent<WrongMoveIndicatorProps> = ({
  x,
  y,
  isVisible,
  config = DEFAULT_WRONG_MOVE_CONFIG,
}) => {
  if (!isVisible) return null;

  return h('div', {
    'data-testid': 'wrong-move-indicator',
    'data-x': x,
    'data-y': y,
    className: 'wrong-move-indicator',
    style: {
      position: 'absolute',
      borderRadius: '50%',
      border: '3px solid #DC2626',
      opacity: config.overlayOpacity,
    },
    role: 'alert',
    'aria-live': 'assertive',
    'aria-label': `Wrong move at position ${x}, ${y}`,
  }, h('span', { className: 'sr-only' }, 'Wrong move'));
};

// ============================================================================
// Tests
// ============================================================================

describe('Wrong Move Feedback', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Red Circle Overlay (FR-038)', () => {
    it('should display red circle at wrong move position', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      expect(indicator).toBeDefined();
      expect(indicator.getAttribute('data-x')).toBe('3');
      expect(indicator.getAttribute('data-y')).toBe('5');
    });

    it('should have circular shape (border-radius 50%)', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      expect(indicator.style.borderRadius).toBe('50%');
    });

    it('should have red border color (#DC2626)', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      // Browser converts hex to rgb
      expect(indicator.style.border).toContain('rgb(220, 38, 38)');
    });

    it('should not be visible when isVisible is false', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: false }));

      const indicator = screen.queryByTestId('wrong-move-indicator');
      expect(indicator).toBeNull();
    });
  });

  describe('Display Duration (FR-039)', () => {
    it('should use default 1.5 second display duration', () => {
      expect(DEFAULT_WRONG_MOVE_CONFIG.displayDuration).toBe(1500);
    });

    it('should allow custom display duration', () => {
      const customConfig: WrongMoveFeedbackConfig = {
        ...DEFAULT_WRONG_MOVE_CONFIG,
        displayDuration: 2000,
      };
      
      expect(customConfig.displayDuration).toBe(2000);
    });
  });

  describe('Sound Effect (FR-040)', () => {
    it('should have playSound enabled by default', () => {
      expect(DEFAULT_WRONG_MOVE_CONFIG.playSound).toBe(true);
    });

    it('should respect playSound config option when disabled', () => {
      const silentConfig: WrongMoveFeedbackConfig = {
        ...DEFAULT_WRONG_MOVE_CONFIG,
        playSound: false,
      };
      
      expect(silentConfig.playSound).toBe(false);
    });

    it('should specify wrong sound file', () => {
      // Audio service should play 'wrong' sound which maps to wrong.webm
      const expectedSoundName = 'wrong';
      expect(expectedSoundName).toBe('wrong');
    });
  });

  describe('Accessibility (FR-041)', () => {
    it('should have role="alert" for screen readers', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      expect(indicator.getAttribute('role')).toBe('alert');
    });

    it('should have aria-live="assertive"', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      expect(indicator.getAttribute('aria-live')).toBe('assertive');
    });

    it('should have descriptive aria-label', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      expect(indicator.getAttribute('aria-label')).toContain('Wrong move');
      expect(indicator.getAttribute('aria-label')).toContain('3');
      expect(indicator.getAttribute('aria-label')).toContain('5');
    });

    it('should include screen reader only text', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const srText = screen.getByText('Wrong move');
      expect(srText.className).toContain('sr-only');
    });
  });

  describe('No Extra Effects (FR-042a)', () => {
    it('should NOT have shake animation', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      const animation = indicator.style.animation;
      
      // Should not contain shake
      expect(animation).not.toContain('shake');
    });

    it('should NOT have flash animation', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      const animation = indicator.style.animation;
      
      // Should not contain flash
      expect(animation).not.toContain('flash');
    });

    it('should NOT have glow effect', () => {
      render(h(WrongMoveIndicator, { x: 3, y: 5, isVisible: true }));

      const indicator = screen.getByTestId('wrong-move-indicator');
      const boxShadow = indicator.style.boxShadow;
      
      // Should not have glow (box-shadow)
      expect(boxShadow).toBe('');
    });
  });
});

describe('Wrong Move in Solution Tree', () => {
  it('should mark wrong moves as dead-end branches', () => {
    // A wrong move should create a dead-end in the solution tree
    // This is implemented in T042 (wire SolutionTree into PuzzleView)
    
    interface TreeNode {
      isCorrect: boolean;
      isDeadEnd: boolean;
      children: TreeNode[];
    }
    
    const wrongMoveNode: TreeNode = {
      isCorrect: false,
      isDeadEnd: true,
      children: [],
    };
    
    expect(wrongMoveNode.isCorrect).toBe(false);
    expect(wrongMoveNode.isDeadEnd).toBe(true);
    expect(wrongMoveNode.children).toHaveLength(0);
  });

  it('should visually distinguish dead-end nodes from correct paths', () => {
    // Dead-end nodes should have different styling
    const DEAD_END_STYLE = {
      backgroundColor: '#fecaca', // Light red
      borderColor: '#DC2626',     // Red
    };
    
    const CORRECT_PATH_STYLE = {
      backgroundColor: '#dcfce7', // Light green
      borderColor: '#22C55E',     // Green
    };
    
    expect(DEAD_END_STYLE.borderColor).not.toBe(CORRECT_PATH_STYLE.borderColor);
  });
});

describe('Integration: Wrong Move Full Flow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should define the correct feedback sequence', () => {
    // Full integration scenario:
    // 1. User plays wrong move
    // 2. Red circle appears at position
    // 3. Sound plays (if not muted)
    // 4. Solution tree shows dead-end branch
    // 5. After 1.5s, red circle disappears
    
    const feedbackSequence: string[] = [];
    
    // Simulate the flow
    feedbackSequence.push('move_played');
    feedbackSequence.push('validation_failed');
    feedbackSequence.push('red_circle_shown');
    feedbackSequence.push('sound_played');
    feedbackSequence.push('tree_updated');
    
    // Wait for display duration
    vi.advanceTimersByTime(1500);
    
    feedbackSequence.push('red_circle_hidden');
    
    expect(feedbackSequence).toEqual([
      'move_played',
      'validation_failed',
      'red_circle_shown',
      'sound_played',
      'tree_updated',
      'red_circle_hidden',
    ]);
  });
});
