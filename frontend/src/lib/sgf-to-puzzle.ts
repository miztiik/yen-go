/**
 * SGF → Puzzle Object Adapter (OGS-native format)
 *
 * Converts a cleaned SGF string into an OGS-compatible puzzle object with
 * `initial_state`, `move_tree`, `width`, `height`, and `initial_player`.
 *
 * Uses comment-based correct/wrong marking: walks the tree looking for
 * leaf nodes with `C[Correct...]` text, marks those paths as correct_answer,
 * and everything else as wrong_answer. This supports multiple correct paths.
 *
 * Pipeline: Raw SGF → preprocessSgf() → sgfToPuzzle() → GobanConfig → goban
 *
 * Uses the canonical parser from sgf-metadata.ts (no duplicate parser).
 *
 * @module lib/sgf-to-puzzle
 */

// ---------------------------------------------------------------------------
// Types (matching goban's MoveTreeJson and GobanEngineInitialState)
// ---------------------------------------------------------------------------

/** Recursive move tree structure matching goban's MoveTreeJson. */
export interface MoveTreeJson {
  x: number;
  y: number;
  trunk_next?: MoveTreeJson;
  branches?: MoveTreeJson[];
  correct_answer?: boolean;
  wrong_answer?: boolean;
  text?: string;
}

/** Setup stone positions matching goban's GobanEngineInitialState. */
export interface InitialState {
  black?: string;
  white?: string;
}

/** Complete puzzle object ready for GobanConfig. */
export interface PuzzleObject {
  initial_state: InitialState;
  move_tree: MoveTreeJson;
  width: number;
  height: number;
  initial_player: 'black' | 'white';
}

// ---------------------------------------------------------------------------
// Canonical parser import (DRY — single parser in sgf-metadata.ts)
// ---------------------------------------------------------------------------

import { parseSgfToTree } from './sgf-metadata';
import type { SgfNode } from './sgf-metadata';

// ---------------------------------------------------------------------------
// Setup Stone Extraction
// ---------------------------------------------------------------------------

/**
 * Extract setup stones from root node properties.
 * Encodes as concatenated 2-char SGF coordinate pairs (goban format).
 *
 * AB[dp][pp] → "dppp"
 */
function extractInitialState(rootNode: SgfNode): InitialState {
  const state: InitialState = {};

  const blackStones = rootNode.properties['AB'];
  if (blackStones && blackStones.length > 0) {
    state.black = blackStones.filter((v) => v.length === 2).join('');
  }

  const whiteStones = rootNode.properties['AW'];
  if (whiteStones && whiteStones.length > 0) {
    state.white = whiteStones.filter((v) => v.length === 2).join('');
  }

  return state;
}

// ---------------------------------------------------------------------------
// Move Tree Conversion
// ---------------------------------------------------------------------------

/**
 * Determine the initial player (who plays first) from the SGF tree.
 *
 * Priority:
 * 1. PL[] property on root node (explicit)
 * 2. First B[] or W[] move in the tree (implicit)
 * 3. Default: "black"
 */
function determineInitialPlayer(rootNode: SgfNode): 'black' | 'white' {
  // Check PL property
  const pl = rootNode.properties['PL'];
  if (pl && pl[0]) {
    return pl[0].toUpperCase() === 'W' ? 'white' : 'black';
  }

  // Find first move in the tree
  function findFirstMove(node: SgfNode): 'black' | 'white' | null {
    if (node.properties['B']) return 'black';
    if (node.properties['W']) return 'white';
    for (const child of node.children) {
      const result = findFirstMove(child);
      if (result) return result;
    }
    return null;
  }

  return findFirstMove(rootNode) ?? 'black';
}

/**
 * Convert an SgfNode (with a B[] or W[] move) to a MoveTreeJson node.
 *
 * @param node The SGF node to convert
 * @param isTrunk Whether this node is on the trunk (main line).
 *   Only trunk nodes can have `trunk_next`. Branch nodes put ALL
 *   children in `branches[]`. This matches goban's MoveTree invariant:
 *   a non-trunk node cannot have trunk children.
 */
