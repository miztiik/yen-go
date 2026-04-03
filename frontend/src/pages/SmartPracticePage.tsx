/**
 * SmartPracticePage — Adaptive practice targeting weak techniques.
 * @module pages/SmartPracticePage
 *
 * Uses progressAnalytics to identify weakest techniques, fetches matching
 * puzzles via SQLite, filters out already-solved ones, and presents them
 * through PuzzleSetPlayer.
 */

import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { PageLayout } from '../components/Layout/PageLayout';
import { PageHeader } from '../components/shared/PageHeader';
import { PuzzleSetPlayer } from '../components/PuzzleSetPlayer';
import type { PuzzleSetLoader, PuzzleEntryMeta, LoaderStatus } from '../services/puzzleLoaders';
import { fetchSGFContent, type LoaderResult } from '../services/puzzleLoader';
import { puzzleRowToEntry } from '../services/puzzleLoaders';
import { getWeakestTechniques, type TechniqueStats } from '../services/progressAnalytics';
import { getPuzzlesByTag } from '../services/puzzleQueryService';
import { init as initDb } from '../services/sqliteService';
import { tagSlugToId } from '../services/configService';
import { isPuzzleCompleted } from '../services/progressTracker';
import { addToRetryQueue } from '../services/retryQueue';
import { Button } from '../components/shared/Button';

// ============================================================================
// Constants
// ============================================================================

const MAX_PUZZLES = 15;

// ============================================================================
// SmartPracticeLoader
// ============================================================================

/**
 * Simple inline PuzzleSetLoader wrapping a pre-built list of puzzle entries.
 * Fetches SGF on demand via fetchSGFContent.
 */
class SmartPracticeLoader implements PuzzleSetLoader {
  private entries: PuzzleEntryMeta[];
  private status: LoaderStatus = 'idle';

  constructor(entries: PuzzleEntryMeta[]) {
    this.entries = entries;
  }

  load(): Promise<void> {
    this.status = this.entries.length > 0 ? 'ready' : 'empty';
    return Promise.resolve();
  }

  getStatus(): LoaderStatus {
    return this.status;
  }

  getTotal(): number {
    return this.entries.length;
  }

  getEntry(index: number): PuzzleEntryMeta | null {
    return this.entries[index] ?? null;
  }

  getPuzzleSgf(index: number): Promise<LoaderResult<string>> {
    const entry = this.entries[index];
    if (!entry) {
      return Promise.resolve({ success: false, error: 'not_found' as const, message: 'No entry at index' });
    }
    return fetchSGFContent(entry.path);
  }

  getError(): string | null {
    return null;
  }
}

// ============================================================================
// Helpers
// ============================================================================

/** Fisher-Yates shuffle (in-place). */
function shuffle<T>(arr: T[]): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    const tmp = arr[i] as T;
    arr[i] = arr[j] as T;
    arr[j] = tmp;
  }
  return arr;
}

// ============================================================================
// Page States
// ============================================================================

type PageState =
  | { phase: 'loading' }
  | { phase: 'empty'; techniques: TechniqueStats[] }
  | { phase: 'playing'; loader: SmartPracticeLoader; techniques: TechniqueStats[] }
  | { phase: 'complete'; techniques: TechniqueStats[] };

// ============================================================================
// Component
// ============================================================================

export interface SmartPracticePageProps {
  onBack: () => void;
  techniques?: readonly string[];
}

