/**
 * Debug Collection Page Test
 * Quick diagnostic test to identify the frontend issue.
 */

import { test, expect } from '@playwright/test';

// Override base URL for this test file - use existing dev server
test.use({ baseURL: 'http://localhost:5173' });

test.describe('Debug Collection Page', () => {
  test.setTimeout(30000); // 30 second timeout
  
  test('should load elementary collection', async ({ page }) => {
    // Track errors
    const errors: string[] = [];
    const consoleLogs: string[] = [];
    
    page.on('console', msg => {
      consoleLogs.push(`${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', error => errors.push(error.message));
    page.on('requestfailed', request => {
      errors.push(`FAILED REQUEST: ${request.url()}`);
    });
    
    // Go directly to the collection page
    await page.goto('/collections/level-elementary');
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    
    // Take a screenshot
    await page.screenshot({ path: 'tests/e2e/test-results/debug-collection.png', fullPage: true });
    
    // Log what we see on the page
    console.log('PAGE TITLE:', await page.title());
    console.log('PAGE URL:', page.url());
    console.log('ERRORS:', errors.join('\n'));
    console.log('CONSOLE LOGS (last 20):', consoleLogs.slice(-20).join('\n'));
    
    // Get body text
    const bodyText = await page.locator('body').innerText();
    console.log('BODY TEXT:', bodyText);
    
    // Check for specific elements
    const hasGoBoard = await page.locator('[data-testid="go-board"]').count();
    const hasBackButton = await page.locator('text=Back').count();
    const hasLoadingText = await page.locator('text=/Loading/i').count();
    const hasErrorText = await page.locator('text=/error|failed|not found|could not/i').count();
    const hasPuzzle = await page.locator('svg').count();
    
    console.log('Has Go Board:', hasGoBoard);
    console.log('Has Back Button:', hasBackButton);
    console.log('Has Loading:', hasLoadingText);
    console.log('Has Error:', hasErrorText);
    console.log('Has SVG:', hasPuzzle);
    
    // Expect no errors 
    expect(errors.length).toBe(0);
    // Expect puzzle to be visible
    expect(hasPuzzle).toBeGreaterThan(0);
  });

  test('should check if collection service can load data', async ({ page }) => {
    // Navigate to home first
    await page.goto('/');
    
    // Check what levels are available
    const levelCheck = await page.evaluate(async () => {
      try {
        // Get the SKILL_LEVELS from models
        const response = await fetch('/yengo-puzzle-collections/views/by-level/elementary.json');
        const data = await response.json();
        
        // Also try to load the index
        const indexResp = await fetch('/yengo-puzzle-collections/views/by-level/index.json');
        const indexOk = indexResp.ok;
        let indexData = null;
        if (indexOk) {
          indexData = await indexResp.json();
        }
        
        return {
          success: true,
          dataLength: Array.isArray(data) ? data.length : 'not-array',
          sample: Array.isArray(data) ? data.slice(0, 1) : data,
          indexExists: indexOk,
          indexData: indexData ? Object.keys(indexData) : null,
        };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    });
    
    console.log('Level check result:', JSON.stringify(levelCheck, null, 2));
    
    // Try to fetch the collection data directly
    const result = await page.evaluate(async () => {
      try {
        const response = await fetch('/yengo-puzzle-collections/views/by-level/elementary.json');
        const status = response.status;
        const contentType = response.headers.get('content-type');
        if (!response.ok) {
          return { success: false, status, contentType, error: 'HTTP error' };
        }
        const data = await response.json();
        return { 
          success: true, 
          status,
          contentType,
          dataLength: Array.isArray(data) ? data.length : Object.keys(data).length,
          sample: Array.isArray(data) ? data.slice(0, 2) : data
        };
      } catch (e) {
        return { success: false, error: String(e) };
      }
    });
    
    console.log('Collection data fetch result:', JSON.stringify(result, null, 2));
    
    // Check result
    expect(result.success).toBe(true);
  });
});
