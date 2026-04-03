# Plan: Browser Engine via TF.js + MCTS (Option B)

**Created:** 2026-02-26  
**Last Updated:** 2026-02-27  
**Status:** Plan — updated with expert reviews + architecture clarification  
**Supersedes:** Earlier plan that proposed compiling KataGo NN to custom WASM  
**Based on:** Failed WASM stdin/stdout approach, web-katrain source analysis, OGS goban internals, BTP/tsumego-hero audit  
**Reviewed by:** Principal Systems Architect, Cho Chikun 1P Professional Go Player  
**Review findings:** [005-learnings-and-review-browser-engine.md](005-learnings-and-review-browser-engine.md)  
**Cross-references:** [Puzzle Quality Scorer plan](../puzzle-quality-scorer/implementation-plan.md) (symbolic tactical analysis — complementary)

---

## Landscape: Beaten Path or Unicorn?

This is NOT a unicorn. Browser-based Go AI is a narrow but real path with two proven tiers.

### Four Tiers of Browser Go AI (Updated)

| Tier | What it does | Size | Technique | Who ships it |
|------|-------------|------|-----------|-------------|
| **Tier 0: Heuristic JS** | Liberty/influence-based territory estimation | 0 KB (pure JS) | Flood fill, liberty counting, capture detection | **blacktoplay.com** (`estimator.js`, ~700 LOC) |
| **Tier 0.5: Policy-Only NN** | Single NN forward pass → policy priors + value | 3-4 MB model + TF.js | TF.js inference, no MCTS | **maksimKorzh/go**, concept from **KaTrain** `AI_POLICY` mode |
| **Tier 1: Monte Carlo Ownership** | Random playouts → ownership heatmap + score | 29 KB WASM | C Monte Carlo via Emscripten | **OGS** via `OGSScoreEstimator.wasm` in `goban` npm (already in our deps) |
| **Tier 2: Neural Net + MCTS** | Full KataGo-strength move analysis | 4-11 MB model + TF.js | TensorFlow.js (WebGPU/WASM/CPU) + TypeScript MCTS | **web-katrain** (sir-teo.github.io/web-katrain) |

**Tier 0** answers: "Rough territory estimation" (no model, <1ms, ~60% accurate).  
**Tier 0.5** answers: "How obvious is the correct move?" (3-4MB model, 50-100ms, difficulty estimation).  
**Tier 1** answers: "Who controls this area?" (territory ownership, ~100KB).  
**Tier 2** answers: "What's the best move? Is this puzzle correct?" (full analysis, ~6MB).

**Key insight from reviews:** Tier 0.5 (policy-only) delivers immediate value for difficulty estimation with zero MCTS complexity. KaTrain's `AI_POLICY` and `AI_RANK` modes prove that policy priors alone correlate strongly with difficulty. This can be our first deliverable before the full MCTS engine.

### Public Go Sites — What They Actually Use

| Site | Browser AI? | How | WASM? |
|------|------------|-----|-------|
| **OGS (online-go.com)** | Tier 1 local + server KataGo | `OGSScoreEstimator.wasm` (29KB) for quick ownership; server KataGo for "AI Review" | **Yes** — Monte Carlo only |
| **web-katrain** | Tier 2 browser-only | TF.js auto-cascade: WebGPU (~10ms) → WASM/XNNPACK (~50-100ms) → CPU (~500ms) | **TF.js manages its own WASM** — no custom Emscripten |
| **blacktoplay.com** | Tier 0 heuristic | Pure JS `Estimator` class (~700 LOC): liberty counting, capture detection, influence propagation, closed-group analysis. No NN. | **No** — pure algorithmic JS |
| **tsumego-hero** | Unknown | Site currently under maintenance. No confirmed browser WASM. | **Unknown** |
| **goproblems.com** | Likely server-side | No confirmed browser WASM or scoring | **No** |
| **maksimKorzh/go** | TF.js NN eval, no MCTS | Raw policy output only (weaker without search) | No custom WASM |

### What Our Dependencies Already Have

`goban` v8.3.147 (already in `frontend/package.json`) ships three estimator backends:

| Backend | Technique | Status in Yen-Go |
|---------|-----------|-----------------|
| `wasm_estimator` | `OGSScoreEstimator.wasm` + Emscripten `cwrap("estimate")` | Available but unused |
| `voronoi_estimator` | Manhattan-distance flood fill (pure JS) | Available but unused |
| `remote_estimator` | Server-side KataGo (OGS servers) | N/A (no server) |

API: `init_wasm_ownership_estimator()` → `wasm_estimate_ownership(board[][], color, trials, tolerance)`.  
See `TODO/134-score-estimation-wasm/` for the Feature 134 plan (separate effort for the main frontend).

### OGS vs BTP Score Estimator Comparison

