/**
 * useGoban -- Coordination hook for goban lifecycle management.
 *
 * Manages the full create -> configure -> resize -> destroy cycle for goban
 * renderer instances (SVGRenderer default, GobanCanvas opt-in).
 *
 * **OGS-native format:**
 * - Converts SGF to structured PuzzleObject via sgfToPuzzle()
 * - Passes initial_state + move_tree to goban — zero monkey-patches
 * - correct_answer/wrong_answer baked into MoveTreeJson from C[] comments
 *
 * **Lifecycle:**
 * 1. On mount / rawSgf change: preprocessSgf (metadata) → sgfToPuzzle → buildPuzzleConfig → instantiate
 * 2. GobanContainer handles ResizeObserver + centering
 * 3. On unmount / input change: goban.destroy(), cleanup
 *
 * @module useGoban
 */

import { useEffect, useRef, useState, useMemo } from "preact/hooks";
import type { RefObject } from "preact";
import type {
  GobanConfig,
  SVGRendererGobanConfig,
  CanvasRendererGobanConfig,
} from "goban";

// Runtime goban exports loaded via dynamic import for code splitting
type SVGRendererCtor = typeof import("goban").SVGRenderer;
type GobanCanvasCtor = typeof import("goban").GobanCanvas;

import { preprocessSgf } from "@lib/sgf-preprocessor";
import { buildPuzzleConfig } from "@lib/puzzle-config";
import { sgfToPuzzle } from "@lib/sgf-to-puzzle";
import type { TransformSettings, RendererPreference } from "../types/goban";
import { RENDERER_PREFERENCE_KEY } from "../types/goban";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Union type for goban renderer instances. */
export type GobanInstance = InstanceType<SVGRendererCtor> | InstanceType<GobanCanvasCtor>;

/** Active renderer type reported to consumers. */
export type ActiveRenderer = "svg" | "canvas";

/** A goban message forwarded from the library to our sidebar UI. */
export interface GobanMessage {
  /** The goban message_id (e.g. 'self_capture_not_allowed', 'illegal_ko_move'). */
  messageId: string;
  /** Human-readable formatted message text. */
  text: string;
}

