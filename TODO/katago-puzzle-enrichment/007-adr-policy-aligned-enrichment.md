# ADR-007: KataGo Puzzle Enrichment — Architecture Decision Record

**Status**: Accepted  
**Date**: 2026-03-01 (consolidated from research started 2026-02-25)  
**Context**: KataGo enrichment lab → pipeline integration  
**Supersedes**: `sgf_patcher.py` hardcoded property classification  
**Source documents**: [001](001-research-browser-and-local-katago-for-tsumego.md), [002](002-implementation-plan-katago-enrichment.md), [003](003-building-katago-wasm.md), [004](004-plan-browser-engine-option-b.md), [005](005-learnings-and-review-browser-engine.md), [006](006-implementation-plan-final.md)

---

## Summary

This ADR consolidates ALL architectural design decisions made across the KataGo puzzle enrichment initiative (docs 001–006), including the rename of `sgf_patcher.py` → `sgf_enricher.py` and the alignment of property-writing behavior with the pipeline's declarative policy system.

## Context

The enrichment lab's original `sgf_patcher.py` used a two-tier property classification:

- `_HUMAN_CURATED_PROPS = {"YG", "YT", "YH"}` — preserved when FLAGGED
- `_ENGINE_DERIVED_PROPS = {"YR", "YX"}` — **always overwritten** regardless of status

This conflicts with the pipeline's analyze stage, which uses `config/sgf-property-policies.json`:

- `YR` → `enrich_if_absent` (preserve if present)
- `YX` → `enrich_if_partial` (preserve if valid, recompute if malformed)
- `YG` → `enrich_if_absent` (preserve if present)

When puzzles arrive from the pipeline's analyze stage (any source — Cho Chikun, sanderland, OGS, etc.), they may already have valid `YX` and `YG` computed by the pipeline's own classifiers. The enrichment lab should not blindly overwrite these.

More broadly, the enrichment lab went through a multi-phase research and implementation cycle spanning feasibility research (001), planning (002), a failed WASM compilation attempt (003), a corrected browser engine plan (004), expert reviews (005), and a comprehensive final implementation plan (006). The decisions below capture the full arc.

## Decisions

### D1: Policy-Driven Property Writing

**Decision**: Replace hardcoded `_HUMAN_CURATED_PROPS` / `_ENGINE_DERIVED_PROPS` with config-driven policy checks that read from `config/sgf-property-policies.json`.

**Rationale**: Single source of truth for property policies. If a policy changes (e.g., `YR` moves from `enrich_if_absent` to `enrich_if_partial`), the enricher automatically respects it.

**Constraint**: `tools/` must NOT import from `backend/`. The enricher implements a lightweight local policy reader that reads the shared JSON config directly, mirroring the pipeline's `PropertyPolicyRegistry.is_enrichment_needed()` logic for the 3 enrichment-relevant policies: `enrich_if_absent`, `enrich_if_partial`, `override`.

### D2: SGF Refutation Branches (Not Just YR Property)

**Decision**: The enricher adds full refutation variation branches to the SGF move tree. `YR` is derived from the branch root moves, not set independently.

**Rationale**: The pipeline's analyze stage can already extract `YR` coordinates from existing wrong-move branches (via `is_correct=False` inference in `correctness.py`). By writing actual SGF branches with `C[Wrong. ...]` comments, the KataGo enrichments become visible to both the pipeline and the frontend puzzle solver. The `YR` property becomes a derived summary, not a primary data store.

**Format**: Each refutation branch is appended at root level:

```sgf
(;B[cd]C[Wrong. After this move, winrate drops to 15%.]
;W[dc]
;B[dd])
```

### D3: Refutation Branch Detection (Skip If Present)

**Decision**: Before generating refutations, check whether the SGF tree already has wrong-move branches. If present, skip refutation generation entirely.

**Detection**: Walk first-level children of root. A child is a wrong-move branch if:

- Comment starts with "Wrong" or "Incorrect" (Layer 2 inference)
- Has `BM` (bad move) or `TR` (triangle) property markers (Layer 1 inference)

**Rationale**: Re-running KataGo on puzzles that already have curated refutation trees would overwrite human-reviewed wrong-move sequences. This applies to all puzzle sources, not just Cho Chikun.

### D4: Level Mismatch Threshold (Overwrite on Severe Mismatch)

**Decision**: `YG` follows `enrich_if_absent` by default, but with a configurable mismatch threshold. When the KataGo-estimated level differs from the existing level by ≥ N steps, the enricher overwrites `YG` and logs a warning.

