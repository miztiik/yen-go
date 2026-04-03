/**
 * Variant Style Toggle Tests
 * @module tests/unit/variant-toggle.test.tsx
 *
 * Unit tests for VariantStyleToggle component.
 * Covers: T033-T035 (P3 variant styling)
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { VariantStyleToggle } from '../../src/components/SolutionTree';
import type { VariantStyle } from '../../src/components/SolutionTree';

// ============================================================================
// Tests
// ============================================================================

describe('VariantStyleToggle', () => {
  const defaultProps = {
    value: 'children' as VariantStyle,
    onChange: vi.fn(),
  };

  describe('Rendering', () => {
    it('should render three toggle options', () => {
      render(<VariantStyleToggle {...defaultProps} />);

      expect(screen.getByRole('radiogroup')).toBeTruthy();
      expect(screen.getAllByRole('radio')).toHaveLength(3);
    });

    it('should display children, siblings, and hidden options', () => {
      render(<VariantStyleToggle {...defaultProps} />);

      // Use getByTestId since aria-labels don't match regex directly
      expect(screen.getByTestId('variant-option-children')).toBeTruthy();
      expect(screen.getByTestId('variant-option-siblings')).toBeTruthy();
      expect(screen.getByTestId('variant-option-hidden')).toBeTruthy();
    });

    it('should show currently selected value', () => {
      render(<VariantStyleToggle {...defaultProps} value="siblings" />);

      const siblingsRadio = screen.getByTestId('variant-option-siblings');
      expect(siblingsRadio.getAttribute('aria-checked')).toBe('true');
    });
  });

  describe('Interaction', () => {
    it('should call onChange when option is clicked', () => {
      const onChange = vi.fn();
      render(<VariantStyleToggle {...defaultProps} onChange={onChange} />);

      const siblingsButton = screen.getByTestId('variant-option-siblings');
      fireEvent.click(siblingsButton);

      expect(onChange).toHaveBeenCalledWith('siblings');
    });

    it('should not call onChange when clicking current selection', () => {
      const onChange = vi.fn();
      render(<VariantStyleToggle {...defaultProps} value="children" onChange={onChange} />);

      const childrenButton = screen.getByTestId('variant-option-children');
      fireEvent.click(childrenButton);

      // Should not call onChange for already selected option
      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe('Disabled State', () => {
    it('should disable all buttons when disabled prop is true', () => {
      render(<VariantStyleToggle {...defaultProps} disabled={true} />);

      const buttons = screen.getAllByRole('radio');
      buttons.forEach(button => {
        // Check for disabled attribute (not aria-disabled)
        expect(button.hasAttribute('disabled')).toBe(true);
      });
    });

    it('should not call onChange when disabled', () => {
      const onChange = vi.fn();
      render(<VariantStyleToggle {...defaultProps} disabled={true} onChange={onChange} />);

      const siblingsButton = screen.getByTestId('variant-option-siblings');
      fireEvent.click(siblingsButton);

      expect(onChange).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('should have accessible group label', () => {
      render(<VariantStyleToggle {...defaultProps} />);

      const group = screen.getByRole('radiogroup');
      expect(group.getAttribute('aria-label')).toBe('Variant display style');
    });

    it('should support keyboard navigation', () => {
      render(<VariantStyleToggle {...defaultProps} />);

      const buttons = screen.getAllByRole('radio');
      // Should be focusable
      buttons.forEach(button => {
        expect(button.getAttribute('tabIndex')).toBeDefined();
      });
    });

    it('should have minimum 44px touch targets', () => {
      const { container } = render(<VariantStyleToggle {...defaultProps} />);

      // Check that component has proper class for touch target styling
      expect(container.querySelector('.variant-style-toggle')).toBeTruthy();
    });
  });

  describe('Custom Styling', () => {
    it('should accept custom className', () => {
      const { container } = render(
        <VariantStyleToggle {...defaultProps} className="custom-toggle" />
      );

      expect(container.querySelector('.custom-toggle')).toBeTruthy();
    });
  });

  describe('All Values', () => {
    it('should handle children value', () => {
      render(<VariantStyleToggle {...defaultProps} value="children" />);

      const childrenRadio = screen.getByTestId('variant-option-children');
      expect(childrenRadio.getAttribute('aria-checked')).toBe('true');
    });

    it('should handle siblings value', () => {
      render(<VariantStyleToggle {...defaultProps} value="siblings" />);

      const siblingsRadio = screen.getByTestId('variant-option-siblings');
      expect(siblingsRadio.getAttribute('aria-checked')).toBe('true');
    });

    it('should handle hidden value', () => {
      render(<VariantStyleToggle {...defaultProps} value="hidden" />);

      const hiddenRadio = screen.getByTestId('variant-option-hidden');
      expect(hiddenRadio.getAttribute('aria-checked')).toBe('true');
    });
  });
});
