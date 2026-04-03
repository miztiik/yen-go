/**
 * Solution Tree Builder
 * @module lib/sgf-solution
 *
 * Builds a SolutionNode tree from parsed SGF data.
 * The tree is used for move validation during puzzle solving.
 *
 * Consolidated from the sgf directory during Spec 129.
 *
 * Key Conventions:
 * - Moves with BM[] property are wrong moves (isCorrect: false)
 * - Moves with TE[] property are tesuji/key moves (isTesuji: true)
 * - Moves with "wrong"/"失敗" in comment are wrong (isCorrect: false)
 * - All other SGF moves are correct paths (isCorrect: true)
 * - Multiple correct first moves appear as sibling variations
 * - Opponent responses are included in the tree
 *
 *
 * Spec 012: Frontend Refutation Tree Support
 */

import type { SGFNode } from '@/types/sgf';
import type { SolutionNode } from '@/types/puzzle-internal';

// ============================================================================
// Solution Tree Building
// ============================================================================

/**
 * Build a SolutionNode tree from parsed SGF root node.
 *
 * The SGF tree structure is preserved:
 * - Each SGFNode with a B or W property becomes a SolutionNode
 * - Children (variations) become children in the solution tree
 * - isCorrect is true for all nodes (they're all valid solution paths)
 * - isUserMove is determined by comparing player to sideToMove
 *
 * @param root - Parsed SGF root node (should have children with moves)
 * @param sideToMove - Which side plays first (puzzle's perspective)
 * @returns Root SolutionNode representing all correct solution paths
 *
 * @example
 * const tree = buildSolutionTree(parsedSGF.root, 'B');
 * // tree.children contains all valid first moves
 */
export function buildSolutionTree(root: SGFNode, sideToMove: 'B' | 'W'): SolutionNode {
  // Create a virtual root node to hold all first-move variations
  // This ensures consistent structure whether there's 1 or many first moves
  const virtualRoot: SolutionNode = {
    move: '',  // Virtual root has no move
    player: sideToMove,
    isCorrect: true,
    isUserMove: false,  // Virtual root is not a user move
    children: [],
  };

  // Build tree from SGF children (the actual moves)
  for (const child of root.children) {
    const childNode = buildSolutionNodeFromSGF(child, sideToMove, sideToMove);
    if (childNode) {
      virtualRoot.children.push(childNode);
    }
  }

  return virtualRoot;
}

/**
 * Recursively build SolutionNode from an SGFNode.
 *
 * @param sgfNode - SGF node to convert
 * @param sideToMove - Puzzle's side to move (for isUserMove calculation)
 * @param expectedPlayer - Expected player for this move (alternates B/W)
 * @returns SolutionNode or null if no move found
 */
function buildSolutionNodeFromSGF(
  sgfNode: SGFNode,
  sideToMove: 'B' | 'W',
  expectedPlayer: 'B' | 'W'
): SolutionNode | null {
  const props = sgfNode.properties;

  // Extract move from B or W property
  const blackMove = props.B;
  const whiteMove = props.W;

  // Determine which move this node represents
  let move: string | undefined;
  let player: 'B' | 'W';

  if (blackMove !== undefined && typeof blackMove === 'string') {
    move = blackMove;
    player = 'B';
  } else if (whiteMove !== undefined && typeof whiteMove === 'string') {
    move = whiteMove;
    player = 'W';
  } else {
    // No move in this node - skip it but process children
    // This handles nodes with only setup properties
    if (sgfNode.children.length > 0) {
      // Pass through to children (keeps expected player same)
      for (const child of sgfNode.children) {
        return buildSolutionNodeFromSGF(child, sideToMove, expectedPlayer);
      }
    }
    return null;
  }

  // Determine if this is a user move
  // User moves when it's their turn (player matches sideToMove)
  const isUserMove = player === sideToMove;

  // Extract comment if present
  const comment = typeof props.C === 'string' ? props.C : undefined;

  // Spec 012: Detect wrong moves from BM[] property or comment
  const hasBadMoveProperty = props.BM !== undefined;
  const hasWrongComment = isWrongMoveComment(comment);
  const isCorrect = !hasBadMoveProperty && !hasWrongComment;

  // Spec 012: Detect tesuji from TE[] property
  const isTesuji = props.TE !== undefined;

  // Create the solution node
  const node: SolutionNode = {
    move,
    player,
    isCorrect,
    isUserMove,
    children: [],
    ...(comment && { comment }),
    ...(isTesuji && { isTesuji }),
  };

  // Recursively build children
  const nextPlayer: 'B' | 'W' = player === 'B' ? 'W' : 'B';
  for (const child of sgfNode.children) {
    const childNode = buildSolutionNodeFromSGF(child, sideToMove, nextPlayer);
    if (childNode) {
      node.children.push(childNode);
    }
  }

  return node;
}

