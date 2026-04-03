/**
 * Keyboard navigation for the Go board.
 * Enables arrow key navigation and keyboard shortcuts.
 * @module components/Board/keyboard
 */

import type { Coordinate } from '../../types/puzzle';

/**
 * Keyboard navigation state.
 */
export interface KeyboardNavState {
  /** Whether keyboard navigation is active */
  readonly isActive: boolean;
  /** Current cursor position */
  readonly cursor: Coordinate;
  /** Whether cursor is visible */
  readonly cursorVisible: boolean;
}

/**
 * Create initial keyboard navigation state.
 */
export function createKeyboardNavState(boardSize: number = 19): KeyboardNavState {
  // Start cursor at center of board
  const center = Math.floor(boardSize / 2);
  return {
    isActive: false,
    cursor: { row: center, col: center },
    cursorVisible: false,
  };
}

/**
 * Keyboard shortcut configuration.
 */
export interface KeyboardConfig {
  /** Keys for moving up */
  readonly upKeys: string[];
  /** Keys for moving down */
  readonly downKeys: string[];
  /** Keys for moving left */
  readonly leftKeys: string[];
  /** Keys for moving right */
  readonly rightKeys: string[];
  /** Keys for placing a stone */
  readonly placeKeys: string[];
  /** Keys for passing */
  readonly passKeys: string[];
  /** Keys for undoing */
  readonly undoKeys: string[];
  /** Keys for getting a hint */
  readonly hintKeys: string[];
  /** Keys for toggling solution */
  readonly solutionKeys: string[];
  /** Enable vi-style keys (hjkl) */
  readonly enableViKeys: boolean;
  /** Enable number keys for quick position */
  readonly enableNumberKeys: boolean;
}

/**
 * Default keyboard configuration.
 */
export const DEFAULT_KEYBOARD_CONFIG: KeyboardConfig = {
  upKeys: ['ArrowUp', 'w', 'W', 'k'],
  downKeys: ['ArrowDown', 's', 'S', 'j'],
  leftKeys: ['ArrowLeft', 'a', 'A', 'h'],
  rightKeys: ['ArrowRight', 'd', 'D', 'l'],
  placeKeys: ['Enter', ' '],
  passKeys: ['p', 'P'],
  undoKeys: ['z', 'Z', 'Backspace'],
  hintKeys: ['?', '/'],
  solutionKeys: ['s', 'S'],
  enableViKeys: true,
  enableNumberKeys: true,
};

/**
 * Keyboard action types.
 */
export type KeyboardAction =
  | { type: 'move'; direction: 'up' | 'down' | 'left' | 'right' }
  | { type: 'place'; coordinate: Coordinate }
  | { type: 'pass' }
  | { type: 'undo' }
  | { type: 'hint' }
  | { type: 'solution' }
  | { type: 'activate' }
  | { type: 'deactivate' }
  | { type: 'jump'; coordinate: Coordinate }
  | { type: 'none' };

/**
 * Parse keyboard event to action.
 */
export function parseKeyboardEvent(
  event: KeyboardEvent,
  config: KeyboardConfig = DEFAULT_KEYBOARD_CONFIG
): KeyboardAction {
  const key = event.key;

  // Movement keys
  if (config.upKeys.includes(key)) {
    return { type: 'move', direction: 'up' };
  }
  if (config.downKeys.includes(key)) {
    return { type: 'move', direction: 'down' };
  }
  if (config.leftKeys.includes(key)) {
    return { type: 'move', direction: 'left' };
  }
  if (config.rightKeys.includes(key)) {
    return { type: 'move', direction: 'right' };
  }

  // Action keys
  if (config.placeKeys.includes(key)) {
    return { type: 'place', coordinate: { row: 0, col: 0 } }; // Coordinate filled by handler
  }
  if (config.passKeys.includes(key)) {
    return { type: 'pass' };
  }
  if (config.undoKeys.includes(key)) {
    return { type: 'undo' };
  }
  if (config.hintKeys.includes(key)) {
    return { type: 'hint' };
  }
  if (config.solutionKeys.includes(key) && event.altKey) {
    return { type: 'solution' };
  }

  // Number keys for quick position (1-9 on numpad or top row)
  if (config.enableNumberKeys && /^[1-9]$/.test(key)) {
    const num = parseInt(key, 10);
    // Map 1-9 to 3x3 grid positions (like numpad layout)
    const row = 2 - Math.floor((num - 1) / 3); // 7-9 = top, 1-3 = bottom
    const col = (num - 1) % 3;
    return { type: 'jump', coordinate: { row, col } };
  }

  // Tab to activate/deactivate
  if (key === 'Tab') {
    return { type: 'activate' };
  }
  if (key === 'Escape') {
    return { type: 'deactivate' };
  }

  return { type: 'none' };
}

