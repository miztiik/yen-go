# Yen-Go Development Guidelines

## Code Generation Principles

### Before Writing Code

1. **Search existing codebase first** → Check `docs/`, `backend/puzzle_manager/core/`, `pyproject.toml` for existing solutions
2. **Identify constraints** → File locations, existing abstractions, test boundaries
3. **Default to simple structural solution** → Prefer editing existing code over new files/classes

### Quality Thresholds

| Change Scope                                             | Auto-proceed if...                     | Ask user if...                         |
| -------------------------------------------------------- | -------------------------------------- | -------------------------------------- |
| **Trivial** (typo, formatting, docstring)                | Follows existing style                 | Style is inconsistent                  |
| **Local** (single function/class)                        | No new dependencies, <20 lines changed | Changes public API or adds abstraction |
| **Structural** (new file, class, module)                 | **Never auto-proceed**                 | Always propose with rationale          |
| **Architectural** (test strategy, DI pattern, new layer) | **Never auto-proceed**                 | Always propose with alternatives       |

### Architecture & Structural Changes

**MANDATORY CHECKLIST** (before creating new files, classes, or abstraction layers):

- [ ] **Existing mechanism check**: Does the codebase already solve this?
- [ ] **Minimal change principle**: Can I achieve this by editing <3 files?
- [ ] **Dependency analysis**: Does this introduce new libraries? (check `pyproject.toml` first)
- [ ] **Test impact**: Does this change test isolation or require new test infrastructure?
- [ ] **Run the failing case**: Execute the exact command that causes the problem
- [ ] **Trace data flow**: Where does data actually go? Use `git status` after running
- [ ] **Ripple effect analysis**: What are second-order impacts across the project? For removals: What regressions could this cause in other modules?

If ANY checkbox fails → **Propose alternatives with explicit tradeoffs**

**Anti-patterns (Stop and Ask):**

- Creating wrapper class around single function → Can I use the function directly?
- Modifying >5 files for single feature → Can I localize this change?
- "This will make future changes easier" → YAGNI violation - is this needed NOW?
- Adding dependency injection framework → Does stdlib/existing pattern suffice?
- New test fixture/helper when `tmp_path`/`mock` exist → Am I reinventing built-ins?

### Domain-Specific Rules

**For test code:**

- Unit tests → mock external dependencies
- Integration tests → use `pytest.tmp_path` for file isolation
- CLI tests → verify `--help` only, use dry-run flags for integration
- Batch sizes in tests → use `batch_size=2` (if it works for 2, it works for N)

**For architecture decisions:**

- Systems design → Review with Principal/Staff Engineer persona before proposing
- Go/Tsumego logic → Verify with 1P Professional Go Player persona
- SOLID/DRY/KISS/YAGNI compliance takes precedence over clever solutions
- Explicit > implicit (type hints, error messages, variable names)

### When Uncertain

**Ask user with this format:**
Proposed: [specific change]
Alternative: [simpler approach]
Tradeoff: [what we lose with alternative]
Recommendation: [pick one with reasoning]

## Feature Change Requirements (Non-Negotiable)

Every feature change, bug fix, or enhancement MUST include:

1. **Tests** - Unit tests for new code, updated tests for modified code. Red-Green-Refactor for critical paths.
2. **Documentation** - Update relevant docs in `docs/` (concepts, architecture, how-to, or reference). Update `config/` schemas if configuration changed.
3. **Schema evolution** - If config files are modified, bump version and add changelog entry.

Skipping tests or documentation is NEVER acceptable. These are not separate tasks to "do later" - they are part of the definition of done for every change.

## Git Safety Rules (MANDATORY)

Multiple agents may work concurrently in this repository. Untracked files (crawler output, runtime data) can be permanently destroyed by careless git operations.

### FORBIDDEN Git Commands

```bash
# NEVER use these - they destroy untracked files
❌ git stash              # Loses untracked files when popped/dropped
❌ git reset --hard       # Destroys all uncommitted changes
❌ git clean -fd          # Deletes untracked files permanently
❌ git checkout .         # Reverts all tracked file changes
❌ git restore .          # Same as checkout .
```

