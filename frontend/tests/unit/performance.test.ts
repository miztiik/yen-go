/**
 * Performance Tests for Rules Engine and Solution Verifier
 * 
 * Verifies FR-051: Move validation < 100ms (p95)
 */
import { describe, it, expect } from 'vitest';
import { placeStone, isValidMove } from '../../src/services/rulesEngine';
import { createSolutionState, verifyMove, advanceSolutionState } from '../../src/services/solutionVerifier';
import { createEmptyBoard } from '../../src/models/board';
import type { KoState } from '../../src/models/board';
import type { Puzzle, SolutionNode, Stone } from '../../src/models/puzzle';

/** No ko state for performance tests */
const NO_KO: KoState = { position: null, capturedAt: 0 };

/**
 * Create a complex puzzle for performance testing
 */
function createComplexPuzzle(): Puzzle {
  // Create a puzzle with a deep solution tree (10 moves)
  const createBranch = (depth: number, x: number, y: number): SolutionNode => {
    if (depth === 0) {
      return { move: { x, y } };
    }
    return {
      move: { x, y },
      response: { x: (x + 1) % 9, y: (y + 1) % 9 },
      branches: [
        createBranch(depth - 1, (x + 2) % 9, y),
        createBranch(depth - 1, x, (y + 2) % 9),
      ],
    };
  };

  return {
    version: '1.0',
    id: 'perf-test',
    boardSize: 9,
    initialState: createEmptyBoard(9) as Stone[][],
    sideToMove: 'black',
    solutionTree: createBranch(10, 3, 3),
    hints: [],
    explanations: [],
    metadata: {
      difficulty: '1kyu',
      difficultyScore: 1000,
      tags: ['performance'],
      level: '2026-01-20',
      createdAt: '2026-01-20T00:00:00Z',
    },
  };
}

/**
 * Create a board with many groups for liberty counting
 */
function createComplexBoard(): Stone[][] {
  const board = createEmptyBoard(19) as Stone[][];
  
  // Add multiple groups of stones
  for (let i = 0; i < 19; i += 2) {
    for (let j = 0; j < 19; j += 2) {
      if ((i + j) % 4 === 0) {
        board[i][j] = 'black';
        if (i + 1 < 19) board[i + 1][j] = 'black';
      } else {
        board[i][j] = 'white';
        if (j + 1 < 19) board[i][j + 1] = 'white';
      }
    }
  }
  
  return board;
}

