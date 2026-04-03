/**
 * UI Diagnostic Test
 * Captures screenshots of current UI state for analysis
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';

// Use existing dev server
test.use({ baseURL: 'http://localhost:5173' });

test.describe('UI Diagnostic Screenshots', () => {
  test.setTimeout(20000); // 20 second timeout
  
  test('capture collection page screenshot', async ({ page }) => {
    // Track console errors
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Go to the collection page
    await page.goto('/collections/level-elementary', { waitUntil: 'networkidle', timeout: 10000 });
    
    // Wait for any animations
    await page.waitForTimeout(1000);
    
    // Capture full page screenshot
    const screenshotDir = 'tests/e2e/test-results/ui-diagnostic';
    if (!fs.existsSync(screenshotDir)) {
      fs.mkdirSync(screenshotDir, { recursive: true });
    }
    
    await page.screenshot({ 
      path: `${screenshotDir}/collection-page-full.png`, 
      fullPage: true 
    });
    
    // Capture viewport screenshot
    await page.screenshot({ 
      path: `${screenshotDir}/collection-page-viewport.png` 
    });
    
    // Log page info
    console.log('URL:', page.url());
    console.log('Title:', await page.title());
    console.log('Errors:', errors);
    
    // Check for key elements
    const hasBoard = await page.locator('svg').count();
    const hasCanvas = await page.locator('canvas').count();
    const bodyText = await page.locator('body').innerText();
    
    console.log('SVG count:', hasBoard);
    console.log('Canvas count:', hasCanvas);
    console.log('Body text preview:', bodyText.substring(0, 500));
    
    // Just pass - we're using this for diagnosis
    expect(true).toBe(true);
  });

  test('capture daily challenge screenshot', async ({ page }) => {
    await page.goto('/daily', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(1000);
    
    const screenshotDir = 'tests/e2e/test-results/ui-diagnostic';
    
    await page.screenshot({ 
      path: `${screenshotDir}/daily-page-full.png`, 
      fullPage: true 
    });
    
    console.log('Daily page captured');
    expect(true).toBe(true);
  });

  test('capture home page screenshot', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(500);
    
    const screenshotDir = 'tests/e2e/test-results/ui-diagnostic';
    
    await page.screenshot({ 
      path: `${screenshotDir}/home-page.png`, 
      fullPage: true 
    });
    
    console.log('Home page captured');
    expect(true).toBe(true);
  });
});
