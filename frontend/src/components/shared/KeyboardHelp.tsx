/**
 * KeyboardHelp — keyboard shortcut reference overlay.
 * @module components/shared/KeyboardHelp
 *
 * Triggered by `?` in any solver view. Lists existing keyboard bindings so
 * power users can discover them without docs. Pure addition — does not change
 * binding behavior. Behind UI_KEYBOARD_HELP flag.
 */

import type { JSX } from 'preact';
import { useState, useCallback } from 'preact/hooks';
import { BottomSheet } from './BottomSheet';
import { KBShortcut } from './KBShortcut';

export interface KeyboardShortcutEntry {
  /** Key combination as displayed (e.g. "Esc", "z", "←"). */
  keys: string;
  /** What pressing the key does. */
  description: string;
  /** Whether the shortcut is currently active in the parent context. */
  enabled?: boolean;
}

export interface KeyboardHelpProps {
  /** Shortcut entries to display. */
  shortcuts: readonly KeyboardShortcutEntry[];
  /**
   * If false, the `?` keyboard binding is not registered. Use this when the
   * parent view is unmounted but kept in the tree.
   */
  enabled?: boolean;
  /** Test id (defaults to `keyboard-help`). */
  testId?: string;
}

/**
 * Renders an invisible `?` keyboard binding plus the help sheet it opens.
 * Self-contained — no props need to flow up to the parent.
 */
export function KeyboardHelp({
  shortcuts,
  enabled = true,
  testId = 'keyboard-help',
}: KeyboardHelpProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const handleOpen = useCallback(() => setOpen(true), []);
  const handleClose = useCallback(() => setOpen(false), []);

  return (
    <>
      <KBShortcut shortcut="?" action={handleOpen} enabled={enabled} />
      <BottomSheet isOpen={open} onClose={handleClose} title="Keyboard shortcuts" testId={testId}>
        <ul className="keyboard-help-list" data-testid={`${testId}-list`}>
          {shortcuts.map((entry) => (
            <li key={entry.keys} className="keyboard-help-row">
              <kbd className="keyboard-help-key">{entry.keys}</kbd>
              <span className="keyboard-help-desc">{entry.description}</span>
            </li>
          ))}
        </ul>
        <p className="keyboard-help-hint">
          Press <kbd className="keyboard-help-key">?</kbd> at any time to reopen this list.
        </p>
      </BottomSheet>
    </>
  );
}

export default KeyboardHelp;
