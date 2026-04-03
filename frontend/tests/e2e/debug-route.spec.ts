import { test, expect } from '@playwright/test';

test('tag-connection page loads puzzles with board', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('/yen-go/collections/tag-connection', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  const bodyText = await page.textContent('body');
  console.log('Has "No puzzles":', bodyText?.includes('No puzzles'));
  console.log('Has "Connection":', bodyText?.includes('Connection'));
  console.log('Page errors:', errors);

  // Check for puzzle content (goban board elements)
  const testIds = await page.evaluate(() => {
    const els = document.querySelectorAll('[data-testid]');
    return Array.from(els).map(el => el.getAttribute('data-testid'));
  });
  console.log('Test IDs:', testIds);

  // The page should NOT show "No puzzles available"
  const noPuzzles = bodyText?.includes('No puzzles');
  expect(noPuzzles).toBe(false);
});
