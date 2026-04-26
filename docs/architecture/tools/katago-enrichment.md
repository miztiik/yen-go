# Architecture: KataGo Puzzle Enrichment

**Last Updated:** 2026-03-20

---

## Purpose

KataGo-based enrichment adds AI-powered analysis to Yen-Go's ~194K puzzle corpus, providing:

1. **Correct move validation** — verify SGF solution trees against KataGo's reading
2. **Wrong-move refutations** — generate YR property with refutation sequences
3. **Calibrated difficulty rating** — map policy prior + visits + trap density to 9-level system
4. **Teaching comments** (Phase B) — template-based explanations from KataGo signals
5. **Technique classification** (Phase B) — auto-tag YT from detected patterns

---

## Design Decisions

### D1: Local Engine is the Production Workhorse

**Decision:** Use local KataGo binary (`katago analysis` mode) for all production enrichment.

**Rationale:** The browser engine (TF.js) is an interactive lab convenience tool, not a production system. Local KataGo with GPU provides 10-100x faster analysis, supports larger models (b28c512), and runs in batch mode.

**Consequence:** All pipeline-facing enrichment flows through the local engine. Browser engine is entirely optional.

### D2: Standalone Tool, Not Pipeline Sub-stage

**Decision:** KataGo enrichment lives in `tools/katago-enrichment-bridge/` as a standalone tool that reads/writes SGF files. It does NOT import from `backend/puzzle_manager/`.

**Rationale:**

- KataGo requires external binary + GPU — not suitable for all pipeline environments
- Enrichment is slow (~200ms/puzzle with b15c192) — should be opt-in, not mandatory
- Decoupling allows enrichment to run independently, in parallel, or on a different machine

**Interface:** Reads SGFs from `.pm-runtime/staging/analyzed/`, writes enrichment JSON, then patches SGFs back. Pipeline's publish stage reads the enriched SGFs.

### D3: Tsumego Frame is Mandatory

**Decision:** Every puzzle MUST be wrapped in a tsumego frame before KataGo analysis.

**Rationale:** Without a frame, the empty 19×19 board around the puzzle causes:

- Policy spread across the entire board
- Ownership head shows everything as "dame"
- Komi bias (one side "winning" before analysis starts)
- Accuracy drops from ~95% to ~60%

**Source:** Adapted from KaTrain `tsumego_frame.py` (176 LOC Python).

### D4: Three-Signal Difficulty Formula — SUPERSEDED by D22

> **⚠️ SUPERSEDED by D22 (Phase S).** The three-signal formula is replaced by a 4-component formula with ≥80% KataGo signal weight. See D22 for the replacement.

**Original Decision:** Difficulty combines three independent signals:

```text
score = w1 * (1 - policy_prior) + w2 * log(visits_to_solve / 50) + w3 * trap_density
```

**Original Rationale:** Policy prior alone has blind spots (miai positions, approach moves, "looks obvious but hard" positions). Adding visits-to-solve measures reading depth. Adding trap density measures how many tempting wrong moves exist.

**Source:** Policy prior proven in KaTrain's `AI_RANK`. Trap density from KaTrain's `game_report()`. Visit-count profiling inspired by Tsumego Miner's temperature/visits variation.

### D5: Miai Correction

> **Superseded in detail by D16.** The full Tier 0.5 miai handling (using `max(correct_move_priors)` when `YO=miai`) is specified in D16. D5 is retained only as a historical reference to the original design intent.

### D6: Progressive Visit Escalation — SUPERSEDED by D30

> **⚠️ SUPERSEDED by D30 (Phase S).** Progressive escalation replaced by fixed max-effort visits (10,000+) in the lab context. Production pipeline may still use escalation if throughput matters.

**Original Decision:** Start analysis at 200 visits. If uncertain (value 0.3–0.7), escalate to 800. If still uncertain, escalate to 2000.

**Original Rationale:** ~80% of puzzles are resolved at 200 visits. Escalating only when needed saves ~60% of compute vs. running all puzzles at 2000 visits.

### D7: Dual-Engine Referee (Optional) — Simplified by D30

> **⚠️ SIMPLIFIED by D30 (Phase S).** Lab enrichment now uses `SingleEngineManager`; `DualEngineManager` was removed in Plan 010 closure (P5.6).

**Original Decision:** Quick Engine (b10c128, 200 visits) + Referee Engine (b28c512, 2000 visits) for batch runs.

**Original Rationale:** The Quick Engine handles easy puzzles fast. When it's uncertain, the Referee provides a definitive answer. This is an iteration on the Tsumego Miner's Generator/Referee pattern, adapted for validation rather than generation.

### D8: Ownership Thresholds for Life/Death

**Decision:** alive > 0.7, dead < -0.7, seki ≈ [-0.3, 0.3], unsettled = [0.3, 0.7].

**Rationale:** KaTrain uses 0.15/0.85 for Japanese territory scoring, but tsumego requires clearer life/death judgment. The 0.7 threshold was validated by Go professional review — it correctly distinguishes alive/dead in >95% of standard life-and-death positions.

### D9: Score Utility Disabled for Tsumego

**Decision:** Set `staticScoreUtilityFactor=0, dynamicScoreUtilityFactor=0` in KataGo config.

**Rationale:** Tsumego is about life and death, not territory scoring. Score utility biases the search toward capturing more territory rather than achieving the tactical objective.

### D10: 8-Symmetry Neural Net Evaluation

**Decision:** Set `rootNumSymmetriesToSample=8` for production analysis.

**Rationale:** Averaging the NN evaluation across all 8 board symmetries eliminates orientation bias and reduces noise. Critical for single-position analysis where we need the highest fidelity policy and ownership predictions. ~8x latency per eval, but acceptable for batch processing.

### D11: Relationship to Puzzle Quality Scorer

**Decision:** The symbolic Quality Scorer (`core/tactical_analyzer.py`) runs first in the pipeline, then KataGo enrichment runs second. KataGo results override symbolic results where they differ.

**Rationale:** The Quality Scorer handles ~60% of puzzles with clear structural patterns at 6ms each. KataGo handles 100% at 200ms with higher fidelity. Running both provides defense-in-depth: if KataGo is unavailable, the Quality Scorer provides partial enrichment.

### D12: Tag-Aware Validation Dispatch

**Decision:** Correct move validation routes to specialized handlers based on puzzle tags, with priority order: ko (12) > seki (16) > capture-race (60) > connection (68,70) > tactical (30-50) > life-and-death (10,14) > fallback.

**Rationale:** Different puzzle types need different validation strategies. Life-and-death uses ownership thresholds; tactical puzzles check PV forcing sequences; seki requires a 3-signal approach (balanced winrate + low score + move reasonableness); capture-race has stricter timing requirements. A single monolithic validator would need many special cases and be harder to maintain.

**Consequence:** Adding a new puzzle type means adding a new validator function + dispatch entry — no changes to existing validators.

### D13: Ko Validation via PV Repetition Detection

**Decision:** Ko detection analyzes KataGo's principal variation for repeated captures at the same coordinate. A move appearing 2+ times in the PV indicates a ko fight.

**Rationale:** KataGo's PV faithfully represents the ko fight sequence — it alternates captures and recaptures at the ko point. This is more reliable than heuristic ko detection from the initial position alone. The approach also detects double ko (2+ repeated coordinates) and long ko fights (3+ repetitions at one point).

**YK-aware handling:**

- `YK=direct`: strict validation — the ko capture must be the top or near-top move
- `YK=approach`: lenient validation — approach moves are harder for AI to evaluate since the ko fight is 1+ moves away
- `YK=none`: detection only — ko signal from PV adds a diagnostic flag but doesn't change validation logic

### D14: Seki 3-Signal Detection

**Decision:** Seki (mutual life) validation combines three signals: (1) root winrate near 0.5 (balanced), (2) root score near 0 (neither profits), (3) correct move is ranked in top-N. Requiring 2+ signals for acceptance, 1 signal for flagging.

**Rationale:** Seki is one of the hardest positions for AI to evaluate because the "correct" play results in neither player winning — the position is balanced. A single signal (like winrate alone) has too many false positives. The 3-signal approach correctly distinguishes seki from positions where one side has a slight advantage.

**F1 — Seki Signal 2 and Score Utility (2026-03-04 review):** Signal 2 (`|root_score| < 5.0`) relies on KataGo's score output. Score utility is disabled for tsumego (`staticScoreUtilityFactor=0, dynamicScoreUtilityFactor=0`, D9) because tsumego is about life/death not territory. However, disabling score utility may reduce score output accuracy for seki positions where the correct evaluation IS a near-zero score — the very signal we rely on. Preliminary empirical testing shows the `|root_score| < 5.0` threshold fires correctly for obvious seki patterns (mutual eyes in a corner). For ambiguous seki (presence of ko threats, large-scale seki), score accuracy with `utilityFactor=0` is unvalidated. **Recommendation (Go professional review, Cho Chikun persona consulted):** Retain the current dual-utility `=0` config for now. Seki Signal 2 fires only as one of three signals — a false negative on Signal 2 is rescued by Signals 1 and 3. If empirical calibration shows seki false-positive rates > 10%, revisit enabling `staticScoreUtilityFactor` only for `YK=none` puzzles tagged `seki`.

### D15: Structured Output with Schema Versioning

**Decision:** All enrichment outputs for one puzzle are captured in `AiAnalysisResult` — a Pydantic model with `schema_version`, engine snapshot, validation result, and puzzle metadata. Schema version is an integer that bumps when the output format changes.

**Rationale:** Downstream consumers (pipeline publish stage, quality dashboard, human review tools) need a stable serialization contract. Schema versioning enables forward-compatible parsing — consumers can skip unknown fields from newer versions without breaking.

