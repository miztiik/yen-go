/**
 * safeFetchJson Tests
 * @module tests/unit/safeFetchJson
 *
 * Tests for utils/safeFetchJson — the centralized fetch+JSON utility.
 * Verifies all three guards: response.ok, Content-Type, JSON parse.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { safeFetchJson, safeParseJson, FetchJsonError } from '@/utils/safeFetchJson';

const mockFetch = vi.fn();

describe('safeFetchJson', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // safeFetchJson
  // ==========================================================================

  describe('safeFetchJson', () => {
    it('should return parsed JSON on success', async () => {
      const payload = { version: '1.0', items: [1, 2, 3] };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(payload),
      });

      const result = await safeFetchJson<typeof payload>('https://cdn.example.com/data.json');

      expect(result).toEqual(payload);
      expect(mockFetch).toHaveBeenCalledWith('https://cdn.example.com/data.json');
    });

    it('should pass init options to fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve({}),
      });

      const init = { headers: { Authorization: 'Bearer token' } };
      await safeFetchJson('https://api.example.com/data', init);

      expect(mockFetch).toHaveBeenCalledWith('https://api.example.com/data', init);
    });

    it('should allow missing Content-Type header', async () => {
      const payload = { ok: true };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers(), // no content-type
        json: () => Promise.resolve(payload),
      });

      const result = await safeFetchJson<typeof payload>('https://cdn.example.com/data.json');
      expect(result).toEqual(payload);
    });

    it('should work with mock responses missing headers (test compatibility)', async () => {
      const payload = { data: 42 };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        // No headers property — common in test mocks
        json: () => Promise.resolve(payload),
      });

      const result = await safeFetchJson<typeof payload>('https://cdn.example.com/data.json');
      expect(result).toEqual(payload);
    });

    // Guard 1: response.ok
    it('should throw FetchJsonError on HTTP 404', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: 'Not Found',
      });

      const err = await safeFetchJson('https://cdn.example.com/missing.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('http');
      expect(err.status).toBe(404);
      expect(err.url).toBe('https://cdn.example.com/missing.json');
    });

    it('should throw FetchJsonError on HTTP 500', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      const err = await safeFetchJson('https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('http');
      expect(err.status).toBe(500);
    });

    // Guard 2: Content-Type rejection
    it('should throw FetchJsonError when Content-Type is text/html (SPA fallback)', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'text/html; charset=utf-8' }),
        json: () => Promise.resolve('<html>...</html>'),
      });

      const err = await safeFetchJson('https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('content-type');
      expect(err.message).toContain('HTML');
    });

    // Guard 3: JSON parse failure
    it('should throw FetchJsonError on malformed JSON', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      });

      const err = await safeFetchJson('https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('parse');
    });

    // Network error
    it('should throw FetchJsonError on network failure', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      const err = await safeFetchJson('https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('network');
      expect(err.status).toBe(0);
      expect(err.message).toContain('Failed to fetch');
    });
  });

  // ==========================================================================
  // safeParseJson
  // ==========================================================================

  describe('safeParseJson', () => {
    it('should parse JSON from a successful Response', async () => {
      const payload = { level: 'beginner', count: 42 };
      const response = {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.resolve(payload),
      } as unknown as Response;

      const result = await safeParseJson<typeof payload>(response, 'https://cdn.example.com/data.json');
      expect(result).toEqual(payload);
    });

    it('should reject HTML Content-Type', async () => {
      const response = {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'text/html' }),
        json: () => Promise.resolve({}),
      } as unknown as Response;

      const err = await safeParseJson(response, 'https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('content-type');
    });

    it('should handle JSON parse errors', async () => {
      const response = {
        ok: true,
        status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: () => Promise.reject(new SyntaxError('Unexpected token')),
      } as unknown as Response;

      const err = await safeParseJson(response, 'https://cdn.example.com/data.json').catch((e) => e);

      expect(err).toBeInstanceOf(FetchJsonError);
      expect(err.category).toBe('parse');
    });

    it('should work without headers (test mock compatibility)', async () => {
      const payload = { data: true };
      const response = {
        ok: true,
        status: 200,
        json: () => Promise.resolve(payload),
      } as unknown as Response;

      const result = await safeParseJson<typeof payload>(response, 'https://cdn.example.com/data.json');
      expect(result).toEqual(payload);
    });
  });

  // ==========================================================================
  // FetchJsonError
  // ==========================================================================

  describe('FetchJsonError', () => {
    it('should be an instance of Error', () => {
      const err = new FetchJsonError('test', 'https://x.com', 0, 'network');
      expect(err).toBeInstanceOf(Error);
      expect(err).toBeInstanceOf(FetchJsonError);
    });

    it('should expose structured properties', () => {
      const err = new FetchJsonError('HTTP 404', 'https://cdn.example.com/data.json', 404, 'http');
      expect(err.name).toBe('FetchJsonError');
      expect(err.message).toBe('HTTP 404');
      expect(err.url).toBe('https://cdn.example.com/data.json');
      expect(err.status).toBe(404);
      expect(err.category).toBe('http');
    });
  });
});
