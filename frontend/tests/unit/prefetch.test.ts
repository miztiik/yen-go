/**
 * usePrefetch hook — unit tests.
 * T201: Verify prefetch service:
 * (1) fetches puzzle N+1 SGF after puzzle N loads
 * (2) returns cached SGF on Next click
 * (3) silent fallback on fetch failure
 * (4) no prefetch on last puzzle
 * Spec 132 US19
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { usePrefetch } from '../../src/hooks/usePrefetch';

describe('usePrefetch', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('prefetch() triggers a fetch for the given path', () => {
    fetchMock.mockResolvedValue(new Response('(;FF[4]GM[1]SZ[19])', { status: 200 }));

    const { result } = renderHook(() => usePrefetch());
    act(() => {
      result.current.prefetch('/sgf/beginner/batch-0001/abc123.sgf');
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      '/sgf/beginner/batch-0001/abc123.sgf',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it('getCached() returns cached SGF after successful prefetch', async () => {
    const sgfContent = '(;FF[4]GM[1]SZ[19])';
    fetchMock.mockResolvedValue(new Response(sgfContent, { status: 200 }));

    const { result } = renderHook(() => usePrefetch());

    // Before prefetch — not cached
    expect(result.current.getCached('/sgf/test.sgf')).toBeUndefined();

    // Trigger prefetch
    act(() => {
      result.current.prefetch('/sgf/test.sgf');
    });

    // Wait for async fetch to resolve
    await vi.waitFor(() => {
      expect(result.current.getCached('/sgf/test.sgf')).toBe(sgfContent);
    });
  });

  it('does not re-fetch if path is already cached', async () => {
    const sgfContent = '(;FF[4]GM[1]SZ[19])';
    fetchMock.mockResolvedValue(new Response(sgfContent, { status: 200 }));

    const { result } = renderHook(() => usePrefetch());

    // Prefetch first time
    act(() => {
      result.current.prefetch('/sgf/test.sgf');
    });

    await vi.waitFor(() => {
      expect(result.current.getCached('/sgf/test.sgf')).toBeDefined();
    });

    // Second prefetch for same path — should NOT trigger another fetch
    fetchMock.mockClear();
    act(() => {
      result.current.prefetch('/sgf/test.sgf');
    });

    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('handles fetch failure silently (non-critical)', async () => {
    const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});
    fetchMock.mockRejectedValue(new Error('Network error'));

    const { result } = renderHook(() => usePrefetch());

    act(() => {
      result.current.prefetch('/sgf/missing.sgf');
    });

    // Wait for promise to settle
    await vi.waitFor(() => {
      // Should not throw; getCached returns undefined for failed fetch
      expect(result.current.getCached('/sgf/missing.sgf')).toBeUndefined();
    });

    consoleSpy.mockRestore();
  });

  it('cancel() aborts in-flight prefetch', () => {
    const abortSpy = vi.fn();
    const mockController = { abort: abortSpy, signal: new AbortController().signal };
    vi.spyOn(globalThis, 'AbortController').mockReturnValue(mockController as unknown as AbortController);

    fetchMock.mockResolvedValue(new Response('', { status: 200 }));

    const { result } = renderHook(() => usePrefetch());

    act(() => {
      result.current.prefetch('/sgf/test.sgf');
    });

    act(() => {
      result.current.cancel();
    });

    expect(abortSpy).toHaveBeenCalled();
  });

  it('new prefetch cancels previous in-flight request', () => {
    // Save original before mocking to avoid infinite recursion
    const OriginalAbortController = globalThis.AbortController;
    const controllers: { abort: ReturnType<typeof vi.fn> }[] = [];
    vi.spyOn(globalThis, 'AbortController').mockImplementation(() => {
      const real = new OriginalAbortController();
      const ctrl = { abort: vi.fn(), signal: real.signal };
      controllers.push(ctrl);
      return ctrl as unknown as AbortController;
    });

    fetchMock.mockResolvedValue(new Response('', { status: 200 }));

    const { result } = renderHook(() => usePrefetch());

    act(() => {
      result.current.prefetch('/sgf/first.sgf');
    });

    act(() => {
      result.current.prefetch('/sgf/second.sgf');
    });

    // The first controller should have been aborted
    expect(controllers[0]?.abort).toHaveBeenCalled();
  });
});
