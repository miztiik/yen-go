/**
 * BoardControls - Compact floating control bar for board settings
 *
 * Apple control bar aesthetic with glassmorphism effect.
 * Positioned in top-right corner of board.
 *
 * Spec 122 - Board Controls Component
 */

import './BoardControls.css';

export interface BoardControlsProps {
  /** Current rotation in degrees (0, 90, 180, 270) */
  rotation: number;
  /** Callback when rotation changes */
  onRotationChange: (rotation: number) => void;
  /** Whether coordinates are shown */
  showCoordinates: boolean;
  /** Callback when coordinates toggle changes */
  onCoordinatesChange: (show: boolean) => void;
  /** Optional className */
  className?: string;
}

/** Valid rotation values */
const ROTATION_VALUES = [0, 90, 180, 270] as const;

/**
 * Get next rotation value in cycle: 0 → 90 → 180 → 270 → 0
 */
function getNextRotation(current: number): number {
  const currentIndex = ROTATION_VALUES.indexOf(current as typeof ROTATION_VALUES[number]);
  if (currentIndex === -1) return 0;
  const nextIndex = (currentIndex + 1) % ROTATION_VALUES.length;
  return ROTATION_VALUES[nextIndex] as number;
}

/**
 * BoardControls component
 *
 * Provides rotation cycling and coordinate visibility toggle.
 *
 * TODO: Future enhancement - Long-press on rotation button opens picker
 * with 4 rotation options (0°, 90°, 180°, 270°)
 */
export function BoardControls({
  rotation,
  onRotationChange,
  showCoordinates,
  onCoordinatesChange,
  className = '',
}: BoardControlsProps) {
  const handleRotationClick = () => {
    const nextRotation = getNextRotation(rotation);
    onRotationChange(nextRotation);
  };

  const handleCoordinatesClick = () => {
    onCoordinatesChange(!showCoordinates);
  };

  // Handle keyboard navigation between buttons
  const handleKeyDown = (e: KeyboardEvent, action: 'rotation' | 'coordinates') => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      const target = e.currentTarget as HTMLButtonElement;
      const buttons = target.parentElement?.querySelectorAll('button');
      if (!buttons) return;

      const currentIndex = action === 'rotation' ? 0 : 1;
      const nextIndex = e.key === 'ArrowRight'
        ? (currentIndex + 1) % buttons.length
        : (currentIndex - 1 + buttons.length) % buttons.length;

      (buttons[nextIndex] as HTMLButtonElement).focus();
    }
  };

  return (
    <div
      className={`board-controls ${className}`.trim()}
      role="toolbar"
      aria-label="Board controls"
    >
      {/* Rotation toggle button */}
      <button
        type="button"
        className="btn-icon board-controls__btn"
        onClick={handleRotationClick}
        onKeyDown={(e) => handleKeyDown(e, 'rotation')}
        aria-label={`Rotate board. Current rotation: ${rotation} degrees`}
        title={`Rotate board (${rotation}°)`}
      >
        <RotationIcon />
      </button>

      {/* Coordinates toggle button */}
      <button
        type="button"
        className="btn-icon board-controls__btn"
        onClick={handleCoordinatesClick}
        onKeyDown={(e) => handleKeyDown(e, 'coordinates')}
        aria-label={showCoordinates ? 'Hide coordinates' : 'Show coordinates'}
        aria-pressed={showCoordinates}
        title={showCoordinates ? 'Hide coordinates' : 'Show coordinates'}
      >
        <GridIcon active={showCoordinates} />
      </button>
    </div>
  );
}

/**
 * Rotation icon (🔄 style, but as SVG)
 */
function RotationIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M14.5 3.5C12.5 2 9.5 1.5 7 2.5C3.5 4 1.5 8 2.5 12C3.5 16 7.5 18.5 11.5 17.5C14.5 16.8 16.5 14.5 17.2 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M14 1L14.5 3.5L17 4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Grid/coordinates icon
 */
function GridIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {/* Grid lines */}
      <rect
        x="3"
        y="3"
        width="14"
        height="14"
        rx="1"
        stroke="currentColor"
        strokeWidth="1.5"
        fill={active ? 'currentColor' : 'none'}
        fillOpacity={active ? 0.1 : 0}
      />
      {/* Vertical lines */}
      <line x1="7" y1="3" x2="7" y2="17" stroke="currentColor" strokeWidth="1" />
      <line x1="10" y1="3" x2="10" y2="17" stroke="currentColor" strokeWidth="1" />
      <line x1="13" y1="3" x2="13" y2="17" stroke="currentColor" strokeWidth="1" />
      {/* Horizontal lines */}
      <line x1="3" y1="7" x2="17" y2="7" stroke="currentColor" strokeWidth="1" />
      <line x1="3" y1="10" x2="17" y2="10" stroke="currentColor" strokeWidth="1" />
      <line x1="3" y1="13" x2="17" y2="13" stroke="currentColor" strokeWidth="1" />
      {/* Coordinate labels when active */}
      {active && (
        <>
          <text x="5" y="2" fontSize="4" fill="currentColor" textAnchor="middle">A</text>
          <text x="10" y="2" fontSize="4" fill="currentColor" textAnchor="middle">B</text>
          <text x="15" y="2" fontSize="4" fill="currentColor" textAnchor="middle">C</text>
        </>
      )}
    </svg>
  );
}

export default BoardControls;
