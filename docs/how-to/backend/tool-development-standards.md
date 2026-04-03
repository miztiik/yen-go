# Tool Development Standards

Normative standards for puzzle download tools in `tools/`. The OGS tool (`tools/ogs/`) is the reference implementation.

> **See also**: [TEMPLATE.md](../../../tools/core/TEMPLATE.md) — Quick-start scaffolding with copy-paste file stubs for creating a new tool. This document is the authority; the template is the skeleton.

_Last updated: 2026-03-29_

## 1. File Organization

Each tool lives in `tools/{tool-name}/` with these required modules:

| Module                            | Purpose                                                                        |
| --------------------------------- | ------------------------------------------------------------------------------ |
| `__main__.py`                     | CLI entry point with argparse                                                  |
| `orchestrator.py`                 | Core download loop with progress tracking                                      |
| `client.py`                       | HTTP client with rate limiting                                                 |
| `models.py`                       | Pydantic models or dataclasses for API responses                               |
| `_local_level_tag_mapping.py`     | Source-specific level/tag/category mappings                                    |
| `_local_level_mapping.json`       | Local rating/rank → YenGo level slug config                                    |
| `storage.py`                      | SGF whitelist rebuild and file saving                                          |
| `checkpoint.py`                   | Resume state persistence                                                       |
| `batching.py`                     | Re-exports from `tools.core.batching`                                          |
| `index.py`                        | Puzzle ID index management                                                     |
| `logging_config.py`               | Subclass of `CoreStructuredLogger`                                             |
| `config.py`                       | Centralized constants and path utilities                                       |
| `_local_collections_mapping.py`   | Local collection name -> YenGo slug mapping                                    |
| `_local_collections_mapping.json` | Local collections config file                                                  |
| `_local_tag_mapping.py`           | Local source tag → YenGo tag mapping loader                                    |
| `_local_tag_mapping.json`         | Local source tags → YenGo tag slug config                                      |
| `_local_intent_mapping.py`        | Local category/type -> puzzle intent mapping                                   |
| `_local_intent_mapping.json`      | Local intent derivation config (optional, for sources with structured signals) |
| `README.md`                       | Tool-level documentation (see Section 16)                                      |

## 2. CLI Standards

### Required Flags

```
--max-puzzles N       Maximum puzzles to download (int)
--batch-size N        Max files per batch directory (int, default 500 or 1000)
--puzzle-delay F      Delay between puzzle requests in seconds (float)
--resume              Resume from last checkpoint (store_true)
--dry-run             Show plan without downloading (store_true)
--output-dir PATH     Output directory (Path)
--no-log-file         Disable file logging (store_true)
-v / --verbose        Enable debug logging (store_true)
--match-collections   Enable YL[] collection matching (BooleanOptionalAction, default: True)
--resolve-intent      Enable C[] intent resolution (BooleanOptionalAction, default: True)
--intent-threshold F  Minimum confidence for intent match (float, default: 0.8)
--min-stones N        Minimum stones required on board (int, optional, overrides config default of 2)
```

### Console Banner (at start)

```python
print(f"\n{'='*60}")
print(f"{TOOL_NAME}")
print(f"{'='*60}")
print(f"Output directory: {to_relative_path(output_dir)}")
print(f"Max puzzles: {args.max_puzzles}")
print(f"Batch size: {args.batch_size}")
print(f"Resume: {args.resume}")
print(f"Dry run: {args.dry_run}")
print(f"{'='*60}\n")
```

### Console Summary (at end)

```python
print(f"\n{'='*60}")
print("Download Summary")
print(f"{'='*60}")
print(f"Downloaded: {stats.downloaded}")
print(f"Skipped: {stats.skipped}")
print(f"Errors: {stats.errors}")
print(f"Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
print(f"Rate: {stats.puzzles_per_minute():.1f} puzzles/min")
print(f"Collections assigned: {stats.collections_assigned}")
print(f"Intents resolved: {stats.intents_resolved}")
print(f"Output: {to_relative_path(output_dir)}")
print(f"{'='*60}")
```

## 3. Logging Standards

### Logger Setup