**Threshold**: Configured in `config/katago-enrichment.json` under `level_mismatch.threshold`. Uses numeric level IDs from `puzzle-levels.json` (110=novice through 230=expert, 10 apart within ranges). Distance = `abs(existing_id - estimated_id) / 10`. The gap between kyu (160) and dan (210) counts as 5 steps.

**Placeholder**: The threshold value is TBD — needs calibration against multiple puzzle collections with Go professional input. Default is set conservatively high to avoid false overwrites.

**Audit trail**: When mismatch overwrite fires, the enrichment result includes `level_overridden: true` with both the original and new level for review.

### D5: Multi-Source Applicability

**Decision**: The enrichment policies apply uniformly to ALL puzzle sources, not just a single collection.

**Rationale**: Puzzles from different sources arrive with different subsets of properties. For example:

- Some sources provide `YG` but no `YR` or refutation branches
- Some provide refutation branches with "Wrong" comments but no `YX`
- Some arrive fully enriched from a previous pipeline run

The policy system handles all cases: check each property independently, enrich only when the policy says to.

### D6: YX Validation (enrich_if_partial)

**Decision**: `YX` uses the same validation regex as the pipeline: `^d:\d+;r:\d+;s:\d+;u:[01](;a:\d+)?$`. If the existing value passes, preserve it. If absent or malformed, recompute from the (possibly newly enriched) solution tree.

### D7: ACCEPTED/FLAGGED Status Simplification

**Decision**: The ACCEPTED/FLAGGED distinction for property overwrite is removed for `YR` and `YX`. Property policies from the config govern all overwrite decisions. REJECTED status still returns the original SGF unchanged.

**Rationale**: The old behavior (ACCEPTED → overwrite YG, FLAGGED → preserve YG) was a proxy for confidence. The pipeline's policy system is more precise — `enrich_if_absent` means "never overwrite existing valid value regardless of confidence." The mismatch threshold (D4) handles the case where the existing level is clearly wrong.

---

## Historical Design Decisions (from docs 001–006)

The following decisions were made during the research and design phases and form the architectural foundation for the enrichment system. They are preserved here as the consolidated record.

### Feasibility & KataGo Engine (from 001-Research)

#### D8: Full-Board Input, Local Output

**Decision**: KataGo receives the full 19×19 board but we only read policy/ownership for the puzzle-relevant region.

**Rationale**: KataGo's neural net expects full-board input (no partial-board mode exists). Restricting output interpretation to the puzzle region avoids noise from irrelevant board areas. The tsumego frame (D20) controls what fills the non-puzzle area.

#### D9: Max 3 Refutations, Policy > 0.05

**Decision**: Generate at most 3 refutation (wrong-move) branches per puzzle. Only moves with policy prior > 0.05 qualify.

**Rationale**: Diminishing pedagogical returns beyond 3. Low-policy moves are rarely attempted by students and generate noise. Threshold from KataGo analysis of 200+ puzzles: moves below 0.05 are almost always irrelevant stones.

#### D10: Difficulty Formula

**Decision**: Difficulty = f(policy_prior, visits_to_solve, solution_depth, refutation_count). Maps to YX complexity fields [d, r, s, u]. Level assignment (YG) is derived from this via calibrated difficulty bands.

**Rationale**: Single-metric difficulty is insufficient — a deep tesuji with an obvious first move (high policy) is easier than a shallow problem with a non-obvious first move (low policy). Multi-factor model captures this.

#### D11: No LLM for Comments  - Suspended

**Decision**: Suspended 15Mar2026 - We are using katago

#### D12: KataGo Model Tiers

**Decision**: Tiered model selection based on context:

- `b6c96` (3.7MB) — Browser/Tier 0.5 policy-only inference
- `b10c128` (~25MB) — Quick local engine (200 visits)
- `b28c512` (~260MB) — Referee local engine (2000 visits), production enrichment

**Rationale**: Smaller models are faster but less accurate. Browser needs smallest model for download size. Local enrichment pipeline uses strongest model for correctness. Dual-engine approach (D24) gets best of both.

### Implementation Boundaries (from 002-Implementation Plan)

#### D13: Side-Quest Isolation

**Decision**: `tools/puzzle-enrichment-lab/` MUST NOT import from `backend/`. Shared configuration lives in `config/` as JSON read by both independently.

**Rationale**: The enrichment lab is an experimental side-quest. Backend import chains would create coupling that makes the lab hard to delete or restructure. Config JSON is the shared contract.

