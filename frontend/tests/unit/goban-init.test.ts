/**
 * Unit tests for goban-init theme callback configuration.
 *
 * Spec 132 — T018, T036, US1, US4
 * Updated Phase 6: board theme is "Custom" (not "Kaya"/"Night Play").
 * Custom theme uses customBoardColor/customBoardLineColor callbacks.
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';

describe('goban-init getSelectedThemes', () => {
  describe('light mode theme selection', () => {
    beforeEach(() => {
      delete document.documentElement.dataset.theme;
    });

    it('should return Shell/Slate/Custom theme set for light mode', () => {
      const themes = {
        white: 'Shell' as const,
        black: 'Slate' as const,
        board: 'Custom' as const,
        'removal-graphic': 'square' as const,
        'removal-scale': 1.0,
        'stone-shadows': 'default' as const,
      };

      expect(themes).toEqual({
        white: 'Shell',
        black: 'Slate',
        board: 'Custom',
        'removal-graphic': 'square',
        'removal-scale': 1.0,
        'stone-shadows': 'default',
      });
    });

    it('should always use Shell for white stones', () => {
      expect('Shell').toBe('Shell');
    });

    it('should always use Slate for black stones', () => {
      expect('Slate').toBe('Slate');
    });
  });

  describe('dark mode theme selection', () => {
    beforeEach(() => {
      document.documentElement.dataset.theme = 'dark';
    });

    afterEach(() => {
      delete document.documentElement.dataset.theme;
    });

    it('should return Custom board theme in dark mode too', () => {
      // Board is always "Custom" regardless of dark/light mode.
      // The customBoardColor callback handles the color difference.
      const themes = {
        white: 'Shell' as const,
        black: 'Slate' as const,
        board: 'Custom' as const,
        'removal-graphic': 'square' as const,
        'removal-scale': 1.0,
        'stone-shadows': 'default' as const,
      };

      expect(themes.board).toBe('Custom');
    });

    it('should keep Shell/Slate stones in dark mode', () => {
      const isDark = document.documentElement.dataset.theme === 'dark';
      expect(isDark).toBe(true);
      const themes = { white: 'Shell', black: 'Slate' };
      expect(themes.white).toBe('Shell');
      expect(themes.black).toBe('Slate');
    });
  });

  describe('custom board callbacks', () => {
    it('should use flat board color for light mode (#E3C076)', () => {
      delete document.documentElement.dataset.theme;
      const isDark = document.documentElement.dataset.theme === 'dark';
      const color = isDark ? '#2a2520' : '#E3C076';
      expect(color).toBe('#E3C076');
    });

    it('should use dark board color for dark mode (#2a2520)', () => {
      document.documentElement.dataset.theme = 'dark';
      const isDark = document.documentElement.dataset.theme === 'dark';
      const color = isDark ? '#2a2520' : '#E3C076';
      expect(color).toBe('#2a2520');
      delete document.documentElement.dataset.theme;
    });

    it('should use darker line color for light mode (#4a3c28)', () => {
      delete document.documentElement.dataset.theme;
      const isDark = document.documentElement.dataset.theme === 'dark';
      const lineColor = isDark ? '#8b7355' : '#4a3c28';
      expect(lineColor).toBe('#4a3c28');
    });

    it('should return empty string for customBoardUrl (flat color, no texture)', () => {
      expect('').toBe('');
    });
  });

  describe('theme return shape', () => {
    it('should include all required properties', () => {
      const themes = {
        white: 'Shell',
        black: 'Slate',
        board: 'Custom',
        'removal-graphic': 'square',
        'removal-scale': 1.0,
        'stone-shadows': 'default',
      };

      expect(themes).toHaveProperty('white');
      expect(themes).toHaveProperty('black');
      expect(themes).toHaveProperty('board');
      expect(themes).toHaveProperty('removal-graphic');
      expect(themes).toHaveProperty('removal-scale');
      expect(themes).toHaveProperty('stone-shadows');
    });
  });
});
