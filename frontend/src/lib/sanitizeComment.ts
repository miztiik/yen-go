/**
 * SGF Comment Sanitizer (UI-041)
 *
 * Safely renders SGF comment text (C[] property) in the UI.
 * SGF comments can contain arbitrary text — raw HTML, markdown-style
 * formatting, backslash escapes, and Unicode.
 *
 * Rules:
 * - Escape HTML to prevent XSS (do NOT render as HTML)
 * - Unescape SGF FF[4] escapes: \] → ] and \\ → \
 * - Convert \n and \r\n to <br> for line breaks
 * - Render everything else as plain text
 * - Do NOT strip characters that look like formatting (#, *, etc.)
 *
 * @module lib/sanitizeComment
 */

/**
 * Sanitize an SGF comment for safe display.
 *
 * Returns an HTML string safe for dangerouslySetInnerHTML,
 * containing only text and <br> tags.
 *
 * @param raw - Raw SGF comment text (from C[] property)
 * @returns Sanitized HTML string, or empty string if comment is blank
 */
export function sanitizeComment(raw: string | undefined | null): string {
  if (!raw) return '';

  let text = raw;

  // 1. Strip leading/trailing whitespace first (before any conversion)
  text = text.trim();

  // Return empty if only whitespace/newlines
  if (!text) return '';

  // 2. Normalize line endings: \r\n → \n, \r → \n
  text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  // 3. Unescape SGF FF[4] escapes BEFORE HTML escaping
  //    SGF spec defines exactly two escapes: \] → ] and \\ → \
  text = text.replace(/\\\]/g, ']').replace(/\\\\/g, '\\');

  // 4. Escape HTML entities to prevent XSS
  text = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  // 5. Convert newlines to <br> for rendering
  text = text.replace(/\n/g, '<br>');

  return text;
}