/**
 * Move cursor in a direction.
 */
export function moveCursor(
  current: Coordinate,
  direction: 'up' | 'down' | 'left' | 'right',
  boardSize: number,
  wrap: boolean = false
): Coordinate {
  let { row, col } = current;

  switch (direction) {
    case 'up':
      row = wrap ? (row - 1 + boardSize) % boardSize : Math.max(0, row - 1);
      break;
    case 'down':
      row = wrap ? (row + 1) % boardSize : Math.min(boardSize - 1, row + 1);
      break;
    case 'left':
      col = wrap ? (col - 1 + boardSize) % boardSize : Math.max(0, col - 1);
      break;
    case 'right':
      col = wrap ? (col + 1) % boardSize : Math.min(boardSize - 1, col + 1);
      break;
  }

  return { row, col };
}

/**
 * Jump cursor to a mapped position on the board.
 *
 * @param gridPosition - Position on 3x3 grid (0-2 for row/col)
 * @param boardSize - Board size
 * @returns Board coordinate
 */
export function jumpToPosition(
  gridPosition: Coordinate,
  boardSize: number
): Coordinate {
  // Map 3x3 grid to board positions
  // 0 = near edge, 1 = quarter, 2 = center/far side
  const positions = [
    Math.floor(boardSize * 0.15), // Near edge (15%)
    Math.floor(boardSize * 0.5), // Center (50%)
    Math.floor(boardSize * 0.85), // Far side (85%)
  ];

  return {
    row: positions[Math.min(2, gridPosition.row)] ?? positions[1]!,
    col: positions[Math.min(2, gridPosition.col)] ?? positions[1]!,
  };
}

/**
 * Keyboard navigation manager.
 */
export class KeyboardNavigationManager {
  private state: KeyboardNavState;
  private config: KeyboardConfig;
  private boardSize: number;
  private onPlace: ((coord: Coordinate) => void) | null = null;
  private onPass: (() => void) | null = null;
  private onUndo: (() => void) | null = null;
  private onHint: (() => void) | null = null;
  private onSolution: (() => void) | null = null;
  private onCursorChange: ((coord: Coordinate, visible: boolean) => void) | null = null;

  constructor(
    boardSize: number = 19,
    config: Partial<KeyboardConfig> = {}
  ) {
    this.boardSize = boardSize;
    this.config = { ...DEFAULT_KEYBOARD_CONFIG, ...config };
    this.state = createKeyboardNavState(boardSize);
  }

  /**
   * Get current state.
   */
  getState(): KeyboardNavState {
    return this.state;
  }

  /**
   * Set callback handlers.
   */
  setHandlers(handlers: {
    onPlace?: (coord: Coordinate) => void;
    onPass?: () => void;
    onUndo?: () => void;
    onHint?: () => void;
    onSolution?: () => void;
    onCursorChange?: (coord: Coordinate, visible: boolean) => void;
  }): void {
    if (handlers.onPlace) this.onPlace = handlers.onPlace;
    if (handlers.onPass) this.onPass = handlers.onPass;
    if (handlers.onUndo) this.onUndo = handlers.onUndo;
    if (handlers.onHint) this.onHint = handlers.onHint;
    if (handlers.onSolution) this.onSolution = handlers.onSolution;
    if (handlers.onCursorChange) this.onCursorChange = handlers.onCursorChange;
  }

