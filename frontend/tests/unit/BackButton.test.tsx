/**
 * BackButton SVG chevron — unit tests.
 * T152: Verify back button renders SVG chevron-left icon (not Unicode ←).
 * Spec 132 US16
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { ChevronLeftIcon } from '../../src/components/shared/icons/ChevronLeftIcon';

describe('ChevronLeftIcon (back button icon)', () => {
  it('renders an SVG element', () => {
    const { container } = render(<ChevronLeftIcon />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
  });

  it('renders with default size of 20', () => {
    const { container } = render(<ChevronLeftIcon />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('width')).toBe('20');
    expect(svg.getAttribute('height')).toBe('20');
  });

  it('renders with custom size', () => {
    const { container } = render(<ChevronLeftIcon size={14} />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('width')).toBe('14');
    expect(svg.getAttribute('height')).toBe('14');
  });

  it('contains a polyline element for the chevron shape', () => {
    const { container } = render(<ChevronLeftIcon />);
    const polyline = container.querySelector('polyline');
    expect(polyline).not.toBeNull();
    expect(polyline!.getAttribute('points')).toBe('15 18 9 12 15 6');
  });

  it('does NOT render Unicode ← character', () => {
    const { container } = render(<ChevronLeftIcon />);
    expect(container.textContent).not.toContain('←');
  });

  it('uses currentColor for stroke', () => {
    const { container } = render(<ChevronLeftIcon />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('stroke')).toBe('currentColor');
  });

  it('applies custom className', () => {
    const { container } = render(<ChevronLeftIcon className="text-gray-500" />);
    const svg = container.querySelector('svg')!;
    expect(svg.getAttribute('class')).toBe('text-gray-500');
  });
});

describe('back button pattern (T152)', () => {
  it('back button with ChevronLeftIcon renders SVG, not Unicode arrow', () => {
    // Simulate the inline back button pattern used across pages
    const BackButtonSimulation = () => (
      <button type="button" className="inline-flex items-center gap-1">
        <ChevronLeftIcon size={14} /> Back
      </button>
    );

    const { container, getByText } = render(<BackButtonSimulation />);

    // Has SVG icon
    expect(container.querySelector('svg')).not.toBeNull();
    // Has "Back" text
    expect(getByText('Back')).toBeTruthy();
    // No Unicode ← anywhere
    expect(container.textContent).not.toContain('←');
  });
});
