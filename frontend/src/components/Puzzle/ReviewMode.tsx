/**
 * ReviewMode Component - Solution review with step-through controls
 * @module components/Puzzle/ReviewMode
 *
 * Covers: FR-036, FR-037, FR-038, US6
 *
 * Allows users to step through the solution move by move after completion.
 */

import { useState, useCallback, useMemo } from 'preact/hooks';
import type { JSX } from 'preact';
import type { Coordinate, Puzzle, Stone, Move, SolutionNode } from '@models/puzzle';
import { cloneBoardState } from '@models/puzzle';
import { colorToStone, opponent } from '../../types/board';
import { Board } from '../Board/Board';
import { placeStone } from '@services/rulesEngine';

/** Props for ReviewMode component */
export interface ReviewModeProps {
  /** The puzzle to review */
  readonly puzzle: Puzzle;
  /** Callback when exiting review mode */
  readonly onExit?: () => void;
  /** CSS class name */
  readonly className?: string;
}

/** A single step in the solution path */
export interface SolutionStep {
  /** The move made */
  readonly move: Move;
  /** Board state after this move */
  readonly boardState: readonly (readonly Stone[])[];
  /** Explanation for this move, if available */
  readonly explanation: string | undefined;
  /** Move index (0-based) */
  readonly index: number;
  /** Whether this is a player or opponent move */
  readonly isPlayerMove: boolean;
}

/**
 * Extract the main line solution path from solution tree.
 * Follows the first branch at each node to get the canonical solution.
 */
function extractSolutionPath(
  puzzle: Puzzle
): SolutionStep[] {
  const steps: SolutionStep[] = [];
  const board = cloneBoardState(puzzle.initialState);
  let currentNode: SolutionNode | undefined = puzzle.solutionTree;
  let moveIndex = 0;
  const playerColor: Stone = colorToStone(puzzle.sideToMove);
  const opponentColor: Stone = opponent(playerColor);

  while (currentNode) {
    // Player's move
    const playerMove: Move = {
      x: currentNode.move.x,
      y: currentNode.move.y,
      color: playerColor,
    };

    // Apply player's move to board
    const playerResult = placeStone(
      board,
      currentNode.move,
      playerColor,
      puzzle.boardSize
    );

    if (playerResult.success && playerResult.newBoard) {
      // Copy new board state back
      const newBoard = playerResult.newBoard;
      for (let y = 0; y < puzzle.boardSize; y++) {
        const boardRow = board[y];
        const newRow = newBoard[y];
        if (boardRow && newRow) {
          for (let x = 0; x < puzzle.boardSize; x++) {
            const stone = newRow[x];
            if (stone !== undefined) {
              boardRow[x] = stone;
            }
          }
        }
      }
    }

    // Find explanation for this move
    const explanation = puzzle.explanations.find(
      (exp) => exp.move.x === currentNode!.move.x && exp.move.y === currentNode!.move.y
    );

    steps.push({
      move: playerMove,
      boardState: board.map((row) => [...row]),
      explanation: explanation?.text,
      index: moveIndex++,
      isPlayerMove: true,
    });

    // Check for opponent's response
    if (currentNode.response) {
      const opponentMove: Move = {
        x: currentNode.response.x,
        y: currentNode.response.y,
        color: opponentColor,
      };

      // Apply opponent's move
      const opponentResult = placeStone(
        board,
        currentNode.response,
        opponentColor,
        puzzle.boardSize
      );

      if (opponentResult.success && opponentResult.newBoard) {
        const newBoard = opponentResult.newBoard;
        for (let y = 0; y < puzzle.boardSize; y++) {
          const boardRow = board[y];
          const newRow = newBoard[y];
          if (boardRow && newRow) {
            for (let x = 0; x < puzzle.boardSize; x++) {
              const stone = newRow[x];
              if (stone !== undefined) {
                boardRow[x] = stone;
              }
            }
          }
        }
      }

      // Find explanation for opponent's move
      const responseExplanation = puzzle.explanations.find(
        (exp) =>
          exp.move.x === currentNode!.response!.x &&
          exp.move.y === currentNode!.response!.y
      );

      steps.push({
        move: opponentMove,
        boardState: board.map((row) => [...row]),
        explanation: responseExplanation?.text,
        index: moveIndex++,
        isPlayerMove: false,
      });
    }

    // Follow first branch to continue main line
    currentNode = currentNode.branches?.[0];
  }

  return steps;
}