| Dimension | **OGS WASM** (`OGSScoreEstimator.wasm`) | **BTP Heuristic** (`estimator.js`) |
|-----------|----------------------------------------|-----------------------------------|
| **Technique** | Monte Carlo random playouts (C compiled to WASM) | Liberty counting + influence propagation + closed-group detection (pure JS) |
| **Size** | 29 KB WASM binary | ~700 LOC JS, 0 KB model |
| **Accuracy** | ~70% for territory, moderate for life/death | ~60% for territory, good for simple captures |
| **Latency** | <500ms (1000 trials) | <1ms |
| **Dead stone detection** | Ownership threshold → `getProbablyDead()` | `is_group_closed()` — flood fill + stone count heuristic |
| **Territory estimation** | Random playout consensus | Influence propagation from stones (±1 to ±4 radiating) |
| **Edge/corner handling** | Implicit in playouts | Explicit 1st/2nd line heuristics |
| **Group life/death** | Statistical (playout survival rate) | Structural (`is_group_closed`: <7 stones, fully enclosed) |
| **Interactive mode** | Board state → ownership map | Board state → ownership map + `toggle_group_status()` |
| **Viewport support** | Full board only | Optional `viewport` parameter for sub-region analysis |
| **Source** | Part of `goban` | blacktoplay.com |

**Verdict:**
- **OGS WASM is better for general territory scoring** — Monte Carlo is more reliable across positions
- **BTP is better for quick structural life/death checks** — `is_group_closed()` is deterministic and instant
- **For the enrichment lab**, neither replaces KataGo. But BTP's `is_group_closed()` is worth porting to `fast-board.js` Phase 2 as a pre-filter
- **For Feature 134** (main frontend), OGS WASM is the right choice — already in our deps, proven API

---

## Architecture: Browser Engine vs Local Engine (Clarification)

**The browser engine and local engine are completely independent systems.** They serve different use cases and do not counterbalance each other.

### Browser Engine (this plan — `tools/puzzle-enrichment-lab/js/engine/`)
- **Purpose:** Lightweight, quick-check tool for interactive puzzle analysis in the lab UI
- **Model:** b6c96 (3.7 MB) — fast download, sufficient for SDK-level puzzles
- **Capability:** Tier 0.5 (policy-only, instant) + Tier 2 (MCTS, 1-10s)
- **Use case:** A developer opens a puzzle in the lab, clicks "Analyze" → instant difficulty estimate + quick validation
- **No batch processing** — one puzzle at a time, interactive

### Local Engine (existing — `tools/puzzle-enrichment-lab/katago/katago.exe`)
- **Purpose:** Production workhorse for batch enrichment of 194K+ puzzles
- **Model options:** b15c192 (35 MB, good balance) or b28c512 (260 MB, strongest)
- **Capability:** Full KataGo analysis protocol (JSON stdin/stdout)
- **Use case:** Pipeline runs → enrich all puzzles with validation, refutations, difficulty
- **Batch processing** — thousands of puzzles per run

### Dual-Engine Referee System (Local Only — Optional Enhancement)

Inspired by Infinite_AI_Tsumego_Miner's Generator/Referee pattern:

```
┌────────────────── Local Dual-Engine Setup ──────────────────┐
│                                                              │
│  Quick Engine (b10c128, 100 visits, ~50ms/puzzle)            │
│  └─ Generates initial analysis: policy, value, top moves     │
│                         ↓                                    │
│  Referee Engine (b28c512, 400 visits, ~500ms/puzzle)         │
│  └─ Validates: confirms/rejects Quick Engine findings        │
│  └─ Resolves disagreements with deeper reading               │
│  └─ Only runs on puzzles where Quick Engine is uncertain     │
│                                                              │
│  Result: 80% of puzzles processed at Quick speed,            │
│          20% escalated to Referee for deeper analysis         │
└──────────────────────────────────────────────────────────────┘
```

**This is NOT browser vs local.** It is **two local KataGo instances** with different models:
- **Quick Engine** = weaker model, fewer visits, fast (~50ms)
- **Referee Engine** = strongest model, more visits, slower (~500ms) — only invoked when Quick Engine is uncertain (value between 0.3-0.7, policy prior < 0.05 for all candidates)

**When to escalate to Referee:**
- Quick Engine value is ambiguous (0.3 < value < 0.7)
- Quick Engine's top move differs from SGF's correct move
- Policy prior of correct move < 0.05 (potentially hard puzzle)
- Ko or seki suspected (ownership ≈ 0 for contested groups)

**This is optional.** The baseline implementation uses a single local engine. The dual-engine pattern is an optimization for batch runs to save ~60% of compute while maintaining quality.---

## Our Failed Approach (Option A) — Lessons Learned

We compiled the **entire** KataGo C++ codebase to WASM via Emscripten:

```
KataGo C++ (ALL 100+ source files) → Emscripten → katago.wasm (47 MB) + katago.js (139 KB)
  → callMain(['analysis', ...])
  → emulated stdin (JSON) → emulated stdout (JSON)
  → FAILED: stdin blocks, no async, 30s timeout
```