export const SmartPracticePage: FunctionalComponent<SmartPracticePageProps> = ({
  onBack,
  techniques: techniquesProp,
}) => {
  const [state, setState] = useState<PageState>({ phase: 'loading' });

  useEffect(() => {
    let cancelled = false;

    async function init() {
      // 1. Determine target techniques
      let techStats: TechniqueStats[];
      if (techniquesProp && techniquesProp.length > 0) {
        // Use prop-provided technique slugs — fetch their stats for display
        const allWeak = await getWeakestTechniques(10);
        techStats = allWeak.filter(t => techniquesProp.includes(t.tagSlug));
        // If none matched from analytics, create minimal entries for resolution
        if (techStats.length === 0) {
          techStats = techniquesProp.map(slug => ({
            tagId: tagSlugToId(slug) ?? 0,
            tagSlug: slug,
            tagName: slug,
            correct: 0,
            total: 0,
            accuracy: 0,
            avgTimeMs: 0,
            trend30d: 0,
            lowData: true,
          }));
        }
      } else {
        techStats = await getWeakestTechniques(3);
      }

      if (cancelled) return;

      // 2. Gather puzzles for each technique
      await initDb();
      const seen = new Set<string>();
      const allEntries: PuzzleEntryMeta[] = [];

      for (const tech of techStats) {
        const tagId = tagSlugToId(tech.tagSlug);
        if (tagId === undefined) continue;
        const rows = getPuzzlesByTag(tagId);
        for (const row of rows) {
          const entry = puzzleRowToEntry(row);
          if (seen.has(entry.id)) continue;
          if (isPuzzleCompleted(entry.id)) continue;
          seen.add(entry.id);
          allEntries.push({ id: entry.id, path: entry.path, level: entry.level });
        }
      }

      if (cancelled) return;

      // 3. Shuffle and take first N
      const selected = shuffle(allEntries).slice(0, MAX_PUZZLES);

      if (selected.length === 0) {
        setState({ phase: 'empty', techniques: techStats });
        return;
      }

      // 4. Build loader
      const loader = new SmartPracticeLoader(selected);
      setState({ phase: 'playing', loader, techniques: techStats });
    }

    void init();
    return () => { cancelled = true; };
  }, [techniquesProp]);

  const handlePuzzleComplete = useCallback((puzzleId: string, isCorrect: boolean) => {
    if (!isCorrect) {
      let context = 'smart-practice';
      if (state.phase === 'playing') {
        const first = state.techniques[0];
        if (first) context = first.tagSlug;
      }
      addToRetryQueue(puzzleId, context);
    }
  }, [state]);

  const handleAllComplete = useCallback(() => {
    if (state.phase === 'playing') {
      setState({ phase: 'complete', techniques: state.techniques });
    }
  }, [state]);

  // ============================================================================
  // Render
  // ============================================================================

  if (state.phase === 'loading') {
    return (
      <PageLayout>
        <PageHeader
          title="Smart Practice"
          onBack={onBack}
        />
        <div className="flex flex-1 items-center justify-center">
          <p className="text-[var(--color-text-secondary)]">Analyzing your progress...</p>
        </div>
      </PageLayout>
    );
  }

  if (state.phase === 'empty') {
    return (
      <PageLayout>
        <PageHeader
          title="Smart Practice"
          onBack={onBack}
        />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-lg font-medium text-[var(--color-text-primary)]">
            All caught up!
          </p>
          <p className="text-[var(--color-text-secondary)]">
            No unsolved puzzles found for your weak techniques. Keep practicing to unlock more!
          </p>
          <Button onClick={onBack} variant="secondary">
            Back
          </Button>
        </div>
      </PageLayout>
    );
  }

  if (state.phase === 'complete') {
    const techNames = state.techniques.map(t => t.tagName).join(', ');
    return (
      <PageLayout>
        <PageHeader
          title="Smart Practice"
          onBack={onBack}
        />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
          <p className="text-lg font-medium text-[var(--color-text-primary)]">
            Session Complete
          </p>
          <p className="text-[var(--color-text-secondary)]">
            Focused techniques: {techNames}
          </p>
          <Button onClick={onBack} variant="secondary">
            Done
          </Button>
        </div>
      </PageLayout>
    );
  }

  // phase === 'playing'
  return (
    <div>
      <PuzzleSetPlayer
        loader={state.loader}
        onBack={onBack}
        onPuzzleComplete={handlePuzzleComplete}
        onAllComplete={handleAllComplete}
        mode="training"
      />
    </div>
  );
};