#### D14: Pydantic Models for Inter-Function Data Flow

**Decision**: All enrichment data structures (analysis results, validation results, enrichment status) use Pydantic `BaseModel` with full type annotations.

**Rationale**: Structured validation at boundaries catches type errors early. Schema versioning (D23) is trivial with Pydantic. Serialization to JSON for debugging/logging is free.

#### D15: Phase A Scope Lock

**Decision**: Phase A delivers ONLY: validate existing properties + generate refutation branches + estimate difficulty. Phase B (comments, classification, hints) is a separate scope.

**Rationale**: Prevents scope creep. Phase A produces the highest-value enrichments (wrong-move branches + difficulty) with the simplest KataGo integration (single analysis query per puzzle).

### WASM Feasibility (from 003-Building KataGo WASM)

#### D16: WASM Approach Abandoned

**Decision**: Browser-native KataGo via WebAssembly is not viable. Compilation succeeded (Emscripten, 47MB WASM + 11MB model) but JS integration failed: KataGo's stdin/stdout-based GTP protocol is incompatible with browser event loops (no synchronous blocking I/O in web workers).

**Rationale**: Extensive debugging confirmed this is a fundamental architecture mismatch, not a fixable bug. Shifted to TF.js approach (D17).

### Browser Engine Architecture (from 004-Browser Engine Option B)

#### D17: TensorFlow.js Over Custom WASM

**Decision**: Use TF.js for browser-side neural net inference, not a custom WASM build.

**Rationale**: TF.js handles the WebGPU → WebGL → WASM → CPU fallback cascade automatically across browsers. Custom WASM requires reimplementing this cascade manually. TF.js model conversion from KataGo weights is well-documented.

#### D18: Rewrite Over Import

**Decision**: Write a new minimal Go engine for the browser rather than importing web-katrain.

**Rationale**: web-katrain source analysis revealed: Copilot-generated code with inconsistent quality, React coupling throughout, 12K+ lines with much irrelevant to tsumego. Extracting the ~2K lines of useful core logic and rewriting with proper types is less risky than adapting the full codebase.

#### D19: Browser vs Local Are Independent Systems

**Decision**: The browser Go engine and the local KataGo enrichment pipeline are independent parallel systems, not a single system with browser/local modes.

**Rationale**: They serve different purposes:

- **Browser**: Real-time move validation during puzzle solving (< 100ms constraint)
- **Local**: Batch enrichment of puzzle metadata during pipeline processing (no time constraint)

They share the model architecture but differ in visit counts, output processing, and integration points. Treating them as one system would over-constrain both.

#### D20: Tsumego Frame Is Mandatory

**Decision**: Before KataGo analysis, every puzzle MUST be placed in a "tsumego frame" — surrounding empty board space filled with a specific pattern that prevents the NN from treating the position as a real game.

**Rationale**: Without the frame, KataGo's policy/value outputs are meaningless for tsumego — the model treats the puzzle as a fragment of a whole-board position and suggests moves that make sense for a full game but are wrong for the isolated problem. The frame must look "unnatural" (D21) to the NN.

#### D21: Tsumego Frame Must Look Unnatural

**Decision**: The tsumego frame pattern should NOT resemble a natural game position. Use alternating stones, checkerboard, or wall patterns.

**Rationale**: If the frame looks like a real game, KataGo's value head produces biased evaluations. An obviously artificial frame signals to the NN that only the puzzle region matters. Validated empirically: natural-looking frames produce ~15% winrate error vs ~3% for artificial frames.

#### D22: Quality Scorer + KataGo Are Complementary

**Decision**: The symbolic Quality Scorer (6ms, pattern-based) runs FIRST. KataGo (200ms+, NN-based) overrides specific metrics where it has higher signal.

**Rationale**: Quality Scorer catches structural issues (missing solution, duplicate stones, invalid coordinates) that don't need NN analysis. KataGo adds difficulty estimation and refutation quality that require search. Sequential composition: Quality Scorer gates KataGo (don't waste GPU on structurally invalid puzzles).

### Expert Review Findings (from 005-Learnings)

#### D23: Schema Versioning for AiAnalysisResult

**Decision**: `AiAnalysisResult` Pydantic model carries a `schema_version` field (v1→v4 progression). Breaking changes bump the version. Consumers check the version before processing.

**Rationale**: As enrichment features evolve, the result structure grows. Without explicit versioning, consumers silently misinterpret fields. Pydantic validators enforce schema compliance at deserialization.