**Why it failed:**
1. KataGo's `main()` blocks on stdin — incompatible with browser event loop
2. 47 MB WASM + 11 MB model = ~60MB, unacceptable load time
3. stdin/stdout emulation via Emscripten is not designed for interactive CLI protocols
4. 4 CMakeLists.txt patches needed; fragile and unmaintainable

**Files to remove (cleanup):**
- `.emsdk/` — Entire Emscripten SDK (~1.5 GB)
- `.wasm-build/` — KataGo source clone + build artifacts (~900 MB)
- `vendor/katago-wasm/` — katago.js (139 KB) + katago.wasm (47 MB)
- `js/browser-engine.js` — 280-line broken stdin/stdout emulation
- `scripts/build_wasm.sh` — 156-line Emscripten build script
- Update `index.html` to remove `<script src="js/browser-engine.js">` tag
- Update `js/app.js` to remove `BrowserEngine` references (temporarily; re-add when TF.js engine works)

---

## Option B: What web-katrain Actually Does

**Critical correction from earlier plan:** web-katrain does **NOT** compile KataGo to custom WASM. They use **TensorFlow.js** for neural network inference and **reimplement MCTS, board logic, and feature extraction in TypeScript**.

```
Architecture:
┌──────────────────────── Web Worker ─────────────────────────┐
│                                                              │
│  Board State → features.ts (22 ch) → TF.js NN eval          │
│                                          ↓                   │
│                         policy + value + ownership           │
│                                          ↓                   │
│                       analyzeMcts.ts (MCTS search)           │
│                                ↓                             │
│                  AnalysisResult (top moves, winrate, PV)     │
│                                                              │
└──────────────── postMessage back to Main Thread ─────────────┘
```

### TF.js Backend Auto-Cascade (no custom WASM compilation needed)

```
① WebGPU  → GPU compute shaders      (~10ms/eval)   ← Chrome 113+
    ↓ fallback
② WASM    → XNNPACK + threads        (~50-100ms/eval) ← needs COOP/COEP headers
    ↓ fallback
③ CPU     → pure JavaScript           (~500ms+/eval)  ← always works
```

TF.js handles all backend selection automatically. The "WASM" is TF.js's own WASM backend (XNNPACK), NOT a custom Emscripten build. We never compile anything ourselves.

### web-katrain Engine Files (reference, not imported)

From `src/engine/katago/`:

| File | LOC | Purpose | Port? |
|------|-----|---------|-------|
| `analyzeMcts.ts` | ~2330 | MCTS: selection, expansion, backprop, UCB1+PUCT | **Yes — core** |
| `fastBoard.ts` | ~650 | Board logic: liberties, captures, ko, Zobrist | **Yes — core** |
| `features.ts` | ~480 | 22-channel input tensor from board state | **Yes — core** |
| `loadModelV8.ts` | ~200 | Binary .bin.gz model parser (pako decompress) | **Yes — core** |
| `modelV8.ts` | ~300 | NN architecture (TF.js computation graph) | **Yes — core** |
| `symmetry.ts` | ~100 | Board rotation/reflection | Nice-to-have |
| `ladderDetector.ts` | ~150 | Ladder reading heuristic | Nice-to-have |
| `types.ts` | ~50 | Type definitions | **Yes** |
| `worker.ts` | ~100 | Web Worker entry point | **Yes** |
| `client.ts` | ~100 | Main thread ↔ Worker messaging | **Yes** |
| `gameStore.ts` | ~2970 | Zustand state management | **No — skip** |
| `GoBoard.tsx` | ~1530 | React canvas rendering | **No — we use BesoGo** |
| `aiStrategies.ts` | varies | AI play modes (8 strategies) | **No — not needed for tsumego** |

**Core engine to rewrite: ~4,210 LOC → ~3,000 LOC JavaScript** (simpler without TypeScript generics and React integration).

### Why Rewrite Instead of Import

1. **Quality concerns** — web-katrain is Copilot/Jules-generated, 8 stars, created Jan 2026, quality unknown
2. **Copilot/Jules-generated** — 8 stars, created Jan 2026, quality unknown
3. **React+Zustand coupling** — extracting engine means untangling a monolithic store
4. **We only need tsumego** — not full-game analysis with 8 AI strategies, game reports, etc.
5. **Simplification** — we can optimize for small board regions, add puzzle-specific heuristics

---

## Implementation Plan

### Cleanup Phase (prerequisite): Remove Failed Option A Artifacts

**Goal:** Delete all Emscripten/custom WASM code and the broken browser-engine.js.

**Delete:**
- `tools/puzzle-enrichment-lab/.emsdk/` (~1.5 GB Emscripten SDK)
- `tools/puzzle-enrichment-lab/.wasm-build/` (~900 MB KataGo source + build)
- `tools/puzzle-enrichment-lab/vendor/katago-wasm/` (47 MB katago.wasm + katago.js)
- `tools/puzzle-enrichment-lab/js/browser-engine.js` (280 lines, broken)
- `tools/puzzle-enrichment-lab/scripts/build_wasm.sh` (156 lines)

