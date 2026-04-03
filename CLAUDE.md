# Yen-Go

Offline Go (Baduk/Weiqi) tsumego puzzle platform. Static files on GitHub Pages, no runtime backend. Puzzles imported from established collections, processed through a Python pipeline, solved in the browser against pre-computed solution trees.

See `frontend/CLAUDE.md` and `backend/CLAUDE.md` for subsystem-specific guidance.

## Non-Negotiable Constraints ("Holy Laws")

1. **Zero Runtime Backend** -- No server-side logic. Static files on GitHub Pages only (SQLite DB is a static file loaded client-side via sql.js WASM).
2. **Deterministic Builds** -- Same input must produce identical output. Pinned sources, reproducible CI.
3. **Local-First Persistence** -- All user data in `localStorage`. No cloud sync, no accounts.
4. **No Browser AI** -- Browser validates moves against pre-computed solution trees. No neural nets, no MCTS, no move generation, no blocking computation >100ms. sql.js is a query engine, not AI.
5. **Type Safety** -- TypeScript `strict: true`. No `any` without justification. Python type hints everywhere.

## Project Structure

| Directory                   | Purpose                                                               |
| --------------------------- | --------------------------------------------------------------------- |
| `frontend/`                 | Preact + TypeScript + Vite web app                                    |
| `backend/puzzle_manager/`   | Python pipeline (v4.0, primary)                                       |
| `tools/`                    | Self-contained processing tools (must NOT import from backend/). Includes `tools/core/collection_embedder.py` for pre-pipeline YL embedding |
| `config/`                   | Shared JSON config (tags, levels, schemas, collections)               |
| `docs/`                     | User-facing documentation (architecture, how-to, concepts, reference) |
| `yengo-puzzle-collections/` | Published SGF files + JSON view indexes                               |
| `deprecated_generator/`     | ARCHIVED -- do not modify                                             |

## SGF Custom Properties (Schema v15)

| Property | Description                                                                                               | Example                                                                |
| -------- | --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `GN`     | Puzzle ID (set at publish)                                                                                | `GN[YENGO-765f38a5196edb79]`                                           |
| `YV`     | Schema version (integer)                                                                                  | `YV[15]`                                                               |
| `YG`     | Level slug                                                                                                | `YG[intermediate]`                                                     |
| `YT`     | Tags (comma-separated, sorted, deduplicated)                                                              | `YT[ko,ladder,life-and-death]`                                         |
| `YH`     | Hints (pipe-delimited, max 3, uses `{!xy}` coordinate tokens)                                             | `YH[Focus on the corner\|Ladder pattern\|The first move is at {!cg}.]` |
| `YQ`     | Quality metrics (hc: 0=none, 1=markers, 2=teaching; ac: 0=untouched, 1=enriched, 2=ai_solved, 3=verified) | `YQ[q:2;rc:0;hc:0;ac:1]`                                               |
| `YX`     | Complexity metrics (w/a optional)                                                                         | `YX[d:1;r:2;s:19;u:1;w:2;a:0]`                                         |
| `YK`     | Ko context                                                                                                | `YK[none]`, `YK[direct]`, or `YK[approach]`                            |
| `YO`     | Move order                                                                                                | `YO[strict]`, `YO[flexible]`, `YO[miai]`                               |
| `YL`     | Collection membership (v14: optional `:CHAPTER/POSITION` suffix)                                          | `YL[cho-chikun-life-death-elementary:3/12]`                             |
| `YC`     | Corner position                                                                                           | `YC[TL]`, `YC[BR]`, `YC[C]`, `YC[E]`                                   |
| `YR`     | Refutation moves (wrong first-move SGF coords)                                                            | `YR[cd,de,ef]`                                                         |
| `YM`     | Pipeline metadata JSON (trace_id, filename, run_id)                                                       | `YM[{"t":"a1b2c3d4e5f67890","i":"20260220-abc12345"}]`                 |

Rules: Root `C[]` PRESERVED by default (configurable via `preserve_root_comment`). Move `C[]` PRESERVED. `SO` REMOVED.

## Pipeline Architecture (3-Stage)

```text
Sources -> ingest (fetch/parse/validate) -> analyze (classify/tag/enrich) -> publish (index/daily/output)
```

Publish generates `GN[YENGO-{SHA256(content)[:16]}]` where GN == filename.