### Safe Commit Workflow (Selective Cherry-Pick)

```bash
# 1. BEFORE any git operation, check for untracked files
git status --porcelain | grep "^??"
# If files exist in external-sources/, .pm-runtime/, tools/*/output/ - STOP and ask user

# 2. Stage ONLY your specific files
# NEVER use `git add .` or `git add -A`
git add src/components/MyFile.tsx
git add src/utils/helper.ts

# 3. Verify staged files are ONLY yours
git diff --cached --name-only
# If unexpected files appear, unstage them: git reset HEAD <file>

# 4. Create feature branch from current commit
git checkout -b feature/my-change

# 5. Commit your staged changes
git commit -m "feat: description"

# 6. Return to main and merge with --no-ff
git checkout main
git merge --no-ff feature/my-change -m "Merge feature/my-change"

# 7. Optionally delete the feature branch
git branch -d feature/my-change
```

### Switching Branches with Uncommitted Work

**DO NOT attempt automatic stash/restore.** If you need to switch branches and have uncommitted changes:

1. **Ask the user** how to proceed
2. Or commit your changes first to a WIP branch
3. Never use `git stash` as it can lose untracked files

### Protected Directories (Runtime Data)

These directories contain data NOT tracked by git. Destructive git operations will permanently delete them with NO recovery:

| Directory                  | Contents        | Recovery Time    |
| -------------------------- | --------------- | ---------------- |
| `external-sources/*/sgf/`  | Crawled puzzles | Hours (re-crawl) |
| `external-sources/*/logs/` | Crawl history   | Lost forever     |
| `.pm-runtime/`             | Pipeline state  | Re-run pipeline  |
| `tools/*/output/`          | Tool outputs    | Re-run tool      |

### What NOT to Do with Git

❌ `git add .` or `git add -A` — stages everything, including files you didn't change  
❌ `git stash` when untracked files exist outside your scope  
❌ `git reset --hard` to "clean up" before switching branches  
❌ `git clean` to remove untracked files  
❌ Assume the working directory only contains your changes

## Architecture: Static-First, Zero Backend

**Offline Go (Baduk) tsumego puzzle app** — no runtime backend, puzzles are pre-generated static files, user progress in `localStorage`.

### The Holy Laws (Non-Negotiable)

1. **Zero Runtime Backend** — Static JSON/SGF on GitHub Pages only
2. **Local-First** — All user data in `localStorage` only

## Project Structure

| Directory                   | Purpose                                                               |
| --------------------------- | --------------------------------------------------------------------- |
| `frontend/`                 | Preact + TypeScript + Vite                                            |
| `backend/puzzle_manager/`   | Python pipeline (v4.0, primary)                                       |
| `docs/`                     | User-facing documentation (architecture, how-to, concepts, reference) |
| `yengo-puzzle-collections/` | Published SGF + JSON views                                            |
| `deprecated_generator/`     | ARCHIVED — do not modify                                              |

## Key Conventions

### Engineering Principles (SOLID, DRY, KISS, YAGNI)

**SOLID Principles:**

- **Single Responsibility** — Each module/function does ONE thing well
- **Open/Closed** — Open for extension, closed for modification (use config, not code changes)
- **Liskov Substitution** — Subtypes must be substitutable for base types
- **Interface Segregation** — Prefer small, focused interfaces over large ones
- **Dependency Inversion** — Depend on abstractions (import from `core`), not concretions

