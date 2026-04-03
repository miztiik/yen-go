# Implementation Plan: KataGo Puzzle Enrichment

**Created:** 2026-02-25  
**Status:** Draft — ready for implementation  
**Based on:** [001-research-browser-and-local-katago-for-tsumego.md](001-research-browser-and-local-katago-for-tsumego.md)

---

## Phasing Overview

|      Phase      | Scope                                                          | Deliverable                                       | Dependency                 |
| :-------------: | -------------------------------------------------------------- | ------------------------------------------------- | -------------------------- |
|      **A**      | Validate + Refutations + Difficulty                            | Side-quest tool in `tools/puzzle-enrichment-lab/` | KataGo binary + model file |
|      **B**      | Teaching comments + Technique classification + Hint generation | Extend side-quest with pattern taxonomy           | Phase A working            |
| **Integration** | Merge into `backend/puzzle_manager/` analyze stage             | New `enrich_katago` sub-stage                     | Phase A proven at scale    |

**Phase A is the focus of this plan.** Phase B and Integration are outlined for future reference.

---

## Phase A: Core Enrichment (Side-Quest)

### A.1 — Validate Correct Moves

**Goal:** Given an SGF with a solution tree, confirm KataGo agrees the correct first move is indeed correct.

**Input:** SGF string (pasted or loaded)  
**Output:** Structured result:

```python
class ValidationResult(BaseModel):
    puzzle_id: str
    correct_move: str                    # SGF coord, e.g. "cg"
    katago_agrees: bool
    katago_top_move: str                 # What KataGo thinks is best
    katago_top_move_policy: float        # Policy prior for KataGo's top pick
    correct_move_policy: float           # Policy prior for the SGF's correct move
    correct_move_winrate: float          # Winrate after playing correct move
    correct_move_ownership_delta: dict   # Key stones' ownership before/after
    visits_used: int
    confidence: str                      # "high" | "medium" | "low"
    flags: list[str]                     # ["ko_position", "seki_candidate", etc.]
```

**Method:**

1. Parse SGF → extract initial stones, player to move, correct first move
2. Send position to KataGo (analysis mode, maxVisits=200)
3. Check if correct move is in top-3 KataGo moves
4. Play correct move → re-analyze → check value stays > 0.8
5. Compare ownership before/after for puzzle-region stones

**Success criteria:** KataGo's top-1 move matches SGF correct move on ≥80% of test puzzles. Top-3 match on ≥95%.

### A.2 — Generate Wrong-Move Refutations

**Goal:** Find 1-3 plausible wrong first moves and their refutation sequences.

**Input:** SGF string + ValidationResult from A.1  
**Output:**

```python
class Refutation(BaseModel):
    wrong_move: str                      # SGF coord
    wrong_move_policy: float             # How "tempting" it looks
    refutation_sequence: list[str]       # PV after wrong move (2-4 moves)
    winrate_after_wrong: float           # Puzzle-player's winrate after wrong + response
    winrate_delta: float                 # Drop from initial position
    ownership_consequence: dict          # Which stones die/live

class RefutationResult(BaseModel):
    puzzle_id: str
    refutations: list[Refutation]        # 1-3 refutations, sorted by policy desc
    total_candidates_evaluated: int
    visits_per_candidate: int
```

**Method:**

1. From A.1's KataGo output, get top-5 policy moves
2. Remove the correct move(s)
3. For each remaining candidate (policy > 0.05):
   - Play it → run KataGo analysis (maxVisits=100)
   - If winrate drops below 0.3 → confirmed wrong move
   - Record PV (2-4 moves) as refutation sequence
4. Sort by policy descending, keep top 3

**Architectural limit: 3 refutations maximum.**

- Rationale: top policy move is the most "human-like" mistake. Beyond 3, moves are so unlikely that refutations have little teaching value.
- Each refutation costs ~100 MCTS visits (~0.5-1s local, ~5-10s browser)

### A.3 — Estimate Difficulty

**Goal:** Produce a KataGo-derived difficulty estimate mapping to Yen-Go's 9-level system.

**Input:** ValidationResult + RefutationResult  
**Output:**