/** Return value of {@link useGoban}. */
export interface UseGobanResult {
  /** Ref to the active goban instance (null before mount or after destroy). */
  readonly gobanRef: RefObject<GobanInstance | null>;
  /** Which renderer is currently active. */
  readonly activeRenderer: ActiveRenderer | null;
  /** Whether the goban instance is ready (mounted and configured). */
  readonly isReady: boolean;
  /** Current goban message (self-capture, ko, etc.) -- shown in sidebar. */
  readonly boardMessage: GobanMessage | null;
  /** The goban DOM element (created programmatically, mounted by GobanContainer). */
  readonly gobanDiv: HTMLElement | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getRendererPreference(): RendererPreference {
  try {
    const stored = localStorage.getItem(RENDERER_PREFERENCE_KEY);
    if (stored === "svg" || stored === "canvas" || stored === "auto") {
      return stored;
    }
  } catch { /* localStorage unavailable */ }
  return "svg";
}

function createRenderer(
  config: GobanConfig,
  preference: RendererPreference,
  SvgCtor: SVGRendererCtor,
  CanvasCtor: GobanCanvasCtor,
): [GobanInstance, ActiveRenderer] {
  if (preference === "canvas") {
    return [new CanvasCtor(config as CanvasRendererGobanConfig), "canvas"];
  }
  if (preference === "svg") {
    return [new SvgCtor(config as SVGRendererGobanConfig), "svg"];
  }
  // "auto" -- try SVG first, fallback to Canvas
  try {
    return [new SvgCtor(config as SVGRendererGobanConfig), "svg"];
  } catch {
    console.warn("[useGoban] SVGRenderer failed, falling back to GobanCanvas");
    return [new CanvasCtor(config as CanvasRendererGobanConfig), "canvas"];
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useGoban -- manages goban renderer lifecycle using OGS-native puzzle format.
 *
 * Default renderer: SVG (via OGS goban library's SVGRenderer with Shadow DOM).
 * Users can override via localStorage key "yengo-renderer-preference" ("svg" | "canvas" | "auto").
 *
 * Creates goban_div programmatically (GobanContainer mounts it).
 * Converts SGF to PuzzleObject via sgfToPuzzle(), passes structured data to goban.
 * Zero monkey-patches — correct_answer/wrong_answer baked into MoveTreeJson.
 *
 * @param rawSgf Raw SGF string (with YenGo properties — metadata extracted separately)
 * @param treeRef Optional ref for move tree container
 * @param transforms Optional transform settings
 * @param bounds Optional viewport bounds
 * @param labelPosition Coordinate label position ('all' | 'none')
 */
export function useGoban(
  rawSgf: string,
  treeRef?: RefObject<HTMLDivElement | null>,
  transforms?: TransformSettings,
  bounds?: { top: number; left: number; bottom: number; right: number },
  labelPosition?: 'all' | 'none',
): UseGobanResult {
  const gobanRef = useRef<GobanInstance | null>(null);
  const [activeRenderer, setActiveRenderer] = useState<ActiveRenderer | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [boardMessage, setBoardMessage] = useState<GobanMessage | null>(null);
  const [gobanDiv, setGobanDiv] = useState<HTMLElement | null>(null);

  const transformsKey = useMemo(
    () => (transforms ? JSON.stringify(transforms) : ""),
    [transforms],
  );
  const boundsKey = useMemo(
    () => (bounds ? JSON.stringify(bounds) : ""),
    [bounds],
  );

  useEffect(() => {
    if (!rawSgf) return;

    let cancelled = false;
    let gobanInstance: GobanInstance | null = null;

    // Create board container div (OGS pattern)
    // The goban library will create its own .Goban div inside this container
    const boardEl = document.createElement("div");
    boardEl.className = "goban-board-container";

    void (async () => {
      const { SVGRenderer, GobanCanvas } = await import("goban");
      if (cancelled) return;

      // Pipeline: preprocessSgf (metadata extraction) → sgfToPuzzle → buildPuzzleConfig
      // Metadata extracted for sidebar; SGF converted to structured PuzzleObject for goban
      const preprocessed = preprocessSgf(rawSgf);
      let puzzle;
      try {
        puzzle = sgfToPuzzle(preprocessed.cleanedSgf);
      } catch (err) {
        console.error("[useGoban] sgfToPuzzle failed:", err);
        if (!cancelled) { setIsReady(false); setActiveRenderer(null); }
        return;
      }
      const puzzleConfig = buildPuzzleConfig(puzzle, {
        boardDiv: boardEl,
        moveTreeContainer: treeRef?.current ?? null,
        bounds: bounds ?? null,
        labelPosition: labelPosition ?? 'all',
      });

      const preference = getRendererPreference();
      let renderer: ActiveRenderer;

      try {
        [gobanInstance, renderer] = createRenderer(puzzleConfig, preference, SVGRenderer, GobanCanvas);
      } catch (err) {
        console.error("[useGoban] Failed to create goban instance:", err);
        if (!cancelled) { setIsReady(false); setActiveRenderer(null); }
        return;
      }

      if (cancelled) { try { gobanInstance.destroy(); } catch { /* noop */ } return; }

      // No post-construction monkey-patches needed with OGS-native format:
      // - engine.phase stays "play" (not "finished")
      // - stone placement works out of the box
      // - correct_answer/wrong_answer baked into MoveTreeJson
      // - cursor starts at root position

      gobanRef.current = gobanInstance;
      setGobanDiv(boardEl);
      setActiveRenderer(renderer);
      setIsReady(true);

      // Forward goban messages to sidebar UI
      gobanInstance.on("show-message" as never, (data: { formatted: string; message_id: string }) => {
        setBoardMessage({ messageId: data.message_id ?? "unknown", text: data.formatted ?? "Invalid move" });
        // T08: Increased from 4s to 6s for better readability
        setTimeout(() => setBoardMessage(null), 6000);
      });
    })();

    return () => {
      cancelled = true;
      setIsReady(false);
      setBoardMessage(null);
      setGobanDiv(null);
      if (gobanRef.current) {
        try { gobanRef.current.destroy(); } catch { /* noop */ }
        gobanRef.current = null;
      }
      setActiveRenderer(null);
    };
  }, [rawSgf, transformsKey, boundsKey, labelPosition]);

  return { gobanRef, activeRenderer, isReady, boardMessage, gobanDiv };
}
