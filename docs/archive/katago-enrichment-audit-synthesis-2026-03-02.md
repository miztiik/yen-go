# TODO Opus — KataGo Puzzle Enrichment: Consolidated Action Plan

**Last Updated:** 2026-03-02  
**Sources:** Three independent reviews cross-referenced against actual codebase  
**Scope:** `tools/puzzle-enrichment-lab/` — all 13 analyzer modules, models, config, CLI, tests  
**Goal:** Reliable KataGo-powered puzzle enrichment for levels, correct-move validation, wrong-move trees, hints, and teaching comments

---

## How This Document Was Built

Three independent reviews were conducted:

1. **Expert Code Review** (Principal Engineer + Cho Chikun 9p + Lee Sedol 9p) — Line-level bug audit
2. **Principal Review Gap Plan (009)** — Architecture-level gap analysis against 5 promised outcomes
3. **Algorithmic Review** — Deep analysis of statistical/Go-domain logic flaws

Each review found overlapping AND unique issues. This document extracts the **verified findings** (confirmed against actual source code), flags **false positives** (review claims that don't match the code), and adds **gaps none of the reviews caught**.

---

## Verdict Summary

| Area                        | Status                                                  | Confidence        |
| --------------------------- | ------------------------------------------------------- | ----------------- |
| Correct-move validation     | Implemented, algorithmically weak for L&D               | ~70%              |
| Wrong-move refutation trees | Partial — single PV lines, not branching trees          | ~50%              |
| Difficulty estimation       | Implemented, calibration fragile, collinear weights     | ~65%              |
| Teaching comments           | Template-only, generic, low pedagogical ceiling         | ~40%              |
| Hints                       | Implemented, **broken on non-19x19 boards**             | ~80% (19x19 only) |
| KataGo integration          | Protocol-correct, config-correct, operationally fragile | ~75%              |

---

## PHASE 0: Critical Bugs (Correctness Failures)

These are verified bugs that produce wrong output for real puzzles.

### P0.1 — YX `u` Field: Semantic Mismatch Between Enrichment Lab and Pipeline

**File:** `analyzers/property_policy.py` line 66 AND `analyzers/sgf_enricher.py` line 378  
**Severity:** CRITICAL — not just a regex bug, but a **semantic conflict**  
**All 3 reviews flagged the regex, but none caught the underlying mismatch.**

#### The Problem Is Deeper Than a Regex

The regex `u:[01]` looks like a bug, but it actually matches the **pipeline's canonical definition**:

| Source                                    | `u` Means                                                                      | Valid Values |
| ----------------------------------------- | ------------------------------------------------------------------------------ | ------------ |
| `docs/concepts/quality.md`                | "Unique correct first move" — 0=miai, 1=unique                                 | 0 or 1       |
| `docs/architecture/backend/enrichment.md` | "1 if single correct first move"                                               | 0 or 1       |
| Pipeline `core/complexity.py`             | `is_unique_first_move(game)` — checks if exactly 1 child has `is_correct=True` | 0 or 1       |
| Enrichment lab `_build_yx()`              | `len(set(wrong_moves))` — count of unique wrong first moves                    | 0, 1, 2, 3   |

The enrichment lab **redefines `u`** from a binary "is the correct answer unique?" to a count of distinct wrong first moves. These are completely different things.

#### Go Domain Perspective (Cho Chikun 9p + Lee Sedol 9p)

**Cho Chikun:** "Miai in tsumego is not useful to count — it's a binary property. Either there's one vital point (unique) or multiple equivalent first moves (miai). A puzzle with miai is slightly easier because the student has multiple correct options. Counting wrong moves is interesting but it's a different metric entirely — it measures how 'trappy' a position is, not its uniqueness."

**Lee Sedol:** "A puzzle with 5 wrong first moves that all look tempting is harder than one with 1 obvious wrong move. But that's trap density, not uniqueness. Don't overload a field — let `u` stay as 'is the answer unique?' and track wrong-move count separately."

**Verdict:** `u` = miai indicator (binary, pipeline definition). Wrong-move count is a separate metric.

#### Resolution: Option A — Align Lab to Pipeline (DECIDED)

1. **Fix `_build_yx()` in `sgf_enricher.py`** to compute `u` correctly per pipeline definition:

   ```python
   # Pipeline definition: is there exactly one correct first move?
   # Parse the solution tree to count correct first-level children
   unique = 1 if is_unique_correct_move(solution_moves) else 0
   ```

   Regex stays `u:[01]`. No downstream changes needed.

2. **Add new optional field `w` to YX** for wrong-first-move count (the metric the lab WAS computing):

   ```
   YX[d:5;r:3;s:24;u:1;w:3]     # w = number of distinct wrong first moves found
   YX[d:5;r:3;s:24;u:1;w:3;a:2] # w before a (optional fields)
   ```

   Update regex:

   ```python
   r"^d:\d+;r:\d+;s:\d+;u:[01](;w:\d+)?(;a:\d+)?$"
   ```

3. **Update docs:**
   - `docs/concepts/quality.md` — add `w` field definition
   - `docs/architecture/backend/enrichment.md` — add `w` field
   - `CLAUDE.md` — clarify YX field descriptions

**Why this is the right call:** The pipeline's `u` is already consumed by `core/complexity.py`, move alternation detection, and the view schema's `x` array. Breaking its semantics to mean "wrong move count" would cascade through the entire system. Adding a new field `w` is additive and safe — old consumers ignore it, new consumers can use it.

**Effort:** Small — fix `_build_yx()`, add `w` field, update regex and docs  
**Tests:** Add test verifying `u=0` for miai puzzles, `u=1` for unique puzzles, `w=N` for wrong-move count  
**Integration requirement:** When enrichment lab output is integrated into the main pipeline, the `u` field MUST match `core/complexity.py`'s `is_unique_first_move()` output. This is the integration contract.

---

### P0.2 — Tree Validation Sorts Top-3 by Policy Prior Instead of Visits

**File:** `analyzers/validate_correct_move.py` ~line 889  
**Confirmed:** YES — tree validation uses `policy_prior` but `_classify_move()` (line 367) correctly uses `visits`  
**Reviews 1 & 3 caught this. Review 2 alludes to it indirectly.**

```python
# CURRENT (~line 889):
top_moves = [m.move.upper() for m in sorted(
    response.move_infos, key=lambda m: m.policy_prior, reverse=True
)[:3]]

# FIX:
top_moves = [m.move.upper() for m in sorted(
    response.move_infos, key=lambda m: m.visits, reverse=True
)[:3]]
```

**Why (Cho Chikun):** KataGo's policy prior is the neural net's first guess before search. Tesuji (throw-in, under-the-stones, sacrifice) often have LOW policy prior but become the best move after deep reading (high visits). The tree validator rejects these correct moves because they're not in the net's "first impression" top 3.  
**Impact:** Dan-level puzzles with sacrifice moves are incorrectly REJECTED.  
**Effort:** 1-line fix  
**Tests:** Add test with a tesuji that has low policy but high visits, verify tree validation accepts it

---

### P0.3 — Hint Coordinate Conversion Hardcodes 19×19

**File:** `analyzers/hint_generator.py` line 256  
**Confirmed:** YES — `board_size = 19` is hardcoded in `_gtp_to_sgf_token()`  
**All 3 reviews agree.**

```python
# CURRENT (line 256):
board_size = 19  # hardcoded!
sgf_row = chr(ord("a") + board_size - row_num)

# FIX: Pass board_size through from puzzle context
def _gtp_to_sgf_token(gtp_coord: str, board_size: int = 19) -> str:
    sgf_row = chr(ord("a") + board_size - row_num)
```

**Why (Lee Sedol):** Many beginner-intermediate tsumego are on 9×9 or 13×13 boards. The hint `{!cg}` would resolve to the wrong intersection — potentially off the board. A player following the hint would play the wrong move.  
**Impact:** ALL hints on non-19×19 puzzles point to wrong coordinates.  
**Effort:** Small — pass `board_size` through `generate_hints()` → `_gtp_to_sgf_token()`  
**Tests:** Add 9×9 and 13×13 fixtures, verify coordinate tokens resolve correctly  
**Tracing needed:** Follow `board_size` from `CroppedPosition` → `enrich_single.py` → `hint_generator.py`

---

### P0.4 — Refutation PV Capped at 4 Moves Regardless of Complexity

**File:** `analyzers/generate_refutations.py` line 226  
**Confirmed:** YES — `opp_best.pv[:4]` truncates all refutation PVs  
**Reviews 1 & 3 caught this. Review 2 identifies shallow PV as a core weakness.**

```python
# CURRENT (line 226):
pv_sgf = [gtp_to_sgf(m) for m in opp_best.pv[:4]]

# FIX: Make cap configurable via katago-enrichment.json, with per-tier defaults:
# Elementary: 4, Intermediate: 6, Dan: 8-10
pv_cap = config.refutation_pv_cap  # or derive from difficulty tier
pv_sgf = [gtp_to_sgf(m) for m in opp_best.pv[:pv_cap]]
```

**Why (Cho Chikun):** Capture-race (semeai) refutations routinely need 5-8 moves. Ko fight refutations need 6-12 moves. Truncating at 4 means the "punishment" sequence stops before the actual capture/death, making the refutation meaningless — the student doesn't see WHY the move was wrong.  
**Impact:** Complex refutation sequences are incomplete for dan-level puzzles.  
**Effort:** Small config addition + 5-line code change  
**Tests:** Add test with deep PV (8 moves), verify full sequence preserved

---

## PHASE 1: Significant Go Domain & Algorithm Issues

### P1.1 — Correct-Move Validation Never Uses KataGo Ownership Grid

**File:** `analyzers/validate_correct_move.py`  
**Confirmed:** YES — ownership arrays are stored in `MoveAnalysis.ownership` but NO validator reads them  
**Reviews 2 & 3 caught this. Review 1 missed it.**

The code promises "ownership-based thresholds" for Life & Death puzzles, but validation relies only on winrate, policy, and visits. Winrate evaluates the ENTIRE game state, not local group survival.

**Why this matters:** A correct L&D move may not change the global winrate significantly (e.g., living a small group in a whole-board position), but ownership of the target stones should flip from dead → alive. Without ownership checking, the validator uses proxy signals that can be misleading.

**Fix direction:**

- Add ownership sweep for target stones (from `AB`/`AW` setup) to `_validate_life_and_death()`
- Promote ownership delta to first-class acceptance criterion
- Keep winrate/policy as secondary tiebreakers
- Requires: `KataGoResponse` already has `ownership` field — just need to wire it into validation

**Effort:** Medium — requires identifying target group stones from puzzle setup  
**Tests:** Add L&D fixture where correct move has modest winrate but clear ownership flip

---

### P1.2 — Dual Engine Escalation Misses "Confident but Wrong" Case

**File:** `analyzers/dual_engine.py`  
**Confirmed:** PARTIAL — escalation triggers on uncertain winrate (0.3–0.7), but a low-visit engine seeing a horizon-effect failure returns 0.0 or 1.0 (very confident), skipping escalation  
**Review 3 caught this clearly. Others noted escalation issues indirectly.**

Additionally confirmed: `_compare_results()` is called WITHOUT `correct_move_gtp` (line ~280), so the F2 per-move winrate tiebreaker path is **dead code** — it always falls through to root_winrate comparison.

**Fix direction:**

1. Add escalation trigger: if Quick engine disagrees with the curated `correct_move` → ALWAYS escalate, regardless of winrate confidence
2. Pass `correct_move_gtp` to `_compare_results()` to activate F2 per-move tiebreaker
3. Make tiebreaker tolerance (0.05) configurable via `katago-enrichment.json`

**Effort:** Medium  
**Tests:** Add test where Quick engine returns 0.0 winrate (confident wrong) for a valid puzzle

---

### P1.3 — Throw-in Detection Only Checks Bottom-Left Edges

**File:** `analyzers/technique_classifier.py` lines 233-245  
**Confirmed:** YES — `row <= 2 or col <= 2` misses upper and right edges  
**Review 1 caught this.**

```python
# CURRENT:
row <= 2 or col <= 2

# FIX:
row <= 2 or row >= board_size - 1 or col <= 2 or col >= board_size - 1
```

**Impact:** Throw-ins near top/right edges (rows 18-19, cols 18-19 on 19×19) are not detected.  
**Effort:** 2-line fix  
**Tests:** Add throw-in fixture at top-right corner

---

### P1.4 — Ladder Detection Misses Edge-Following Patterns

**File:** `analyzers/technique_classifier.py` lines 184-203  
**Confirmed:** YES — requires 4+ consecutive diagonal moves, misses real ladder patterns along edges  
**Review 1 caught this.**

Real ladders along the board edge produce alternating diagonal+orthogonal move pairs (a "staircase" pattern). The current detector requires ≥50% diagonal moves, which misses edge ladders.

**Fix direction:** Check for staircase pattern (alternating move directions) instead of strict diagonal percentage.  
**Effort:** Medium — rewrite ~20 lines  
**Tests:** Add edge-ladder fixture (moves along first line)

---

### P1.5 — Ko Detection Uses Coordinate Recurrence Without Capture Verification

**File:** `analyzers/ko_validation.py` lines 88-115  
**Confirmed:** YES — uses `Counter` on GTP coordinates in PV. Coordinate appearing 2+ times → ko detected  
**Review 1 caught this thoroughly.**

A PV like `[A1, B2, A1, C3]` has A1 appearing twice but this might be a repeated approach, not an actual capture-recapture ko. This produces false positives — normal L&D puzzles incorrectly flagged as ko puzzles, which cascades into wrong validation thresholds and KataGo rules selection.

**Fix direction:** Verify that the repeated coordinate involves a capture (liberties → 0 → recapture). Requires board state tracking or KataGo's `removedStoneCount`.  
**Effort:** Large — needs board state simulation  
**Tests:** Add false-positive regression test (repeated coordinate that isn't actually ko)

---

### P1.6 — Difficulty Estimation: Statistical Collinearity

**File:** `analyzers/estimate_difficulty.py`  
**Confirmed:** YES — policy (30%) and visits (30%) are PUCT-coupled  
**Review 3 caught this explicitly. Review 1 alluded to visits noise.**

PUCT allocates visits proportional to policy prior. So `policy_component` and `visits_component` measure nearly the same underlying signal. 60% of difficulty score comes from one variable: KataGo's neural network bias.

Furthermore: KataGo finds a 15-move ladder trivial (99% policy prior → "novice"), but it's mentally taxing for a human beginner. The structural component (20%) is too low.

**Fix direction:**

1. Reduce `policy_rank` + `visits_to_solve` combined weight to ~40%
2. Increase `structural` weight to 35-40% (solution depth, branch count)
3. Add new factor: `solution_length` (number of forced moves in solution) — distinct from depth
4. Add confidence intervals to handle PUCT noise
5. Make this transparent: add score decomposition fields to output for auditability

**Effort:** Medium — algorithm change + config update  
**Tests:** Add boundary-value tests at level transitions

---

### P1.7 — Config Weight Sums Not Validated

**File:** `config.py` — `DifficultyWeights`  
**Confirmed:** YES — no `@model_validator` ensures weights sum to 100  
**Review 1 caught this (S9).**

```python
# FIX: Add Pydantic model_validator
@model_validator(mode='after')
def check_weights_sum(self) -> 'DifficultyWeights':
    total = self.policy_rank + self.visits_to_solve + self.trap_density + self.structural
    if total != 100:
        raise ValueError(f"Difficulty weights must sum to 100, got {total}")
    return self
```

**Effort:** 5-line fix  
**Tests:** Add config test with weights summing to 80 → expect validation error

---

### P1.8 — Seki Validation Score Threshold Too Rigid

**File:** `analyzers/validate_correct_move.py`  
**Confirmed:** YES — uses `abs(response.root_score) < 5.0`  
**Review 3 caught this.**

Seki 3-signal detection uses `abs(root_score) < 5.0`, but KataGo's Tromp-Taylor scoring makes this unreliable — many sekis encompass enclosed areas where the expected score delta exceeds 5 points depending on the framing.

**Fix direction:** Use score delta (before/after move) rather than absolute score. Or make threshold configurable and board-size-relative.  
**Effort:** Small-medium  
**Tests:** Add seki fixture with large territory framing

---

## PHASE 2: Operational Robustness

### P2.1 — No Timeout/Cancellation for KataGo Analysis

**File:** `cli.py`  
**Confirmed:** YES — `max_time` config field exists (default 0) but is never consumed by any code path. KataGo can hang forever on malformed positions or GPU errors.  
**Review 1 caught this (S8). Review 2 caught engine mode hardening.**

**Fix direction:**

- Read `max_time` from lab_mode config; if >0, apply per-analysis timeout
- On timeout: kill engine process, log error, mark puzzle as FLAGGED with reason
- Add `--timeout` CLI arg (overrides config)
- Add watchdog for batch mode (~50 lines)

**Effort:** Medium  
**Tests:** Add timeout recovery test (mock engine that hangs)

---

### P2.2 — Engine Mode Fallback: Referee-Only Dead Paths

**File:** `analyzers/dual_engine.py`, `cli.py`  
**Confirmed:** Partially. Lab mode forces `referee_only`, but if the referee model file doesn't exist, there's no graceful fallback.  
**Review 2 caught this (P0.2).**

**Fix direction:**

- Validate model file availability at engine startup (fail fast, not mid-pipeline)
- If referee unavailable in lab mode: clear error message, suggest model download
- Add `scripts/download_models.py` integration check

**Effort:** Small-medium  
**Tests:** Add test for missing model graceful error

---

### P2.3 — Batch Processing Is Sequential

**File:** `cli.py` batch mode  
**Confirmed:** YES — processes puzzles one at a time  
**Review 1 caught this (M6).**

For 1000+ puzzles, sequential processing takes hours when async batching could cut this to minutes. KataGo supports batched queries natively.

**Fix direction:** Use KataGo's batch query capability or `asyncio.gather()` with concurrency limit.  
**Effort:** Medium-large  
**Tests:** Add batch performance benchmark

---

### P2.4 — Determinism and Stability Not Characterized

**Not in any review explicitly, but Review 2 mentions it (P2.8).**

Run-to-run variance for the same puzzle isn't measured. PUCT search with different thread scheduling can produce different visit counts, causing difficulty scores to jitter by ~1 level.

**Fix direction:**

- Add repeat-run variance tests in calibration
- Define acceptance tolerance (e.g., difficulty may differ by at most 1 level across runs)
- Use `reportAnalysisWinratesAs = SIDETOMOVE` + fixed symmetry count for reproducibility
- Document known failure modes

**Effort:** Medium  
**Tests:** Run same puzzle 5 times, assert difficulty stays within ±1 level

---

### P2.5 — CLI Workflow: Unify Enrich + Apply Into Single Command with `--emit-sgf`

> _See full description below_

---

### P2.6 — Per-Run Log Files Instead of Single Shared Log

**File:** `log_config.py` lines 259-265  
**Not in any review — identified through operational troubleshooting.**

All enrichment runs write to `logs/enrichment.log`. The run_id is in every JSON record, but the filename is always the same. Troubleshooting a specific run requires grepping through a giant interleaved file.

**Fix:**

```python
# CURRENT (line 259):
log_path = log_dir / "enrichment.log"
file_handler = TimedRotatingFileHandler(log_path, when=rotation_when, ...)

# NEW:
if run_id:
    log_path = log_dir / f"{run_id}_enrichment.log"
    file_handler = logging.FileHandler(log_path)  # no rotation needed per-run
else:
    log_path = log_dir / "enrichment.log"
    file_handler = TimedRotatingFileHandler(log_path, when=rotation_when, ...)
```

**Result:** `logs/20260302-92fb3590_enrichment.log` — one file per run, self-contained, easy to find, easy to clean.

**Effort:** Small (~15 lines)  
**Tests:** Verify log file is created with run_id in name  
**Cleanup:** Add `logs/*.log` to `.gitignore` (already done), add old-log pruning script

---

### P2.7 — KataGo Thread/Batch Size Tuning

**File:** `katago/tsumego_analysis.cfg` lines 78-82  
**Source:** KataGo stderr warning from production run.

#### The Problem

```
nnMaxBatchSize * GPUs (8) < numSearchThreads * numAnalysisThreads (16)
Simultaneous GPU queries could exceed batch capacity.
Increase nnMaxBatchSize for better performance.
```

Current cfg:

```cfg
numAnalysisThreads = 2
numSearchThreadsPerAnalysisThread = 8   # total search = 16
nnMaxBatchSize = 8                       # GPU batch = 8 < 16 threads
```

16 threads can queue GPU queries but only 8 are batched at once → serialization bottleneck.

#### Fix

**Rule:** `nnMaxBatchSize` ≥ `numSearchThreadsPerAnalysisThread` × `numAnalysisThreads`

```cfg
# Option A: increase batch (more GPU memory, full parallelism)
nnMaxBatchSize = 16  # = 8 * 2

# Option B: reduce threads (less parallelism, stays in bounds)
numSearchThreadsPerAnalysisThread = 4
nnMaxBatchSize = 8   # = 4 * 2
```

**Recommendation:** Option A if GPU memory allows. For small tsumego boards (9-19), batch size 16 uses minimal memory.

**Additionally:** Add a startup check in `engine/local_subprocess.py` that parses the cfg and logs a WARNING if `nnMaxBatchSize < numSearchThreads * numAnalysisThreads`. This prevents silent performance degradation on different machines.

**Effort:** Small — 1-line cfg fix + ~10-line validation check  
**Tests:** Unit test for the cfg validation logic

---

### P2.8 — Consolidate Output Artifact Directory Layout

**Not in any review — identified from operational chaos.**

#### Current State (7+ scattered locations)

```
yen-go/                                # REPO ROOT
├─ analysis_logs/                      # SPILLED KataGo logs (14 files!) - CWD hazard
├─ calibration_results.txt             # Manual pytest capture
└─ tools/puzzle-enrichment-lab/
   ├─ logs/enrichment.log                # Python logs (single file)
   ├─ analysis_logs/                     # KataGo stderr logs
   ├─ output/                            # Batch output (empty)
   ├─ test-results/                      # Benchmark outputs
   └─ tests/fixtures/calibration/results/ # Calibration snapshots (mixed with fixtures)
```

#### Proposed Standard Layout

```
tools/puzzle-enrichment-lab/
├─ .lab-runtime/                       # ALL runtime outputs (gitignored)
│  ├─ logs/                             # Python enrichment logs (per-run)
│  │  ├─ 20260302-92fb3590_enrichment.log
│  │  └─ 20260302-abc12345_enrichment.log
│  ├─ katago-logs/                      # KataGo stderr logs (was analysis_logs/)
│  │  └─ 20260302-170530-ab12cd34.log
│  ├─ output/                           # Enrichment output (JSON + SGF)
│  │  ├─ single/                         # Single-file enrich output
│  │  └─ batch/                          # Batch output dirs
│  ├─ calibration/                      # Calibration run results
│  │  ├─ 20260302-386dec1b/
│  │  └─ 20260302-bb9143e5/
│  └─ benchmarks/                       # Performance test outputs
└─ tests/fixtures/                       # INPUT fixtures only (no outputs mixed in)
```

**Design principles:**

1. **Single runtime root:** `.lab-runtime/` (mirrors main pipeline's `.pm-runtime/`)
2. **All gitignored:** `.lab-runtime/` in `.gitignore`
3. **Input vs output separation:** `tests/fixtures/` = INPUT only. `calibration/results/` moves to `.lab-runtime/calibration/`
4. **No CWD-dependent paths:** KataGo `logDir` overridden via `-override-config logDir=<absolute>` at startup
5. **Easy cleanup:** `rm -rf .lab-runtime/` clears everything
6. **Repo root clean:** No more `analysis_logs/` or `calibration_results.txt` at repo root

**Migration:**

1. Create `.lab-runtime/` directory structure
2. Update `log_config.py` to use `.lab-runtime/logs/`
3. Update `tsumego_analysis.cfg` (or override at startup): `logDir` → `.lab-runtime/katago-logs/`
4. Update `cli.py` default `--output-dir` to `.lab-runtime/output/`
5. Update `scripts/run_calibration.py` output to `.lab-runtime/calibration/`
6. Move `tests/fixtures/calibration/results/` contents to `.lab-runtime/calibration/`
7. Add `.lab-runtime/` to `.gitignore`
8. Delete repo-root `analysis_logs/` and `calibration_results.txt`
9. Update README with new layout

**Effort:** Medium — ~8 file changes + directory restructure  
**Tests:** Verify all output goes to `.lab-runtime/`, no CWD spillage

---

### P2.9 — Fix KataGo logDir CWD-Dependency

**File:** `katago/tsumego_analysis.cfg` line 28, `engine/local_subprocess.py`  
**Root cause:** `logDir = analysis_logs` in cfg is resolved by KataGo relative to its CWD, not the cfg file location.

**Fix:** In `local_subprocess.py`, when constructing the KataGo launch command, add:

```python
lab_dir = Path(__file__).resolve().parent.parent
katago_log_dir = lab_dir / ".lab-runtime" / "katago-logs"
katago_log_dir.mkdir(parents=True, exist_ok=True)
cmd.extend(["-override-config", f"logDir={katago_log_dir.as_posix()}"])
```

This forces KataGo to use an absolute POSIX path regardless of CWD. The `.as_posix()` call ensures forward slashes even on Windows (KataGo accepts both).

**Effort:** Small — 5 lines  
**Tests:** Start KataGo from repo root, verify logs land in `.lab-runtime/katago-logs/`

---

**File:** `cli.py` — `enrich` and `patch` subcommands  
**Not in any review — identified through workflow analysis.**

#### Current Workflow (Two-Step)

The current single-file enrichment requires two separate commands:

```bash
# Step 1: Analyze puzzle → produce JSON
python -m cli enrich --sgf puzzle.sgf --output result.json

# Step 2: Apply JSON back to SGF → produce enriched SGF
python -m cli patch --sgf puzzle.sgf --result result.json --output enriched.sgf
```

The `batch` command already does both in one pass, but single-file enrichment requires this awkward two-step dance. The verb "patch" is also misleading — it implies a small fix, not "apply enrichment results to produce an enriched SGF."

#### Problems

1. **Two-step is error-prone** — users forget step 2, or use the wrong JSON with the wrong SGF
2. **"Patch" is the wrong verb** — this isn't patching a bug, it's applying AI analysis results to produce enriched output
3. **Inconsistent with `batch`** — batch does both in one pass; why can't single-file?
4. **Integration friction** — when integrating into the main pipeline, one command is cleaner than two

#### Resolution

**1. Add `--emit-sgf <path>` flag to the `enrich` command:**

```bash
# New single-step workflow:
python -m cli enrich --sgf puzzle.sgf --output result.json --emit-sgf enriched.sgf

# JSON-only (current behavior preserved):
python -m cli enrich --sgf puzzle.sgf --output result.json
```

When `--emit-sgf` is provided, the `enrich` command:

1. Runs full KataGo analysis → produces `AiAnalysisResult`
2. Writes JSON to `--output` (as today)
3. Calls `enrich_sgf(sgf_text, result)` → writes enriched SGF to `--emit-sgf`

This is exactly what `batch` already does per-puzzle — just wire the same logic into `enrich`.

**2. Rename `patch` → `apply` (or deprecate entirely):**

Better verbs than "patch":

| Verb       | Meaning                              | Recommendation                  |
| ---------- | ------------------------------------ | ------------------------------- |
| `apply`    | Apply enrichment results to SGF      | **Preferred** — clear, standard |
| `stamp`    | Stamp enrichment properties onto SGF | OK but unusual                  |
| `merge`    | Merge analysis into SGF              | Conflicts with git terminology  |
| `embed`    | Embed analysis into SGF              | OK                              |
| `inscribe` | Write properties into SGF            | Too fancy                       |

**Recommendation:** Rename `patch` → `apply`. Keep it as the standalone command for when you already have JSON and just need to produce the SGF:

```bash
# Standalone apply (for when you already have JSON):
python -m cli apply --sgf puzzle.sgf --result result.json --output enriched.sgf
```

**3. Implementation plan:**

- Add `--emit-sgf` optional arg to `enrich` subcommand (~10 lines)
- Rename `patch` → `apply` in argparse (keep `patch` as alias for backward compat)
- Update `--help` text and README
- `batch` command unchanged (already works correctly)

**Effort:** Small (15-20 lines of CLI code)  
**Tests:** Add test: `enrich --emit-sgf` produces both JSON + SGF in one run  
**Docs:** Update `tools/puzzle-enrichment-lab/README.md` with new workflow

---

## PHASE 3: Quality & Pedagogy Improvements

### P3.1 — Teaching Comments Are Generic Templates

**File:** `analyzers/teaching_comments.py`  
**Confirmed:** YES — 28 technique-specific templates, but no personalization based on board state, corner/center, stone configuration, or move type  
**All 3 reviews agree.**

"This is a life-and-death problem. Focus on eye shape and the vital point." appears verbatim for hundreds of puzzles.

**Fix direction:**

1. Add 3-5 variants per technique (random or condition-based selection)
2. Use board region (corner vs center), stone count, solution depth to select variant
3. Reference actual board coordinates and engine-specific reading mechanics
4. Tie explanations to concrete evidence: policy delta, tactical threat, liberty swing
5. For wrong moves: explain WHY using refutation PV contents, not just "This is wrong"

**Effort:** Medium  
**Tests:** Assert no two adjacent puzzles get identical comments

---

### P3.2 — Refutation Tree Is Shallow (Single PV Lines)

**File:** `analyzers/generate_refutations.py`  
**Confirmed:** YES — captures only best opponent response per wrong move, single linear PV  
**Reviews 2 & 3 caught this as a core weakness.**

**Why (Lee Sedol):** In many positions, the opponent has 2-3 viable defensive moves after a wrong approach. Only showing one creates a false sense of simplicity. A student might think "I can avoid that response" and not understand the position is truly lost.

**Fix direction:**

1. Multi-branch exploration per wrong first move (depth + breadth caps)
2. Capture top 2-3 opponent responses when winrate differences are small (<0.05)
3. Store confidence/coverage metadata per branch
4. Keep within SGF limitations (subtree depth cap per difficulty tier)

**Effort:** Medium-large refactor  
**Tests:** Add test with multi-response position, verify branching

---

### P3.3 — Refutation Branch Color Assignment Limited to 4 Positions

**File:** `analyzers/sgf_enricher.py` ~line 198  
**Status:** Need to verify if this is actually hardcoded to 4 or dynamic.  
**Review 1 caught this (C3) but subagent reports the alternation at lines 190-200 only pre-defines 4 color entries.**

If the hardcoded color array is `[opponent, player, opponent, player]` and PV > 4 moves, later moves get no color assignment.

**Fix:** Generate colors dynamically: `color = opponent_color if i % 2 == 0 else player_color`  
**Effort:** 5-line fix  
**Tests:** Add test with 6-move refutation PV, verify all moves have colors

---

## PHASE 4: Moderate Issues (Nice to Fix)

### M1 — SGF Parser Sibling Assumption

**File:** `analyzers/sgf_parser.py` ~lines 276-289  
If 1+ sibling is explicitly marked correct, remaining unmarked siblings are assumed wrong. But both could be wrong.  
**Review 1 caught this.**

### M2 — Move Alternation Not Validated in AnalysisRequest

**File:** `models/analysis_request.py`  
Consecutive same-color moves (BB, WW) are silently accepted. Should validate or warn.  
**Review 1 caught this.**

### M3 — Position Coordinate Fallback Silently Returns 'A'

**File:** `models/position.py` ~line 120  
Out-of-bounds coordinates fall back to 'A' instead of raising an error. Produces silently wrong GTP coordinates.  
**Review 1 caught this.**

### M4 — Dual Engine Tiebreaker Tolerance Is Magic Number

**File:** `analyzers/dual_engine.py` ~line 383  
0.05 tolerance is hardcoded with no justification. Should be configurable.  
**Review 1 caught this.**

### M5 — Level Mismatch Distance Assumes Uniform 10-Step IDs

**File:** `analyzers/sgf_enricher.py` ~lines 111-124  
`(id_a - id_b) // 10` assumes level IDs increment by exactly 10. Currently true (110-230 by 10), but fragile. If IDs change, distances break silently.  
**Review 1 caught this.**

### M6 — check_conflicts.py Uses Regex Instead of SGF Parser

**File:** `check_conflicts.py`  
Regex-based stone conflict detection fails on escaped brackets, nested properties, and pass moves.  
**Review 1 caught this.**

### M7 — AiAnalysisResult.hints Is List, SGF YH Is Pipe-String

**File:** `models/ai_analysis_result.py`  
Model stores hints as `list[str]` but Schema v13 YH is `pipe|delimited|string`. Serialization mismatch risk in edge cases (pipes in hint text).  
**Review 1 caught this.**

### M8 — Existing Refutation Detection Only Checks First-Level Children

**File:** `analyzers/sgf_enricher.py` ~lines 142-169  
Won't detect refutation branches nested deeper in the tree.  
**Review 1 caught this.**

### M9 — Pass Move as Wrong Move Not Handled

**File:** `analyzers/sgf_parser.py`  
`B[]`/`W[]` (pass) produces empty string coordinate. Later GTP conversion produces invalid coord.  
**Review 1 caught this.**

---

## FALSE POSITIVES (Review Claims That Don't Match Code)

These were flagged as bugs but are either already fixed or misread the code:

| #   | Claim                                          | Actual State                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| --- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| S7  | `DifficultyResult` is dead code                | **MISLEADING** — The reviewers were confused by a naming mismatch. The **file** is `difficulty_result.py` but the **class** is `DifficultyEstimate`. There is no class called `DifficultyResult` anywhere in the codebase. `DifficultyEstimate` IS actively used: created by `estimate_difficulty()`, consumed by `_build_difficulty_snapshot()` in `enrich_single.py`, mapped to `DifficultySnapshot` in `AiAnalysisResult`. Full runtime call chain: `enrich_puzzle_from_sgf()` → `estimate_difficulty()` → returns `DifficultyEstimate` → `_build_difficulty_snapshot(estimate)` → `DifficultySnapshot` stored in output. The file name is misleading — consider renaming `difficulty_result.py` → `difficulty_estimate.py` to match the class. |
| C3  | Refutation branch color truncates at exactly 4 | **PARTIALLY FALSE** — the PV cap at 4 (P0.4) limits the input, so color assignment never needs >4 entries. The color logic itself could handle more IF the cap were raised. The cap is the real bug, not the colors.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| M5  | Level mismatch distance is wrong               | **FALSE** — IDs DO increment by 10 (110, 120, ..., 230). The code is correct for current data. It's fragile but not buggy.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

---

## GAPS NOT FOUND BY ANY REVIEW

These issues were discovered during codebase verification but aren't in any of the three reviews:

### G1 — `lab_mode.max_time` Is Dead Config

**File:** `config.py`, `cli.py`  
Config field `max_time` (default 0) exists in `LabModeConfig` but is never read by any code path. Users who set it expect timeout behavior that doesn't exist.

### G2 — Dual Engine: `correct_move_gtp` Not Passed to `_compare_results()`

**File:** `analyzers/dual_engine.py` line ~280  
The F2 per-move winrate tiebreaker requires `correct_move_gtp` to look up the correct move's per-move winrate in each engine's results. But `analyze()` calls `_compare_results()` WITHOUT this parameter. The entire per-move winrate tiebreaker path is **dead code** — it always falls through to root_winrate comparison.

### G3 — `Stone.gtp_coord` Property Hardcodes 19×19

**File:** `models/position.py` line 53  
The property `gtp_coord` calls `self.gtp_coord_for(19)` unconditionally. Callers using `.gtp_coord` on non-19×19 boards get wrong coordinates. The method `gtp_coord_for(board_size)` exists as the correct alternative but isn't always used.

### G4 — `StructuralDifficultyWeights` Defined But Never Used

**File:** `config.py`  
The `StructuralDifficultyWeights` model is defined (with `depth_weight`, `branch_weight` fields) but `estimate_difficulty.py` uses hardcoded inline values (0.6, 0.4) instead. Config-driven behavior is promised but not delivered.

### G5 — No 9×9 / 13×13 Test Fixtures Anywhere

**File:** `tests/fixtures/`  
All calibration and control fixtures are 19×19. Zero test coverage for non-standard board sizes. This means P0.3 (hint coords), G3 (Stone.gtp_coord), and related issues have NO regression tests.

### G6 — PV Truncation Cascades to Teaching Comments

**File:** `analyzers/teaching_comments.py`  
If KataGo's PV is truncated due to lack of visits, refutation_depth is logged as 1. Teaching comments see `ref_depth <= 1` and print "This move is captured immediately" — even for deep, complex sequences. Review 3 caught this cascade but the other two missed the teaching comment side.

### G7 — Refutation Delta Threshold Doesn't Account for Ko Evaluations

**File:** `analyzers/generate_refutations.py`  
The rigid `delta_threshold = 0.08` fails for ko evaluations. A "ko to kill" puzzle might have initial winrate 90% but a wrong move drops it variably (to 10%, 30%, 50%) depending on ko threats. The fixed threshold either over-includes or under-includes refutations in ko contexts.

### G8 — No Quality Gate for Enrichment Coverage

There's no aggregate metric tracking what percentage of enriched puzzles have complete data (all 5 outcomes: valid move, refutations, difficulty, hints, comments). Individual puzzles can pass with partial enrichment, but there's no batch-level quality dashboard.

### G9 — YX `u` Field Semantic Mismatch (Enrichment Lab vs Pipeline)

**File:** `analyzers/sgf_enricher.py` line 378 vs `docs/concepts/quality.md`  
The enrichment lab computes `u = len(set(wrong_moves))` (count of unique wrong first moves, range 0-3) but the canonical pipeline docs define `u` as "unique correct first move" (binary: 0=miai, 1=unique). The regex `u:[01]` in `property_policy.py` actually **correctly enforces the pipeline's definition**, but the enrichment lab computes a completely different quantity. This is not a regex bug — it's a semantic conflict between two systems. See P0.1 for fix options.

### G10 — `difficulty_result.py` File Name Doesn't Match Class Name

**File:** `models/difficulty_result.py`  
The file is named `difficulty_result.py` but contains class `DifficultyEstimate`. Three independent reviewers all flagged this as "dead code" because they searched for `DifficultyResult` (matching the filename) and found nothing. The naming mismatch caused real confusion. Rename to `difficulty_estimate.py`.

### G11 — CLI `patch` Subcommand Uses Wrong Verb and Forces Two-Step Workflow

**File:** `cli.py`  
The `enrich` command produces JSON only. To get an enriched SGF, you must run `patch` separately with the JSON output. The `batch` command already does both in one pass, but single-file doesn't. The verb "patch" implies a bugfix, not "apply enrichment analysis." See P2.5 for the unified workflow fix.

### G12 — Enrichment Log Is a Single File — No Per-Run Log Isolation

**File:** `log_config.py` lines 259-265  
**Confirmed:** All runs write to `logs/enrichment.log`, rotated daily via `TimedRotatingFileHandler(when="midnight")`. The run_id IS injected into every JSON record, but the **filename** is always `enrichment.log`. When troubleshooting a specific enrichment run, you must grep through a single giant file to find your run_id.

**Problem:** If you run enrichment 5 times in a day, all 5 runs are interleaved in one file. Each run has its own `run_id` (e.g., `20260302-92fb3590`), but finding a specific run means `grep -F "20260302-92fb3590" enrichment.log` — slow and error-prone.

**Fix direction:** Name log files per-run: `logs/{YYYYMMDD}_{run_id}_enrichment.log`

- Example: `logs/20260302_92fb3590_enrichment.log`
- Keep the daily rotation as a fallback for runs that don't have a run_id (shouldn't happen, but defense-in-depth)
- Implementation: in `setup_logging()`, if `run_id` is provided, use `FileHandler` with run-specific filename instead of `TimedRotatingFileHandler`
- Old logs can still be cleaned by date prefix

**Effort:** Small — ~15 lines in `log_config.py`  
**Tests:** Add test verifying log filename contains run_id  
See P2.6.

### G13 — KataGo Thread/Batch Config Mismatch Warning

**File:** `katago/tsumego_analysis.cfg` lines 78-82  
**Source:** KataGo stderr log from real run:

```
nnMaxBatchSize * number of GPUs (8) < numSearchThreads * numAnalysisThreads (16)
```

Current config:

- `numAnalysisThreads = 2`
- `numSearchThreadsPerAnalysisThread = 8` → total search threads = 16
- `nnMaxBatchSize = 8`

KataGo warns that 16 threads can queue GPU queries faster than the batch size (8) can handle. The GPU processes 8 at a time but 16 threads are queuing, causing serialization delays.

**Fix direction:** Either:

- **Option A:** Increase `nnMaxBatchSize` to 16 (= numSearch × numAnalysis) — uses more GPU memory but eliminates bottleneck
- **Option B:** Reduce `numSearchThreadsPerAnalysisThread` to 4 — reduces parallelism but stays within batch limit
- **Option C (recommended):** Set `nnMaxBatchSize` = `numSearchThreadsPerAnalysisThread` × `numAnalysisThreads` as a rule. Add a startup validation check in `engine/local_subprocess.py` that parses the cfg and warns if mismatched.

**Effort:** Small — 1-line cfg change + optional validation  
See P2.7.

### G14 — Output Artifacts Scattered Across 7+ Directories

**Confirmed locations of output artifacts:**

| Location                                                          | Contents                           | Created by                                    |
| ----------------------------------------------------------------- | ---------------------------------- | --------------------------------------------- |
| `tools/puzzle-enrichment-lab/logs/`                               | Python enrichment log              | `log_config.py`                               |
| `tools/puzzle-enrichment-lab/analysis_logs/`                      | KataGo stderr logs (8 files)       | `tsumego_analysis.cfg` `logDir=analysis_logs` |
| `tools/puzzle-enrichment-lab/output/`                             | Batch output (empty)               | `cli.py --output-dir`                         |
| `tools/puzzle-enrichment-lab/test-results/`                       | Benchmark outputs                  | Test runs                                     |
| `tools/puzzle-enrichment-lab/tests/fixtures/calibration/results/` | Calibration run snapshots (3 dirs) | `scripts/run_calibration.py`                  |
| `analysis_logs/` **(REPO ROOT!)**                                 | Spilled KataGo logs (14 files)     | CWD-relative `logDir` hazard                  |
| `calibration_results.txt` **(REPO ROOT!)**                        | Pytest tee output                  | Manual shell command                          |

**Problems:**

1. **KataGo `logDir = analysis_logs`** is a relative path in cfg — resolves against CWD, NOT against cfg file location. Running from repo root spills logs into repo root `analysis_logs/`.
2. **No single `.pm-runtime`-style output root** — the main pipeline centralizes runtime data in `.pm-runtime/`; the enrichment lab has no equivalent.
3. **Calibration results** live inside `tests/fixtures/` (mixed with input fixtures) — confusing: are they fixtures or outputs?
4. **Root-level `calibration_results.txt`** is a manual artifact with no convention.

See P2.8 for the consolidated layout fix.

### G15 — Path Style: KataGo Config Uses Relative Paths Without Anchor

**File:** `katago/tsumego_analysis.cfg` line 28, `engine/local_subprocess.py`  
The KataGo cfg uses `logDir = analysis_logs` (relative to CWD). The Python code correctly resolves `katago_path`, `model_path`, `config_path` relative to the config file's parent via `from_file()` in `engine/config.py`. But KataGo itself resolves `logDir` relative to its CWD, not the cfg location.

The Python codebase uses `pathlib.Path` throughout (good), and no hardcoded Windows backslashes or absolute paths were found (good). The remaining issue is the KataGo cfg's CWD-dependency.

**Fix direction:** In `engine/local_subprocess.py`, when starting KataGo, pass `-override-config logDir=<absolute_path_to_lab>/analysis_logs` to force the correct directory regardless of CWD.

See P2.9.

---

## CONFIGURATION IMPROVEMENTS

Current config values in `katago-enrichment.json` v1.11 that should be reviewed:

| Config Key                            | Current                | Issue                             | Recommended                        |
| ------------------------------------- | ---------------------- | --------------------------------- | ---------------------------------- |
| `difficulty.weights.policy_rank`      | 30                     | Collinear with visits             | 20                                 |
| `difficulty.weights.visits_to_solve`  | 30                     | Collinear with policy             | 20                                 |
| `difficulty.weights.structural`       | 20                     | Too low for human difficulty      | 35                                 |
| `difficulty.weights.trap_density`     | 20                     | Reasonable                        | 25                                 |
| `refutation.pv_cap`                   | N/A (hardcoded 4)      | Should be config-driven, per-tier | Add: `{"elementary": 4, "dan": 8}` |
| `validation.tree_validation_sort_key` | N/A (hardcoded policy) | Should use visits                 | Fix in code, no config needed      |
| `dual_engine.tiebreaker_tolerance`    | N/A (hardcoded 0.05)   | Should be configurable            | Add to config                      |
| `lab_mode.max_time`                   | 0                      | Dead config                       | Wire to actual timeout logic       |
| `seki.score_threshold`                | N/A (hardcoded 5.0)    | Too rigid for Tromp-Taylor        | Make configurable                  |
| `nnMaxBatchSize`                      | 8 (in cfg)             | < numSearch×numAnalysis (16)      | Set to 16 (= threads)              |
| `numSearchThreadsPerAnalysisThread`   | 8 (in cfg)             | May be too high for single-GPU    | Tune per machine                   |

---

## RECOMMENDED FIX ORDER

### Sprint 0: Test Infrastructure First (Day 0)

> **Principle: Algorithm must work for 1 puzzle before scaling to 1,000.**

0a. **Create `golden5` marker** and select 5 canonical puzzles (1 L&D, 1 ko, 1 tesuji, 1 small-board, 1 multi-response)  
0b. **Create per-puzzle integration tests** — each golden5 puzzle gets its own parametrized test  
0c. **Create `calibration` marker** separate from `slow` — calibration is never run during fixes  
0d. **Document test tier system** in `tools/puzzle-enrichment-lab/tests/README.md`  
0e. **Set default dev command:** `pytest -m "unit or golden5"` (~3 min)

> ✅ Validation after Sprint 0: `pytest -m unit` passes, golden5 fixtures selected

### Sprint 1: Critical Correctness (Day 1-2)

1. **P0.1** — YX `u` field: resolve semantic mismatch (align lab to pipeline definition OR expand pipeline)
2. **P0.2** — Tree validation: `policy_prior` → `visits` (1-line fix)
3. **P1.3** — Throw-in upper edge: add `row >= board_size - 1` check (2-line fix)
4. **P1.7** — Config weight sum validator (5-line Pydantic validator)
5. **G2** — Pass `correct_move_gtp` to `_compare_results()` (dead code revival)
6. **Rename** `difficulty_result.py` → `difficulty_estimate.py` to match class name (avoid future confusion)

> ✅ Validation: `pytest -m "unit or golden5"` — all pass, no KataGo calibration needed

### Sprint 2: Coordinate & Hint Correctness (Day 3-4)

7. **P0.3** — Hint coordinate: pass `board_size` through pipeline (multi-file trace)
8. **G3** — Audit all `Stone.gtp_coord` usage, replace with `gtp_coord_for(board_size)`
9. **G5** — Create 9×9 and 13×13 test fixtures (3-5 each) + coordinate unit tests
10. **Docs:** Update `docs/concepts/quality.md` with board-size requirement for hints

> ✅ Validation: `pytest -m "unit or golden5"` — includes 9×9 golden puzzle

### Sprint 3: Depth & Refutation Quality (Day 5-7)

11. **P0.4** — PV cap: make configurable per difficulty tier (add to `katago-enrichment.json`)
12. **P3.3** — Refutation branch colors: dynamic loop for any PV length
13. **P1.2** — Dual engine: add escalation on correct-move disagreement
14. **P2.2** — Engine model availability check at startup (fail fast)
15. **Docs:** Update `docs/architecture/tools/katago-enrichment.md`

> ✅ Validation: `pytest -m "unit or golden5"` — tesuji golden puzzle tests escalation

### Sprint 4: Algorithm Quality (Day 8-12)

16. **P1.1** — Wire ownership grid into L&D validation
17. **P1.6** — Reweight difficulty: reduce collinearity, boost structural weight
18. **G4** — Wire `StructuralDifficultyWeights` from config instead of hardcoded values
19. **P1.5** — Ko capture verification (board state tracking)
20. **Docs:** Update `docs/concepts/levels.md` with revised weight rationale

> ✅ Validation: `pytest -m "unit or golden5 or regression"` — then run calibration ONCE to baseline

### Sprint 5: Robustness & Infrastructure (Day 13-17)

21. **P2.1** — Add timeout/cancellation for KataGo analysis (wire or remove `max_time`)
22. **P2.4** — Add determinism/stability tests (repeat-run variance on 3 puzzles)
23. **G1** — Wire `max_time` config or delete the dead field
24. **P2.3** — Batch concurrency (async processing)
25. **P2.5** — Add `--emit-sgf` to `enrich` command, rename `patch` → `apply`
26. **P2.6** — Per-run log files with `{YYYYMMDD}_{run_id}_enrichment.log` naming
27. **P2.7** — Fix KataGo `nnMaxBatchSize` vs thread count mismatch
28. **P2.8** — Consolidate all output artifacts into standard directory layout
29. **P2.9** — Fix KataGo `logDir` CWD-dependency via `-override-config`

> ✅ Validation: `pytest -m "unit or golden5 or regression"`

### Sprint 6: Pedagogy & Polish (Day 18-22)

30. **P3.1** — Expand teaching comment templates (3-5 variants per technique)
31. **P3.2** — Multi-branch refutation trees
32. **P1.4** — Ladder staircase detection
33. **P1.8** — Seki validation threshold
34. **G6** — PV truncation → teaching comment cascade fix
35. **Docs:** Final doc sweep — all `docs/architecture/tools/` and `docs/concepts/` updated

> ✅ Final Validation: Full calibration run (`test_calibration.py`) + `pytest -m "not scale"`

---

## TEST COVERAGE GAPS (All Reviews Combined)

| Area                         | Current Coverage     | Gap                                         |
| ---------------------------- | -------------------- | ------------------------------------------- |
| Move validation (L&D)        | Excellent            | Ownership-based validation untested         |
| Move validation (ko)         | Good                 | Ko detection false positives not tested     |
| Move validation (seki)       | Good                 | No real SGF fixtures for seki               |
| Refutation generation        | Good                 | No test for >4 move sequences               |
| Refutation branching         | Missing              | Only single-PV tests                        |
| Difficulty estimation        | Good                 | No boundary-value tests (level transitions) |
| Difficulty stability         | Missing              | No repeat-run variance tests                |
| Teaching comments            | Exists               | No variant diversity tests                  |
| Hint generation              | Exists               | No 9×9/13×13 tests                          |
| Technique classification     | Exists               | No edge-ladder tests                        |
| CLI batch mode               | Exists               | No timeout/recovery tests                   |
| 9×9 / 13×13 boards           | **Missing entirely** | No fixtures exist                           |
| Tree validation (deep)       | **Missing**          | Only surface-level tested                   |
| KataGo timeout/hang          | **Missing**          | No timeout tests                            |
| Ko false-positive regression | **Missing**          | No tests                                    |
| Ownership validation         | **Missing**          | Not implemented                             |
| Score decomposition audit    | **Missing**          | No transparency tests                       |
| Per-run log isolation        | **Missing**          | No test for run_id in log filename          |
| KataGo cfg validation        | **Missing**          | No thread/batch mismatch check              |
| Output directory consistency | **Missing**          | No test for CWD-independent output          |

---

## CALIBRATION & TESTING STRATEGY (Revised)

### ⚠️ CRITICAL: Calibration Must NOT Block the Fix Plan

The current calibration tests (`test_calibration.py`) process 15 puzzles through real KataGo, taking 5-15 minutes per run. Scale tests go up to 10,000 puzzles (33+ hours). **Running these as part of the fix validation cycle is a plan-killer.** The plan gets stuck waiting for calibration instead of making progress on correctness.

### Current Test Inventory (The Problem)

| Test                  | Puzzles              | Time      | KataGo? |
| --------------------- | -------------------- | --------- | ------- |
| Unit tests (all)      | 0 (mocked)           | ~20s      | No      |
| `test_calibration.py` | 15 (5×3 collections) | 5-15 min  | Yes     |
| `test_perf_smoke.py`  | 33                   | 10-17 min | Yes     |
| `test_perf_100.py`    | 100                  | 30-60 min | Yes     |
| `test_perf_1k.py`     | 1,000                | 5-10 hr   | Yes     |
| `test_perf_10k.py`    | 6,951                | 15-33 hr  | Yes     |

The current approach runs **batch first, then checks results**. This is backwards — algorithm correctness should be proven on 1 puzzle before scaling to 1,000.

### Revised Strategy: "Prove It On 1, Then 5, Then Scale"

**Tier 0 — Algorithm Unit Tests (No KataGo, ~20s)**

- Mock KataGo responses with known-good JSON
- Test each analyzer in isolation with controlled inputs
- This is where ALL bug fixes get their first test
- Run after every code change: `pytest -m unit`

**Tier 1 — Golden 5 Integration (Real KataGo, ~2-3 min)**

- Pick **5 canonical puzzles** — 1 per motif:
  1. Simple L&D (elementary, 3-move, 19×19)
  2. Ko puzzle (intermediate)
  3. Sacrifice tesuji (advanced, low-policy correct move)
  4. 9×9 puzzle (coordinate validation)
  5. Multi-response puzzle (u>1 wrong moves)
- Each puzzle tests a specific capability end-to-end
- Run after algorithm changes: `pytest -m golden5`
- **If it works for these 5, the algorithm is sound**

**Tier 2 — Regression Set (Real KataGo, ~10 min)**

- The existing `controls-10` set (10 puzzles)
- Run before merging: `pytest -m regression`
- Validates no regression from the golden 5 expansion

**Tier 3 — Calibration (Real KataGo, ~15-30 min)**

- The existing `test_calibration.py` with Cho Chikun sets
- Run **only before releases or after difficulty algorithm changes**
- NEVER run as part of a bug fix validation cycle
- Mark as `@pytest.mark.calibration` (not `slow`)

**Tier 4 — Scale (Real KataGo, hours-days)**

- perf-100, perf-1k, perf-10k
- Run **only in CI/CD or overnight**
- NEVER run locally during development

### Action Items for Test Strategy

1. **Create `golden5` marker** and select 5 canonical puzzles
2. **Create `calibration` marker** separate from `slow`
3. **Add per-puzzle integration tests** (parametrized by fixture, 1 puzzle each)
4. **Document the tier system** in `tests/README.md`
5. **Default dev command:** `pytest -m "unit or golden5"` (~3 min total)
6. **Pre-merge command:** `pytest -m "unit or golden5 or regression"` (~13 min total)
7. **Release command:** `pytest -m "not (slow or scale)"` (~30 min total)

### Current Calibration Assets

- **Cho Chikun Elementary** (30 SGFs) — baseline beginner/elementary
- **Cho Chikun Intermediate** (30 SGFs) — baseline intermediate/upper-int
- **Cho Chikun Advanced** (30 SGFs) — baseline advanced/dan
- **Ko subset** (5 SGFs) — ko-specific validation
- **Controls-10** (10 SGFs) — mixed difficulty controls
- **Perf-33** (33 SGFs) — core reference set (all tags, all difficulties)
- **Scale-100/1k/10k** — performance benchmarking only
- Three calibration run snapshots (2026-03-02)

### Needed Fixture Additions

- **9×9 corpus** — 3-5 puzzles for coordinate and small-board validation
- **13×13 corpus** — 3-5 puzzles for medium-board validation
- **Seki fixtures** — 3-5 real seki puzzles
- **False ko fixtures** — 3 puzzles with coordinate recurrence that aren't actually ko
- **Edge ladder fixtures** — 3 puzzles with edge-following ladders
- **Low-policy tesuji fixtures** — 3 puzzles with sacrifice moves (high visits, low policy)
- **Multi-response fixtures** — 3 puzzles with 2-3 correct first moves (miai)

---

## DOCUMENTATION REQUIREMENTS (Non-Negotiable)

Per project guidelines, every feature change, bug fix, or enhancement MUST include documentation updates. This plan is no exception.

### Docs That Must Be Updated Per Fix

| Fix                       | Doc File(s) to Update                                                                |
| ------------------------- | ------------------------------------------------------------------------------------ |
| P0.1 (YX `u` semantics)   | `docs/concepts/quality.md` — clarify `u` field definition                            |
| P0.2 (tree validation)    | `docs/architecture/tools/katago-enrichment.md` — note sort-by-visits                 |
| P0.3 (hint coordinates)   | `docs/concepts/quality.md` — note board-size requirement for hints                   |
| P0.4 (PV cap)             | `docs/architecture/tools/katago-enrichment.md` — document configurable PV cap        |
| P1.1 (ownership)          | `docs/architecture/tools/katago-enrichment.md` — document ownership-based validation |
| P1.6 (difficulty weights) | `docs/concepts/levels.md` — update weight descriptions                               |
| Test strategy             | `tools/puzzle-enrichment-lab/tests/README.md` — document tier system                 |
| Config changes            | `config/README.md` — update any new config fields                                    |

### What Counts as "Documentation Done"

1. Updated relevant `docs/` file with new behavior
2. Cross-reference callouts added ("See also" section)
3. "Last Updated" date bumped
4. Config schemas updated if config changed

---

## DEFINITIONS OF DONE

A fix is accepted only if ALL are true:

1. The bug is verified against actual source code (not just review claims)
2. Unit test covers the specific failure mode (Tier 0 — no KataGo needed)
3. Integration test for 1 puzzle validates end-to-end (Tier 1 — golden 5)
4. Existing unit tests still pass: `pytest -m unit`
5. Config changes are backward-compatible (old configs still load)
6. **Documentation updated** — relevant `docs/` file, config schema if applicable
7. Code follows existing patterns and style
8. **Calibration is NOT required** for individual bug fixes — only for difficulty algorithm changes

---

## WHAT WORKS WELL (Credit From All 3 Reviews)

All three reviews agree these aspects are sound:

1. **Dual-Engine Referee Pattern** — Quick engine → escalate if uncertain → referee confirms
2. **KataGo Tsumego Config** — Score utility disabled (0.0), conservative pass, correct for L&D
3. **Tag-Aware Validation Dispatch** — Different thresholds for L&D vs ko vs seki vs capture-race
4. **Winrate Rescue Logic** — Correct moves with low policy but high winrate auto-accepted
5. **Property Policy System** — Enrich-if-absent / enrich-if-partial / override / preserve
6. **Config-Driven Architecture** — All thresholds from JSON (except the bugs above)
7. **AiAnalysisResult Model** — Schema versioning (v8), enrichment tiers, traceability
8. **Test Infrastructure** — 33+ test files, 10,600+ lines of test code
9. **Curated-First Merging** — SGF-annotated wrong moves take priority over AI-discovered
10. **Pydantic Models** — Strong typing throughout, catches many errors at parse time

---

_This consolidated plan was built by cross-referencing actual source code against three independent expert reviews. False positives were flagged. Gaps not found by any reviewer were added. Fix order prioritizes correctness (Phase 0-1) before robustness (Phase 2) before quality (Phase 3)._
