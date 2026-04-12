/**
 * usePuzzleState — Reactive puzzle solve state from goban events.
 * @module hooks/usePuzzleState
 *
 * Manages the puzzle solving lifecycle:
 *   loading → solving → correct/wrong → complete → review
 *
 * Uses useReducer for atomic state transitions. All state updates
 * come from goban events (puzzle-correct-answer, puzzle-wrong-answer,
 * update, puzzle-place).
 *
 * Move Order Validation (T034):
 * - YO[flexible] (default): Any correct branch is accepted
 * - YO[strict]: Only the first (trunk) move at each decision point is accepted
 *
 * Spec 125, Tasks T029, T034
 */

import { useReducer, useEffect, useCallback } from 'preact/hooks';
import type { GobanInstance } from './useGoban';
import { audioService } from '../services/audioService';

// ============================================================================
// Types
// ============================================================================

/** Move order validation mode (YO property) */
export type MoveOrderMode = 'strict' | 'flexible';

/** Puzzle solve lifecycle status */
export type PuzzleStatus =
  | 'loading' // Waiting for goban initialization
  | 'solving' // User actively solving
  | 'correct' // Just played a correct move (transient)
  | 'wrong' // Just played a wrong move
  | 'complete' // All moves played correctly
  | 'review'; // Exploring solution tree

/**
 * Reactive puzzle solve state.
 * Drives UI indicators and progress tracking.
 */
export interface PuzzleSolveState {
  /** Current puzzle status */
  readonly status: PuzzleStatus;
  /** Number of moves made by the player */
  readonly moveCount: number;
  /** Whether hints have been used */
  readonly hintsUsed: boolean;
  /** Current hint tier displayed (0 = none, 1-3 = hint tiers) */
  readonly currentHintTier: number;
  /** Active move comment (from SGF C property) */
  readonly currentComment: string | undefined;
  /** Whether solution has been revealed */
  readonly solutionRevealed: boolean;
  /** Number of wrong attempts */
  readonly wrongAttempts: number;
  /** Timestamp when solving started */
  readonly startedAt: number | null;
  /** Number of out-of-order moves (for strict mode tracking) */
  readonly outOfOrderMoves: number;
}

/** Initial state */
const INITIAL_STATE: PuzzleSolveState = {
  status: 'loading',
  moveCount: 0,
  hintsUsed: false,
  currentHintTier: 0,
  currentComment: undefined,
  solutionRevealed: false,
  wrongAttempts: 0,
  startedAt: null,
  outOfOrderMoves: 0,
};

// ============================================================================
// Actions
// ============================================================================

type PuzzleAction =
  | { type: 'GOBAN_READY' }
  | { type: 'CORRECT_ANSWER' }
  | { type: 'WRONG_ANSWER' }
  | { type: 'PUZZLE_COMPLETE' }
  | { type: 'MOVE_PLACED' }
  | { type: 'UPDATE_COMMENT'; comment: string | undefined }
  | { type: 'USE_HINT'; tier: number }
  | { type: 'REVEAL_SOLUTION' }
  | { type: 'ENTER_REVIEW' }
  | { type: 'RESET' }
  | { type: 'OUT_OF_ORDER' }
  | { type: 'UNDO' };

// ============================================================================
// Reducer
// ============================================================================

