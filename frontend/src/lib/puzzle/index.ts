/**
 * Puzzle library index.
 */

export {
  PuzzleLoader,
  getDefaultLoader,
  loadPuzzle,
  loadPuzzles,
  type LoadResult,
  type LoaderConfig,
} from './loader';

export { extractPuzzleIdFromPath, extractLevelFromPath } from './utils';
