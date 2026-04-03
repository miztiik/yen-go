# Adding UI Components

> **See also**:
>
> - [Architecture: Frontend Structure](../../architecture/frontend/structure.md) — Directory layout
> - [Architecture: State Management](../../architecture/frontend/state-management.md) — State patterns
> - [How-To: Local Development](./local-development.md) — Testing setup

**Last Updated**: 2026-02-16

How to create and integrate UI components in the Yen-Go frontend.

---

## Component Architecture

### Directory Structure

```
frontend/src/components/
├── GobanBoard/
│   ├── GobanBoard.tsx      # Board wrapper
│   └── GobanRenderer.tsx   # goban library integration
├── Layout/
│   └── PageLayout.tsx      # Composition layout (mode prop)
├── shared/
│   ├── Button.tsx          # Shared button with variants
│   ├── ErrorState.tsx      # Friendly error display
│   ├── ProgressBar.tsx     # Progress bar with mode color
│   ├── FilterBar.tsx       # Filter pills + sort
│   ├── StatsBar.tsx        # Stats display
│   ├── GoQuote.tsx         # Quote/empty state
│   └── PuzzleCollectionCard.tsx
├── Solver/
│   └── SolverView.tsx      # Core puzzle solving
├── DailyChallenge/         # Daily challenge components
├── PuzzleRush/             # Rush mode components
├── Training/               # Training mode
└── TechniqueFocus/         # Technique browsing
```

### Naming Conventions

| Type                | Convention | Example             |
| ------------------- | ---------- | ------------------- |
| Component file      | PascalCase | `PuzzleCard.tsx`    |
| Component directory | PascalCase | `GobanBoard/`       |
| Utility file        | kebab-case | `accuracy-color.ts` |
| Types file          | kebab-case | `page-mode.ts`      |
| Export file         | index.ts   | `index.ts`          |

---

## Creating a Component

### Step 1: Create Component File

```typescript
// components/shared/ErrorState.tsx
import type { FunctionalComponent, ComponentChildren } from 'preact';

export interface ErrorStateProps {
  message: string;
  icon?: ComponentChildren;
  onRetry?: () => void;
  onGoBack?: () => void;
  details?: string;
  className?: string;
  testId?: string;
}

export const ErrorState: FunctionalComponent<ErrorStateProps> = ({
  message,
  icon = '⚠️',
  onRetry,
  onGoBack,
  details,
  className,
  testId = 'error-state',
}) => {
  return (
    <div
      className={`flex min-h-[200px] flex-col items-center justify-center gap-4 p-8 text-center ${className ?? ''}`}
      data-testid={testId}
      role="alert"
    >
      <div className="text-4xl" aria-hidden="true">{icon}</div>
      <p className="m-0 max-w-[400px] text-base text-[--color-text-primary]">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg bg-[--color-accent] px-4 py-2 text-sm font-medium text-[--color-bg-panel]"
        >
          Retry
        </button>
      )}
    </div>
  );
};
```

### Step 2: Style with Tailwind + CSS Custom Properties

**No separate CSS files needed.** Use Tailwind utility classes directly in JSX.

For colors, use CSS custom properties from `styles/app.css`:

```tsx
{
  /* ✅ Correct — use CSS custom properties */
}
<div className="bg-[--color-bg-panel] text-[--color-text-primary]">
  <span className="text-[--color-accent]">Accent text</span>
</div>;

{
  /* ✅ Page mode colors — adapt to current page context */
}
<div className="border-[--color-mode-daily-border] bg-[--color-mode-daily-light]">
  Daily-themed element
</div>;

{
  /* ❌ Never use hardcoded colors */
}
<div style={{ color: "white", background: "#1a1a2e" }}>Bad</div>;

{
  /* ❌ Never use inline styles for static values */
}
<div style={{ display: "flex", padding: "16px" }}>Bad</div>;
```

### Step 3: Create Types (Optional)

For complex prop types, create a separate types file:

```typescript
// types/page-mode.ts
export type PageMode =
  | "daily"
  | "training"
  | "technique"
  | "collections"
  | "rush"
  | "random";
```

### Step 4: Create Index Export

```typescript
// components/shared/index.ts
export { ErrorState } from "./ErrorState";
export type { ErrorStateProps } from "./ErrorState";
```

---

## Component Patterns

### Functional Components (Preferred)

```typescript
import type { FunctionalComponent } from 'preact';

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export const Input: FunctionalComponent<Props> = ({ value, onChange }) => {
  return (
    <input
      type="text"
      className="w-full rounded-lg border border-[--color-border] bg-[--color-bg-main] px-3 py-2 text-[--color-text-primary]"
      value={value}
      onInput={(e) => onChange((e.target as HTMLInputElement).value)}
    />
  );
};
```

