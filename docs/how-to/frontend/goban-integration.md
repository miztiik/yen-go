# How-To: Goban Integration

**Last Updated:** 2026-02-05  
**Spec:** 125 (Goban Library Migration)

This guide explains how to integrate the OGS goban library into a new puzzle page or component.

## Prerequisites

- Node.js 18+
- Frontend dependencies installed (`npm install`)
- Familiarity with Preact hooks

## Step 1: Create Your Page Component

Create a new page that will display a puzzle:

```tsx
// src/pages/MyPuzzlePage.tsx
import type { FunctionComponent } from 'preact';
import { useRef, useMemo, useLayoutEffect } from 'preact/hooks';
import { GobanRenderer } from '../components/GobanBoard';
import { useGoban } from '../hooks/useGoban';
import { usePuzzleState } from '../hooks/usePuzzleState';
import { extractYenGoProperties } from '../lib/sgf-preprocessor';

interface MyPuzzlePageProps {
  rawSgf: string;
  puzzleId: string;
}

export const MyPuzzlePage: FunctionComponent<MyPuzzlePageProps> = ({
  rawSgf,
  puzzleId,
}) => {
  // Container refs
  const boardRef = useRef<HTMLDivElement>(null);
  const treeRef = useRef<HTMLDivElement>(null);

  // Extract YenGo metadata
  const metadata = useMemo(
    () => extractYenGoProperties(rawSgf),
    [rawSgf]
  );

  // Initialize goban
  const { gobanRef, isReady } = useGoban(rawSgf, boardRef, treeRef);

  // Track puzzle state
  const { state, onGobanReady, reset, undo } = usePuzzleState(
    gobanRef.current,
    { moveOrder: metadata.moveOrder }
  );

  // Initialize goban when ready
  useLayoutEffect(() => {
    if (isReady) {
      onGobanReady();
    }
  }, [isReady, onGobanReady]);

  return (
    <div>
      <h1>Puzzle: {puzzleId}</h1>
      <GobanRenderer
        boardRef={boardRef}
        isReady={isReady}
        status={state.status}
      />
      <button onClick={reset}>Reset</button>
      <button onClick={undo}>Undo</button>
    </div>
  );
};
```

## Step 2: Use the useGoban Hook

The `useGoban` hook handles goban lifecycle:

```tsx
const { gobanRef, isReady } = useGoban(
  rawSgf,           // SGF string to load
  boardRef,         // Ref to mount container
  treeContainerRef, // Optional: Ref for variation tree
  transformSettings, // Optional: Flip/rotate/zoom settings
  zoomBounds,       // Optional: Auto-zoom bounds
);
```

### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `gobanRef` | `MutableRef<Goban \| null>` | Reference to goban instance |
| `isReady` | `boolean` | Whether goban is mounted and ready |

## Step 3: Use the usePuzzleState Hook

The `usePuzzleState` hook tracks puzzle solving state:

```tsx
const {
  state,           // Current puzzle state
  onGobanReady,    // Call when goban is mounted
  requestHint,     // Request hint tier (1-3)
  revealSolution,  // Show full solution
  reset,           // Reset puzzle
  undo,            // Undo last move
  elapsedMs,       // Time tracking
} = usePuzzleState(goban, { moveOrder });
```

### Puzzle State Object

```tsx
interface PuzzleState {
  status: 'idle' | 'playing' | 'wrong' | 'complete' | 'review';
  moveCount: number;
  wrongAttempts: number;
  hintsUsed: number;
  currentHintTier: number;
  solutionRevealed: boolean;
  currentComment?: string;
}
```

## Step 4: Add Board Transforms (Optional)

Use `useTransforms` for flip, rotate, and zoom:

```tsx
import { useTransforms } from '../hooks/useTransforms';

const {
  settings,
  toggleFlipH,
  toggleFlipV,
  toggleSwapColors,
  toggleZoom,
  randomize,
  reset: resetTransforms,
  applyTransforms,
  getZoomBounds,
} = useTransforms();

// Apply transforms to SGF
const transformedSgf = useMemo(
  () => applyTransforms(rawSgf),
  [rawSgf, applyTransforms]
);

// Pass transformed SGF to useGoban
const { gobanRef, isReady } = useGoban(transformedSgf, boardRef, treeRef);
```

## Step 5: Add Review Mode Markers (Optional)

Use `useBoardMarkers` to show correct/wrong dots in review mode:

```tsx
import { useBoardMarkers } from '../hooks/useBoardMarkers';

const isReviewMode = state.status === 'review' ||
  state.status === 'complete' ||
  state.solutionRevealed;

// Automatically adds markers in review mode
useBoardMarkers(gobanRef, isReviewMode);
```

## Complete Example

See [PuzzleSolvePage.tsx](../../frontend/src/pages/PuzzleSolvePage.tsx) for the full implementation.

## Testing

### E2E Tests

Use Playwright to test puzzle interactions:

```ts
// tests/e2e/my-puzzle.spec.ts
import { test, expect } from '@playwright/test';

test('puzzle loads and is intractable', async ({ page }) => {
  await page.goto('/puzzle/abc123');
  await expect(page.locator('[data-testid="goban-renderer"]')).toBeVisible();
  await expect(page.locator('[data-testid="goban-renderer"]')).toContainText('Ready');
});
```

### Visual Tests

Use Playwright visual regression:

```ts
// tests/visual/my-puzzle.visual.spec.ts
import { test, expect } from '@playwright/test';

test('puzzle page matches snapshot', async ({ page }) => {
  await page.goto('/puzzle/abc123');
  await page.waitForSelector('[data-testid="goban-renderer"]:has-text("Ready")');
  await expect(page).toHaveScreenshot('my-puzzle.png');
});
```

## Troubleshooting

### Goban Not Rendering

1. **Check refs**: Ensure `boardRef` is attached to a visible DOM element
2. **Check SGF**: Validate SGF string is not empty and parseable
3. **Check container size**: goban needs non-zero width/height

### Puzzle State Not Updating

1. **Check onGobanReady**: Ensure it's called after `isReady` is true
2. **Check goban instance**: Ensure `gobanRef.current` is not null

### Transform Issues

1. **Key changes**: If transforms don't apply, ensure component re-mounts
2. **Zoom bounds**: Call `getZoomBounds()` after transforms are applied

## See Also

- [Architecture: Goban Integration](../architecture/frontend/goban-integration.md) — Design decisions
- [Testing Guide](../architecture/frontend/testing.md) — Test patterns
- [Puzzle Solving Architecture](../architecture/frontend/puzzle-solving.md) — Solving lifecycle
