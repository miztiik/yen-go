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
| `cli.py` | 14-command argparse CLI: `run`, `status` (Theme 2a: `--failures-summary`), `sources`, `daily`, `clean`, `validate`, `publish-log`, `logs` (Theme 4: `grep`), `rollback`, `vacuum-db`, `inventory` (Theme 14a: `--check --json` emits `IntegrityReport`; Theme 14c1/14c2: `--{rebuild,reconcile,fix} [--dry-run] --json` emits `InventoryMutationPreview` / `InventoryMutationResult` — apply path takes `PipelineLock` and writes an `inventory_{op}` row to `audit.jsonl`), `runtime-info` (Theme 3a), `activity` (Theme 13a), `ops catalog` (Theme 16a: `--json` emits the blast-radius taxonomy from `models/ops_catalog.py`), `tags list` / `levels list` (Theme 5: `--with-usage --json` emits `TagUsageEntry` / `LevelUsageEntry` rows from `models/taxonomy.py`); `source-status` (Theme 6a: `--source ID --details --json` emits `SourceDetails` from `models/source_details.py` — summary counts + recent runs/failures + config echo, scanned from `.pm-runtime/state/runs/*.json`); `source-ingest-state` (Theme 6b: positional `source_id` + `[--reset] [--dry-run] [--json] [--max-failed-rows N]` emits `SourceIngestState` / `SourceIngestResetPreview` / `SourceIngestResetResult` from `models/source_ingest_state.py` — reads counts via read-only `file:?mode=ro` URI; reset apply uses `SourceIngestDB.wipe()` to atomically remove the SQLite file + WAL/SHM sidecars); `adapter-config {list|show|validate-all}` (Theme 7a: read-only sources.json inspection. `list --json` emits `AdapterConfigList` with derived `active`/`path_exists` flags; `show ID --json` emits `AdapterConfigShow` with adapter_kind + JSON-Schema fragment from `sources.schema.json` `$defs/{Kind}Config` + available_kinds from the adapter registry; `validate-all --json` emits `AdapterValidationReport` combining schema validation + path-existence checks — codes: `schema`/`path-missing`. Theme 7b adds mutating sub-actions `add|clone|update|remove` — each validates the proposed sources doc against `sources.schema.json` via `Draft202012Validator`, acquires `PipelineLock` (skip with `--force`), then `atomic_write_json`s back; rc 2 + `errors[]` on duplicate-id / unknown-source / schema / pipeline-locked. `remove` refuses to delete the `active_adapter` unless `--force`. Theme 7c adds `adapter-config bootstrap --from-folder PATH [--adapter local] [--id-prefix STR] [--dry-run] --json` — scans immediate subdirectories, slugifies their names into source IDs, emits proposal JSON (`{ok, dry_run, applied, from_folder, entries[{id,name,adapter,config,conflicts_with_existing}], applied_ids?}`); apply path filters out collisions, validates the doc, acquires `PipelineLock`, and `atomic_write_json`s. Theme 7d adds `pipeline-config {show|set}` — `show --json` reads `config/pipeline.json` and emits `{ok, pipeline}`; `set --set KEY=VALUE [--force] --json` performs deep-copy + dotted-path nested-dict mutation (creating intermediate dicts as needed), JSON-decodes each VALUE with string fallback, acquires `PipelineLock` (skip with `--force`), and `atomic_write_json`s; rc 2 on bad `--set` syntax / missing pairs / pipeline-locked. Theme 8a adds `daily-list [--from --to] --json` (reads `daily_schedule` joined to `daily_puzzles` from `yengo-search.db` via read-only `file:?mode=ro` URI; emits `{ok, db_exists, from?, to?, rows[{date, version, generated_at, technique, attrs, puzzle_count}]}`; missing DB returns `rows=[]`) and `daily-status [--window-days N] [--stale-days M] --json` (computes rolling-window health: emits `{ok, db_exists, window{from,to,days}, expected_dates, generated_dates, missing_dates[], stale_dates[{date, regenerated_at, age_days}], last_regenerated_at}`). Theme 8b adds `daily-preview --date DATE --json` (read-only dry-run via `DailyGenerator(dry_run=True)`; emits `{ok, db_exists, date, challenge?, failures[]}` where `challenge` is the full `DailyChallenge.model_dump(mode="json")` or `null` when no challenge / DB missing; rc 1 + `{ok:false, error}` on bad `--date`). Theme 8c adds `daily-cancel {--date DATE | --from F --to T} [--dry-run] [--force] --json` — preview-then-apply destructive removal. Reads affected dates + puzzle counts via read-only URI, then on apply acquires `PipelineLock(run_id="daily-cancel")` (skip with `--force`) and deletes `daily_puzzles` + `daily_schedule` rows in one transaction. Emits `{ok, dry_run, db_exists, from, to, dates_affected[], puzzle_rows_affected, schedule_rows_deleted?}`; rc 2 on missing args / invalid date / `--from > --to` / pipeline-locked.) |
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
| `core/atomic_write.py` | `atomic_write_text/json()` — crash-safe file writes |
| `core/source_ingest_db.py` | `SourceIngestDB` — per-source `.yengo-ingest.sqlite` (ingest state, content-aware skip, rename detection). Replaces legacy `AdapterCheckpoint`. |
| `adapters/_base.py` | `BaseAdapter` protocol + `ResumableAdapter` + `FetchResult` |
| `adapters/_registry.py` | `register_adapter()` decorator, `discover_adapters()`, `get_adapter(name)` |
| `adapters/yengo-source/` | `YengoSourceAdapter` — JSON collection → SGF (HTTP) |
| `adapters/local/` | `LocalAdapter` — filesystem SGF import (uses `SourceIngestDB` for skip + rename detection) |
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
| `models/failures.py` | `FailureGroup` (Pydantic) + `summarize_failures(runs)` — Theme 2a wire contract for `status --failures-summary` |
| `models/runtime_info.py` | `RuntimeInfo` (Pydantic) + `compute_runtime_info(runtime_dir, sources, publish_log_dir)` — Theme 3a wire contract for `runtime-info` CLI |
| `models/activity.py` | `ActivityEvent` (Pydantic) + `compute_activity(runs_dir, audit_file, publish_log_dir, ...)` — Theme 13a wire contract for `activity` CLI; merges run/audit/publish-log events, no new persistence |
| `models/integrity.py` | `IntegrityReport` / `IntegrityIssue` / `IntegritySummary` (Pydantic) — Theme 14a wire contract for `inventory --check --json`. Adapts the legacy `IntegrityResult` dataclass into a list-of-issues shape (kinds: `missing_file`, `orphan_file`); `hash_mismatch` deferred. |
| `models/inventory_preview.py` | `InventoryMutationPreview` + `InventoryMutationResult` (Pydantic, `op = rebuild|reconcile|fix`) — Theme 14c1/14c2 wire contracts for `inventory --{rebuild,reconcile,fix} [--dry-run] --json`. Preview reports the impact summary without touching disk; Result mirrors the same shape post-apply with `executed=True`, `audit_timestamp`, and post-state totals. |
| `models/ops_catalog.py` | `OpsCatalogEntry` (Pydantic) + `OPS_CATALOG` registry + `get_ops_catalog()` — Theme 16a wire contract for `ops catalog --json`. Single source of truth for blast-radius classification (scope, reversible, preview_supported, section) of every mutating CLI subcommand. The drift-fence test in `tests/unit/test_ops_catalog.py` enforces that registering a new mutating subcommand without a catalog row fails CI. |
| `models/taxonomy.py` | `TagUsageEntry` + `LevelUsageEntry` (Pydantic) — Theme 5 wire contracts for `tags list --with-usage --json` and `levels list --with-usage --json`. Usage counts join `inventory.json` snapshot with `config/tags.json` / `config/puzzle-levels.json`; `first_seen_run` / `last_seen_run` reserved (set to `None`) until publish-log scan is added. |
| `models/source_details.py` | `SourceDetails` + `SummaryCounts` + `RecentRunSummary` + `RecentFailureSummary` (Pydantic) — Theme 6a wire contract for `source-status --source ID --details --json`. Built by `cli._build_source_details()` from per-source filtering of `.pm-runtime/state/runs/*.json` (matches `state.config_snapshot.source_id`); recent_runs/failures capped (default 10). |
| `models/source_ingest_state.py` | `SourceIngestState` + `FailedIngestRow` + `SourceIngestResetPreview` + `SourceIngestResetResult` (Pydantic) — Theme 6b wire contract for `source-ingest-state --json`. Status literal: `healthy`/`stale`/`empty`/`missing`; failed_rows capped (`--max-failed-rows`, default 50). Counts derived from per-source `.yengo-ingest.sqlite` via read-only URI; reset apply path is `SourceIngestDB.wipe()`. |
| `models/adapter_config.py` | `AdapterSourceEntry` + `AdapterConfigList` + `AdapterConfigShow` + `AdapterValidationIssue` + `AdapterValidationRow` + `AdapterValidationReport` (Pydantic) — Theme 7a wire contracts for the read-only `adapter-config {list|show|validate-all} --json` subcommands. `AdapterSourceEntry` augments the on-disk source schema with derived `active` / `path_exists` flags so the dashboard table renders without a second round-trip. |
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
| `AdapterCheckpoint.mark_done(puzzle_id)` | — | _removed; superseded by `SourceIngestDB.upsert()`_ |
| `AdapterCheckpoint.is_done(puzzle_id)` | `(str) -> bool` | _removed; superseded by `SourceIngestDB.find_by_path()` + tier-3 rehash_ |
| `SourceIngestDB.open(source_path, *, source_id, run_id)` | classmethod context manager | `LocalAdapter.fetch()`, `SanderlandAdapter.fetch()`, `cli source-status` |
| `SourceIngestDB.upsert(record)` | `(FileRecord) -> None` | adapter `_process_file()` per file |
| `SourceIngestDB.find_by_hash(content_hash)` | `(str) -> list[FileRecord]` | adapter `_detect_rename()` |
| `SourceIngestDB.progress()` | `() -> IngestProgress` | `cli source-status`, future telemetry |
| `SourceIngestDB.wipe(source_path)` | `(Path) -> bool` | `cli run --fresh` |
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
- **Ingest skip coupling**: `SourceIngestDB` keys on `rel_path` (POSIX, source-root relative) and `content_hash` = `SHA256(raw_sgf)[:16]`. The DB lives at `<source.path>/.yengo-ingest.sqlite` and is the single source of truth for resume/skip. Tier-3 always-rehash policy means stat changes alone never cause a re-publish; content drives everything. Wipe with `python -m backend.puzzle_manager run --source <id> --fresh` (also wipes `.pm-runtime/state`).
- **`batch` field**: Determined by file count (BatchWriter auto-shards at 100 files/dir). Batch is in directory name AND in `PuzzleEntry.batch`. Used by frontend for path reconstruction: `sgf/{batch}/{content_hash}.sgf`.
- **Run from repo root**: `python -m backend.puzzle_manager` must run from repo root (paths relative to repo root in `paths.py`).
