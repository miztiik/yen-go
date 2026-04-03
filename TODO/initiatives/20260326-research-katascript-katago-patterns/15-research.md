# Research Brief: psy777/katascript Repository Analysis for Yen-Go Puzzle Enrichment

> **Initiative**: 20260326-research-katascript-katago-patterns
> **Date**: 2026-03-26
> **Status**: research_completed

---

## 1. Research Question and Boundaries

**Primary question**: What KataGo integration patterns, signal extraction techniques, engine management approaches, and analysis configurations from the `psy777/katascript` repository could improve Yen-Go's puzzle enrichment lab?

**Boundaries**:
- In scope: KataGo engine lifecycle, analysis protocol usage, signal extraction, config tuning, LLM integration patterns, move explanation approaches
- Out of scope: Full game review (katascript is game-focused; Yen-Go is tsumego-focused), Ollama/LLM hosting setup
- Constraint: Yen-Go is zero-runtime-backend; any patterns must work in offline pipeline context

---

## 2. Internal Code Evidence

### IR-1: Yen-Go KataGo Integration (Enrichment Lab)

| Ref | File | Pattern | Detail |
|-----|------|---------|--------|
| IR-1a | `tools/puzzle-enrichment-lab/engine/local_subprocess.py` | `LocalEngine`: async subprocess, JSON stdin/stdout, threading.Lock serialization | Line-buffered, daemon stderr drain thread, wait-after-spawn crash detection, per-request payload logging |
| IR-1b | `tools/puzzle-enrichment-lab/analyzers/single_engine.py` | `SingleEngineManager`: config-driven visit escalation, model routing by level category | Supports `async with` context manager, escalation thresholds from config, visit counter per puzzle |
| IR-1c | `tools/puzzle-enrichment-lab/models/analysis_response.py` | `AnalysisResponse.from_katago_json()` parses: `winrate`, `scoreLead`, `prior` (policy_prior), `pv`, per-move `ownership`, root `ownership` | Full signal capture from KataGo JSON response |
| IR-1d | `tools/puzzle-enrichment-lab/models/analysis_request.py` | `AnalysisRequest` with: `allowed_moves`, `override_settings`, `analysis_pv_len`, `rules` override, `report_analysis_winrates_as` | Per-request KataGo config overrides, ko-aware rules, region-restricted analysis |

### IR-2: Signal Extraction Depth

| Ref | Module | Signals Extracted | Usage |
|-----|--------|-------------------|-------|
| IR-2a | `analyzers/solve_position.py` | winrate delta → TE/BM/NEUTRAL classification, pre/post normalization | Move quality classification |
| IR-2b | `analyzers/estimate_difficulty.py` | `policy_entropy` (Shannon entropy of top-K priors), `correct_move_rank` | Difficulty estimation |
| IR-2c | `analyzers/generate_refutations.py` | `ownership_delta` (max Δ across intersections), `score_delta`, Dirichlet noise for candidate discovery | Refutation quality scoring |
| IR-2d | `analyzers/stages/analyze_stage.py` | Root winrate, root score, per-move visits, PV sequences | Core position analysis |

### IR-3: Engine Configuration

| Ref | Source | Config Parameter | Value |
|-----|--------|-----------------|-------|
| IR-3a | `config/katago-enrichment.json` | Adaptive visits: branch=500, continuation=200 | Budget-aware visit allocation |
| IR-3b | Same | Corner/ladder visit boosts (multiplicative) | Edge-case handling |
| IR-3c | Same | Board-size-scaled Dirichlet noise for refutation discovery | Noise scaling |
| IR-3d | Same | Per-request `analysisPVLen` override for ko puzzles (30) | Ko-type-aware |
| IR-3e | Same | `rootNumSymmetriesToSample` via override_settings | Symmetry handling |
| IR-3f | Same | Model routing: b10c128 (entry), b18c384 (core), b28 (strong) | Difficulty-aware model selection |

---

## 3. External Evidence: psy777/katascript Repository

### ER-1: Repository Profile