Subclass `CoreStructuredLogger` from `tools.core.logging`:

```python
from tools.core.logging import (
    setup_logging as core_setup_logging,
    StructuredLogger as CoreStructuredLogger,
    EventType,
)

class StructuredLogger(CoreStructuredLogger):
    """Tool-specific structured logger."""

    def puzzle_fetch(self, puzzle_id: int | str, url: str) -> None:
        """Log puzzle fetch at INFO with URL."""
        self.event(EventType.ITEM_FETCH, f"GET {puzzle_id}", puzzle_id=puzzle_id, url=url)

    def puzzle_save(self, puzzle_id: int | str, path: str,
                    downloaded: int = 0, skipped: int = 0, errors: int = 0) -> None:
        """Log puzzle saved with running totals."""
        self.item_save(item_id=str(puzzle_id), path=path,
                       downloaded=downloaded, skipped=skipped, errors=errors)

    def puzzle_skip(self, puzzle_id: int | str, reason: str) -> None:
        self.item_skip(item_id=str(puzzle_id), reason=reason)

    def puzzle_error(self, puzzle_id: int | str, error: str) -> bool:
        return self.item_error(item_id=str(puzzle_id), error=error)

    def puzzle_enrich(
        self,
        puzzle_id: int | str,
        level: str,
        tags: list[str],
        collections: list[str] | None = None,
        intent: str | None = None,
    ) -> None:
        """Log puzzle enrichment with YG/YT/YL/intent."""
        self.event(
            "puzzle_enrich",
            f"ENRICH {puzzle_id} level={level} tags={tags} coll={collections or []} intent={intent or ''}",
            puzzle_id=puzzle_id,
            level=level,
            tags=tags,
            collections=collections or [],
            intent=intent or "",
        )

    def collection_match(
        self,
        puzzle_id: int | str,
        source_name: str,
        matched_slug: str | None,
    ) -> None:
        """Log collection resolution result (YL)."""
        status = "matched" if matched_slug else "no_match"
        self.event(
            "collection_match",
            f"COLLECTION {puzzle_id} '{source_name}' -> {matched_slug or 'NONE'}",
            puzzle_id=puzzle_id,
            source_name=source_name,
            matched_slug=matched_slug,
            status=status,
        )

    def intent_match(
        self,
        puzzle_id: int | str,
        description_snippet: str,
        matched_slug: str | None,
        confidence: float = 0.0,
        tier: str = "",
    ) -> None:
        """Log intent resolution result (C[])."""
        status = "matched" if matched_slug else "no_match"
        self.event(
            "intent_match",
            f"INTENT {puzzle_id} '{description_snippet[:30]}...' -> {matched_slug or 'NONE'} (conf={confidence:.2f}, tier={tier})",
            puzzle_id=puzzle_id,
            description_snippet=description_snippet[:50],
            matched_slug=matched_slug,
            confidence=confidence,
            tier=tier,
            status=status,
        )
```

### Logging Rules

- **URL at INFO**: Every HTTP request URL must be logged at INFO level (not DEBUG).
- **Relative paths**: Use `tools.core.paths.rel_path()` for ALL path logging. Produces project-root-relative POSIX paths.
- **Progress with timing**: Progress messages must include downloaded count, skipped, errors, elapsed time, and rate.
- **Progress interval**: Log progress every **10 puzzles** (default; configurable).
- **Rate field**: Include `rate` (puzzles per minute) in progress output.
- **Rich two-line progress format (REQUIRED)**: Every progress log must produce a two-line output on the console. The first line is the `SAVE` line (from `puzzle_save()`). The second line is the rich progress summary. Pass `on_disk` and `max_target` to `logger.progress()` to activate the rich format:

```
22:56:41 [INFO ] SAVE 12489 -> 12489.sgf [saved=9998 skip=2073 err=195]
22:56:41 [INFO ]   [9998/10000] saved | 9998 on disk | 1h33m elapsed | ~106.7 puzzles/min
```

Call pattern:

```python
logger.progress(
    downloaded=stats.downloaded,
    skipped=stats.skipped,
    errors=stats.errors,
    rate=stats.puzzles_per_minute(),
    elapsed_sec=elapsed,
    on_disk=len(known_ids),        # REQUIRED: total puzzles on disk
    max_target=config.max_puzzles,  # REQUIRED: download session target
)
```

**JSONL output is unaffected** — the structured JSON event always contains the full field set (`downloaded`, `skipped`, `errors`, `on_disk`, `max_target`, `rate`, `elapsed_sec`). Only the console message format changes.

- **Enrichment logging**: Log `puzzle_enrich` after assigning YG/YT/YL/intent.
- **Collection resolution logging**: Log `collection_match` when resolving source names to YL slugs.
- **Intent resolution logging**: Log `intent_match` when resolving descriptions to C[] objective slugs.
- **Log files**: JSON lines in `{output_dir}/logs/` with format `{YYYYMMDD-HHMMSS}-{tool}.jsonl`.

## 4. SGF Output Standards

### Whitelist-Only Rebuild

Parse source SGF, rebuild from scratch with only approved properties:

```python
from tools.core.sgf_parser import parse_sgf
from tools.core.sgf_builder import SGFBuilder

def rebuild_sgf(sgf_text, level_slug, tags, source_id, **kwargs):
    tree = parse_sgf(sgf_text)
    builder = SGFBuilder.from_tree(tree)
    # from_tree() preserves: board_size, stones, player_to_move, solution tree
    # from_tree() strips: AP, RU, KM, PW, PB, DT, ST, GN, PC, EV, SO, etc.

    if level_slug:
        builder.set_level_slug(level_slug)
    if tags:
        for tag in tags:
            builder.add_tag(tag)
    builder.yengo_props.source = source_id
    # ... set YL, C[], YQ as needed
    return builder.build()
```

### Approved Root Properties

| Property          | Source         | Notes  |
| ----------------- | -------------- | ------ |
| `FF[4]`           | SGF header     | Always |
| `GM[1]`           | SGF header     | Always |
| `CA[UTF-8]`       | SGF header     | Always |
| `SZ[N]`           | Board size     | Always |
| `PL[B/W]`         | Player to move | Always |
| `AB[...] AW[...]` | Initial stones | Always |

### Optional YenGo Properties (at download time)

| Property        | Description                                        | Example            |
| --------------- | -------------------------------------------------- | ------------------ |
| `YG[slug]`      | Level from `config/puzzle-levels.json`             | `YG[intermediate]` |
| `YT[tag1,tag2]` | Tags sorted, deduplicated, from `config/tags.json` | `YT[ko,ladder]`    |
| `YS[id]`        | Source adapter ID                                  | `YS[td]`, `YS[th]` |
| `YL[slug1,slug2]` | Collections, sorted, comma-separated | `YL[cho-chikun-elementary]` |
| `C[text]`         | Root comment for puzzle objective    | `C[black-to-kill]`          |

### Minimal-Edit Exception (Pre-Ingest Annotation Tools)

Pre-ingest annotation tools (such as `tools/core/collection_embedder.py`) may use a **minimal-edit approach**: parse the SGF, add only the specific target property (e.g., `YL`), and write back via round-trip mode. This avoids stripping source metadata that the pipeline will later process. The pipeline's whitelist-rebuild at ingest is the enforcement point — it will strip any non-approved properties regardless of what the annotation tool preserved.

### Explicitly Excluded (stripped by whitelist rebuild)

`GN[]`, `PC[]`, `EV[]`, `SO[]`, `AP[]`, `RU[]`, `KM[]`, `DT[]`, `PW[]`, `PB[]`, `ST[]`, and any other non-whitelisted property.

### Move Comments

`C[...]` on solution move nodes: **PRESERVED** from source (e.g., `C[Correct]`, `C[+]`, `C[Wrong]`).

## 5. Quality Metrics Standard (YQ)

YQ is computed by the pipeline enricher (`analyze` stage), not by download tools. The canonical format is:

```
YQ[q:{level};rc:{refutation_count};hc:{comment_level}]
```

