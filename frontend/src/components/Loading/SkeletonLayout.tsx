/**
 * SkeletonLayout — placeholder outlines for loading state.
 *
 * Shows navigation panel placeholders and a board area placeholder
 * while puzzle data is being fetched.
 *
 * Spec 127: FR-032, T007
 * @module components/Loading/SkeletonLayout
 */

import type { JSX } from 'preact';

/**
 * Animated skeleton pulse block.
 */
function SkeletonBlock({ className = '' }: { className?: string }): JSX.Element {
  return (
    <div
      className={`bg-[var(--color-bg-secondary)] rounded-[var(--radius-md)] animate-pulse ${className}`}
    />
  );
}

/**
 * SkeletonLayout — renders placeholder outlines for navigation panels
 * and a board area placeholder.
 */
export function SkeletonLayout(): JSX.Element {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[65fr_35fr] gap-[var(--spacing-md)] p-[var(--spacing-md)] min-h-[60vh]">
      {/* Board area placeholder */}
      <div className="flex items-center justify-center">
        <SkeletonBlock className="w-full aspect-square max-w-lg" />
      </div>

      {/* Sidebar placeholder */}
      <div className="flex flex-col gap-[var(--spacing-sm)]">
        <SkeletonBlock className="h-10 w-3/4" />
        <SkeletonBlock className="h-6 w-1/2" />
        <SkeletonBlock className="h-32 w-full" />
        <SkeletonBlock className="h-8 w-2/3" />
        <SkeletonBlock className="h-8 w-1/2" />
      </div>
    </div>
  );
}
