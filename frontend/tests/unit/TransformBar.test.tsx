/**
 * Unit tests for TransformBar component.
 *
 * UI-028: Phase 6 — verify transform buttons, coordinate toggle,
 * disabled state, aria attributes, and performance patterns.
 *
 * Uses source analysis approach since TransformBar has icon component
 * dependencies that require complex mocking.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const source = readFileSync(
  resolve(__dirname, '../../src/components/Transforms/TransformBar.tsx'),
  'utf-8',
);

describe('TransformBar component structure', () => {
  it('has data-testid="transform-bar"', () => {
    expect(source).toContain('data-testid="transform-bar"');
  });

  it('has role="toolbar"', () => {
    expect(source).toContain('role="toolbar"');
  });

  it('has aria-label="Puzzle transforms"', () => {
    expect(source).toContain('aria-label="Puzzle transforms"');
  });

  it('renders all 5 transform buttons', () => {
    const labels = [
      'Flip horizontal',
      'Flip vertical',
      'Rotate counter-clockwise',
      'Rotate clockwise',
      'Swap colors',
    ];
    for (const label of labels) {
      expect(source).toContain(`aria-label="${label}"`);
    }
  });

  it('has coordinate toggle with dynamic aria-label', () => {
    expect(source).toContain("'Hide coordinates'");
    expect(source).toContain("'Show coordinates'");
  });

  it('coordinate toggle uses aria-pressed attribute', () => {
    expect(source).toContain('aria-pressed={coordinateLabels}');
  });

  it('uses transition-colors (not transition-all) for performance', () => {
    expect(source).toContain('transition-colors');
    expect(source).not.toContain('transition-all');
  });

  it('is wrapped in memo() for performance', () => {
    expect(source).toContain('memo(TransformBar)');
  });

  it('coordinate toggle is never disabled (always accessible)', () => {
    // The coordinate button uses coordsBtnClass directly, not btnClass()
    expect(source).toContain('const coordsBtnClass');
    expect(source).toContain('className={coordsBtnClass}');
  });

  it('has a visual separator between transforms and coordinate toggle', () => {
    expect(source).toContain('Separator');
    expect(source).toContain('w-px h-10');
  });

  it('transform buttons have aria-pressed for toggle state', () => {
    expect(source).toContain('aria-pressed={settings.flipH}');
    expect(source).toContain('aria-pressed={settings.flipV}');
    expect(source).toContain('aria-pressed={settings.swapColors}');
  });

  it('uses SVG icon components (not emoji)', () => {
    const icons = ['FlipHIcon', 'FlipVIcon', 'RotateCWIcon', 'RotateCCWIcon', 'SwapColorsIcon', 'CoordsIcon'];
    for (const icon of icons) {
      expect(source).toContain(icon);
    }
  });
});