| Field | Meaning          | Values                                 |
| ----- | ---------------- | -------------------------------------- |
| `q`   | Quality level    | 1-5 (1=unverified, 5=premium)          |
| `rc`  | Refutation count | 0+ (wrong-move branches)               |
| `hc`  | Comment level    | 0 (none), 1 (markers), or 2 (teaching) |

Download tools should **not** set YQ at ingest. The enricher preserves existing YQ values (does not overwrite), so any value set at download time will persist through the pipeline unchanged. The enricher only computes YQ when the property is absent.

See `docs/concepts/quality.md` for the three-layer correctness inference system and quality level criteria.

## 6. Collections Standard (YL)

### Local Collections Config

Each tool maintains a local JSON mapping source names to YenGo slugs in `_local_collections_mapping.json`:

```json
{
  "version": "1.0.0",
  "source": "t-dragon",
  "mappings": {
    "ladder": "ladder-problems",
    "snapback": "snapback-problems",
    "capture-race": "capturing-race"
  }
}
```

### Workflow

1. Local config maps source names/categories to YenGo collection slugs
2. Slugs must exist in global `config/collections.json`
3. `tools/collections_align.py` validates alignment
4. `--match-collections` flag (default: enabled)
5. YL[] values: sorted, deduplicated, comma-separated

### Collection Logging

Always call `logger.collection_match()` after resolving collection slugs:

```python
# After collection resolution
slug = resolve_collection_slug(source_category)
logger.collection_match(
    puzzle_id=puzzle.id,
    source_name=source_category,
    matched_slug=slug,  # None if no match
)
```

## 7. Intent Resolution Standard (C[])

- `--resolve-intent` flag with `--intent-threshold` (default: 0.8)
- Sources **with description text**: use `tools.puzzle_intent.resolve_intent(description)` with semantic fallback
- Sources **without description**: use static category/type -> intent mapping in `_local_intent_mapping.py`
- Write as root `C[objective-slug]` property

Example static mapping in `_local_intent_mapping.py` (T-Dragon):

```python
CATEGORY_TO_INTENT = {
    "capture": "Black to capture",
    "making-eyes": "Black to make eyes and live",
    "taking-eyes": "Black to destroy eyes and kill",
    "connecting": "Black to connect",
    "disconnect": "Black to cut",
}
```

### Intent Logging

Always call `logger.intent_match()` after resolving puzzle intent:

```python
# After intent resolution
slug = resolve_intent(description)
logger.intent_match(
    puzzle_id=puzzle.id,
    description_snippet=description,
    matched_slug=slug,
    confidence=result.confidence,
    tier=result.match_tier,
)
```

## 8. Checkpoint and Resume Standards

- Checkpoint file: `{output_dir}/.checkpoint.json` (hidden dotfile)
- Use `tools.core.checkpoint.BatchTrackingMixin` for O(1) batch placement
- Save after EVERY successful file save
- `--resume` loads checkpoint and continues from last position
- SIGINT graceful exit: catch signal, save checkpoint, exit cleanly
- Tracked state: downloaded, skipped, errors, position-specific fields

## 9. Validation Standards

### Centralized Configuration (v2.0)

Validation rules are config-driven via `config/puzzle-validation.json` (schema version 2.0):

| Field                 | Type | Default | Description                             |
| --------------------- | ---- | ------- | --------------------------------------- |
| `min_board_dimension` | int  | 5       | Minimum board width/height              |
| `max_board_dimension` | int  | 19      | Maximum board width/height              |
| `min_stones`          | int  | 2       | Minimum stones on board (black + white) |
| `min_solution_depth`  | int  | 1       | Minimum solution tree depth (moves)     |
| `max_solution_depth`  | int  | 30      | Maximum solution tree depth             |

### Design Decisions (v2.0 Consolidation)

1. **`min_solution_depth` replaces `require_solution`**: A single integer range `[min_solution_depth, max_solution_depth]` expresses both "solution must exist" (depth >= 1) and "solution not too deep" (depth <= 30). `min_solution_depth=0` allows puzzles without solutions (OGS use case). This eliminates the boolean `require_solution` flag.