**Modify:**
- `index.html` — remove `<script src="js/browser-engine.js"></script>`
- `js/app.js` — stub out browser engine functions (remove `BrowserEngine` calls)
- `bridge.py` — remove WASM static file mounting, keep COOP/COEP headers (TF.js WASM backend still needs them)

**Keep:**
- `katago/katago.exe` + `katago/tsumego_analysis.cfg` — local engine (working)
- `models-data/` — neural network models (used by both local and future browser engine)
- `vendor/besogo/` — BesoGo viewer (working)
- `bridge.py` — FastAPI bridge for local engine (working)
- `js/katago-client.js` — HTTP client for local bridge (working)
- `js/app.js` — main UI controller (working, will be cleaned up)
- All Python code (`analyzers/`, `engine/`, `models/`, `tests/`) — working

### Phase 0: TF.js Infrastructure

**Goal:** Add TensorFlow.js, set up Web Worker scaffolding, verify backend detection.

**Actions:**
- Add `@tensorflow/tfjs` via CDN `<script>` tags in `index.html` (no npm for this tool)
- Create Web Worker shell with `postMessage` interface
- Verify TF.js backend auto-detection (WebGPU / WASM / CPU) on user's hardware (Intel Iris Xe)
- COOP/COEP headers already configured in `bridge.py`

**Dependencies:** None (works standalone)

### Phase 0.5: Tsumego Frame (NEW — Critical Path)

**Goal:** Port KaTrain's `tsumego_frame.py` to JavaScript so KataGo receives a properly prepared full board.

**Why this is critical (from expert reviews):**
- Without a tsumego frame, an isolated puzzle position on an empty 19×19 board produces garbage NN output
- KataGo's policy spreads across the entire empty board instead of focusing on the puzzle region
- Ownership head shows everything as "dame" because there are no surrounding stones
- Komi bias makes KataGo think one side is already winning

**Port from:** KaTrain `katrain/core/tsumego_frame.py` (~176 LOC Python)

**Algorithm:**
1. Detect puzzle region from stone positions (corner/edge/center) — maps to `YC` property
2. Compute bounding box with margin
3. Fill outside with balanced offense/defense stones:
   - Attacker stones fill most of the outside
   - Defender stones fill enough territory to balance the score
   - Empty intersections every other point for natural appearance
4. Add ko threats (attack + defense patterns) if position may involve ko
5. Normalize orientation (flip/rotate to standard position for consistent NN input)

**What KaTrain's tsumego frame solves that we need:**
- `guess_black_to_attack()` — determines which color is attacking from stone positions
- `put_border()` / `put_outside()` — fills the board outside the puzzle region
- `put_ko_threat()` — adds ko threats using fixed patterns (offense and defense)
- `snap()` — snaps puzzle boundary to board edge if within 2 points

**Corner concerns (from Cho Chikun 1P review):**
- Corner positions (TL/TR/BL/BR) work best with KataGo — natural boundaries
- Edge positions need wider frame extension
- Center positions need full surrounding — hardest to frame correctly
- Frame should look *unnatural* to prevent KataGo from treating it as a real game opening

**Files:**
```
js/engine/tsumego-frame.js   # Board preparation for NN input
```

**Dependencies:** None (pure logic, no TF.js needed)

### Phase 1: Model Loader

**Goal:** Load KataGo `.bin.gz` model, parse binary format, build TF.js computation graph.

**Rewrite from:** `loadModelV8.ts` + `modelV8.ts` (~500 LOC)

**Details:**
- KataGo .bin.gz format: gzip-compressed binary, header + conv layers + residual blocks + policy/value/ownership heads
- Use `pako` for decompression (CDN include)
- Build TF.js computation graph from parsed weights
- Test: load b6c96 (3.7MB), run dummy inference, verify output shape (362 policy + 1 value + 361 ownership)

**Files:**
```
js/engine/model-loader.js    # Parse .bin.gz → TF.js model
```

### Phase 2: Board Logic

**Goal:** Fast board state management for MCTS simulation.

**Rewrite from:** `fastBoard.ts` (~650 LOC)

**Details:**
- Place stone, compute captures, detect ko
- Zobrist hashing for position deduplication in MCTS tree
- Liberty counting via flood fill
- Undo/redo for MCTS simulation rollback
- **NEW: `isGroupClosed()` heuristic** — adapted from BTP `estimator.js`. Detects if a group with <7 stones is fully enclosed by opponent/territory. Provides a non-NN life/death check for simple positions (instant, no model needed). Useful as:
  - Quick pre-filter before NN analysis
  - Validation of NN results (if NN says alive but group is clearly enclosed → flag)
  - Fallback when NN is unavailable

**Files:**
```
js/engine/fast-board.js      # Board state + Zobrist + captures + isGroupClosed()
```

### Phase 3: Feature Extraction

**Goal:** Convert board state to 22-channel input tensor for KataGo NN.

**Rewrite from:** `features.ts` (~480 LOC)

