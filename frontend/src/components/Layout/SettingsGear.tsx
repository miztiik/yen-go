/**
 * SettingsGear — Gear icon button that opens settings dropdown.
 * @module components/Layout/SettingsGear
 *
 * Separates settings (theme, sound) from user profile.
 * Gear icon sits to the left of the profile avatar in AppHeader.
 *
 * Spec 132, Phase 12 — Settings UX improvement
 */

import { useState, useCallback, useRef, useEffect } from 'preact/hooks';
import { useSettings } from '../../hooks/useSettings';

/**
 * Gear SVG icon — 20×20, matches Apple HIG gear style.
 */
function GearIcon({ size = 20 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.32 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
    </svg>
  );
}

/** Reusable toggle switch — DRY extraction from 3 identical toggles. */
function ToggleSwitch({
  label,
  checked,
  onClick,
  ariaLabel,
}: {
  label: string;
  checked: boolean;
  onClick: () => void;
  ariaLabel?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-[var(--color-text-primary)]">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        {...(ariaLabel ? { 'aria-label': ariaLabel } : {})}
        onClick={onClick}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 ${
          checked ? 'bg-[var(--color-accent)]' : 'bg-[var(--color-text-muted)]/30'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

/**
 * SettingsGear — Gear icon that opens a dropdown with Dark Mode + Sound toggles.
 */
export function SettingsGear() {
  const [isOpen, setIsOpen] = useState(false);
  const { settings, updateSettings } = useSettings();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  const toggleDropdown = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const toggleTheme = useCallback(() => {
    updateSettings({ theme: settings.theme === 'dark' ? 'light' : 'dark' });
  }, [settings.theme, updateSettings]);

  const toggleSound = useCallback(() => {
    updateSettings({ soundEnabled: !settings.soundEnabled });
  }, [settings.soundEnabled, updateSettings]);

  const toggleAutoAdvance = useCallback(() => {
    updateSettings({ autoAdvance: !settings.autoAdvance });
  }, [settings.autoAdvance, updateSettings]);

  const decrementDelay = useCallback(() => {
    if (settings.autoAdvanceDelay > 1) {
      updateSettings({ autoAdvanceDelay: settings.autoAdvanceDelay - 1 });
    }
  }, [settings.autoAdvanceDelay, updateSettings]);

  const incrementDelay = useCallback(() => {
    if (settings.autoAdvanceDelay < 5) {
      updateSettings({ autoAdvanceDelay: settings.autoAdvanceDelay + 1 });
    }
  }, [settings.autoAdvanceDelay, updateSettings]);

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        className="flex items-center justify-center rounded-full p-1.5 text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-bg-secondary)] hover:text-[var(--color-text-primary)]"
        onClick={toggleDropdown}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label="Settings"
      >
        <GearIcon size={18} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} aria-hidden="true" />
          <div
            ref={dropdownRef}
            className="absolute right-0 top-full z-50 mt-2 w-56 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-panel)] shadow-xl"
            role="menu"
            aria-label="Settings"
          >
            <div className="border-b border-[var(--color-border)] px-4 py-2.5">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                Settings
              </span>
            </div>

            <div className="p-3">
              <ToggleSwitch
                label="Dark Mode"
                checked={settings.theme === 'dark'}
                onClick={toggleTheme}
              />
              <ToggleSwitch
                label="Sound Effects"
                checked={settings.soundEnabled}
                onClick={toggleSound}
              />
              <ToggleSwitch
                label="Auto-Advance"
                checked={settings.autoAdvance}
                onClick={toggleAutoAdvance}
                ariaLabel="Auto-advance to next puzzle after solving"
              />

              {/* Auto-Advance delay stepper (progressive disclosure) */}
              {settings.autoAdvance && (
                <div className="flex items-center justify-between py-2 pl-2">
                  <span className="text-xs text-[var(--color-text-muted)]">Delay</span>
                  <div
                    className="flex items-center gap-1.5"
                    role="group"
                    aria-label="Auto-advance delay"
                  >
                    <button
                      type="button"
                      onClick={decrementDelay}
                      disabled={settings.autoAdvanceDelay <= 1}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-[var(--color-text-secondary)] bg-[var(--color-bg-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                      aria-label="Decrease delay"
                    >
                      −
                    </button>
                    <span
                      className="min-w-[2rem] text-center text-sm font-semibold text-[var(--color-text-primary)]"
                      aria-live="polite"
                    >
                      {settings.autoAdvanceDelay}s
                    </span>
                    <button
                      type="button"
                      onClick={incrementDelay}
                      disabled={settings.autoAdvanceDelay >= 5}
                      className="inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-[var(--color-text-secondary)] bg-[var(--color-bg-secondary)] hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                      aria-label="Increase delay"
                    >
                      +
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default SettingsGear;
