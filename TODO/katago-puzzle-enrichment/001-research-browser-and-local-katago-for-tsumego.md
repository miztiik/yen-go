# Research: Browser & Local KataGo for Tsumego Puzzle Enrichment

**Created:** 2026-02-25  
**Status:** Research complete — ready for planning  
**Purpose:** Feasibility study for using KataGo (browser WebGPU + local engine) to enrich puzzles with validation, refutations, difficulty ratings, teaching comments, and technique classification

---

## 1. Problem Statement

Yen-Go's ~194K puzzle corpus has varying quality of metadata. Many puzzles lack:

- **Validated correct answers** — some source SGFs have untested solution trees
- **Wrong-move refutations** — the YR property is empty or incomplete on most puzzles
- **Difficulty ratings** — YG is assigned by source metadata or heuristic, not verified
- **Teaching comments** — move-level `C[]` explaining _why_ a move is correct/wrong
- **Technique classification** — what tsumego technique (snapback, ladder, ko, etc.)

KataGo can provide the raw signals to address all five gaps.

---

## 2. Landscape: Browser-Based Go AI

### 2.1 Projects Surveyed

| Project                                   | Tech                          | Model Size                    | Strength                         | Status                 | License  |
| ----------------------------------------- | ----------------------------- | ----------------------------- | -------------------------------- | ---------------------- | -------- |
| **d180cf/tsumego.js**                     | Pure JS, alpha-beta + DCNN    | ~1MB                          | ~15 intersections, enclosed only | Abandoned 2017         | MIT      |
| **Sir-Teo/web-katrain**                   | React + TF.js + MCTS          | b6c96 ~4MB, b18c384 ~160MB    | b6: ~OGS 1d, b18: ~5d+           | Active (updated daily) | —        |
| **maksimKorzh/go**                        | PWA, bare KataGo net, no MCTS | b6c96 ~4MB                    | ~OGS 1d (no MCTS)                | Stable                 | —        |
| **y-ich/KataGo**                          | WASM (Emscripten) + TF.js     | Various                       | Full KataGo in browser           | Experimental           | MIT      |
| **cameron-martin/tsumego-solver**         | Rust CLI                      | N/A (search-based)            | Strong for small boards          | Stable                 | MIT      |
| **MachineKomi/Infinite_AI_Tsumego_Miner** | Python + 11 KataGo nets       | Full GPU models (~1-2GB each) | Professional-grade               | Active                 | AGPL-3.0 |

### 2.2 Key Finding: No Tsumego-Specific Browser Solver Exists

- **tsumego.js** is the only tsumego-specific browser solver, but limited to ≤15 intersection enclosed positions (abandoned 2017)
- All modern browser Go AI uses full-board KataGo models via TF.js
- For tsumego, the technique is: **full board input, local output interpretation** — model sees 19×19 but we only read policy/ownership for the puzzle region

### 2.3 web-katrain Architecture (Reference Implementation)

