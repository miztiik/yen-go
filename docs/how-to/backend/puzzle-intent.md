# Puzzle Intent — Objective Resolution from SGF Comments

**Last Updated**: 2026-02-13

Extract puzzle objectives from noisy SGF comment text using a tiered matching strategy.

## Quick Start

```bash
# Exact match (fast, deterministic)
python -m tools.puzzle_intent "Black to play"

# Semantic match (requires sentence-transformers)
python -m tools.puzzle_intent "Play as black and win"

# Deterministic-only mode (no ML)
python -m tools.puzzle_intent --no-semantic "Black to play"

# Read from file (recommended for CJK / multi-line text)
python -m tools.puzzle_intent --file sgf_comment.txt

# Rebuild embedding cache after changing aliases
python -m tools.puzzle_intent --rebuild-embeddings
```

## Architecture

```
Raw SGF text
    |
    v
[1. Text Cleaning]  strip HTML, URLs, CJK, boilerplate, normalize
    |
    v
[2. Tier 1: Exact]  substring/token match against 250+ aliases (confidence=1.0)
    |
    v  (no match)
[3. Tier 1.5: Keyword]  Go verb + side co-occurrence via regex (confidence=0.7)
    |
    v  (no match)
[4. Tier 2: Semantic]  sentence-transformer cosine similarity (confidence=0.65+)
    |
    v  (no match)
[5. No Match]  confidence=0.0, match_tier="none"
```

### Matching Tiers

| Tier          | Strategy                                      | Confidence | Dependencies          | Speed |
| ------------- | --------------------------------------------- | ---------- | --------------------- | ----- |
| 1 (Exact)     | Substring/token match against curated aliases | 1.0        | None                  | <1ms  |
| 1.5 (Keyword) | Go verb + side keyword co-occurrence          | 0.7        | None                  | <1ms  |
| 2 (Semantic)  | Cosine similarity via all-MiniLM-L6-v2        | 0.65+      | sentence-transformers | ~50ms |

### Text Cleaning Pipeline

Applied before any matching tier:

1. **strip_html** — Remove HTML tags, decode entities
2. **strip_urls** — Remove http/https URLs
3. **strip_cjk** — Remove CJK character blocks (preserves Latin text)
4. **strip_boilerplate** — Remove numbered labels ("Question 6", "Problem #3")
5. **normalize_text** — NFKC normalize, lowercase, collapse whitespace

## CLI Reference

```
python -m tools.puzzle_intent [OPTIONS] [TEXT]
```

| Flag                   | Description                              |
| ---------------------- | ---------------------------------------- |
| `TEXT`                 | Text to resolve (positional arg)         |
| `--file PATH`          | Read input from UTF-8 file               |
| `--no-semantic`        | Disable ML matching (deterministic only) |
| `--rebuild-embeddings` | Rebuild .npy embedding cache and exit    |
| `--help`               | Show help                                |

**Exit codes**: 0 = matched, 1 = no match

**Input priority**: positional arg > `--file` > stdin

## Output Format

```json
{
  "objective_id": "MOVE.BLACK.PLAY",
  "slug": "black-to-play",
  "name": "Black to Play",
  "matched_alias": "black to play",
  "confidence": 1.0,
  "match_tier": "exact",
  "matched": true,
  "cleaned_text": "black to play",
  "raw_text": "Black to play"
}
```

| Field           | Type             | Description                                                     |
| --------------- | ---------------- | --------------------------------------------------------------- |
| `objective_id`  | `string \| null` | Internal objective key (e.g. `MOVE.BLACK.PLAY`)                 |
| `slug`          | `string \| null` | Kebab-case backend identifier (e.g. `black-to-play`)            |
| `name`          | `string \| null` | Human-readable display name for frontend (e.g. `Black to Play`) |
| `matched_alias` | `string \| null` | Which alias triggered the match                                 |
| `confidence`    | `float`          | Match confidence (0.0--1.0)                                     |
| `match_tier`    | `string`         | `"exact"`, `"keyword"`, `"semantic"`, or `"none"`               |
| `matched`       | `bool`           | Whether an objective was matched                                |
| `cleaned_text`  | `string`         | Preprocessed input text                                         |
| `raw_text`      | `string`         | Original input text                                             |

## Python API

```python
from tools.puzzle_intent import resolve_intent, resolve_intents_batch

# Single resolution
result = resolve_intent("Black to play and live")
print(result.objective_id)       # "LIFE_AND_DEATH.BLACK.LIVE"
print(result.objective.slug)     # "black-to-live"
print(result.objective.name)     # "Black to Live"
print(result.confidence)         # 1.0
print(result.match_tier)         # MatchTier.EXACT

# Deterministic-only mode
result = resolve_intent(text, enable_semantic=False)

# Batch processing (semantic model batching)
results = resolve_intents_batch(["black to live", "white to kill"])
```

## Embedding Cache (.npy)

Alias embeddings are cached as `.npy` files for fast startup:

- **Location**: `tools/puzzle_intent/.embedding_cache/`
- **Cache key**: SHA-256 of model name + sorted aliases (16 hex chars)
- **Auto-invalidation**: Any change to aliases or model produces a new key
- **Manual rebuild**: `python -m tools.puzzle_intent --rebuild-embeddings`
- **Git-ignored**: Cache files are derived data, not committed

## Adding New Aliases

1. Edit `config/puzzle-objectives.json` — add aliases to the relevant objective
2. Run `python -m tools.puzzle_intent --rebuild-embeddings` to update the cache
3. Run `pytest tools/puzzle_intent/tests/ -v` to verify

## Config Source of Truth

- **Objectives**: `config/puzzle-objectives.json` (23 objectives, 250+ aliases)
- **Schema**: `config/schemas/puzzle-objectives.schema.json`

> **See also**:
>
> - [Architecture: Pipeline](../../../specs/035-puzzle-manager-refactor/) — Pipeline context
> - [How-To: CLI Reference](./cli-reference.md) — Backend CLI commands
> - [Reference: Puzzle Sources](../../reference/puzzle-sources.md) — Source adapters
