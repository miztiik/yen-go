> ⚠️ **ARCHIVED** — This document describes the original 11-stage pipeline design (v3.0/v3.1)
> which was simplified to the current 3-stage model (ingest → analyze → publish) in v3.2.
> Kept for historical reference only.

---

# Pipeline v3.0 Design (11-Stage Model)

## What Was Tried

The original pipeline design (specs 002 + 003) proposed an 11-stage sequential pipeline:

1. Fetch — Download SGF from sources
2. Parse — Parse SGF strings
3. Validate — Structural validation
4. Deduplicate — D8 content hashing to detect duplicates
5. Classify — Assign difficulty levels
6. Tag — Detect techniques (ko, ladder, etc.)
7. Enrich — Generate hints, quality metrics
8. Solve — KataGo/smargo validation
9. Serialize — Write enriched SGF
10. Index — Build view indexes
11. Publish — Write final output

Each stage was a separate class with its own configuration, and the `PipelineOrchestrator` managed stage initialization and data flow between them.

## Why It Was Simplified

- **Over-segmented**: Most stages were 20–50 lines of code. The overhead of stage configuration, inter-stage data contracts, and orchestration exceeded the actual logic.
- **Deduplication unnecessary**: Curated sources (Cho Chikun, Gokyo Shumyo, OGS collections) don't have duplicates. The D8 hashing was solving a problem that didn't exist.
- **Solve stage removed**: KataGo/smargo validation was abandoned (see [ai-puzzle-validation.md](./ai-puzzle-validation.md)) because sources are pre-validated.
- **Orchestrator brittle**: Stage constructors expected `PipelineConfig + StateManager` but the orchestrator passed `StageConfig`, causing runtime initialization failures (spec 003).

## What Replaced It

The current 3-stage pipeline (`backend/puzzle_manager/`) groups the 11 stages into 3 logical phases:

| Current Stage                       | Replaces (v3.0) |
| ----------------------------------- | --------------- |
| `ingest` (fetch → parse → validate) | Stages 1–3      |
| `analyze` (classify → tag → enrich) | Stages 4–8      |
| `publish` (index → daily → output)  | Stages 9–11     |

This model is implemented in `backend/puzzle_manager/cli.py` via the `run` command with `--stage` flags.

## Lesson

Prefer fewer, larger stages with clear boundaries over many granular stages. The orchestration overhead should never exceed the logic being orchestrated.
