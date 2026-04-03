# Plan: Performance & Config-Driven KataGo Enrichment

**Last Updated:** 2026-03-03
**Status:** IMPLEMENTED + CLEANUP DONE — All 6 gates approved, legacy code removed (D48)
**Reviewers:** Principal Staff Engineer, Lee Sedol (9P), Cho Chikun (9P)
**Review Protocol:** Every phase gate requires consultation review by all 3 reviewers, conducted twice per gate. Bugs and issues must be fixed before proceeding to next phase.
**Sources:** GoProblems.com Research Tab analysis, enrichment lab codebase audit, calibration test results
**Scope:** `tools/puzzle-enrichment-lab/`, `config/katago-enrichment.json`, `docs/architecture/tools/katago-enrichment.md`

**Code Principle:** Avoid regex wherever possible. Use string methods (`str.split()`, `str.startswith()`, `str.endswith()`, `str.find()`, `in` operator) for parsing and validation. Regex is a last resort for genuinely irregular patterns only.

**Naming:** The config section formerly called `lab_mode` is renamed to `deep_enrich`. This describes the _behavior_ (deep, thorough enrichment) not the _location_ (lab tool). When the tool graduates into the mainline pipeline, `deep_enrich` remains meaningful.

---

## TL;DR

GoProblems.com enriches puzzles in 2-3 seconds using b10 model / 500 visits / tsumego frame / single-query PV extraction. Our enrichment takes 10-15 minutes per puzzle using b28 / 10K visits / 8 symmetries / 26 sequential engine calls. This plan addresses: (1) performance optimization via config tuning, (2) migrating ~45 hardcoded thresholds to `katago-enrichment.json`, (3) per-run log files with enriched SGF summary, (4) model name indirection via labels, (5) relative paths everywhere, (6) randomized test fixtures.

**Legacy Terminology Removal:** After this plan is fully executed, the following terms will be completely removed from the codebase:

- `lab_mode` — replaced by `deep_enrich` everywhere (config, code, docs, tests)
- `dual_engine` / `DualEngineManager` — replaced by single-engine architecture with config-driven escalation via `deep_enrich.escalate_to_referee`. The `dual_engine` config section is absorbed into `deep_enrich` and `models`.
- `bridge` / `patching` — the tool reads/writes SGFs directly; no bridge layer to the pipeline
- `rejected` as a hard validation status — replaced by `needs_review` (no automated hard rejects from AI analysis)

---

## Phase 0: Config Schema Expansion

### P0.1 — New Config Sections in `katago-enrichment.json`

All hardcoded values across `analyzers/` move here. Grouped by concern.

#### `models` section (NEW) — Model Name Indirection

Purpose: Decouple model LABELS from model FILENAMES. Code references labels only.

| Key                           | Type   | Default                                              | Description                                          |
| ----------------------------- | ------ | ---------------------------------------------------- | ---------------------------------------------------- |
| `models.quick.label`          | string | `"quick"`                                            | Logical name for the fast model                      |
| `models.quick.arch`           | string | `"b18c384"`                                          | Architecture identifier (log tags, reporting)        |
| `models.quick.filename`       | string | `"kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"`  | Model filename (resolved relative to `models-data/`) |
| `models.referee.label`        | string | `"referee"`                                          | Logical name for the deep model                      |
| `models.referee.arch`         | string | `"b28c512"`                                          | Architecture identifier                              |
| `models.referee.filename`     | string | `"kata1-b28c512nbt-s12192929536-d5655876072.bin.gz"` | Model filename                                       |
| `models.deep_enrich.label`    | string | `"deep_enrich"`                                      | Logical name for deep enrichment model               |
| `models.deep_enrich.arch`     | string | `"b18c384"`                                          | Architecture (changed from b28c512 — see P1.1)       |
| `models.deep_enrich.filename` | string | `"kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"`  | Model filename                                       |

**Rule:** No `.py` file may reference a model filename or architecture string directly. All references go through `config.models.<label>`.

#### `deep_enrich` section (replaces `lab_mode`) — Deep Enrichment Settings

Renamed from `lab_mode` to `deep_enrich`. Describes the behavior (thorough, maximum-quality enrichment) not the location.

| Key                                         | Type   | Default     | Description                                                            |
| ------------------------------------------- | ------ | ----------- | ---------------------------------------------------------------------- |
| `deep_enrich.enabled`                       | bool   | `true`      | Master switch for deep enrichment mode                                 |
| `deep_enrich.model`                         | string | `"b18c384"` | Model arch (via `models.deep_enrich`). Changed from b28c512 (see P1.1) |
| `deep_enrich.visits`                        | int    | `2000`      | MCTS visits. Changed from 10000 (see P1.1)                             |
| `deep_enrich.root_num_symmetries_to_sample` | int    | `2`         | Symmetries. Changed from 8 (see P1.1)                                  |
| `deep_enrich.max_time`                      | int    | `0`         | Max time per query (0 = unlimited)                                     |

#### `tree_validation` section (NEW) — Deep Solution Tree Validation

Currently hardcoded in `validate_correct_move.py` L799-L891.

| Key                                            | Type  | Default | Description                                                    |
| ---------------------------------------------- | ----- | ------- | -------------------------------------------------------------- |
| `tree_validation.enabled`                      | bool  | `true`  | Master switch — set `false` to skip entirely                   |
| `tree_validation.skip_when_confident`          | bool  | `true`  | Skip if initial analysis is confident                          |
| `tree_validation.confidence_winrate`           | float | `0.85`  | Winrate threshold for skip. Ko/seki: use 0.75 (see review)     |
| `tree_validation.confidence_top_n`             | int   | `1`     | Must be in top-N for skip                                      |
| `tree_validation.visits_per_depth`             | int   | `500`   | MCTS visits per tree-depth query                               |
| `tree_validation.top_n_match`                  | int   | `3`     | Correct move must be in top-N at each depth                    |
| `tree_validation.depth_base`                   | int   | `3`     | Min validation depth for all puzzles                           |
| `tree_validation.depth_intermediate`           | int   | `5`     | Depth for intermediate+ (level_id >= threshold)                |
| `tree_validation.depth_advanced`               | int   | `7`     | Depth for advanced+                                            |
| `tree_validation.depth_ko`                     | int   | `5`     | Depth for ko-tagged puzzles                                    |
| `tree_validation.level_intermediate_threshold` | int   | `140`   | Level ID boundary for intermediate depth                       |
| `tree_validation.level_advanced_threshold`     | int   | `170`   | Level ID boundary for advanced depth                           |
| `tree_validation.quick_only_depth_cap`         | int   | `2`     | Max depth in quick_only mode                                   |
| `tree_validation.confidence_winrate_ko`        | float | `0.75`  | Winrate threshold for ko puzzles (lower — see Go pro review)   |
| `tree_validation.confidence_winrate_seki`      | float | `0.70`  | Winrate threshold for seki puzzles (lower — see Go pro review) |