**DRY (Don't Repeat Yourself):**

- Before writing code, **search the codebase** for existing utilities
- If functionality exists in `core/`, use it — don't recreate
- Shared logic belongs in `core/` or `utils/`, not duplicated in adapters

**KISS (Keep It Simple, Stupid):**

- Prefer simple solutions over clever ones
- If it needs a comment to explain, simplify the code
- Avoid premature optimization

**YAGNI (You Aren't Gonna Need It):**

- Don't build features "just in case"
- Implement only what's needed NOW
- Delete unused code aggressively

### Core Utilities (Use These, Don't Reinvent)

| Utility             | Location                                    | Purpose                                         |
| ------------------- | ------------------------------------------- | ----------------------------------------------- |
| `SgfBuilder`        | `backend.puzzle_manager.core.sgf_builder`   | Build SGF from primitives (stones, level, tags) |
| `parse_sgf()`       | `backend.puzzle_manager.core.sgf_parser`    | Parse SGF string to SGFGame object              |
| `publish_sgf()`     | `backend.puzzle_manager.core.sgf_publisher` | Serialize SGFGame to string                     |
| `HttpClient`        | `backend.puzzle_manager.core.http`          | HTTP requests with retry, rate-limit, backoff   |
| `YENGO_SGF_VERSION` | `backend.puzzle_manager.core.schema`        | Current schema version (from config/schemas/)   |

### Agent Architecture Maps (AGENTS.md)

Each major module has an `AGENTS.md` in its root — a dense, agent-facing architecture map (NOT user docs). Read it before working in that module. Update it **in the same commit** as any structural code change.

| Module | AGENTS.md location |
|--------|-------------------|
| Python pipeline | `backend/puzzle_manager/AGENTS.md` |
| Enrichment tool | `tools/puzzle-enrichment-lab/AGENTS.md` |
| Frontend app | `frontend/src/AGENTS.md` |

To regenerate from scratch after large changes: use `.github/prompts/regen-agents-map.prompt.md`.

Scoped auto-injection: `.github/instructions/*.instructions.md` files with `applyTo` patterns inject the "read AGENTS.md" rule automatically when working in each module directory.

### Development Principles

- **Buy, don't build** — Use existing libraries: `sgfmill`, `tenacity`, `httpx`, `preact`, `vite` (check `pyproject.toml` before writing custom code)

### Pipeline (Python)

- Python 3.11+ with type hints
- Tags source of truth: `config/tags.json` (never hardcode)
- Skill levels from `config/puzzle-levels.json`: `novice`, `beginner`, `elementary`, `intermediate`, `upper-intermediate`, `advanced`, `low-dan`, `high-dan`, `expert`

**SGF Custom Properties (Schema v15):**

- `GN` = YENGO-{16-char-lowercase-hex} (e.g., `GN[YENGO-765f38a5196edb79]`)
- `YV` = Schema version integer (e.g., `YV[15]`)
- `YG` = Level slug (e.g., `YG[intermediate]`) — NOT codes like DDK30
- `YT` = Comma-separated tags, sorted, deduplicated (e.g., `YT[ko,ladder,life-and-death]`)
- `YQ` = Quality metrics; hc: 0=none, 1=correctness markers, 2=teaching text; ac: 0=untouched, 1=enriched, 2=ai_solved, 3=verified (e.g., `YQ[q:2;rc:0;hc:0;ac:1]`)
- `YX` = Complexity metrics; a: avg refutation depth, optional (e.g., `YX[d:1;r:2;s:19;u:1;a:0]`)
- `YL` = Collection membership, comma-separated; v14: supports optional `:CHAPTER/POSITION` suffix for chapter+position (e.g., `YL[cho-chikun-life-death-elementary:3/12]`)
- `YH` = Pipe-delimited hints, max 3 (e.g., `YH[Corner focus|Ladder pattern|cg]`)
- `YC` = Corner position: `TL`, `TR`, `BL`, `BR`, `C`, `E`
- `YK` = Ko context: `none`, `direct`, `approach`
- `YO` = Move order: `strict`, `flexible`, `miai`
- `YR` = Refutation moves (wrong first-move SGF coords, e.g., `YR[cd,de,ef]`)
- `YM` = Pipeline metadata JSON (e.g., `YM[{"t":"a1b2c3d4e5f67890","i":"20260220-abc12345"}]`)
  - `t`: trace_id (16-char hex), `f`: original filename (optional), `i`: run_id (was YI)
- Root `C[]` = **PRESERVED** by default (configurable via `preserve_root_comment`)
- Move `C[]` = **STANDARDIZED** (Correct/Wrong prefix, CJK stripped)
- `SO` = **REMOVED** (provenance tracked in pipeline state, not SGF)

**⚠️ Note**: `trace_id` is stored in SGF files via the `YM` property (v12+). `run_id` is also in `YM` (v13). Source adapter ID is tracked via the CLI `--source` flag and publish log, not embedded in YM. Use `trace_id` for debugging; use `puzzle_id` (GN property) for published puzzle identity.

### Puzzle Data Flow

```
Sources → Import → Validate → Classify → Tag → Serialize
SGF: yengo-puzzle-collections/sgf/{NNNN}/
DB:  yengo-puzzle-collections/yengo-search.db (search index)
Daily: yengo-puzzle-collections/yengo-search.db (daily_schedule + daily_puzzles tables)
```

### SQLite Query Architecture

All puzzle indexes are served as a single **SQLite database** (`yengo-search.db`) loaded into the browser via sql.js WASM. The frontend resolves filters via SQL queries against this in-memory database.

### Database Files

| File | Scope | Purpose |
|------|-------|---------|
| `yengo-search.db`  | Frontend (browser) | Search/metadata index, ~500 KB for 9K puzzles |
| `yengo-content.db`  | Backend only | SGF content + canonical position hash for dedup |
| `db-version.json` | Both | Version pointer with puzzle count and timestamp |

### yengo-search.db Schema (Ships to Browser)

| Table | Purpose |
|-------|---------|
| `puzzles` | Core metadata: content_hash, batch, level_id, quality, content_type, complexity |
| `puzzle_tags` | Many-to-many: puzzle ↔ tags (all numeric IDs) |
| `puzzle_collections` | Many-to-many: puzzle ↔ collections (with sequence_number) |
| `collections` | Collection catalog: slug, name, category, puzzle_count |
| `collections_fts` | FTS5 full-text search on collection names/slugs |
| `daily_schedule` | Daily challenge dates: version, generated_at, technique, attrs |
| `daily_puzzles` | Many-to-many: date ↔ puzzles (with section, position) |

### Compact Entry Fields

| Field | Type | Description |
|-------|------|-------------|
| `content_hash` | TEXT | 16-char hex (matches GN, filename) |
| `batch` | TEXT | Batch directory (e.g., "0001") |
| `level_id` | INTEGER | Numeric level ID (110-230) |
| `quality` | INTEGER | Quality level (0-5) |
| `content_type` | INTEGER | 1=curated, 2=practice, 3=training |
| `cx_depth` | INTEGER | Solution depth |
| `cx_refutations` | INTEGER | Total reading nodes |
| `cx_solution_len` | INTEGER | Solution length |
| `cx_unique_resp` | INTEGER | Unique first-move count |
| `ac` | INTEGER | Analysis completeness (0=untouched, 1=enriched, 2=ai_solved, 3=verified) |

### Frontend Bootstrap Sequence

```text
1. Fetch yengo-search.db (~500 KB)
2. Initialize sql.js WASM
3. Load DB into memory
4. All queries via SQL (no shard fetching, no manifest resolution)
```

### Incremental Publish

Each pipeline run reads `yengo-content.db`  for existing entries, merges with new entries, and rebuilds `yengo-search.db` . The `db-version.json` file is updated atomically with version, puzzle count, and timestamp. Rollback and reconcile operations also rebuild yengo-search.db from remaining yengo-content.db entries. Use `vacuum-db` CLI command for maintenance.

**Path Reconstruction**: `content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

**ID Extraction**: `sgf/0001/abc123.sgf` → `abc123`

See `docs/concepts/sqlite-index-architecture.md` for terminology and `docs/concepts/numeric-id-scheme.md` for ID ranges.

### Daily Challenge Format (v2.2)

Daily challenges are stored in the `daily_schedule` and `daily_puzzles` tables inside `yengo-search.db` (DB-1). No JSON files are written.

- **Tables**: `daily_schedule` (one row per date) + `daily_puzzles` (puzzle-per-date-section rows)
- **Sections**: `standard`, `timed`, `by_tag`
- **Technique of day**: stored in `daily_schedule.technique_of_day`
- **Rolling window**: configurable via `DailyConfig.rolling_window_days` (default 90); dates older than the window are pruned

## Commands

```bash
# Frontend
cd frontend && npm run dev    # Dev server :5173
cd frontend && npm test       # Vitest

# Backend pipeline (run from repo root — pytest.ini is at root)
pytest backend/ -m unit -q --no-header --tb=short   # Fast unit tests (~4s)
pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no  # Quick validation (~30s)
pytest backend/ -q --no-header --tb=no               # Full backend suite (~60s)
cd backend/puzzle_manager && ruff check .            # Linting
```

### Backend Test Commands (IMPORTANT FOR AI AGENTS)

**Default behavior:** `pytest` runs ALL ~1,250 tests (~3 minutes)

**Use markers to run faster subsets:**

| Command                                    | Tests  | Time | When to Use                |
| ------------------------------------------ | ------ | ---- | -------------------------- |
| `pytest backend/ -m unit -q --no-header --tb=short`              | ~365   | ~4s  | **Fastest isolated tests** |
| `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no`  | ~1,600 | ~30s | Local dev / quick check    |
| `pytest backend/ -m "not slow" -q --no-header --tb=no`            | ~2,000 | ~60s | Pre-commit                 |
| `pytest backend/ -m adapter -q --no-header --tb=no`               | ~160   | ~10s | Adapter work only          |
| `pytest backend/ -n auto`                                          | all    | ~30s | Parallel execution (CI)    |

**Test Directory Structure:**

```
tests/
├── unit/          # Fast isolated tests (auto-marked @pytest.mark.unit)
├── integration/   # Multi-component tests (CLI, pipeline, inventory)
├── adapters/      # Adapter-specific tests (@pytest.mark.adapter)
├── core/          # Core module tests
└── stages/        # Stage-specific tests
```

**Available markers:**

- `unit` - Fast isolated tests (~365 tests, ~20s) - auto-applied in tests/unit/
- `cli` - CLI subprocess tests (slowest, ~36 tests, ~40s)
- `slow` - Benchmarks and large data tests (~11 tests)
- `adapter` - Adapter-specific tests (~160 tests)
- `inventory` - Inventory management tests
- `pagination` - Pagination/views tests
- `posix` - POSIX path compatibility tests
- `e2e` - End-to-end pipeline tests
- `integration` - Multi-component tests

**AI Agent Guidelines:**

- **Always run from repository root** — root `pytest.ini` scopes collection; no need to `cd`
- After making changes: `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no`
- For unit-only work: `pytest backend/ -m unit -q --no-header --tb=short`
- For enrichment lab: `pytest tools/puzzle-enrichment-lab/tests/ --ignore=tests/test_golden5.py --ignore=tests/test_calibration.py --ignore=tests/test_ai_solve_calibration.py -m "not slow" -q --no-header --tb=short`
- For puzzle_intent: `pytest tools/puzzle_intent/tests/ -q --no-header --tb=short`
- Only run full `pytest backend/` before PR submission
- When working on adapters: `pytest backend/ -m adapter -q --no-header --tb=no`
- **Never run bare `pytest` without a path argument** — external-sources/ has 259K files (no tests)
- For parallel execution on CI: `pytest backend/ -n auto`

```bash
# CLI Commands (--source is REQUIRED)
# Full pipeline for a source
python -m backend.puzzle_manager run --source sanderland

# Run stages separately
python -m backend.puzzle_manager run --source sanderland --stage ingest   # Step 1: Fetch
python -m backend.puzzle_manager run --source sanderland --stage analyze  # Step 2: Enrich
python -m backend.puzzle_manager run --source sanderland --stage publish  # Step 3: Output

# Combine stages
python -m backend.puzzle_manager run --source sanderland --stage analyze --stage publish

# Other commands
python -m backend.puzzle_manager status                    # Show run status
python -m backend.puzzle_manager status --history          # Show run history
python -m backend.puzzle_manager sources                   # List configured sources
python -m backend.puzzle_manager daily --date 2026-01-28   # Generate daily challenge
python -m backend.puzzle_manager clean --target staging    # Clean staging dir
python -m backend.puzzle_manager validate                  # Validate config

# Publish log search commands
python -m backend.puzzle_manager publish-log search --puzzle-id abc123def456  # Find by puzzle
python -m backend.puzzle_manager publish-log search --run-id abc123def456     # All in run
python -m backend.puzzle_manager publish-log search --source sanderland       # By source
python -m backend.puzzle_manager publish-log search --date 2026-02-20        # By date
python -m backend.puzzle_manager publish-log list                            # Available dates
```

## What NOT to Do

❌ Server-side code or APIs  
❌ Go moves in browser  
❌ Modify `deprecated_generator/`  
❌ Hardcode tag aliases or version numbers  
❌ Store user data outside `localStorage`  
❌ >100 files per directory  
❌ Skip logging  
❌ Assume context — ask first  
❌ Manual SGF string building — use `SgfBuilder`  
❌ Custom retry/HTTP logic — use `HttpClient`

## Frontend Design Conventions

- **No emojis in production UI** — All icons are SVG components from `frontend/src/components/shared/icons/`
- **No goban package modifications** — Zero changes to `node_modules/goban/`. Customize via callbacks, config, CSS, events, adapter layer.
- **OGS alignment** — Follow OGS patterns for board rendering; deviate only with documented justification.
- **OGS-native puzzle format** — SGF converted to PuzzleObject via `sgfToPuzzle()`. Goban receives `initial_state` + `move_tree`. Metadata extracted via tree parser (`parseSgfToTree`). No regex stripping, no monkey-patches.
- **GobanContainer** — Goban creates its own DOM element; GobanContainer mounts it (ported from OGS)
- **Dead code policy** — Delete, don't deprecate. Git history preserves everything.
- **Action buttons are icon-only** with `aria-label` tooltips (except Review)
- **Solution tree gating** — Hidden until wrong move or explicit review. No spoilers.

## Pipeline Architecture (v4.0)

**3-Stage Pipeline:** ingest → analyze → publish

| Stage   | Sub-stages               | Description                                          |
| ------- | ------------------------ | ---------------------------------------------------- |
| ingest  | fetch → parse → validate | Download, parse SGF, verify structure                |
| analyze | classify → tag → enrich  | Assign difficulty, detect techniques, generate hints |
| publish | index → daily → output   | Build indexes, daily challenges, write output        |

### Adapter Development: GN Property Flow

**CRITICAL for adapter developers:** Adapters do NOT set the final `GN` property.

```
INGEST:  Adapter returns puzzle_id (any format)
         → File: staging/ingest/{puzzle_id}.sgf
         → GN: can be anything (will be overwritten)

ANALYZE: Enriches SGF with YG, YT, YQ, YX, YH
         → File: staging/analyzed/{puzzle_id}.sgf
         → GN: unchanged

PUBLISH: Generates content_hash = SHA256(content)[:16]
         → Updates GN to: GN[YENGO-{content_hash}]
         → File: {content_hash}.sgf
         → GUARANTEED: GN == filename
```

**Adapter checklist:**

- ✅ Generate unique puzzle_id (any format)
- ✅ Return valid SGF (FF, GM, SZ, stones, solution)
- ❌ Don't set GN to YENGO format (publish stage handles it)
- ❌ Don't worry about final filename

**Runtime directories:** `.pm-runtime/staging/`, `.pm-runtime/state/`, `.pm-runtime/logs/` (at project root)

State tracked in `.pm-runtime/state/current_run.json`. Override with `YENGO_RUNTIME_DIR` env var. Rules:

- Skip already-completed batches
- Write state after each batch
- Re-running processes only incomplete/failed items
- Support `--resume` flag for interrupted runs

> Note: Smargo/KataGo solver removed in v3.2 (Spec 013) - curated sources are pre-validated.

## Error Handling

**Pipeline:** Never swallow exceptions; fail fast on config errors; continue on puzzle errors (log + record); batch-level recovery.

**Frontend:** Graceful degradation; catch localStorage quota exceeded; console logging only.

## Go/Tsumego Glossary

| Term             | Meaning                                                  |
| ---------------- | -------------------------------------------------------- |
| **Tsumego**      | Life-and-death puzzle                                    |
| **SGF**          | Smart Game Format (`.sgf`), coordinates `aa`-`ss` (1-19) |
| **Liberty**      | Empty point adjacent to stone                            |
| **Ko**           | Can't immediately recapture                              |
| **Eye/Two eyes** | Living group requirements                                |
| **Tesuji**       | Tactical technique (snapback, ladder, net)               |

_See Pipeline section for SGF custom property details (Schema v14)_

### Three-Tier Documentation Pattern

> **Authoritative placement rules**: See [`docs/reference/documentation-structure.md`](../docs/reference/documentation-structure.md) for the complete guide: tier definitions, placement flowchart, naming conventions, depth limits, required document elements, and known violations.

| Tier             | Directory            | Purpose                   | Content Type                                               |
| ---------------- | -------------------- | ------------------------- | ---------------------------------------------------------- |
| **Architecture** | `docs/architecture/` | WHY and HOW it's designed | Design decisions, rationale, constraints, data flow        |
| **How-To**       | `docs/how-to/`       | HOW TO USE/CREATE         | Step-by-step guides, examples, commands                    |
| **Concepts**     | `docs/concepts/`     | Shared knowledge          | Cross-cutting topics (tags, levels, SGF properties, hints) |
| **Reference**    | `docs/reference/`    | PURE lookup               | Configuration options, quick reference cards               |

### Documentation Rules (Non-Negotiable)

1. **Read `docs/reference/documentation-structure.md` first** — Before creating, moving, or deleting any doc, consult the placement flowchart and rules in that file. It is the single source of truth for structure.

2. **3-Level Maximum Depth** — Never exceed `docs/tier/component/file.md`
   - ✅ `docs/how-to/backend/create-adapter.md`
   - ❌ `docs/how-to/backend/adapters/ogs/config.md`

3. **Single Source of Truth** — Each topic has ONE canonical location
   - Cross-cutting concepts (tags, levels, hints, SGF) → `docs/concepts/`
   - Never duplicate content across backend/frontend sections

4. **Mandatory Cross-References** — Every doc MUST have "See also" callout:

   ```markdown
   > **See also**:
   >
   > - [Architecture: X](../architecture/backend/x.md) — Why this works
   > - [How-To: Y](./y.md) — Step-by-step guide
   > - [Reference: Z](../reference/z.md) — Configuration options
   ```

5. **Content Placement Rules**:
   - Design decisions, rationale → `docs/architecture/`
   - Step-by-step tutorials, quickstarts → `docs/how-to/`
   - Property definitions, taxonomies → `docs/concepts/`
   - Configuration tables, CLI cheat sheets → `docs/reference/`
   - Research, alternatives, historical context → `docs/archive/` (historical reference)

6. **Metadata Required** — Every doc needs "Last Updated" date

7. **Trigger for docs update** — A documentation update is required whenever:
   - A new feature, API, or CLI command is added
   - An existing API, config option, or behavior changes
   - A file, module, or architecture component is renamed, moved, or removed
   - A concept, taxonomy item (tag, level), or schema property changes
   - Any architectural decision is made
   The update is part of the **same commit** as the code change. Docs-only PRs are a code smell.

### What NOT to Do with Documentation

❌ Create new directories under `docs/` without checking structure above  
❌ Put the same information in multiple places  
❌ Create adapter-specific docs outside `docs/reference/adapters/`  
❌ Put CLI commands anywhere except `docs/how-to/backend/cli-reference.md`  
❌ Duplicate concept docs in backend AND frontend sections  
❌ Exceed 3 directory levels  
❌ Skip cross-reference callouts

### Spec-to-Docs Flow

When specs contain content useful for public documentation:

| Spec Content Type      | Flows To             | Example                          |
| ---------------------- | -------------------- | -------------------------------- |
| Design decisions       | `docs/architecture/` | "Why publish-log based rollback" |
| Quickstarts, tutorials | `docs/how-to/`       | "How to rollback"                |
| Property definitions   | `docs/concepts/`     | "YH compact format"              |
| Config options         | `docs/reference/`    | "Adapter config"                 |
| Research, alternatives | `docs/archive/`      | Historical design record         |

All project knowledge lives in `docs/`. The `specs/` directory has been retired — see `docs/archive/` for historical design narratives.
