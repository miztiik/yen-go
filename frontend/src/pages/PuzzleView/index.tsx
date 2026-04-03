/**
 * PuzzleView Page - Main puzzle solving interface
 * @module pages/PuzzleView
 *
 * Covers: US1 (Solve a Single Puzzle), FR-001 to FR-017
 * Enhanced with: SolutionTree (T042-T043), ProblemNav (T048-T049),
 * QuickControls (T054-T056), Branding (T073), Responsive (T065-T068)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: Page composes components
 * - IV. Local-First: State in memory, can save to localStorage
 * - V. No Browser AI: Uses precomputed solution tree
 * - Single source of truth: Uses config/puzzle-levels.json via Vite JSON import
 *
 * This module has been split for maintainability:
 * - useGameState.ts: All state management and game logic
 * - BoardSection.tsx: Board area and mobile controls
 * - SidebarSection.tsx: Side panel with controls and info
 * - types.ts: Shared type definitions
 * - utils.ts: Helper functions
 */

import type { JSX } from 'preact';
import { useEffect } from 'preact/hooks';

import type { PuzzleViewProps, SkillLevel } from './types';
import { useGameState } from './useGameState';
import { BoardSection } from './BoardSection';
import { SidebarSection } from './SidebarSection';
import { theme } from './utils';

// Re-export types for backward compatibility
export type { PuzzleViewProps, SkillLevel };

/**
 * PuzzleView - Main puzzle solving page
 */
export function PuzzleView({
  puzzle,
  puzzleId,
  skillLevel = 'novice',
  onComplete,
  onNextPuzzle,
  onPrevPuzzle,
  onBack,
  initialState: _initialState,
  puzzleSetNavigation,
  techniqueOfDay,
  showTimer: _showTimer = false,
  autoAdvance = true,
  autoAdvanceDelay = 1500,
  boardRegion,
}: PuzzleViewProps): JSX.Element {
  // Build game state props, only including defined callbacks
  const gameStateProps = {
    puzzle,
    puzzleId,
    skillLevel,
    autoAdvance,
    autoAdvanceDelay,
    ...(onComplete !== undefined && { onComplete }),
    ...(onNextPuzzle !== undefined && { onNextPuzzle }),
    ...(onPrevPuzzle !== undefined && { onPrevPuzzle }),
  };

  // Use the game state hook
  const gameState = useGameState(gameStateProps);

  // Handle browser back button
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (gameState.traversalState.history.length > 0 && !gameState.traversalState.complete) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    const handlePopState = () => {
      if (gameState.traversalState.history.length > 0 && !gameState.traversalState.complete) {
        const stateJson = JSON.stringify({
          puzzleId,
          moves: gameState.traversalState.history,
          wrongAttempts: gameState.traversalState.wrongAttempts,
        });
        sessionStorage.setItem('puzzle-state', stateJson);
      }
      onBack?.();
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    window.addEventListener('popstate', handlePopState);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      window.removeEventListener('popstate', handlePopState);
    };
  }, [puzzleId, gameState.traversalState, onBack]);

  // Container styles
  const containerStyle: JSX.CSSProperties = {
    display: 'flex',
    flexDirection: gameState.isMobileView ? 'column' : 'row',
    height: '100vh',
    maxWidth: gameState.isMobileView ? '100%' : '1200px',
    margin: '0 auto',
    padding: gameState.isMobileView ? '4px' : '8px',
    boxSizing: 'border-box',
    gap: gameState.isMobileView ? '4px' : '16px',
    backgroundColor: theme.bgLight,
    fontFamily: '"Nunito", system-ui, -apple-system, sans-serif',
  };

  return (
    <div className="puzzle-view" style={containerStyle}>
      {/* Main Column: Header, Board, Mobile Controls */}
      <BoardSection
        puzzleId={puzzleId}
        puzzleLevel={puzzle.level}
        {...(puzzle.tags !== undefined && { puzzleTags: puzzle.tags })}
        boardSize={gameState.boardSize}
        stones={gameState.stones}
        lastMove={gameState.lastMove}
        lastMoveCorrectness={gameState.lastMoveCorrectness ?? gameState.currentNodeInfo?.isCorrect}
        hoverStone={gameState.hoverStone}
        boardRotation={gameState.boardRotation}
        {...((boardRegion ?? gameState.boardRegion) !== undefined && { boardRegion: boardRegion ?? gameState.boardRegion })}
        interactiveBoard={gameState.isPlayerTurn && !gameState.showSuccess && !gameState.showFailure}
        currentPath={gameState.currentPath}
        currentNodeId={gameState.currentNodeId}
        solutionTree={gameState.solutionTree}
        traversalState={gameState.traversalState}
        historyManager={gameState.historyManager}
        hintsRemaining={gameState.hintsRemaining}
        isMobileView={gameState.isMobileView}
        onIntersectionClick={gameState.handleIntersectionClick}
        onIntersectionHover={gameState.handleIntersectionHover}
        onRotate={gameState.handleRotate}
        onUndo={gameState.handleUndo}
        onReset={gameState.handleRetry}
        onHint={gameState.handleHint}
        onTreeNodeSelect={gameState.handleTreeNodeSelect}
        {...(onBack !== undefined && { onBack })}
        {...(techniqueOfDay !== undefined && { techniqueOfDay })}
        {...(puzzleSetNavigation !== undefined && { puzzleSetNavigation })}
        onPrevPuzzle={gameState.handlePrevPuzzle}
        onNextPuzzle={gameState.handleNextPuzzle}
        isExploreMode={gameState.isExploreMode}
        onToggleExploreMode={gameState.toggleExploreMode}
      />

      {/* Side Column: Panel with all controls (desktop) */}
      <SidebarSection
        puzzleLevel={puzzle.level}
        {...(puzzle.tags !== undefined && { puzzleTags: puzzle.tags })}
        currentColor={gameState.currentColor}
        boardRotation={gameState.boardRotation}
        solutionTree={gameState.solutionTree}
        currentNodeId={gameState.currentNodeId}
        currentNodeInfo={gameState.currentNodeInfo}
        traversalState={gameState.traversalState}
        historyManager={gameState.historyManager}
        feedback={gameState.feedback}
        showSuccess={gameState.showSuccess}
        showFailure={gameState.showFailure}
        completionResult={gameState.completionResult}
        hintsRemaining={gameState.hintsRemaining}
        currentHintText={gameState.currentHintText}
        elapsedTime={gameState.elapsedTime}
        hintsUsed={gameState.hintsUsed}
        puzzleHintCount={puzzle.hint ? 1 : 0}
        autoAdvance={autoAdvance}
        autoAdvanceDelay={autoAdvanceDelay}
        isMobileView={gameState.isMobileView}
        onRotate={gameState.handleRotate}
        onUndo={gameState.handleUndo}
        onReset={gameState.handleRetry}
        onHint={gameState.handleHint}
        onTreeNodeSelect={gameState.handleTreeNodeSelect}
        onShowSuccess={gameState.setShowSuccess}
        onShowFailure={gameState.setShowFailure}
        onRevealFullTree={gameState.setRevealFullTree}
        onFeedbackDismiss={() => gameState.setFeedback(null)}
        {...(onNextPuzzle !== undefined && { onNextPuzzle })}
        {...(puzzleSetNavigation !== undefined && { puzzleSetNavigation })}
        onPrevPuzzle={gameState.handlePrevPuzzle}
        isExploreMode={gameState.isExploreMode}
        onToggleExploreMode={gameState.toggleExploreMode}
      />
    </div>
  );
}

export default PuzzleView;
