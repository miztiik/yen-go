import type { FunctionalComponent, JSX } from 'preact';
import { useMemo } from 'preact/hooks';
import { TechniqueCard, type TechniqueInfo } from './TechniqueCard';
import type { TechniqueStats } from '../../models/collection';
import { EmptyState } from '@/components/shared/GoQuote';
import { ObjectiveFlagIcon } from '../shared/icons/ObjectiveFlagIcon';
import { TechniqueKeyIcon } from '../shared/icons/TechniqueKeyIcon';
import { TesujiIcon } from '../shared/icons/TesujiIcon';

/** Category display labels, ordering, and SVG icons */
const CATEGORY_SECTIONS: Array<{ id: string; label: string; icon: JSX.Element }> = [
  { id: 'objective', label: 'Objectives', icon: <ObjectiveFlagIcon size={18} /> },
  { id: 'technique', label: 'Techniques', icon: <TechniqueKeyIcon size={18} /> },
  { id: 'tesuji', label: 'Tesuji Patterns', icon: <TesujiIcon size={18} /> },
];

/** Accent palette with cascade + mode-specific fallback */
const ACCENT = {
  text: 'var(--color-accent, var(--color-mode-technique-text))',
  light: 'var(--color-accent-light, var(--color-mode-technique-light))',
  bg: 'var(--color-accent-bg, var(--color-mode-technique-bg))',
  border: 'var(--color-accent-border, var(--color-mode-technique-border))',
} as const;

export interface TechniqueListProps {
  /** All available techniques loaded from config */
  techniques: readonly TechniqueInfo[];
  /** User's technique-specific stats */
  stats: Readonly<Record<string, TechniqueStats>>;
  /** Filter to only show specific categories */
  categoryFilter?: 'tesuji' | 'technique' | 'objective' | 'all';
  /** Sort order */
  sortBy?: 'name' | 'puzzleCount';
  /** Callback when user selects a technique */
  onSelectTechnique: (techniqueId: string) => void;
}

/**
 * Displays a grid of technique cards for focused practice.
 * Filters by category and sorts by various criteria.
 *
 * Redesigned per FR-044, FR-046: Tailwind-only, theme colors.
 */
export const TechniqueList: FunctionalComponent<TechniqueListProps> = ({
  techniques,
  stats,
  categoryFilter = 'all',
  sortBy = 'name',
  onSelectTechnique,
}) => {
  const filteredAndSorted = useMemo(() => {
    // Filter by category
    const filtered =
      categoryFilter === 'all'
        ? techniques
        : techniques.filter((t) => t.category === categoryFilter);

    // Sort
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'puzzleCount':
          return b.puzzleCount - a.puzzleCount;
        default:
          return 0;
      }
    });

    return sorted;
  }, [techniques, categoryFilter, sortBy]);

  if (filteredAndSorted.length === 0) {
    return (
      <EmptyState
        message={
          categoryFilter === 'all'
            ? 'No techniques available.'
            : `No ${categoryFilter} techniques available.`
        }
      />
    );
  }

  // When showing all categories, render grouped sections with headers
  if (categoryFilter === 'all') {
    return (
      <div>
        {CATEGORY_SECTIONS.map((section) => {
          const sectionItems = filteredAndSorted.filter((t) => t.category === section.id);
          if (sectionItems.length === 0) return null;
          return (
            <div key={section.id} className="mb-8">
              {/* Section header — bold with emoji icon and count badge */}
              <div className="mx-2 mb-4 flex items-center gap-3">
                <span
                  className="flex items-center justify-center rounded-full"
                  style={{
                    width: '36px',
                    height: '36px',
                    backgroundColor: ACCENT.light,
                    color: ACCENT.text,
                  }}
                >
                  {section.icon}
                </span>
                <h2 className="m-0 text-xl font-bold text-[var(--color-text-primary)]">
                  {section.label}
                </h2>
                <span
                  className="rounded-lg px-2.5 py-1 text-xs font-bold"
                  style={{ backgroundColor: ACCENT.bg, color: ACCENT.text }}
                >
                  {sectionItems.length}
                </span>
              </div>
              <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-6 px-2">
                {sectionItems.map((technique) => (
                  <TechniqueCard
                    key={technique.id}
                    technique={technique}
                    stats={stats[technique.id]}
                    onSelect={onSelectTechnique}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Single category: flat grid
  return (
    <div className="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-6 p-2">
      {filteredAndSorted.map((technique) => (
        <TechniqueCard
          key={technique.id}
          technique={technique}
          stats={stats[technique.id]}
          onSelect={onSelectTechnique}
        />
      ))}
    </div>
  );
};

/** Sort option type for TechniqueList sortBy prop */
export type TechniqueSortOption = 'name' | 'puzzleCount';

export default TechniqueList;
