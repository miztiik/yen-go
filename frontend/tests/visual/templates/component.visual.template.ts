/**
 * Component Visual Test Template
 * @module tests/visual/templates/component.visual.template
 *
 * Template for creating visual tests for new components.
 * Copy this file and modify for your component.
 *
 * Spec 122 - T0.8
 *
 * Naming convention: {component-name}.visual.spec.ts
 *
 * @example
 * Copy to: tests/visual/specs/my-component.visual.spec.ts
 * Update: Component selectors, test names, expected states
 */

import { test, expect } from '@playwright/test';

// Navigate to visual tests page before each test
test.beforeEach(async ({ page }) => {
  // Update URL if your component has its own test page
  await page.goto('/visual-tests.html');
  await page.waitForLoadState('networkidle');
  // Wait for any animations to complete
  await page.waitForTimeout(200);
});

test.describe('ComponentName Visual Tests', () => {
  /**
   * Test the default/initial state of the component.
   * This is the most important visual test.
   */
  test('default state', async ({ page }) => {
    // Update selector to match your component's fixture ID
    const fixture = page.locator('#component-default');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('component-default.png');
  });

  /**
   * Test hover state (if applicable).
   */
  test('hover state', async ({ page }) => {
    const fixture = page.locator('#component-default');
    await fixture.hover();
    await expect(fixture).toHaveScreenshot('component-hover.png');
  });

  /**
   * Test focused state.
   * Important for accessibility verification.
   */
  test('focused state', async ({ page }) => {
    const fixture = page.locator('#component-focusable');
    await fixture.focus();
    await expect(fixture).toHaveScreenshot('component-focused.png');
  });

  /**
   * Test disabled state (if applicable).
   */
  test('disabled state', async ({ page }) => {
    const fixture = page.locator('#component-disabled');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('component-disabled.png');
  });

  /**
   * Test with data/content loaded.
   */
  test('with content', async ({ page }) => {
    const fixture = page.locator('#component-with-content');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('component-with-content.png');
  });

  /**
   * Test loading state (if applicable).
   */
  test('loading state', async ({ page }) => {
    const fixture = page.locator('#component-loading');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('component-loading.png');
  });

  /**
   * Test error state (if applicable).
   */
  test('error state', async ({ page }) => {
    const fixture = page.locator('#component-error');
    await expect(fixture).toBeVisible();
    await expect(fixture).toHaveScreenshot('component-error.png');
  });
});

/**
 * Responsive tests - test at different viewport sizes.
 */
test.describe('ComponentName Responsive Tests', () => {
  test('mobile viewport (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');

    const fixture = page.locator('#component-default');
    await expect(fixture).toHaveScreenshot('component-mobile.png');
  });

  test('tablet viewport (768px)', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');

    const fixture = page.locator('#component-default');
    await expect(fixture).toHaveScreenshot('component-tablet.png');
  });

  test('desktop viewport (1280px)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto('/visual-tests.html');
    await page.waitForLoadState('networkidle');

    const fixture = page.locator('#component-default');
    await expect(fixture).toHaveScreenshot('component-desktop.png');
  });
});

/**
 * Interactive states - test user interactions.
 */
test.describe('ComponentName Interactive Tests', () => {
  test('click interaction', async ({ page }) => {
    const fixture = page.locator('#component-interactive');
    await fixture.click();
    // Wait for any state changes
    await page.waitForTimeout(100);
    await expect(fixture).toHaveScreenshot('component-after-click.png');
  });

  test('keyboard navigation', async ({ page }) => {
    const fixture = page.locator('#component-interactive');
    await fixture.focus();
    await page.keyboard.press('Enter');
    await expect(fixture).toHaveScreenshot('component-after-enter.png');
  });
});

/**
 * Theme tests (for components with theme support).
 */
test.describe('ComponentName Theme Tests', () => {
  test('light theme', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light' });
    const fixture = page.locator('#component-default');
    await expect(fixture).toHaveScreenshot('component-light-theme.png');
  });

  // Uncomment when dark theme is implemented
  // test('dark theme', async ({ page }) => {
  //   await page.emulateMedia({ colorScheme: 'dark' });
  //   const fixture = page.locator('#component-default');
  //   await expect(fixture).toHaveScreenshot('component-dark-theme.png');
  // });
});
