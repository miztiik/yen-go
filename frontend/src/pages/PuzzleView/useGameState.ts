/**
 * useGameState Hook
 * @module pages/PuzzleView/useGameState
 *
 * Manages all game state and logic for puzzle solving.
 * Extracted from PuzzleView.tsx for better separation of concerns.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'preact/hooks';
import type { Puzzle, Coordinate, BoardSize } from '../../types';
import { EMPTY } from '../../types/board';
import type { SolutionNode } from '../../types/puzzle-internal';
import type { BoardRotation } from '../../components/Board/rotation';
import type { FeedbackType } from '../../components/Puzzle/FeedbackOverlay';
import type { LevelSlug } from '../../lib/levels/config';

import { createPuzzleBoardFromData, executePuzzleMove, getDisplayStones, type PuzzleBoard } from '../../services/puzzleGameState';
import { isMoveLegal, isSelfAtari } from '../../services/boardAnalysis';
import { SHOW_SELF_ATARI_WARNING, SELF_ATARI_WARNING_HIDDEN_ABOVE } from '../../services/featureFlags';
import { createTraversal, checkMove, type TraversalState } from '../../lib/solver/traversal';
import { getCompletionResult, isPuzzleComplete, isPuzzleFailed, type CompletionResult } from '../../lib/solver/completion';
import { createHistoryManager } from '../../lib/solver/history';
import { shouldEnablePreview, type HoverStone } from '../../components/Board/preview';
import { sgfToPosition, positionToSgf } from '../../lib/sgf/coordinates';
import {
  getProgressStorage,
  loadAndRecoverProgress,
  recordCompletion,
  updateStatisticsAfterCompletion,
  isPuzzleCompleted,
  PuzzleTimer,
  type CompletionData,
} from '../../lib/progress';
import { buildSolutionTreeFromSequences } from '../../lib/sgf/solution-tree';
import { playStoneSound, playErrorSound, playCompletionSound } from '../../utils/sound';
import { sideToColor, findPathToNode, pathToTreeNodeId } from './utils';

export interface UseGameStateProps {
  puzzle: Puzzle;
  puzzleId: string;
  skillLevel: LevelSlug;
  onComplete?: (result: CompletionResult) => void;
  onNextPuzzle?: () => void;
  onPrevPuzzle?: () => void;
  autoAdvance?: boolean;
  autoAdvanceDelay?: number;
}

export interface UseGameStateReturn {
  // Board state
  boardSize: BoardSize;
  stones: import('../../types').Stone[][];
  currentColor: 'black' | 'white';
  isPlayerTurn: boolean;
  enableHover: boolean;
  boardState: PuzzleBoard;
  lastMove: Coordinate | null;
  hoverStone: HoverStone | null;
  boardRotation: BoardRotation;
  
  // Game state
  traversalState: TraversalState;
  showSuccess: boolean;
  showFailure: boolean;
  completionResult: CompletionResult | null;
  hintsUsed: number;
  hintsRemaining: number;
  currentHintText: string | null;
  elapsedTime: number;
  alreadyCompleted: boolean;
  feedback: { type: FeedbackType; message: string } | null;
  
  // Solution tree
  solutionTree: SolutionNode;
  currentPath: string[];
  currentNodeId: string;
  currentNodeInfo: { comment: string | null; isCorrect: boolean; move: string; moveNumber: number } | null;
  
  // Layout
  isMobileView: boolean;
  
  // History
  historyManager: ReturnType<typeof createHistoryManager>;
  
  // Actions
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
  // Explore mode (shows tree with correctness indicators)
  isExploreMode: boolean;
  toggleExploreMode: () => void;
}

/**
 * Hook that manages all game state for PuzzleView
 */
