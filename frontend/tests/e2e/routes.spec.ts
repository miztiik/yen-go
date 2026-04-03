/**
 * E2E test: Route Validation (T108).
 * Verify every frontend route loads without errors.
 * Spec 132
 */
import { test, expect } from '@playwright/test';

const ROUTES = [
  { path: '/', name: 'Home/Training' },
  { path: '/daily', name: 'Daily Challenge' },
  { path: '/technique', name: 'Technique Focus' },
  { path: '/collections', name: 'Collections' },
  { path: '/random', name: 'Random Challenge' },
  { path: '/rush', name: 'Puzzle Rush' },
  { path: '/collection/beginner', name: 'Collection View' },
] as const;

test.describe('Route Validation E2E', () => {
  for (const route of ROUTES) {
    test(`${route.name} (${route.path}) loads without console errors`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));

      const response = await page.goto(route.path);
      await page.waitForLoadState('networkidle');

      // Page should return 200
      expect(response?.status()).toBe(200);

      // No uncaught JS errors
      expect(errors).toEqual([]);

      // Page should have content
      const body = page.locator('body');
      await expect(body).not.toBeEmpty();
    });
  }
});