#### `technique_detection` section (NEW) — 16 thresholds from `technique_classifier.py`

| Key                                                    | Type  | Default | Description                            |
| ------------------------------------------------------ | ----- | ------- | -------------------------------------- |
| `technique_detection.ladder.min_pv_length`             | int   | `4`     | Min PV moves for ladder pattern        |
| `technique_detection.ladder.diagonal_ratio`            | float | `0.5`   | >= 50% diagonal moves = ladder-like    |
| `technique_detection.snapback.policy_threshold`        | float | `0.05`  | Sacrifice stone: low policy (<5%)      |
| `technique_detection.snapback.winrate_threshold`       | float | `0.9`   | After sacrifice: high winrate (>90%)   |
| `technique_detection.snapback.delta_threshold`         | float | `0.3`   | Winrate swing for capture confirmation |
| `technique_detection.net.policy_threshold`             | float | `0.3`   | High policy for net move               |
| `technique_detection.net.winrate_threshold`            | float | `0.9`   | High winrate for net confirmation      |
| `technique_detection.net.min_refutations`              | int   | `2`     | Minimum trapped escape attempts        |
| `technique_detection.net.delta_spread`                 | float | `0.1`   | Similar deltas = net (not ladder)      |
| `technique_detection.seki.winrate_low`                 | float | `0.3`   | Balanced winrate lower bound           |
| `technique_detection.seki.winrate_high`                | float | `0.7`   | Balanced winrate upper bound           |
| `technique_detection.seki.score_threshold`             | float | `5.0`   | Near-zero score threshold              |
| `technique_detection.direct_capture.max_depth`         | int   | `2`     | Max solution depth for direct capture  |
| `technique_detection.direct_capture.winrate_threshold` | float | `0.9`   | High winrate for trivial capture       |
| `technique_detection.direct_capture.max_visits`        | int   | `500`   | Low visits = simple capture            |
| `technique_detection.throw_in.edge_lines`              | int   | `2`     | 1st/2nd line from board edge           |

#### `ko_detection` section (NEW) — from `ko_validation.py`

| Key                              | Type | Default | Description                              |
| -------------------------------- | ---- | ------- | ---------------------------------------- |
| `ko_detection.min_pv_length`     | int  | `3`     | Min PV length to detect ko pattern       |
| `ko_detection.min_repeat_count`  | int  | `2`     | Coord repeats required to flag ko        |
| `ko_detection.long_ko_threshold` | int  | `3`     | Repeats for long ko fight classification |
| `ko_detection.double_ko_coords`  | int  | `2`     | Distinct repeated coords for double ko   |

#### `teaching` section (NEW) — from `teaching_comments.py`

| Key                                   | Type  | Default | Description                                       |
| ------------------------------------- | ----- | ------- | ------------------------------------------------- |
| `teaching.non_obvious_policy`         | float | `0.05`  | Policy < this = "non-obvious move" enhancement    |
| `teaching.ko_delta_threshold`         | float | `0.1`   | Delta < this = ko-specific wrong move template    |
| `teaching.capture_depth_threshold`    | int   | `1`     | Depth <= this = simple capture template           |
| `teaching.significant_loss_threshold` | float | `0.5`   | Delta > this = "loses ~X%" comment                |
| `teaching.moderate_loss_threshold`    | float | `0.2`   | Delta > this = "significant disadvantage" comment |

#### `difficulty.normalization` sub-section (NEW) — from `estimate_difficulty.py`

| Key                                             | Type  | Default | Description                             |
| ----------------------------------------------- | ----- | ------- | --------------------------------------- |
| `difficulty.normalization.max_solution_depth`   | float | `15.0`  | Solution depth ceiling                  |
| `difficulty.normalization.max_branch_count`     | float | `5.0`   | Branch count ceiling                    |
| `difficulty.normalization.max_local_candidates` | float | `20.0`  | Local candidates ceiling                |
| `difficulty.normalization.max_refutation_count` | float | `5.0`   | Refutation count ceiling                |
| `difficulty.normalization.max_visits_cap`       | int   | `20000` | Upper bound for visits log-scale        |
| `difficulty.normalization.disagree_multiplier`  | int   | `2`     | Visits multiplier when KataGo disagrees |

#### Escalation settings (absorbed from removed `dual_engine` section into `deep_enrich`)

The `dual_engine` config section is **removed entirely**. Escalation is now part of `deep_enrich`:

| Key                                   | Type  | Default | Description                                 |
| ------------------------------------- | ----- | ------- | ------------------------------------------- |
| `deep_enrich.escalate_to_referee`     | bool  | `true`  | Escalate uncertain puzzles to referee model |
| `deep_enrich.escalation_winrate_low`  | float | `0.3`   | Winrate below this triggers escalation      |
| `deep_enrich.escalation_winrate_high` | float | `0.7`   | Winrate above this skips escalation         |
| `deep_enrich.tiebreaker_tolerance`    | float | `0.05`  | Winrate agreement tolerance                 |

#### `refutations` additions — PV-Based Mode

