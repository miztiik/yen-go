/**
 * ARIA labels and accessibility helpers for the Go board.
 * @module components/Board/aria
 */

import type { StoneColor } from '../../types/puzzle';
import type { Coordinate } from '../../types/board';

/**
 * Get ARIA label for the board container.
 */
export function getBoardAriaLabel(
  boardSize: number,
  puzzleName?: string
): string {
  const sizeText = `${boardSize} by ${boardSize}`;
  if (puzzleName) {
    return `Go board, ${sizeText} grid, ${puzzleName}`;
  }
  return `Go board, ${sizeText} grid`;
}

/**
 * Get ARIA description for board state.
 */
export function getBoardAriaDescription(
  playerTurn: StoneColor,
  moveNumber: number,
  capturedBlack: number,
  capturedWhite: number
): string {
  const parts: string[] = [];

  if (moveNumber > 0) {
    parts.push(`Move ${moveNumber}`);
  }

  parts.push(`${playerTurn === 'black' ? 'Black' : 'White'} to play`);

  if (capturedBlack > 0 || capturedWhite > 0) {
    parts.push(`Captured: Black ${capturedBlack}, White ${capturedWhite}`);
  }

  return parts.join('. ');
}

/**
 * Convert coordinate to letter-number notation (e.g., "A1", "K10").
 * Skips 'I' to avoid confusion with 'J'.
 */
export function coordinateToNotation(coord: Coordinate, boardSize: number): string {
  // Column letters: A-H, J-T (skip I)
  const letters = 'ABCDEFGHJKLMNOPQRST';
  const col = letters[coord.x] ?? '?';
  // Row numbers: 1 from bottom, so invert
  const row = boardSize - coord.y;
  return `${col}${row}`;
}

/**
 * Get ARIA label for a single intersection.
 */
export function getIntersectionAriaLabel(
  coord: Coordinate,
  boardSize: number,
  stone: StoneColor | null,
  isStarPoint: boolean = false
): string {
  const notation = coordinateToNotation(coord, boardSize);
  const parts: string[] = [notation];

  if (stone) {
    parts.push(`${stone} stone`);
  } else {
    parts.push('empty');
    if (isStarPoint) {
      parts.push('star point');
    }
  }

  return parts.join(', ');
}

/**
 * Get ARIA label for cursor position.
 */
export function getCursorAriaLabel(
  coord: Coordinate,
  boardSize: number,
  stone: StoneColor | null
): string {
  const notation = coordinateToNotation(coord, boardSize);
  if (stone) {
    return `Cursor at ${notation}, ${stone} stone`;
  }
  return `Cursor at ${notation}, empty intersection`;
}

/**
 * ARIA live region announcement types.
 */
export type AnnouncementPriority = 'polite' | 'assertive';

/**
 * Announcement message.
 */
export interface Announcement {
  readonly message: string;
  readonly priority: AnnouncementPriority;
}

/**
 * Create announcement for move made.
 */
export function announceMoveResult(
  coord: Coordinate,
  boardSize: number,
  color: StoneColor,
  isCorrect: boolean,
  capturedCount: number = 0
): Announcement {
  const notation = coordinateToNotation(coord, boardSize);
  let message = `${color} played at ${notation}`;

  if (capturedCount > 0) {
    message += `, captured ${capturedCount} stone${capturedCount > 1 ? 's' : ''}`;
  }

  if (isCorrect) {
    message += '. Correct move!';
  } else {
    message += '. Incorrect move.';
  }

  return {
    message,
    priority: 'assertive',
  };
}

/**
 * Create announcement for puzzle completion.
 */
export function announcePuzzleComplete(
  movesUsed: number,
  hintsUsed: number
): Announcement {
  let message = `Puzzle completed in ${movesUsed} move${movesUsed > 1 ? 's' : ''}`;
  if (hintsUsed > 0) {
    message += ` with ${hintsUsed} hint${hintsUsed > 1 ? 's' : ''}`;
  }
  return {
    message,
    priority: 'assertive',
  };
}

/**
 * Create announcement for hint.
 */
export function announceHint(
  coord: Coordinate,
  boardSize: number,
  hintText?: string
): Announcement {
  const notation = coordinateToNotation(coord, boardSize);
  let message = `Hint: Try ${notation}`;
  if (hintText) {
    message += `. ${hintText}`;
  }
  return {
    message,
    priority: 'polite',
  };
}

/**
 * Create announcement for cursor movement.
 */
export function announceCursorMove(
  coord: Coordinate,
  boardSize: number,
  stone: StoneColor | null
): Announcement {
  const notation = coordinateToNotation(coord, boardSize);
  const status = stone ? `${stone} stone` : 'empty';
  return {
    message: `${notation}, ${status}`,
    priority: 'polite',
  };
}

/**
 * ARIA role attributes for board elements.
 */
export const ARIA_ROLES = {
  board: 'application',
  grid: 'grid',
  row: 'row',
  cell: 'gridcell',
  button: 'button',
  status: 'status',
  alert: 'alert',
  timer: 'timer',
  progressbar: 'progressbar',
} as const;

