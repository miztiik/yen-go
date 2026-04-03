/**
 * Quick screenshot test to verify UI changes
 */
import { test, expect } from '@playwright/test';

test('puzzle view screenshot check', async ({ page }) => {
  // Navigate to a puzzle collection
  await page.goto('http://localhost:5175/');
  
  // Wait for page to load
  await page.waitForTimeout(1000);
  
  // Take screenshot of home page
  await page.screenshot({ path: 'test-results/screenshots/home.png', fullPage: true });
  
  // Click on Collections
  await page.getByText('Collections').first().click();
  await page.waitForTimeout(1000);
  
  // Take screenshot of collections
  await page.screenshot({ path: 'test-results/screenshots/collections.png', fullPage: true });
  
  // Click on first available collection
  const firstCard = page.locator('[data-testid="collection-card"]').first();
  if (await firstCard.isVisible()) {
    await firstCard.click();
    await page.waitForTimeout(1000);
    
    // Take screenshot of puzzle view
    await page.screenshot({ path: 'test-results/screenshots/puzzle-view.png', fullPage: true });
  }
});
