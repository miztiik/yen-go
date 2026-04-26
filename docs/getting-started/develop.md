# Development Setup

> **See also**:
>
> - [How-To: Create Adapter](../how-to/backend/create-adapter.md) — Add new puzzle sources
> - [Architecture: Overview](../architecture/README.md) — System design
> - [Reference: CLI Quick Reference](../reference/cli-quick-ref.md) — Command cheat sheet

**Last Updated**: 2026-02-22

Get Yen-Go running locally for development.

---

## Prerequisites

- Node.js 18+
- Python 3.11+ (for puzzle manager)
- Git

## Quick Start

```bash
# Clone
git clone https://github.com/[org]/yen-go.git
cd yen-go

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173/yen-go/

# Tests
npm test              # Unit tests (Vitest)
npm run test:visual   # Visual tests (Playwright)
```

## Project Structure

```
yen-go/
├── frontend/                    # Preact + TypeScript + Vite
├── backend/puzzle_manager/      # Python pipeline (v4.0)
├── config/                      # Shared configuration
├── docs/                        # Documentation (you are here)
└── yengo-puzzle-collections/    # Published puzzles
```

## Development Workflow

### Frontend

```bash
cd frontend
npm run dev       # Start dev server
npm test          # Run Vitest tests
npm run build     # Production build
```

## Production Build & Preview

Yen-Go is a **static-first app** deployed to GitHub Pages. You can preview exactly what will be deployed:

### Build Commands

| Command                 | Purpose                              | URL                           |
| ----------------------- | ------------------------------------ | ----------------------------- |
| `npm run dev`           | Development server (hot reload)      | http://localhost:5173/yen-go/ |
| `npm run build`         | Generate production files in `dist/` | N/A                           |
| `npm run preview`       | Preview production build locally     | http://localhost:4173/yen-go/ |
| `npm run build:preview` | Build + preview in one command       | http://localhost:4173/yen-go/ |

### Step-by-Step

```bash
cd frontend
npm run build          # Generate production artifacts
npm run preview        # Start preview server
# → Open http://localhost:4173/yen-go/
```

Or use the combined command:

```bash
npm run build:preview  # Build and preview in one step
```

### Understanding the Build → Deploy Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   npm run dev   │     │  npm run build  │     │  GitHub Pages   │
│  localhost:5173 │     │    dist/        │────▶│  /yen-go/       │
│   (development) │     │  (artifacts)    │     │  (production)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │ npm run preview │
                        │ localhost:4173  │
                        │ /yen-go/        │
                        │ (simulates      │
                        │  GitHub Pages)  │
                        └─────────────────┘
```

**Key insight**: `npm run preview` serves the same files that GitHub Pages will serve, with the same base path (`/yen-go/`). This is the correct way to test production builds locally.

### ⚠️ Why Opening dist/index.html Directly Doesn't Work

You **cannot** double-click `dist/index.html` to test the app. Here's why:

| Issue                 | Why It Fails                                                                                                  |
| --------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Absolute Paths**    | Built assets use `/yen-go/assets/...` which browsers interpret as `file:///yen-go/assets/...` (doesn't exist) |
| **CORS Restrictions** | Browsers block fetch requests from `file://` origins                                                          |
| **Service Workers**   | PWA service workers require HTTP/HTTPS protocol                                                               |
| **PWA Manifest**      | Cannot load manifest from `file://` context                                                                   |

**But it DOES work on GitHub Pages!** The difference:

- `file://` → Browser reads from filesystem, can't resolve `/yen-go/` path
- `http://` (preview) → Server resolves paths correctly at `/yen-go/`
- `https://` (GitHub Pages) → Same as preview, served over HTTPS

**Bottom line**: Always use `npm run preview` to test production builds locally.

### Puzzle Manager

```bash
cd backend/puzzle_manager
pip install -e .           # Install in dev mode
pytest                     # Run tests
ruff check .               # Lint code

# Pipeline commands
python -m backend.puzzle_manager sources              # List sources
python -m backend.puzzle_manager run --source yengo-source     # Run import
python -m backend.puzzle_manager status               # Check status
```

See [CLI Reference](../how-to/backend/cli-reference.md) for all commands.

## Key Files

| File                                               | Purpose                      |
| -------------------------------------------------- | ---------------------------- |
| `config/puzzle-levels.json`                        | Difficulty level definitions |
| `config/tags.json`                                 | Technique tag taxonomy       |
| `frontend/src/app.tsx`                             | App entry point              |
| `backend/puzzle_manager/src/puzzle_manager/cli.py` | CLI entry point              |

## Testing

| Component       | Framework  | Command                               |
| --------------- | ---------- | ------------------------------------- |
| Frontend unit   | Vitest     | `cd frontend && npm test`             |
| Frontend visual | Playwright | `cd frontend && npm run test:visual`  |
| Backend         | Pytest     | `cd backend/puzzle_manager && pytest` |

## Code Style

- **TypeScript**: Strict mode, no `any` types
- **Python**: Type hints, ruff linter
- **Commits**: Conventional commits (`feat:`, `fix:`, `docs:`)

## Next Steps

- [Architecture Overview](../architecture/README.md) — Understand the system design
- [Create Adapter](../how-to/backend/create-adapter.md) — Contribute puzzle sources
- [Run Pipeline](../how-to/backend/run-pipeline.md) — Import puzzles

---

_For players: see [How to Play](play.md)_  
_For operators: see [Operations Guide](operate.md)_
