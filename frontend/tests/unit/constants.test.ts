/**
 * Unit test for centralized constants module.
 *
 * Tests: default values, helper functions, path construction.
 * Spec 127: T054 (test-first for T003)
 *
 * Note: In the test environment, `import.meta.env.BASE_URL` defaults to `'/'`
 * so all paths appear without a base prefix (e.g. `/config`). In production
 * builds with `base: '/yen-go/'`, paths are prefixed (e.g. `/yen-go/config`).
 */

import { describe, it, expect } from 'vitest';
import {
  APP_CONSTANTS,
  cdnUrl,
  sgfUrl,
  soundUrl,
  configUrl,
} from '../../src/config/constants';

describe('APP_CONSTANTS', () => {
  it('has correct default CDN base path', () => {
    expect(APP_CONSTANTS.paths.cdnBase).toBe('/yengo-puzzle-collections');
  });

  it('has correct default config base path', () => {
    expect(APP_CONSTANTS.paths.configBase).toBe('/config');
  });

  it('has all 6 sound paths defined', () => {
    expect(APP_CONSTANTS.sounds.stone).toBe('/sounds/move.ogg');
    expect(APP_CONSTANTS.sounds.capture).toBe('/sounds/newStone.ogg');
    expect(APP_CONSTANTS.sounds.correct).toBe('/sounds/success.webm');
    expect(APP_CONSTANTS.sounds.wrong).toBe('/sounds/wrong.webm');
    expect(APP_CONSTANTS.sounds.complete).toBe('/sounds/pling.webm');
    expect(APP_CONSTANTS.sounds.click).toBe('/sounds/click.webm');
  });

  it('has all 3 config paths defined', () => {
    expect(APP_CONSTANTS.config.levels).toBe('/config/puzzle-levels.json');
    expect(APP_CONSTANTS.config.tags).toBe('/config/tags.json');
    expect(APP_CONSTANTS.config.tips).toBe('/config/go-tips.json');
  });

  it('has responsive breakpoints', () => {
    expect(APP_CONSTANTS.breakpoints.mobile).toBe(768);
    expect(APP_CONSTANTS.breakpoints.desktop).toBe(1024);
  });
});

describe('cdnUrl', () => {
  it('constructs URL from relative path', () => {
    expect(cdnUrl('sgf/beginner/batch-0001/abc.sgf')).toBe(
      '/yengo-puzzle-collections/sgf/beginner/batch-0001/abc.sgf'
    );
  });

  it('strips leading slash from relative path', () => {
    expect(cdnUrl('/sgf/test.sgf')).toBe('/yengo-puzzle-collections/sgf/test.sgf');
  });
});

describe('sgfUrl', () => {
  it('returns same as cdnUrl', () => {
    const path = 'sgf/beginner/batch-0001/abc.sgf';
    expect(sgfUrl(path)).toBe(cdnUrl(path));
  });
});

describe('soundUrl', () => {
  it('returns sound path by name', () => {
    expect(soundUrl('stone')).toBe('/sounds/move.ogg');
    expect(soundUrl('correct')).toBe('/sounds/success.webm');
  });
});

describe('configUrl', () => {
  it('returns config path by name', () => {
    expect(configUrl('levels')).toBe('/config/puzzle-levels.json');
    expect(configUrl('tags')).toBe('/config/tags.json');
    expect(configUrl('tips')).toBe('/config/go-tips.json');
  });
});
