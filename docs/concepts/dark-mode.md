# Dark Mode Theming

**Last Updated**: 2026-02-11

> **See also**:
>
> - [Concepts: Design Tokens](./design-tokens.md) — CSS custom property architecture
> - [Architecture: Goban Integration](../architecture/frontend/goban-integration.md) — Theme callbacks
> - [Architecture: Board Rendering](../architecture/frontend/svg-board.md) — Canvas vs SVG decision
> - [Architecture: Frontend Overview](../architecture/frontend/overview.md) — System architecture

## Overview

YenGo supports dark mode via the `[data-theme="dark"]` attribute on `<html>`. The attribute is toggled by user preference (Settings page) and persisted in `localStorage`.

## Implementation Strategy

### CSS Custom Properties

All colors are defined as CSS custom properties in `frontend/src/styles/app.css`:

- **`:root`** block contains light mode values (default)
- **`[data-theme="dark"]`** block overrides with dark-appropriate values

This approach means:

- Zero JavaScript color logic at runtime
- All components automatically adapt via CSS cascade
- Dark mode is opt-in per token (unoverridden tokens keep light values)

### Goban Board Theme

The Go board uses the goban library's built-in theme system:

| Mode  | Board Theme | Background                     | Stone Themes                 |
| ----- | ----------- | ------------------------------ | ---------------------------- |
| Light | Kaya        | `#DCB35C` (wood grain texture) | Shell (white), Slate (black) |
| Dark  | Night Play  | `#444444` (solid dark grey)    | Shell (white), Slate (black) |

The board theme is set via `getSelectedThemes` callback in `goban-init.ts`:

```typescript
getSelectedThemes: () => ({
  white: "Shell",
  black: "Slate",
  board: isDarkMode ? "Night Play" : "Kaya",
  "removal-graphic": "square",
  "removal-scale": 1.0,
  "stone-shadows": "default",
});
```

### Live Theme Switching

The `watchSelectedThemes` callback uses a `MutationObserver` on the `<html>` element to detect `data-theme` attribute changes:

```typescript
watchSelectedThemes: (cb) => {
  const observer = new MutationObserver(() => {
    cb(getSelectedThemes());
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  return { remove: () => observer.disconnect() };
};
```

This enables real-time board theme switching without page reload or goban instance recreation. The goban library's `setTheme()` method handles re-rendering.

### Page Mode Colors in Dark Mode

All 24 page mode color variables (6 modes × 4 variants) have dark-mode overrides with:

- **Reduced saturation** on border colors (e.g., `#fbbf24` → `#d97706`)
- **Semi-transparent backgrounds** (e.g., `rgba(251, 191, 36, 0.1)`)
- **Elevated text brightness** for readability (e.g., `#92400e` → `#fbbf24`)
- **Very low-opacity lights** for subtle hover states

### Detection Pattern

```typescript
// Check current dark mode state
const isDarkMode = document.documentElement.dataset.theme === "dark";
```

## Rules

1. **Never use `prefers-color-scheme`** — YenGo uses explicit `data-theme` attribute, not OS preference
2. **Test both themes** — Every visual change must be verified in both light and dark mode
3. **No bright artifacts** — Dark mode should have zero `#ffffff` backgrounds or saturated colors
4. **Board blending** — Night Play board (`#444444`) should blend within 30% luminance of surrounding UI
