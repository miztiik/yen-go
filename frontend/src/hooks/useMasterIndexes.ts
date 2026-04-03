/**
 * Hook to load level and tag master index entries from the SQLite search database.
 * @module hooks/useMasterIndexes
 *
 * Builds LevelMasterEntry[] and TagMasterEntry[] from SQL aggregate queries.
 * Used by TechniqueBrowsePage and TrainingBrowsePage for reactive puzzle
 * counts and cross-dimensional filtering.
 */

import { useState, useEffect } from 'preact/hooks';
import type { LevelMasterEntry, TagMasterEntry } from '@/types/indexes';
import { init as initDb } from '@/services/sqliteService';
import {
  getLevelCounts,
  getTagCounts,
  getTagDistributionByLevel,
  getLevelDistributionByTag,
} from '@/services/puzzleQueryService';
import { getAllLevels, tagIdToSlug, getTagMeta } from '@/services/configService';

interface MasterIndexes {
  readonly levelMasterEntries: readonly LevelMasterEntry[];
  readonly tagMasterEntries: readonly TagMasterEntry[];
  readonly isLoading: boolean;
}

/**
 * Load level and tag master index entries from the SQLite search database.
 *
 * Level entries include per-tag distribution counts.
 * Tag entries include per-level distribution counts.
 */
export function useMasterIndexes(): MasterIndexes {
  const [levelMasterEntries, setLevelEntries] = useState<readonly LevelMasterEntry[]>([]);
  const [tagMasterEntries, setTagEntries] = useState<readonly TagMasterEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        await initDb();

        const allLevels = getAllLevels();
        const levelCounts = getLevelCounts();
        const tagCounts = getTagCounts();
        const tagsByLevel = getTagDistributionByLevel();
        const levelsByTag = getLevelDistributionByTag();

        if (cancelled) return;

        const levels: LevelMasterEntry[] = allLevels.map((l) => ({
          id: l.id,
          name: l.name,
          slug: l.slug,
          count: levelCounts[l.id] ?? 0,
          paginated: false,
          tags: tagsByLevel[l.id] ?? {},
        }));

        const tags: TagMasterEntry[] = Object.entries(tagCounts).map(([idStr, count]) => {
          const tagId = Number(idStr);
          const slug = tagIdToSlug(tagId);
          const tagMetaInfo = getTagMeta(slug);
          return {
            id: tagId,
            name: tagMetaInfo?.name ?? slug,
            slug,
            count,
            paginated: false,
            levels: levelsByTag[tagId] ?? {},
          };
        });

        if (!cancelled) {
          setLevelEntries(levels);
          setTagEntries(tags);
          setIsLoading(false);
        }
      } catch (err) {
        console.error('[useMasterIndexes] Error loading from database:', err);
        if (!cancelled) setIsLoading(false);
      }
    };

    void load();
    return () => { cancelled = true; };
  }, []);

  return { levelMasterEntries, tagMasterEntries, isLoading };
}
