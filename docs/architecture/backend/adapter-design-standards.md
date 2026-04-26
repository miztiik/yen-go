# Adapter Design Standards

> **Document Type**: Architecture Standard  
> **Last Updated**: 2026-01-31  
> **Spec Reference**: 051-adapter-consolidation  
> **Status**: Active

---

## 1. Core Principles

| Principle | Description |
|-----------|-------------|
| Single Responsibility | Each adapter handles exactly one puzzle source |
| Protocol Compliance | All adapters implement `BaseAdapter` protocol |
| Deterministic Output | Same input → identical output (content-hash filenames) |
| Configuration via JSON | No hardcoded values; all config from `sources.json` |
| Graceful Failure | Yield `FetchResult.failed()`, never raise exceptions in `fetch()` |

---

## 2. Adapter Location

All adapters live in subdirectories: `backend/puzzle_manager/adapters/{name}/`

```
backend/puzzle_manager/adapters/
├── __init__.py       # Exports registry, base
├── _base.py          # BaseAdapter + ResumableAdapter protocols (underscore = non-adapter)
├── _registry.py      # @register_adapter decorator (underscore = non-adapter)
├── local/
│   ├── __init__.py
│   └── adapter.py    # LocalAdapter
├── yengo-source/
│   ├── __init__.py
│   ├── adapter.py    # YengoSourceAdapter (ResumableAdapter)
│   ├── converter.py
│   ├── models.py
│   └── translator.py
├── yengo-source/
│   ├── __init__.py
│   └── adapter.py    # YengoSourceAdapter
└── yengo-source/
    ├── __init__.py
    ├── adapter.py    # YengoSourceAdapter (ResumableAdapter)
    ├── converter.py
    ├── checkpoint.py
    └── mappers.py
```

### Naming Convention

| File Pattern | Meaning |
|--------------|--------|
| `_base.py`, `_registry.py` | Internal modules (underscore prefix) - NOT adapters |
| `{name}/adapter.py` | Adapter implementation |
| `{name}/converter.py` | Source-to-SGF conversion |
| `{name}/models.py` | Data classes for source API |

### Subdirectory Criteria

| Condition | Structure |
|-----------|----------|
| Adapter has **≥2 auxiliary modules** (converter, models, etc.) | Subdirectory required |
| Adapter is **single file** | Subdirectory still required (consistency) |

---

## 3. Adapter Protocols

Two protocols from `backend.puzzle_manager.adapters._base`:

### BaseAdapter (All Adapters)

```python
@runtime_checkable
class BaseAdapter(Protocol):
    @property
    def name(self) -> str: ...          # Human-readable name
    
    @property  
    def source_id(self) -> str: ...     # Unique ID (e.g., "yengo-source", "yengo-source")
    
    def configure(self, config: dict) -> None: ...
    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]: ...
```

### ResumableAdapter (API-Based Adapters)

```python
@runtime_checkable
class ResumableAdapter(BaseAdapter, Protocol):
    def supports_resume(self) -> bool: ...
    def get_checkpoint(self) -> str | None: ...
    def set_checkpoint(self, checkpoint: str) -> None: ...
```

| Adapter | Protocol | Rationale |
|---------|----------|----------|
| local, yengo-source, yengo-source | `BaseAdapter` | File-based, no checkpoint needed |
| yengo-source, yengo-source | `ResumableAdapter` | API-based, large datasets |

### FetchResult

```python
@dataclass
class FetchResult:
    status: Literal["success", "skipped", "failed"]
    puzzle_id: str | None = None
    sgf_content: str | None = None
    error: str | None = None
    
    # Factory methods
    FetchResult.success(puzzle_id, sgf_content)
    FetchResult.skipped(puzzle_id, reason)
    FetchResult.failed(puzzle_id, error)
```

---

## 4. Registration

Use the `@register_adapter` decorator to register adapters:

```python
from backend.puzzle_manager.adapters.registry import register_adapter

@register_adapter("my-source")
class MySourceAdapter:
    ...
```

---

## 5. Configuration

### 5.1 Sources Configuration

All adapter configuration lives in `backend/puzzle_manager/config/sources.json`:

```json
{
  "active_adapter": "yengo-source",
  "sources": [
    {
      "id": "yengo-source",
      "name": "yengo-source Puzzles",
      "adapter": "yengo-source",
      "config": {
        "base_url": "https://example.com/api/v1",
        "request_timeout_seconds": 30,
        "max_retries": 5,
        "collections": [123, 456]
      }
    }
  ]
}
```

> **Design Decision**: `active_adapter` is **singular by design** (not an array). The pipeline processes one adapter per run. Use `--source` CLI flag to override.

> **No `config/adapters/` directory**: All adapter config is embedded in sources.json entries.

