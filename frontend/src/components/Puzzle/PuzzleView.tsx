// @ts-nocheck
/**
 * PuzzleView Component - Main puzzle solving interface
 * @module components/Puzzle/PuzzleView
 *
 * Covers: FR-001 to FR-007, US1
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: UI only, delegates to services
 * - IV. Offline First: Works with cached puzzle data
 */

import { useState, useCallback, useEffect } from 'preact/hooks';
import type { JSX } from 'preact';
import type { Coordinate, Puzzle, Stone, Move } from '@models/puzzle';
import { cloneBoardState } from '@models/puzzle';
import { Board, type SolutionMarker } from '../Board/Board';
import { FeedbackOverlay, type FeedbackType } from './FeedbackOverlay';
import { placeStone } from '@services/rulesEngine';
import { playStoneSound, playErrorSound } from '@utils/sound';
import {
  createSolutionState,
  verifyMove,
  advanceSolutionState,
  getHint,
  getSolutionMarkers,
  type SolutionState,
} from '@services/solutionVerifier';

/** Props for PuzzleView component */
export interface PuzzleViewProps {
  /** The puzzle to display and solve */
  puzzle: Puzzle;
  /** Callback when puzzle is completed */
  onComplete?: (stats: PuzzleCompletionStats) => void;
  /** Maximum number of move hints allowed (undefined = unlimited, 0 = disabled) */
  maxMoveHints?: number;
  /** Whether the puzzle has been completed (from parent) */
  isCompleted?: boolean;
  /** CSS class name */
  className?: string;
  /** Difficulty label to display */
  difficultyLabel?: string | null;
  /** Current puzzle number (1-based) */
  puzzleNumber?: number;
  /** Total puzzles in level */
  totalPuzzles?: number;
  /** Callback to go to previous puzzle */
  onPrevious?: () => void;
  /** Callback to go to next puzzle */
  onNext?: () => void;
  /** Callback to retry puzzle */
  onRetry?: () => void;
  /** Completion stats from parent */
  completedStats?: PuzzleCompletionStats | null;
}

/** Statistics about puzzle completion */
export interface PuzzleCompletionStats {
  puzzleId: string;
  attempts: number;
  hintsUsed: number;
  timeMs: number;
  perfectSolve: boolean;
}

/** Component state */
interface PuzzleState {
  board: Stone[][];
  solutionState: SolutionState;
  moveHistory: Move[];
  attempts: number;
  hintsUsed: number;
  moveHintsUsed: number;
  startTime: number;
  isComplete: boolean;
  lastMove: Coordinate | null;
  feedback: { type: FeedbackType; message: string } | null;
  ghostStone: { coord: Coordinate; color: 'black' | 'white' } | null;
  hintHighlight: Coordinate | null;
  isShaking: boolean;
  showSolution: boolean;
  wrongMoveRefuted: boolean; // Track if current state is after a wrong move refutation
}

/**
 * PuzzleView - Main component for solving Go puzzles
 */
