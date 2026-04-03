/**
 * Centralized Constants Module — ONE file, all runtime paths.
 *
 * Every service that needs a path, sound, or config endpoint reads from here.
 * Changing a sound file or CDN path is a one-line edit in this file.
 *
 * Spec 127: FR-015, FR-016, US8
 * @module config/constants
 */

// ============================================================================
// Types
// ============================================================================

/** CDN and data paths. */
export interface PathConfig {
  cdnBase: string;
  configBase: string;
}

/** Sound file paths. */
export interface SoundConfig {
  stone: string;
  capture: string;
  correct: string;
  wrong: string;
  complete: string;
  click: string;
}

/** Config file paths loaded at boot. */
export interface ConfigPaths {
  levels: string;
  tags: string;
  tips: string;
}

/** Responsive breakpoints in pixels. */
export interface BreakpointConfig {
  mobile: number;
  desktop: number;
}

/** The centralized constants module. */
export interface AppConstantsType {
  paths: PathConfig;
  sounds: SoundConfig;
  config: ConfigPaths;
  breakpoints: BreakpointConfig;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Base URL path derived from Vite's `base` config.
 *
 * At build time `import.meta.env.BASE_URL` resolves to the value of
 * `base` in vite.config.ts (e.g. `'/yen-go/'`).  We strip the trailing
 * slash so path concatenation is simple: `${BASE}/foo` → `/yen-go/foo`.
 */
const BASE = import.meta.env.BASE_URL.replace(/\/$/, '');

export const APP_CONSTANTS: AppConstantsType = {
  paths: {
    cdnBase: `${BASE}/yengo-puzzle-collections`,
    configBase: `${BASE}/config`,
  },
  sounds: {
    stone: `${BASE}/sounds/move.ogg`,
    capture: `${BASE}/sounds/newStone.ogg`,
    correct: `${BASE}/sounds/success.webm`,
    wrong: `${BASE}/sounds/wrong.webm`,
    complete: `${BASE}/sounds/pling.webm`,
    click: `${BASE}/sounds/click.webm`,
  },
  config: {
    levels: `${BASE}/config/puzzle-levels.json`,
    tags: `${BASE}/config/tags.json`,
    tips: `${BASE}/config/go-tips.json`,
  },
  breakpoints: {
    mobile: 768,
    desktop: 1024,
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Build full CDN URL for a relative path.
 * @example cdnUrl('sgf/beginner/batch-0001/abc.sgf')
 */
export function cdnUrl(path: string): string {
  const clean = path.startsWith('/') ? path.slice(1) : path;
  return `${APP_CONSTANTS.paths.cdnBase}/${clean}`;
}

/**
 * Build SGF file URL.
 * @example sgfUrl('sgf/beginner/batch-0001/abc.sgf')
 */
export function sgfUrl(path: string): string {
  return cdnUrl(path);
}

/**
 * Get a sound file URL by name.
 * @example soundUrl('stone')
 */
export function soundUrl(name: keyof SoundConfig): string {
  return APP_CONSTANTS.sounds[name];
}

/**
 * Get a config file URL by name.
 * @example configUrl('levels')
 */
export function configUrl(name: keyof ConfigPaths): string {
  return APP_CONSTANTS.config[name];
}
