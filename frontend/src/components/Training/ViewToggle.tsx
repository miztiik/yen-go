/**
 * ViewToggle — Grid/List segmented control with bounce animation.
 * @module components/Training/ViewToggle
 *
 * Spec 132, Phase 12 — Training Page Redesign
 */

import type { FunctionalComponent, JSX } from 'preact';
import { useState, useCallback } from 'preact/hooks';
import { GridIcon } from '../shared/icons/GridIcon';
import { ListIcon } from '../shared/icons/ListIcon';

export type ViewMode = 'grid' | 'list';

export interface ViewToggleProps {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
  testId?: string;
}

/**
 * Segmented control to switch between grid and list view modes.
 * Active button gets accent bg + white text. Inactive is transparent.
 * Clicking triggers a 250ms bounce animation on the icon.
 */
export const ViewToggle: FunctionalComponent<ViewToggleProps> = ({
  value,
  onChange,
  testId = 'view-toggle',
}) => {
  const [bouncing, setBouncing] = useState<ViewMode | null>(null);

  const handleClick = useCallback(
    (mode: ViewMode) => {
      if (mode === value) return;
      setBouncing(mode);
      onChange(mode);
      setTimeout(() => setBouncing(null), 250);
    },
    [value, onChange]
  );

  return (
    <div
      className="flex rounded-full bg-[var(--color-bg-tertiary)] p-1 shadow-inner"
      role="radiogroup"
      aria-label="View mode"
      data-testid={testId}
    >
      <ToggleButton
        mode="grid"
        active={value === 'grid'}
        bouncing={bouncing === 'grid'}
        onClick={handleClick}
        icon={<GridIcon size={16} />}
        label="Grid view"
      />
      <ToggleButton
        mode="list"
        active={value === 'list'}
        bouncing={bouncing === 'list'}
        onClick={handleClick}
        icon={<ListIcon size={16} />}
        label="List view"
      />
    </div>
  );
};

interface ToggleButtonProps {
  mode: ViewMode;
  active: boolean;
  bouncing: boolean;
  onClick: (mode: ViewMode) => void;
  icon: JSX.Element;
  label: string;
}

function ToggleButton({
  mode,
  active,
  bouncing,
  onClick,
  icon,
  label,
}: ToggleButtonProps): JSX.Element {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      aria-label={label}
      onClick={() => onClick(mode)}
      className={`flex items-center justify-center rounded-full px-3.5 py-1.5 text-sm font-bold transition-all duration-200 ${
        active
          ? 'bg-[var(--color-accent)] text-white shadow-[var(--shadow-md)]'
          : 'bg-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-secondary)]'
      }`}
    >
      <span className={bouncing ? 'animate-bounce-icon' : ''}>{icon}</span>
    </button>
  );
}

export default ViewToggle;