### Hooks for State

```typescript
import type { FunctionalComponent } from 'preact';
import { useState, useCallback } from 'preact/hooks';

export const Counter: FunctionalComponent = () => {
  const [count, setCount] = useState(0);

  const increment = useCallback(() => {
    setCount(c => c + 1);
  }, []);

  return (
    <div className="flex items-center gap-2">
      <span className="text-[--color-text-primary]">{count}</span>
      <button
        type="button"
        onClick={increment}
        className="rounded bg-[--color-accent] px-3 py-1 text-[--color-bg-panel]"
      >+</button>
    </div>
  );
};
```

### Signals for Shared State

```typescript
import type { FunctionalComponent } from 'preact';
import { useSignal, useComputed } from '@preact/signals';

export const PuzzleStats: FunctionalComponent = () => {
  const solved = useSignal(0);
  const total = useSignal(100);

  const progress = useComputed(() =>
    Math.round((solved.value / total.value) * 100)
  );

  return (
    <div className="text-sm text-[--color-text-secondary]">
      Progress: {progress}%
    </div>
  );
};
```

### Children and Slots

```typescript
import type { FunctionalComponent, ComponentChildren } from 'preact';

interface CardProps {
  title: string;
  children: ComponentChildren;
  footer?: ComponentChildren;
}

export const Card: FunctionalComponent<CardProps> = ({
  title,
  children,
  footer
}) => {
  return (
    <div className="rounded-lg border border-[--color-border] bg-[--color-bg-panel] p-4">
      <h2 className="m-0 mb-2 text-lg font-semibold text-[--color-text-primary]">{title}</h2>
      <div className="text-[--color-text-secondary]">{children}</div>
      {footer && <div className="mt-4 border-t border-[--color-border] pt-4">{footer}</div>}
    </div>
  );
};
```

### PageLayout with Mode Colors

Use `PageLayout` for pages that need mode-specific accent colors:

```typescript
import { PageLayout } from '../components/Layout/PageLayout';

export const DailyPage: FunctionalComponent = () => {
  return (
    <PageLayout mode="daily">
      <PageLayout.Header>
        <h1 className="text-[--color-mode-daily-text]">Daily Challenge</h1>
      </PageLayout.Header>
      <PageLayout.Content>
        {/* Content inherits --color-accent from mode */}
        <button className="bg-[--color-accent] text-[--color-bg-panel]">
          Start
        </button>
      </PageLayout.Content>
    </PageLayout>
  );
};
```

Available modes: `daily`, `training`, `technique`, `collections`, `rush`, `random`

---

## Styling Guidelines

### Tailwind + CSS Custom Properties

All styling uses **Tailwind utility classes** with **CSS custom property tokens** for colors.

#### Color Token System

Colors are defined in `styles/app.css` and adapt to light/dark mode automatically:

```tsx
{/* Layout tokens */}
<div className="bg-[--color-bg-main] text-[--color-text-primary]">
  <p className="text-[--color-text-secondary]">Secondary text</p>
  <div className="border border-[--color-border] bg-[--color-bg-panel]">Panel</div>
</div>

{/* Semantic tokens */}
<span className="text-[--color-success]">Correct!</span>
<span className="text-[--color-error]">Wrong</span>
<button className="bg-[--color-accent] text-[--color-bg-panel]">Action</button>
```

#### Page Mode Colors

Each page mode has its own accent family (set by `PageLayout` mode prop):

| Mode        | Border token                      | Text token                      | Light token                      |
| ----------- | --------------------------------- | ------------------------------- | -------------------------------- |
| daily       | `--color-mode-daily-border`       | `--color-mode-daily-text`       | `--color-mode-daily-light`       |
| training    | `--color-mode-training-border`    | `--color-mode-training-text`    | `--color-mode-training-light`    |
| technique   | `--color-mode-technique-border`   | `--color-mode-technique-text`   | `--color-mode-technique-light`   |
| collections | `--color-mode-collections-border` | `--color-mode-collections-text` | `--color-mode-collections-light` |
| rush        | `--color-mode-rush-border`        | `--color-mode-rush-text`        | `--color-mode-rush-light`        |
| random      | `--color-mode-random-border`      | `--color-mode-random-text`      | `--color-mode-random-light`      |

```tsx
{
  /* Mode-aware styling */
}
<div className="border-2 border-[--color-mode-daily-border] bg-[--color-mode-daily-light]">
  <h2 className="text-[--color-mode-daily-text]">Daily Challenge</h2>
</div>;
```