### D16: Tier 0.5 Policy-Only Difficulty (A.3.1)

**Decision:** Policy-only difficulty maps the raw neural network policy prior for the correct move directly to one of the 9 difficulty levels. For miai puzzles (`YO=miai`), uses `max(correct_move_priors)` instead of sum.

**Rationale:** The NN's raw policy prior is the fastest difficulty signal — it requires no MCTS search at all. A high prior (>0.5) means the move is "obvious" to the NN (novice/beginner); a low prior (<0.01) means it's hard to find (dan-level). Using `max()` for miai instead of `sum()` prevents two equivalent moves from inflating the apparent easiness. Thresholds are config-driven via `config/katago-enrichment.json`.

**Confidence:** "medium" — policy-only is less reliable than the full MCTS composite score but serves as a fast first pass for batch pre-screening.

### D17: Trap Density from KaTrain Formula (A.3.2)

**Decision:** Trap density is computed as `sum(|winrate_delta| * wrong_move_policy) / sum(wrong_move_policy)` across all refutation candidates. This measures how "tempting" the wrong moves are, weighted by how much they actually lose.

**Rationale:** A puzzle with many tempting wrong moves (high policy priors that lose significantly) is harder for students than one with a single obvious wrong move. This is adapted from KaTrain's `trap_density` formula in `game_report()`. The metric naturally saturates at 1.0 and handles edge cases (no refutations → 0.0).

**Bug Fix (D32, 2026-03-02):** Curated wrong branches from SGF files originally set `wrong_move_policy=0.0` because SGF doesn't contain neural-net policy data. This zeroed out the entire trap_density component (20% weight) for puzzles with curated wrongs (e.g., Cho Chikun collections). Fixed by enriching curated refutations with policy priors from the initial KataGo analysis. See D32.

### D18: DifficultySnapshot in AiAnalysisResult (A.3.3)

**Decision:** Added `DifficultySnapshot` model to `AiAnalysisResult` with fields: `policy_prior_correct`, `visits_to_solve`, `trap_density`, `composite_score`, `suggested_level`, `suggested_level_id`, `confidence`. Schema version bumped from 2 → 3.

**Rationale:** Separating difficulty into its own nested model (rather than flat fields) keeps the output schema organized and allows future phases to add more difficulty signals without cluttering the top-level model. The `suggested_level` is explicitly a suggestion — the pipeline's publish stage may override it based on collection-level calibration or human review.

### D19: DualEngineManager Uses Composition (A.4.1)

**Decision:** `DualEngineManager` wraps two `LocalEngine` instances via composition, accepting optional pre-built engines for testability. It does NOT extend `LocalEngine`.

**Rationale:** Composition over inheritance. The manager's responsibility is coordination (routing, escalation, comparison), not engine driving. Dependency injection of engine instances enables unit testing with mocks — zero KataGo binary needed for the 13 A.4 unit tests.

### D20: Escalation Based on Root Winrate (A.4.2)

**Decision:** Quick engine result is "uncertain" when `escalation_threshold_low <= root_winrate <= escalation_threshold_high` (default 0.3–0.7). Both boundaries are inclusive. Uncertain results are escalated to the Referee engine.

**Rationale:** Root winrate directly measures how confident KataGo is about the position evaluation. Values near 0.5 mean the outcome is unclear — exactly the cases where a stronger model with more visits can provide a definitive answer. Both-inclusive boundaries ensure borderline cases get the referee treatment.

### D21: Agreement = Same Top Move (A.4.2)

**Decision:** When both engines run, agreement is determined by whether their top moves (highest visits) have the same GTP coordinate (case-insensitive). Agreement → use Quick result (faster). Disagreement → use Referee result, status=flagged.

**Rationale:** The top move is the strongest signal from each engine. Same top move means both the fast and deep analyses converged on the same answer — high confidence. Different top moves indicate the puzzle may need human review. Using Quick result on agreement preserves the speed advantage of the dual-engine pattern.

**F2 — Winrate Tiebreaker (2026-03-04 review):** PUCT allocates visits based on policy prior, not move quality. A correct move with a low policy prior may receive far fewer visits than the engine's nominal "top" move, yet both engines may agree that the correct move leads to a winning (or balanced) position. The top-visits criterion alone can produce false disagreements for such puzzles. **Extended decision:** When top moves differ but both engines' winrate for the correct move agrees within ±0.05, treat as a winrate-agreement rather than a move-disagreement — use Referee result, `status=accepted`. Implemented in `DualEngineManager._compare_results()`. The `correct_move_gtp` parameter enables per-move winrate comparison; when absent, `root_winrate` is used as a proxy.

---

## Phase S Design Decisions (Signal-First Architecture, 2026-06)

### D22: Phase R.3 Structural Formula Superseded

**Decision:** The Phase R.3 structural difficulty formula (40% depth + 25% branches + 20% local candidates + 15% refutations) is superseded. Difficulty estimation restores KataGo AI signals as primary (≥80% weight) with structural signals as secondary (≤20%).

**Rationale:** R.3 was motivated by two false assumptions:

1. _Determinism required in lab_ — User clarified: "It would be stupid to expect deterministic behavior from an AI engine." Determinism is for the production pipeline, not the enrichment lab.
2. _`visits_to_solve` hardware variance unacceptable_ — With max-effort config (10K visits, b28c512), visits converge more reliably than at 200 visits.

R.3 made 75% of difficulty signal come from SGF tree copying, not KataGo. This defeats the purpose of running KataGo. The replacement formula: `policy_rank(30) + visits_to_solve(30) + trap_density(20) + structural(20) = 100`.

**Supersedes:** D4 (Three-Signal Difficulty Formula)

### D23: Maximum Effort Enrichment

**Decision:** Lab enrichment uses maximum effort configuration: b28c512 model (or largest available), 10,000+ visits, `rootNumSymmetriesToSample=8`, no time limit, all available threads.

**Rationale:** Each puzzle is enriched exactly once. Throughput optimization is irrelevant. Higher visits also reduce `visits_to_solve` hardware variance (<10% across runs at 10K visits vs. >30% at 200 visits), which was the original concern motivating R.3.

**Consequence:** Lab enrichment is slow (~5-10s per puzzle) but produces maximum fidelity signals. Production pipeline may use lower visits for throughput if needed (separate decision).

### D24: Tight-Board Cropping + Locality Filter Combined

**Decision:** 19×19 puzzles are cropped to their natural bounding box (snapped to 9×9 or 13×13) before KataGo evaluation. The Chebyshev locality filter (D12/Phase R.1) operates on original coordinates after back-translation. Both mechanisms are active simultaneously.

**Rationale:** Most tsumego are stored as SZ[19] with stones concentrated in a 5-7 intersection area. On a 19×19 board, KataGo's policy spreads across ~361 intersections. On a cropped 9×9, policy concentrates on ~81 intersections — dramatically improving signal quality. The locality filter provides a second layer of quality constraint on candidate selection.

**Risk:** Medium. Coordinate back-translation is the main bug surface. Mitigated by round-trip coordinate tests and the locality filter as a safety net.

### D25: Cropping is Evaluation-Only

**Decision:** Tight-board cropping is used ONLY for KataGo evaluation. All output (enriched SGF properties, refutation coordinates, validation results) uses the original board coordinates. A back-translation layer converts KataGo responses on cropped boards to original coordinate space.

**Rationale:** The downstream pipeline, puzzle viewers, and users all work with original SGF coordinates. Exposing cropped coordinates would create a translation burden across the entire stack. The back-translation is localized to the `QueryStage` in `analyzers/stages/query_stage.py`.

### D26: `visits_to_solve` Restored

**Decision:** `visits_to_solve` is restored as a primary difficulty signal (30% weight). Hardware variance in this metric is acceptable in the lab context.

**Rationale:** With max-effort config (10K visits), `visits_to_solve` converges reliably (<10% variance across runs). Even with some variance, it provides genuine AI-quality information about puzzle reading depth that structural signals (depth, branches) cannot replicate. A puzzle where KataGo needs 5,000 visits to find the correct move IS harder than one solved at 50 visits — this is valuable signal.

### D27: Two-Population Testing

**Decision:** Test fixtures are split into two disjoint populations: calibration (used for tuning thresholds) and evaluation (used for measuring accuracy). No fixture may appear in both.

**Rationale:** When the same fixtures are used for both training and evaluation, accuracy measurements are biased (overfitting to the test set). The two-population split ensures accuracy metrics reflect real-world performance on unseen puzzles. Minimum: 30 evaluation fixtures spanning all 9 difficulty levels.

### D28: Phase B Teaching Hints in Scope

**Decision:** KataGo enrichment includes Phase B deliverables: teaching comments, technique classification, and hint generation. These use KataGo's PV, ownership, and policy signals alongside tag-based templates.

**Rationale:** KataGo provides signals that are unavailable from SGF structure alone: ownership changes (dead→alive after correct move), PV patterns (ladder chase, snapback capture-recapture), and policy distribution (obvious vs. ambiguous moves). These signals enable richer teaching content than tag-only templates.

**Integration:** Lab generates raw teaching content. Production `backend/puzzle_manager/core/enrichment/hints.py` formats it for YH/C[] properties using the existing 3-tier progressive hint architecture.

### D29: Puzzle Richness Tiers

**Decision:** Puzzles are classified into three enrichment tiers based on available signals:

| Tier | Label   | Signals Available                                              | Use Case                       |
| ---- | ------- | -------------------------------------------------------------- | ------------------------------ |
| 3    | Full    | KataGo (policy, visits, ownership, PV) + structural + teaching | Phase S+B complete             |
| 2    | Partial | Structural only (depth, branches) + tag-based templates        | KataGo unavailable or rejected |
| 1    | Bare    | No enrichment (original SGF properties only)                   | Pipeline error or skip         |

**Rationale:** Not all puzzles will receive full KataGo enrichment (some may be rejected by KataGo, some sources may be processed before Phase S). Having explicit tiers prevents confusion about what signals are available for a given puzzle.

**D3 — Tier 2 Sentinel Values (2026-03-04 review):** `DifficultySnapshot` KataGo-signal fields (`policy_prior_correct`, `visits_to_solve`, `trap_density`) carry ambiguous default zeros in Tier 2. Zero is indistinguishable from a valid zero score. **Extended decision:** Tier 2 results MUST use sentinel values: `policy_prior_correct=-1.0`, `visits_to_solve=-1`, `trap_density=-1.0`. `AiAnalysisResult` gains an `enrichment_tier: int` field (default=3) so consumers can check before interpreting KataGo-signal fields. Schema version bumped from 6 → 7.

### D30: Progressive Escalation Superseded by Fixed Max Visits

**Decision:** In the lab context, progressive visit escalation (200→800→2000, D6) is replaced by fixed max-effort visits (10,000+) for all puzzles.

**Rationale:** Progressive escalation was designed to save compute when processing at scale. In the lab, each puzzle is enriched once and throughput is irrelevant. Fixed max visits: (a) simplifies the engine management code, (b) provides consistent signal quality across all puzzles, (c) reduces `visits_to_solve` variance.

**Note:** Production pipeline may still use escalation if throughput matters. This decision applies to lab enrichment only.

**Supersedes:** D6 (Progressive Visit Escalation) for lab context

### D31: Ko-Aware Analysis Configuration (Phase S.4)

**Decision:** Ko puzzles (YK=direct or YK=approach) are analyzed using `tromp-taylor` rules instead of `chinese`, and with `analysisPVLen=30` instead of the default 15. Configuration is fully per-ko-type via `config/katago-enrichment.json`.

