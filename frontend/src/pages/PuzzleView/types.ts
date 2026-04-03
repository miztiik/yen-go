/**
 * PuzzleView Types
 * @module pages/PuzzleView/types
 *
 * Shared types for the PuzzleView module.
 */

import type { BoardRotation } from '../../components/Board/rotation';
import type { BoardRegion } from '../../hooks/useBoardViewport';
import type { LevelSlug } from '../../lib/levels/config';
import type { Puzzle, Coordinate } from '../../types';
import type { SolutionNode } from '../../types/puzzle-internal';
import type { PuzzleBoard } from '../../services/puzzleGameState';
import type { TraversalState } from '../../lib/solver/traversal';
import type { CompletionResult } from '../../lib/solver/completion';
import type { HoverStone } from '../../components/Board/preview';
import type { PuzzleStatus } from '../../components/ProblemNav/ProblemNav';
import type { FeedbackType } from '../../components/Puzzle/FeedbackOverlay';

/** Re-export for backward compatibility */
export type SkillLevel = LevelSlug;

/**
 * Props for PuzzleView page
 */
export interface PuzzleViewProps {
  /** Puzzle to solve */
  puzzle: Puzzle;
  /** Puzzle ID (for tracking) */
  puzzleId: string;
  /** Skill level of the puzzle (1-5) */
  skillLevel?: SkillLevel;
  /** Callback when puzzle is completed */
  onComplete?: (result: CompletionResult) => void;
  /** Callback for next puzzle */
  onNextPuzzle?: () => void;
  /** Callback for previous puzzle */
  onPrevPuzzle?: () => void;
  /** Callback for going back */
  onBack?: () => void;
  /** Optional initial state (for restoring from history) */
  initialState?: {
    moves: string[];
    wrongAttempts: number;
  };
  /** Puzzle set navigation props (for ProblemNav) */
  puzzleSetNavigation?: {
    /** Total number of puzzles in set */
    totalPuzzles: number;
    /** Current puzzle index (0-based) */
    currentIndex: number;
    /** Status of each puzzle in set */
    statuses: PuzzleStatus[];
    /** Navigate to specific puzzle by index */
    onNavigate: (index: number) => void;
  };
  /** Daily challenge technique of the day */
  techniqueOfDay?: string;
  /** Whether to show the elapsed time timer (default: false for standard mode) */
  showTimer?: boolean;
  /** Auto-advance to next puzzle on success/failure (default: true) */
  autoAdvance?: boolean;
  /** Delay before auto-advancing in ms (default: 1500, recommended 1-2 seconds) */
  autoAdvanceDelay?: number;
  /** Board region for partial viewport (e.g., 'top-left', 'bottom-right') */
  boardRegion?: BoardRegion;
}

/**
 * Solution node type with optional comment
 */
export interface SolutionNodeWithComment {
  move: string;
  isCorrect?: boolean;
  comment?: string;
  children: SolutionNodeWithComment[];
}

/**
 * Game state managed by useGameState hook
 */
export interface GameState {
  boardState: PuzzleBoard;
  traversalState: TraversalState;
  lastMove: Coordinate | null;
  hoverStone: HoverStone | null;
  showSuccess: boolean;
  showFailure: boolean;
  completionResult: CompletionResult | null;
  hintsUsed: number;
  elapsedTime: number;
  alreadyCompleted: boolean;
  feedback: { type: FeedbackType; message: string } | null;
  boardRotation: BoardRotation;
  currentPath: string[];
  exploredNodes: Set<string>;
  revealFullTree: boolean;
  isMobileView: boolean;
}

/**
 * Game actions returned by useGameState hook
 */
export interface GameActions {
  handleIntersectionClick: (coord: Coordinate) => void;
  handleIntersectionHover: (coord: Coordinate | null) => void;
  handleUndo: () => void;
  handleRetry: () => void;
  handleRotate: () => void;
  handleHint: () => void;
  handleTreeNodeClick: (nodeId: string) => void;
  handleTreeNodeSelect: (treeNodeId: string, node: SolutionNode) => void;
  handlePrevPuzzle: () => void;
  handleNextPuzzle: () => void;
  setFeedback: (feedback: { type: FeedbackType; message: string } | null) => void;
  setShowSuccess: (show: boolean) => void;
  setShowFailure: (show: boolean) => void;
  setRevealFullTree: (reveal: boolean) => void;
}

/**
 * Current node info from solution tree
 */
export interface CurrentNodeInfo {
  comment: string | null;
  isCorrect: boolean;
  move: string;
  moveNumber: number;
}