#### Common Tailwind Patterns

```tsx
{
  /* Flexbox layout */
}
<div className="flex items-center gap-3">...</div>;

{
  /* Grid */
}
<div className="grid grid-cols-2 gap-4 sm:grid-cols-3">...</div>;

{
  /* Card pattern */
}
<div className="rounded-lg border border-[--color-border] bg-[--color-bg-panel] p-4 shadow-sm">
  ...
</div>;

{
  /* Responsive text */
}
<h1 className="text-lg font-bold sm:text-xl md:text-2xl">...</h1>;

{
  /* Truncation */
}
<p className="truncate">Long text here...</p>;
```

### When Inline Styles Are Acceptable

Only use `style={{}}` for **truly dynamic computed values**:

```tsx
{/* ✅ Dynamic values computed at runtime */}
<div style={{ transform: `translateX(${offset}px)` }}>Moving</div>
<canvas style={{ width: `${boardSize}px`, height: `${boardSize}px` }} />

{/* ❌ Static values — use Tailwind instead */}
<div style={{ display: 'flex', gap: '8px' }}>Bad</div>
```

### Responsive Design

```tsx
{
  /* Mobile-first with Tailwind breakpoints */
}
<div className="p-4 sm:p-6 md:p-8">
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
    ...
  </div>
</div>;
```

---

## Testing Components

### Unit Test

```typescript
// tests/unit/ErrorState.test.tsx
import { render, screen, fireEvent } from '@testing-library/preact';
import { describe, it, expect, vi } from 'vitest';
import { ErrorState } from '../../src/components/shared/ErrorState';

describe('ErrorState', () => {
  it('renders message with alert role', () => {
    render(<ErrorState message="Something went wrong" />);

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('shows retry button when onRetry provided', () => {
    const onRetry = vi.fn();
    render(<ErrorState message="Failed" onRetry={onRetry} />);

    fireEvent.click(screen.getByText('Retry'));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('shows technical details in disclosure', () => {
    render(
      <ErrorState
        message="Failed"
        details="NetworkError: timeout"
      />
    );

    expect(screen.getByText('NetworkError: timeout')).toBeInTheDocument();
  });
});
```

### Visual Test

```typescript
// tests/visual/error-state.visual.ts
import { test, expect } from "@playwright/test";

test("error state visual", async ({ page }) => {
  await page.goto("/test/components/error-state");

  await expect(page.getByTestId("error-state")).toHaveScreenshot(
    "error-state.png",
  );
});
```

---

## Integration Checklist

When adding a new component:

- [ ] Create component file with TypeScript types and `FunctionalComponent`
- [ ] Style using Tailwind utility classes + CSS custom property tokens
- [ ] Create index.ts with named exports
- [ ] Add unit tests (Vitest + @testing-library/preact)
- [ ] Add visual test if UI-heavy (Playwright)
- [ ] Document props with JSDoc or inline comments
- [ ] Use `className` (not `class`) for JSX attributes
- [ ] Wrap in `PageLayout` with correct `mode` if it's a page
- [ ] Verify responsive behavior (mobile-first breakpoints)
- [ ] Check accessibility (semantic HTML, `role`, `aria-*`, keyboard)

---

## Accessibility

### Semantic HTML

```typescript
// ✅ Good
<button type="button" onClick={handleClick}>Submit</button>
<nav aria-label="Main">...</nav>

// ❌ Avoid
<div onClick={handleClick}>Submit</div>
<div className="nav">...</div>
```

### ARIA Attributes

```typescript
<div
  role="alert"
  aria-live="polite"
  className="rounded-lg bg-[--color-bg-panel] p-4 text-[--color-text-primary]"
>
  {message}
</div>
```

### Keyboard Navigation

```typescript
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
>
  Action
</button>
```

### Focus Management

```typescript
import { useRef, useEffect } from 'preact/hooks';
import type { FunctionalComponent, ComponentChildren } from 'preact';

const Modal: FunctionalComponent<{ isOpen: boolean; children: ComponentChildren }> = ({ isOpen, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      modalRef.current?.focus();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div ref={modalRef} tabIndex={-1} role="dialog" aria-modal="true">
      {children}
    </div>
  );
};
```

---

> **See also**:
>
> - [Architecture: Frontend Overview](../../architecture/frontend/overview.md) — Directory structure and theme system
> - [Concepts: Design Tokens](../../concepts/design-tokens.md) — Full color token reference
> - [Architecture: Testing](../../architecture/frontend/testing.md) — Test strategy and visual testing
