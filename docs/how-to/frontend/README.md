# Frontend How-To Guides

> **See also**:
>
> - [Architecture: Frontend](../../architecture/frontend/) — Design decisions
> - [Reference: Frontend](../../reference/frontend/) — Configuration lookup
> - [Getting Started](../../getting-started/) — Initial setup

**Last Updated**: 2026-02-01

Step-by-step guides for frontend development.

---

## Guides

| Guide                                                       | Purpose                         |
| ----------------------------------------------------------- | ------------------------------- |
| [Local Development](./local-development.md)                 | Dev server, testing, debugging  |
| [Build and Deploy](./build-deploy.md)                       | Production builds, GitHub Pages |
| [Adding Components](./add-components.md)                    | Creating UI components          |
| [Playwright Visual Testing](./playwright-visual-testing.md) | Visual regression test setup    |

---

## Quick Commands

```bash
cd frontend

# Development
npm run dev                 # Start dev server
npm test                    # Run unit tests (watch)
npm run test:visual         # Run visual tests

# Production
npm run build               # Build for production
npm run preview             # Preview production build

# Quality
npm run lint                # ESLint
npx tsc --noEmit           # Type check
```

---

## Common Tasks

### Add a New Page

1. Create page component in `src/pages/`
2. Add route in `src/app.tsx`
3. Add link in navigation

### Add a New Service

1. Create service in `src/services/`
2. Define types in `src/models/`
3. Add unit tests

### Update Shared Config

Config in `config/` is shared with backend:

```typescript
// Import shared config
import levels from "../../../config/puzzle-levels.json";
```
