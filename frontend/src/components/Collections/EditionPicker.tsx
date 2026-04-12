/**
 * EditionPicker Component
 * @module components/Collections/EditionPicker
 *
 * Displays edition options when a collection has multiple source editions.
 * Users pick which edition (source) to study from.
 */

import type { JSX } from 'preact';
import type { CollectionRow } from '@/services/puzzleQueryService';

export interface EditionPickerProps {
  /** Edition sub-collections */
  editions: CollectionRow[];
  /** Parent collection name */
  parentName: string;
  /** Handler when user selects an edition */
  onSelect: (editionSlug: string) => void;
}

/**
 * Edition picker for multi-source collections.
 * Shows cards for each edition with label and puzzle count.
 */
export function EditionPicker({
  editions,
  parentName: _parentName,
  onSelect,
}: EditionPickerProps): JSX.Element {
  return (
    <div class="flex flex-col gap-4 p-4">
      <div class="text-sm text-gray-500 dark:text-gray-400">
        This collection has multiple editions from different sources.
        Choose an edition to study:
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {editions.map((edition) => {
          const attrs = JSON.parse(edition.attrs || '{}') as Record<string, unknown>;
          const label = typeof attrs.label === 'string' ? attrs.label : edition.name;
          return (
            <button
              key={edition.collection_id}
              type="button"
              class="flex flex-col gap-1 p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all text-left cursor-pointer"
              onClick={() => onSelect(edition.slug)}
              aria-label={`${label} - ${edition.puzzle_count} puzzles`}
            >
              <span class="font-medium text-gray-900 dark:text-gray-100">
                {label}
              </span>
              <span class="text-sm text-gray-500 dark:text-gray-400">
                {edition.puzzle_count} puzzles
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
