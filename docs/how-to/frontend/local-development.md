# Frontend Local Development

> **See also**:
>
> - [Architecture: Frontend Overview](../../architecture/frontend/overview.md) — Technology stack
> - [Architecture: Testing](../../architecture/frontend/testing.md) — Test architecture
> - [Getting Started: Development](../../getting-started/develop.md) — Initial setup

**Last Updated**: 2026-02-01

How to run the frontend locally for development.

---

## Prerequisites

- Node.js 18+
- npm 9+

---

## Quick Start

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app runs at http://localhost:5173/yen-go/

---

## Development Server

### Start Dev Server

```bash
npm run dev
```

Features:

- Hot Module Replacement (HMR)
- Fast refresh on code changes
- Error overlay
- Source maps

### Watch Mode Options

```bash
# Standard development
npm run dev

# Expose to network (for mobile testing)
npm run dev -- --host

# Custom port
npm run dev -- --port 3000
```

---

## Running Tests

### Unit Tests (Vitest)

```bash
# Watch mode (default)
npm test

# Single run
npm test -- --run

# With coverage
npm test -- --coverage

# Specific file
npm test -- tests/lib/puzzle.test.ts

# Specific test
npm test -- -t "should validate correct move"
```

### Visual Tests (Playwright)

Visual testing captures screenshots of components and compares them against baselines to detect unintended UI changes.

#### Quick Start

```bash
# Run all visual tests
npm run test:visual

# Update snapshots (baselines)
npm run test:visual:update

# Run specific test
npm run test:visual -- tests/visual/board.visual.ts

# Debug mode (headed)
npm run test:visual -- --headed
```

#### Principles

1. **Test Rendered Appearance**: Screenshots verify actual rendering, not just DOM presence
2. **Component Isolation**: Each component has its own visual test file
3. **State Coverage**: Test default, hover, focus, disabled, loading, and error states
4. **Responsive Testing**: Verify at mobile (375px), tablet (768px), and desktop (1280px)

#### Test File Structure

```
tests/visual/
├── baselines/       # Golden screenshots (committed to git)
├── fixtures/        # Test data
├── specs/           # Visual test specifications
│   ├── board.visual.spec.ts
│   ├── collections.visual.spec.ts
│   └── *.visual.spec.ts
├── templates/       # Test templates
│   └── component.visual.template.ts
├── test-results/    # Test output (gitignored)
└── README.md
```

#### Creating New Visual Tests

1. Copy the template:

   ```bash
   cp tests/visual/templates/component.visual.template.ts \
      tests/visual/specs/my-component.visual.spec.ts
   ```

2. Add fixture in `src/visual-tests.tsx`:

   ```tsx
   <div id="my-component-default">
     <MyComponent />
   </div>
   ```

3. Update test selectors to match your fixtures

4. Generate initial baselines:
   ```bash
   npx playwright test tests/visual/specs/my-component.visual.spec.ts --update-snapshots
   ```

#### Required States Per Component

| State        | Purpose                  | Required             |
| ------------ | ------------------------ | -------------------- |
| Default      | Initial render           | ✅ Yes               |
| Hover        | Mouse interaction        | If interactive       |
| Focus        | Keyboard focus indicator | ✅ For accessibility |
| Disabled     | Disabled appearance      | If applicable        |
| Loading      | Skeleton/spinner         | If async             |
| Error        | Error state              | If fail mode exists  |
| With Content | Populated state          | If data-driven       |

#### Best Practices

**Do:**

- Test one visual state per screenshot
- Use meaningful fixture IDs (`#board-with-stones`, not `#test-1`)
- Wait for animations to complete before capturing
- Include viewport size tests for responsive components

**Don't:**

- Test logic in visual tests (use unit tests)
- Capture unstable elements (animations, times, random IDs)
- Create overly large screenshots
- Skip the default state test

#### Troubleshooting Visual Tests

**Flaky Tests:**

```typescript
// Add wait for stability
await page.waitForLoadState("networkidle");
await page.waitForTimeout(200); // Wait for render
```

