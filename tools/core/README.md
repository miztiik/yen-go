# Tools Core Utilities

Shared functionality for all download tools (OGS, TsumegoDragon, etc.).

**→ [TEMPLATE.md](TEMPLATE.md)** — Quick-start scaffolding for creating a new tool
**→ [Tool Development Standards](../../docs/how-to/backend/tool-development-standards.md)** — Normative rules (authority)

## ⚠️ Architecture Boundary

**DO NOT IMPORT FROM `backend.*`**

Tools and backend are separate codebases with different responsibilities:

- `tools/` = External source ingestors (download from web)
- `backend/` = Pipeline processing (ingest → analyze → publish)

If `tools.core` is missing functionality that exists in `backend.puzzle_manager.core`,
**copy** the implementation to `tools.core` - do not import across the boundary.

This ensures:

- Tools can be used standalone without backend dependencies
- Clear separation of concerns
- Independent testing and versioning

## Modules

| Module            | Purpose                                                                                                                                                              |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `atomic_write`    | Cross-platform atomic file writes (temp + rename) with Windows retry                                                                                                 |
| `batching`        | Batch directory management (batch-001, batch-002, etc.)                                                                                                              |
| `checkpoint`      | Resume support with JSON checkpoint files                                                                                                                            |
| `collection_embedder` | Pre-pipeline YL embedder: `EmbedStrategy` protocol, 3 strategies (phrase match, manifest lookup, filename pattern), `embed_collections()`, atomic writes, dry-run, restore |
| `collection_matcher`  | Shared phrase matcher for collection name → slug resolution: `CollectionMatcher`, `match()`, `match_all()`                                                                |
| `paths`           | Path utilities - project root, relative paths, POSIX normalization                                                                                                   |
| `logging`         | Structured logging (console + JSON file)                                                                                                                             |
| `http`            | HTTP client with retry, rate limiting, backoff                                                                                                                       |
| `rate_limit`      | Timestamp-based rate limiting (overlaps wait with processing)                                                                                                        |
| `validation`      | Puzzle validation (board size, stones, solution depth)                                                                                                               |
| `sgf_types`       | Go primitives: `Color`, `Point`, `Move`, level constants                                                                                                             |
| `sgf_parser`      | Full SGF tree parser: `parse_sgf()`, `SgfNode`, `SgfTree`, `YenGoProperties`                                                                                         |
| `sgf_correctness` | Move correctness inference (SGF markers + comment prefix matching)                                                                                                   |
| `sgf_analysis`    | Tree analysis: `max_branch_depth()`, `compute_solution_depth()`, `get_all_paths()`, `classify_difficulty()`, `detect_move_order()`                                   |
| `sgf_builder`     | SGF string builder: `SGFBuilder` (30+ methods), `publish_sgf()`                                                                                                      |
| `text_cleaner`    | Text normalization: comment cleaning (`strip_html`, `clean_comment_text`), collection name processing (`clean_name`, `generate_slug`, `infer_curator`, `infer_type`) |

## Usage

```python
from tools.core import (
    # atomic_write
    atomic_write_json, atomic_write_text,
    # batching
    get_batch_for_file, BatchInfo,
    # checkpoint
    ToolCheckpoint, load_checkpoint, save_checkpoint,
    # paths
    get_project_root, rel_path, to_posix_path,
    # logging
    setup_logging, StructuredLogger, EventType,
    # http
    HttpClient, calculate_backoff_with_jitter,
    # rate_limit
    RateLimiter, wait_with_jitter,
    # text_cleaner - comment cleaning
    clean_comment_text, strip_html, strip_urls, strip_cjk,
    # text_cleaner - collection name processing
    clean_name, generate_slug, infer_curator, infer_type,
)
```

## Testing Guidelines

### ⚠️ CRITICAL: Avoid Checkpoint Pollution

When running tests, always use these patterns to avoid polluting real checkpoints
or hammering external APIs:

```bash
# ALWAYS use --dry-run for testing
python -m tools.ogs --dry-run --max-puzzles 1

# ALWAYS use batch_size=1 for minimal testing
python -m tools.ogs --dry-run --batch-size 1 --max-puzzles 1

# ALWAYS use --no-log-file to avoid log pollution
python -m tools.ogs --dry-run --no-log-file --max-puzzles 1

# Full minimal test command
python -m tools.ogs --dry-run --no-log-file --batch-size 1 --max-puzzles 1
```

### Test Patterns

1. **Dry Run Mode**: Always test with `--dry-run` first
   - No actual downloads
   - No checkpoint modifications
   - No API calls (or minimal)
   - Shows what would happen

2. **Batch Size = 1**: Use `--batch-size 1` for tests
   - If it works for 1, it works for N
   - Faster test execution
   - Minimal resource usage

3. **No Log File**: Use `--no-log-file` in tests
   - Avoids polluting logs directory
   - Console output only
   - Cleaner test output

4. **Max Puzzles = 1**: Use `--max-puzzles 1` for tests
   - Minimal API calls
   - Fast test execution
   - Sufficient for testing flow