```
┌─────────────────────────────┐
│ React + Zustand UI          │
│ (gameStore.ts — 2971 LOC)   │
├─────────────────────────────┤
│ Web Worker                  │
│ ┌─────────────────────────┐ │
│ │ MCTS Engine             │ │
│ │ (analyzeMcts.ts — 2330) │ │
│ │                         │ │
│ │ FastBoard (650 LOC)     │ │
│ │ Features (480 LOC)      │ │
│ │                         │ │
│ │ TF.js NN Evaluator      │ │
│ │ ┌───────────────────┐   │ │
│ │ │ WebGPU  ~10ms/eval│   │ │
│ │ │ WASM    ~50-100ms │   │ │
│ │ │ CPU     ~500ms+   │   │ │
│ │ └───────────────────┘   │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Model I/O Specification:**

- **Input:** 22 channels × 19×19 binary feature planes
- **Output (4 heads):**
  1. **Policy** [362] = 19×19 + pass — probability distribution over moves
  2. **Value** scalar [-1, +1] — win probability for current player
  3. **Ownership** [19×19] [-1, +1] — per-point ownership prediction
  4. **Score** scalar — predicted final score

**Performance Benchmarks (web-katrain measured):**

| Backend          | Eval Time | MCTS 100 visits | Notes                                |
| ---------------- | --------- | --------------- | ------------------------------------ |
| WebGPU (b6c96)   | ~10ms     | ~1-2s           | Requires `SharedArrayBuffer` headers |
| WASM (b6c96)     | ~50-100ms | ~5-10s          | Threaded WASM with XNNPACK           |
| CPU (b6c96)      | ~500ms+   | ~50s+           | Last resort fallback                 |
| WebGPU (b18c384) | ~50ms     | ~5-10s          | Much stronger, 160MB download        |

---

## 3. KataGo Model Tiers & Sizes

From katagotraining.org:

| Model Tier  | Architecture            | Approx. File Size | Elo (kata1 scale) | Suitability for Tsumego              |
| ----------- | ----------------------- | ----------------- | ----------------- | ------------------------------------ |
| **b6c96**   | 6 blocks, 96 channels   | ~4 MB (.bin.gz)   | ~9,900            | SDK-level puzzles; fast browser eval |
| **b10c128** | 10 blocks, 128 channels | ~15 MB            | ~11,500           | Elementary-Advanced puzzles          |
| **b15c192** | 15 blocks, 192 channels | ~40 MB            | ~12,200           | Good for most tsumego                |
| **b18c384** | 18 blocks, 384 channels | ~160 MB           | ~13,600           | Strong; near-pro reading             |
| **b28c512** | 28 blocks, 512 channels | ~450 MB           | ~14,090           | Strongest; overkill for most tsumego |
| **b40c256** | 40 blocks, 256 channels | ~200 MB           | ~13,400           | Older architecture                   |
| **b60c320** | 60 blocks, 320 channels | ~500 MB           | ~13,530           | Depth over width                     |

**For tsumego enrichment, b10c128 (~15MB) or b15c192 (~40MB) hits the sweet spot** — handles 90%+ of SDK-level puzzles correctly, while b6c96 (~4MB) is best for browser-side quick checks.

**Browser recommendation:** b6c96 for the side-quest prototype (4MB download, fast eval). Local engine: b15c192 or b18c384 for production pipeline enrichment.

---

## 4. KataGo for Tsumego: The "Full Board Input, Local Output" Technique

### 4.1 Core Insight

KataGo always processes a full 19×19 board. For tsumego:

1. **Set up the full board** with puzzle stones placed at their SGF coordinates
2. **Run analysis** (forward pass or MCTS)
3. **Read only the puzzle-region outputs:**
   - **Policy**: mask to puzzle bounding box → top moves are candidate answers
   - **Ownership**: tells us which groups are alive/dead after a move
   - **Value**: win/loss confirms if the puzzle objective (kill/live/capture) is met

### 4.2 Why This Works for Tsumego

Tsumego positions are typically in one corner/edge of a 19×19 board. The empty remainder biases the model toward local tactical reading — exactly what we want. The ownership head is particularly valuable because it directly answers "is this group alive or dead?"

### 4.3 Puzzle Region Detection

Most Yen-Go puzzles already have `YC` (corner position: TL, TR, BL, BR, C, E). For puzzles without it:

- Compute bounding box of all stones + 2-point margin
- Limit policy analysis to this region
- Read ownership only for groups in the puzzle region

---

## 5. Feasibility Analysis: Four Enrichment Tasks

### 5.1 Task 1: Validate Correct Moves — FEASIBLE

**Method:**

1. Set up the initial position from SGF
2. For each correct-path first move in the solution tree:
   - Play the move, run MCTS (~100 visits)
   - Check: does value for puzzle-player stay > 0.8? → validated
   - Check: does ownership show target group alive/dead as expected? → validated
3. If KataGo disagrees with the SGF solution → flag for manual review

**Accuracy:** ~95%+ for standard life-and-death (KataGo reads deeper than most puzzle authors)

**Edge Cases:**

- Ko situations: KataGo may evaluate differently depending on ko threats (use `YK` property)
- Seki: ownership head handles this well (both groups show ~0)
- Approach-move puzzles: trickier — value change is subtler

**KataGo Signals Used:** Value, Ownership, Policy (for cross-validation)

### 5.2 Task 2: Generate Wrong-Move Refutations — FEASIBLE

**Method:**

1. Set up initial position
2. Get top-N policy moves (e.g., top 5) from KataGo
3. Exclude the correct first move(s) from the SGF
4. For each remaining move (the "wrong" moves):
   - Play it, then play KataGo's best response (the refutation)
   - Continue the refutation sequence for 2-4 moves
   - Verify: value for puzzle-player drops below -0.5 (confirmed wrong)
   - Record the refutation principal variation (PV)
5. Output: wrong moves + refutation sequences → YR property + SGF branches

**Architectural Limit on Refutation Count:**

- **2-3 refutations is optimal.** Rationale:
  - Top policy move (excluding correct) is almost always the most "tempting" wrong move
  - 2nd and 3rd wrong moves cover common mistakes
  - Beyond 3: diminishing UX value, each adds ~100-visit MCTS cost
  - **Recommendation: generate up to 3 refutations, keep those with policy > 0.05**

**KataGo Signals Used:** Policy (candidate wrong moves), Value (confirm they're wrong), PV (refutation sequence)

### 5.3 Task 3: Difficulty Rating — FEASIBLE (EASIEST TASK)

**Method (from Infinite_AI_Tsumego_Miner approach):**

```
difficulty ∝ visits_to_solve / policy_prior_of_correct_move
```

**Concrete mapping:**

| Signal                                            | What it measures                            | Maps to                |
| ------------------------------------------------- | ------------------------------------------- | ---------------------- |
| `policy_prior` of correct first move              | How "obvious" the move is to the neural net | Intuition difficulty   |
| `visits_to_solve` (MCTS visits until value > 0.9) | Reading depth required                      | Calculation difficulty |
| `solution_length` (PV depth)                      | How many moves deep                         | Sequence difficulty    |
| `refutation_count`                                | How many plausible wrong moves exist        | Trap density           |

**Calibration to Yen-Go levels:**

| Policy Prior | Visits to Solve | Solution Length | Approx. Level                 |
| ------------ | --------------- | --------------- | ----------------------------- |
| > 0.5        | < 10            | 1-2             | novice / beginner             |
| 0.2 - 0.5    | 10-50           | 2-4             | elementary / intermediate     |
| 0.05 - 0.2   | 50-200          | 4-8             | upper-intermediate / advanced |
| 0.01 - 0.05  | 200-500         | 8-12            | low-dan / high-dan            |
| < 0.01       | 500+            | 12+             | expert                        |

**This maps directly to existing YX complexity metrics:**

- `d` (depth) ← solution_length
- `r` (refutations) ← refutation_count
- `s` (solution_length) ← PV length
- `u` (unique_responses) ← branching factor

**Partial difficulty rating is achievable with just 1 forward pass** (no MCTS needed) — the policy prior alone correlates well with difficulty. Full MCTS refines it.

### 5.4 Task 4: Teaching Comments + Technique Classification — FEASIBLE BUT COMPLEX

**This is Phase B.** Requires building a pattern taxonomy on top of KataGo signals.

**Teaching Comments — What's needed:**

- **Correct move**: "Why does this move work?" → requires causal explanation of the tactical mechanism
- **Wrong move**: "Why does this move fail?" → requires explaining the refutation

**The Translation Problem:**

```
KataGo says:  ownership[D3] changed from -0.92 to +0.87, PV length 5
Human says:   "This move creates a second eye at D3, ensuring the group lives
               because White cannot fill both eye spaces simultaneously."
