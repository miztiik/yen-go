/**
 * Boot — single idempotent entry point for the YenGo app.
 *
 * 5-step boot sequence:
 * 1. fetchConfigs   → Render BootLoading shell, then fetch levels + tags + tips
 * 2. cacheConfigs   → Cache results in module-level singleton
 * 3. cleanLegacy    → Delete legacy localStorage keys (NON-FATAL)
 * 4. initGoban      → Initialize Goban callbacks
 * 5. renderApp      → Render <App /> into #app
 *
 * On failure at steps 1,2,4,5: renders <BootError /> with retry button.
 * cleanLegacySettings (step 3) is NON-FATAL — localStorage errors are
 * swallowed so the app always proceeds to step 4.
 *
 * Spec 127: FR-036, US8, contracts/boot.ts
 * @module boot
 */

import { render } from 'preact';
import { h } from 'preact';
import { APP_CONSTANTS } from './config/constants';
import { BootLoading, BootError } from './components/Boot/BootScreens';
import { cleanLegacyKeys } from './hooks/useSettings';
import { initGoban } from './lib/goban-init';
import type { TagDefinition } from './services/tagsService';

// ============================================================================
// Types
// ============================================================================

/** Boot lifecycle states. */
export type BootState = 'idle' | 'loading' | 'ready' | 'error';

/** Cached config data loaded during boot — accessible globally after boot. */
export interface BootConfigs {
  levels: PuzzleLevel[];
  tags: TagDefinition[];
  tips: GoTip[];
}

/** Puzzle difficulty level from puzzle-levels.json. */
export interface PuzzleLevel {
  slug: string;
  name: string;
  rankRange: string;
  order: number;
}

/** Go tip from go-tips.json. */
export interface GoTip {
  text: string;
  category: 'tip' | 'proverb' | 'definition';
  levels: string[];
}

// ============================================================================
// Module-Level State
// ============================================================================

let bootState: BootState = 'idle';
let cachedConfigs: BootConfigs | null = null;

// ============================================================================
// Config Fetching + Validation
// ============================================================================

/** Valid tag categories for runtime validation. */
const VALID_TAG_CATEGORIES = new Set(['objective', 'technique', 'tesuji']);

/**
 * Fetch and validate all config files.
 * @throws Error with descriptive message on fetch or parse failure.
 */
