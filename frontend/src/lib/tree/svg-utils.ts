/**
 * SVG Utility Functions for Tree Rendering
 * @module lib/tree/svg-utils
 *
 * Pure functions that create SVG attribute objects.
 * These return data, not JSX - components use these to render.
 *
 * Feature: 056-solution-tree-visualization
 * Tasks: T003
 *
 * Constitution Compliance:
 * - VI. Type Safety: Fully typed return values
 * - X. Accessibility: ARIA attributes included
 */

import type {
  StoneAttributes,
  LabelAttributes,
  MarkerAttributes,
  VisualTreeNode,
} from '../../types/tree';
import {
  STONE_RADIUS,
  LABEL_FONT_SIZE,
  COLORS,
  PATH,
  GRID_SIZE,
  GRID_OFFSET,
} from './constants';

// ============================================================================
// Stone Rendering
// ============================================================================

/**
 * Creates attributes for an SVG circle representing a Go stone.
 *
 * @param svgX - Center X coordinate in SVG space
 * @param svgY - Center Y coordinate in SVG space
 * @param player - 'B' for black, 'W' for white
 * @returns StoneAttributes for rendering
 */
export function createStoneAttributes(
  svgX: number,
  svgY: number,
  player: 'B' | 'W'
): StoneAttributes {
  const isBlack = player === 'B';
  return {
    cx: svgX,
    cy: svgY,
    r: STONE_RADIUS,
    fill: isBlack ? COLORS.stone.black : COLORS.stone.white,
    stroke: isBlack ? COLORS.stone.blackStroke : COLORS.stone.whiteStroke,
    strokeWidth: 1,
  };
}

// ============================================================================
// Label Rendering
// ============================================================================

/**
 * Creates attributes for an SVG text label on a stone.
 *
 * @param svgX - Center X coordinate (same as stone)
 * @param svgY - Center Y coordinate (same as stone)
 * @param player - Stone color to determine text color
 * @returns LabelAttributes for rendering
 */
export function createLabelAttributes(
  svgX: number,
  svgY: number,
  player: 'B' | 'W'
): LabelAttributes {
  const isBlack = player === 'B';
  return {
    x: svgX,
    y: svgY,
    textAnchor: 'middle',
    dominantBaseline: 'central',
    fill: isBlack ? COLORS.label.onBlack : COLORS.label.onWhite,
    fontSize: LABEL_FONT_SIZE,
    fontWeight: '500',
  };
}

// ============================================================================
// Path Rendering
// ============================================================================

/**
 * Creates an SVG path data string connecting parent to child node.
 * Uses simple straight lines (Besogo approach).
 *
 * @param parent - Parent node position
 * @param child - Child node position
 * @returns SVG path 'd' attribute string
 */
export function createPathData(
  parent: { svgX: number; svgY: number },
  child: { svgX: number; svgY: number }
): string {
  // Simple straight line from parent to child
  return `M ${parent.svgX} ${parent.svgY} L ${child.svgX} ${child.svgY}`;
}

/**
 * Creates attributes for an edge path between nodes.
 *
 * @param isOnCurrentPath - Whether this edge is part of current navigation path
 * @returns SVG path attributes object
 */
export function createPathAttributes(isOnCurrentPath: boolean): {
  stroke: string;
  strokeWidth: number;
  fill: string;
} {
  return {
    stroke: isOnCurrentPath ? COLORS.path.current : COLORS.path.default,
    strokeWidth: isOnCurrentPath ? PATH.currentStrokeWidth : PATH.strokeWidth,
    fill: 'none',
  };
}

// ============================================================================
// Marker Rendering
// ============================================================================

/**
 * Creates attributes for the current position marker.
 * This is a highlight rectangle/circle behind the current stone.
 *
 * @param svgX - Center X coordinate
 * @param svgY - Center Y coordinate
 * @returns MarkerAttributes for rendering
 */
export function createCurrentMarkerAttributes(
  svgX: number,
  svgY: number
): MarkerAttributes {
  const size = STONE_RADIUS * 2.5;
  return {
    x: svgX - size / 2,
    y: svgY - size / 2,
    width: size,
    height: size,
    fill: COLORS.state.current,
    opacity: 0.3,
    rx: size / 2, // Circular marker
    stroke: COLORS.state.focus,
    strokeWidth: 2,
  };
}

/**
 * Creates attributes for the hover highlight.
 *
 * @param svgX - Center X coordinate
 * @param svgY - Center Y coordinate
 * @returns MarkerAttributes for rendering
 */
export function createHoverMarkerAttributes(
  svgX: number,
  svgY: number
): MarkerAttributes {
  const size = STONE_RADIUS * 2.2;
  return {
    x: svgX - size / 2,
    y: svgY - size / 2,
    width: size,
    height: size,
    fill: COLORS.state.hover,
    opacity: 0.2,
    rx: size / 2,
  };
}

// ============================================================================
// Correctness Indicator (FR-022)
// ============================================================================

/**
 * Creates attributes for correctness indicator ring.
 * Shows green/red ring around stones based on correctness.
 *
 * @param svgX - Center X coordinate
 * @param svgY - Center Y coordinate
 * @param isCorrect - Whether the move is correct
 * @returns Circle attributes for the indicator ring
 */
