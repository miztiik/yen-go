/**
 * Settings Panel Component - Hamburger menu with app settings
 * @module components/Settings/SettingsPanel
 */

import { useState, useCallback, useEffect } from 'preact/hooks';
import type { JSX } from 'preact';
import { getTagsConfig, type TagDefinition } from '../../services/tagsService';

/** Game modes */
export type GameMode = 'daily' | 'practice' | 'rush';

/** Difficulty filter */
export interface DifficultyFilter {
  minRank: string; // e.g., "30k", "10k", "1d"
  maxRank: string; // e.g., "15k", "1k", "5d"
}

/** Valid board rotation angles */
export type BoardRotation = 0 | 90 | 180 | 270;

/** Settings state */
export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  gameMode: GameMode;
  difficultyFilter: DifficultyFilter | null;
  tagFilter: string[]; // e.g., ['life-and-death', 'tesuji']
  soundEnabled: boolean;
  hintsEnabled: boolean;
  boardRotation: BoardRotation;
}

/** Default settings */
export const DEFAULT_SETTINGS: AppSettings = {
  theme: 'light',
  gameMode: 'daily',
  difficultyFilter: null,
  tagFilter: [],
  soundEnabled: true,
  hintsEnabled: true,
  boardRotation: 0,
};

/** Difficulty levels for filter */
export const DIFFICULTY_PRESETS = [
  { label: 'All Levels', min: '30k', max: '9d' },
  { label: 'Beginner (30k-15k)', min: '30k', max: '15k' },
  { label: 'SDK (14k-1k)', min: '14k', max: '1k' },
  { label: 'Dan (1d+)', min: '1d', max: '9d' },
  { label: 'Intermediate (10k-5k)', min: '10k', max: '5k' },
  { label: 'Advanced (4k-1d)', min: '4k', max: '1d' },
] as const;

