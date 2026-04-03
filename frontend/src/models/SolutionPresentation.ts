/**
 * Solution Presentation Types
 * @module models/SolutionPresentation
 *
 * Type definitions for solution presentation features including:
 * - Numbered move display
 * - Animation playback
 * - Explore mode (valid/invalid hints)
 * - Board viewport (auto-crop)
 * - Move collision detection
 * - SGF labels and comments
 *
 * Constitution Compliance:
 * - V. No Browser AI: All data comes from pre-parsed SGF
 * - VI. Type Safety: Strict TypeScript, no 'any' types
 */

// =============================================================================
// Core Types
// =============================================================================

/**
 * @deprecated Use Coord from types/coordinate.ts instead (Besogo 1-indexed).
 * 0-indexed board coordinate - legacy pattern.
 */
export interface Coordinate {
  x: number;
  y: number;
}

/**
 * @deprecated Use Stone from types/board.ts (-1/0/1) for logic.
 * String stone color - kept for legacy display APIs.
 */
export type StoneColor = 'B' | 'W';

/** Presentation mode for solution display */
export type SolutionPresentationMode = 'normal' | 'numbered' | 'animated' | 'explore';

// =============================================================================
// Numbered Move Display
// =============================================================================

/**
 * A move with its sequence number for display on the board.
 */
export interface NumberedMove {
  /** 1-based move number in sequence */
  moveNumber: number;

  /** Board coordinate (0-indexed) */
  coord: Coordinate;

  /** Stone color for this move */
  color: StoneColor;

  /** If collides with earlier move, that move's number (e.g., "5 at 3" → 3) */
  collisionWith: number | null;
}

/**
 * Result of building a numbered move sequence from solution path.
 */
export interface NumberedSequenceResult {
  /** All moves with numbers */
  moves: NumberedMove[];

  /** List of collisions detected (for annotation display) */
  collisions: MoveCollision[];

  /** Count of moves */
  totalMoves: number;
}

/**
 * Collision between moves at the same position.
 */
export interface MoveCollision {
  /** The later move number */
  laterMove: number;

  /** The earlier move it collides with */
  originalMove: number;

  /** Coordinate where collision occurred */
  coord: Coordinate;

  /** Optional reason for collision (e.g., "recapture", "ko") */
  reason?: string;
}

// =============================================================================
// Board Labels (SGF LB[] property)
// =============================================================================

/**
 * Text label at a board position from SGF LB[] property.
 */
export interface BoardLabel {
  /** Board coordinate */
  coord: Coordinate;

  /** Label text (typically A-Z or 1-9, max 3 chars) */
  text: string;
}

// =============================================================================
// Move Comments (SGF C[] property)
// =============================================================================

/**
 * Comment attached to a specific move node.
 */
export interface MoveComment {
  /** Move number in sequence (1-indexed, 0 = root/initial position) */
  moveNumber?: number;

  /** Legacy: Move index in sequence (0 = root/initial position) */
  atMove?: number;

  /** Comment text from SGF C[] property */
  text: string;

  /** Inferred player perspective if detected */
  perspective?: StoneColor | null;
}

// =============================================================================
// Explore Mode
// =============================================================================

/**
 * Hint indicator for explore mode showing valid/invalid next moves.
 */
export interface ExploreHint {
  /** Board coordinate */
  coord: Coordinate;

  /** Whether this leads to correct solution */
  isValid: boolean;

  /** Optional outcome description */
  outcome?: string | undefined;
}

/**
 * State for explore/navigate mode.
 */
export interface ExploreState {
  /** Currently showing explore hints */
  isActive: boolean;

  /** Available hints at current position */
  hints: ExploreHint[];

  /** Path taken so far (move coordinates) */
  currentPath: Coordinate[];
}

/**
 * Extended explore mode state for UI components.
 * Adds convenience properties for the controls component.
 */
export interface ExploreModeState extends ExploreState {
  /** Depth of exploration (number of moves from start) */
  exploreDepth: number;

  /** Whether currently on the main solution path */
  isOnSolutionPath: boolean;
}

// =============================================================================
// Board Viewport (Auto-crop)
// =============================================================================

/**
 * Visible portion of the board for auto-crop display.
 */
export interface BoardViewport {
  /** Min X coordinate (inclusive, 0-indexed) */
  minX: number;

  /** Max X coordinate (inclusive, 0-indexed) */
  maxX: number;

  /** Min Y coordinate (inclusive, 0-indexed) */
  minY: number;

  /** Max Y coordinate (inclusive, 0-indexed) */
  maxY: number;

  /** Width in grid squares */
  width: number;

  /** Height in grid squares */
  height: number;

  /** Whether this is effectively the full board */
  isFullBoard: boolean;
}

/**
 * Calculate grid size from viewport.
 */
export function getViewportGridSize(viewport: BoardViewport): number {
  return Math.max(viewport.maxX - viewport.minX + 1, viewport.maxY - viewport.minY + 1);
}

/**
 * Options for viewport calculation.
 */
export interface ViewportOptions {
  /** Padding around stones (default: 2) */
  padding?: number;

  /** Snap to board edge when close (default: true) */
  snapToEdge?: boolean;

  /** Minimum viewport size in grid squares (default: 7) */
  minSize?: number;

  /** Legacy: margin around stones (alias for padding) */
  margin?: number;

  /** Legacy: edge snap distance (deprecated, use snapToEdge) */
  edgeSnapDistance?: number;

  /** Include solution moves in calculation */
  includeSolutionMoves?: boolean;
}

// =============================================================================
// Animation
// =============================================================================

/**
 * State for solution animation playback.
 */
export interface SolutionAnimationState {
  /** Currently displayed move count (0 = initial position only) */
  currentFrame: number;

  /** Total moves in sequence */
  totalFrames: number;

  /** Is auto-play active */
  isPlaying: boolean;

  /** Delay between moves (ms) */
  delayMs: number;
}

/**
 * Animation control actions.
 */
export interface SolutionAnimationActions {
  /** Start playing */
  play: () => void;

  /** Pause playback */
  pause: () => void;

  /** Reset to beginning */
  reset: () => void;

  /** Go to specific frame */
  goToFrame: (frame: number) => void;

  /** Step forward one frame */
  stepForward: () => void;

  /** Step backward one frame */
  stepBackward: () => void;

  /** Set delay between frames */
  setDelay: (delayMs: number) => void;
}

// =============================================================================
// Configuration
// =============================================================================

/**
 * User preferences for solution presentation.
 */
export interface SolutionPresentationConfig {
  /** Animation delay in ms (500-3000, default 1500) */
  animationDelayMs: number;

  /** Show numbered moves */
  showMoveNumbers: boolean;

  /** Auto-crop to problem area */
  autoCrop: boolean;

  /** Margin for auto-crop (1-5, default 2) */
  cropMargin: number;

  /** Enable colorblind-friendly colors */
  colorblindMode: boolean;

  /** Show explore hints in explore mode */
  showExploreHints: boolean;
}

/**
 * Default presentation configuration.
 */
export const DEFAULT_PRESENTATION_CONFIG: SolutionPresentationConfig = {
  animationDelayMs: 1500,
  showMoveNumbers: true,
  autoCrop: true,
  cropMargin: 2,
  colorblindMode: false,
  showExploreHints: true,
};
