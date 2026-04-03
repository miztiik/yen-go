/**
 * useGoban lazy import — unit tests.
 *
 * T062: Verify useGoban uses dynamic import("goban") instead of static imports.
 * Spec 131: FR-028
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

describe('useGoban lazy import', () => {
  const source = readFileSync(
    resolve(__dirname, '../../src/hooks/useGoban.ts'),
    'utf-8',
  );

  it('does NOT have static runtime import from "goban"', () => {
    // Match lines like `import { X } from "goban"` but NOT `import type { ... } from "goban"`
    // For multiline imports, look for the `import` keyword line (not the closing `} from` line)
    const importStatements = source.match(/^import\s+\{[^}]*\}\s+from\s+"goban"/gm) ?? [];
    const runtimeImports = importStatements.filter(
      (stmt) => !stmt.includes('import type'),
    );
    expect(runtimeImports).toEqual([]);
  });

  it('uses dynamic import("goban") inside the effect', () => {
    expect(source).toContain('await import("goban")');
  });
});
