/**
 * Coordinate Spacing Investigation — Measure actual pixel distances
 * between board grid/stones and coordinate labels on all four sides.
 *
 * This is an INVESTIGATION script — it captures screenshots and logs measurements.
 * Screenshots saved to: frontend/tests/visual/investigation/screenshots/
 *
 * Run with:
 *   cd frontend
 *   npx playwright test --config playwright.investigation.config.ts tests/visual/investigation/coordinate-spacing-investigation.spec.ts
 */

import { test, expect, type Page } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

// Collection puzzle URL (Yamada Kimio Collection — visible in user's screenshot)
const COLLECTION_URL = 'contexts/collection/yamada-tsumego-collection';
// Also test a different collection for comparison
const ALT_PUZZLE_URL = 'contexts/collection/curated-beginner-essentials';

/** Wait for the goban board to be fully rendered */
async function waitForBoard(page: Page): Promise<void> {
  // Wait for SPA to finish routing
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  // Debug: log current URL and page content
  console.log('Current URL:', page.url());
  const bodyText = await page.evaluate(() => document.body.textContent?.substring(0, 300));
  console.log('Body text:', bodyText);

  // Take debug screenshot
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, 'debug-page-state.png'),
    fullPage: true,
  });

  // Check what elements exist
  const hasGobanContainer = await page.evaluate(() => !!document.querySelector('[data-testid="goban-container"]'));
  const hasGobanBoard = await page.evaluate(() => !!document.querySelector('.goban-board-container'));
  const hasSolver = await page.evaluate(() => !!document.querySelector('[data-component="solver-view"]'));
  console.log(`Elements: goban-container=${hasGobanContainer}, goban-board=${hasGobanBoard}, solver=${hasSolver}`);

  // List some top-level data-testid elements
  const testIds = await page.evaluate(() => {
    const els = document.querySelectorAll('[data-testid]');
    return Array.from(els).map(e => e.getAttribute('data-testid')).slice(0, 10);
  });
  console.log('Found data-testid elements:', testIds);

  const container = page.getByTestId('goban-container');
  await expect(container).toBeVisible({ timeout: 15_000 });
  // Wait for the SVG or canvas to render inside the shadow DOM
  await page.waitForTimeout(2000);
}

