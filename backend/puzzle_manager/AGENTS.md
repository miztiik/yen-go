# backend/puzzle_manager — Agent Architecture Map

> Agent-facing reference. NOT user documentation. Dense structural facts only.
> _Last updated: 2026-03-24 | Trigger: dead code cleanup — fixed CLI framework ref to argparse, removed url/ adapter, removed dead module references_

---

## 0. Quick Test Commands (run from repository root)

| Command | Tests | Time | When to Use |
|---------|-------|------|-------------|
| `pytest backend/ -m unit -q --no-header --tb=short` | ~365 | ~4s | **Fastest** — after any change |
| `pytest backend/ -m "not (cli or slow)" -q --no-header --tb=no` | ~1,600 | ~30s | Quick validation |
| `pytest backend/ -m adapter -q --no-header --tb=no` | ~160 | ~10s | Adapter work only |
| `pytest backend/ -q --no-header --tb=no` | ~2,000 | ~60s | Full backend suite |

> Always run from **repository root** (not `cd backend/puzzle_manager`). Root `pytest.ini` is authoritative — no need to navigate into subdirectory. Running from `backend/puzzle_manager/` still works but misses cross-module marker registration.

---

## 1. Directory Structure

| Path | Purpose |
|------|---------|
| `__main__.py` | `python -m backend.puzzle_manager` entry; delegates to `cli.py` |
| `cli.py` | 13-command argparse CLI: `run`, `status`, `sources`, `daily`, `clean`, `validate`, `publish-log`, `rollback`, `vacuum-db`, `inventory` |
| `pm_logging.py` | `setup_logging()`, `create_trace_logger()` — structured JSON logs |
| `paths.py` | `get_output_dir()`, `get_pm_staging_dir()`, `get_pm_state_dir()`, etc. — all path resolution |
| `exceptions.py` | `PuzzleManagerError`, `SGFParseError`, `AdapterNotFoundError`, `ValidationError` |
| `publish_log.py` | `PublishLogWriter` / `PublishLogReader` — JSONL append log for rollback |
| `rollback.py` | `RollbackManager` — remove runs/puzzles from yengo-content.db, rebuild yengo-search.db |
| `audit.py` | `write_audit_entry()` — append-only audit trail |
| `core/sgf_builder.py` | `SGFBuilder` — construct SGF from primitives with YenGo properties |
| `core/sgf_parser.py` | `parse_sgf()` → `SGFGame` + `SolutionNode` tree + `YenGoProperties` |
| `core/sgf_publisher.py` | `publish_sgf()` — serialize `SGFGame` back to string |
| `core/sgf_utils.py` | `escape_sgf_value()` + SGF string utilities |
| `core/sgf_validator.py` | `SGFValidator` — pre-publish validation (required properties) |
| `core/katrain_sgf_parser.py` | KaTrain-MIT SGF parser (internal parser; wrapped by `sgf_parser.py`) |
| `core/board.py` | `Board` — stone placement, liberty counting, ko detection |
| `core/primitives.py` | `Color (B/W)`, `Point`, `Move` — lowest-level types |
| `core/coordinates.py` | `sgf_to_point()` / `point_to_sgf()` — coordinate conversion |
| `core/classifier.py` | `classify_difficulty()` heuristic → level 1-9 |
| `core/correctness.py` | 3-layer correctness inference (markers→comments→structure); `mark_sibling_refutations(root)` fixes unmarked wrong siblings; `_has_correctness_signal(node)` helper |
| `core/tagger.py` | `detect_techniques()` — confidence-based tag detection from SGF |
| `core/enrichment/` | 8-file enrichment subsystem: hints, region, ko, move_order, refutation, solution_tagger |
| `core/enrichment/__init__.py` | `enrich_puzzle(game: SGFGame, config) -> EnrichmentResult` — main enrichment entry |
| `core/enrichment/hints.py` | `HintGenerator` — 3-tier pedagogical hints from solution tree + board region |
| `core/enrichment/region.py` | `detect_region(board) -> str` — TL/TR/BR/BL/C/E corner detection |
| `core/enrichment/ko.py` | `classify_ko_context(game) -> str` — none/direct/approach |
| `core/enrichment/move_order.py` | `detect_move_order(game) -> str` — strict/flexible/miai |
| `core/enrichment/refutation.py` | `extract_refutations(game) -> list[str]` — wrong-move SGF coords |
| `core/enrichment/solution_tagger.py` | Tag correct/wrong move comments in solution tree |
| `core/quality.py` | `QualityMetrics` — compute/parse quality fields (`q`, `rc`, `hc`, `ac`); config-driven thresholds from `config/puzzle-quality.json` (fail-fast) |
| `core/complexity.py` | `ComplexityMetrics` — depth, refutations, solution_len, unique_responses |
| `core/content_classifier.py` | `classify_content_type()` → config-driven (IDs from `config/content-types.json`); `get_content_type_id(name)` |
| `core/puzzle_validator.py` | `PuzzleValidator` — centralized validation; config-driven from `config/puzzle-validation.json` (fail-fast); supports v1→v2 field migration |
| `core/naming.py` | `generate_content_hash(content: str) -> str` — SHA256[:16] hex |
| `core/trace_utils.py` | `generate_trace_id()`, `parse_pipeline_meta()` — observability |
| `core/http.py` | `HttpClient` — SSRF-protected HTTP with retry, rate-limit, backoff |
| `core/schema.py` | `get_yengo_sgf_version() -> int` — reads from `config/schemas/` |
| `core/id_maps.py` | `IdMaps` — numeric ID ↔ slug resolution (tags, levels, collections) |
| `core/db_builder.py` | `build_search_db()` — builds `yengo-search.db` |
| `core/content_db.py` | `build_content_db()` — builds `yengo-content.db`; `_extract_collection_slug()` parses YL[]; `_ensure_collection_slug_column()` migration |
| `core/edition_detection.py` | `create_editions(entries, collections, db_path)` — detect multi-source collections, create edition sub-collections; called by publish + rollback |
| `core/db_models.py` | `PuzzleEntry` (has `source: str`), `CollectionMeta`, `DbVersionInfo` dataclasses |
| `core/batch_writer.py` | `BatchWriter` — sharded SGF output (sgf/{batch}/) with ≤100 files/dir |
| `core/checkpoint.py` | `AdapterCheckpoint` — cross-run resume support (spec 109) |
| `core/atomic_write.py` | `atomic_write_text/json()` — crash-safe file writes |
| `adapters/_base.py` | `BaseAdapter` protocol + `ResumableAdapter` + `FetchResult` |
| `adapters/_registry.py` | `register_adapter()` decorator, `discover_adapters()`, `get_adapter(name)` |
| `adapters/yengo-source/` | `YengoSourceAdapter` — JSON collection → SGF (HTTP) |
| `adapters/local/` | `LocalAdapter` — filesystem SGF import with checkpoint |
| `adapters/yengo-source/` | `YengoSourceAdapter` — local puzzle import |
| `adapters/yengo-source/` | `YengoSourceAdapter` — local collection import |
| `stages/ingest.py` | `IngestStage.run()` — fetch + parse + validate; generates `trace_id`; `_check_dedup(conn, sgf, source_id=)` allows cross-source duplicates |
| `stages/analyze.py` | `AnalyzeStage.run()` — classify + tag + enrich; reads/preserves `trace_id` |
| `stages/publish.py` | `PublishStage.run()` — batch output + DB build + publish log append |
| `stages/protocol.py` | `StageContext`, `StageResult` — shared stage interface |
| `pipeline/coordinator.py` | `PipelineCoordinator.run()` — sequential stage execution + `PipelineResult` |
| `pipeline/prerequisites.py` | `check_source_availability()` — pre-flight checks |
| `pipeline/cleanup.py` | `cleanup_old_files()`, `cleanup_target()` — log/state/staging cleanup |
| `models/config.py` | `PipelineConfig`, `BatchConfig`, `RetentionConfig`, `DailyConfig` (Pydantic) |
| `models/publish_log.py` | `PublishLogEntry` — frozen dataclass for JSONL |
| `models/enums.py` | `SkillLevel`, `BoardRegion`, `RunStatus`, `StageStatus` |
| `config/loader.py` | `ConfigLoader` — load `sources.json`, `config/*.json`, `get_active_adapter()` |
| `inventory/manager.py` | `InventoryManager` — load/rebuild/reconcile `inventory.json` |
| `daily/generator.py` | `DailyGenerator` — select puzzles by level/tag, write via db_writer |
| `daily/db_writer.py` | `inject_daily_schedule()`, `prune_daily_window()` — write daily rows to yengo-search.db |
| `state/manager.py` | `StateManager` — create/load/save run state JSON |

