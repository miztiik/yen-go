/**
 * Unit tests for useAutoAdvance hook.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useAutoAdvance } from '../../src/hooks/useAutoAdvance';

describe('useAutoAdvance', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does nothing when disabled', () => {
    const onAdvance = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: false, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });

    expect(result.current.isCountingDown).toBe(false);
    expect(result.current.remainingMs).toBe(0);
    expect(onAdvance).not.toHaveBeenCalled();
  });

  it('starts countdown when enabled', () => {
    const onAdvance = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });

    expect(result.current.isCountingDown).toBe(true);
    expect(result.current.remainingMs).toBe(3000);
  });

  it('fires onAdvance after delay completes', () => {
    const onAdvance = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });
    act(() => { vi.advanceTimersByTime(3100); });

    expect(onAdvance).toHaveBeenCalledTimes(1);
    expect(result.current.isCountingDown).toBe(false);
    expect(result.current.remainingMs).toBe(0);
  });

  it('cancels countdown and fires onCancel', () => {
    const onAdvance = vi.fn();
    const onCancel = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance, onCancel })
    );

    act(() => { result.current.startCountdown(); });
    act(() => { vi.advanceTimersByTime(1000); });
    act(() => { result.current.cancelCountdown(); });

    expect(result.current.isCountingDown).toBe(false);
    expect(result.current.remainingMs).toBe(0);
    expect(onAdvance).not.toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('cancels automatically when enabled is toggled off', () => {
    const onAdvance = vi.fn();
    let enabled = true;
    const { result, rerender } = renderHook(() =>
      useAutoAdvance({ enabled, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });
    expect(result.current.isCountingDown).toBe(true);

    // Toggle off
    enabled = false;
    rerender();

    expect(result.current.isCountingDown).toBe(false);
    expect(onAdvance).not.toHaveBeenCalled();
  });

  it('does not start twice if already counting', () => {
    const onAdvance = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });
    act(() => { result.current.startCountdown(); }); // second call should be no-op

    act(() => { vi.advanceTimersByTime(3100); });
    expect(onAdvance).toHaveBeenCalledTimes(1);
  });

  it('exposes totalMs matching delayMs', () => {
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 2000, onAdvance: vi.fn() })
    );

    expect(result.current.totalMs).toBe(2000);
  });

  it('cleans up on unmount', () => {
    const onAdvance = vi.fn();
    const { result, unmount } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance })
    );

    act(() => { result.current.startCountdown(); });
    unmount();

    act(() => { vi.advanceTimersByTime(5000); });
    expect(onAdvance).not.toHaveBeenCalled();
  });

  it('cancelCountdown is a no-op when not counting', () => {
    const onCancel = vi.fn();
    const { result } = renderHook(() =>
      useAutoAdvance({ enabled: true, delayMs: 3000, onAdvance: vi.fn(), onCancel })
    );

    // Cancel without ever starting — should not fire onCancel
    act(() => { result.current.cancelCountdown(); });

    expect(onCancel).not.toHaveBeenCalled();
    expect(result.current.isCountingDown).toBe(false);
  });
});