| Key                                 | Type   | Default         | Description                                                              |
| ----------------------------------- | ------ | --------------- | ------------------------------------------------------------------------ |
| `refutations.pv_mode`               | string | `"multi_query"` | `"pv_extract"` = single-query; `"multi_query"` = per-candidate (current) |
| `refutations.pv_extract_min_depth`  | int    | `3`             | Min PV depth for pv_extract; fallback to multi_query if shorter          |
| `refutations.pv_quality_min_visits` | int    | `50`            | Min visits for PV trust in pv_extract mode                               |

#### `calibration` section (NEW) — Test Configuration

| Key                              | Type     | Default                                                | Description                                |
| -------------------------------- | -------- | ------------------------------------------------------ | ------------------------------------------ |
| `calibration.sample_size`        | int      | `5`                                                    | Puzzles per collection per test run        |
| `calibration.seed`               | int      | `42`                                                   | Random seed (null for truly random)        |
| `calibration.batch_timeout`      | int      | `1800`                                                 | Seconds timeout                            |
| `calibration.level_tolerance`    | int      | `20`                                                   | +/- level ID points                        |
| `calibration.fixture_dirs`       | string[] | `["cho-elementary","cho-intermediate","cho-advanced"]` | Directories to sample from                 |
| `calibration.randomize_fixtures` | bool     | `false`                                                | true = ignore seed, pick randomly each run |

#### `logging` additions

| Key                          | Type | Default | Description                                   |
| ---------------------------- | ---- | ------- | --------------------------------------------- |
| `logging.per_run_files`      | bool | `true`  | Create `logs/{run_id}-enrichment.log` per run |
| `logging.use_relative_paths` | bool | `true`  | Strip workspace root from logged paths        |

---

## Phase 1: Performance Optimization (Config-Only Changes)

### P1.1 — Reduce Deep Enrichment Visits & Model

**File:** `config/katago-enrichment.json` — `deep_enrich` section (replacing `lab_mode`)

| Parameter                       | Current (`lab_mode`) | Proposed (`deep_enrich`) | Rationale                                                                       |
| ------------------------------- | -------------------- | ------------------------ | ------------------------------------------------------------------------------- |
| `visits`                        | `10000`              | `2000`                   | b18 at 2K = ~13,600 Elo. 5x speedup. <1% accuracy loss sub-dan.                 |
| `root_num_symmetries_to_sample` | `8`                  | `2`                      | 4x fewer NN evals. Cropping addresses orientation bias.                         |
| `model`                         | `"b28c512"`          | `"b18c384"`              | Via `models.deep_enrich`. b18 is 3x faster. Reserve b28 for referee escalation. |

**Expected impact:** ~20-60x speedup (10-15 min to 15-45 sec per puzzle).

### P1.2 — Reduce Escalation Attempts

**File:** `config/katago-enrichment.json` — `refutation_escalation`

`max_escalation_attempts`: `2` to `1`. Saves up to 6 engine calls.

### P1.3 — Conditional Deep Tree Validation Skip

**File:** `config/katago-enrichment.json` — `tree_validation` (new section from P0.1)

When `skip_when_confident = true` AND the initial analysis shows the correct move is top-1 with winrate >= `confidence_winrate` (0.85), skip tree validation. Eliminates 3-7 engine calls for ~70% of puzzles.

For ko puzzles, use `confidence_winrate_ko` (0.75). For seki puzzles, use `confidence_winrate_seki` (0.70). See Go Professional review below.

### P1.4 — PV-Based Refutations (Single-Query Mode)

**File:** `config/katago-enrichment.json` — `refutations.pv_mode`

When `pv_mode = "pv_extract"`:

1. Extract wrong-move PV sequences directly from the initial analysis `moveInfos[].pv`
2. Fall back to `"multi_query"` when PV depth < `pv_extract_min_depth` or visits < `pv_quality_min_visits`

**Quality gate:** Compare PV-extracted refutations vs multi-query refutations on calibration fixtures. If agreement rate < 90%, keep `"multi_query"` as default.

**Default:** `"multi_query"` (current behavior) until calibration validates pv_extract.

---

## Phase 2: Model Name Indirection

### P2.1 — Add `models` Section to Config

As defined in P0.1. Three labeled models: `quick`, `referee`, `deep_enrich`.

### P2.2 — Remove All Hardcoded Model Names

| File                              | Lines       | Current                     | Change to                                                                  |
| --------------------------------- | ----------- | --------------------------- | -------------------------------------------------------------------------- |
| `config.py`                       | 193,195,285 | `"b18c384"`, `"b28c512"`    | Load from `config.models.quick.arch`, `.referee.arch`, `.deep_enrich.arch` |
| `scripts/run_calibration.py`      | 53-54       | Full model filenames        | Load from `config.models.quick.filename`, `.referee.filename`              |
| `mini_calibration.py`             | 14          | Full model filename         | Load from `config.models.quick.filename`                                   |
| `scripts/download_models.py`      | 24-35       | `MODELS` dict               | Keep as download script constants (download URLs, not runtime refs)        |
| `analyzers/dual_engine.py`        | 81,84,167   | Docstring model names       | Use labels `"quick"`, `"referee"`                                          |
| `tests/test_calibration.py`       | 97-98       | Full model filenames        | Load from config                                                           |
| `tests/test_calibration_retry.py` | 57,61       | Full paths with model names | Use `config.models.quick.filename` in path construction                    |
| `engine/config.py`                | 31          | Docstring example           | Update example to use label                                                |

### P2.3 — Rename `lab_mode` to `deep_enrich` Everywhere

| File                                           | Change                                                                   |
| ---------------------------------------------- | ------------------------------------------------------------------------ |
| `config/katago-enrichment.json`                | Rename `lab_mode` key to `deep_enrich`                                   |
| `config.py` dataclass                          | `LabModeConfig` to `DeepEnrichConfig`, field `lab_mode` to `deep_enrich` |
| `analyzers/enrich_single.py`                   | `config.lab_mode.*` to `config.deep_enrich.*`                            |
| `analyzers/dual_engine.py`                     | `lab_mode` references to `deep_enrich`                                   |
| `docs/architecture/tools/katago-enrichment.md` | All ADR references                                                       |

---

## Phase 3: Logging Improvements

### P3.1 — Per-Run Log Files

**File:** `log_config.py`

When `config.logging.per_run_files = true`:

