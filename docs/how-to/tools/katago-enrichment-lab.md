# How-To: KataGo Puzzle Enrichment Lab

**Last Updated:** 2026-03-24

---

## Prerequisites

1. **KataGo binary** — `tools/puzzle-enrichment-lab/katago/katago.exe` (Windows) or equivalent
2. **Neural net model** — at least one `.bin.gz` file in `tools/puzzle-enrichment-lab/models-data/`:
   - `b6c96` (~3.7 MB) — smallest, browser-suitable
   - `b10c128` (~10.6 MB) — quick engine
   - `b15c192` (~35 MB) — recommended for production
   - `b28c512` (~260 MB) — strongest, referee engine
3. **Python 3.11+** with dependencies installed (`pip install -r requirements.txt`)
4. **Puzzle SGF files** in `.pm-runtime/staging/analyzed/` (produced by pipeline analyze stage)

## Quick Start

### 1. Verify KataGo Works

```bash
cd tools/puzzle-enrichment-lab
katago/katago.exe analysis -config katago/tsumego_enrichment.cfg -model models-data/b15c192.bin.gz
```

Send a test query (paste into stdin):

```json
{
  "id": "test",
  "initialStones": [
    ["B", "C3"],
    ["B", "D3"],
    ["W", "C4"],
    ["W", "D4"]
  ],
  "rules": "chinese",
  "komi": 0,
  "boardXSize": 19,
  "boardYSize": 19,
  "analyzeTurns": [0],
  "maxVisits": 100,
  "includeOwnership": true,
  "includePolicy": true
}
```

You should see a JSON response with `moveInfos`, `rootInfo`, `ownership`, and `policy`.

### 2. Run Batch Enrichment

```bash
# Enrich all SGFs in a directory
python tools/puzzle-enrichment-lab/cli.py batch \
  --input-dir .pm-runtime/staging/analyzed/ \
  --output-dir enrichment-output/ \
  --katago tools/puzzle-enrichment-lab/katago/katago.exe
```

### 3. Enrich a Single Puzzle

```bash
python tools/puzzle-enrichment-lab/cli.py enrich \
  --sgf path/to/puzzle.sgf \
  --output result.json \
  --emit-sgf enriched.sgf \
  --katago tools/puzzle-enrichment-lab/katago/katago.exe
```

### 4. Apply Enrichment Results to SGF

```bash
python tools/puzzle-enrichment-lab/cli.py apply \
  --sgf path/to/puzzle.sgf \
  --result result.json \
  --output enriched.sgf
```

### 5. Validate a Single Puzzle

```bash
python tools/puzzle-enrichment-lab/cli.py validate \
  --sgf path/to/puzzle.sgf \
  --katago tools/puzzle-enrichment-lab/katago/katago.exe
```

### 6. Visual GUI Mode (Pipeline Observer)

The `--gui` flag on the `enrich` command launches a visual pipeline observer — a web UI where you can watch each enrichment step in real time, interact with the board, and verify enrichment quality visually.

#### Start the GUI

```bash
# Terminal 1: Start Python bridge server + enrichment pipeline
python tools/puzzle-enrichment-lab/cli.py enrich \
  --sgf path/to/puzzle.sgf \
  --output result.json \
  --emit-sgf enriched.sgf \
  --katago tools/puzzle-enrichment-lab/katago/katago.exe \
  --gui

# Terminal 2: Start Vite dev server (first time: run npm install)
cd tools/puzzle-enrichment-lab/gui
npm install   # only needed once
npm run dev
# → Opens at http://localhost:5173 (proxies /api to bridge on :8999)
```

The `--gui` flag starts the FastAPI bridge server (`bridge.py`) as a subprocess on port 8999. The Vite dev server proxies `/api/*` requests to the bridge.

#### What the GUI shows

- **PipelineStageBar** — 9-stage progress bar (Parse → Teaching) with real-time status via SSE
- **GoBoard** — Interactive board; read-only during pipeline observation, click-to-play after completion
- **MoveTree** — Color-coded nodes: green (correct), red (wrong), orange (refutation)
- **Eval/ownership overlays** — Same visualizations as web-katrain (winrate, score graph, PV overlay)

#### Observation mode

While the pipeline is running, the board enters **observation mode** (`isObserving=true`):

- Board updates reflect each pipeline stage automatically
- Click-to-play is disabled to prevent conflicts with SSE updates
- Once the pipeline completes, full interactivity is restored

#### Bridge server standalone

You can also start the bridge server directly for interactive analysis without running the full pipeline:

