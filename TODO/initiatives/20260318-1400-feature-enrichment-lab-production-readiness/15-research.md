# Research — Enrichment Lab Production Readiness: Gap Synthesis

**Initiative**: `20260318-1400-feature-enrichment-lab-production-readiness`
**Last Updated**: 2026-03-18
**Planning Confidence Score**: 75 (medium risk)
**Research status**: Synthesis of 15+ existing research artifacts, 65+ initiative folders, and codebase audit

---

## 1. Research Question

What accretive features/fixes remain between the current enrichment lab state and production-readiness, considering:
- Removed "No Browser AI" constraint
- Extensive prior research (gogogo patterns, KM search optimizations, capability audit)
- Deferred NG items from gogogo research panel
- Incomplete initiatives (data liberation, hinting unification, calibration)

---

## 2. Current Implementation State Summary

### Fully Implemented (Production-Grade)

| Area | Evidence | Test Count |
|------|----------|------------|
| 28 technique detectors | `analyzers/detectors/*.py` | 100+ |
| KataGo solve pipeline (position-only + has-solution) | `solve_position.py`, `enrich_single.py` | 220+ |
| Multi-root tree building (A/B/C priority) | `enrich_single.py` Sprint 2 | 150+ |
| Kishimoto-Mueller optimizations (KM-01 to KM-04 + L3) | `solve_position.py` Phases 3-7 | 80+ |
| Refutation quality (4 phases, 12 PI items) | `generate_refutations.py`, `solve_position.py` | 127+ |
| Instinct classifier (5 instincts: push/hane/cut/descent/extend) | `instinct_classifier.py` | 35+ |
| Policy entropy + correct_move_rank computation | `estimate_difficulty.py` | 20+ |
| Multi-orientation test infrastructure | `Position.rotate()`, `Position.reflect()` | 55 |
| Level-adaptive hint content (entry/core/strong) | `hint_generator.py` | 20+ |
| Teaching comment assembly (15-word cap, opponent response) | `comment_assembler.py` | 40+ |
| Config decomposition (9 sub-modules) | `config/` package | 30+ |
| Stage runner pipeline (12 stages) | `analyzers/stages/*.py` | 50+ |
| Benson unconditional life check | `benson_check.py` | 10+ |
| Observability (BatchSummary, DisagreementSink) | `observability.py` | 20+ |
| Bridge/GUI (FastAPI + SSE + config overrides) | `bridge.py`, `bridge_config_utils.py` | 11 |
| **Total enrichment lab tests** | | **~550+** |

### Implemented But Gated/Disabled

| Feature | Gate | Reason |
|---------|------|--------|
| Instinct classifier | `instinct_enabled=False` | Awaiting golden set calibration (AC-4: ≥70% accuracy) |
| Surprise-weighted calibration (PI-11) | `surprise_weighting=False` | Awaiting activation study |
| Branch escalation (PI-7) | `branch_escalation_enabled=False` | Awaiting compute tracking RC |
| Multi-pass harvesting (PI-8) | `multi_pass_harvesting=False` | Awaiting composite re-ranking RC |
| Best resistance (PI-12) | `best_resistance_enabled=False` | Awaiting activation RC |
| Model routing by level (PI-4) | `model_by_category={}` | Awaiting multi-model setup |
| Adaptive visit allocation (PI-2) | `visit_allocation_mode="fixed"` | Awaiting benchmark |
| Board-scaled noise (PI-5) | `noise_scaling="fixed"` | Awaiting benchmark |
| Forced min visits formula (PI-6) | `forced_min_visits_formula=""` | Awaiting benchmark |
| Player alternatives (PI-9) | `player_alternative_rate=0.0` | Awaiting benchmark |

### NOT Implemented — Deferred Research Items (NG Table)

| NG-ID | Finding | Status | Verdict |
|-------|---------|--------|---------|
| NG-1 | Priority/urgency scoring on DetectionResult | Not implemented. Only static `TAG_PRIORITY` ordering. | **Low value now** — existing tag priority works for hints. Worth revisiting after data liberation shows where priority matters. |
| NG-2 | Static life/death evaluation formula | Partially implemented: Benson gates + interior-point death in `benson_check.py`. No full minimax evaluator. | **Adequate as-is** — full symbolic evaluator (gogogo-style minimax) is redundant with KataGo ownership analysis. Benson check handles the unconditional case. |
| NG-3 | Multi-tag evidence layering / feature planes | Not implemented. 28 detectors run independently; no fusion layer. | **Defer** — requires training data or confidence calibration. No immediate production need. |
| NG-4 | New tags in config/tags.json | Not implemented. 28 canonical tags. | **Defer** — Level 5 change, taxonomy expansion not justified by current content scale. |
| NG-5 | Alpha-beta capture search engine | Not implemented. All analysis is KataGo-based. | **Reject** — KataGo is superior; PNS research (`20260310-research-tsumego-solver-pns`) is the better direction for symbolic search. |

### Critical Gaps — Production Blockers

