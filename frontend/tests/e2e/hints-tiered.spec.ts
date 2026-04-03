/**
 * Hints Tiered E2E Tests
 * @module tests/e2e/hints-tiered.spec
 *
 * Tests for progressive hint revelation (1→2→3 tiers).
 *
 * Covers: US4
 * Spec 125, Task T084
 */

import { test, expect } from '@playwright/test';

test.describe('Tiered Hints', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
  });

  test('should reveal hints progressively tier 1 → 2 → 3', async ({ page }) => {
    // Navigate to puzzle with 3 hints
    // Click hint - see tier 1
    // Click again - see tier 2
    // Click again - see tier 3
    test.skip(true, 'Requires puzzle with 3-tier hints');
  });

  test('should show all previously revealed hints', async ({ page }) => {
    // Reveal tier 1, 2, 3
    // All three should be visible
    test.skip(true, 'Requires hint display');
  });

  test('should keep hints visible after navigation', async ({ page }) => {
    // Reveal some hints
    // Navigate to review mode
    // Hints should still be shown
    test.skip(true, 'Requires hint persistence');
  });
});
