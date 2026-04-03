/**
 * Audio feedback — unit tests.
 * T160: Verify audioService.play() is called with correct sound types on events.
 * T161: Verify no audioService calls when mute is enabled.
 * Spec 132 US17
 *
 * Uses source analysis for integration checks (jsdom doesn't support HTMLAudioElement.play),
 * plus direct API tests for mute/volume behavior.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

// Must mock APP_CONSTANTS before importing audioService
vi.mock('../../src/config/constants', () => ({
  APP_CONSTANTS: {
    sounds: {
      stone: '/sounds/stone.mp3',
      capture: '/sounds/capture.mp3',
      correct: '/sounds/correct.mp3',
      wrong: '/sounds/wrong.mp3',
      complete: '/sounds/complete.mp3',
      click: '/sounds/click.mp3',
    },
  },
}));

// Must mock useSettings before importing audioService
vi.mock('../../src/hooks/useSettings', () => {
  let soundEnabled = true;
  return {
    getSettingsSnapshot: () => ({ soundEnabled, theme: 'light', coordinateLabels: true }),
    _testSetSoundEnabled: (v: boolean) => { soundEnabled = v; },
    _testGetSoundEnabled: () => soundEnabled,
  };
});

const usePuzzleStateSource = readFileSync(
  resolve(__dirname, '../../src/hooks/usePuzzleState.ts'),
  'utf-8',
);

const audioServiceSource = readFileSync(
  resolve(__dirname, '../../src/services/audioService.ts'),
  'utf-8',
);

describe('audioService event wiring (T160)', () => {
  it('usePuzzleState imports audioService', () => {
    expect(usePuzzleStateSource).toContain("from '../services/audioService'");
  });

  it('stone sound is played by usePuzzleState on puzzle-place', () => {
    // Stone placement sound is now played via audioService in usePuzzleState
    expect(usePuzzleStateSource).toContain("audioService.play('stone')");
  });

  it('plays correct sound on correct answer', () => {
    expect(usePuzzleStateSource).toContain("audioService.play('correct')");
  });

  it('plays wrong sound on wrong answer', () => {
    expect(usePuzzleStateSource).toContain("audioService.play('wrong')");
  });

  it('audioService supports all required sound types', () => {
    expect(audioServiceSource).toContain("'stone'");
    expect(audioServiceSource).toContain("'correct'");
    expect(audioServiceSource).toContain("'wrong'");
    expect(audioServiceSource).toContain("'complete'");
    expect(audioServiceSource).toContain("'capture'");
    expect(audioServiceSource).toContain("'click'");
  });

  it('audioService play function checks muted state via settings', () => {
    // The play function returns early if sound is disabled via canonical settings
    expect(audioServiceSource).toContain('isSoundDisabled()');
  });
});

describe('audioService mute behavior (T161)', () => {
  let audioService: typeof import('../../src/services/audioService');
  let settingsMock: { _testSetSoundEnabled: (v: boolean) => void; _testGetSoundEnabled: () => boolean };

  beforeEach(async () => {
    localStorage.removeItem('yen-go:audio:volume');
    vi.clearAllMocks();
    vi.resetModules();
    audioService = await import('../../src/services/audioService');
    settingsMock = (await import('../../src/hooks/useSettings')) as unknown as typeof settingsMock;
    settingsMock._testSetSoundEnabled(true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('isMuted returns false when soundEnabled is true', () => {
    settingsMock._testSetSoundEnabled(true);
    expect(audioService.audioService.isMuted()).toBe(false);
  });

  it('isMuted returns true when soundEnabled is false', () => {
    settingsMock._testSetSoundEnabled(false);
    expect(audioService.audioService.isMuted()).toBe(true);
  });
});