**Animation Interference:**

```typescript
// Disable animations in test
await page.addStyleTag({
  content:
    "*, *::before, *::after { animation: none !important; transition: none !important; }",
});
```

**Dynamic Content:**

```typescript
// Hide dynamic elements
await page
  .locator(".timestamp")
  .evaluate((el) => (el.style.visibility = "hidden"));
```

**Visual Test Failures:**

```bash
# Update baselines if intentional change
npm run test:visual:update

# View diff images
open tests/visual/test-results/
```

---

## Project Structure

```
frontend/
├── src/
│   ├── app.tsx           # Entry point, routing
│   ├── components/       # UI components
│   │   ├── Board/        # Go board renderer
│   │   ├── Puzzle/       # Puzzle display
│   │   └── ...
│   ├── lib/              # Core logic
│   │   ├── puzzle.ts     # Puzzle validation
│   │   ├── progress.ts   # Progress tracking
│   │   └── sgf-parser.ts # SGF parsing
│   ├── pages/            # Page components
│   ├── services/         # Data services
│   ├── models/           # TypeScript types
│   └── styles/           # CSS
├── public/               # Static assets
├── tests/                # Test files
│   ├── unit/             # Vitest tests
│   └── visual/           # Playwright tests
├── index.html            # Entry HTML
├── vite.config.ts        # Vite configuration
├── vitest.config.ts      # Vitest configuration
└── playwright.config.ts  # Playwright configuration
```

---

## TypeScript

### Strict Mode

TypeScript is in strict mode. Common patterns:

```typescript
// ✅ Proper typing
interface Props {
  puzzle: Puzzle;
  onSolve: (result: SolveResult) => void;
}

// ✅ Explicit null handling
const data = localStorage.getItem("key");
if (data === null) {
  return defaultValue;
}

// ✅ Type guards
function isPuzzle(obj: unknown): obj is Puzzle {
  return typeof obj === "object" && obj !== null && "id" in obj;
}
```

### Type Checking

```bash
# Check types (no emit)
npx tsc --noEmit

# Watch mode
npx tsc --noEmit --watch
```

---

## Linting

```bash
# ESLint
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix
```

---

## Styling

CSS with custom properties for theming:

```css
/* styles/variables.css */
:root {
  --board-color: #dcb35c;
  --stone-black: #1a1a1a;
  --stone-white: #f0f0f0;
}

[data-theme="dark"] {
  --board-color: #8b7355;
}
```

---

## Working with SGF

### Loading Test Puzzles

```typescript
// tests/fixtures/puzzles.ts
export function loadTestPuzzle(name: string): Puzzle {
  const sgf = readFileSync(`fixtures/${name}.sgf`, "utf-8");
  return parseSgf(sgf);
}
```

### Testing Puzzle Logic

```typescript
describe("puzzle validation", () => {
  it("validates correct first move", () => {
    const puzzle = loadTestPuzzle("simple-capture");
    const result = validateMove(puzzle, puzzle.root, "cc");
    expect(result.isCorrect).toBe(true);
  });
});
```

---

## Debugging

### Browser DevTools

1. Open DevTools (F12)
2. Sources tab shows mapped TypeScript
3. Add breakpoints in `.ts`/`.tsx` files

### VS Code Debugging

```json
// .vscode/launch.json
{
  "configurations": [
    {
      "name": "Debug Frontend",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173/yen-go/",
      "webRoot": "${workspaceFolder}/frontend/src"
    }
  ]
}
```

### React DevTools

Install [Preact DevTools](https://preactjs.com/guide/v10/debugging/) browser extension for component inspection.

---

## Common Issues

### Port in Use

```bash
# Find process using port
npx kill-port 5173

# Or use different port
npm run dev -- --port 3000
```

### Dependencies Out of Sync

```bash
# Clear and reinstall
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Errors

```bash
# Clear TypeScript cache
rm -rf node_modules/.cache
npx tsc --noEmit
```