/**
 * Hook for managing review mode state
 */
export function useReviewMode(puzzle: Puzzle) {
  const solutionPath = useMemo(() => extractSolutionPath(puzzle), [puzzle]);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1); // -1 = initial position

  const currentBoard = useMemo(() => {
    if (currentStepIndex < 0) {
      return puzzle.initialState;
    }
    return solutionPath[currentStepIndex]?.boardState ?? puzzle.initialState;
  }, [puzzle, solutionPath, currentStepIndex]);

  const currentStep = useMemo(() => {
    if (currentStepIndex < 0) return null;
    return solutionPath[currentStepIndex] ?? null;
  }, [solutionPath, currentStepIndex]);

  const canGoBack = currentStepIndex >= 0;
  const canGoForward = currentStepIndex < solutionPath.length - 1;
  const isAtStart = currentStepIndex < 0;
  const isAtEnd = currentStepIndex >= solutionPath.length - 1;

  const goToStart = useCallback(() => {
    setCurrentStepIndex(-1);
  }, []);

  const goToEnd = useCallback(() => {
    setCurrentStepIndex(solutionPath.length - 1);
  }, [solutionPath.length]);

  const goForward = useCallback(() => {
    if (canGoForward) {
      setCurrentStepIndex((prev) => prev + 1);
    }
  }, [canGoForward]);

  const goBack = useCallback(() => {
    if (canGoBack) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  }, [canGoBack]);

  const goToStep = useCallback(
    (index: number) => {
      if (index >= -1 && index < solutionPath.length) {
        setCurrentStepIndex(index);
      }
    },
    [solutionPath.length]
  );

  return {
    solutionPath,
    currentStepIndex,
    currentBoard,
    currentStep,
    canGoBack,
    canGoForward,
    isAtStart,
    isAtEnd,
    totalSteps: solutionPath.length,
    goToStart,
    goToEnd,
    goForward,
    goBack,
    goToStep,
  };
}

/** Return type of useReviewMode hook */
export type ReviewModeState = ReturnType<typeof useReviewMode>;

/**
 * ReviewMode - Solution review component with step-through controls
 */