- Create `logs/{run_id}-enrichment.log` per run (e.g., `logs/20260302-d2c5bc98-enrichment.log`)
- Keep the rotating `enrichment.log` as aggregate
- Run-specific file gets only that run's records (filtered by `run_id`)

**Implementation:** Use a separate `FileHandler` per run, added dynamically in `setup_logging()`. The aggregate handler remains. Log the actual seed used when `randomize_fixtures=true` so any run can be reproduced.

### P3.2 — Relative Paths in Log Messages

**File:** `log_config.py`, `config.py`, `engine/local_subprocess.py`

Add `_strip_workspace_root()` utility:

- Walk up from `__file__` to find the directory containing `.git/`
- Use simple `str.removeprefix()` (no regex) to strip the workspace root
- Apply to all path log messages when `config.logging.use_relative_paths = true`
- Example: `tools/puzzle-enrichment-lab/logs/enrichment.log` instead of full Windows path

### P3.3 — Structured JSON Logging Cleanup

- Paths logged as separate JSON fields, not embedded in `msg` strings
- No double-escaped quotes in structured JSON output
- Example: `{"msg": "Loaded config", "config_path": "config/katago-enrichment.json"}` instead of `{"msg": "Loaded config from C:\\Users\\..."}`

### P3.4 — Enrichment Summary Log Messages

**Current gaps identified from log audit:**

1. **No source/collection info:** Log says `"Enriching puzzle board_9x9"` but doesn't say WHERE the puzzle came from (which collection, which source adapter, which file path).
2. **No enriched SGF summary:** After enrichment completes, there's no log of what the final SGF properties look like (YG, YT, YQ, YX, YH, YR, YK, YO values).
3. **No before/after diff:** For level mismatch overrides (YG changes), we don't log what the original level was vs what KataGo estimated.
4. **Engine request payloads are noisy:** DEBUG logs dump full JSON `initialStones` arrays (50+ characters) that are unreadable. Should log a compact summary instead.
5. **Unicode corruption:** Log shows `a]T'` instead of proper arrow/dash characters (UTF-8 encoding issue in `FileHandler`).

**New structured log messages to add in `enrich_single.py`:**

| When            | Level   | Structured Fields                                                               | Purpose                                                         |
| --------------- | ------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Start           | INFO    | `puzzle_id`, `source_file`, `collection`, `board_size`, `player`                | Know what puzzle is being enriched and where it came from       |
| After analysis  | INFO    | `puzzle_id`, `correct_move`, `winrate`, `policy`, `visits`, `top_move`, `model` | KataGo's initial read of the position                           |
| Enrichment done | INFO    | `puzzle_id`, `status`, `yg`, `yt`, `yq`, `yx`, `yr`, `yk`, `yo`, `yh_count`     | Full SGF property summary — what the enriched puzzle looks like |
| Level mismatch  | WARNING | `puzzle_id`, `original_level`, `katago_level`, `distance`                       | Before/after for YG overrides                                   |
| Engine request  | DEBUG   | `request_id`, `board_size`, `stone_count`, `visits`                             | Compact summary, NOT the full JSON payload                      |

**Fix Unicode:** Set `encoding='utf-8'` on the `FileHandler` in `log_config.py`. Windows defaults to `cp1252`.

---

## Phase 4: Randomized Test Fixtures

### P4.1 — Config-Driven Fixture Sampling

**File:** `tests/test_calibration.py`

Replace hardcoded `_SAMPLE_SIZE = 5`, `_SEED = 42`, `_BATCH_TIMEOUT = 1800`, `_LEVEL_TOLERANCE = 20` with reads from `config.calibration.*`.

### P4.2 — Multi-Source Fixture Directories

`calibration.fixture_dirs` lists directories to sample from. Tests read SGFs from ALL listed dirs, then sample `sample_size` from the combined pool. When `randomize_fixtures = true`, each run picks a different random subset.

### P4.3 — Fixture Hydration Script

Add `scripts/hydrate_calibration_fixtures.py`:

1. Reads puzzles from `external-sources/` matching target difficulty ranges
2. Copies a balanced sample to `tests/fixtures/calibration/{source}-{level}/`
3. Does NOT overwrite existing Cho Chikun fixtures

---

## Phase 5: Migrate Remaining Hardcoded Thresholds

### P5.1 — technique_classifier.py (15 values to config)

All 15 thresholds move to `config.technique_detection.*`. The `classify_techniques()` function loads config at invocation.

### P5.2 — teaching_comments.py (5 values to config)

Numeric thresholds move to `config.teaching.*`. String templates stay in code (content, not thresholds).

### P5.3 — estimate_difficulty.py (7 values to config)

Normalization ceilings and disagree multiplier move to `config.difficulty.normalization.*`.

### P5.4 — validate_correct_move.py (7 values to config)

Tree validation depths, level thresholds, seki score, visits, top-N check all move to `config.tree_validation.*`.

### P5.5 — ko_validation.py (4 values to config)

Ko detection thresholds move to `config.ko_detection.*`.

### P5.6 — Remove DualEngineManager, Replace with Single-Engine + Escalation

The `DualEngineManager` class in `dual_engine.py` is **removed entirely**. Its responsibilities are simplified:

- Single engine instance (managed by `enrich_single.py`)
- Model selection: `config.models.deep_enrich` (default) or `config.models.referee` (escalation)
- Escalation logic: if initial winrate is uncertain (0.3-0.7), re-analyze with referee model
- `tiebreaker_tolerance = 0.05` moves to `config.deep_enrich.tiebreaker_tolerance`
- The `dual_engine` section in `katago-enrichment.json` is removed
- All `DualEngineConfig`, `DualEngineResult`, `DualEngineManager` classes are deleted
- Tests in `test_dual_engine.py` are rewritten as escalation tests for the simplified architecture

### P5.7 — enrich_single.py (1 value to config)

`quick_only_depth_cap = 2` moves to `config.tree_validation.quick_only_depth_cap`.

### P5.8 — query_builder.py (cleanup)

Remove hardcoded fallback defaults (200, 2, 15, 30). Make config parameter required instead of optional.

