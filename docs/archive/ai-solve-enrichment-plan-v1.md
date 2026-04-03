# AI-Solve: Position-Only Puzzle Enrichment Plan

**Last Updated:** 2026-03-03  
**Reviewers:** Principal Staff Engineer + Cho Chikun (9p, Meijin) + Staff Engineer  
**Scope:** `tools/puzzle-enrichment-lab/` — analyzers, models, config, CLI, tests  
**Goal:** Enable enrichment of SGFs that have NO solution tree — KataGo discovers the correct first move, builds the solution+refutation branches, estimates difficulty, generates hints and teaching comments  
**Status:** DESIGN PLAN — requires approval before implementation

---

## Motivation

### The Problem

Today, `enrich_single_puzzle()` rejects any SGF without a child node containing a correct first move:

```python
# enrich_single.py ~line 505
correct_move_sgf = extract_correct_first_move(root)
if correct_move_sgf is None:
    return _make_error_result("No correct first move found in SGF", ...)
```

This means the entire `external-sources/tasuki/cho-chikun-elementary/` collection (900+ position-only puzzles) and any future source that provides only board positions cannot be enriched.

### Why This Matters

1. **Not just textbooks.** Many puzzle collections exist as position-only files — no solution tree anywhere. Scraping, OCR, community contributions, and manual imports all produce these. There is no solution to look up; the positions are standalone.
2. **Two correct answers is fine.** If KataGo finds two winning first moves, that's a learning opportunity ("both B[ac] and B[ba] work — can you find both?"). We are not reproducing a book answer; we are helping people learn and have fun.
3. **KataGo is the authority.** We already trust KataGo for refutation generation, difficulty estimation, validation, and teaching. Trusting it to identify the correct first move is a natural extension — it's what the engine is best at.

### Cho Chikun (9p) Perspective

> "In tsumego, the correct answer produces a decisive change in group status. KataGo at 1000+ visits with tsumego config will find it reliably for elementary and intermediate problems. The real question is not whether it can find the answer — it's whether it can distinguish clean kill from ko, and handle seki correctly. For a learning platform, showing two correct paths is educational, not a bug."

---

## Design Decision: NOT a Separate `solve` Stage

### Why Not `ingest → solve → analyze → publish`?

During analysis, we already:

- Run KataGo on the initial position (Step 3-4 in `enrich_single_puzzle`)
- Look at the top moves by winrate and policy (Step 5: `validate_correct_move`)
- Identify wrong moves by low winrate delta (Step 6: `generate_refutations`)