/**
 * Check if a comment indicates a wrong move.
 * Detects various patterns used in tsumego collections.
 *
 * @param comment - The comment text from SGF C[] property
 * @returns true if the comment indicates this is a wrong move
 */
function isWrongMoveComment(comment: string | undefined): boolean {
  if (!comment) {
    return false;
  }
  
  const lowerComment = comment.toLowerCase();
  
  // Check for common wrong move indicators (case-insensitive)
  const wrongIndicators = [
    'wrong',
    'incorrect',
    'failure',
    'fails',
    'bad',
    'mistake',
  ];
  
  for (const indicator of wrongIndicators) {
    if (lowerComment.includes(indicator)) {
      return true;
    }
  }
  
  // Check for Chinese/Japanese wrong move indicators
  const cjkWrongIndicators = ['失敗', '错', '錯', '不正解', '失败'];
  
  for (const indicator of cjkWrongIndicators) {
    if (comment.includes(indicator)) {
      return true;
    }
  }
  
  return false;
}

// ============================================================================
// Tree Navigation
// ============================================================================

/**
 * Find a move among the direct children of a node.
 *
 * @param node - Current position in tree (look at its children)
 * @param move - SGF coordinate to find (e.g., "ba")
 * @returns The matching SolutionNode, or null if not found
 */
export function findMove(node: SolutionNode, move: string): SolutionNode | null {
  for (const child of node.children) {
    if (child.move === move) {
      return child;
    }
  }
  return null;
}

/**
 * Find a move anywhere in the tree (depth-first search).
 *
 * @param node - Root of subtree to search
 * @param move - SGF coordinate to find
 * @returns The matching SolutionNode, or null if not found
 */
export function findMoveDeep(node: SolutionNode, move: string): SolutionNode | null {
  if (node.move === move) {
    return node;
  }

  for (const child of node.children) {
    const found = findMoveDeep(child, move);
    if (found) {
      return found;
    }
  }

  return null;
}

// ============================================================================
// Path Validation
// ============================================================================

/**
 * Validate a sequence of moves against the solution tree.
 *
 * @param tree - Root of solution tree
 * @param moves - Array of SGF coordinates to validate
 * @returns True if all moves are valid at their positions
 */
export function validatePath(tree: SolutionNode, moves: string[]): boolean {
  let current: SolutionNode | null = tree;

  for (const move of moves) {
    if (!current) {
      return false;
    }

    const next = findMove(current, move);
    if (!next) {
      return false;
    }

    current = next;
  }

  return true;
}

/**
 * Validate a single move at the current position.
 *
 * @param current - Current position in tree
 * @param move - SGF coordinate to validate
 * @returns Object with isValid and the next node if valid
 */
export function validateMove(
  current: SolutionNode,
  move: string
): { isValid: boolean; nextNode: SolutionNode | null } {
  const nextNode = findMove(current, move);
  return {
    isValid: nextNode !== null,
    nextNode,
  };
}

// ============================================================================
// Tree Traversal
// ============================================================================

/**
 * Get the main line (first variation at each depth) from a tree.
 *
 * @param tree - Root of solution tree
 * @returns Array of moves in main line order
 */