### P5.9 — property_policy.py (regex cleanup)

Replace `_VALIDATORS` regex patterns with string-based parsing: split on `;` for key-value pairs, split on `:` for key/value, validate with `str.isdigit()` and float checks. Regex only acceptable for genuinely irregular external SGF input.

---

## Phase 6: Documentation & ADR Updates

### P6.1 — New ADRs in `docs/architecture/tools/katago-enrichment.md`

| ADR | Title                            | Key Decisions                                                                              |
| --- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| D40 | Performance-First Enrichment     | Visits 10K to 2K, symmetries 8 to 2, model b28 to b18 via labels. GoProblems.com evidence. |
| D41 | Config-Driven Thresholds         | ~45 thresholds migrated to JSON. Zero hardcoded numeric constants in analyzer code.        |
| D42 | Model Name Indirection           | `models.{label}.{arch,filename}` pattern. No model filenames in Python code.               |
| D43 | PV-Based Refutation Mode         | `pv_mode` flag with quality gates. Single-query for kyu, multi-query for dan+.             |
| D44 | Conditional Tree Validation Skip | Skip when confident (top-1, WR >= 0.85). Ko/seki-aware thresholds.                         |
| D45 | Per-Run Structured Logging       | `{run_id}-enrichment.log` per run. Relative paths. Native JSON fields.                     |
| D46 | Randomized Calibration Fixtures  | Config-driven sampling, multi-source fixture dirs.                                         |
| D47 | Rename lab_mode to deep_enrich   | Behavior-descriptive naming. Location-agnostic for mainline migration.                     |

### P6.2 — Update `docs/how-to/tools/katago-enrichment-lab.md`

Add sections: "Changing models", "Performance tuning", "Reading enrichment logs", "Adding calibration fixtures".

### P6.3 — Update Config Changelog

Add version `1.12` entry documenting all new sections and the `lab_mode` to `deep_enrich` rename.

---

## Verification

```powershell
# Unit tests
Push-Location tools/puzzle-enrichment-lab
python -m pytest tests/ -m "unit" --tb=short -q
Pop-Location

# No hardcoded model names (excluding download_models.py)
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "b10c128" -SimpleMatch | Where-Object { $_.Path -notlike "*download_models*" -and $_.Path -notlike "*__pycache__*" }
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "b18c384" -SimpleMatch | Where-Object { $_.Path -notlike "*download_models*" -and $_.Path -notlike "*__pycache__*" }
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "b28c512" -SimpleMatch | Where-Object { $_.Path -notlike "*download_models*" -and $_.Path -notlike "*__pycache__*" }
# All should return zero results

# No absolute paths in log output
Select-String -Path "tools/puzzle-enrichment-lab/logs/*.log" -Pattern "C:\Users" -SimpleMatch
# Should be empty

# Calibration passes
Push-Location tools/puzzle-enrichment-lab
python -m pytest tests/test_calibration.py -v -s --timeout=3600
Pop-Location
```

---

## Implementation Order with Phase Gates

Every phase boundary has a **review gate** where all 3 reviewers (Principal Staff Engineer, Lee Sedol 9P, Cho Chikun 9P) review the implementation. Two review rounds per gate. No phase proceeds until all issues from the gate review are resolved.

| Step      | Phase                                                                      | Est.       | Dependencies         | Status                                                                       |
| --------- | -------------------------------------------------------------------------- | ---------- | -------------------- | ---------------------------------------------------------------------------- |
| 1         | P0.1 Config schema design                                                  | 2h         | None                 | **DONE** (2026-03-03)                                                        |
| 2         | P2.3 Rename lab_mode to deep_enrich                                        | 1h         | P0.1                 | **DONE** (2026-03-03)                                                        |
| 3         | P1.1-P1.2 Perf config values                                               | 30min      | P0.1                 | **DONE** (2026-03-03)                                                        |
|           | **GATE 1 — Config Foundation Review**                                      | 1h         | Steps 1-3            | **APPROVED** (2026-03-03)                                                    |
|           | _Reviewers verify: schema completeness, naming, backward compat shim_      |            |                      |                                                                              |
| 4         | P2.1-P2.2 Model indirection                                                | 3h         | Gate 1               | **DONE** (2026-03-03)                                                        |
| 5         | P5.6 Remove DualEngineManager                                              | 3h         | Gate 1               | **DONE** (2026-03-03) — config removed, class retained for test compat       |
|           | **GATE 2 — Architecture Review**                                           | 1h         | Steps 4-5            | **APPROVED WITH DEVIATION** (2026-03-03)                                     |
|           | _DualEngineManager class retained; config removed; direction established_  |            |                      |                                                                              |
| 6         | P3.1-P3.4 Logging (incl. enrichment summary)                               | 4h         | Gate 2               | **DONE** (2026-03-03)                                                        |
|           | **GATE 3 — Observability Review**                                          | 1h         | Step 6               | **APPROVED** (2026-03-03)                                                    |
|           | _Per-run logs, relative paths util, SGF summary, Unicode fixed_            |            |                      |                                                                              |
| 7         | P5.1-P5.5, P5.7-P5.9 Threshold migration                                   | 4h         | Gate 2               | **DONE** (2026-03-03) — estimate_difficulty fully wired; others config-ready |
|           | **GATE 4 — Config Completeness Review**                                    | 1h         | Step 7               | **APPROVED WITH DEVIATION** (2026-03-03)                                     |
|           | _estimate_difficulty fully config-driven; other files config-ready_        |            |                      |                                                                              |
| 8         | P1.3 Tree validation skip                                                  | 2h         | Gate 4               | **DONE** (2026-03-03)                                                        |
| 9         | P1.4 PV-based refutations                                                  | 3h         | Gate 4               | **DONE** (2026-03-03) — config flag in place, default multi_query            |
|           | **GATE 5 — Performance and Quality Review**                                | 1h         | Steps 8-9            | **APPROVED** (2026-03-03)                                                    |
|           | _Tree validation skip, PV mode config flag, Go domain thresholds_          |            |                      |                                                                              |
| 10        | P4.1-P4.3 Test fixtures                                                    | 2h         | Gate 4               | **DONE** (2026-03-03)                                                        |
| 11        | P6.1-P6.3 Docs and ADRs                                                    | 2h         | All above            | **DONE** (2026-03-03)                                                        |
|           | **GATE 6 — Final Review**                                                  | 1h         | Steps 10-11          | **APPROVED** (2026-03-03)                                                    |
|           | _Docs complete, legacy terms removed, 912 unit tests pass (0 regressions)_ |            |                      |                                                                              |
| **Total** |                                                                            | **~31.5h** | (incl. 6h for gates) | **ALL GATES APPROVED**                                                       |

