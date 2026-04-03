/**
 * Home page performance test — T126b (FR-074, SC-005).
 * Validates that `performance.mark('home-interactive')` fires
 * within 1 s of navigation start.
 */
import { test, expect } from '@playwright/test';

// TODO: Implement performance.mark('home-interactive') in HomePage component
// then remove this skip. See FR-074, SC-005.
test.skip('home-interactive mark fires within 1 s', async ({ page }) => {
  await page.goto('/');

  // Wait for the mark to appear (data loads are async)
  await page.waitForFunction(
    () => performance.getEntriesByName('home-interactive').length > 0,
    { timeout: 5000 },
  );

  const startTime = await page.evaluate(() => {
    const entries = performance.getEntriesByName('home-interactive');
    return entries[0]?.startTime ?? -1;
  });

  expect(startTime).toBeGreaterThan(0);
  expect(startTime).toBeLessThan(1000);
});
