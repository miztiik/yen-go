# Implementation Plan: Puzzle Quality Scorer

**Created:** 2026-02-27  
**Status:** Ready for implementation  
**Depends on:** Strategy D plan (position fingerprinting, dedup, content-type classification)  
**Addresses:** Strategy D deferred item D2 (Difficulty Classifier Improvement) + new capabilities  
**Source repos:** [PLNech/gogogo](https://github.com/PLNech/gogogo) (GPL-3.0), [zhoumeng-creater/gogamev4.0](https://github.com/zhoumeng-creater/gogamev4.0) (MIT)

---

## Executive Summary

Add **tactical pattern analysis** to the yen-go pipeline, enabling:

1. **Auto-tag technique detection** — automatically assign YT tags (ladder, snapback, eye-shape, seki, etc.) based on position analysis
2. **Position validation** — flag broken puzzles where the objective contradicts the board state
3. **Difficulty scoring signals** — feed tactical complexity into the difficulty classifier
4. **Enhanced hint generation** — generate richer YH hints from detected patterns

All analysis is **symbolic** (no ML/AI), **CPU-only**, and runs at **pipeline time** (analyze stage). Reuses the existing `core/board.py` Board/Group infrastructure.

---

## What We Extract from Each Repository

### From GoGoGo (PLNech/gogogo)

| Algorithm                | What it does                                                    | Yen-go application                                             |
| ------------------------ | --------------------------------------------------------------- | -------------------------------------------------------------- |
| **Ladder tracer**        | Traces diagonal chase sequences, detects breakers               | Auto-tag `ladder`, hint "The chase begins here"                |
| **Snapback detector**    | Detects capture-then-recapture patterns                         | Auto-tag `snapback`, hint "Let them capture — recapture more"  |
| **Capture verifier**     | Alpha-beta (depth 4) verifies forced captures                   | Validate solution correctness, flag trivial vs forced captures |
| **Life/death evaluator** | Minimax with eye counting to ±1/0                               | Validate life-and-death puzzles, auto-tag                      |
| **Instinct patterns**    | 8 named patterns (extend-from-atari, hane-at-head-of-two, etc.) | Auto-tag specific techniques, hint generation                  |
| **Tactical plane count** | Count of active tactical features in position                   | Difficulty signal: 0=trivial, 1-2=focused, 3+=complex          |

### From gogamev4.0 (zhoumeng-creater/gogamev4.0)

| Algorithm                                     | What it does                                           | Yen-go application                                       |
| --------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------- |
| **Eye counting** (true/false eye distinction) | Count real eyes using orthogonal + diagonal validation | Validate life/death outcomes, auto-tag `eye-shape`       |
| **Group status assessment**                   | Classify groups as alive/dead/unsettled                | Position validation: flag puzzles with broken objectives |
| **Weak group detection**                      | Find critical (1 lib), weak (2 lib), unsettled groups  | Difficulty signal + position validation                  |
| **Escape potential**                          | Assess if group can run away                           | Auto-tag `escape`, difficulty signal                     |
| **Seki detection**                            | Identify dual-life situations                          | Auto-tag `seki`                                          |
| **Influence map**                             | Distance-decay strength propagation                    | Position balance → difficulty signal                     |

### What We Do NOT Extract

| Excluded                                       | Why                                                  |
| ---------------------------------------------- | ---------------------------------------------------- |
| MCTS search (GoGoGo)                           | Self-play not relevant to puzzle analysis            |
| Tkinter UI (gogamev4.0)                        | Desktop GUI not applicable                           |
| SQLite puzzle database (gogamev4.0)            | Yen-go has its own state management                  |
| Full game analysis (gogamev4.0 AnalysisEngine) | We analyze static positions, not games               |
| Joseki library (gogamev4.0)                    | Tsumego puzzles don't involve joseki                 |
| Win-rate estimation (gogamev4.0)               | Requires AI engine we don't have                     |

---

## Architecture

### New Module: `core/tactical_analyzer.py`

Single new module. All analysis functions are **pure functions** that take
`SGFGame` or `Board` and return results. No side effects, no state.

```
core/tactical_analyzer.py
├── analyze_tactics(game: SGFGame) → TacticalAnalysis
│   ├── detect_ladder(board, first_move) → LadderResult | None
│   ├── detect_snapback(board, first_move) → bool
│   ├── detect_capture_pattern(board, first_move) → CaptureType
│   ├── count_eyes(board, group) → int
│   ├── assess_group_status(board, group) → GroupStatus
│   ├── find_weak_groups(board, color) → list[WeakGroup]
│   ├── detect_seki(board) → list[SekiRegion]
│   └── detect_instinct_pattern(board, first_move, color) → InstinctType | None
└── compute_tactical_complexity(analysis: TacticalAnalysis) → int
```

### Integration Points

```
                            analyze stage
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     │                           │                           │
┌────▼────┐              ┌───────▼───────┐           ┌───────▼────────┐
│classify()│              │  tag()         │           │  enrich()      │
│(existing)│              │  (existing)    │           │  (existing)    │
└────┬────┘              └───────┬───────┘           └───────┬────────┘
     │                           │                           │
     │              ┌────────────▼────────────┐              │
     │              │ analyze_tactics() [NEW]  │              │
     │              │ → detected techniques    │              │
     │              │ → group status           │              │
     │              │ → tactical complexity    │              │
     │              └────────────┬────────────┘              │
     │                           │                           │
     ▼                           ▼                           ▼
 YG (level)              YT (auto-merged)           YH (enhanced hints)
                         YQ (quality signal)         YX (complexity signal)
```

### Data Flow

1. **Input:** `SGFGame` with initial position (AB/AW) and solution tree
2. **Build board:** Reuse pattern from `hints.py` `_build_board()` — create `core/board.py` `Board` from AB/AW stones
3. **Extract first correct move** from solution tree root
4. **Run tactical analysis:** All detectors run on (initial_board, first_move)
5. **Output:** `TacticalAnalysis` dataclass with all findings
6. **Consume:**
   - `tagger.py` → merge detected techniques into YT (ENRICH_IF_ABSENT)
   - `quality.py` → use tactical depth as quality signal
   - `hints.py` → use detected patterns for richer hints
   - `classifier.py` → use tactical complexity for difficulty estimation

---

## Phase 1: Core Tactical Analysis (~2 weeks)

### 1.1 Data Types

```python
# In core/tactical_analyzer.py

from dataclasses import dataclass
from enum import Enum

class GroupStatus(Enum):
    ALIVE = "alive"
    DEAD = "dead"
    UNSETTLED = "unsettled"

class CaptureType(Enum):
    NONE = "none"
    TRIVIAL = "trivial"       # 1-liberty group, 1-move capture
    FORCED = "forced"         # Multi-move forced sequence
    LADDER = "ladder"         # Ladder capture
    SNAPBACK = "snapback"     # Snapback capture
    NET = "net"               # Net/geta capture

class InstinctType(Enum):
    EXTEND_FROM_ATARI = "extend_from_atari"
    CONNECT_AGAINST_PEEP = "connect_against_peep"
    HANE_AT_HEAD_OF_TWO = "hane_at_head_of_two"
    BLOCK_THRUST = "block_thrust"

@dataclass
class WeakGroup:
    color: Color
    stones: set[Point]
    liberties: int
    status: GroupStatus          # critical / weak / unsettled
    can_escape: bool
    eye_count: int

@dataclass
class LadderResult:
    outcome: str                 # "captured" | "escaped" | "breaker"
    depth: int                   # Moves in the chase
    breaker_point: Point | None  # Location of ladder breaker (if any)

@dataclass
class TacticalAnalysis:
    """Complete tactical analysis of a puzzle position."""
    # Detected techniques (for auto-tagging)
    has_ladder: LadderResult | None
    has_snapback: bool
    capture_type: CaptureType
    has_seki: bool
    instinct: InstinctType | None

    # Group assessment (for validation and difficulty)
    player_weak_groups: list[WeakGroup]
    opponent_weak_groups: list[WeakGroup]

    # Derived metrics
    tactical_complexity: int     # 0-6 scale (count of active features)
    position_valid: bool         # Does objective match position?
    validation_notes: list[str]  # Why position may be invalid
```

### 1.2 Core Detection Functions

**Ladder detection** (from GoGoGo `trace_ladder`):

- Use yen-go's `Board.get_group()` and `Group.liberties` (already exists)
- Trace escape diagonal up to depth 30
- Return `LadderResult` with outcome and depth

**Snapback detection** (from GoGoGo `detect_snapback`):

- Find 1-liberty groups near the first move
- Simulate capture → check if capturing stone has 1 liberty → recapture
- Uses `Board.copy()` + `Board.play()` (already exists)

**Eye counting** (from gogamev4.0 `_is_eye` + `_is_real_eye`):

- Orthogonal: all 4 neighbors must be same color or edge
- Diagonal: ≥3 of 4 must be same color or edge
- Real eye: all orthogonal neighbors in SAME group (not just same color)

**Group status** (from gogamev4.0 `_analyze_group`):

- Decision tree: liberties → eyes → escape → eye-making potential
- Uses eye counting + internal space estimation

**Weak group finder** (from gogamev4.0 `find_weak_groups`):

- Scan all groups, classify by liberty count
- For each weak group: assess escape and eye-making potential

**Instinct detection** (from GoGoGo `instincts.py`):

- After first move: check if it matches extend-from-atari, connect-against-peep,
  hane-at-head-of-two, or block-thrust patterns
- Only check 4 most relevant patterns (skip bump/kosumi/angle — less relevant to tsumego)

### 1.3 Position Validation

**Purpose:** Flag puzzles where the objective contradicts the board state.

```python
def validate_position(board, game, analysis):
    """Check if puzzle objective makes sense given the position."""
    notes = []
    tags = set(game.yengo.tags or [])

    # Life-and-death puzzle: should have at least one threatened group
    if "life-and-death" in tags or "living" in tags:
        has_threatened = any(
            g.status in (GroupStatus.DEAD, GroupStatus.UNSETTLED)
            for g in analysis.player_weak_groups + analysis.opponent_weak_groups
        )
        if not has_threatened:
            notes.append("life-and-death tagged but no threatened groups found")

    # Kill puzzle: opponent should have vulnerable groups
    if "kill" in (game.root_comment or "").lower():
        if not analysis.opponent_weak_groups:
            notes.append("kill objective but no weak opponent groups")

    # Capture puzzle: opponent should have critical/weak groups
    if "capture" in tags:
        if not any(g.liberties <= 2 for g in analysis.opponent_weak_groups):
            notes.append("capture tagged but no low-liberty opponent groups")

    return len(notes) == 0, notes
```

**Impact:** Broken puzzles get q:1 quality. This is a **NEW quality signal**
that doesn't exist in the current pipeline.

### 1.4 Files to Create/Modify

| File                        | Action     | Description                                          |
| --------------------------- | ---------- | ---------------------------------------------------- |
| `core/tactical_analyzer.py` | **CREATE** | All detection functions + TacticalAnalysis dataclass |
| `stages/analyze.py`         | MODIFY     | Call `analyze_tactics()` after existing enrichment   |
| `core/quality.py`           | MODIFY     | Accept tactical analysis as quality signal           |
| `core/enrichment/hints.py`  | MODIFY     | Use detected patterns for richer hints               |

### 1.5 Tests

- **Ladder:** Known ladder position → detected with correct depth. Non-ladder → not detected.
- **Snapback:** Known snapback → detected. Simple capture → not snapback.
- **Eyes:** Known 2-eye position → count=2. False eye → count=0. True eye surrounded by 2 groups → count=0.
- **Group status:** Dead group (0 liberties) → DEAD. 2+ eyes → ALIVE. 1 eye + 2 liberties → UNSETTLED.
- **Position validation:** Life/death puzzle with no threatened groups → flagged. Trivial capture → flagged.
- **Round-trip:** analyze_tactics → TacticalAnalysis is deterministic (same input → same output).

---

## Phase 2: Auto-Tagging Integration (~1 week)

### 2.1 Tag Detection Mapping

| Detected Pattern                     | YT Tag           | Confidence | Condition                             |
| ------------------------------------ | ---------------- | ---------- | ------------------------------------- |
| `has_ladder` with outcome="captured" | `ladder`         | High       | Only if ladder depth ≥ 3              |
| `has_snapback`                       | `snapback`       | High       | Direct pattern match                  |
| `capture_type == NET`                | `net`            | High       | Net/geta detection                    |
| `has_seki`                           | `seki`           | High       | At initial position or after solution |
| Eye counting reveals key technique   | `eye-shape`      | Medium     | Solution changes eye count            |
| Instinct: extend_from_atari          | `escape`         | Medium     | First move extends atari group        |
| Instinct: connect_against_peep       | `connection`     | Medium     | First move connects groups            |
| Instinct: hane_at_head_of_two        | `tesuji`         | Low        | May over-tag                          |
| Weak groups with status=UNSETTLED    | `life-and-death` | Medium     | If not already tagged                 |
| Capture type != NONE                 | `capture`        | Low        | Only if no more specific tag          |

### 2.2 Merge Policy

- All auto-tags use **ENRICH_IF_ABSENT** policy — don't override manually set tags
- If a tag is already present (from source or prior enrichment), skip
- If a conflict exists (e.g., source says `ladder` but analysis says no ladder), **preserve source** (human-curated wins)
- Auto-tags are recorded in pipeline log for audit

### 2.3 Integration into `tagger.py`

```python
# In stages/analyze.py, after existing tag enrichment:
if tactical_analysis:
    auto_tags = derive_auto_tags(tactical_analysis)
    for tag in auto_tags:
        if tag not in game.yengo.tags:
            game.yengo.tags.append(tag)
    game.yengo.tags.sort()  # YT requires sorted, deduplicated
```

### 2.4 Files to Modify

| File                        | Change                                       |
| --------------------------- | -------------------------------------------- |
| `core/tactical_analyzer.py` | Add `derive_auto_tags(analysis) → list[str]` |
| `stages/analyze.py`         | Call auto-tagging after tactical analysis    |

---

## Phase 3: Difficulty Classifier Enhancement (~1 week)

### 3.1 New Signals for Classifier

The existing `core/classifier.py` uses a placeholder additive scorer.
Add three new signals from tactical analysis:

| Signal                | Source                                                            | Range   | Interpretation                   |
| --------------------- | ----------------------------------------------------------------- | ------- | -------------------------------- |
| `tactical_complexity` | Count of active tactical features (ladder, snapback, atari, etc.) | 0–6     | 0=trivial, 3+=complex            |
| `weak_group_count`    | Number of weak/unsettled groups in initial position               | 0–N     | More groups = harder             |
| `position_balance`    | Influence map balance (from gogamev4.0)                           | 0.0–1.0 | 0=balanced (harder), 1=one-sided |

### 3.2 Classifier Score Adjustment

```python
# Conceptual — actual integration TBD based on classifier.py structure
def adjusted_difficulty_score(base_score, tactical_analysis):
    tactical_bonus = tactical_analysis.tactical_complexity * 0.5
    group_bonus = min(len(tactical_analysis.player_weak_groups) +
                      len(tactical_analysis.opponent_weak_groups), 4) * 0.3
    return base_score + tactical_bonus + group_bonus
```

### 3.3 Files to Modify

| File                 | Change                                                |
| -------------------- | ----------------------------------------------------- |
| `core/classifier.py` | Accept `TacticalAnalysis`, use new signals in scoring |

---

## Phase 4: Enhanced Hint Generation (~1 week)

### 4.1 Tactic-Aware Hints

Currently, `hints.py` generates hints based on coordinates and tags.
With tactical analysis, hints can be more specific:

| Detected Pattern | Current YH                    | Enhanced YH                                        |
| ---------------- | ----------------------------- | -------------------------------------------------- |
| Ladder           | "The first move is at {!cg}." | "This begins the ladder chase."                    |
| Snapback         | "Consider the key point."     | "Let them capture — then take back more."          |
| Escape           | "A group needs attention."    | "A group is in danger — extend to gain liberties." |
| Eye shape        | "Look at the shape."          | "The key is creating (or destroying) eye space."   |
| Seki             | (none)                        | "Neither side can capture — find the balance."     |

### 4.2 Implementation

Add a method to `HintGenerator` that takes `TacticalAnalysis` and produces
pattern-aware hint text for YH[1] (conceptual hint):

```python
def generate_tactical_hint(self, analysis: TacticalAnalysis) -> str | None:
    if analysis.has_ladder and analysis.has_ladder.outcome == "captured":
        return "This begins the chase."
    if analysis.has_snapback:
        return "Let them capture — then take back more."
    if analysis.instinct == InstinctType.EXTEND_FROM_ATARI:
        return "A group is in danger — extend to gain liberties."
    # ... etc
    return None
```

### 4.3 Files to Modify

| File                       | Change                                                                |
| -------------------------- | --------------------------------------------------------------------- |
| `core/enrichment/hints.py` | Add `generate_tactical_hint()`, integrate with existing hint pipeline |

---

## Performance Budget

| Operation                 | Per-puzzle cost | Total (~194K puzzles) | Parallelizable |
| ------------------------- | --------------: | --------------------: | :------------: |
| Build board from AB/AW    |          ~0.1ms |                  ~20s |      Yes       |
| Ladder detection          |            ~2ms |                 ~6min |      Yes       |
| Snapback detection        |          ~0.5ms |               ~1.5min |      Yes       |
| Eye counting (all groups) |            ~1ms |                 ~3min |      Yes       |
| Group status (all groups) |            ~1ms |                 ~3min |      Yes       |
| Weak group finding        |          ~0.5ms |               ~1.5min |      Yes       |
| Instinct detection        |          ~0.5ms |               ~1.5min |      Yes       |
| **Total per puzzle**      |        **~6ms** |            **~20min** |      Yes       |

At ~6ms per puzzle, the total analysis adds ~20 minutes to a full pipeline
run — acceptable for a batch process. Per-batch parallelism (existing `pytest -n auto`
pattern) would reduce wall-clock time to ~5 minutes on 4 cores.

---

## Dependency Analysis

### New Dependencies: NONE

All algorithms use only:

- `core/board.py` — `Board`, `Group`, `Point`, `Color` (already exists)
- `core/sgf_parser.py` — `SGFGame`, `SolutionNode` (already exists)
- Standard library: `dataclasses`, `enum`, `typing`, `logging`

No new entries in `pyproject.toml`. No new external libraries.

### Existing Code Reuse

| Existing Code                                    | Reused For                            |
| ------------------------------------------------ | ------------------------------------- |
| `Board.get_group()`                              | Group finding, liberty counting       |
| `Board.copy()` + `Board.play()`                  | Simulating moves for ladder/snapback  |
| `Group.liberties`                                | Liberty analysis for all detectors    |
| `Point.neighbors()`                              | Adjacency checks                      |
| `Color.opponent()`                               | Color switching                       |
| `_build_board()` from hints.py                   | Building board from SGF initial state |
| `move_captures_stones()` from solution_tagger.py | Capture detection                     |
| `_analyze_liberties()` from hints.py             | Liberty situation analysis            |

---

## Schema Impact

### No new SGF properties

Tactical analysis results flow into EXISTING properties:

- `YT` — additional auto-tags (already supports multiple tags)
- `YH` — enhanced hints (already supports 3 hints)
- `YQ` — quality score adjustment (already has q:1-5)
- `YX` — tactical complexity could extend existing format

### Optional: Extend YX with tactical complexity

```
Current:  YX[d:5;r:13;s:24;u:1;a:3]
Extended: YX[d:5;r:13;s:24;u:1;a:3;tc:4]
```

Where `tc` = tactical complexity (0-6). This is the count of distinct
tactical patterns detected in the position.

**Decision required:** Is extending YX worth the schema change?
Alternative: store only in pipeline log, derive from tags at query time.

> **Recommendation:** Defer YX extension. Tactical complexity can be derived
> from YT tags (count of technique-specific tags). YAGNI.

---

## Verification Plan

| Phase       | Unit Tests                                                                                                                                                                    | Integration Test                                                                       |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **Phase 1** | Ladder: known position → detected. Snapback: known position → detected. Eyes: 2-eye alive → 2. False eye → 0. Group status: dead → DEAD. Validation: broken puzzle → flagged. | Full pipeline run with diagnostic logging → tactical analysis recorded for each puzzle |
| **Phase 2** | Auto-tag: ladder detected → YT includes "ladder". No conflict with existing tags. Tag dedup works.                                                                            | Re-run goproblems source → check auto-tags enrich ~20% of puzzles                      |
| **Phase 3** | Classifier with tactical signals → scores differ from base. Same puzzle, different tactical complexity → different scores.                                                    | Compare difficulty distribution before/after                                           |
| **Phase 4** | Known patterns → correct hint text. No pattern → fallback to existing hints.                                                                                                  | Spot-check: 20 random puzzles have reasonable hints                                    |

**Commands:**

```bash
# Phase 1 validation
cd backend/puzzle_manager && pytest tests/unit/test_tactical_analyzer.py -v

# Quick validation after any change
cd backend/puzzle_manager && pytest -m "not (cli or slow)"

# Full pipeline test
python -m backend.puzzle_manager run --source goproblems --stage analyze
```

---

## Risk Assessment

| Risk                                                      | Probability | Impact | Mitigation                                              |
| --------------------------------------------------------- | :---------: | :----: | ------------------------------------------------------- |
| Ladder detection too slow on large boards                 |     Low     | Medium | Depth limit (30) caps worst case                        |
| False positive auto-tags                                  |   Medium    |  Low   | ENRICH_IF_ABSENT policy → human tags always win         |
| Eye counting inaccurate for complex shapes                |   Medium    |  Low   | Use only for ≥2 eyes (alive) threshold, not exact count |
| Position validation too strict                            |   Medium    | Medium | Log-only first (don't drop puzzles), tune thresholds    |
| Group status heuristics differ from professional judgment |    High     |  Low   | Status is a signal, not final judgment                  |

---

## Phasing & Effort Estimate

| Phase                                 | Effort       | Dependencies               | Deliverables                                                 |
| ------------------------------------- | ------------ | -------------------------- | ------------------------------------------------------------ |
| **Phase 1:** Core tactical analysis   | ~2 weeks     | None (uses existing Board) | `core/tactical_analyzer.py`, unit tests, position validation |
| **Phase 2:** Auto-tagging integration | ~1 week      | Phase 1                    | Tag derivation, tagger integration, integration tests        |
| **Phase 3:** Difficulty classifier    | ~1 week      | Phase 1                    | Classifier enhancement, calibration                          |
| **Phase 4:** Enhanced hints           | ~1 week      | Phase 1 + Phase 2          | Tactic-aware hint generation                                 |
| **Total**                             | **~5 weeks** |                            |                                                              |

Phases 2, 3, 4 can run in parallel after Phase 1 is complete.
With parallelization: **~3 weeks total**.

---

## Relationship to Strategy D Plan

This plan is **complementary**, not conflicting:

| Strategy D Component                     | This Plan's Component              | Interaction                                                               |
| ---------------------------------------- | ---------------------------------- | ------------------------------------------------------------------------- |
| Position fingerprinting (D Phase 1)      | —                                  | Independent, no conflict                                                  |
| Dedup registry (D Phase 1)               | —                                  | Independent                                                               |
| Content-type classification (D Phase 2)  | Position validation (Phase 1)      | Tactical analysis feeds into content-type: trivial capture → training (3) |
| Quality scoring config (D Phase 1)       | Tactical quality signals (Phase 1) | Both feed `compute_puzzle_quality_level()`                                |
| Frontend tabs (D Phase 3)                | —                                  | Independent                                                               |
| **D2 (deferred): Difficulty classifier** | **Phase 3 (this plan)**            | THIS PLAN implements D2                                                   |

**Implementation order recommendation:**

1. Strategy D Phase 1 (fingerprinting, dedup)
2. **This plan Phase 1** (tactical analyzer)
3. Strategy D Phase 2 (content-type) — uses tactical analysis for trivial capture
4. **This plan Phases 2-4** (auto-tagging, classifier, hints)
5. Strategy D Phase 3 (frontend tabs)

---

## Summary

**One new file** (`core/tactical_analyzer.py`) + modifications to 4 existing
files. **Zero new dependencies**. All algorithms are symbolic, deterministic,
CPU-only. Reuses existing Board/Group infrastructure. Adds ~20 minutes to
full pipeline run. Enriches ~60% of puzzles with additional tags, hints,
and quality signals.

**Key principle from GoGoGo:** "Separate pattern recognition from tactical
verification." We detect patterns symbolically, then verify with shallow search.

**Key principle from gogamev4.0:** "Group assessment provides the vocabulary
for position evaluation." Liberty count + eye count + escape potential = the
language of tsumego quality.

---

## See Also

- [reference/gogogo-tactics.md](reference/gogogo-tactics.md) — Ladder, snapback, capture, life/death algorithms
- [reference/gogogo-instincts.md](reference/gogogo-instincts.md) — 8 instinct pattern detectors
- [reference/gogamev4-territory.md](reference/gogamev4-territory.md) — Territory, eye counting, group status
- [reference/gogamev4-analysis.md](reference/gogamev4-analysis.md) — Analysis engine, mistake detection, weak groups
- [../puzzle-quality-strategy/002-implementation-plan-strategy-d.md](../puzzle-quality-strategy/002-implementation-plan-strategy-d.md) — Strategy D plan