/**
 * Common ARIA attributes.
 */
export interface AriaAttributes {
  'aria-label'?: string;
  'aria-describedby'?: string;
  'aria-live'?: 'off' | 'polite' | 'assertive';
  'aria-atomic'?: boolean;
  'aria-busy'?: boolean;
  'aria-disabled'?: boolean;
  'aria-hidden'?: boolean;
  'aria-current'?: boolean | 'page' | 'step' | 'location' | 'date' | 'time';
  'aria-pressed'?: boolean | 'mixed';
  'aria-expanded'?: boolean;
  'aria-selected'?: boolean;
  'aria-valuenow'?: number;
  'aria-valuemin'?: number;
  'aria-valuemax'?: number;
  'aria-valuetext'?: string;
  role?: string;
  tabIndex?: number;
}

/**
 * Get ARIA attributes for the board canvas.
 */
export function getBoardCanvasAriaAttributes(
  boardSize: number,
  puzzleName?: string,
  _playerTurn?: StoneColor,
  isInteractive: boolean = true
): AriaAttributes {
  return {
    role: isInteractive ? 'application' : 'img',
    'aria-label': getBoardAriaLabel(boardSize, puzzleName),
    tabIndex: isInteractive ? 0 : -1,
  };
}

/**
 * Get ARIA attributes for control buttons.
 */
export function getControlButtonAriaAttributes(
  label: string,
  isDisabled: boolean = false,
  isPressed?: boolean
): AriaAttributes {
  return {
    role: ARIA_ROLES.button,
    'aria-label': label,
    'aria-disabled': isDisabled,
    ...(isPressed !== undefined && { 'aria-pressed': isPressed }),
    tabIndex: isDisabled ? -1 : 0,
  };
}

/**
 * Get ARIA attributes for timer display.
 */
export function getTimerAriaAttributes(
  timeRemaining: number,
  isRunning: boolean
): AriaAttributes {
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const timeText =
    minutes > 0
      ? `${minutes} minute${minutes > 1 ? 's' : ''} ${seconds} second${seconds !== 1 ? 's' : ''}`
      : `${seconds} second${seconds !== 1 ? 's' : ''}`;

  return {
    role: ARIA_ROLES.timer,
    'aria-label': `Time remaining: ${timeText}`,
    'aria-live': isRunning ? 'off' : 'polite',
  };
}

/**
 * Get ARIA attributes for progress indicator.
 */
export function getProgressAriaAttributes(
  current: number,
  total: number,
  label: string
): AriaAttributes {
  return {
    role: ARIA_ROLES.progressbar,
    'aria-label': label,
    'aria-valuenow': current,
    'aria-valuemin': 0,
    'aria-valuemax': total,
    'aria-valuetext': `${current} of ${total}`,
  };
}

/**
 * ARIA live region manager for announcements.
 */
export class AriaLiveRegion {
  private politeRegion: HTMLElement | null = null;
  private assertiveRegion: HTMLElement | null = null;
  private clearTimeout: number | null = null;

  constructor() {
    this.createRegions();
  }

  private createRegions(): void {
    // Create polite region
    this.politeRegion = document.createElement('div');
    this.politeRegion.setAttribute('aria-live', 'polite');
    this.politeRegion.setAttribute('aria-atomic', 'true');
    this.politeRegion.className = 'sr-only';
    this.politeRegion.id = 'aria-live-polite';

    // Create assertive region
    this.assertiveRegion = document.createElement('div');
    this.assertiveRegion.setAttribute('aria-live', 'assertive');
    this.assertiveRegion.setAttribute('aria-atomic', 'true');
    this.assertiveRegion.className = 'sr-only';
    this.assertiveRegion.id = 'aria-live-assertive';

    // Add to document
    document.body.appendChild(this.politeRegion);
    document.body.appendChild(this.assertiveRegion);
  }

  /**
   * Announce a message to screen readers.
   */
  announce(announcement: Announcement): void {
    const region =
      announcement.priority === 'assertive'
        ? this.assertiveRegion
        : this.politeRegion;

    if (!region) return;

    // Clear any pending timeout
    if (this.clearTimeout !== null) {
      clearTimeout(this.clearTimeout);
    }

    // Set the message
    region.textContent = announcement.message;

    // Clear after delay to allow for repeated announcements
    this.clearTimeout = window.setTimeout(() => {
      if (region) {
        region.textContent = '';
      }
      this.clearTimeout = null;
    }, 3000);
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    if (this.clearTimeout !== null) {
      clearTimeout(this.clearTimeout);
    }
    this.politeRegion?.remove();
    this.assertiveRegion?.remove();
    this.politeRegion = null;
    this.assertiveRegion = null;
  }
}

/**
 * Create ARIA live region manager.
 */
export function createAriaLiveRegion(): AriaLiveRegion {
  return new AriaLiveRegion();
}

/**
 * Screen reader only CSS class (for use with global styles).
 */
export const SR_ONLY_CSS = `
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
`;