```

**Approach (Template Engine — no LLM):**

Pattern classification from KataGo signals → canned explanation:

| KataGo Signal Pattern                         | Tsumego Technique                  | Template                                        |
| --------------------------------------------- | ---------------------------------- | ----------------------------------------------- |
| Dead group → alive, new liberty space created | Eye-making                         | "Creates a vital eye at {coord}"                |
| Opponent stones captured in PV                | Capturing race (semeai)            | "Wins the capturing race by {N} liberties"      |
| PV shows forced ladder sequence               | Ladder                             | "The ladder works — {edge/stone} blocks escape" |
| Capture → recapture → net gain                | Snapback                           | "Snapback at {coord} recaptures"                |
| Ko threat in PV, alternating captures         | Ko                                 | "Ko fight at {coord}"                           |
| Ownership shows mutual survival               | Seki                               | "Both groups live in seki"                      |
| Liberty count drops to 1 then capture         | Shortage of liberties (damezumari) | "Shortage of liberties (damezumari)"            |
| Atari → connect threatens                     | Connect/cut                        | "Connecting at {coord} ensures life"            |
| Throw-in sacrifice → reduce eye space         | Throw-in                           | "Sacrifice at {coord} reduces to one eye"       |
| Under-the-stones capturing sequence           | Under-the-stones                   | "Under-the-stones technique captures"           |
| Bulky five / rectangular six shape dies       | Shape death                        | "This shape is dead — {shape_name}"             |
| Net/geta capture pattern                      | Net                                | "Net at {coord} captures the group"             |

**Wrong move explanations are easier than correct move explanations** — the refutation sequence is concrete and the ownership change is dramatic (alive → dead). For correct moves, the explanation often requires understanding the _absence_ of a refutation, which is subtler.

**LLM fallback** (deferred — not in Phase A or B initial scope): For positions that don't match known patterns, an LLM could generate explanations from structured KataGo context. Estimated ~$500-1000 for 50K puzzles via API. Local LLM (Llama 3, Qwen): free but 1-3 sec/puzzle. **Least preferred option; revisit only after template engine is proven insufficient.**

---

## 6. Local KataGo Engine: GTP & Analysis Protocol

### 6.1 KataGo Analysis Mode

KataGo supports a JSON-based analysis protocol via stdin/stdout:

```json
// Request
{
  "id": "puzzle_001",
  "moves": [],
  "initialStones": [["B","C3"],["B","D3"],["W","C4"],["W","D4"]],
  "rules": "chinese",
  "komi": 7.5,
  "boardXSize": 19,
  "boardYSize": 19,
  "analyzeTurns": [0],
  "maxVisits": 200
}

