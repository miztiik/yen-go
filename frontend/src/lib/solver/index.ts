/**
 * Solver library index.
 */

// Parser
export {
  parseSolution,
  parseLine,
  isCorrectFirstMove,
  getResponses,
  matchesHistory,
  getMatchingLines,
  isSolutionComplete,
  getRemainingMoves,
  validateSolutionStructure,
  type SolutionMove,
  type SolutionLine,
  type ParsedSolution,
} from './parser';

// Traversal
export {
  createTraversal,
  checkMove,
  getHint,
  getCorrectFirstMoves,
  getSolution,
  resetTraversal,
  undoMove,
  getProgress,
  isOnCorrectPath,
  getValidContinuations,
  type MoveCheckResult,
  type TraversalState,
} from './traversal';