export interface SettingsPanelProps {
  settings: AppSettings;
  onSettingsChange: (settings: AppSettings) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsPanel({
  settings,
  onSettingsChange,
  isOpen,
  onClose,
}: SettingsPanelProps): JSX.Element | null {
  const [tags, setTags] = useState<TagDefinition[]>([]);
  const [tagsLoading, setTagsLoading] = useState(true);

  // Load tags from tags.json on mount
  useEffect(() => {
    void getTagsConfig()
      .then(config => {
        setTags(Object.values(config.tags));
        setTagsLoading(false);
      })
      .catch(err => {
        console.error('Failed to load tags:', err);
        setTagsLoading(false);
      });
  }, []);

  const handleThemeChange = useCallback((theme: AppSettings['theme']) => {
    onSettingsChange({ ...settings, theme });
  }, [settings, onSettingsChange]);

  const handleGameModeChange = useCallback((gameMode: GameMode) => {
    onSettingsChange({ ...settings, gameMode });
  }, [settings, onSettingsChange]);

  const handleDifficultyChange = useCallback((preset: typeof DIFFICULTY_PRESETS[number] | null) => {
    onSettingsChange({
      ...settings,
      difficultyFilter: preset ? { minRank: preset.min, maxRank: preset.max } : null,
    });
  }, [settings, onSettingsChange]);

  const handleTagToggle = useCallback((tag: string) => {
    const newTags = settings.tagFilter.includes(tag)
      ? settings.tagFilter.filter(t => t !== tag)
      : [...settings.tagFilter, tag];
    onSettingsChange({ ...settings, tagFilter: newTags });
  }, [settings, onSettingsChange]);

  const handleSoundToggle = useCallback(() => {
    onSettingsChange({ ...settings, soundEnabled: !settings.soundEnabled });
  }, [settings, onSettingsChange]);

  const handleHintsToggle = useCallback(() => {
    onSettingsChange({ ...settings, hintsEnabled: !settings.hintsEnabled });
  }, [settings, onSettingsChange]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div style={styles.backdrop} onClick={onClose} />
      
      {/* Panel */}
      <div style={styles.panel}>
        <div style={styles.header}>
          <h2 style={styles.title}>Settings</h2>
          <button style={styles.closeButton} onClick={onClose} aria-label="Close settings">
            ✕
          </button>
        </div>

        <div style={styles.content}>
          {/* Theme Section */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Theme</h3>
            <div style={styles.optionRow}>
              {(['light', 'dark', 'system'] as const).map(theme => (
                <button
                  key={theme}
                  style={{
                    ...styles.optionButton,
                    ...(settings.theme === theme ? styles.optionButtonActive : {}),
                  }}
                  onClick={() => handleThemeChange(theme)}
                >
                  {theme === 'light' ? '☀️' : theme === 'dark' ? '🌙' : '🖥️'} {theme}
                </button>
              ))}
            </div>
          </section>

          {/* Game Mode Section */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Game Mode</h3>
            <div style={styles.optionColumn}>
              <button
                style={{
                  ...styles.modeButton,
                  ...(settings.gameMode === 'daily' ? styles.modeButtonActive : {}),
                }}
                onClick={() => handleGameModeChange('daily')}
              >
                <span style={styles.modeIcon}>📅</span>
                <div style={styles.modeText}>
                  <strong>Daily Challenge</strong>
                  <span style={styles.modeDesc}>Curated puzzles for today</span>
                </div>
              </button>
              <button
                style={{
                  ...styles.modeButton,
                  ...(settings.gameMode === 'practice' ? styles.modeButtonActive : {}),
                }}
                onClick={() => handleGameModeChange('practice')}
              >
                <span style={styles.modeIcon}>🎯</span>
                <div style={styles.modeText}>
                  <strong>Practice Mode</strong>
                  <span style={styles.modeDesc}>Filter by difficulty & tags</span>
                </div>
              </button>
              <button
                style={{
                  ...styles.modeButton,
                  ...(settings.gameMode === 'rush' ? styles.modeButtonActive : {}),
                }}
                onClick={() => handleGameModeChange('rush')}
              >
                <span style={styles.modeIcon}>⚡</span>
                <div style={styles.modeText}>
                  <strong>Puzzle Rush</strong>
                  <span style={styles.modeDesc}>Solve as many as you can</span>
                </div>
              </button>
            </div>
          </section>

          {/* Difficulty Filter (only for practice mode) */}
          {settings.gameMode === 'practice' && (
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Difficulty</h3>
              <div style={styles.optionColumn}>
                {DIFFICULTY_PRESETS.map(preset => (
                  <button
                    key={preset.label}
                    style={{
                      ...styles.filterButton,
                      ...(settings.difficultyFilter?.minRank === preset.min ? styles.filterButtonActive : {}),
                    }}
                    onClick={() => handleDifficultyChange(
                      settings.difficultyFilter?.minRank === preset.min ? null : preset
                    )}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </section>
          )}

          {/* Tag Filter (only for practice mode) */}
          {settings.gameMode === 'practice' && (
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Puzzle Types</h3>
              {tagsLoading ? (
                <div style={styles.loading}>Loading tags...</div>
              ) : (
                <div style={styles.tagGrid}>
                  {tags.map(tag => (
                    <button
                      key={tag.id}
                      style={{
                        ...styles.tagButton,
                        ...(settings.tagFilter.includes(tag.slug) ? styles.tagButtonActive : {}),
                      }}
                      onClick={() => handleTagToggle(tag.slug)}
                      title={tag.description}
                    >
                      {tag.name}
                    </button>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Sound & Hints */}
          <section style={styles.section}>
            <h3 style={styles.sectionTitle}>Preferences</h3>
            <div style={styles.toggleRow}>
              <span>Sound effects</span>
              <button
                style={{
                  ...styles.toggle,
                  ...(settings.soundEnabled ? styles.toggleOn : styles.toggleOff),
                }}
                onClick={handleSoundToggle}
                aria-label={settings.soundEnabled ? 'Disable sound' : 'Enable sound'}
              >
                <span style={{
                  ...styles.toggleKnob,
                  ...(settings.soundEnabled ? styles.toggleKnobOn : {}),
                }} />
              </button>
            </div>
            <div style={styles.toggleRow}>
              <span>Show hints</span>
              <button
                style={{
                  ...styles.toggle,
                  ...(settings.hintsEnabled ? styles.toggleOn : styles.toggleOff),
                }}
                onClick={handleHintsToggle}
                aria-label={settings.hintsEnabled ? 'Disable hints' : 'Enable hints'}
              >
                <span style={{
                  ...styles.toggleKnob,
                  ...(settings.hintsEnabled ? styles.toggleKnobOn : {}),
                }} />
              </button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
}

/** Hamburger menu button */
export interface HamburgerButtonProps {
  onClick: () => void;
}

export function HamburgerButton({ onClick }: HamburgerButtonProps): JSX.Element {
  return (
    <button style={styles.hamburger} onClick={onClick} aria-label="Open settings">
      <span style={styles.hamburgerLine} />
      <span style={styles.hamburgerLine} />
      <span style={styles.hamburgerLine} />
    </button>
  );
}

const styles: Record<string, JSX.CSSProperties> = {
  backdrop: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.4)',
    zIndex: 100,
  },
  panel: {
    position: 'fixed',
    top: 0,
    right: 0,
    bottom: 0,
    width: '320px',
    maxWidth: '90vw',
    background: 'var(--color-bg-primary)',
    boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.15)',
    zIndex: 101,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '1rem 1.25rem',
    borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
  },
  title: {
    margin: 0,
    fontSize: '1.1rem',
    fontWeight: '600',
    color: 'var(--color-text-secondary)',
  },
  closeButton: {
    background: 'none',
    border: 'none',
    fontSize: '1.25rem',
    color: 'var(--color-text-muted)',
    cursor: 'pointer',
    padding: '0.25rem',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '0.5rem 1.25rem 1.5rem',
  },
  section: {
    marginBottom: '1.5rem',
  },
  sectionTitle: {
    fontSize: '0.75rem',
    fontWeight: '600',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '0.75rem',
  },
  optionRow: {
    display: 'flex',
    gap: '0.5rem',
  },
  optionColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  optionButton: {
    flex: 1,
    padding: '0.6rem 0.75rem',
    fontSize: '0.8rem',
    fontWeight: '500',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '8px',
    background: 'white',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    textTransform: 'capitalize',
  },
  optionButtonActive: {
    background: 'rgba(92, 74, 50, 0.1)',
    borderColor: 'var(--color-text-secondary)',
  },
  modeButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '10px',
    background: 'white',
    cursor: 'pointer',
    textAlign: 'left',
  },
  modeButtonActive: {
    background: 'rgba(92, 74, 50, 0.08)',
    borderColor: 'var(--color-text-secondary)',
  },
  modeIcon: {
    fontSize: '1.5rem',
  },
  modeText: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
  },
  modeDesc: {
    fontSize: '0.7rem',
    color: 'var(--color-text-muted)',
  },
  filterButton: {
    padding: '0.5rem 0.75rem',
    fontSize: '0.8rem',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '6px',
    background: 'white',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    textAlign: 'left',
  },
  filterButtonActive: {
    background: 'rgba(92, 74, 50, 0.1)',
    borderColor: 'var(--color-text-secondary)',
  },
  tagGrid: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.4rem',
  },
  loading: {
    fontSize: '0.8rem',
    color: 'var(--color-text-muted)',
    fontStyle: 'italic',
    padding: '0.5rem 0',
  },
  tagButton: {
    padding: '0.35rem 0.6rem',
    fontSize: '0.7rem',
    border: '1px solid rgba(0, 0, 0, 0.08)',
    borderRadius: '12px',
    background: 'white',
    color: 'var(--color-text-secondary)',
    cursor: 'pointer',
    textTransform: 'capitalize',
  },
  tagButtonActive: {
    background: 'var(--color-text-secondary)',
    borderColor: 'var(--color-text-secondary)',
    color: 'white',
  },
  toggleRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.5rem 0',
    fontSize: '0.85rem',
    color: 'var(--color-text-secondary)',
  },
  toggle: {
    width: '44px',
    height: '24px',
    borderRadius: '12px',
    border: 'none',
    cursor: 'pointer',
    position: 'relative',
    transition: 'background 0.2s',
  },
  toggleOn: {
    background: 'var(--color-text-secondary)',
  },
  toggleOff: {
    background: 'rgba(0, 0, 0, 0.15)',
  },
  toggleKnob: {
    position: 'absolute',
    top: '2px',
    left: '2px',
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    background: 'white',
    transition: 'transform 0.2s',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.2)',
  },
  toggleKnobOn: {
    transform: 'translateX(20px)',
  },
  hamburger: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    padding: '8px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  },
  hamburgerLine: {
    width: '20px',
    height: '2px',
    background: 'var(--color-text-secondary)',
    borderRadius: '1px',
  },
};

export default SettingsPanel;
