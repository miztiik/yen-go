# Source Adapters

> **See also**:
>
> - [How-To: Create Adapter](../../how-to/backend/create-adapter.md) — Step-by-step guide
> - [Reference: Adapter Configs](../../reference/adapters/) — Per-adapter configuration

**Last Updated**: 2026-03-09

Adapters fetch puzzles from various sources into the pipeline.

---

## Architecture Overview

Adapters are the bridge between external puzzle sources and the YenGo pipeline. Each adapter:

- Connects to a specific puzzle source (file system, API, web scraper)
- Fetches puzzles in batches
- Returns normalized `FetchResult` objects for pipeline processing

---

## Core Principles

| Principle                 | Description                                                |
| ------------------------- | ---------------------------------------------------------- |
| **Single Responsibility** | One adapter per source type                                |
| **Protocol Compliance**   | All adapters implement `BaseAdapter` or `ResumableAdapter` |
| **Deterministic Output**  | Same input → identical output (no random elements)         |
| **Config via JSON**       | No hardcoded level mappings or source URLs                 |
| **Graceful Failure**      | Never raise from `fetch()`; yield `FetchResult.failed()`   |

---

## Adapter Location

All adapters live in subdirectories under `backend/puzzle_manager/adapters/`:

```
backend/puzzle_manager/adapters/
├── __init__.py
├── _base.py            # BaseAdapter / ResumableAdapter protocols
├── _registry.py        # @register_adapter decorator
├── local/              # File system adapter
│   ├── __init__.py
│   └── adapter.py
├── source-a/           # API-backed adapter (example)
│   ├── __init__.py
│   └── adapter.py
└── source-b/           # Remote file-backed adapter (example)
    ├── __init__.py
    └── adapter.py
```

---

## Adapter Protocols

### BaseAdapter (All Adapters)

```python
class BaseAdapter(Protocol):
    @property
    def name(self) -> str:
        """Human-readable name."""
        ...

    @property
    def source_id(self) -> str:
        """Unique identifier for this source."""
        ...

    def configure(self, config: dict[str, Any]) -> None:
        """Initialize with source-specific settings."""
        ...

    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
        """Yield results for each puzzle fetched."""
        ...
```

### ResumableAdapter (API-Based Sources)

Extends `BaseAdapter` with checkpoint support:

```python
class ResumableAdapter(BaseAdapter):
    def supports_resume(self) -> bool:
        """Return True if adapter supports checkpoints."""
        ...

    def get_checkpoint(self) -> str | None:
        """Return serialized checkpoint state."""
        ...

    def set_checkpoint(self, checkpoint: str) -> None:
        """Restore from serialized checkpoint."""
        ...
```

---

## FetchResult Dataclass

All adapters yield `FetchResult` objects:

```python
@dataclass
class FetchResult:
    puzzle_id: str | None
    status: Literal["success", "skipped", "failed"]
    sgf_content: str | None = None
    reason: str | None = None
    error: str | None = None

    @classmethod
    def success(cls, puzzle_id: str, sgf_content: str) -> "FetchResult":
        ...

    @classmethod
    def skipped(cls, puzzle_id: str, reason: str) -> "FetchResult":
        ...

    @classmethod
    def failed(cls, puzzle_id: str | None, error: str) -> "FetchResult":
        ...
```

---

## Configuration

Adapters are configured in `backend/puzzle_manager/config/sources.json`:

```json
{
  "active_adapter": "<source_id>",
  "sources": [
    {
      "id": "source-a",
      "name": "Source A",
      "adapter": "source-a",
      "enabled": true,
      "config": {
        "base_url": "https://example.invalid/api/v1",
        "batch_hint": 100
      }
    },
    {
      "id": "source-b",
      "name": "Source B",
      "adapter": "source-b",
      "enabled": true,
      "config": {
        "base_path": "./external-sources/source-b"
      }
    }
  ]
}
```

> **Design Decision**: `active_adapter` is **singular by design**. The pipeline processes one adapter per run. Use `--source` CLI flag to override.

---

## Built-in Adapter Patterns

| Pattern                            | Type        | Resume      | Typical Input                 |
| ---------------------------------- | ----------- | ----------- | ----------------------------- |
| `local`                            | File system | No          | Local SGF directories         |
| `url`                              | HTTP fetch  | No          | Remote SGF URLs               |
| Source-specific API adapter        | API         | Usually Yes | Paginated source APIs         |
| Source-specific scraper adapter    | Scraper     | Varies      | Structured HTML or JSON pages |
| Source-specific repository adapter | File fetch  | No          | Versioned SGF bundles         |

---

## Error Handling

| Error Type       | Behavior                                                    |
| ---------------- | ----------------------------------------------------------- |
| Config Error     | Abort run, exit with error                                  |
| Network Error    | Retry with exponential backoff, then `FetchResult.failed()` |
| Parse Error      | `FetchResult.failed()`, log error, continue                 |
| Validation Error | `FetchResult.skipped()`, log reason, continue               |

---

## Puzzle ID and Filename Flow

Understanding how puzzle IDs flow through the pipeline is critical for adapter development:

### Pipeline Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INGEST STAGE (Adapter)                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Adapter fetches puzzle from source                                        │
│ 2. Adapter generates puzzle_id (any format - doesn't matter)                 │
│ 3. Adapter may set GN property (will be overwritten)                         │
│ 4. Returns FetchResult(puzzle_id=..., sgf_content=...)                       │
│ 5. Ingest stage saves: staging/ingest/{puzzle_id}.sgf                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ANALYZE STAGE (Enrichment)                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Reads staging/ingest/{puzzle_id}.sgf                                      │
│ 2. Enriches with YenGo properties (YG, YT, YQ, YX, YH, etc.)                 │
│ 3. Saves: staging/analyzed/{puzzle_id}.sgf                                   │
│    (filename unchanged, content enriched)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PUBLISH STAGE (Final Output)                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Reads staging/analyzed/{puzzle_id}.sgf                                    │
│ 2. Generates content_hash = SHA256(enriched_content)[:16]                    │
│ 3. Updates GN property: GN[YENGO-{content_hash}]                             │
│ 4. Injects YI[run_id] for traceability                                       │
│ 5. Saves: yengo-puzzle-collections/sgf/{level}/.../batch-NNN/{content_hash}.sgf │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principle: GN == Filename

**The publish stage ensures `GN` always matches the filename:**

```
Filename: 765f38a5196edb79.sgf
GN:       GN[YENGO-765f38a5196edb79]
```

This is critical for:

- **Rollback**: Can locate file by GN property
- **Deduplication**: Content hash prevents duplicates
- **Frontend**: Can construct URL from GN value

### Adapter Responsibility

Adapters only need to:

1. Generate a **unique puzzle_id** for the batch (any format)
2. Return valid SGF content

Adapters do **NOT** need to:

- Generate YENGO-format IDs (publish stage handles this)
- Set GN property correctly (publish stage overwrites it)
- Worry about final filename (determined by content hash)