---

## 2. Core Entities

| Class | Key Fields | Represents |
|-------|-----------|------------|
| `SGFGame` | `root_properties: dict`, `solution: SolutionNode \| None`, `yengo: YenGoProperties` | Parsed puzzle in memory |
| `YenGoProperties` | `puzzle_id`, `schema_version`, `level_slug`, `tags`, `hints`, `quality`, `complexity`, `collection`, `ko_context`, `move_order`, `corner`, `refutations`, `pipeline_meta` | All YenGo custom SGF properties |
| `SolutionNode` | `move: str`, `color: str`, `is_correct: bool`, `comment: str`, `children: list[SolutionNode]` | One node in solution tree |
| `PuzzleEntry` | `content_hash`, `batch`, `level_id`, `quality`, `content_type`, `cx_depth`, `cx_refutations`, `cx_solution_len`, `cx_unique_resp`, `ac` | yengo-search.db row for one puzzle |
| `FetchResult` | `puzzle_id: str`, `sgf_text: str`, `source_metadata: dict` | Adapter output for one puzzle |
| `StageContext` | `config: PipelineConfig`, `adapter: BaseAdapter`, `source_name: str`, `run_id: str`, `staging_dir: Path`, `output_dir: Path` | Shared context threaded through pipeline |
| `PublishLogEntry` | `run_id`, `puzzle_id (content_hash)`, `source`, `batch`, `timestamp`, `action (publish/rollback)` | Append-only audit trail entry |