#### D24: Dual-Engine Referee Pattern

**Decision**: Local enrichment uses two KataGo engines at different strengths:

- **Quick** (b10c128, 200 visits) — fast first-pass analysis
- **Referee** (b28c512, 2000 visits) — high-confidence second opinion

Escalation trigger: Quick engine winrate for the "correct" move falls in uncertainty band (0.3–0.7).

**Rationale**: Running the strongest engine on every puzzle is wasteful — 70%+ of puzzles are unambiguous to the quick engine. The referee only activates for genuinely uncertain positions, cutting average enrichment time by ~60%.

#### D25: KaTrain Calibrated Rank Formula

**Decision**: Adopt KaTrain's empirically-calibrated formula for difficulty estimation:

```
orig_calib_avemodrank = 0.063015 + 0.7624 * board_squares / (10^(-0.05737 * kyu_rank + 1.9482))
```

**Rationale**: KaTrain's formula is calibrated against thousands of problems with known difficulty. Reimplementing difficulty estimation from scratch would require the same calibration effort. The formula maps directly to our 9-level system via configurable bands.

#### D26: Trap Density as Difficulty Signal

**Decision**: Trap density = `sum(pointsLost × prior) / sum(prior)` over wrong first moves.

**Rationale**: Measures how "tempting" the wrong moves are. A puzzle where the top-policy wrong move loses 30 points is harder than one where it loses 2 points. Adopted from KaTrain analysis tools, validated against professional game records.

#### D27: `visits_at_first_consensus` Over Visit Ratios

**Decision**: Use `visits_at_first_consensus` (the visit count at which the correct move first becomes the top move) as the primary depth signal, not `top_visits / avg_visits`.

**Rationale**: Visit ratios are noisy for easy puzzles (small absolute numbers inflate ratios). `visits_at_first_consensus` has a direct interpretation: "how much thinking does the engine need?" This correlates better with human difficulty perception.

#### D28: Miai Correction for Multi-Answer Puzzles

**Decision**: When `YO=miai` or `YO=flexible`, sum the policy priors of ALL correct first moves when computing difficulty. Do not penalize difficulty for having multiple solutions.

**Rationale**: Without correction, a puzzle with two equally good first moves (each with policy 0.25) would be rated harder than one with a single move (policy 0.50), which is the opposite of reality. Miai puzzles are easier because any of several moves works.

#### D29: Ownership Thresholds for Life/Death

**Decision**: KataGo ownership values map to life/death status:

- \> 0.7 → alive
- < -0.7 → dead
- ≈ 0 (within ±0.1) → seki candidate

**Rationale**: Thresholds from KaTrain, validated by professional Go player review. Used to verify that the puzzle's stated objective matches what KataGo's ownership map shows: a "kill" puzzle should show the target group as dead after the correct sequence.

#### D30: Delta Validation for Refutations

**Decision**: A wrong move is only a valid refutation if the winrate drops > 75% from the correct move's winrate.

**Rationale**: From Infinite_AI_Tsumego_Miner research — moves that only slightly reduce winrate are ambiguous (could be suboptimal but not "wrong"). The 75% threshold ensures refutations are clearly incorrect, avoiding pedagogically confusing "almost-right" variations.

### Final Implementation Architecture (from 006)

#### D31: Tag-Aware Validation Dispatch

**Decision**: Validation logic is dispatched based on puzzle tags in priority order: ko > seki > capture_race > connection > tactical > life_and_death > fallback. Each tag type has specialized validation rules.

**Rationale**: A ko puzzle requires different validation (detecting repeated board positions in the PV) than a seki puzzle (checking balanced ownership). Generic validation misses tag-specific correctness criteria.

#### D32: Ko PV Detection

**Decision**: Detect ko fights by finding repeated coordinates in KataGo's principal variation (PV). If a stone coordinate appears at position N and again at position N+2 or N+4, it indicates capture-recapture.

**Rationale**: Ko fights invalidate simple winrate-based validation — the PV may show ko exchanges that look like oscillating winrate. Ko detection allows switching to ko-specific validation (check ko threat counting, verify unconditional resolution).

#### D33: Seki 3-Signal Detection

**Decision**: Classify a position as seki when three signals converge:

1. Balanced winrate (both sides ≈ 0.5)
2. Low score (near 0)
3. Both contested groups survive (ownership ≈ 0 for both)

**Rationale**: Any single signal can occur in non-seki positions. The three-signal conjunction has near-zero false positive rate in testing against Sensei's Library seki problems.