```bash
cd tools/puzzle-enrichment-lab
python -m gui.bridge --katago katago/katago.exe --port 8999
```

### Exit Codes

| Code | Meaning                                             |
| :--: | --------------------------------------------------- |
|  0   | ACCEPTED — puzzle validated successfully            |
|  1   | ERROR/REJECTED — pipeline failure or invalid puzzle |
|  2   | FLAGGED — puzzle needs human review                 |

### Configuration Overrides (Python vs KataGo)

The CLI accepts two different configuration flags that serve distinct purposes:

1. **`--config`**: Expects a `.json` file that configures the Python enrichment pipeline (default: `config/katago-enrichment.json`).
2. **`--katago-config`**: Expects a `.cfg` file that configures the KataGo engine behavior itself. If omitted, it auto-detects `tsumego_analysis.cfg` next to the `katago` binary.

> ⚠️ **Common Error**: Passing `katago/tsumego_analysis.cfg` to `--config` will result in a `json.decoder.JSONDecodeError` because the Python JSON loader cannot parse KataGo's `.cfg` format. Be sure to use `--katago-config` for KataGo configuration files.

```bash
# Use custom configurations for both the Python pipeline and KataGo engine
python tools/puzzle-enrichment-lab/cli.py enrich \
  --sgf puzzle.sgf --output result.json \
  --katago path/to/katago \
  --config custom-config.json \
  --katago-config katago/tsumego_analysis.cfg
```

## Interpreting Results

### Enrichment JSON Output

Each puzzle produces a JSON file with:

```json
{
  "puzzle_id": "YENGO-765f38a5196edb79",
  "engine": { "model": "b15c192", "visits": 200, "symmetries": 8 },
  "validation": {
    "correct_moves_validated": true,
    "value_after_correct": 0.92,
    "ownership_confirms": true
  },
  "refutations": [...],
  "difficulty": {
    "policy_prior_correct": 0.12,
    "visits_to_solve": 85,
    "trap_density": 0.67,
    "composite_score": 5.2,
    "suggested_level": "upper-intermediate"
  }
}
```

### Difficulty Level Mapping

| Composite Score |    Yen-Go Level    |
| :-------------: | :----------------: |
|    0.0 – 1.0    |       novice       |
|    1.0 – 2.0    |      beginner      |
|    2.0 – 3.0    |     elementary     |
|    3.0 – 4.0    |    intermediate    |
|    4.0 – 5.0    | upper-intermediate |
|    5.0 – 6.0    |      advanced      |
|    6.0 – 7.0    |      low-dan       |
|    7.0 – 8.0    |      high-dan      |
|      8.0+       |       expert       |

## Troubleshooting

### KataGo fails to start

- Check that the model file exists and is not corrupted
- Verify GPU drivers are up to date (for OpenCL/CUDA builds)
- Try the Eigen (CPU) build if no GPU available

### Low accuracy results

- Verify tsumego frame is being applied (check logs for "frame applied")
- Increase visits: `--visits 800` or `--visits 2000`
- Use a stronger model label by updating `config/katago-enrichment.json` (`models.deep_enrich` / `models.referee`)
- Check komi is 0 (not 7.5)

### Slow batch processing

- Use single-engine processing and tune visits for throughput/quality tradeoffs with `--visits`
- Use config-driven visit escalation thresholds to keep deeper analysis only for uncertain puzzles
- Use GPU builds for 10-100x speedup over CPU
- Start with lower visits for speed, then increase only when needed for stability

## Changing Models

All model references use **label indirection** via `config/katago-enrichment.json` `models` section (ADR D42). Code never references model filenames directly.

### Available model labels

| Label         | Default Arch | Use Case                              |
| ------------- | ------------ | ------------------------------------- |
| `quick`       | b18c384      | Fast first-pass analysis (500 visits) |
| `referee`     | b28c512      | Deep analysis for uncertain puzzles   |
| `deep_enrich` | b18c384      | Full enrichment (2000 visits)         |
| `test_fast`   | b10c128      | Integration tests only                |

### Switching models

1. Download the new model to `tools/puzzle-enrichment-lab/models-data/`
2. Update `config/katago-enrichment.json` → `models.<label>.filename` and `models.<label>.arch`
3. Re-run calibration to validate accuracy: `python -m pytest tests/test_calibration.py -v -s`

No Python code changes are needed — the model path is resolved from config at runtime.

## Performance Tuning

Key parameters in `config/katago-enrichment.json` → `deep_enrich` section:

| Parameter                       | Default | Effect                                                  |
| ------------------------------- | ------- | ------------------------------------------------------- |
| `visits`                        | 2000    | MCTS search depth. Higher = more accurate, slower.      |
| `root_num_symmetries_to_sample` | 2       | Board symmetries evaluated. 8 = thorough but 4x slower. |
| `model`                         | b18c384 | Model architecture. b28 is stronger but 3x slower.      |
| `max_time`                      | 0       | Per-query time limit (0 = unlimited).                   |

### Tree validation skip

When `tree_validation.skip_when_confident = true` (default), puzzles where KataGo's top-1 move matches with winrate >= 0.85 skip deep tree validation. This saves 3-7 engine calls for ~70% of puzzles. Ko puzzles use a lower threshold (0.75), seki uses 0.70.

### Escalation

When `deep_enrich.escalate_to_referee = true`, uncertain puzzles (winrate 0.3-0.7) are re-analyzed with the stronger referee model. Disable for faster but less accurate results.

## Reading Enrichment Logs

### Log locations

- **Per-run log**: `.lab-runtime/logs/{run_id}_enrichment.log` — contains only records from that run
- **Aggregate log**: `.lab-runtime/logs/enrichment.log` — rotating log across all runs

### Log format

Logs use structured JSON format with fields: `time`, `level`, `logger`, `run_id`, `msg`, plus any extra fields.

### Key log messages

| Message Pattern            | Level   | Meaning                                                                  |
| -------------------------- | ------- | ------------------------------------------------------------------------ |
| `Puzzle start:`            | INFO    | Enrichment beginning — shows puzzle_id, source, board_size, player       |
| `Post-analysis:`           | INFO    | KataGo analysis complete — correct_move, winrate, policy, visits, model  |
| `Enrichment complete:`     | INFO    | Full SGF property summary — yg, yt, yq, yx, yr, yk, yo, yh_count         |
| `Level mismatch:`          | WARNING | YG differs from KataGo estimate — original_level, katago_level, distance |
| `Tree validation skipped:` | INFO    | Confident skip — winrate above threshold                                 |
| `Refutation escalation:`   | INFO    | Retrying with higher visits                                              |

### Path format

All paths in logs are relative to the workspace root (e.g., `tools/puzzle-enrichment-lab/...`) when `logging.use_relative_paths = true` in config.

## Adding Calibration Fixtures

### From existing collections

Use the hydration script:

```bash
python scripts/hydrate_calibration_fixtures.py \
    --source-dir ../../external-sources/yengo-source/sgf \
    --target-dir tests/fixtures/calibration/yengo-source-elementary \
    --level elementary \
    --count 10
```

The script:

- Reads YG property from each SGF to find matching puzzles
- Samples randomly (seed-controlled for reproducibility)
- Never overwrites existing Cho Chikun fixtures (protected prefix `cho-`)

### Configuring fixture directories

Add new directories to `config/katago-enrichment.json` → `calibration.fixture_dirs`:

```json
{
  "calibration": {
    "fixture_dirs": [
      "cho-elementary",
      "cho-intermediate",
      "cho-advanced",
      "yengo-source-elementary"
    ],
    "sample_size": 5,
    "randomize_fixtures": true,
    "restart_every_n": 10
  }
}
```

Tests will automatically include puzzles from all listed directories.

### Randomized fixtures

Set `calibration.randomize_fixtures = true` (v1.27 default) to pick a different random subset each run. The actual seed used is logged for reproducibility. Set `randomize_fixtures = false` with a fixed `seed` for deterministic, reproducible runs.

---

## Running Calibration

Calibration validates that the enrichment pipeline produces correct results on known puzzle collections. There are two ways to run it: the **CLI script** (recommended for manual runs) and **pytest** (for CI/automated checks).

### Engine Modes

| Mode | Flag | Visits | Escalation | Speed | When to Use |
|------|------|--------|------------|-------|-------------|
| **Quick-only** | `--quick-only` | 500, capped | Disabled — no referee re-analysis | Fast | Calibration, smoke tests, iGPU |
| **Default** | _(no flag)_ | 500 base, escalates to 2000+ | Enabled — uncertain puzzles re-analyzed with more visits | Slower | Production enrichment |

> **What is `--quick-only`?** It is NOT a different model. It uses the same KataGo binary and the same neural net. The difference is analysis intensity: `--quick-only` caps visits at 500 with 2 symmetries and disables referee escalation (the automatic re-analysis of uncertain positions with deeper search). For calibration you're validating pipeline correctness, not production accuracy, so `--quick-only` is recommended.

### Engine Restart (iGPU crash mitigation)

