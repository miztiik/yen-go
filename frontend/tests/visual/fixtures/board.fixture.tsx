/** @jsxImportSource preact */
/**
 * Board Component Visual Test Fixtures
 * 
 * Defines various states of the Board component for visual testing.
 * Each fixture represents a specific visual state that should be captured.
 */

import type { BoardProps, SolutionMarker } from '../../../src/components/Board/Board';
import type { Stone, Coordinate, BoardSize } from '../../../src/models/puzzle';

/** Helper to create an empty stone grid */
function createEmptyGrid(size: BoardSize): Stone[][] {
  return Array.from({ length: size }, () => 
    Array.from({ length: size }, () => null as unknown as Stone)
  );
}

/** Helper to create a stone grid with specific stones */
function createGridWithStones(
  size: BoardSize,
  stones: Array<{ x: number; y: number; color: 'black' | 'white' }>
): Stone[][] {
  const grid = createEmptyGrid(size);
  for (const { x, y, color } of stones) {
    grid[y][x] = { color } as Stone;
  }
  return grid;
}

/** Board fixture definition */
export interface BoardFixture {
  name: string;
  description: string;
  props: BoardProps;
}

/**
 * Board Visual Test Fixtures
 * 
 * Each fixture tests a specific visual state of the Board component.
 */
export const boardFixtures: BoardFixture[] = [
  {
    name: 'empty-9x9',
    description: 'Empty 9x9 board with grid lines and star points',
    props: {
      boardSize: 9,
      stones: createEmptyGrid(9),
      interactive: false,
    },
  },
  {
    name: 'empty-13x13',
    description: 'Empty 13x13 board with grid lines and star points',
    props: {
      boardSize: 13,
      stones: createEmptyGrid(13),
      interactive: false,
    },
  },
  {
    name: 'empty-19x19',
    description: 'Empty 19x19 board with grid lines and star points',
    props: {
      boardSize: 19,
      stones: createEmptyGrid(19),
      interactive: false,
    },
  },
  {
    name: 'with-stones',
    description: 'Board with black and white stones placed',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 3, y: 2, color: 'white' },
        { x: 2, y: 3, color: 'white' },
        { x: 3, y: 3, color: 'black' },
        { x: 4, y: 4, color: 'black' }, // tengen
        { x: 6, y: 2, color: 'white' },
        { x: 6, y: 6, color: 'black' },
      ]),
      interactive: false,
    },
  },
  {
    name: 'with-last-move',
    description: 'Board showing the last move marker',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 3, y: 3, color: 'white' },
        { x: 4, y: 4, color: 'black' },
      ]),
      lastMove: { x: 4, y: 4 },
      interactive: false,
    },
  },
  {
    name: 'with-ghost-stone',
    description: 'Board showing a ghost stone preview',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 3, y: 3, color: 'white' },
      ]),
      ghostStone: { coord: { x: 5, y: 5 }, color: 'black' },
      interactive: true,
    },
  },
  {
    name: 'with-highlight',
    description: 'Board with highlighted move (hint)',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 3, y: 3, color: 'white' },
      ]),
      highlightedMove: { x: 4, y: 4 },
      interactive: false,
    },
  },
  {
    name: 'with-solution-markers',
    description: 'Board showing solution correct/wrong markers',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 3, y: 3, color: 'white' },
      ]),
      solutionMarkers: [
        { coord: { x: 4, y: 4 }, type: 'correct' },
        { coord: { x: 5, y: 5 }, type: 'wrong' },
        { coord: { x: 6, y: 6 }, type: 'optimal' },
      ] as SolutionMarker[],
      interactive: false,
    },
  },
  {
    name: 'rotated-90',
    description: 'Board rotated 90 degrees',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        { x: 2, y: 2, color: 'black' },
        { x: 6, y: 2, color: 'white' },
      ]),
      rotation: 90,
      interactive: false,
    },
  },
  {
    name: 'corner-pattern',
    description: 'Classic corner tsumego pattern',
    props: {
      boardSize: 9,
      stones: createGridWithStones(9, [
        // Black corner group
        { x: 0, y: 0, color: 'black' },
        { x: 1, y: 0, color: 'black' },
        { x: 0, y: 1, color: 'black' },
        { x: 1, y: 1, color: 'black' },
        { x: 2, y: 1, color: 'black' },
        { x: 0, y: 2, color: 'black' },
        // White surrounding
        { x: 2, y: 0, color: 'white' },
        { x: 3, y: 0, color: 'white' },
        { x: 3, y: 1, color: 'white' },
        { x: 3, y: 2, color: 'white' },
        { x: 1, y: 2, color: 'white' },
        { x: 2, y: 2, color: 'white' },
        { x: 0, y: 3, color: 'white' },
        { x: 1, y: 3, color: 'white' },
      ]),
      interactive: false,
    },
  },
];
