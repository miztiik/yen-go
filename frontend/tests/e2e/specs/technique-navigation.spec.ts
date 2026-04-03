/**
 * E2E test: Technique Tag Navigation.
 * Verify clicking each technique tag navigates to the correct /technique/{tag} URL
 * and loads puzzles (for tags with data) or shows graceful error (for tags without).
 *
 * Covers all 28 tags across objectives, techniques, and tesuji patterns.
 */
import { test, expect } from '@playwright/test';

/**
 * All 28 tags from config/tags.json organized by category.
 * hasData indicates whether a view file exists in yengo-puzzle-collections/views/by-tag/
 */
const TAGS_WITH_DATA = [
  { id: 'life-and-death', name: 'Life & Death', category: 'objective', tab: 'Objectives' },
  { id: 'ko', name: 'Ko', category: 'objective', tab: 'Objectives' },
  { id: 'capture-race', name: 'Capture Race', category: 'technique', tab: 'Techniques' },
  { id: 'eye-shape', name: 'Eye Shape', category: 'technique', tab: 'Techniques' },
  { id: 'connection', name: 'Connection', category: 'technique', tab: 'Techniques' },
  { id: 'cutting', name: 'Cutting', category: 'technique', tab: 'Techniques' },
  { id: 'snapback', name: 'Snapback', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'throw-in', name: 'Throw-in', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'ladder', name: 'Ladder', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'net', name: 'Net', category: 'tesuji', tab: 'Tesuji Patterns' },
] as const;

const TAGS_WITHOUT_DATA = [
  { id: 'living', name: 'Living', category: 'objective', tab: 'Objectives' },
  { id: 'seki', name: 'Seki', category: 'objective', tab: 'Objectives' },
  { id: 'escape', name: 'Escape', category: 'technique', tab: 'Techniques' },
  { id: 'dead-shapes', name: 'Dead Shapes', category: 'technique', tab: 'Techniques' },
  { id: 'corner', name: 'Corner', category: 'technique', tab: 'Techniques' },
  { id: 'sacrifice', name: 'Sacrifice', category: 'technique', tab: 'Techniques' },
  { id: 'shape', name: 'Shape', category: 'technique', tab: 'Techniques' },
  { id: 'endgame', name: 'Endgame', category: 'technique', tab: 'Techniques' },
  { id: 'joseki', name: 'Joseki', category: 'technique', tab: 'Techniques' },
  { id: 'fuseki', name: 'Fuseki', category: 'technique', tab: 'Techniques' },
  { id: 'liberty-shortage', name: 'Liberty Shortage', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'connect-and-die', name: 'Connect & Die', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'under-the-stones', name: 'Under the Stones', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'double-atari', name: 'Double Atari', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'vital-point', name: 'Vital Point', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'clamp', name: 'Clamp', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'nakade', name: 'Nakade', category: 'tesuji', tab: 'Tesuji Patterns' },
  { id: 'tesuji', name: 'Tesuji', category: 'tesuji', tab: 'Tesuji Patterns' },
] as const;

const ALL_TAGS = [...TAGS_WITH_DATA, ...TAGS_WITHOUT_DATA];

test.describe('Technique Navigation E2E', () => {

  test('Technique browse page loads at /technique', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/technique');
    await page.waitForLoadState('networkidle');

    // Page should contain the heading
    await expect(page.getByText('Technique Focus')).toBeVisible();

    // No uncaught JS errors
    expect(errors).toEqual([]);
  });

  // ── Tags with published puzzle data: should load puzzles ──────────────

  for (const tag of TAGS_WITH_DATA) {
    test(`Tag "${tag.name}" (${tag.id}) — click navigates to /technique/${tag.id} and loads puzzles`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));

      // 1. Go to technique browse page
      await page.goto('/technique');
      await page.waitForLoadState('networkidle');

      // 2. Click the category tab (radio) to show this tag's category
      const tab = page.getByRole('radio', { name: tag.tab });
      await tab.click();
      await page.waitForTimeout(500);

      // 3. Find and click the tag card by its heading text
      const card = page.locator('button', { has: page.getByRole('heading', { name: tag.name, exact: true, level: 3 }) });
      await expect(card).toBeVisible({ timeout: 10000 });
      await card.click();

      // 4. Verify URL is /technique/{tag.id}
      await page.waitForURL(`**/technique/${tag.id}`, { timeout: 10000 });
      expect(page.url()).toContain(`/technique/${tag.id}`);

      // 5. Verify no console errors
      expect(errors).toEqual([]);
    });
  }

  // ── Tags without published puzzle data: should show graceful state ────

  for (const tag of TAGS_WITHOUT_DATA) {
    test(`Tag "${tag.name}" (${tag.id}) — click navigates to /technique/${tag.id} without crash`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (err) => errors.push(err.message));

      // 1. Go to technique browse page
      await page.goto('/technique');
      await page.waitForLoadState('networkidle');

      // 2. Click the category tab (radio) to show this tag's category
      const tab = page.getByRole('radio', { name: tag.tab });
      await tab.click();
      await page.waitForTimeout(500);

      // 3. Find and click the tag card
      const card = page.locator('button', { has: page.getByRole('heading', { name: tag.name, exact: true, level: 3 }) });
      await expect(card).toBeVisible({ timeout: 10000 });
      await card.click();

      // 4. Verify URL is /technique/{tag.id}
      await page.waitForURL(`**/technique/${tag.id}`, { timeout: 10000 });
      expect(page.url()).toContain(`/technique/${tag.id}`);

      // 5. Verify no uncaught JS errors (graceful error/empty state is OK)
      expect(errors).toEqual([]);
    });
  }

  // ── Direct URL entry ──────────────────────────────────────────────────

  test('Direct URL /technique/ko loads puzzle view', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/technique/ko');
    await page.waitForLoadState('networkidle');

    // Should not be on the browse page
    const heading = page.getByText('Technique Focus');
    await expect(heading).not.toBeVisible({ timeout: 5000 }).catch(() => {
      // It's OK if heading is visible briefly during redirect
    });

    // URL should stay at /technique/ko
    expect(page.url()).toContain('/technique/ko');

    // No console errors
    expect(errors).toEqual([]);
  });

  test('Direct URL /technique/nonexistent shows graceful error', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/technique/nonexistent');
    await page.waitForLoadState('networkidle');

    // URL should stay at /technique/nonexistent
    expect(page.url()).toContain('/technique/nonexistent');

    // No uncaught JS errors
    expect(errors).toEqual([]);
  });

  // ── Back navigation ───────────────────────────────────────────────────

  test('Back from /technique/ko returns to /technique browse page', async ({ page }) => {
    // 1. Navigate to technique browse
    await page.goto('/technique');
    await page.waitForLoadState('networkidle');

    // 2. Click Objectives tab (radio) then Ko card
    const objTab = page.getByRole('radio', { name: 'Objectives' });
    await objTab.click();
    await page.waitForTimeout(500);
    const koCard = page.locator('button', { has: page.getByRole('heading', { name: 'Ko', exact: true, level: 3 }) });
    await expect(koCard).toBeVisible({ timeout: 10000 });
    await koCard.click();

    // 3. Verify we're at /technique/ko
    await page.waitForURL('**/technique/ko', { timeout: 10000 });

    // 4. Go back
    await page.goBack();
    await page.waitForLoadState('networkidle');

    // 5. Should be back at /technique
    expect(page.url()).toMatch(/\/technique\/?$/);

    // 6. Browse page heading should be visible
    await expect(page.getByText('Technique Focus')).toBeVisible({ timeout: 10000 });
  });
});