export function getMainLine(tree: SolutionNode): string[] {
  const moves: string[] = [];
  let current: SolutionNode | null = tree;

  while (current && current.children.length > 0) {
    const firstChild: SolutionNode | undefined = current.children[0];
    if (firstChild) {
      moves.push(firstChild.move);
      current = firstChild;
    } else {
      break;
    }
  }

  return moves;
}

/**
 * Get all valid first moves (direct children of virtual root).
 *
 * @param tree - Root of solution tree (virtual root)
 * @returns Array of valid first move coordinates
 */
export function getValidFirstMoves(tree: SolutionNode): string[] {
  return tree.children.map((child) => child.move);
}

/**
 * Count total nodes in the tree.
 *
 * @param node - Root of subtree to count
 * @returns Number of nodes
 */
export function countNodes(node: SolutionNode): number {
  let count = 1;
  for (const child of node.children) {
    count += countNodes(child);
  }
  return count;
}

/**
 * Get the maximum depth of the tree.
 *
 * @param node - Root of subtree
 * @returns Maximum depth (0 for leaf node)
 */
export function getTreeDepth(node: SolutionNode): number {
  if (node.children.length === 0) {
    return 0;
  }

  let maxChildDepth = 0;
  for (const child of node.children) {
    const childDepth = getTreeDepth(child);
    if (childDepth > maxChildDepth) {
      maxChildDepth = childDepth;
    }
  }

  return 1 + maxChildDepth;
}

// ============================================================================
// Wrong Move Handling
// ============================================================================

/**
 * Create a wrong move node (dead-end).
 *
 * @param move - SGF coordinate of wrong move
 * @param player - Who played the wrong move
 * @returns SolutionNode marked as incorrect
 */
export function createWrongMoveNode(move: string, player: 'B' | 'W'): SolutionNode {
  return {
    move,
    player,
    isCorrect: false,
    isUserMove: true,
    children: [],
  };
}

/**
 * Check if a node is a leaf (end of solution branch).
 *
 * @param node - Node to check
 * @returns True if node has no children
 */
export function isLeafNode(node: SolutionNode): boolean {
  return node.children.length === 0;
}

/**
 * Check if completing this node completes the puzzle.
 *
 * @param node - Current node
 * @returns True if this completes the puzzle
 */
export function isCompletingNode(node: SolutionNode): boolean {
  if (!node.isUserMove || !node.isCorrect) {
    return false;
  }

  if (node.children.length === 0) {
    return true;
  }

  return node.children.every((child) => child.children.length === 0);
}

// ============================================================================
// Move Sequence Conversion
// ============================================================================

/**
 * Convert simple move sequences to a SolutionNode tree.
 *
 * @param sequences - Array of move sequences
 * @param playerSide - Which side plays first ('B' or 'W')
 * @returns Root SolutionNode tree
 */
export function buildSolutionTreeFromSequences(
  sequences: readonly (readonly string[])[],
  playerSide: 'B' | 'W'
): SolutionNode {
  const root: SolutionNode = {
    move: '',
    player: playerSide,
    isCorrect: true,
    isUserMove: false,
    children: [],
  };

  for (const sequence of sequences) {
    addSequenceToTree(root, sequence, playerSide);
  }

  return root;
}

/**
 * Add a move sequence to the tree, creating nodes as needed.
 */
function addSequenceToTree(
  root: SolutionNode,
  sequence: readonly string[],
  playerSide: 'B' | 'W'
): void {
  let currentNode = root;
  let currentPlayer: 'B' | 'W' = playerSide;

  for (const move of sequence) {
    let childNode = currentNode.children.find((c) => c.move === move);

    if (!childNode) {
      childNode = {
        move,
        player: currentPlayer,
        isCorrect: true,
        isUserMove: currentPlayer === playerSide,
        children: [],
      };
      currentNode.children.push(childNode);
    }

    currentNode = childNode;
    currentPlayer = currentPlayer === 'B' ? 'W' : 'B';
  }
}
