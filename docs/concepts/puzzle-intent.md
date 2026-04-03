# Puzzle Intent - Objective Extraction from SGF Comments

> **Module**: `tools/puzzle_intent/`
> **Config**: `config/puzzle-objectives.json`
> **Schema**: `config/schemas/puzzle-objectives.schema.json`
> **Version**: 2.0.0

## Purpose

Extracts puzzle objectives (e.g., "black to play", "white to live") from noisy SGF comment text that may contain CJK characters, HTML markup, tutorial preambles, and other irrelevant content.

## Architecture

```
Raw SGF Comment Text
    |
    v
[Text Cleaner]  -- strip HTML, CJK, normalize
    |
    v
[Tier 1: Exact Matcher]  -- deterministic substring/token matching
    |
    +---> Match found? --> Return IntentResult (confidence=1.0)
    |
    v (no match)
[Tier 2: Semantic Matcher]  -- sentence-transformer cosine similarity
    |
    +---> Above threshold? --> Return IntentResult (confidence=similarity)
    |
    v (below threshold)
Return IntentResult (matched=False)
```

### Tiered Matching Strategy

| Tier | Method                                 | Speed | Dependencies          | Confidence |
| ---- | -------------------------------------- | ----- | --------------------- | ---------- |
| 1    | Exact substring + token match          | <1ms  | None (stdlib)         | Always 1.0 |
| 2    | Sentence-transformer cosine similarity | ~10ms | sentence-transformers | 0.0-1.0    |

Tier 1 runs first (fast, deterministic). Tier 2 is the fallback for creative paraphrasing that doesn't match any exact alias.

## Configuration

### Objectives (config/puzzle-objectives.json)

23 objectives across 7 categories with 250+ aliases. Each objective has:

- **`slug`**: Kebab-case backend identifier (e.g. `black-to-play`)
- **`name`**: Human-readable display name for frontend (e.g. `Black to Play`)
- **`objective_id`**: Internal key (e.g. `MOVE.BLACK.PLAY`)

| Category       | Objectives                                                                 | Example                                          |
| -------------- | -------------------------------------------------------------------------- | ------------------------------------------------ |
| MOVE_ORDER     | BLACK.PLAY, WHITE.PLAY                                                     | "black to play", "kurosaki"                      |
| LIFE_AND_DEATH | BLACK.LIVE, WHITE.LIVE, BLACK.KILL, WHITE.KILL, BLACK.ESCAPE, WHITE.ESCAPE | "white to live", "kill black", "black to escape" |
| CAPTURING      | BLACK, WHITE                                                               | "capture with black"                             |
| SHAPE          | BLACK.CONNECT, WHITE.CONNECT, BLACK.CUT, WHITE.CUT                         | "black to connect"                               |
| FIGHT          | BLACK.WIN_SEMEAI, WHITE.WIN_SEMEAI, BLACK.WIN_KO, WHITE.WIN_KO, SEKI       | "seki", "black wins ko"                          |
| TESUJI         | BLACK, WHITE                                                               | "find the tesuji for black"                      |
| ENDGAME        | BLACK, WHITE                                                               | "white yose"                                     |

### Alias Strategy

**Objectives are narrow** (23 canonical goals), **aliases are broad** (250+ surface forms):

- English phrases: "black to play", "save the black group"
- Abbreviations: "b to play", "w to play"
- Romanized Japanese: "kurosaki" (black first), "shirosaki" (white first)
- Romanized Korean: "heukseon" (black first), "baekseon" (white first)
- Common paraphrases: "black's turn", "black plays first"

### CJK Handling

The text cleaner **strips CJK characters** before matching because the semantic model (all-MiniLM-L6-v2) is English-only. Instead of CJK aliases, we use **romanized equivalents** that survive the cleaning pipeline.

For pure CJK text with no English content, a future enhancement would add a CJK pre-translation step using `config/jp-en-dictionary.json`.

## Usage

### Basic Usage

```python
from tools.puzzle_intent import resolve_intent

result = resolve_intent("Welcome to Go! Black to play")
print(result.objective_id)       # "MOVE.BLACK.PLAY"
print(result.objective.slug)     # "black-to-play"
print(result.objective.name)     # "Black to Play"
print(result.confidence)         # 1.0
print(result.match_tier)         # MatchTier.EXACT
print(result.matched)            # True
```

### Deterministic Mode (no ML)

```python
result = resolve_intent(text, enable_semantic=False)
```

### Batch Processing

```python
from tools.puzzle_intent import resolve_intents_batch

results = resolve_intents_batch([
    "black to live",
    "white to kill",
    "some random text",
])
```

### Custom Logger

```python
from tools.puzzle_intent import IntentResolver

resolver = IntentResolver(
    enable_semantic=True,
    similarity_threshold=0.65,
    structured_logger=my_logger,
)
result = resolver.resolve(text)
```

## Dependencies

### Required (always)

- Python 3.12+ (stdlib only: `re`, `html`, `unicodedata`, `json`, `functools`)
- `tools.core.logging` (project utility)

### Optional (for semantic matching)

- `sentence-transformers>=2.2.0` (PyTorch, transformers, ~500MB)
- Install: `pip install sentence-transformers` or `pip install -e ".[nlp]"`
- Model: `all-MiniLM-L6-v2` (~80MB, downloaded on first use)

The module gracefully degrades without sentence-transformers: only Tier 1 (exact matching) runs.

## Schema Evolution

The objectives schema is versioned (`schema_version` field) with a changelog for auditability:

- **Major version bump** (1.0 -> 2.0): New objectives added
- **Minor version bump** (2.0 -> 2.1): New aliases added to existing objectives

Validation: `config/schemas/puzzle-objectives.schema.json`

### Adding New Aliases

1. Edit `config/puzzle-objectives.json` - add alias to the appropriate objective
2. Bump `schema_version` minor
3. Add changelog entry
4. Run tests: `pytest tools/puzzle_intent/tests/ -v`
5. Validate against schema

### Adding New Objectives

1. Edit `config/puzzle-objectives.json` - add new objective with aliases
2. Update `models.py` if new `ObjectiveCategory` or `objective_type` needed
3. Update `config/schemas/puzzle-objectives.schema.json` enums
4. Bump `schema_version` major
5. Add changelog entry
6. Add tests for new objective
7. Run full test suite

## Testing

```bash
# All tests (exact matching only - no ML dependency)
pytest tools/puzzle_intent/tests/ -v

# Semantic tests require sentence-transformers (auto-skipped if missing)
pip install sentence-transformers
pytest tools/puzzle_intent/tests/ -v
```

## Cross-References

- [Tags taxonomy](tags.md) - Tags describe techniques, objectives describe goals
- [SGF Properties](sgf-properties.md) - YT (tags) property in enriched SGF
- [Pipeline stages](../architecture/backend/stages.md) - analyze stage where intent could be used
- [Configuration](../architecture/backend/README.md) - config/ directory conventions