2. **`min_stones` replaces `require_initial_stones`**: An integer count is strictly more informative than a boolean presence check. `min_stones=2` is the Go-valid minimum (attacker + defender). Count also enables future quality filters (e.g., "reject trivially simple puzzles with < 5 stones").

3. **Two validation tiers**:
   - **Pre-ingest structural** (`tools/core/validation.py`): Board size range, stone count, solution depth — executed at download time before SGF enrichment.
   - **Post-ingest schema** (`backend/puzzle_manager/core/puzzle_validator.py`): Same rules plus adapter-specific overrides — executed by pipeline adapters.

4. **CLI override**: `--min-stones N` overrides the config default at download time. Uses `DownloadConfig.validation_config` property which builds a merged `PuzzleValidationConfig` from `DEFAULT_CONFIG.merge({"min_stones": N})`.

### Usage

- Use `tools.core.validation.validate_sgf_puzzle()` for raw SGF validation
- Use `tools.core.validation.validate_sgf_puzzle(sgf, config=custom_config)` for CLI overrides
- Validate BEFORE enrichment and save (fail early)
- Log skips via `logger.puzzle_skip(id, reason)`
- Validation failures are **skips**, not errors
- Backward compatibility: both validators accept v1.0 config fields (`require_solution`, `require_initial_stones`) via `from_dict()`

## 10. Rate Limiting Standards

- Configurable delays via CLI flags or config defaults
- Apply jitter to avoid thundering herd (typically +/-20-40%)
- Exponential backoff for 429/5xx responses
- Log wait times via `logger.api_wait(delay, reason)`

### Processing-Aware Rate Limiting (Required)

**The delay must subtract time already spent fetching and converting.** A flat `time.sleep(delay)` adds the full delay _on top of_ processing time, causing inter-request gaps to grow unboundedly under slow responses.

**Incorrect pattern — flat sleep:**

```python
result = fetch_and_convert(puzzle_id)   # takes 2s
time.sleep(8)                           # total gap = 10s (not 8s)
```

**Required pattern — elapsed-aware sleep:**

```python
t_start = time.monotonic()
result = fetch_and_convert(puzzle_id)   # takes 2s
apply_rate_limit(elapsed=time.monotonic() - t_start)
```

**Reference implementation:**

```python
import time
import random

def apply_rate_limit(
    elapsed: float = 0.0,
    min_seconds: float = 5.0,
    max_seconds: float = 10.0,
    jitter_seconds: float = 5.0,
) -> None:
    """Sleep for the remaining portion of the target inter-request window.

    Args:
        elapsed:        Seconds already spent on the current request cycle
                        (fetch + parse + convert). Subtracted from the target
                        delay so the total gap between request starts stays
                        within the configured window.
        min_seconds:    Minimum target inter-request delay.
        max_seconds:    Maximum target inter-request delay (before jitter).
        jitter_seconds: Maximum random jitter added to the base delay.
    """
    target = random.uniform(min_seconds, max_seconds)
    target += random.uniform(0, jitter_seconds)
    remaining = max(0.0, target - elapsed)

    logger.debug(
        f"Rate limit: target={target:.2f}s, elapsed={elapsed:.2f}s, "
        f"waiting={remaining:.2f}s"
    )
    if remaining > 0:
        time.sleep(remaining)
```

**Calling pattern in fetch loops:**

```python
# By ID list
for puzzle_id in puzzle_ids:
    t_start = time.monotonic()
    result = fetch_and_convert(puzzle_id)
    yield result
    apply_rate_limit(elapsed=time.monotonic() - t_start)

# By ID range (skip delay after last item)
for puzzle_id in range(start_id, end_id + 1):
    t_start = time.monotonic()
    result = fetch_and_convert(puzzle_id)
    yield result
    if puzzle_id < end_id:
        apply_rate_limit(elapsed=time.monotonic() - t_start)
```

**Key properties of this approach:**

| Scenario                          | Flat sleep | Elapsed-aware sleep      |
| --------------------------------- | ---------- | ------------------------ |
| Fast fetch (0.5s) + 8s target     | 8.5s gap   | 8s gap ✓                 |
| Slow fetch (6s) + 8s target       | 14s gap    | 2s gap ✓                 |
| Very slow fetch (10s) + 8s target | 18s gap    | 0s gap ✓ (no extra wait) |

