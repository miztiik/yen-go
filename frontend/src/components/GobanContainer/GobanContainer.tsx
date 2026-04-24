/**
 * GobanContainer — Board container with resize + centering, ported from OGS.
 *
 * Wraps PersistentElement + ResizeObserver to:
 * 1. Mount the goban_div (created programmatically by useGoban)
 * 2. Observe **parent** element size changes for available space
 * 3. Call setSquareSizeBasedOnDisplayWidth(min(width, height))
 * 4. Shrink-wrap the container to the board's actual metrics
 *
 * The container shrink-wraps to the board's exact pixel dimensions.
 * The parent layout (e.g. solver-board-col) handles centering.
 * This eliminates dead space between the board and coordinate labels.
 *
 * @module components/GobanContainer/GobanContainer
 */

import { useRef, useEffect, useCallback } from 'preact/hooks';
import type { JSX } from 'preact';
import { PersistentElement } from './PersistentElement';
import type { GobanInstance } from '../../hooks/useGoban';

export interface GobanContainerProps {
  /** The goban DOM element to mount (created programmatically). */
  gobanDiv: HTMLElement | null;
  /** The active goban instance (for resize/centering callbacks). */
  goban: GobanInstance | null;
  /** Additional CSS class. */
  className?: string;
  /** Tooltip text shown on hover (e.g., puzzle filename). */
  title?: string;
}

/**
 * GobanContainer — OGS-aligned board container.
 *
 * Observes the parent element for available space, sizes the board to fit,
 * then shrink-wraps this container to the board's exact dimensions.
 * The parent uses flexbox centering to position the board.
 */
export function GobanContainer({
  gobanDiv,
  goban,
  className = '',
  title,
}: GobanContainerProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastSizeRef = useRef({ width: 0, height: 0 });
  /**
   * Phase 5 (F2): when we publish `--goban-h` the parent column shrinks,
   * which the ResizeObserver below would otherwise interpret as "less
   * space available" and re-size the goban smaller — producing an
   * infinite shrink loop. We remember the parent height we just induced
   * and ignore the next matching observation. */
  const expectedParentShrinkRef = useRef<number | null>(null);

  const recenterGoban = useCallback(() => {
    if (!goban || !gobanDiv || !containerRef.current) return;

    try {
      const metrics = goban.computeMetrics();
      if (metrics) {
        // Size the board element to exactly match goban's computed metrics
        gobanDiv.style.position = 'relative';
        gobanDiv.style.width = `${metrics.width}px`;
        gobanDiv.style.height = `${metrics.height}px`;
        gobanDiv.style.marginLeft = '0px';
        gobanDiv.style.marginTop = '0px';

        // Shrink-wrap the container to match the board's actual dimensions.
        // This eliminates dead space between the board edge and coordinates.
        // The parent layout (e.g. solver-board-col) handles centering.
        containerRef.current.style.width = `${metrics.width}px`;
        containerRef.current.style.height = `${metrics.height}px`;

        // Phase 5 (F2): publish the actual rendered board height back to the
        // parent column as `--goban-h`, so `.solver-board-col` can shrink to
        // hug the goban (the column originally reserved a square viewport
        // slot, leaving 120-180px of dead space below cropped corner puzzles).
        // Pure CSS can't observe child metrics, so we bridge via a custom
        // property. The parent CSS uses `min(...)` as the fallback so the
        // initial render still gets enough space for the goban to size itself.
        const parent = containerRef.current.parentElement;
        if (parent) {
          parent.style.setProperty('--goban-h', `${metrics.height}px`);
          // Tell the ResizeObserver below to ignore the shrink we just caused.
          expectedParentShrinkRef.current = metrics.height;
        }
      }
    } catch {
      // computeMetrics may not be available on all renderer types
    }
  }, [goban, gobanDiv]);

  /**
   * Get the available space from the parent element.
   * We observe the parent instead of the container because the container
   * shrink-wraps to the board — observing it would create a feedback loop.
   */
  const getAvailableSpace = useCallback((): { width: number; height: number } | null => {
    const container = containerRef.current;
    if (!container) return null;
    const parent = container.parentElement;
    if (!parent) return null;
    return { width: parent.clientWidth, height: parent.clientHeight };
  }, []);

  // ResizeObserver for responsive board sizing — watches PARENT for available space
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !goban) return;
    const parent = container.parentElement;
    if (!parent) return;

    // Phase 5 (F2): reset the published goban height so the parent's CSS
    // fallback (`min(100vw - 1rem, 80vh)`) is in effect for the initial
    // measurement of this new goban instance. Without this, switching to a
    // taller puzzle after a cropped one would be sized against the previous
    // puzzle's shrunken parent height.
    parent.style.removeProperty('--goban-h');
    expectedParentShrinkRef.current = null;
    lastSizeRef.current = { width: 0, height: 0 };

    let rafId: number | null = null;

    const handleResize = (entries: ResizeObserverEntry[]): void => {
      const entry = entries[0];
      if (!entry) return;

      const { width, height } = entry.contentRect;
      if (width <= 0 || height <= 0) return;

      // Phase 5 (F2): if the parent just shrank to the height we induced via
      // `--goban-h`, ignore this observation to break the resize feedback loop.
      if (
        expectedParentShrinkRef.current !== null &&
        Math.abs(height - expectedParentShrinkRef.current) < 2
      ) {
        expectedParentShrinkRef.current = null;
        lastSizeRef.current = { width, height };
        return;
      }

      // Debounce: skip if size hasn't meaningfully changed
      const prev = lastSizeRef.current;
      if (Math.abs(prev.width - width) < 1 && Math.abs(prev.height - height) < 1) {
        return;
      }
      lastSizeRef.current = { width, height };

      // Use min(width, height) for square board sizing (OGS pattern)
      const displayWidth = Math.min(width, height);

      if (rafId !== null) cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(() => {
        goban.setSquareSizeBasedOnDisplayWidth(displayWidth);
        recenterGoban();
      });
    };

    const observer = new ResizeObserver(handleResize);
    observer.observe(parent);

    // Initial sizing from available space
    const space = getAvailableSpace();
    if (space && space.width > 0 && space.height > 0) {
      const displayWidth = Math.min(space.width, space.height);
      goban.setSquareSizeBasedOnDisplayWidth(displayWidth);
      requestAnimationFrame(recenterGoban);
    }

    return () => {
      observer.disconnect();
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, [goban, recenterGoban, getAvailableSpace]);

  return (
    <div
      ref={containerRef}
      className={`goban-container ${className}`}
      data-testid="goban-container"
      title={title}
    >
      <PersistentElement elt={gobanDiv} />
    </div>
  );
}
