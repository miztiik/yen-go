/**
 * useTransforms Hook
 * @module hooks/useTransforms
 *
 * Manages board transformation settings (flip H/V, rotation CW, color swap).
 * Triggers goban re-initialization when transforms change.
 *
 * Spec 125, Task T057
 * User Story 2: Board Transformations
 */

import { useState, useCallback, useMemo } from 'preact/hooks';
import {
  type TransformSettings,
  DEFAULT_TRANSFORM_SETTINGS,
  transformPuzzleSgf,
} from '../lib/sgf-preprocessor';

export interface UseTransformsResult {
  /**
   * Current transform settings.
   */
  settings: TransformSettings;

  /**
   * Toggle horizontal flip.
   */
  toggleFlipH: () => void;

  /**
   * Toggle vertical flip.
   */
  toggleFlipV: () => void;

  /**
   * Toggle diagonal flip (matrix transposition).
   */
  toggleFlipDiag: () => void;

  /**
   * Rotate board 90° clockwise (cycles through 0→90→180→270→0).
   */
  rotateCW: () => void;

  /**
   * Rotate board 90° counter-clockwise (cycles through 0→270→180→90→0).
   */
  rotateCCW: () => void;

  /**
   * Toggle color swap (black ↔ white).
   */
  toggleSwapColors: () => void;

  /**
   * Randomize all transforms (for puzzle variety).
   */
  randomize: () => void;

  /**
   * Reset all transforms to default (disabled).
   */
  reset: () => void;

  /**
   * Apply transforms to an SGF string.
   * @param sgf Original SGF
   * @param boardSize Board size (default 19)
   * @returns Transformed SGF
   */
  applyTransforms: (sgf: string, boardSize?: number) => string;

  /**
   * Whether any transform is currently active.
   */
  hasActiveTransforms: boolean;

  /**
   * Version/key that changes when transforms change.
   * Use as a React key to trigger goban re-initialization.
   */
  transformKey: number;
}

/**
 * useTransforms
 *
 * Manages puzzle transform settings with toggle handlers.
 * Provides applyTransforms() to transform SGF before passing to goban.
 *
 * @param initialSettings Optional initial settings (defaults to all disabled)
 * @returns Transform state and handlers
 *
 * @example
 * ```tsx
 * const { settings, toggleFlipH, rotateCW, applyTransforms, transformKey } = useTransforms();
 *
 * // When user clicks "Flip H" button:
 * <button onClick={toggleFlipH}>Flip H</button>
 *
 * // When user clicks "Rotate" button:
 * <button onClick={rotateCW}>Rotate CW</button>
 *
 * // Transform SGF before passing to goban via useGoban hook:
 * const transformedSgf = applyTransforms(rawSgf);
 *
 * // Use transformKey to force goban re-init:
 * useGoban(transformedSgf, treeRef, settings);
 * ```
 */
export function useTransforms(
  initialSettings: TransformSettings = DEFAULT_TRANSFORM_SETTINGS
): UseTransformsResult {
  const [settings, setSettings] = useState<TransformSettings>(initialSettings);
  const [transformKey, setTransformKey] = useState(0);

  // Increment key whenever settings change to trigger re-init
  const updateSettings = useCallback((updater: (prev: TransformSettings) => TransformSettings) => {
    setSettings(updater);
    setTransformKey((k) => k + 1);
  }, []);

  const toggleFlipH = useCallback(() => {
    updateSettings((prev) => ({ ...prev, flipH: !prev.flipH }));
  }, [updateSettings]);

  const toggleFlipV = useCallback(() => {
    updateSettings((prev) => ({ ...prev, flipV: !prev.flipV }));
  }, [updateSettings]);

  const rotateCW = useCallback(() => {
    updateSettings((prev) => ({
      ...prev,
      rotation: ((prev.rotation + 90) % 360) as 0 | 90 | 180 | 270,
    }));
  }, [updateSettings]);

  const rotateCCW = useCallback(() => {
    updateSettings((prev) => ({
      ...prev,
      rotation: (((prev.rotation - 90) + 360) % 360) as 0 | 90 | 180 | 270,
    }));
  }, [updateSettings]);

  const toggleSwapColors = useCallback(() => {
    updateSettings((prev) => ({ ...prev, swapColors: !prev.swapColors }));
  }, [updateSettings]);

  const toggleFlipDiag = useCallback(() => {
    updateSettings((prev) => ({ ...prev, flipDiag: !prev.flipDiag }));
  }, [updateSettings]);

  const randomize = useCallback(() => {
    const rotations = [0, 90, 180, 270] as const;
    updateSettings(() => ({
      flipH: Math.random() > 0.5,
      flipV: Math.random() > 0.5,
      flipDiag: Math.random() > 0.5,
      rotation: rotations[Math.floor(Math.random() * 4)]!,
      swapColors: Math.random() > 0.5,
    }));
  }, [updateSettings]);

  const reset = useCallback(() => {
    updateSettings(() => DEFAULT_TRANSFORM_SETTINGS);
  }, [updateSettings]);

  const applyTransforms = useCallback(
    (sgf: string, boardSize?: number): string => {
      return transformPuzzleSgf(sgf, settings, boardSize);
    },
    [settings]
  );

  const hasActiveTransforms = useMemo(() => {
    return (
      settings.flipH ||
      settings.flipV ||
      settings.flipDiag ||
      settings.rotation !== 0 ||
      settings.swapColors
    );
  }, [settings]);

  return {
    settings,
    toggleFlipH,
    toggleFlipV,
    toggleFlipDiag,
    rotateCW,
    rotateCCW,
    toggleSwapColors,
    randomize,
    reset,
    applyTransforms,
    hasActiveTransforms,
    transformKey,
  };
}

export type { TransformSettings };

export default useTransforms;