If processing already exceeds the target window, `remaining` clamps to `0.0` and no additional sleep is added — the loop proceeds immediately without compounding the delay.

## 11. Index Standards

- `sgf-index.txt` in output directory, one entry per line: `batch-NNN/filename.sgf`
- `add_to_index()` after each file save for O(1) duplicate detection
- `rebuild_index()` when file count > index count (stale detection)
- `sort_index()` after download completes, sorts numerically by puzzle ID
- `load_puzzle_ids()` returns `set` for O(1) dedup lookup

## 12. Output Directory Structure

```
external-sources/{source}/
+-- sgf/
|   +-- batch-001/
|   |   +-- {id}.sgf
|   +-- batch-002/
|   +-- ...
+-- logs/
|   +-- {YYYYMMDD-HHMMSS}-{tool}.jsonl
+-- sgf-index.txt
+-- .checkpoint.json
```

## 13. Shared Core Infrastructure

All tools MUST use these modules (never re-implement):

| Module                   | Key Exports                                                                |
| ------------------------ | -------------------------------------------------------------------------- |
| `tools.core.logging`     | `StructuredLogger`, `EventType`, `setup_logging()`                         |
| `tools.core.paths`       | `rel_path()`, `get_project_root()`, `to_posix_path()`                      |
| `tools.core.batching`    | `get_batch_for_file()`, `get_batch_for_file_fast()`, `count_total_files()` |
| `tools.core.checkpoint`  | `BatchTrackingMixin`                                                       |
| `tools.core.index`       | `add_entry()`, `sort_and_rewrite()`, `load_ids()`                          |
| `tools.core.validation`  | `validate_sgf_puzzle()`                                                    |
| `tools.core.sgf_parser`  | `parse_sgf()`, `SgfTree`, `SgfNode`                                        |
| `tools.core.sgf_builder` | `SGFBuilder`, `publish_sgf()`                                              |
| `tools.core.rate_limit`  | `RateLimiter`, `wait_with_jitter()`                                        |

## 14. Counter Pattern (MANDATORY)

The `puzzle_save()` / `item_save()` log line includes `[saved=N skip=N err=N]` counters
that are written to both console and JSONL log. **You MUST pass the stats values from
the main download loop.** Omitting them causes all counters to show zero.

**Correct pattern** (from OGS and Tsumego Hero):

```python
# In the main download loop — NOT in _process_puzzle()
if result_key == "downloaded":
    stats.downloaded += 1

    logger.puzzle_save(
        puzzle_id=puzzle_id,
        path=file_path.name,
        downloaded=stats.downloaded,  # ← REQUIRED
        skipped=stats.skipped,        # ← REQUIRED
        errors=stats.errors,          # ← REQUIRED
    )
```

**Why this matters:**

- `_process_puzzle()` is a single-item function — it has no access to aggregate stats
- The JSONL log is used for post-run analysis (e.g., `analyze_logs.py`)
- Zero counters make it impossible to track progress from log files

**Anti-pattern (DO NOT DO THIS):**

```python
# ❌ WRONG — calling puzzle_save inside _process_puzzle without stats
def _process_puzzle(...) -> str:
    ...
    logger.puzzle_save(puzzle_id=puzzle_id, path=file_path.name)  # counters default to 0!
    return "downloaded"
```

## 15. Architecture Boundary

`tools/core/` modules are fully standalone — **zero imports from `backend/`**.

| Codebase   | Responsibility                                   |
| ---------- | ------------------------------------------------ |
| `tools/`   | External source ingestors (download from web)    |
| `backend/` | Pipeline processing (ingest → analyze → publish) |

`tools/core/sgf_*.py` mirror `backend/puzzle_manager/core/sgf_*.py` but are independent copies. If `tools.core` is missing functionality that exists in `backend.puzzle_manager.core`, **copy** the implementation — do not import across the boundary.

This ensures:

- Tools can be used standalone without backend dependencies
- Clear separation of concerns
- Independent testing and versioning

## 16. Tool README Standard

