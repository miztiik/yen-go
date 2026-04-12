/**
 * CreatePracticeSetModal Component
 * @module components/Collections/CreatePracticeSetModal
 *
 * Modal for creating custom practice sets by level and tags.
 * Shows puzzle count preview and allows generating custom sets.
 *
 * Covers: T029, T030, T031 - User Story 3 (Custom Sets)
 */

import type { JSX } from 'preact';
import { useState, useEffect, useCallback } from 'preact/hooks';
import { Modal } from '@/components/shared/Modal';
import type { SkillLevel } from '@/models/collection';
import { SKILL_LEVELS } from '@/models/collection';
import { EmptyState } from '@/components/shared/GoQuote';

// ============================================================================
// Types
// ============================================================================

export interface CreatePracticeSetModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Handler to close the modal */
  onClose: () => void;
  /** Handler when practice set is created */
  onCreate: (config: PracticeSetConfig) => void;
  /** Available tags for filtering */
  availableTags: string[];
  /** Function to get puzzle count for filters */
  getPuzzleCount: (level: SkillLevel | null, tags: string[]) => Promise<number>;
}

export interface PracticeSetConfig {
  /** Selected skill level (null = all) */
  level: SkillLevel | null;
  /** Selected tags */
  tags: string[];
  /** Number of puzzles to include */
  puzzleCount: number;
  /** Session name (optional) */
  name?: string;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
  content: {
    padding: '1.5rem',
    maxWidth: '480px',
  } as JSX.CSSProperties,

  title: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: 'var(--color-neutral-800)',
    marginBottom: '1.5rem',
    textAlign: 'center',
  } as JSX.CSSProperties,

  section: {
    marginBottom: '1.5rem',
  } as JSX.CSSProperties,

  label: {
    display: 'block',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--color-text-secondary)',
    marginBottom: '0.75rem',
  } as JSX.CSSProperties,

  buttonGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
  } as JSX.CSSProperties,

  levelButton: (isActive: boolean): JSX.CSSProperties => ({
    padding: '0.5rem 0.75rem',
    fontSize: '0.875rem',
    border: isActive ? '2px solid var(--color-info-border)' : '1px solid var(--color-neutral-200)',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: isActive ? 'var(--color-mode-collections-light)' : 'white',
    color: isActive ? 'var(--color-mode-collections-text)' : 'var(--color-neutral-500)',
    fontWeight: isActive ? 600 : 400,
    transition: 'all 0.15s ease',
  }),

  tagButton: (isActive: boolean): JSX.CSSProperties => ({
    padding: '0.375rem 0.625rem',
    fontSize: '0.75rem',
    border: isActive
      ? '2px solid var(--color-mode-collections-border)'
      : '1px solid var(--color-neutral-200)',
    borderRadius: '6px',
    cursor: 'pointer',
    backgroundColor: isActive ? 'var(--color-mode-collections-light)' : 'white',
    color: isActive ? 'var(--color-mode-collections-text)' : 'var(--color-neutral-500)',
    fontWeight: isActive ? 600 : 400,
    transition: 'all 0.15s ease',
  }),

  countPreview: {
    backgroundColor: 'var(--color-neutral-100)',
    borderRadius: '8px',
    padding: '1rem',
    textAlign: 'center',
    marginBottom: '1.5rem',
  } as JSX.CSSProperties,

  countNumber: {
    fontSize: '2rem',
    fontWeight: 700,
    color: 'var(--color-neutral-900)',
  } as JSX.CSSProperties,

  countLabel: {
    fontSize: '0.875rem',
    color: 'var(--color-neutral-500)',
    marginTop: '0.25rem',
  } as JSX.CSSProperties,

  countSlider: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    marginTop: '1rem',
  } as JSX.CSSProperties,

  slider: {
    flex: 1,
    height: '8px',
    borderRadius: '4px',
    cursor: 'pointer',
  } as JSX.CSSProperties,

  sliderValue: {
    fontSize: '1rem',
    fontWeight: 600,
    color: 'var(--color-neutral-800)',
    minWidth: '3rem',
    textAlign: 'right',
  } as JSX.CSSProperties,

  actions: {
    display: 'flex',
    gap: '0.75rem',
    justifyContent: 'flex-end',
  } as JSX.CSSProperties,

  cancelButton: {
    padding: '0.625rem 1.25rem',
    fontSize: '0.875rem',
    border: '1px solid var(--color-neutral-200)',
    borderRadius: '8px',
    cursor: 'pointer',
    backgroundColor: 'white',
    color: 'var(--color-neutral-500)',
  } as JSX.CSSProperties,

  createButton: (enabled: boolean): JSX.CSSProperties => ({
    padding: '0.625rem 1.5rem',
    fontSize: '0.875rem',
    border: 'none',
    borderRadius: '8px',
    cursor: enabled ? 'pointer' : 'not-allowed',
    backgroundColor: enabled ? 'var(--color-info-border)' : 'var(--color-neutral-400)',
    color: 'white',
    fontWeight: 600,
    opacity: enabled ? 1 : 0.7,
  }),

  loading: {
    color: 'var(--color-neutral-500)',
    fontSize: '0.875rem',
  } as JSX.CSSProperties,

  warning: {
    backgroundColor: 'var(--color-mode-collections-bg)',
    border: '1px solid var(--color-warning-border)',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    marginTop: '1rem',
    fontSize: '0.8125rem',
    color: 'var(--color-warning-text)',
  } as JSX.CSSProperties,
};

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_PUZZLE_COUNT = 20;
const MAX_PUZZLE_COUNT = 100;