function convertNodeToMoveTree(node: SgfNode, isTrunk: boolean): MoveTreeJson | null {
  // Extract move coordinates
  const bMove = node.properties['B']?.[0];
  const wMove = node.properties['W']?.[0];
  const moveCoord = bMove ?? wMove;

  if (moveCoord === undefined) {
    // No move on this node — might be a setup-only node
    // If it has children, recurse to find the first move
    if (node.children.length > 0) {
      return convertNodeToMoveTree(node.children[0]!, isTrunk);
    }
    return null;
  }

  // Handle pass moves (empty coordinate or 'tt' on 19x19)
  if (moveCoord === '' || moveCoord === 'tt') {
    // Pass moves: use -1, -1 (goban convention)
    const moveNode: MoveTreeJson = { x: -1, y: -1 };

    // Extract comment
    const comment = node.properties['C']?.[0];
    if (comment) moveNode.text = comment;

    // Process children
    processChildren(node, moveNode, isTrunk);

    return moveNode;
  }

  if (moveCoord.length !== 2) return null;

  const x = moveCoord.charCodeAt(0) - 97; // 'a' = 0
  const y = moveCoord.charCodeAt(1) - 97;

  const moveNode: MoveTreeJson = { x, y };

  // Extract comment
  const comment = node.properties['C']?.[0];
  if (comment) moveNode.text = comment;

  // Process children
  processChildren(node, moveNode, isTrunk);

  return moveNode;
}

/**
 * Process children of a node and attach them as trunk_next/branches.
 *
 * Goban invariant: only trunk nodes can have `trunk_next`. If a node
 * is on a branch (isTrunk=false), ALL children go into `branches[]`.
 * This prevents the "Attempted trunk move made on non-trunk" error.
 *
 * @param node The SGF node whose children to process
 * @param moveNode The MoveTreeJson node to attach children to
 * @param isTrunk Whether the parent (moveNode) is on the trunk
 */
function processChildren(node: SgfNode, moveNode: MoveTreeJson, isTrunk: boolean): void {
  if (node.children.length === 0) return;

  const childMoves: MoveTreeJson[] = [];
  for (let i = 0; i < node.children.length; i++) {
    // Only the first child of a trunk node is itself trunk
    const childIsTrunk = isTrunk && i === 0;
    const childMove = convertNodeToMoveTree(node.children[i]!, childIsTrunk);
    if (childMove) {
      childMoves.push(childMove);
    }
  }

  if (childMoves.length === 0) return;

  if (isTrunk) {
    // Trunk node: first child is trunk_next, rest are branches
    const trunk = childMoves[0];
    if (trunk) {
      moveNode.trunk_next = trunk;
    }
    if (childMoves.length > 1) {
      moveNode.branches = childMoves.slice(1);
    }
  } else {
    // Branch node: ALL children go into branches (no trunk_next allowed)
    moveNode.branches = childMoves;
  }
}

/**
 * Mark correct_answer and wrong_answer flags on the move tree
 * based on comment text (C[] property).
 *
 * Algorithm:
 * 1. Find ALL leaf nodes in the tree
 * 2. Leaves with "Correct" in comment text → mark entire path to root as correct_answer
 * 3. All non-root nodes NOT on a correct path → mark as wrong_answer
 * 4. FALLBACK: If NO leaves have "Correct" comments, treat the trunk line as the
 *    correct path. This handles the majority of SGFs that don't use comment annotations.
 *
 * This supports multiple correct paths (not just trunk).
 *
 * @param root Root MoveTreeJson node (x=-1, y=-1)
 */
