/**
 * Tags Service - Runtime fetch of tags configuration
 *
 * Fetches tags.json at runtime (not build-time) so tag changes
 * don't require frontend rebuild.
 *
 * The tags.json file is the SINGLE SOURCE OF TRUTH for:
 * - Tag IDs (canonical names)
 * - Display names (for UI)
 * - Aliases (for normalization)
 * - Categories (for grouping)
 */

/** Tag definition from tags.json (schema v8.0: id is numeric, slug is the string key) */
export interface TagDefinition {
  readonly id: number;
  readonly slug: string;
  readonly name: string;
  readonly category: 'objective' | 'technique' | 'tesuji';
  readonly description: string;
  readonly aliases: readonly string[];
}

/** Tags configuration structure */
export interface TagsConfig {
  readonly version: string;
  readonly description: string;
  readonly last_updated: string;
  readonly tags: Record<string, TagDefinition>;
}

/** Cached tags configuration */
let tagsCache: TagsConfig | null = null;

/** Promise for in-flight fetch (prevents duplicate requests) */
let fetchPromise: Promise<TagsConfig> | null = null;

/**
 * Get tags configuration (cached after first load)
 *
 * Uses prefetch hint in index.html for early loading.
 * Safe to call multiple times - will return cached value.
 */
export async function getTagsConfig(): Promise<TagsConfig> {
  // Return cached value if available
  if (tagsCache) {
    return tagsCache;
  }

  // Return in-flight promise if fetch already started
  if (fetchPromise) {
    return fetchPromise;
  }

  // Start fetch
  fetchPromise = fetchTagsConfig();

  try {
    tagsCache = await fetchPromise;
    return tagsCache;
  } finally {
    fetchPromise = null;
  }
}

/**
 * Fetch tags configuration from server
 */
async function fetchTagsConfig(): Promise<TagsConfig> {
  try {
    const { safeFetchJson } = await import('@/utils/safeFetchJson');
    const { configUrl } = await import('@/config/constants');
    return await safeFetchJson<TagsConfig>(configUrl('tags'));
  } catch (error) {
    console.error(`Failed to fetch tags.json:`, error);
    // Return fallback minimal config
    return getFallbackConfig();
  }
}

/**
 * Get list of all tag IDs
 */
export async function getTagIds(): Promise<string[]> {
  const config = await getTagsConfig();
  return Object.keys(config.tags);
}

/**
 * Get tag display name for UI
 */
export async function getTagDisplayName(tagId: string): Promise<string> {
  const config = await getTagsConfig();
  const tag = config.tags[tagId];
  return tag?.name ?? tagId.replace(/-/g, ' ');
}

/**
 * Synchronous access to cached tags (returns null if not loaded)
 * Use this only after ensuring getTagsConfig() has been called
 */
export function getCachedTagsConfig(): TagsConfig | null {
  return tagsCache;
}

/**
 * Fallback config if fetch fails
 */
function getFallbackConfig(): TagsConfig {
  return {
    version: 'fallback',
    description: 'Fallback tags (fetch failed)',
    last_updated: new Date().toISOString(),
    tags: {
      'life-and-death': {
        id: 10,
        slug: 'life-and-death',
        name: 'Life & Death',
        category: 'objective',
        description: 'Core tsumego objective',
        aliases: ['killing', 'tsumego'],
      },
    },
  };
}
