# Research: Collections Launch Polish (v2)

_Last Updated: 2026-03-29_

## Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 90 |
| `risk_level` | medium |
| `research_invoked` | yes |
| `trigger` | Source directory audit + frontend puzzle loading flow |

## Source Directory Audit

| src_id | Source | Exploitable Structure | Strategy | Puzzle Count | Priority |
|--------|--------|-----------------------|----------|-------------|----------|
| S-1 | `ogs` | `sgf-by-collection/{tier}/{batch}/{id-slug}/` + manifest | Manifest lookup (B) | ~42,749 | **Highest** |
| S-2 | `kisvadim-goproblems` | 60+ author/book dirs with rich names | Phrase match (A) | ~3,000 | **Highest** |
| S-3 | `gotools` | Level dirs + filename encoding `gotools_lv{N}_{ch}_p{id}.sgf` | Filename pattern (C) | ~5,000 | **High** |
| S-4 | `eidogo_puzzles` | 1 dir: `Qi Jing Zhong Miao - Gokyo Shumyo/` | Phrase match (A) | ~200 | Medium |
| S-5 | `tasuki` | `hatsuyoron/`, `lee-chang-ho/` with batch subs | Phrase match (A) | ~200 | Medium |
| S-6 | `101weiqi` | `books/book-{N}/` structure | Phrase match (A) | ~500 | Medium |
| S-7 | `goproblems_difficulty_based` | 3 dirs: `easy/`, `medium/`, `hard/` | Level dirs only | ~1,000 | Low |
| S-8 | `ambak-tsumego` | 3 dirs: `advanced/`, `elementary/`, `intermediate/` | Level dirs only | ~500 | Low |
| S-9 | `syougo` | 5 level dirs + filename `syougo_L{N}_P{NN}.sgf` | Filename pattern (C) | ~130 | Low |
| S-10 | `blacktoplay` | Flat `sgf/` + `collections.json` category decode | Local mapping file | ~1,000 | Low |
| S-11 | `sanderland` | Handled by dedicated adapter | Already works (NG) | ~2,000 | N/A |
| S-12 | `goproblems` | Flat `sgf/batch-NNN/` | None | ~2,000 | None |
| S-13 | `t-hero` | Flat `sgf/` | None | ~500 | None |
| S-14 | `tsumegodragon` | Flat | None | ~200 | None |
| S-15 | `manual-imports` | Empty | None | 0 | None |

## Embedder Strategy Registry

Three strategies, selected per source:

| strategy_id | Strategy | How It Works | Sources |
|-------------|----------|-------------|---------|
| A | Phrase Match | Walk dirs, match dir name against `config/collections.json` aliases | kisvadim, eidogo, tasuki, 101weiqi |
| B | Manifest Lookup | Parse OGS `sgf-by-collection/` manifests; `puzzles` array gives ordering | OGS only |
| C | Filename Pattern | Regex extracts level/chapter/position from filename | gotools, syougo |

## Duplicated Matcher Implementations (DRY Finding)

4 independent phrase-matching implementations exist:

| file | Location | Key Additions |
|------|----------|---------------|
| U-1 | `backend/puzzle_manager/core/collection_assigner.py` | Canonical: normalize, tokenize, contiguous subsequence |
| U-3 | `tools/ogs/collections.py` | Adds stop-word removal, CJK regex, longest-match-wins |
| U-5 | `tools/tsumego_hero/collections_matcher.py` | Adds local override priority |
| U-7 | `tools/go_problems/collections.py` | Clone of U-3 |

**Consolidation target**: `tools/core/collection_matcher.py` — merges U-1 + U-3 stop words + U-5 override pattern.

## Frontend Puzzle Loading Flow

| Finding | Detail |
|---------|--------|
| Ordering | `ORDER BY pc.sequence_number` in `puzzleQueryService.ts` |
| Offset support | Route supports `offset`; `CollectionViewPage` accepts `startIndex`; `CollectionPuzzleLoader` has `startIndex` param |
| Randomization | Not implemented. Would be client-side Fisher-Yates on loaded `puzzles` array |
| Filters | Level + tag filters via `usePuzzleFilters()` hook in `CollectionViewPage` |
| Browse sections | 4 current: Learning Paths (graded, limit:0), Techniques (technique, limit:6), Authors (author, limit:6), Reference (reference, limit:6) |
| "Show more" | Bottom of section, `rounded-full border` button |
| Card hover | `hover:-translate-y-1 hover:shadow-xl active:scale-[0.98]` — translateY bounce + shadow |

## Data Flow: Embedder → Pipeline → Frontend

```
EMBEDDER (pre-pipeline):
  external-sources/{source}/{dir}/{puzzle}.sgf
    → Parse SGF → Match dir name against collections.json aliases
    → Add/update YL[slug:chapter/position]
    → Log match/skip event

PIPELINE (unmodified):
  Reads SGF with YL already present → preserves through ingest → analyze → publish
  → Publish writes puzzle_collections row with sequence_number from YL position

FRONTEND (unmodified query):
  SELECT ... ORDER BY pc.sequence_number → displays in embedded order
```

## Reusable Existing Code

| Asset | Location | Reuse |
|-------|----------|-------|
| OGS phrase matcher | `tools/ogs/collections.py` | Extract to `tools/core/collection_matcher.py` |
| OGS collection index | `tools/ogs/collection_index.py` | OGS manifest → puzzle ID reverse lookup |
| Collections alignment | `tools/collections_align.py` | Post-embed validation |
| Canonical assigner | `backend/puzzle_manager/core/collection_assigner.py` | Algorithm reference (cannot import — architecture boundary) |
| SGF parser/builder | `tools/core/sgf_parser.py`, `sgf_builder.py` | Parse SGF, add YL, write back |
| Structured logging | `tools/core/logging.py` | Subclass for embed events |
| Checkpointing | `tools/core/checkpoint.py` | Resume support for large sources |
| OGS sorted JSONL | `external-sources/ogs/20260211-203516-collections-sorted.jsonl` | Puzzle ordering within OGS collections |
