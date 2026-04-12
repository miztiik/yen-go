/**
 * TileIcons - Colorful SVG icons for home tiles
 * @module components/Home/TileIcons
 *
 * All icons are inline SVG components — NO Unicode emoji in rendered UI.
 * Each icon uses its page's accent color for visual identity.
 *
 * Covers: T046, T-U27m
 */

import type { JSX } from 'preact';
import { CalendarIcon } from '../shared/icons/CalendarIcon';
import { LightningIcon } from '../shared/icons/LightningIcon';
import { BookIcon } from '../shared/icons/BookIcon';
import { GraduationCapIcon } from '../shared/icons/GraduationCapIcon';
import { DiceIcon } from '../shared/icons/DiceIcon';
import { SeedlingIcon } from '../shared/icons/SeedlingIcon';

export interface TileIconProps {
  /** Size of the icon */
  size?: 'sm' | 'md' | 'lg' | undefined;
  /** Custom className */
  className?: string | undefined;
}

const sizeMap: Record<'sm' | 'md' | 'lg', number> = {
  sm: 24,
  md: 32,
  lg: 40,
};

/**
 * Daily Challenge Icon - Calendar (amber)
 */
export function DailyIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span class={`tile-icon tile-icon--daily ${className}`} role="img" aria-label="Daily Challenge">
      <CalendarIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Puzzle Rush Icon - Lightning bolt (rose)
 */
export function RushIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span class={`tile-icon tile-icon--rush ${className}`} role="img" aria-label="Puzzle Rush">
      <LightningIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Collections Icon - Open book (purple)
 */
export function CollectionsIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span
      class={`tile-icon tile-icon--collections ${className}`}
      role="img"
      aria-label="Collections"
    >
      <BookIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Training Icon - Graduation cap (blue)
 */
export function TrainingIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span class={`tile-icon tile-icon--training ${className}`} role="img" aria-label="Training">
      <GraduationCapIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Technique Icon - Target/Bullseye (emerald)
 * Note: Uses a custom SVG target icon since no TesujiIcon shared icon exists for this purpose.
 */
export function TechniqueIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  const px = sizeMap[size];
  return (
    <span class={`tile-icon tile-icon--technique ${className}`} role="img" aria-label="Technique">
      <svg
        width={px}
        height={px}
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--color-mode-technique-border, #10b981)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle
          cx="12"
          cy="12"
          r="2"
          fill="var(--color-mode-technique-border, #10b981)"
          stroke="none"
        />
      </svg>
    </span>
  );
}

/**
 * Random Icon - Dice (indigo)
 */
export function RandomIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span class={`tile-icon tile-icon--random ${className}`} role="img" aria-label="Random">
      <DiceIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Learning Icon - Seedling (teal/cyan)
 */
export function LearningIcon({ size = 'md', className = '' }: TileIconProps): JSX.Element {
  return (
    <span class={`tile-icon tile-icon--learning ${className}`} role="img" aria-label="Learn Go">
      <SeedlingIcon size={sizeMap[size]} />
    </span>
  );
}

/**
 * Get icon component by variant name
 */
export function getTileIcon(
  variant: 'daily' | 'rush' | 'collections' | 'training' | 'technique' | 'random' | 'learning',
  props?: TileIconProps
): JSX.Element {
  const iconProps = props ?? {};
  switch (variant) {
    case 'daily':
      return <DailyIcon {...iconProps} />;
    case 'rush':
      return <RushIcon {...iconProps} />;
    case 'collections':
      return <CollectionsIcon {...iconProps} />;
    case 'training':
      return <TrainingIcon {...iconProps} />;
    case 'technique':
      return <TechniqueIcon {...iconProps} />;
    case 'random':
      return <RandomIcon {...iconProps} />;
    case 'learning':
      return <LearningIcon {...iconProps} />;
  }
}

export default {
  DailyIcon,
  RushIcon,
  CollectionsIcon,
  TrainingIcon,
  TechniqueIcon,
  RandomIcon,
  LearningIcon,
  getTileIcon,
};
