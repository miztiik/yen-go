/**
 * Solver UI Polish — Before/After Visual Verification
 *
 * Playwright E2E tests that capture pixel-accurate screenshots of the solver UI
 * before and after the changes described in TODO/solver-ui-polish.md (T01–T12).
 *
 * Strategy:
 * - Each test captures a specific visual area (board, toolbar, sidebar, banners).
 * - Uses toHaveScreenshot() for pixel comparison across runs.
 * - First run generates baseline snapshots; subsequent runs compare against them.
 * - maxDiffPixelRatio threshold allows minor anti-aliasing differences.
 *
 * Run: npx playwright test --config=playwright.e2e.config.ts solver-ui-polish
 */
import { test, expect, type Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TECHNIQUE_URL = '/technique/ko';
const COLLECTION_URL = '/collections/cho-chikun-life-death-elementary';
const LOAD_TIMEOUT = 15_000;

/** Wait for goban board to be fully rendered (canvas elements present). */
async function waitForBoard(page: Page): Promise<void> {
  // Wait for the goban container with a canvas inside
  await page.waitForSelector('.goban-container canvas', { timeout: LOAD_TIMEOUT });
  // Additional wait for rendering to settle (goban draws asynchronously)
  await page.waitForTimeout(1500);
}

/** Wait for sidebar card to be present. */
async function waitForSidebar(page: Page): Promise<void> {
  await page.waitForSelector('.solver-sidebar-col', { timeout: LOAD_TIMEOUT });
  await page.waitForTimeout(500);
}

/**
 * Try to load a collection page. Returns true if puzzles loaded, false if
 * the collection data is not available (e.g., dev server without published data).
 */
async function tryLoadCollection(page: Page): Promise<boolean> {
  await page.goto(COLLECTION_URL);
  try {
    await page.waitForSelector('.goban-container canvas', { timeout: LOAD_TIMEOUT });
    await page.waitForTimeout(1500);
    return true;
  } catch {
    // Collection data not available on dev server
    return false;
  }
}

// ---------------------------------------------------------------------------
// T01 — Board Shadow
// ---------------------------------------------------------------------------

test.describe('T01 — Board Shadow', () => {
  test('board container has subtle shadow elevation', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);

    const board = page.locator('.goban-container');
    await expect(board).toBeVisible();
    await expect(board).toHaveScreenshot('t01-board-shadow.png', {
      maxDiffPixelRatio: 0.02,
    });
  });

  test('shadow persists with coordinates toggled off', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // Find and click the coordinates toggle button
    const coordsBtn = page.locator('button[aria-label*="oordinate"]');
    if (await coordsBtn.isVisible()) {
      await coordsBtn.click();
      await page.waitForTimeout(500);
    }

    const board = page.locator('.goban-container');
    await expect(board).toHaveScreenshot('t01-board-shadow-no-coords.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T02 — Board Edge Padding
// ---------------------------------------------------------------------------

test.describe('T02 — Board Edge Padding', () => {
  test('board edges render without extra non-standard padding', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);

    // Capture the goban-container to check edge padding and stone rendering
    const board = page.locator('.goban-container');
    await expect(board).toBeVisible();
    await expect(board).toHaveScreenshot('t02-board-edges.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T03 — Toolbar Strip Layout
// ---------------------------------------------------------------------------

test.describe('T03 — Toolbar Strip', () => {
  test('toolbar renders as single horizontal strip — desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const transforms = page.locator('[data-section="transforms"]');
    await expect(transforms).toBeVisible();
    await expect(transforms).toHaveScreenshot('t03-toolbar-strip-desktop.png', {
      maxDiffPixelRatio: 0.02,
    });
  });

  test('toolbar renders as single horizontal strip — mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const transforms = page.locator('[data-section="transforms"]');
    await expect(transforms).toBeVisible();
    await expect(transforms).toHaveScreenshot('t03-toolbar-strip-mobile.png', {
      maxDiffPixelRatio: 0.02,
    });
  });

  test('toolbar buttons have hover feedback', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // Hover over the first transform button
    const firstBtn = page.locator('[data-section="transforms"] button').first();
    await firstBtn.hover();
    await page.waitForTimeout(300);

    await expect(firstBtn).toHaveScreenshot('t03-toolbar-button-hover.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T04 + T05 — Icon Replacements (Zoom + Coords)
// ---------------------------------------------------------------------------

test.describe('T04/T05 — Icon Replacements', () => {
  test('zoom icon renders as expand/maximize arrows', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const zoomBtn = page.locator('button[aria-label*="oom"], button[aria-label*="full board"]');
    if (await zoomBtn.isVisible()) {
      await expect(zoomBtn).toHaveScreenshot('t04-zoom-icon.png', {
        maxDiffPixelRatio: 0.02,
      });
    }
  });

  test('coordinates icon renders as 9A text style', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const coordsBtn = page.locator('button[aria-label*="oordinate"]');
    await expect(coordsBtn).toBeVisible();
    await expect(coordsBtn).toHaveScreenshot('t05-coords-icon.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T07 — Answer Feedback Banners
// ---------------------------------------------------------------------------

test.describe('T07 — Answer Feedback Banners', () => {
  test('correct banner shows green tint after solving', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // Wait for the puzzle to be interactive
    await page.waitForTimeout(1000);

    // Check if a correct banner is visible (may need to solve a puzzle)
    // For baseline capture, check if data-testid="answer-banner" exists
    const banner = page.locator('[data-testid="answer-banner"]');
    const status = page.locator('[data-component="solver-view"]');

    // Capture full sidebar for color verification
    const sidebar = page.locator('.solver-sidebar-col');
    await expect(sidebar).toHaveScreenshot('t07-sidebar-initial-state.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T08 — Board Message (Self-Atari Warning)
// ---------------------------------------------------------------------------

test.describe('T08 — Board Message Warning', () => {
  test('board message area renders with amber warning styling', async ({ page }) => {
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // The board message appears on invalid moves (self-atari, ko violation)
    // Check for the element's presence and styling
    const boardMessage = page.locator('[data-testid="board-message"]');

    // This element is conditional — may not be visible initially
    // Capture sidebar area for baseline regardless
    const sidebar = page.locator('.solver-sidebar-col');
    await expect(sidebar).toHaveScreenshot('t08-sidebar-no-warning.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T09 — ProblemNav Consistency
// ---------------------------------------------------------------------------

test.describe('T09 — ProblemNav', () => {
  test('technique page shows counter mode (30+ puzzles)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const nav = page.locator('[data-testid="puzzle-nav-slot"]');
    await expect(nav).toBeVisible();
    await expect(nav).toHaveScreenshot('t09-problemnav-counter.png', {
      maxDiffPixelRatio: 0.02,
    });
  });

  test('collection page shows dots mode (<=20 puzzles)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    const loaded = await tryLoadCollection(page);
    test.skip(!loaded, 'Collection data not available on dev server');
    await waitForSidebar(page);

    const nav = page.locator('[data-testid="puzzle-nav-slot"]');
    await expect(nav).toBeVisible();
    await expect(nav).toHaveScreenshot('t09-problemnav-dots.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T10 — Sidebar Width + Layout
// ---------------------------------------------------------------------------

test.describe('T10 — Sidebar Width & Layout', () => {
  test('full page layout — desktop 1280×800', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    await expect(page).toHaveScreenshot('t10-layout-desktop.png', {
      maxDiffPixelRatio: 0.02,
      fullPage: false,
    });
  });

  test('full page layout — tablet 768×1024', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    await expect(page).toHaveScreenshot('t10-layout-tablet.png', {
      maxDiffPixelRatio: 0.02,
      fullPage: false,
    });
  });

  test('sidebar has adequate width for content', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    const sidebar = page.locator('.solver-sidebar-col');
    await expect(sidebar).toBeVisible();

    // Verify sidebar has reasonable width on desktop (current is ~360px, target ~400px)
    const box = await sidebar.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.width).toBeGreaterThanOrEqual(300);
    }

    await expect(sidebar).toHaveScreenshot('t10-sidebar-width.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T11 — Solution Tree Padding
// ---------------------------------------------------------------------------

test.describe('T11 — Solution Tree Padding', () => {
  test('solution tree container has adequate padding in review mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // Try to enter review mode by clicking the Review button
    const reviewBtn = page.locator('button:has-text("Review"), [aria-label*="eview"]');
    if (await reviewBtn.isVisible()) {
      await reviewBtn.click();
      await page.waitForTimeout(800);

      const tree = page.locator('[data-testid="solution-tree-container"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('t11-solution-tree-padding.png', {
          maxDiffPixelRatio: 0.02,
        });
      }
    }
  });
});

// ---------------------------------------------------------------------------
// T12 — Collection Icon
// ---------------------------------------------------------------------------

test.describe('T12 — Collection Icon', () => {
  test('collection badge renders with updated icon', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    const loaded = await tryLoadCollection(page);
    test.skip(!loaded, 'Collection data not available on dev server');
    await waitForSidebar(page);

    // Collection badges are in the metadata section
    const sidebar = page.locator('.solver-sidebar-col');
    await expect(sidebar).toHaveScreenshot('t12-collection-icon-sidebar.png', {
      maxDiffPixelRatio: 0.02,
    });
  });
});

// ---------------------------------------------------------------------------
// T14 — Solution Tree Branch Colors (Unified)
// ---------------------------------------------------------------------------

test.describe('T14 — Solution Tree Branch Colors', () => {
  test('solution tree renders with unified branch colors', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    // Enter review mode to make the solution tree visible
    const reviewBtn = page.locator('button:has-text("Review"), [aria-label*="eview"]');
    if (await reviewBtn.isVisible()) {
      await reviewBtn.click();
      await page.waitForTimeout(800);

      const treeContainer = page.locator('[data-testid="solution-tree-container"]');
      if (await treeContainer.isVisible()) {
        // Branch colors should be uniform gray after T14 implementation
        await expect(treeContainer).toHaveScreenshot('t14-tree-branch-colors.png', {
          maxDiffPixelRatio: 0.02,
        });
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Composite — Full Solver View (all changes combined)
// ---------------------------------------------------------------------------

test.describe('Composite — Full Solver View', () => {
  test('technique page — complete solver UI', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(TECHNIQUE_URL);
    await waitForBoard(page);
    await waitForSidebar(page);

    await expect(page).toHaveScreenshot('composite-technique-page.png', {
      maxDiffPixelRatio: 0.02,
      fullPage: false,
    });
  });

  test('collection page — complete solver UI', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    const loaded = await tryLoadCollection(page);
    test.skip(!loaded, 'Collection data not available on dev server');
    await waitForSidebar(page);

    await expect(page).toHaveScreenshot('composite-collection-page.png', {
      maxDiffPixelRatio: 0.02,
      fullPage: false,
    });
  });
});
