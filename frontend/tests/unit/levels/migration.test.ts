/**
 * Tests for level system migration
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  needsMigration,
  getCurrentSchemaVersion,
  mapOldToNewLevel,
  migrateProgressData,
  runMigrationIfNeeded,
  backupProgressData,
  restoreFromBackup,
} from '../../../src/lib/levels/migration';

// LEVEL_SCHEMA_VERSION is now internal to migration.ts.
// Use the public contract (needsMigration, runMigrationIfNeeded) instead.
const LEVEL_SCHEMA_VERSION = 2;

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    get length() {
      return Object.keys(store).length;
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('needsMigration', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('returns false when no progress data exists', () => {
    expect(needsMigration()).toBe(false);
  });

  it('returns true for version 1 data', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ schemaVersion: 1, puzzleLevels: {} })
    );
    expect(needsMigration()).toBe(true);
  });

  it('returns false for current version data', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ schemaVersion: LEVEL_SCHEMA_VERSION, puzzleLevels: {} })
    );
    expect(needsMigration()).toBe(false);
  });

  it('returns true when schemaVersion is missing (legacy data)', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ puzzleLevels: {} })
    );
    expect(needsMigration()).toBe(true);
  });
});

describe('getCurrentSchemaVersion', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('returns 0 when no data exists', () => {
    expect(getCurrentSchemaVersion()).toBe(0);
  });

  it('returns 1 for legacy data without version', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ puzzleLevels: {} })
    );
    expect(getCurrentSchemaVersion()).toBe(1);
  });

  it('returns stored version', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ schemaVersion: 2 })
    );
    expect(getCurrentSchemaVersion()).toBe(2);
  });
});

describe('mapOldToNewLevel', () => {
  it('maps old level 1 to new level 2', () => {
    expect(mapOldToNewLevel(1)).toBe(2);
  });

  it('maps old level 2 to new level 4', () => {
    expect(mapOldToNewLevel(2)).toBe(4);
  });

  it('maps old level 3 to new level 5', () => {
    expect(mapOldToNewLevel(3)).toBe(5);
  });

  it('maps old level 4 to new level 7', () => {
    expect(mapOldToNewLevel(4)).toBe(7);
  });

  it('maps old level 5 to new level 9', () => {
    expect(mapOldToNewLevel(5)).toBe(9);
  });

  it('uses rank for precise mapping when available', () => {
    // 8k should map to level 5
    expect(mapOldToNewLevel(3, '8k')).toBe(5);
    // 3d should map to level 7
    expect(mapOldToNewLevel(4, '3d')).toBe(7);
  });

  it('falls back to default when rank is invalid', () => {
    expect(mapOldToNewLevel(3, 'invalid')).toBe(5);
  });

  it('returns level 5 for unknown old levels', () => {
    expect(mapOldToNewLevel(99)).toBe(5);
  });
});

describe('migrateProgressData', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('returns empty stats when no data exists', () => {
    const stats = migrateProgressData();
    expect(stats.totalPuzzles).toBe(0);
    expect(stats.puzzlesMigrated).toBe(0);
  });

  it('migrates puzzle levels correctly', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({
        schemaVersion: 1,
        puzzleLevels: {
          'puzzle-1': 1, // -> 2
          'puzzle-2': 3, // -> 5
          'puzzle-3': 5, // -> 9
        },
        solvedPuzzles: { 'puzzle-1': true },
      })
    );

    const stats = migrateProgressData();

    expect(stats.totalPuzzles).toBe(3);
    expect(stats.puzzlesMigrated).toBe(3);
    expect(stats.errors).toHaveLength(0);

    // Check the migrated data
    const migrated = JSON.parse(localStorageMock.getItem('yengo_progress')!);
    expect(migrated.schemaVersion).toBe(LEVEL_SCHEMA_VERSION);
    expect(migrated.puzzleLevels['puzzle-1']).toBe(2);
    expect(migrated.puzzleLevels['puzzle-2']).toBe(5);
    expect(migrated.puzzleLevels['puzzle-3']).toBe(9);
  });

  it('preserves solvedPuzzles during migration', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({
        schemaVersion: 1,
        puzzleLevels: { 'puzzle-1': 1 },
        solvedPuzzles: { 'puzzle-1': true, 'puzzle-2': true },
      })
    );

    migrateProgressData();

    const migrated = JSON.parse(localStorageMock.getItem('yengo_progress')!);
    expect(migrated.solvedPuzzles).toEqual({ 'puzzle-1': true, 'puzzle-2': true });
  });

  it('creates backup before migration', () => {
    const originalData = {
      schemaVersion: 1,
      puzzleLevels: { 'puzzle-1': 1 },
    };
    localStorageMock.setItem('yengo_progress', JSON.stringify(originalData));

    migrateProgressData();

    const backup = localStorageMock.getItem('yengo_progress_backup');
    expect(backup).not.toBeNull();
    expect(JSON.parse(backup!)).toEqual(originalData);
  });

  it('logs migration stats', () => {
    const consoleSpy = vi.spyOn(console, 'info').mockImplementation(() => {});

    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({
        schemaVersion: 1,
        puzzleLevels: { 'puzzle-1': 1 },
      })
    );

    migrateProgressData();

    expect(consoleSpy).toHaveBeenCalledWith(
      '[YenGo Migration] Completed:',
      expect.any(Object)
    );

    consoleSpy.mockRestore();
  });

  it('tracks level changes in stats', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({
        schemaVersion: 1,
        puzzleLevels: {
          'puzzle-1': 1,
          'puzzle-2': 1,
          'puzzle-3': 3,
        },
      })
    );

    const stats = migrateProgressData();

    expect(stats.levelChanges['1->2']).toBe(2);
    expect(stats.levelChanges['3->5']).toBe(1);
  });
});

describe('runMigrationIfNeeded', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('returns null when no migration needed', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ schemaVersion: LEVEL_SCHEMA_VERSION })
    );
    expect(runMigrationIfNeeded()).toBeNull();
  });

  it('performs migration when needed', () => {
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({
        schemaVersion: 1,
        puzzleLevels: { 'puzzle-1': 3 },
      })
    );

    const stats = runMigrationIfNeeded();

    expect(stats).not.toBeNull();
    expect(stats!.puzzlesMigrated).toBe(1);
  });
});

describe('backup and restore', () => {
  beforeEach(() => {
    localStorageMock.clear();
  });

  it('backupProgressData creates backup', () => {
    localStorageMock.setItem('yengo_progress', JSON.stringify({ test: 'data' }));
    
    const result = backupProgressData();
    
    expect(result).toBe(true);
    expect(localStorageMock.getItem('yengo_progress_backup')).not.toBeNull();
  });

  it('restoreFromBackup restores data', () => {
    localStorageMock.setItem(
      'yengo_progress_backup',
      JSON.stringify({ original: 'data' })
    );
    localStorageMock.setItem(
      'yengo_progress',
      JSON.stringify({ modified: 'data' })
    );

    const result = restoreFromBackup();

    expect(result).toBe(true);
    const restored = JSON.parse(localStorageMock.getItem('yengo_progress')!);
    expect(restored).toEqual({ original: 'data' });
  });

  it('restoreFromBackup returns false when no backup', () => {
    expect(restoreFromBackup()).toBe(false);
  });
});