// ============================================================================
// Component
// ============================================================================

/**
 * CreatePracticeSetModal - Create custom practice sets
 */
export function CreatePracticeSetModal({
  isOpen,
  onClose,
  onCreate,
  availableTags,
  getPuzzleCount,
}: CreatePracticeSetModalProps): JSX.Element {
  const [selectedLevel, setSelectedLevel] = useState<SkillLevel | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [requestedCount, setRequestedCount] = useState(DEFAULT_PUZZLE_COUNT);
  const [availableCount, setAvailableCount] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch available puzzle count when filters change
  useEffect(() => {
    if (!isOpen) return;

    const fetchCount = async () => {
      setIsLoading(true);
      try {
        const count = await getPuzzleCount(selectedLevel, selectedTags);
        setAvailableCount(count);
      } catch (error) {
        console.error('Failed to get puzzle count:', error);
        setAvailableCount(0);
      } finally {
        setIsLoading(false);
      }
    };

    void fetchCount();
  }, [isOpen, selectedLevel, selectedTags, getPuzzleCount]);

  // Reset when modal opens
  useEffect(() => {
    if (isOpen) {
      setSelectedLevel(null);
      setSelectedTags([]);
      setRequestedCount(DEFAULT_PUZZLE_COUNT);
    }
  }, [isOpen]);

  const handleLevelSelect = useCallback((level: SkillLevel | null) => {
    setSelectedLevel(level);
  }, []);

  const handleTagToggle = useCallback((tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  }, []);

  const handleCountChange = useCallback((e: Event) => {
    const target = e.target as HTMLInputElement;
    setRequestedCount(parseInt(target.value, 10));
  }, []);

  const handleCreate = useCallback(() => {
    const actualCount = Math.min(requestedCount, availableCount ?? 0);
    if (actualCount > 0) {
      onCreate({
        level: selectedLevel,
        tags: selectedTags,
        puzzleCount: actualCount,
      });
    }
  }, [selectedLevel, selectedTags, requestedCount, availableCount, onCreate]);

  const actualPuzzleCount = Math.min(requestedCount, availableCount ?? 0);
  const showInsufficientWarning =
    availableCount !== null && availableCount < requestedCount && availableCount > 0;
  const hasNoPuzzles = availableCount !== null && availableCount === 0;
  const canCreate = actualPuzzleCount > 0;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create Practice Set">
      <div style={styles.content}>
        {/* Level Selection */}
        <div style={styles.section}>
          <label style={styles.label}>Skill Level</label>
          <div style={styles.buttonGroup}>
            <button
              type="button"
              style={styles.levelButton(selectedLevel === null)}
              onClick={() => handleLevelSelect(null)}
            >
              All Levels
            </button>
            {SKILL_LEVELS.map((level) => (
              <button
                key={level.slug}
                type="button"
                style={styles.levelButton(selectedLevel === level.slug)}
                onClick={() => handleLevelSelect(level.slug)}
                title={level.description}
              >
                {level.shortName}
              </button>
            ))}
          </div>
        </div>

        {/* Tag Selection */}
        {availableTags.length > 0 && (
          <div style={styles.section}>
            <label style={styles.label}>Techniques ({selectedTags.length} selected)</label>
            <div style={styles.buttonGroup}>
              {availableTags.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  style={styles.tagButton(selectedTags.includes(tag))}
                  onClick={() => handleTagToggle(tag)}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Puzzle Count Preview */}
        <div style={styles.countPreview}>
          {isLoading ? (
            <span style={styles.loading}>Loading...</span>
          ) : hasNoPuzzles ? (
            <EmptyState message="No puzzles found - try adjusting your filters" />
          ) : (
            <>
              <div style={styles.countNumber}>{actualPuzzleCount}</div>
              <div style={styles.countLabel}>
                puzzles available
                {availableCount !== null &&
                  availableCount > actualPuzzleCount &&
                  ` (${availableCount} total)`}
              </div>

              {/* Puzzle count slider */}
              <div style={styles.countSlider}>
                <span style={{ fontSize: '0.75rem', color: 'var(--color-neutral-500)' }}>10</span>
                <input
                  type="range"
                  min={10}
                  max={Math.min(MAX_PUZZLE_COUNT, availableCount ?? MAX_PUZZLE_COUNT)}
                  value={requestedCount}
                  onChange={handleCountChange}
                  style={styles.slider}
                  aria-label="Number of puzzles"
                />
                <span style={styles.sliderValue}>{requestedCount}</span>
              </div>
            </>
          )}

          {/* Insufficient puzzles warning */}
          {showInsufficientWarning && (
            <div style={styles.warning}>
              Only {availableCount} puzzles match your criteria. The practice set will include all
              available puzzles.
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={styles.actions}>
          <button type="button" style={styles.cancelButton} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            style={styles.createButton(canCreate)}
            onClick={handleCreate}
            disabled={!canCreate}
          >
            Start Practice
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default CreatePracticeSetModal;
