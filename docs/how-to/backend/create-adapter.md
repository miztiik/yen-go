# Create a New Adapter

> **See also**:
>
> - [Architecture: Adapters](../../architecture/backend/adapters.md) — Adapter design
> - [Reference: Adapter Configs](../../reference/adapters/) — Per-adapter configuration
> - [CLI Reference](./cli-reference.md) — Pipeline commands

**Last Updated**: 2026-02-01

Step-by-step guide for creating custom adapters to import puzzles from new sources.

---

## Overview

Adapters are the bridge between external puzzle sources and the YenGo pipeline. Each adapter:

- Connects to a specific puzzle source (file system, API, web scraper)
- Fetches puzzles in batches
- Returns normalized puzzle data for pipeline processing

---

## Quick Start

1. Create a new adapter directory in `backend/puzzle_manager/adapters/`
2. Implement the `BaseAdapter` protocol
3. Register with `@register_adapter` decorator
4. Add source configuration in `config/sources.json`
5. Test with `python -m backend.puzzle_manager run --source my-source --batch-size 5`

---

## Step 1: Create Adapter Directory

All adapters live in subdirectories:

```
backend/puzzle_manager/adapters/
├── __init__.py
├── _base.py            # BaseAdapter protocol
├── _registry.py        # @register_adapter decorator
└── my_source/          # Your new adapter
    ├── __init__.py
    └── adapter.py      # Main adapter implementation
```

---

## Step 2: Implement BaseAdapter

Create `backend/puzzle_manager/adapters/my_source/adapter.py`:

```python
from typing import Iterator, Any
from backend.puzzle_manager.adapters import register_adapter
from backend.puzzle_manager.adapters._base import BaseAdapter, FetchResult
from backend.puzzle_manager.core.http import HttpClient

import logging

logger = logging.getLogger("puzzle_manager.adapters.my_source")


@register_adapter("my-source")
class MySourceAdapter(BaseAdapter):
    """Adapter for MySource puzzle repository."""

    @property
    def name(self) -> str:
        return "My Puzzle Source"

    @property
    def source_id(self) -> str:
        return "my-source"

    def configure(self, config: dict[str, Any]) -> None:
        """Configure adapter with source-specific settings."""
        self._base_url = config.get("base_url", "")
        self._api_key = config.get("api_key", "")
        self._client = HttpClient()

    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
        """Fetch a batch of puzzles from the source.

        Yields:
            FetchResult for each puzzle (success, skipped, or failed)
        """
        logger.info(f"Fetching batch of {batch_size} puzzles from {self._base_url}")

        try:
            response = self._client.get(f"{self._base_url}/puzzles?limit={batch_size}")
            puzzles = response.json()

            for puzzle in puzzles:
                try:
                    sgf = self._convert_to_sgf(puzzle)
                    yield FetchResult.success(
                        puzzle_id=puzzle["id"],
                        sgf_content=sgf
                    )
                except Exception as e:
                    yield FetchResult.failed(
                        puzzle_id=puzzle.get("id"),
                        error=str(e)
                    )

        except Exception as e:
            logger.error(f"Failed to fetch from source: {e}")
            # Don't raise - let pipeline handle gracefully

    def _convert_to_sgf(self, puzzle: dict) -> str:
        """Convert source puzzle format to SGF."""
        # Implementation specific to your source format
        pass
```

---

## Step 3: Add Checkpoint Support (Optional)

For API-based adapters with large datasets, implement `ResumableAdapter`:

```python
from backend.puzzle_manager.adapters._base import ResumableAdapter

@register_adapter("my-source")
class MySourceAdapter(ResumableAdapter):

    def supports_resume(self) -> bool:
        return True

    def get_checkpoint(self) -> str | None:
        """Return current position for resumption."""
        return json.dumps({
            "page": self._current_page,
            "last_id": self._last_processed_id,
        })

    def set_checkpoint(self, checkpoint: str) -> None:
        """Restore position from checkpoint."""
        data = json.loads(checkpoint)
        self._current_page = data.get("page", 1)
        self._last_processed_id = data.get("last_id")
```

---

## Step 4: Register and Export

Update `backend/puzzle_manager/adapters/my_source/__init__.py`:

```python
from .adapter import MySourceAdapter

__all__ = ["MySourceAdapter"]
```

---

## Step 5: Add Source Configuration

Add to `backend/puzzle_manager/config/sources.json`:

```json
{
  "sources": [
    {
      "id": "my-source",
      "name": "My Puzzle Source",
      "adapter": "my-source",
      "enabled": true,
      "config": {
        "base_url": "https://api.example.com",
        "api_key": "${MY_SOURCE_API_KEY}",
        "batch_size": 100
      }
    }
  ]
}
```

---

## Step 6: Test Your Adapter

```bash
# List sources to verify registration
python -m backend.puzzle_manager sources

# Dry run with small batch
python -m backend.puzzle_manager run --source my-source --batch-size 5 --dry-run

# Real run with small batch
python -m backend.puzzle_manager run --source my-source --batch-size 5

# Check results
python -m backend.puzzle_manager status
```

---

## FetchResult Reference

Each puzzle result must be wrapped in `FetchResult`:

```python
# Success - puzzle fetched and converted
FetchResult.success(puzzle_id="puz-001", sgf_content="(;FF[4]...)")

# Skipped - puzzle intentionally skipped (e.g., duplicate)
FetchResult.skipped(puzzle_id="puz-002", reason="Duplicate")

# Failed - puzzle failed to process
FetchResult.failed(puzzle_id="puz-003", error="Invalid SGF format")
```