export function ReviewMode({
  puzzle,
  onExit,
  className,
}: ReviewModeProps): JSX.Element {
  const review = useReviewMode(puzzle);

  const lastMove: Coordinate | null = useMemo(() => {
    if (review.currentStep) {
      return {
        x: review.currentStep.move.x,
        y: review.currentStep.move.y,
      };
    }
    return null;
  }, [review.currentStep]);

  return (
    <div
      className={`review-mode ${className ?? ''}`}
      role="region"
      aria-label="Solution review"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
        maxWidth: '600px',
        margin: '0 auto',
      }}
    >
      {/* Header */}
      <div
        className="review-header"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.5rem',
        }}
      >
        <h2
          style={{
            margin: 0,
            fontSize: '1.25rem',
            color: '#333',
          }}
        >
          Solution Review
        </h2>
        {onExit && (
          <button
            type="button"
            onClick={onExit}
            aria-label="Exit review mode"
            style={{
              padding: '0.5rem 1rem',
              fontSize: '0.9rem',
              borderRadius: '6px',
              border: '1px solid #dee2e6',
              backgroundColor: 'transparent',
              cursor: 'pointer',
            }}
          >
            Exit Review
          </button>
        )}
      </div>

      {/* Board display */}
      <div className="review-board">
        <Board
          boardSize={puzzle.boardSize}
          stones={review.currentBoard}
          lastMove={lastMove}
          interactive={false}
        />
      </div>

      {/* Step indicator */}
      <div
        className="review-step-indicator"
        role="status"
        aria-live="polite"
        style={{
          textAlign: 'center',
          fontSize: '0.9rem',
          color: '#6c757d',
        }}
      >
        {review.isAtStart
          ? 'Initial position'
          : `Move ${review.currentStepIndex + 1} of ${review.totalSteps}`}
        {review.currentStep && (
          <span style={{ marginLeft: '0.5rem' }}>
            ({review.currentStep.isPlayerMove ? puzzle.sideToMove : puzzle.sideToMove === 'black' ? 'white' : 'black'} plays)
          </span>
        )}
      </div>

      {/* Explanation panel */}
      {review.currentStep?.explanation && (
        <div
          className="review-explanation"
          role="region"
          aria-label="Move explanation"
          style={{
            padding: '1rem',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            border: '1px solid #e9ecef',
          }}
        >
          <p style={{ margin: 0, lineHeight: 1.6 }}>{review.currentStep.explanation}</p>
        </div>
      )}

      {/* Navigation controls */}
      <ReviewControls
        canGoBack={review.canGoBack}
        canGoForward={review.canGoForward}
        isAtStart={review.isAtStart}
        isAtEnd={review.isAtEnd}
        onGoToStart={review.goToStart}
        onGoBack={review.goBack}
        onGoForward={review.goForward}
        onGoToEnd={review.goToEnd}
      />

      {/* Progress bar */}
      <div
        className="review-progress"
        role="progressbar"
        aria-valuenow={review.currentStepIndex + 1}
        aria-valuemin={0}
        aria-valuemax={review.totalSteps}
        aria-label={`Review progress: ${review.currentStepIndex + 1} of ${review.totalSteps} moves`}
        style={{
          height: '4px',
          backgroundColor: '#e9ecef',
          borderRadius: '2px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: review.totalSteps > 0
              ? `${((review.currentStepIndex + 1) / review.totalSteps) * 100}%`
              : '0%',
            height: '100%',
            backgroundColor: '#4a90d9',
            transition: 'width 0.2s ease',
          }}
        />
      </div>
    </div>
  );
}

/** Props for ReviewControls component */
export interface ReviewControlsProps {
  readonly canGoBack: boolean;
  readonly canGoForward: boolean;
  readonly isAtStart: boolean;
  readonly isAtEnd: boolean;
  readonly onGoToStart: () => void;
  readonly onGoBack: () => void;
  readonly onGoForward: () => void;
  readonly onGoToEnd: () => void;
  readonly className?: string;
}

/**
 * ReviewControls - Navigation buttons for stepping through solution
 */
export function ReviewControls({
  canGoBack,
  canGoForward,
  isAtStart,
  isAtEnd,
  onGoToStart,
  onGoBack,
  onGoForward,
  onGoToEnd,
  className,
}: ReviewControlsProps): JSX.Element {
  const buttonStyle = (enabled: boolean): JSX.CSSProperties => ({
    padding: '0.5rem 1rem',
    fontSize: '1rem',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: enabled ? '#4a90d9' : '#e9ecef',
    color: enabled ? '#ffffff' : '#6c757d',
    cursor: enabled ? 'pointer' : 'not-allowed',
    minWidth: '3rem',
    transition: 'background-color 0.2s',
  });

  return (
    <div
      className={`review-controls ${className ?? ''}`}
      role="group"
      aria-label="Review navigation controls"
      style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '0.5rem',
        padding: '0.5rem',
      }}
    >
      <button
        type="button"
        onClick={onGoToStart}
        disabled={isAtStart}
        aria-label="Go to start"
        title="Go to start"
        style={buttonStyle(!isAtStart)}
      >
        ⏮
      </button>
      <button
        type="button"
        onClick={onGoBack}
        disabled={!canGoBack}
        aria-label="Previous move"
        title="Previous move"
        style={buttonStyle(canGoBack)}
      >
        ◀
      </button>
      <button
        type="button"
        onClick={onGoForward}
        disabled={!canGoForward}
        aria-label="Next move"
        title="Next move"
        style={buttonStyle(canGoForward)}
      >
        ▶
      </button>
      <button
        type="button"
        onClick={onGoToEnd}
        disabled={isAtEnd}
        aria-label="Go to end"
        title="Go to end"
        style={buttonStyle(!isAtEnd)}
      >
        ⏭
      </button>
    </div>
  );
}

export default ReviewMode;
