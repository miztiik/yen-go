// @ts-nocheck
/**
 * PuzzleSidebar — Sidebar component for puzzle solving page.
 * @module components/Puzzle/PuzzleSidebar
 *
 * Structured in three sections (identity → tools → content):
 * 1. Identity: Level, collection, tags, ko context
 * 2. Tools: Transform controls
 * 3. Content: Hints/comments (solving mode) or solution tree (review mode)
 *
 * Spec 132 US11, Tasks T135–T141
 */

import type { FunctionComponent, RefObject } from 'preact';
import type { TransformSettings } from '../../types/goban';
import type { GobanInstance } from '../../hooks/useGoban';
import { TransformBar } from '../Transforms';
import { SolutionTreePanel, BreadcrumbTrail, CommentPanel, TreeControls } from '../SolutionTree';

// ============================================================================
// Props
// ============================================================================

export interface PuzzleSidebarProps {
  /** Current puzzle state status */
  status: string;
  /** Whether in review mode (show tree controls) */
  isReviewMode: boolean;
  /** Reference to goban instance */
  gobanRef: RefObject<GobanInstance | null>;
  /** Tree container ref for goban's built-in tree */
  treeContainerRef: RefObject<HTMLDivElement>;
  /** Transform settings */
  transformSettings: TransformSettings;
  /** Transform toggle handlers */
  onToggleFlipH: () => void;
  onToggleFlipV: () => void;
  onToggleFlipDiagonal: () => void;
  onToggleSwapColors: () => void;
  onToggleZoom: () => void;
  onRandomize: () => void;
  onResetTransforms: () => void;
  /** Current comment from puzzle */
  currentComment?: string | undefined;
  /** Current hint tier (0 = no hint) */
  currentHintTier: number;
  /** Available hints from puzzle metadata */
  hints: readonly string[];
  /** Skill level for display (YG property) */
  skillLevel?: string | undefined;
  /** Tags from puzzle (YT property) */
  tags?: readonly string[] | undefined;
  /** Ko context (YK property) */
  koContext?: 'none' | 'simple' | 'complex' | undefined;
  /** Corner position (YC property) */
  cornerPosition?: string | undefined;
  /** Collection name for navigable link */
  collection?: { id: string; name: string } | undefined;
  /** Additional CSS class */
  className?: string | undefined;
}

// ============================================================================
// Component
// ============================================================================

