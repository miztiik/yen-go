/**
 * KeyboardShortcutsLegend
 * @module components/SolutionTree/KeyboardShortcutsLegend
 *
 * Displays keyboard shortcuts for tree navigation.
 * Supports full and compact modes.
 *
 * Spec 056, Task T046/T057
 */

import { type JSX } from 'preact';

export interface KeyboardShortcutsLegendProps {
  /** Whether the legend is visible. Defaults to true. */
  visible?: boolean;
  /** Compact mode hides descriptions and Home/End keys. */
  compact?: boolean;
  /** Optional CSS class */
  className?: string;
}

interface ShortcutEntry {
  key: string;
  description: string;
  /** If true, hidden in compact mode */
  fullOnly?: boolean;
}

const shortcuts: ShortcutEntry[] = [
  { key: '←', description: 'Previous move' },
  { key: '→', description: 'Next move' },
  { key: '↑', description: 'Previous variation' },
  { key: '↓', description: 'Next variation' },
  { key: 'Home', description: 'Go to start', fullOnly: true },
  { key: 'End', description: 'Go to end', fullOnly: true },
];

const styles: Record<string, JSX.CSSProperties> = {
  container: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    padding: '8px 12px',
    backgroundColor: 'var(--color-neutral-50)',
    borderRadius: '6px',
    border: '1px solid var(--color-neutral-200)',
    fontSize: '12px',
    alignItems: 'center',
  },
  label: {
    fontWeight: '600',
    color: 'var(--color-text-secondary)',
    marginRight: '4px',
  },
  entry: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  },
  kbd: {
    display: 'inline-block',
    padding: '2px 6px',
    fontSize: '11px',
    fontFamily: 'monospace',
    fontWeight: '600',
    lineHeight: '1.4',
    color: 'var(--color-text-primary)',
    backgroundColor: 'white',
    border: '1px solid var(--color-neutral-300)',
    borderRadius: '3px',
    boxShadow: '0 1px 0 var(--color-neutral-200)',
    minWidth: '22px',
    textAlign: 'center' as const,
  },
  description: {
    color: 'var(--color-text-muted)',
    fontSize: '11px',
  },
};

/**
 * KeyboardShortcutsLegend
 *
 * Shows available keyboard shortcuts for solution tree navigation.
 * In compact mode, only arrow keys are shown without descriptions.
 */
export function KeyboardShortcutsLegend({
  visible = true,
  compact = false,
  className,
}: KeyboardShortcutsLegendProps): JSX.Element | null {
  if (!visible) return null;

  const visibleShortcuts = compact
    ? shortcuts.filter((s) => !s.fullOnly)
    : shortcuts;

  return (
    <div
      className={`keyboard-shortcuts-legend ${compact ? 'compact' : ''} ${className || ''}`}
      role="note"
      aria-label="Keyboard shortcuts"
      style={styles.container}
    >
      <span style={styles.label}>Navigate:</span>
      {visibleShortcuts.map((shortcut) => (
        <span key={shortcut.key} style={styles.entry}>
          <kbd style={styles.kbd} title={shortcut.description}>
            {shortcut.key}
          </kbd>
          {!compact && (
            <span style={styles.description}>{shortcut.description}</span>
          )}
        </span>
      ))}
    </div>
  );
}

export default KeyboardShortcutsLegend;
