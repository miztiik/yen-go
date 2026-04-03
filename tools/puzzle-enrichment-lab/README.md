# Puzzle Enrichment Lab

**Validate · Refute · Rate** — AI-powered tsumego puzzle enrichment using KataGo.

This tool analyzes Go/Baduk puzzles to:

1. **Validate** the correct first move (does KataGo agree?)
2. **Find refutations** for wrong moves (punishment sequences for common mistakes)
3. **Estimate difficulty** (novice to expert, based on reading depth and engine signals)
   - **Score-based trap density** — uses KataGo `scoreLead` (not just winrate) for more accurate wrong-move attractiveness, inspired by [KaTrain](https://github.com/sanderland/katrain) (MIT licensed)
   - **Elo-anchor hard gate** — cross-checks composite difficulty against KaTrain's calibrated Elo table to catch level misclassifications

Use the **CLI** for batch/automated enrichment, or the **GUI** for visual pipeline observation.

---

## GUI (Visual Pipeline Observer)

Start the bridge server with `--katago` flag, then open `http://localhost:8999`:

```bash
cd tools/puzzle-enrichment-lab
python bridge.py --katago katago/katago.exe --katago-config katago/tsumego_analysis.cfg
# Open http://localhost:8999 in browser
```

The GUI visualizes the enrichment pipeline in real-time: board updates, analysis dots, solution tree with correct/wrong coloring, pipeline stage progress, and streaming logs. A **GUI config panel** lets you edit all 45 enrichment parameters via the sidebar — supports real-time overrides, difficulty weight normalization, config persistence across sessions, and a visits dropdown for quick KataGo analysis tuning. See [gui/README.md](gui/README.md) for details.

---

## Prerequisites

1. **KataGo binary** — Download from [github.com/lightvector/KataGo/releases](https://github.com/lightvector/KataGo/releases) or install via package manager
2. **Model file** — Download a `.bin.gz` model (see Model Recommendations below)
3. **Python dependencies** — `pip install -r requirements.txt`

## CLI Usage

### Enrich a Single Puzzle

```bash
cd tools/puzzle-enrichment-lab

python cli.py enrich \
  --sgf /path/to/puzzle.sgf \
  --output /path/to/result.json \
  --katago /path/to/katago
```

**Output:** A JSON file containing validation status, refutation moves, and difficulty rating.

### Apply Enrichment to SGF

After enrichment, apply the results back to the SGF:

```bash
python cli.py apply \
  --sgf /path/to/puzzle.sgf \
  --result /path/to/result.json \
  --output /path/to/enriched.sgf
```

### Validate Only (No Output File)

Quick validation without writing results — useful for scripting:

```bash
python cli.py validate \
  --sgf /path/to/puzzle.sgf \
  --katago /path/to/katago
```

**Exit codes:**

- `0` = ACCEPTED (puzzle validated successfully)
- `1` = ERROR or REJECTED (pipeline failure or invalid puzzle)
- `2` = FLAGGED (puzzle needs human review)

### Batch Processing

Enrich all SGF files in a directory:

```bash
python cli.py batch \
  --input-dir /path/to/sgf_directory \
  --output-dir /path/to/output_directory \
  --katago /path/to/katago
```

**Optional flags (all subcommands):**

- `--config /path/to/katago-enrichment.json` — Override Python enrichment pipeline config. **Do not pass KataGo `.cfg` files here.**
- `--katago-config /path/to/tsumego_analysis.cfg` — Override KataGo engine config (auto-detected if placed next to the KataGo binary).
- `--visits N` — Override MCTS visit count (default: 500)
- `--symmetries N` — Override root symmetries sampled (default: 2)
- `--quick-only` — Force quick mode (500 visits, 2 symmetries, no referee)
- `--verbose` / `-v` — Enable DEBUG logging
- `--num-puzzles N` — (batch only) Stop after N puzzles

**Logs:** Runtime logs are written to `.lab-runtime/logs/` by default.

### Example: Full Workflow

```bash
# 1. Enrich a puzzle
python cli.py enrich \
  --sgf tests/fixtures/simple_life_death.sgf \
  --output output/result.json \
  --katago katago/katago.exe

# 2. Apply enrichment to create final SGF
python cli.py apply \
  --sgf tests/fixtures/simple_life_death.sgf \
  --result output/result.json \
  --output output/enriched.sgf
```

### Quick Reference: Copy-Paste Examples

All commands assume you are in the `tools/puzzle-enrichment-lab/` directory with the venv activated.

```bash
# Show help for any subcommand
python cli.py --help
python cli.py enrich --help
python cli.py batch --help
```

**Single puzzle (minimal — auto-detects katago config):**

```bash
python cli.py enrich --sgf tests/fixtures/perf-33/14_net.sgf --output .lab-runtime/outputs/14_net_result.json --katago katago/katago.exe
```

**Single puzzle with explicit enrichment config:**

```bash
python cli.py enrich --sgf tests/fixtures/perf-33/01_novice_ld_9x9.sgf --output .lab-runtime/outputs/01_novice_result.json --katago katago/katago.exe --config ../../config/katago-enrichment.json
```

**Single puzzle with verbose logging (DEBUG level):**

```bash
python cli.py -v enrich --sgf tests/fixtures/perf-33/03_elementary_ko.sgf --output .lab-runtime/outputs/03_ko_result.json --katago katago/katago.exe
```

**Single puzzle with enriched SGF emitted in the same run:**

```bash
python cli.py enrich --sgf tests/fixtures/perf-33/11_snapback.sgf --output .lab-runtime/outputs/11_snapback_result.json --katago katago/katago.exe --emit-sgf .lab-runtime/outputs/11_snapback_enriched.sgf
```

**Batch — enrich all perf-33 fixtures:**

```bash
python cli.py batch --input-dir tests/fixtures/perf-33/ --output-dir .lab-runtime/outputs/perf-33/ --katago katago/katago.exe
```

**Validate only (no output file, exits 0/1/2):**

```bash
python cli.py validate --sgf tests/fixtures/perf-33/17_nakade.sgf --katago katago/katago.exe
```

**GUI mode (opens browser at localhost:8999):**

```bash
python cli.py enrich --gui --katago katago/katago.exe
```

> **Tip:** The `--config` flag expects the **Python enrichment JSON** (`katago-enrichment.json`), not a KataGo `.cfg` file. For the KataGo engine config, use `--katago-config`.

---

## Model Recommendations

| Model       | Size      | Elo     | Recommended Use  | Download                                                                                                                           |
| ----------- | --------- | ------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **b6c96**   | 4MB       | ~9,900  | Testing only     | [GitHub](https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170-b6c96-s175395328-d26788732.bin.gz)      |
| **b10c128** | 11MB      | ~11,500 | Light analysis   | [GitHub](https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170e-b10c128-s1141046784-d204142634.bin.gz) |
| **b15c192** | 35MB      | ~12,200 | **Good balance** | katagotraining.org (manual)                                                                                                        |
| **b18c384** | 95-160MB  | ~13,600 | Strong           | katagotraining.org (manual)                                                                                                        |
| **b28c512** | 260-450MB | ~14,090 | **Strongest**    | katagotraining.org (manual)                                                                                                        |

**How to find more models:** Open [katagotraining.org/networks/](https://katagotraining.org/networks/), Ctrl+F for architecture (e.g., `b10c128`), click "Download". Models are at the bottom of the page. The `nbt` suffix means newer architecture — prefer these when available.

### Installing KataGo

| OS          | Install Command                                                                                                              |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Windows** | Download from [github.com/lightvector/KataGo/releases](https://github.com/lightvector/KataGo/releases), extract to `katago/` |
| **macOS**   | `brew install katago`                                                                                                        |
| **Ubuntu**  | `apt install katago`                                                                                                         |

---

## GUI (Research Mode)

The lab ships with a browser-based GUI for visual analysis and enrichment, modeled after goproblems.com's Research(Beta) interface.

**Features:** GhostBan board with analysis overlay, dual-engine analysis (in-browser TF.js or Python bridge), solution tree navigation, problem frame, enrichment pipeline with SSE progress.

### Quick Start

```bash
# 1. Install Node dependencies (first time only)
cd tools/puzzle-enrichment-lab/gui
npm install

# 2. Start the Python bridge server (in one terminal)
cd tools/puzzle-enrichment-lab
python cli.py enrich --gui --katago /path/to/katago

> ⚠️ **Note:** If you want to specify a KataGo configuration file, use `--katago-config katago/tsumego_analysis.cfg`. Do NOT pass `.cfg` files to the `--config` flag, as that expects JSON.

# 3. Start the Vite dev server (in another terminal)
cd tools/puzzle-enrichment-lab/gui
npm run dev
# → Opens at http://localhost:5173
```

The Vite dev server proxies `/api` requests to the FastAPI bridge running on `:8999`.

> See [gui/README.md](gui/README.md) for architecture details, pipeline stage descriptions, and MoveTree color coding.

---

## What It Does

| Task                | Description                                                  | Output                                 |
| ------------------- | ------------------------------------------------------------ | -------------------------------------- |
| **A.1 Validate**    | Confirms the engine agrees with the SGF's correct first move | check/cross + policy prior + winrate   |
| **A.2 Refutations** | Finds 1-3 plausible wrong moves + punishment sequences       | Wrong moves + refutation PV            |
| **A.3 Difficulty**  | Estimates puzzle difficulty from engine signals              | Level (novice to expert) + raw metrics |

---

## Architecture

### Stage Runner Pattern

The enrichment pipeline uses a **Stage Runner** pattern where each enrichment step is an isolated stage class implementing the `EnrichmentStage` protocol. The orchestrator (`enrich_single.py`, ~225 lines) delegates to stages via `StageRunner`, which auto-wraps each stage with notify/timing/error handling.

```text
enrich_single.py (thin orchestrator)
  │
  ├── ParseStage          → Parse SGF, extract metadata, correct first move
  ├── SolvePathStage      → Dispatch: position-only / has-solution / standard
  ├── AnalyzeStage        → Build query (full board + entropy ROI), run KataGo analysis
  ├── ValidationStage     → Validate correct move, tree validation, curated wrongs
  ├── RefutationStage     → Generate wrong-move refutations + tenuki rejection
  ├── DifficultyStage     → Estimate difficulty (structural + policy fallback)
  ├── AssemblyStage       → Assemble AiAnalysisResult, AC level, goal inference
  ├── TechniqueStage      → Classify techniques (ko, ladder, life-and-death, etc.)
  ├── TeachingStage       → Teaching comments, hints generation
  └── SgfWritebackStage   → Write enriched properties back to SGF
```

**Key changes from v1 pipeline:**

- **SolvePathStage** (new) — wraps solve-path dispatch with StageRunner protocol
- **AnalyzeStage** (renamed from QueryStage) — accepts Position directly, no cropping; uses entropy ROI for puzzle region detection
- **TechniqueStage** (new) — split from TeachingStage; classifies Go techniques
- **SgfWritebackStage** (new) — split from TeachingStage; writes enriched SGF
- **Board cropping removed** — all analysis on full board with entropy ROI
- **Visit tiers**: T0(50), T1(500), T2(2000), T3(5000)
- **Tenuki rejection** for refutations — rejects far-away KataGo responses via Manhattan distance

Each stage declares an `ErrorPolicy` (`FAIL_FAST` or `DEGRADE`). `DEGRADE` stages log warnings and continue on failure; `FAIL_FAST` stages abort the pipeline.

### Data Flow

```text
+------------+      CLI       +------------------+     stdin/stdout    +----------+
|  SGF File  | -------------> |  cli.py          | ------------------> | KataGo   |
|            |                |  (Python)        |    Analysis JSON    | (local)  |
+------------+                |                  | <------------------ | engine   |
       |                      +------------------+                     +----------+
       v                              |
+------------+                +------------------+
| Enriched   | <------------- |  analyzers/      |
| SGF + JSON |                |  stages/         |
|            |                |  (10 stages)     |
+------------+                +------------------+
```

---

## Directory Structure

```text
tools/puzzle-enrichment-lab/
├── cli.py                        # CLI entry point (enrich/apply/validate/batch)
├── config/                       # Config package (domain-organized sub-modules)
│   ├── __init__.py               # EnrichmentConfig + loaders
│   ├── difficulty.py             # Difficulty/validation models
│   ├── refutations.py            # Refutation analysis models
│   ├── technique.py              # Technique detection models
│   ├── solution_tree.py          # Solution tree construction models
│   ├── ai_solve.py               # AI-Solve pipeline models
│   ├── teaching.py               # Teaching comment models + loader
│   ├── analysis.py               # Analysis/engine/deep-enrich models
│   ├── infrastructure.py         # Paths, calibration, logging, test defaults
│   └── helpers.py                # get_effective_max_visits, get_level_category
├── log_config.py                 # Structured logging setup
├── requirements.txt              # Python deps
├── analyzers/                    # Enrichment pipeline
│   ├── enrich_single.py          # Thin orchestrator (~225 lines)
│   ├── result_builders.py        # Pure result assembly functions
│   ├── config_lookup.py          # Centralized config resolution (tags, levels)
│   └── stages/                   # Stage runner pipeline
│       ├── protocols.py          # PipelineContext, EnrichmentStage protocol
│       ├── stage_runner.py       # StageRunner (auto timing/notify/error)
│       ├── parse_stage.py        # SGF parsing + metadata extraction
│       ├── solve_paths.py        # Solve-path dispatch functions
│       ├── solve_path_stage.py   # Solve-path dispatch (StageRunner wrapped)
│       ├── analyze_stage.py      # Full-board query + entropy ROI analysis
│       ├── validation_stage.py   # Correct move validation
│       ├── refutation_stage.py   # Wrong-move refutation + tenuki rejection
│       ├── difficulty_stage.py   # Difficulty estimation
│       ├── assembly_stage.py     # Result assembly + AC level
│       ├── technique_stage.py    # Technique classification
│       ├── teaching_stage.py     # Teaching comments + hints
│       └── sgf_writeback_stage.py # Enriched SGF output
├── engine/                       # KataGo subprocess integration
├── models/                       # Pydantic models
├── scripts/                      # Utility scripts
├── tests/                        # Unit/integration tests + fixtures
├── katago/                       # KataGo binaries/configs
└── models-data/                  # Model files (resolved via config labels)
```

---

## Running Tests

```bash
cd tools/puzzle-enrichment-lab

# Unit tests only (no KataGo needed, ~20s)
pytest tests/ -m unit -v --tb=short

# Golden 5 — core capability smoke test (~2-3 min, requires KataGo)
pytest tests/ -m "unit or golden5" -v --tb=short

# Technique calibration — 25 techniques × 5 dimensions (~5-10 min, requires KataGo)
pytest tests/test_technique_calibration.py -v --tb=short

# Technique calibration unit tests only (no KataGo)
pytest tests/test_technique_calibration.py -m unit -v

# Full suite excluding slow benchmarks (~10 min)
pytest tests/ -m "not (slow or calibration)" -v --tb=short
```

See [tests/README.md](tests/README.md) for the full tier system and recommended commands.

See [Concepts: Technique Calibration](../../docs/concepts/technique-calibration.md) for how the 25-technique calibration system works.

---

## KataGo Analysis Config (Tsumego Tuning)

The file `katago/tsumego_analysis.cfg` is tuned specifically for life-and-death puzzle analysis. Key settings and rationale:

| Setting                             | Value    | Default | Range      | Rationale                                                                                                                                                           |
| ----------------------------------- | -------- | ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `wideRootNoise`                     | **0.01** | 0.04    | 0.0-1.0    | Tsumego has 1-3 vital points. Low noise focuses search on top candidates instead of exploring obviously wrong moves across the whole board.                         |
| `analysisPVLen`                     | **15**   | 15      | 1-100      | Tsumego solutions are typically 3-15 moves deep. 15 covers even complex dan-level sequences.                                                                        |
| `maxVisits`                         | **200**  | 500     | 10-100000  | 200 is fast (~0.5-2s) and sufficient for SDK puzzles. Increase to 500-1000 for dan-level. Decrease to 50-100 for quick screening.                                   |
| `conservativePass`                  | **true** | true    | true/false | In tsumego, passing = death. Never assume a pass wins.                                                                                                              |
| `ignorePreRootHistory`              | **true** | true    | true/false | Puzzle positions are standalone — no game context to influence evaluation.                                                                                          |
| `numAnalysisThreads`                | **1**    | 2       | 1-64       | We analyze one puzzle at a time interactively. More threads would help batch processing.                                                                            |
| `numSearchThreadsPerAnalysisThread` | **8**    | 16      | 1-256      | On Intel Iris Xe (integrated GPU), 8 threads gives good depth without overwhelming the GPU. Increase to 16-32 on dedicated GPUs.                                    |
| `nnMaxBatchSize`                    | **8**    | 64      | 1-256      | Smaller batch for integrated GPU. Increase to 32-64 on dedicated NVIDIA/AMD GPUs.                                                                                   |
| `nnCacheSizePowerOfTwo`             | **20**   | 23      | 16-26      | 2^20 = ~1M entries. Tsumego has many transpositions (same position via different move orders), so caching is valuable. Smaller than default to save RAM on laptops. |
| `nnRandomize`                       | **true** | true    | true/false | Randomize board orientation — helps the neural net generalize.                                                                                                      |

### Tuning for your hardware

| GPU Type                   | `numSearchThreads` | `nnMaxBatchSize` | `maxVisits` | Expected speed   |
| -------------------------- | ------------------ | ---------------- | ----------- | ---------------- |
| Intel Iris Xe (integrated) | 8                  | 8                | 200         | ~1-3s/puzzle     |
| NVIDIA GTX 1060            | 16                 | 32               | 500         | ~0.5-1s/puzzle   |
| NVIDIA RTX 3080            | 32                 | 64               | 1000        | ~0.2-0.5s/puzzle |
| NVIDIA RTX 4090            | 64                 | 128              | 2000        | ~0.1s/puzzle     |

### Tuning for puzzle difficulty

| Puzzle Level          | `maxVisits` | `wideRootNoise` | Notes                                            |
| --------------------- | ----------- | --------------- | ------------------------------------------------ |
| Novice-Elementary     | 50-100      | 0.01            | Quick, correct answer is obvious                 |
| Intermediate-Advanced | 200-500     | 0.01            | Standard depth for SDK puzzles                   |
| Low Dan-High Dan      | 500-2000    | 0.02            | Deeper reading needed, slightly more exploration |
| Expert (7d+)          | 2000-10000  | 0.03            | Maximum depth for professional-level puzzles     |

---

## Design Principles

- **Self-contained** — All dependencies (KataGo, models) live inside this directory
- **No backend imports** — Completely isolated from `backend/puzzle_manager/`
- **Structured payloads** — Pydantic models everywhere; API-ready
- **Relative paths** — config.json uses paths relative to this directory
- **Tsumego-optimized config** — `katago/tsumego_analysis.cfg` tuned for life-and-death reading
- **Future integration** — Clean interfaces for backend pipeline adapter

### Query Architecture

All KataGo tsumego queries flow through a single preparation function:

```text
prepare_tsumego_query(position, config, ko_type, margin)
  → TsumegoQueryBundle(framed_position, region_moves, rules, pv_len, komi)
```

**Two query paths, one preparation:**

| Path          | Entry Point                   | Use Case                                    |
| ------------- | ----------------------------- | ------------------------------------------- |
| Position path | `build_query_from_position()` | Position object → entropy ROI → query       |
| Adapter path  | `SyncEngineAdapter`           | Tree builder → per-node queries             |

All paths call `prepare_tsumego_query()` which guarantees:

- **komi = 0.0** — Tsumego is life/death, not scoring
- **`allowed_moves`** — Restricts analysis via entropy ROI (ownership-based region detection)
- **tsumego frame** — Fills empty areas with offense/defense stones
- **ko-aware rules** — Configurable rules and PV length per ko type
- **Full-board analysis** — No cropping; entropy ROI replaces bounding-box cropping

### Comment Policy

- **C[] on solution tree nodes**: Teaching comments only (`Correct.` / `Wrong.`)
- **Diagnostic data** (winrate deltas, scores): Logged to file, not embedded in SGF
- **Original root C[]**: Preserved as-is; never modified by enrichment

### Log File Naming

- Run ID format: `YYYYMMDD-HHMMSS-8HEXUPPER` (aligned with KataGo log naming)
- Enrichment log: `{run_id}-enrichment.log`
- Module prefixes: `analyzers`, `engine`, `models`, `config`, `cli`

---

> **See also:**
>
> - [Concepts: Entropy ROI](../../docs/concepts/entropy-roi.md) — Ownership entropy formula and ROI detection
> - [Reference: KataGo Enrichment Config](../../docs/reference/katago-enrichment-config.md) — Visit tiers, refutation config, curated pruning
> - [Research](../../TODO/katago-puzzle-enrichment/001-research-browser-and-local-katago-for-tsumego.md) — Full feasibility study
> - [Plan](../../TODO/katago-puzzle-enrichment/002-implementation-plan-katago-enrichment.md) — Phase A/B implementation plan