| Ref | Property | Value |
|-----|----------|-------|
| ER-1a | URL | https://github.com/psy777/katascript |
| ER-1b | Description | "Script that takes sgf and returns katago best response using LLM" |
| ER-1c | Files | 3 files total: `katanalyze.py`, `katago_api.py`, `analysis.cfg` |
| ER-1d | Stars / Forks / Contributors | 0 / 0 / 1 |
| ER-1e | Last commit | ~8 months ago (single "Add files via upload" commit) |
| ER-1f | Language | Python 100% |
| ER-1g | README | None (no README.md) |
| ER-1h | Maturity | Minimal prototype; no tests, no CI, no package management |

### ER-2: Architecture of katanalyze.py (Client)

| Ref | Component | Description |
|-----|-----------|-------------|
| ER-2a | SGF parsing | Uses `sgfmill` — `Sgf_game.from_bytes()`, extracts board_size, initial_stones (AB/AW), moves from main sequence, initial_player (PL property) |
| ER-2b | Coordinate conversion | Custom `KATAGO_COLUMNS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"` (skips I), converts sgfmill row/col to KataGo GTP format |
| ER-2c | API communication | HTTP POST to `localhost:8000/analyze` via `requests` library, 180s timeout |
| ER-2d | Query construction | `{ boardXSize, boardYSize, initialStones, moves, rules: "japanese", initialPlayer, maxVisits, analyzeTurns: [turn] }` |
| ER-2e | Visit levels | 3 tiers: `gut=500, read=1000, deepread=10000` |
| ER-2f | Move ranking | `sorted(moveInfos, key=lambda x: (playSelectionValue, visits), reverse=True)` — top 5 moves in markdown table |
| ER-2g | Signal extraction | Only: `move`, `playSelectionValue`, `visits` from moveInfos + `rootInfo.currentPlayer` |
| ER-2h | LLM integration | Calls Ollama subprocess; trivial prompt: "The best move for [Player] is [Move]" — data extraction only, not explanation |
| ER-2i | Output | Log file with raw KataGo JSON + move table + LLM prompt/response |
| ER-2j | Scope | Single move analysis per invocation (`--move N` required argument) |

### ER-3: Architecture of katago_api.py (Server)

| Ref | Component | Description |
|-----|-----------|-------------|
| ER-3a | Framework | FastAPI with Pydantic validation, ASGI lifespan manager |
| ER-3b | `KataGoManager` class | Manages single KataGo subprocess: `subprocess.Popen(stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True, bufsize=1)` |
| ER-3c | Thread architecture | Dedicated `_read_stdout` thread (daemon): reads JSON lines, stores by UUID in `response_dict`. Dedicated `_read_stderr` thread (daemon): logs warnings |
| ER-3d | Query flow | `query_analysis()`: UUID-tagged request → stdin write under `threading.Lock` → poll `response_dict` with 10ms sleep → filter `isDuringSearch=false` for final result |
| ER-3e | Response routing | `self.response_dict[query_id] = response` — dictionary keyed by UUID, supports concurrent queries |
| ER-3f | Crash recovery | On `BrokenPipeError` during stdin write: `stop_engine()` → `start_engine()` → raise HTTP 503 |
| ER-3g | Error handling | KataGo error responses stored in response_dict and re-raised as HTTP 400 |
| ER-3h | Timeout | 180s polling loop; raises HTTP 504 on timeout; cleans up response_dict entry |
| ER-3i | Shutdown | `terminate()` → `wait(5s)` → `kill()` if needed; joins daemon threads with 2s timeout |
| ER-3j | Pydantic model | `KataGoQuery`: validates `initialStones`, `moves`, `boardXSize/YSize`, `komi=6.5`, `rules="japanese"`, `initialPlayer` (lowercase b/w), `maxVisits`, `analyzeTurns` |

### ER-4: analysis.cfg (KataGo Configuration)

| Ref | Parameter | Value | Comparison to Yen-Go |
|-----|-----------|-------|----------------------|
| ER-4a | `maxVisits` | 80 | Yen-Go: 200-500 (branch), 200 (continuation) — katascript is lower |
| ER-4b | `maxPlayouts` | 100 | Yen-Go: not explicitly set (visits-driven) |
| ER-4c | `maxTime` | 5 | Yen-Go: per-request via override, not cfg-level |
| ER-4d | `numSearchThreads` | 4 | Yen-Go: configurable, tied to nnMaxBatchSize |
| ER-4e | `wideRootNoise` | 0.04 | Yen-Go: board-size-scaled Dirichlet noise (more sophisticated) |
| ER-4f | `nnMaxBatchSize` | 2 | Yen-Go: matches numAnalysisThreads (typically higher) |
| ER-4g | `analysisPVLen` | 30 | Yen-Go: 30 for ko puzzles (per-request override), default cfg varies |
| ER-4h | `numAnalysisThreads` | 1 | Yen-Go: configurable (typically 1-4) |
| ER-4i | `logSearchInfo` | false | Yen-Go: false (diagnostic logging at application level) |