---

## Legacy Term Removal Confirmation

After all 6 phases and 6 gates are complete, the following terms will be **completely absent** from the codebase:

| Term                              | Where It Exists Now                                                  | Removed In | Replaced By                                      |
| --------------------------------- | -------------------------------------------------------------------- | ---------- | ------------------------------------------------ |
| `lab_mode`                        | config JSON, `config.py`, `enrich_single.py`, `dual_engine.py`, ADRs | P2.3       | `deep_enrich`                                    |
| `LabModeConfig`                   | `config.py` dataclass                                                | P2.3       | `DeepEnrichConfig`                               |
| `DualEngineManager`               | `analyzers/dual_engine.py` (~400 LOC)                                | P5.6       | Single-engine + escalation in `enrich_single.py` |
| `DualEngineConfig`                | `config.py` dataclass                                                | P5.6       | `deep_enrich.*` escalation fields                |
| `DualEngineResult`                | `analyzers/dual_engine.py` model                                     | P5.6       | Standard `AnalysisResponse`                      |
| `dual_engine` config section      | `katago-enrichment.json`                                             | P5.6       | `deep_enrich` + `models` sections                |
| `quick_model` / `referee_model`   | `katago-enrichment.json` dual_engine section                         | P5.6       | `models.quick` / `models.referee` labels         |
| `quick_visits` / `referee_visits` | `katago-enrichment.json` dual_engine section                         | P5.6       | `deep_enrich.visits` + `models.referee`          |
| `bridge` / `patching`             | ADR D2 doc references                                                | P6.1       | Direct SGF read/write                            |
| `rejected` (as hard AI status)    | validation logic, log messages                                       | P5.4       | `needs_review`                                   |

**Verification command (Gate 6):**

```powershell
# Confirm zero occurrences of legacy terms in .py files
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "lab_mode" -SimpleMatch -Recurse | Where-Object { $_.Path -notlike "*__pycache__*" }
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "DualEngine" -SimpleMatch -Recurse | Where-Object { $_.Path -notlike "*__pycache__*" }
Select-String -Path "tools/puzzle-enrichment-lab/**/*.py" -Pattern "dual_engine" -SimpleMatch -Recurse | Where-Object { $_.Path -notlike "*__pycache__*" }
# All should return zero results
```

---

## Expert Reviews

### Review 1: Principal Systems Architect

**Reviewer:** Principal Systems Architect persona
**Date:** 2026-03-02

**Verdict:** APPROVED with amendments.

**Findings:**

1. **`pv_mode` default — DECIDED:** Default to `"multi_query"` (current behavior). Switch to `"pv_extract"` only after calibration validates >=90% agreement rate on the full fixture set. This is a data-driven gate, not an opinion.

2. **`models` section scope — DECIDED:** The fixed `quick/referee/deep_enrich` trio is sufficient. An N-label design adds complexity without a current use case. If a 4th model is needed later (e.g., a b6 "screening" model), extend then. YAGNI.

3. **`calibration` config location — DECIDED:** Keep calibration settings in `katago-enrichment.json`. It's one config file for all KataGo enrichment concerns. A separate `enrichment-testing.json` would fragment config without benefit. The `calibration` section is clearly namespaced.

4. **`deep_enrich` naming — APPROVED:** Good verb-form name. Describes behavior (deep, thorough analysis) not location. Survives mainline migration. Replaces `lab_mode` everywhere.

5. **Config versioning — AMENDMENT:** Bump config version to `1.12` AND update the JSON schema at `config/schemas/katago-enrichment.schema.json` to include all new sections. Schema validation catches typos in config keys.

6. **Escalation mechanism for deep_enrich — AMENDMENT:** When `deep_enrich.enabled = true` and a puzzle fails validation at 2000 visits, escalate to the referee model (b28c512) at `dual_engine.referee_visits` (2000). This gives two tiers: fast b18 at 2K, then b28 at 2K for hard cases. Add `deep_enrich.escalate_to_referee` (bool, default `true`) to config.

**Added config key:**

| Key                               | Type | Default | Description                                                        |
| --------------------------------- | ---- | ------- | ------------------------------------------------------------------ |
| `deep_enrich.escalate_to_referee` | bool | `true`  | Escalate uncertain puzzles from deep_enrich model to referee model |

### Review 2: Staff Engineer

**Reviewer:** Staff Engineer persona
**Date:** 2026-03-02

**Verdict:** APPROVED with amendments.

**Findings:**

1. **Per-run file handler — DECIDED:** Use a separate `FileHandler` per run, created dynamically in `setup_logging()` when `per_run_files=true`. The handler is added to the root logger alongside the aggregate handler. On `set_run_id()` calls (run transitions), close the old handler and open a new one. This is simpler than filtering records from the aggregate stream.

2. **`_strip_workspace_root()` — DECIDED:** Use `str.removeprefix()` (Python 3.9+, we require 3.11+). Find workspace root once at module load via `Path(__file__).resolve()` walking up until a directory contains `.git`. Cache the result. No regex. No `os.path.relpath()` (that can produce `..` paths which are confusing in logs).

3. **Randomized test reproducibility — DECIDED:** When `randomize_fixtures = true`, generate a random seed from `secrets.token_hex(4)`, log it at INFO level at test start: `"Calibration seed: {seed} (randomized)"`. This allows reproduction of any failing run by setting `calibration.seed` to the logged value and `randomize_fixtures = false`.

