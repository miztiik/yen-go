/**
 * SettingsPanel — unified settings panel with 2 controls.
 *
 * Controls:
 * 1. Theme toggle (light / dark)
 * 2. Sound toggle (on / off)
 *
 * All settings read/written via useSettings() hook.
 * No music, no coordinates (coordinates toggle on puzzle page),
 * no renderer preference.
 *
 * Spec 127: FR-020, FR-028, FR-029, US10
 * @module components/Layout/SettingsPanel
 */

import type { VNode } from 'preact';
import { useSettings } from '../../hooks/useSettings';

// ============================================================================
// Toggle Component
// ============================================================================

interface ToggleProps {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  description?: string;
}

function Toggle({ label, checked, onChange, description }: ToggleProps): VNode {
  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex flex-col">
        <span className="text-sm font-medium text-[var(--color-text-primary)]">{label}</span>
        {description && (
          <span className="text-xs text-[var(--color-text-muted)]">{description}</span>
        )}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-accent)] ${
          checked ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-bg-tertiary)]'
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow ring-0 transition-transform ${
            checked ? 'translate-x-5' : 'translate-x-0'
          }`}
        />
      </button>
    </div>
  );
}

// ============================================================================
// Settings Panel
// ============================================================================

export interface SettingsPanelProps {
  /** Whether the panel is open/visible. */
  isOpen?: boolean;
  /** Called when user requests to close the panel. */
  onClose?: () => void;
}

/**
 * SettingsPanel — 2 controls only.
 *
 * - Theme: light/dark toggle
 * - Sound: on/off toggle
 */
export function SettingsPanel({ isOpen = true, onClose }: SettingsPanelProps): VNode | null {
  const { settings, updateSettings } = useSettings();

  if (!isOpen) return null;

  return (
    <div
      className="w-72 rounded-xl bg-[var(--color-bg-panel)] p-4 shadow-lg"
      role="dialog"
      aria-label="Settings"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-3">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)]">Settings</h2>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="rounded-lg p-1 text-[var(--color-text-muted)] transition-colors hover:bg-[var(--color-bg-secondary)]"
          >
            ✕
          </button>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)]" />

      {/* Appearance section */}
      <div className="py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Appearance
        </span>
        <Toggle
          label="Dark Mode"
          checked={settings.theme === 'dark'}
          onChange={(dark) => updateSettings({ theme: dark ? 'dark' : 'light' })}
          description="Switch between light and dark theme"
        />
      </div>

      {/* Divider */}
      <div className="border-t border-[var(--color-border)]" />

      {/* Sound section */}
      <div className="py-2">
        <span className="text-xs font-medium uppercase tracking-wider text-[var(--color-text-muted)]">
          Audio
        </span>
        <Toggle
          label="Sound Effects"
          checked={settings.soundEnabled}
          onChange={(enabled) => updateSettings({ soundEnabled: enabled })}
          description="Stone placement, captures, and feedback"
        />
      </div>
    </div>
  );
}

export default SettingsPanel;