On Intel integrated GPUs (e.g., Iris Xe), KataGo's OpenCL backend can crash after processing many puzzles (driver bug, exit code `0xC0000005`). The `restart_every_n` setting periodically restarts the engine to give the GPU a fresh OpenCL context.

- **Default**: restart every 10 puzzles (~1–2% overhead)
- **Disable**: `--restart-every-n 0`
- **More frequent**: `--restart-every-n 5` (for unstable drivers)

### CLI Script: `run_calibration.py`

Run from `tools/puzzle-enrichment-lab/`:

```bash
cd tools/puzzle-enrichment-lab
```

#### All defaults (config-driven)

```bash
python scripts/run_calibration.py --quick-only
```

Reads `fixture_dirs`, `sample_size` (default 5 per collection), and `seed`/`randomize_fixtures` from `config/katago-enrichment.json`. With 3 collections × 5 puzzles = 15 puzzles total. Random sampling by default (v1.27).

#### Custom sample size

```bash
# 15 puzzles per collection = 45 total
python scripts/run_calibration.py --quick-only --sample-size 15
```

#### Deterministic mode (reproducible)

```bash
# Fixed seed → same puzzles every run
python scripts/run_calibration.py --quick-only --sample-size 10 --seed 42
```

#### Process all files from a specific directory

```bash
# Bypass config sampling — run every SGF in the directory
python scripts/run_calibration.py --quick-only --input-dir tests/fixtures/calibration/cho-elementary
```

#### Limit total puzzles

```bash
python scripts/run_calibration.py --quick-only --limit 20
```

#### Full custom example

```bash
python scripts/run_calibration.py --quick-only \
  --sample-size 20 --seed 42 \
  --restart-every-n 8 \
  --run-label "v127-validation" \
  -v
```

#### All CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `--input-dir` | _(from config)_ | Directory with SGFs; overrides config `fixture_dirs` |
| `--output-dir` | _(from config)_ | Where to write results |
| `--run-label` | `""` | Label for this calibration run |
| `--sample-size` | _(from config, default 5)_ | Puzzles per collection |
| `--seed` | _(random)_ | Random seed; implies deterministic mode |
| `--quick-only` | off | Use quick mode (500 visits, no escalation) |
| `--restart-every-n` | _(from config, default 10)_ | Restart engine every N puzzles; 0 = never |
| `--retry-rejected` | on | Retry rejected puzzles with referee engine |
| `--no-retry-rejected` | — | Disable retry of rejected puzzles |
| `--retry-skip-refutations` | 4 | Skip retry if puzzle has ≥ N refutations |
| `--limit` | 0 | Max puzzles to process (0 = all) |
| `--katago` | _(from config)_ | Path to KataGo binary |
| `--quick-model` | _(from config)_ | Path to quick model file |
| `--referee-model` | _(from config)_ | Path to referee model file |
| `--katago-config` | _(from config)_ | Path to KataGo `.cfg` file |
| `-v` / `--verbose` | off | Enable DEBUG logging |

#### Calibration Output

Results are written to the output directory (default: `.lab-runtime/calibration-results/`):

- One JSON file per puzzle with enrichment results
- Console summary: accepted/rejected/flagged counts, pass rate
- Logs include the random seed used (for reproducibility)

### Pytest: `test_calibration.py`

For automated/CI use. Reads all settings from `config/katago-enrichment.json`:

```bash
cd tools/puzzle-enrichment-lab
python -m pytest tests/test_calibration.py -v --tb=short
```

The pytest path has no CLI overrides — to change `sample_size`, `seed`, or `randomize_fixtures`, edit the config file directly. The test class `TestCalibrationChoCkikun` processes each configured collection and asserts enrichment quality thresholds.

### Quick Reference

| What | Config default | CLI override |
|------|---------------|--------------|
| Puzzles per collection | 5 | `--sample-size N` |
| Collections | cho-elementary, cho-intermediate, cho-advanced | `--input-dir <path>` or edit `fixture_dirs` |
| Sampling mode | Random (v1.27) | `--seed N` for deterministic |
| Engine restart | Every 10 puzzles | `--restart-every-n N` (0=never) |
| Engine mode | Quick + referee escalation | `--quick-only` for quick only |
| Puzzle limit | All sampled | `--limit N` |

---

## Running Technique Calibration

Technique calibration validates that each of the 25 technique tags produces correct enrichment results. Unlike difficulty calibration (which tests score accuracy across a reference collection), technique calibration tests **per-tag quality gates** across 5 dimensions: correct move, technique tags, difficulty range, refutations, and teaching comments.

> **See also:** [Concepts: Technique Calibration](../../concepts/technique-calibration.md) — full architecture and dimension definitions