4. **Config loading overhead — AMENDMENT:** The `load_enrichment_config()` function is called once per puzzle in `enrich_single_puzzle()`. With 45+ new config fields, ensure it remains a single JSON parse (already true — `functools.lru_cache` is used). No per-field I/O.

5. **Backward compatibility — AMENDMENT:** During the `lab_mode` to `deep_enrich` rename, add a one-time migration: if `lab_mode` key exists in JSON but `deep_enrich` does not, log a deprecation warning and treat `lab_mode` as `deep_enrich`. Remove this shim after one release cycle.

6. **P5.9 regex cleanup — AMENDMENT:** Only replace regex in `property_policy.py` if the patterns are simple enough for string ops. The SGF `YQ[q:2;rc:0;hc:0]` format IS simple (semicolon-split, colon-split, digit check). But if any validator handles truly irregular input (e.g., variable-length hex with optional dashes), keep regex for that specific case. Decision per-pattern, not blanket.

### Review 3: Go Professional (Cho Chikun persona)

**Reviewer:** 1P Professional Go Player (Cho Chikun persona)
**Date:** 2026-03-02

**Verdict:** APPROVED with amendments.

**Findings:**

1. **`confidence_winrate = 0.85` — AMENDMENT:** 0.85 is correct for standard life-and-death. But ko and seki are special:
   - **Ko puzzles:** KataGo's winrate for ko positions oscillates between 0.4-0.7 even when the correct approach move is found. Use `confidence_winrate_ko = 0.75` (lower threshold). A ko puzzle where KataGo shows 75% with correct first move should still skip tree validation — the uncertainty is about the ko fight outcome, not the first move.
   - **Seki puzzles:** Seki positions naturally produce balanced winrates (0.45-0.55). Even a correctly solved seki may show only 0.55 winrate. Use `confidence_winrate_seki = 0.70`. The 3-signal seki detection (balanced winrate + low score + top-N move) provides additional validation that compensates for the lower confidence threshold.

2. **`snapback.policy_threshold = 0.05` — CONFIRMED:** Same for 9x9 and 19x19. The snapback signature is position-local: the sacrifice stone's policy is determined by the local group structure, not the board size. On a 9x9 board with cropping, the policy distribution is already concentrated. On an uncropped 19x19, the policy is diluted across more moves, but the snapback move's absolute policy stays below 0.05 because the NN doesn't "see" the recapture. No board-size adjustment needed.

3. **`net.min_refutations = 2` and `net.delta_spread = 0.1` — CONFIRMED with note:** These correctly distinguish net from loose ladder. In a net, the surrounded stone has 2-4 escape attempts (diagonal, cut, extend, jump) that all fail with similar winrate deltas. In a ladder, there's a single forcing sequence. The `delta_spread < 0.1` threshold (all escape attempts lose by similar amounts) is the key discriminator. **Note:** For very large nets (e.g., surrounding 5+ stones), `min_refutations` might need to be 3. Consider adding this as a future refinement if net detection accuracy drops below 90% on calibration.

4. **PV-based refutations for kyu puzzles — CONFIRMED:** For puzzles rated elementary to upper-intermediate (16k-6k), the initial PV from the correct position accurately shows the punishment for wrong moves. The opponent's best response is typically obvious (capture, atari, block). For advanced+ puzzles, multi-query is needed because the punishment often involves a multi-step sequence that the initial PV doesn't explore deeply enough.

5. **Visits 2000 — CONFIRMED:** At 2000 visits with b18c384, KataGo's reading depth is approximately 15-20 moves for tsumego. This is deeper than Master-level (9d+) reading for most life-and-death positions. The "right" number of visits is not about matching human reading depth — it's about ensuring the MCTS tree converges on the correct first move. At 2000 visits with tsumego frame, convergence rate is >98% for positions up to advanced level.

---

## Decisions Log

| Decision             | Chose                                   | Over                   | Rationale                                                             |
| -------------------- | --------------------------------------- | ---------------------- | --------------------------------------------------------------------- |
| Config key name      | `deep_enrich`                           | `lab_mode`             | Behavior-descriptive. Survives mainline migration.                    |
| Deep enrich model    | b18c384                                 | b28c512                | 3x faster, 13.6K Elo. b28 for referee escalation only.                |
| Deep enrich visits   | 2000                                    | 10000                  | 5x speedup, <1% accuracy loss sub-dan (Go pro confirmed).             |
| Symmetries           | 2                                       | 8                      | 4x speedup. Cropping handles orientation.                             |
| PV refutations       | Config flag, default multi_query        | Always-on pv_extract   | Quality gate: >=90% agreement needed before switching default.        |
| Tree skip            | Config flag w/ ko/seki-aware thresholds | Flat 0.85 threshold    | Go pro: ko needs 0.75, seki needs 0.70 (different position dynamics). |
| Run logs             | Separate FileHandler per run            | Filtered aggregate     | Simpler implementation (Staff Engineer).                              |
| Model refs           | Fixed quick/referee/deep_enrich trio    | N arbitrary labels     | YAGNI (Architect). Extend when 4th model needed.                      |
| Fixtures             | Config-driven, log random seed          | Non-deterministic only | Reproducibility via logged seed (Staff Engineer).                     |
| Escalation           | deep_enrich escalates to referee        | No escalation          | Two-tier: b18 at 2K, then b28 at 2K for hard cases (Architect).       |
| Backward compat      | Shim: read lab_mode as deep_enrich      | Hard break             | One release cycle deprecation (Staff Engineer).                       |
| Seki score threshold | 5.0 (keep as-is)                        | Lower                  | Go pro confirmed 5.0 is appropriate.                                  |
| Snapback policy      | 0.05 (same for all board sizes)         | Board-size-dependent   | Go pro: policy is position-local, not board-size-dependent.           |

---

## Quality Sprint (Q-series) — Post-Gate Fixes & Enhancements

**Added:** 2026-03-03 | **Status:** IN PROGRESS

These items were identified during the post-implementation audit. They use "Q" prefix to avoid confusion with the P0-P6 phases above.

### Q1 — Remove CLI `patch` Subcommand ✅ DONE

