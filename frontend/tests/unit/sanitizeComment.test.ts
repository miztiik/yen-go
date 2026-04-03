/**
 * Tests for sanitizeComment utility (UI-041)
 */
import { describe, it, expect } from 'vitest';
import { sanitizeComment } from '../../src/lib/sanitizeComment';

describe('sanitizeComment', () => {
  it('returns empty string for null/undefined', () => {
    expect(sanitizeComment(null)).toBe('');
    expect(sanitizeComment(undefined)).toBe('');
    expect(sanitizeComment('')).toBe('');
  });

  it('escapes HTML tags', () => {
    expect(sanitizeComment('<b>Bold</b>')).toBe('&lt;b&gt;Bold&lt;/b&gt;');
    expect(sanitizeComment('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
    );
  });

  it('unescapes SGF FF[4] escapes', () => {
    expect(sanitizeComment('text with \\] bracket')).toBe('text with ] bracket');
    expect(sanitizeComment('backslash \\\\ here')).toBe('backslash \\ here');
  });

  it('converts newlines to <br>', () => {
    expect(sanitizeComment('line1\nline2')).toBe('line1<br>line2');
    expect(sanitizeComment('line1\r\nline2')).toBe('line1<br>line2');
  });

  it('handles multiple consecutive newlines', () => {
    expect(sanitizeComment('a\n\nb')).toBe('a<br><br>b');
  });

  it('preserves markdown-style characters as plain text', () => {
    expect(sanitizeComment('# Heading')).toBe('# Heading');
    expect(sanitizeComment('**bold**')).toBe('**bold**');
    expect(sanitizeComment('[link](url)')).toBe('[link](url)');
  });

  it('preserves Unicode characters', () => {
    expect(sanitizeComment('黒は白を取る')).toBe('黒は白を取る');
    expect(sanitizeComment('Café résumé')).toBe('Café résumé');
  });

  it('trims leading/trailing whitespace', () => {
    expect(sanitizeComment('  hello  ')).toBe('hello');
  });

  it('returns empty string for whitespace-only input', () => {
    expect(sanitizeComment('   ')).toBe('');
    expect(sanitizeComment('\n\n\n')).toBe('');
  });

  it('handles ampersands correctly', () => {
    expect(sanitizeComment('A & B')).toBe('A &amp; B');
  });

  it('handles combined SGF escape + HTML', () => {
    expect(sanitizeComment('<br>New \\] line')).toBe('&lt;br&gt;New ] line');
  });
});