function markCorrectWrongFromComments(root: MoveTreeJson): void {
  // Step 1: Find all correct leaf nodes and mark paths to root
  const correctNodes = new Set<MoveTreeJson>();

  function findCorrectLeavesAndMark(
    node: MoveTreeJson,
    parent: MoveTreeJson | null,
    parentMap: Map<MoveTreeJson, MoveTreeJson | null>
  ): void {
    parentMap.set(node, parent);

    const isLeaf = !node.trunk_next && (!node.branches || node.branches.length === 0);

    if (isLeaf && node.text && node.text.toLowerCase().includes('correct')) {
      // Walk parent chain from this leaf → mark all as correct
      let current: MoveTreeJson | null | undefined = node;
      while (current) {
        correctNodes.add(current);
        current.correct_answer = true;
        current = parentMap.get(current) ?? null;
      }
    }

    if (node.trunk_next) {
      findCorrectLeavesAndMark(node.trunk_next, node, parentMap);
    }
    if (node.branches) {
      for (const branch of node.branches) {
        findCorrectLeavesAndMark(branch, node, parentMap);
      }
    }
  }

  const parentMap = new Map<MoveTreeJson, MoveTreeJson | null>();
  findCorrectLeavesAndMark(root, null, parentMap);

  // Step 2: FALLBACK — if no C[Correct...] annotations found, treat trunk as correct.
  // This handles ~90% of SGF files that lack comment annotations.
  if (correctNodes.size === 0) {
    markTrunkAsCorrect(root, correctNodes);
  }

  // Step 3: Mark everything NOT on a correct path as wrong_answer
  // Skip the root node (x=-1, y=-1) — it's the starting position, not a move
  function markNonCorrectAsWrong(node: MoveTreeJson, isRoot: boolean): void {
    if (!isRoot && !correctNodes.has(node)) {
      markWrongSubtree(node);
      return; // Don't recurse further — entire subtree is marked
    }

    if (node.trunk_next) {
      markNonCorrectAsWrong(node.trunk_next, false);
    }
    if (node.branches) {
      for (const branch of node.branches) {
        markNonCorrectAsWrong(branch, false);
      }
    }
  }

  markNonCorrectAsWrong(root, true);
}

/**
 * Mark the entire trunk line (main line) as correct_answer.
 * Used as fallback when no C[Correct...] leaf comments exist.
 * The trunk is the chain of trunk_next from root to the terminal node.
 * Branches off the trunk are left unmarked (will be marked wrong later).
 */
function markTrunkAsCorrect(root: MoveTreeJson, correctNodes: Set<MoveTreeJson>): void {
  let node: MoveTreeJson | undefined = root;
  while (node) {
    correctNodes.add(node);
    node.correct_answer = true;
    node = node.trunk_next;
  }
}

/**
 * Mark an entire subtree as wrong_answer.
 */
function markWrongSubtree(node: MoveTreeJson): void {
  node.wrong_answer = true;
  if (node.trunk_next) {
    markWrongSubtree(node.trunk_next);
  }
  if (node.branches) {
    for (const branch of node.branches) {
      markWrongSubtree(branch);
    }
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Convert a cleaned SGF string to an OGS-compatible puzzle object.
 *
 * The SGF should have YenGo custom properties already stripped
 * (via preprocessSgf). The returned object can be spread into
 * GobanConfig to create a puzzle instance without any workarounds.
 *
 * @param cleanedSgf SGF string with YenGo properties stripped
 * @returns PuzzleObject with initial_state, move_tree, dimensions, initial_player
 *
 * @example
 * ```ts
 * const preprocessed = preprocessSgf(rawSgf);
 * const puzzle = sgfToPuzzle(preprocessed.cleanedSgf);
 * const config: GobanConfig = {
 *   mode: "puzzle",
 *   ...puzzle,
 *   board_div: boardEl,
 *   puzzle_opponent_move_mode: "automatic",
 *   puzzle_player_move_mode: "free",
 * };
 * ```
 */
export function sgfToPuzzle(cleanedSgf: string): PuzzleObject {
  const rootNode = parseSgfToTree(cleanedSgf);
  if (!rootNode) {
    throw new Error('[sgf-to-puzzle] Failed to parse SGF tree');
  }

  // 1. Extract board size
  const szValues = rootNode.properties['SZ'];
  const size = szValues?.[0] ? parseInt(szValues[0], 10) : 19;
  const width = size;
  const height = size;

  // 2. Extract setup stones
  const initial_state = extractInitialState(rootNode);

  // 3. Determine initial player
  const initial_player = determineInitialPlayer(rootNode);

  // 4. Build move tree
  // Root node in MoveTreeJson: x=-1, y=-1 (no move, starting position)
  const moveTreeRoot: MoveTreeJson = { x: -1, y: -1 };

  // Extract comment from root node (if any survived stripping)
  const rootComment = rootNode.properties['C']?.[0];
  if (rootComment) moveTreeRoot.text = rootComment;

  // Convert children of root node to move tree
  // Root is always trunk — its first child continues the trunk line
  processChildren(rootNode, moveTreeRoot, true);

  // 5. Mark correct/wrong flags from C[] comment text
  markCorrectWrongFromComments(moveTreeRoot);

  return {
    initial_state,
    move_tree: moveTreeRoot,
    width,
    height,
    initial_player,
  };
}
