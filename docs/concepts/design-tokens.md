# CSS Design Tokens

**Last Updated**: 2026-02-12

> **See also**:
>
> - [Architecture: Frontend Overview](../architecture/frontend/overview.md) — System architecture
> - [Concepts: Dark Mode](./dark-mode.md) — Dark mode theming strategy

## Overview

YenGo uses CSS custom properties (design tokens) as the single source of truth for all visual styling. No colors, spacing, or typography values are hardcoded in components — everything flows through the token system defined in `frontend/src/styles/app.css`.

## Token Architecture

### Naming Convention

```
--color-{category}-{variant}
```

| Category                | Example                     | Purpose           |
| ----------------------- | --------------------------- | ----------------- |
| `bg`                    | `--color-bg-primary`        | Background colors |
| `text`                  | `--color-text-primary`      | Text colors       |
| `border`                | `--color-border`            | Border colors     |
| `accent`                | `--color-accent`            | Brand/page accent |
| `mode-{name}`           | `--color-mode-daily-border` | Page mode colors  |
| `success/warning/error` | `--color-success`           | Semantic status   |

### Page Mode Color System

Six pages, each with a distinctive accent color and 4 variants:

| Mode        | Color   | Border                            | Background                    | Text                            | Light                            |
| ----------- | ------- | --------------------------------- | ----------------------------- | ------------------------------- | -------------------------------- |
| Daily       | Amber   | `--color-mode-daily-border`       | `--color-mode-daily-bg`       | `--color-mode-daily-text`       | `--color-mode-daily-light`       |
| Rush        | Rose    | `--color-mode-rush-border`        | `--color-mode-rush-bg`        | `--color-mode-rush-text`        | `--color-mode-rush-light`        |
| Collections | Purple  | `--color-mode-collections-border` | `--color-mode-collections-bg` | `--color-mode-collections-text` | `--color-mode-collections-light` |
| Training    | Blue    | `--color-mode-training-border`    | `--color-mode-training-bg`    | `--color-mode-training-text`    | `--color-mode-training-light`    |
| Technique   | Emerald | `--color-mode-technique-border`   | `--color-mode-technique-bg`   | `--color-mode-technique-text`   | `--color-mode-technique-light`   |
| Random      | Indigo  | `--color-mode-random-border`      | `--color-mode-random-bg`      | `--color-mode-random-text`      | `--color-mode-random-light`      |

### `[data-mode]` CSS Cascade

Pages set their mode via `PageLayout`'s `mode` prop, which renders `data-mode` on the wrapper:

```tsx
<PageLayout mode="technique">
  {/* All children inherit --color-accent = technique's text color */}
</PageLayout>
```

CSS rules in `app.css`:

```css
[data-mode="technique"] {
  --color-accent: var(--color-mode-technique-text);
}
[data-mode="daily"] {
  --color-accent: var(--color-mode-daily-text);
}
/* ... etc for all 6 modes */
```

Components like `FilterBar`, `ProgressBar`, and `StatsBar` use `var(--color-accent)` and automatically inherit the correct page color.

### Dark Mode Overrides

All 24 mode color variables have dark-mode variants in the `[data-theme="dark"]` block with:

- **Reduced saturation** on border and text colors
- **Low-opacity backgrounds** (e.g., `rgba(251, 191, 36, 0.1)`) for subtle tinting
- **Lighter text values** for readability against dark backgrounds

### Variant Usage Guide

| Variant  | Use Case                                              | Example                              |
| -------- | ----------------------------------------------------- | ------------------------------------ |
| `border` | Accent borders, progress bar fills, active indicators | `border-[--color-mode-daily-border]` |
| `bg`     | Subtle background tints for cards/sections            | `bg-[--color-mode-daily-bg]`         |
| `text`   | Accent text, headings, active labels                  | `text-[--color-mode-daily-text]`     |
| `light`  | Very subtle backgrounds, hover states                 | `bg-[--color-mode-daily-light]`      |

## Rules

1. **Never hardcode colors** — Use `var(--color-*)` or Tailwind utilities referencing tokens
2. **No inline `style={{}}`** — Use Tailwind utility classes (exception: dynamic computed values like widths/transforms)
3. **Mode isolation** — Each page uses ONLY its own `--color-mode-{name}-*` variables
4. **Cascade over props** — Prefer CSS cascade (`data-mode`) over passing color props to every component

## Migration Results (Spec 132)

| Metric                        | Before | After                                  |
| ----------------------------- | ------ | -------------------------------------- |
| Inline `style={{}}`           | 224    | 0 (excluding dynamic width/borderLeft) |
| Cross-mode contamination bugs | 8      | 0                                      |
| Hardcoded color values        | 25     | 0                                      |

### Accuracy Color System

A shared 3-tier semantic color utility (`lib/accuracy-color.ts`) provides consistent accuracy-based coloring across all pages:

| Threshold | Color Token       | Class                    |
| --------- | ----------------- | ------------------------ |
| >= 70%    | `--color-success` | `text-[--color-success]` |
| >= 50%    | `--color-warning` | `text-[--color-warning]` |
| < 50%     | `--color-error`   | `text-[--color-error]`   |