### Integration Test Structure

```python
def test_ogs_dry_run():
    """Test OGS downloader in dry-run mode."""
    result = subprocess.run([
        "python", "-m", "tools.ogs",
        "--dry-run",
        "--no-log-file",
        "--batch-size", "1",
        "--max-puzzles", "1",
    ], capture_output=True, text=True)

    assert result.returncode == 0
    assert "dry run" in result.stdout.lower() or "would download" in result.stdout.lower()
```

### Checkpoint Isolation

For unit tests, use temporary directories:

```python
def test_checkpoint_save_load(tmp_path):
    """Test checkpoint save/load in isolation."""
    from tools.core.checkpoint import save_checkpoint, load_checkpoint, ToolCheckpoint
    from dataclasses import dataclass

    @dataclass
    class TestCheckpoint(ToolCheckpoint):
        counter: int = 0

    # Save to temp directory
    checkpoint = TestCheckpoint(counter=42)
    save_checkpoint(checkpoint, tmp_path)

    # Load and verify
    loaded = load_checkpoint(tmp_path, TestCheckpoint)
    assert loaded.counter == 42
```

### ⚠️ Test Directory Isolation (CRITICAL)

**NEVER test against production directories!** Use `--output-dir` with a test directory:

```bash
# Create isolated test directory
mkdir -p external-sources/ogs-test

# Run with test directory (safe!)
python -m tools.ogs --output-dir external-sources/ogs-test --max-puzzles 5

# Clean up after testing
rm -rf external-sources/ogs-test
```

For unit tests, always use `pytest`'s `tmp_path` fixture:

```python
def test_batching_edge_cases(tmp_path):
    """Test batching without touching production directories."""
    from tools.core.batching import get_batch_for_file_fast
    from tools.core.checkpoint import BatchTrackingMixin

    sgf_dir = tmp_path / "sgf"
    sgf_dir.mkdir()

    # Test batch transitions
    batch_dir, batch_num = get_batch_for_file_fast(
        sgf_dir, current_batch=1, files_in_current_batch=499, batch_size=500
    )
    assert batch_num == 1  # Still room for one more

    batch_dir, batch_num = get_batch_for_file_fast(
        sgf_dir, current_batch=1, files_in_current_batch=500, batch_size=500
    )
    assert batch_num == 2  # Batch full, use next
```

## Design Principles

- **DRY**: Don't repeat code across tools
- **KISS**: Simple, focused modules
- **Configurable**: Paths defined in one place (`TOOL_OUTPUT_DIRS`)
- **Testable**: Every module supports dry-run/test mode
- **O(1) Batching**: Use `get_batch_for_file_fast()` with checkpoint tracking

## Core Components

### atomic_write_json / atomic_write_text

**ALWAYS use atomic writes for JSON checkpoint files and configuration outputs.**

```python
from tools.core.atomic_write import atomic_write_json, atomic_write_text

# Write JSON atomically (temp file + rename)
data = {"checkpoint": {"completed": 100, "current_batch": 2}}
atomic_write_json(output_path, data, indent=2)

# Write text atomically
atomic_write_text(output_path, sgf_content)
```

**Why atomic writes matter:**

- Crash/interrupt safety: File is either fully written or unchanged
- No orphaned temp files: Cleanup guaranteed via try/finally
- Windows compatibility: Retries on PermissionError (antivirus/indexer)

**When to use:**

- ✅ Checkpoint files
- ✅ Configuration outputs
- ✅ Index/manifest files
- ✅ Any file that must not be left in partial state

**When NOT needed:**

- Downloaded content from external sources (can re-download)
- Temporary working files

### BatchTrackingMixin

Provides O(1) batch tracking without filesystem scanning:

```python
from dataclasses import dataclass
from tools.core.checkpoint import ToolCheckpoint, BatchTrackingMixin

@dataclass
class MyCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    puzzles_downloaded: int = 0

# After successful file save:
checkpoint.record_file_saved(batch_size=500)
```

### get_batch_for_file_fast()

O(1) batch directory lookup using checkpoint state:

```python
from tools.core.batching import get_batch_for_file_fast

batch_dir, batch_num = get_batch_for_file_fast(
    parent_dir=sgf_dir,
    current_batch=checkpoint.current_batch,
    files_in_current_batch=checkpoint.files_in_current_batch,
    batch_size=500,
)
# Returns (Path("sgf/batch-001"), 1)
```

**Edge cases handled:**

- `files_in_current_batch=0` → Returns current batch
- `files_in_current_batch=499` → Returns current batch (room for 1 more)
- `files_in_current_batch=500` → Returns NEXT batch (current is full)
- `current_batch=10` → Returns `batch-010` (3-digit zero-padded)

## Path Configuration

All tool output paths are centralized in `tools/core/paths.py`:

```python
TOOL_OUTPUT_DIRS = {
    "ogs": "external-sources/ogs",
    "tsumegodragon": "external-sources/tsumegodragon",
    "t-dragon": "external-sources/tsumegodragon",  # Alias
}
```

To add a new tool, register its output directory here.