---

## Critical: GN Property and Puzzle ID Flow

> ⚠️ **IMPORTANT FOR ADAPTER DEVELOPERS**
>
> Adapters do **NOT** need to set the `GN` property correctly. The pipeline handles it automatically.

### What Adapters Must Do

1. Generate a **unique `puzzle_id`** for each puzzle (any format works)
2. Return valid SGF content with basic properties (`FF`, `GM`, `SZ`)
3. Return `FetchResult.success(puzzle_id=..., sgf_content=...)`

### What Adapters Should NOT Do

- ❌ Generate YENGO-format IDs (publish stage handles this)
- ❌ Set `GN` property to match any specific format (will be overwritten)
- ❌ Worry about final filename (determined by content hash)

### How the Pipeline Handles GN

```
INGEST:  Adapter returns puzzle_id="my-adapter-123"
         → File saved as: staging/ingest/my-adapter-123.sgf
         → GN property: doesn't matter (can be anything or missing)

ANALYZE: Enriches with YG, YT, YQ, YX, YH properties
         → File saved as: staging/analyzed/my-adapter-123.sgf
         → GN property: still unchanged

PUBLISH: Generates content_hash from enriched SGF
         → Updates GN to: GN[YENGO-{content_hash}]
         → File saved as: {content_hash}.sgf
         → GN == filename (guaranteed)
```

### Example

```python
# ✅ CORRECT - Simple puzzle_id, no GN worry
yield FetchResult.success(
    puzzle_id="cho-chikun-001",  # Any unique ID
    sgf_content="(;FF[4]GM[1]SZ[19]AB[aa][bb]AW[cc];B[dd])"
)

# ✅ ALSO CORRECT - YENGO-format ID (but not required)
yield FetchResult.success(
    puzzle_id="YENGO-abc123def456",
    sgf_content="(;FF[4]GM[1]SZ[19]GN[anything]...)"  # GN will be overwritten
)
```

> **See also**: [Architecture: Adapters - Puzzle ID Flow](../../architecture/backend/adapters.md#puzzle-id-and-filename-flow) for the complete flow diagram.

---

## Best Practices

### 1. Use HttpClient for HTTP Requests

```python
from backend.puzzle_manager.core.http import HttpClient

self._client = HttpClient()
response = self._client.get(url)
```

`HttpClient` provides automatic retries, rate limiting, and timeout handling.

### 2. Handle Errors Gracefully

Never raise exceptions from `fetch()`. Yield `FetchResult.failed()` instead:

```python
def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
    try:
        # ... fetch logic
    except RequestError as e:
        yield FetchResult.failed(puzzle_id=None, error=str(e))
```

### 3. Validate SGF Content

```python
from backend.puzzle_manager.core.sgf_parser import parse_sgf

def _validate_sgf(self, sgf: str) -> bool:
    try:
        game = parse_sgf(sgf)
        return game is not None
    except Exception:
        return False
```

### 4. Log Operations

```python
import logging
logger = logging.getLogger("puzzle_manager.adapters.my_source")

logger.info(f"Fetching batch of {batch_size} puzzles")
logger.debug(f"API response: {response.status_code}")
```

### 5. Use PuzzleValidator for Consistent Validation

All adapters should use the centralized `PuzzleValidator` for puzzle validation:

```python
from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleValidator,
    PuzzleData,
)

class MySourceAdapter(BaseAdapter):
    def __init__(self) -> None:
        self._validator = PuzzleValidator()  # Loads defaults from config

    def configure(self, config: dict[str, Any]) -> None:
        # Apply adapter-specific validation overrides
        validation_overrides = config.get("validation", {})
        self._validator.configure(validation_overrides)

    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
        for puzzle in puzzles:
            # Convert to PuzzleData
            puzzle_data = PuzzleData(
                board_width=puzzle["width"],
                board_height=puzzle["height"],
                black_stones=puzzle["black_stones"],
                white_stones=puzzle["white_stones"],
                has_solution=puzzle.get("has_solution", False),
                solution_depth=puzzle.get("solution_depth"),
            )

            # Validate
            result = self._validator.validate(puzzle_data)

            if not result:
                yield FetchResult.skipped(
                    puzzle_id=puzzle["id"],
                    reason=result.rejection_reason
                )
                continue

            # Process valid puzzle...
```

**Adapter-specific validation overrides** can be configured in the adapter config:

```json
{
  "id": "my-source",
  "config": {
    "base_url": "https://api.example.com"
  },
  "validation": {
    "max_solution_depth": 20,
    "min_stones": 3
  }
}
```

> **See also**: [Config: puzzle-validation.json](../../../config/README.md#puzzle-validationjson-spec-108) for all validation options.

---

## Existing Adapters (Reference)

| Adapter       | Type          | Resume | Notes                    |
| ------------- | ------------- | ------ | ------------------------ |
| `local`       | File system   | No     | Reference implementation |
| `sanderland`  | File (GitHub) | No     | Sanderland collection    |
| `blacktoplay` | API           | Yes    | BlackToPlay.com          |

See [Reference: Adapters](../../reference/adapters/) for configuration details.

---

## Troubleshooting

### Adapter Not Found

```
AdapterNotFoundError: Unknown adapter: my-source
```

- Ensure `@register_adapter("my-source")` decorator is applied
- Check adapter module is imported in `adapters/__init__.py`
- Verify directory structure matches convention

### Configuration Errors

- Check `sources.json` has all required fields
- Environment variables (e.g., `${MY_API_KEY}`) must be set
