# Solution Trees in SGF

> **See also**:
>
> - [How-To: Create Adapter](../how-to/backend/create-adapter.md) — Handling move alternation
> - [Reference: Sanderland Adapter](../reference/adapters/sanderland.md) — Miai handling example
> - [Architecture: SGF Parsing](../architecture/backend/sgf-parsing.md) — Parser design

**Last Updated**: 2026-02-05

Understanding how Go puzzle solutions are represented as tree structures in SGF format.

---

## What is an SGF Solution Tree?

A **solution tree** represents all possible correct (and incorrect) move sequences for a Go puzzle. It's stored in the SGF file format as a tree of moves with branches.

### Basic Structure

```
Root (setup position)
├── Black move 1 (correct) ✓
│   └── White response
│       └── Black move 2 ✓
└── Black move 1 (wrong) ✗
    └── White refutation
```

In SGF notation:

```sgf
(;FF[4]GM[1]SZ[9]
  AB[aa][bb]AW[cc]   ; Setup: Black at aa, bb; White at cc
  (;B[dd]C[Correct]  ; First variation: correct
    ;W[ee]           ; White response
    ;B[ff])          ; Black continuation
  (;B[gg]C[Wrong]    ; Second variation: wrong
    ;W[hh]))         ; White refutation
```

---

## Sequential Moves vs. Variations

### Sequential Moves

In Go, players take turns: Black, White, Black, White...

Sequential moves are written as:

```sgf
;B[aa];W[bb];B[cc]
```

This means:

1. Black plays at aa
2. White responds at bb
3. Black continues at cc

### Variations (Branches)

When there are multiple choices at a position, SGF uses parentheses to create branches:

```sgf
(;B[aa])(;B[bb])
```

This means:

- Black can play at aa, OR
- Black can play at bb

These are **sibling variations** at the same position.

---

## Miai: Alternative First Moves

> **Miai** (見合い): Two equally valuable points where playing one makes the other unimportant.

In puzzle context, **miai** means multiple equally correct first moves. The player can choose any of them.

### Example: Two-Way Miai

Black can live by playing at A OR B (either works equally well):

```
. . B . .
B B W W .
. W . . .
```

```sgf
(;B[aa]C[Lives by making eye here])
(;B[ba]C[Also lives by playing here])
```

### Why This Matters for SGF

**WRONG** — Sequential moves (invalid Go):

```sgf
;B[aa];B[ba]  ← Black plays twice! Invalid.
```

**CORRECT** — Variations (miai alternatives):

```sgf
(;B[aa])(;B[ba])  ← Two choices for Black's first move
```

---

## Move Alternation Rule

**Go Rule**: Players MUST alternate turns.

| Pattern   | Valid? | Interpretation                    |
| --------- | ------ | --------------------------------- |
| B → W → B | ✓      | Normal sequence                   |
| B → B     | ✗      | Invalid as sequence, must be miai |
| W → W → W | ✗      | Invalid as sequence, must be miai |

### Detection in Code

Use `MoveAlternationDetector` to classify move patterns:

```python
from backend.puzzle_manager.core.move_alternation import MoveAlternationDetector

detector = MoveAlternationDetector()

# Alternating = valid sequence
detector.analyze([("B", "aa"), ("W", "bb")])
# → MoveAlternationResult.ALTERNATING

# Same color = miai
detector.analyze([("B", "aa"), ("B", "bb")])
# → MoveAlternationResult.MIAI
```

---

## Correct vs. Wrong Variations

Solution trees often include both correct moves (the player should find) and wrong moves (common mistakes with refutations).

### Marking Correctness

In YenGo SGF format, correct moves are marked in variation structure:

```sgf
(;FF[4]GM[1]SZ[9]
  (;B[dd]  ; Correct first move
    ;W[ee] ; Opponent response
    ;B[ff]) ; Correct continuation
  (;B[gg]C[Wrong - leads to death]
    ;W[hh]C[White captures]))
```

The frontend uses this structure to:

- Validate player moves
- Show feedback ("Correct!" or "Try again")
- Display the full solution tree

---

## Multi-Move Solutions

Complex puzzles have deeper trees with multiple levels:

```
Black move 1 (correct)
├── White response 1 (most common)
│   └── Black move 2 ✓
│       └── White response
│           └── Black move 3 ✓ (life)
└── White response 2 (tesuji attempt)
    └── Black move 2 (different) ✓
        └── White response
            └── Black move 3 ✓ (still lives)
```

---

## Flexible Move Order (Transpositions)

Some puzzles allow moves in different orders:

- Playing A→B→C gives same result as A→C→B
- Both paths are correct (transposition)

This is marked with `YO[flexible]` in YenGo puzzles:

```sgf
YO[flexible]  ; Move order is flexible
```

**Detection**: `MoveAlternationDetector` + comment analysis identifies transpositions.

---

## Summary Table

| Term             | Meaning                         | SGF Representation               |
| ---------------- | ------------------------------- | -------------------------------- |
| Sequential moves | One move after another          | `;B[aa];W[bb]`                   |
| Variations       | Different choices at same point | `(;B[aa])(;B[bb])`               |
| Miai             | Equally good alternatives       | Same-color moves as variations   |
| Correct move     | Part of winning solution        | Usually first variation          |
| Wrong move       | Common mistake                  | Other variations with refutation |
| Transposition    | Different order, same result    | `YO[flexible]` flag              |

---

## Related Documentation

- [How-To: Create Adapter](../how-to/backend/create-adapter.md) — Implementing miai detection
- [Reference: SGF Properties](../reference/sgf-properties.md) — YenGo custom properties
- [Architecture: SGF Parsing](../architecture/backend/sgf-parsing.md) — Parser implementation
