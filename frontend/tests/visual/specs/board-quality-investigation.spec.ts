/**
 * Board Quality Investigation — Playwright Screenshot Capture
 *
 * PURPOSE: Capture screenshots of the Go board across multiple routes
 * to document the current rendering quality issues (flat stones, missing
 * wood texture) and support the root cause analysis.
 *
 * This is an INVESTIGATION script — it does NOT assert pass/fail.
 * Screenshots are saved to: frontend/tests/visual/investigation/screenshots/
 *
 * Run with: npx playwright test --config playwright.config.ts tests/visual/investigation/board-quality-investigation.spec.ts
 */

import { test, type Page } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

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

/** Capture console logs and network errors for diagnostics. */
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

  page.on('response', (response) => {
    if (response.status() >= 400) {
      errors.push(`[HTTP ${response.status()}] ${response.url()}`);
    }
  });

  return { logs, errors };
}

/** Detect what renderer type (SVG or Canvas) the goban is using. */
async function detectRendererType(page: Page): Promise<string> {
  return await page.evaluate(() => {
    const boardSlot = document.querySelector('[data-slot="board"]');
    if (!boardSlot) return 'NO_BOARD_FOUND';

    const svgElement = boardSlot.querySelector('svg');
    const canvasElement = boardSlot.querySelector('canvas');

    if (svgElement && canvasElement) return 'BOTH_SVG_AND_CANVAS';
    if (svgElement) return 'SVG';
    if (canvasElement) return 'CANVAS';
    return 'UNKNOWN_NO_SVG_OR_CANVAS';
  });
}

/** Get board DOM diagnostics (element counts, classes, etc.). */
async function getBoardDiagnostics(page: Page): Promise<Record<string, unknown>> {
  return await page.evaluate(() => {
    const boardSlot = document.querySelector('[data-slot="board"]');
    if (!boardSlot) return { found: false };

    const svgElement = boardSlot.querySelector('svg');
    const canvasElement = boardSlot.querySelector('canvas');

    return {
      found: true,
      boardSlotClasses: boardSlot.className,
      boardSlotChildCount: boardSlot.childElementCount,
      hasSVG: !!svgElement,
      hasCanvas: !!canvasElement,
      svgChildCount: svgElement?.childElementCount ?? 0,
      canvasWidth: canvasElement?.width ?? null,
      canvasHeight: canvasElement?.height ?? null,
      // Check for goban-specific elements
      hasGobanContainer: !!boardSlot.querySelector('.Goban'),
      gobanContainerClasses: boardSlot.querySelector('.Goban')?.className ?? null,
      // Check background style on goban container (board theme)
      gobanBgStyle: (() => {
        const gobanEl = boardSlot.querySelector('.Goban') ?? boardSlot.firstElementChild;
        if (!gobanEl) return null;
        const style = window.getComputedStyle(gobanEl);
        return {
          backgroundColor: style.backgroundColor,
          backgroundImage: style.backgroundImage,
        };
      })(),
    };
  });
}

