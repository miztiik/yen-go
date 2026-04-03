# Plan: Collections Launch Polish (v2 — OPT-2: Multi-Strategy Embedder)

_Last Updated: 2026-03-29_

## Selected Option

OPT-2: Multi-Strategy Embedder — strategy registry with (A) phrase match, (B) manifest lookup, (C) filename pattern. Generic core in `tools/core/`, thin CLI wrappers per source.

## Architecture Overview

### Core Module: `tools/core/collection_matcher.py`

Consolidates 4 duplicated phrase-matching implementations:
- `backend/puzzle_manager/core/collection_assigner.py` (algorithm reference — NOT imported)
- `tools/ogs/collections.py` (stop-word removal, CJK regex, longest-match-wins)
- `tools/go_problems/collections.py` (clone of OGS)
- `tools/tsumego_hero/collections_matcher.py` (local override priority)

New shared module provides:
```python
class CollectionMatcher:
    def __init__(self, collections_config: Path, local_overrides: dict | None = None):
        """Load collections.json, build alias map."""
    
    def match(self, text: str) -> MatchResult | None:
        """Normalize + tokenize + contiguous subsequence match.
        Returns slug, confidence, matched_alias."""
    
    def match_all(self, text: str) -> list[MatchResult]:
        """Return all matches, sorted by confidence (longest-match-wins)."""
```

Features extracted from existing implementations:
- NFKC normalization + lowercasing (from U-1)
- Stop-word removal: `go`, `baduk`, `weiqi`, `problem` (from U-3)
- CJK-aware regex splitting (from U-3)
- Longest-match-wins tie-breaking (from U-3)
- Local override priority (from U-5)

**Architecture boundary**: This module does NOT import from `backend/`. It re-implements the algorithm from `tools/core/` scope. The backend's `collection_assigner.py` remains canonical for pipeline use.

### Core Module: `tools/core/collection_embedder.py`

Strategy interface + registry:

```python
class EmbedStrategy(Protocol):
    def resolve(self, sgf_path: Path, dir_name: str) -> EmbedResult | None:
        """Given an SGF file and its parent directory name, return YL value."""

class EmbedResult:
    slug: str
    chapter: int  # 0 = no chapter concept
    position: int  # 1-based position within chapter

# Strategy registry
STRATEGIES: dict[str, type[EmbedStrategy]] = {
    "phrase_match": PhraseMatchStrategy,    # Strategy A
    "manifest_lookup": ManifestStrategy,    # Strategy B
    "filename_pattern": FilenameStrategy,   # Strategy C
}
```

Core embedding function:
```python
def embed_collections(
    source_dir: Path,
    strategy: EmbedStrategy,
    matcher: CollectionMatcher,
    logger: StructuredLogger,
    *,
    dry_run: bool = False,
    checkpoint: ToolCheckpoint | None = None,
) -> EmbedSummary:
    """Walk source_dir, match directories, embed YL[] into SGF files."""
```

**Minimal-edit SGF approach**: The embedder parses SGF via `tools.core.sgf_parser`, adds/updates only the `YL[]` property in the root node, and writes back via `tools.core.sgf_builder.publish_sgf()`. All other properties are preserved. This is documented as an explicit exception to the whitelist-rebuild standard — the embedder is a pre-ingest annotation tool; the pipeline's own whitelist rebuild at ingest is the enforcement point.

### Strategy Details

**Strategy A: Phrase Match** (kisvadim, eidogo, tasuki, 101weiqi)
1. Walk directory tree under `external-sources/{source}/`
2. For each non-batch subdirectory, match directory name against `CollectionMatcher`
3. Position = enumation order within directory (sorted by filename)
4. Chapter 0 (no chapter concept)
5. Embed `YL[slug:0/position]`

**Strategy B: Manifest Lookup** (OGS)
1. Read `external-sources/ogs/20260211-203516-collections-sorted.jsonl`
2. Build reverse index: `{puzzle_numeric_id} → (collection_name, position_in_puzzles_array)`
3. Match collection name to slug via `CollectionMatcher`
4. Walk SGF files in `sgf-by-collection/` directories
5. Position from manifest `puzzles` array index
6. Chapter 0 (OGS has no chapter concept)
7. Embed `YL[slug:0/position]`
8. **Coverage validation**: ≥80% of OGS directories must resolve to a known slug

**Strategy C: Filename Pattern** (gotools, syougo)
1. Parse filename regex: `gotools_lv{level}_{chapter}_p{id}.sgf`
2. Map level → collection slug via `CollectionMatcher` (e.g., "gotools elementary" → slug)
3. Chapter = extracted chapter number
4. Position = extracted puzzle ID
5. Embed `YL[slug:chapter/position]`

### Chapter 0 Convention

