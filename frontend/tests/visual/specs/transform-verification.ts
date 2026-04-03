/**
 * Playwright screenshot script — captures board state before/after each transform.
 * Used for visual verification by a 1P Go player (AI review).
 *
 * Takes screenshots of:
 * 1. Initial board state (auto-zoomed, with coordinates)
 * 2. After horizontal flip
 * 3. After vertical flip
 * 4. After diagonal flip
 * 5. After color swap
 * 6. Toolbar state (5 buttons: 4 transforms + coords)
 * 7. Skip button styling
 * 8. Board after stone placement (validation test)
 * 9. Undo / reset test
 * 10. Coordinate toggle test
 * 11. Hover stone test
 *
 * Run: npx playwright test --config=playwright.screenshots.config.ts tests/screenshots/transform-verification.ts
 */
import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const SCREENSHOT_DIR = 'tests/screenshots/transform-verification';
const PUZZLE_URL = '/collections/tag-life-and-death';

test.describe('Transform Visual Verification', () => {
  test.beforeAll(() => {
    // Ensure screenshot directory exists
    const dir = path.resolve(SCREENSHOT_DIR);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('00 — Goban diagnostics (canvas layers, board container)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    const diagnostics = await page.evaluate(() => {
      const canvas = document.querySelector('canvas.StoneLayer') as HTMLCanvasElement | null;
      const penLayer = document.querySelector('canvas.PenLayer') as HTMLCanvasElement | null;
      const shadowLayer = document.querySelector('canvas.ShadowLayer') as HTMLCanvasElement | null;
      const boardEl = document.querySelector('[data-slot="board"]') as HTMLElement | null;
      const solverView = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      const allCanvases = document.querySelectorAll('[data-slot="board"] canvas');

      return {
        stoneLayerExists: !!canvas,
        stoneLayerSize: canvas ? { w: canvas.width, h: canvas.height } : null,
        penLayerExists: !!penLayer,
        penLayerSize: penLayer ? { w: penLayer.width, h: penLayer.height } : null,
        shadowLayerExists: !!shadowLayer,
        shadowLayerSize: shadowLayer ? { w: shadowLayer.width, h: shadowLayer.height } : null,
        boardContainerSize: boardEl ? { w: boardEl.clientWidth, h: boardEl.clientHeight } : null,
        boardContainerBounds: boardEl ? boardEl.getBoundingClientRect() : null,
        canvasCount: allCanvases.length,
        canvasClasses: Array.from(allCanvases).map(c => c.className),
        solverStatus: solverView?.getAttribute('data-status') ?? null,
      };
    });
    console.log('Goban diagnostics:', JSON.stringify(diagnostics, null, 2));
  });

  test('01 — Initial board state (auto-zoomed, coordinates visible)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/01-initial-board.png`,
      fullPage: true,
    });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/01-initial-board-only.png`,
    });
  });

  test('02 — Horizontal flip transform', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/02-flipH-before.png`,
    });

    const flipHBtn = page.locator('[aria-label="Flip horizontal"]');
    await expect(flipHBtn).toBeVisible();
    await flipHBtn.click();
    await page.waitForTimeout(2000);

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/02-flipH-after.png`,
    });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/02-flipH-full-page.png`,
      fullPage: true,
    });
  });

  test('03 — Vertical flip transform', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/03-flipV-before.png`,
    });

    const flipVBtn = page.locator('[aria-label="Flip vertical"]');
    await expect(flipVBtn).toBeVisible();
    await flipVBtn.click();
    await page.waitForTimeout(2000);

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/03-flipV-after.png`,
    });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/03-flipV-full-page.png`,
      fullPage: true,
    });
  });

  test('04 — Diagonal flip transform', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/04-flipDiag-before.png`,
    });

    const flipDiagBtn = page.locator('[aria-label="Flip diagonal"]');
    await expect(flipDiagBtn).toBeVisible();
    await flipDiagBtn.click();
    await page.waitForTimeout(2000);

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/04-flipDiag-after.png`,
    });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/04-flipDiag-full-page.png`,
      fullPage: true,
    });
  });

  test('05 — Color swap transform', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/05-colorSwap-before.png`,
    });

    const swapBtn = page.locator('[aria-label="Swap colors"]');
    await expect(swapBtn).toBeVisible();
    await swapBtn.click();
    await page.waitForTimeout(2000);

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/05-colorSwap-after.png`,
    });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/05-colorSwap-full-page.png`,
      fullPage: true,
    });
  });

  test('06 — Toolbar state (5 buttons: 4 transforms + coords toggle)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const transformBar = page.locator('[data-testid="transform-bar"]');
    await expect(transformBar).toBeVisible({ timeout: 10000 });

    const buttons = transformBar.locator('button');
    const count = await buttons.count();
    console.log(`Transform bar button count: ${count}`);

    await transformBar.screenshot({
      path: `${SCREENSHOT_DIR}/06-toolbar-buttons.png`,
    });
  });

  test('07 — Skip button styling', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const sidebar = page.locator('.solver-sidebar-col');
    if (await sidebar.count() > 0) {
      await sidebar.screenshot({
        path: `${SCREENSHOT_DIR}/07-sidebar-skip-button.png`,
      });
    }
  });

  test('08 — Board after stone placement (validation test)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/08-validation-before.png`,
    });

    // Diagnose the goban state before clicking
    const preClickDiag = await page.evaluate(() => {
      const stoneLayer = document.querySelector('canvas.StoneLayer') as HTMLCanvasElement | null;
      const boardEl = document.querySelector('[data-slot="board"]') as HTMLElement | null;
      const solverView = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      return {
        stoneLayerExists: !!stoneLayer,
        stoneLayerSize: stoneLayer ? { w: stoneLayer.width, h: stoneLayer.height } : null,
        boardContainerSize: boardEl ? { w: boardEl.clientWidth, h: boardEl.clientHeight } : null,
        solverStatus: solverView?.getAttribute('data-status') ?? null,
        canvasCount: boardEl ? boardEl.querySelectorAll('canvas').length : 0,
      };
    });
    console.log(`Pre-click diagnostics: ${JSON.stringify(preClickDiag)}`);

    const solverView = page.locator('[data-component="solver-view"]');
    const statusBefore = await solverView.getAttribute('data-status');
    console.log(`Status before click: ${statusBefore}`);

    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Board coordinate labels take ~10-15% of width/height.
      // Visible board spans roughly A13-G19 (upper-left corner).
      // White stones at A18, B18, C18, D18, D19 — those are in the top-left area.
      // Click at ~65% width, ~55% height to target E-F row 15-16 area (clearly empty).
      const clickX = boardBox.width * 0.65;
      const clickY = boardBox.height * 0.55;
      console.log(`Clicking at board-relative position: (${clickX.toFixed(0)}, ${clickY.toFixed(0)}) of board size (${boardBox.width.toFixed(0)} x ${boardBox.height.toFixed(0)})`);

      await board.click({
        position: { x: clickX, y: clickY },
      });
      await page.waitForTimeout(2000);
    }

    // Check post-click diagnostics
    const postClickDiag = await page.evaluate(() => {
      const solverView = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      const answerBanner = document.querySelector('[data-testid="answer-banner"]') as HTMLElement | null;
      return {
        solverStatus: solverView?.getAttribute('data-status') ?? null,
        answerBannerVisible: !!answerBanner,
        answerBannerText: answerBanner?.textContent?.trim() ?? null,
      };
    });
    console.log(`Post-click diagnostics: ${JSON.stringify(postClickDiag)}`);

    const statusAfter = await solverView.getAttribute('data-status');
    console.log(`Status after click: ${statusAfter}`);

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/08-validation-after-click.png`,
    });

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/08-validation-full-page.png`,
      fullPage: true,
    });
  });

  test('09 — Undo functionality', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/09-undo-initial.png`,
    });

    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Use the same improved click position as test 08:
      // ~65% width, ~55% height targets E-F row 15-16 area (clearly empty).
      const clickX = boardBox.width * 0.65;
      const clickY = boardBox.height * 0.55;
      console.log(`[Test 09] Clicking at board-relative position: (${clickX.toFixed(0)}, ${clickY.toFixed(0)})`);

      await board.click({
        position: { x: clickX, y: clickY },
      });
      await page.waitForTimeout(2500);
    }

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/09-undo-after-move.png`,
    });

    const solverView = page.locator('[data-component="solver-view"]');
    const statusAfterMove = await solverView.getAttribute('data-status');
    console.log(`[Test 09] Status after move: ${statusAfterMove}`);

    // Log all visible buttons for debugging
    const visibleButtons = await page.evaluate(() => {
      const buttons = document.querySelectorAll('button');
      return Array.from(buttons)
        .filter(b => b.offsetParent !== null) // only visible buttons
        .map(b => ({
          text: b.textContent?.trim() ?? '',
          ariaLabel: b.getAttribute('aria-label') ?? '',
          testId: b.getAttribute('data-testid') ?? '',
          disabled: b.disabled,
        }));
    });
    console.log(`[Test 09] Visible buttons: ${JSON.stringify(visibleButtons)}`);

    // Try multiple selectors for the undo button:
    // 1. The always-visible action-bar Undo button
    // 2. The QuickControls undo button (data-testid="undo-button")
    // 3. Any button containing "Undo" text
    const undoBtnActionBar = page.locator('[data-testid="action-bar"] button:has-text("Undo")');
    const undoBtnQuickControls = page.locator('[data-testid="undo-button"]');
    const undoBtnGeneric = page.locator('button:has-text("Undo")');

    let undoClicked = false;

    // First try the always-visible action bar undo
    if (await undoBtnActionBar.isVisible({ timeout: 3000 }).catch(() => false)) {
      console.log('[Test 09] Found Undo in action-bar, clicking...');
      await undoBtnActionBar.click();
      undoClicked = true;
    }
    // Then try QuickControls undo button
    else if (await undoBtnQuickControls.isVisible({ timeout: 2000 }).catch(() => false)) {
      const isDisabled = await undoBtnQuickControls.isDisabled();
      console.log(`[Test 09] Found QuickControls undo button, disabled=${isDisabled}`);
      if (!isDisabled) {
        await undoBtnQuickControls.click();
        undoClicked = true;
      }
    }
    // Fallback: any button with "Undo" text
    else if (await undoBtnGeneric.first().isVisible({ timeout: 2000 }).catch(() => false)) {
      console.log('[Test 09] Found generic Undo button, clicking...');
      await undoBtnGeneric.first().click();
      undoClicked = true;
    }
    else {
      console.log('[Test 09] No Undo button found. Status may not have changed to wrong.');
    }

    if (undoClicked) {
      await page.waitForTimeout(1500);

      const statusAfterUndo = await solverView.getAttribute('data-status');
      console.log(`[Test 09] Status after undo: ${statusAfterUndo}`);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/09-undo-after-undo.png`,
      });

      // Try a second move at a slightly different empty position
      if (boardBox) {
        const retryX = boardBox.width * 0.55;
        const retryY = boardBox.height * 0.65;
        console.log(`[Test 09] Retry click at board-relative position: (${retryX.toFixed(0)}, ${retryY.toFixed(0)})`);

        await board.click({
          position: { x: retryX, y: retryY },
        });
        await page.waitForTimeout(1500);
      }

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/09-undo-after-retry.png`,
      });

      const statusAfterRetry = await solverView.getAttribute('data-status');
      console.log(`[Test 09] Status after retry: ${statusAfterRetry}`);
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/09-undo-full-page.png`,
      fullPage: true,
    });
  });

  test('10 — Coordinate toggle', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    await board.screenshot({
      path: `${SCREENSHOT_DIR}/10-coords-on.png`,
    });

    const coordsBtn = page.locator('[aria-label="Hide coordinates"]');
    if (await coordsBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await coordsBtn.click();
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/10-coords-off.png`,
      });

      const showBtn = page.locator('[aria-label="Show coordinates"]');
      if (await showBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await showBtn.click();
        await page.waitForTimeout(1000);

        await board.screenshot({
          path: `${SCREENSHOT_DIR}/10-coords-back-on.png`,
        });
      }
    }
  });

  test('11 — Hover stone visibility', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await page.waitForTimeout(3000);

    const board = page.locator('[data-slot="board"]');
    await expect(board).toBeVisible({ timeout: 10000 });

    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Move to a clearly empty intersection deep inside the grid.
      // ~65% width, ~65% height should be around E-F row 15-16 (clearly empty).
      const hoverX1 = boardBox.x + boardBox.width * 0.65;
      const hoverY1 = boardBox.y + boardBox.height * 0.65;
      console.log(`[Test 11] Hovering at absolute position: (${hoverX1.toFixed(0)}, ${hoverY1.toFixed(0)})`);

      await page.mouse.move(hoverX1, hoverY1);
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/11-hover-stone-position1.png`,
      });

      // Wait a bit more and take another screenshot (canvas may need time to render)
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/11-hover-stone-position1-delayed.png`,
      });

      // Move to a second clearly empty position (~50% width, ~75% height)
      const hoverX2 = boardBox.x + boardBox.width * 0.50;
      const hoverY2 = boardBox.y + boardBox.height * 0.75;
      console.log(`[Test 11] Moving to second position: (${hoverX2.toFixed(0)}, ${hoverY2.toFixed(0)})`);

      await page.mouse.move(hoverX2, hoverY2);
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/11-hover-stone-position2.png`,
      });

      // Wait again and capture for good measure
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/11-hover-stone-position2-delayed.png`,
      });

      // Move to a third position to show the hover stone follows the cursor
      // ~75% width, ~45% height — another clearly empty area
      const hoverX3 = boardBox.x + boardBox.width * 0.75;
      const hoverY3 = boardBox.y + boardBox.height * 0.45;
      console.log(`[Test 11] Moving to third position: (${hoverX3.toFixed(0)}, ${hoverY3.toFixed(0)})`);

      await page.mouse.move(hoverX3, hoverY3);
      await page.waitForTimeout(1000);

      await board.screenshot({
        path: `${SCREENSHOT_DIR}/11-hover-stone-position3.png`,
      });
    }
  });
});
