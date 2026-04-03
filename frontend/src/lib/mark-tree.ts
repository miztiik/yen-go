/**
 * Mark solution tree nodes with correct_answer / wrong_answer flags.
 *
 * After goban builds the move tree from `original_sgf`, each tree node
 * has a `.text` property (set from SGF `C[]` comments). Our puzzles use
 * `C[Correct!]` on correct terminal nodes and `C[Wrong...]` on wrong ones.
 *
 * This utility walks the engine's move tree post-construction and marks:
 * - Leaf nodes with "Correct" in text → correct_answer = true
 * - Leaf nodes with "Wrong" text or BM marker → wrong_answer = true
 * - Propagates correct_answer up through parent path
 *
 * The flags are used for TWO things:
 * 1. Puzzle events: goban fires puzzle-correct-answer/puzzle-wrong-answer
 * 2. Tree coloring: goban draws green/red circles in solution tree
 *
 * @module lib/mark-tree
 */

interface MoveTreeNode {
  text: string;
  trunk_next?: MoveTreeNode;
  branches: MoveTreeNode[];
  correct_answer: boolean;
  wrong_answer: boolean;
  parent: MoveTreeNode | null;
}

/**
 * Check if a node's comment text indicates a correct answer.
 */
function isCorrectNode(node: MoveTreeNode): boolean {
  const text = (node.text ?? '').toLowerCase();
  return text.includes('correct');
}

/**
 * Check if a node is a leaf (no children).
 */
function isLeaf(node: MoveTreeNode): boolean {
  return !node.trunk_next && node.branches.length === 0;
}

/**
 * Mark a path from leaf to root as correct_answer.
 */
function markPathCorrect(node: MoveTreeNode): void {
  let current: MoveTreeNode | null = node;
  while (current) {
    current.correct_answer = true;
    current = current.parent;
  }
}

/**
 * Mark an entire subtree as wrong_answer.
 */
function markSubtreeWrong(node: MoveTreeNode): void {
  node.wrong_answer = true;
  if (node.trunk_next) {
    markSubtreeWrong(node.trunk_next);
  }
  for (const branch of node.branches) {
    markSubtreeWrong(branch);
  }
}

/**
 * Walk the goban engine's move tree and mark correct_answer / wrong_answer
 * flags based on comment text content.
 *
 * Algorithm:
 * 1. Find ALL leaf nodes in the tree
 * 2. Leaves with "Correct" in comment → mark path to root as correct_answer
 * 3. All other branches → mark as wrong_answer
 *
 * @param moveTree - The root MoveTree node from goban.engine.move_tree
 */
export function markTreeFromComments(moveTree: unknown): void {
  const root = moveTree as MoveTreeNode;
  if (!root) return;

  // Step 1: Find all leaf nodes and mark correct paths
  const correctLeaves: MoveTreeNode[] = [];

  function findCorrectLeaves(node: MoveTreeNode): void {
    if (isLeaf(node) && isCorrectNode(node)) {
      correctLeaves.push(node);
    }
    if (node.trunk_next) {
      findCorrectLeaves(node.trunk_next);
    }
    for (const branch of node.branches) {
      findCorrectLeaves(branch);
    }
  }

  findCorrectLeaves(root);

  // Step 2: Mark correct paths (leaf → root)
  for (const leaf of correctLeaves) {
    markPathCorrect(leaf);
  }

  // Step 3: Mark everything NOT on a correct path as wrong
  // Walk the tree again — any node that isn't marked correct_answer
  // and has a move (not root) gets marked wrong_answer
  function markNonCorrectAsWrong(node: MoveTreeNode): void {
    // Skip the root node (x=-1, y=-1)
    if (node.parent && !node.correct_answer) {
      markSubtreeWrong(node);
      return; // Don't recurse further — entire subtree is marked
    }

    if (node.trunk_next) {
      markNonCorrectAsWrong(node.trunk_next);
    }
    for (const branch of node.branches) {
      markNonCorrectAsWrong(branch);
    }
  }

  markNonCorrectAsWrong(root);
}
