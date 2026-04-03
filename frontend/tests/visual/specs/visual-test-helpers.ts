/**
 * Shared helpers for visual regression tests.
 * @module tests/visual/specs/visual-test-helpers
 *
 * Centralised utilities to avoid DRY violations across visual spec files.
 * Every visual spec should import from here instead of defining inline.
 */

import type { Page } from '@playwright/test';

// ============================================================================
// Viewport definitions (aligned with playwright.config.ts projects + existing specs)
// ============================================================================

export const VIEWPORTS = [
  { width: 375, height: 667, name: 'mobile' },
  { width: 667, height: 375, name: 'mobile-landscape' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 1280, height: 800, name: 'desktop' },
] as const;

// ============================================================================
// Animation suppression
// ============================================================================

/**
 * Disable all CSS transitions and animations for deterministic screenshots.
 * Call after page navigation completes but before taking screenshots.
 */
export async function disableAnimations(page: Page): Promise<void> {
  await page.addStyleTag({
    content:
      '*, *::before, *::after { transition-duration: 0ms !important; animation-duration: 0ms !important; }',
  });
}

// ============================================================================
// Timing constants
// ============================================================================

/** Wait duration (ms) for UI state changes to settle after click/interaction. */
export const INTERACTION_SETTLE_MS = 300;

/** Wait duration (ms) for focus ring rendering. */
export const FOCUS_SETTLE_MS = 150;

// ============================================================================
// Screenshot defaults
// ============================================================================

/** Default maxDiffPixelRatio for component-level screenshots. */
export const DEFAULT_MAX_DIFF = 0.02;

/** Standard screenshot options for full-page captures. */
export const FULL_PAGE_SCREENSHOT = {
  fullPage: true,
  maxDiffPixelRatio: DEFAULT_MAX_DIFF,
};

// ============================================================================
// Clip helpers
// ============================================================================

/** Padding (px) added around bounding-box clips to capture focus rings / shadows. */
const CLIP_PADDING = 8;

/**
 * Expand a bounding box by CLIP_PADDING on each side for screenshot clips.
 * Prevents focus rings and drop shadows from being clipped at element edges.
 */
export function padClip(box: { x: number; y: number; width: number; height: number }): {
  x: number;
  y: number;
  width: number;
  height: number;
} {
  return {
    x: Math.max(0, box.x - CLIP_PADDING),
    y: Math.max(0, box.y - CLIP_PADDING),
    width: box.width + CLIP_PADDING * 2,
    height: box.height + CLIP_PADDING * 2,
  };
}