### Quick start

```bash
cd tools/puzzle-enrichment-lab

# Unit tests only (no KataGo needed, ~1s)
pytest tests/test_technique_calibration.py -m unit -v

# Full calibration with live KataGo (~5–10 min)
pytest tests/test_technique_calibration.py -v --tb=short

# Single technique
pytest tests/test_technique_calibration.py -k "snapback" -v
```

### When to run

| Situation | Run technique calibration? |
|-----------|---------------------------|
| Changed a technique detector | Yes — validates detection accuracy |
| Changed difficulty algorithm | No — use `test_calibration.py` instead |
| Added/replaced a technique fixture | Yes — validates new fixture works |
| Changed enrichment pipeline stages | Yes — end-to-end quality check |
| Routine pre-merge | No — unit tests + golden5 are sufficient |

### Adding a new technique entry

When adding a new calibration entry (e.g., after replacing a fixture):

1. Place the SGF fixture in `tests/fixtures/`
2. Determine the correct first move in GTP format (e.g., "B2")
3. Add a `TechniqueSpec` entry to the `TECHNIQUE_REGISTRY` dict in `test_technique_calibration.py`
4. Set `expected_tags`, difficulty range (`min_level_id`/`max_level_id`), `min_refutations`, and `expect_teaching_comments`
5. Run: `pytest tests/test_technique_calibration.py -k "your_tag" -v`

### Test markers

Technique calibration tests use these markers:
- `@pytest.mark.unit` — 3 cross-check tests (no KataGo)
- `@pytest.mark.slow` + `@pytest.mark.integration` — 5 × 25 parametrized integration tests

---

## Pre-Query Terminal Detection

The solution tree builder includes two algorithmic gates that fire before each KataGo engine query, eliminating unnecessary queries for positions with deterministic outcomes.

### Benson Gate (Unconditional Life)

When the defender's contest group is unconditionally alive (two or more vital regions), the tree builder skips the engine query and returns a terminal node. This saves budget for deeper exploration elsewhere in the tree.

The gate is always active when board state tracking is enabled (`transposition_enabled: true`). No additional configuration is needed.

**What it detects:** Positions where the defender has provably made two eyes within the contest area, regardless of the attacker's moves.

**What it does NOT detect:** Seki (falls through to KataGo), ko-dependent life (falls through to KataGo), framework group life (ignored — only contest group membership triggers the gate).

### Interior-Point Death Check

When the defender has ≤ 2 empty interior points within the puzzle region with no two adjacent, the tree builder returns a terminal node (attacker wins). The geometric impossibility of forming two eyes makes the engine query unnecessary.

### Ko Capture Verification

When `initial_stones` is passed to `detect_ko_in_pv()`, the function replays the PV on a board to verify captures occur between repeated coordinates. This eliminates false positives from the adjacency-only proxy.

Without `initial_stones`, the function falls back to adjacency-based detection (backward compatible).

---