### ER-5: LLM Integration Pattern

| Ref | Aspect | Detail |
|-----|--------|--------|
| ER-5a | Model | Ollama local models (gemma2:9b, llama3, etc.) via subprocess |
| ER-5b | Prompt design | Trivial extraction prompt: "You are a data extraction robot... Respond with ONLY the following sentence" |
| ER-5c | Output | Single sentence: "The best move for [Player] is [Move]" |
| ER-5d | Timeout | 60s for LLM response; returns partial output on timeout |
| ER-5e | Sophistication | Minimal — no game-theoretic reasoning, no positional explanation, no technique identification |

---

## 4. Candidate Adaptations for Yen-Go

### CA-1: HTTP API Wrapper Pattern (from katago_api.py)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-1a | Pattern | FastAPI server wrapping KataGo subprocess, UUID-tagged concurrent queries |
| CA-1b | Yen-Go relevance | **LOW**. Yen-Go's `LocalEngine` already communicates directly via stdin/stdout JSON protocol. Adding an HTTP layer would add latency and complexity for no benefit in a single-user pipeline tool. |
| CA-1c | What's interesting | The `isDuringSearch` filter to wait for final results is a clean pattern, but Yen-Go already handles this implicitly (single-threaded serialized queries). |
| CA-1d | Recommendation | **REJECT** — HTTP intermediary adds overhead without benefit for batch pipeline use case. |

### CA-2: Crash Recovery with Auto-Restart (from katago_api.py)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-2a | Pattern | On `BrokenPipeError`: stop → restart → retry. katago_api.py raises 503 and asks client to retry. |
| CA-2b | Yen-Go current | `LocalEngine._lock` guards stdin write; checks `process.poll()` before each query; raises `RuntimeError` on dead process. No auto-restart. |
| CA-2c | Gap | Yen-Go fails hard on KataGo crash. For batch processing (100+ puzzles), a single crash means manual restart. |
| CA-2d | Recommendation | **CONSIDER** (low priority) — Add optional auto-restart with `max_restarts=3` to `SingleEngineManager`. Config-gated (`engine.auto_restart_enabled`, `engine.max_restarts`). Impact: resilience for long batch runs. Risk: low (no behavior change when disabled). |

### CA-3: playSelectionValue Signal (from katanalyze.py)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-3a | Pattern | katanalyze.py sorts by `playSelectionValue` then `visits` |
| CA-3b | What is playSelectionValue | KataGo's move selection weight — blends visits + LCB (lower confidence bound). Different from raw winrate or visits alone. |
| CA-3c | Yen-Go current | `AnalysisResponse.from_katago_json()` does NOT capture `playSelectionValue`. Moves ranked by visits only (`top_move` uses `max(visits)`). |
| CA-3d | Gap | `playSelectionValue` integrates uncertainty into selection and may be more reliable than raw visits for distinguishing close moves. |
| CA-3e | Recommendation | **CONSIDER** (medium priority) — Add `play_selection_value: float` to `MoveAnalysis` model, extract from `moveInfos[].playSelectionValue`. Could improve move ranking in cases where two moves have similar visits but different certainty. |

### CA-4: Visit Level Tiers (from katanalyze.py)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-4a | Pattern | gut=500, read=1000, deepread=10000 — simple named tiers |
| CA-4b | Yen-Go current | Adaptive: branch=500, continuation=200, corner/ladder boosts, escalation via deep_enrich. Far more sophisticated. |
| CA-4c | Recommendation | **REJECT** — Yen-Go's adaptive visit allocation is strictly superior. No value in adopting static tiers. |