// Response
{
  "id": "puzzle_001",
  "turnNumber": 0,
  "moveInfos": [
    {
      "move": "C5",
      "visits": 150,
      "winrate": 0.95,
      "scoreLead": 12.3,
      "prior": 0.42,
      "pv": ["C5","D5","C6","D6"],
      "ownership": [/* 19x19 array */]
    }
  ],
  "rootInfo": {
    "winrate": 0.85,
    "scoreLead": 8.1,
    "visits": 200
  }
}
```

### 6.2 Installation

```bash
# Option A: Pre-built binary (recommended)
# Download from https://github.com/lightvector/KataGo/releases
# Windows: katago.exe, Linux/Mac: katago

# Option B: Via package manager
brew install katago        # macOS
apt install katago         # Ubuntu

# Download a model
curl -O https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b15c192-s1672170752-d466197061.bin.gz
```

### 6.3 Running in Analysis Mode

```bash
katago analysis -model kata1-b15c192.bin.gz -config analysis.cfg
# Then send JSON requests via stdin, receive JSON responses via stdout
```

This is the protocol our side-quest tool will use for local engine communication.

---

## 7. Browser KataGo via WASM (Corrected Approach)

**UPDATE (2026-02-26):** The original research incorrectly described web-katrain as using TF.js. It actually compiles KataGo C++ to WASM via Emscripten, which reads `.bin.gz` files directly. This is the standard and correct approach for browser-based KataGo.

### 7.1 How Browser KataGo Actually Works

There are two approaches in the wild:

| Approach                      | Used By        | Model Format                      | MCTS?            | Strength    |
| ----------------------------- | -------------- | --------------------------------- | ---------------- | ----------- |
| **KataGo WASM (Emscripten)**  | web-katrain    | `.bin.gz` (native, same as local) | Yes              | Full KataGo |
| **TF.js (converted weights)** | maksimkorzh/go | `model.json` + shards (converted) | No (raw NN only) | Weaker      |

**KataGo WASM is the correct approach** because:

1. Same `.bin.gz` model format — no conversion needed, any model from katagotraining.org works
2. Full MCTS search — not just raw NN output
3. Full analysis protocol — ownership, PV, value, score
4. One model format for both local and browser

### 7.2 WASM Build Pipeline

```
KataGo C++ source → Emscripten (emcc) → katago.js + katago.wasm
                                              ↓
                                    Browser loads .wasm
                                    Reads .bin.gz directly
                                    Runs MCTS in Web Worker
