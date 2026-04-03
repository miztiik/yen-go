/**
 * HomeTile hover — unit tests.
 *
 * T070: Verify HomeTile does NOT use useState for hover state.
 * Spec 131: FR-034
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('HomeTile hover implementation', () => {
  const source = readFileSync(
    resolve(__dirname, '../../src/components/Home/HomeTile.tsx'),
    'utf-8',
  );

  it('does NOT use useState for hover', () => {
    expect(source).not.toContain('useState');
  });

  it('does NOT have onMouseEnter handler', () => {
    expect(source).not.toContain('onMouseEnter');
  });

  it('does NOT have onMouseLeave handler', () => {
    expect(source).not.toContain('onMouseLeave');
  });

  it('uses CSS hover class instead of JS state', () => {
    // The component should rely on CSS .home-tile:hover
    expect(source).toContain('home-tile');
  });
});