Collection embedding (`YL[]`) is done **pre-pipeline** via `tools/core/collection_embedder.py` (3 strategies: phrase match, manifest lookup, filename pattern). The pipeline's whitelist-rebuild at ingest is the enforcement point.

## Puzzle Data Flow

```text
Sources -> Import -> Validate -> Classify -> Tag -> Serialize
SGF: yengo-puzzle-collections/sgf/{NNNN}/
DB:  yengo-puzzle-collections/yengo-search.db (search index)
Daily: yengo-puzzle-collections/yengo-search.db (daily_schedule + daily_puzzles tables)
```

## SQLite Query Architecture

All puzzle indexes are served as a single **SQLite database** (`yengo-search.db`) loaded into the browser via sql.js WASM. The frontend resolves filters via SQL queries against this in-memory database.

### Database Files

| File | Scope | Purpose |
|------|-------|---------|
| `yengo-search.db` | Frontend (browser) | Search/metadata index, ~500 KB for 9K puzzles |
| `yengo-content.db` | Backend only | SGF content + canonical position hash for dedup |
| `db-version.json` | Both | Version pointer with puzzle count and timestamp |

### DB-1 Schema (Ships to Browser)

| Table | Purpose |
|-------|---------|
| `puzzles` | Core metadata: content_hash, batch, level_id, quality, content_type, complexity |
| `puzzle_tags` | Many-to-many: puzzle ↔ tags (all numeric IDs) |
| `puzzle_collections` | Many-to-many: puzzle ↔ collections (with sequence_number) |
| `collections` | Collection catalog: slug, name, category, puzzle_count |
| `collections_fts` | FTS5 full-text search on collection names/slugs |
| `daily_schedule` | Daily challenge dates: version, generated_at, technique, attrs |
| `daily_puzzles` | Many-to-many: date ↔ puzzles (with section, position) |

### Frontend Bootstrap Sequence

```text
1. Fetch yengo-search.db (~500 KB)
2. Initialize sql.js WASM
3. Load DB into memory
4. All queries via SQL (no shard fetching, no manifest resolution)
```

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

### Incremental Publish

Each pipeline run reads `yengo-content.db` for existing entries, merges with new entries, and rebuilds `yengo-search.db`. The `db-version.json` file is updated atomically with version, puzzle count, and timestamp. Rollback and reconcile operations also rebuild `yengo-search.db` from remaining `yengo-content.db` entries. Use `vacuum-db` CLI command for maintenance.

**Path Reconstruction**: `content_hash` + `batch` → `sgf/{batch}/{content_hash}.sgf`

**ID Extraction**: `sgf/0001/abc123.sgf` → `abc123`

See `docs/concepts/sqlite-index-architecture.md` for terminology and `docs/concepts/numeric-id-scheme.md` for ID ranges.

## Difficulty Levels (9-level system)

Authoritative source: `config/puzzle-levels.json`

Novice (30k-26k), Beginner (25k-21k), Elementary (20k-16k), Intermediate (15k-11k), Upper-Intermediate (10k-6k), Advanced (5k-1k), Low-Dan (1d-3d), High-Dan (4d-6d), Expert (7d-9d)

## Agent Architecture Maps (AGENTS.md)

Each major module has an `AGENTS.md` in its root — a dense, agent-facing architecture map (NOT user docs). Read it before working in that module. Update it **in the same commit** as any structural code change.

| Module | AGENTS.md location |
|--------|-------------------|
| Python pipeline | `backend/puzzle_manager/AGENTS.md` |
| Enrichment tool | `tools/puzzle-enrichment-lab/AGENTS.md` |
| Frontend app | `frontend/src/AGENTS.md` |

To regenerate from scratch after large changes: use `.github/prompts/regen-agents-map.prompt.md`.

Scoped auto-injection: `.github/instructions/*.instructions.md` files with `applyTo` patterns inject the "read AGENTS.md" rule automatically when working in each module directory.

## Development Principles

- **SOLID/DRY/KISS/YAGNI** -- Search existing codebase before writing new code. Use `core/` utilities. No premature abstraction.
- **Test-first** -- Red-Green-Refactor for critical paths. Tests are part of definition of done.
- **Documentation** -- Update `docs/` for any user-visible or architectural change. Part of definition of done. Use `docs/reference/documentation-structure.md` to determine where each document belongs before creating or moving files.
- **Buy, don't build** -- Buy, don’t build — Prefer mature, well-maintained public libraries over custom implementations. Check `pyproject.toml` / `package.json` before adding dependencies. Do not re-implement solved infrastructure problems.Examples:
  1. HTTP client → use `httpx`, not a custom wrapper around sockets.
  2. XML parsing → use `lxml`, not a handwritten parser.
  3. SGF handling → use `sgfmill`.
  4. Retries → use `tenacity`.