| Gap-ID | Gap | Impact | Source |
|--------|-----|--------|--------|
| GAP-1 | **Data Liberation**: 10+ computed signals discarded before DB-1 | Frontend cannot sort/filter by reading depth, trap density, entropy, etc. `puzzles.attrs` column is universally empty. | `15-research-enrichment-lab-accretion.md` (R-2 through R-14) |
| GAP-2 | **Calibration**: Golden set has 0 labeled puzzles | Instinct classifier (disabled), entropy correlation, threshold validation (S5-G18) all blocked. No empirical validation of difficulty accuracy. | `ai-solve-remediation-sprints.md` S5-G18, tactical-hints AC-2/AC-4 |
| GAP-3 | **Hinting Unification**: Two separate hint systems (lab + backend pipeline) | Drift risk between lab hints and pipeline hints. No shared contract. Transition plan v1 written but Phase 1 not started. | `hinting-unification-transition-plan-v1.md` |
| GAP-4 | **Documentation**: 4 docs from S5-G19 never created | `docs/concepts/quality.md`, `docs/architecture/tools/katago-enrichment.md`, `docs/how-to/backend/enrichment-lab.md`, `docs/reference/enrichment-config.md` | `ai-solve-remediation-sprints.md` S5-G19 |
| GAP-5 | **Feature Activation**: 10 features gated/disabled awaiting benchmarks | Full refutation quality pipeline, instinct, adaptive visits, model routing all disabled. | Refutation quality Phase A-D validation reports |
| GAP-6 | **Review Panel Sign-Off**: Multiple gate reviews pending across completed sprints | KM tasks (T017a, T027a, T039a, T048a, T058a, T063a), remediation sprints (all review sign-offs), refutation quality phase activation RCs | Multiple task docs |

### In-Progress Initiatives (Started, Not Complete)

| Initiative | Phase | Missing |
|------------|-------|---------|
| `20260317-1400-feature-enrichment-data-liberation` | Clarify (14 questions pending) | User needs to answer Q1-Q14 |
| `20260315-research-gogogo-tactics-patterns` | Research-review (GOV-CHARTER-REVISE, RC-1/RC-2) | Governance blocking items |
| `hinting-unification-transition-plan-v1` | Draft | Zero phases executed |

---

## 3. NG Items Deep Analysis

### NG-1: Priority/Urgency Scoring — LOW VALUE NOW

Current state: `TAG_PRIORITY` in `config_lookup.py` provides static hint ordering. DetectionResult has `confidence: float` but no `priority/urgency` field. Instinct classifier has empirically-validated priority weights from gogogo research (R-E5b: hane_vs_tsuke=+13.2%, extend_from_atari=+9.7%, etc.).

**Assessment**: The instinct classifier already captures move urgency for the 5 tsumego-relevant instincts. Adding a `priority` field to DetectionResult would help multi-detector scenarios but the current static ordering works. Value is mostly post-data-liberation when frontend needs richer sorting dimensions.

### NG-2: Static Life/Death Evaluation — ADEQUATE

Current state: `benson_check.py` implements Benson's algorithm for unconditional life detection. Interior-point death detection also present. No full minimax evaluator (gogogo-style `evaluate_life_death()` with eye counting + liberty heuristic).

**Assessment**: KataGo ownership + winrate analysis is far more accurate than any symbolic evaluator for the puzzles we process. Benson check handles the unconditional case (which is deterministic). Adding a symbolic evaluator would create a second opinion source that's strictly inferior to KataGo. Only value would be as a fast pre-filter for trivial positions — but the pipeline already handles this via policy prior analysis.

### NG-3: Multi-Tag Evidence Layering — PREMATURE

Current state: 28 detectors produce independent `Detection` results. `technique_classifier.py` aggregates but doesn't fuse evidence across detectors. No "if A is detected with confidence X AND B with confidence Y, then infer C" logic.

**Assessment**: Evidence layering requires either (a) training data on detector co-occurrence patterns, or (b) expert-authored rules. Neither exists. The 28 detectors have good precision today. Multi-tag layering is a research project, not a production feature. Defer until we have 10K+ enriched puzzles with ground truth.

### NG-5: Alpha-Beta Capture Search — REJECT

Current state: All tactical analysis uses KataGo via engine queries. No minimax or alpha-beta.

**Assessment**: PNS (Proof-Number Search) research (`20260310-research-tsumego-solver-pns`) is the correct symbolic search direction. Alpha-beta is inferior for Go life-and-death. KataGo + KM optimizations already provide excellent tactical analysis. Adding a parallel search engine creates maintenance burden with no clear user value.

---

## 4. Highest-Value Accretive Actions (Ranked)

| Rank | Action | Value | Effort | Dependencies |
|------|--------|-------|--------|-------------|
| 1 | **Data Liberation** — persist 6-7 signals to `attrs` JSON, wire through publish → DB-1 → frontend | CRITICAL — unlocks frontend sorting/filtering | Medium (3-4 files) | Needs Q1-Q14 answered |
| 2 | **Golden Set Creation + Calibration Run** — label 50-100 puzzles, run calibration | HIGH — unblocks instinct activation, entropy calibration, threshold validation | Low (labeling + test run) | KataGo engine access |
| 3 | **Feature Activation** — enable 3-4 proven-safe features (PI-11, instinct, adaptive visits) after calibration | HIGH — moves enrichment from "built" to "active" | Low (config changes + benchmark test) | Calibration (rank 2) |
| 4 | **Documentation Closure (S5-G19)** — create 4 missing docs | MEDIUM — enables external contributors, reduces bus factor | Low (doc writing) | None |
| 5 | **Hinting Unification Phase 1** — drift inventory | MEDIUM — prevents divergence before production | Medium | None |

---

## 5. "No Browser AI" Constraint Removal — Impact Assessment

The removal opens three doors:
1. **Pipeline-side LLM for teaching comments** — generate richer explanations than template-based assembly (initiative `20260317-1400`)
2. **Browser-side tiny LLM for personalized hints** — adapt hint difficulty/style to user level at runtime (initiative `20260317-research-browser-tiny-llm`)
3. **NG-3 revisited** — multi-tag evidence layering could use a small classifier model instead of expert rules

**Current assessment**: The data liberation pipeline must ship first (rank 1) to provide structured signals that any LLM/personalization feature would consume. Browser AI features are build-on-top, not foundational.
