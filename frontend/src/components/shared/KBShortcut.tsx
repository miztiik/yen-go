/**
 * KBShortcut — Declarative keyboard shortcut component.
 * @module components/shared/KBShortcut
 *
 * Ported from OGS pattern. Renders no DOM. Registers a `keydown` listener
 * on mount and cleans up on unmount. Excludes events from input/textarea.
 *
 * Usage:
 *   <KBShortcut shortcut="Escape" action={handleReset} />
 *   <KBShortcut shortcut="z" action={handleUndo} />
 */

import { useEffect } from 'preact/hooks';

export interface KBShortcutProps {
  /** Key value to match (e.g. "Escape", "ArrowLeft", "z", "x") */
  shortcut: string;
  /** Action to invoke when shortcut fires */
  action: () => void;
  /** Whether to use capture phase (fires before bubble listeners) */
  capture?: boolean;
  /** Whether to call stopImmediatePropagation (prevents other window listeners) */
  stopImmediate?: boolean;
  /** Whether the shortcut is currently active (default: true) */
  enabled?: boolean;
}

/**
 * Declarative keyboard shortcut — renders nothing, binds keydown on window.
 */
export function KBShortcut({
  shortcut,
  action,
  capture = false,
  stopImmediate = false,
  enabled = true,
}: KBShortcutProps): null {
  useEffect(() => {
    if (!enabled) return;

    const handler = (e: KeyboardEvent) => {
      // Don't capture when user is typing in an input or textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        (e.target instanceof HTMLElement && e.target.isContentEditable)
      ) {
        return;
      }

      if (e.key === shortcut) {
        e.preventDefault();
        if (stopImmediate) {
          e.stopImmediatePropagation();
        }
        action();
      }
    };

    window.addEventListener('keydown', handler, { capture });
    return () => window.removeEventListener('keydown', handler, { capture });
  }, [shortcut, action, capture, stopImmediate, enabled]);

  return null;
}

export default KBShortcut;
