/**
 * Input sanitization utilities for security.
 * @module utils/sanitize
 */

/**
 * HTML entities to escape.
 */
const HTML_ENTITIES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#x27;',
  '/': '&#x2F;',
  '`': '&#x60;',
  '=': '&#x3D;',
};

/**
 * Escape HTML special characters to prevent XSS.
 *
 * @param str - String to escape
 * @returns Escaped string safe for HTML insertion
 */
export function escapeHtml(str: string): string {
  return str.replace(/[&<>"'`=/]/g, (char) => HTML_ENTITIES[char] ?? char);
}

/**
 * Sanitize a string for safe display.
 * Removes potentially dangerous characters and trims whitespace.
 *
 * @param str - String to sanitize
 * @param maxLength - Maximum allowed length (default: 1000)
 * @returns Sanitized string
 */
export function sanitizeString(str: string, maxLength: number = 1000): string {
  if (typeof str !== 'string') {
    return '';
  }

  return str
    .trim()
    .slice(0, maxLength)
    .replace(/[\x00-\x1F\x7F]/g, ''); // eslint-disable-line no-control-regex
}

/**
 * Sanitize a puzzle ID.
 * Only allows alphanumeric characters, hyphens, and underscores.
 *
 * @param id - Puzzle ID to sanitize
 * @returns Sanitized ID or empty string if invalid
 */
export function sanitizePuzzleId(id: string): string {
  if (typeof id !== 'string') {
    return '';
  }

  // Only allow alphanumeric, hyphens, underscores
  const sanitized = id.replace(/[^a-zA-Z0-9_-]/g, '');

  // Max length for puzzle IDs
  return sanitized.slice(0, 100);
}

/**
 * Validate and sanitize a coordinate.
 *
 * @param coord - Coordinate value to validate
 * @param boardSize - Board size (9, 13, 19)
 * @returns Sanitized coordinate or null if invalid
 */
export function sanitizeCoordinate(
  coord: unknown,
  boardSize: number
): number | null {
  if (typeof coord !== 'number' || !Number.isInteger(coord)) {
    return null;
  }

  if (coord < 0 || coord >= boardSize) {
    return null;
  }

  return coord;
}

/**
 * Validate and sanitize a board size.
 *
 * @param size - Board size to validate
 * @returns Valid board size or default (19)
 */
export function sanitizeBoardSize(size: unknown): 9 | 13 | 19 {
  if (size === 9 || size === 13 || size === 19) {
    return size;
  }
  return 19;
}

/**
 * Sanitize JSON data from localStorage or external sources.
 *
 * @param data - Data to sanitize
 * @param schema - Expected schema properties
 * @returns Sanitized data or null if invalid
 */
export function sanitizeJsonData<T extends object>(
  data: unknown,
  schema: { [K in keyof T]: 'string' | 'number' | 'boolean' | 'array' | 'object' }
): T | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }

  const result: Partial<T> = {};

  for (const [key, expectedType] of Object.entries(schema)) {
    const value = (data as Record<string, unknown>)[key];

    if (value === undefined) {
      continue;
    }

    switch (expectedType) {
      case 'string':
        if (typeof value === 'string') {
          result[key as keyof T] = sanitizeString(value) as T[keyof T];
        }
        break;
      case 'number':
        if (typeof value === 'number' && Number.isFinite(value)) {
          result[key as keyof T] = value as T[keyof T];
        }
        break;
      case 'boolean':
        if (typeof value === 'boolean') {
          result[key as keyof T] = value as T[keyof T];
        }
        break;
      case 'array':
        if (Array.isArray(value)) {
          result[key as keyof T] = value as T[keyof T];
        }
        break;
      case 'object':
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          result[key as keyof T] = value as T[keyof T];
        }
        break;
    }
  }

  return result as T;
}

/**
 * Validate URL is safe (same-origin or allowed external).
 *
 * @param url - URL to validate
 * @param allowedHosts - List of allowed external hosts
 * @returns Whether URL is safe
 */
export function isUrlSafe(url: string, allowedHosts: string[] = []): boolean {
  try {
    const parsed = new URL(url, window.location.origin);

    // Allow same-origin
    if (parsed.origin === window.location.origin) {
      return true;
    }

    // Check allowed external hosts
    return allowedHosts.includes(parsed.host);
  } catch {
    return false;
  }
}

/**
 * Sanitize a filename for safe storage/display.
 *
 * @param filename - Filename to sanitize
 * @returns Sanitized filename
 */
export function sanitizeFilename(filename: string): string {
  if (typeof filename !== 'string') {
    return '';
  }

  return filename
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, '') // eslint-disable-line no-control-regex
    .replace(/^\.+/, '') // Remove leading dots
    .slice(0, 255); // Max filename length
}

/**
 * Create a safe text node instead of setting innerHTML.
 *
 * @param text - Text content
 * @returns Text node
 */
export function createSafeTextNode(text: string): Text {
  return document.createTextNode(sanitizeString(text));
}

/**
 * Safely parse JSON with error handling.
 *
 * @param jsonString - JSON string to parse
 * @returns Parsed object or null on error
 */
export function safeJsonParse<T>(jsonString: string): T | null {
  try {
    return JSON.parse(jsonString) as T;
  } catch {
    return null;
  }
}

/**
 * Safely stringify JSON with error handling.
 *
 * @param data - Data to stringify
 * @returns JSON string or null on error
 */
export function safeJsonStringify(data: unknown): string | null {
  try {
    return JSON.stringify(data);
  } catch {
    return null;
  }
}