```python
class DifficultyEstimate(BaseModel):
    puzzle_id: str
    policy_prior: float                  # Correct move's raw policy
    visits_to_solve: int                 # Visits before value > 0.9
    solution_depth: int                  # PV length for correct line
    refutation_count: int                # Number of plausible wrong moves
    raw_difficulty_score: float          # Composite 0-100
    estimated_level: str                 # "novice" .. "expert"
    estimated_level_id: int              # Numeric ID from puzzle-levels.json
    confidence: str                      # "high" | "medium" | "low"
```

**Method:**

1. Extract metrics from A.1 and A.2 results (zero additional KataGo calls needed)
2. Compute composite score:
   ```
   raw_score = w1 * (1 - policy_prior) + w2 * log(visits_to_solve) + w3 * solution_depth + w4 * refutation_count
   ```
3. Map raw_score to level via calibration table (initially hand-tuned, later fitted to known-rated puzzles)

**This is the cheapest task — it requires no additional KataGo calls beyond A.1 + A.2.**

---

## Phase B: Teaching & Classification (Future)

### B.1 — Teaching Comments (Move-level `C[]`)

**Goal:** Generate natural-language explanations for correct and wrong moves.

**Approach:** Template engine with ~15 pattern detectors. Each detector examines KataGo signals (ownership delta, PV pattern, capture count) and selects a template.

**Example output:**

```sgf
;B[cg]C[Correct! This move creates a vital eye, giving the group two eyes.
White cannot prevent both eyes from forming.]
```

### B.2 — Technique Classification

**Goal:** Detect which tsumego technique applies (eye-making, snapback, ladder, ko, seki, throw-in, net, etc.)

**Approach:** Build classifiers on top of KataGo signals:

- Ownership delta patterns → eye-making, killing
- PV capture patterns → snapback, under-the-stones
- Liberty counting → semeai, damezumari
- Board geometry → ladder, net

### B.3 — Hint Generation Refinement

**Goal:** Improve existing `YH` hints using KataGo's understanding of the position.

**Approach:** Use ownership head to identify the critical region, policy to find the vital point, generate hints at 3 levels of specificity (area → shape → coordinate).

---

## Side-Quest Implementation: `tools/puzzle-enrichment-lab/`

### Design Principles

1. **Completely isolated** from `backend/puzzle_manager/` — zero imports across the boundary
2. **Consciously duplicated** — SGF parsing, coordinate logic reimplemented locally
3. **Structured payloads everywhere** — Pydantic models for all inter-function communication
4. **Clean interface boundaries** — every function takes/returns a typed model, never raw dicts
5. **Dual-backend ready** — same analysis interface for local engine and browser TF.js
6. **Future API-ready** — structured payloads can become REST request/response bodies trivially

### Directory Structure

```
tools/puzzle-enrichment-lab/
├── README.md                         # Setup instructions, model download
├── requirements.txt                  # pydantic, fastapi, uvicorn, sgfmill
│
├── index.html                        # Main UI — SGF input + board + results
├── css/
│   └── lab.css
├── js/
│   ├── app.js                        # UI controller
│   ├── sgf-display.js                # Board rendering (uses BesoGo or simple SVG)
│   └── katago-client.js              # HTTP client → bridge.py
│
├── models/                           # Pydantic data models (structured payloads)
│   ├── __init__.py
│   ├── position.py                   # Board position, stones, player-to-move
│   ├── analysis_request.py           # → KataGo engine
│   ├── analysis_response.py          # ← KataGo engine
│   ├── validation_result.py          # Task A.1 output
│   ├── refutation_result.py          # Task A.2 output
│   └── difficulty_result.py          # Task A.3 output
│
├── engine/                           # KataGo communication layer
│   ├── __init__.py
│   ├── protocol.py                   # Abstract engine protocol
│   ├── local_subprocess.py           # Drives katago via stdin/stdout
│   └── config.py                     # Engine paths, model paths, visit limits
│
├── analyzers/                        # Enrichment logic (pure functions)
│   ├── __init__.py
│   ├── validate_solution.py          # A.1: correct move validation
│   ├── generate_refutations.py       # A.2: wrong move + refutation PV
│   ├── estimate_difficulty.py        # A.3: difficulty scoring
│   └── sgf_parser.py                 # Minimal SGF → Position (local, no backend import)
│
├── bridge.py                         # HTTP bridge (FastAPI)
│   # POST /analyze     → full analysis (A.1 + A.2 + A.3)
│   # POST /validate    → A.1 only
│   # POST /refutations → A.2 only
│   # POST /difficulty  → A.3 only
│   # GET  /health      → engine status
│
└── tests/
    ├── __init__.py
    ├── test_sgf_parser.py
    ├── test_validate_solution.py
    ├── test_generate_refutations.py
    ├── test_estimate_difficulty.py
    └── fixtures/
        ├── simple_life_death.sgf
        ├── ko_puzzle.sgf
        └── seki_puzzle.sgf
```

### UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  KataGo Lab — Tsumego Enrichment Workbench                     │
├─────────────────────────┬───────────────────────────────────────┤
│                         │  SGF Input                           │
│                         │  ┌─────────────────────────────────┐ │
│                         │  │ (;FF[4]GM[1]SZ[19]             │ │
│                         │  │  ;B[cg];W[dg];B[cf])           │ │
│   ┌─────────────────┐   │  └─────────────────────────────────┘ │
│   │                 │   │                                       │
│   │   Go Board      │   │  Engine: [Local ▼] [Browser (GPU)]   │
│   │   (BesoGo or    │   │  Model:  [b15c192 ▼]                │
│   │    SVG render)   │   │  Visits: [200    ]                  │
│   │                 │   │                                       │
│   │                 │   │  [ Analyze ]                          │
│   └─────────────────┘   │                                       │
│                         ├───────────────────────────────────────┤
│                         │  Results                              │
│                         │                                       │
│                         │  Validation: ✓ Correct move C7       │
│                         │    KataGo top: C7 (policy=0.42)      │
│                         │    Winrate after: 95.3%              │
│                         │                                       │
│                         │  Refutations:                        │
│                         │    1. B8 (policy=0.18) → W:C7 B:D7  │
│                         │       Winrate: 12% (dead)            │
│                         │    2. D8 (policy=0.09) → W:C7 B:C8  │
│                         │       Winrate: 8% (dead)             │
│                         │                                       │
│                         │  Difficulty: intermediate (score: 42) │
│                         │    Policy prior: 0.42                │
│                         │    Solution depth: 3                 │
│                         │    Visits to solve: 45               │
├─────────────────────────┴───────────────────────────────────────┤
│  Status: Connected to local engine (b15c192, 200 visits)       │
└─────────────────────────────────────────────────────────────────┘
```

### HTTP Bridge API (bridge.py)

```
POST /analyze
  Body: { "sgf": "(;FF[4]GM[1]SZ[19]...)", "max_visits": 200 }
  Returns: { "validation": {...}, "refutations": {...}, "difficulty": {...} }

POST /validate
  Body: { "sgf": "...", "max_visits": 200 }
  Returns: ValidationResult

POST /refutations
  Body: { "sgf": "...", "max_refutations": 3, "min_policy": 0.05, "max_visits": 100 }
  Returns: RefutationResult

POST /difficulty
  Body: { "sgf": "...", "max_visits": 200 }
  Returns: DifficultyEstimate

GET /health
  Returns: { "engine": "local", "model": "b15c192", "status": "ready" }
```

All payloads are Pydantic models serialized as JSON — directly convertible to a proper REST API or event-driven pipeline interface later.

### Engine Abstraction

```python
# engine/protocol.py — the interface that both local and browser backends implement

class AnalysisRequest(BaseModel):
    position: Position                    # Stones + board size + player to move
    max_visits: int = 200
    include_ownership: bool = True
    include_pv: bool = True

class MoveAnalysis(BaseModel):
    move: str                             # SGF coordinate
    visits: int
    winrate: float
    score_lead: float
    policy_prior: float
    pv: list[str]
    ownership: list[list[float]] | None   # 19x19 or None

class AnalysisResponse(BaseModel):
    request_id: str
    move_infos: list[MoveAnalysis]
    root_winrate: float
    root_score: float
    total_visits: int

class EngineProtocol(Protocol):
    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse: ...
    async def health(self) -> dict: ...
    async def shutdown(self) -> None: ...
