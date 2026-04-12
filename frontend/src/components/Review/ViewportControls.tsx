/**
 * Viewport Controls Component
 * @module components/Review/ViewportControls
 *
 * Provides controls for auto-crop viewport (FR-011, FR-012, FR-013, FR-014).
 * Features: toggle auto-crop, expand/shrink, reset to full board.
 *
 * Constitution Compliance:
 * - IX. Accessibility: Keyboard accessible, clear feedback
 * - X. Design Philosophy: Minimal, non-intrusive controls
 */

import type { JSX } from 'preact';
import type { BoardViewport, ViewportOptions } from '@models/SolutionPresentation';

/**
 * Props for ViewportControls component.
 */
export interface ViewportControlsProps {
  /** Current viewport state */
  viewport: BoardViewport;
  /** Board size (9, 13, 19) */
  boardSize: number;
  /** Toggle auto-crop callback */
  onToggle: () => void;
  /** Expand viewport by N cells callback */
  onExpand: (cells: number) => void;
  /** Reset to full board callback */
  onReset: () => void;
  /** Options update callback */
  onOptionsChange?: (options: Partial<ViewportOptions>) => void;
  /** Current options */
  options?: ViewportOptions;
  /** Whether controls are disabled */
  disabled?: boolean;
  /** CSS class override */
  className?: string;
  /** Compact mode */
  compact?: boolean;
}

/**
 * Icons for viewport controls.
 */
const CropIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M2 4v10h10v2h2V4h-2v8H4V4H2zM4 0v2h8v8h2V2h-8V0H4z" />
  </svg>
);

const ExpandIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M0 0v6h2V2h4V0H0zM10 0v2h4v4h2V0h-6zM0 10v6h6v-2H2v-4H0zM14 10v4h-4v2h6v-6h-2z" />
  </svg>
);

const ShrinkIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M6 0v4H2v2h6V0H6zM8 0v6h6V4h-4V0H8zM0 8v2h4v4h2V8H0zM8 8v8h2v-4h4V10H8z" />
  </svg>
);

const FullBoardIcon = (): JSX.Element => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" />
    <circle cx="4" cy="4" r="1.5" />
    <circle cx="8" cy="4" r="1.5" />
    <circle cx="12" cy="4" r="1.5" />
    <circle cx="4" cy="8" r="1.5" />
    <circle cx="8" cy="8" r="1.5" />
    <circle cx="12" cy="8" r="1.5" />
    <circle cx="4" cy="12" r="1.5" />
    <circle cx="8" cy="12" r="1.5" />
    <circle cx="12" cy="12" r="1.5" />
  </svg>
);

/**
 * ViewportControls component - controls for auto-crop feature.
 */
export function ViewportControls({
  viewport,
  boardSize,
  onToggle,
  onExpand,
  onReset,
  onOptionsChange: _onOptionsChange,
  options: _options,
  disabled = false,
  className,
  compact = false,
}: ViewportControlsProps): JSX.Element {
  const { isFullBoard, width, height } = viewport;

  // Calculate current crop percentage
  const cropPercentage = isFullBoard
    ? 100
    : Math.round(((width * height) / (boardSize * boardSize)) * 100);

  // Check if we can expand/shrink
  const canExpand = !isFullBoard;
  const canShrink = isFullBoard || width > 3 || height > 3;

  return (
    <div
      className={`viewport-controls ${compact ? 'viewport-controls--compact' : ''} ${className ?? ''}`}
      role="group"
      aria-label="Board viewport controls"
    >
      {/* Toggle auto-crop */}
      <button
        type="button"
        className={`viewport-controls__btn ${!isFullBoard ? 'viewport-controls__btn--active' : ''}`}
        onClick={onToggle}
        disabled={disabled}
        aria-label={isFullBoard ? 'Enable auto-crop' : 'Disable auto-crop'}
        aria-pressed={!isFullBoard}
        title={isFullBoard ? 'Auto-crop (C)' : 'Show full board (C)'}
      >
        <CropIcon />
        {!compact && <span className="viewport-controls__label">Crop</span>}
      </button>

      {/* Only show expand/shrink when cropped */}
      {!isFullBoard && (
        <>
          {/* Expand viewport */}
          <button
            type="button"
            className="viewport-controls__btn"
            onClick={() => onExpand(1)}
            disabled={disabled || !canExpand}
            aria-label="Expand viewport"
            title="Expand view (+)"
          >
            <ExpandIcon />
          </button>

          {/* Shrink viewport */}
          <button
            type="button"
            className="viewport-controls__btn"
            onClick={() => onExpand(-1)}
            disabled={disabled || !canShrink}
            aria-label="Shrink viewport"
            title="Shrink view (-)"
          >
            <ShrinkIcon />
          </button>
        </>
      )}

      {/* Reset to full board */}
      <button
        type="button"
        className="viewport-controls__btn"
        onClick={onReset}
        disabled={disabled || isFullBoard}
        aria-label="Show full board"
        title="Full board (F)"
      >
        <FullBoardIcon />
        {!compact && <span className="viewport-controls__label">Full</span>}
      </button>

      {/* Viewport info */}
      {!compact && !isFullBoard && (
        <span className="viewport-controls__info" aria-live="polite">
          {width}×{height} ({cropPercentage}%)
        </span>
      )}
    </div>
  );
}

/**
 * ViewportOptionsPanel - advanced options for viewport control.
 */
export function ViewportOptionsPanel({
  options,
  onChange,
  disabled = false,
  className,
}: {
  options: ViewportOptions;
  onChange: (options: Partial<ViewportOptions>) => void;
  disabled?: boolean;
  className?: string;
}): JSX.Element {
  return (
    <div
      className={`viewport-options ${className ?? ''}`}
      role="group"
      aria-label="Viewport options"
    >
      {/* Padding control */}
      <label className="viewport-options__field">
        <span className="viewport-options__label">Padding</span>
        <input
          type="range"
          min="0"
          max="5"
          value={options.padding ?? 1}
          onChange={(e) =>
            onChange({ padding: parseInt((e.target as HTMLInputElement).value, 10) })
          }
          disabled={disabled}
          className="viewport-options__slider"
        />
        <span className="viewport-options__value">{options.padding ?? 1}</span>
      </label>

      {/* Snap to edge toggle */}
      <label className="viewport-options__field viewport-options__field--checkbox">
        <input
          type="checkbox"
          checked={options.snapToEdge ?? true}
          onChange={(e) => onChange({ snapToEdge: (e.target as HTMLInputElement).checked })}
          disabled={disabled}
        />
        <span className="viewport-options__label">Snap to board edge</span>
      </label>

      {/* Minimum size control */}
      <label className="viewport-options__field">
        <span className="viewport-options__label">Min size</span>
        <input
          type="number"
          min="5"
          max="19"
          value={options.minSize ?? 7}
          onChange={(e) =>
            onChange({ minSize: parseInt((e.target as HTMLInputElement).value, 10) })
          }
          disabled={disabled}
          className="viewport-options__input"
        />
      </label>
    </div>
  );
}

export default ViewportControls;
