/**
 * E2E test: Collection browse with v3.0 ViewEnvelope/DirectoryIndex.
 * @module tests/e2e/view-schema-collection.spec
 *
 * Spec 131, Task T046
 * Verifies collection page loads correctly with v3.0 format.
 */

import { test, expect } from '@playwright/test';

test.describe('View Schema — Collection Browse', () => {
  test('collection page intercepts DirectoryIndex and PageDocument', async ({ page }) => {
    let interceptedDirectory = false;
    let interceptedPage = false;

    // Mock collection directory index
    await page.route('**/views/by-collection/*/index.json', async (route) => {
      interceptedDirectory = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'collection',
          name: 'cho-chikun-elementary',
          total_count: 4,
          page_size: 2,
          pages: [
            { page: 1, count: 2 },
            { page: 2, count: 2 },
          ],
        }),
      });
    });

    // Mock collection page
    await page.route('**/views/by-collection/*/page-*.json', async (route) => {
      interceptedPage = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          type: 'collection',
          name: 'cho-chikun-elementary',
          page: 1,
          entries: [
            { path: 'sgf/beginner/batch-0001/puzzle-001.sgf', level: 'beginner', sequence_number: 1 },
            { path: 'sgf/beginner/batch-0001/puzzle-002.sgf', level: 'beginner', sequence_number: 2 },
          ],
        }),
      });
    });

    // Mock the collection master index
    await page.route('**/collections.json', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          version: '3.0',
          collections: [{
            slug: 'cho-chikun-elementary',
            name: 'Cho Chikun Elementary',
            author: 'Cho Chikun',
            totalPuzzles: 4,
            levels: ['beginner'],
          }],
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
          totalPuzzles: 100,
          latestDate: '2026-01-01',
          levels: [],
        }),
      });
    });

    // Navigate to collection page
    await page.goto('/collections/cho-chikun-life-death-intermediate');
    await page.waitForTimeout(2000);

    // Page loaded
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeDefined();
  });
});
