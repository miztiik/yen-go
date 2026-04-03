import { test, expect } from '@playwright/test';

test('tag-connection route renders collection view', async ({ page }) => {
  // Capture console errors
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(err.message));

  await page.goto('/yen-go/collections/tag-connection', { waitUntil: 'networkidle' });

  // Log what we see
  const title = await page.title();
  console.log('Page title:', title);

  const bodyText = await page.textContent('body');
  console.log('Body text (first 500 chars):', bodyText?.slice(0, 500));

  // Check if we see the home page or the collection view
  const homeHeading = await page.locator('text=Ready for Go, Sensei?').count();
  console.log('Home page visible:', homeHeading > 0);

  // Check for collection-related content
  const puzzleSetPlayer = await page.locator('[data-testid]').evaluateAll(els =>
    els.map(el => el.getAttribute('data-testid')).filter(Boolean)
  );
  console.log('data-testid elements:', puzzleSetPlayer);

  // Log errors
  if (errors.length > 0) {
    console.log('Page errors:', errors);
  }

  // The route should NOT show home page
  expect(homeHeading).toBe(0);
});
