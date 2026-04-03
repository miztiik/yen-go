# Puzzle Solving Architecture

> **See also**:
>
> - [Architecture: State Management](./state-management.md) — How state flows
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — SGF format reference
> - [How-To: Frontend Development](../../how-to/frontend/) — Implementation guides

**Last Updated**: 2026-03-24

How the browser validates user moves against pre-computed solution trees.

---

## Design Principle

**No AI in Browser** — All validation is tree comparison, not Go calculation.

The backend pipeline pre-computes complete solution trees with all correct/incorrect variations. The browser simply traverses these trees.

---

## Solution Tree Structure

SGF encodes the full solution tree:

```
(;FF[4]GM[1]SZ[9]...
  ;B[cc]C[Correct! This threatens the corner.]
    (;W[dd]
      ;B[ee]C[Good follow-up])
  ;B[dd]C[Incorrect. This misses the vital point.]
)
```

Parsed into:

```typescript
// models/puzzle.ts
interface SolutionNode {
  move: Coordinate;              // {x, y}
  response?: Coordinate | null;  // Opponent auto-response
  branches?: SolutionNode[];     // Child continuations
  isWinning?: boolean;           // Terminal correct path
}

// lib/sgf-solution.ts builds this tree from parsed SGF data
// services/solutionVerifier.ts validates moves against this tree
```

---

## Validation Flow

```
User clicks → solutionVerifier.verifyMove() → VerificationResult
                    │
                    ├── isCorrect: true  → Apply move, auto-play opponent response
                    ├── isCorrect: false → Show feedback, allow retry
                    └── Not in tree      → Treat as incorrect
```

### Move Lookup

```typescript
function lookupMove(tree: MoveNode, move: Move): LookupResult {
  for (const child of tree.children) {
    if (movesEqual(child.move, move)) {
      return {
        found: true,
        node: child,
        isCorrect: child.isCorrect,
      };
    }
  }
  return { found: false };
}
```

### Correctness Determination

How we know if a move is correct:

1. **Comment prefix** — `Correct!`, `Good`, `Right` indicates correct
2. **Solution path** — Moves in main line are correct
3. **Variation depth** — First-level variations typically incorrect
4. **YenGo convention** — Solution tree structure encodes correctness

---

## Move Validation Process

```typescript
async function validateUserMove(
  puzzle: Puzzle,
  currentNode: MoveNode,
  userMove: Move,
): Promise<ValidationResult> {
  // 1. Look up in current node's children
  const lookup = lookupMove(currentNode, userMove);

  if (!lookup.found) {
    return {
      valid: false,
      feedback: "This move is not in the solution tree.",
      canRetry: true,
    };
  }

  // 2. Check if correct path
  if (!lookup.node.isCorrect) {
    return {
      valid: false,
      feedback: lookup.node.comment || "Try again.",
      canRetry: true,
    };
  }

  // 3. Correct move
  return {
    valid: true,
    feedback: lookup.node.comment,
    nextNode: lookup.node,
    puzzleComplete: lookup.node.children.length === 0,
  };
}
```

---

## Opponent Response

After a correct user move, the opponent plays automatically:

```typescript
function getOpponentResponse(node: MoveNode): MoveNode | null {
  // Find the main line continuation
  const mainLine = node.children.find((c) => c.isCorrect);
  return mainLine || node.children[0] || null;
}

async function playOpponentMove(node: MoveNode) {
  const response = getOpponentResponse(node);
  if (response) {
    // Animate opponent's move
    await animateMove(response.move);
    // Update current position
    setCurrentNode(response);
  }
}
```

---

## Hint System

Hints from `YH` property:

```typescript
interface HintState {
  hints: string[]; // ['Corner focus', 'Ladder pattern', 'cg']
  revealed: number; // How many shown (0-3)
}

function revealNextHint(state: HintState): string | null {
  if (state.revealed >= state.hints.length) return null;
  return state.hints[state.revealed++];
}

function parseCoordinateHint(hint: string): Coord | null {
  // Last hint may be coordinate like 'cg'
  if (hint.length === 2 && /^[a-s]{2}$/.test(hint)) {
    return sgfToCoord(hint);
  }
  return null;
}
```

---

## Puzzle Completion

A puzzle is complete when:

1. User reaches a terminal node (no children)
2. All required moves in solution played

```typescript
function isPuzzleComplete(node: MoveNode): boolean {
  // Terminal node with correct status
  return node.children.length === 0 && node.isCorrect;
}

async function onPuzzleComplete(puzzle: Puzzle) {
  // Update progress
  markPuzzleSolved(puzzle.id);

  // Check achievements
  await checkAchievements();

  // Show completion UI
  showCompletionModal(puzzle);
}
```

---

## Ko Handling

Ko context from `YK` property:

```typescript
type KoContext = "none" | "direct" | "approach";

function getKoContext(puzzle: Puzzle): KoContext {
  return puzzle.koContext || "none";
}

// Ko rules are pre-validated in solution tree
// Browser just follows the tree without ko calculation
```

---

## Error Handling

```typescript
async function handleMoveError(error: Error) {
  if (error instanceof ParseError) {
    console.error("Failed to parse SGF:", error);
    showError("Puzzle format error. Please try another puzzle.");
  } else {
    console.error("Move validation failed:", error);
    showError("Something went wrong. Please refresh.");
  }
}
```
