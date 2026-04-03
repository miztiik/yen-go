/**
 * Board Section Component
 * @module pages/PuzzleView/BoardSection
 *
 * The main board area including header, board, and mobile controls.
 * Extracted from PuzzleView.tsx for better modularity.
 */

import type { JSX } from 'preact';
import type { Coordinate, BoardSize, Stone, PuzzleTag } from '../../types';
import type { BoardRotation } from '../../components/Board/rotation';
import type { BoardRegion } from '../../hooks/useBoardViewport';
import type { HoverStone } from '../../components/Board/preview';
import type { SolutionNode } from '../../types/puzzle-internal';
import type { PuzzleStatus } from '../../components/ProblemNav/ProblemNav';
import type { TraversalState } from '../../lib/solver/traversal';
import type { HistoryManager } from '../../lib/solver/history';

import { BoardSvg } from '../../components/Board/BoardSvg';
import { QuickControls } from '../../components/QuickControls/QuickControls';
import { ProblemNav } from '../../components/ProblemNav/ProblemNav';
import { SolutionTreeView } from '../../components/SolutionTree/SolutionTreeView';
import { theme } from './utils';

export interface BoardSectionProps {
  puzzleId: string;
  puzzleLevel: string;
  puzzleTags?: readonly PuzzleTag[];
  boardSize: BoardSize;
  stones: Stone[][];
  lastMove: Coordinate | null;
  lastMoveCorrectness?: boolean | undefined;
  hoverStone: HoverStone | null;
  boardRotation: BoardRotation;
  boardRegion?: BoardRegion;
  interactiveBoard: boolean;
  currentPath: string[];
  currentNodeId: string;
  solutionTree: SolutionNode;
  traversalState: TraversalState;
  historyManager: HistoryManager;
  hintsRemaining: number;
  isMobileView: boolean;
  onIntersectionClick: (coord: Coordinate) => void;
  onIntersectionHover: (coord: Coordinate | null) => void;
  onRotate: () => void;
  onUndo: () => void;
  onReset: () => void;
  onHint: () => void;
  onTreeNodeSelect: (treeNodeId: string, node: SolutionNode) => void;
  onBack?: () => void;
  techniqueOfDay?: string;
  // Puzzle navigation
  puzzleSetNavigation?: {
    totalPuzzles: number;
    currentIndex: number;
    statuses: PuzzleStatus[];
    onNavigate: (index: number) => void;
    currentStreak?: number | undefined;
  };
  onPrevPuzzle: () => void;
  onNextPuzzle: () => void;
  // Explore mode
  isExploreMode: boolean;
  onToggleExploreMode: () => void;
}