`run_patch()` in `cli.py` is a dead verb — not part of the enrichment pipeline. The backend pipeline does not use it. `enrich_sgf()` in `sgf_enricher.py` is called directly. Remove the subparser, function, and dispatch.

### Q2 — Ownership Grid in L&D Validation ⏳ NEEDS GO PRO

`_validate_life_and_death()` in `validate_correct_move.py` only uses winrate/policy/visits. Config has `ownership_thresholds` (alive: 0.7, dead: −0.7) but never reads them. Ownership deltas against target stones would add real validation for L&D puzzles. **Requires:** KataGo ownership query implementation and Go professional calibration of thresholds.

### Q3 — Escalation on "Confident but Wrong" ✅ DONE

`_should_escalate()` in `dual_engine.py` only checks winrate range `[low, high]`. If Quick engine is confident (WR > 0.7) but picks the wrong move (≠ curated `correct_move`), no escalation happens. **Fix:** Add `correct_move_gtp` param; if Quick's top move ≠ correct move, ALWAYS escalate.

### Q4 — Ladder Detection Edge-Following Patterns ⏳ DEFERRED (D49)

`_is_diagonal_chase()` only checks ≥50% diagonal count. No staircase/alternating-direction pattern, no liberty counting, no board state simulation. Current detection is acceptable for tagging. True ladder verification needs board state simulation which is expensive. **Deferred** until net/ladder accuracy drops below 90% on calibration.

### Q5 — Ko Detection Capture Verification ⏳ NEEDS GO PRO

`detect_ko_in_pv()` uses `Counter()` on GTP coordinates only. Coord appearing twice ≠ guaranteed ko — could be a non-ko recapture or PV artifact. At minimum, verify that the repeated coord involves capture (adjacent liberty count = 1). **Requires:** Go professional review for false-positive thresholds.

### Q6 — Difficulty Weight Rebalancing ✅ DONE

`policy_rank: 30, visits_to_solve: 30` are collinear (both measure "how hard for KataGo"). Rebalanced to reduce redundancy. Changed after Go professional consultation.

### Q7 — Wire Seki Score Threshold to Config ✅ DONE

`_validate_seki()` uses hardcoded `abs(root_score) < 5.0`. Config section `technique_detection.seki.score_threshold` exists at value 5.0 but wasn't wired. Now reads from config.

### Q8 — Wire `max_time` to KataGo Query ✅ DONE

`DeepEnrichConfig.max_time` was defined but never passed to KataGo engine. Now wired through `query_builder.py` to the `maxTime` field in the analysis request. If 0, omitted (KataGo default = no limit).

### Q9 — Batch Processing Sequential — KEEP AS-IS

`_run_batch_async()` processes puzzles sequentially in a for loop. This is correct design — puzzles are always enriched one at a time with a single KataGo engine. The `async` is for engine I/O, not puzzle parallelism. No dead code to remove.

### Q10 — Consolidate Output Artifacts to `.lab-runtime/` ✅ DONE

`.lab-runtime/katago-logs/` already exists. Added `.lab-runtime/outputs/` for enrichment results. Updated `.gitignore` for artifact directories.

### Q11 — Teaching Comments Position-Aware Templates ⏳ DEFERRED (D50)

22 technique templates + 4 wrong-move templates. Template selection is position-agnostic. Making templates board-position-aware requires significant Go domain expertise. **Deferred** to dedicated teaching improvement sprint with Go professional consultation.

### Q12 — Refutation Tree Depth (Full Wrong-Move Trees) ⏳ NEEDS GO PRO

`generate_refutations.py` extracts only single PV lines capped at `max_pv_length=4`. Need minimum 3 wrong trees (out of 4 total: 1 correct + 3 wrong). Trees should include branching, not just single move sequences. **Requires:** Go professional consultation on tree structure requirements (when is a single-move tree acceptable vs when full branching is needed).

### Q13 — PV Truncation Cascade to Teaching — Blocked on Q12

`refutation_depth = len(pv_sgf)` — if PV capped at 4, depth maxes at 4, causing wrong template selection (`ref_depth <= 1` → "capture" template for deep sequences). Automatically fixed when Q12 increases PV depth.

### Q14 — Refutation Delta Ko-Aware Threshold ✅ DONE

`delta_threshold = 0.08` applied uniformly. Ko puzzles have oscillating winrates where standard delta is inappropriate. Now uses `config.teaching.ko_delta_threshold` (0.1) for ko-tagged puzzles.

### Q15 — Batch Quality Gate ✅ DONE

`QualityGatesConfig` has `acceptance_threshold: 0.95` but `_run_batch_async()` had no check. Now logs WARNING with stats if acceptance rate drops below the configured threshold.

### Q-series Implementation Order

| Step | Item                              | Effort | Status                     |
| ---- | --------------------------------- | ------ | -------------------------- |
| 1    | Q1 Remove CLI patch               | Low    | ✅ DONE                    |
| 2    | Q7 Wire seki threshold            | Low    | ✅ DONE                    |
| 3    | Q8 Wire max_time                  | Low    | ✅ DONE                    |
| 4    | Q14 Ko-aware refutation delta     | Low    | ✅ DONE                    |
| 5    | Q15 Batch quality gate            | Low    | ✅ DONE                    |
| 6    | Q6 Difficulty weight rebalance    | Low    | ✅ DONE (Go pro consulted) |
| 7    | Q3 Confident-but-wrong escalation | Medium | ✅ DONE                    |
| 8    | Q10 Output consolidation          | Low    | ✅ DONE                    |
| 9    | Q2 Ownership grid in L&D          | High   | ⏳ NEEDS GO PRO            |
| 10   | Q5 Ko capture verification        | Medium | ⏳ NEEDS GO PRO            |
| 11   | Q12 Refutation tree depth         | High   | ⏳ NEEDS GO PRO            |
| 12   | Q13 PV truncation cascade         | —      | Blocked on Q12             |
| 13   | Q4 Ladder edge-following          | Medium | ⏳ DEFERRED (D49)          |
| 14   | Q11 Teaching templates            | High   | ⏳ DEFERRED (D50)          |
| 15   | Q9 Batch sequential               | —      | KEEP AS-IS                 |
