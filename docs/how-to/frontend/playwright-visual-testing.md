# Playwright Visual Testing Guide

**Last Updated**: 2026-02-05

Visual testing captures screenshots of components and compares them against baselines to detect unintended UI changes.

## Quick Start

```bash
# Run all visual tests
cd frontend
npm run test:visual

# Update baselines
npm run test:visual:update

# Run specific test file
npx playwright test tests/visual/specs/board.visual.spec.ts
```

## Principles

1. **Test Rendered Appearance**: Screenshots verify actual rendering, not just DOM presence
2. **Component Isolation**: Each component has its own visual test file
3. **State Coverage**: Test default, hover, focus, disabled, loading, and error states
4. **Responsive Testing**: Verify at mobile (375px), tablet (768px), and desktop (1280px)

## Test File Structure

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

## Creating New Visual Tests

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

## Required States Per Component

| State | Purpose | Required |
|-------|---------|----------|
| Default | Initial render | ✅ Yes |
| Hover | Mouse interaction | If interactive |
| Focus | Keyboard focus indicator | ✅ For accessibility |
| Disabled | Disabled appearance | If applicable |
| Loading | Skeleton/spinner | If async |
| Error | Error state | If fail mode exists |
| With Content | Populated state | If data-driven |

## Best Practices

### Do

- Test one visual state per screenshot
- Use meaningful fixture IDs (`#board-with-stones`, not `#test-1`)
- Wait for animations to complete before capturing
- Include viewport size tests for responsive components

### Don't

- Test logic in visual tests (use unit tests)
- Capture unstable elements (animations, times, random IDs)
- Create overly large screenshots
- Skip the default state test

## Troubleshooting

### Flaky Tests

```typescript
// Add wait for stability
await page.waitForLoadState('networkidle');
await page.waitForTimeout(200); // Wait for render
```

### Animation Interference

```typescript
// Disable animations in test
await page.addStyleTag({
  content: '*, *::before, *::after { animation: none !important; transition: none !important; }'
});
```

### Dynamic Content

```typescript
// Hide dynamic elements
await page.locator('.timestamp').evaluate(el => el.style.visibility = 'hidden');
```

## See Also

- [Architecture: Frontend Testing](../../architecture/frontend/testing.md) - Testing architecture and conventions
- [Component Template](../../../frontend/tests/visual/templates/component.visual.template.ts) - Copy for new tests
- [Playwright Docs](https://playwright.dev/docs/test-snapshots) - Official snapshot testing docs