**22 input channels:**
| Channels | Description |
|----------|-------------|
| 0-1 | Current/opponent stones |
| 2-3 | Second player stones |
| 4-8 | Turns since stone played (1,2,3,4,5+) |
| 9-12 | Liberties (1,2,3,4+) |
| 13-14 | Ladder features |
| 15-16 | Pass-alive territory |
| 17-18 | Ko features |
| 19-21 | Board edge, rules |

**Files:**
```
js/engine/features.js        # Board → Float32Array (22 × boardSize²)
```

**NEW: Policy-Only Mode (Tier 0.5)**

After Phase 3, we can deliver a "policy-only" analysis mode that skips MCTS entirely:
1. Set up board with tsumego frame (Phase 0.5)
2. Extract features (Phase 3)
3. Run single NN forward pass (~50-100ms on WASM)
4. Read policy prior of the correct first move → instant difficulty estimate
5. Read value head → quick "is this position winning/losing" check
6. Read ownership head → quick "which groups are alive/dead" check

**Difficulty calibration formula (from KaTrain + expert reviews):**
```
difficulty_score = w1 * (1 - policy_prior)           # "how surprising is the correct move"
                 + w2 * log(visits_to_solve / 50)     # "how deep to read" (Tier 2 only)
                 + w3 * trap_density                   # "how tempting are wrong moves" (Tier 2 only)
```