**Finding the correct move is the logical inverse of finding wrong moves.** The move with the highest winrate (from the puzzle player's perspective) IS the correct first move. Adding a separate `solve` stage before `analyze` would:

- Duplicate KataGo queries (solve queries the same position that analyze will query again)
- Break the single-responsibility of the enrichment orchestrator into a two-pass system
- Require a separate engine lifecycle, config, and error handling path

**Instead:** Extend the existing `enrich_single_puzzle()` to handle the "no solution tree" case by inverting the candidate selection logic that already exists in `generate_refutations.py`.

### The Inversion Principle

Today's refutation logic in `generate_refutations.py` already does 90% of what AI-Solve needs — just from the opposite perspective:

| Existing Logic (refutations)                   | New Logic (AI-solve)                           |
| ---------------------------------------------- | ---------------------------------------------- |
| Find moves where winrate **drops** the most    | Find the move where winrate is **highest**     |
| `Δwr > delta_threshold` → move is wrong        | `Δwr < T_good` → move is correct (tesuji)      |
| Exclude the correct move from candidates       | The top move IS the correct move               |
| Build opponent's punishment PV                 | Build player's continuation PV (solution tree) |
| Cap at `refutation_max_count=3` wrong branches | Select top 1-2 correct first moves             |

This is a clean functional inversion — not a new pipeline stage.

### Principal Engineer Rationale

The enrichment pipeline already contains ALL the engine calls, coordinate handling, PV extraction, ownership analysis, and winrate comparison needed. AI-Solve is a **pre-processing step within Step 2** of the existing pipeline — not a new stage. After `inject_solution_into_sgf()` runs, the rest of the pipeline (Steps 3-9) is completely unchanged and cannot distinguish an AI-solved puzzle from a human-solved one. This is the minimal-change, zero-new-dependency design.

---

## Architecture

### Modified Pipeline Flow

```
Step 1:  Parse SGF & extract metadata (UNCHANGED)
Step 2:  Extract correct first move
         ├── IF solution tree exists → extract as today (UNCHANGED)
         └── IF no solution tree → mark ai_solve_mode=True, defer to Step 2b
Step 2b: [NEW] AI-Solve: Run KataGo, select correct first move(s)
         ├── Classify all candidate moves by winrate delta
         ├── Confirm top move via opponent-response query
         └── Inject synthetic child nodes into parsed SGF tree
Step 3+: Continue pipeline as normal (query, validate, refutations, difficulty, ...)
```

The rest of the pipeline (Steps 3-9) remains unchanged. From Step 3 onward, `enrich_single_puzzle()` cannot distinguish an AI-solved puzzle from a human-solved one — this is intentional.

### New Module: `analyzers/solve_position.py`

**Single file, single responsibility.** Called only when `extract_correct_first_move(root)` returns `None` and `config.ai_solve.enabled` is `True`.

```python
"""AI-Solve: Discover correct first move(s) for position-only puzzles.

When an SGF has board setup (AB/AW) but no solution tree (no child nodes),
uses KataGo analysis to identify the correct first move by selecting the
move with the highest winrate from the puzzle player's perspective.

This is the functional inverse of generate_refutations.py:
  - Refutations: find moves where Δwr is large and NEGATIVE (bad moves)
  - AI-Solve:    find the move where winrate is HIGHEST (best move)

All thresholds loaded from config/katago-enrichment.json → ai_solve section.
"""
```

#### Core Functions

```python
async def solve_position(
    engine: LocalEngine,
    position: Position,
    config: EnrichmentConfig | None = None,
    puzzle_id: str = "",
) -> SolveResult:
    """Discover correct first move(s) for a position-only puzzle.

    Algorithm:
      1. Run high-visit analysis on initial position (solve_visits from config)
      2. Classify all candidate moves using winrate delta thresholds
      3. Select top move(s) where Δwr < T_good as correct first move(s)
      4. Verify via confirmation query (play move, check opponent response)
      5. Optionally detect secondary correct moves (miai)
      6. Build minimal solution continuation (correct move + opponent response + continuation)

    Returns SolveResult with correct_move(s), confidence, and solution PV.
    """


def classify_move_quality(
    analysis: AnalysisResponse,
    root_winrate: float,
    player_color: Color,
    config: EnrichmentConfig,
) -> list[MoveClassification]:
    """Classify each candidate move using winrate delta thresholds.

    For each move (t), get the engine's evaluation and compute:
      Δwr = wr_root - wr_after_move  (sign-adjusted by player color)
      Δscore = score_root - score_after_move

    Sign adjustment ensures "positive drop" always means "this player hurt
    themselves," regardless of whether Black or White is to play.

    Apply configured thresholds:
      If Δwr < T_good     → TE (good move / tesuji)
      If Δwr > T_hotspot  → BM + HO (bad move + major turning point)
      If Δwr > T_bad      → BM (bad move)
      Otherwise            → neutral

    Where:
      - wr = winrate (0.0 to 1.0, chance to win)
      - Δwr = how much win chance changed after this move
      - score = expected point lead
      - Δscore = how much expected point advantage changed
      - T_good, T_bad, T_hotspot are from config.ai_solve.thresholds

    Returns list of MoveClassification for all candidates, sorted by winrate
    descending (best moves first).
    """


async def confirm_correct_move(
    engine: LocalEngine,
    position: Position,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> bool:
    """Verify AI-discovered correct move via opponent response query.

    Plays the candidate correct move, lets KataGo find opponent's best
    response. If the puzzle player's winrate after opponent's best reply
    still exceeds min_delta_after_opponent threshold, the move is confirmed.

    This catches false positives where a move looks good superficially but
    the opponent has a strong refutation making it dubious.
    """


async def build_solution_continuation(
    engine: LocalEngine,
    position: Position,
    correct_move_gtp: str,
    config: EnrichmentConfig,
) -> list[str]:
    """Build the solution path beyond the first move.

    Plays correct_move, asks KataGo for opponent's best response,
    then continues alternating until:
      - Terminal condition detected (group clearly dead/alive)
      - solution_max_depth reached
      - Winrate becomes inconclusive

    Returns list of SGF coordinates forming the solution mainline.
    """


def inject_solution_into_sgf(
    root: SgfNode,
    correct_moves: list[SolvedMove],
    wrong_moves: list[MoveClassification],
) -> None:
    """Mutate parsed SGF tree: add correct child node(s) and wrong branches.

    Adds:
      - ;B[coord]C[Correct] for each correct first move (TE[] marker)
      - ;B[coord]C[Wrong] for top N wrong first moves (BM[] marker)
      - Solution continuation as children of the correct node

    After this, the SGF tree is indistinguishable from a human-authored one,
    and extract_correct_first_move(root) will succeed.
    """
```

### Move Classification: Winrate Delta Thresholds

For each candidate move in the initial analysis, classify quality using consecutive engine states:

```
Δwr = wr_before - wr_after  (sign-adjusted by player color)
Δscore = score_before - score_after

Thresholds (configured in ai_solve section):
  T_good    = 0.02   → Δwr < T_good    → TE (tesuji / correct move)
  T_bad     = 0.08   → Δwr > T_bad     → BM (bad move)
  T_hotspot = 0.25   → Δwr > T_hotspot → BM + HO (major blunder)
```

**Explanation in plain language:**

- `wr` = winrate (chance to win), so `Δwr` is "how much win chance changed after this move."
- `score` = expected point lead, so `Δscore` is "how much expected point advantage changed."
- Signs are flipped by player color so "positive drop" always means "this player hurt themselves," no matter Black or White.
- Then simple cutoffs:
  - If the damage is tiny (`Δwr` below `T_good`) → label it **TE** (good move / tesuji).
  - If the damage is huge (`Δwr` above `T_hotspot`) → label it **BM+HO** (bad move and major turning point).
  - Otherwise, if damage is clearly bad (`Δwr` above `T_bad`) → label it **BM** (bad move).

This reuses the same signal pipeline that `generate_refutations.py` already computes — just classifying from the opposite direction.

**Relationship to existing refutation delta_threshold:**

The existing `config.refutations.delta_threshold = 0.08` determines when a wrong move's punishment is "significant enough" to include as a refutation. The AI-Solve `T_bad = 0.08` threshold is intentionally aligned — a move that would be included as a refutation is, by definition, a bad move.

---

## New Model: `models/solve_result.py`

Follows existing Pydantic model pattern from `models/refutation_result.py` and `models/difficulty_estimate.py`.

```python
"""Results from AI-Solve: position-only puzzle solving.

Models follow the same Pydantic BaseModel pattern as other result types
in the enrichment lab (RefutationResult, DifficultyEstimate, etc.).
"""

from __future__ import annotations

from pydantic import BaseModel


class SolvedMove(BaseModel):
    """A correct first move discovered by KataGo."""
    move_sgf: str           # SGF coordinate (e.g., "ac")
    move_gtp: str           # GTP coordinate (e.g., "A3")
    winrate: float          # Winrate after this move (from puzzle player's POV)
    score_lead: float       # Score lead after this move
    policy_prior: float     # Neural net policy prior
    visits: int             # Visits allocated to this move
    solution_pv: list[str]  # Continuation PV beyond first move (SGF coords)
    confidence: str         # "high" | "medium" | "low"


class MoveClassification(BaseModel):
    """Quality classification for a candidate move.

    Classification values use standard SGF property mnemonics:
      TE = tesuji (good/correct move)
      BM = bad move
      BM_HO = bad move + hotspot (major turning point)
      neutral = not clearly good or bad
    """
    move_gtp: str
    move_sgf: str
    winrate: float
    winrate_delta: float    # Δwr from root (sign-adjusted by player color)
    score_delta: float      # Δscore from root
    policy_prior: float
    classification: str     # "TE" | "BM" | "BM_HO" | "neutral"


class SolveResult(BaseModel):
    """Complete result from AI position solving."""
    puzzle_id: str
    correct_moves: list[SolvedMove]       # 1-2 correct first moves
    wrong_moves: list[MoveClassification] # Top wrong candidates (BM/BM_HO)
    all_classifications: list[MoveClassification]  # All moves classified
    root_winrate: float
    root_score: float
    solve_visits: int                     # Visits used for solve analysis
    confirmation_passed: bool             # True if confirmation query succeeded
    goal_inference: str     # "kill" | "live" | "ko" | "capture" | "unknown"
    ai_solve: bool = True   # Always True for AI-solved puzzles
```

---

## New Config Section: `ai_solve`

**File:** `config/katago-enrichment.json` → new `ai_solve` section  
**Schema version bump:** `1.13` → `1.14`  
**Changelog entry:** `"v1.14": "AI-Solve: discover correct first move for position-only puzzles. New ai_solve section with solve_visits, confirmation, move classification thresholds (T_good/T_bad/T_hotspot), goal inference config. Feature gated behind enabled=false."`

### JSON Config

```json
{
  "ai_solve": {
    "description": "AI-Solve: discover correct first move for position-only puzzles. Feature-gated (default: disabled).",
    "enabled": false,
    "solve_visits": 1000,
    "confirmation_visits": 500,
    "min_winrate_gap": 0.15,
    "max_correct_moves": 2,
    "solution_max_depth": 8,
    "thresholds": {
      "description": "Move classification thresholds based on winrate delta. See solve_position.classify_move_quality().",
      "T_good": 0.02,
      "T_bad": 0.08,
      "T_hotspot": 0.25
    },
    "goal_inference": {
      "description": "Thresholds for inferring puzzle goal (kill/live/ko) from KataGo analysis.",
      "score_delta_kill_threshold": 15.0,
      "ownership_alive_threshold": 0.7,
      "ownership_dead_threshold": -0.7
    },
    "confirmation": {
      "description": "Confirmation query: play candidate correct move, check opponent response still loses.",
      "enabled": true,
      "require_opponent_response": true,
      "min_delta_after_opponent": 0.1
    }
  }
}
```

### Pydantic Models (in `config.py`)

Follows existing pattern: nested `BaseModel` classes, loaded from JSON via `load_enrichment_config()`.

```python
class AiSolveThresholds(BaseModel):
    """Winrate delta thresholds for move quality classification.

    T_good:    Δwr below this → TE (tesuji/correct). Default 0.02.
    T_bad:     Δwr above this → BM (bad move). Default 0.08 (aligned with refutations.delta_threshold).
    T_hotspot: Δwr above this → BM+HO (major blunder). Default 0.25.
    """
    T_good: float = 0.02
    T_bad: float = 0.08
    T_hotspot: float = 0.25


class AiSolveGoalInference(BaseModel):
    """Thresholds for inferring puzzle goal (kill/live/ko)."""
    score_delta_kill_threshold: float = 15.0
    ownership_alive_threshold: float = 0.7
    ownership_dead_threshold: float = -0.7


class AiSolveConfirmation(BaseModel):
    """Confirmation query settings to verify AI-discovered correct move."""
    enabled: bool = True
    require_opponent_response: bool = True
    min_delta_after_opponent: float = 0.10


class AiSolveConfig(BaseModel):
    """AI-Solve configuration for position-only puzzle enrichment.

    When enabled, puzzles with no solution tree (no child nodes in SGF)
    will be solved by KataGo instead of rejected. The correct first move
    is identified by highest winrate, confirmed via opponent response query,
    and injected into the SGF tree before the rest of the enrichment pipeline.

    Feature-gated: default disabled. Enable via config or --allow-ai-solve CLI flag.
    """
    enabled: bool = False
    solve_visits: int = 1000
    confirmation_visits: int = 500
    min_winrate_gap: float = 0.15
    max_correct_moves: int = 2
    solution_max_depth: int = 8
    thresholds: AiSolveThresholds = AiSolveThresholds()
    goal_inference: AiSolveGoalInference = AiSolveGoalInference()
    confirmation: AiSolveConfirmation = AiSolveConfirmation()
```

### EnrichmentConfig Addition

```python
class EnrichmentConfig(BaseModel):
    # ... existing fields (ownership_thresholds, validation, difficulty, refutations, etc.) ...
    ai_solve: AiSolveConfig | None = None  # NEW — optional, None when absent from JSON
```

**Backward compatibility:** `ai_solve` defaults to `None`. When `None`, the feature is disabled. Existing `config/katago-enrichment.json` files without the `ai_solve` key continue to work unchanged.

---

## CLI Changes

### New Flag: `--allow-ai-solve`

Added to both `enrich` and `batch` subcommands. Follows existing pattern of `--quick-only` (boolean flag override).

```python
# cli.py — enrich subparser
enrich_parser.add_argument(
    "--allow-ai-solve",
    action="store_true",
    default=False,
    help="Enable AI-Solve mode: discover correct first move for position-only puzzles "
         "using KataGo analysis. Requires config ai_solve.enabled=true OR this flag.",
)

# cli.py — batch subparser (same flag)
batch_parser.add_argument(
    "--allow-ai-solve",
    action="store_true",
    default=False,
    help="Enable AI-Solve mode for position-only puzzles in batch.",
)
```

**Runtime resolution:** `--allow-ai-solve` CLI flag OR `config.ai_solve.enabled=True` — either one enables the feature. CLI flag is the override for one-off runs without modifying config.

**Exit codes:** Unchanged. AI-solved puzzles that pass all quality gates → `EXIT_ACCEPTED = 0`. AI-solve failures → `EXIT_ERROR = 1`.

---

## Integration Point: `enrich_single.py` Step 2

**Minimal change to existing code.** Replace the hard rejection with a conditional AI-solve call:

```python
    # ---------------------------------------------------------------
    # Step 2: Extract correct first move and solution tree
    # ---------------------------------------------------------------
    correct_move_sgf = extract_correct_first_move(root)

    if correct_move_sgf is None:
        # NEW: AI-Solve for position-only puzzles
        ai_solve_enabled = (
            (config.ai_solve is not None and config.ai_solve.enabled)
            or allow_ai_solve  # passed from CLI
        )
        if not ai_solve_enabled:
            logger.error("No correct first move found in SGF for puzzle %s", puzzle_id)
            return _make_error_result(
                "No correct first move found in SGF",
                puzzle_id=puzzle_id, source_file=source_file,
                trace_id=trace_id, run_id=run_id,
            )

        # AI-Solve: discover correct move from KataGo analysis
        log_with_context(
            logger, "INFO",
            "No solution tree in SGF — entering AI-Solve mode for puzzle %s",
            puzzle_id,
            puzzle_id=puzzle_id, stage="ai_solve",
        )
        t_solve_start = time.monotonic()

        position = extract_position(root)
        from analyzers.solve_position import solve_position, inject_solution_into_sgf

        solve_result = await solve_position(
            engine=engine_manager.get_engine(),
            position=position,
            config=config,
            puzzle_id=puzzle_id,
        )

        if not solve_result.correct_moves:
            log_with_context(
                logger, "ERROR",
                "AI-Solve found no confident correct moves for puzzle %s",
                puzzle_id,
                puzzle_id=puzzle_id, stage="ai_solve",
            )
            return _make_error_result(
                "AI-Solve failed: no confident correct move found",
                puzzle_id=puzzle_id, source_file=source_file,
                trace_id=trace_id, run_id=run_id,
            )

        # Inject solution into SGF tree — from here on, pipeline is identical
        inject_solution_into_sgf(
            root, solve_result.correct_moves, solve_result.wrong_moves,
        )
        correct_move_sgf = extract_correct_first_move(root)  # Now succeeds
        ai_solved = True  # Track for YQ ac field

        timings["ai_solve"] = time.monotonic() - t_solve_start
        log_with_context(
            logger, "INFO",
            "AI-Solve completed: correct=%s, confidence=%s, goal=%s, %.1fs",
            correct_move_sgf,
            solve_result.correct_moves[0].confidence,
            solve_result.goal_inference,
            timings["ai_solve"],
            puzzle_id=puzzle_id, stage="ai_solve",
            elapsed=timings["ai_solve"],
        )

    # ... rest of pipeline continues unchanged (Step 3+) ...
```

**Function signature change:** Add `allow_ai_solve: bool = False` parameter:

```python
async def enrich_single_puzzle(
    sgf_text: str,
    engine_manager: DualEngineManager,
    config: EnrichmentConfig | None = None,
    source_file: str = "",
    run_id: str = "",
    allow_ai_solve: bool = False,  # NEW
) -> AiAnalysisResult:
```

---

## Quality Tracking: `YQ` Extension

AI-solved puzzles must be distinguishable from human-solved ones downstream.

### New Field: `ac` (AI Correctness)

| Value  | Meaning                                                            |
| ------ | ------------------------------------------------------------------ |
| `ac:0` | Not AI-solved (solution from source SGF — default, omitted when 0) |
| `ac:1` | AI-solved (KataGo discovered the correct first move)               |
| `ac:2` | AI-solved + human verified (future: review queue)                  |

**Wire format:** `YQ[q:2;rc:0;hc:0;ac:1]`

**Schema v13 backward compatibility:** Existing `YQ` regex permits optional trailing fields. `ac` is additive — old consumers ignore it, new consumers can filter on it.

### `AiAnalysisResult` Addition

```python
class AiAnalysisResult(BaseModel):
    # ... existing fields ...
    ai_solved: bool = False  # True when AI-Solve discovered the correct move
```

### `SgfEnricher` Change

In `analyzers/sgf_enricher.py`, the `_build_yq()` function appends `ac:1` when `result.ai_solved is True`:

```python
def _build_yq(result: AiAnalysisResult) -> str:
    parts = [
        f"q:{result.validation.quality_level}",
        f"rc:{result.validation.refutation_coverage}",
        f"hc:{result.validation.human_correctness}",
    ]
    if result.ai_solved:
        parts.append("ac:1")
    return ";".join(parts)
```

YQ regex updated: `r"^q:\d+;rc:\d+;hc:\d+(;ac:[012])?$"`

---

## Logging Contract

All AI-Solve operations follow the existing `log_with_context()` structured logging pattern from `log_config.py`.

```python
from log_config import log_with_context

# Stage entry
log_with_context(logger, "INFO", "AI-Solve: analyzing position",
    puzzle_id=puzzle_id, stage="ai_solve", visits=config.ai_solve.solve_visits)

# Move classification
log_with_context(logger, "DEBUG", "Move %s → %s (Δwr=%.3f, Δscore=%.1f, policy=%.4f)",
    move_gtp, classification, winrate_delta, score_delta, policy_prior,
    puzzle_id=puzzle_id, stage="ai_solve")

# Confirmation query
log_with_context(logger, "INFO", "AI-Solve confirmation: %s → %s (wr_after_opp=%.3f)",
    correct_move_gtp, "PASSED" if confirmed else "FAILED", wr_after_opponent,
    puzzle_id=puzzle_id, stage="ai_solve")

# Goal inference
log_with_context(logger, "DEBUG", "Goal inference: %s (score_delta=%.1f, ownership_shift=%.2f)",
    goal, score_delta, ownership_shift,
    puzzle_id=puzzle_id, stage="ai_solve")

# Phase timing — included in AiAnalysisResult.phase_timings
timings["ai_solve"] = elapsed
```

**Structured JSON log fields:** `stage: "ai_solve"`, `puzzle_id`, `model`, `visits`, `elapsed` — consistent with existing phase logging in `enrich_single.py`.

---

## Validation Checklist

### Pre-Implementation Validation

- [ ] `config/katago-enrichment.json` schema bumped to v1.14 with `ai_solve` section and changelog entry
- [ ] `config/schemas/katago-enrichment.schema.json` updated with `ai_solve` properties (if schema file exists)
- [ ] `AiSolveConfig` Pydantic model validates against JSON (test: `load_enrichment_config()` with new section)
- [ ] `load_enrichment_config()` loads `ai_solve` section without breaking existing configs (optional field, `None` default)
- [ ] Config with NO `ai_solve` key → `config.ai_solve is None` → feature disabled → zero behavior change

### Functional Validation

- [ ] Position-only SGF (no children) + `--allow-ai-solve` → AI-Solve discovers correct move → full enrichment succeeds
- [ ] SGF with existing solution tree → AI-Solve bypassed entirely, zero behavior change
- [ ] `--allow-ai-solve` flag enables AI-Solve even when `config.ai_solve.enabled=false`
- [ ] Without flag and config disabled → hard rejection as today (backward compatible)
- [ ] Two correct moves detected (both < `T_good`) → both injected, `miai` move_order inferred
- [ ] Confirmation query rejects false positive (top move doesn't survive opponent's best response)
- [ ] `YQ` property includes `ac:1` for AI-solved puzzles, omits `ac` for human-solved
- [ ] `AiAnalysisResult.ai_solved` is `True`, `phase_timings` includes `"ai_solve"` key
- [ ] Solution continuation built correctly (mainline PV up to `solution_max_depth`)

### Move Classification Validation

- [ ] Move with Δwr < T_good (0.02) → classified as TE (tesuji/correct)
- [ ] Move with Δwr > T_hotspot (0.25) → classified as BM+HO (blunder)
- [ ] Move with T_bad < Δwr < T_hotspot → classified as BM (bad move)
- [ ] Move with T_good < Δwr < T_bad → classified as neutral
- [ ] Sign adjustment correct for Black-to-play puzzles (positive Δwr = player hurt themselves)
- [ ] Sign adjustment correct for White-to-play puzzles (PL[W]) — inverted correctly
- [ ] Classification thresholds read from `config.ai_solve.thresholds`, not hardcoded

### Integration Validation

- [ ] Steps 3-9 of `enrich_single_puzzle` produce identical output whether solution came from SGF or AI-Solve
- [ ] `extract_correct_first_move(root)` succeeds after `inject_solution_into_sgf()` — the contract
- [ ] Refutation generation works normally after AI-Solve injection (same correct_move_gtp, same candidates)
- [ ] Difficulty estimation works normally (policy_prior, visits_to_solve populated from AI-Solve analysis)
- [ ] Teaching comments and hints generated correctly (tags, corner, move_order populated)
- [ ] `compose_enriched_sgf()` produces valid SGF with AI-solved branches

### Edge Cases

- [ ] Seki position → AI-Solve handles correctly (winrate near 0.5, confidence="low")
- [ ] Ko position → AI-Solve detects ko context, sets `goal_inference="ko"`
- [ ] Multiple equally good moves (within `min_winrate_gap`) → selects up to `max_correct_moves=2`
- [ ] No move exceeds `min_winrate_gap` over second-best → rejects (returns error result)
- [ ] 9×9 board puzzles → coordinate handling correct (`gtp_to_sgf`, `sgf_to_gtp` with board_size)
- [ ] 13×13 board puzzles → coordinate handling correct
- [ ] Empty position (no stones, only SZ) → rejected gracefully ("no stones in position")
- [ ] Position with only one legal move → trivially solved
- [ ] White-to-play puzzles (`PL[W]`) → sign adjustment correct, `W[coord]C[Correct]` injected (not `B[]`)
- [ ] Position where all moves are bad (defending side losing regardless) → rejected or flagged

---

## Documentation Updates Required

| Document                                       | Change                                               | Type         |
| ---------------------------------------------- | ---------------------------------------------------- | ------------ |
| `config/katago-enrichment.json`                | Add `ai_solve` section, bump to v1.14                | Config       |
| `config/schemas/katago-enrichment.schema.json` | Add `ai_solve` schema definition (if exists)         | Schema       |
| `CLAUDE.md` (root)                             | Add `ac` to YQ property description table            | Reference    |
| `.github/copilot-instructions.md`              | Add `ac` to YQ property description table            | Reference    |
| `docs/concepts/quality.md`                     | Add `ac` field definition, AI-Solve quality tier     | Concepts     |
| `docs/architecture/tools/katago-enrichment.md` | Add AI-Solve phase description, design rationale     | Architecture |
| `docs/how-to/backend/enrichment-lab.md`        | Add `--allow-ai-solve` usage, position-only workflow | How-To       |
| `docs/reference/enrichment-config.md`          | Add `ai_solve` config section reference table        | Reference    |
| `CHANGELOG.md`                                 | Add AI-Solve feature entry                           | Changelog    |

**Cross-references required** (per documentation rules):

- Architecture doc → links to Concepts (quality.md) and How-To (enrichment-lab.md)
- How-To doc → links to Architecture (rationale) and Reference (config)
- Concepts doc → links to Architecture (design) and Reference (config)

---

## Test Plan

### Unit Tests: `tests/test_solve_position.py`

```python
class TestClassifyMoveQuality:
    """Test winrate delta classification thresholds."""

    def test_good_move_below_t_good(self):
        """Δwr < 0.02 → TE (tesuji)."""

    def test_bad_move_above_t_bad(self):
        """Δwr > 0.08 → BM (bad move)."""

    def test_hotspot_above_t_hotspot(self):
        """Δwr > 0.25 → BM + HO (blunder hotspot)."""

    def test_neutral_between_good_and_bad(self):
        """T_good < Δwr < T_bad → neutral."""

    def test_sign_adjustment_black_to_play(self):
        """Black's winrate drop is positive Δwr."""

    def test_sign_adjustment_white_to_play(self):
        """White's winrate drop is positive Δwr (inverted)."""

    def test_thresholds_from_config(self):
        """Thresholds read from config, not hardcoded."""

    def test_all_moves_classified(self):
        """Every move in analysis gets a classification."""


class TestSolvePosition:
    """Test the main solve_position() function with mock engine."""

    async def test_finds_correct_move_for_simple_position(self):
        """Mock engine returns clear top move → SolveResult with 1 correct move."""

    async def test_rejects_when_no_confident_move(self):
        """All moves have similar winrate (gap < min_winrate_gap) → empty correct_moves."""

    async def test_detects_miai_two_correct_moves(self):
        """Two moves both above threshold, gap between them < T_good → 2 correct moves returned."""

    async def test_confirmation_rejects_false_positive(self):
        """Top move + opponent response drops below min_delta_after_opponent → rejected."""

    async def test_confirmation_disabled(self):
        """config.ai_solve.confirmation.enabled=False → skip confirmation, accept top move."""

    async def test_builds_solution_continuation(self):
        """Solution PV extends beyond first move (opponent response + continuation)."""

    async def test_respects_max_correct_moves_config(self):
        """Never returns more than config.ai_solve.max_correct_moves."""

    async def test_respects_solve_visits_config(self):
        """Engine queried with config.ai_solve.solve_visits, not default_max_visits."""

    async def test_returns_goal_inference(self):
        """SolveResult.goal_inference populated based on score/ownership analysis."""


class TestConfirmCorrectMove:
    """Test the confirmation query logic."""

    async def test_strong_move_passes_confirmation(self):
        """Winrate stays high after opponent response → True."""

    async def test_weak_move_fails_confirmation(self):
        """Winrate drops below threshold after opponent response → False."""

    async def test_uses_confirmation_visits_from_config(self):
        """Confirmation query uses config.ai_solve.confirmation_visits."""


class TestBuildSolutionContinuation:
    """Test solution path construction."""

    async def test_builds_mainline(self):
        """Correct move + opponent + continuation → list of SGF coords."""

    async def test_stops_at_max_depth(self):
        """Does not exceed config.ai_solve.solution_max_depth."""

    async def test_handles_9x9_coordinates(self):
        """GTP↔SGF conversion correct for 9×9 board."""


class TestInjectSolutionIntoSgf:
    """Test SGF tree mutation."""

    def test_adds_correct_child_node(self):
        """Root gains ;B[xx]C[Correct] child with TE[] marker."""

    def test_adds_wrong_branches(self):
        """Root gains ;B[yy]C[Wrong] children for BM-classified moves with BM[] marker."""

    def test_extract_correct_first_move_succeeds_after_injection(self):
        """After injection, extract_correct_first_move(root) returns the AI-solved move."""

    def test_preserves_existing_root_properties(self):
        """AB, AW, SZ, FF, GM, PL, C[] all unchanged after injection."""

    def test_white_to_play_injects_w_node(self):
        """PL[W] → injects ;W[coord]C[Correct], not ;B[coord]."""

    def test_solution_continuation_as_grandchildren(self):
        """Correct child has its own children forming the solution mainline."""


class TestGoalInference:
    """Test puzzle goal detection from KataGo signals."""

    def test_kill_detected_by_score_delta(self):
        """Score delta > score_delta_kill_threshold → goal = kill."""

    def test_ko_detected_by_oscillating_pv(self):
        """PV contains repeated captures → goal = ko."""

    def test_live_detected_by_ownership_shift(self):
        """Target group ownership flips to > alive threshold → goal = live."""

    def test_unknown_when_ambiguous(self):
        """No clear signal → goal = unknown."""
```

### Integration Tests: `tests/test_ai_solve_integration.py`

```python
class TestAiSolveEndToEnd:
    """End-to-end tests with mock engine through full enrich_single_puzzle()."""

    async def test_position_only_sgf_enriched_successfully(self):
        """SGF with no children + allow_ai_solve=True → full AiAnalysisResult with status != REJECTED."""

    async def test_existing_solution_bypasses_ai_solve(self):
        """SGF with ;B[xx]C[Correct] child → AI-Solve never called, ai_solved=False."""

    async def test_ai_solve_disabled_rejects_position_only(self):
        """config.ai_solve.enabled=False + allow_ai_solve=False → _make_error_result as today."""

    async def test_cli_flag_overrides_config(self):
        """config.ai_solve.enabled=False + allow_ai_solve=True → AI-Solve runs."""

    async def test_yq_includes_ac_field_for_ai_solved(self):
        """AI-solved puzzle → YQ contains ac:1."""

    async def test_yq_omits_ac_field_for_human_solved(self):
        """Human-solved puzzle → YQ does NOT contain ac."""

    async def test_phase_timings_include_ai_solve(self):
        """AiAnalysisResult.phase_timings has "ai_solve" key with > 0 value."""

    async def test_ai_solved_flag_set_correctly(self):
        """AiAnalysisResult.ai_solved is True for AI-solved, False for human-solved."""

    async def test_refutations_work_after_ai_solve(self):
        """AI-solved puzzle → refutations generated normally (non-empty RefutationResult)."""

    async def test_difficulty_estimated_after_ai_solve(self):
        """AI-solved puzzle → DifficultySnapshot populated (not sentinel values)."""
```

### Calibration Tests: `tests/test_ai_solve_calibration.py`

```python
@pytest.mark.calibration
class TestAiSolveCalibration:
    """Real KataGo runs against known position-only puzzles.

    Requires live KataGo binary + model. Skipped in CI without GPU.
    Uses fixtures from tests/fixtures/ai_solve/ directory.
    """

    async def test_cho_elementary_problem_1(self):
        """Cho Chikun Elementary #1 (corner L&D) — AI-Solve finds B[ac] or equivalent."""

    async def test_cho_elementary_batch_5(self):
        """Batch of 5 Cho Chikun elementary puzzles — ≥80% correctly solved."""

    async def test_9x9_tsumego(self):
        """9×9 tsumego — correct solution with proper coordinate conversion."""

    async def test_classification_thresholds_reasonable(self):
        """For a known puzzle: TE moves are actually correct, BM moves are actually wrong."""
```

---

## Implementation Order

| Phase                     | Files Changed/Created                                                                                     | Effort | Dependencies                                                                                               |
| ------------------------- | --------------------------------------------------------------------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------- |
| **P1: Config**            | `config.py` (add `AiSolveConfig` + sub-models), `config/katago-enrichment.json` (add section, bump v1.14) | Small  | None                                                                                                       |
| **P2: Model**             | `models/solve_result.py` (NEW)                                                                            | Small  | P1                                                                                                         |
| **P3: Core solver**       | `analyzers/solve_position.py` (NEW — ~200 lines)                                                          | Medium | P1, P2, existing `engine/local_subprocess.py`, `models/analysis_request.py`, `models/analysis_response.py` |
| **P4: Integration**       | `analyzers/enrich_single.py` (Step 2 conditional, ~40 lines added)                                        | Small  | P3                                                                                                         |
| **P5: CLI**               | `cli.py` (`--allow-ai-solve` flag, pass to `enrich_single_puzzle`)                                        | Small  | P4                                                                                                         |
| **P6: Quality tracking**  | `analyzers/sgf_enricher.py` (YQ `ac` field), `models/ai_analysis_result.py` (`ai_solved` field)           | Small  | P4                                                                                                         |
| **P7: Unit tests**        | `tests/test_solve_position.py` (NEW — ~250 lines)                                                         | Medium | P3                                                                                                         |
| **P8: Integration tests** | `tests/test_ai_solve_integration.py` (NEW — ~150 lines)                                                   | Medium | P4, P5, P6                                                                                                 |
| **P9: Calibration tests** | `tests/test_ai_solve_calibration.py` (NEW — ~100 lines), `tests/fixtures/ai_solve/` (NEW)                 | Medium | P3, P4, live KataGo                                                                                        |
| **P10: Documentation**    | See documentation table above (~9 files)                                                                  | Small  | P6                                                                                                         |

**Total estimated scope:**

- ~500 lines of new code (3 new files: `solve_position.py`, `solve_result.py`, test files)
- ~50 lines of modified code (4 modified files: `enrich_single.py`, `cli.py`, `config.py`, `sgf_enricher.py`)
- ~500 lines of tests (3 new test files)
- ~9 documentation files updated

---

## Risks and Mitigations

| Risk                                                  | Severity              | Mitigation                                                                                                                                    |
| ----------------------------------------------------- | --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| KataGo finds wrong correct move for complex positions | MEDIUM                | Confirmation query (play move + check opponent); `min_winrate_gap` threshold; `ac:1` quality flag lets downstream filter                      |
| Dual-solution confusion (book answer vs AI answer)    | LOW                   | This is a feature, not a bug. `max_correct_moves=2` + miai detection. Learning platform values exploration.                                   |
| Performance: extra KataGo queries for AI-Solve        | LOW                   | Only runs for position-only puzzles; `solve_visits=1000` is comparable to existing `deep_enrich.visits=2000`; confirmation adds 1 extra query |
| Seki false positives (winrate ~0.5, ambiguous)        | MEDIUM                | `goal_inference` config; seki-specific ownership check; reject when confidence="low"                                                          |
| Ko oscillation confusing threshold logic              | MEDIUM                | Reuse existing `ko_analysis` config from enrichment; `ko_detection` module handles PV repeat detection                                        |
| Breaking existing behavior                            | **NONE**              | Feature gated behind `config.ai_solve.enabled=false` + `--allow-ai-solve` flag. Default OFF. Existing tests unaffected.                       |
| Advanced/expert puzzles where AI misreads             | HIGH for those levels | `ac:1` quality flag; `min_winrate_gap` prevents low-confidence solves; future: human review queue for `ac:1` puzzles                          |

### Cho Chikun (9p) Risk Assessment

> "For elementary to upper-intermediate (30k-6k), KataGo at 1000 visits with tsumego config is reliable. The real danger is dan-level puzzles where reading depth matters — a position where both sides have multiple ko threats and the correct answer requires reading 15+ moves. For those, solve_visits should be escalated to 2000-5000, or the puzzle should be flagged for human review. The confirmation query is essential — it catches the 'looks good but dies to a tesuji' case that even strong players sometimes miss on first glance."

---

## Non-Goals (Explicitly Out of Scope)

- **Full branching solution tree generation.** AI-Solve produces a mainline (first correct move + continuation PV). Deep branching trees (opponent has multiple responses, each with correct follow-up) are a future extension.
- **Replacing human-authored solutions.** AI-Solve is additive. When a solution tree exists, it is never overwritten or modified.
- **Auto-enabling for all sources.** Each source must opt-in via config or CLI flag. No source silently gets AI-Solve.
- **AI difficulty estimation bypass.** AI-solved puzzles still go through the full difficulty estimation pipeline. `ac:1` is metadata, not a skip flag.

---

## Appendix A: Worked Example

**Input SGF (position-only, from `external-sources/tasuki/cho-chikun-elementary/batch-001/problem_0001_p1.sgf`):**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]
C[problem 1 | Source: Cho Chikun - Encyclopedia of Life & Death - Elementary]
AB[be][dc][cc][eb][fb][bc]AW[bb][ab][db][da][cb])
```

**Step 2: `extract_correct_first_move(root)` → `None`** (no children)

**Step 2b: AI-Solve runs with `solve_visits=1000`:**

| Move (GTP) | Move (SGF) | Winrate | Δwr   | Policy | Classification |
| ---------- | ---------- | ------- | ----- | ------ | -------------- |
| A3         | ac         | 0.98    | -0.01 | 0.45   | TE (correct)   |
| B1         | ba         | 0.62    | 0.35  | 0.12   | BM+HO          |
| C1         | ca         | 0.55    | 0.42  | 0.08   | BM+HO          |
| A4         | ad         | 0.71    | 0.26  | 0.05   | BM+HO          |

**Confirmation:** Play B[ac], opponent responds W[ba] → Black winrate 0.97 → `min_delta_after_opponent` (0.10) check PASSED.

**Solution continuation:** `B[ac] → W[ba] → B[aa]` (3 moves deep, group captured)

**`inject_solution_into_sgf()` result:**

```sgf
(;SZ[19]FF[4]GM[1]PL[B]
C[problem 1 | Source: Cho Chikun - Encyclopedia of Life & Death - Elementary]
AB[be][dc][cc][eb][fb][bc]AW[bb][ab][db][da][cb]
(;B[ac]C[Correct]
  ;W[ba]
  ;B[aa])
(;B[ba]C[Wrong])
(;B[ca]C[Wrong]))
```

**Pipeline continues (Steps 3-9):** validate → refutations → difficulty → hints → `AiAnalysisResult` with:

- `ai_solved=True`
- `YQ[q:1;rc:0;hc:0;ac:1]`
- `phase_timings={"parse": 0.01, "ai_solve": 1.23, "query": 0.02, "validate": 0.85, ...}`

---

## Appendix B: Relationship to Existing Refutation Logic

The AI-Solve design intentionally mirrors `generate_refutations.py` to maintain architectural consistency:

| Concept               | `generate_refutations.py` (existing)                        | `solve_position.py` (new)                             |
| --------------------- | ----------------------------------------------------------- | ----------------------------------------------------- |
| Engine query          | `AnalysisRequest.with_puzzle_region()`                      | Same                                                  |
| Move filtering        | `identify_candidates()` → exclude correct, filter by policy | `classify_move_quality()` → classify all moves by Δwr |
| Core threshold        | `delta_threshold=0.08` (move is "wrong enough")             | `T_bad=0.08` (same value, inverse meaning)            |
| Per-move query        | `generate_single_refutation()` → play wrong, get opponent   | `confirm_correct_move()` → play correct, get opponent |
| PV extraction         | `opp_best.pv[:pv_cap]` → refutation sequence                | `build_solution_continuation()` → solution mainline   |
| Escalation            | `RefutationEscalationConfig` → retry with higher visits     | `AiSolveConfirmation` → verify with opponent response |
| Coordinate conversion | `gtp_to_sgf()`, `sgf_to_gtp()` with `board_size`            | Same functions, same board_size awareness             |
| Config source         | `config.refutations.*`                                      | `config.ai_solve.*`                                   |
| Logging               | `log_with_context(stage="refutations")`                     | `log_with_context(stage="ai_solve")`                  |

This parallelism is deliberate — it means developers familiar with one module can immediately understand the other.