```

Both `LocalSubprocessEngine` and a future `BrowserTFJSEngine` implement this protocol.

---

## Task Checklist

### Phase A — Core Enrichment

- [x] **A.0** Set up `tools/puzzle-enrichment-lab/` directory structure
- [ ] **A.0.1** Create Pydantic models (position, request, response, results)
- [ ] **A.0.2** Implement minimal SGF parser (stones, player, correct move extraction)
- [ ] **A.0.3** Implement local engine subprocess driver (stdin/stdout JSON)
- [ ] **A.0.4** Implement HTTP bridge (FastAPI, 4 endpoints)
- [ ] **A.1** Implement `validate_solution.py` — correct move validation
- [ ] **A.2** Implement `generate_refutations.py` — wrong moves + PV
- [ ] **A.3** Implement `estimate_difficulty.py` — difficulty scoring
- [ ] **A.4** Build `index.html` UI with BesoGo viewer + SGF input + results panel
- [ ] **A.5** Write JS client (`katago-client.js`) to call bridge endpoints
- [ ] **A.6** Write tests with fixture SGFs
- [ ] **A.7** Document setup (README: download KataGo, download model, run bridge)

### Phase B — Teaching & Classification (Future)

- [ ] **B.1** Design pattern taxonomy (~15 techniques)
- [ ] **B.2** Implement pattern detectors on KataGo signals
- [ ] **B.3** Implement template engine for teaching comments
- [ ] **B.4** Implement technique classification
- [ ] **B.5** Implement hint generation refinement
- [ ] **B.6** Add results to UI

### Integration (Future)

- [ ] **I.1** Define interface contract between `tools/puzzle-enrichment-lab/` and `backend/puzzle_manager/`
- [ ] **I.2** Create adapter in backend that calls puzzle-enrichment-lab's analysis functions
- [ ] **I.3** Wire into analyze stage as `enrich_katago` sub-stage
- [ ] **I.4** Map outputs to SGF properties (YR, YG, YX, C[], YT)
- [ ] **I.5** Run at scale on ~50K puzzles, validate results

---

## Key Decisions (Locked)

| Decision                    | Choice                                      | Rationale                                                       |
| --------------------------- | ------------------------------------------- | --------------------------------------------------------------- |
| Side-quest location         | `tools/puzzle-enrichment-lab/`              | Isolated from backend; follows `tools/` convention              |
| No backend imports          | Consciously duplicate SGF parsing, coords   | Clean boundary; future integration via structured payloads      |
| Pydantic everywhere         | All inter-function data as typed models     | API-ready; self-documenting; validates at boundary              |
| Max refutations             | 3                                           | Diminishing returns; each costs ~100 visits                     |
| Refutation policy threshold | 0.05                                        | Below this, moves are too unlikely to be real mistakes          |
| Local engine first          | HTTP bridge to `katago analysis` subprocess | Simplest, strongest, most debuggable path                       |
| Browser engine              | Stretch goal, not Phase A                   | Complexity of TF.js model loading, MCTS reimplementation        |
| LLM for comments            | Deferred (least preferred)                  | Template engine first; LLM only if templates prove insufficient |
| Phase A scope               | Validate + Refute + Difficulty only         | No teaching comments, no technique classification in Phase A    |

---

## Effort Estimates

| Task                       | Effort           | Notes                                      |
| -------------------------- | ---------------- | ------------------------------------------ |
| A.0 (scaffolding + models) | 2-3 hours        | Pydantic models, SGF parser, engine driver |
| A.1 (validate)             | 2-3 hours        | Core logic + tests                         |
| A.2 (refutations)          | 3-4 hours        | Multi-move analysis + PV extraction        |
| A.3 (difficulty)           | 1-2 hours        | Reuses A.1+A.2 data, just scoring          |
| A.4-A.5 (UI)               | 3-4 hours        | HTML + BesoGo integration + JS client      |
| A.6-A.7 (tests + docs)     | 2-3 hours        | Fixture SGFs, README                       |
| **Phase A total**          | **~15-20 hours** |                                            |
| B.1-B.6 (Phase B)          | ~2-3 weeks       | Pattern taxonomy is the hard part          |
| I.1-I.5 (Integration)      | ~1 week          | Adapter + scale testing                    |

---

> **See also:**
>
> - [Research: Browser & Local KataGo](001-research-browser-and-local-katago-for-tsumego.md) — Full feasibility study
> - [Puzzle Quality Strategy](../puzzle-quality-strategy/) — Related quality scoring initiative
> - KataGo Analysis Protocol — github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md
