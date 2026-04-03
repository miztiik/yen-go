/**
 * Board Overlay Component
 * @module components/Board/BoardOverlay
 *
 * Renders overlays on the Go board including:
 * - Numbered moves (FR-001, FR-002)
 * - Board labels from SGF LB[] (FR-019, FR-020)
 * - Explore mode hints (FR-007, FR-008)
 *
 * NOTE: This component renders HTML elements positioned over a Canvas board.
 * It must be given the same dimensions as the Board component uses internally.
 * Use the exported BoardOverlayContainer to wrap Board and get automatic sizing.
 *
 * Constitution Compliance:
 * - IX. Accessibility: Uses high contrast, colorblind-safe options
 * - X. Design Philosophy: Minimalist, non-intrusive overlays
 */

import type { JSX } from 'preact';
import type {
  NumberedMove,
  BoardLabel,
  ExploreHint,
  BoardViewport,
  Coordinate,
} from '@models/SolutionPresentation';

/**
 * Props for BoardOverlay component.
 */
export interface BoardOverlayProps {
  /** Board size (9, 13, or 19) */
  boardSize: number;
  /** Cell size in pixels */
  cellSize: number;
  /** X offset for board positioning */
  offsetX: number;
  /** Y offset for board positioning */
  offsetY: number;
  /** Numbered moves to display */
  numberedMoves?: readonly NumberedMove[];
  /** Labels from SGF LB[] property */
  labels?: readonly BoardLabel[];
  /** Explore mode hints */
  exploreHints?: readonly ExploreHint[];
  /** Stone positions (for hiding labels under stones) */
  stonePositions?: ReadonlySet<string>;
  /** Optional viewport for coordinate transformation */
  viewport?: BoardViewport;
  /** Whether colorblind mode is enabled */
  colorblindMode?: boolean;
}

/**
 * Convert coordinate to pixel position.
 */
function coordToPixel(
  coord: Coordinate,
  cellSize: number,
  offsetX: number,
  offsetY: number,
  viewport?: BoardViewport
): { x: number; y: number } {
  let x = coord.x;
  let y = coord.y;

  // Apply viewport transformation if present
  if (viewport && !viewport.isFullBoard) {
    x = coord.x - viewport.minX;
    y = coord.y - viewport.minY;
  }

  return {
    x: offsetX + x * cellSize,
    y: offsetY + y * cellSize,
  };
}

/**
 * Create key for coordinate lookup.
 */
function coordKey(coord: Coordinate): string {
  return `${coord.x},${coord.y}`;
}

/**
 * NumberedMoveOverlay - Renders move numbers on stones.
 */
function NumberedMoveOverlay({
  move,
  cellSize,
  offsetX,
  offsetY,
  viewport,
}: {
  move: NumberedMove;
  cellSize: number;
  offsetX: number;
  offsetY: number;
  viewport: BoardViewport | undefined;
}): JSX.Element {
  const { x, y } = coordToPixel(move.coord, cellSize, offsetX, offsetY, viewport);
  const fontSize = Math.max(10, cellSize * 0.5);
  const textColor = move.color === 'B' ? '#ffffff' : '#000000';

  return (
    <div
      className="board-overlay__number"
      style={{
        position: 'absolute',
        left: `${x}px`,
        top: `${y}px`,
        transform: 'translate(-50%, -50%)',
        fontSize: `${fontSize}px`,
        fontWeight: 600,
        color: textColor,
        pointerEvents: 'none',
        userSelect: 'none',
        textShadow: move.color === 'B'
          ? '0 0 2px rgba(0,0,0,0.5)'
          : '0 0 2px rgba(255,255,255,0.5)',
      }}
      aria-label={`Move ${move.moveNumber}${move.collisionWith ? ` at ${move.collisionWith}` : ''}`}
    >
      {move.moveNumber}
    </div>
  );
}

/**
 * LabelOverlay - Renders SGF labels on the board.
 */
