/**
 * Undo/retry functionality for puzzle solving
 * @module lib/solver/history
 *
 * Covers: FR-017 (Undo/retry)
 *
 * Constitution Compliance:
 * - III. Separation of Concerns: History management separate from game logic
 * - IV. Local-First: All history stored in memory, can be persisted to localStorage
 */

import type { SgfCoord } from '../../types';
import type { PuzzleBoard } from '../../services/puzzleGameState';

/**
 * History entry for a single turn
 */
export interface HistoryEntry {
  /** Turn number (0-indexed) */
  turn: number;
  /** Player's move */
  playerMove: SgfCoord;
  /** Opponent's response (if any) */
  opponentMove?: SgfCoord;
  /** Captures from player move */
  playerCaptures: readonly SgfCoord[];
  /** Captures from opponent move */
  opponentCaptures: readonly SgfCoord[];
  /** Board state before this turn */
  boardStateBefore: PuzzleBoard;
  /** Was this move correct? */
  wasCorrect: boolean;
  /** Timestamp */
  timestamp: number;
}

/**
 * History state for a puzzle session
 */
export interface HistoryState {
  /** Puzzle ID */
  puzzleId: string;
  /** All history entries */
  entries: readonly HistoryEntry[];
  /** Current position in history */
  currentIndex: number;
  /** Initial board state */
  initialBoard: PuzzleBoard;
  /** Session start time */
  startTime: number;
  /** Total attempts (doesn't decrement on undo per FR-017) */
  totalAttempts: number;
}

/**
 * Create a new history state
 *
 * @param puzzleId - Puzzle ID
 * @param initialBoard - Initial board state
 * @returns New history state
 */
export function createHistoryState(puzzleId: string, initialBoard: PuzzleBoard): HistoryState {
  return {
    puzzleId,
    entries: [],
    currentIndex: -1,
    initialBoard,
    startTime: Date.now(),
    totalAttempts: 0,
  };
}

/**
 * Add an entry to history
 *
 * @param state - Current history state
 * @param entry - Entry to add (without turn number)
 * @returns Updated history state
 */
export function addHistoryEntry(
  state: HistoryState,
  entry: Omit<HistoryEntry, 'turn'>
): HistoryState {
  // When adding new entry, discard any "future" entries if we've undone
  const entries = state.entries.slice(0, state.currentIndex + 1);

  const newEntry: HistoryEntry = {
    ...entry,
    turn: entries.length,
  };

  return {
    ...state,
    entries: [...entries, newEntry],
    currentIndex: entries.length,
    totalAttempts: state.totalAttempts + 1,
  };
}

/**
 * Undo the last move pair (player + opponent)
 *
 * @param state - Current history state
 * @returns Updated history state or null if can't undo
 */
export function undo(state: HistoryState): HistoryState | null {
  if (state.currentIndex < 0) {
    return null; // Nothing to undo
  }

  return {
    ...state,
    currentIndex: state.currentIndex - 1,
    // Note: totalAttempts does NOT decrement per FR-017
  };
}

/**
 * Redo a previously undone move
 *
 * @param state - Current history state
 * @returns Updated history state or null if can't redo
 */
export function redo(state: HistoryState): HistoryState | null {
  if (state.currentIndex >= state.entries.length - 1) {
    return null; // Nothing to redo
  }

  return {
    ...state,
    currentIndex: state.currentIndex + 1,
  };
}

/**
 * Reset history to beginning (retry puzzle)
 *
 * @param state - Current history state
 * @returns Reset history state
 */
export function retry(state: HistoryState): HistoryState {
  return {
    ...state,
    entries: [],
    currentIndex: -1,
    // Note: totalAttempts resets on new puzzle, not on retry within session
    // Per FR-017: attempts reset on new puzzle
  };
}

/**
 * Get the board state at current history position
 *
 * @param state - History state
 * @returns Board state
 */
export function getCurrentBoard(state: HistoryState): PuzzleBoard {
  if (state.currentIndex < 0) {
    return state.initialBoard;
  }

  // Get board state after the current entry's moves
  // This would need to be recalculated from entries
  // For simplicity, we store boardStateBefore in each entry
  const entry = state.entries[state.currentIndex];
  if (!entry) {
    return state.initialBoard;
  }

  // We need to reconstruct the board after this turn's moves
  // This is where we'd replay the moves from boardStateBefore
  // For now, return initial board (full implementation would track board state)
  return state.initialBoard;
}

/**
 * Get moves up to current position
 *
 * @param state - History state
 * @returns Array of moves
 */
export function getCurrentMoves(state: HistoryState): SgfCoord[] {
  const moves: SgfCoord[] = [];

  for (let i = 0; i <= state.currentIndex && i < state.entries.length; i++) {
    const entry = state.entries[i];
    if (entry) {
      moves.push(entry.playerMove);
      if (entry.opponentMove) {
        moves.push(entry.opponentMove);
      }
    }
  }

  return moves;
}

/**
 * Check if undo is available
 *
 * @param state - History state
 * @returns true if can undo
 */
export function canUndo(state: HistoryState): boolean {
  return state.currentIndex >= 0;
}

/**
 * Check if redo is available
 *
 * @param state - History state
 * @returns true if can redo
 */
export function canRedo(state: HistoryState): boolean {
  return state.currentIndex < state.entries.length - 1;
}

/**
 * Get elapsed time for this session
 *
 * @param state - History state
 * @returns Elapsed time in milliseconds
 */