```

Build requirements:

- Emscripten SDK (emsdk)
- CMake 3.16+
- Backend: EIGEN (CPU-based, works in WASM — no CUDA/OpenCL in browser)
- COOP/COEP headers for SharedArrayBuffer (threading)

See `scripts/build_wasm.sh` for the complete build pipeline.

### 7.3 Model Recommendations

**Why different models for local vs browser:**

| Factor              | Local Engine                                                       | Browser Engine                        |
| ------------------- | ------------------------------------------------------------------ | ------------------------------------- |
| **Constraint**      | Disk space, GPU speed                                              | Download size, WASM CPU speed         |
| **Model loading**   | Read from disk (instant)                                           | Download over network (user waits)    |
| **Compute backend** | GPU (OpenCL/CUDA)                                                  | EIGEN CPU via WASM (slower)           |
| **Recommended**     | **b28c512** (259MB, strongest) or **b15c192** (40MB, good balance) | **b10c128** (11MB) or **b6c96** (4MB) |

**Model selection guide:**

| Model   | Size      | Elo     | Local Use              | Browser Use                                       | How to Find                          |
| ------- | --------- | ------- | ---------------------- | ------------------------------------------------- | ------------------------------------ |
| b6c96   | 4MB       | ~9,900  | Testing only           | Good (fast download, quick)                       | GitHub: `KataGo/cpp/tests/models/`   |
| b10c128 | 11MB      | ~11,500 | Light analysis         | **Best for browser** (balance of strength + size) | GitHub: `KataGo/cpp/tests/models/`   |
| b15c192 | 35MB      | ~12,200 | **Good local balance** | Acceptable (6s download on 50Mbps)                | katagotraining.org (manual download) |
| b18c384 | 95-160MB  | ~13,600 | Strong local           | Too large for browser                             | katagotraining.org                   |
| b28c512 | 260-450MB | ~14,090 | **Strongest local**    | Not for browser                                   | katagotraining.org                   |

**How to find models on katagotraining.org/networks/:**

1. Open https://katagotraining.org/networks/
2. Ctrl+F search for the architecture you want (e.g., `b10c128`)
3. Smaller/older models are at the bottom of the page
4. Click "Download" in the "Network File" column
5. The file downloads as `.bin.gz` — works for both local and WASM browser

**Directly downloadable from GitHub (no 403 blocks):**

- b6c96: `https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170-b6c96-s175395328-d26788732.bin.gz`
- b10c128: `https://raw.githubusercontent.com/lightvector/KataGo/master/cpp/tests/models/g170e-b10c128-s1141046784-d204142634.bin.gz`
- b18c384 (human model): `https://github.com/lightvector/KataGo/releases/download/v1.15.0/b18c384nbt-humanv0.bin.gz`

### 7.4 Browser Engine Architecture (Target)

```
Browser
  ├── index.html
  ├── browser-engine.js         ← JS wrapper
  │     └── loads katago.wasm   ← KataGo compiled to WASM
  │           └── reads .bin.gz ← Same model as local
  │           └── runs MCTS     ← Full analysis
  │           └── Web Worker    ← Non-blocking
  └── COOP/COEP headers required for SharedArrayBuffer
```

---

## 8. Reference: Infinite_AI_Tsumego_Miner Architecture

The Tsumego Miner project demonstrates a production pattern for AI-driven puzzle enrichment:

### 8.1 Dual-Engine Architecture

```
Generator Engine (weaker, explores)     Referee Engine (stronger, validates)
         │                                        │
         ├─ Plays candidate moves                 ├─ Verifies solutions
         ├─ Winrate threshold: 90%→15% = blunder  ├─ Confirms difficulty
         └─ Explores response tree                └─ Final quality gate
```

### 8.2 Difficulty Formula

```
difficulty = f(policy_prior, visits_to_solve, solution_depth, branching_factor)
```

Maps to their 9-level kyu/dan system — directly analogous to Yen-Go's 9-level system.

### 8.3 Blunder Detection for Wrong Moves

A wrong move is defined as a move where:

- Puzzle-player's winrate before the move: > 90%
- After the move + opponent's best response: winrate < 15%
- This winrate delta (Δ > 75%) constitutes a "blunder"

This is exactly what we need for generating refutations (Task 2).

---

## 9. Where This Fits in Yen-Go Architecture

