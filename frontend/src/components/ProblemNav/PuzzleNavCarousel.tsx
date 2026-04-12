/**
 * Puzzle Navigation Carousel Component
 * @module components/ProblemNav/PuzzleNavCarousel
 *
 * Spec 118 - T3.3: PuzzleNavCarousel Component
 * Main carousel component with horizontal scroll
 *
 * Accessibility Features (T3.7):
 * - WAI-ARIA tablist pattern
 * - Keyboard navigation (arrows, Home, End)
 * - Screen reader announcements via live region
 * - Touch gesture support
 */

import { useRef, useEffect, useCallback, useState } from 'preact/hooks';
import type { JSX } from 'preact';
import { PuzzleCard, type PuzzleCardStatus } from './PuzzleCard';
import { ProgressBar } from './ProgressBar';

export interface PuzzleIndicator {
  index: number;
  status: PuzzleCardStatus;
}

export interface PuzzleNavCarouselProps {
  /** Array of puzzle indicators */
  puzzles: PuzzleIndicator[];
  /** Current puzzle index */
  currentIndex: number;
  /** Callback when puzzle is selected */
  onSelectPuzzle: (index: number) => void;
  /** Compact mode */
  compact?: boolean;
}

/**
 * PuzzleNavCarousel - Main carousel navigation
 *
 * Features:
 * - Horizontal scroll layout
 * - CSS scroll-snap
 * - Auto-scroll to current
 * - Touch gesture support
 * - Keyboard navigation
 */
export function PuzzleNavCarousel({
  puzzles,
  currentIndex,
  onSelectPuzzle,
  compact = false,
}: PuzzleNavCarouselProps): JSX.Element {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const touchStartX = useRef<number>(0);
  const touchStartY = useRef<number>(0);
  const touchStartTime = useRef<number>(0);

  // Screen reader announcement state (T3.7)
  const [announcement, setAnnouncement] = useState<string>('');

  // Auto-scroll to current card
  useEffect(() => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const currentCard = container.querySelector(`[data-index="${currentIndex}"]`);

    if (currentCard) {
      currentCard.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
        inline: 'center',
      });
    }

    // Update screen reader announcement
    const puzzle = puzzles[currentIndex];
    if (puzzle) {
      const statusText =
        puzzle.status === 'correct'
          ? 'completed'
          : puzzle.status === 'wrong'
            ? 'incorrect'
            : 'unsolved';
      setAnnouncement(`Puzzle ${currentIndex + 1} of ${puzzles.length}, ${statusText}`);
    }
  }, [currentIndex, puzzles]);

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          if (currentIndex > 0) {
            onSelectPuzzle(currentIndex - 1);
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (currentIndex < puzzles.length - 1) {
            onSelectPuzzle(currentIndex + 1);
          }
          break;
        case 'Home':
          e.preventDefault();
          onSelectPuzzle(0);
          break;
        case 'End':
          e.preventDefault();
          onSelectPuzzle(puzzles.length - 1);
          break;
      }
    },
    [currentIndex, puzzles.length, onSelectPuzzle]
  );

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    container.addEventListener('keydown', handleKeyDown as EventListener);
    return () => container.removeEventListener('keydown', handleKeyDown as EventListener);
  }, [handleKeyDown]);

  // Touch gesture support (T3.5)
  const handleTouchStart = useCallback((e: TouchEvent) => {
    const touch = e.touches[0];
    if (!touch) return; // Safety check for undefined touch

    touchStartX.current = touch.clientX;
    touchStartY.current = touch.clientY;
    touchStartTime.current = Date.now();
  }, []);

  const handleTouchEnd = useCallback(
    (e: TouchEvent) => {
      const touch = e.changedTouches[0];
      if (!touch) return; // Safety check for undefined touch

      const touchEndX = touch.clientX;
      const touchEndY = touch.clientY;
      const touchEndTime = Date.now();

      // Calculate swipe distance and time
      const deltaX = touchEndX - touchStartX.current;
      const deltaY = touchEndY - touchStartY.current;
      const deltaTime = touchEndTime - touchStartTime.current;

      // Thresholds
      const MIN_SWIPE_DISTANCE = 50; // Minimum horizontal distance for swipe
      const MAX_VERTICAL_DRIFT = 80; // Maximum vertical drift to still count as horizontal swipe
      const MAX_SWIPE_TIME = 300; // Maximum time for a swipe gesture

      // Check if it's a valid horizontal swipe
      const isHorizontalSwipe =
        Math.abs(deltaX) > MIN_SWIPE_DISTANCE &&
        Math.abs(deltaY) < MAX_VERTICAL_DRIFT &&
        deltaTime < MAX_SWIPE_TIME;

      if (isHorizontalSwipe) {
        e.preventDefault(); // Prevent default scrolling behavior

        if (deltaX > 0) {
          // Swipe right - go to previous puzzle
          if (currentIndex > 0) {
            onSelectPuzzle(currentIndex - 1);
          }
        } else {
          // Swipe left - go to next puzzle
          if (currentIndex < puzzles.length - 1) {
            onSelectPuzzle(currentIndex + 1);
          }
        }
      }
    },
    [currentIndex, puzzles.length, onSelectPuzzle]
  );

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    container.addEventListener('touchstart', handleTouchStart, { passive: true });
    container.addEventListener('touchend', handleTouchEnd);

    return () => {
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchEnd]);

  // Calculate progress
  const completedCount = puzzles.filter((p) => p.status === 'correct').length;

  return (
    <div className={`puzzle-nav-carousel ${compact ? 'compact' : ''}`}>
      {/* Screen reader announcements (T3.7) */}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      <div
        ref={scrollContainerRef}
        className="flex gap-2 overflow-x-auto scroll-smooth snap-x snap-mandatory py-1 px-0.5 scrollbar-thin"
        role="tablist"
        aria-label="Puzzle navigation"
        aria-orientation="horizontal"
        tabIndex={0}
      >
        {puzzles.map((puzzle, index) => (
          <div key={`card-${index}`} className="snap-start shrink-0" data-index={index}>
            <PuzzleCard
              number={index + 1}
              status={puzzle.status}
              isCurrent={index === currentIndex}
              onClick={() => onSelectPuzzle(index)}
            />
          </div>
        ))}
      </div>

      <ProgressBar completed={completedCount} total={puzzles.length} compact={compact} />
    </div>
  );
}

export default PuzzleNavCarousel;
