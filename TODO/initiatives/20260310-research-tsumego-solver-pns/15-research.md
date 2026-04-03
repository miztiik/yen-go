# Research: cameron-martin/tsumego-solver — What Can puzzle-enrichment-lab Learn?

**Initiative:** `20260310-research-tsumego-solver-pns`
**Last Updated:** 2026-03-10
**Status:** Research Complete
**Researcher Role:** Feature-Researcher (read-only, no implementation)

---

## 1. Research Question and Boundaries

### Question
How does [cameron-martin/tsumego-solver](https://github.com/cameron-martin/tsumego-solver) solve life-and-death (L&D) tsumego puzzles, and what concrete techniques can `tools/puzzle-enrichment-lab` adopt or adapt to save KataGo query budget and improve solution tree quality?

### In Scope
- Algorithmic techniques in the solver (search, terminal detection, board representation)
- Techniques transferable to the KataGo-oracle architecture used by the enrichment lab
- Python/pure-logic implementations that do not require a Rust runtime dependency

### Out of Scope
- Using the Rust binary as a dependency at runtime (violates "Zero Runtime Backend" holy law and tool isolation rules)
- Full replacement of KataGo with a pure-search solver (KataGo handles non-enclosed puzzles, ko, technique annotation — scope too narrow for tsumego-solver)
- Generating new puzzles (Yen-Go imports from curated sources)

---

## 2. Internal Code Evidence

| R-ID | File | Symbol | Behavior |
|------|------|---------|----------|
| R-I-1 | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | `build_solution_tree()` | KataGo-oracle recursive tree builder; calls engine for every node; no rule-based early exit before query |
| R-I-2 | `tools/puzzle-enrichment-lab/analyzers/solve_position.py` | `_build_tree_recursive()` | Stopping conditions: budget cap, depth profile, pass-as-best, seki early-exit; no combinatorial "dead group" exit |
| R-I-3 | `tools/puzzle-enrichment-lab/analyzers/ko_validation.py` | `KoPvDetection`, `can_ko_be_validated()` | Ko detection via PV repetition scan — already partly rule-based, complementary to solver approach |
| R-I-4 | `tools/puzzle-enrichment-lab/analyzers/technique_classifier.py` | `classify_techniques()` | Detects seki by near-zero ownership — equivalent to tsumego-solver's unconditional-life terminal; NOT used as a pre-query gate |
| R-I-5 | `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` | (module) | Boundary/cropping logic for isolating the puzzle region — parallel to tsumego-solver's `out_of_bounds` BitBoard concept |
| R-I-6 | `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py` | `estimate_difficulty_policy_only()` | Uses raw policy prior only (no search depth) — could be complemented by proof-search depth signal |
| R-I-7 | `TODO/kishimoto-mueller-tasks.md` | Phase 3–6 | Transposition table (T018–T027), simulation (T028+), forced moves — tasks already planned from the SAME Kishimoto-Müller paper as tsumego-solver |
| R-I-8 | `TODO/kishimoto-mueller-search-optimizations.md` | `## Paper Summary` | Confirms Yen-Go has an active plan referencing the identical AAAI-05 Kishimoto-Müller paper; transposition (KM-02) is complete; simulation (KM-01) and forced moves (KM-03) are pending phases |

### Key Internal Finding
The Kishimoto-Müller paper is **already the active design authority** for the enrichment lab's tree builder (see R-I-7, R-I-8). The cameron-martin solver is a **working open-source implementation of the same paper**. It is a reference implementation, not a novel technique source.

---

## 3. External References

| R-ID | Source | Relevance |
|------|--------|-----------|
| R-E-1 | cameron-martin/tsumego-solver `src/puzzle.rs` | Implements **Proof-Number Search (PNS)** as an AND-OR tree; `solve_iteration()` = select MPN → expand → update ancestors; directly maps to the df-pn variant in the Kishimoto-Müller paper |
| R-E-2 | `src/puzzle/terminal_detection.rs` | `is_terminal()` checks: (1) double-pass → game ends, (2) **Benson's unconditional life** → defender wins immediately, (3) interior-point count < 3 → attacker wins; no KataGo needed for these checks |
| R-E-3 | `src/go/benson.rs` | Implements **Benson's algorithm** for unconditional life: iterative block pruning with "healthy region" counting; pure Go rules, zero neural network |
| R-E-4 | `src/puzzle/proof_number.rs` | `ProofNumber` data structure: finite/infinite values with saturating arithmetic; used to propagate proven/disproven status up the AND-OR tree |
| R-E-5 | Kishimoto & Müller (2005), AAAI-05 pp. 1374–1379 | Canonical reference: df-pn search, transposition tables, simulation, forced move detection; **same paper already planned in `TODO/kishimoto-mueller-search-optimizations.md`** |
| R-E-6 | `src/go.rs` (GoBoard, BitBoard) | Board encoded as two `BitBoard` words (black, white); out-of-bounds occupies both — enables O(1) group-liberty and flood-fill checks; this is the source of the solver's speed |
| R-E-7 | Thomsen (2000), Lambda-Search — ICGA Journal 23(4) | Already referenced in `TODO/kishimoto-mueller-search-optimizations.md` as DD-L3; depth-dependent policy thresholds in the enrichment lab `_build_tree_recursive()` are the direct analogue |
| R-E-8 | `src/generation.rs` | Puzzle generator: random board → validate with PNS timeout → emit SGF; irrelevant to Yen-Go (no generated puzzles per architecture rule) |

---

## 4. Candidate Adaptations for Yen-Go

| R-ID | Technique | Source in tsumego-solver | Current Enrichment Lab Status | Adaptation Effort | Budget Impact |
|------|-----------|--------------------------|-------------------------------|-------------------|---------------|
| R-A-1 | **Benson's Unconditional Life (pre-query gate)** | `terminal_detection.rs` → `unconditionally_alive_blocks_for_player()` + `benson.rs` | ❌ Not implemented — seki detection uses KataGo ownership (post-query) | Medium: implement in pure Python using `sgfmill` stone data; gate before `engine.query()` | High: avoids entire subtree queries when defender is already unconditionally alive |
| R-A-2 | **Interior-point early exit** | `can_defender_live()` counts non-adjacent interior points; if ≤ 2, attacker wins | ❌ Not implemented | Low: pure geometry on the sgfmill board; returns `attacker_wins=True` early | Medium: avoids deep queries in lost positions |
| R-A-3 | **Simulation (KM-01)** | AND-OR sibling simulation — tsumego-solver does this via proof-number propagation | ⚠️ Planned — `TODO/kishimoto-mueller-tasks.md` Phases 4–5, not yet implemented | Already designed in the KM plan | 30–50% budget reduction (per KM plan) |
| R-A-4 | **Transposition table (KM-02)** | `select_most_proving_node()` implicitly handles via node reuse in stable graph | ✅ Already implemented — T018–T027 complete | N/A | Already realized |
| R-A-5 | **Forced-move reduction (KM-03)** | Tsumego-solver implicitly prunes forced moves at And-Or node expansion | ⚠️ Planned — `TODO/kishimoto-mueller-tasks.md` Phase 5 | Already designed | 15–25% reduction |
| R-A-6 | **BitBoard-based liberty checking** | `get_alive_groups_for_player()` + flood fill ops | ❌ Enrichment lab uses sgfmill (pure Python, slower) | High: would require replacing board representation; violates "buy don't build" unless a library exists | Low immediate impact — lab is I/O-bound on KataGo, not CPU-bound on board logic |
| R-A-7 | **Double-pass terminal** | `PassState::PassedTwice → attacker wins` | ✅ Already handled — `EDGE-4: Pass as best move → explicit rejection` in `solve_position.py` | N/A | Already handled |

**Top Priority Adaptations:** R-A-1 (Benson gate) and R-A-2 (interior-point exit) are the clearest gaps relative to tsumego-solver that are (a) not already planned, (b) implementable without a new engine, and (c) provide early-exit budget savings.

---

## 5. Risks, License, and Rejection Reasons

| R-ID | Item | Detail | Severity |
|------|------|---------|----------|
| R-R-1 | **License** | No LICENSE file found in the repository (HTTP 404 on `/LICENSE`). No SPDX identifier in `Cargo.toml`. The repo is public on GitHub but **not confirmed open-source**. | ⚠️ Medium — Do NOT copy code verbatim. Adapt concepts/algorithms only (algorithms are not copyrightable). |
| R-R-2 | **Scope mismatch** | tsumego-solver is designed for **fully enclosed local L&D** with a small boundary. Yen-Go imports puzzles from diverse sources (goproblems, ogs, tsumego dragon) including non-enclosed positions. Benson's algorithm only applies to locally enclosed groups. | ⚠️ Medium — Gate must check whether puzzle has clear boundary before applying Benson early-exit |
| R-R-3 | **Ko puzzles** | tsumego-solver has limited ko handling (single-point ko via `ko_violations: BitBoard`; no multi-step ko). Yen-Go already has `YK[direct|approach]` and `KoValidationResult`. Benson cannot unconditionally determine life in ko-dependent positions. | ⚠️ Medium — Skip Benson gate when `YK != none` |
| R-R-4 | **Seki blind spot** | Benson's algorithm does NOT detect seki. A group in seki is NOT unconditionally alive per Benson — it would be counted as dead. Applying Benson as a terminal-detection gate could incorrectly classify seki positions as "attacker wins". | 🔴 High — Must pair Benson gate with existing seki detection (technique_classifier `seki` tag or KataGo ownership near zero) |
| R-R-5 | **Rust dependency** | Using the tsumego-solver binary would introduce a Rust runtime dependency and violate the tool isolation rule (`tools/ must NOT import from backend/`) and compilation complexity. | 🔴 High — Rejected: algorithms must be re-implemented in Python or skipped |
| R-R-6 | **CPU vs I/O bottleneck** | BitBoard speed (R-A-6) is only valuable when the solver is CPU-bound. The enrichment lab is I/O-bound (KataGo network calls). Python BitBoard impl has negligible impact. | Low — R-A-6 rejected on ROI grounds |
| R-R-7 | **Overlap with existing KM plan** | KM-01 (simulation) and KM-03 (forced moves) are already planned in `TODO/kishimoto-mueller-tasks.md`. Re-deriving them from tsumego-solver would duplicate planned work. | Low — no new work needed; confirm planner is aware |

---

## 6. Planner Recommendations

1. **Implement Benson's unconditional-life pre-query gate (R-A-1)** as a new Phase in `TODO/kishimoto-mueller-tasks.md`. Place it in `analyze_position_candidates()` in `solve_position.py`: before calling `engine.query()` at a node, run a pure-Python Benson check using the reconstructed board from `SgfNode` stone data. Return a synthetic "defender wins" terminal node immediately. Skip when `YK != none` or when technique includes `seki`. This requires ≤ 1 new file (`analyzers/benson_check.py`) and ≤ 50 lines of logic.

2. **Implement interior-point two-eye check (R-A-2)** alongside R-A-1 as the "attacker wins" counterpart. The math: count empty interior cells in the region bounded by the attacker's safe stones; if ≤ 2 and no adjacent pair exists, defender cannot form two eyes. This is already implicit in `tsumego_frame.py` boundary logic — it needs connecting to the query gate.

3. **Complete KM-01 (simulation) and KM-03 (forced moves)** from the existing plan before implementing R-A-1/R-A-2 — they are higher-ROI (30–50% budget reduction) and already specified. R-A-1/R-A-2 are bolt-on improvements after the KM phases are stable.

4. **Do not adopt BitBoard board representation (R-A-6)** — the enrichment lab is I/O-bound on KataGo, not CPU-bound on board operations. The cost of replacing `sgfmill` as the board representation engine far exceeds any performance gain.

---

## 7. Open Questions for Planners

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should R-A-1 (Benson gate) be added as a new KM sub-phase in `kishimoto-mueller-tasks.md`, or as a separate initiative? | A: New sub-phase in KM plan (Phase 7) / B: Separate initiative / C: Defer until KM phases complete | A | — | ❌ pending |
| Q2 | How should the Benson gate handle seki positions? KataGo correctly handles seki via near-zero ownership. Does the planner want a hard skip (never gate seki) or a soft skip (fall through to KataGo if ownership ambiguous)? | A: Hard skip when `seki` tag present / B: Run Benson; if result is "dead", fall through to KataGo / C: Do not implement Benson gate at all | B | — | ❌ pending |
| Q3 | The tsumego-solver repo has no LICENSE file. Does the legal policy allow using its algorithmic concepts (not code) as reference, given algorithms are not copyrightable? | A: Yes, conceptual reference only is fine (standard practice) / B: Require explicit license confirmation from repo author / C: Derive independently from the Kishimoto-Müller paper instead | A | — | ❌ pending |
| Q4 | Should the interior-point check (R-A-2) use the existing `tsumego_frame.py` boundary, or define its own? | A: Reuse tsumego_frame boundary (consistent) / B: Compute independently (decoupled) | A | — | ❌ pending |

---

## 8. Post-Research Summary

### What tsumego-solver Does
- Implements **Proof-Number Search (PNS)** on an AND-OR game tree (Kishimoto-Müller AAAI-05)
- Uses **Benson's algorithm** for unconditional life as the deterministic "defender wins" terminal condition
- Uses **interior-point geometry** as the "attacker wins" terminal condition
- Uses a **BitBoard** representation for O(1) group/liberty operations
- Works best on **fully enclosed local positions** — not full-board 19×19

### What's New vs. Existing Yen-Go Knowledge
- ✅ Benson's terminal gate (R-A-1) — **not yet in the lab, not yet planned in KM tasks**
- ✅ Interior-point two-eye exit (R-A-2) — **not yet in the lab, not yet planned**
- ℹ️ PNS/transpositions/simulation/forced moves — already in KM plan, tsumego-solver is confirmation
- ❌ No novel techniques beyond what the paper already provides

---

**post_research_confidence_score:** 82  
**post_research_risk_level:** medium  
_(Medium risk because: Benson gate correctness requires careful seki/ko exclusion; license ambiguity on the repo; KM plan phases must complete first for stable integration baseline)_
