/**
 * Shared type definitions for YenGo goban integration.
 * These types are used across all extensions (hooks, components, lib modules).
 */

/** 9-level difficulty system */
import type { LevelSlug } from '../lib/levels/config';
import type { ContentTypeSlug } from '../services/configService';
import type { CollectionMembership } from '../lib/sgf-metadata';

/** Metadata extracted from YenGo custom SGF properties (YG, YT, YH, YK, YO, YL, YQ, YM) */
export interface YenGoMetadata {
  /** Difficulty level from YG property */
  readonly level: LevelSlug;
  /** Tags from YT property (comma-separated in SGF, parsed to array) */
  readonly tags: readonly string[];
  /** Progressive hints from YH property (pipe-delimited in SGF, parsed to array, max 3) */
  readonly hints: readonly string[];
  /** Ko context from YK property */
  readonly koContext: "none" | "direct" | "approach";
  /** Move order flexibility from YO property */
  readonly moveOrder: "strict" | "flexible";
  /** Collection membership from YL property (comma-separated slugs, schema v10) */
  readonly collections: readonly string[];
  /** Structured collection memberships with chapter/position from YL property */
  readonly collectionMemberships: readonly CollectionMembership[];
  /** First correct move SGF coordinate extracted from solution tree (e.g. 'dp'), null for pass/unknown */
  readonly firstCorrectMove: string | null;
  /** Quality level (1-5) from YQ property q field. 0 = unscored. */
  readonly quality: number;
  /** Content type from YM property ct field. */
  readonly contentType: ContentTypeSlug;
}

/** Transform toggle state for puzzle board */
export interface TransformSettings {
  /** Flip horizontally (mirror left-right) */
  readonly flipH: boolean;
  /** Flip vertically (mirror top-bottom) */
  readonly flipV: boolean;
  /** Flip along the main diagonal (transpose: swap x,y coordinates) */
  readonly flipDiag: boolean;
  /** Clockwise rotation in degrees (0 = none, 90/180/270) */
  readonly rotation: 0 | 90 | 180 | 270;
  /** Swap black and white colors */
  readonly swapColors: boolean;
}

/** Result of SGF pre-processing: extracted metadata + cleaned SGF for goban */
export interface PreprocessedPuzzle {
  /** Raw SGF with YenGo properties stripped (safe to pass to goban) */
  readonly cleanedSgf: string;
  /** Extracted YenGo metadata */
  readonly metadata: YenGoMetadata;
  /** Original raw SGF (preserved for reference) */
  readonly originalSgf: string;
}

/** Puzzle solve status tracked in progress */
export type PuzzleSolveState =
  | "unsolved"
  | "solving"
  | "solved"
  | "solved-with-hints"
  | "failed"
  | "review";

/** Puzzle Rush session duration in seconds (60–1800, i.e., 1–30 min). */
export type RushDuration = number;

/** Puzzle Rush session state */
export interface RushSessionState {
  readonly isActive: boolean;
  readonly duration: RushDuration;
  readonly timeRemaining: number;
  readonly lives: number;
  readonly maxLives: number;
  readonly score: number;
  readonly puzzlesSolved: number;
  readonly puzzlesFailed: number;
  readonly currentStreak: number;
}

/** Board bounds for partial board display (corner/side tsumego) */
export interface GobanBounds {
  readonly top: number;
  readonly left: number;
  readonly bottom: number;
  readonly right: number;
}

/** Rush puzzle entry with level and tags — used by Rush and Random modes. */
export interface RushPuzzle {
  readonly id: string;
  readonly path: string;
  readonly level: string;
  readonly tags: readonly string[];
}

/**
 * Configuration for creating a YenGo puzzle instance.
 * Used by puzzle-config.ts to build the GobanConfig object.
 * SVGRenderer is the default renderer; GobanCanvas is automatic fallback.
 */
export interface YenGoPuzzleConfig {
  /** Raw SGF string (before pre-processing) */
  readonly rawSgf: string;
  /** Board container element */
  readonly boardDiv: HTMLElement;
  /** Move tree container element (optional) */
  readonly moveTreeContainer?: HTMLElement;
  /** Optional transform settings to apply */
  readonly transforms?: TransformSettings;
  /** Optional board bounds for partial display */
  readonly bounds?: GobanBounds;
}

/** Renderer preference stored in localStorage */
export type RendererPreference = "auto" | "svg" | "canvas";

/** localStorage key for renderer preference */
export const RENDERER_PREFERENCE_KEY = "yengo-renderer-preference" as const;


