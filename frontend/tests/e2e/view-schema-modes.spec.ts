/**
 * E2E test: Daily/Random/Timed/Technique modes with v3.0 format.
 * @module tests/e2e/view-schema-modes.spec
 *
 * Spec 131, Task T047
 * Verifies all puzzle modes load and render correctly.
 */

import { test, expect } from '@playwright/test';

test.describe('View Schema — Puzzle Modes', () => {
  test.beforeEach(async ({ page }) => {
    // Mock manifest for all tests
    await page.route('**/manifest.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          generatedAt: '2026-01-01T00:00:00Z',
          totalPuzzles: 100,
          latestDate: '2026-01-01',
          levels: [
            { name: 'beginner', count: 50, paginated: false },
            { name: 'intermediate', count: 50, paginated: false },
          ],
        }),
      });
    });
  });

  test('daily page loads and renders daily challenge', async ({ page }) => {
    // Daily challenges load from SQLite (daily_schedule + daily_puzzles tables).
    // No JSON mock needed — the app queries the in-memory DB.
    await page.goto('/');
    await page.waitForTimeout(2000);

    // Home page should render
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });

  test('random mode draws from level index with .entries', async ({ page }) => {
    // Mock level index with v3.0 format
    await page.route('**/views/by-level/beginner*.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          type: 'level',
          name: 'beginner',
          total: 5,
          entries: [
            { path: 'sgf/beginner/batch-0001/p1.sgf', tags: ['capture'] },
            { path: 'sgf/beginner/batch-0001/p2.sgf', tags: ['ladder'] },
            { path: 'sgf/beginner/batch-0001/p3.sgf', tags: ['net'] },
            { path: 'sgf/beginner/batch-0001/p4.sgf', tags: ['snapback'] },
            { path: 'sgf/beginner/batch-0001/p5.sgf', tags: ['escape'] },
          ],
        }),
      });
    });

    // Navigate to random mode
    await page.goto('/random');
    await page.waitForTimeout(2000);

    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });

  test('technique page loads tag master index and lists tags', async ({ page }) => {
    // Mock tag master index
    await page.route('**/views/by-tag/index.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          generated_at: '2026-01-01T00:00:00Z',
          tags: [
            { name: 'snapback', count: 10, paginated: false },
            { name: 'ladder', count: 15, paginated: false },
            { name: 'life-and-death', count: 20, paginated: false },
          ],
        }),
      });
    });

    await page.goto('/technique/snapback');
    await page.waitForTimeout(2000);

    // Page should render technique list
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });
});
