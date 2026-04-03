/**
 * PersistentElement — Mounts a raw DOM element in the Preact tree.
 *
 * Ported from OGS pattern. Used by GobanContainer to insert
 * the goban_div (created programmatically) into the component tree
 * without Preact re-creating it on each render.
 *
 * @module components/GobanContainer/PersistentElement
 */

import { useRef, useEffect } from 'preact/hooks';
import type { JSX } from 'preact';

export interface PersistentElementProps {
  /** The DOM element to mount. */
  elt: HTMLElement | null;
  /** Additional className for the wrapper div. */
  className?: string;
}

/**
 * Mounts a raw DOM element into the Preact render tree.
 * The element persists across re-renders without being recreated.
 */
export function PersistentElement({ elt, className }: PersistentElementProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !elt) return;

    // Only append if not already a child
    if (elt.parentElement !== container) {
      // Clear container first
      while (container.firstChild) {
        container.removeChild(container.firstChild);
      }
      container.appendChild(elt);
    }

    return () => {
      // On unmount, remove the element from the container
      // but don't destroy it (goban manages its own lifecycle)
      if (elt.parentElement === container) {
        container.removeChild(elt);
      }
    };
  }, [elt]);

  return <div ref={containerRef} className={className} />;
}