#### D34: TDD Governance

**Decision**: All enrichment code follows strict Red-Green-Refactor:

1. Write failing test with fixtures from Sensei's Library
2. Implement minimal code to pass
3. Refactor without changing behavior
4. Each phase (A.1–A.5) has prerequisite tests that must pass before proceeding

**Rationale**: The enrichment lab produces data that feeds into published puzzles. Incorrect enrichment (wrong difficulty, missing refutations) degrades user experience. TDD ensures correctness is verified before integration.

#### D35: Sensei's Library as Golden Reference

**Decision**: ALL test fixtures for enrichment validation come from Sensei's Library positions, not synthetic puzzles.

**Rationale**: Sensei's Library positions are verified by strong Go players. Using synthetic fixtures risks encoding the developer's (possibly incorrect) understanding of Go. Real positions catch edge cases that synthetic ones miss.

#### D36: KataGo Config for Tsumego

**Decision**: KataGo analysis configuration for tsumego uses:

- `rootNumSymmetriesToSample = 8` (all board symmetries)
- `staticScoreUtilityFactor = 0` (disable territory scoring)
- `dynamicScoreUtilityFactor = 0` (disable score-based search)
- `komi = 0` (no komi for life-and-death)

**Rationale**: Tsumego is qualitative (alive/dead), not quantitative (who leads by how many points). Score-based search wastes visits on score estimation irrelevant to life-and-death. 8 symmetries improve policy accuracy for the small puzzle region.

#### D37: Progressive Visit Escalation

**Decision**: For uncertain positions, escalate visits progressively: 50 → 100 → 200 → 400 → 800 → 2000 until the correct move becomes the top policy move.

**Rationale**: Most puzzles resolve at low visit counts. Jumping straight to 2000 visits wastes computation. Progressive escalation provides the right amount of analysis per puzzle, keeping average enrichment time low.

#### D38: CLI Subcommands with Exit Codes

**Decision**: Enrichment CLI exposes `enrich`, `patch` (alias), `validate`, `batch` subcommands. Exit codes: 0=accepted, 1=error, 2=flagged-for-review.

**Rationale**: Machine-readable exit codes enable batch scripting (e.g., `find . -name "*.sgf" | xargs enrich` with error handling). The `patch` alias preserves backward compatibility during migration.

#### D39: Port BTP `isGroupClosed()` for Structural Pre-Check

**Decision**: Port the `isGroupClosed()` function from BTP (BlackToPlay) for quick structural life/death pre-check before KataGo analysis.

**Rationale**: A simple graph traversal can detect whether a group has any liberties that connect to the board edge. Groups that are fully enclosed can be validated structurally (no KataGo needed for obvious captures). Reduces unnecessary KataGo calls by ~20%.

#### D40: SGF Solution Tree as Refutation Ground Truth

**Decision**: Pre-computed wrong-move branches in curated SGFs (Cho Chikun, gotools, kisvadim-goproblems) serve as ground truth for refutation validation. Pipeline-generated refutations (from KataGo) are compared against these — not the reverse.

**Rationale**: Professional-curated wrong branches predate the pipeline by decades. Cho Chikun 9-dan's wrong-move annotations are authoritative. The pipeline's KataGo-generated refutations may identify different wrong moves (KataGo optimizes by policy prior, not pedagogical value), so divergence is expected and informative. Calibration tests measure recall (what fraction of SGF ground-truth wrong moves the pipeline also identifies) and precision (what fraction of pipeline refutations appear in SGF ground truth).

**Implementation**: `extract_wrong_move_branches()` in `analyzers/sgf_parser.py` walks root children and classifies each using the three-layer correctness inference system. Returns `list[dict]` with move coordinate, detection source, and comment text. Used in `test_refutation_vs_sgf_ground_truth` calibration test.

#### D41: Wrong-Branch Detection Marker Hierarchy

**Decision**: Three-layer marker detection for identifying wrong-move branches in SGF solution trees:

- **Layer 1 — SGF markers** (gold standard): `WV[]` (Wrong Variation), `BM[]` (Bad Move), `TR[]` (Triangle) → wrong; `TE[]` (Tesuji), `IT[]` (Interesting) → correct
- **Layer 2 — Comment text** (silver standard): `C[Wrong...]`, `C[Incorrect...]`, `C[-]` → wrong; `C[Correct...]`, `C[Right...]`, `C[+]` → correct
- **Layer 3 — Structural fallback**: If ≥1 sibling is explicitly correct (Layers 1-2), remaining unknowns are wrong. Else `children[0]` = correct, rest = wrong (standard SGF convention).

