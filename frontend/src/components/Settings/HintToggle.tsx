/**
 * Hint toggle component for settings.
 * Allows users to enable/disable hints globally.
 * @module components/Settings/HintToggle
 */

import type { FunctionalComponent } from 'preact';
import './HintToggle.css';

/**
 * Props for HintToggle component.
 */
export interface HintToggleProps {
  /** Whether hints are currently enabled */
  enabled: boolean;
  /** Callback when toggle is changed */
  onChange: (enabled: boolean) => void;
  /** Optional label text */
  label?: string;
}

/**
 * Toggle switch for enabling/disabling hints.
 */
export const HintToggle: FunctionalComponent<HintToggleProps> = ({
  enabled,
  onChange,
  label = 'Enable Hints',
}) => {
  const handleChange = (e: Event) => {
    const target = e.target as HTMLInputElement;
    onChange(target.checked);
  };

  const id = 'hint-toggle';

  return (
    <div className="hint-toggle">
      <label className="hint-toggle__container" htmlFor={id}>
        <span className="hint-toggle__label">{label}</span>
        <div className="hint-toggle__switch">
          <input
            type="checkbox"
            id={id}
            className="hint-toggle__input"
            checked={enabled}
            onChange={handleChange}
            role="switch"
            aria-checked={enabled}
          />
          <span className="hint-toggle__slider" aria-hidden="true" />
        </div>
      </label>
      <p className="hint-toggle__description">
        {enabled
          ? 'Hints are available during puzzles. Using hints will be recorded.'
          : 'Hints are disabled. You can solve puzzles without any assistance.'}
      </p>
    </div>
  );
};

export default HintToggle;