### CA-5: wideRootNoise = 0.04 (from analysis.cfg)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-5a | Parameter | katascript uses `wideRootNoise=0.04` in the KataGo config file |
| CA-5b | Effect | Adds noise to root node visits to explore more diverse first moves |
| CA-5c | Yen-Go current | Board-size-scaled Dirichlet noise (`noise_scaling=board_scaled`) with configurable base and reference area. Applied per-request for refutation candidate discovery. |
| CA-5d | Key difference | katascript uses KataGo's built-in wideRootNoise; Yen-Go uses per-request Dirichlet noise. KataGo's version applies uniformly; Yen-Go's scales with board occupancy. |
| CA-5e | Recommendation | **REJECT** — Yen-Go's approach is more tsumego-appropriate (puzzle region focus vs full-board noise). However, the `wideRootNoise=0.04` value could be compared against Yen-Go's noise magnitude for calibration reference. |

### CA-6: maxPlayouts + maxTime Dual Cap (from analysis.cfg)

| Ref | Aspect | Assessment |
|-----|--------|------------|
| CA-6a | Pattern | `maxPlayouts=100` + `maxTime=5` alongside `maxVisits=80` — triple redundancy |
| CA-6b | Yen-Go current | Primarily `maxVisits`-driven. Has per-request `max_time` support in AnalysisRequest but doesn't use `maxPlayouts`. |
| CA-6c | Recommendation | **NOTE** — Adding `maxTime` as a per-request safety cap could prevent hung queries. Already supported in the model but underutilized. Not a net-new insight. |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

### Risks

| Ref | Risk | Severity | Mitigation |
|-----|------|----------|------------|
| RK-1 | katascript is a minimal prototype (0 stars, no tests, single commit) — patterns may not be production-proven | Medium | Treat as "inspiration only"; validate any adopted patterns against KataGo official docs |
| RK-2 | katascript is designed for full game review, not tsumego | High | Most config values (komi=6.5, rules="japanese") are game-specific. Yen-Go uses komi=0.0, allowMoves restriction — fundamentally different analysis context. |
| RK-3 | katascript uses HTTP API layer adding unnecessary latency | Low | Already rejected (CA-1d) |
| RK-4 | LLM integration is trivial and non-transferable | Low | The "data extraction robot" prompt pattern is far below what Yen-Go would need for teaching comments |

### License/Compliance

| Ref | Aspect | Status |
|-----|--------|--------|
| LC-1 | Repository license | **NONE specified**. No LICENSE file in repository. All code is unlicensed by default (copyright reserved). |
| LC-2 | Impact on Yen-Go | Cannot copy code verbatim. Patterns and ideas (not copyrightable) are safe to adapt. |
| LC-3 | Dependencies used | `sgfmill` (MIT), `requests` (Apache 2.0), `fastapi` (MIT), `pydantic` (MIT) — all permissive |

### Rejection Log

| Ref | Pattern | Reason |
|-----|---------|--------|
| REJ-1 | HTTP API wrapper (CA-1) | Adds latency/complexity without benefit for pipeline use case |
| REJ-2 | Static visit tiers (CA-4) | Yen-Go's adaptive allocation is strictly superior |
| REJ-3 | cfg-level `wideRootNoise` (CA-5) | Yen-Go's board-scaled Dirichlet noise is more appropriate for tsumego |
| REJ-4 | LLM prompt pattern (ER-5) | Trivial data extraction; no teaching/explanation value |
| REJ-5 | `rules: "japanese"` / `komi: 6.5` (ER-3j) | Game-specific; Yen-Go uses `chinese`/`tromp-taylor` + `komi=0.0` for tsumego |

---

## 6. Planner Recommendations

**R-1** (Low impact, low effort): **Capture `playSelectionValue`** in `MoveAnalysis` model. katascript's sort-by-playSelectionValue pattern (ER-2f) reveals a KataGo signal we currently discard. Adding it to our response model costs ~3 lines of code and may improve move ranking quality for close-call positions. No behavior change unless explicitly used downstream.

**R-2** (Low impact, low effort): **Add auto-restart to `SingleEngineManager`** for batch resilience. katascript's crash-recovery pattern (ER-3f) handles `BrokenPipeError` → restart. Yen-Go currently fails hard. For long batch runs this is a quality-of-life improvement. Config-gated, default disabled.

**R-3** (Informational): **No actionable signal extraction gaps identified.** katascript extracts only `move`, `playSelectionValue`, `visits` (ER-2g). Yen-Go already captures a superset: `winrate`, `scoreLead`, `prior`, `pv`, `ownership` maps, plus computes derived signals (`policy_entropy`, `correct_move_rank`, `ownership_delta`, `score_delta`). The signal gap is entirely in Yen-Go's favor.

