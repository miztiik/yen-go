/**
 * VirtualList component for rendering large puzzle lists efficiently.
 * @module components/PuzzleList/VirtualList
 *
 * Uses windowing technique to only render visible items,
 * improving performance for large puzzle collections.
 *
 * Constitution Compliance:
 * - I. Zero Runtime Backend: Pure client-side rendering
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'preact/hooks';
import './VirtualList.css';

/**
 * Props for the VirtualList component.
 */
export interface VirtualListProps<T> {
  /** Array of items to render */
  items: T[];
  /** Height of each item in pixels */
  itemHeight: number;
  /** Height of the container in pixels */
  containerHeight: number;
  /** Render function for each item */
  renderItem: (item: T, index: number) => preact.JSX.Element;
  /** Number of items to render outside the visible area (for smooth scrolling) */
  overscan?: number;
  /** Custom class name */
  className?: string;
  /** Key extractor for items */
  getKey?: (item: T, index: number) => string | number;
  /** Callback when scroll reaches near the end */
  onEndReached?: () => void;
  /** Distance from end to trigger onEndReached (in pixels) */
  endReachedThreshold?: number;
}

/**
 * Virtual scroll range calculation.
 */
interface ScrollRange {
  startIndex: number;
  endIndex: number;
  offsetTop: number;
}

/**
 * Calculate the visible range of items.
 */
function calculateRange(
  scrollTop: number,
  containerHeight: number,
  itemHeight: number,
  itemCount: number,
  overscan: number
): ScrollRange {
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(containerHeight / itemHeight);
  const endIndex = Math.min(itemCount - 1, startIndex + visibleCount + overscan * 2);
  const offsetTop = startIndex * itemHeight;

  return { startIndex, endIndex, offsetTop };
}

/**
 * VirtualList component for efficient rendering of large lists.
 */
export function VirtualList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 3,
  className = '',
  getKey,
  onEndReached,
  endReachedThreshold = 200,
}: VirtualListProps<T>): preact.JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);

  // Calculate visible range
  const { startIndex, endIndex, offsetTop } = useMemo(
    () =>
      calculateRange(scrollTop, containerHeight, itemHeight, items.length, overscan),
    [scrollTop, containerHeight, itemHeight, items.length, overscan]
  );

  // Total height of all items
  const totalHeight = items.length * itemHeight;

  // Handle scroll events
  const handleScroll = useCallback(
    (e: Event) => {
      const target = e.target as HTMLDivElement;
      setScrollTop(target.scrollTop);

      // Check if we're near the end
      if (onEndReached) {
        const scrollBottom = target.scrollTop + target.clientHeight;
        if (scrollBottom >= totalHeight - endReachedThreshold) {
          onEndReached();
        }
      }
    },
    [onEndReached, totalHeight, endReachedThreshold]
  );

  // Attach scroll listener
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll]);

  // Get visible items
  const visibleItems = useMemo(() => {
    const result: preact.JSX.Element[] = [];
    for (let i = startIndex; i <= endIndex && i < items.length; i++) {
      const item = items[i];
      if (item === undefined) continue;
      const key = getKey ? getKey(item, i) : i;
      result.push(
        <div
          key={key}
          className="virtual-list__item"
          style={{ height: `${itemHeight}px` }}
        >
          {renderItem(item, i)}
        </div>
      );
    }
    return result;
  }, [items, startIndex, endIndex, itemHeight, renderItem, getKey]);

  return (
    <div
      ref={containerRef}
      className={`virtual-list ${className}`}
      style={{ height: `${containerHeight}px` }}
    >
      <div
        className="virtual-list__content"
        style={{ height: `${totalHeight}px` }}
      >
        <div
          className="virtual-list__visible"
          style={{ transform: `translateY(${offsetTop}px)` }}
        >
          {visibleItems}
        </div>
      </div>
    </div>
  );
}

/**
 * Default export as a generic component.
 */
export default VirtualList;
