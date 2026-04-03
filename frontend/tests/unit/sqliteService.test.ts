import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockFree = vi.fn();
const mockBind = vi.fn();
const mockStep = vi.fn();
const mockGetAsObject = vi.fn();
const mockPrepare = vi.fn(() => ({
  bind: mockBind,
  step: mockStep,
  getAsObject: mockGetAsObject,
  free: mockFree,
}));
const MockDatabase = vi.fn(() => ({
  prepare: mockPrepare,
}));

vi.mock('sql.js', () => ({
  default: vi.fn(() => Promise.resolve({ Database: MockDatabase })),
}));

describe('sqliteService', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.resetModules();
    mockStep.mockReset();
    mockGetAsObject.mockReset();
    mockBind.mockReset();
    mockFree.mockReset();
    mockPrepare.mockReset();
    mockPrepare.mockImplementation(() => ({
      bind: mockBind,
      step: mockStep,
      getAsObject: mockGetAsObject,
      free: mockFree,
    }));
    MockDatabase.mockReset();
    MockDatabase.mockImplementation(() => ({
      prepare: mockPrepare,
    }));
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  it('isReady returns false before init', async () => {
    const { isReady } = await import('@services/sqliteService');
    expect(isReady()).toBe(false);
  });

  it('query throws before init', async () => {
    const { query } = await import('@services/sqliteService');
    expect(() => query('SELECT 1')).toThrow('Database not initialized. Call init() first.');
  });

  it('init loads database', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      })
      .mockResolvedValueOnce({ ok: false }); // db-version.json (best-effort)

    const { init, isReady } = await import('@services/sqliteService');
    await init();

    expect(isReady()).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith('/yen-go/yengo-puzzle-collections/yengo-search.db');
    expect(MockDatabase).toHaveBeenCalled();
  });

  it('init throws on fetch failure', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

    const { init } = await import('@services/sqliteService');
    await expect(init()).rejects.toThrow('Failed to fetch search database: 404');
  });

  it('query returns results', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      })
      .mockResolvedValueOnce({ ok: false });

    const { init, query } = await import('@services/sqliteService');
    await init();

    mockStep.mockReturnValueOnce(true).mockReturnValueOnce(true).mockReturnValueOnce(false);
    mockGetAsObject
      .mockReturnValueOnce({ content_hash: 'abc123', level_id: 120 })
      .mockReturnValueOnce({ content_hash: 'def456', level_id: 130 });

    const results = query<{ content_hash: string; level_id: number }>('SELECT * FROM puzzles');

    expect(results).toHaveLength(2);
    expect(results[0]).toEqual({ content_hash: 'abc123', level_id: 120 });
    expect(results[1]).toEqual({ content_hash: 'def456', level_id: 130 });
    expect(mockFree).toHaveBeenCalled();
  });

  it('query passes params to bind', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      })
      .mockResolvedValueOnce({ ok: false });

    const { init, query } = await import('@services/sqliteService');
    await init();

    mockStep.mockReturnValueOnce(false);

    query('SELECT * FROM puzzles WHERE level_id = ?', [120]);

    expect(mockBind).toHaveBeenCalledWith([120]);
  });

  it('getDb returns null before init', async () => {
    const { getDb } = await import('@services/sqliteService');
    expect(getDb()).toBeNull();
  });

  it('getDb returns database after init', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      })
      .mockResolvedValueOnce({ ok: false });

    const { init, getDb } = await import('@services/sqliteService');
    await init();

    expect(getDb()).not.toBeNull();
  });

  // --- GAP-3: init retry after failure ---

  it('init can be retried after failure', async () => {
    // First call fails
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 });

    const { init, isReady } = await import('@services/sqliteService');
    await expect(init()).rejects.toThrow('Failed to fetch search database: 500');
    expect(isReady()).toBe(false);

    // Second call should attempt again (not cache the rejection)
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
      })
      .mockResolvedValueOnce({ ok: false });
    await init();
    expect(isReady()).toBe(true);
  });

  // --- checkForUpdates ---

  describe('checkForUpdates', () => {
    const mockLocalStorage: Record<string, string> = {};

    beforeEach(() => {
      Object.keys(mockLocalStorage).forEach(k => delete mockLocalStorage[k]);
      vi.stubGlobal('localStorage', {
        getItem: vi.fn((key: string) => mockLocalStorage[key] ?? null),
        setItem: vi.fn((key: string, val: string) => { mockLocalStorage[key] = val; }),
        removeItem: vi.fn((key: string) => { delete mockLocalStorage[key]; }),
      });
    });

    it('returns updateAvailable true when remote differs from stored', async () => {
      mockLocalStorage['yen-go-db-version'] = '20260313-aabbccdd';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ db_version: '20260314-11223344' }),
      });

      const { checkForUpdates } = await import('@services/sqliteService');
      const result = await checkForUpdates();

      expect(result.updateAvailable).toBe(true);
      expect(result.currentVersion).toBe('20260313-aabbccdd');
      expect(result.newVersion).toBe('20260314-11223344');
    });

    it('returns updateAvailable false when versions match', async () => {
      mockLocalStorage['yen-go-db-version'] = '20260313-aabbccdd';
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ db_version: '20260313-aabbccdd' }),
      });

      const { checkForUpdates } = await import('@services/sqliteService');
      const result = await checkForUpdates();

      expect(result.updateAvailable).toBe(false);
    });

    it('returns updateAvailable false on fetch failure', async () => {
      mockFetch.mockResolvedValueOnce({ ok: false, status: 404 });

      const { checkForUpdates } = await import('@services/sqliteService');
      const result = await checkForUpdates();

      expect(result.updateAvailable).toBe(false);
      expect(result.newVersion).toBeNull();
    });

    it('returns updateAvailable false on network error', async () => {
      mockFetch.mockRejectedValueOnce(new Error('network'));

      const { checkForUpdates } = await import('@services/sqliteService');
      const result = await checkForUpdates();

      expect(result.updateAvailable).toBe(false);
    });
  });
});
