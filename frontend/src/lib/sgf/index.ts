/**
 * SGF library index.
 * @module lib/sgf
 *
 * Provides SGF parsing, type definitions, and coordinate utilities
 * for the YenGo puzzle application.
 */

// Type definitions
export type {
  StandardSGFProperties,
  YenGoSGFProperties,
  SGFProperties,
  SGFNode,
  GameInfo,
  ParsedSGF,
  SGFParseError,
  ISGFParser,
} from './types';

export { isValidPlayer, isSGFProperties } from './types';

// Parser
export { parseSGF, validateSGF, SGFParser, SGFParseErrorImpl, defaultParser } from './parser';

// Coordinate utilities
export {
  sgfToPosition,
  positionToSgf,
  boardPositionToSgf,
  isValidSgfCoord,
  parseSgfCoords,
  positionsToSgf,
  distance,
  areAdjacent,
  getNeighbors,
  getNeighborCoords,
} from './coordinates';

// Solution tree builder
export {
  buildSolutionTree,
  findMove,
  findMoveDeep,
  validatePath,
  validateMove,
  getMainLine,
  getValidFirstMoves,
  countNodes,
  getTreeDepth,
  createWrongMoveNode,
  isLeafNode,
  isCompletingNode,
} from './solution-tree';