**R-4** (Informational): **No actionable LLM patterns.** katascript's LLM usage (ER-5) is trivial data extraction ("The best move for Black is D4"). For Yen-Go's teaching comment aspirations, examine repositories with actual game commentary generation — e.g., `BrightonLiu-zZ/KataGo-LLM-Team` (already researched in initiative `20260326-research-katago-llm-team-analysis`).

---

## 7. Confidence and Risk Update

### Signal Gap Analysis (katascript vs Yen-Go)

| Ref | Signal | katascript | Yen-Go | Gap Direction |
|-----|--------|------------|--------|---------------|
| SG-1 | winrate | ❌ Not extracted | ✅ Per-move + root | Yen-Go ahead |
| SG-2 | scoreLead | ❌ Not extracted | ✅ Per-move + root | Yen-Go ahead |
| SG-3 | policy_prior | ❌ Not extracted | ✅ Per-move | Yen-Go ahead |
| SG-4 | PV (principal variation) | ❌ Not extracted | ✅ Per-move, ko-aware PV length | Yen-Go ahead |
| SG-5 | ownership maps | ❌ Not used | ✅ Root + per-move, delta scoring | Yen-Go ahead |
| SG-6 | playSelectionValue | ✅ Primary sort key | ❌ Not captured | **katascript ahead** |
| SG-7 | visits | ✅ Secondary sort key | ✅ Per-move + root | Parity |
| SG-8 | policy_entropy (derived) | ❌ | ✅ Shannon entropy of top-K priors | Yen-Go ahead |
| SG-9 | correct_move_rank (derived) | ❌ | ✅ Rank in policy ordering | Yen-Go ahead |
| SG-10 | ownership_delta (derived) | ❌ | ✅ Max absolute Δ for refutation scoring | Yen-Go ahead |
| SG-11 | wideRootNoise | ✅ cfg-level 0.04 | ✅ Board-scaled Dirichlet (more sophisticated) | Yen-Go ahead |
| SG-12 | isDuringSearch filter | ✅ Explicit check | ✅ Implicit (serialized queries) | Parity |
| SG-13 | allowMoves restriction | ❌ Full-board analysis | ✅ Puzzle region focus | Yen-Go ahead |

**Summary**: katascript has exactly **one signal** (SG-6: `playSelectionValue`) that Yen-Go doesn't currently capture. All other dimensions show Yen-Go equal or ahead.

### Confidence Assessment

| Metric | Value | Reasoning |
|--------|-------|-----------|
| Post-research confidence | **90/100** | Repository is small (3 files), fully readable, no hidden patterns. Low uncertainty. |
| Post-research risk level | **Low** | katascript is a minimal prototype with very limited applicability to Yen-Go's sophisticated pipeline. Only two minor improvements identified, both low risk. |
| Value assessment | **Low** | This repository provides negligible new insights for Yen-Go's enrichment lab. The codebase is orders of magnitude simpler than Yen-Go's existing system. |

### Key Takeaway

The `psy777/katascript` repository is a minimal single-developer prototype (~400 lines across 3 files) for doing basic KataGo game analysis + LLM query. **Yen-Go's enrichment lab is substantially more sophisticated in every dimension**: engine management (async, config-driven, model routing), signal extraction (12+ signals vs 3), analysis configuration (adaptive visits, region restriction, ko-aware rules, symmetry sampling), and move classification (delta-based with confidence levels vs simple ranking).

The only net-new insight is the `playSelectionValue` field from KataGo that Yen-Go doesn't currently capture (R-1). The crash recovery pattern (R-2) is a minor quality-of-life improvement. No architectural, configuration, or analysis patterns warrant adoption.

---

## Appendix: Full File Inventory of psy777/katascript

| File | Lines (est.) | Purpose |
|------|-------------|---------|
| `katanalyze.py` | ~200 | CLI: parse SGF → HTTP API query → move table → LLM prompt → response |
| `katago_api.py` | ~200 | FastAPI server wrapping KataGo subprocess with thread-based I/O |
| `analysis.cfg` | 10 | KataGo config: 80 visits, 4 search threads, PV len 30 |