export function useGameState({
  puzzle,
  puzzleId,
  skillLevel,
  onComplete,
  onNextPuzzle,
  onPrevPuzzle,
  autoAdvance = true,
  autoAdvanceDelay = 1500,
}: UseGameStateProps): UseGameStateReturn {
  // Determine board size from puzzle region
  const boardSize = puzzle.region.w as BoardSize;

  // Initialize board state from puzzle
  const initialBoard = useMemo(
    () => createPuzzleBoardFromData(boardSize, puzzle.B ?? [], puzzle.W ?? [], puzzle.side),
    [puzzle, boardSize]
  );

  // Initialize traversal state
  const initialTraversal = useMemo(
    () => createTraversal(puzzle.sol, puzzle.side),
    [puzzle]
  );

  // Convert solution sequences to SolutionNode tree for visualization
  const solutionTree = useMemo(
    () => buildSolutionTreeFromSequences(puzzle.sol, puzzle.side),
    [puzzle.sol, puzzle.side]
  );

  // State
  const [boardState, setBoardState] = useState<PuzzleBoard>(initialBoard);
  const [traversalState, setTraversalState] = useState<TraversalState>(initialTraversal);
  const [lastMove, setLastMove] = useState<Coordinate | null>(null);
  const [hoverStone, setHoverStone] = useState<HoverStone | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);
  const [showFailure, setShowFailure] = useState(false);
  const [completionResult, setCompletionResult] = useState<CompletionResult | null>(null);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [alreadyCompleted, setAlreadyCompleted] = useState(false);
  const [feedback, setFeedback] = useState<{ type: FeedbackType; message: string } | null>(null);
  const [boardRotation, setBoardRotation] = useState<BoardRotation>(() => {
    const saved = localStorage.getItem('yen-go:settings:v1');
    if (saved) {
      try {
        const settings = JSON.parse(saved) as { boardRotation?: BoardRotation };
        return settings.boardRotation ?? 0;
      } catch {
        return 0;
      }
    }
    return 0;
  });
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [, setExploredNodes] = useState<Set<string>>(() => new Set());
  const [, setRevealFullTree] = useState(false);
  const [isExploreMode, setIsExploreMode] = useState(false);
  const [isMobileView, setIsMobileView] = useState(() => 
    typeof window !== 'undefined' && window.innerWidth < 768
  );

  // Refs
  const timerRef = useRef<PuzzleTimer | null>(null);

  // Derived values
  const currentNodeId = useMemo(
    () => pathToTreeNodeId(solutionTree, currentPath),
    [solutionTree, currentPath]
  );

  const stones = useMemo(
    () => getDisplayStones(boardState),
    [boardState]
  );

  const currentColor = sideToColor(boardState.sideToMove);
  const isPlayerTurn = boardState.sideToMove === puzzle.side;
  const enableHover = shouldEnablePreview();

  const hasActualHint = !!puzzle.hint;
  const hintsRemaining = hasActualHint ? Math.max(0, 1 - hintsUsed) : 0;

  const currentHintText = useMemo(() => {
    if (hintsUsed === 0) return null;
    if (puzzle.hint) return puzzle.hint;
    return 'Look at the vital points on the board.';
  }, [puzzle.hint, hintsUsed]);

  // Get current node info for CommentPanel
  const currentNodeInfo = useMemo(() => {
    if (currentPath.length === 0) return null;
    
    let current = solutionTree as { move: string; comment?: string; isCorrect?: boolean; children: SolutionNode[] };
    let lastNodeMove = '';
    for (const pathId of currentPath) {
      const [, move] = pathId.split('-');
      const child = current.children.find(c => c.move === move);
      if (!child) return null;
      current = child;
      lastNodeMove = move ?? '';
    }

    return {
      comment: current.comment ?? null,
      isCorrect: current.isCorrect !== false,
      move: lastNodeMove,
      moveNumber: currentPath.length,
    };
  }, [solutionTree, currentPath]);

  // History manager
  const historyManager = useMemo(
    () => createHistoryManager(puzzleId, initialBoard),
    [puzzleId, initialBoard]
  );

  // Effects
  useEffect(() => {
    const handleResize = () => {
      setIsMobileView(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!autoAdvance || !onNextPuzzle) return;
    
    if (showSuccess || showFailure) {
      const timer = setTimeout(() => {
        onNextPuzzle();
      }, autoAdvanceDelay);
      return () => clearTimeout(timer);
    }
  }, [showSuccess, showFailure, autoAdvance, autoAdvanceDelay, onNextPuzzle]);

  useEffect(() => {
    const storage = getProgressStorage();
    const result = loadAndRecoverProgress(() => storage.getRaw());
    if (result.data && isPuzzleCompleted(result.data, puzzleId)) {
      setAlreadyCompleted(true);
    }

    timerRef.current = new PuzzleTimer(puzzleId);
    const unsubscribe = timerRef.current.onTick((elapsed) => {
      setElapsedTime(elapsed);
    }, 1000);

    return () => {
      unsubscribe();
      timerRef.current?.dispose();
    };
  }, [puzzleId]);

  // Save completion helper
  const saveCompletion = useCallback(
    (timeTaken: number, wrongAttempts: number) => {
      const storage = getProgressStorage();
      const loadResult = loadAndRecoverProgress(() => storage.getRaw());
      if (!loadResult.data) return;

      let progress = loadResult.data;

      const completionData: CompletionData = {
        puzzleId,
        timeSpentMs: timeTaken,
        attempts: wrongAttempts,
        hintsUsed,
        skillLevel,
      };

      progress = recordCompletion(progress, completionData);

      const puzzleCompletion = progress.completedPuzzles[puzzleId];
      if (puzzleCompletion) {
        progress = updateStatisticsAfterCompletion(progress, puzzleCompletion);
      }

      storage.set(progress);
    },
    [puzzleId, hintsUsed, skillLevel]
  );

  // Handlers
  const handleIntersectionClick = useCallback(
    (coord: Coordinate) => {
      if (!isPlayerTurn) return;

      const sgfCoord = positionToSgf(coord.x, coord.y);
      if (!sgfCoord) return;

      const { result, newState } = checkMove(traversalState, sgfCoord);

      if (!result.correct) {
        setTraversalState(newState);
        
        const wrongMoveDepth = currentPath.length;
        const wrongMoveId = `${wrongMoveDepth}-${sgfCoord}`;
        setCurrentPath((prev) => [...prev, wrongMoveId]);
        setExploredNodes((prev) => new Set([...prev, wrongMoveId]));

        playErrorSound();
        setFeedback({ type: 'incorrect', message: 'Incorrect' });

        if (isPuzzleFailed(newState)) {
          const timeTaken = timerRef.current?.stop() ?? 0;
          const compResult = getCompletionResult(newState, undefined, timeTaken, hintsUsed);
          setCompletionResult(compResult);
          setShowFailure(true);
          setFeedback(null);
        }
        return;
      }

      setFeedback({ type: 'correct', message: 'Correct! Keep going.' });

      const moveResult = executePuzzleMove(boardState, sgfCoord);
      if (!moveResult.success || !moveResult.newBoard) return;

      let newBoardState = moveResult.newBoard;
      setLastMove(coord);

      const moveDepth = currentPath.length;
      const moveId = `${moveDepth}-${sgfCoord}`;
      setCurrentPath((prev) => [...prev, moveId]);
      setExploredNodes((prev) => new Set([...prev, moveId]));

      historyManager.addMove(
        sgfCoord,
        result.response,
        moveResult.captures ?? [],
        [],
        boardState,
        true
      );

      if (result.response) {
        const opponentResult = executePuzzleMove(newBoardState, result.response);
        if (opponentResult.success && opponentResult.newBoard) {
          newBoardState = opponentResult.newBoard;
          const responsePos = sgfToPosition(result.response);
          if (responsePos) {
            setLastMove(responsePos);
          }
          const responseDepth = currentPath.length + 1;
          const responseId = `${responseDepth}-${result.response}`;
          setCurrentPath((prev) => [...prev, responseId]);
          setExploredNodes((prev) => new Set([...prev, responseId]));
        }
      }

      setBoardState(newBoardState);
      setTraversalState(newState);

      if (result.isComplete || isPuzzleComplete(newState)) {
        const timeTaken = timerRef.current?.stop() ?? 0;
        const compResult = getCompletionResult(newState, undefined, timeTaken, hintsUsed);
        setCompletionResult(compResult);
        
        playCompletionSound();
        setShowSuccess(true);

        if (!alreadyCompleted) {
          saveCompletion(timeTaken, newState.wrongAttempts);
        }

        onComplete?.(compResult);
      } else {
        playStoneSound();
      }
    },
    [
      boardState,
      traversalState,
      isPlayerTurn,
      hintsUsed,
      historyManager,
      onComplete,
      alreadyCompleted,
      saveCompletion,
      currentPath,
    ]
  );

  const handleIntersectionHover = useCallback(
    (coord: Coordinate | null) => {
      if (!enableHover || !isPlayerTurn) {
        setHoverStone(null);
        return;
      }

      // Besogo pattern: EMPTY = 0, check for empty intersection
      if (coord && stones[coord.y]?.[coord.x] === EMPTY) {
        // Block hover on illegal moves (suicide, ko)
        // Besogo convention: BLACK = -1, WHITE = 1
        const numericColor = currentColor === 'black' ? -1 : 1;
        if (!isMoveLegal(boardState.grid, { x: coord.x + 1, y: coord.y + 1 }, numericColor, boardSize, boardState.koState)) {
          setHoverStone(null);
          return;
        }

        // Check self-atari for warning display
        let selfAtari = false;
        if (SHOW_SELF_ATARI_WARNING) {
          const hiddenAboveIdx = ['novice', 'beginner', 'elementary', 'intermediate', 'upper-intermediate', 'advanced', 'low-dan', 'high-dan', 'expert'].indexOf(SELF_ATARI_WARNING_HIDDEN_ABOVE);
          const skillIdx = ['novice', 'beginner', 'elementary', 'intermediate', 'upper-intermediate', 'advanced', 'low-dan', 'high-dan', 'expert'].indexOf(skillLevel);
          const showWarning = hiddenAboveIdx < 0 || skillIdx <= hiddenAboveIdx;
          if (showWarning) {
            selfAtari = isSelfAtari(boardState.grid, { x: coord.x + 1, y: coord.y + 1 }, numericColor, boardSize);
          }
        }

        setHoverStone(selfAtari ? { coord, color: currentColor, isSelfAtari: true } : { coord, color: currentColor });
      } else {
        setHoverStone(null);
      }
    },
    [enableHover, isPlayerTurn, currentColor, stones, boardState, skillLevel]
  );

  const handleUndo = useCallback(() => {
    if (!historyManager.canUndo()) return;

    historyManager.undo();
    setBoardState(initialBoard);
    setTraversalState(initialTraversal);
    setLastMove(null);
    setCurrentPath((prev) => prev.slice(0, -1));
  }, [historyManager, initialBoard, initialTraversal]);

  const handleRetry = useCallback(() => {
    setBoardState(initialBoard);
    setTraversalState(initialTraversal);
    setLastMove(null);
    setHoverStone(null);
    setShowSuccess(false);
    setShowFailure(false);
    setCompletionResult(null);
    setCurrentPath([]);
    setExploredNodes(new Set());
    setRevealFullTree(false);
    setIsExploreMode(false);
    setFeedback(null);
    historyManager.retry();
  }, [initialBoard, initialTraversal, historyManager]);

  const handleRotate = useCallback(() => {
    setBoardRotation((prev) => {
      const newRotation = ((prev + 90) % 360) as BoardRotation;
      try {
        const saved = localStorage.getItem('yen-go:settings:v1');
        const settings = saved ? JSON.parse(saved) : {};
        settings.boardRotation = newRotation;
        localStorage.setItem('yen-go:settings:v1', JSON.stringify(settings));
      } catch {
        // Ignore storage errors
      }
      return newRotation;
    });
  }, []);

  const handleHint = useCallback(() => {
    if (puzzle.hint && hintsUsed < 1) {
      setHintsUsed((prev) => prev + 1);
    }
  }, [puzzle.hint, hintsUsed]);

  const handleTreeNodeClick = useCallback((nodeId: string) => {
    const movesPath = findPathToNode(solutionTree, nodeId);
    
    if (!movesPath) {
      console.warn('Could not find path to node:', nodeId);
      return;
    }

    let newBoardState = initialBoard;
    const newPath: string[] = [];
    
    for (let i = 0; i < movesPath.length; i++) {
      const move = movesPath[i];
      if (!move) continue;
      
      const moveResult = executePuzzleMove(newBoardState, move);
      if (moveResult.success && moveResult.newBoard) {
        newBoardState = moveResult.newBoard;
        const moveNodeId = `${i + 1}-${move}`;
        newPath.push(moveNodeId);
      }
    }

    setBoardState(newBoardState);
    setCurrentPath(newPath);
    
    if (movesPath.length > 0) {
      const lastMoveCoord = movesPath[movesPath.length - 1];
      if (lastMoveCoord) {
        const pos = sgfToPosition(lastMoveCoord);
        if (pos) {
          setLastMove({ x: pos.x, y: pos.y });
        }
      }
    } else {
      setLastMove(null);
    }
    
    setTraversalState({
      ...initialTraversal,
      history: movesPath,
      complete: false,
      wrongAttempts: traversalState.wrongAttempts,
    });
  }, [solutionTree, initialBoard, initialTraversal, traversalState.wrongAttempts]);

  const handleTreeNodeSelect = useCallback((_treeNodeId: string, node: SolutionNode) => {
    const collectMovesToNode = (
      root: SolutionNode, 
      targetMove: string, 
      parentPath: string[] = []
    ): string[] | null => {
      if (root.move === targetMove) {
        return [...parentPath, root.move].filter(m => m !== '');
      }
      
      for (const child of root.children) {
        const foundResult = collectMovesToNode(
          child, 
          targetMove, 
          root.move ? [...parentPath, root.move] : parentPath
        );
        if (foundResult) return foundResult;
      }
      
      return null;
    };

    const movesPath = collectMovesToNode(solutionTree, node.move) ?? [];

    let newBoardState = initialBoard;
    const newPath: string[] = [];
    
    for (let i = 0; i < movesPath.length; i++) {
      const move = movesPath[i];
      if (!move) continue;
      
      const moveResult = executePuzzleMove(newBoardState, move);
      if (moveResult.success && moveResult.newBoard) {
        newBoardState = moveResult.newBoard;
        const moveNodeId = `${i + 1}-${move}`;
        newPath.push(moveNodeId);
      }
    }

    setBoardState(newBoardState);
    setCurrentPath(newPath);
    
    if (movesPath.length > 0) {
      const lastMoveCoord = movesPath[movesPath.length - 1];
      if (lastMoveCoord) {
        const pos = sgfToPosition(lastMoveCoord);
        if (pos) {
          setLastMove({ x: pos.x, y: pos.y });
        }
      }
    } else {
      setLastMove(null);
    }
    
    setTraversalState({
      ...initialTraversal,
      history: movesPath,
      complete: false,
      wrongAttempts: traversalState.wrongAttempts,
    });
  }, [solutionTree, initialBoard, initialTraversal, traversalState.wrongAttempts]);

  const handlePrevPuzzle = useCallback(() => {
    onPrevPuzzle?.();
  }, [onPrevPuzzle]);

  const handleNextPuzzle = useCallback(() => {
    onNextPuzzle?.();
  }, [onNextPuzzle]);

  return {
    // Board state
    boardSize,
    stones,
    currentColor,
    isPlayerTurn,
    enableHover,
    boardState,
    lastMove,
    hoverStone,
    boardRotation,
    
    // Game state
    traversalState,
    showSuccess,
    showFailure,
    completionResult,
    hintsUsed,
    hintsRemaining,
    currentHintText,
    elapsedTime,
    alreadyCompleted,
    feedback,
    
    // Solution tree
    solutionTree,
    currentPath,
    currentNodeId,
    currentNodeInfo,
    
    // Layout
    isMobileView,
    
    // History
    historyManager,
    
    // Actions
    handleIntersectionClick,
    handleIntersectionHover,
    handleUndo,
    handleRetry,
    handleRotate,
    handleHint,
    handleTreeNodeClick,
    handleTreeNodeSelect,
    handlePrevPuzzle,
    handleNextPuzzle,
    setFeedback,
    setShowSuccess,
    setShowFailure,
    setRevealFullTree,
    // Explore mode
    isExploreMode,
    toggleExploreMode: useCallback(() => setIsExploreMode(prev => !prev), []),
  };
}
