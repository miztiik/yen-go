# yen-go Development Guidelines

You are an 1P Go Player. You are also expert in software development best practices. Use these pesonas to critically analyze the development guidelines for the yen-go project  and suggest improvements where necessary.

Auto-generated from all feature plans. Last updated: 2026-01-21

## Active Technologies
- TypeScript 5.x (frontend), Python 3.11+ (pipeline)
- Preact, Vite, Vitest (frontend); smargo/KataGo, pytest (pipeline)
- Static JSON files (puzzles), localStorage (user progress)
- Python 3.11+ (pipeline), TypeScript 5.x (frontend) + smargo/KataGo for validation, Vite + Preact for UI, pytest for pipeline, localStorage for persistence (001-core-platform)
- Static JSON artifacts (`/puzzles/data`, `/puzzles/views`, `manifest.json`); browser localStorage for user progress/stats (001-core-platform)
- TypeScript 5.x (frontend), Python 3.11+ (pipeline) + Preact 10.x, Vite 5.x, Vitest, smargo/KataGo (validation) (001-core-platform)
- TypeScript 5.x (frontend), Python 3.11+ (pipeline) + Preact, Vite, Vitest (frontend); smargo/KataGo, pytest (pipeline) (001-core-platform)
- Python 3.11+ (pipeline), TypeScript strict (frontend) + smargo/KataGo (validation), Preact (UI), Vite (build), Click (CLI) (001-core-platform)
- Static JSON on GitHub Pages (puzzles), localStorage (user progress) (001-core-platform)
- Python 3.11+ + httpx (HTTP client), pytest (testing), existing smargo/KataGo validators (002-puzzle-manager-refactor)
- SGF files (source of truth) + JSON indexes (views), filesystem-based with batch sharding (002-puzzle-manager-refactor)
- Python 3.11+ (pipeline), TypeScript strict (frontend) + sgfmill (SGF parsing), smargo (validation), Preact (frontend) (002-puzzle-manager-refactor)
- Static JSON files → SGF-native storage (v3.0 migration) (002-puzzle-manager-refactor)
- Python 3.11+ with type hints everywhere + `sgfmill` (SGF parsing), `smargo`/`KataGo` (solution validation), `click` (CLI), `httpx` (URL fetching) (002-puzzle-manager-refactor)
- Static SGF files → `yengo-puzzle-collections/sgf/`, JSON indexes → `yengo-puzzle-collections/views/` (002-puzzle-manager-refactor)
- Python 3.11+ with type hints (strict mode) (002-puzzle-manager-refactor)
- Python 3.11+ + click>=8.1.0, pydantic>=2.5.0, sgfmill>=1.1.0, httpx>=0.26.0 (002-puzzle-manager-refactor)
- Static SGF files (enriched) + JSON indexes, filesystem-based staging (002-puzzle-manager-refactor)
- TypeScript 5.x (strict mode) + Preact (UI), Vite (build), existing rulesEngine.ts (004-frontend-sgf-refactor)
- Static SGF files (GitHub Pages CDN), localStorage (user progress) (004-frontend-sgf-refactor)
- TypeScript 5.x (strict mode) + Preact 10.x, Vite 5.x, Vitest (004-frontend-sgf-refactor)
- localStorage (progress), static SGF files (puzzles) (004-frontend-sgf-refactor)
- TypeScript 5.x (strict mode) + Preact, Vite, Vitest (004-frontend-sgf-refactor)
- Static files (CDN), localStorage (user progress) (004-frontend-sgf-refactor)
- localStorage (user progress), static files from CDN (puzzles) (004-frontend-sgf-refactor)
- JSONL for publish logs, JSON for indexes, SGF for puzzles (007-collections-integrity-rollback)
- TypeScript 5.x (strict mode) + Preact, Vite, existing SGF parser (\`lib/sgf/parser.ts\`) (008-solution-presentation)
- N/A (display features only, no new persistence) (008-solution-presentation)
- TypeScript 5.x (strict mode) + Preact (lightweight React), Vite (build) (012-frontend-refutation-tree)
- N/A (runtime - reads from static SGF files) (012-frontend-refutation-tree)
- Python 3.11 (pipeline), TypeScript 5.x (frontend) + Pipeline (sgfmill, smargo), Frontend (Preact, Vite) (010-level-system-refactor)
- Static JSON/SGF files (puzzles), localStorage (user progress) (010-level-system-refactor)
- Python 3.11+ + sgfmill (SGF parsing), json (built-in), base64 (board decoding) (011-101books-adapter)
- Static SGF files output to `yengo-puzzle-collections/sgf/` (011-101books-adapter)
- Python 3.11 (pipeline), TypeScript 5.x (frontend) + sgfmill (Python), Preact (frontend) (014-codebase-cleanup)
- N/A (cleanup only) (014-codebase-cleanup)
- TypeScript 5.3+ (strict mode required per constitution) + `@playwright/test` (visual testing), existing Preact/Vite stack (016-playwright-visual-testing)
- Baseline images stored in repository (Git LFS recommended for images) (016-playwright-visual-testing)
- Python 3.11+ + `requests`, `sgfmill`, existing adapter utilities (`SgfBuilder`, `generate_sgf_filename`, `FailedIngestionRegistry`) (031-goproblems-adapter)
- Static SGF files in `staging/ingest/goproblems/`, checkpoint state in `state/adapters/` (031-goproblems-adapter)
- Python 3.11+ (puzzle_manager) + Pydantic (config validation), Click (CLI) (034-source-quality-rating)
- JSON config files (`sources.json`, `source-quality.json`) (034-source-quality-rating)
- Python 3.12+ (fallback to 3.11 if unavailable) + pydantic>=2.5.0, httpx>=0.26.0, tenacity>=8.2.0 (035-puzzle-manager-refactor)
- File-based only (JSON state files, SGF puzzles, no database) (035-puzzle-manager-refactor)
- Python 3.11+ with type hints + pydantic (models), pathlib (file operations), json (JSONL) (036-atomic-rollback)
- JSONL for publish logs and audit trail, SGF for puzzles (036-atomic-rollback)
- Markdown (documentation), JSON (package.json) + Vite (existing) - provides `vite preview` command (037-local-build-workflow)
- N/A (documentation only) (037-local-build-workflow)
- Python 3.11+ + argparse (stdlib), pydantic, pathlib (038-staging-dir-consistency)
- Filesystem (.pm-runtime/staging/, yengo-puzzle-collections/) (038-staging-dir-consistency)
- Python 3.11+ (backend/puzzle_manager pipeline) + Standard library (`pathlib`), existing `backend.puzzle_manager` modules (040-posix-path-fix)
- Static JSON files in `yengo-puzzle-collections/views/` (040-posix-path-fix)
- Python 3.11+ + `secrets` (stdlib), `datetime` (stdlib) - no new dependencies (041-run-id-date-prefix)
- SGF files with YI property, JSONL publish logs (041-run-id-date-prefix)
- Python 3.11+ + Pydantic (models), standard logging (043-pipeline-observability)
- JSON files (.pm-runtime/state/runs/), log files (.pm-runtime/logs/) (043-pipeline-observability)
- Python 3.11+ + pytest (testing), pathlib (paths), dataclasses (RuntimePaths) (044-test-isolation)
- File system paths (staging, state, output directories) (044-test-isolation)
- Python 3.11 + pytest (testing), pathlib (paths) (046-fix-dry-run-test-isolation)
- Filesystem - `yengo-puzzle-collections/`, `.pm-runtime/staging/`, `.pm-runtime/state/` (046-fix-dry-run-test-isolation)
- Python 3.11 (backend), TypeScript strict mode (frontend) + Preact, Vite (frontend); pytest (backend tests) (047-quality-config-consistency)
- Static JSON config files, localStorage (unchanged) (047-quality-config-consistency)
- Python 3.12+ (puzzle_manager pipeline) + pathlib (stdlib), os (stdlib) - no new dependencies (048-runtime-artifacts-separation)
- File system - `.pm-runtime/` directory at project root (048-runtime-artifacts-separation)
- Python 3.11+ + httpx (HTTP client), tenacity (retry logic), existing core utilities (049-ogs-adapter)
- SGF files in `.pm-runtime/staging/` during ingest, final output to `yengo-puzzle-collections/` (049-ogs-adapter)
- N/A (frontend fix only) (050-make-frontend-work)
- Python 3.11+ + httpx, tenacity (for rate limiting/retry), sgfmill (SGF parsing) (051-adapter-consolidation)
- File-based SGF + JSON config (no database) (051-adapter-consolidation)
- Python 3.11+ (backend), TypeScript (frontend) + sgfmill, pytest, pydantic (backend); Preact, Vite (frontend) (053-sgf-enrich-refactor)
- Static SGF files, JSON indexes, pipeline state in `.pm-runtime/` (053-sgf-enrich-refactor)
- Python 3.11 (backend/puzzle_manager) + sgfmill for SGF parsing/serialization; backend.puzzle_manager core utilities (`sgf_parser`, `sgf_publisher`, `sgf_builder`) (053-sgf-enrich-refactor)
- SGF files on filesystem (`.pm-runtime/staging`, published collections) (053-sgf-enrich-refactor)
- JavaScript (ES5+), HTML5, CSS3 + BesoGo library (JS/CSS from GitHub repo; no npm/build required) (054-sgf-viewer-besogo)
- N/A (transient client-side only; no persistence) (054-sgf-viewer-besogo)
- Python 3.11+ + `httpx` (via `HttpClient`), `tenacity` (via `HttpClient` retry logic) (055-ogs-http-client)
- N/A (network operations only) (055-ogs-http-client)
- N/A (state managed via props and context) (056-solution-tree-visualization)
- Python 3.11 + pydantic, sgfmill (existing) (103-dry-code-consolidation)
- SGF files with custom YenGo properties, JSON indexes (103-dry-code-consolidation)
- Markdown (no code changes) + N/A (documentation-only) (104-docs-audit-consolidation)
- Markdown files in `docs/` directory (104-docs-audit-consolidation)
- Python 3.11+ + Standard library `logging`, `datetime`; Pydantic models (105-logging-state-fixes)
- JSON state files in `.pm-runtime/state/runs/` (105-logging-state-fixes)
- Python 3.11+ + pydantic (models), json (serialization), pathlib (file ops) (106-view-index-pagination)
- Static JSON files on filesystem (106-view-index-pagination)
- Python 3.11+ + pathlib (stdlib), pytest, existing `to_posix_path()` utility (107-rollback-paths-refactor)
- JSON files (inventory.json), JSONL files (audit.jsonl, publish-log), SGF files (107-rollback-paths-refactor)
- Python 3.11+ + Pydantic (models), existing `core/` utilities (108-puzzle-validation-centralize)
- JSON config files (`config/puzzle-validation.json`) (108-puzzle-validation-centralize)
- Python 3.11+ + sgfmill (SGF parsing), existing core modules (AdapterCheckpoint, PuzzleValidator) (111-local-adapter-enhancement)
- File system (`.pm-runtime/state/` for checkpoints) (111-local-adapter-enhancement)
- TypeScript 5.x (frontend), Vitest 1.1.0 + Vitest, @testing-library/preact 3.2.4, jsdom 23.0.1 (113-fix-frontend-test-hang)
- N/A (test infrastructure only) (113-fix-frontend-test-hang)
- TypeScript 5.x, Preact 10.x + Preact, Preact Hooks (existing) (123-solution-tree-rewrite)
- N/A (component receives data via props) (123-solution-tree-rewrite)
- TypeScript (strict) with Preact (frontend) + Preact, Vite, Vitest, Playwright (frontend) (123-solution-tree-rewrite)
- N/A (runtime); localStorage used elsewhere for progress (123-solution-tree-rewrite)
- Python 3.12+ (backend pipeline), TypeScript (frontend path regex only) + pydantic >=2.5, httpx >=0.26, tenacity >=8.2, filelock >=3.13 — no new dependencies required (126-sharding-taxonomy-evolution)
- Static SGF files on disk (`yengo-puzzle-collections/sgf/`), JSON view indexes, JSON config files (126-sharding-taxonomy-evolution)
- Python 3.11+ (backend), TypeScript strict (frontend) + `sgfmill`, `pydantic` (backend models), `preact` + `vite` (frontend) (128-tsumego-collections-v2)
- Static JSON config files (`config/collections.json`, `config/schemas/collections.schema.json`), SGF files with `YL[]` property (128-tsumego-collections-v2)
- TypeScript 5.3 (strict mode, ES2020 target) + Preact 10.19 + `goban@^8.3.147` (board renderer), `tailwindcss@^4.1.18` (v4 via @tailwindcss/vite), `@playwright/test@^1.48.0`, `vitest@^1.1.0` (132-board-ui-polish)
- N/A (localStorage for user progress, static JSON for puzzle data) (132-board-ui-polish)
- TypeScript 5.3+ (strict mode) + Preact ^10.19.3, goban ^8.3.147, Vite ^5.0.7, Tailwind CSS ^4.1.18 (132-board-ui-polish)
- N/A (frontend-only, no persistence changes — existing `localStorage` unaffected) (132-board-ui-polish)

## Project Structure

```text
frontend/           # Preact + TypeScript web app
├── src/
│   ├── components/ # UI components
│   ├── lib/        # Core logic
│   └── pages/      # Route pages
└── tests/

pipeline/           # Python puzzle import pipeline
├── src/
│   ├── importers/  # Source importers
│   ├── validators/ # Validation wrappers
│   ├── stages/     # Pipeline stages
│   └── models/     # Data models
├── tests/
└── config/

puzzles/            # Published puzzle data
├── data/           # JSON puzzle files
└── views/          # Index files

deprecated_generator/  # ARCHIVED (removal: v2.0.0)
```

## Commands

```bash
# Frontend
cd frontend
npm run dev          # Development server
npm run test         # Run tests
npm run lint         # Lint code

# Pipeline
cd pipeline
pytest               # Run tests
ruff check .         # Lint Python
python -m src.puzzle_cli import run --all    # Import puzzles
python -m src.puzzle_cli pipeline run        # Run pipeline
```

## Code Style

- TypeScript: strict mode, ESLint + Prettier
- Python: ruff, mypy type checking
- Follow existing conventions in codebase

## Recent Changes
- 132-board-ui-polish: Added TypeScript 5.3+ (strict mode) + Preact ^10.19.3, goban ^8.3.147, Vite ^5.0.7, Tailwind CSS ^4.1.18
- 132-board-ui-polish: Added TypeScript 5.3 (strict mode, ES2020 target) + Preact 10.19 + `goban@^8.3.147` (board renderer), `tailwindcss@^4.1.18` (v4 via @tailwindcss/vite), `@playwright/test@^1.48.0`, `vitest@^1.1.0`
- 128-tsumego-collections-v2: Added Python 3.11+ (backend), TypeScript strict (frontend) + `sgfmill`, `pydantic` (backend models), `preact` + `vite` (frontend)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