/** Ko badge color mapping */
const KO_STYLES: Record<string, { cls: string; label: string }> = {
  simple: { cls: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400', label: 'Simple Ko' },
  complex: { cls: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400', label: 'Complex Ko' },
};

/**
 * PuzzleSidebar — Three-section sidebar: identity → tools → content.
 *
 * Constrained to max-width 400px. Uses Tailwind utility classes.
 */
export const PuzzleSidebar: FunctionComponent<PuzzleSidebarProps> = ({
  isReviewMode,
  gobanRef,
  treeContainerRef,
  transformSettings,
  onToggleFlipH,
  onToggleFlipV,
  onToggleFlipDiagonal,
  onToggleSwapColors,
  onToggleZoom,
  onRandomize,
  onResetTransforms,
  currentComment,
  currentHintTier,
  hints,
  skillLevel,
  tags,
  koContext,
  cornerPosition,
  collection,
  className,
}) => {
  return (
    <aside
      className={`flex max-w-[400px] flex-col gap-4 rounded-lg border border-[--color-border] bg-[--color-bg-secondary] p-4 ${className ?? ''}`}
      data-testid="puzzle-sidebar"
    >
      {/* ── Section 1: Identity ── */}
      <div data-testid="puzzle-metadata">
        <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-text-primary]">Puzzle Info</h3>
        <div className="flex flex-col gap-2">
          {/* Level (YG) */}
          {skillLevel !== undefined && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="shrink-0 text-[--color-text-muted]">Level:</span>
              <span className="text-[--color-text-primary]">{skillLevel}</span>
            </div>
          )}

          {/* Collection link */}
          {collection !== undefined && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="shrink-0 text-[--color-text-muted]">Collection:</span>
              <a
                href={`/collections/${collection.id}`}
                className="text-[--color-accent] underline decoration-[--color-accent]/30 hover:decoration-[--color-accent]"
              >
                {collection.name}
              </a>
            </div>
          )}

          {/* Corner position (YC) */}
          {cornerPosition !== undefined && cornerPosition !== 'C' && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="shrink-0 text-[--color-text-muted]">Corner:</span>
              <span className="text-[--color-text-primary]">{cornerPosition}</span>
            </div>
          )}

          {/* Hints available (YH) */}
          <div className="flex items-center gap-2 text-[13px]">
            <span className="shrink-0 text-[--color-text-muted]">Hints:</span>
            <span className="text-[--color-text-primary]">
              {hints.length > 0 ? `${hints.length} available` : 'None'}
            </span>
          </div>

          {/* Ko Context (YK) */}
          {koContext !== undefined && koContext !== 'none' && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="shrink-0 text-[--color-text-muted]">Ko:</span>
              <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${KO_STYLES[koContext]?.cls ?? ''}`}>
                {KO_STYLES[koContext]?.label ?? koContext}
              </span>
            </div>
          )}

          {/* Tags (YT) */}
          {tags !== undefined && tags.length > 0 && (
            <div className="flex items-center gap-2 text-[13px]">
              <span className="shrink-0 text-[--color-text-muted]">Tags:</span>
              <div className="flex flex-wrap gap-1">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-[--color-bg-tertiary] px-1.5 py-0.5 text-[11px] text-[--color-text-secondary]"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Section 2: Tools ── */}
      <div>
        <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-text-primary]">Transforms</h3>
        <TransformBar
          settings={transformSettings}
          onToggleFlipH={onToggleFlipH}
          onToggleFlipV={onToggleFlipV}
          onToggleFlipDiagonal={onToggleFlipDiagonal}
          onToggleSwapColors={onToggleSwapColors}
          onToggleZoom={onToggleZoom}
          onRandomize={onRandomize}
          onReset={onResetTransforms}
          disabled={isReviewMode}
        />
      </div>

      {/* ── Section 3: Content ── */}

      {/* Review mode: Solution tree exploration */}
      {isReviewMode && (
        <>
          <div>
            <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-text-primary]">Solution Tree</h3>
            <TreeControls
              gobanRef={gobanRef}
              keyboardEnabled={isReviewMode}
            />
          </div>

          <BreadcrumbTrail gobanRef={gobanRef} />

          <SolutionTreePanel
            gobanRef={gobanRef}
            isVisible={isReviewMode}
          />

          <CommentPanel gobanRef={gobanRef} />
        </>
      )}

      {/* Solving mode: Comment and hint display */}
      {!isReviewMode && (
        <>
          {/* Comment display */}
          {currentComment !== undefined && currentComment !== '' && (
            <div>
              <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-text-primary]">Comment</h3>
              <p className="m-0 text-sm italic leading-relaxed text-[--color-text-secondary]">{currentComment}</p>
            </div>
          )}

          {/* Hint display */}
          {currentHintTier > 0 && hints.length >= currentHintTier && (
            <div>
              <h3 className="m-0 mb-2 text-sm font-semibold text-[--color-text-primary]">Hint {currentHintTier}</h3>
              <p className="m-0 rounded border-l-[3px] border-[--color-accent] bg-[--color-bg-tertiary] px-3 py-2 text-sm leading-relaxed text-[--color-text-secondary]">
                {hints[currentHintTier - 1]}
              </p>
            </div>
          )}

          {/* Placeholder for solving mode */}
          {(currentComment === undefined || currentComment === '') && currentHintTier === 0 && (
            <p className="m-0 text-sm italic leading-relaxed text-[--color-text-secondary]">
              Make your move on the board.{skillLevel !== undefined ? ` Level: ${skillLevel}` : ''}
            </p>
          )}
        </>
      )}

      {/* Tree container for goban's built-in tree visualization */}
      <div
        ref={treeContainerRef}
        className={isReviewMode ? 'block max-h-48 min-h-[100px] overflow-auto scroll-smooth' : 'hidden'}
        data-testid="tree-container"
      />
    </aside>
  );
};

export default PuzzleSidebar;