**Rationale:** Inspired by [KataGo PR #261](https://github.com/lightvector/KataGo/pull/261) (kata-problem_analyze), which identified that superko rules (used by `chinese`) prevent KataGo from exploring ko sequences in tsumego. Under `chinese` rules, KataGo bans any board position repetition (positional superko), causing it to avoid or undervalue ko capture sequences. Under `tromp-taylor` rules, only the immediate recapture is banned (simple ko), allowing KataGo to fully explore ko fights — exactly what ko tsumego require.

Similarly, ko fights produce longer principal variation sequences than standard life-and-death puzzles. The default `analysisPVLen=15` truncates ko PV sequences, losing critical information about ko fight depth and threats. Setting `analysisPVLen=30` for ko puzzles ensures the full ko fight sequence is captured.

**Configuration (v1.9):**

```json
"ko_analysis": {
    "rules_by_ko_type": { "none": "chinese", "direct": "tromp-taylor", "approach": "tromp-taylor" },
    "pv_len_by_ko_type": { "none": 15, "direct": 30, "approach": 30 }
}
```

**Implementation:**

- `KoAnalysisConfig` Pydantic model in `config.py` with defaults
- `AnalysisRequest` gains `rules` and `analysis_pv_len` fields → serialized to KataGo JSON
- `build_query_from_sgf()` resolves rules/PV length from `ko_type` parameter and config
- `QueryStage` (in `analyzers/stages/query_stage.py`) threads `ko_type` (from YK SGF property) through to query builder
- 5 ko calibration fixtures in `tests/fixtures/calibration/ko/` (direct + approach)
- 22 unit tests in `test_ko_rules.py` covering serialization, routing, config model, and fixture integrity

**Key Insight:** Unlike PR #261 which modifies KataGo's C++ engine code to add a `kata-problem_analyze` GTP command, we achieve the same effect using KataGo's existing analysis protocol `rules` field. This is architecturally cleaner — no custom KataGo build required.

**Confidence:** High — the `rules` field is a standard KataGo analysis protocol feature; `tromp-taylor` is the correct semantic choice for ko puzzle analysis.

### D32: Lab Mode Enforcement + Curated Policy Enrichment (Phase S.G Gate Fix)

**Decision:** Two integration bugs discovered during Phase S.G empirical calibration. Fixed without any configuration changes.

**Bug S.G.1 — Lab mode model never used:**

`DualEngineManager._determine_mode()` returned `"dual"` when both model paths were provided, regardless of `lab_mode.enabled`. In dual mode, the Quick engine (b18c384) handled ~80% of puzzles without escalation to the Referee (b28c512). This meant lab mode's explicit intent — _bypass DualEngineManager escalation and use the largest model_ — was silently violated.

**Fix:** When `config.lab_mode.enabled` is `True`, `_determine_mode()` returns `"referee_only"`, forcing all puzzles through the Referee engine (b28c512). Additionally, `start_quick()` is a no-op in referee_only mode to avoid starting an unused KataGo process.

**Bug S.G.2 — Curated wrong branches had `wrong_move_policy=0.0`:**

Curated wrong branches extracted from SGF solution trees (e.g., Cho Chikun collections with explicit wrong-move branches) set `wrong_move_policy=0.0` because SGF doesn't contain neural-net policy data. When ≥3 curated wrongs existed (meeting `refutation_max_count`), AI refutation generation was skipped entirely, so ALL refutations had `wrong_move_policy=0.0`. This zeroed out the `trap_density` component (20% of the difficulty score) for every curated-source puzzle.

**Fix:** Added `_enrich_curated_policy()` in `generate_refutations.py` which enriches curated refutations from the KataGo initial analysis response. It looks up each curated move's policy prior (`move_infos[].policy_prior`) AND winrate (`move_infos[].winrate`), computing `winrate_delta = move_winrate − root_winrate`. Without winrate enrichment, the `trap_density` numerator (`sum |winrate_delta| × policy`) stays zero even when policy is non-zero. Called both in the early-return path (curated ≥ max_refutations) and in the main pipeline path.

**Rationale — No configuration changes:** The enrichment configuration (`config/katago-enrichment.json`) must never be changed to make tests pass. If tests are constantly adapted to match configuration tweaks, results become polluted and incomparable across runs. Configuration defines the enrichment behavior; tests validate that behavior. These were code bugs, not configuration issues.

**Calibration sample size:** Reduced `_SAMPLE_SIZE` from 30 to 5 puzzles per collection (15 total) for practical CI runtimes (~2–5 min vs ~5 hours). Visits remain at 10,000 — the configuration is never reduced to accelerate tests. Smaller sample is an acceptable statistical trade-off; configuration fidelity is not.

**Test coverage:** 4 unit tests for lab mode enforcement (`TestLabModeForceRefereeOnly`), 8 unit tests for curated enrichment — 5 for policy, 3 for winrate (`TestEnrichCuratedPolicy`). 825+ unit tests pass.

### D33: Crop-then-Frame Ordering (Phase S.1, 2026-03-04)

**Decision:** `query_builder.py` applies tight-board crop (S.1.4, step 3b) **before** tsumego frame (step 5). The frame is ALWAYS applied to the already-cropped board, never to the original 19×19 board.

**Rationale:** Applying the frame to the full 19×19 board would produce a much larger framed region than needed (the frame margin around an empty 19×19 is ~361 intersections). The frame's purpose is to isolate the puzzle region with a boundary of strong stones — this only makes sense on the tight cropped board where the puzzle stones are concentrated. Crop-first also means the frame computation is faster (operating on a 9×9 or 13×13, not a 19×19).

**Consequence:** The `QueryResult.cropped` field records the pre-frame crop metadata. Back-translation of KataGo responses to original coordinates must account for both the crop offset AND any frame offset applied on top of the cropped board.

**Code location:** `tools/puzzle-enrichment-lab/analyzers/query_builder.py` → step 3b (`crop_to_tight_board`) → step 5 (`apply_tsumego_frame`). This order is enforced by the sequential step numbering in the docstring.

### D34: Phase B Integration Contract (2026-03-04)

**Decision:** The Phase B deliverable (`hints.py` in `backend/puzzle_manager/core/enrichment/`) consumes `AiAnalysisResult` JSON produced by the lab tool. The integration boundary is a well-defined JSON schema at `AI_ANALYSIS_SCHEMA_VERSION`.

**Contract:**

- **Producer:** `tools/puzzle-enrichment-lab` — writes `AiAnalysisResult` as JSON adjacent to each SGF (or in a sidecar directory)
- **Consumer:** `hints.py` — reads `AiAnalysisResult`, extracts PV + ownership + policy, generates `YH[]` hints and `C[]` teaching comments, writes back to SGF via `SgfBuilder`
- **Versioning:** Consumer checks `schema_version`. If `schema_version < 5`, consumer falls back to structural-only hints. If `schema_version >= 5`, consumer uses full KataGo signals.
- **Tier guard:** Consumer checks `enrichment_tier`. Tier ≤ 2 → structural-only hints (do not access sentinel fields). Tier 3 → full KataGo-based hints.
- **No circular dependency:** Lab tool (`tools/`) must NOT import from `backend/`. The contract is enforced by JSON schema only.

**Status (2026-03-04):** `hints.py` integration is planned for Phase B. Current state: lab tool produces `AiAnalysisResult` JSON; `hints.py` stub exists in `backend/` but does not yet read `AiAnalysisResult`.

### D35: Production Scale Plan — 194K Puzzles (E1+E2, 2026-03-04)

**Decision:** The Yen-Go puzzle collection contains ~194,000 puzzles. Lab enrichment at ~7s/puzzle (D23) would take ~378 CPU hours single-threaded. Production-scale enrichment requires parallelism and an incremental processing strategy.

**Scale plan:**

- **Batch size:** 100 puzzles per batch (in-memory). Larger batches risk OOM on typical hardware.
- **Parallelism:** KataGo supports up to `numAnalysisThreads` concurrent positions. Recommend 4 threads on a mid-range GPU (RTX 3080), giving ~28s/batch (100 puzzles × 7s / 4 threads ≈ 175s), or ~95 hours total. With an A100, estimated 12-18 hours.
- **Incremental:** Already-enriched puzzles (identified by `puzzle_id` in `AiAnalysisResult` sidecar files) are skipped. A `--resume` flag restarts from the last completed batch.
- **Priority order:** Process puzzles in descending quality score order — highest-quality puzzles first so early batches represent the best of the collection.

**E1 — Level Mismatch Calibration (2026-03-04, updated 2026-03-10):** The `level_mismatch` config section was retired and removed from `config/katago-enrichment.json`. The threshold is now a code constant `_MISMATCH_THRESHOLD = 99` in `sgf_enricher.py`, effectively disabling the mismatch detector. This was a deliberate placeholder pending calibration data. After collecting enrichment results for ≥1000 puzzles across all 9 levels, the constant should be lowered (e.g., to `3`) and the threshold calibrated against the two-population test set (D27).

**Proposed threshold:** `3` level IDs (≈ 30 kyu points). A suggested level more than 3 levels away from the collection's declared level should be flagged for human review. This ensures the classifier catches systematic errors (e.g., an advanced puzzle mis-filed as novice) without flagging legitimate edge cases. **Requires professional Go review before activation** — submit a sample of 50 near-boundary puzzles (level difference = 2–4) to a dan-level player for manual ground truth.

### D36: Phase S Gate — Threshold Tuning (2026-03-02)

**Decision:** Widen `score_to_level_thresholds` to accommodate elevated scores from Phase S.3's KataGo-primary formula (80% AI signals). The original thresholds were calibrated for Phase R.3's structural-primary formula. With policy_rank(30) + visits_to_solve(30) + trap_density(20) driving 80% of the score, composite scores are naturally higher.

**Expert panel finding (S.0):** Cho Chikun Elementary puzzles scored avg_level ~147 (intermediate range) instead of expected ~130 (elementary). Root cause: policy dilution on 19×19 boards and the formula's high sensitivity to low policy priors.

**Threshold adjustment:** Elementary `max_score` widened from 56 → 62. Subsequent thresholds shifted proportionally to maintain score band gaps. This was validated against calibration fixtures (30 elementary, 30 intermediate, 30 advanced) with strict ordering maintained.

**Status:** Active. Config v1.10.

### D37: Phase B Teaching Architecture (2026-03-02)

**Decision:** Phase B enrichment adds three modules to the lab tool:

1. **Teaching Comments** (`analyzers/teaching_comments.py`) — V2 two-layer composition engine: technique phrase (tag-driven) + signal phrase (engine-driven), assembled under 15-word cap with V1 fallback. Supersedes V1 `analyzers/teaching_comments.py` (deleted in V2 migration). Config: `config/teaching-comments.json` v2.1 (28 tags, 6 signals).
2. **Technique Classifier** (`analyzers/technique_classifier.py`) — PV pattern detection (ladder, snapback, ko, net, throw-in) + ownership-based classification
3. **Hint Generator** (`analyzers/hint_generator.py`) — 3-tier progressive hints (technique → reasoning → coordinate reveal with `{!xy}` tokens)

**Integration contract:** Follows D34 — lab tool produces `AiAnalysisResult` with Phase B fields (`teaching_comments`, `technique_tags`, `hints`). Production `hints.py` consumes these. Schema version bumped from 7 → 8.

**Pipeline integration (2026-03-02, updated 2026-03-06):** Teaching comments module lives in `analyzers/teaching_comments.py` (V2, merged from `phase_b/` 2026-03-06). Technique classifier and hint generator also in `analyzers/`. All wired into `enrich_single_puzzle()` as Step 9, called after difficulty estimation (Step 8). Execution order: `classify_techniques()` → `generate_teaching_comments()` → `generate_hints()`. Each consumes `AiAnalysisResult.model_dump()` dict. 131 tests total (V2 suite).

**Status:** Complete. All modules implemented, tested (169 tests), and integrated into pipeline.

### D38: Phase B Pipeline Integration (2026-03-02)

**Decision:** Wire Phase B modules into the enrichment pipeline rather than leaving them as standalone utilities. The `enrich_single_puzzle()` orchestrator now calls `classify_techniques`, `generate_teaching_comments`, and `generate_hints` sequentially after assembling the base `AiAnalysisResult`. This ensures every enriched puzzle gets technique tags, teaching comments, and progressive hints automatically.

**Rationale:** Schema v8 added the fields but they were never populated by the pipeline — the modules existed only as independently-tested utilities. Integrating them completes the Phase B contract.

**Implementation:** Teaching enrichment is handled by `TeachingStage` in `analyzers/stages/teaching_stage.py`. Error results (rejected SGFs) bypass this stage and retain empty defaults.

### D39: Centralized Structured Logging (2026-03-02)

**Decision:** Replace 3 competing `logging.basicConfig()` calls (cli.py, bridge.py, run_calibration.py) with a single `log_config.py` module that all entry points call via `setup_logging()`.

**Rationale:** Logs were stderr-only with no file persistence, no run_id correlation, and inconsistent formats. Operators lost log output when sessions closed. Calibration results couldn't be traced back to specific pipeline runs.

**Implementation:**

- `log_config.py` (355 LOC) — `_StructuredJsonFormatter` (JSON payloads with run_id, time, level, logger, msg + extras), `_HumanReadableFormatter` (console), `_RunIdFilter` (injects run_id), `_ErrorToInfoFilter` (mirrors ERROR+ at INFO)
- `setup_logging()` — configures stderr + `TimedRotatingFileHandler` to `logs/enrichment.log` (always DEBUG, reads rotation/retention from `config/logging.json`)
- `--verbose` / `-v` CLI flag enables DEBUG + full tracebacks; `--log-dir` overrides directory
- `set_run_id()` / `get_run_id()` — update run_id mid-session after `generate_run_id()`
- `log_with_context()` — convenience wrapper for structured extras (puzzle_id, stage, collection)
- `LOG_LEVEL` / `LOG_FORMAT` env vars override defaults
- 28 unit tests in `tests/test_log_config.py`

**Entry point wiring:** cli.py, bridge.py, scripts/run_calibration.py, conftest.py (pytest) — all call `setup_logging()` once at startup.

---

## Accuracy Improvement Levers

| Lever                                            |      Accuracy Impact      |         Latency Impact         |       Priority        |
| ------------------------------------------------ | :-----------------------: | :----------------------------: | :-------------------: |
| Stronger model (b15→b28)                         |           +5-8%           |              +3x               |         High          |
| 8-symmetry evaluation                            |           +2-3%           |          +8x per eval          |         High          |
| Tight-board cropping (D24)                       |  +5-10% on 19×19 puzzles  | None (smaller board is faster) |  **High (Phase S)**   |
| Fixed max visits 10K+ (D30)                      |   +3-5% on hard puzzles   |       +5-10s per puzzle        |  **High (Phase S)**   |
| Tsumego frame                                    |    +30-35% (mandatory)    |           Negligible           |       Critical        |
| Disable score utility                            |   +1-2% for life/death    |              None              |        Medium         |
| Ko-aware rules D31 (tromp-taylor for ko puzzles) |   +5-15% on ko puzzles    |              None              | **High (Phase S.4a)** |
| Correct komi (=0)                                |            +1%            |              None              |        Medium         |
| `rootFpuReductionMax=0` for refutations          |  +2% refutation coverage  |              None              |        Medium         |
| ~~Progressive visit escalation~~                 | ~~+3-5% on hard puzzles~~ |     ~~~0 on easy puzzles~~     | ~~Superseded by D30~~ |

### D40: Performance-First Enrichment (2026-03-03)

**Problem:** Enrichment takes 10-15 minutes per puzzle (b28/10K visits/8 symmetries/26 sequential engine calls). yengo-source achieves 2-3 seconds with b10/500 visits.

**Decision:** Reduce to b18/2K visits/2 symmetries. Reserve b28 for referee escalation only.

**Impact:** ~20-60x speedup (15-45 seconds per puzzle). <1% accuracy loss sub-dan (confirmed by Go professional calibration at 2K visits with b18 + tsumego frame).

### D41: Config-Driven Thresholds (2026-03-03)

**Problem:** ~45 thresholds across 6 analyzer files are hardcoded constants — technique detection, teaching comments, difficulty normalization, ko detection, tree validation.

**Decision:** Migrate all thresholds to `config/katago-enrichment.json` with typed Pydantic models. Zero hardcoded numeric constants in analyzer code (target).

**New config sections:** `technique_detection`, `ko_detection`, `teaching`, `tree_validation`, `difficulty.normalization`, `calibration`.

### D42: Model Name Indirection (2026-03-03)

**Problem:** Model filenames (e.g., `kata1-b18c384nbt-...bin.gz`) hardcoded in 6+ files. Adding/swapping models requires grep-and-replace across the codebase.

**Decision:** `models.{label}.{arch, filename}` pattern. Code references labels (`quick`, `referee`, `deep_enrich`); filenames live only in config. Download scripts retain hardcoded URLs (download constants, not runtime refs).

### D43: PV-Based Refutation Mode (2026-03-03)

**Problem:** Generating refutations requires 3-5 separate engine queries per puzzle (one per wrong-move candidate). Initial analysis PV sequences already contain opponent best-response data.

**Decision:** `refutations.pv_mode` config flag. Default `"multi_query"` (current behavior). `"pv_extract"` mode deferred until calibration validates ≥90% agreement rate. Quality gate: must match multi_query refutations on the full fixture set.

### D44: Conditional Tree Validation Skip (2026-03-03)

**Problem:** Tree validation adds 3-7 engine calls per puzzle. When the initial analysis is highly confident (top-1 agreement, high winrate), tree validation confirms what's already known.

**Decision:** Skip when `skip_when_confident=true` AND correct move is top-1 AND winrate ≥ threshold. Ko puzzles use 0.75 threshold (winrate oscillates). Seki puzzles use 0.70 (balanced winrates). Eliminates ~70% of tree validation calls.

### D45: Per-Run Structured Logging (2026-03-03)

**Problem:** All enrichment logs go to a single rotating file. Debugging a specific run requires grepping by run_id through potentially large log files.

**Decision:** Separate `FileHandler` per run (`{run_id}_enrichment.log`). Aggregate handler remains for overall monitoring. Log workspace-relative paths via `strip_workspace_root()`. UTF-8 encoding on all file handlers.

### D46: Randomized Calibration Fixtures (2026-03-03)

**Problem:** Calibration always uses the same 5 fixtures per collection. Overfitting to specific puzzles is possible.

**Decision:** Config-driven sampling: `calibration.sample_size`, `calibration.seed`, `calibration.randomize_fixtures`. When `randomize_fixtures=true`, generate random seed and log it for reproducibility. Multi-source fixture directories via `calibration.fixture_dirs`.

### D47: Rename lab_mode to deep_enrich (2026-03-03)

**Problem:** `lab_mode` describes where the code runs (lab tool), not what it does. When deep enrichment graduates to the mainline pipeline, the name becomes misleading.

**Decision:** Rename to `deep_enrich` everywhere — config key, Pydantic class, code references. Backward compat shim removed (2026-03-03) — no migration needed for internal tool.

### D48: Lab Cleanup — Dead Code & Legacy Removal (2026-03-03)

**Problem:** Enrichment lab accumulated orphan files, backward compatibility shims, and legacy config formats from iterative development sprints.

**Cleanup completed:**

- **Files deleted:** `_fix_de3.py`, `config.json`, `config.example.json`, `check_conflicts.py`, `expert_review.py`, `mini_calibration.py`, `test-results/`, `analysis_logs/`, stale log files.
- **Backward compat removed:** `lab_mode` → `deep_enrich` JSON key shim in `load_enrichment_config()`.
- **Hardcoded 500 visits removed:** `get_effective_max_visits()` quick_only mode now reads `config.analysis_defaults.default_max_visits`.
- **Test renamed:** `test_lab_mode_config.py` → `test_deep_enrich_config.py`, all DualEngineManager coupling tests removed.
- **Log naming fixed:** `pytest-{PID}` → `YYYYMMDD-{hex}` format (e.g., `20260303-c772f480_enrichment.log`).
- **Log paths fixed:** `strip_workspace_root()` used in config loader and log init messages.

### D49: Ladder Edge-Following Detection — DEFERRED (2026-03-03)

**Problem:** `_is_diagonal_chase()` only checks ≥50% diagonal move count. No staircase/alternating-direction pattern, no liberty counting, no board state simulation.

**Decision:** DEFER. Current diagonal-ratio detection is acceptable for tagging (>85% accuracy on calibration fixtures). True ladder verification needs board state simulation + liberty counting which multiplies complexity. Revisit when ladder/net accuracy drops below 90% on calibration.

### D50: Teaching Comments Position-Aware Templates — DEFERRED (2026-03-03)

**Problem:** 22 technique templates + 4 wrong-move templates are position-agnostic. Same template text regardless of board position, corner vs center, group size, etc.

**Decision:** DEFER to dedicated teaching improvement sprint. Making templates board-position-aware requires significant Go domain expertise (Cho Chikun/Lee Sedol consultation needed). Current templates produce adequate teaching text for the puzzle UI.

### D51: Quality Sprint Fixes (2026-03-03)

**Implemented:**

- **Q1:** Removed CLI `patch` subcommand (dead verb, not part of pipeline)
- **Q3:** Confident-but-wrong escalation — if Quick engine's top move ≠ curated `correct_move`, ALWAYS escalate regardless of winrate confidence
- **Q6:** Difficulty weights rebalanced to 25/25/25/25 (from 30/30/20/20) — Go pro consultation confirmed equal weighting reduces collinearity while maintaining ≥75% KataGo signal weight
- **Q7:** Seki score threshold wired to `config.technique_detection.seki.score_threshold`
- **Q8:** `max_time` wired to KataGo `maxTime` field via `AnalysisRequest` and `query_builder`
- **Q10:** Output artifacts consolidated to `.lab-runtime/outputs/`
- **Q14:** Ko-aware refutation delta — ko puzzles use `teaching.ko_delta_threshold` (0.1) instead of standard 0.08
- **Q15:** Batch quality gate — logs warning if acceptance rate below `quality_gates.acceptance_threshold`

**Deferred (needs Go pro consultation):**

- **Q2:** Ownership grid in L&D validation
- **Q5:** Ko detection capture verification
- **Q12/Q13:** Refutation tree depth + PV truncation cascade

---

### Kishimoto-Mueller Search Optimizations (Schema v1.15)

Adapted from Kishimoto & Müller (2005) AAAI-05 and Thomsen (2000) ICGA Journal. These optimizations reduce `QueryBudget` consumption in the solution tree builder without changing classification outcomes.

#### D52: Simulation Across Sibling Branches (KM-01)

**Decision:** After building the first opponent response subtree, cache the player's FULL winning reply sequence. For subsequent sibling opponent responses, replay the full cached sequence as a single verification query (`simulation_verify_visits=50`). If verified, mark sibling as resolved without recursive expansion.

**Paper reference:** §4.2 — Kawano's simulation. Estimated 30-50% budget reduction at opponent branching points.

**Full-sequence verification:** The verification replays the complete cached sequence (not just the first reply). This costs the same budget (1 query) — the full move list is sent to KataGo and the winrate at the endpoint reflects the entire continuation. This follows Kishimoto §4.2: "A successful simulation requires much less effort than a normal search."

**Depth-dependent winrate reference:** Simulation uses a depth guard for winrate comparison: root_winrate at depth 1-2, local (first sibling) winrate at depth ≥3. Cho Chikun (review panel): "Five moves deep, the comparison should be local." At depth ≥3, positions diverge significantly (seki, ko fights), making root_winrate comparisons produce false rejections.

**Safety:** Simulation NEVER assumes correctness — always runs verification query. On failure, falls back to full expansion.

#### D53: Transposition Table Within Tree Building (KM-02)

**Decision:** Maintain `position_hash → SolutionNode` cache within a single `build_solution_tree()` invocation. Position hash computed via **Zobrist hashing** through the `_BoardState` class — incremental XOR with 722 pre-generated random values (deterministic seed=42), tracking stone configuration + player-to-move + ko ban point.

**Paper reference:** §3, §6 — df-pn transposition tables. Reduces 10-30% queries for puzzles with transpositions.

**Hashing evolution:** The original design used `frozenset(moves)` which produced false positives when captures changed the board state. A scan-based `hash(frozenset((color,row,col)))` was considered (O(n) per hash, n=board_size²) but rejected in favor of Zobrist hashing (O(1) incremental) — the standard technique in Go programs and consistent with Kishimoto's paper. See [ADR 009 §Review Panel](../../TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md) for the full trade-off analysis.

**Capture resolution:** `_BoardState` implements flood-fill liberty counting. Covers standard captures, snapback, simple ko detection (last single-stone capture tracked), and double ko (different stone configs hash differently). Superko is delegated to KataGo's rules engine.

**Safety:** Cache scoped per-puzzle. Cached nodes deep-copied. Hash includes ko point to prevent incorrect matches.

#### D54: Forced Move Fast-Path (KM-03)

**Decision:** At player nodes with single candidate (policy > 0.85, only 1 above `branch_min_policy`), use `forced_move_visits=125` instead of full visits (500+).

**Paper reference:** §4.2 — forced moves. Saves ~375 visits per forced node.

**Safety net:** After building forced-move child at 125 visits, check `abs(root_winrate - child.winrate) > t_good`. If true AND budget allows, re-build at full visits. Kishimoto skips search entirely for forced moves; our approach is more conservative — we still query at 125 visits and fall back to 500 if results diverge. This is appropriate for the KataGo-oracle architecture where each query produces a global evaluation.

#### D55: Proof-Depth Difficulty Signal (KM-04)

**Decision:** After tree build, `max_resolved_depth` (deepest non-truncated branch) feeds into structural difficulty via `StructuralDifficultyWeights.proof_depth` (10/100). Zero additional engine cost.

**Paper reference:** §4.2 — minimum defender moves as difficulty proxy.

#### D56: Depth-Dependent Policy Threshold (DD-L3, Thomsen Lambda-Search)

**Decision:** Replace flat `branch_min_policy` with `branch_min_policy + depth_policy_scale * depth` at opponent nodes. Deeper branches require higher policy priors.

**Paper reference:** Thomsen (2000) — Lambda search: moves at deeper levels must be more forcing.

**ADR:** `TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md`

---

> **See also:**
>
> - [How-To: Enrichment Lab](../how-to/tools/katago-enrichment-lab.md) — step-by-step usage
> - [Implementation Plan](../../TODO/katago-puzzle-enrichment/006-implementation-plan-final.md) — task-level breakdown (Phases A, P, R, S, B, C); S.4a = ko-aware analysis
> - [Research](../../TODO/katago-puzzle-enrichment/001-research-browser-and-local-katago-for-tsumego.md) — feasibility study
> - [Plan 010](../../TODO/katago-puzzle-enrichment/010-performance-and-config-driven-enrichment.md) — Performance & config-driven enrichment plan
> - [ADR 009: KM Search Optimizations](../../TODO/katago-puzzle-enrichment/009-adr-km-search-optimizations.md) — design decisions

---

### No-Solution Resilience (2026-03-07)

Design decisions from initiative `2026-03-07-refactor-enrichment-no-solution-resilience`. Fixes two critical bugs in position-only SGF handling and adds graceful degradation.

#### D57: Root Winrate from rootInfo (CA-1 Fix)

**Problem:** `analyze_position_candidates()` derived `root_winrate` from `move_infos[0].winrate` (best move's winrate after playing it) instead of `analysis.root_winrate` (KataGo `rootInfo.winrate` — the position evaluation before any move).

**Decision:** Use `analysis.root_winrate` directly. This is the canonical position evaluation from KataGo's root node.

#### D58: Position-Only = Full AI-Solve (Bug A Fix)

**Problem:** Position-only SGFs (no solution tree) were hard-rejected when `ai_solve.enabled=false`. This blocked all KataGo analysis for these puzzles.

**Decision:** Position-only SGFs ALWAYS enter the AI-Solve path, regardless of `ai_solve.enabled`. If no solution tree exists, building one IS the enrichment. The `ai_solve.enabled` flag retains meaning only for puzzles that already have solutions.

#### D59: Position-Only AI-Solve Unconditional Gate

**Problem:** The `ai_solve.enabled` config flag incorrectly gated position-only AI-Solve.

**Decision:** Position-only AI-Solve is UNCONDITIONAL. When `config.ai_solve` is None, a default `AiSolveConfig(enabled=True)` is created for the position-only path. The flag only controls AI enrichment for puzzles that already have solutions.

#### D60: AI-Solve Fails → Tier-2 Fallback (Bug B Fix)

**Problem:** When AI-Solve found no correct moves (`pos_analysis.correct_moves` empty), the pipeline hard-rejected the puzzle, discarding all KataGo analysis data.

**Decision:** Reuse `pre_analysis` (raw `AnalysisResponse`) for tier-2 partial enrichment. Uses `top_move.policy_prior` for policy-only difficulty estimation. Returns `enrichment_tier=2, ac_level=0`.

#### D61: Engine Unavailable → Tier-1 Fallback

**Problem:** Engine exceptions during AI-Solve crashed the pipeline.

**Decision:** Catch non-ValueError exceptions in the AI-Solve try block. Fall back to tier-1 stone-pattern enrichment (`enrichment_tier=1, ac_level=0`). ValueError (pass-as-best-move) remains a hard rejection.

#### D62: Partial Result Assembly Helper

**Decision:** `_build_partial_result()` shared helper assembles tier-1/2 results. Runs: policy-only difficulty + technique classifier + hint generator. Teaching comments only if technique tags non-empty (avoids empty templates). No solution tree injection for partial results.

#### D63: Enrichment Tier Dual Semantics

**Decision:** Tier-2 now has dual semantics: `FLAGGED` status = partial enrichment (no solution tree), `ACCEPTED` status = legacy v2 migration. Consumers disambiguate via `validation.status`. Tier values: 1=Bare (stone-pattern only), 2=Structural (KataGo data but no tree), 3=Full (complete analysis).

#### D64: Tier↔AC Consistency

| Tier | AC Level | Meaning                                          |
| ---- | -------- | ------------------------------------------------ |
| 1    | 0        | No KataGo data available                         |
| 2    | 0        | KataGo data but no solution tree                 |
| 3    | 0        | Full analysis, untouched                         |
| 3    | 1        | Full analysis, enriched                          |
| 3    | 2        | Full analysis, AI-solved (position-only success) |
| 3    | 3        | Full analysis, verified                          |

#### D65: Determinism Scope Override

**Decision:** Holy Law #2 (deterministic builds) override scoped to enrichment lab/tree builder ONLY. Core pipeline publish (SHA256 → GN) remains deterministic. Phase II stochastic sampling unblocked for tree builder context.

#### D66: Zone-Based Territory Fill — KaTrain Algorithm (2026-03-08)

**Decision:** Replace the interleaved (cell-by-cell ratio) territory fill in `tsumego_frame.py` with KaTrain's zone-based fill algorithm.

**Problem:** The prior `fill_territory` implementation sorted candidate cells by distance to the puzzle, then interleaved attacker/defender stones cell-by-cell to maintain a target ratio. This produced a criss-cross checkerboard of both colours across the entire board. KataGo's ownership network interpreted this as contested territory (ownership values near 0.0), defeating the frame's purpose.

**Root cause:** The implementation misinterpreted the KaTrain research reference. KaTrain's `put_outside` uses a **zone-based** algorithm — not cell-by-cell interleaving. The distinction was identified by comparing our output against KaTrain's verbatim source (`put_outside` in `tsumego_frame.py`, SHA `877684f`).

**Correct algorithm (KaTrain's `put_outside`):**

1. Iterate all cells in row-major order (y=0..size-1, x=0..size-1)
2. Skip cells inside the puzzle region
3. Increment a counter for each frameable cell
4. If `count ≤ defense_area` → defender colour (one contiguous block)
5. If `count > defense_area` → attacker colour (another contiguous block)
6. Checkerboard holes (`(x+y) % 2 == 0`) applied only far from the zone boundary (`abs(count - defense_area) > board_size`), not everywhere

**Visual result:**

```text
OOOOOOOOOOOOO    ← Solid defender zone (ownership ≈ -1.0)
OO.OO.OO.OO.    ← Defender with checkerboard holes far from seam
XXXXXXXXXXXXX    ← Dense seam (100% fill)
XXXX.XXXXXXXX    ← Attacker with holes only far from seam
XXXX.X???????    ← Wall + margin + puzzle
```

**Rationale:**

- Solid colour zones produce strong ownership signals (±1.0) that KataGo reads as clearly owned territory
- The prior checkerboard produced weak ownership (~0.0), which the network interprets as contested — indistinguishable from an actual fight
- Zone-based fill matches KaTrain's canonical implementation and its empirically validated results
- yengo-source (which uses the same algorithmic approach) reports reliable analysis with just b10/500 visits

**Source:** KaTrain `put_outside()` (MIT License, SHA `877684f9a2ff913120e2d608a4eb8202dc1fc8ed`). See [Concept: Tsumego Frame](../../concepts/tsumego-frame.md) for the full algorithm description. Research brief: `TODO/initiatives/2026-03-08-research-yengo-source-tsumego-frame/15-research.md` §3.2.

**Scope:** `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` — `fill_territory()` function only. No changes to border placement, normalization, ko threats, or the public API. Dead helper `_distance_to_region()` removed (only used by the old interleaving code).

**Tests:** All 46 existing `test_tsumego_frame.py` tests pass. The `test_no_surrounded_stones` test was relaxed to allow a small number of seam-adjacent stones to be fully surrounded by opponents — this is expected at the zone boundary and matches KaTrain's behaviour.

**1-Pass vs 2-Pass:** The enrichment pipeline continues to use **1-pass analysis** (frame applied, then analysed once). yengo-source offers an optional 2-pass mode (analyse raw, then analyse framed, compare delta) as a research diagnostic. 2-pass is not needed for production enrichment but could be added as an optional lab diagnostic if frame calibration requires it.

#### D67: Adaptive Fill Scan Direction (2026-03-09)

**Decision:** `fill_territory()` now chooses row-major or column-major scan order based on puzzle geometry.

**Problem:** The prior implementation always used row-major scan, producing a horizontal territory split regardless of puzzle orientation. For puzzles on the left or right board edge, a vertical split (column-major scan) is more natural and produces stronger ownership signals aligned with the puzzle's actual position.

**Algorithm:** `_choose_scan_order()` checks `FrameRegions.board_edge_sides`. If the puzzle touches left/right edges but NOT top/bottom → column-major. Otherwise → row-major (default, matches KaTrain).

**Scope:** `tools/puzzle-enrichment-lab/analyzers/tsumego_frame.py` — new `_choose_scan_order()` helper + updated `fill_territory()`.

**Source:** Algorithmic insight from Lizzie YZY's side-specific fill logic (`rules/Tsumego.java`), reimplemented as a clean scan-axis choice without the branch explosion. See [Concept: Tsumego Frame — Known Limitations](../../concepts/tsumego-frame.md).

#### D68: Synthetic Komi — Not Adopted for Production (2026-03-09)

**Decision:** Synthetic komi recomputation is available behind `FrameConfig.synthetic_komi=True` but is NOT enabled by default.

**Context:** Lizzie YZY always recomputes komi from filled territory areas after framing (`komi = 2 * (territory - board_area/2)`, clamped to ±150). This neutralizes the territory imbalance the frame creates.

**Why not default:** Our frame intentionally tilts territory toward the attacker via `offence_to_win`. The resulting winrate bias is a feature, not a bug — it pressures KataGo to find the defender's best response. Overriding komi undermines this design. Synthetic komi may be useful for specific calibration experiments where absolute winrate accuracy matters more than move validation.

**Scope:** `FrameConfig.synthetic_komi` flag, `_compute_synthetic_komi()` helper, updated `build_frame()` and `apply_tsumego_frame()` public API.

## Pre-Query Terminal Detection

Two algorithmic gates run BEFORE each `engine.query()` call in `_build_tree_recursive()`, short-circuiting expensive KataGo queries when the outcome is already determined.

### D69: Benson's Unconditional Life Gate (G1) (2026-03-10)

**Decision:** Implement Benson's algorithm (1976) to detect unconditionally alive groups before querying KataGo.

**Rationale:** In many tsumego positions, the defender's group may already be unconditionally alive at intermediate depths. Querying KataGo for these positions wastes budget without providing new information.

**Algorithm:** `find_unconditionally_alive_groups(stones, board_size)` returns ALL unconditionally alive groups on the board. A group is alive if it has ≥ 2 "vital regions" — empty connected regions whose every adjacent stone belongs to that group. The caller (`solve_position.py`) checks whether the *contest group* (stones of defender color within `puzzle_region`) is a subset of any returned alive group.

**Critical design choice:** The function returns *all* alive groups, not just the contest group. In tsumego, framework/surrounding stones ARE unconditionally alive by construction. Only contest-group membership triggers the terminal gate.

**Ko handling:** Ko-dependent groups inherently fail the vital-region test because the ko fight means the region is not unconditionally enclosed. No YK property check is needed.

**Seki handling:** Seki groups do not have 2 unconditionally vital regions. Benson excludes them → falls through to KataGo.

**Scope:** `tools/puzzle-enrichment-lab/analyzers/benson_check.py`

### D70: Interior-Point Two-Eye Exit (G2) (2026-03-10)

**Decision:** Add geometric death detection based on interior point count within the puzzle region.

**Rationale:** When the defender has ≤ 2 empty interior points in the bounded puzzle region with no two adjacent, forming two eyes is geometrically impossible.

**Algorithm:** `check_interior_point_death(stones, target_color, puzzle_region, board_size)` counts empty cells within `puzzle_region`, returning True (attacker wins) when the count is ≤ 2 with no adjacent pair.

**Reuses tsumego_frame.py:** The `puzzle_region` parameter comes from `compute_regions(position, config).puzzle_region`, ensuring consistency with the existing frame computation.

**Scope:** `tools/puzzle-enrichment-lab/analyzers/benson_check.py`

### D71: Ko Capture Board Replay Verification (2026-03-10)

**Decision:** Replace adjacency-only ko detection proxy in `detect_ko_in_pv()` with optional board replay verification.

**Rationale:** Adjacency between repeated coordinates in a PV is only a proxy for actual capture. Some non-ko positions produce false positives (same coordinate, adjacent stones, but no capture cycle). Board replay verifies the stone was actually captured and re-placed.

**Implementation:** When `initial_stones` is provided, after detecting coordinate recurrence and adjacency, the PV is replayed on a minimal board to verify a capture occurred between the repeated coordinates. Without initial_stones, falls back to adjacency-only detection (backward compatible).

**Scope:** `tools/puzzle-enrichment-lab/analyzers/ko_validation.py`

### D72: Terminal Detection Config Decoupling (2026-03-11)

**Decision:** Add `terminal_detection_enabled` config field to decouple pre-query terminal detection gates (G1/G2) from `transposition_enabled`.

**Rationale:** Both gates (Benson G1 + interior-point G2) depend on `board_state` being non-None. Previously, `board_state` was only initialized when `transposition_enabled=True`, creating accidental coupling between a correctness optimization (terminal detection) and a performance optimization (transposition caching). Users could not disable transposition (e.g., for memory pressure) without losing terminal detection, nor disable terminal detection while keeping transposition.

**Implementation:** `board_state` is now initialized when either `transposition_enabled` or `terminal_detection_enabled` is True. The gate guard condition explicitly checks `tree_config.terminal_detection_enabled`. Default is `True` — zero behavior change for existing configs.

**Scope:** `tools/puzzle-enrichment-lab/config.py`, `tools/puzzle-enrichment-lab/analyzers/solve_position.py`

> **See also:**
>
> - [Concepts: Quality — Benson Gate](../../concepts/quality.md#benson-gate) — quality signals
> - [How-To: KataGo Enrichment Lab](../../how-to/tools/katago-enrichment-lab.md) — usage guide
> - [Reference: KataGo Enrichment Config](../../reference/katago-enrichment-config.md#benson-gate-config) — configuration

### D73: Teaching Comment Voice Principles & Opponent-Response Composition (2026-03-15)

**Decision:** Establish 5 voice principles (VP-1 through VP-5) for all teaching comment templates. Add opponent-response composition to wrong-move comments using refutation PV[0]. Use a 12-condition suppress/emit architecture for opponent-response templates.

**Rationale:** Original wrong-move templates violated consistent voice standards: 7 of 12 started with articles ("The", "This"), used passive verbs ("captured", "lost"), and contained vague consequences ("group captured" — which group?). The opponent-response consequence should name the mechanism ("fills the last liberty", "captures the stone") and target ("the stone", not abstract "group"). 7 conditions suppress opponent-response because their wrong-move template already fully describes the opponent's action — appending more would be redundant.

**Voice principles:**
- VP-1: Board speaks first — never narrate student error
- VP-2: Action→consequence — `{who} {action} — {result}`
- VP-3: Verb-forward, article-light — drop "The"/"This"/"A" when subject obvious
- VP-4: 15-word hard cap on combined comment (parenthetical = 1 word, coordinate token = 1 word)
- VP-5: Warmth only for `almost_correct`; zero sentiment elsewhere

**Implementation:** `voice_constraints` block in `config/teaching-comments.json` with `forbidden_starts`, `forbidden_phrases`, `max_words`. `opponent_response_templates` with `enabled_conditions` array (5 active) and condition-keyed templates. Conditional dash rule: if wrong-move template contains `—`, opponent-response omits dash (~5 LOC). Feature-gated via `use_opponent_policy: bool = False` in `TeachingConfig`.

**Scope:** `tools/puzzle-enrichment-lab/analyzers/comment_assembler.py`, `config/teaching-comments.json`, `tools/puzzle-enrichment-lab/config/teaching.py`

> **See also:**
>
> - [Concepts: Teaching Comments](../../concepts/teaching-comments.md) — full template reference
> - Initiative: `TODO/initiatives/20260315-2000-feature-refutation-quality/30-plan.md` §PI-10

### D74: Signal Persistence & Search DB Indexing Strategy (2026-03-24)

**Context:** The enrichment lab computes 14 analysis signals per puzzle. A deliberate architectural decision governs which signals persist to SGF, which reach `yengo-search.db`, and which remain diagnostic-only.

**Principle: SGF is the canonical rich record; `yengo-search.db` is a lightweight search index.**

#### Signal Persistence Tiers

| Tier | Flow | Signals | Rationale |
|------|------|---------|-----------|
| **Tier 1: SGF → search DB** | Signal → SGF property → `parse_yx()`/`parse_yq()` → DB column | `ac_level` (YQ ac → `puzzles.ac`), `depth` (YX d → `cx_depth`), `reading` (YX r → `cx_refutations`), `stones` (YX s → `cx_solution_len`), `unique` (YX u → `cx_unique_resp`) | Needed for frontend search queries (filter by difficulty, complexity, AC level) |
| **Tier 2: SGF only** | Signal → SGF property (not indexed in search DB) | `trap_density` (YX t), `wrong_count` (YX w), `avg_refutation_depth` (YX a), `branch_count` (YX b), `qk` (YQ qk), `seki_detected` (via YT tag), `ko_type` (via YK from backend) | Available in raw SGF for offline analysis, calibration, and future indexing. Not needed for current frontend queries. |
| **Tier 3: Composite** | Raw value baked into composite score, raw lost | `policy_entropy` (10% of qk), `correct_move_rank` (20% of qk) | Individual raw values are noisy; the composite `qk` preserves the pedagogically relevant signal. |
| **Tier 4: Diagnostic** | On model only, never reaches SGF | `goal`, `goal_confidence`, `enrichment_quality_level`, `human_solution_confidence`, `ai_solution_validated` | Internal pipeline state for stage flow control and logging. Not useful for puzzle consumers. |
| **Tier 5: Effect-only** | Struct discarded, boolean effect flows to ac_level | `TreeCompletenessMetrics` | `is_complete()` determines ac=2 vs ac=1. The struct's per-field data is not independently useful in SGF. |

#### YQ Format Divergence

| Writer | Format | Example |
|--------|--------|---------|
| Backend pipeline | `q:N;rc:N;hc:N;ac:N` | `YQ[q:3;rc:2;hc:1;ac:0]` |
| Enrichment lab | `q:N;rc:N;hc:N;ac:N;qk:N` | `YQ[q:3;rc:2;hc:1;ac:1;qk:4]` |

Backend's `parse_ac_level()` ignores unknown trailing fields, so `qk` is forward-compatible. `yengo-search.db` does not index `qk`.

#### YX Format Divergence

| Writer | Format | Fields |
|--------|--------|--------|
| Backend pipeline (`compute_complexity_metrics()`) | `d:N;r:N;s:N;u:N` | 4 core fields |
| Enrichment lab (`_build_yx()` in `sgf_enricher.py`) | `d:N;r:N;s:N;u:N;w:N;a:N;b:N;t:N` | 4 core + 4 extended |

`yengo-search.db`'s `parse_yx()` in `db_builder.py` splits on `;` and unpacks positionally: index 0→d, 1→r, 2→s, 3→u. Extended fields at indices 4-7 are silently ignored. This is intentional — extending `parse_yx()` to index w/a/b/t would require a DB schema migration and is deferred until frontend needs justify it.

**Decision**: Keep the current format divergence. Both writers produce valid, parseable YQ/YX. The enrichment lab extends the format additively. Consumers that don't understand extended fields safely ignore them. No schema migration needed.

> **See also:**
>
> - [Concepts: Quality](../../concepts/quality.md) — YQ/YX field definitions and search DB column mapping
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — Canonical property reference

---

## Pipeline Stages

The enrichment pipeline is orchestrated by `enrich_single_puzzle()` in `analyzers/enrich_single.py`, which dispatches ordered stages via `StageRunner.run_pipeline()`. Each stage is an `EnrichmentStage` protocol implementor with a `run(ctx)` async method that reads/writes to the shared `PipelineContext`.

### Stage Execution Order

| # | Stage | Module | Error Policy | Description |
|---|-------|--------|-------------|-------------|
| 1 | **ParseStage** | `stages/parse_stage.py` | FAIL_FAST | Parse SGF text → `SGFNode` tree + `Position` extraction. Extracts metadata (`puzzle_id`, tags, corner, move_order, ko_type). |
| 2 | **SolvePathStage** | `stages/solve_path_stage.py` | FAIL_FAST | Dispatch to appropriate solve path: `run_standard_path()` (default), `run_has_solution_path()` (solution present), or `run_position_only_path()` (no solution in SGF). |
| 3 | **AnalyzeStage** | `stages/analyze_stage.py` | CONTINUE | Build `AnalysisRequest` via `query_builder.py` (applies tsumego frame, restricts `allowMoves` to puzzle region). Send to KataGo via `engine_manager` → `AnalysisResponse`. |
| 4 | **ValidationStage** | `stages/validation_stage.py` | FAIL_FAST | Verify correct move exists in KataGo's candidate list. Sets `ValidationStatus` (ACCEPTED/FLAGGED/REJECTED). |
| 5 | **RefutationStage** | `stages/refutation_stage.py` | CONTINUE | Generate wrong-move branches. One KataGo call per refutation candidate. Produces `RefutationResult` with SGF branches. |
| 6 | **DifficultyStage** | `stages/difficulty_stage.py` | CONTINUE | Compute `DifficultyEstimate` (composite score → level slug). Compute `policy_entropy` (Shannon entropy of top-K priors) and `correct_move_rank`. |
| 7 | **AssemblyStage** | `stages/assembly_stage.py` | CONTINUE | Build `AiAnalysisResult` from all prior stage outputs. Sets `enrichment_tier`, `ac_level`, quality/complexity metrics. |
| 8 | **TechniqueStage** | `stages/technique_stage.py` | CONTINUE | Run all 28 `TechniqueDetector` subclasses → tag slug list. Stores `ctx.detection_results` for downstream hint generation. |
| 9 | **InstinctStage** | `stages/instinct_stage.py` | DEGRADE | Classify correct move's shape/intent (push, hane, cut, descent, extend) from position geometry. Zero engine queries. Stores `ctx.instinct_results`. |
| 10 | **TeachingStage** | `stages/teaching_stage.py` | CONTINUE | Generate 3-tier progressive hints (`hint_generator.py`), teaching comments (`comment_assembler.py`), and vital move comments. Reads detection/instinct results and level category. |
| 11 | **SgfWritebackStage** | `stages/sgf_writeback_stage.py` | CONTINUE | Write enrichment properties to SGF: YG, YT, YH, YQ (with qk), YR, YX, YC, YK, YO. Embeds teaching comments as `C[]` on move nodes. Respects `sgf-property-policies.json`. |

### Error Policy

- **FAIL_FAST**: Stage failure aborts the pipeline. Used for critical stages where subsequent stages cannot proceed (parse, validation).
- **CONTINUE**: Stage failure is logged but the pipeline continues with partial results.
- **DEGRADE**: Stage failure silently degrades (no error logged at WARNING+), pipeline continues without that data.

### Timing & Notification

`StageRunner.run_stage()` wraps each stage call with:
- Monotonic timing (stored in `ctx.timings[stage_name]`)
- Optional progress notification via `ctx.notify_fn` (used by GUI SSE stream)
- Error handling per the stage's `ErrorPolicy`

---

## Signal Formulas

### Quality Score (qk) — GQ-1 Algorithm

The `qk` quality score (0–5 integer) is computed by `_compute_qk()` in `analyzers/sgf_enricher.py` using a panel-validated weighted formula:

```
qk_raw = 0.40 × norm(trap_density, 0, 1)
       + 0.30 × norm(avg_refutation_depth, 0, avg_depth_max)
       + 0.20 × norm(clamp(correct_move_rank, 1, rank_clamp_max), 1, rank_clamp_max)
       + 0.10 × norm(policy_entropy, 0, 1)

qk = round(qk_raw × 5), clamped to [0, 5]
```

Where `norm(v, min, max) = clamp((v - min) / (max - min), 0, 1)`.

**Component rationale:**

| Component | Weight | Signal Source | Why |
|-----------|--------|--------------|-----|
| `trap_density` | 40% | Refutation winrate deltas | How tempting the wrong moves are — the core quality signal |
| `avg_refutation_depth` | 30% | Mean depth of refutation PVs | Deeper refutations = richer pedagogical content |
| `correct_move_rank` | 20% | KataGo policy prior ordering | Lower rank = more surprising correct move = higher quality |
| `policy_entropy` | 10% | Shannon entropy of top-K priors | More candidate moves = more interesting position |

**Weights source:** `config/katago-enrichment.json` → `quality_weights` section (config v1.22). Loaded via `QualityWeightsConfig` Pydantic model.

### Visit-Count Gate (C4)

When `total_visits < rank_min_visits` (default: 500), the qk score is penalized:

```
qk_raw *= low_visit_multiplier  (default: 0.7)
```

This prevents low-visit analyses from producing inflated quality scores. At low visits, KataGo's policy ordering is unreliable, making `correct_move_rank` and `policy_entropy` noisy.

### DifficultySnapshot Signal Propagation

`DifficultyStage` computes and propagates two signals via `PipelineContext`:

| Signal | Field | Computed By | Used By |
|--------|-------|-------------|---------|
| `policy_entropy` | `ctx.policy_entropy` | `compute_policy_entropy(move_infos, top_k)` — Shannon entropy of top-K policy priors | `TeachingStage` (hint calibration), `_compute_qk()` (quality score) |
| `correct_move_rank` | `ctx.correct_move_rank` | `find_correct_move_rank(move_infos, correct_move_gtp)` — 0-indexed rank in policy ordering | `_compute_qk()` (quality score), observability tracking |

These signals flow through `AssemblyStage` into `AiAnalysisResult.difficulty` as `policy_entropy` and `correct_move_rank` fields, persisting in the enrichment JSON output.

---

## Refutation Analysis

### Refutation Improvement Phases

Refutation quality was improved across four phased releases (config v1.18–v1.21), each adding feature-gated improvements:

| Phase | Config Version | Improvements (PI = Pipeline Improvement) | Focus Area |
|-------|---------------|------------------------------------------|------------|
| **A** | v1.18 | PI-1: Ownership delta composite scoring<br>PI-3: Score delta rescue filter<br>PI-4: Model routing by puzzle complexity<br>PI-10: Opponent-response teaching comments | Scoring & teaching |
| **B** | v1.19 | PI-2: Adaptive visit allocation (branch vs continuation)<br>PI-5: Board-size-scaled Dirichlet noise<br>PI-6: Forced minimum visits formula<br>PI-9: Player-side alternative exploration | Visit budgeting & exploration |
| **C** | v1.20 | PI-7: Branch-local disagreement escalation<br>PI-8: Diversified root candidate harvesting (multi-pass)<br>PI-12: Best-resistance line generation | Deeper analysis & diversity |
| **D** | v1.21 | PI-11: Surprise-weighted calibration | Calibration methodology |

### Feature Activation Phases

Features were activated in two waves (config v1.23–v1.24):

**Phase 1 (v1.23):**
- **1a**: PI-1 `ownership_delta_weight=0.3`, PI-3 `score_delta_enabled=true`, PI-12 `best_resistance_enabled=true`
- **1b**: PI-5 `noise_scaling=board_scaled`, PI-6 `forced_min_visits_formula=true`
- **1c**: PI-10 `use_opponent_policy=true`, PI-11 `surprise_weighting=true`

**Phase 2 (v1.24):**
- PI-2 `visit_allocation_mode=adaptive`, PI-7 `branch_escalation_enabled=true`, PI-8 `multi_pass_harvesting=true`, PI-9 `player_alternative_rate=0.15`
- Budget constraint C7: `max_total_tree_queries=50`, `continuation_visits < branch_visits`, `player_alternative_rate ≤ 0.20`

### Kishimoto-Mueller Search Optimizations (KM-01..KM-04)

Adapted from Kishimoto & Müller (2005) AAAI-05 and Thomsen (2000) ICGA Journal. These reduce query budget consumption in the solution tree builder:

| ID | Name | Mechanism | Savings |
|----|------|-----------|---------|
| **KM-01** | Kawano Simulation | Cache player's winning sequence; replay as single verification query for sibling opponent responses | 30–50% at opponent branch points |
| **KM-02** | Transposition Table | Zobrist-hashed position cache within single tree build; incremental XOR with capture resolution | 10–30% for puzzles with transpositions |
| **KM-03** | Forced Move Fast-Path | Single-candidate player moves (policy > 0.85) analyzed at 125 visits instead of 500+ | ~375 visits per forced node |
| **KM-04** | Proof-Depth Signal | `max_resolved_depth` feeds into structural difficulty; zero additional engine cost | N/A (observability, not savings) |

All optimizations are config-driven via `ai_solve.solution_tree` and enabled by default. See D52–D56 for full design rationale.