- Only build custom code when no stable, production-grade library exists.
- **Config-driven** -- Tags from `config/tags.json`, levels from `config/puzzle-levels.json`. Never hardcode.

## Quality Gates

- All tests pass
- TypeScript strict compilation succeeds
- No lint warnings (ESLint frontend, ruff backend)
- Lighthouse score > 90 (Performance, PWA)
- Constitution compliance verified

## What NOT to Do

- Server-side code or APIs
- AI/move computation in browser
- Modify `deprecated_generator/`
- Hardcode tag aliases or version numbers
- Store user data outside `localStorage`
- > 100 files per directory
- Skip logging
- Manual SGF string building (use `SgfBuilder`)
- Custom retry/HTTP logic (use `HttpClient`)
- Assume context without checking -- ask first

## Frontend Design Conventions

- **No emojis in production UI** -- All icons are SVG components from `frontend/src/components/shared/icons/`
- **No goban package modifications** -- Zero changes to `node_modules/goban/`. Customize via callbacks, config, CSS, events, adapter layer.
- **OGS alignment** -- Follow OGS patterns for board rendering; deviate only with documented justification.
- **OGS-native puzzle format** -- SGF converted to PuzzleObject via `sgfToPuzzle()`. Goban receives `initial_state` + `move_tree`. Metadata extracted via tree parser (`parseSgfToTree`). No regex stripping, no monkey-patches.
- **GobanContainer** -- Goban creates its own DOM element; GobanContainer mounts it (ported from OGS)
- **Dead code policy** -- Delete, don't deprecate. Git history preserves everything.
- **Action buttons are icon-only** with `aria-label` tooltips (except Review)
- **Solution tree gating** -- Hidden until wrong move or explicit review. No spoilers.

See `frontend/CLAUDE.md` for full design decisions and puzzle solver architecture.

## Git Safety Rules (MANDATORY for AI Agents)

Multiple agents may work concurrently. Untracked files (crawler output, runtime data) can be destroyed by careless git operations.

### FORBIDDEN Git Commands

```bash
# NEVER use these - they destroy untracked files
git stash              # Loses untracked files when popped/dropped
git reset --hard       # Destroys all uncommitted changes
git clean -fd          # Deletes untracked files permanently
git checkout .         # Reverts all tracked file changes
git restore .          # Same as checkout .
```

### Safe Commit Workflow

```bash
# 1. Check for untracked files outside your scope
git status --porcelain | grep "^??"
# If files exist in external-sources/, .pm-runtime/, etc. - DO NOT proceed with stash/reset

# 2. Stage ONLY your specific files (NEVER use `git add .` or `git add -A`)
git add src/components/MyFile.tsx src/utils/helper.ts

# 3. Verify staged files are ONLY yours
git diff --cached --name-only

# 4. Create feature branch from current HEAD
git checkout -b feature/my-change

# 5. Commit
git commit -m "feat: description"

# 6. Return to main and merge
git checkout main
git merge --no-ff feature/my-change
```

### If You Need to Switch Branches with Uncommitted Work

**ASK THE USER FIRST.** Do not attempt automatic stash/restore operations.

### Protected Directories

These contain runtime/crawled data that is NOT in git. Any destructive git operation will permanently delete them:

- `external-sources/*/sgf/` - Crawler output (takes hours to regenerate)
- `external-sources/*/logs/` - Crawl logs
- `.pm-runtime/` - Pipeline runtime state

 
 # #   A g e n t   S t a n d a r d   G u i d e l i n e s 
 
 P l e a s e   s e e   \ . c l a u d e / r u l e s / \   f o r   d e t a i l e d   a g e n t   d e b u g g i n g   a n d   m o d i f i c a t i o n   p r o t o c o l s   ( e . g . ,   d e b u g   w o r k f l o w s ,   c o r r e c t i o n   l e v e l s   t a x o n o m y ,   a n d   a r c h i t e c t u r a l   c o m p l i a n c e ) . 
 
 