  /**
   * Handle keyboard event.
   */
  handleKeyDown(event: KeyboardEvent): boolean {
    // Ignore if focus is in an input
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target instanceof HTMLSelectElement
    ) {
      return false;
    }

    const action = parseKeyboardEvent(event, this.config);

    switch (action.type) {
      case 'move': {
        event.preventDefault();
        const newCursor = moveCursor(
          this.state.cursor,
          action.direction,
          this.boardSize
        );
        this.state = {
          ...this.state,
          isActive: true,
          cursor: newCursor,
          cursorVisible: true,
        };
        this.onCursorChange?.(newCursor, true);
        return true;
      }

      case 'place': {
        if (this.state.isActive && this.state.cursorVisible) {
          event.preventDefault();
          this.onPlace?.(this.state.cursor);
          return true;
        }
        return false;
      }

      case 'pass': {
        event.preventDefault();
        this.onPass?.();
        return true;
      }

      case 'undo': {
        event.preventDefault();
        this.onUndo?.();
        return true;
      }

      case 'hint': {
        event.preventDefault();
        this.onHint?.();
        return true;
      }

      case 'solution': {
        event.preventDefault();
        this.onSolution?.();
        return true;
      }

      case 'activate': {
        if (!this.state.isActive) {
          event.preventDefault();
          this.state = {
            ...this.state,
            isActive: true,
            cursorVisible: true,
          };
          this.onCursorChange?.(this.state.cursor, true);
          return true;
        }
        return false;
      }

      case 'deactivate': {
        if (this.state.isActive) {
          event.preventDefault();
          this.state = {
            ...this.state,
            isActive: false,
            cursorVisible: false,
          };
          this.onCursorChange?.(this.state.cursor, false);
          return true;
        }
        return false;
      }

      case 'jump': {
        event.preventDefault();
        const jumpTarget = jumpToPosition(action.coordinate, this.boardSize);
        this.state = {
          ...this.state,
          isActive: true,
          cursor: jumpTarget,
          cursorVisible: true,
        };
        this.onCursorChange?.(jumpTarget, true);
        return true;
      }

      case 'none':
      default:
        return false;
    }
  }

  /**
   * Update board size.
   */
  setBoardSize(size: number): void {
    this.boardSize = size;
    // Re-center cursor if out of bounds
    if (
      this.state.cursor.row >= size ||
      this.state.cursor.col >= size
    ) {
      const center = Math.floor(size / 2);
      this.state = {
        ...this.state,
        cursor: { row: center, col: center },
      };
    }
  }

  /**
   * Set cursor position.
   */
  setCursor(coord: Coordinate): void {
    if (
      coord.row >= 0 &&
      coord.row < this.boardSize &&
      coord.col >= 0 &&
      coord.col < this.boardSize
    ) {
      this.state = {
        ...this.state,
        cursor: coord,
      };
    }
  }

  /**
   * Activate keyboard navigation.
   */
  activate(): void {
    this.state = {
      ...this.state,
      isActive: true,
      cursorVisible: true,
    };
    this.onCursorChange?.(this.state.cursor, true);
  }

  /**
   * Deactivate keyboard navigation.
   */
  deactivate(): void {
    this.state = {
      ...this.state,
      isActive: false,
      cursorVisible: false,
    };
    this.onCursorChange?.(this.state.cursor, false);
  }

  /**
   * Cleanup.
   */
  destroy(): void {
    this.onPlace = null;
    this.onPass = null;
    this.onUndo = null;
    this.onHint = null;
    this.onSolution = null;
    this.onCursorChange = null;
  }
}

/**
 * Create keyboard navigation manager.
 */
export function createKeyboardNavigationManager(
  boardSize: number = 19,
  config?: Partial<KeyboardConfig>
): KeyboardNavigationManager {
  return new KeyboardNavigationManager(boardSize, config);
}

/**
 * Hook helper for keyboard navigation (for Preact components).
 */
export function useKeyboardNavigation(
  manager: KeyboardNavigationManager
): (event: KeyboardEvent) => void {
  return (event: KeyboardEvent) => manager.handleKeyDown(event);
}
