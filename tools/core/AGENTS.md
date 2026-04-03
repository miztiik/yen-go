# tools/core — Agent Architecture Map

> Last Updated: 2026-03-29

Shared utility library for tool adapters. Self-contained — does NOT import from `backend/`.

## Directory Structure

| File | Purpose |
|------|---------|
| `atomic_write.py` | Cross-platform atomic file writes (temp + rename) |
| `batching.py` | Batch directory management with O(1) fast path |
| `checkpoint.py` | Resume support with JSON checkpoints |
| `chinese_translator.py` | CJK Go term translation via `config/cn-en-dictionary.json` |
| `collection_embedder.py` | Pre-pipeline YL embedder (EmbedStrategy protocol, 3 strategies, embed_collections()) |
| `collection_matcher.py` | Shared phrase matcher for collection name → slug resolution |
| `http.py` | HTTP client with backoff, rate limiting, SSRF protection |
| `index.py` | File index for dedup & tracking (one ID per line) |
| `logging.py` | Structured logging (console + JSON event types) |
| `paths.py` | Project root detection, POSIX normalization |
| `rate_limit.py` | Timestamp-based rate limiting |
| `rebalance.py` | Batch rebalancer (dry-run safe) |
| `sgf_analysis.py` | Tree analysis: depth, complexity, difficulty, move order |
| `sgf_builder.py` | SGF builder (fluent API) + round-trip rebuild |
| `sgf_correctness.py` | 3-layer correctness inference (markers → comment → heuristic) |
| `sgf_parser.py` | Recursive descent SGF parser (Schema v15 aware) |
| `sgf_types.py` | Primitives: Color, Point, Move |
| `text_cleaner.py` | Comment cleaning, slug generation, CJK stripping |
| `validation.py` | Source-agnostic puzzle validation |

## Key Entities

| Entity | File | Role |
|--------|------|------|
| `SGFParser` | sgf_parser.py | Parse SGF string → `SgfTree` |
| `SGFBuilder` | sgf_builder.py | Build SGF from primitives (fluent API) |
| `BatchWriter` | batching.py | Manage batch dirs (≤100 files each) |
| `CollectionMatcher` | collection_matcher.py | Collection name → slug phrase matcher |
| `EmbedStrategy` | collection_embedder.py | Protocol for collection resolution strategies |
| `PhraseMatchStrategy` | collection_embedder.py | Resolve dirs via CollectionMatcher aliases |
| `ManifestLookupStrategy` | collection_embedder.py | Resolve dirs via _collections_manifest.json |
| `FilenamePatternStrategy` | collection_embedder.py | Resolve slug from filename regex |
| `ToolCheckpoint` | checkpoint.py | JSON checkpoint for resume |
| `HttpClient` | http.py | HTTP with retry, rate-limit, backoff |
| `StructuredLogger` | logging.py | Console + JSONL event logging |
| `RateLimiter` | rate_limit.py | Overlap-aware rate limiting |

## Key Methods

| Method | File | Signature |
|--------|------|-----------|
| `CollectionMatcher.match()` | collection_matcher.py | `str → MatchResult \| None` |
| `CollectionMatcher.match_all()` | collection_matcher.py | `str → list[MatchResult]` |
| `embed_collections()` | collection_embedder.py | `(dir, strategy, matcher, logger) → EmbedSummary` |
| `restore_backups()` | collection_embedder.py | `(dir) → int` (restored count) |
| `parse_sgf()` | sgf_parser.py | `str → SgfTree` |
| `publish_sgf()` | sgf_builder.py | `SgfTree → str` |
| `infer_correctness()` | sgf_correctness.py | `SgfNode → "correct"\|"wrong"\|None` |
| `classify_difficulty()` | sgf_analysis.py | `SgfTree → level_id` |
| `validate_sgf_puzzle()` | validation.py | `str → PuzzleValidationResult` |
| `clean_comment_text()` | text_cleaner.py | `str → str` (strip HTML/CJK/URLs) |
| `get_batch_for_file_fast()` | batching.py | `path → batch_dir` (O(1)) |
| `load_checkpoint()` | checkpoint.py | `path → ToolCheckpoint` |

## Data Flow

```
External SGF → sgf_parser.parse_sgf() → SgfTree
  → sgf_correctness.infer_correctness() → annotated nodes
  → sgf_analysis.classify_difficulty() → level_id
  → validation.validate_sgf_puzzle() → pass/fail
  → sgf_builder.publish_sgf() → output SGF string
  → batching.BatchWriter → sgf/{batch}/{hash}.sgf
```

## Design Rules

- **Self-contained**: No imports from `backend/puzzle_manager/`
- **Config-driven**: Loads from `config/*.json` (tags, levels, dictionaries)
- **Dry-run safe**: Rebalance defaults to dry-run
- **3-layer correctness**: markers (`BM`, `TE`) → comment (`C[Correct]`) → heuristic