### 5.2 Configuration Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `active_adapter` | string | Yes | Default adapter ID for pipeline runs |
| `id` | string | Yes | Unique source identifier (used in CLI `--source`) |
| `name` | string | Yes | Human-readable display name |
| `adapter` | string | Yes | Adapter registration name |
| `config` | object | Yes | **ALL** adapter-specific configuration (inline, not external file) |

### 5.3 Shared Configuration (Read-Only)

Adapters MUST read these from global config—never hardcode:

| File | Purpose |
|------|---------|
| `config/puzzle-levels.json` | 9-level difficulty system (DDK30 to Pro) |
| `config/tags.json` | Tag taxonomy |
| `config/source-quality.json` | Source credibility ratings |

---

## 6. SGF Output Standards

### 6.1 Required Properties

| Property | Required | Value | Example |
|----------|----------|-------|---------|
| `FF` | Yes | `4` | `FF[4]` |
| `GM` | Yes | `1` (Go) | `GM[1]` |
| `CA` | Yes | `UTF-8` | `CA[UTF-8]` |
| `SZ` | Yes | Board size | `SZ[19]` |
| `GN` | Yes | SGF filename (no extension) | `GN[YENGO-765f38a5196edb79]` |
| `PL` | Yes | Player to move | `PL[B]` |
| `AB` | If any | Black stones | `AB[aa][bb]` |
| `AW` | If any | White stones | `AW[cc][dd]` |

### 6.2 YenGo Extension Properties

| Property | Required | Format | Example |
|----------|----------|--------|---------|
| `YV` | Yes | Schema version | `YV[7]` |
| `YG` | Yes | Level slug from `puzzle-levels.json` | `YG[intermediate]` |
| `YT` | Yes | Comma-separated tags | `YT[life-and-death,tesuji]` |
| `YH` | No | Pipe-separated hints | `YH[hint1\|hint2\|hint3]` |
| `YQ` | No | Quality metrics | `YQ[depth:5,unique:true]` |

### 6.3 Forbidden Properties

| Property | Rule |
|----------|------|
| `SO` | **MUST be EMPTY** — Do not include source URLs |

### 6.4 Level Mapping

**CRITICAL**: Adapters MUST NOT hardcode level mappings.

```python
# ❌ WRONG - Hardcoded mapping
LEVEL_MAP = {"novice": "DDK30", "intermediate": "SDK"}

# ✅ CORRECT - Load from config
from backend.puzzle_manager.config.loader import ConfigLoader
loader = ConfigLoader()
level_config = loader.load_puzzle_levels()
```

---

## 7. Filename Convention

| Aspect | Standard |
|--------|----------|
| Format | `YENGO-{16-char-hash}.sgf` |
| Hash | SHA-256 of SGF content, truncated to 16 chars |
| Case | Lowercase hexadecimal |
| GN Property | Must equal filename without `.sgf` |

Example: `YENGO-765f38a5196edb79.sgf` → `GN[YENGO-765f38a5196edb79]`

---

## 8. Error Handling

| Error Type | Behavior |
|------------|----------|
| Config Error | Abort run, exit with error |
| Network Error | Retry with exponential backoff, then `FetchResult.failed()` |
| Parse Error | `FetchResult.failed()`, log error, continue |
| Validation Error | `FetchResult.skipped()`, log reason, continue |

---

## 9. Logging Standards

All adapters MUST log:

1. **Start**: Source ID, config summary
2. **Per-puzzle**: ID, result status
3. **Complete**: Total counts (success/failed/skipped), duration

```python
logger.info("Puzzle processed", extra={
    "source": self.source_id,
    "puzzle_id": puzzle_id,
    "result": "success",
})
```

---

## 10. Testing Requirements

Every adapter MUST have tests for:

- [ ] SGF output validity
- [ ] Required properties present
- [ ] Deterministic output (same input → same hash)
- [ ] Error handling (malformed input → `FetchResult.failed()`)
- [ ] No hardcoded level mappings

Test location: `backend/puzzle_manager/tests/adapters/test_{source_id}.py`

---

## 11. Compliance Checklist

Before merging adapter changes:

- [ ] Implements `BaseAdapter` protocol
- [ ] Uses `@register_adapter` decorator
- [ ] Configured in `sources.json`
- [ ] No hardcoded level mappings (uses `puzzle-levels.json`)
- [ ] No `SO` property in output
- [ ] `GN` equals filename
- [ ] `YG` uses valid level slug
- [ ] Errors logged with context
- [ ] Unit tests pass

---

## Related Documents

- [CLI Reference](../../reference/puzzle-manager-cli.md) — Pipeline commands
- [SGF Properties Schema](../../../config/schemas/sgf-properties.schema.json) — Schema definition
- [Puzzle Levels](../../../config/puzzle-levels.json) — Level definitions
