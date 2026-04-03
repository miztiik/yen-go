/**
 * KeyboardShortcutsLegend Component Tests
 * @module tests/unit/keyboard-shortcuts-legend.test
 *
 * Tests for keyboard shortcuts legend display.
 * P4 polish feature.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { KeyboardShortcutsLegend } from '@/components/SolutionTree';

describe('KeyboardShortcutsLegend', () => {
  describe('Rendering', () => {
    it('should render when visible is true', () => {
      render(<KeyboardShortcutsLegend visible={true} />);
      
      expect(screen.getByRole('note')).toBeDefined();
      expect(screen.getByText('Navigate:')).toBeDefined();
    });

    it('should not render when visible is false', () => {
      render(<KeyboardShortcutsLegend visible={false} />);
      
      expect(screen.queryByRole('note')).toBeNull();
    });

    it('should render by default (visible = true)', () => {
      render(<KeyboardShortcutsLegend />);
      
      expect(screen.getByRole('note')).toBeDefined();
    });

    it('should show all navigation shortcuts', () => {
      render(<KeyboardShortcutsLegend />);
      
      expect(screen.getByText('↑')).toBeDefined();
      expect(screen.getByText('↓')).toBeDefined();
      expect(screen.getByText('←')).toBeDefined();
      expect(screen.getByText('→')).toBeDefined();
      expect(screen.getByText('Home')).toBeDefined();
      expect(screen.getByText('End')).toBeDefined();
    });

    it('should show descriptions for shortcuts', () => {
      render(<KeyboardShortcutsLegend />);
      
      expect(screen.getByText('Previous move')).toBeDefined();
      expect(screen.getByText('Next move')).toBeDefined();
      expect(screen.getByText('Previous variation')).toBeDefined();
      expect(screen.getByText('Next variation')).toBeDefined();
    });
  });

  describe('Compact Mode', () => {
    it('should render fewer shortcuts in compact mode', () => {
      render(<KeyboardShortcutsLegend compact={true} />);
      
      // Arrow keys should be visible
      expect(screen.getByText('↑')).toBeDefined();
      expect(screen.getByText('↓')).toBeDefined();
      expect(screen.getByText('←')).toBeDefined();
      expect(screen.getByText('→')).toBeDefined();
      
      // Home/End should not be visible in compact mode
      expect(screen.queryByText('Home')).toBeNull();
      expect(screen.queryByText('End')).toBeNull();
    });

    it('should hide descriptions in compact mode', () => {
      render(<KeyboardShortcutsLegend compact={true} />);
      
      expect(screen.queryByText('Previous move')).toBeNull();
      expect(screen.queryByText('Next move')).toBeNull();
    });

    it('should have compact class when compact is true', () => {
      render(<KeyboardShortcutsLegend compact={true} />);
      
      expect(screen.getByRole('note').className).toContain('compact');
    });
  });

  describe('Accessibility', () => {
    it('should have accessible label', () => {
      render(<KeyboardShortcutsLegend />);
      
      expect(screen.getByRole('note').getAttribute('aria-label')).toBe('Keyboard shortcuts');
    });

    it('should use kbd elements for key representations', () => {
      render(<KeyboardShortcutsLegend />);
      
      const kbdElements = document.querySelectorAll('kbd');
      expect(kbdElements.length).toBeGreaterThanOrEqual(4);
    });

    it('should have title attributes for descriptions', () => {
      render(<KeyboardShortcutsLegend />);
      
      const upKey = screen.getByText('↑');
      expect(upKey.getAttribute('title')).toBe('Previous variation');
    });
  });

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      render(<KeyboardShortcutsLegend className="custom-class" />);
      
      expect(screen.getByRole('note').className).toContain('custom-class');
    });
  });
});
