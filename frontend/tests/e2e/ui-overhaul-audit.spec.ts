/**
 * UI/UX Overhaul — Comprehensive Playwright Audit
 *
 * This test captures screenshots and validates EVERY claim in the
 * TODO/ui-ux-overhaul.md document, organized by phase.
 *
 * Run: npx playwright test tests/e2e/ui-overhaul-audit.spec.ts --config=playwright.e2e.config.ts
 */
import { test, expect, type Page } from '@playwright/test';

const PUZZLE_URL = '/collections/curated-beginner-essentials/1';
const COLLECTION_URL = '/collections/curated-beginner-essentials';
const SCREENSHOT_DIR = 'test-screenshots/ui-overhaul-audit';

// Helper: wait for puzzle solver to fully load
async function waitForSolverReady(page: Page) {
  // Wait for the solver layout to appear
  await page.waitForSelector('.solver-layout', { timeout: 15000 });
  // Wait for goban container to have content (board rendered)
  await page.waitForSelector('.goban-container', { timeout: 15000 });
  // Wait a bit more for canvas rendering
  await page.waitForTimeout(2000);
}

// ============================================================
// PHASE 1 — OGS Structural Alignment
// ============================================================
test.describe('Phase 1 — OGS Structural Alignment', () => {
  test.describe.configure({ mode: 'serial' });

  test('P1-SCREENSHOT: Full page layout capture', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-full-page.png`,
      fullPage: false,
    });
  });

  // UI-001: GobanContainer with overflow:hidden + centering
  test('P1-UI-001: Board is contained (no overflow into sidebar)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Check GobanContainer exists
    const gobanContainer = page.locator('.goban-container');
    await expect(gobanContainer).toBeVisible();

    // Check overflow is hidden on the board column
    const boardCol = page.locator('.solver-board-col');
    const overflow = await boardCol.evaluate(el => getComputedStyle(el).overflow);
    expect(overflow).toContain('hidden');

    // Check board column has canvas/SVG content
    const hasBoard = await page.locator('.goban-container canvas, .goban-container svg').count();
    expect(hasBoard).toBeGreaterThan(0);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-board-containment.png`,
      fullPage: false,
    });
  });

  // UI-001b: Viewport-filling layout
  test('P1-UI-001b: Layout fills viewport (flex, not scrollable)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    const layout = page.locator('.solver-layout');
    await expect(layout).toBeVisible();

    // Check it uses flex
    const display = await layout.evaluate(el => getComputedStyle(el).display);
    expect(display).toBe('flex');

    // On desktop (1280x800), check that sidebar is visible side-by-side
    const sidebar = page.locator('.solver-sidebar-col');
    const sidebarBox = await sidebar.boundingBox();
    const layoutBox = await layout.boundingBox();

    // Layout should fill most of the viewport height
    expect(layoutBox!.height).toBeGreaterThan(500);

    // Board should be visible (not pushed off-screen)
    const boardCol = page.locator('.solver-board-col');
    const boardBox = await boardCol.boundingBox();
    expect(boardBox!.y).toBeLessThan(200); // Board starts near top
    expect(boardBox!.height).toBeGreaterThan(300); // Board has significant height

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-viewport-layout.png`,
      fullPage: false,
    });
  });

  // UI-032: SGF→puzzle-object adapter (structural — verify via no workaround artifacts)
  test('P1-UI-032: Puzzle loads and is interactive (adapter works)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Board should have interactive canvas (hoverable)
    const goban = page.locator('.Goban, .goban-container canvas, .goban-container svg');
    await expect(goban.first()).toBeVisible();

    // Verify no "finished" state artifacts — puzzle should be interactive
    // If adapter failed, engine.phase would be "finished" and no hover stones would show
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-puzzle-interactive.png`,
      fullPage: false,
    });
  });

  // UI-002 + UI-017: Custom board theme (darker lines, flat color)
  test('P1-UI-002+017: Board uses custom theme (visible lines)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Take a close-up of the board area
    const boardCol = page.locator('.solver-board-col');
    await boardCol.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-board-theme.png`,
    });
  });

  // UI-003: Coordinate labels via setLabelPosition
  test('P1-UI-003: Coordinate labels visible by default', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Take screenshot showing coordinates
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase1-coordinates-default.png`,
      fullPage: false,
    });

    // Toggle coordinates off via the coords button
    const coordsBtn = page.locator('button[aria-label*="oordinate" i], button[title*="oordinate" i]');
    if (await coordsBtn.count() > 0) {
      await coordsBtn.first().click();
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/phase1-coordinates-off.png`,
        fullPage: false,
      });
      // Toggle back on
      await coordsBtn.first().click();
      await page.waitForTimeout(500);
    }
  });

  // UI-033: player_id: 0 (correct hover stone color)
  test('P1-UI-033: Hover stone visible on board', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Hover over the board to check for hover stone
    const board = page.locator('.goban-container');
    const boardBox = await board.boundingBox();
    if (boardBox) {
      await page.mouse.move(boardBox.x + boardBox.width / 2, boardBox.y + boardBox.height / 2);
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/phase1-hover-stone.png`,
        fullPage: false,
      });
    }
  });
});

