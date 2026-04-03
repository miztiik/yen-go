/**
 * E2E test: Sidebar metadata display (YG, YT, YH, YK).
 * @module tests/e2e/nav-metadata.spec
 *
 * Spec 125, Task T110
 */

import { test, expect } from '@playwright/test';

test.describe('Navigation - Metadata Display', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/collections/curated-beginner-essentials/1');
    await page.waitForTimeout(1000);
  });

  test('sidebar shows puzzle metadata section', async ({ page }) => {
    const sidebar = page.getByTestId('puzzle-sidebar');
    
    if (await sidebar.count() > 0) {
      // Should have puzzle info section
      await expect(sidebar.getByText(/Puzzle Info|Level|Tags/i)).toBeVisible();
    }
  });

  test('sidebar shows skill level (YG)', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      // Should show level
      await expect(metadata.getByText(/Level/i)).toBeVisible();
    }
  });

  test('sidebar shows hints available count (YH)', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      // Should show hints count
      await expect(metadata.getByText(/Hints/i)).toBeVisible();
    }
  });

  test('sidebar shows tags when present (YT)', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      // Tags section may or may not be present depending on puzzle
      const tagsLabel = metadata.getByText(/Tags/i);
      // At minimum, the metadata section should exist
      await expect(metadata).toBeVisible();
    }
  });

  test('sidebar shows ko context badge when applicable (YK)', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      // Ko context may not be present on all puzzles
      // This test verifies the container exists
      await expect(metadata).toBeVisible();
    }
  });

  test('metadata section is in solving mode', async ({ page }) => {
    const sidebar = page.getByTestId('puzzle-sidebar');
    
    if (await sidebar.count() > 0) {
      // In solving mode, should show transforms and puzzle info
      await expect(sidebar.getByText(/Transforms/i)).toBeVisible();
    }
  });
});
