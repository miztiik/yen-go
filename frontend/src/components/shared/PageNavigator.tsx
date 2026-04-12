/**
 * Page navigator — pagination + jump-to-puzzle component.
 * @module components/shared/PageNavigator
 *
 * Renders a pagination bar with Prev/Next buttons, page number buttons,
 * ellipsis for large page counts, and a "Jump to puzzle #" input.
 *
 * Designed for the SQLite query architecture.
 * Works with both collection queries (sequence number `n`) and
 * non-collection queries (offset-based).
 *
 * See also: plan-composable-fragments-architecture.md §3.2.1
 */

import { useCallback, useState } from 'preact/hooks';
import type { JSX } from 'preact';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  DoubleChevronLeftIcon,
  DoubleChevronRightIcon,
} from '@/components/shared/icons';

// ─── Types ─────────────────────────────────────────────────────────

export interface PageNavigatorProps {
  /** Total number of items in the result set */
  readonly totalItems: number;
  /** Items per page */
  readonly pageSize: number;
  /** Current zero-based offset in the result set */
  readonly currentOffset: number;
  /** Callback when offset changes (via page nav or jump-to) */
  readonly onOffsetChange: (newOffset: number) => void;
  /** Enable collection-style "Jump to puzzle #N" (uses 1-indexed `n`) */
  readonly isCollection?: boolean;
}

// ─── Constants ─────────────────────────────────────────────────────

/** Maximum page buttons to show (excluding ellipses) */
const MAX_VISIBLE_PAGES = 7;

// ─── Component ─────────────────────────────────────────────────────

export function PageNavigator({
  totalItems,
  pageSize,
  currentOffset,
  onOffsetChange,
  isCollection,
}: PageNavigatorProps): JSX.Element | null {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const currentPage = Math.floor(currentOffset / pageSize) + 1;

  const [jumpValue, setJumpValue] = useState('');

  // ─── Navigation Handlers ──────────────────────────────────

  const goToPage = useCallback(
    (page: number) => {
      const clamped = Math.max(1, Math.min(page, totalPages));
      const newOffset = (clamped - 1) * pageSize;
      onOffsetChange(Math.min(newOffset, Math.max(0, totalItems - 1)));
    },
    [totalPages, pageSize, totalItems, onOffsetChange]
  );

  const handleJump = useCallback(() => {
    const num = parseInt(jumpValue, 10);
    if (isNaN(num) || num < 1) return;

    if (isCollection) {
      // Jump by collection sequence number (1-indexed puzzle position)
      const offset = Math.min(num - 1, Math.max(0, totalItems - 1));
      onOffsetChange(offset);
    } else {
      // Jump to this offset position
      const offset = Math.min(num - 1, Math.max(0, totalItems - 1));
      onOffsetChange(offset);
    }
    setJumpValue('');
  }, [jumpValue, isCollection, totalItems, onOffsetChange]);

  const handleJumpKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleJump();
      }
    },
    [handleJump]
  );

  // Don't render for single page
  if (totalPages <= 1 && !isCollection) return null;

  // ─── Page Number Generation ───────────────────────────────

  const pageNumbers = computeVisiblePages(currentPage, totalPages);

  // ─── Render ───────────────────────────────────────────────

  return (
    <nav class="page-navigator" aria-label="Puzzle page navigation">
      <div class="page-navigator__buttons">
        {/* First page */}
        <button
          type="button"
          class="page-navigator__btn"
          onClick={() => goToPage(1)}
          disabled={currentPage <= 1}
          aria-label="First page"
        >
          <DoubleChevronLeftIcon size={16} />
        </button>

        {/* Previous */}
        <button
          type="button"
          class="page-navigator__btn"
          onClick={() => goToPage(currentPage - 1)}
          disabled={currentPage <= 1}
          aria-label="Previous page"
        >
          <ChevronLeftIcon size={16} />
        </button>

        {/* Page numbers */}
        {pageNumbers.map((p, i) =>
          p === null ? (
            <span key={`ellipsis-${i}`} class="page-navigator__ellipsis" aria-hidden="true">
              &hellip;
            </span>
          ) : (
            <button
              key={p}
              type="button"
              class={`page-navigator__btn page-navigator__page ${
                p === currentPage ? 'page-navigator__page--active' : ''
              }`}
              onClick={() => goToPage(p)}
              aria-label={`Page ${p}`}
              aria-current={p === currentPage ? 'page' : undefined}
            >
              {p}
            </button>
          )
        )}

        {/* Next */}
        <button
          type="button"
          class="page-navigator__btn"
          onClick={() => goToPage(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
        >
          <ChevronRightIcon size={16} />
        </button>

        {/* Last page */}
        <button
          type="button"
          class="page-navigator__btn"
          onClick={() => goToPage(totalPages)}
          disabled={currentPage >= totalPages}
          aria-label="Last page"
        >
          <DoubleChevronRightIcon size={16} />
        </button>
      </div>

      {/* Jump to puzzle */}
      <div class="page-navigator__jump">
        <label class="page-navigator__jump-label">
          {isCollection ? 'Jump to puzzle #' : 'Go to puzzle '}
          <input
            type="number"
            class="page-navigator__jump-input"
            min={1}
            max={totalItems}
            value={jumpValue}
            onInput={(e) => setJumpValue((e.target as HTMLInputElement).value)}
            onKeyDown={handleJumpKeyDown}
            aria-label={isCollection ? 'Jump to puzzle number' : 'Go to puzzle position'}
            placeholder={isCollection ? '#' : '#'}
          />
        </label>
        <button type="button" class="page-navigator__jump-btn" onClick={handleJump} aria-label="Go">
          Go
        </button>
      </div>

      {/* Page info */}
      <div class="page-navigator__info" aria-live="polite">
        Page {currentPage} of {totalPages}
        {totalItems > 0 && <span> ({totalItems.toLocaleString('en-US')} puzzles)</span>}
      </div>
    </nav>
  );
}

// ─── Page Number Algorithm ─────────────────────────────────────────

/**
 * Compute which page numbers to show, with ellipsis gaps.
 * Returns an array where null = ellipsis.
 *
 * @example
 * computeVisiblePages(1, 20)  → [1, 2, 3, 4, 5, null, 20]
 * computeVisiblePages(10, 20) → [1, null, 9, 10, 11, null, 20]
 * computeVisiblePages(20, 20) → [1, null, 16, 17, 18, 19, 20]
 * computeVisiblePages(3, 5)   → [1, 2, 3, 4, 5]
 */
export function computeVisiblePages(currentPage: number, totalPages: number): Array<number | null> {
  if (totalPages <= MAX_VISIBLE_PAGES) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: Array<number | null> = [];

  // Always show first page
  pages.push(1);

  // Calculate window around current page
  const windowStart = Math.max(2, currentPage - 1);
  const windowEnd = Math.min(totalPages - 1, currentPage + 1);

  // Ellipsis before window?
  if (windowStart > 2) {
    pages.push(null);
  }

  // Window pages
  for (let i = windowStart; i <= windowEnd; i++) {
    pages.push(i);
  }

  // Ellipsis after window?
  if (windowEnd < totalPages - 1) {
    pages.push(null);
  }

  // Always show last page
  if (totalPages > 1) {
    pages.push(totalPages);
  }

  return pages;
}
