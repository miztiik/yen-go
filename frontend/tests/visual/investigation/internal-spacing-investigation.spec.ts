/**
 * Internal SVG Spacing Investigation — Measure coordinate label positions
 * INSIDE the shadow DOM SVG renderer of the goban board.
 *
 * Investigates the reported "huge gap between board and coordinates in
 * the bottom right" by measuring all text elements, grid lines, stones,
 * and SVG dimensions inside the shadow DOM.
 *
 * Run with:
 *   cd frontend
 *   npx playwright test --config playwright.coord-spacing.config.ts tests/visual/investigation/internal-spacing-investigation.spec.ts --reporter=list
 */

import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');

const COLLECTION_URL = 'contexts/collection/yamada-tsumego-collection';

test.describe('Internal SVG Spacing Investigation', () => {

  test('measure all SVG internals on Yamada collection puzzle', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto(COLLECTION_URL);

    // Wait for board to render
    await page.waitForLoadState('networkidle');
    const container = page.getByTestId('goban-container');
    await expect(container).toBeVisible({ timeout: 15_000 });
    await page.waitForTimeout(3000);

    // ── 1. Full-page and board-only screenshots ──────────────────────
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'internal-spacing-fullpage.png'),
      fullPage: true,
    });

    await container.screenshot({
      path: path.join(SCREENSHOT_DIR, 'internal-spacing-board.png'),
    });

    // ── 2. Measure everything inside the shadow DOM ─────────────────
    const measurements = await page.evaluate(() => {
      const result: Record<string, unknown> = {};

      // Find the goban-board-container which hosts the shadow DOM
      const boardContainer = document.querySelector('.goban-board-container');
      if (!boardContainer) {
        result.error = 'No .goban-board-container found';
        // Try to find what exists
        const allClasses = Array.from(document.querySelectorAll('*'))
          .map(e => e.className)
          .filter(c => typeof c === 'string' && c.includes('goban'))
          .slice(0, 20);
        result.gobanClasses = allClasses;
        return result;
      }

      const shadow = boardContainer.shadowRoot;
      if (!shadow) {
        result.error = 'No shadowRoot on .goban-board-container';
        result.boardContainerHTML = boardContainer.outerHTML.substring(0, 500);
        return result;
      }

      // Find the SVG element
      const svg = shadow.querySelector('svg');
      if (!svg) {
        result.error = 'No SVG inside shadow DOM';
        result.shadowHTML = shadow.innerHTML.substring(0, 1000);
        return result;
      }

      // ── SVG attributes ──
      const svgRect = svg.getBoundingClientRect();
      result.svg = {
        viewBox: svg.getAttribute('viewBox'),
        width: svg.getAttribute('width'),
        height: svg.getAttribute('height'),
        style: svg.getAttribute('style'),
        boundingRect: {
          x: svgRect.x,
          y: svgRect.y,
          width: svgRect.width,
          height: svgRect.height,
        },
      };

      // ── Container rect
      const containerRect = boardContainer.getBoundingClientRect();
      result.containerRect = {
        x: containerRect.x,
        y: containerRect.y,
        width: containerRect.width,
        height: containerRect.height,
      };

      // Gap between container and SVG
      result.containerToSvgGap = {
        left: svgRect.x - containerRect.x,
        right: (containerRect.x + containerRect.width) - (svgRect.x + svgRect.width),
        top: svgRect.y - containerRect.y,
        bottom: (containerRect.y + containerRect.height) - (svgRect.y + svgRect.height),
      };

      // ── All text elements (coordinate labels) ──
      const textEls = shadow.querySelectorAll('text');
      const texts: Array<{
        content: string;
        x: string | null;
        y: string | null;
        textAnchor: string;
        fontSize: string;
        transform: string | null;
        rect: { x: number; y: number; width: number; height: number };
      }> = [];
      textEls.forEach(t => {
        const r = t.getBoundingClientRect();
        texts.push({
          content: t.textContent || '',
          x: t.getAttribute('x'),
          y: t.getAttribute('y'),
          textAnchor: t.getAttribute('text-anchor') || '',
          fontSize: t.getAttribute('font-size') || '',
          transform: t.getAttribute('transform'),
          rect: { x: r.x, y: r.y, width: r.width, height: r.height },
        });
      });
      result.textElements = texts;
      result.textCount = texts.length;

      // ── All line elements (grid lines) ──
      const lineEls = shadow.querySelectorAll('line');
      const lines: Array<{
        x1: string | null; y1: string | null;
        x2: string | null; y2: string | null;
        stroke: string | null;
        rect: { x: number; y: number; width: number; height: number };
      }> = [];
      lineEls.forEach(l => {
        const r = l.getBoundingClientRect();
        lines.push({
          x1: l.getAttribute('x1'), y1: l.getAttribute('y1'),
          x2: l.getAttribute('x2'), y2: l.getAttribute('y2'),
          stroke: l.getAttribute('stroke'),
          rect: { x: r.x, y: r.y, width: r.width, height: r.height },
        });
      });
      result.lineElements = lines;
      result.lineCount = lines.length;

      // ── All circle elements (stones and star points) ──
      const circleEls = shadow.querySelectorAll('circle');
      const circles: Array<{
        cx: string | null; cy: string | null; r: string | null;
        fill: string | null; className: string;
        rect: { x: number; y: number; width: number; height: number };
      }> = [];
      circleEls.forEach(c => {
        const r = c.getBoundingClientRect();
        circles.push({
          cx: c.getAttribute('cx'), cy: c.getAttribute('cy'),
          r: c.getAttribute('r'),
          fill: c.getAttribute('fill'),
          className: c.getAttribute('class') || '',
          rect: { x: r.x, y: r.y, width: r.width, height: r.height },
        });
      });
      result.circleElements = circles;
      result.circleCount = circles.length;

      // ── All rect elements (background, cell rects, etc.) ──
      const rectEls = shadow.querySelectorAll('rect');
      const rects: Array<{
        x: string | null; y: string | null;
        width: string | null; height: string | null;
        fill: string | null; className: string;
        rect: { x: number; y: number; width: number; height: number };
      }> = [];
      rectEls.forEach(r => {
        const br = r.getBoundingClientRect();
        rects.push({
          x: r.getAttribute('x'), y: r.getAttribute('y'),
          width: r.getAttribute('width'), height: r.getAttribute('height'),
          fill: r.getAttribute('fill'),
          className: r.getAttribute('class') || '',
          rect: { x: br.x, y: br.y, width: br.width, height: br.height },
        });
      });
      result.rectElements = rects;
      result.rectCount = rects.length;

      // ── All path elements ──
      const pathEls = shadow.querySelectorAll('path');
      result.pathCount = pathEls.length;
      const pathData: string[] = [];
      pathEls.forEach(p => {
        pathData.push(p.getAttribute('d')?.substring(0, 2000) || '');
      });
      result.pathDataSample = pathData;

      // ── Derive grid from star points (circles with small radius) ──
      const starPoints = circles.filter(c => parseFloat(c.r || '0') < 5);
      result.starPointCount = starPoints.length;
      result.starPointPositions = starPoints.map(c => ({
        cx: parseFloat(c.cx || '0'),
        cy: parseFloat(c.cy || '0'),
      }));

      // Star points on 19x19 are at positions 4,10,16 (1-indexed)
      // From 3 star x-values, derive grid spacing and full grid
      if (starPoints.length === 9) {
        const starXs = [...new Set(starPoints.map(c => parseFloat(c.cx || '0')))].sort((a, b) => a - b);
        const starYs = [...new Set(starPoints.map(c => parseFloat(c.cy || '0')))].sort((a, b) => a - b);

        const gridSpacingX = (starXs[1] - starXs[0]) / 6;
        const gridSpacingY = (starYs[1] - starYs[0]) / 6;

        // Position 4 (1-indexed) = index 3 → starXs[0] = gridOriginX + 3 * spacing
        const gridOriginX = starXs[0] - 3 * gridSpacingX; // x of line 1 (leftmost A)
        const gridEndX = starXs[2] + 3 * gridSpacingX;    // x of line 19 (rightmost T)
        const gridOriginY = starYs[0] - 3 * gridSpacingY;
        const gridEndY = starYs[2] + 3 * gridSpacingY;

        result.gridSpacing = { x: gridSpacingX, y: gridSpacingY };
        result.gridBounds = {
          minX: gridOriginX, maxX: gridEndX,
          minY: gridOriginY, maxY: gridEndY,
        };

        // All 19 grid line positions
        const gridXs = Array.from({ length: 19 }, (_, i) => gridOriginX + i * gridSpacingX);
        const gridYs = Array.from({ length: 19 }, (_, i) => gridOriginY + i * gridSpacingY);
        result.allGridLineXs = gridXs;
        result.allGridLineYs = gridYs;

        // ── Classify labels ──
        const labeled = texts.map(t => ({
          ...t,
          svgX: parseFloat(t.x || '0'),
          svgY: parseFloat(t.y || '0'),
        }));

        // Column labels: y < grid top (above the grid)
        const topLabels = labeled.filter(t => t.svgY < gridOriginY);
        // Column labels below grid
        const bottomLabels = labeled.filter(t => t.svgY > gridEndY);
        // Row labels: x > grid right (to right of grid)
        const rightLabels = labeled.filter(t => t.svgX > gridEndX);
        // Row labels to left of grid
        const leftLabels = labeled.filter(t => t.svgX < gridOriginX);
        // Labels inside grid area
        const insideLabels = labeled.filter(t =>
          t.svgX >= gridOriginX && t.svgX <= gridEndX &&
          t.svgY >= gridOriginY && t.svgY <= gridEndY
        );

        result.labelClassification = {
          top: topLabels.map(t => ({ content: t.content, svgX: t.svgX, svgY: t.svgY, screenRect: t.rect })),
          bottom: bottomLabels.map(t => ({ content: t.content, svgX: t.svgX, svgY: t.svgY, screenRect: t.rect })),
          left: leftLabels.map(t => ({ content: t.content, svgX: t.svgX, svgY: t.svgY, screenRect: t.rect })),
          right: rightLabels.map(t => ({ content: t.content, svgX: t.svgX, svgY: t.svgY, screenRect: t.rect })),
          inside: insideLabels.map(t => ({ content: t.content, svgX: t.svgX, svgY: t.svgY, screenRect: t.rect })),
        };

        // ── Gaps from grid to labels (SVG units) ──
        // Top: column labels y=34, grid top = gridOriginY
        if (topLabels.length > 0) {
          const labelY = Math.max(...topLabels.map(t => t.svgY));
          result.topLabelToGridGap_svg = gridOriginY - labelY;
        }
        if (bottomLabels.length > 0) {
          const labelY = Math.min(...bottomLabels.map(t => t.svgY));
          result.bottomLabelToGridGap_svg = labelY - gridEndY;
        }
        if (rightLabels.length > 0) {
          const labelX = Math.min(...rightLabels.map(t => t.svgX));
          result.rightLabelToGridGap_svg = labelX - gridEndX;
        }
        if (leftLabels.length > 0) {
          const labelX = Math.max(...leftLabels.map(t => t.svgX));
          result.leftLabelToGridGap_svg = gridOriginX - labelX;
        }

        // ── SVG viewport margins ──
        // SVG visible area: (0, 0) to (svgWidth, svgHeight) since no viewBox
        const svgW = parseFloat(svg.getAttribute('width') || '0');
        const svgH = parseFloat(svg.getAttribute('height') || '0');

        result.svgViewportToGrid = {
          leftMargin: gridOriginX - 0,            // grid left - SVG left
          rightMargin: svgW - gridEndX,            // SVG right - grid right
          topMargin: gridOriginY - 0,              // grid top - SVG top
          bottomMargin: svgH - gridEndY,           // SVG bottom - grid bottom
        };

        // Which grid lines are visible within SVG viewport?
        const visibleGridXs = gridXs.filter(x => x >= 0 && x <= svgW);
        const visibleGridYs = gridYs.filter(y => y >= 0 && y <= svgH);
        result.visibleGridLines = {
          xCount: visibleGridXs.length,
          yCount: visibleGridYs.length,
          firstVisibleX: visibleGridXs[0],
          lastVisibleX: visibleGridXs[visibleGridXs.length - 1],
          firstVisibleY: visibleGridYs[0],
          lastVisibleY: visibleGridYs[visibleGridYs.length - 1],
        };

        // ── Asymmetry analysis ──
        // For the VISIBLE portion, compute margins from SVG edges to first/last visible grid line
        result.visibleMargins = {
          left: (visibleGridXs[0] || 0) - 0,
          right: svgW - (visibleGridXs[visibleGridXs.length - 1] || svgW),
          top: (visibleGridYs[0] || 0) - 0,
          bottom: svgH - (visibleGridYs[visibleGridYs.length - 1] || svgH),
        };

        // Label area space
        result.labelAreaAnalysis = {
          topLabelAreaHeight: topLabels.length > 0 ? gridOriginY : 0,
          rightLabelAreaWidth: rightLabels.length > 0 ? svgW - gridEndX : 0,
          bottomLabelAreaHeight: bottomLabels.length > 0 ? svgH - gridEndY : 0,
          leftLabelAreaWidth: leftLabels.length > 0 ? gridOriginX : 0,
          labelSides: {
            hasTop: topLabels.length > 0,
            hasBottom: bottomLabels.length > 0,
            hasLeft: leftLabels.length > 0,
            hasRight: rightLabels.length > 0,
          },
        };
      }

      // ── Dump the raw shadow DOM HTML structure (first 3000 chars) ──
      result.shadowDomStructure = shadow.innerHTML.substring(0, 3000);

      // ── List all unique tag names in shadow DOM ──
      const allEls = shadow.querySelectorAll('*');
      const tagNames = new Set<string>();
      allEls.forEach(e => tagNames.add(e.tagName.toLowerCase()));
      result.uniqueTagNames = Array.from(tagNames).sort();

      return result;
    });

    // Log the full measurements
    console.log('\n========== INTERNAL SVG MEASUREMENTS ==========');
    console.log(JSON.stringify(measurements, null, 2));
    console.log('================================================\n');

    // ── 3. Corner screenshots (crop from board screenshot) ──
    // We'll take a larger board screenshot region and crop corners
    const containerBox = await container.boundingBox();
    if (containerBox) {
      const cornerSize = 200;

      // Top-left corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'internal-spacing-corner-TL.png'),
        clip: {
          x: containerBox.x,
          y: containerBox.y,
          width: Math.min(cornerSize, containerBox.width),
          height: Math.min(cornerSize, containerBox.height),
        },
      });

      // Top-right corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'internal-spacing-corner-TR.png'),
        clip: {
          x: containerBox.x + containerBox.width - cornerSize,
          y: containerBox.y,
          width: cornerSize,
          height: Math.min(cornerSize, containerBox.height),
        },
      });

      // Bottom-left corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'internal-spacing-corner-BL.png'),
        clip: {
          x: containerBox.x,
          y: containerBox.y + containerBox.height - cornerSize,
          width: Math.min(cornerSize, containerBox.width),
          height: cornerSize,
        },
      });

      // Bottom-right corner
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, 'internal-spacing-corner-BR.png'),
        clip: {
          x: containerBox.x + containerBox.width - cornerSize,
          y: containerBox.y + containerBox.height - cornerSize,
          width: cornerSize,
          height: cornerSize,
        },
      });
    }

    // ── 4. Summary assertions (informational, not blocking) ──
    const m = measurements as Record<string, any>;
    console.log('\n========== SPACING SUMMARY ==========');
    console.log(`SVG viewBox: ${m.svg?.viewBox}`);
    console.log(`SVG width: ${m.svg?.width}, height: ${m.svg?.height}`);
    console.log(`SVG bounding rect: ${JSON.stringify(m.svg?.boundingRect)}`);
    console.log(`Container rect: ${JSON.stringify(m.containerRect)}`);
    console.log(`Container→SVG gap: ${JSON.stringify(m.containerToSvgGap)}`);
    console.log('');
    console.log(`Grid spacing: ${JSON.stringify(m.gridSpacing)}`);
    console.log(`Grid bounds (SVG coords): ${JSON.stringify(m.gridBounds)}`);
    console.log(`All grid line X positions: ${JSON.stringify(m.allGridLineXs)}`);
    console.log(`All grid line Y positions: ${JSON.stringify(m.allGridLineYs)}`);
    console.log('');
    console.log(`Text elements: ${m.textCount}`);
    console.log(`Circle elements: ${m.circleCount} (star points: ${m.starPointCount})`);
    console.log(`Rect elements: ${m.rectCount}`);
    console.log(`Path elements: ${m.pathCount}`);
    console.log(`Line elements: ${m.lineCount}`);
    console.log('');
    console.log('--- Label Classification ---');
    if (m.labelClassification) {
      const lc = m.labelClassification;
      console.log(`Top labels (${lc.top.length}): ${lc.top.map((l: any) => l.content).join(', ')}`);
      console.log(`Bottom labels (${lc.bottom.length}): ${lc.bottom.map((l: any) => l.content).join(', ')}`);
      console.log(`Left labels (${lc.left.length}): ${lc.left.map((l: any) => l.content).join(', ')}`);
      console.log(`Right labels (${lc.right.length}): ${lc.right.map((l: any) => l.content).join(', ')}`);
      console.log(`Inside grid (${lc.inside.length}): ${lc.inside.map((l: any) => l.content).join(', ')}`);
    }
    console.log('');
    console.log('--- Gap: Grid ↔ Labels (SVG units) ---');
    console.log(`Top label→grid gap: ${m.topLabelToGridGap_svg?.toFixed(2)}`);
    console.log(`Bottom label→grid gap: ${m.bottomLabelToGridGap_svg?.toFixed(2) ?? 'N/A (no bottom labels)'}`);
    console.log(`Left label→grid gap: ${m.leftLabelToGridGap_svg?.toFixed(2) ?? 'N/A (no left labels)'}`);
    console.log(`Right label→grid gap: ${m.rightLabelToGridGap_svg?.toFixed(2)}`);
    console.log('');
    console.log('--- SVG Viewport → Grid Margins (SVG units) ---');
    console.log(`  Left margin (SVG x=0 → first grid line):  ${m.svgViewportToGrid?.leftMargin?.toFixed(1)}`);
    console.log(`  Right margin (last grid line → SVG right): ${m.svgViewportToGrid?.rightMargin?.toFixed(1)}`);
    console.log(`  Top margin (SVG y=0 → first grid line):    ${m.svgViewportToGrid?.topMargin?.toFixed(1)}`);
    console.log(`  Bottom margin (last grid line → SVG bottom): ${m.svgViewportToGrid?.bottomMargin?.toFixed(1)}`);
    console.log('');
    console.log('--- Visible Grid Lines ---');
    console.log(JSON.stringify(m.visibleGridLines, null, 2));
    console.log('');
    console.log('--- Visible Area Margins (SVG edge → first/last VISIBLE grid line) ---');
    console.log(JSON.stringify(m.visibleMargins, null, 2));
    console.log('');
    console.log('--- Label Area Analysis ---');
    console.log(JSON.stringify(m.labelAreaAnalysis, null, 2));
    console.log('');
    console.log('--- ASYMMETRY CHECK ---');
    if (m.svgViewportToGrid) {
      const v = m.svgViewportToGrid;
      console.log(`  Left vs Right margin: ${v.leftMargin?.toFixed(1)} vs ${v.rightMargin?.toFixed(1)} (ratio: ${(v.rightMargin / v.leftMargin).toFixed(2)}x)`);
      console.log(`  Top vs Bottom margin: ${v.topMargin?.toFixed(1)} vs ${v.bottomMargin?.toFixed(1)} (ratio: ${(v.topMargin / v.bottomMargin).toFixed(2)}x)`);
    }
    if (m.visibleMargins) {
      const vm = m.visibleMargins;
      console.log(`  Visible Left vs Right: ${vm.left?.toFixed(1)} vs ${vm.right?.toFixed(1)}`);
      console.log(`  Visible Top vs Bottom: ${vm.top?.toFixed(1)} vs ${vm.bottom?.toFixed(1)}`);
    }
    console.log('');
    console.log(`Star point SVG positions: ${JSON.stringify(m.starPointPositions)}`);
    console.log(`Unique SVG tag names: ${m.uniqueTagNames?.join(', ')}`);
    console.log('=====================================\n');

    // The test passes — it's an investigation, not an assertion
    expect(measurements).toBeTruthy();
  });
});