function puzzleReducer(state: PuzzleSolveState, action: PuzzleAction): PuzzleSolveState {
  switch (action.type) {
    case 'GOBAN_READY':
      return {
        ...state,
        status: 'solving',
        startedAt: Date.now(),
      };

    case 'CORRECT_ANSWER':
      // Transient "correct" status — UI shows green flash
      return {
        ...state,
        status: 'correct',
      };

    case 'WRONG_ANSWER':
      // Guard: ignore wrong answers during review mode — the user is exploring,
      // not solving. Stone placement should be disabled but goban may re-enable it.
      if (state.status === 'review') return state;
      return {
        ...state,
        status: 'wrong',
        wrongAttempts: state.wrongAttempts + 1,
      };

    case 'PUZZLE_COMPLETE':
      return {
        ...state,
        status: 'complete',
      };

    case 'MOVE_PLACED':
      // Guard: ignore stone placements during review mode — goban's
      // showNext/showPrevious re-enables placement internally.
      if (state.status === 'review') return state;
      // Only count player moves (not opponent auto-plays)
      // Return to solving after correct/wrong indicator
      return {
        ...state,
        status: 'solving',
        moveCount: state.moveCount + 1,
      };

    case 'UPDATE_COMMENT':
      return {
        ...state,
        currentComment: action.comment,
      };

    case 'USE_HINT':
      return {
        ...state,
        hintsUsed: true,
        currentHintTier: action.tier,
      };

    case 'REVEAL_SOLUTION':
      return {
        ...state,
        solutionRevealed: true,
      };

    case 'ENTER_REVIEW':
      return {
        ...state,
        status: 'review',
      };

    case 'RESET':
      return {
        ...INITIAL_STATE,
        status: 'solving',
        startedAt: Date.now(),
      };

    case 'UNDO':
      // Guard: ignore undo during review mode
      if (state.status === 'review') return state;
      // Decrement move count, return to solving if was wrong
      return {
        ...state,
        status: 'solving',
        moveCount: Math.max(0, state.moveCount - 1),
      };

    case 'OUT_OF_ORDER':
      // Track out-of-order moves for strict mode
      return {
        ...state,
        outOfOrderMoves: state.outOfOrderMoves + 1,
      };

    default:
      return state;
  }
}

// ============================================================================
// Hook Interface
// ============================================================================
// Hook Interface
// ============================================================================

/**
 * Options for usePuzzleState hook.
 */
export interface UsePuzzleStateOptions {
  /** Move order mode from YO property (default: 'flexible') */
  moveOrder?: MoveOrderMode;
}