Every tool MUST have a `README.md` in its directory (`tools/{tool-name}/README.md`). The OGS tool (`tools/ogs/README.md`) is the reference implementation.

### Required Sections

| Section                     | Content                                                                    |
| --------------------------- | -------------------------------------------------------------------------- |
| **Title + Description**     | One-line summary of what the tool does and links to the source             |
| **Features**                | Bullet list of key capabilities                                            |
| **Usage**                   | CLI examples (download, resume, dry-run, type filtering)                   |
| **Configuration**           | Table of all CLI flags with defaults and descriptions                      |
| **Output Structure**        | Tree diagram of output directory layout                                    |
| **API/Data Format**         | Source API endpoints, data format details, any proprietary encoding        |
| **SGF Output**              | Table mapping source fields → SGF properties, included/excluded properties |
| **Level Mapping**           | Rating/rank → YenGo level table with Go rank equivalents                   |
| **Tag Mapping**             | Source tags → YenGo tags table with coverage stats                         |
| **Collection Mapping (YL)** | Source categories → YenGo collection slugs                                 |
| **Intent Resolution (C[])** | How puzzle objectives are derived                                          |
| **Quality (YQ)**            | Explanation that YQ is pipeline-computed, signal preservation table        |
| **Module Architecture**     | File tree with one-line descriptions of each module                        |
| **Dependencies**            | Required and optional packages                                             |
| **Known Limitations**       | Documented gaps, unmapped values, API quirks                               |
| **See Also**                | Cross-references to tool-development-standards, other READMEs              |

### Optional Sections (when applicable)

| Section                           | When to Include                                               |
| --------------------------------- | ------------------------------------------------------------- |
| **Research & Verification**       | Tool required reverse-engineering or format analysis          |
| **Go Engine / Custom Components** | Tool includes non-standard components (e.g., legality engine) |
| **Log Analysis**                  | Tool has a companion log analysis script                      |
| **Bootstrap / Setup Scripts**     | Tool has one-time setup or data generation scripts            |

### Content Rules

1. **Last Updated date** — Required at top, update with any README change
2. **CLI examples first** — Users need to know how to run it before understanding internals
3. **Source-specific details** — Document anything unique about the source (encoding, API quirks, rate limits)
4. **Mapping coverage stats** — Report exact numbers (e.g., "69/99 mapped (70%)")
5. **Known limitations** — Be explicit about gaps; don't hide unmapped values or API issues
6. **Cross-references** — Link to tool-development-standards and other tool READMEs

## 17. Atomicity and Progress Tracking (MANDATORY)

### Per-File Atomicity

Every download tool MUST persist state **after each successful file save**. If the process is interrupted (SIGINT, crash, power loss), the tool must be able to resume without re-downloading already-saved files.

**Required sequence per puzzle:**

```
1. Fetch puzzle data from source
2. Parse, validate, and enrich SGF
3. Write SGF file to disk (atomic write)
4. Update running counters (downloaded, skipped, errors)
5. Save checkpoint to {output_dir}/.checkpoint.json  ← MANDATORY after every file
```

**Reference implementation** (from OGS `orchestrator.py`):

```python
# Step 3: Save puzzle file
file_path, batch_num = save_puzzle(puzzle, config.output_dir, config.batch_size, ...)

# Step 4: Update counters
stats.downloaded += 1
total_downloaded = global_stats.downloaded + stats.downloaded
total_skipped = global_stats.skipped + stats.skipped
total_errors = global_stats.errors + stats.errors

# Step 5a: Log with running totals
logger.puzzle_save(
    puzzle_id=puzzle_id,
    path=file_path.name,
    downloaded=total_downloaded,
    skipped=total_skipped,
    errors=total_errors,
)

# Step 5b: Update and persist checkpoint
checkpoint.record_success(config.batch_size)
checkpoint.puzzle_index_in_page = idx
checkpoint.last_puzzle_id = puzzle_id
save_checkpoint(checkpoint, config.output_dir)  # ← PERSISTED PER FILE
```

### Progress Counters

All progress logging MUST include **running totals** that show `M of N` style progress. This enables users to see exactly where a download stands and estimate remaining time.