---

## 3. Key Methods & Call Sites

| Function | Signature | Called By |
|----------|-----------|-----------|
| `parse_sgf(sgf_text)` | `(str) -> SGFGame` | `IngestStage`, `AnalyzeStage`, `SGFValidator` |
| `publish_sgf(game)` | `(SGFGame) -> str` | `PublishStage`, `SGFBuilder.build()` |
| `enrich_puzzle(game, config)` | `(SGFGame, EnrichmentConfig) -> EnrichmentResult` | `AnalyzeStage.run()` |
| `generate_content_hash(content)` | `(str) -> str` | `PublishStage` (sets GN property) |
| `build_search_db(entries, output_path)` | `(list[PuzzleEntry], Path) -> None` | `PublishStage` (incremental rebuild) |
| `get_adapter(name)` | `(str) -> BaseAdapter` | `PipelineCoordinator`, `cli.py` |
| `discover_adapters()` | `() -> list[str]` | `cli.py sources` command |
| `AdapterCheckpoint.mark_done(puzzle_id)` | — | `IngestStage` per-puzzle |
| `AdapterCheckpoint.is_done(puzzle_id)` | `(str) -> bool` | `IngestStage` (skip already-processed) |
| `HttpClient.get(url)` | `async (str) -> Response` | All adapters that fetch from network |
| `generate_trace_id()` | `() -> str` | `IngestStage` (16-char hex, one per puzzle) |

---

## 4. Data Flow

