/**
 * SolverView -- unified puzzle-solving component with OGS-style layout.
 *
 * Phase 0 fix + Phase 1 refactor:
 * - Uses GobanContainer for board mounting (overflow:hidden, centering)
 * - OGS-native puzzle format via sgfToPuzzle() (initial_state + move_tree)
 * - Viewport-filling layout via flex (OGS pattern)
 * - Coordinate labels via setLabelPosition() API
 * - player_id: 1 (non-zero required for hover stones)
 *
 * Desktop: 2-column layout (board left, sidebar right)
 * Mobile: stacked layout (board top, sidebar below)
 *
 * @module components/Solver/SolverView
 */

import {
  useRef,
  useMemo,
  useState,
  useEffect,
  useLayoutEffect,
  useCallback,
  memo,
} from 'preact/compat';
import type { VNode } from 'preact';
import { useGoban } from '../../hooks/useGoban';
import { usePuzzleState, type PuzzleStatus } from '../../hooks/usePuzzleState';
import { useTransforms } from '../../hooks/useTransforms';
import { useSettings } from '../../hooks/useSettings';
import { useIsDesktop } from '../../hooks/useMediaQuery';
import { GobanContainer } from '../GobanContainer';
import { HintOverlay, cornerPositionToLabel, getMaxLevel } from './HintOverlay';
import { TransformBar } from '../Transforms/TransformBar';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  DoubleChevronLeftIcon,
  DoubleChevronRightIcon,
  UndoIcon,
  ResetIcon,
  SolutionIcon,
  HintIcon,
  CollectionIcon,
  SlidersIcon,
} from '../shared/icons';
import { QualityStars } from '../shared/QualityStars';
import { BottomSheet } from '../shared/BottomSheet';
import {
  UI_HIDE_QUALITY_IN_SOLVER,
  UI_COLLAPSE_TRANSFORM_BAR,
  UI_PINNED_SOLVER_ACTION_BAR,
  UI_KEYBOARD_HELP,
} from '../../services/featureFlags';
import { KBShortcut } from '../shared/KBShortcut';
import { KeyboardHelp } from '../shared/KeyboardHelp';
import { parseYCProperty, getCornerBounds, transformCornerPosition } from '../../lib/auto-viewport';
import {
  extractYenGoProperties,
  computeBounds,
  transformSgfCoordinate,
} from '../../lib/sgf-preprocessor';
import { resolveHintTokens } from '../../lib/hints/token-resolver';
import { sgfToPosition } from '../../utils/coordinates';
import { swapColorText } from '../../lib/colorTextTransform';
import { sanitizeComment } from '../../lib/sanitizeComment';
import { formatRankRange, formatCollectionPill } from '../../lib/levelRanks';

// ============================================================================
// Types
// ============================================================================

/** Auto-advance countdown state passed from PuzzleSetPlayer. */
export interface AutoAdvanceCountdown {
  /** Remaining time in milliseconds. */
  remainingMs: number;
  /** Total delay in milliseconds (for progress calculation). */
  totalMs: number;
  /** Cancel the countdown. */
  onCancel: () => void;
}

export interface SolverViewProps {
  /** Raw SGF puzzle data. */
  sgf: string;
  /** Puzzle difficulty level slug (for tip filtering during loading). */
  level?: string;
  /** Puzzle ID/filename (shown in board tooltip and passed to URL). */
  puzzleId?: string;
  /**
   * Called when puzzle reaches a terminal state (solved or gave up).
   * @param isCorrect true if solved correctly, false if solution was revealed
   */
  onComplete?: (isCorrect: boolean) => void;
  /**
   * Called on each wrong move attempt.
   * Allows parent to track failure metrics without treating as terminal.
   */
  onFail?: () => void;
  /** Called to advance to next puzzle in a set. */
  onNext?: () => void;
  /** Called to go back to previous puzzle in a set. */
  onPrev?: (() => void) | undefined;
  /** Called to skip current puzzle. */
  onSkip?: () => void;
  /** Optional puzzle counter element to render in sidebar. */
  puzzleCounter?: VNode;
  /** Optional ProblemNav element to render at top of sidebar. */
  puzzleNav?: VNode | undefined;
  /** Auto-advance countdown state (present when countdown is active). */
  autoAdvanceCountdown?: AutoAdvanceCountdown;
  /** Optional CSS class. */
  className?: string;
  /** When true, hide sidebar column and show only the board. */
  minimal?: boolean;
}

export type { PuzzleStatus };

// ============================================================================
// Component
// ============================================================================

