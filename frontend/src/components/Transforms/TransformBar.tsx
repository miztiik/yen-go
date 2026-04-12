/**
 * TransformBar Component
 * @module components/Transforms/TransformBar
 *
 * Toggle buttons for puzzle transformations + coordinate visibility:
 * - Flip Horizontal
 * - Flip Vertical
 * - Rotate Clockwise (90° steps)
 * - Swap Colors
 * - Show/Hide Coordinates
 *
 * Spec 125, Task T058 | Spec 132: T129–T131 (SVG icons, Tailwind migration)
 * User Story 2: Board Transformations
 */

import { type JSX } from 'preact';
import { useCallback } from 'preact/hooks';
import { memo } from 'preact/compat';
import type { TransformSettings } from '../../lib/sgf-preprocessor';
import {
  FlipHIcon,
  FlipVIcon,
  FlipDiagIcon,
  RotateCWIcon,
  RotateCCWIcon,
  SwapColorsIcon,
  CoordsIcon,
} from '../shared/icons';
import { ZoomIcon } from '../shared/icons';

export interface TransformBarProps {
  settings: TransformSettings;
  onToggleFlipH: () => void;
  onToggleFlipV: () => void;
  onToggleFlipDiag: () => void;
  onRotateCW: () => void;
  onRotateCCW: () => void;
  onToggleSwapColors: () => void;
  /** Whether coordinate labels are currently visible */
  coordinateLabels: boolean;
  /** Toggle coordinate label visibility */
  onToggleCoordinates: () => void;
  disabled?: boolean;
  className?: string;
  /** T03: Zoom toggle state + handler */
  zoomEnabled?: boolean;
  isZoomable?: boolean;
  onToggleZoom?: () => void;
}

/* T03: Icon button styles — 66px (+50%), accessible touch targets */
const baseBtn =
  'inline-flex items-center justify-center rounded-[10px] w-[4.125rem] h-[4.125rem] transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--color-bg-primary)]';
const inactiveBtn = `${baseBtn} bg-transparent text-[var(--color-text-secondary)] cursor-pointer hover:bg-[var(--color-accent)]/10 hover:text-[var(--color-accent)]`;
const activeBtn = `${baseBtn} bg-[var(--color-accent)]/12 text-[var(--color-accent)] font-semibold cursor-pointer`;
const disabledBtn = `${baseBtn} bg-transparent text-[var(--color-text-disabled)] cursor-not-allowed opacity-40`;

/**
 * TransformBar — Toolbar with toggle buttons for puzzle transformations
 * and a coordinate visibility toggle.
 * All icons are clean SVG components (zero emoji). Spec 132 FR-051, FR-077.
 */
export function TransformBar({
  settings,
  onToggleFlipH,
  onToggleFlipV,
  onToggleFlipDiag,
  onRotateCW,
  onRotateCCW,
  onToggleSwapColors,
  coordinateLabels,
  onToggleCoordinates,
  disabled = false,
  className,
  zoomEnabled,
  isZoomable,
  onToggleZoom,
}: TransformBarProps): JSX.Element {
  const btnClass = useCallback(
    (isActive: boolean) => {
      if (disabled) return disabledBtn;
      return isActive ? activeBtn : inactiveBtn;
    },
    [disabled]
  );

  // Coordinate toggle is never disabled (always accessible)
  const coordsBtnClass = coordinateLabels ? activeBtn : inactiveBtn;

  return (
    <div
      className={`flex flex-wrap items-center justify-center gap-2.5 ${className ?? ''}`}
      role="toolbar"
      aria-label="Puzzle transforms"
      data-testid="transform-bar"
    >
      <button
        type="button"
        className={btnClass(settings.flipH)}
        onClick={onToggleFlipH}
        disabled={disabled}
        aria-pressed={settings.flipH}
        aria-label="Flip horizontal"
        title="Flip Horizontal"
      >
        <FlipHIcon size={30} />
      </button>
      <button
        type="button"
        className={btnClass(settings.flipV)}
        onClick={onToggleFlipV}
        disabled={disabled}
        aria-pressed={settings.flipV}
        aria-label="Flip vertical"
        title="Flip Vertical"
      >
        <FlipVIcon size={30} />
      </button>
      <button
        type="button"
        className={btnClass(settings.flipDiag)}
        onClick={onToggleFlipDiag}
        disabled={disabled}
        aria-pressed={settings.flipDiag}
        aria-label="Flip diagonal"
        title="Flip Diagonal"
      >
        <FlipDiagIcon size={30} />
      </button>
      <button
        type="button"
        className={btnClass(settings.rotation !== 0)}
        onClick={onRotateCCW}
        disabled={disabled}
        aria-label="Rotate counter-clockwise"
        title="Rotate CCW"
      >
        <RotateCCWIcon size={30} />
      </button>
      <button
        type="button"
        className={btnClass(settings.rotation !== 0)}
        onClick={onRotateCW}
        disabled={disabled}
        aria-label="Rotate clockwise"
        title="Rotate CW"
      >
        <RotateCWIcon size={30} />
      </button>
      <button
        type="button"
        className={btnClass(settings.swapColors)}
        onClick={onToggleSwapColors}
        disabled={disabled}
        aria-pressed={settings.swapColors}
        aria-label="Swap colors"
        title="Swap Colors"
      >
        <SwapColorsIcon size={30} />
      </button>

      {/* Separator */}
      <div className="w-px h-10 bg-[var(--color-neutral-200)] mx-1.5" />

      <button
        type="button"
        className={coordsBtnClass}
        onClick={onToggleCoordinates}
        aria-pressed={coordinateLabels}
        aria-label={coordinateLabels ? 'Hide coordinates' : 'Show coordinates'}
        title={coordinateLabels ? 'Hide Coordinates' : 'Show Coordinates'}
      >
        <CoordsIcon size={30} />
      </button>

      {/* T03: Zoom toggle (only when zoomable) */}
      {isZoomable && onToggleZoom && (
        <button
          type="button"
          className={zoomEnabled ? activeBtn : inactiveBtn}
          onClick={onToggleZoom}
          aria-label={zoomEnabled ? 'Show full board' : 'Zoom to puzzle area'}
          title={zoomEnabled ? 'Show full board' : 'Zoom to puzzle area'}
        >
          <ZoomIcon size={30} />
        </button>
      )}
    </div>
  );
}

export default memo(TransformBar);