When a source has no chapter concept (most sources), the embedder uses chapter `0` as a synthetic default:
- `YL[cho-chikun-life-death-elementary:0/42]` = puzzle 42, no chapter structure
- `YL[gotools-elementary:3/7]` = chapter 3, puzzle 7 (gotools has real chapters)

This is a documented architectural decision. Chapter 0 means "single flat sequence within this collection."

### CLI Design

Per-source thin wrappers follow tool development standards:

```bash
# OGS wrapper
python -m tools.ogs embed-collections \
  --output-dir external-sources/ogs/sgf-by-collection \
  --dry-run --verbose

# Also usable from project root
python -m tools.core.collection_embedder \
  --source ogs \
  --strategy manifest_lookup \
  --source-dir external-sources/ogs/sgf-by-collection
```

Required CLI flags (per tool dev standards): `--dry-run`, `--resume`, `--verbose`, `--no-log-file`, `--output-dir`

### JSONL Logging Schema

Events follow `StructuredLogger` pattern from `tools/core/logging.py`:

| Event Type | Fields | When |
|-----------|--------|------|
| `collection_embed` | `puzzle_id`, `slug`, `chapter`, `position`, `strategy` | YL embedded successfully |
| `folder_match` | `folder_name`, `matched_slug`, `confidence` | Directory matched to collection |
| `folder_skip` | `folder_name`, `reason` | Directory skipped (no match, already embedded, etc.) |
| `folder_error` | `folder_name`, `error` | Processing error |
| `embed_summary` | `total`, `embedded`, `skipped`, `errors`, `coverage_pct` | End of run |

Log files to `external-sources/{source}/logs/{timestamp}-embed-collections.jsonl`

### Checkpointing & Resume

- Checkpoint after each completed directory (not per-file — directories are the natural batch unit)
- Resume reads checkpoint and skips already-processed directories
- Uses `tools/core/checkpoint.py` (`ToolCheckpoint` class)

### Idempotency