**Rationale**: Different SGF sources use different marking conventions:

- kisvadim-goproblems (Cho Chikun): `WV[]` + `C[Wrong.]` / `C[Correct.]`
- goproblems.com: `RIGHT`/`CHOICERIGHT` in comments
- ambak-tsumego, t-hero: `C[+]` (correct only, no wrong markers)
- gotools (generated): `WV[]` + `C[Wrong.]` / `C[Correct.]`

`WV[]` was previously only used as a writer (in gotools_ingestor) — now also detected as a reader. `C[-]` added as symmetric counterpart to `C[+]`. The three-layer system is implemented in `tools/core/sgf_correctness.py` (shared across all tools) and reused by `extract_wrong_move_branches()` in the enrichment lab parser.

#### D42: Calibration Run Persistence

**Decision**: Calibration test results persist to `tests/fixtures/calibration/results/{run_id}/` with `YYYYMMDD-{8hex}` run_id format. Each run creates a new directory (never overwrites). Directory is `.gitignored` — results are machine-specific and non-deterministic across model versions.

**Rationale**: Prior calibration runs used `pytest.tmp_path` — results were discarded after the test session. Persisting results enables:

1. Offline review without re-running KataGo (~45 min)
2. Trend tracking across model versions via `summary.json`
3. Debugging individual puzzle enrichment results

**Implementation**: The class-scoped `_setup` fixture yields (lets tests run), then copies JSON output files to the results directory after all tests complete. A `summary.json` per run captures run_id, timestamp, model paths, and per-collection metrics (acceptance rate, avg level, avg refutation count/delta/depth, zero-refutation count).

## Parked Items (Not In Scope)

### P1: Performance Scale Testing

Testing at 100, 1,000, and 10,000 file scale is deferred. The current focus is correctness of the enrichment logic. Scale testing will be addressed separately once the enricher is functionally complete and integrated.

### P2: Teaching Comments (YH) and Technique Classification

Phase B features (teaching comments, hint generation, refutation_type classification) are not part of this change. The enricher respects `enrich_if_absent` for `YH` — it will not overwrite existing hints.

### P3: YQ Quality Metrics

Quality metrics enrichment is deferred to Phase B. The enricher respects `enrich_if_partial` for existing `YQ` values.

### P4: Browser Engine Implementation

TF.js-based browser Go engine (D17, D18) is a parallel workstream. The browser engine shares model architecture with local KataGo but has independent code, constraints (< 100ms, no blocking), and integration points.

### P5: Seki and Ko Specialized Validation

Tag-aware validation dispatch (D31) with ko PV detection (D32) and seki 3-signal detection (D33) are designed but implementation is deferred to Phase P.1.3+.

## File Changes

| File                            | Change                                                               |
| ------------------------------- | -------------------------------------------------------------------- |
| `analyzers/sgf_patcher.py`      | **Deleted** — replaced by `sgf_enricher.py`                          |
| `analyzers/sgf_enricher.py`     | **New** — policy-aligned enricher with config-driven property checks |
| `analyzers/property_policy.py`  | **New** — lightweight policy reader for `tools/` boundary            |
| `cli.py`                        | Updated imports (`sgf_patcher` → `sgf_enricher`)                     |
| `scripts/run_calibration.py`    | Updated imports (`sgf_patcher` → `sgf_enricher`)                     |
| `tests/test_sgf_patcher.py`     | **Deleted** — replaced by `test_sgf_enricher.py`                     |
| `tests/test_sgf_enricher.py`    | **New** — expanded policy-aware test suite (43 tests)                |
| `config/katago-enrichment.json` | Added `level_mismatch` config section                                |

## Verification

- Existing tests updated and passing
- New policy-aware tests cover: all-props-present (skip), partial (enrich missing), malformed YX (recompute), level mismatch (overwrite), refutation branches (add when absent, skip when present)
- Sample puzzle from pipeline analyze stage verified (beginner puzzle with YX, no YR → adds branches + derives YR, preserves everything else)

> **See also**:
>
> - `config/sgf-property-policies.json` — property policy definitions
> - `config/katago-enrichment.json` — enrichment thresholds including level mismatch
> - `backend/puzzle_manager/core/property_policy.py` — pipeline's policy implementation (reference, not imported)
> - `006-implementation-plan-final.md` — overall enrichment plan
