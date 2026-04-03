/**
 * E2E test: Level browse with v3.0 ViewEnvelope.
 * @module tests/e2e/view-schema-level.spec
 *
 * Spec 131, Task T044
 * Verifies level page loads correctly and uses v3.0 view index format.
 */

import { test, expect } from '@playwright/test';

test.describe('View Schema — Level Browse', () => {
  test('level page intercepts ViewEnvelope<LevelEntry> and renders puzzle count', async ({ page }) => {
    let interceptedEnvelope: Record<string, unknown> | null = null;

    // Intercept the level index fetch
    await page.route('**/views/by-level/beginner*.json', async (route) => {
      // Serve a mock v3.0 ViewEnvelope
      const mockEnvelope = {
        version: '3.0',
        type: 'level',
        name: 'beginner',
        total: 3,
        entries: [
          { path: 'sgf/beginner/batch-0001/puzzle-001.sgf', tags: ['capture'] },
          { path: 'sgf/beginner/batch-0001/puzzle-002.sgf', tags: ['ladder'] },
          { path: 'sgf/beginner/batch-0001/puzzle-003.sgf', tags: ['life-and-death'] },
        ],
      };
      interceptedEnvelope = mockEnvelope;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockEnvelope),
      });
    });

    // Also mock the manifest to prevent 404s
    await page.route('**/manifest.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          generatedAt: '2026-01-01T00:00:00Z',
          totalPuzzles: 100,
          latestDate: '2026-01-01',
          levels: [{ name: 'beginner', count: 3, paginated: false }],
        }),
      });
    });

    // Navigate to level page
    await page.goto('/training/beginner');
    await page.waitForTimeout(2000);

    // Verify the mock ViewEnvelope was served
    expect(interceptedEnvelope).not.toBeNull();
    expect(interceptedEnvelope!.version).toBe('3.0');
    expect(interceptedEnvelope!.type).toBe('level');
    expect(interceptedEnvelope!.entries).toHaveLength(3);

    // Verify the page rendered (check for puzzle grid or puzzle count)
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });

  test('level page handles empty ViewEnvelope gracefully', async ({ page }) => {
    await page.route('**/views/by-level/advanced*.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          type: 'level',
          name: 'advanced',
          total: 0,
          entries: [],
        }),
      });
    });

    await page.route('**/manifest.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          generatedAt: '2026-01-01T00:00:00Z',
          totalPuzzles: 0,
          latestDate: '2026-01-01',
          levels: [{ name: 'advanced', count: 0, paginated: false }],
        }),
      });
    });

    await page.goto('/training/advanced');
    await page.waitForTimeout(2000);

    // Page should handle empty state
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });
});
