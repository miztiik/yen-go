import { test, expect } from '@playwright/test';

test('check shadow DOM for goban SVG', async ({ page }) => {
  const logs: string[] = [];
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));

  await page.goto('/yen-go/collections/tag-connection', { waitUntil: 'networkidle' });
  await page.waitForTimeout(6000);

  const results = await page.evaluate(() => {
    const boardDiv = document.querySelector('[data-slot="board"]');
    if (!boardDiv) return { error: 'boardDiv not found' };

    const shadowRoot = boardDiv.shadowRoot;
    const boardRect = boardDiv.getBoundingClientRect();
    const boardStyle = boardDiv.getAttribute('style');
    const boardComputed = window.getComputedStyle(boardDiv);

    let shadowInfo: any = null;
    if (shadowRoot) {
      const svgs = shadowRoot.querySelectorAll('svg');
      const allEls = shadowRoot.querySelectorAll('*');
      shadowInfo = {
        childCount: shadowRoot.childNodes.length,
        elementCount: allEls.length,
        svgCount: svgs.length,
        svgDims: Array.from(svgs).map(s => ({
          width: s.getAttribute('width'),
          height: s.getAttribute('height'),
          viewBox: s.getAttribute('viewBox'),
          style: s.getAttribute('style')?.slice(0, 200),
          childCount: s.childElementCount,
        })),
        innerHTML: shadowRoot.innerHTML?.slice(0, 500),
      };
    }

    // Also check the parent
    const parentEl = boardDiv.parentElement;
    const parentRect = parentEl?.getBoundingClientRect();
    const parentComputed = parentEl ? window.getComputedStyle(parentEl) : null;

    return {
      hasShadowRoot: !!shadowRoot,
      shadowInfo,
      boardRect: { x: boardRect.x, y: boardRect.y, w: boardRect.width, h: boardRect.height },
      boardStyle,
      boardComputedWidth: boardComputed.width,
      boardComputedHeight: boardComputed.height,
      boardDisplay: boardComputed.display,
      boardOverflow: boardComputed.overflow,
      boardChildCount: boardDiv.childElementCount,
      boardChildTags: Array.from(boardDiv.children).map(c => c.tagName),
      boardFirstChildInfo: boardDiv.firstElementChild ? {
        tag: boardDiv.firstElementChild.tagName,
        width: boardDiv.firstElementChild.getAttribute('width'),
        height: boardDiv.firstElementChild.getAttribute('height'),
        childCount: boardDiv.firstElementChild.childElementCount,
      } : null,
      parentRect: parentRect ? { x: parentRect.x, y: parentRect.y, w: parentRect.width, h: parentRect.height } : null,
      parentComputedWidth: parentComputed?.width,
      parentComputedHeight: parentComputed?.height,
      parentOverflow: parentComputed?.overflow,
    };
  });

  console.log('Results:', JSON.stringify(results, null, 2));
  console.log('Relevant logs:', logs.filter(l => l.includes('goban') || l.includes('Goban') || l.includes('canvas') || l.includes('SVG') || l.includes('width') || l.includes('renderer') || l.includes('Invalid') || l.includes('warn') || l.includes('error') || l.includes('useGoban') || l.includes('shadow')));

  // Take screenshot for visual verification
  await page.screenshot({ path: 'tests/e2e/test-results/board-render-check.png', fullPage: false });

  expect(true).toBe(true);
});
