/**
 * utils.js — Shared utilities for Enrichment Lab GUI modules.
 */

const ESC_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };

/**
 * Escape a string for safe insertion into HTML content or attribute contexts.
 * Handles &, <, >, ", and ' to prevent XSS via attribute breakout.
 */
export function escHtml(s) {
  return String(s).replace(/[&<>"']/g, ch => ESC_MAP[ch]);
}