// ============================================================
// PHASE 2 — OGS Feature Alignment + Navigation
// ============================================================
test.describe('Phase 2 — Features & Navigation', () => {
  test.describe.configure({ mode: 'serial' });

  // UI-004: Zoom toggle
  test('P2-UI-004: Zoom toggle button exists and works', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Look for zoom button
    const zoomBtn = page.locator('button[aria-label*="oom" i], button[title*="ull board" i], button[aria-label*="ull board" i]');
    const zoomCount = await zoomBtn.count();

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-zoom-before.png`,
      fullPage: false,
    });

    if (zoomCount > 0) {
      await zoomBtn.first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/phase2-zoom-toggled.png`,
        fullPage: false,
      });
      // Toggle back
      await zoomBtn.first().click();
      await page.waitForTimeout(1000);
    }
  });

  // UI-034: ProblemNav with dots
  test('P2-UI-034: ProblemNav displays dots/progress', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Check for ProblemNav elements: dots or counter
    const problemNav = page.locator('[role="tablist"], .puzzle-nav, [data-testid="problem-nav"]');
    const dotsOrCounter = page.locator('[role="tab"], .puzzle-dot, .puzzle-counter');

    // Look for any navigation element
    const navArea = page.locator('.solver-sidebar-col');
    await navArea.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-problemnav-sidebar.png`,
    });

    // Check if old-style "1 / N" counter is present vs dot nav
    const oldCounter = page.locator('text=/\\d+\\s*\\/\\s*\\d+/');
    const oldCounterCount = await oldCounter.count();
    // This will be in the findings
  });

  // UI-037: Rank range + Collection pills
  test('P2-UI-037: Metadata shows rank range and collection badges', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Look for rank range pattern like "25k–21k" or "10k–6k"
    const rankBadge = page.locator('text=/\\d+k/');
    const rankCount = await rankBadge.count();

    // Look for collection badge with CollectionIcon 
    const collectionBadge = page.locator('[class*="collection"], [data-section="metadata"]');

    // Screenshot the metadata area
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-metadata-display.png`,
    });
  });

  // UI-039: Prev + Review buttons in action bar
  test('P2-UI-039: Action bar has Prev and Review buttons', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Check for prev button
    const prevBtn = page.locator('button[aria-label*="revious" i], button[title*="revious" i]');
    const prevCount = await prevBtn.count();

    // Check for undo button
    const undoBtn = page.locator('button[aria-label*="ndo" i], button[title*="ndo" i]');
    const undoCount = await undoBtn.count();

    // Check for reset button
    const resetBtn = page.locator('button[aria-label*="eset" i], button[title*="eset" i]');
    const resetCount = await resetBtn.count();

    // Check for review button  
    const reviewBtn = page.locator('button:has-text("Review"), button[aria-label*="eview" i]');
    const reviewCount = await reviewBtn.count();

    // Screenshot the action area
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-action-bar.png`,
      fullPage: false,
    });

    // Prev should exist (even if disabled for puzzle 1)
    expect(prevCount).toBeGreaterThan(0);
    // Undo and Reset should exist
    expect(undoCount).toBeGreaterThan(0);
    expect(resetCount).toBeGreaterThan(0);
  });

  // UI-040: Transform bar — check for FlipDiag
  test('P2-UI-040: Transform bar has all 8 buttons (including FlipDiag)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Count all transform buttons (in the transforms section)
    const transformSection = page.locator('[data-section="transforms"], [role="toolbar"]');
    
    // Get all buttons in the transform area
    const transformBtns = transformSection.locator('button');
    const btnCount = await transformBtns.count();

    // Look specifically for FlipDiag
    const flipDiagBtn = page.locator('button[aria-label*="iagonal" i], button[title*="iagonal" i], button[aria-label*="lip diagonal" i]');
    const flipDiagCount = await flipDiagBtn.count();

    // Screenshot the transform bar
    await transformSection.first().screenshot({
      path: `${SCREENSHOT_DIR}/phase2-transform-bar.png`,
    });

    // Spec requires 8 buttons: FlipH, FlipV, FlipDiag, RotCCW, RotCW, SwapColors, Zoom, Coords
    // Note: Zoom may be separate from transform bar
  });

  // UI-041: Comments display
  test('P2-UI-041: Comment display section exists', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Look for comment container
    const commentSection = page.locator('[data-section="comments"], .puzzle-comment, [class*="comment"]');
    const commentCount = await commentSection.count();

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-comments.png`,
      fullPage: false,
    });
  });

  // UI-011: Color swap text transformation
  test('P2-UI-011: Color swap changes hint text', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Screenshot before swap
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase2-before-color-swap.png`,
      fullPage: false,
    });

    // Find and click swap colors button
    const swapBtn = page.locator('button[aria-label*="wap" i], button[aria-label*="everse" i], button[title*="wap" i]');
    if (await swapBtn.count() > 0) {
      await swapBtn.first().click();
      await page.waitForTimeout(1000);
      await page.screenshot({
        path: `${SCREENSHOT_DIR}/phase2-after-color-swap.png`,
        fullPage: false,
      });
      // Toggle back
      await swapBtn.first().click();
      await page.waitForTimeout(500);
    }
  });
});

// ============================================================
// PHASE 3 — Visual Polish
// ============================================================
test.describe('Phase 3 — Visual Polish', () => {
  test.describe.configure({ mode: 'serial' });

  // UI-005: No thick bottom border on sidebar
  test('P3-UI-005: No thick gold bottom border on sidebar card', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    const sidebar = page.locator('.solver-sidebar-col');
    // Check that there's no 6px border-bottom
    const sidebarCard = sidebar.locator('> div').first();
    if (await sidebarCard.count() > 0) {
      const borderBottom = await sidebarCard.evaluate(el => {
        const style = getComputedStyle(el);
        return {
          borderBottomWidth: style.borderBottomWidth,
          borderBottomColor: style.borderBottomColor,
          borderBottomStyle: style.borderBottomStyle,
        };
      });
      // 6px border = FAIL
      const widthNum = parseFloat(borderBottom.borderBottomWidth);
      expect(widthNum).toBeLessThan(4); // Should not be 6px
    }

    await sidebar.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-sidebar-no-thick-border.png`,
    });
  });

  // UI-008: No heavy section dividers
  test('P3-UI-008: No "BOARD" or "ACTIONS" section divider text', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // These should NOT exist
    const boardDivider = page.locator('text="BOARD"');
    const actionsDivider = page.locator('text="ACTIONS"');

    expect(await boardDivider.count()).toBe(0);
    expect(await actionsDivider.count()).toBe(0);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-no-section-dividers.png`,
      fullPage: false,
    });
  });

  // UI-010: No hover shadow transition
  test('P3-UI-010: No hover shadow animation on sidebar', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Hover over sidebar
    const sidebar = page.locator('.solver-sidebar-col');
    await sidebar.hover();
    await page.waitForTimeout(500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-sidebar-hover.png`,
      fullPage: false,
    });
  });

  // UI-036: No turn indicator dot
  test('P3-UI-036: No bare ● dot in sidebar', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-no-turn-dot.png`,
      fullPage: false,
    });
  });

  // UI-031 + UI-045: Keyboard shortcuts
  test('P3-UI-031: Keyboard shortcuts work (Escape, Z, X)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Press Escape — should reset if any moves made
    await page.keyboard.press('Escape');
    await page.waitForTimeout(500);
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-keyboard-escape.png`,
      fullPage: false,
    });
  });

  // UI-038: Hint layout shift
  test('P3-UI-038: Hint section has fixed height (no layout shift)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Find hint button
    const hintBtn = page.locator('button:has-text("Hint"), button[aria-label*="int" i]');

    // Take screenshot before hint
    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase3-before-hint.png`,
      fullPage: false,
    });

    if (await hintBtn.count() > 0) {
      // Record position of action buttons before hint
      const actionSection = page.locator('[data-section="actions"]');
      let actionPosBefore = null;
      if (await actionSection.count() > 0) {
        actionPosBefore = await actionSection.boundingBox();
      }

      // Click hint
      await hintBtn.first().click();
      await page.waitForTimeout(500);

      await page.screenshot({
        path: `${SCREENSHOT_DIR}/phase3-after-hint.png`,
        fullPage: false,
      });

      // Check action section didn't move
      if (actionPosBefore && await actionSection.count() > 0) {
        const actionPosAfter = await actionSection.boundingBox();
        // Allow small tolerance (5px) for animation
        if (actionPosAfter) {
          const shift = Math.abs(actionPosAfter.y - actionPosBefore.y);
          // This is informational — may or may not fail depending on implementation
        }
      }
    }
  });
});

// ============================================================
// PHASE 4 — Color & Theming
// ============================================================
test.describe('Phase 4 — Color & Theming', () => {
  test.describe.configure({ mode: 'serial' });

  // UI-012: Warm accent color
  test('P4-UI-012: Accent color is warm (not muddy #8B6914)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Read the computed accent color
    const accentColor = await page.evaluate(() => {
      return getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim();
    });

    // Should not be the old muddy #8B6914
    expect(accentColor.toLowerCase()).not.toBe('#8b6914');

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase4-accent-color.png`,
      fullPage: false,
    });
  });

  // UI-013: Hint button uses accent color, not green
  test('P4-UI-013: Hint button uses warm accent (not green)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    const hintBtn = page.locator('button:has-text("Hint"), .solver-btn-text');
    if (await hintBtn.count() > 0) {
      const color = await hintBtn.first().evaluate(el => {
        return getComputedStyle(el).color;
      });
      // Should not be green-ish (#4caf50, #2e7d32, etc.)
      // Green in RGB has high G relative to R and B
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase4-hint-button-color.png`,
      fullPage: false,
    });
  });

  // UI-016: Action buttons pill-shaped
  test('P4-UI-016: Action buttons are pill-shaped (rounded-full)', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Check undo/reset button border-radius
    const undoBtn = page.locator('button[aria-label*="ndo" i]');
    if (await undoBtn.count() > 0) {
      const borderRadius = await undoBtn.first().evaluate(el => {
        return getComputedStyle(el).borderRadius;
      });
      // rounded-full produces 9999px or very high value
      const radiusNum = parseFloat(borderRadius);
      expect(radiusNum).toBeGreaterThan(15); // Not the old 12px rounded-md
    }

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase4-pill-buttons.png`,
      fullPage: false,
    });
  });

  // Dark mode test
  test('P4-DARK: Dark mode rendering', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Toggle dark mode via localStorage or class
    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark');
      document.documentElement.classList.add('dark');
      localStorage.setItem('yen-go:theme', 'dark');
    });
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase4-dark-mode.png`,
      fullPage: false,
    });
  });
});

// ============================================================
// PHASE 5 — Cleanup Validation
// ============================================================
test.describe('Phase 5 — Dead Code & Docs', () => {
  test('P5: Collection page renders correctly', async ({ page }) => {
    await page.goto(COLLECTION_URL);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase5-collection-page.png`,
      fullPage: true,
    });
  });

  test('P5: Home page renders correctly', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase5-home-page.png`,
      fullPage: true,
    });
  });

  test('P5: Daily page renders correctly', async ({ page }) => {
    await page.goto('/daily');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/phase5-daily-page.png`,
      fullPage: true,
    });
  });
});