> **See also:**
>
> - [Architecture: KataGo Enrichment](../../architecture/tools/katago-enrichment.md) — design decisions
> - [Architecture: Enrichment Lab GUI](../../architecture/tools/enrichment-lab-gui.md) — GUI design decisions
> - [Reference: KataGo Enrichment Config](../../reference/katago-enrichment-config.md) — full configuration reference
> - [Concepts: Quality — Benson Gate](../../concepts/quality.md#benson-gate) — quality signals
> - [Concepts: Quality](../../concepts/quality.md) — AC quality levels
> - [Implementation Plan](../../../TODO/katago-puzzle-enrichment/006-implementation-plan-final.md) — task breakdown

## AI-Solve Unified Enrichment (v3)

AI-Solve extends the enrichment pipeline to handle **all puzzles** through AI analysis, whether they have existing solutions or not.

### Position-Only Workflow

For puzzles without an existing solution (no correct first move in SGF):

```bash
# Enable AI-Solve in config/katago-enrichment.json:
# "ai_solve": { "enabled": true, ... }

python tools/puzzle-enrichment-lab/cli.py batch \
  --input-dir position-only-sgfs/ \
  --output-dir enriched/ \
  --katago path/to/katago
```

The pipeline will:

1. Analyze the position to find candidate moves
2. Classify moves as correct/wrong using configurable thresholds
3. Build a recursive solution tree for the best correct move
4. Inject the solution tree into the SGF

### Has-Solution Workflow

For puzzles with existing solutions, AI-Solve validates and discovers alternatives:

1. Validates the human's correct move against KataGo's analysis
2. Discovers alternative correct moves (co-correct detection)
3. Builds trees for alternatives and injects them

### AC Quality Levels (DD-4)

The `ac_level` field in output (flows to `YQ` property as `ac:N`):

| Level | Name      | Meaning                                                       |
| :---: | --------- | ------------------------------------------------------------- |
|   0   | Untouched | AI pipeline not engaged, or enrichment failed                 |
|   1   | Enriched  | AI validated/enriched; has-solution path; or tree truncated   |
|   2   | AI Solved | Position-only path with complete, non-truncated solution tree |
|   3   | Verified  | Reserved for future manual verification                       |

### Observability (DD-11)

Batch runs emit a `BatchSummary` at the end with:

- AC level distribution, disagreement count/rate
- Per-collection disagreement monitoring with configurable WARNING threshold
- Disagreement records written to `.lab-runtime/logs/disagreements/{run_id}.jsonl`

## Kishimoto-Mueller Search Optimizations

The solution tree builder includes search optimizations adapted from Kishimoto & Müller (2005) and Thomsen (2000). All are config-driven and enabled by default.

### Config Knobs

Add or modify these fields under `ai_solve.solution_tree` in `config/katago-enrichment.json`:

```json
{
  "ai_solve": {
    "solution_tree": {
      "simulation_enabled": true,
      "simulation_verify_visits": 50,
      "transposition_enabled": true,
      "forced_move_visits": 125,
      "forced_move_policy_threshold": 0.85,
      "depth_policy_scale": 0.01
    }
  }
}
```

| Knob                           | Default | Effect                                                     | To Disable                                  |
| ------------------------------ | ------- | ---------------------------------------------------------- | ------------------------------------------- |
| `simulation_enabled`           | `true`  | Reuse proven refutation for sibling opponent responses     | Set `false`                                 |
| `simulation_verify_visits`     | `50`    | Visits for simulation verification query                   | N/A (only used when simulation enabled)     |
| `transposition_enabled`        | `true`  | Cache identical board positions within one tree build      | Set `false`                                 |
| `terminal_detection_enabled`   | `true`  | Pre-query Benson (G1) + interior-point (G2) gates          | Set `false`                                 |
| `forced_move_visits`           | `125`   | Reduced visits for trivially forced player moves           | Set `0` to disable                          |
| `forced_move_policy_threshold` | `0.85`  | Policy prior threshold for forced-move detection           | N/A (only used when forced_move_visits > 0) |
| `depth_policy_scale`           | `0.01`  | Per-depth increment to branch_min_policy at opponent nodes | Set `0.0` to revert to flat threshold       |

### Depth-Dependent Winrate Reference (Simulation)

Simulation verification uses a **depth guard** for winrate comparison:

- **Depth 1-2:** Compares against `root_winrate` (root evaluation is still relevant at shallow depth)
- **Depth ≥3:** Compares against local winrate (first sibling's winrate at that depth)

## Pipeline Internals

### 10-Stage Pipeline Flow

Each puzzle passes through these stages in order:

| # | Stage | Error Policy | Purpose |
|---|-------|-------------|---------|
| 1 | `ParseStage` | FAIL_FAST | Parse SGF, extract metadata + correct first move |
| 2 | `SolvePathStage` | DEGRADE | Dispatch: position-only / has-solution / standard |
| 3 | `AnalyzeStage` | FAIL_FAST | Build query (frame + ROI), run KataGo analysis |
| 4 | `ValidationStage` | DEGRADE | Validate correct move against KataGo top moves |
| 5 | `RefutationStage` | DEGRADE | Generate wrong-move refutations + escalation |
| 6 | `DifficultyStage` | DEGRADE | Estimate difficulty |
| 7 | `AssemblyStage` | FAIL_FAST | Assemble AiAnalysisResult, AC level, goal inference |
| 8 | `TechniqueStage` | DEGRADE | Detect techniques via 28 typed detectors |
| 9 | `TeachingStage` | DEGRADE | Generate teaching comments and hints |
| 10 | `SgfWritebackStage` | DEGRADE | Write enriched properties back to SGF |

Stages with `DEGRADE` error policy allow the pipeline to continue even if that stage fails — the puzzle is enriched with whatever information is available.

### Visit Tiers

KataGo analysis uses tiered visit budgets:

| Tier | Visits | Purpose | When Used |
|------|--------|---------|-----------|
| T0 | 50 | Policy snapshot | Quick technique pre-classification |
| T1 | 500 | Standard analysis | Correct move validation, difficulty estimation |
| T2 | 2000 | Deep analysis | Refutation generation, complex positions |
| T3 | 5000 | Referee | Disagreement resolution, escalation endpoint |

All tiers are config-driven via `config/katago-enrichment.json` under `visit_tiers`. Puzzles start at T1 and escalate to T2/T3 when analysis is uncertain (winrate within escalation thresholds).

### Entropy-Based Region of Interest

The pipeline computes ownership entropy per intersection: `H(p) = -p·log₂(p) - (1-p)·log₂(1-p)` where `p = (ownership + 1) / 2`. High-entropy intersections (above threshold, default 0.5) indicate contested positions. The resulting `EntropyROI` is used as `allowMoves` restriction for refutation queries.

**Fallback chain**: Frame + ROI → ROI only (if frame fails) → bounding box (if entropy unavailable).

### Technique Detection

28 individual technique detectors, one per tag in `config/tags.json`. Each implements the `TechniqueDetector` protocol. Organized by priority (1=most common: life-and-death, ko, ladder, snapback; 4-6=specialized: endgame, tesuji, joseki, fuseki).

### Graceful Degradation

No puzzle is silently dropped. When any component fails:

- Frame failure → entropy ROI fallback → `allowMoves` from bounding box
- Technique detection failure → defaults to "life-and-death" tag
- Difficulty estimation failure → uses structural metrics only
- Teaching comment failure → omits comments, puzzle still enriched

This prevents false rejections at deep positions where root_winrate diverges from local evaluations (e.g., seki formations, ko fights at depth 5+). The guard was approved by the Review Panel — Cho Chikun: "The first opponent response can be surprising [at shallow depth], but five moves deep, the comparison should be local."

### Monitoring Counters

After tree build, `TreeCompletenessMetrics` includes:

- `simulation_hits` / `simulation_misses` — Kawano simulation success/failure
- `transposition_hits` — position cache hits
- `forced_move_count` — forced-move fast-path activations
- `max_resolved_depth` — deepest non-truncated branch
- `branches_pruned_by_depth_policy` — L3 depth-policy pruning

### Disabling All Optimizations

To run the tree builder in "baseline" mode (pre-KM behavior):

```json
{
  "ai_solve": {
    "solution_tree": {
      "simulation_enabled": false,
      "transposition_enabled": false,
      "terminal_detection_enabled": false,
      "forced_move_visits": 0,
      "depth_policy_scale": 0.0
    }
  }
}
```

## Tactical Hints: Instinct Classification & Level-Adaptive Content

The enrichment pipeline includes an **InstinctStage** that classifies the correct first move's shape/intent (push, hane, cut, descent, extend) from position geometry alone — no additional KataGo queries.

### InstinctStage in the Pipeline

The InstinctStage runs after TechniqueStage and before TeachingStage:

```
... → TechniqueStage → InstinctStage → TeachingStage → SgfWritebackStage
```

- **Error policy**: DEGRADE — if classification fails, the pipeline continues without instinct data
- **Engine queries**: Zero (geometry-only analysis)
- **Output**: `ctx.instinct_results: list[InstinctResult]` (instinct type, confidence, evidence)

### Policy Entropy as Difficulty Signal

`DifficultyStage` now computes **policy entropy** — the Shannon entropy of KataGo's top-K policy priors. Higher entropy means more candidate moves with similar probability, indicating greater difficulty.

The entropy value is stored in `ctx.policy_entropy` and used by downstream stages for hint calibration. Additionally, `ctx.correct_move_rank` records the correct move's rank in KataGo's candidate list (1 = top move, 0 = not found).

### Configuration Options

#### Instinct Confidence Thresholds

In `config/teaching.py` → `InstinctConfig`:

| Parameter              | Default | Effect                                              |
| ---------------------- | ------- | --------------------------------------------------- |
| `min_confidence`       | 0.6     | Minimum confidence to include instinct in hints     |
| `instinct_phrases`     | (dict)  | Maps instinct types to hint prefix phrases          |

#### Level-Adaptive Templates

In `config/teaching.py` → `LevelAdaptiveTemplates`:

| Level Category | Template Style                                           |
| -------------- | -------------------------------------------------------- |
| `entry`        | Simple language, focus on visual patterns                |
| `core`         | Standard depth with reading hints + refutation warnings  |
| `strong`       | Terse/concise, assumes familiarity with Go terminology   |

Level category is determined by `get_level_category()` in `config/helpers.py`.

### Calibration: Golden Set Methodology

To validate instinct classification accuracy:

1. **Golden fixtures**: Curated SGF puzzles with known instinct labels in `tests/fixtures/`
2. **Calibration tests**: `tests/test_instinct_calibration.py` runs classification against golden set
3. **Accuracy target**: ≥80% agreement with human-labeled instinct types
4. **Process**: Add new fixtures with `instinct_type` metadata, run calibration, adjust confidence thresholds

```bash
# Run instinct calibration tests
cd tools/puzzle-enrichment-lab
python -B -m pytest tests/test_instinct_calibration.py -v -s
```

## Debug Export (`--debug-export`)

The `--debug-export` CLI flag writes per-puzzle debug artifacts containing trap moves and detector activation data. Useful for diagnosing enrichment quality issues.

### Usage

```bash
# Single puzzle with debug export
python tools/puzzle-enrichment-lab/cli.py enrich \
  --sgf puzzle.sgf \
  --output result.json \
  --katago path/to/katago \
  --debug-export
```

### Output

Debug artifacts are written to `.lab-runtime/debug/{run_id}/{puzzle_id}.debug.json`:

```json
{
  "puzzle_id": "YENGO-765f38a5196edb79",
  "run_id": "20260319-a1b2c3d4",
  "trap_moves": [
    {
      "wrong_move": "cd",
      "delta": -0.45,
      "refutation_pv": ["dc", "dd"],
      "refutation_type": "ai_generated"
    }
  ],
  "detector_matrix": {
    "capture-race": false,
    "ladder": true,
    "life-and-death": true,
    "snapback": false
  }
}
```

| Field | Description |
|-------|-------------|
| `trap_moves` | Top-5 wrong moves sorted by delta, with refutation PV and type |
| `detector_matrix` | Boolean activation state for all 28 technique detectors |

### When to use

- **Investigating false tags**: Check `detector_matrix` to see which detectors fired
- **Missing refutations**: Review `trap_moves` to see what candidates were found
- **Quality debugging**: Compare trap move deltas across puzzles in a collection

## Per-Puzzle Diagnostic JSON

In batch mode, the pipeline automatically writes per-puzzle diagnostic JSON files for observability and quality monitoring.

### Output Location

Diagnostic files are written to `.lab-runtime/diagnostics/{run_id}/{puzzle_id}.json` during batch processing:

```json
{
  "puzzle_id": "YENGO-765f38a5196edb79",
  "source_file": "puzzle_001.sgf",
  "stages_run": ["parse", "analyze", "validation", "refutation", "difficulty", "assembly", "technique", "instinct", "teaching", "sgf_writeback"],
  "stages_skipped": [],
  "signals_computed": {
    "policy_entropy": 0.82,
    "correct_move_rank": 3,
    "trap_density": 0.67
  },
  "goal_stated": "kill",
  "goal_inferred": "kill",
  "goal_agreement": "match",
  "errors": [],
  "warnings": [],
  "phase_timings": {
    "parse": 0.012,
    "analyze": 2.345,
    "refutation": 1.876
  },
  "qk_score": 4,
  "ac_level": 1,
  "enrichment_tier": 3
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `stages_run` / `stages_skipped` | Which pipeline stages executed vs were skipped |
| `signals_computed` | Computed signal values (entropy, rank, trap density) |
| `goal_agreement` | Whether stated puzzle goal matches inferred goal (`match`/`mismatch`/`unknown`) |
| `phase_timings` | Per-stage wall-clock timing in seconds |
| `qk_score` | Computed quality score (0–5) |
| `ac_level` | Analysis completeness (0=untouched, 1=enriched, 2=ai_solved, 3=verified) |
| `enrichment_tier` | Enrichment data tier (1=bare, 2=structural, 3=full) |

### Batch Aggregation

Diagnostics are aggregated by `BatchSummaryAccumulator` and included in the batch summary at the end of a run. Use the batch summary to identify collection-level quality patterns.

## CLI Workflow Examples

### Full enrichment with all diagnostics

```bash
# Generate run ID, enrich with debug export and SGF emission
python tools/puzzle-enrichment-lab/cli.py enrich \
  --sgf puzzle.sgf \
  --output result.json \
  --emit-sgf enriched.sgf \
  --katago path/to/katago \
  --debug-export \
  --visits 2000 \
  --symmetries 4
```

### Batch with custom config

```bash
python tools/puzzle-enrichment-lab/cli.py batch \
  --input-dir .pm-runtime/staging/analyzed/ \
  --output-dir enrichment-output/ \
  --katago path/to/katago \
  --config custom-enrichment.json
```

### Quick validation (no SGF write)

```bash
python tools/puzzle-enrichment-lab/cli.py validate \
  --sgf puzzle.sgf \
  --katago path/to/katago \
  --visits 500
```
