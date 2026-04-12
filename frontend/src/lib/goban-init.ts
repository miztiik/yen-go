/**
 * Goban one-time initialization module.
 *
 * Calls `setGobanCallbacks` once at app startup to configure goban's
 * global behavior BEFORE any goban instances are created.
 *
 * Phase 1 changes (UI-002 + UI-017):
 * - Custom board theme for full control over line color/thickness
 * - customBoardColor for flat kaya wood color
 * - customBoardLineColor for darker, more visible grid lines
 * - Dark mode support via theme-aware callbacks
 */

import { setGobanCallbacks } from 'goban';
import { MoveTree } from 'goban';
import { getSettingsSnapshot } from '../hooks/useSettings';

let initialized = false;

/** Check if dark mode is active. */
function isDarkMode(): boolean {
  try {
    return document.documentElement.dataset.theme === 'dark';
  } catch {
    return false;
  }
}

function getSelectedThemes() {
  return {
    white: 'Shell',
    black: 'Slate',
    board: 'Custom', // Use Custom board for full control (UI-017)
    'removal-graphic': 'square' as const,
    'removal-scale': 1.0,
    'stone-shadows': 'default' as const,
  };
}

export function initGoban(): void {
  if (initialized) return;

  setGobanCallbacks({
    getCDNReleaseBase: () => '',
    getSelectedThemes: () => getSelectedThemes(),
    watchSelectedThemes: (cb: (themes: ReturnType<typeof getSelectedThemes>) => void) => {
      const observer = new MutationObserver(() => {
        cb(getSelectedThemes());
      });
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme'],
      });
      return { remove: () => observer.disconnect() };
    },
    getCoordinateDisplaySystem: () => 'A1',
    // UI-035: Sound enabled/volume read from canonical settings.
    // Stone placement sounds are played by usePuzzleState via audioService.
    getSoundEnabled: () => {
      try {
        return getSettingsSnapshot().soundEnabled;
      } catch {
        return true;
      }
    },
    getSoundVolume: () => 1.0,
    getMoveTreeNumbering: () => 'move-number',

    // UI-017: Custom board theme callbacks for full visual control
    customBoardColor: () => (isDarkMode() ? '#2a2520' : '#E3C076'),
    customBoardLineColor: () => (isDarkMode() ? '#8b7355' : '#4a3c28'),
    customBoardUrl: () => (isDarkMode() ? '' : '/img/kaya.jpg'),
  });

  // T14: Unify solution tree branch colors — single muted gray instead of rainbow
  MoveTree.line_colors = [
    '#9ca3af',
    '#9ca3af',
    '#9ca3af',
    '#9ca3af',
    '#9ca3af',
    '#9ca3af',
    '#9ca3af',
  ];
  (MoveTree as unknown as { isobranch_colors: { strong: string; weak: string } }).isobranch_colors =
    { strong: '#6b7280', weak: '#d1d5db' };

  initialized = true;
}