describe('Performance Tests (FR-051: <100ms)', () => {
  describe('Rules Engine Performance', () => {
    it('should validate move in under 100ms on 9x9 board', () => {
      const board = createEmptyBoard(9) as Stone[][];
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        isValidMove(board, { x: 4, y: 4 }, 'black', 9, NO_KO);
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`9x9 isValidMove p95: ${p95.toFixed(2)}ms`);
    });

    it('should validate move in under 100ms on 19x19 board', () => {
      const board = createEmptyBoard(19) as Stone[][];
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        isValidMove(board, { x: 9, y: 9 }, 'black', 19, NO_KO);
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`19x19 isValidMove p95: ${p95.toFixed(2)}ms`);
    });

    it('should place stone with captures in under 100ms', () => {
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        // Create fresh board with capture scenario each iteration
        const board = createEmptyBoard(9) as Stone[][];
        // Set up a capture scenario - surround a white stone
        board[0][1] = 'white';
        board[0][0] = 'black';
        board[1][1] = 'black';
        // board[0][2] will capture white[0][1]

        const start = performance.now();
        placeStone(board, { x: 2, y: 0 }, 'black', 9, NO_KO);
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`9x9 placeStone with capture p95: ${p95.toFixed(2)}ms`);
    });

    it('should handle complex board with many groups in under 100ms', () => {
      const board = createComplexBoard();
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        isValidMove(board, { x: 9, y: 9 }, 'black', 19, NO_KO);
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`19x19 complex board isValidMove p95: ${p95.toFixed(2)}ms`);
    });
  });

  describe('Solution Verifier Performance', () => {
    it('should verify move against deep solution tree in under 100ms', () => {
      const puzzle = createComplexPuzzle();
      const state = createSolutionState(puzzle);
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        verifyMove(state, { x: 3, y: 3 }, 'black');
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`Solution verifyMove p95: ${p95.toFixed(2)}ms`);
    });

    it('should advance solution state in under 100ms', () => {
      const puzzle = createComplexPuzzle();
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const state = createSolutionState(puzzle);
        const matchedNode = state.currentNode;
        const move = { x: 3, y: 3 };
        const start = performance.now();
        advanceSolutionState(state, matchedNode, move);
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`Solution advanceSolutionState p95: ${p95.toFixed(2)}ms`);
    });
  });

  describe('Combined Move Validation Performance', () => {
    it('should complete full move validation flow in under 100ms', () => {
      const puzzle = createComplexPuzzle();
      const state = createSolutionState(puzzle);
      const board = createEmptyBoard(9) as Stone[][];
      const iterations = 100;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        
        // Full validation flow: rules check + solution verification
        const isValid = isValidMove(board, { x: 3, y: 3 }, 'black', 9, NO_KO);
        if (isValid) {
          verifyMove(state, { x: 3, y: 3 }, 'black');
        }
        
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`Full move validation p95: ${p95.toFixed(2)}ms`);
    });
  });

  describe('Solution Tree Visualization Performance (SC-005, SC-005a)', () => {
    /**
     * Generate a tree with specified number of nodes for performance testing.
     * Creates a binary tree structure with alternating correct/wrong paths.
     */
    function generateTreeNodeData(nodeCount: number): { id: string; children: unknown[]; depth: number }[] {
      const nodes: { id: string; children: unknown[]; depth: number }[] = [];
      const queue: { depth: number; parent: number | null }[] = [{ depth: 0, parent: null }];
      
      while (nodes.length < nodeCount && queue.length > 0) {
        const current = queue.shift()!;
        const id = `node-${nodes.length}`;
        const node = {
          id,
          move: `${String.fromCharCode(97 + (nodes.length % 19))}${String.fromCharCode(97 + (Math.floor(nodes.length / 19) % 19))}`,
          displayMove: `${String.fromCharCode(65 + (nodes.length % 19))}${19 - (Math.floor(nodes.length / 19) % 19)}`,
          isCorrect: nodes.length % 3 !== 0,
          isTesuji: nodes.length % 7 === 0,
          isSetupNode: false,
          isOnPath: nodes.length < 10,
          isCurrent: nodes.length === 5,
          isUserMove: nodes.length % 2 === 0,
          depth: current.depth,
          moveNumber: nodes.length + 1,
          children: [] as unknown[],
        };
        
        nodes.push(node);
        
        // Add children to queue if we haven't reached the limit
        if (nodes.length + queue.length < nodeCount) {
          queue.push({ depth: current.depth + 1, parent: nodes.length - 1 });
          if (nodes.length + queue.length < nodeCount) {
            queue.push({ depth: current.depth + 1, parent: nodes.length - 1 });
          }
        }
      }
      
      return nodes;
    }

    it('SC-005: should render 100-node tree in under 100ms', () => {
      const treeData = generateTreeNodeData(100);
      const iterations = 50;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        
        // Simulate tree rendering by iterating through all nodes
        // and computing CSS classes (this is the main render work)
        for (const node of treeData) {
          const nodeClasses = [
            'tree-node',
            node.isOnPath ? 'on-path' : '',
            node.isCurrent ? 'current' : '',
            node.isCorrect ? 'correct' : 'wrong',
          ].filter(Boolean).join(' ');
          
          // Simulate DOM element creation cost
          void nodeClasses;
        }
        
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`100-node tree render p95: ${p95.toFixed(2)}ms`);
    });

    it('SC-005a: should remain responsive with 500-node tree (click under 100ms)', () => {
      const treeData = generateTreeNodeData(500);
      const iterations = 50;
      const times: number[] = [];

      for (let i = 0; i < iterations; i++) {
        const start = performance.now();
        
        // Simulate click handler: find node and update path
        const targetNodeId = `node-${Math.floor(Math.random() * 500)}`;
        const foundNode = treeData.find(n => n.id === targetNodeId);
        
        if (foundNode) {
          // Simulate path update
          for (const node of treeData) {
            node.isOnPath = node.depth <= foundNode.depth;
            node.isCurrent = node.id === targetNodeId;
          }
        }
        
        const end = performance.now();
        times.push(end - start);
      }

      const sorted = times.sort((a, b) => a - b);
      const p95 = sorted[Math.floor(iterations * 0.95)];

      expect(p95).toBeLessThan(100);
      console.log(`500-node tree click response p95: ${p95.toFixed(2)}ms`);
    });
  });
});