test.describe('Board Quality Investigation', () => {
  test.describe.configure({ mode: 'serial' });

  // ── Route 1: Collection/Level (beginner) ──────────────────
  test('Route 1: /collections/level-beginner — level collection board', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/collections/level-beginner');
    await page.waitForLoadState('networkidle');

    // Wait for board to appear
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    // Full page screenshot
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route1-level-beginner-full.png'),
      fullPage: true,
    });

    // Board-only screenshot (if board exists)
    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route1-level-beginner-board.png'),
      });
    }

    // Diagnostics
    const rendererType = await detectRendererType(page);
    const boardDiag = await getBoardDiagnostics(page);

    console.log('=== Route 1: /collections/level-beginner ===');
    console.log('Renderer type:', rendererType);
    console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    console.log('Errors:', diag.errors);
  });

  // ── Route 2: Collection/Tag (life-and-death) ─────────────
  test('Route 2: /collections/tag-life-and-death — technique collection board', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/collections/tag-life-and-death');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route2-tag-life-and-death-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route2-tag-life-and-death-board.png'),
      });
    }

    const rendererType = await detectRendererType(page);
    const boardDiag = await getBoardDiagnostics(page);

    console.log('=== Route 2: /collections/tag-life-and-death ===');
    console.log('Renderer type:', rendererType);
    console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    console.log('Errors:', diag.errors);
  });

  // ── Route 3: Daily challenge ──────────────────────────────
  test('Route 3: /daily — daily challenge board', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/daily');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route3-daily-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route3-daily-board.png'),
      });
    }

    const rendererType = await detectRendererType(page);
    const boardDiag = await getBoardDiagnostics(page);

    console.log('=== Route 3: /daily ===');
    console.log('Renderer type:', rendererType);
    console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    console.log('Errors:', diag.errors);
  });

  // ── Route 4: Puzzle Rush ──────────────────────────────────
  test('Route 4: /puzzle-rush — puzzle rush board', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/puzzle-rush');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await disableAnimations(page);

    // Screenshot the Rush modal / landing state
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route4-puzzle-rush-full.png'),
      fullPage: true,
    });

    // Try to start a rush session by clicking a duration button (if modal is visible)
    const startButton = page.locator('button:has-text("Start"), button:has-text("3 min"), button:has-text("180")');
    if (await startButton.count() > 0) {
      await startButton.first().click();
      await page.waitForTimeout(3000);
      await disableAnimations(page);

      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'route4-puzzle-rush-playing-full.png'),
        fullPage: true,
      });

      const boardSlot = page.locator('[data-slot="board"]');
      if (await boardSlot.count() > 0) {
        await boardSlot.first().screenshot({
          path: path.join(SCREENSHOT_DIR, 'route4-puzzle-rush-board.png'),
        });
      }

      const rendererType = await detectRendererType(page);
      const boardDiag = await getBoardDiagnostics(page);

      console.log('=== Route 4: /puzzle-rush (playing) ===');
      console.log('Renderer type:', rendererType);
      console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    } else {
      console.log('=== Route 4: /puzzle-rush (modal not found/clickable) ===');
    }
    console.log('Errors:', diag.errors);
  });

  // ── Route 5: Random puzzle ────────────────────────────────
  test('Route 5: /random — random puzzle board', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/random');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route5-random-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route5-random-board.png'),
      });
    }

    const rendererType = await detectRendererType(page);
    const boardDiag = await getBoardDiagnostics(page);

    console.log('=== Route 5: /random ===');
    console.log('Renderer type:', rendererType);
    console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    console.log('Errors:', diag.errors);
  });

  // ── Route 6: Direct puzzle by index ───────────────────────
  test('Route 6: /collections/level-beginner/1 — direct puzzle solve', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    const diag = attachDiagnostics(page);

    await page.goto('/collections/level-beginner/1');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route6-direct-puzzle-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route6-direct-puzzle-board.png'),
      });
    }

    const rendererType = await detectRendererType(page);
    const boardDiag = await getBoardDiagnostics(page);

    console.log('=== Route 6: /collections/level-beginner/1 ===');
    console.log('Renderer type:', rendererType);
    console.log('Board diagnostics:', JSON.stringify(boardDiag, null, 2));
    console.log('Errors:', diag.errors);
  });

  // ── Dark mode comparison ──────────────────────────────────
  test('Route 7: /collections/level-beginner — dark mode', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });

    await page.goto('/collections/level-beginner');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Switch to dark mode
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
    });
    await page.waitForTimeout(500);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route7-level-beginner-dark-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route7-level-beginner-dark-board.png'),
      });
    }

    console.log('=== Route 7: Dark mode screenshot captured ===');
  });

  // ── Mobile viewport comparison ────────────────────────────
  test('Route 8: /collections/level-beginner — mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });

    await page.goto('/collections/level-beginner');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await disableAnimations(page);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'route8-level-beginner-mobile-full.png'),
      fullPage: true,
    });

    const boardSlot = page.locator('[data-slot="board"]');
    if (await boardSlot.count() > 0) {
      await boardSlot.first().screenshot({
        path: path.join(SCREENSHOT_DIR, 'route8-level-beginner-mobile-board.png'),
      });
    }

    console.log('=== Route 8: Mobile viewport screenshot captured ===');
  });
});
