/**
 * PageLayout — shared composition component for all pages.
 *
 * Provides a CSS Grid layout with named slots:
 * - Board: ~65% width on desktop (Goban container)
 * - Sidebar: ~35% width on desktop
 * - Controls: overlay inside Board grid cell
 * - Navigation: within sidebar area
 * - Content: full-width (single-column variant)
 *
 * Variants:
 * - 'puzzle': 2-column board+sidebar
 * - 'single-column': full-width content
 *
 * Spec 127: FR-001, FR-003, FR-008, US2, US6
 * @module components/Layout/PageLayout
 */

import type { ComponentChildren, VNode, FunctionComponent } from 'preact';
import type { PageMode } from '../../types/page-mode';

// ============================================================================
// Types
// ============================================================================

export type LayoutVariant = 'puzzle' | 'single-column';

export interface PageLayoutProps {
  variant?: LayoutVariant;
  children: ComponentChildren;
  /** Page mode identity — sets data-mode attribute for CSS accent cascade. */
  mode?: PageMode;
}

// ============================================================================
// Slot Components
// ============================================================================

interface SlotProps {
  children: ComponentChildren;
  className?: string;
}

/** Board slot — Goban container. */
function Board({ children, className = '' }: SlotProps): VNode {
  return (
    <div
      className={`relative min-h-0 ${className}`}
      data-slot="board"
    >
      {children}
    </div>
  );
}
Board.displayName = 'PageLayout.Board';

/** Sidebar slot — puzzle info, hints, solution tree. */
function Sidebar({ children, className = '' }: SlotProps): VNode {
  return (
    <div
      className={`min-h-0 overflow-y-auto ${className}`}
      data-slot="sidebar"
    >
      {children}
    </div>
  );
}
Sidebar.displayName = 'PageLayout.Sidebar';

/** Controls slot — rendered inside Board area. */
function Controls({ children, className = '' }: SlotProps): VNode {
  return (
    <div
      className={`flex items-center gap-2 py-2 ${className}`}
      data-slot="controls"
    >
      {children}
    </div>
  );
}
Controls.displayName = 'PageLayout.Controls';

/** Navigation slot — within sidebar. */
function Navigation({ children, className = '' }: SlotProps): VNode {
  return (
    <div
      className={`flex items-center justify-between py-2 ${className}`}
      data-slot="navigation"
    >
      {children}
    </div>
  );
}
Navigation.displayName = 'PageLayout.Navigation';

/** Content slot — full-width for single-column variant. */
function Content({ children, className = '' }: SlotProps): VNode {
  return (
    <div
      className={`w-full ${className}`}
      data-slot="content"
    >
      {children}
    </div>
  );
}
Content.displayName = 'PageLayout.Content';

// ============================================================================
// Error Boundary
// ============================================================================

// Unused ErrorBoundary components removed (TS6196, TS6133)

// ============================================================================
// PageLayout Component
// ============================================================================

/**
 * PageLayout — shared page shell with CSS Grid slots.
 *
 * Header is rendered globally in App.tsx — NOT in PageLayout.
 * Background from ThemeTokens (--color-bg-primary).
 * Fluid proportional widths — NO fixed max-width.
 * Responsive stacking below 768px mobile breakpoint.
 */
function PageLayoutBase({
  variant = 'puzzle',
  children,
  mode,
}: PageLayoutProps): VNode {
  const isPuzzle = variant === 'puzzle';

  return (
    <div
      className="flex min-h-screen flex-col bg-[var(--color-bg-primary)]"
      data-layout={variant}
      {...(mode ? { 'data-mode': mode } : {})}
    >
      <main
        className={
          isPuzzle
            ? // Puzzle variant: uses .puzzle-layout CSS class for aspect-ratio-aware 2-column (US13, T185)
              'flex-1 puzzle-layout gap-4 p-4'
            : // Single-column variant: full-width (sections manage own padding)
              'flex-1'
        }
      >
        {children}
      </main>
    </div>
  );
}

// ============================================================================
// Compound Component Pattern
// ============================================================================

type PageLayoutComponent = FunctionComponent<PageLayoutProps> & {
  Board: typeof Board;
  Sidebar: typeof Sidebar;
  Controls: typeof Controls;
  Navigation: typeof Navigation;
  Content: typeof Content;
};

export const PageLayout = PageLayoutBase as PageLayoutComponent;
PageLayout.Board = Board;
PageLayout.Sidebar = Sidebar;
PageLayout.Controls = Controls;
PageLayout.Navigation = Navigation;
PageLayout.Content = Content;

export default PageLayout;