function LabelOverlay({
  label,
  cellSize,
  offsetX,
  offsetY,
  viewport,
  isHidden,
}: {
  label: BoardLabel;
  cellSize: number;
  offsetX: number;
  offsetY: number;
  viewport: BoardViewport | undefined;
  isHidden: boolean;
}): JSX.Element | null {
  if (isHidden) {
    return null;
  }

  const { x, y } = coordToPixel(label.coord, cellSize, offsetX, offsetY, viewport);
  const fontSize = Math.max(8, cellSize * 0.4);

  return (
    <div
      className="board-overlay__label"
      style={{
        position: 'absolute',
        left: `${x}px`,
        top: `${y}px`,
        transform: 'translate(-50%, -50%)',
        fontSize: `${fontSize}px`,
        fontWeight: 500,
        color: 'var(--color-label-text, #1f2937)',
        backgroundColor: 'var(--color-label-bg, rgba(255, 255, 255, 0.9))',
        padding: '2px 4px',
        borderRadius: '2px',
        pointerEvents: 'none',
        userSelect: 'none',
        maxWidth: `${cellSize * 1.5}px`,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}
      aria-label={`Label ${label.text}`}
    >
      {label.text.substring(0, 3)}
    </div>
  );
}

/**
 * ExploreHintOverlay - Renders valid/invalid move hints.
 */
function ExploreHintOverlay({
  hint,
  cellSize,
  offsetX,
  offsetY,
  viewport,
  colorblindMode,
}: {
  hint: ExploreHint;
  cellSize: number;
  offsetX: number;
  offsetY: number;
  viewport: BoardViewport | undefined;
  colorblindMode: boolean;
}): JSX.Element {
  const { x, y } = coordToPixel(hint.coord, cellSize, offsetX, offsetY, viewport);
  const size = Math.max(8, cellSize * 0.3);

  // Use CSS variables for colors (supports colorblind mode)
  const colorVar = hint.isValid
    ? 'var(--color-valid-move, #22c55e)'
    : 'var(--color-invalid-move, #dc2626)';
  const bgColorVar = hint.isValid
    ? 'var(--color-valid-move-bg, rgba(34, 197, 94, 0.3))'
    : 'var(--color-invalid-move-bg, rgba(220, 38, 38, 0.3))';

  // In colorblind mode, also add shape indicator
  const shape = hint.isValid ? '●' : '✕';

  return (
    <div
      className={`board-overlay__hint board-overlay__hint--${hint.isValid ? 'valid' : 'invalid'}`}
      style={{
        position: 'absolute',
        left: `${x}px`,
        top: `${y}px`,
        transform: 'translate(-50%, -50%)',
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: hint.isValid ? '50%' : '2px',
        backgroundColor: colorVar,
        boxShadow: `0 0 ${size / 2}px ${bgColorVar}`,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: `${size * 0.7}px`,
        color: '#fff',
      }}
      aria-label={hint.isValid ? 'Valid move' : 'Invalid move'}
      title={hint.outcome}
    >
      {colorblindMode && <span aria-hidden="true">{shape}</span>}
    </div>
  );
}

/**
 * BoardOverlay component - renders all overlay elements on the board.
 */
export function BoardOverlay({
  boardSize: _boardSize,
  cellSize,
  offsetX,
  offsetY,
  numberedMoves = [],
  labels = [],
  exploreHints = [],
  stonePositions = new Set(),
  viewport,
  colorblindMode = false,
}: BoardOverlayProps): JSX.Element {
  return (
    <div
      className="board-overlay"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
      }}
      aria-hidden="true"
    >
      {/* Explore hints (render first, under other overlays) */}
      {exploreHints.map((hint) => (
        <ExploreHintOverlay
          key={`hint-${hint.coord.x}-${hint.coord.y}`}
          hint={hint}
          cellSize={cellSize}
          offsetX={offsetX}
          offsetY={offsetY}
          viewport={viewport}
          colorblindMode={colorblindMode}
        />
      ))}

      {/* Labels (hidden when stone is placed - FR-020) */}
      {labels.map((label) => (
        <LabelOverlay
          key={`label-${label.coord.x}-${label.coord.y}`}
          label={label}
          cellSize={cellSize}
          offsetX={offsetX}
          offsetY={offsetY}
          viewport={viewport}
          isHidden={stonePositions.has(coordKey(label.coord))}
        />
      ))}

      {/* Numbered moves (render on top) */}
      {numberedMoves.map((move) => (
        <NumberedMoveOverlay
          key={`num-${move.moveNumber}`}
          move={move}
          cellSize={cellSize}
          offsetX={offsetX}
          offsetY={offsetY}
          viewport={viewport}
        />
      ))}
    </div>
  );
}

export default BoardOverlay;