export function createCorrectnessIndicatorAttributes(
  svgX: number,
  svgY: number,
  isCorrect: boolean
): StoneAttributes {
  return {
    cx: svgX,
    cy: svgY,
    r: STONE_RADIUS * 1.2,
    fill: 'none',
    stroke: isCorrect ? COLORS.correctness.correct : COLORS.correctness.wrong,
    strokeWidth: 3,
  };
}

// ============================================================================
// Coordinate Helpers
// ============================================================================

/**
 * Converts grid position to SVG coordinates.
 *
 * @param gridX - X position in grid units (column/depth)
 * @param gridY - Y position in grid units (row/variation)
 * @returns SVG coordinates
 */
export function gridToSvg(
  gridX: number,
  gridY: number
): { svgX: number; svgY: number } {
  return {
    svgX: gridX * GRID_SIZE + GRID_OFFSET,
    svgY: gridY * GRID_SIZE + GRID_OFFSET,
  };
}

/**
 * Converts SVG coordinates to grid position.
 * Useful for hit testing on clicks.
 *
 * @param svgX - X coordinate in SVG space
 * @param svgY - Y coordinate in SVG space
 * @returns Grid position (may be fractional)
 */
export function svgToGrid(
  svgX: number,
  svgY: number
): { gridX: number; gridY: number } {
  return {
    gridX: (svgX - GRID_OFFSET) / GRID_SIZE,
    gridY: (svgY - GRID_OFFSET) / GRID_SIZE,
  };
}

/**
 * Converts SGF coordinate (e.g., "ba") to human-readable format (e.g., "C2").
 * Uses standard Go notation: letters for columns (A-T, skipping I),
 * numbers for rows (1-19 from bottom).
 *
 * @param sgfCoord - SGF coordinate string (e.g., "ba", "dd")
 * @param boardSize - Board size (default 19)
 * @returns Human-readable coordinate (e.g., "B1", "D4")
 */
export function sgfToDisplayCoord(sgfCoord: string, boardSize = 19): string {
  if (!sgfCoord || sgfCoord.length < 2) {
    return '';
  }

  // SGF uses 'a' = 0 for both x and y
  const x = sgfCoord.charCodeAt(0) - 97; // 'a' = 0
  const y = sgfCoord.charCodeAt(1) - 97; // 'a' = 0

  // Column: A-T (skipping I)
  const colLetters = 'ABCDEFGHJKLMNOPQRST'; // Note: no 'I'
  const col = x < colLetters.length ? colLetters[x] : '?';

  // Row: numbered from bottom (1 = row 0 in SGF for standard display)
  // In SGF, 'a' row is at the top, so we invert
  const row = boardSize - y;

  return `${col}${row}`;
}

// ============================================================================
// ViewBox Calculation
// ============================================================================

/**
 * Calculates the SVG viewBox dimensions for a tree.
 *
 * @param width - Width in grid units
 * @param height - Height in grid units
 * @param padding - Padding in grid units (default 0.5)
 * @returns ViewBox dimensions
 */
export function calculateViewBox(
  width: number,
  height: number,
  padding = 0.5
): { width: number; height: number; minX: number; minY: number } {
  const paddedWidth = (width + padding * 2) * GRID_SIZE;
  const paddedHeight = (height + padding * 2) * GRID_SIZE;
  const minX = -padding * GRID_SIZE;
  const minY = -padding * GRID_SIZE;

  return {
    width: paddedWidth,
    height: paddedHeight,
    minX,
    minY,
  };
}

// ============================================================================
// Hit Testing
// ============================================================================

/**
 * Checks if a click position hits a node.
 *
 * @param clickSvgX - Click X in SVG coordinates
 * @param clickSvgY - Click Y in SVG coordinates
 * @param node - Node to test
 * @returns True if click is within stone radius
 */
export function isClickOnNode(
  clickSvgX: number,
  clickSvgY: number,
  node: VisualTreeNode
): boolean {
  const dx = clickSvgX - node.layout.svgX;
  const dy = clickSvgY - node.layout.svgY;
  const distance = Math.sqrt(dx * dx + dy * dy);

  // Use slightly larger hit area for easier clicking
  return distance <= STONE_RADIUS * 1.3;
}

/**
 * Finds the closest node to a click position.
 *
 * @param clickSvgX - Click X in SVG coordinates
 * @param clickSvgY - Click Y in SVG coordinates
 * @param nodes - All nodes to search
 * @returns Closest node if within hit radius, undefined otherwise
 */
export function findNodeAtPosition(
  clickSvgX: number,
  clickSvgY: number,
  nodes: VisualTreeNode[]
): VisualTreeNode | undefined {
  let closest: VisualTreeNode | undefined;
  let minDistance = Infinity;

  for (const node of nodes) {
    const dx = clickSvgX - node.layout.svgX;
    const dy = clickSvgY - node.layout.svgY;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < minDistance && distance <= STONE_RADIUS * 1.3) {
      minDistance = distance;
      closest = node;
    }
  }

  return closest;
}
