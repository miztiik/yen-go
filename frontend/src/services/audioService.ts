/**
 * Audio Service
 * @module services/audioService
 *
 * Handles sound effects for the app per FR-040, FR-052, FR-053.
 * Sound files are expected in /sounds/ directory.
 *
 * Constitution Compliance:
 * - Simple audio playback only
 * - IX. Accessibility: Respects user mute preference
 *
 * Spec 127 US8: Reads sound file paths from APP_CONSTANTS.sounds
 */

import { APP_CONSTANTS } from '../config/constants';
import { getSettingsSnapshot } from '../hooks/useSettings';

// ============================================================================
// Types
// ============================================================================

/**
 * Available sound effects
 */
export type SoundName =
  | 'stone' // Stone placement
  | 'capture' // Stones captured
  | 'correct' // Correct move
  | 'wrong' // Wrong move (FR-040)
  | 'complete' // Puzzle complete
  | 'click'; // UI click

/**
 * Sound configuration
 */
export interface SoundConfig {
  /** Path to sound file */
  path: string;
  /** Volume (0-1) */
  volume: number;
}

/**
 * Audio service interface
 */
export interface AudioService {
  /** Play a sound effect */
  play: (name: SoundName) => void;
  /** Check if audio is muted */
  isMuted: () => boolean;
  /** Preload sounds for faster playback */
  preload: () => void;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Sound file paths from centralized constants and default volumes.
 * Spec 127 US8: All paths read from APP_CONSTANTS.sounds
 */
const SOUNDS: Record<SoundName, SoundConfig> = {
  stone: { path: APP_CONSTANTS.sounds.stone, volume: 0.7 },
  capture: { path: APP_CONSTANTS.sounds.capture, volume: 0.6 },
  correct: { path: APP_CONSTANTS.sounds.correct, volume: 0.5 },
  wrong: { path: APP_CONSTANTS.sounds.wrong, volume: 0.5 },
  complete: { path: APP_CONSTANTS.sounds.complete, volume: 0.6 },
  click: { path: APP_CONSTANTS.sounds.click, volume: 0.3 },
};

/**
 * Master volume for all sounds. Not exposed in UI — uses default 1.0.
 * Could be made configurable later via AppSettings if needed.
 */
const MASTER_VOLUME = 1.0;

// ============================================================================
// Implementation
// ============================================================================

/**
 * Creates the audio service.
 * Uses HTMLAudioElement for sound playback.
 */
function createAudioService(): AudioService {
  // Audio cache for preloaded sounds
  const audioCache = new Map<SoundName, HTMLAudioElement>();

  /**
   * Create and cache an audio element for a sound
   */
  function getOrCreateAudio(name: SoundName): HTMLAudioElement {
    let audio = audioCache.get(name);

    if (!audio) {
      const config = SOUNDS[name];
      audio = new Audio(config.path);
      audio.preload = 'auto';
      audioCache.set(name, audio);
    }

    return audio;
  }

  /**
   * Check if sound is disabled via canonical settings.
   */
  function isSoundDisabled(): boolean {
    try {
      return !getSettingsSnapshot().soundEnabled;
    } catch {
      return false;
    }
  }

  /**
   * Play a sound
   */
  function play(name: SoundName): void {
    if (isSoundDisabled()) return;

    try {
      const audio = getOrCreateAudio(name);
      const config = SOUNDS[name];

      // Set volume (sound-specific * master)
      audio.volume = config.volume * MASTER_VOLUME;

      // Reset to start if already playing
      audio.currentTime = 0;

      // Play (ignore promise rejection for autoplay policy)
      audio.play().catch(() => {
        // User hasn't interacted with page yet, sound won't play
        // This is expected behavior per browser autoplay policy
      });
    } catch {
      // Audio not supported or other error - fail silently
    }
  }

  /**
   * Check if muted (reads from canonical settings)
   */
  function isMuted(): boolean {
    return isSoundDisabled();
  }

  /**
   * Preload all sounds
   */
  function preload(): void {
    for (const name of Object.keys(SOUNDS) as SoundName[]) {
      getOrCreateAudio(name);
    }
  }

  return {
    play,
    isMuted,
    preload,
  };
}

// ============================================================================
// Singleton Export
// ============================================================================

/**
 * Audio service singleton instance
 */
export const audioService = createAudioService();

/**
 * Convenience function to play a sound
 */
export function playSound(name: SoundName): void {
  audioService.play(name);
}
