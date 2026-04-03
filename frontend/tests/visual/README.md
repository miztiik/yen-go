# Visual Tests

This directory contains Playwright visual regression tests for UI components.

## Quick Start

```bash
# Run all visual tests
npm run test:visual

# Update baselines (after intentional changes)
npm run test:visual:update

# Interactive UI mode
npm run test:visual:ui
```

## Directory Structure

```
tests/visual/
├── fixtures/      # Component test fixtures (props/states)
├── specs/         # Visual test specifications (.visual.spec.ts)
├── baselines/     # Screenshot baselines (committed to git)
└── test-results/  # Test output and diff images (gitignored)
```

## Baseline Update Workflow (User Story 2)

When you intentionally change a component's appearance:

### Step 1: Make your changes
Edit the component code as needed.

### Step 2: Run tests to see failures
```bash
npm run test:visual
```
Tests will fail showing the differences. Review the diff images in `test-results/` to confirm changes are intentional.

### Step 3: Update baselines
```bash
# Update ALL baselines
npm run test:visual:update

# Update baselines for a specific component
npm run test:visual:update -- --grep "Board"

# Update baselines for specific test
npm run test:visual:update -- --grep "empty 9x9"
```

### Step 4: Verify and commit
```bash
# Verify tests pass with new baselines
npm run test:visual

# Commit the updated baselines
git add tests/visual/baselines/
git commit -m "chore: update visual baselines for [component]"
```

### Common Patterns

**Selective updates by component:**
```bash
npm run test:visual:update -- --grep "Board"
npm run test:visual:update -- --grep "Puzzle"
```

**Selective updates by viewport:**
```bash
npm run test:visual:update -- --project=desktop
npm run test:visual:update -- --project=mobile
```

**Review diff images before updating:**
After a failing test, check `test-results/` for:
- `*-actual.png` - What the component looks like now
- `*-expected.png` - What the baseline expects
- `*-diff.png` - Visual diff highlighting changes

## Writing Tests

1. Add fixtures to `frontend/src/visual-tests.tsx`
2. Create a spec in `specs/{component}.visual.spec.ts`
3. Run `npm run test:visual:update` to generate baselines
4. Commit the baseline images

## Viewport Testing

Tests run on 3 viewports:
- **Desktop**: 1280x800 (Chromium)
- **Tablet**: 768x1024 (WebKit)
- **Mobile**: 375x667 (WebKit)

## Troubleshooting

### Tests fail on different machines

Baselines may differ due to OS/font rendering. Solutions:
1. Generate baselines from CI (Linux) as source of truth
2. Run `npm run test:visual:update` locally
3. Baselines include platform suffix (e.g., `board-empty-9x9-desktop-win32.png`)

### Flaky tests

The test page disables CSS animations. If still flaky:
```typescript
await page.waitForTimeout(100);
```

### Missing browsers

Run `npx playwright install` to install required browsers.

See `specs/016-playwright-visual-testing/quickstart.md` for full documentation.
