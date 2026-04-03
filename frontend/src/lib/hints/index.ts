/**
 * Hints module exports.
 * @module lib/hints
 */

// Legacy progressive hints (for old puzzle format)
export {
  type HintLevel,
  type HintState,
  type HighlightRegion,
  DEFAULT_HINT_STATE,
} from './progressive';

// SGF-native progressive hints (for InternalPuzzle format)
export {
  type SGFHintLevel,
  type SGFHintState,
  type SGFHighlightRegion,
  DEFAULT_SGF_HINT_STATE,
} from './sgf-progressive';

// SGF hint extraction
export {
  extractHints,
  generateFallbackHint,
  getTechniqueHint,
  getProgressiveHint,
  createHighlightRegion,
  positionToHumanCoord,
  columnToLetter,
} from './sgf-mapper';

// Token resolution for transform-aware hints
export {
  resolveHintTokens,
  hasTokens,
} from './token-resolver';