export interface UsePuzzleStateResult {
  /** Current puzzle solve state */
  state: PuzzleSolveState;
  /** Call when goban is ready (mounted and initialized) */
  onGobanReady: () => void;
  /** Request hint at specified tier (1-3) */
  requestHint: (tier: number) => void;
  /** Reveal full solution */
  revealSolution: () => void;
  /** Enter review mode (explore solution tree) */
  enterReview: () => void;
  /** Reset puzzle to initial state */
  reset: () => void;
  /** Undo last move */
  undo: () => void;
  /** Whether puzzle is in a terminal state (complete/wrong) */
  isTerminal: boolean;
  /** Time elapsed since solving started (ms), or null if not started */
  elapsedMs: number | null;
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Manage puzzle solve state using goban events.
 *
 * @param goban - GobanInstance from useGoban hook (null while loading)
 * @param options - Optional configuration including move order mode
 * @returns Puzzle state and control functions
 *
 * @example
 * ```tsx
 * const { goban } = useGoban({ rawSgf, boardDiv: ref.current });
 * const {
 *   state,
 *   onGobanReady,
 *   requestHint,
 *   reset,
 *   isTerminal
 * } = usePuzzleState(goban, { moveOrder: 'strict' });
 *
 * useEffect(() => {
 *   if (goban) onGobanReady();
 * }, [goban, onGobanReady]);
 * ```
 */
export function usePuzzleState(
  goban: GobanInstance | null,
  options: UsePuzzleStateOptions = {}
): UsePuzzleStateResult {
  const { moveOrder = 'flexible' } = options;
  const [state, dispatch] = useReducer(puzzleReducer, INITIAL_STATE);

  // -------------------------------------------------------------------------
  // Move order validation helper
  // -------------------------------------------------------------------------
  /**
   * Check if the current move is on the main trunk line.
   * For YO[strict] mode, we only accept trunk moves.
   *
   * Returns true if:
   * - Move order is 'flexible' (always accept)
   * - Current move is the parent's trunk_next (main line)
   */
  const isOnTrunk = useCallback((): boolean => {
    if (moveOrder === 'flexible') return true;
    if (!goban?.engine) return true;

    const curMove = goban.engine.cur_move;
    if (!curMove) return true;

    const parentMove = curMove.parent;
    if (!parentMove) return true; // Root move is always on trunk

    // Check if this move is the parent's trunk_next
    return parentMove.trunk_next === curMove;
  }, [goban, moveOrder]);

  // -------------------------------------------------------------------------
  // Subscribe to goban events
  // -------------------------------------------------------------------------
  useEffect(() => {
    if (!goban) return;

    // Delay (ms) between stone placement click and validation feedback sound.
    // Lets the player hear the satisfying "click" before correct/wrong plays.
    const VALIDATION_SOUND_DELAY_MS = 150;

    // Handler: Correct answer
    const onCorrectAnswer = (): void => {
      // For strict mode, check if move is on trunk
      if (moveOrder === 'strict' && !isOnTrunk()) {
        // Move is correct but not in order — track for stats
        dispatch({ type: 'OUT_OF_ORDER' });
      }

      setTimeout(() => audioService.play('correct'), VALIDATION_SOUND_DELAY_MS);
      dispatch({ type: 'CORRECT_ANSWER' });

      // Check if puzzle is complete (terminal node — no more moves)
      const curMove = goban.engine?.cur_move;
      if (curMove && !curMove.trunk_next && (!curMove.branches || curMove.branches.length === 0)) {
        dispatch({ type: 'PUZZLE_COMPLETE' });
      }
    };

    // Handler: Wrong answer
    const onWrongAnswer = (): void => {
      setTimeout(() => audioService.play('wrong'), VALIDATION_SOUND_DELAY_MS);
      dispatch({ type: 'WRONG_ANSWER' });
    };

    // Handler: Stone placed (by player in puzzle mode)
    // Play stone placement sound on every move. Correct/wrong/complete sounds
    // are additive feedback on top of the placement click.
    //
    // P0-WRONG: The goban library suppresses `puzzle-wrong-answer` for off-tree
    // moves when any ancestor has correct_answer=true (which the root always
    // does). We detect this by checking — after goban's synchronous event
    // dispatch completes — whether the placed node has neither correct_answer
    // nor wrong_answer and no branches. If so, it's an off-tree wrong move
    // and we dispatch WRONG_ANSWER manually.
    let wrongFired = false;
    let correctFired = false;

    const trackCorrect = (): void => {
      correctFired = true;
    };
    const trackWrong = (): void => {
      wrongFired = true;
    };

    const onPuzzlePlace = (): void => {
      // Play stone placement sound immediately on every move
      audioService.play('stone');

      // Reset trackers before goban fires its events synchronously
      wrongFired = false;
      correctFired = false;

      // Temporarily listen for same-tick correct/wrong events
      goban.on('puzzle-correct-answer', trackCorrect);
      goban.on('puzzle-wrong-answer', trackWrong);

      dispatch({ type: 'MOVE_PLACED' });

      // Use queueMicrotask so goban's synchronous event dispatch completes first
      queueMicrotask(() => {
        goban.off('puzzle-correct-answer', trackCorrect);
        goban.off('puzzle-wrong-answer', trackWrong);

        // If goban didn't fire correct or wrong, determine if this is:
        // (a) an opponent's auto-played move (from the solution tree), or
        // (b) a player's off-tree move (should be marked wrong)
        if (!correctFired && !wrongFired) {
          const curMove = goban.engine?.cur_move;
          if (curMove && !curMove.correct_answer && !curMove.wrong_answer) {
            // Determine if this is the opponent's auto-played move by checking
            // the stone's player number against the puzzle's initial_player.
            // In goban: player=1 is black, player=2 is white.
            const initialPlayer = goban.engine?.config?.initial_player;
            const playerNum = initialPlayer === 'black' ? 1 : 2;
            const isOpponentMove = curMove.player !== undefined && curMove.player !== playerNum;

            if (isOpponentMove) {
              // Opponent auto-played — check if this completes the puzzle
              // (terminal node with a correct ancestor means the solution is complete)
              if (!curMove.trunk_next && (!curMove.branches || curMove.branches.length === 0)) {
                let ancestor = curMove.parent;
                let ancestorCorrect = false;
                while (ancestor) {
                  if (ancestor.correct_answer) {
                    ancestorCorrect = true;
                    break;
                  }
                  ancestor = ancestor.parent;
                }
                if (ancestorCorrect) {
                  dispatch({ type: 'PUZZLE_COMPLETE' });
                }
              }
            } else {
              // Player's off-tree move — mark as wrong
              setTimeout(() => audioService.play('wrong'), VALIDATION_SOUND_DELAY_MS);
              dispatch({ type: 'WRONG_ANSWER' });
            }
          }
        }
      });

      // Force full canvas redraw to clear line artifacts at board edges
      requestAnimationFrame(() => goban.redraw(true));
    };

    // Handler: Board state update (for comments)
    const onUpdate = (): void => {
      const curMove = goban.engine?.cur_move;
      const comment = curMove?.text ?? undefined;
      dispatch({ type: 'UPDATE_COMMENT', comment });
    };

    // Subscribe to events
    goban.on('puzzle-correct-answer', onCorrectAnswer);
    goban.on('puzzle-wrong-answer', onWrongAnswer);
    goban.on('puzzle-place', onPuzzlePlace);
    goban.on('update', onUpdate);

    // Cleanup
    return () => {
      goban.off('puzzle-correct-answer', onCorrectAnswer);
      goban.off('puzzle-wrong-answer', onWrongAnswer);
      goban.off('puzzle-place', onPuzzlePlace);
      goban.off('update', onUpdate);
    };
  }, [goban, moveOrder, isOnTrunk]);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------
  const onGobanReady = useCallback(() => {
    dispatch({ type: 'GOBAN_READY' });
  }, []);

  const requestHint = useCallback((tier: number) => {
    const clampedTier = Math.max(1, Math.min(3, tier));
    dispatch({ type: 'USE_HINT', tier: clampedTier });
  }, []);

  const revealSolution = useCallback(() => {
    if (goban) {
      // Reset to start so user can step through the solution from move 1
      goban.showFirst?.();
      // Disable stone placement — we're in review mode now, not solving
      goban.disableStonePlacement?.();
    }
    dispatch({ type: 'REVEAL_SOLUTION' });
    dispatch({ type: 'ENTER_REVIEW' });
  }, [goban]);

  const enterReview = useCallback(() => {
    dispatch({ type: 'ENTER_REVIEW' });
  }, []);

  const reset = useCallback(() => {
    if (goban) {
      // Reset goban to initial position
      goban.showFirst?.();
      // Jump to the actual root node (setup stones only)
      try {
        if (goban.engine?.move_tree) {
          goban.engine.jumpTo(goban.engine.move_tree);
          goban.redraw(true);
        }
      } catch {
        // Non-critical
      }
      // Re-enable stone placement so user can click again after reset
      if (goban.mode === 'puzzle') {
        goban.enableStonePlacement();
      }
    }
    dispatch({ type: 'RESET' });
  }, [goban]);

  const undo = useCallback(() => {
    if (goban) {
      // Undo last move in goban — navigate back in move tree
      goban.showPrevious?.();
      // Re-enable stone placement in case it was disabled after wrong answer
      if (goban.mode === 'puzzle') {
        goban.enableStonePlacement();
      }
    }
    dispatch({ type: 'UNDO' });
  }, [goban]);

  // -------------------------------------------------------------------------
  // Derived state
  // -------------------------------------------------------------------------
  const isTerminal = state.status === 'complete' || state.status === 'wrong';

  const elapsedMs = state.startedAt !== null ? Date.now() - state.startedAt : null;

  return {
    state,
    onGobanReady,
    requestHint,
    revealSolution,
    enterReview,
    reset,
    undo,
    isTerminal,
    elapsedMs,
  };
}
