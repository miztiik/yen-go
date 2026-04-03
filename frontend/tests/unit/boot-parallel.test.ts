/**
 * Boot parallelization — unit tests.
 *
 * T063: Verify boot() calls fetchAndValidateConfigs() and import('./app')
 * concurrently via Promise.all.
 * Spec 131: FR-030
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('boot parallelization', () => {
  const source = readFileSync(
    resolve(__dirname, '../../src/boot.ts'),
    'utf-8',
  );

  it('uses Promise.all for config fetch and app import', () => {
    // The boot function should call Promise.all with both operations
    expect(source).toContain('Promise.all');
    expect(source).toContain("import('./app')");
    expect(source).toContain('fetchAndValidateConfigs()');
  });

  it('does NOT have sequential await for config then import', () => {
    // Ensure we don't have the old sequential pattern:
    //   cachedConfigs = await fetchAndValidateConfigs();
    //   ... (code) ...
    //   const { App } = await import('./app');
    const lines = source.split('\n');
    const awaitFetchLine = lines.findIndex(
      (l) => l.includes('= await fetchAndValidateConfigs()') && !l.trim().startsWith('//'),
    );
    // The only await fetchAndValidateConfigs should be inside Promise.all (no standalone await)
    expect(awaitFetchLine).toBe(-1);
  });
});