export function SolverView({
  sgf,
  onComplete,
  onFail,
  onNext,
  onPrev,
  onSkip,
  puzzleCounter,
  puzzleNav,
  puzzleId: _puzzleId,
  autoAdvanceCountdown,
  className = '',
  minimal = false,
}: SolverViewProps): VNode {
  const treeRef = useRef<HTMLDivElement>(null);
  const completeFiredRef = useRef(false);
  const prevStatusRef = useRef<PuzzleStatus>('loading');

  // -- Auto-advance toast (shown briefly when toggling via 'A' key) --
  const [autoAdvanceToast, setAutoAdvanceToast] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // -- View options sheet (mobile) — Phase 5 (F-modern): the dated
  // "VIEW OPTIONS \u25be" disclosure card is replaced by an icon-only sliders
  // button that opens this sheet. Desktop keeps the inline <details>. --
  const [viewOptionsSheetOpen, setViewOptionsSheetOpen] = useState(false);
  // Adaptive: on desktop the panel docks into the sidebar (push-down), on
  // mobile it slides up as a BottomSheet. One state, one trigger.
  const isDesktop = useIsDesktop();

  // -- Tag spoiler reveal (F1) — technique tags ("net", "ladder", etc.) leak
  // the puzzle category before the user attempts. Hide behind a single
  // "Reveal hints" pill until the user explicitly opts in, or auto-reveal once
  // they finish (solved / wrong / review). Resets per puzzle below. --
  const [tagsRevealed, setTagsRevealed] = useState(false);

  // -- SGF Metadata --
  const metadata = useMemo(() => extractYenGoProperties(sgf), [sgf]);

  // Reset spoiler reveal whenever the puzzle changes.
  useEffect(() => {
    setTagsRevealed(false);
  }, [sgf]);

  // -- Board size (from SZ property, default 19) --
  const boardSize = useMemo(() => {
    const szMatch = /SZ\[(\d+)\]/.exec(sgf);
    return szMatch?.[1] ? parseInt(szMatch[1], 10) : 19;
  }, [sgf]);

  // -- Transforms (Spec 133 FR-017, FR-025, FR-026) --
  const {
    settings: transformSettings,
    toggleFlipH,
    toggleFlipV,
    rotateCW,
    rotateCCW,
    toggleSwapColors,
    toggleFlipDiag,
    applyTransforms,
  } = useTransforms();

  // Apply transforms to SGF
  const transformedSgf = useMemo(() => applyTransforms(sgf), [sgf, applyTransforms]);

  // Compute correct move position, transformed through active settings
  const correctMovePosition = useMemo(() => {
    if (!metadata.firstCorrectMove) return null;
    const transformed = transformSgfCoordinate(
      metadata.firstCorrectMove,
      boardSize,
      transformSettings
    );
    return sgfToPosition(transformed);
  }, [metadata.firstCorrectMove, boardSize, transformSettings]);

  // Resolve {!xy} coordinate tokens in hints through active transforms
  const resolvedHints = useMemo(
    () => metadata.hints.map((hint) => resolveHintTokens(hint, boardSize, transformSettings)),
    [metadata.hints, boardSize, transformSettings]
  );

  // Derive corner label from YC property for hint display
  const cornerLabel = useMemo(() => {
    const yc = parseYCProperty(sgf);
    const transformed = transformCornerPosition(yc, transformSettings);
    return cornerPositionToLabel(transformed);
  }, [sgf, transformSettings]);

  // Compute bounds from SGF setup stones + YC corner position
  // (computeBounds uses setup stones only — acceptable for auto-zoom)

  // UI-004: Zoom toggle (cropped ↔ full board)
  const [zoomEnabled, setZoomEnabled] = useState(true);

  const croppedBounds = useMemo(() => {
    // Use computeBounds from setup stones
    const tightBounds = computeBounds(transformedSgf, boardSize, 2);
    if (tightBounds) return tightBounds;
    const rawYc = parseYCProperty(sgf);
    const yc = transformCornerPosition(rawYc, transformSettings);
    return getCornerBounds(yc, boardSize);
  }, [sgf, transformedSgf, transformSettings, boardSize]);

  // Zoom is possible when bounds differ from full board
  const isZoomable =
    croppedBounds != null &&
    (croppedBounds.left > 0 ||
      croppedBounds.top > 0 ||
      croppedBounds.right < boardSize - 1 ||
      croppedBounds.bottom < boardSize - 1);

  // Active bounds: null = full board, croppedBounds = zoomed
  const autoViewportBounds = zoomEnabled && isZoomable ? croppedBounds : undefined;

  // Settings
  const { settings, updateSettings } = useSettings();

  // Toggle auto-advance via keyboard shortcut (A key)
  const handleToggleAutoAdvance = useCallback(() => {
    const newValue = !settings.autoAdvance;
    updateSettings({ autoAdvance: newValue });
    // Cancel running countdown immediately when toggling OFF (don't rely on async effect)
    if (!newValue) {
      autoAdvanceCountdown?.onCancel();
    }
    const msg = newValue ? `Auto-Advance: ON (${settings.autoAdvanceDelay}s)` : 'Auto-Advance: OFF';
    setAutoAdvanceToast(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setAutoAdvanceToast(null), 1500);
  }, [settings.autoAdvance, settings.autoAdvanceDelay, updateSettings, autoAdvanceCountdown]);

  // Cleanup toast timer on unmount
  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  // Map coordinateLabels boolean to label position string
  const labelPosition = settings.coordinateLabels ? ('all' as const) : ('none' as const);

  // Core hooks -- useGoban now creates goban_div programmatically
  const { gobanRef, isReady, boardMessage, gobanDiv } = useGoban(
    transformedSgf,
    treeRef,
    transformSettings,
    autoViewportBounds,
    labelPosition
  );
  const gobanInstance = isReady ? gobanRef.current : null;
  const puzzleState = usePuzzleState(gobanInstance);

  // Transition puzzle state from 'loading' -> 'solving' once goban is ready
  useLayoutEffect(() => {
    if (isReady) {
      puzzleState.onGobanReady();
    }
  }, [isReady, puzzleState.onGobanReady]);

  // UI-003: Bounds-aware coordinate label toggle.
  // Cannot use setLabelPosition('all') because it enables ALL sides,
  // undoing the bounds-aware label config from buildPuzzleConfig.
  // Instead, set individual draw_*_labels flags matching the same logic.
  useEffect(() => {
    const goban = gobanRef.current;
    if (!goban) return;
    const show = labelPosition === 'all';
    const bounds = autoViewportBounds;
    goban.draw_top_labels = show && (!bounds || bounds.top === 0);
    goban.draw_left_labels = show && (!bounds || bounds.left === 0);
    goban.draw_bottom_labels = show && (!bounds || bounds.bottom === boardSize - 1);
    goban.draw_right_labels = show && (!bounds || bounds.right === boardSize - 1);
    goban.setSquareSizeBasedOnDisplayWidth(
      Number((goban as unknown as { display_width: number }).display_width)
    );
    goban.redraw(true);
  }, [labelPosition, isReady, autoViewportBounds, boardSize]);

  // Derived state — only 'complete' counts as solved.
  // 'correct' is a transient status for intermediate correct moves in multi-move puzzles
  // and must NOT lock the UI (disable undo/reset, show banner, etc.).
  const isSolved = puzzleState.state.status === 'complete';
  const isWrong = puzzleState.state.status === 'wrong';
  const isReviewMode = puzzleState.state.status === 'review';
  const [hintsUsedCount, setHintsUsedCount] = useState(0);

  // UI-011: Apply color swap text transformation to hints
  const displayHints = useMemo(() => {
    if (!transformSettings.swapColors) return resolvedHints;
    return resolvedHints.map((h) => swapColorText(h));
  }, [resolvedHints, transformSettings.swapColors]);

  // Dynamic hint count from actual YH hints (not hardcoded 3)
  const maxHintLevel = getMaxLevel(displayHints);
  const hintsRemaining = maxHintLevel - hintsUsedCount;

  // UI-041: Comment display (root C[] and move C[])
  const displayComment = useMemo(() => {
    const raw = puzzleState.state.currentComment;
    if (!raw) return '';
    const sanitized = sanitizeComment(raw);
    return transformSettings.swapColors ? swapColorText(sanitized) : sanitized;
  }, [puzzleState.state.currentComment, transformSettings.swapColors]);

  // UI-037: Rank range display
  const rankRange = useMemo(() => {
    if (!metadata.level) return null;
    return formatRankRange(metadata.level);
  }, [metadata.level]);

  // UI-037: Collection names from YL property (with chapter context)
  const collectionNames = useMemo(() => {
    const memberships = metadata.collectionMemberships;
    if (memberships && memberships.length > 0) {
      return memberships.map((m) => formatCollectionPill(m.slug, m.chapter, m.position));
    }
    return [];
  }, [metadata.collectionMemberships]);

  // UI-029 + UI-042: Combined colored circles — hint marker + move tree visual feedback
  // Unified into a single effect because setColoredCircles replaces the full array.
  //
  // Hint circle: green ring on the correct move position (when hints exhausted, solving only)
  // Move feedback: OGS-style filled green (correct) / red (wrong) circles on all stones
  // in the path from root to current move. Updates on each tree navigation via goban 'update' event.
  useEffect(() => {
    const goban = gobanRef.current;
    if (!goban) return;

    // ColoredCircle shape accepted by goban's setColoredCircles API
    type CircleEntry = {
      move: { x: number; y: number };
      color: string;
      border_color?: string;
      border_width?: number;
    };

    // MoveTree node shape (subset of goban's MoveTree class)
    type MoveNode = {
      x: number;
      y: number;
      correct_answer?: boolean;
      wrong_answer?: boolean;
      parent: MoveNode | null;
    };

    const computeAndApply = (): void => {
      const circles: CircleEntry[] = [];

      // 1. Hint circle: green ring on correct move when hints exhausted (solving only)
      if (hintsUsedCount >= maxHintLevel && !isSolved && correctMovePosition) {
        circles.push({
          move: { x: correctMovePosition.x, y: correctMovePosition.y },
          color: 'rgba(34, 139, 34, 0.55)',
          border_color: '#1B6D2D',
          border_width: 0.15,
        });
      }

      // 2. Move tree path feedback: walk root → cur_move, mark each node
      try {
        const engine = (
          goban as unknown as {
            engine?: { cur_move?: MoveNode };
          }
        ).engine;
        const curMove = engine?.cur_move;
        if (curMove) {
          // Collect path from root to current (excluding root which has no stone)
          const path: MoveNode[] = [];
          let node: MoveNode | null = curMove;
          while (node?.parent) {
            path.unshift(node);
            node = node.parent;
          }

          for (const n of path) {
            // Skip pass moves (x === -1 in goban convention)
            if (n.x < 0 || n.y < 0) continue;

            if (n.correct_answer) {
              circles.push({
                move: { x: n.x, y: n.y },
                color: 'rgba(34, 197, 94, 0.6)', // green-500 filled
              });
            } else if (n.wrong_answer) {
              circles.push({
                move: { x: n.x, y: n.y },
                color: 'rgba(239, 68, 68, 0.6)', // red-500 filled
              });
            }
          }

          // Off-tree wrong move: node has no flag but puzzle state is 'wrong'
          if (
            isWrong &&
            curMove.x >= 0 &&
            curMove.y >= 0 &&
            !curMove.correct_answer &&
            !curMove.wrong_answer
          ) {
            circles.push({
              move: { x: curMove.x, y: curMove.y },
              color: 'rgba(239, 68, 68, 0.6)',
            });
          }
        }
      } catch {
        /* engine/tree access failed — skip move circles */
      }

      // Apply combined circles to the board
      try {
        const gobanWithCircles = goban as unknown as {
          setColoredCircles?(circles: CircleEntry[], dont_draw?: boolean): void;
        };
        if (typeof gobanWithCircles.setColoredCircles === 'function') {
          gobanWithCircles.setColoredCircles(circles);
        }
      } catch {
        /* setColoredCircles not available in this goban version */
      }
    };

    // Initial computation
    computeAndApply();

    // Re-compute on every tree navigation (review stepping, auto-play opponent responses)
    const onUpdate = (): void => {
      computeAndApply();
    };
    (
      goban as unknown as {
        on(event: string, cb: () => void): void;
      }
    ).on('update', onUpdate);

    return () => {
      (
        goban as unknown as {
          off(event: string, cb: () => void): void;
        }
      ).off('update', onUpdate);
      // Clear all circles on cleanup
      try {
        const gobanWithCircles = goban as unknown as {
          setColoredCircles?(circles?: unknown[], dont_draw?: boolean): void;
        };
        if (typeof gobanWithCircles.setColoredCircles === 'function') {
          gobanWithCircles.setColoredCircles([]);
        }
      } catch {
        /* noop */
      }
    };
  }, [hintsUsedCount, correctMovePosition, isSolved, isWrong, isReady]);

  // Reset completion tracking when SGF changes
  useEffect(() => {
    completeFiredRef.current = false;
    prevStatusRef.current = 'loading';
    setHintsUsedCount(0);
    setZoomEnabled(true); // Reset zoom to cropped view for new puzzle
  }, [sgf]);

  // -- Keyboard shortcut callbacks (UI-031, UI-045) --
  const isSolving = puzzleState.state.status === 'solving' || puzzleState.state.status === 'wrong';
  const canUndo = isSolving && puzzleState.state.moveCount > 0;

  const handleKBUndo = useCallback(() => {
    if (canUndo) puzzleState.undo();
  }, [canUndo, puzzleState]);

  const handleKBReset = useCallback(() => {
    if (isSolving && puzzleState.state.moveCount > 0) puzzleState.reset();
  }, [isSolving, puzzleState]);

  const handleKBShowPrev = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (goban && typeof goban.showPrevious === 'function') {
        (goban.showPrevious as () => void)();
        // Re-disable stone placement — goban re-enables it for puzzle mode
        if (typeof goban.disableStonePlacement === 'function') {
          (goban.disableStonePlacement as () => void)();
        }
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  const handleKBShowNext = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (goban && typeof goban.showNext === 'function') {
        (goban.showNext as () => void)();
        // Re-disable stone placement — goban re-enables it for puzzle mode
        if (typeof goban.disableStonePlacement === 'function') {
          (goban.disableStonePlacement as () => void)();
        }
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  const handleKBPrevSibling = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (goban && typeof goban.prevSibling === 'function') {
        (goban.prevSibling as () => void)();
        // Re-disable stone placement for safety
        if (typeof goban.disableStonePlacement === 'function') {
          (goban.disableStonePlacement as () => void)();
        }
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  const handleKBNextSibling = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (goban && typeof goban.nextSibling === 'function') {
        (goban.nextSibling as () => void)();
        // Re-disable stone placement for safety
        if (typeof goban.disableStonePlacement === 'function') {
          (goban.disableStonePlacement as () => void)();
        }
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  // Context-aware Left Arrow: undo during solving, showPrevious during review
  const handleKBLeft = useCallback(() => {
    if (isSolving && canUndo) {
      puzzleState.undo();
    } else if (isReviewMode) {
      handleKBShowPrev();
    }
  }, [isSolving, canUndo, isReviewMode, puzzleState, handleKBShowPrev]);

  // Context-aware Right Arrow: showNext during review only
  const handleKBRight = useCallback(() => {
    if (isReviewMode) {
      handleKBShowNext();
    }
  }, [isReviewMode, handleKBShowNext]);

  // Solution tree navigation: go to first move
  const handleTreeFirst = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (goban && typeof goban.showFirst === 'function') {
        (goban.showFirst as () => void)();
        if (typeof goban.disableStonePlacement === 'function') {
          (goban.disableStonePlacement as () => void)();
        }
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  // Solution tree navigation: go to last move (walk trunk to end)
  const handleTreeLast = useCallback(() => {
    try {
      const goban = gobanRef.current as unknown as Record<string, unknown> | null;
      if (!goban) return;
      // Walk trunk line to the end
      if (typeof goban.showFirst === 'function') {
        (goban.showFirst as () => void)();
      }
      const engine = (
        goban as unknown as {
          engine?: {
            move_tree?: Record<string, unknown>;
            cur_move?: unknown;
            jumpTo?: (node: unknown) => void;
          };
        }
      ).engine;
      if (engine?.move_tree) {
        let node = engine.move_tree;
        while (node.trunk_next) {
          node = node.trunk_next as Record<string, unknown>;
        }
        if (typeof engine.jumpTo === 'function') {
          engine.jumpTo(node);
          // Trigger a redraw + update after jumping
          if (
            typeof (goban as unknown as { redraw?: (full: boolean) => void }).redraw === 'function'
          ) {
            (goban as unknown as { redraw: (full: boolean) => void }).redraw(true);
          }
          if (typeof (goban as unknown as { emit?: (event: string) => void }).emit === 'function') {
            (goban as unknown as { emit: (event: string) => void }).emit('update');
          }
        }
      }
      if (typeof goban.disableStonePlacement === 'function') {
        (goban.disableStonePlacement as () => void)();
      }
    } catch {
      /* noop */
    }
  }, [gobanRef]);

  // Auto-scroll to active node in solution tree (US12, T174)
  useEffect(() => {
    const container = treeRef.current;
    if (!container) return;
    const observer = new MutationObserver(() => {
      const active = container.querySelector('.active, [data-active="true"]');
      if (active) {
        active.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
    observer.observe(container, { childList: true, subtree: true, attributes: true });
    return () => observer.disconnect();
  }, []);

  // Auto-fire onComplete(true) when puzzle is solved correctly
  useEffect(() => {
    const currentStatus = puzzleState.state.status;
    const prevStatus = prevStatusRef.current;
    prevStatusRef.current = currentStatus;
    if (currentStatus === 'complete' && prevStatus !== 'complete' && !completeFiredRef.current) {
      completeFiredRef.current = true;
      onComplete?.(true);
    }
    if (currentStatus === 'wrong' && prevStatus !== 'wrong') {
      onFail?.();
    }
  }, [puzzleState.state.status, onComplete, onFail]);

  // ========================================================================
  // Render -- OGS-style 2-column viewport-filling puzzle layout
  // ========================================================================

  return (
    <div
      className={`solver-layout ${UI_PINNED_SOLVER_ACTION_BAR ? 'solver-action-pinned' : ''} ${className}`}
      data-component="solver-view"
      data-status={puzzleState.state.status}
    >
      {/* -- Center Column: Board (GobanContainer) -- */}
      <div className="solver-board-col">
        <GobanContainer gobanDiv={gobanDiv} goban={gobanInstance} />
      </div>

      {/* -- Right Column: Sidebar (hidden in minimal mode) -- */}
      {!minimal && (
        <div className="solver-sidebar-col">
          {/* Phase 5 (F3): drop the floating-card chrome (rounded corners,
              shadow, large padding, border) on mobile — it's a desktop-widget
              treatment that fights the board on small screens. Lichess and
              Tsumego Pro use a flush borderless strip below the board. Desktop
              keeps the full card. */}
          <div className="bg-[var(--color-card-bg)] p-3 flex flex-col gap-3 min-h-0 overflow-y-auto md:rounded-3xl md:shadow-[var(--shadow-lg)] md:p-6 md:gap-5 md:border md:border-[var(--color-panel-border)]">
            {/* Section 0: ProblemNav or Puzzle Counter with Chevron Navigation */}
            {puzzleNav && (
              <div className="py-1.5" data-testid="puzzle-nav-slot">
                {puzzleNav}
              </div>
            )}
            {!puzzleNav && puzzleCounter && (
              <div
                className="py-1.5 flex items-center justify-between gap-2 text-sm"
                data-testid="puzzle-counter"
              >
                {onPrev && (
                  <button
                    type="button"
                    onClick={onPrev}
                    className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer"
                    aria-label="Previous puzzle"
                    title="Previous puzzle"
                  >
                    <ChevronLeftIcon size={16} />
                  </button>
                )}
                {!onPrev && <div className="w-7" />}
                {puzzleCounter}
                {onNext && (
                  <button
                    type="button"
                    onClick={onNext}
                    className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer"
                    aria-label="Next puzzle"
                    title="Next puzzle"
                  >
                    <ChevronRightIcon size={16} />
                  </button>
                )}
                {onSkip && !onNext && (
                  <button
                    type="button"
                    onClick={onSkip}
                    className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer"
                    aria-label="Next puzzle"
                    title="Next puzzle"
                  >
                    <ChevronRightIcon size={16} />
                  </button>
                )}
                {!onNext && !onSkip && <div className="w-7" />}
              </div>
            )}

            {/* Section 0.5: Metadata (level badge with rank range + tags + collections) */}
            {(metadata.level ||
              (metadata.tags && metadata.tags.length > 0) ||
              collectionNames.length > 0) && (
              <div className="py-1.5 flex flex-wrap items-center justify-center gap-1.5">
                {metadata.level && (
                  <span
                    className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold capitalize border"
                    data-level={metadata.level}
                    style={{
                      backgroundColor: `var(--color-level-${metadata.level}-bg)`,
                      color: `var(--color-level-${metadata.level}-text)`,
                      borderColor: `var(--color-level-${metadata.level}-border)`,
                    }}
                  >
                    {rankRange ?? metadata.level.replace(/-/g, ' ')}
                  </span>
                )}
                {metadata.tags &&
                  metadata.tags.length > 0 &&
                  (tagsRevealed || isSolved || isWrong || isReviewMode ? (
                    metadata.tags.map((tag: string) => (
                      <span
                        key={tag}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-bg-secondary)] text-[var(--color-text-primary)] border border-[var(--color-neutral-200)]"
                        data-testid="tag-chip"
                      >
                        {tag.replace(/-/g, ' ')}
                      </span>
                    ))
                  ) : (
                    <button
                      type="button"
                      onClick={() => setTagsRevealed(true)}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-bg-secondary)]/50 text-[var(--color-text-secondary)] border border-dashed border-[var(--color-neutral-300)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] transition-colors cursor-pointer"
                      aria-label={`Reveal ${metadata.tags.length} technique hint tag${metadata.tags.length === 1 ? '' : 's'} (spoiler)`}
                      title="Tags reveal the technique — click to show"
                      data-testid="tags-reveal-button"
                    >
                      Reveal hints · {metadata.tags.length}
                    </button>
                  ))}
                {collectionNames.map((name: string, i: number) => (
                  <span
                    key={`col-${i}`}
                    title={name}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-[var(--color-accent)]/10 text-[var(--color-text-primary)] border border-[var(--color-neutral-300)]"
                  >
                    <CollectionIcon size={16} />
                    {name}
                  </span>
                ))}
                {!UI_HIDE_QUALITY_IN_SOLVER && metadata.quality > 0 && (
                  <QualityStars quality={metadata.quality} size={12} />
                )}
                {/* View Options trigger — single adaptive control across breakpoints.
                 * Anchored to the right of the metadata/tag row; opens a sheet
                 * (bottom on mobile, centered popover on desktop). */}
                {UI_COLLAPSE_TRANSFORM_BAR && (
                  <button
                    type="button"
                    onClick={() => setViewOptionsSheetOpen((v) => !v)}
                    className="ml-auto inline-flex items-center justify-center w-8 h-8 rounded-full text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-accent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] transition-colors data-[active=true]:bg-[var(--color-accent)]/10 data-[active=true]:text-[var(--color-accent)]"
                    aria-label="View options (board flip, rotate, coordinates, zoom)"
                    aria-expanded={viewOptionsSheetOpen}
                    title="View options"
                    data-testid="view-options-trigger"
                    data-active={viewOptionsSheetOpen}
                  >
                    <SlidersIcon size={18} />
                  </button>
                )}
              </div>
            )}

            {/* Section 1: Board Transforms — visible inline only when collapsible flag is OFF.
             * When UI_COLLAPSE_TRANSFORM_BAR is ON, the same controls render at the bottom
             * of the sidebar inside a collapsible "View options" panel. */}
            {!UI_COLLAPSE_TRANSFORM_BAR && (
              <div className="py-1.5" data-section="transforms">
                <TransformBar
                  settings={transformSettings}
                  onToggleFlipH={toggleFlipH}
                  onToggleFlipV={toggleFlipV}
                  onToggleFlipDiag={toggleFlipDiag}
                  onRotateCW={rotateCW}
                  onRotateCCW={rotateCCW}
                  onToggleSwapColors={toggleSwapColors}
                  coordinateLabels={settings.coordinateLabels}
                  onToggleCoordinates={() =>
                    updateSettings({ coordinateLabels: !settings.coordinateLabels })
                  }
                  disabled={isReviewMode}
                  zoomEnabled={zoomEnabled}
                  isZoomable={isZoomable}
                  onToggleZoom={() => setZoomEnabled((z) => !z)}
                />
              </div>
            )}

            {/* Section 2: Hint display + comments — no fixed reserve. Only
             * takes space when hints or comments are present so we don't leave
             * a 60px empty band on solved/clean puzzles. */}
            <div className="hint-section">
              {!isSolved && (
                <HintOverlay
                  hints={displayHints}
                  correctMove={correctMovePosition}
                  boardSize={boardSize}
                  currentLevel={hintsUsedCount}
                  cornerLabel={cornerLabel}
                />
              )}
              {/* UI-041: Comment display (root C[] or move C[]) */}
              {displayComment && (
                <div
                  className="mt-2 text-[0.8125rem] text-[var(--color-text-muted)] overflow-y-auto rounded-[var(--radius-sm)] bg-[var(--color-bg-secondary)]/50 px-2.5 py-1.5"
                  style={{ maxHeight: '80px', wordBreak: 'break-word' }}
                  data-testid="puzzle-comment"
                  dangerouslySetInnerHTML={{ __html: displayComment }}
                />
              )}
            </div>

            {/* Section 3: Always-visible action toolbar */}
            <div className="py-1.5" data-section="actions">
              <div
                className="flex items-center justify-center gap-3 flex-wrap"
                data-testid="action-bar"
              >
                {/* Group 1: Previous navigation */}
                <button
                  type="button"
                  onClick={() => onPrev?.()}
                  className="action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={!onPrev}
                  aria-label="Previous puzzle"
                >
                  <ChevronLeftIcon size={24} />
                </button>

                <div className="action-separator" aria-hidden="true" />

                {/* Group 2: Undo / Reset */}
                <button
                  type="button"
                  onClick={() => puzzleState.undo()}
                  className="action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={puzzleState.state.moveCount === 0 || isSolved || isReviewMode}
                  aria-label="Undo (Z)"
                >
                  <UndoIcon size={24} />
                </button>

                <div className="action-separator" aria-hidden="true" />

                <button
                  type="button"
                  onClick={() => puzzleState.reset()}
                  className="action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 disabled:opacity-40 disabled:cursor-not-allowed"
                  disabled={puzzleState.state.moveCount === 0 || isSolved || isReviewMode}
                  aria-label="Reset (X)"
                >
                  <ResetIcon size={24} />
                </button>

                <div className="action-separator" aria-hidden="true" />

                {/* Group 3: Hint + Reveal */}
                {maxHintLevel > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setHintsUsedCount((c) => c + 1);
                      puzzleState.requestHint(hintsUsedCount);
                    }}
                    className="action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 disabled:opacity-40 disabled:cursor-not-allowed relative"
                    disabled={isSolved || isReviewMode || hintsRemaining <= 0}
                    aria-label={`Hint (${!isSolved ? hintsRemaining : 0} remaining)`}
                  >
                    <HintIcon size={28} count={!isSolved ? hintsRemaining : 0} />
                  </button>
                )}
                {(isSolved || isWrong) && (
                  <button
                    type="button"
                    onClick={() => puzzleState.revealSolution()}
                    className={`action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 ${
                      isReviewMode
                        ? 'bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] shadow-[var(--shadow-sm)]'
                        : 'bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)]'
                    }`}
                    aria-label={isReviewMode ? 'Reviewing solution' : 'Review solution'}
                  >
                    <SolutionIcon size={24} />
                  </button>
                )}

                <div className="action-separator" aria-hidden="true" />

                {/* Group 4: Next navigation (context-aware: ghost during solving, prominent CTA after solve/fail) */}
                {onNext && !autoAdvanceCountdown && (
                  <button
                    type="button"
                    onClick={onNext}
                    className={`action-tooltip inline-flex items-center justify-center rounded-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 ${
                      isSolved || isWrong
                        ? 'w-[3.75rem] h-[3.75rem] bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)] shadow-[0_2px_8px_rgba(0,0,0,0.15)] animate-[pulse-cta_2s_ease-in-out_infinite] transition-all duration-200'
                        : 'w-[3.125rem] h-[3.125rem] bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150'
                    }`}
                    aria-label="Next puzzle"
                    data-testid="next-button"
                  >
                    <ChevronRightIcon size={isSolved || isWrong ? 28 : 24} />
                  </button>
                )}
                {/* Auto-advance countdown ring — replaces Next button during countdown */}
                {autoAdvanceCountdown && onNext && (
                  <button
                    type="button"
                    onClick={autoAdvanceCountdown.onCancel}
                    className="relative inline-flex items-center justify-center w-[3.75rem] h-[3.75rem] rounded-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1"
                    aria-label={`Auto-advancing in ${Math.ceil(autoAdvanceCountdown.remainingMs / 1000)} seconds. Click to cancel.`}
                    data-testid="auto-advance-countdown"
                    role="timer"
                  >
                    <svg
                      width="60"
                      height="60"
                      viewBox="0 0 60 60"
                      className="absolute inset-0"
                      aria-hidden="true"
                    >
                      <circle
                        cx="30"
                        cy="30"
                        r="26"
                        fill="none"
                        stroke="var(--color-bg-secondary)"
                        strokeWidth="3"
                      />
                      <circle
                        cx="30"
                        cy="30"
                        r="26"
                        fill="none"
                        stroke="var(--color-accent)"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeDasharray={`${2 * Math.PI * 26}`}
                        strokeDashoffset={`${2 * Math.PI * 26 * (1 - (autoAdvanceCountdown.totalMs > 0 ? autoAdvanceCountdown.remainingMs / autoAdvanceCountdown.totalMs : 0))}`}
                        style={{
                          transform: 'rotate(-90deg)',
                          transformOrigin: 'center',
                          transition: 'stroke-dashoffset 100ms linear',
                        }}
                      />
                    </svg>
                    <span className="relative z-10 text-base font-bold text-[var(--color-accent)]">
                      {Math.ceil(autoAdvanceCountdown.remainingMs / 1000) || 1}
                    </span>
                  </button>
                )}
                {onSkip && !onNext && !isSolved && (
                  <button
                    type="button"
                    onClick={onSkip}
                    className="action-tooltip inline-flex items-center justify-center w-[3.125rem] h-[3.125rem] rounded-full bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1"
                    aria-label="Skip to next puzzle"
                  >
                    <ChevronRightIcon size={24} />
                  </button>
                )}
              </div>
            </div>

            {/* Section 3.5: Board message (self-capture, ko, etc.) */}
            {boardMessage && (
              <div
                className="py-1.5 flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] text-[var(--color-warning)] text-sm border border-[var(--color-warning-border)]"
                role="alert"
                data-testid="board-message"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="shrink-0"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{boardMessage.text}</span>
              </div>
            )}

            {/* Section 4: Answer feedback */}
            {isWrong && (
              <div
                className="py-1.5 flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] text-[var(--color-error)] text-sm font-medium border border-[var(--color-error-border)]"
                role="status"
                data-testid="answer-banner"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="shrink-0"
                >
                  <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.999L13.732 4.001c-.77-1.333-2.694-1.333-3.464 0L3.34 16.001C2.57 17.334 3.532 19 5.072 19z" />
                </svg>
                <span>Incorrect -- try again</span>
              </div>
            )}
            {isSolved && (
              <div
                className="py-1.5 flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] bg-[var(--color-success-bg)] text-[var(--color-success)] text-sm font-medium border border-[var(--color-success-border)]"
                role="status"
                data-testid="answer-banner"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="shrink-0"
                >
                  <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{puzzleState.state.wrongAttempts === 0 ? 'Correct!' : 'Solved!'}</span>
              </div>
            )}

            {/* Section 5: Solution tree with integrated navigation controls */}
            {/* Always in DOM for goban's move_tree_container; CSS-toggled visibility */}
            <div
              className={
                isReviewMode || puzzleState.state.solutionRevealed
                  ? 'py-1.5 mt-1 rounded-[var(--radius-lg)] bg-[var(--color-bg-elevated)] border border-[var(--color-neutral-200)] flex flex-col'
                  : 'hidden'
              }
              data-testid="solution-tree-wrapper"
            >
              {/* Tree navigation controls — inside the solution tree box */}
              <div
                className="flex items-center justify-center gap-1 px-3 pt-2 pb-1"
                data-testid="tree-nav-controls"
              >
                <button
                  type="button"
                  onClick={handleTreeFirst}
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Go to first move"
                  title="First move"
                >
                  <DoubleChevronLeftIcon size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleKBShowPrev}
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Previous move"
                  title="Previous move"
                >
                  <ChevronLeftIcon size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleKBShowNext}
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Next move"
                  title="Next move"
                >
                  <ChevronRightIcon size={14} />
                </button>
                <button
                  type="button"
                  onClick={handleTreeLast}
                  className="inline-flex items-center justify-center w-7 h-7 rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Go to last move"
                  title="Last move"
                >
                  <DoubleChevronRightIcon size={14} />
                </button>
              </div>
              {/* Solution tree rendered by goban library */}
              <div
                ref={treeRef}
                className="overflow-auto p-3 scrollbar-thin"
                style={{ maxHeight: '200px', minHeight: '80px' }}
                data-testid="solution-tree-container"
              />
            </div>

            {/* Section 6: View options — trigger lives inline with the metadata
             * row above (right-anchored). On desktop the panel docks here
             * (push-down inside the sidebar) so it never blocks the board.
             * On mobile it opens as a BottomSheet (rendered below). */}
            {UI_COLLAPSE_TRANSFORM_BAR && isDesktop && viewOptionsSheetOpen && (
              <div
                className="py-2 px-3 rounded-[var(--radius-md)] border border-[var(--color-panel-border)] bg-[var(--color-bg-elevated)]/60"
                data-testid="view-options-inline"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider">
                    View options
                  </span>
                  <button
                    type="button"
                    onClick={() => setViewOptionsSheetOpen(false)}
                    className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[var(--color-text-muted)] hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] transition-colors"
                    aria-label="Close view options"
                  >
                    ✕
                  </button>
                </div>
                <TransformBar
                  settings={transformSettings}
                  onToggleFlipH={toggleFlipH}
                  onToggleFlipV={toggleFlipV}
                  onToggleFlipDiag={toggleFlipDiag}
                  onRotateCW={rotateCW}
                  onRotateCCW={rotateCCW}
                  onToggleSwapColors={toggleSwapColors}
                  coordinateLabels={settings.coordinateLabels}
                  onToggleCoordinates={() =>
                    updateSettings({ coordinateLabels: !settings.coordinateLabels })
                  }
                  disabled={isReviewMode}
                  zoomEnabled={zoomEnabled}
                  isZoomable={isZoomable}
                  onToggleZoom={() => setZoomEnabled((z) => !z)}
                />
              </div>
            )}
          </div>
          {/* end solver-sidebar-surface */}
        </div>
      )}

      {/* Auto-advance toggle toast */}
      {autoAdvanceToast && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 rounded-full bg-[var(--color-bg-elevated)] px-4 py-2 text-sm font-medium text-[var(--color-text-primary)] shadow-lg border border-[var(--color-border)] animate-fade-in"
          role="status"
          aria-live="polite"
          data-testid="auto-advance-toast"
        >
          {autoAdvanceToast}
        </div>
      )}

      {/* Phase 5: View options BottomSheet — mobile only.
          Desktop docks the same content inline in the sidebar (above). */}
      {UI_COLLAPSE_TRANSFORM_BAR && !isDesktop && (
        <BottomSheet
          isOpen={viewOptionsSheetOpen}
          onClose={() => setViewOptionsSheetOpen(false)}
          title="View options"
          testId="view-options-sheet"
        >
          <div className="px-4 py-3">
            <TransformBar
              settings={transformSettings}
              onToggleFlipH={toggleFlipH}
              onToggleFlipV={toggleFlipV}
              onToggleFlipDiag={toggleFlipDiag}
              onRotateCW={rotateCW}
              onRotateCCW={rotateCCW}
              onToggleSwapColors={toggleSwapColors}
              coordinateLabels={settings.coordinateLabels}
              onToggleCoordinates={() =>
                updateSettings({ coordinateLabels: !settings.coordinateLabels })
              }
              disabled={isReviewMode}
              zoomEnabled={zoomEnabled}
              isZoomable={isZoomable}
              onToggleZoom={() => setZoomEnabled((z) => !z)}
            />
          </div>
        </BottomSheet>
      )}

      {/* Keyboard shortcuts (UI-031, UI-045) — rendered as invisible components */}
      {/* Escape: cancel auto-advance countdown takes priority; otherwise reset puzzle */}
      <KBShortcut
        shortcut="Escape"
        action={handleKBReset}
        enabled={isSolving && !autoAdvanceCountdown}
      />
      {autoAdvanceCountdown && (
        <KBShortcut shortcut="Escape" action={autoAdvanceCountdown.onCancel} enabled={true} />
      )}
      <KBShortcut shortcut="z" action={handleKBUndo} enabled={canUndo} />
      <KBShortcut
        shortcut="x"
        action={handleKBReset}
        enabled={isSolving && puzzleState.state.moveCount > 0}
      />
      <KBShortcut
        shortcut="ArrowLeft"
        action={handleKBLeft}
        enabled={isSolving || isReviewMode}
        capture
        stopImmediate
      />
      <KBShortcut
        shortcut="ArrowRight"
        action={handleKBRight}
        enabled={isReviewMode}
        capture
        stopImmediate
      />
      <KBShortcut shortcut="ArrowUp" action={handleKBPrevSibling} enabled={isReviewMode} />
      <KBShortcut shortcut="ArrowDown" action={handleKBNextSibling} enabled={isReviewMode} />
      <KBShortcut shortcut="a" action={handleToggleAutoAdvance} enabled={true} />

      {/* Phase 3: Keyboard shortcut help overlay (`?` key) — UI_KEYBOARD_HELP */}
      {UI_KEYBOARD_HELP && (
        <KeyboardHelp
          shortcuts={[
            { keys: 'Esc', description: 'Reset puzzle (or cancel auto-advance)' },
            { keys: 'z', description: 'Undo last move' },
            { keys: 'x', description: 'Reset puzzle' },
            { keys: '←', description: 'Previous puzzle / move (in review)' },
            { keys: '→', description: 'Next move (in review)' },
            { keys: '↑ / ↓', description: 'Cycle sibling variations (review mode)' },
            { keys: 'a', description: 'Toggle auto-advance' },
            { keys: '?', description: 'Show this help' },
          ]}
        />
      )}
    </div>
  );
}

export default memo(SolverView);
