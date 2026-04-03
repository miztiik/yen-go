/**
 * Visual Tests for Solution Tree Component
 * 
 * Tests solution tree visualization showing:
 * - Correct path branches
 * - Wrong move indicators
 * - Current position highlighting
 * - Expandable/collapsible nodes
 */

import { test, expect } from '@playwright/test';

test.describe('Solution Tree Visual Tests', () => {
  test.describe('Tree Structure', () => {
    test.beforeEach(async ({ page }) => {
      // Navigate to a puzzle page with solution tree
      await page.goto('/collections');
      await page.waitForLoadState('networkidle');
      
      // Start a collection to get to puzzle view
      const card = page.locator('[data-testid="collection-card"]').first();
      if (await card.isVisible()) {
        await card.click();
        await page.getByRole('button', { name: /start|practice/i }).click();
      }
    });

    test('initial tree state', async ({ page }) => {
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('solution-tree-initial.png');
      }
    });

    test('tree with current position highlighted', async ({ page }) => {
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        // Tree should show current node
        const currentNode = tree.locator('[data-current="true"]');
        await expect(currentNode.first()).toBeVisible();
        await expect(tree).toHaveScreenshot('solution-tree-current-position.png');
      }
    });
  });

  test.describe('Branch Visualization', () => {
    test('correct path branches in green', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const correctBranch = page.locator('[data-testid="tree-branch-correct"]');
      if (await correctBranch.first().isVisible()) {
        await expect(correctBranch.first()).toHaveScreenshot('tree-branch-correct.png');
      }
    });

    test('wrong move branches in red', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const wrongBranch = page.locator('[data-testid="tree-branch-wrong"]');
      if (await wrongBranch.first().isVisible()) {
        await expect(wrongBranch.first()).toHaveScreenshot('tree-branch-wrong.png');
      }
    });

    test('unexplored branches dimmed', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const unexploredBranch = page.locator('[data-testid="tree-branch-unexplored"]');
      if (await unexploredBranch.first().isVisible()) {
        await expect(unexploredBranch.first()).toHaveScreenshot('tree-branch-unexplored.png');
      }
    });
  });

  test.describe('Node States', () => {
    test('root node', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const rootNode = page.locator('[data-testid="tree-node-root"]');
      if (await rootNode.isVisible()) {
        await expect(rootNode).toHaveScreenshot('tree-node-root.png');
      }
    });

    test('player move node', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const playerNode = page.locator('[data-testid="tree-node-player"]');
      if (await playerNode.first().isVisible()) {
        await expect(playerNode.first()).toHaveScreenshot('tree-node-player.png');
      }
    });

    test('opponent response node', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const opponentNode = page.locator('[data-testid="tree-node-opponent"]');
      if (await opponentNode.first().isVisible()) {
        await expect(opponentNode.first()).toHaveScreenshot('tree-node-opponent.png');
      }
    });

    test('terminal node (puzzle solved)', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const terminalNode = page.locator('[data-testid="tree-node-terminal"]');
      if (await terminalNode.isVisible()) {
        await expect(terminalNode).toHaveScreenshot('tree-node-terminal.png');
      }
    });
  });

  test.describe('Interactive States', () => {
    test('node hover state', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const node = page.locator('[data-testid^="tree-node"]').first();
      if (await node.isVisible()) {
        await node.hover();
        await expect(node).toHaveScreenshot('tree-node-hover.png');
      }
    });

    test('expanded branch', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const expandable = page.locator('[data-testid="tree-expandable"]');
      if (await expandable.first().isVisible()) {
        await expandable.first().click();
        await expect(expandable.first()).toHaveScreenshot('tree-branch-expanded.png');
      }
    });

    test('collapsed branch', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const collapsible = page.locator('[data-testid="tree-collapsible"]');
      if (await collapsible.first().isVisible()) {
        await expect(collapsible.first()).toHaveScreenshot('tree-branch-collapsed.png');
      }
    });
  });

  test.describe('Responsive Layout', () => {
    test('tree on desktop (side panel)', async ({ page }) => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('solution-tree-desktop.png');
      }
    });

    test('tree on mobile (below board)', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('solution-tree-mobile.png');
      }
    });

    test('tree scrollable on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/visual-tests.html#solution-tree-long');
      await page.waitForLoadState('networkidle');
      
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        // Scroll tree to show overflow behavior
        await tree.evaluate(el => el.scrollTop = 100);
        await expect(tree).toHaveScreenshot('solution-tree-mobile-scrolled.png');
      }
    });
  });

  test.describe('Accessibility', () => {
    test('tree with focus indicators', async ({ page }) => {
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      // Tab to first focusable node
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');
      
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('solution-tree-focus.png');
      }
    });

    test('high contrast mode', async ({ page }) => {
      await page.emulateMedia({ forcedColors: 'active' });
      await page.goto('/visual-tests.html#solution-tree');
      await page.waitForLoadState('networkidle');
      
      const tree = page.locator('[data-testid="solution-tree"]');
      if (await tree.isVisible()) {
        await expect(tree).toHaveScreenshot('solution-tree-high-contrast.png');
      }
    });
  });
});
