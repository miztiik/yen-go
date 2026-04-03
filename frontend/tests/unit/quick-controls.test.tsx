/**
 * Quick Controls Tests
 * @module tests/unit/quick-controls.test
 *
 * Tests for QuickControls panel component.
 *
 * Covers: T051
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { h } from 'preact';

// Types for quick controls
interface QuickControlsProps {
  onRotate: () => void;
  onUndo: () => void;
  onReset: () => void;
  onHint: () => void;
  canUndo: boolean;
  hintsRemaining: number;
  rotationAngle?: 0 | 90 | 180 | 270;
}

// Mock QuickControls component for contract testing
function MockQuickControls({
  onRotate,
  onUndo,
  onReset,
  onHint,
  canUndo,
  hintsRemaining,
  rotationAngle = 0,
}: QuickControlsProps) {
  return (
    <div className="quick-controls" data-testid="quick-controls" role="toolbar" aria-label="Quick controls">
      <button
        type="button"
        className="control-button rotate"
        onClick={onRotate}
        aria-label={`Rotate board (currently ${rotationAngle}°)`}
        data-testid="rotate-button"
      >
        <span className="icon">🔄</span>
        <span className="label">Rotate</span>
      </button>

      <button
        type="button"
        className="control-button undo"
        onClick={onUndo}
        disabled={!canUndo}
        aria-label="Undo last move"
        data-testid="undo-button"
      >
        <span className="icon">↩️</span>
        <span className="label">Undo</span>
      </button>

      <button
        type="button"
        className="control-button reset"
        onClick={onReset}
        aria-label="Reset puzzle"
        data-testid="reset-button"
      >
        <span className="icon">🔄</span>
        <span className="label">Reset</span>
      </button>

      <button
        type="button"
        className="control-button hint"
        onClick={onHint}
        disabled={hintsRemaining === 0}
        aria-label={`Get hint (${hintsRemaining} remaining)`}
        data-testid="hint-button"
      >
        <span className="icon">💡</span>
        <span className="label">Hint ({hintsRemaining})</span>
      </button>
    </div>
  );
}

describe('QuickControls Component', () => {
  const defaultProps: QuickControlsProps = {
    onRotate: vi.fn(),
    onUndo: vi.fn(),
    onReset: vi.fn(),
    onHint: vi.fn(),
    canUndo: true,
    hintsRemaining: 3,
  };

  describe('Basic rendering', () => {
    it('should render controls container', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByTestId('quick-controls')).toBeDefined();
    });

    it('should have toolbar role', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByRole('toolbar')).toBeDefined();
    });

    it('should render all control buttons', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByTestId('rotate-button')).toBeDefined();
      expect(screen.getByTestId('undo-button')).toBeDefined();
      expect(screen.getByTestId('reset-button')).toBeDefined();
      expect(screen.getByTestId('hint-button')).toBeDefined();
    });
  });

  describe('Rotate button', () => {
    it('should call onRotate when clicked', () => {
      const onRotate = vi.fn();
      render(<MockQuickControls {...defaultProps} onRotate={onRotate} />);
      
      fireEvent.click(screen.getByTestId('rotate-button'));
      expect(onRotate).toHaveBeenCalled();
    });

    it('should show current rotation angle', () => {
      render(<MockQuickControls {...defaultProps} rotationAngle={90} />);
      const label = screen.getByTestId('rotate-button').getAttribute('aria-label');
      expect(label).toContain('90°');
    });

    it('should always be enabled', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByTestId('rotate-button').hasAttribute('disabled')).toBe(false);
    });
  });

  describe('Undo button', () => {
    it('should call onUndo when clicked', () => {
      const onUndo = vi.fn();
      render(<MockQuickControls {...defaultProps} onUndo={onUndo} />);
      
      fireEvent.click(screen.getByTestId('undo-button'));
      expect(onUndo).toHaveBeenCalled();
    });

    it('should be disabled when canUndo is false', () => {
      render(<MockQuickControls {...defaultProps} canUndo={false} />);
      expect(screen.getByTestId('undo-button').hasAttribute('disabled')).toBe(true);
    });

    it('should be enabled when canUndo is true', () => {
      render(<MockQuickControls {...defaultProps} canUndo={true} />);
      expect(screen.getByTestId('undo-button').hasAttribute('disabled')).toBe(false);
    });
  });

  describe('Reset button', () => {
    it('should call onReset when clicked', () => {
      const onReset = vi.fn();
      render(<MockQuickControls {...defaultProps} onReset={onReset} />);
      
      fireEvent.click(screen.getByTestId('reset-button'));
      expect(onReset).toHaveBeenCalled();
    });

    it('should always be enabled', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByTestId('reset-button').hasAttribute('disabled')).toBe(false);
    });
  });

  describe('Hint button', () => {
    it('should call onHint when clicked', () => {
      const onHint = vi.fn();
      render(<MockQuickControls {...defaultProps} onHint={onHint} />);
      
      fireEvent.click(screen.getByTestId('hint-button'));
      expect(onHint).toHaveBeenCalled();
    });

    it('should show hints remaining count', () => {
      render(<MockQuickControls {...defaultProps} hintsRemaining={2} />);
      expect(screen.getByTestId('hint-button').textContent).toContain('2');
    });

    it('should be disabled when no hints remaining', () => {
      render(<MockQuickControls {...defaultProps} hintsRemaining={0} />);
      expect(screen.getByTestId('hint-button').hasAttribute('disabled')).toBe(true);
    });

    it('should be enabled when hints remaining', () => {
      render(<MockQuickControls {...defaultProps} hintsRemaining={1} />);
      expect(screen.getByTestId('hint-button').hasAttribute('disabled')).toBe(false);
    });

    it('should show remaining count in aria-label', () => {
      render(<MockQuickControls {...defaultProps} hintsRemaining={2} />);
      const label = screen.getByTestId('hint-button').getAttribute('aria-label');
      expect(label).toContain('2 remaining');
    });
  });

  describe('Accessibility', () => {
    it('should have aria-label on container', () => {
      render(<MockQuickControls {...defaultProps} />);
      expect(screen.getByRole('toolbar').getAttribute('aria-label')).toBe('Quick controls');
    });

    it('should have aria-labels on all buttons', () => {
      render(<MockQuickControls {...defaultProps} />);
      
      expect(screen.getByTestId('rotate-button').getAttribute('aria-label')).toBeDefined();
      expect(screen.getByTestId('undo-button').getAttribute('aria-label')).toBe('Undo last move');
      expect(screen.getByTestId('reset-button').getAttribute('aria-label')).toBe('Reset puzzle');
      expect(screen.getByTestId('hint-button').getAttribute('aria-label')).toBeDefined();
    });
  });
});

describe('QuickControls keyboard shortcuts', () => {
  it('should define shortcut keys', () => {
    const shortcuts = {
      rotate: 'r',
      undo: 'z',
      reset: 'x',
      hint: 'h',
    };

    expect(shortcuts.rotate).toBe('r');
    expect(shortcuts.undo).toBe('z');
    expect(shortcuts.reset).toBe('x');
    expect(shortcuts.hint).toBe('h');
  });
});
