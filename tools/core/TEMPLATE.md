# Creating a New Download Tool

Quick-start scaffolding for building a new tsumego download tool.

> **This is scaffolding, not specification.** The normative rules for tool development
> live in [Tool Development Standards](../../docs/how-to/backend/tool-development-standards.md).
> This template provides a quick-start skeleton and copy-paste file stubs.
> **When in conflict, Standards wins.**

## Quick Start

1. Register your tool in `tools/core/paths.py` (Step 1)
2. Create the required modules (Steps 2–9)
3. Run: `python -m tools.your-tool --dry-run --no-log-file --max-puzzles 1`

> **See also**: [Standards §1](../../docs/how-to/backend/tool-development-standards.md#1-file-organization) for the full list of required modules (13 files).

## Directory Structure

```
tools/
├── core/                    # Shared utilities (DO NOT DUPLICATE)
│   └── (see README.md for full module list)
│
└── your-tool/              # Your new tool
    ├── __init__.py         # Package exports
    ├── __main__.py         # CLI entry point
    ├── client.py           # API/HTTP client
    ├── models.py           # Data models (dataclasses)
    ├── mappers.py          # Source-specific level/tag/category mappings
    ├── storage.py          # SGF whitelist rebuild and file saving
    ├── checkpoint.py       # Tool-specific checkpoint
    ├── logging_config.py   # Tool-specific logger
    ├── orchestrator.py     # Download orchestration
    ├── config.py           # Centralized constants and path utilities
    ├── batching.py         # Re-exports from tools.core.batching
    ├── index.py            # Puzzle ID index management
    ├── collections.py      # Local collection name -> YenGo slug mapping
    └── collections.json    # Local collections config file
```

---

## Step 1: Register in paths.py

```python
# In tools/core/paths.py
TOOL_OUTPUT_DIRS = {
    ...
    "your-tool": "external-sources/your-tool",
}
```

## Step 2: Create models.py

```python
"""Data models for YourTool."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class YourPuzzle:
    id: str
    sgf: str
    level: str
    tags: list[str]
    title: Optional[str] = None

@dataclass
class YourCategory:
    slug: str
    name: str
    puzzle_count: int
```

## Step 3: Create client.py

> **Standards**: See [§10 Rate Limiting](../../docs/how-to/backend/tool-development-standards.md#10-rate-limiting-standards) for processing-aware delay requirements.

```python
"""HTTP client for YourTool API."""
from tools.core.http import HttpClient

class YourToolClient:
    BASE_URL = "https://api.yourtool.com"

    def __init__(self, request_delay: float = 1.0):
        self._http = HttpClient(base_url=self.BASE_URL, request_delay=request_delay, max_retries=3)

    def __enter__(self): return self
    def __exit__(self, *args): self._http.close()

    def get_puzzles(self, category: str, page: int = 1) -> list[dict]:
        return self._http.get(f"/puzzles/{category}", params={"page": page}).json().get("puzzles", [])
```

## Step 4: Create checkpoint.py

> **Standards**: See [§8 Checkpoint and Resume](../../docs/how-to/backend/tool-development-standards.md#8-checkpoint-and-resume-standards) — save after EVERY successful file save, use `.checkpoint.json` (hidden dotfile).

```python
"""Checkpoint management for YourTool."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from tools.core.checkpoint import ToolCheckpoint, BatchTrackingMixin
from tools.core.checkpoint import load_checkpoint as core_load, save_checkpoint as core_save

@dataclass
class YourToolCheckpoint(ToolCheckpoint, BatchTrackingMixin):
    current_page: int = 1
    completed_categories: list[str] = field(default_factory=list)

def load_checkpoint(output_dir: Path) -> Optional[YourToolCheckpoint]:
    return core_load(output_dir, YourToolCheckpoint)

def save_checkpoint(checkpoint: YourToolCheckpoint, output_dir: Path) -> None:
    core_save(checkpoint, output_dir)
```

## Step 5: Create logging_config.py

> **Standards**: See [§3 Logging](../../docs/how-to/backend/tool-development-standards.md#3-logging-standards) for required methods (`puzzle_fetch`, `puzzle_enrich`, `collection_match`, `intent_match`) and the rich two-line progress format.

```python
"""Logging configuration for YourTool."""
import logging
from pathlib import Path
from tools.core.logging import setup_logging as core_setup_logging, StructuredLogger as CoreStructuredLogger, EventType

class StructuredLogger(CoreStructuredLogger):
    """YourTool-specific logger. Add tool-specific convenience methods here.
    See Standards §3 for the full required method set."""

    def puzzle_save(self, puzzle_id, path, downloaded=0, skipped=0, errors=0):
        self.reset_error_count()
        self.item_save(item_id=str(puzzle_id), path=path,
                       downloaded=downloaded, skipped=skipped, errors=errors)

def setup_logging(output_dir: Path, verbose=False, log_to_file=True, max_consecutive_errors=10):
    core_logger = core_setup_logging(output_dir=output_dir, logger_name="yourtool",
        verbose=verbose, log_to_file=log_to_file, log_suffix="yourtool",
        max_consecutive_errors=max_consecutive_errors)
    logger = StructuredLogger(core_logger.logger)
    logger.set_max_errors(max_consecutive_errors)
    return logger
```

## Step 6: Create storage.py

> **Standards**: See [§4 SGF Output](../../docs/how-to/backend/tool-development-standards.md#4-sgf-output-standards) for whitelist-only rebuild and approved properties.

```python
"""SGF file storage for YourTool."""
from pathlib import Path
from tools.core.batching import get_batch_for_file
from tools.core.paths import to_posix_path

def save_puzzle(puzzle_id: str, sgf_content: str, output_dir: Path, batch_size: int = 500) -> str:
    sgf_dir = output_dir / "sgf"
    batch_info = get_batch_for_file(sgf_dir, batch_size=batch_size)
    batch_dir = sgf_dir / batch_info.batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    file_path = batch_dir / f"{puzzle_id}.sgf"
    file_path.write_text(sgf_content, encoding="utf-8")
    return to_posix_path(file_path.relative_to(output_dir))
```

## Step 7: Create orchestrator.py

> **Standards**: See [§2 CLI (banner/summary)](../../docs/how-to/backend/tool-development-standards.md#2-cli-standards), [§14 Counter Pattern](../../docs/how-to/backend/tool-development-standards.md#14-counter-pattern-mandatory), and [§8 Checkpoint](../../docs/how-to/backend/tool-development-standards.md#8-checkpoint-and-resume-standards).

```python
"""Download orchestration for YourTool."""
import signal, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .client import YourToolClient
from .checkpoint import YourToolCheckpoint, load_checkpoint, save_checkpoint
from .storage import save_puzzle
from .logging_config import setup_logging

@dataclass
class DownloadConfig:
    output_dir: Path
    max_puzzles: int = 0        # 0 = unlimited
    batch_size: int = 500       # Standards default: 500 or 1000
    request_delay: float = 1.0
    resume: bool = False        # Standards: --resume is opt-in
    verbose: bool = False
    dry_run: bool = False
    log_to_file: bool = True

@dataclass
class DownloadStats:
    downloaded: int = 0
    skipped: int = 0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    @property
    def elapsed(self): return time.time() - self.start_time

def download_puzzles(config: DownloadConfig) -> DownloadStats:
    logger = setup_logging(config.output_dir, verbose=config.verbose, log_to_file=config.log_to_file)
    stats = DownloadStats()
    checkpoint: Optional[YourToolCheckpoint] = None
    interrupted = False

    def handle_interrupt(signum, frame):
        nonlocal interrupted
        interrupted = True

    signal.signal(signal.SIGINT, handle_interrupt)

    if config.resume:
        checkpoint = load_checkpoint(config.output_dir)
    if checkpoint is None:
        checkpoint = YourToolCheckpoint()

    try:
        with YourToolClient(request_delay=config.request_delay) as client:
            pass  # Your download loop here
            # IMPORTANT: save_checkpoint() after EVERY successful file save
            # IMPORTANT: pass stats to logger.puzzle_save() — see Standards §14
    finally:
        save_checkpoint(checkpoint, config.output_dir)
        logger.run_end(downloaded=stats.downloaded, skipped=stats.skipped,
                       errors=stats.errors, duration_sec=stats.elapsed)
    return stats
```

## Step 8: Create **main**.py

> **Standards**: See [§2 CLI Standards](../../docs/how-to/backend/tool-development-standards.md#2-cli-standards) for the full required flag set (including `--match-collections`, `--resolve-intent`, `--min-stones`).

```python
"""CLI entry point for YourTool."""
import argparse, sys
from pathlib import Path
from tools.core.paths import get_tool_output_dir
from .orchestrator import download_puzzles, DownloadConfig

def main() -> int:
    parser = argparse.ArgumentParser(description="Download puzzles from YourTool")
    parser.add_argument("--max-puzzles", "-n", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--request-delay", type=float, default=1.0)
    parser.add_argument("--output-dir", "-o", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--no-log-file", action="store_true")
    # See Standards §2 for additional required flags
    args = parser.parse_args()

    config = DownloadConfig(
        output_dir=args.output_dir or get_tool_output_dir("your-tool"),
        max_puzzles=args.max_puzzles, batch_size=args.batch_size,
        request_delay=args.request_delay, resume=args.resume,
        verbose=args.verbose, dry_run=args.dry_run, log_to_file=not args.no_log_file,
    )
    try:
        stats = download_puzzles(config)
        return 0 if stats.errors == 0 else 1
    except KeyboardInterrupt:
        return 130

if __name__ == "__main__":
    sys.exit(main())
```

## Step 9: Create **init**.py

```python
"""YourTool downloader package."""
__version__ = "1.0.0"

from .client import YourToolClient
from .models import YourPuzzle, YourCategory
from .orchestrator import download_puzzles, DownloadConfig, DownloadStats
```

---

## Naming Conventions

| Type             | Format                           | Example                        |
| ---------------- | -------------------------------- | ------------------------------ |
| SGF files        | `{puzzle_id}.sgf`                | `abc123.sgf`                   |
| Log files        | `{YYYYMMDD-HHMMSS}-{tool}.jsonl` | `20260205-143022-ogs.jsonl`    |
| Checkpoint       | `.checkpoint.json`               | (hidden dotfile in output_dir) |
| Batch dirs       | `batch-{NNN}`                    | `batch-001`, `batch-002`       |
| Checkpoint class | `{Tool}Checkpoint`               | `OGSCheckpoint`                |
| Client class     | `{Tool}Client`                   | `OGSClient`                    |
| Logger class     | `StructuredLogger`               | (extend per tool)              |

## Anti-Patterns

- Don't duplicate `tools.core` code — always import
- Don't prefix files with tool name — you're already in the tool directory
- Don't skip `--dry-run` mode — always implement it
- Don't put timestamp at end of log filename — use timestamp-first for auto-sorting

## Testing Your Tool

```bash
# Minimal smoke test
python -m tools.your-tool --dry-run --no-log-file --max-puzzles 1
```

### Test Checklist

- [ ] `--dry-run` previews without downloading
- [ ] `--max-puzzles 1` limits to one puzzle
- [ ] Ctrl+C triggers graceful shutdown + checkpoint save
- [ ] Resume works (run twice with same args)
- [ ] Batch directories created correctly

> **See also**: `tools/core/README.md` — Testing Guidelines section for checkpoint isolation and directory safety.

## Reference: Core Module APIs

```python
# paths
from tools.core.paths import get_project_root, get_tool_output_dir, rel_path, to_posix_path

# batching
from tools.core.batching import get_batch_for_file, get_batch_for_file_fast, count_total_files, BatchInfo

# checkpoint
from tools.core.checkpoint import ToolCheckpoint, BatchTrackingMixin, load_checkpoint, save_checkpoint

# logging
from tools.core.logging import setup_logging, StructuredLogger, EventType, get_logger

# http
from tools.core.http import HttpClient, calculate_backoff_with_jitter

# rate_limit
from tools.core.rate_limit import RateLimiter, wait_with_jitter

# sgf
from tools.core.sgf_parser import parse_sgf, SgfNode, SgfTree, YenGoProperties
from tools.core.sgf_analysis import max_branch_depth, compute_solution_depth, get_all_paths
from tools.core.sgf_builder import SGFBuilder, publish_sgf
from tools.core.sgf_correctness import infer_correctness

# validation
from tools.core.validation import validate_sgf_puzzle, validate_sgf_puzzle_from_tree, PuzzleValidationConfig

# index
from tools.core.index import add_entry, sort_and_rewrite, load_ids
```

## Normative Standards Reference

All rules, conventions, and required patterns live in the authoritative document:

**[Tool Development Standards](../../docs/how-to/backend/tool-development-standards.md)**

| Section                        | Covers                                          |
| ------------------------------ | ----------------------------------------------- |
| §1 File Organization           | Required modules (13 files)                     |
| §2 CLI Standards               | Required flags, banner/summary patterns         |
| §3 Logging Standards           | Logger methods, rich progress format, JSONL     |
| §4 SGF Output Standards        | Whitelist rebuild, approved/excluded properties |
| §5 Quality Metrics (YQ)        | Don't set at ingest — enricher handles it       |
| §6 Collections (YL)            | Local config format, workflow, logging          |
| §7 Intent Resolution (C[])     | Static mapping, semantic fallback               |
| §8 Checkpoint & Resume         | `.checkpoint.json`, save frequency, SIGINT      |
| §9 Validation                  | Config-driven rules, CLI override               |
| §10 Rate Limiting              | Processing-aware delay (mandatory)              |
| §11 Index Standards            | `sgf-index.txt`, O(1) dedup                     |
| §12 Output Directory Structure | Canonical layout                                |
| §13 Shared Core Infrastructure | Required imports                                |
| §14 Counter Pattern            | `puzzle_save()` MUST receive stats              |
| §15 Architecture Boundary      | `tools/core` independent from `backend/`        |

_Last updated: 2026-02-24_
