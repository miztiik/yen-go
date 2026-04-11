// @ts-nocheck
import type { FunctionalComponent } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { Modal } from '../shared/Modal';
import { TechniqueList, CategoryFilter, SortSelector, type SortSelectorProps } from './TechniqueList';
import type { TechniqueInfo } from './TechniqueCard';
import type { TechniqueStats } from '../../models/collection';

export interface TechniqueFocusModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTechnique: (techniqueId: string) => void;
  /** Pass technique stats from localStorage */
  stats: Readonly<Record<string, TechniqueStats>>;
}

/**
 * Parsed tag data from config/tags.json
 */
interface TagConfig {
  tags: Record<string, {
    id: string;
    name: string;
    category: string;
    description: string;
    aliases?: string[];
  }>;
}

/**
 * Modal for browsing and selecting techniques for focused practice.
 * Loads technique data from config/tags.json and displays with filtering.
 */
export const TechniqueFocusModal: FunctionalComponent<TechniqueFocusModalProps> = ({
  isOpen,
  onClose,
  onSelectTechnique,
  stats,
}) => {
  const [techniques, setTechniques] = useState<TechniqueInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<'all' | 'tesuji' | 'technique' | 'objective'>('all');
  const [sortBy, setSortBy] = useState<SortSelectorProps['selected']>('name');

  // Load techniques from config/tags.json
  useEffect(() => {
    if (!isOpen) return;

    const loadTechniques = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch tags.json from the config directory
        // In dev, this may be served from public or a static file
        const { safeFetchJson } = await import('@/utils/safeFetchJson');
        const data = await safeFetchJson<TagConfig>('/config/tags.json');
        
        // Transform tag config to TechniqueInfo array
        const techniqueList: TechniqueInfo[] = Object.values(data.tags)
          .filter((tag): tag is TagConfig['tags'][string] & { category: 'tesuji' | 'technique' | 'objective' } =>
            ['tesuji', 'technique', 'objective'].includes(tag.category)
          )
          .map((tag) => ({
            id: tag.id,
            name: tag.name,
            category: tag.category,
            description: tag.description,
            // Puzzle count will come from a separate index
            // For now, default to 0 until we have puzzle counts per tag
            puzzleCount: 0,
          }));

        setTechniques(techniqueList);
      } catch (err) {
        console.error('Error loading techniques:', err);
        setError('Failed to load techniques. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    void loadTechniques();
  }, [isOpen]);

  const handleSelectTechnique = useCallback((techniqueId: string) => {
    onSelectTechnique(techniqueId);
    onClose();
  }, [onSelectTechnique, onClose]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Practice by Technique"
      size="lg"
    >
      <div className="flex flex-col gap-4">
        {/* Header with filters */}
        <div className="flex justify-between items-center flex-wrap gap-2 pb-2 border-b border-[--color-neutral-200]">
          <CategoryFilter
            selected={categoryFilter}
            onChange={setCategoryFilter}
          />
          <SortSelector
            selected={sortBy}
            onChange={setSortBy}
          />
        </div>

        {/* Content */}
        <div className="min-h-[300px] max-h-[60vh] overflow-y-auto">
          {isLoading && (
            <div className="flex justify-center items-center h-[200px] text-[--color-text-muted]">
              Loading techniques...
            </div>
          )}

          {error && (
            <div className="flex justify-center items-center h-[200px] text-[--color-error]">
              {error}
            </div>
          )}

          {!isLoading && !error && (
            <TechniqueList
              techniques={techniques}
              stats={stats}
              categoryFilter={categoryFilter}
              sortBy={sortBy}
              onSelectTechnique={handleSelectTechnique}
            />
          )}
        </div>

        {/* Footer stats */}
        <div className="flex justify-between pt-2 border-t border-[--color-neutral-200] text-sm text-[--color-text-muted]">
          <span>
            {techniques.length} techniques available
          </span>
          <span>
            {Object.keys(stats).length} practiced
          </span>
        </div>
      </div>
    </Modal>
  );
};

export default TechniqueFocusModal;
