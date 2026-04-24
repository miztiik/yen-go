/**
 * KeyboardHelp — unit tests.
 *
 * Phase 3 (UI_KEYBOARD_HELP) overlay. Verifies the help sheet opens on `?`
 * and lists the supplied shortcut entries.
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/preact';
import { KeyboardHelp } from '@/components/shared/KeyboardHelp';

afterEach(() => {
  cleanup();
  document.body.style.overflow = '';
});

const SHORTCUTS = [
  { keys: 'Esc', description: 'Reset puzzle' },
  { keys: 'z', description: 'Undo last move' },
  { keys: '?', description: 'Show this help' },
];

describe('KeyboardHelp', () => {
  it('does not render the sheet by default', () => {
    render(<KeyboardHelp shortcuts={SHORTCUTS} />);
    expect(screen.queryByTestId('keyboard-help')).toBeNull();
  });

  it('opens the sheet when `?` is pressed and lists every shortcut', () => {
    render(<KeyboardHelp shortcuts={SHORTCUTS} />);

    fireEvent.keyDown(window, { key: '?' });

    expect(screen.getByTestId('keyboard-help')).toBeDefined();
    const list = screen.getByTestId('keyboard-help-list');
    expect(list.querySelectorAll('li')).toHaveLength(SHORTCUTS.length);
    expect(screen.getByText('Reset puzzle')).toBeDefined();
    expect(screen.getByText('Undo last move')).toBeDefined();
    expect(screen.getByText('Show this help')).toBeDefined();
  });

  it('closes the sheet on Escape', () => {
    render(<KeyboardHelp shortcuts={SHORTCUTS} />);

    fireEvent.keyDown(window, { key: '?' });
    expect(screen.getByTestId('keyboard-help')).toBeDefined();

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByTestId('keyboard-help')).toBeNull();
  });

  it('does not register the `?` binding when disabled', () => {
    render(<KeyboardHelp shortcuts={SHORTCUTS} enabled={false} />);

    fireEvent.keyDown(window, { key: '?' });
    expect(screen.queryByTestId('keyboard-help')).toBeNull();
  });
});