```
sources.json → get_adapter(name) → BaseAdapter.fetch_all()
  │
  ▼ IngestStage
  │  • adapter.fetch() → FetchResult(puzzle_id, sgf_text)
  │  • parse_sgf(sgf_text) → SGFGame
  │  • SGFValidator.validate(game) → errors/warnings
  │  • generate_trace_id() → set YM[t=...]
  │  • write: .pm-runtime/staging/ingest/{puzzle_id}.sgf
  │
  ▼ AnalyzeStage
  │  • parse_sgf(staging_sgf) → SGFGame
  │  • classify_difficulty() → level slug → YG
  │  • detect_techniques() → tags → YT
  │  • enrich_puzzle(game, config) → EnrichmentResult
  │      → hints (YH), region (YC), ko (YK), move_order (YO), refutations (YR)
  │  • compute quality + complexity → YQ, YX
  │  • publish_sgf(game) → write: .pm-runtime/staging/analyzed/{puzzle_id}.sgf
  │
  ▼ PublishStage
  │  • parse_sgf(analyzed_sgf) → SGFGame
  │  • generate_content_hash(sgf_text) → content_hash (16 hex)
  │  • game.yengo.puzzle_id = f"YENGO-{content_hash}" → GN property
  │  • BatchWriter.write(content_hash, sgf_text) → yengo-puzzle-collections/sgf/{batch}/{hash}.sgf
  │  • Insert PuzzleEntry into yengo-content.db
  │  • Rebuild yengo-search.db from all content DB entries
  │  • PublishLogWriter.append(entry) → publish-log.jsonl
  │  • atomic_write_json(db-version.json)
  │
OUTPUT: yengo-puzzle-collections/sgf/{NNNN}/{hash}.sgf
        yengo-puzzle-collections/yengo-search.db  ← ships to browser
        yengo-puzzle-collections/db-version.json
```

**GN property invariant**: `GN = YENGO-{SHA256(sgf_content)[:16]}`. Adapters MUST NOT set GN in YenGo format — publish stage overwrites it. GN == filename (guaranteed by PublishStage).

**Config authority**: Tags from `config/tags.json`. Levels from `config/puzzle-levels.json`. Never hardcoded.

---

## 5. External Dependencies

| Library | Used For |
|---------|----------|
| `sgfmill` | SGF board manipulation in `core/board.py` |
| `httpx` | HTTP in `HttpClient` (async) |
| `tenacity` | Retry logic in `HttpClient` |
| `pydantic` | `models/config.py` and all config loading |
| `argparse` (stdlib) | CLI (`cli.py`) |
| `sqlite3` (stdlib) | yengo-search.db and yengo-content.db builds |

---

## 6. Known Gotchas

- **Adapter GN rule**: Adapters set `puzzle_id` (any format). Publish stage computes content hash and overwrites GN. An adapter setting `GN[YENGO-...]` will have it overwritten.
- **Incremental publish**: yengo-search.db is always rebuilt from all yengo-content.db entries. Never partially modify yengo-search.db directly.
- **`content_hash` == filename == GN suffix**: All three must match. `naming.py:generate_content_hash()` is the single source of truth.
- **`trace_id` != `puzzle_id`**: `trace_id` is per-puzzle pipeline-run identifier (in `YM[t=...]`). `puzzle_id` is the stable content hash (in `GN`). Use `trace_id` for debugging; use `puzzle_id` for identity.
- **Checkpoint coupling**: `AdapterCheckpoint.is_done()` uses `puzzle_id` from the adapter, not the content hash. If an adapter changes its puzzle_id format, existing checkpoints won't be recognized.
- **`batch` field**: Determined by file count (BatchWriter auto-shards at 100 files/dir). Batch is in directory name AND in `PuzzleEntry.batch`. Used by frontend for path reconstruction: `sgf/{batch}/{content_hash}.sgf`.
- **Run from repo root**: `python -m backend.puzzle_manager` must run from repo root (paths relative to repo root in `paths.py`).