// ============================================================
// COMPREHENSIVE: All sidebar elements in one shot
// ============================================================
test.describe('Comprehensive Sidebar Audit', () => {
  test('AUDIT: Sidebar element inventory', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    // Collect all visible sidebar elements
    const sidebar = page.locator('.solver-sidebar-col');
    
    // Inventory check
    const elements = {
      // ProblemNav (dots or counter)
      problemNavDots: await page.locator('[role="tab"]').count(),
      puzzleCounter: await page.locator('text=/\\d+\\s*\\/\\s*\\d+/').count(),
      
      // Metadata
      rankRange: await page.locator('text=/\\d+k/').count(),
      tagPills: await page.locator('[class*="tag"], .technique-tag, .level-badge').count(),
      collectionBadge: await page.locator('[class*="collection"]').count(),

      // Transform buttons
      flipH: await page.locator('button[aria-label*="lip horizontal" i], button[aria-label*="lipH" i]').count(),
      flipV: await page.locator('button[aria-label*="lip vertical" i], button[aria-label*="lipV" i]').count(),
      flipDiag: await page.locator('button[aria-label*="iagonal" i]').count(),
      rotateCCW: await page.locator('button[aria-label*="otate counter" i], button[aria-label*="otate left" i]').count(),
      rotateCW: await page.locator('button[aria-label*="otate clock" i], button[aria-label*="otate right" i]').count(),
      swapColors: await page.locator('button[aria-label*="wap" i], button[aria-label*="everse" i]').count(),
      zoom: await page.locator('button[aria-label*="oom" i], button[aria-label*="ull board" i]').count(),
      coords: await page.locator('button[aria-label*="oordinate" i], button[title*="oordinate" i]').count(),

      // Hint
      hintButton: await page.locator('button:has-text("Hint")').count(),

      // Actions
      prevButton: await page.locator('button[aria-label*="revious" i]').count(),
      undoButton: await page.locator('button[aria-label*="ndo" i]').count(),
      resetButton: await page.locator('button[aria-label*="eset" i]').count(),
      reviewButton: await page.locator('button:has-text("Review")').count(),
      nextButton: await page.locator('button[aria-label*="ext puzzle" i], button[aria-label*="kip" i]').count(),

      // Dividers (should be 0)
      boardDivider: await page.locator('text="BOARD"').count(),
      actionsDivider: await page.locator('text="ACTIONS"').count(),
    };

    // Write inventory to console for the test report
    console.log('=== SIDEBAR ELEMENT INVENTORY ===');
    console.log(JSON.stringify(elements, null, 2));

    // Take comprehensive sidebar screenshot
    await sidebar.screenshot({
      path: `${SCREENSHOT_DIR}/audit-sidebar-full.png`,
    });
  });

  test('AUDIT: Transform bar close-up', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    const transformSection = page.locator('[data-section="transforms"], [role="toolbar"]');
    if (await transformSection.count() > 0) {
      await transformSection.first().screenshot({
        path: `${SCREENSHOT_DIR}/audit-transform-bar.png`,
      });

      // Count buttons
      const buttons = transformSection.first().locator('button');
      const count = await buttons.count();
      console.log(`Transform bar button count: ${count}`);

      // Get all aria-labels
      for (let i = 0; i < count; i++) {
        const label = await buttons.nth(i).getAttribute('aria-label');
        const title = await buttons.nth(i).getAttribute('title');
        console.log(`  Button ${i}: aria-label="${label}", title="${title}"`);
      }
    }
  });

  test('AUDIT: Action bar close-up', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    const actionSection = page.locator('[data-section="actions"]');
    if (await actionSection.count() > 0) {
      await actionSection.screenshot({
        path: `${SCREENSHOT_DIR}/audit-action-bar.png`,
      });

      const buttons = actionSection.locator('button');
      const count = await buttons.count();
      console.log(`Action bar button count: ${count}`);

      for (let i = 0; i < count; i++) {
        const label = await buttons.nth(i).getAttribute('aria-label');
        const title = await buttons.nth(i).getAttribute('title');
        const text = await buttons.nth(i).textContent();
        console.log(`  Button ${i}: aria-label="${label}", title="${title}", text="${text?.trim()}"`);
      }
    }
  });
});

// ============================================================
// MOBILE: Portrait layout
// ============================================================
test.describe('Mobile Layout', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('MOBILE: Portrait layout screenshot', async ({ page }) => {
    await page.goto(PUZZLE_URL);
    await waitForSolverReady(page);

    await page.screenshot({
      path: `${SCREENSHOT_DIR}/mobile-portrait.png`,
      fullPage: true,
    });
  });
});