test.describe('Coordinate Spacing Investigation', () => {

  test('measure spacing on Yamada collection puzzle (desktop)', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(COLLECTION_URL);
    await waitForBoard(page);

    // Take full page screenshot
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'coord-spacing-yamada-desktop-full.png'),
      fullPage: false,
    });

    // Take board-only screenshot
    const container = page.getByTestId('goban-container');
    await container.screenshot({
      path: path.join(SCREENSHOT_DIR, 'coord-spacing-yamada-desktop-board.png'),
    });

    // Measure container dimensions vs actual board element dimensions
    const measurements = await page.evaluate(() => {
      const container = document.querySelector('[data-testid="goban-container"]') as HTMLElement;
      if (!container) return { error: 'No container found' };

      const containerRect = container.getBoundingClientRect();
      const containerStyle = window.getComputedStyle(container);

      // Find the board div (.goban-board-container)
      const boardDiv = container.querySelector('.goban-board-container') as HTMLElement;
      if (!boardDiv) return { error: 'No board div found', containerRect };

      const boardRect = boardDiv.getBoundingClientRect();
      const boardStyle = window.getComputedStyle(boardDiv);

      // Look for SVG inside shadow DOM
      let svgRect = null;
      let svgWidth = 0;
      let svgHeight = 0;
      let svgViewBox = '';

      if (boardDiv.shadowRoot) {
        const svg = boardDiv.shadowRoot.querySelector('svg');
        if (svg) {
          svgRect = svg.getBoundingClientRect();
          svgWidth = parseFloat(svg.getAttribute('width') || '0');
          svgHeight = parseFloat(svg.getAttribute('height') || '0');
          svgViewBox = svg.getAttribute('viewBox') || 'NONE';
        }
      }

      // Look for canvas elements (Canvas renderer)
      const canvases = boardDiv.querySelectorAll('canvas');
      const canvasInfo = Array.from(canvases).map(c => ({
        class: c.className,
        width: c.width,
        height: c.height,
        cssWidth: c.clientWidth,
        cssHeight: c.clientHeight,
        rect: c.getBoundingClientRect(),
      }));

      // Calculate gaps
      const gapLeft = boardRect.left - containerRect.left;
      const gapRight = containerRect.right - boardRect.right;
      const gapTop = boardRect.top - containerRect.top;
      const gapBottom = containerRect.bottom - boardRect.bottom;

      return {
        container: {
          width: containerRect.width,
          height: containerRect.height,
          cssWidth: containerStyle.width,
          cssHeight: containerStyle.height,
          aspectRatio: containerStyle.aspectRatio,
        },
        board: {
          width: boardRect.width,
          height: boardRect.height,
          cssWidth: boardStyle.width,
          cssHeight: boardStyle.height,
          marginLeft: boardStyle.marginLeft,
          marginTop: boardStyle.marginTop,
          position: boardStyle.position,
        },
        svg: svgRect ? {
          width: svgRect.width,
          height: svgRect.height,
          attrWidth: svgWidth,
          attrHeight: svgHeight,
          viewBox: svgViewBox,
        } : null,
        canvases: canvasInfo,
        gaps: {
          left: gapLeft,
          right: gapRight,
          top: gapTop,
          bottom: gapBottom,
        },
        containerToBoard: {
          widthDiff: containerRect.width - boardRect.width,
          heightDiff: containerRect.height - boardRect.height,
        },
      };
    });

    console.log('\n=== YAMADA COLLECTION PUZZLE — DESKTOP (1280x800) ===');
    console.log(JSON.stringify(measurements, null, 2));
  });

  test('measure spacing on Yamada puzzle — measure grid vs coordinate positions via SVG', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(COLLECTION_URL);
    await waitForBoard(page);

    // Deep measurement: find actual grid lines and coordinate text positions in SVG
    const svgMeasurements = await page.evaluate(() => {
      const boardDiv = document.querySelector('.goban-board-container') as HTMLElement;
      if (!boardDiv) return { error: 'No board div' };

      const shadow = boardDiv.shadowRoot;
      if (!shadow) return { error: 'No shadow root — might be Canvas renderer' };

      const svg = shadow.querySelector('svg');
      if (!svg) return { error: 'No SVG found in shadow root' };

      const svgRect = svg.getBoundingClientRect();

      // Find all <text> elements (coordinate labels)
      const texts = shadow.querySelectorAll('text');
      const labels: Array<{text: string; x: number; y: number; bbox: DOMRect}> = [];
      texts.forEach(t => {
        labels.push({
          text: t.textContent || '',
          x: parseFloat(t.getAttribute('x') || '0'),
          y: parseFloat(t.getAttribute('y') || '0'),
          bbox: t.getBoundingClientRect(),
        });
      });

      // Group labels by position (top row, bottom row, left col, right col)
      // Top labels: those in the top ~square_size area
      // We need to figure out square_size first
      // Find all <line> or <path> for grid lines
      const paths = shadow.querySelectorAll('path');
      const lines = shadow.querySelectorAll('line');
      const circles = shadow.querySelectorAll('circle');

      // Find all stone-like elements (circles or images)
      const stoneElements: Array<{cx: number; cy: number; r: number; tag: string}> = [];
      circles.forEach(c => {
        stoneElements.push({
          cx: parseFloat(c.getAttribute('cx') || '0'),
          cy: parseFloat(c.getAttribute('cy') || '0'),
          r: parseFloat(c.getAttribute('r') || '0'),
          tag: c.tagName,
        });
      });

      // Find <image> tags (stone images)
      const images = shadow.querySelectorAll('image');
      const imageElements: Array<{x: number; y: number; w: number; h: number}> = [];
      images.forEach(img => {
        imageElements.push({
          x: parseFloat(img.getAttribute('x') || '0'),
          y: parseFloat(img.getAttribute('y') || '0'),
          w: parseFloat(img.getAttribute('width') || '0'),
          h: parseFloat(img.getAttribute('height') || '0'),
        });
      });

      // Sort labels to identify edge labels
      const sortedByX = [...labels].sort((a, b) => a.x - b.x);
      const sortedByY = [...labels].sort((a, b) => a.y - b.y);

      // Identify left column labels (smallest x values)
      // Identify right column labels (largest x values)
      // Identify top row labels (smallest y values)
      // Identify bottom row labels (largest y values)

      // Find min/max x and y of labels
      const allX = labels.map(l => l.x);
      const allY = labels.map(l => l.y);
      const minLabelX = Math.min(...allX);
      const maxLabelX = Math.max(...allX);
      const minLabelY = Math.min(...allY);
      const maxLabelY = Math.max(...allY);

      // Find min/max x and y of stone images
      let minStoneX = Infinity, maxStoneX = -Infinity;
      let minStoneY = Infinity, maxStoneY = -Infinity;
      imageElements.forEach(img => {
        const cx = img.x + img.w / 2;
        const cy = img.y + img.h / 2;
        if (cx < minStoneX) minStoneX = cx;
        if (cx > maxStoneX) maxStoneX = cx;
        if (cy < minStoneY) minStoneY = cy;
        if (cy > maxStoneY) maxStoneY = cy;
      });

      return {
        svgSize: { width: svgRect.width, height: svgRect.height },
        svgAttrWidth: parseFloat(svg.getAttribute('width') || '0'),
        svgAttrHeight: parseFloat(svg.getAttribute('height') || '0'),
        labelCount: labels.length,
        labels: labels.slice(0, 80), // first 80 labels for analysis
        labelBounds: { minX: minLabelX, maxX: maxLabelX, minY: minLabelY, maxY: maxLabelY },
        stoneImageCount: imageElements.length,
        stoneImages: imageElements.slice(0, 20),
        stoneBounds: {
          minX: minStoneX === Infinity ? null : minStoneX,
          maxX: maxStoneX === -Infinity ? null : maxStoneX,
          minY: minStoneY === Infinity ? null : minStoneY,
          maxY: maxStoneY === -Infinity ? null : maxStoneY,
        },
        pathCount: paths.length,
        lineCount: lines.length,
        circleCount: circles.length,
        // Get the d attribute from grid line paths to find grid extent
        pathData: Array.from(paths).slice(0, 5).map(p => ({
          d: (p.getAttribute('d') || '').substring(0, 200),
          stroke: p.getAttribute('stroke'),
        })),
      };
    });

    console.log('\n=== SVG INTERNAL MEASUREMENTS ===');
    console.log(JSON.stringify(svgMeasurements, null, 2));
  });

  test('measure spacing — parse grid lines from SVG path data', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(COLLECTION_URL);
    await waitForBoard(page);

    const gridAnalysis = await page.evaluate(() => {
      const boardDiv = document.querySelector('.goban-board-container') as HTMLElement;
      if (!boardDiv?.shadowRoot) return { error: 'No shadow root' };

      const svg = boardDiv.shadowRoot.querySelector('svg');
      if (!svg) return { error: 'No SVG' };

      const svgW = parseFloat(svg.getAttribute('width') || '0');
      const svgH = parseFloat(svg.getAttribute('height') || '0');

      // Get ALL text labels and classify them
      const allTexts = boardDiv.shadowRoot.querySelectorAll('text');
      const textData: Array<{text: string; x: number; y: number}> = [];
      allTexts.forEach(t => {
        textData.push({
          text: t.textContent || '',
          x: parseFloat(t.getAttribute('x') || '0'),
          y: parseFloat(t.getAttribute('y') || '0'),
        });
      });

      // Get unique y values to identify horizontal bands (top labels, bottom labels, grid rows)
      const uniqueY = [...new Set(textData.map(t => Math.round(t.y)))].sort((a, b) => a - b);

      // Get unique x values to identify vertical bands (left labels, right labels, grid cols)
      const uniqueX = [...new Set(textData.map(t => Math.round(t.x)))].sort((a, b) => a - b);

      // Top row labels: label texts at the smallest y
      const topRowY = uniqueY[0];
      const topLabels = textData.filter(t => Math.round(t.y) === topRowY);

      // Bottom row labels: label texts at the largest y
      const bottomRowY = uniqueY[uniqueY.length - 1];
      const bottomLabels = textData.filter(t => Math.round(t.y) === bottomRowY);

      // Left column labels: look for numeric labels (1-19) at smallest x
      const numericLabels = textData.filter(t => /^\d+$/.test(t.text));
      const letterLabels = textData.filter(t => /^[A-T]$/.test(t.text));

      // Left labels have the smallest x among numeric labels
      const leftLabelX = numericLabels.length > 0
        ? Math.min(...numericLabels.map(l => l.x))
        : null;
      const leftLabels = numericLabels.filter(t => Math.abs(t.x - (leftLabelX || 0)) < 2);

      // Right labels have the largest x among numeric labels
      const rightLabelX = numericLabels.length > 0
        ? Math.max(...numericLabels.map(l => l.x))
        : null;
      const rightLabels = numericLabels.filter(t => Math.abs(t.x - (rightLabelX || 0)) < 2);

      // Get all stone images
      const images = boardDiv.shadowRoot.querySelectorAll('image');
      const stonePositions: Array<{cx: number; cy: number}> = [];
      images.forEach(img => {
        const x = parseFloat(img.getAttribute('x') || '0');
        const y = parseFloat(img.getAttribute('y') || '0');
        const w = parseFloat(img.getAttribute('width') || '0');
        const h = parseFloat(img.getAttribute('height') || '0');
        stonePositions.push({ cx: x + w / 2, cy: y + h / 2 });
      });

      // Find the grid extent from stone positions
      const stoneXs = stonePositions.map(s => s.cx);
      const stoneYs = stonePositions.map(s => s.cy);

      // Compute distances
      // Distance from leftmost stone center to left label center (x)
      const leftmostStoneX = stoneXs.length > 0 ? Math.min(...stoneXs) : null;
      const rightmostStoneX = stoneXs.length > 0 ? Math.max(...stoneXs) : null;
      const topmostStoneY = stoneYs.length > 0 ? Math.min(...stoneYs) : null;
      const bottommostStoneY = stoneYs.length > 0 ? Math.max(...stoneYs) : null;

      // Parse path d attributes to find grid lines
      const paths = boardDiv.shadowRoot.querySelectorAll('path');
      let gridMoveCommands: Array<{type: string; x: number; y: number}> = [];
      paths.forEach(p => {
        const d = p.getAttribute('d') || '';
        // Parse M and L commands
        const regex = /([ML])\s*([\d.]+)\s+([\d.]+)/g;
        let match;
        while ((match = regex.exec(d)) !== null) {
          gridMoveCommands.push({
            type: match[1],
            x: parseFloat(match[2]),
            y: parseFloat(match[3]),
          });
        }
      });

      // Grid lines: find unique x values (vertical lines) and unique y values (horizontal lines)
      const gridXs = [...new Set(gridMoveCommands.filter(c => c.type === 'M').map(c => Math.round(c.x * 10) / 10))].sort((a, b) => a - b);
      const gridYs = [...new Set(gridMoveCommands.filter(c => c.type === 'M').map(c => Math.round(c.y * 10) / 10))].sort((a, b) => a - b);

      return {
        svgSize: { w: svgW, h: svgH },
        textLabelCount: textData.length,
        uniqueTextYs: uniqueY,
        uniqueTextXs: uniqueX,
        topLabels: topLabels.map(l => `${l.text}@(${l.x},${l.y})`),
        bottomLabels: bottomLabels.map(l => `${l.text}@(${l.x},${l.y})`),
        leftLabels: leftLabels.map(l => `${l.text}@(${l.x},${l.y})`).sort(),
        rightLabels: rightLabels.map(l => `${l.text}@(${l.x},${l.y})`).sort(),
        stoneCount: stonePositions.length,
        stoneBounds: {
          leftmost: leftmostStoneX,
          rightmost: rightmostStoneX,
          topmost: topmostStoneY,
          bottommost: bottommostStoneY,
        },
        gridLineXs: gridXs,
        gridLineYs: gridYs,
        spacing: {
          leftLabelCenterX: leftLabelX,
          rightLabelCenterX: rightLabelX,
          topLabelCenterY: topRowY,
          bottomLabelCenterY: bottomRowY,
          // Key measurements:
          leftLabel_to_firstGridLine: gridXs.length > 0 && leftLabelX != null ? gridXs[0] - leftLabelX : null,
          lastGridLine_to_rightLabel: gridXs.length > 0 && rightLabelX != null ? rightLabelX - gridXs[gridXs.length - 1] : null,
          topLabel_to_firstGridLine: gridYs.length > 0 ? gridYs[0] - topRowY : null,
          lastGridLine_to_bottomLabel: gridYs.length > 0 ? bottomRowY - gridYs[gridYs.length - 1] : null,
          // SVG right edge to rightmost grid line:
          svgRightEdge_to_lastGridLine: gridXs.length > 0 ? svgW - gridXs[gridXs.length - 1] : null,
          svgBottomEdge_to_lastGridLine: gridYs.length > 0 ? svgH - gridYs[gridYs.length - 1] : null,
          // SVG left edge to first grid line:
          svgLeftEdge_to_firstGridLine: gridXs.length > 0 ? gridXs[0] : null,
          svgTopEdge_to_firstGridLine: gridYs.length > 0 ? gridYs[0] : null,
        },
        // Container vs board gaps
        containerInfo: (() => {
          const container = document.querySelector('[data-testid="goban-container"]') as HTMLElement;
          if (!container) return null;
          const cRect = container.getBoundingClientRect();
          const bRect = boardDiv.getBoundingClientRect();
          return {
            containerWidth: cRect.width,
            containerHeight: cRect.height,
            boardWidth: bRect.width,
            boardHeight: bRect.height,
            gapLeft: bRect.left - cRect.left,
            gapRight: cRect.right - bRect.right,
            gapTop: bRect.top - cRect.top,
            gapBottom: cRect.bottom - bRect.bottom,
          };
        })(),
      };
    });

    console.log('\n=== GRID LINE & COORDINATE POSITION ANALYSIS ===');
    console.log(JSON.stringify(gridAnalysis, null, 2));
  });

  test('visual comparison — take screenshots of all four corners', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(COLLECTION_URL);
    await waitForBoard(page);

    // Take a full screenshot for reference
    const container = page.getByTestId('goban-container');
    await container.screenshot({
      path: path.join(SCREENSHOT_DIR, 'coord-spacing-board-full.png'),
    });

    // Clip screenshots of each corner of the board to compare spacing
    const box = await container.boundingBox();
    if (box) {
      // Top-left corner (should look good based on user report)
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'coord-spacing-corner-TL.png'),
        clip: { x: box.x, y: box.y, width: Math.min(300, box.width), height: Math.min(300, box.height) },
      });

      // Top-right corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'coord-spacing-corner-TR.png'),
        clip: {
          x: box.x + box.width - Math.min(300, box.width),
          y: box.y,
          width: Math.min(300, box.width),
          height: Math.min(300, box.height),
        },
      });

      // Bottom-left corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'coord-spacing-corner-BL.png'),
        clip: {
          x: box.x,
          y: box.y + box.height - Math.min(300, box.height),
          width: Math.min(300, box.width),
          height: Math.min(300, box.height),
        },
      });

      // Bottom-right corner (should look bad based on user report)
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'coord-spacing-corner-BR.png'),
        clip: {
          x: box.x + box.width - Math.min(300, box.width),
          y: box.y + box.height - Math.min(300, box.height),
          width: Math.min(300, box.width),
          height: Math.min(300, box.height),
        },
      });

      console.log(`\nBoard box: x=${box.x} y=${box.y} w=${box.width} h=${box.height}`);
    }
  });

  test('alternate puzzle for comparison', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(ALT_PUZZLE_URL);
    await waitForBoard(page);

    const container = page.getByTestId('goban-container');
    await container.screenshot({
      path: path.join(SCREENSHOT_DIR, 'coord-spacing-beginner-essentials-board.png'),
    });

    const measurements = await page.evaluate(() => {
      const container = document.querySelector('[data-testid="goban-container"]') as HTMLElement;
      const boardDiv = container?.querySelector('.goban-board-container') as HTMLElement;
      if (!container || !boardDiv) return { error: 'Missing elements' };

      const cRect = container.getBoundingClientRect();
      const bRect = boardDiv.getBoundingClientRect();

      return {
        container: { w: cRect.width, h: cRect.height },
        board: { w: bRect.width, h: bRect.height },
        gaps: {
          left: bRect.left - cRect.left,
          right: cRect.right - bRect.right,
          top: bRect.top - cRect.top,
          bottom: cRect.bottom - bRect.bottom,
        },
      };
    });

    console.log('\n=== BEGINNER ESSENTIALS PUZZLE ===');
    console.log(JSON.stringify(measurements, null, 2));
  });

  test('daily challenge board renders with correct sizing', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    // Navigate to home page which shows the daily challenge
    await page.goto('');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    // Check if a goban container exists on the daily challenge view
    const hasGobanContainer = await page.evaluate(() => !!document.querySelector('[data-testid="goban-container"]'));
    console.log(`\n=== DAILY CHALLENGE PAGE ===`);
    console.log(`Has goban container: ${hasGobanContainer}`);

    if (!hasGobanContainer) {
      console.log('No daily challenge board visible — may need specific route or date');
      // Try the daily challenge route
      await page.goto('modes/daily');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(3000);
      const hasGobanAfterNav = await page.evaluate(() => !!document.querySelector('[data-testid="goban-container"]'));
      console.log(`After navigating to modes/daily — has goban: ${hasGobanAfterNav}`);
    }

    // If we have a goban container, measure it
    const measurements = await page.evaluate(() => {
      const container = document.querySelector('[data-testid="goban-container"]') as HTMLElement;
      if (!container) return { error: 'No goban-container found' };

      const boardDiv = container.querySelector('.goban-board-container') as HTMLElement;
      const cRect = container.getBoundingClientRect();
      const bRect = boardDiv?.getBoundingClientRect();

      const parent = container.parentElement;
      const pRect = parent?.getBoundingClientRect();

      const containerStyles = window.getComputedStyle(container);

      return {
        container: {
          w: cRect.width,
          h: cRect.height,
          x: cRect.x,
          y: cRect.y,
          aspectRatio: containerStyles.aspectRatio,
          width: containerStyles.width,
          height: containerStyles.height,
          maxWidth: containerStyles.maxWidth,
          className: container.className,
        },
        board: boardDiv ? {
          w: bRect!.width,
          h: bRect!.height,
        } : null,
        parent: pRect ? {
          w: pRect.width,
          h: pRect.height,
        } : null,
        gaps: boardDiv ? {
          left: bRect!.left - cRect.left,
          right: cRect.right - bRect!.right,
          top: bRect!.top - cRect.top,
          bottom: cRect.bottom - bRect!.bottom,
        } : null,
      };
    });

    console.log(JSON.stringify(measurements, null, 2));

    // Take screenshot
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'daily-challenge-board.png'),
      fullPage: true,
    });
  });
});