Where `trap_density = sum(pointsLost * prior) / sum(prior)` (adapted from KaTrain's `game_report()` complexity formula).

**Miai puzzle correction (from Cho Chikun 1P review):**
When `YO=miai` or `YO=flexible`, *sum* the policy priors of ALL correct first moves before computing difficulty. Otherwise miai puzzles are artificially rated as harder because the prior is split between equivalent moves.

**This is a valuable checkpoint** — delivers difficulty estimation before the complex MCTS work in Phase 4.

### Phase 4: MCTS Search

**Goal:** Tree search using NN evaluations. Selection → Expansion → NN Eval → Backpropagation.

**Rewrite from:** `analyzeMcts.ts` (~2330 LOC)

**Core algorithm:**
```
UCB = Q + c_puct × P × √(N_parent) / (1 + N)
```
- Tree node: move, visits, Q-value, prior P, children
- Selection: descend tree by highest UCB
- Expansion: create children from top-k policy moves
- Backpropagation: update Q-values up the tree
- Result: top moves, winrate, ownership, principal variation

**Tsumego optimizations (our custom additions):**
- `allowedMoves` region restriction (from existing puzzle region logic in Python analyzers)
- Reduced visit count (50-200 sufficient for tsumego vs 800+ for full games)
- Focus on life-and-death value, not territory scoring
- **Ownership thresholds for life/death:** Use 0.7 as "alive" threshold, <-0.7 as "dead". Positions between -0.3 and 0.3 = seki. Positions between 0.3-0.7 = unsettled, needs more visits (from KaTrain thresholds validated by Cho Chikun 1P review)
- **Delta validation for refutations:** A wrong move refutation is only valid if winrate delta > 75% (adapted from Infinite_AI_Tsumego_Miner's blunder detection)
- **Visit-count difficulty profiling:** Analyze at visits=[50, 100, 200, 400] to measure "reading depth" — if the correct move appears at 50 visits → easy, only at 400 → hard
- **Refutation quality recording:** For each generated refutation, record `refutation_depth` (moves until group confirmed dead/alive) and `refutation_type` (immediate_capture, shortage_of_liberties, eye_destruction, ko, etc.) — from Cho Chikun 1P review

**Files:**
```
js/engine/mcts.js            # MCTS search engine
js/engine/search-worker.js   # Web Worker entry point
js/engine/engine-client.js   # Main thread ↔ Worker messaging
```

### Phase 5: Integration

**Goal:** Wire the TF.js engine into the lab UI.

**Actions:**
- Create new `js/browser-engine.js` that wraps `engine-client.js`
- Re-enable browser panel in `index.html` and `app.js`
- Display NN analysis results alongside local KataGo results for comparison
- Show backend indicator (WebGPU / WASM / CPU) and eval speed
- Model selector points to `models-data/` directory
- **NEW: Dual-engine comparison view** — show browser engine (b6c96) results alongside local KataGo (b28c512) results on the same position. This enables the natural dual-engine validation pattern from Infinite_AI_Tsumego_Miner (weaker generator vs. stronger referee)
- **NEW: Policy-only quick mode** — button to run Tier 0.5 (policy-only forward pass) for instant difficulty estimate without waiting for full MCTS
- **NEW: Difficulty calibration display** — show the 3-signal difficulty formula results and map to Yen-Go's 9-level system

---

## Effort Estimate (Updated)

| Phase | Effort | Testable? | Value Delivered |
|-------|--------|-----------|----------------|
| Cleanup | 1-2 hours | Yes — lab still works with local engine | Removes dead code |
| Phase 0: TF.js setup | 2-3 hours | Yes — backend detection | Infrastructure |
| **Phase 0.5: Tsumego Frame** | **0.5 days** | **Yes — verify frame output visually** | **Critical prerequisite** |
| Phase 1: Model loader | 1 day | Yes — load model, verify output shapes | Infrastructure |
| Phase 2: Board logic | 0.75 days | Yes — unit tests for captures, ko, **isGroupClosed** | Board engine + heuristic life/death |
| Phase 3: Features + Policy-only | 0.75 days | Yes — verify tensor dimensions, **run Tier 0.5 difficulty estimate** | **First usable output: difficulty estimation** |
| Phase 4: MCTS | 1-2 days | Yes — compare top move vs local KataGo | Full analysis capability |
| Phase 5: Integration | 0.75 days | Yes — full browser analysis, **dual-engine comparison** | Complete lab integration |
| **Total** | **4.5-7 days** | | |

---

## Model Selection for Browser

| Model | File Size | Download (.gz) | Eval Speed (WASM) | Recommended |
|-------|-----------|---------------|-------------------|-------------|
| b6c96 | 3.7 MB | ~3 MB | ~50ms/eval | **Yes — browser default** |
| b10c128 | 10.6 MB | ~8 MB | ~120ms/eval | Desktop with WebGPU |
| b28c512 | 258.9 MB | n/a | Impractical | **No — local engine only** |

web-katrain ships with b6c96 as default. For tsumego (small regions, tactical), b6c96 is sufficient.

---

## Enrichment Output Format (Structured Results)

Every enrichment run (browser or local) produces a structured `EnrichmentResult` for each puzzle. The exact schema will be finalized during implementation, but the contract is:

```json
{
  "puzzle_id": "YENGO-765f38a5196edb79",
  "engine": { "model": "b6c96", "backend": "wasm", "visits": 200 },
  "phase_a": {
    "task1_validation": {
      "correct_moves_validated": true,
      "value_after_correct": 0.92,
      "ownership_confirms": true,
      "disagreements": []
    },
    "task2_refutations": [
      {
        "wrong_move": "cd",
        "refutation_pv": ["de", "cf", "dg"],
        "delta": 0.83,
        "refutation_depth": 3,
        "refutation_type": "eye_destruction"
      }
    ],
    "task3_difficulty": {
      "policy_prior_correct": 0.12,
      "visits_to_solve": 85,
      "trap_density": 0.67,
      "composite_score": 5.2,
      "suggested_level": "upper-intermediate"
    }
  },
  "phase_b": {
    "task4_teaching_comment": "This throw-in reduces the eye space to one.",
    "task5_technique": ["throw-in", "eye-destruction"],
    "task6_hints": ["Look for a sacrifice", "Reduce the eye space"]
  }
}
```

### Phase A — Core Enrichment Tasks

| Task | Input | Output | Engine Needed |
|------|-------|--------|--------------|
| **A.1: Validate Correct Moves** | SGF solution tree + initial position | `correct_moves_validated: bool`, value/ownership | Local (authoritative) or Browser (quick check) |
| **A.2: Generate Refutations** | Top-N policy moves − correct moves | YR property + SGF branches with PV, delta, depth, type | Local (production) |
| **A.3: Difficulty Rating** | Policy prior + visits + trap density | YG/YX enrichment, 9-level mapping | Browser (Tier 0.5 policy-only) or Local (full MCTS) |

### Phase B — Extended Enrichment Tasks (Deferred)

| Task | Input | Output | Engine Needed |
|------|-------|--------|--------------|
| **B.4: Teaching Comments** | KataGo signal patterns (ownership changes, PV) | Move-level `C[]` with causal explanation | Local |
| **B.5: Technique Classification** | KataGo PV + ownership + value patterns | YT auto-tags (12 technique templates) | Local |
| **B.6: Hint Refinement** | Detected patterns + coordinates | Enhanced YH hints | Local or symbolic (via Quality Scorer) |

---

## Relationship to Other Plans

### Feature 134 (Score Estimation)

| This Plan (Option B) | Feature 134 (Score Estimation) |
|----------------------|-------------------------------|
| **Where:** `tools/puzzle-enrichment-lab/` | **Where:** `frontend/` (main app) |
| **Tier 2:** Full NN + MCTS analysis | **Tier 1:** Monte Carlo ownership heatmap |
| **4.5-7 days**, ~3,000 LOC new JS | **~1 day**, uses existing `goban` WASM API |
| **Purpose:** Puzzle enrichment lab tool | **Purpose:** User-facing ownership overlay |
| **Engine:** TF.js + custom MCTS | **Engine:** `OGSScoreEstimator.wasm` (29 KB) |

The two efforts are **completely independent**. Feature 134 does NOT need TF.js or MCTS.

### Puzzle Quality Scorer (Symbolic Tactical Analysis)

| This Plan (KataGo-based) | Quality Scorer (Symbolic) |
|------------------------|--------------------------|
| **Where:** `tools/puzzle-enrichment-lab/` | **Where:** `backend/puzzle_manager/core/tactical_analyzer.py` |
| **Technique:** KataGo NN + MCTS | **Technique:** Symbolic pattern matching (GoGoGo + gogamev4.0) |
| **Speed:** 100-500ms/puzzle | **Speed:** ~6ms/puzzle |
| **Accuracy:** ~95% (with sufficient visits) | ~70% (structural patterns only) |
| **Dependencies:** KataGo engine, TF.js | Zero new dependencies (uses existing `core/board.py`) |
| **Strengths:** Deep reading, calibrated difficulty, refutations | Fast, deterministic, no engine needed |
| **Weaknesses:** Requires engine, slower | Can't assess reading depth, no refutations |

**They are complementary, not competing:**

```
┌────────────────────────────────────────────────────────────┐
│  Pipeline analyze stage                                    │
│                                                            │
│  1. Quality Scorer (symbolic, ~6ms/puzzle, in-pipeline)     │
│     └─ Ladder/snapback/eye detection → YT auto-tags          │
│     └─ Group status → position validation                    │
│     └─ Tactical complexity → difficulty signal                │
│                                                            │
│  2. KataGo Enrichment (ML, ~200ms/puzzle, external tool)    │
│     └─ Policy prior → calibrated difficulty (overrides #1)    │
│     └─ MCTS → correct move validation                        │
│     └─ MCTS → refutation generation (YR)                      │
│     └─ Ownership → authoritative life/death judgment           │
│                                                            │
│  Quality Scorer runs first (fast, structural).              │
│  KataGo Enrichment runs second (slow, authoritative).       │
│  KataGo results override symbolic results where they differ.│
└────────────────────────────────────────────────────────────┘
```

**Overlap areas where Quality Scorer provides fallback if KataGo unavailable:**
| Capability | Quality Scorer | KataGo Enrichment |
|-----------|---------------|-------------------|
| Ladder detection | Symbolic trace (deterministic) | PV analysis (probabilistic) |
| Snapback detection | Capture-recapture simulation | PV analysis |
| Eye counting | Orthogonal+diagonal validation | Ownership head |
| Difficulty | Tactical complexity count (0-6) | Policy prior + visits (continuous, calibrated) |
| Technique tagging | 10 pattern→tag mappings | 12 signal→technique templates |
| Refutation generation | Not in scope | Core capability |
| Teaching comments | Not in scope | Phase B template engine |

---

## Lab Directory: After Cleanup

```
tools/puzzle-enrichment-lab/
├── bridge.py                 # FastAPI bridge (KEEP — local engine)
├── config.json               # Engine config (KEEP)
├── index.html                # UI (KEEP — update: remove browser-engine script tag)
├── README.md                 # Documentation (KEEP — update)
├── requirements.txt          # Python deps (KEEP)
├── start.sh / start.bat      # Start scripts (KEEP)
├── analyzers/                # Python analyzers (KEEP)
├── engine/                   # Python engine driver (KEEP)
├── models/                   # Pydantic models (KEEP)
├── tests/                    # Python tests (KEEP)
├── katago/                   # katago.exe + tsumego_analysis.cfg (KEEP)
├── models-data/              # NN models: b6c96, b10c128, b28c512 (KEEP)
├── vendor/besogo/            # BesoGo viewer (KEEP)
├── css/                      # Stylesheets (KEEP)
├── js/katago-client.js       # HTTP client for local bridge (KEEP)
├── js/app.js                 # Main UI controller (KEEP — update)
│
├── js/engine/                # NEW — TF.js browser engine (Phase 0-5)
│   ├── tsumego-frame.js      # Phase 0.5: Board preparation for NN input
│   ├── model-loader.js       # Phase 1: Parse .bin.gz → TF.js model
│   ├── fast-board.js         # Phase 2: Board state + Zobrist + captures + isGroupClosed()
│   ├── features.js           # Phase 3: Board → 22-channel input tensor
│   ├── mcts.js               # Phase 4: MCTS search engine
│   ├── search-worker.js      # Phase 4: Web Worker entry point
│   └── engine-client.js      # Phase 4: Main thread ↔ Worker messaging
│
├── .emsdk/                   # DELETE (~1.5 GB)
├── .wasm-build/              # DELETE (~900 MB)
├── vendor/katago-wasm/       # DELETE (47 MB)
├── js/browser-engine.js      # DELETE (broken)
└── scripts/build_wasm.sh     # DELETE
```

---

## Risks (Updated)

| Risk | Likelihood | Mitigation | Reviewed By |
|------|-----------|------------|-------------|
| TF.js WebGPU not available on Intel Iris Xe | Medium | TF.js auto-falls back to WASM/CPU | Architect |
| Model format mismatch (.bin.gz vs TF.js) | Low | web-katrain already parses this format; rewrite their parser | Architect |
| MCTS bugs (UCB formula, tree reuse) | Medium | Compare browser results against local KataGo on same position | Architect |
| Performance too slow on WASM backend | Low | b6c96 is fast; reduce visits for tsumego | Architect |
| **Tsumego frame missing → garbage NN output** | **Critical** | **Port tsumego_frame.py as Phase 0.5 (mandatory before any NN work)** | **Architect + Go Pro** |
| **Ko evaluation without proper ko threats** | **High** | **Tsumego frame must include ko threat placement; affects ~15-20% of puzzles** | **Go Pro** |
| **Miai puzzles misgraded as harder** | **Medium** | **Sum policy priors of all correct first moves when YO=miai/flexible** | **Go Pro** |
| **Approach-move puzzles misgraded** | **Medium** | **Flag puzzles where correct first move is >5 intersections from puzzle center** | **Go Pro** |
| **b6c96 too weak for dan-level problems** | **Medium** | **b6c96 reads ~10-15 moves; use b10c128 for 6d+ puzzles, local engine for expert** | **Go Pro** |

---

## Decision Log (Updated)

| Decision | Chose | Over | Reason |
|----------|-------|------|--------|
| NN inference backend | TF.js | Custom KataGo WASM | TF.js handles WebGPU/WASM/CPU cascade automatically; no Emscripten needed |
| Code approach | Rewrite core engine | Import web-katrain dist | Quality concerns, Copilot-generated, React coupling, we only need tsumego subset |
| Browser model | b6c96 (3.7 MB) | b10c128 (10.6 MB) | Sufficient for tsumego; faster download; web-katrain default |
| Feature 134 | Separate (OGS WASM) | Merge with this | Different tier, different purpose, simpler implementation |
| Remove Emscripten artifacts | Yes | Keep for reference | ~2.4 GB of dead weight; documented in 003-building-katago-wasm.md |
| **Tsumego frame** | **Phase 0.5 (mandatory)** | **Defer to late phase** | **Without frame, all NN analysis produces garbage — validated by KaTrain code and Go professional** |
| **Difficulty estimation** | **3-signal combination** | **Policy-prior-only** | **Go professional confirmed policy prior has blind spots for miai, approach moves, and "looks obvious but hard" positions** |
| **BTP heuristic estimator** | **Port `isGroupClosed()` to Phase 2; defer rest to F134** | **Include full BTP in Plan 004** | **Only `isGroupClosed()` needed for enrichment lab; rest is for F134** |
| **Complexity formula** | **KaTrain `sum(ptsLost*prior)/sum(prior)`** | **Custom formula** | **Battle-tested in production KaTrain; exactly what we need for trap density** |
| **Cognitive depth metric** | **`visits_at_first_consensus`** | **Dingdong's `top/avg` ratio** | **The ratio is noisy for tsumego with few candidate moves; visit-to-consensus is more meaningful** |
| **Miai handling** | **Sum policy priors** | **Use max prior** | **Go professional: miai splits priors artificially, inflating perceived difficulty** |
| **Tsumego Miner patterns** | **Study, rewrite, adapt** | **Ignore** | **Delta detection, dual-engine, temperature/visits variation are valuable patterns to learn from and reimplement** |
| **Browser vs Local** | **Independent, parallel tools** | **Browser as counterbalance to local** | **Browser = lightweight quick-check. Local = production workhorse. Dual-engine referee is local-only (two models).** |
| **Quality Scorer overlap** | **Complementary: symbolic first, KataGo overrides** | **Pick one** | **Quality Scorer handles ~60% of puzzles at 6ms each; KataGo handles 100% at 200ms with higher fidelity. Run in sequence.** |

---

> **See also:**
> - [005-learnings-and-review-browser-engine.md](005-learnings-and-review-browser-engine.md) — Full learnings document with expert reviews
> - [003-building-katago-wasm.md](003-building-katago-wasm.md) — WASM compilation guide + why Option A failed
> - [001-research-browser-and-local-katago-for-tsumego.md](001-research-browser-and-local-katago-for-tsumego.md) — Full landscape research
> - [TODO/134-score-estimation-wasm/](../134-score-estimation-wasm/) — Separate Feature 134 plan (Tier 1 Monte Carlo)
> - [web-katrain architecture](https://github.com/Sir-Teo/web-katrain/blob/main/docs/diagram.md) — Reference diagrams
> - [docs/reference/katago-browser-analysis-research.md](../../docs/reference/katago-browser-analysis-research.md) — Executive summary
> - [KaTrain tsumego_frame.py](https://github.com/sanderland/katrain/blob/master/katrain/core/tsumego_frame.py) — Tsumego frame reference
> - [KaTrain ai.py](https://github.com/sanderland/katrain/blob/master/katrain/core/ai.py) — Policy-based AI strategies + complexity formulas
> - [BTP estimator.js](https://blacktoplay.com/js/estimator.js) — Pure JS heuristic scoring reference
> - [Infinite AI Tsumego Miner](https://github.com/MachineKomi/Infinite_AI_Tsumego_Miner) — Puzzle mining patterns (Delta detection, dual-engine, difficulty grading)
> - [Puzzle Quality Scorer plan](../puzzle-quality-scorer/implementation-plan.md) — Symbolic tactical analysis (complementary to KataGo enrichment)