export function getElapsedTime(state: HistoryState): number {
  return Date.now() - state.startTime;
}

/**
 * History manager for convenient state management
 */
export interface HistoryManager {
  /** Current state */
  getState: () => HistoryState;
  /** Add a move to history */
  addMove: (
    playerMove: SgfCoord,
    opponentMove: SgfCoord | undefined,
    playerCaptures: readonly SgfCoord[],
    opponentCaptures: readonly SgfCoord[],
    boardStateBefore: PuzzleBoard,
    wasCorrect: boolean
  ) => void;
  /** Undo last move */
  undo: () => boolean;
  /** Redo move */
  redo: () => boolean;
  /** Retry puzzle */
  retry: () => void;
  /** Can undo? */
  canUndo: () => boolean;
  /** Can redo? */
  canRedo: () => boolean;
  /** Get current move list */
  getMoves: () => SgfCoord[];
  /** Get elapsed time */
  getElapsedTime: () => number;
  /** Get attempt count */
  getAttemptCount: () => number;
}

/**
 * Create a history manager
 *
 * @param puzzleId - Puzzle ID
 * @param initialBoard - Initial board state
 * @param onChange - Callback when history changes
 * @returns History manager
 */
export function createHistoryManager(
  puzzleId: string,
  initialBoard: PuzzleBoard,
  onChange?: (state: HistoryState) => void
): HistoryManager {
  let state = createHistoryState(puzzleId, initialBoard);

  const notify = () => {
    onChange?.(state);
  };

  return {
    getState: () => state,

    addMove(
      playerMove: SgfCoord,
      opponentMove: SgfCoord | undefined,
      playerCaptures: readonly SgfCoord[],
      opponentCaptures: readonly SgfCoord[],
      boardStateBefore: PuzzleBoard,
      wasCorrect: boolean
    ): void {
      const entry: Omit<HistoryEntry, 'turn'> = {
        playerMove,
        playerCaptures,
        opponentCaptures,
        boardStateBefore,
        wasCorrect,
        timestamp: Date.now(),
      };
      if (opponentMove !== undefined) {
        entry.opponentMove = opponentMove;
      }
      state = addHistoryEntry(state, entry);
      notify();
    },

    undo(): boolean {
      const newState = undo(state);
      if (newState) {
        state = newState;
        notify();
        return true;
      }
      return false;
    },

    redo(): boolean {
      const newState = redo(state);
      if (newState) {
        state = newState;
        notify();
        return true;
      }
      return false;
    },

    retry(): void {
      state = retry(state);
      notify();
    },

    canUndo: () => canUndo(state),
    canRedo: () => canRedo(state),
    getMoves: () => getCurrentMoves(state),
    getElapsedTime: () => getElapsedTime(state),
    getAttemptCount: () => state.totalAttempts,
  };
}

/**
 * Serialize history state for storage
 *
 * @param state - History state
 * @returns JSON-serializable object
 */
export function serializeHistory(state: HistoryState): object {
  return {
    puzzleId: state.puzzleId,
    entries: state.entries.map((e) => ({
      turn: e.turn,
      playerMove: e.playerMove,
      opponentMove: e.opponentMove,
      playerCaptures: [...e.playerCaptures],
      opponentCaptures: [...e.opponentCaptures],
      wasCorrect: e.wasCorrect,
      timestamp: e.timestamp,
    })),
    currentIndex: state.currentIndex,
    startTime: state.startTime,
    totalAttempts: state.totalAttempts,
  };
}

/**
 * Save current puzzle state (for browser back button handling)
 *
 * @param state - History state
 * @returns Saved state data
 */
export function savePuzzleState(state: HistoryState): string {
  const data = serializeHistory(state);
  return JSON.stringify(data);
}

/**
 * Restore puzzle state from saved data
 *
 * @param json - Saved state JSON
 * @param initialBoard - Initial board state (needs to be reconstructed)
 * @returns Restored history state or null if invalid
 */
export function restorePuzzleState(json: string, initialBoard: PuzzleBoard): HistoryState | null {
  try {
    interface SerializedEntry {
      turn: number;
      playerMove: SgfCoord;
      opponentMove?: SgfCoord;
      playerCaptures: SgfCoord[];
      opponentCaptures: SgfCoord[];
      wasCorrect: boolean;
      timestamp: number;
    }
    interface SerializedHistory {
      puzzleId: string;
      entries: SerializedEntry[];
      currentIndex?: number;
      startTime?: number;
      totalAttempts?: number;
    }

    const data = JSON.parse(json) as SerializedHistory;

    if (!data.puzzleId || !Array.isArray(data.entries)) {
      return null;
    }

    return {
      puzzleId: data.puzzleId,
      entries: data.entries.map((e) => {
        const entry: HistoryEntry = {
          turn: e.turn,
          playerMove: e.playerMove,
          playerCaptures: e.playerCaptures || [],
          opponentCaptures: e.opponentCaptures || [],
          boardStateBefore: initialBoard,
          wasCorrect: e.wasCorrect,
          timestamp: e.timestamp,
        };
        if (e.opponentMove !== undefined) {
          entry.opponentMove = e.opponentMove;
        }
        return entry;
      }),
      currentIndex: data.currentIndex ?? -1,
      initialBoard,
      startTime: data.startTime ?? Date.now(),
      totalAttempts: data.totalAttempts ?? 0,
    };
  } catch {
    return null;
  }
}