async function fetchAndValidateConfigs(): Promise<BootConfigs> {
  const { safeFetchJson } = await import('@/utils/safeFetchJson');

  // Step 1: Fetch all configs in parallel (safeFetchJson handles ok+content-type+parse guards)
  const [levelsData, tagsData, tipsData] = await Promise.all([
    safeFetchJson<Record<string, unknown>>(APP_CONSTANTS.config.levels),
    safeFetchJson<Record<string, unknown>>(APP_CONSTANTS.config.tags),
    safeFetchJson<Record<string, unknown>>(APP_CONSTANTS.config.tips),
  ]);

  // Validate levels
  if (!levelsData.levels || !Array.isArray(levelsData.levels)) {
    throw new Error('puzzle-levels.json: missing levels array');
  }
  const levels: PuzzleLevel[] = levelsData.levels.map((l: Record<string, unknown>) => {
    if (!l.slug || typeof l.slug !== 'string')
      throw new Error('puzzle-levels.json: entry missing slug');
    if (!l.name || typeof l.name !== 'string')
      throw new Error(`puzzle-levels.json: "${l.slug}" missing name`);
    return {
      slug: l.slug,
      name: l.name,
      rankRange: (l.rankRange as string) ?? (l.rank_range as string) ?? '',
      order: typeof l.order === 'number' ? l.order : 0,
    };
  });

  // Validate tags (v6 dictionary format)
  if (!tagsData.schema_version) throw new Error('tags.json: missing schema_version field');
  if (!tagsData.tags || typeof tagsData.tags !== 'object') {
    throw new Error('tags.json: missing tags dictionary');
  }
  const tags: TagDefinition[] = Object.values(
    tagsData.tags as Record<string, Record<string, unknown>>
  ).map((entry) => {
    if (!entry.slug || typeof entry.slug !== 'string')
      throw new Error('tags.json: entry missing slug');
    if (!entry.name || typeof entry.name !== 'string')
      throw new Error(`tags.json: "${entry.slug}" missing name`);
    if (!entry.category || !VALID_TAG_CATEGORIES.has(entry.category as string)) {
      throw new Error(`tags.json: "${entry.slug}" invalid category "${String(entry.category)}"`);
    }
    if (!entry.description || typeof entry.description !== 'string') {
      throw new Error(`tags.json: "${entry.slug}" missing description`);
    }
    if (typeof entry.id !== 'number')
      throw new Error(`tags.json: "${entry.slug}" missing numeric id`);
    return {
      id: entry.id,
      slug: entry.slug,
      name: entry.name,
      category: entry.category as TagDefinition['category'],
      description: entry.description,
      aliases: Array.isArray(entry.aliases) ? (entry.aliases as string[]) : [],
    };
  });

  // Validate tips
  if (!tipsData.schema_version) throw new Error('go-tips.json: missing schema_version field');
  if (!tipsData.tips || !Array.isArray(tipsData.tips)) {
    throw new Error('go-tips.json: missing tips array');
  }
  const tips: GoTip[] = tipsData.tips.map((t: Record<string, unknown>) => ({
    text: String(t.text ?? ''),
    category: (['tip', 'proverb', 'definition'].includes(t.category as string)
      ? t.category
      : 'tip') as GoTip['category'],
    levels: Array.isArray(t.levels) ? (t.levels as string[]) : [],
  }));

  return { levels, tags, tips };
}

// ============================================================================
// Boot Sequence
// ============================================================================

/**
 * Boot the YenGo application.
 *
 * Idempotent — calling boot() when already booted is a no-op.
 * On failure, renders BootError with a retry button that calls boot() again.
 */
export async function boot(): Promise<void> {
  // Idempotent: if already ready, do nothing
  if (bootState === 'ready') return;

  const container = document.getElementById('app');
  if (!container) {
    throw new Error('Boot: #app container not found');
  }

  try {
    // Step 1+2: Fetch configs and cache (render loading shell first)
    bootState = 'loading';
    render(h(BootLoading, null), container);

    // T066: Parallelize config fetch and app module import (FR-030).
    // Safe because initializeProgressSystem is deferred to useEffect (T065).
    const [configs, appModule] = await Promise.all([
      cachedConfigs ? Promise.resolve(cachedConfigs) : fetchAndValidateConfigs(),
      import('./app'),
    ]);

    if (!cachedConfigs) {
      cachedConfigs = configs;
    }

    // Step 3: Clean legacy settings (NON-FATAL)
    try {
      cleanLegacyKeys();
    } catch {
      // Non-fatal — app continues with defaults
    }

    // Step 4: Initialize Goban callbacks
    initGoban();

    // Step 5: Render the app
    bootState = 'ready';
    render(h(appModule.App, null), container);
  } catch (error) {
    bootState = 'error';
    const message = error instanceof Error ? error.message : 'Unknown boot error';
    render(
      h(BootError, {
        message,
        onRetry: () => {
          bootState = 'idle';
          void boot();
        },
      }),
      container
    );
  }
}

/**
 * Get the cached boot configs.
 *
 * @throws Error if called before boot completes successfully.
 * @returns Cached BootConfigs with levels, tags, and tips.
 */
export function getBootConfigs(): BootConfigs {
  if (!cachedConfigs) {
    throw new Error('getBootConfigs() called before boot completed. Call boot() first.');
  }
  return cachedConfigs;
}

/**
 * Reset boot state for testing only.
 * @internal
 */
export function _resetBootForTesting(): void {
  bootState = 'idle';
  cachedConfigs = null;
}
