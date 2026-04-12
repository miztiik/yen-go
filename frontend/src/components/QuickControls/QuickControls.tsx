/**
 * Quick Controls Component
 * @module components/QuickControls/QuickControls
 *
 * Panel for quick puzzle actions: rotate, undo, reset, hint.
 *
 * Constitution Compliance:
 * - FR-048 to FR-051: Quick controls panel
 *
 * Covers: T052
 */

import type { JSX } from 'preact';
import { useEffect, useCallback } from 'preact/hooks';
import type { BoardRotation } from '../../types/storage';
import { UndoIcon, ResetIcon, HintIcon } from '../shared/icons';
import './QuickControls.css';

/**
 * Props for QuickControls component.
 */
export interface QuickControlsProps {
  /** Callback when rotate button clicked */
  onRotate: () => void;
  /** Callback when undo button clicked */
  onUndo: () => void;
  /** Callback when reset button clicked */
  onReset: () => void;
  /** Callback when hint button clicked */
  onHint: () => void;
  /** Callback when explore toggle clicked */
  onToggleExplore?: () => void;
  /** Whether explore mode is active */
  isExploreMode?: boolean;
  /** Whether solution tree is available (has variations) */
  hasTree?: boolean;
  /** Whether undo is available */
  canUndo: boolean;
  /** Number of hints remaining */
  hintsRemaining: number;
  /** Total hints available for this puzzle (defaults to 3) */
  totalHints?: number;
  /** Current rotation angle */
  rotationAngle?: BoardRotation;
  /** Whether keyboard shortcuts are enabled */
  enableKeyboard?: boolean;
  /** CSS class name */
  className?: string;
}

/**
 * Keyboard shortcut mappings.
 */
export const KEYBOARD_SHORTCUTS = {
  rotate: 'r',
  undo: 'z',
  reset: 'x',
  hint: 'h',
  explore: 'e',
} as const;

/**
 * QuickControls - Panel for quick puzzle actions.
 *
 * Features:
 * - Rotate board (R key)
 * - Undo last move (Z key)
 * - Reset puzzle (X key)
 * - Get hint (H key)
 */
export function QuickControls({
  onRotate,
  onUndo,
  onReset,
  onHint,
  onToggleExplore,
  isExploreMode = false,
  hasTree = false,
  canUndo,
  hintsRemaining,
  totalHints: _totalHints = 3,
  rotationAngle = 0,
  enableKeyboard = true,
  className,
}: QuickControlsProps): JSX.Element {
  // Keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Don't capture if user is typing in an input
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      const key = e.key.toLowerCase();

      switch (key) {
        case KEYBOARD_SHORTCUTS.rotate:
          e.preventDefault();
          onRotate();
          break;
        case KEYBOARD_SHORTCUTS.undo:
          e.preventDefault();
          if (canUndo) {
            onUndo();
          }
          break;
        case KEYBOARD_SHORTCUTS.reset:
          e.preventDefault();
          onReset();
          break;
        case KEYBOARD_SHORTCUTS.hint:
          e.preventDefault();
          if (hintsRemaining > 0) {
            onHint();
          }
          break;
        case KEYBOARD_SHORTCUTS.explore:
          e.preventDefault();
          if (hasTree && onToggleExplore) {
            onToggleExplore();
          }
          break;
      }
    },
    [onRotate, onUndo, onReset, onHint, onToggleExplore, canUndo, hintsRemaining, hasTree]
  );

  useEffect(() => {
    if (!enableKeyboard) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enableKeyboard, handleKeyDown]);

  return (
    <div
      className={`quick-controls ${className ?? ''}`}
      data-testid="quick-controls"
      role="toolbar"
      aria-label="Quick controls"
    >
      <button
        type="button"
        className="control-button rotate"
        onClick={onRotate}
        aria-label={`Rotate board (currently ${rotationAngle}°)`}
        data-testid="rotate-button"
        title={`Rotate board (${KEYBOARD_SHORTCUTS.rotate.toUpperCase()})`}
      >
        <span className="icon" aria-hidden="true">
          <ResetIcon size={16} />
        </span>
        <span className="label">Rotate</span>
        <kbd className="shortcut">{KEYBOARD_SHORTCUTS.rotate.toUpperCase()}</kbd>
      </button>

      <button
        type="button"
        className="control-button undo"
        onClick={onUndo}
        disabled={!canUndo}
        aria-label="Undo last move"
        data-testid="undo-button"
        title={`Undo (${KEYBOARD_SHORTCUTS.undo.toUpperCase()})`}
      >
        <span className="icon" aria-hidden="true">
          <UndoIcon size={16} />
        </span>
        <span className="label">Undo</span>
        <kbd className="shortcut">{KEYBOARD_SHORTCUTS.undo.toUpperCase()}</kbd>
      </button>

      <button
        type="button"
        className="control-button reset"
        onClick={onReset}
        aria-label="Reset puzzle"
        data-testid="reset-button"
        title={`Reset (${KEYBOARD_SHORTCUTS.reset.toUpperCase()})`}
      >
        <span className="icon" aria-hidden="true">
          <ResetIcon size={16} />
        </span>
        <span className="label">Reset</span>
        <kbd className="shortcut">{KEYBOARD_SHORTCUTS.reset.toUpperCase()}</kbd>
      </button>

      <button
        type="button"
        className={`control-button hint ${hintsRemaining === 0 ? 'exhausted' : ''}`}
        onClick={onHint}
        disabled={hintsRemaining === 0}
        aria-label={
          hintsRemaining === 0 ? 'No hints remaining' : `Get hint (${hintsRemaining} remaining)`
        }
        data-testid="hint-button"
        title={
          hintsRemaining > 0
            ? `Hint (${KEYBOARD_SHORTCUTS.hint.toUpperCase()}) - ${hintsRemaining} left`
            : 'No hints available'
        }
      >
        <span className="icon" aria-hidden="true">
          <HintIcon size={16} />
        </span>
        <span className="label">
          Hint
          {hintsRemaining > 0 && <span className="hint-count">{hintsRemaining}</span>}
        </span>
        <kbd className="shortcut">{KEYBOARD_SHORTCUTS.hint.toUpperCase()}</kbd>
      </button>

      {hasTree && onToggleExplore && (
        <button
          type="button"
          className={`control-button explore ${isExploreMode ? 'active' : ''}`}
          onClick={onToggleExplore}
          aria-label={isExploreMode ? 'Exit explore mode' : 'Explore solution tree'}
          aria-pressed={isExploreMode}
          data-testid="explore-button"
          title={`${isExploreMode ? 'Exit' : 'Explore'} (${KEYBOARD_SHORTCUTS.explore.toUpperCase()})`}
        >
          <span className="icon" aria-hidden="true">
            ⏇
          </span>
          <span className="label">Explore</span>
          <kbd className="shortcut">{KEYBOARD_SHORTCUTS.explore.toUpperCase()}</kbd>
        </button>
      )}
    </div>
  );
}

export default QuickControls;
