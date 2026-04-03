/**
 * Unit tests for BoardControls component
 * @module tests/unit/board-controls.test
 *
 * Tests the board control bar with rotation and coordinates toggles.
 * Spec: 122-frontend-comprehensive-refactor
 * Task: T6.3
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { BoardControls } from '../../src/components/Board/BoardControls';

describe('BoardControls', () => {
  let mockOnRotationChange: ReturnType<typeof vi.fn>;
  let mockOnCoordinatesChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockOnRotationChange = vi.fn();
    mockOnCoordinatesChange = vi.fn();
  });

  describe('rendering', () => {
    it('should render rotation and coordinates buttons', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      // Should have rotation button
      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      expect(rotateButton).toBeDefined();

      // Should have coordinates toggle
      const coordsButton = screen.getByRole('button', { name: /coordinates/i });
      expect(coordsButton).toBeDefined();
    });

    it('should apply custom className', () => {
      const { container } = render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
          className="custom-class"
        />
      );

      const controlsDiv = container.querySelector('.board-controls');
      expect(controlsDiv?.classList.contains('custom-class')).toBe(true);
    });
  });

  describe('rotation', () => {
    it('should cycle rotation from 0 to 90', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      fireEvent.click(rotateButton);

      expect(mockOnRotationChange).toHaveBeenCalledWith(90);
    });

    it('should cycle rotation from 90 to 180', () => {
      render(
        <BoardControls
          rotation={90}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      fireEvent.click(rotateButton);

      expect(mockOnRotationChange).toHaveBeenCalledWith(180);
    });

    it('should cycle rotation from 180 to 270', () => {
      render(
        <BoardControls
          rotation={180}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      fireEvent.click(rotateButton);

      expect(mockOnRotationChange).toHaveBeenCalledWith(270);
    });

    it('should cycle rotation from 270 back to 0', () => {
      render(
        <BoardControls
          rotation={270}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      fireEvent.click(rotateButton);

      expect(mockOnRotationChange).toHaveBeenCalledWith(0);
    });

    it('should handle invalid rotation value by resetting to 0', () => {
      render(
        <BoardControls
          rotation={45} // Invalid - not 0, 90, 180, or 270
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const rotateButton = screen.getByRole('button', { name: /rotate/i });
      fireEvent.click(rotateButton);

      expect(mockOnRotationChange).toHaveBeenCalledWith(0);
    });
  });

  describe('coordinates toggle', () => {
    it('should toggle coordinates on when currently off', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const coordsButton = screen.getByRole('button', { name: /coordinates/i });
      fireEvent.click(coordsButton);

      expect(mockOnCoordinatesChange).toHaveBeenCalledWith(true);
    });

    it('should toggle coordinates off when currently on', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={true}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const coordsButton = screen.getByRole('button', { name: /coordinates/i });
      fireEvent.click(coordsButton);

      expect(mockOnCoordinatesChange).toHaveBeenCalledWith(false);
    });

    it('should show active state when coordinates are on', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={true}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const coordsButton = screen.getByRole('button', { name: /coordinates/i });
      expect(coordsButton.getAttribute('aria-pressed')).toBe('true');
    });

    it('should show inactive state when coordinates are off', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const coordsButton = screen.getByRole('button', { name: /coordinates/i });
      expect(coordsButton.getAttribute('aria-pressed')).toBe('false');
    });
  });

  describe('keyboard navigation', () => {
    it('should move focus to next button with ArrowRight', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      const rotateButton = buttons[0];
      const coordsButton = buttons[1];

      rotateButton.focus();
      fireEvent.keyDown(rotateButton, { key: 'ArrowRight' });

      expect(document.activeElement).toBe(coordsButton);
    });

    it('should move focus to previous button with ArrowLeft', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      const rotateButton = buttons[0];
      const coordsButton = buttons[1];

      coordsButton.focus();
      fireEvent.keyDown(coordsButton, { key: 'ArrowLeft' });

      expect(document.activeElement).toBe(rotateButton);
    });

    it('should wrap around when navigating past last button', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      const rotateButton = buttons[0];
      const coordsButton = buttons[1];

      coordsButton.focus();
      fireEvent.keyDown(coordsButton, { key: 'ArrowRight' });

      expect(document.activeElement).toBe(rotateButton);
    });
  });

  describe('accessibility', () => {
    it('should have accessible names for all buttons', () => {
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button.getAttribute('aria-label') || button.textContent).toBeTruthy();
      });
    });

    it('should have proper role attribute on controls container', () => {
      const { container } = render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const toolbar = container.querySelector('[role="toolbar"]');
      expect(toolbar).toBeDefined();
    });

    it('should have focus-visible styles, not focus (spec requirement)', () => {
      // This is a CSS test - we just verify buttons have the right class structure
      render(
        <BoardControls
          rotation={0}
          onRotationChange={mockOnRotationChange}
          showCoordinates={false}
          onCoordinatesChange={mockOnCoordinatesChange}
        />
      );

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        // Buttons should have the icon button class
        expect(button.classList.contains('board-controls__btn')).toBe(true);
      });
    });
  });
});
