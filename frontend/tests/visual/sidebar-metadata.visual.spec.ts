/**
 * Visual test: Sidebar metadata display.
 * @module tests/visual/sidebar-metadata.visual.spec
 *
 * Spec 125, Task T111
 */

import { test, expect } from '@playwright/test';

test.describe('Visual: Sidebar Metadata', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/collection/beginner');
    await page.waitForTimeout(1000);
  });

  test('puzzle metadata section layout', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      await expect(metadata).toHaveScreenshot('sidebar-metadata.png', {
        threshold: 0.3,
      });
    }
  });

  test('sidebar in solving mode', async ({ page }) => {
    const sidebar = page.getByTestId('puzzle-sidebar');
    
    if (await sidebar.count() > 0) {
      await expect(sidebar).toHaveScreenshot('sidebar-solving-mode.png', {
        threshold: 0.3,
      });
    }
  });

  test('tags display', async ({ page }) => {
    const metadata = page.getByTestId('puzzle-metadata');
    
    if (await metadata.count() > 0) {
      // Tags should be styled as badges
      const tags = metadata.locator('span').filter({ hasText: /life-and-death|ladder|ko/i });
      if (await tags.count() > 0) {
        await expect(tags.first()).toHaveScreenshot('tag-badge.png', {
          threshold: 0.3,
        });
      }
    }
  });
});