- Parse existing `YL[]` before writing
- If `YL` already exists with same slug: skip (log `already_embedded`)
- If `YL` exists with different slug: warn and skip (don't overwrite) — log `conflict`
- If no `YL`: embed

### Write Safety

- **Atomic writes**: Uses `atomic_write_text()` from `tools/core/atomic_write.py` (temp file + rename pattern). No partial files on crash.
- **Backup**: Before overwriting any SGF, creates `{filename}.yl-backup` in same directory. Original file recoverable.
- **Rollback**: `--restore-backups` CLI flag scans for `.yl-backup` files and restores originals. Full undo capability.
- **Validation gate**: T10 dry-run validation must pass before any actual writes (enforced by task dependency).

---

## Frontend Changes

### F1: Merge 4 Sections → 3

Current `SECTIONS` array in `CollectionsBrowsePage.tsx`:
```
Learning Paths (graded) | By Technique (technique) | By Author (author) | Reference (reference)
```

New:
```
Learning Paths (graded) | Practice (technique + reference) | Books (author)
```

Implementation: Modify `SECTIONS` constant. The `Practice` section filters `type === 'technique' || type === 'reference'`.

### F2: Learning Paths Sort by Difficulty

Current: alphabetical (default array order from `catalog.byType['graded']`).

New: Sort by `config/puzzle-levels.json` difficulty order. Each graded collection has a `level_hint` in `collections.json`. Map `level_hint` → numeric `level_id` from `config/puzzle-levels.json`, sort ascending.

### F3: Books Sort by Tier → Quality → Puzzle Count

Current: default order.

New sort chain:
1. Tier rank: `editorial` > `premier` > `curated` > `community`
2. Quality (if available in collection metadata)
3. Puzzle count descending
4. Name alphabetical (tiebreaker)

### F4: Hide <15 Puzzle Collections from Browse

Add filter in `CollectionTypeSection` component:
```typescript
const filtered = collections.filter(c => c.puzzleCount >= 15 || !c.hasData);
```

Global search (`searchCollectionCatalog`) remains unfiltered — shows everything.

### F5: Selective Randomization

Toggleable backend config constant:
```typescript
// constants/collectionConfig.ts
export const SHUFFLE_POLICY: Record<CollectionType, boolean> = {
  graded: false,    // Learning Paths: preserve difficulty ordering
  author: false,    // Books: preserve author's sequence
  technique: true,  // Practice: randomize per session
  reference: true,  // Practice: randomize per session
  system: false,
};
```

Implementation in `CollectionPuzzleLoader.loadSet()`:
- After loading puzzles via `ORDER BY sequence_number`, check `SHUFFLE_POLICY[collectionType]`
- If true: Fisher-Yates shuffle on the loaded `puzzles` array (client-side)
- If false: keep sequence order

### F6: DB-Scoped In-Section Search

Each browse section gets a small search input. The query uses `collections_fts` FTS5:

```sql
SELECT c.collection_id, c.name, c.slug, c.category, c.puzzle_count, c.attrs
FROM collections_fts
JOIN collections c ON collections_fts.rowid = c.collection_id
WHERE collections_fts MATCH ?
AND json_extract(c.attrs, '$.type') IN (?, ?)  -- section type filter
```

For the "Practice" section (merged technique + reference), the IN clause includes both types.

Interaction with global search: Global search bar collapses sections into flat results (current behavior preserved). In-section search filters within that section only.

### F7: "Show More" Button → Top of Section

Move from below the card grid to the section header row, inline with section title and in-section search box:

```
[Section Title] (count)  [🔍 search box]  [Show all N →]
  subtitle text
  [card grid...]
```

### F8: Hover Color Treatment — All Browse Pages

Current: `hover:-translate-y-1 hover:shadow-xl` (bounce + shadow). User wants color treatment.

Apply to ALL browse pages: `CollectionsBrowsePage`, `TechniqueBrowsePage` (if exists), `TrainingBrowsePage` (if exists).

UX expert consultation needed for specific color choices. Proposal: on hover, apply accent border color to left edge and subtle background tint using CSS custom properties:
```css
hover:border-l-[var(--color-accent)] hover:bg-[var(--color-accent-bg)]
```

Works in both light/dark themes via CSS custom properties.

### F9: Improve Weak Descriptions

Identify collections with vague descriptions (e.g., "taruc-practice"). Update descriptions in `config/collections.json`. This is a data change, not a code change.

### F10: Puzzle Offset/Jump Navigation Verification

Route supports `offset` → `CollectionViewPage` receives `startIndex` → `CollectionPuzzleLoader` starts at that index. Need to verify during implementation:
- Does applying level/tag filters reset the puzzle index?
- Can users jump to arbitrary positions within filtered results?
- Does navigation consistently continue from the jumped-to position?

---

## Documentation Plan

| doc_id | File | Action | Content |
|--------|------|--------|---------|
| D1 | `docs/concepts/collections.md` | Update | Add chapter 0 convention, embedder utility, multi-strategy approach |
| D2 | `tools/core/AGENTS.md` | Update | Add `collection_matcher.py` and `collection_embedder.py` entries |
| D3 | `frontend/src/AGENTS.md` | Update | Update section configuration (4→3), shuffle policy, in-section search |
| D4 | `CLAUDE.md` | Update | Add embedder utility to project structure; update tool descriptions |
| D5 | `tools/core/README.md` | Update | Add new modules |
| D6 | `docs/how-to/backend/tool-development-standards.md` | Update | Document minimal-edit SGF exception for pre-ingest annotation tools |

---

## Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| IMP-1 | downstream | Existing tools using `tools/ogs/collections.py` | Medium — import paths change when consolidated | Re-export from new location; update imports in tools/ogs, tools/go_problems, tools/tsumego_hero | T1 | ❌ needs action |
| IMP-2 | downstream | `CollectionsBrowsePage` sections | Low — data-driven via SECTIONS constant | Change constant, section type filter logic | T5 | ❌ needs action |
| IMP-3 | lateral | `CollectionPuzzleLoader` | Low — shuffle is additive | New code path, existing path unchanged when shuffle disabled | T6 | ❌ needs action |
| IMP-4 | upstream | `config/collections.json` descriptions | Low — data-only change | No schema change, backward compatible | T4 | ❌ needs action |
| IMP-5 | downstream | Pipeline ingest of embedder-modified SGFs | Low — pipeline preserves existing YL[] | Verified: `is_enrichment_needed()` skips YL when present | N/A | ✅ addressed |
| IMP-6 | lateral | `puzzleQueryService.ts` | Medium — new SQL for in-section search | Add query function using `collections_fts` + type filter | T7 | ❌ needs action |
| IMP-7 | downstream | Other browse pages (technique, training) | Low — hover treatment is CSS-only | Apply consistent hover classes | T8 | ❌ needs action |

---

## Risks

| risk_id | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| R1 | Embedder modifies source SGFs in `external-sources/` (untracked runtime data) | Medium | High | 4-layer safety: (1) `--dry-run` mandatory for first runs, (2) `atomic_write_text()` prevents partial files on crash, (3) `.yl-backup` copy created before each write, (4) `--restore-backups` flag for full rollback |
| R2 | OGS manifest has 3,893 missing files | Low | Low | Graceful skip with logging |
| R3 | kisvadim folder names may not match all aliases | Medium | Medium | Run `collections_align.py` post-embed to audit |
| R4 | gotools filename regex is brittle | Low | Low | Isolated in Strategy C; tested against sample files |
| R5 | Multiple embedder runs could corrupt YL | Medium | Medium | Idempotent: parse-before-write, skip if already embedded. Backup files allow full rollback. |