export function PuzzleView({
  puzzle,
  onComplete,
  maxMoveHints,
  isCompleted: parentIsCompleted,
  className,
  difficultyLabel: _difficultyLabel,
  puzzleNumber: _puzzleNumber,
  totalPuzzles: _totalPuzzles,
  onPrevious: _onPrevious,
  onNext: _onNext,
  onRetry: _onRetry,
  completedStats,
}: PuzzleViewProps): JSX.Element {
  // Initialize state
  const [state, setState] = useState<PuzzleState>(() => ({
    board: cloneBoardState(puzzle.initialState),
    solutionState: createSolutionState(puzzle),
    moveHistory: [],
    attempts: 0,
    hintsUsed: 0,
    moveHintsUsed: 0,
    startTime: Date.now(),
    isComplete: false,
    lastMove: null,
    feedback: null,
    ghostStone: null,
    hintHighlight: null,
    isShaking: false,
    showSolution: false,
    wrongMoveRefuted: false,
  }));

  /**
   * Toggle solution reveal
   */
  const handleShowSolution = useCallback((): void => {
    setState((prev) => ({
      ...prev,
      showSolution: !prev.showSolution,
      hintHighlight: null, // Clear regular hint when showing solution
    }));
  }, []);

  /**
   * Get solution markers for display
   */
  const solutionMarkers: SolutionMarker[] = state.showSolution
    ? getSolutionMarkers(state.solutionState, puzzle.boardSize).map((m) => ({
        coord: m.coord,
        type: m.type,
      }))
    : [];

  /**
   * Handle intersection click - process move attempt
   */
  const handleIntersectionClick = useCallback(
    (coord: Coordinate): void => {
      if (state.isComplete || state.wrongMoveRefuted) return;

      const { board, solutionState, moveHistory, attempts } = state;
      const playerColor = puzzle.sideToMove;

      // Try to place stone using rules engine
      const result = placeStone(
        board,
        coord,
        playerColor,
        puzzle.boardSize
      );

      if (!result.success) {
        // Invalid move according to Go rules (suicide, ko, occupied) - shake the board
        playErrorSound();
        setState((prev) => ({
          ...prev,
          attempts: prev.attempts + 1,
          isShaking: true,
          feedback: null,
        }));
        // Reset shake after animation
        setTimeout(() => {
          setState((prev) => ({ ...prev, isShaking: false }));
        }, 400);
        return;
      }

      // Move is legal according to Go rules - place the stone
      playStoneSound();
      const newBoard = result.newBoard as Stone[][];
      const newMove: Move = { x: coord.x, y: coord.y, color: playerColor };

      // Now verify against solution tree
      const verification = verifyMove(solutionState, coord, playerColor);

      if (!verification.isCorrect) {
        // Wrong move - place it on board and show computer's refutation
        const opponentColor = playerColor === 'black' ? 'white' : 'black';
        
        // Get the correct move as the refutation (opponent plays the winning move)
        const correctMove = state.solutionState.currentNode.move;
        let refutedBoard = newBoard;
        let refutationMove: Coordinate | null = null;
        
        // Place refutation move after a delay
        const refutationResult = placeStone(newBoard, correctMove, opponentColor, puzzle.boardSize);
        if (refutationResult.success) {
          refutedBoard = refutationResult.newBoard as Stone[][];
          refutationMove = correctMove;
        }
        
        // First show the wrong move
        setState((prev) => ({
          ...prev,
          board: newBoard,
          moveHistory: [...moveHistory, newMove],
          attempts: prev.attempts + 1,
          lastMove: coord,
          feedback: null,
          ghostStone: null,
          hintHighlight: null,
          isShaking: true,
          showSolution: false,
          wrongMoveRefuted: false,
        }));
        
        // Then after delay, show refutation
        setTimeout(() => {
          playStoneSound();
          setState((prev) => ({
            ...prev,
            board: refutedBoard,
            lastMove: refutationMove,
            feedback: { type: 'incorrect', message: "That doesn't work — opponent refutes!" },
            isShaking: false,
            wrongMoveRefuted: true,
          }));
        }, 300);
        
        return;
      }

      // Correct move! Update board and advance solution state
      const newMoveHistory = [...moveHistory, newMove];

      // Advance solution state
      const newSolutionState = advanceSolutionState(
        solutionState,
        verification.matchedNode!,
        coord
      );

      // Check for opponent response
      let finalBoard = newBoard;
      let finalLastMove = coord;
      if (verification.responseMove) {
        // Place opponent's response with slight delay for sound
        const opponentColor = playerColor === 'black' ? 'white' : 'black';
        const opponentResult = placeStone(
          newBoard,
          verification.responseMove,
          opponentColor,
          puzzle.boardSize
        );
        if (opponentResult.success) {
          // Play opponent stone sound after a brief delay
          setTimeout(() => playStoneSound(), 150);
          finalBoard = opponentResult.newBoard as Stone[][];
          finalLastMove = verification.responseMove;
          newMoveHistory.push({
            x: verification.responseMove.x,
            y: verification.responseMove.y,
            color: opponentColor,
          });
        }
      }

      // Check if puzzle is complete
      const isComplete = verification.isComplete || newSolutionState.isComplete;

      const feedbackType: FeedbackType = verification.feedback === 'optimal' ? 'correct' : 'suboptimal';
      const feedbackMessage = isComplete
        ? 'Puzzle complete!'
        : null;

      setState({
        board: finalBoard,
        solutionState: newSolutionState,
        moveHistory: newMoveHistory,
        attempts: attempts + 1,
        hintsUsed: state.hintsUsed,
        moveHintsUsed: state.moveHintsUsed,
        startTime: state.startTime,
        isComplete,
        lastMove: finalLastMove,
        feedback: feedbackMessage ? { type: feedbackType, message: feedbackMessage } : null,
        ghostStone: null,
        hintHighlight: null,
        isShaking: false,
        showSolution: false,
        wrongMoveRefuted: false,
      });

      // Report completion
      if (isComplete && onComplete) {
        onComplete({
          puzzleId: puzzle.id,
          attempts: attempts + 1,
          hintsUsed: state.hintsUsed + state.moveHintsUsed,
          timeMs: Date.now() - state.startTime,
          perfectSolve: attempts === 0 && state.hintsUsed === 0 && state.moveHintsUsed === 0,
        });
      }
    },
    [state, puzzle, onComplete]
  );

  /**
   * Handle hover for ghost stone preview
   */
  const handleIntersectionHover = useCallback(
    (coord: Coordinate | null): void => {
      if (state.isComplete) {
        setState((prev) => ({ ...prev, ghostStone: null }));
        return;
      }

      if (coord) {
        // Check if position is empty
        const stone = state.board[coord.y]?.[coord.x];
        if (stone === 'empty') {
          setState((prev) => ({
            ...prev,
            ghostStone: { coord, color: puzzle.sideToMove },
          }));
          return;
        }
      }

      setState((prev) => ({ ...prev, ghostStone: null }));
    },
    [state.isComplete, state.board, puzzle.sideToMove]
  );

  /**
   * Handle move hint request - reveals and plays the correct move
   */
  const handleMoveHintRequest = useCallback((): void => {
    if (state.isComplete) return;

    // Check if hints are limited and exhausted
    if (maxMoveHints !== undefined && state.moveHintsUsed >= maxMoveHints) {
      setState((prev) => ({
        ...prev,
        feedback: null,
      }));
      return;
    }

    // Get the next correct move from solution state
    const hintMove = getHint(state.solutionState, state.moveHintsUsed);
    if (!hintMove) {
      setState((prev) => ({
        ...prev,
        feedback: null,
      }));
      return;
    }

    // Highlight the hint move (no text feedback - just visual)
    setState((prev) => ({
      ...prev,
      hintHighlight: hintMove,
      moveHintsUsed: prev.moveHintsUsed + 1,
      hintsUsed: prev.hintsUsed + 1,
      feedback: null, // No text feedback, just the visual hint
    }));

    // After a short delay, play the move automatically
    setTimeout(() => {
      // Simulate the move
      const playerColor = puzzle.sideToMove;
      const result = placeStone(
        state.board,
        hintMove,
        playerColor,
        puzzle.boardSize
      );

      if (!result.success) return;

      const verification = verifyMove(state.solutionState, hintMove, playerColor);
      if (!verification.isCorrect) return;

      const newBoard = result.newBoard as Stone[][];
      const newMove: Move = { x: hintMove.x, y: hintMove.y, color: playerColor };
      const newMoveHistory = [...state.moveHistory, newMove];

      const newSolutionState = advanceSolutionState(
        state.solutionState,
        verification.matchedNode!,
        hintMove
      );

      // Handle opponent response
      let finalBoard = newBoard;
      let finalLastMove = hintMove;
      if (verification.responseMove) {
        const opponentColor = playerColor === 'black' ? 'white' : 'black';
        const opponentResult = placeStone(
          newBoard,
          verification.responseMove,
          opponentColor,
          puzzle.boardSize
        );
        if (opponentResult.success) {
          finalBoard = opponentResult.newBoard as Stone[][];
          finalLastMove = verification.responseMove;
          newMoveHistory.push({
            x: verification.responseMove.x,
            y: verification.responseMove.y,
            color: opponentColor,
          });
        }
      }

      const isComplete = verification.isComplete || newSolutionState.isComplete;

      setState((prev) => {
        // Call onComplete if puzzle is done
        if (isComplete && onComplete) {
          onComplete({
            puzzleId: puzzle.id,
            attempts: prev.attempts,
            hintsUsed: prev.hintsUsed,
            timeMs: Date.now() - prev.startTime,
            perfectSolve: false,
          });
        }

        return {
          ...prev,
          board: finalBoard,
          solutionState: newSolutionState,
          moveHistory: newMoveHistory,
          isComplete,
          lastMove: finalLastMove,
          feedback: isComplete 
            ? { type: 'correct' as const, message: 'Puzzle complete!' }
            : null, // No text feedback after hint
          ghostStone: null,
          hintHighlight: null,
        };
      });
    }, 800); // Longer delay for better visual
  }, [state, puzzle, maxMoveHints, onComplete]);

  /**
   * Handle feedback dismissal
   */
  const handleDismissFeedback = useCallback((): void => {
    setState((prev) => ({ ...prev, feedback: null, hintHighlight: null }));
  }, []);

  /**
   * Undo last move (for wrong moves or to try different variation)
   */
  const handleUndo = useCallback((): void => {
    // If refuted, go back to before the wrong move (remove both wrong move and refutation)
    if (state.wrongMoveRefuted) {
      // Reset to before the wrong move
      let board = cloneBoardState(puzzle.initialState);
      const newMoveHistory = state.moveHistory.slice(0, -1); // Remove the wrong move
      let lastMove: Coordinate | null = null;
      
      for (const move of newMoveHistory) {
        const moveColor = move.color as 'black' | 'white';
        const result = placeStone(board, { x: move.x, y: move.y }, moveColor, puzzle.boardSize);
        if (result.success) {
          board = result.newBoard as Stone[][];
          lastMove = { x: move.x, y: move.y };
        }
      }
      
      setState((prev) => ({
        ...prev,
        board,
        moveHistory: newMoveHistory,
        lastMove,
        feedback: null,
        ghostStone: null,
        hintHighlight: null,
        isShaking: false,
        wrongMoveRefuted: false,
      }));
      return;
    }
    
    if (state.moveHistory.length === 0) return;
    
    // Reset to initial state and replay all moves except the last one
    let board = cloneBoardState(puzzle.initialState);
    const newMoveHistory = state.moveHistory.slice(0, -1);
    let lastMove: Coordinate | null = null;
    
    // Replay moves
    for (const move of newMoveHistory) {
      const moveColor = move.color as 'black' | 'white';
      const result = placeStone(board, { x: move.x, y: move.y }, moveColor, puzzle.boardSize);
      if (result.success) {
        board = result.newBoard as Stone[][];
        lastMove = { x: move.x, y: move.y };
      }
    }
    
    setState((prev) => ({
      ...prev,
      board,
      moveHistory: newMoveHistory,
      lastMove,
      feedback: null,
      ghostStone: null,
      hintHighlight: null,
      isShaking: false,
      wrongMoveRefuted: false,
    }));
  }, [state.moveHistory, state.wrongMoveRefuted, puzzle]);

  /**
   * Reset puzzle
   */
  const handleReset = useCallback((): void => {
    setState({
      board: cloneBoardState(puzzle.initialState),
      solutionState: createSolutionState(puzzle),
      moveHistory: [],
      attempts: 0,
      hintsUsed: 0,
      moveHintsUsed: 0,
      startTime: Date.now(),
      isComplete: false,
      lastMove: null,
      feedback: null,
      ghostStone: null,
      hintHighlight: null,
      isShaking: false,
      showSolution: false,
      wrongMoveRefuted: false,
    });
  }, [puzzle]);

  // Auto-dismiss feedback after delay
  useEffect(() => {
    if (state.feedback && state.feedback.type !== 'incorrect') {
      const timer = setTimeout(() => {
        handleDismissFeedback();
      }, 2000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [state.feedback, handleDismissFeedback]);

  return (
    <div className={`puzzle-view ${className ?? ''}`} style={styles.container}>
      {/* Board - with shake animation for incorrect moves */}
      <div 
        className={state.isShaking ? 'shake' : ''} 
        style={styles.boardWrapper}
      >
        <Board
          boardSize={puzzle.boardSize}
          stones={state.board}
          lastMove={state.lastMove}
          ghostStone={state.ghostStone}
          highlightedMove={state.hintHighlight}
          solutionMarkers={solutionMarkers}
          onIntersectionClick={handleIntersectionClick}
          onIntersectionHover={handleIntersectionHover}
          interactive={!state.isComplete && !state.showSolution && !parentIsCompleted && !state.wrongMoveRefuted}
        />

        {/* Feedback overlay */}
        {state.feedback && (
          <FeedbackOverlay
            type={state.feedback.type}
            message={state.feedback.message}
            onDismiss={handleDismissFeedback}
          />
        )}
        
        {/* Completion overlay */}
        {completedStats && (
          <div style={styles.completionOverlay}>
            <div style={styles.completionCard}>
              <p style={styles.completionTitle}>
                ✓ Solved{completedStats.perfectSolve ? ' Perfectly!' : '!'}
              </p>
              <p style={styles.completionStats}>
                {completedStats.attempts} attempt{completedStats.attempts !== 1 ? 's' : ''} · {(completedStats.timeMs / 1000).toFixed(1)}s
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Controls row */}
      <div style={styles.controls}>
        {/* Undo - shows after wrong move refutation OR after moves made */}
        {!state.isComplete && (state.wrongMoveRefuted || state.moveHistory.length > 0) && (
          <button
            onClick={handleUndo}
            style={styles.button}
            aria-label="Undo last move"
          >
            ↩ Undo
          </button>
        )}
        {!state.isComplete && !state.wrongMoveRefuted && (maxMoveHints === undefined || maxMoveHints > 0) && (
          <button
            onClick={handleMoveHintRequest}
            style={{
              ...styles.button,
              ...(maxMoveHints !== undefined && state.moveHintsUsed >= maxMoveHints ? styles.buttonDisabled : {}),
            }}
            disabled={maxMoveHints !== undefined && state.moveHintsUsed >= maxMoveHints}
            aria-label="Show hint"
          >
            💡 Hint
          </button>
        )}
        {!state.isComplete && !state.wrongMoveRefuted && (
          <button
            onClick={handleShowSolution}
            style={{
              ...styles.button,
              ...(state.showSolution ? styles.buttonActive : {}),
            }}
            aria-label={state.showSolution ? 'Hide solution' : 'Show solution'}
          >
            {state.showSolution ? '👁 Hide' : '👁 Solution'}
          </button>
        )}
        <button
          onClick={handleReset}
          style={styles.button}
          aria-label="Reset puzzle"
        >
          ↻ Reset
        </button>
      </div>
    </div>
  );
}

/** Component styles */
const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.5rem',
    maxWidth: '540px',
    margin: '0 auto',
  },
  difficultyBadge: {
    padding: '0.25rem 0.6rem',
    fontSize: '0.7rem',
    fontWeight: '600',
    color: '#5C4A32',
    background: 'rgba(212, 165, 116, 0.25)',
    borderRadius: '10px',
    letterSpacing: '0.02em',
  },
  puzzleCounter: {
    fontSize: '0.75rem',
    fontWeight: '500',
    color: '#8B7355',
  },
  boardWrapper: {
    position: 'relative',
    width: '100%',
    maxWidth: '500px',
    aspectRatio: '1 / 1',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 4px 24px rgba(0, 0, 0, 0.12)',
  },
  completionOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    pointerEvents: 'none',
    zIndex: 10,
  },
  completionCard: {
    background: 'rgba(255, 255, 255, 0.95)',
    padding: '1rem 1.5rem',
    borderRadius: '16px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
    textAlign: 'center',
  },
  completionTitle: {
    fontSize: '1.1rem',
    fontWeight: '600',
    color: '#16A34A',
    margin: 0,
  },
  completionStats: {
    fontSize: '0.8rem',
    color: '#666',
    marginTop: '0.25rem',
    margin: '0.25rem 0 0 0',
  },
  controls: {
    display: 'flex',
    gap: '0.5rem',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  button: {
    padding: '0.5rem 0.9rem',
    fontSize: '0.8rem',
    fontWeight: '500',
    border: 'none',
    borderRadius: '16px',
    background: 'rgba(0, 0, 0, 0.06)',
    color: '#333',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  buttonDisabled: {
    background: 'rgba(0, 0, 0, 0.03)',
    color: '#999',
    cursor: 'not-allowed',
  },
  buttonActive: {
    background: 'rgba(34, 197, 94, 0.15)',
    color: '#16A34A',
  },
  navRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    maxWidth: '500px',
    marginTop: '0.25rem',
  },
  navCenter: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  navButton: {
    padding: '0.6rem 0.9rem',
    fontSize: '1rem',
    fontWeight: '400',
    border: 'none',
    borderRadius: '50%',
    background: 'rgba(92, 74, 50, 0.1)',
    color: '#5C4A32',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  retryButton: {
    padding: '0.35rem 0.7rem',
    fontSize: '0.7rem',
    fontWeight: '500',
    border: 'none',
    borderRadius: '12px',
    background: 'rgba(92, 74, 50, 0.1)',
    color: '#5C4A32',
    cursor: 'pointer',
  },
};

export default PuzzleView;
