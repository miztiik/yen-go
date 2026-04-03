# Pipeline Logging Architecture

Last Updated: 2026-02-28

## Design Principle: Two-Tier Logging

The pipeline uses a **two-tier** logging model:

| Tier               | Destination                    | Purpose              | Granularity            |
| ------------------ | ------------------------------ | -------------------- | ---------------------- |
| **Stage log file** | `.pm-runtime/logs/{stage}.log` | Detailed audit trail | Every puzzle processed |
| **Console**        | `stderr`                       | Dashboard / progress | Throttled summaries    |

**Stage log files** are the primary diagnostic tool. Every puzzle that enters a stage gets one INFO-level line recording what happened (ingested, analyzed, published, skipped, or failed) with structured extras (puzzle_id, source_file, level, tags, etc.).

**Console** shows only throttled progress ticks (every 100 puzzles) and stage start/complete summaries. Use `-v` for INFO-level console output, `-vv` for DEBUG.

## Log Level Policy

| Level       | Value | Usage                                                                   | Visible In                            |
| ----------- | ----- | ----------------------------------------------------------------------- | ------------------------------------- |
| **ERROR**   | 40    | Fatal failures (snapshot build, source-level exceptions)                | Console, stage file, main file        |
| **WARNING** | 30    | Recoverable problems (validation warnings, classification fallback)     | Console, stage file, main file        |
| **INFO**    | 20    | Stage start/complete summaries                                          | Console, stage file, main file        |
| **DETAIL**  | 15    | Per-puzzle outcomes (success, skip, fail)                               | Stage file only (NOT console)         |
| **DEBUG**   | 10    | Progress counters, property preservation decisions, batch state flushes | Main file only (`puzzle_manager.log`) |

The custom **DETAIL** level (15) sits between DEBUG and INFO. It's the key mechanism for keeping the console clean ("dashboard") while stage log files retain per-puzzle audit detail. Stage file handlers have their threshold set to DETAIL; console handlers stay at INFO.

### What Gets Logged at DETAIL (Per-Puzzle Detail)

Every puzzle that passes through a stage gets **exactly one DETAIL-level message** in the stage log file:

**Ingest stage** (`ingest.log`):

- `Ingested puzzle` — puzzle_id, source_file, output_file, original_filename
- `Skipped puzzle` — puzzle_id, source_id, reason (adapter-reported skip)
- `Failed puzzle` — puzzle_id, reason (no solution, missing content)
- `Parse error for {id}` — SGF parse failures with error detail

**Analyze stage** (`analyze.log`):

- `Analyzed puzzle` — puzzle_id, source_file, output_file, level, quality_level, tags, collections, hints_count, region, ko, move_order
- `Skipping already analyzed (v{N})` — puzzle_id (already at current schema version)
- `Parse error for {id}` — SGF parse failures
- `Tagging error for {id}` — Tag detection failures

**Publish stage** (`publish.log`):

- `Published puzzle` — puzzle_id, source_file, output_path, puzzle_level, quality, tags, collections
- `Skipping already-published SGF {hash}` — content-hash collision (file already exists)
- `Quality computed for {hash}` — quality fallback when YQ is missing
- `Error publishing {file}` — per-puzzle exceptions (at WARNING)

### What Stays at DEBUG

Progress counters, property preservation decisions ("Preserving source-provided YG"), batch state flush events, and per-batch progress tracking remain at DEBUG. These are useful for deep debugging but would be noise in the stage audit trail.

## Handler Configuration

Configured in `pm_logging.py`:

| Handler                            | Logger                         | Level                            | Format                 |
| ---------------------------------- | ------------------------------ | -------------------------------- | ---------------------- |
| Console (`StreamHandler`)          | `puzzle_manager`               | INFO (default), DEBUG with `-vv` | Colored human-readable |
| Main file (`FlushingFileHandler`)  | `puzzle_manager`               | DEBUG                            | Structured JSON        |
| Stage file (`FlushingFileHandler`) | `ingest`, `analyze`, `publish` | DETAIL (15)                      | Compact JSON           |

## Trace Logger

`create_trace_logger()` wraps the stage logger with automatic injection of `run_id`, `source_id`, and `trace_id` into all log records. This enables end-to-end correlation of a single puzzle across all three stages:

```
[ingest.log]  trace_id=abc123  Ingested puzzle  puzzle_id=foo
[analyze.log] trace_id=abc123  Analyzed puzzle  puzzle_id=foo  level=intermediate
[publish.log] trace_id=abc123  Published puzzle puzzle_id=YENGO-def456
```

## Reading Stage Logs

Stage log files use compact JSON format (one line per event). To find all skipped puzzles in a publish run:

```bash
# All skips in publish stage
grep "Skipping already-published" .pm-runtime/logs/publish.log

# All failures across all stages
grep -i "error\|failed" .pm-runtime/logs/*.log

# Trace a specific puzzle across stages
grep "abc123" .pm-runtime/logs/*.log
```

> **See also**:
>
> - [Architecture: Pipeline Stages](stages.md) — Stage design and data flow
> - [Architecture: Pipeline](pipeline.md) — Overall pipeline architecture
> - [How-To: CLI Reference](../../how-to/backend/cli-reference.md) — `-v` / `-vv` flags