**Required fields in every `puzzle_save()` call:**

| Field | Description | Example |
|-------|-------------|---------|
| `downloaded` | Total puzzles saved so far | `42` |
| `skipped` | Total puzzles skipped (dupes, validation) | `3` |
| `errors` | Total puzzle errors encountered | `1` |

**Console output shows:**

```
22:56:41 [INFO ] SAVE 12489 -> 12489.sgf [saved=42 skip=3 err=1]
22:56:41 [INFO ]   [42/500] saved | 42 on disk | 2m13s elapsed | ~18.9 puzzles/min
```

### Graceful Shutdown

All tools MUST handle SIGINT (Ctrl+C) gracefully:

```python
import signal

def signal_handler(signum, frame):
    logger.info("Interrupted — saving checkpoint...")
    save_checkpoint(checkpoint, config.output_dir)
    logger.info(f"Checkpoint saved. Resume with --resume. Downloaded: {stats.downloaded}")
    sys.exit(130)

signal.signal(signal.SIGINT, signal_handler)
```

### Anti-Patterns

- ❌ Saving checkpoint only at end of batch/page (loses progress on interrupt)
- ❌ Calling `puzzle_save()` without passing counter values (shows zeros in logs)
- ❌ Updating counters inside `_process_puzzle()` instead of the main loop
- ❌ No SIGINT handler (checkpoint lost on Ctrl+C)

## 18. Path Standards (MANDATORY)

### Relative Paths Only

All path output in **console**, **logs**, and **README examples** MUST use project-root-relative POSIX paths. Never log absolute paths.

**Use `tools.core.paths.rel_path()`** for all path formatting:

```python
from tools.core.paths import rel_path

# ✅ CORRECT: Relative POSIX path
logger.info(f"Output: {rel_path(output_dir)}")
# → Output: external-sources/ogs/sgf/batch-001/12345.sgf

# ❌ WRONG: Absolute path
logger.info(f"Output: {output_dir}")
# → Output: C:\Users\dev\yen-go\external-sources\ogs\sgf\batch-001\12345.sgf
```

### Console Banner Paths

The startup banner (§2) MUST display relative paths:

```python
from tools.core.paths import rel_path

print(f"Output directory: {rel_path(output_dir)}")
# → Output directory: external-sources/ogs
```

### Path Configuration Rules

All tools MUST derive paths relative to project root. **Hardcoded absolute paths are forbidden.**

```python
from tools.core.paths import get_project_root

PROJECT_ROOT = get_project_root()

# ✅ CORRECT: Derived from project root
OUTPUT_DIR = PROJECT_ROOT / "external-sources" / "my-tool"

# ❌ WRONG: Relative to script location
OUTPUT_DIR = Path(__file__).parent / "downloads"

# ❌ WRONG: Hardcoded absolute path
OUTPUT_DIR = Path("C:/Users/dev/yen-go/external-sources/my-tool")
```

### Output Directory Layout

All tool output MUST go under `external-sources/{tool-name}/`. This is the **single source of truth** for tool output location.

| Artifact | Location | Notes |
|----------|----------|-------|
| SGF files | `external-sources/{tool}/sgf/batch-NNN/` | Standard batch layout |
| Logs | `external-sources/{tool}/logs/` | JSONL structured logs |
| Checkpoint | `external-sources/{tool}/.checkpoint.json` | Hidden dotfile |
| Index | `external-sources/{tool}/sgf-index.txt` | Puzzle ID index |

**Explicitly forbidden locations for output/logs/state:**

- ❌ `tools/{tool}/downloads/` — tool directory is for code, not data
- ❌ `tools/{tool}/logs/` — logs belong with the output
- ❌ `tools/{tool}/state.json` — state belongs with the output
- ❌ `logs/tools/{tool}/` — centralized log directory is deprecated

### Deprecated: Centralized Logging

The `get_centralized_log_dir()` function (which reads `config/logging.json` and writes to `logs/tools/{tool}/`) is **DEPRECATED**. All tools MUST use `{output_dir}/logs/` instead. This co-locates logs with their associated data for easier debugging and cleanup.