export function BoardSection({
  puzzleId,
  puzzleLevel: _puzzleLevel,
  puzzleTags: _puzzleTags,
  boardSize,
  stones,
  lastMove,
  lastMoveCorrectness,
  hoverStone,
  boardRotation,
  boardRegion,
  interactiveBoard,
  currentPath: _currentPath,
  currentNodeId,
  solutionTree,
  traversalState: _traversalState,
  historyManager,
  hintsRemaining,
  isMobileView,
  onIntersectionClick,
  onIntersectionHover,
  onRotate,
  onUndo,
  onReset,
  onHint,
  onTreeNodeSelect,
  onBack,
  techniqueOfDay,
  puzzleSetNavigation,
  onPrevPuzzle,
  onNextPuzzle,
  isExploreMode,
  onToggleExploreMode,
}: BoardSectionProps): JSX.Element {
  // Styles
  const mainColumnStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    flex: isMobileView ? '1' : '1 1 0',
    maxWidth: isMobileView ? '100%' : 'min(calc(100vh - 40px), 650px)',
    alignItems: 'center',
    justifyContent: 'flex-start',
    paddingTop: '8px',
  };

  const headerStyle: JSX.CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: isMobileView ? '4px' : '8px',
    flexWrap: 'wrap',
    gap: '6px',
    width: '100%',
    position: 'relative',
  };

  const headerLeftStyle: JSX.CSSProperties = {
    position: 'absolute',
    left: 0,
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  };

  const headerCenterStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '4px',
    minWidth: '150px',
  };

  // Empty header center — puzzle metadata (level/tag) moved to sidebar (T11.3)

  const boardContainerStyle: JSX.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    maxWidth: isMobileView ? '100%' : 'min(calc(100vh - 200px), 600px)',
    aspectRatio: '1 / 1',
    position: 'relative',
    margin: '0 auto',
  };

  const buttonStyle: JSX.CSSProperties = {
    padding: '10px 20px',
    borderRadius: '8px',
    border: `1px solid ${theme.border}`,
    backgroundColor: theme.bgWhite,
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: 600,
    color: theme.text,
    transition: 'all 0.15s ease',
  };

  const mobileBottomPanelStyle: JSX.CSSProperties = {
    display: isMobileView ? 'flex' : 'none',
    flexDirection: 'column',
    gap: '8px',
    paddingTop: '8px',
    borderTop: `1px solid ${theme.border}`,
  };

  return (
    <div style={mainColumnStyle}>
      {/* Header - clean minimal design */}
      <header style={headerStyle}>
        <div style={headerLeftStyle}>
          {onBack && !puzzleSetNavigation && (
            <button
              onClick={onBack}
              style={{
                ...buttonStyle,
                padding: '0',
                minWidth: '44px',
                minHeight: '44px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: 'transparent',
                border: 'none',
              }}
              aria-label="Go back"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M15 6l-6 6 6 6" />
              </svg>
            </button>
          )}
        </div>

        <div style={headerCenterStyle}>
          {/* Level badge + tag moved to sidebar (T11.3) */}
          {techniqueOfDay && (
            <span style={{ 
              fontSize: '12px', 
              color: theme.warning, 
              fontWeight: 500,
            }}>
              🎯 {techniqueOfDay}
            </span>
          )}
        </div>
      </header>

      {/* Board with SVG rendering and viewport support */}
      <div style={boardContainerStyle}>
        <BoardSvg
          key={`${puzzleId}-${boardSize}`}
          boardSize={boardSize}
          stones={stones}
          lastMove={lastMove}
          lastMoveCorrectness={lastMoveCorrectness}
          hoverStone={hoverStone}
          onIntersectionClick={onIntersectionClick}
          onIntersectionHover={onIntersectionHover}
          interactive={interactiveBoard}
          rotation={boardRotation}
          {...(boardRegion ? { region: boardRegion } : {})}
        />
      </div>

      {/* Mobile Bottom Panel */}
      <div style={mobileBottomPanelStyle}>
        {/* QuickControls for mobile */}
        <QuickControls
          onRotate={onRotate}
          onUndo={onUndo}
          onReset={onReset}
          onHint={onHint}
          onToggleExplore={onToggleExploreMode}
          isExploreMode={isExploreMode}
          hasTree={solutionTree.children.length > 0}
          canUndo={historyManager.canUndo()}
          hintsRemaining={hintsRemaining}
          rotationAngle={boardRotation}
          enableKeyboard={true}
        />

        {/* ProblemNav carousel at bottom on mobile */}
        {puzzleSetNavigation && (
          <ProblemNav
            totalProblems={puzzleSetNavigation.totalPuzzles}
            currentIndex={puzzleSetNavigation.currentIndex}
            statuses={puzzleSetNavigation.statuses}
            onNavigate={puzzleSetNavigation.onNavigate}
            onPrev={onPrevPuzzle}
            onNext={onNextPuzzle}
            enableKeyboard={false}
            className="mobile-problem-nav"
          />
        )}

        {/* Explore Mode Tree (shown when explore is active via QuickControls) */}
        {solutionTree.children.length > 0 && isExploreMode && (
          <div style={{ marginTop: '8px' }}>
            <SolutionTreeView
              tree={solutionTree}
              currentNodeId={currentNodeId}
              onNodeSelect={onTreeNodeSelect}
              showCorrectness={true}
              scale={0.2}
              className="mobile-solution-tree"
            />
          </div>
        )}
      </div>
    </div>
  );
}