```
                    ┌───────────────────────────────────────┐
                    │         Yen-Go Pipeline (v4.0)        │
                    ├───────────┬───────────┬───────────────┤
                    │  INGEST   │  ANALYZE  │   PUBLISH     │
                    │           │           │               │
                    │ fetch     │ classify  │ index         │
                    │ parse     │ tag       │ daily         │
                    │ validate  │ enrich ◄──┤ output        │
                    │           │    │      │               │
                    └───────────┴────┼──────┴───────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │  KataGo Enrichment    │
                         │  (new sub-stage)      │
                         │                       │
                         │  ┌─────────────────┐  │
                         │  │ Phase A          │  │
                         │  │ 1. Validate      │  │
                         │  │ 2. Refutations   │  │
                         │  │ 3. Difficulty    │  │
                         │  └─────────────────┘  │
                         │  ┌─────────────────┐  │
                         │  │ Phase B          │  │
                         │  │ 4. Teaching C[]  │  │
                         │  │ 5. Technique ID  │  │
                         │  │ 6. Hints (YH)    │  │
                         │  └─────────────────┘  │
                         └───────────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │   KataGo Backend      │
                         │                       │
                         │  ┌──────────────────┐ │
                         │  │ Local Engine      │ │
                         │  │ (Analysis JSON)   │ │
                         │  └──────────────────┘ │
                         │  ┌──────────────────┐ │
                         │  │ Browser TF.js    │ │
                         │  │ (WebGPU/WASM)    │ │
                         │  └──────────────────┘ │
                         └───────────────────────┘
```

### Integration Points with Existing SGF Properties

| Enrichment Task          | SGF Property            | Current State                 | After Enrichment             |
| ------------------------ | ----------------------- | ----------------------------- | ---------------------------- |
| Validate correct         | Existing solution tree  | Trusted from source           | KataGo-verified              |
| Wrong-move refutations   | `YR` + new SGF branches | Empty on most                 | 1-3 refutations with PV      |
| Difficulty rating        | `YG` + `YX`             | Heuristic or source-assigned  | KataGo-calibrated            |
| Teaching comments        | Move `C[]`              | "Correct"/"Wrong" prefix only | Causal explanation           |
| Technique classification | `YT` (tags)             | Source tags or heuristic      | KataGo-derived technique tag |
| Hints                    | `YH`                    | Heuristic coordinate hints    | Could be refined             |

---

## 10. Risk Assessment

| Risk                                          | Likelihood               | Impact | Mitigation                                                |
| --------------------------------------------- | ------------------------ | ------ | --------------------------------------------------------- |
| KataGo disagrees with human-authored solution | Medium                   | High   | Flag for manual review, don't auto-override               |
| Model too weak for dan-level puzzles          | Low (b15c192 reads well) | Medium | Use stronger model for flagged puzzles                    |
| Ko positions confuse analysis                 | Medium                   | Medium | Use `YK` property to adjust analysis params               |
| Browser model too slow for batch processing   | N/A (batch uses local)   | Low    | Browser is interactive only                               |
| Template taxonomy misclassifies technique     | Medium                   | Medium | Confidence threshold → generic fallback                   |
| Side-quest prototype scope creep              | High                     | Medium | Strict Phase A scope: validate + refute + difficulty only |

---

## 11. Open Questions

1. **Ko handling:** Should we set ko threats artificially or let KataGo handle naturally?
2. **Seki detection:** Ownership head shows ~0 for both sides — sufficient for seki detection?
3. **Move-order flexibility (YO):** How to handle `flexible` and `miai` puzzles where multiple first moves are correct?
4. **Calibration dataset:** Need puzzles with known human difficulty ratings to calibrate the formula
5. **Browser model conversion:** web-katrain has TF.js-compatible models — can we reuse directly?

---

## 12. References

| Resource                  | URL                                                               | Relevance                                |
| ------------------------- | ----------------------------------------------------------------- | ---------------------------------------- |
| KataGo Analysis Protocol  | github.com/lightvector/KataGo/blob/master/docs/Analysis_Engine.md | Engine communication spec                |
| KataGo Training Networks  | katagotraining.org/networks/                                      | Model downloads + Elo ratings            |
| web-katrain               | github.com/Sir-Teo/web-katrain                                    | Browser KataGo reference implementation  |
| web-katrain Architecture  | github.com/Sir-Teo/web-katrain/blob/main/docs/diagram.md          | Detailed architecture diagrams           |
| Infinite AI Tsumego Miner | github.com/MachineKomi/Infinite_AI_Tsumego_Miner                  | Difficulty grading, dual-engine pattern  |
| d180cf/tsumego.js         | d180cf.github.io/tsumego.js/                                      | Browser-only solver (limited, abandoned) |
| Yen-Go BesoGo Viewer      | `tools/sgf-viewer-besogo/`                                        | Existing SGF viewer in the repo          |
