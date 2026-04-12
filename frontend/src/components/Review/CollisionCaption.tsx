/**
 * Collision Caption Component
 * @module components/Review/CollisionCaption
 *
 * Displays information about move collisions at same positions (FR-015, FR-016).
 * Shows when multiple moves are played at the same intersection after captures.
 *
 * Example: "7 = 3 (recapture)" means move 7 is at the same position as move 3.
 *
 * Constitution Compliance:
 * - IX. Accessibility: Clear, readable format
 * - X. Design Philosophy: Non-intrusive, informational
 */

import type { JSX } from 'preact';
import type { MoveCollision } from '@models/SolutionPresentation';
import { formatCollisionCaption } from '@lib/presentation/numberedSolution';

/**
 * Props for CollisionCaption component.
 */
export interface CollisionCaptionProps {
  /** List of collisions to display */
  collisions: readonly MoveCollision[];
  /** Current frame (to filter collisions up to this frame) */
  currentFrame?: number;
  /** CSS class override */
  className?: string;
}

/**
 * CollisionCaption component - displays move collision information.
 *
 * @example
 * ```tsx
 * <CollisionCaption
 *   collisions={[
 *     { laterMove: 7, originalMove: 3, coord: { x: 2, y: 2 } }
 *   ]}
 *   currentFrame={10}
 * />
 * // Displays: "7 = 3"
 * ```
 */
export function CollisionCaption({
  collisions,
  currentFrame,
  className,
}: CollisionCaptionProps): JSX.Element | null {
  // Filter collisions up to current frame if specified
  const visibleCollisions =
    currentFrame !== undefined ? collisions.filter((c) => c.laterMove <= currentFrame) : collisions;

  if (visibleCollisions.length === 0) {
    return null;
  }

  // Format the collision caption
  const captionText = formatCollisionCaption(visibleCollisions);

  return (
    <div
      className={`collision-caption ${className ?? ''}`}
      role="note"
      aria-live="polite"
      aria-label={`Move collisions: ${captionText}`}
    >
      <span className="collision-caption__icon" aria-hidden="true">
        ⊙
      </span>
      <span className="collision-caption__text">{captionText}</span>
    </div>
  );
}

/**
 * CollisionList component - detailed list view of collisions.
 * Shows each collision with explanation text.
 */
export function CollisionList({
  collisions,
  className,
}: {
  collisions: readonly MoveCollision[];
  className?: string;
}): JSX.Element | null {
  if (collisions.length === 0) {
    return null;
  }

  return (
    <ul
      className={`collision-list ${className ?? ''}`}
      role="list"
      aria-label="Move collision details"
    >
      {collisions.map((collision) => (
        <li
          key={`${collision.laterMove}-${collision.originalMove}`}
          className="collision-list__item"
        >
          <span className="collision-list__moves">
            {collision.laterMove} = {collision.originalMove}
          </span>
          {collision.reason && <span className="collision-list__reason">({collision.reason})</span>}
        </li>
      ))}
    </ul>
  );
}

export default CollisionCaption;
