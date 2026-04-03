const { chromium } = require('playwright');

const suffix = process.argv[2] || 'screenshot';

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto('http://localhost:5173/collections/curated-cho-chikun-life-death-intermediate/1', { waitUntil: 'networkidle' });
  
  // Wait for goban to render
  try {
    await page.waitForSelector('.goban-container, .goban-board-container, .Goban, [data-component="solver-view"], .solver-layout', { timeout: 15000 });
    console.log('Found board element, waiting for render...');
    await page.waitForTimeout(3000);
  } catch (e) {
    console.log('No board element found within 15s, checking page state...');
    // Check console errors
    const consoleMessages = [];
    page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text()}`));
    await page.waitForTimeout(2000);
    // Dump visible text content
    const pageText = await page.evaluate(() => document.body.innerText.substring(0, 1000));
    console.log('Page text:', pageText);
  }

  // Detect which renderer is active
  const rendererInfo = await page.evaluate(() => {
    const boardContainer = document.querySelector('.goban-board-container') || document.querySelector('.goban-container');
    if (!boardContainer) {
      // Debug: find all classes on page
      const allEls = document.querySelectorAll('[class]');
      const classes = new Set();
      allEls.forEach(el => el.className.split(/\s+/).forEach(c => { if (c.includes('goban') || c.includes('solver') || c.includes('board') || c.includes('Goban')) classes.add(c); }));
      return { error: 'no-board-found', relevantClasses: [...classes], url: window.location.href, title: document.title };
    }
    const hasCanvas = boardContainer.querySelector('canvas') !== null;
    const hasSvg = boardContainer.querySelector('svg') !== null;
    const treeContainer = document.querySelector('[data-testid="solution-tree-container"]');
    const treeHasCanvas = treeContainer ? treeContainer.querySelector('canvas') !== null : false;
    const treeHasSvg = treeContainer ? treeContainer.querySelector('svg') !== null : false;
    return { board: { hasCanvas, hasSvg }, tree: { hasCanvas: treeHasCanvas, hasSvg: treeHasSvg } };
  });
  console.log('Renderer info:', JSON.stringify(rendererInfo, null, 2));

  // Take initial board screenshot (solving state)
  await page.screenshot({ path: `test-screenshots/${suffix}-board.png`, fullPage: false });
  console.log(`Board screenshot saved: ${suffix}-board.png`);

  // Try to trigger review mode to show the tree
  // First, play a wrong move by clicking somewhere random on the board
  const boardBox = await page.evaluate(() => {
    const el = document.querySelector('.goban-container');
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  });

  if (boardBox) {
    // Click near center-ish of the board to place a (likely wrong) move
    await page.mouse.click(boardBox.x + boardBox.width * 0.3, boardBox.y + boardBox.height * 0.3);
    await page.waitForTimeout(1500);

    // Check if Review button appeared
    const reviewBtn = await page.$('button[aria-label="Review solution"]');
    if (reviewBtn) {
      await reviewBtn.click();
      await page.waitForTimeout(2000);

      // Re-detect tree renderer
      const treeInfo = await page.evaluate(() => {
        const treeContainer = document.querySelector('[data-testid="solution-tree-container"]');
        if (!treeContainer) return { error: 'no-tree-container' };
        const hasCanvas = treeContainer.querySelector('canvas') !== null;
        const hasSvg = treeContainer.querySelector('svg') !== null;
        const isHidden = treeContainer.classList.contains('hidden');
        return { hasCanvas, hasSvg, isHidden, html: treeContainer.innerHTML.substring(0, 300) };
      });
      console.log('Tree info:', JSON.stringify(treeInfo, null, 2));

      await page.screenshot({ path: `test-screenshots/${suffix}-with-tree.png`, fullPage: false });
      console.log(`Tree screenshot saved: ${suffix}-with-tree.png`);
    } else {
      console.log('No Review button found after wrong move, trying show solution directly...');
      // Maybe need to click reveal solution via some other means
      const allBtns = await page.evaluate(() =>
        Array.from(document.querySelectorAll('button')).map(b => b.getAttribute('aria-label') || b.textContent?.trim())
      );
      console.log('Available buttons:', allBtns);
    }
  }

  await browser.close();
  console.log('Done.');
})();
