/**
 * Puzzle Issues Investigation — Playwright Screenshot Capture
 *
 * PURPOSE: Capture screenshots and diagnostics for multiple reported issues:
 * 1. Correct move not registering as correct
 * 2. Stone/board clipping when coordinates disabled
 * 3. Canvas line artifacts at edges
 * 4. Solution tree missing in review mode
 * 5. Coordinate label distance when rotated to bottom
 * 6. Board edge padding when coordinates removed
 *
 * This is an INVESTIGATION script — captures screenshots + console diagnostics.
 * Run with: npx playwright test --config playwright.investigation.config.ts tests/visual/investigation/puzzle-issues-investigation.spec.ts
 */

import { test, expect, type Page } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots', 'puzzle-issues');

const PUZZLE_URL = '/collections/level-beginner';

/** Disable CSS transitions for deterministic screenshots. */
async function disableAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        transition-duration: 0ms !important;
        animation-duration: 0ms !important;
      }
    `,
  });
}

/** Capture console logs for diagnostics. */
function attachDiagnostics(page: Page): { logs: string[]; errors: string[] } {
  const logs: string[] = [];
  const errors: string[] = [];

  page.on('console', (msg) => {
    const text = `[${msg.type()}] ${msg.text()}`;
    logs.push(text);
    if (msg.type() === 'error' || msg.type() === 'warning') {
      errors.push(text);
    }
  });

  return { logs, errors };
}

/** Wait for the puzzle solver to be ready */
async function waitForSolver(page: Page): Promise<void> {
  await page.waitForSelector('[data-component="solver-view"][data-status="solving"]', {
    timeout: 15000,
  });
  // Extra wait for canvas rendering to complete
  await page.waitForTimeout(2000);
}

test.describe('Puzzle Issues Investigation', () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  // =========================================================================
  // Issue #1: Correct Move Not Registering
  // =========================================================================

  test('01 — Correct move registration diagnostics', async ({ page }) => {
    const { logs } = attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);
    await disableAnimations(page);

    // Capture goban state
    const gobanState = await page.evaluate(() => {
      const boardEl = document.querySelector('[data-slot="board"]') as HTMLElement | null;
      const solverView = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      const canvases = boardEl?.querySelectorAll('canvas') ?? [];

      return {
        boardSize: boardEl ? { w: boardEl.clientWidth, h: boardEl.clientHeight } : null,
        boardBounds: boardEl ? boardEl.getBoundingClientRect() : null,
        canvasCount: canvases.length,
        canvasClasses: Array.from(canvases).map(c => c.className),
        solverStatus: solverView?.getAttribute('data-status') ?? null,
      };
    });

    console.log('Goban state before click:', JSON.stringify(gobanState, null, 2));

    // Take screenshot before clicking
    const board = page.locator('[data-slot="board"]');
    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '01-correct-move-before.png') });

    // Click near the center of the board (a reasonable guess for first move)
    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Try clicking at ~40% x, ~40% y (common puzzle area for corner problems)
      const clickX = boardBox.width * 0.4;
      const clickY = boardBox.height * 0.4;
      console.log(`Clicking at board-relative (${clickX.toFixed(0)}, ${clickY.toFixed(0)}) of board (${boardBox.width.toFixed(0)} x ${boardBox.height.toFixed(0)})`);

      await board.click({ position: { x: clickX, y: clickY } });
      await page.waitForTimeout(2000);
    }

    const statusAfter = await page.evaluate(() => {
      const sv = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      const banner = document.querySelector('.solver-answer-banner');
      return {
        status: sv?.getAttribute('data-status') ?? null,
        bannerVisible: !!banner,
        bannerText: banner?.textContent?.trim() ?? null,
      };
    });
    console.log('Status after click:', JSON.stringify(statusAfter));

    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '01-correct-move-after.png') });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01-correct-move-full.png'), fullPage: true });

    // Log all console messages for analysis
    console.log(`\n=== Console logs (${logs.length} messages) ===`);
    logs.filter(l => l.includes('[useGoban]') || l.includes('puzzle')).forEach(l => console.log(l));
  });

  // =========================================================================
  // Issue #2: Stone Clipping When Coordinates Disabled
  // =========================================================================

  test('02 — Stone clipping with coordinates off', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);
    await disableAnimations(page);

    const board = page.locator('[data-slot="board"]');

    // Screenshot with coordinates ON
    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '02-coords-on.png') });

    // Toggle coordinates OFF
    const coordsBtn = page.locator('[aria-label="Hide coordinates"]');
    if (await coordsBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await coordsBtn.click();
      await page.waitForTimeout(1500);

      // Screenshot with coordinates OFF — check for edge clipping
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '02-coords-off.png') });

      // Measure board vs canvas sizes for clipping analysis
      const measurements = await page.evaluate(() => {
        const boardEl = document.querySelector('[data-slot="board"]') as HTMLElement;
        const stoneCanvas = document.querySelector('canvas.StoneLayer') as HTMLCanvasElement | null;
        if (!boardEl || !stoneCanvas) return null;

        const boardRect = boardEl.getBoundingClientRect();
        const canvasRect = stoneCanvas.getBoundingClientRect();

        return {
          board: { w: boardRect.width, h: boardRect.height, top: boardRect.top, left: boardRect.left },
          canvas: { w: canvasRect.width, h: canvasRect.height, top: canvasRect.top, left: canvasRect.left },
          overflow: window.getComputedStyle(boardEl).overflow,
          canvasExtendsLeft: canvasRect.left < boardRect.left,
          canvasExtendsTop: canvasRect.top < boardRect.top,
          canvasExtendsRight: canvasRect.right > boardRect.right,
          canvasExtendsBottom: canvasRect.bottom > boardRect.bottom,
        };
      });
      console.log('Clipping analysis:', JSON.stringify(measurements, null, 2));
    }

    // Also test with horizontal flip + coords off
    const flipHBtn = page.locator('[aria-label="Flip horizontal"]');
    if (await flipHBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await flipHBtn.click();
      await page.waitForTimeout(1500);
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '02-coords-off-flipH.png') });
    }

    // Vertical flip + coords off
    const flipVBtn = page.locator('[aria-label="Flip vertical"]');
    if (await flipVBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await flipVBtn.click();
      await page.waitForTimeout(1500);
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '02-coords-off-flipH-flipV.png') });
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02-clipping-full.png'), fullPage: true });
  });

  // =========================================================================
  // Issue #3: Canvas Line Artifacts
  // =========================================================================

  test('03 — Canvas line artifacts at edges', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);

    const board = page.locator('[data-slot="board"]');
    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '03-artifacts-initial.png') });

    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Click near edges to provoke artifacts
      const edgePositions = [
        { name: 'top-left', x: 0.15, y: 0.15 },
        { name: 'top-right', x: 0.85, y: 0.15 },
        { name: 'bottom-left', x: 0.15, y: 0.85 },
        { name: 'bottom-right', x: 0.85, y: 0.85 },
        { name: 'center', x: 0.5, y: 0.5 },
      ];

      for (const pos of edgePositions) {
        const clickX = boardBox.width * pos.x;
        const clickY = boardBox.height * pos.y;

        await board.click({ position: { x: clickX, y: clickY } });
        await page.waitForTimeout(500);
        await board.screenshot({
          path: path.join(SCREENSHOT_DIR, `03-artifacts-after-${pos.name}.png`),
        });

        // Hover around the edges after click
        await page.mouse.move(
          boardBox.x + boardBox.width * 0.1,
          boardBox.y + boardBox.height * 0.1,
        );
        await page.waitForTimeout(300);
        await board.screenshot({
          path: path.join(SCREENSHOT_DIR, `03-artifacts-hover-${pos.name}.png`),
        });
      }
    }
  });

  // =========================================================================
  // Issue #4: Solution Tree Missing
  // =========================================================================

  test('04 — Solution tree in review mode', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);

    // Check the solution tree container
    const treeContainer = page.locator('[data-testid="solution-tree-container"]');
    const treeState = await page.evaluate(() => {
      const tree = document.querySelector('[data-testid="solution-tree-container"]') as HTMLElement | null;
      return {
        exists: !!tree,
        visible: tree ? tree.offsetParent !== null : false,
        className: tree?.className ?? null,
        childCount: tree?.children.length ?? 0,
        innerHTML: tree?.innerHTML?.substring(0, 200) ?? null,
      };
    });
    console.log('Solution tree state (initial):', JSON.stringify(treeState, null, 2));

    // Check if SolutionReveal component is rendered
    const solutionReveal = page.locator('[data-component="solution-reveal"]');
    const revealExists = await solutionReveal.count();
    console.log(`SolutionReveal component count: ${revealExists}`);

    // Try to solve or fail to trigger review mode
    const board = page.locator('[data-slot="board"]');
    const boardBox = await board.boundingBox();
    if (boardBox) {
      // Click to place a stone (likely wrong)
      await board.click({ position: { x: boardBox.width * 0.5, y: boardBox.height * 0.5 } });
      await page.waitForTimeout(2000);
    }

    const statusAfterMove = await page.evaluate(() => {
      const sv = document.querySelector('[data-component="solver-view"]') as HTMLElement | null;
      return sv?.getAttribute('data-status') ?? null;
    });
    console.log(`Status after move: ${statusAfterMove}`);

    // Check tree container again
    const treeStateAfter = await page.evaluate(() => {
      const tree = document.querySelector('[data-testid="solution-tree-container"]') as HTMLElement | null;
      const reveal = document.querySelector('[data-component="solution-reveal"]');
      return {
        treeVisible: tree ? tree.offsetParent !== null : false,
        treeChildCount: tree?.children.length ?? 0,
        treeClass: tree?.className ?? null,
        revealExists: !!reveal,
      };
    });
    console.log('After move - tree/reveal state:', JSON.stringify(treeStateAfter, null, 2));

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04-solution-tree-full.png'), fullPage: true });
  });

  // =========================================================================
  // Issue #5: Coordinate Label Distance When Rotated
  // =========================================================================

  test('05 — Coordinate label distance after transforms', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);
    await disableAnimations(page);

    const board = page.locator('[data-slot="board"]');

    // Original position
    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-original.png') });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-original-full.png'), fullPage: true });

    // After vertical flip (moves coord labels to bottom)
    const flipVBtn = page.locator('[aria-label="Flip vertical"]');
    if (await flipVBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await flipVBtn.click();
      await page.waitForTimeout(2000);
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-flipped-V.png') });
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-flipped-V-full.png'), fullPage: true });
    }

    // After horizontal flip
    const flipHBtn = page.locator('[aria-label="Flip horizontal"]');
    if (await flipHBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await flipHBtn.click();
      await page.waitForTimeout(2000);
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-flipped-HV.png') });
    }

    // After diagonal flip
    const flipDiagBtn = page.locator('[aria-label="Flip diagonal"]');
    if (await flipDiagBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await flipDiagBtn.click();
      await page.waitForTimeout(2000);
      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-flipped-HVD.png') });
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05-coords-flipped-HVD-full.png'), fullPage: true });
    }
  });

  // =========================================================================
  // Issue #6: Board Edge Padding
  // =========================================================================

  test('06 — Board edge padding when coordinates removed', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);
    await disableAnimations(page);

    const board = page.locator('[data-slot="board"]');

    // Coords on — baseline
    await board.screenshot({ path: path.join(SCREENSHOT_DIR, '06-padding-coords-on.png') });

    // Toggle coords off
    const coordsBtn = page.locator('[aria-label="Hide coordinates"]');
    if (await coordsBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await coordsBtn.click();
      await page.waitForTimeout(1500);

      await board.screenshot({ path: path.join(SCREENSHOT_DIR, '06-padding-coords-off.png') });

      // Measure edge spacing
      const edgeMeasurements = await page.evaluate(() => {
        const boardEl = document.querySelector('[data-slot="board"]') as HTMLElement;
        const stoneCanvas = document.querySelector('canvas.StoneLayer') as HTMLCanvasElement | null;
        if (!boardEl || !stoneCanvas) return null;

        const boardStyle = window.getComputedStyle(boardEl);
        return {
          padding: {
            top: boardStyle.paddingTop,
            right: boardStyle.paddingRight,
            bottom: boardStyle.paddingBottom,
            left: boardStyle.paddingLeft,
          },
          overflow: boardStyle.overflow,
          canvasWidth: stoneCanvas.width,
          canvasHeight: stoneCanvas.height,
          containerWidth: boardEl.clientWidth,
          containerHeight: boardEl.clientHeight,
        };
      });
      console.log('Edge measurement (coords off):', JSON.stringify(edgeMeasurements, null, 2));
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06-padding-full.png'), fullPage: true });
  });

  // =========================================================================
  // Overview: Full page with all components visible
  // =========================================================================

  test('07 — Full page overview for visual inspection', async ({ page }) => {
    attachDiagnostics(page);

    await page.goto(PUZZLE_URL);
    await waitForSolver(page);
    await disableAnimations(page);

    // Capture sidebar state (skip button, hint, toolbar)
    const sidebar = page.locator('.solver-sidebar-col');
    if (await sidebar.isVisible({ timeout: 3000 }).catch(() => false)) {
      await sidebar.screenshot({ path: path.join(SCREENSHOT_DIR, '07-sidebar.png') });
    }

    // Capture transform bar
    const transformBar = page.locator('[data-testid="transform-bar"]');
    if (await transformBar.isVisible({ timeout: 2000 }).catch(() => false)) {
      await transformBar.screenshot({ path: path.join(SCREENSHOT_DIR, '07-toolbar.png') });
    }

    // Full page screenshots at different viewports
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07-desktop-1440.png'), fullPage: true });

    // Tablet
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07-tablet-768.png'), fullPage: true });

    // Mobile
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07-mobile-375.png'), fullPage: true });
  });
});
