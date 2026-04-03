# Charter — Enrichment Lab Production Readiness

> Initiative: `20260318-1400-feature-enrichment-lab-production-readiness`
> Last Updated: 2026-03-18
> Supersedes: `20260317-1400-feature-enrichment-data-liberation`, `20260318-1200-feature-enrichment-lab-production-gap-closure`

---

## Goals

| goal_id | goal | success_criteria |
|---------|------|------------------|
| G1 | **Feature activation**: Enable all 16 gated features in phased sequence (Phase 0→1a→1b→1c→2→3) | All features activated with tests passing per phase gate conditions |
| G2 | **Signal wiring**: Extend YX property with `a:`, `b:`, `t:` fields; add `qk:` sub-field to YQ | `_build_yx()` outputs all 8 fields; `_build_yq()` outputs `qk:0-5` from panel-validated algorithm |
| G3 | **Quality algorithm**: Implement panel-validated `qk` formula (trap 40%, depth 30%, rank 20%, entropy 10%) | `qk` scores computed for all enriched puzzles; weights config-driven in `config/katago-enrichment.json` |
| G4 | **Hinting consolidation**: Copy backend `hints.py` safety features into lab; mark backend hints as superseded | Lab `hint_generator.py` includes atari relevance gating, depth-gated Tier 3, solution-aware fallback, structured logging |
| G5 | **Observability closure**: Complete propagation of `correct_move_rank` and `policy_entropy` through result + batch accumulator (OPP-1) | Signals traceable from stage context to `AiAnalysisResult` to `BatchSummary` |
| G6 | **Test coverage expansion**: Expand rotation tests to ≥12 detector families (OPP-2) | Multi-orientation test harness covers ≥12 of 28 detector families |
| G7 | **Debug artifact export**: Add non-invasive trap/detection debug artifact — top trap move + detector activation matrix (OPP-3) | Debug export callable via CLI flag or bridge endpoint |
| G8 | **Calibration baseline**: Run calibration on 95 Cho Chikun fixtures with non-circular labeling methodology | Calibration results for `qk` weights, threshold sensitivity, and instinct accuracy |
| G9 | **Comprehensive enrichment documentation**: Expand `docs/architecture/tools/katago-enrichment.md` into comprehensive one-stop-shop reference covering pipeline stages, signal formulas in plain English, hinting, decisions log, future work. Update existing concept/reference docs with enrichment content. Follow three-tier pattern (≤3 levels). | Architecture doc expanded; concept docs updated; config reference consolidated; English explanations for all mathematical formulas; decisions/future-work captured |
| G10 | **Per-puzzle structured diagnostics**: Each enrichment run produces a structured JSON diagnostic per puzzle capturing: what stages ran, what signals were computed, goal_agreement, disagreements, errors, timings, qk score. Batch-level summary aggregates per-puzzle records. | Per-puzzle diagnostic JSON produced for every puzzle in enrichment run; scoopable via structured log/state files |
| G11 | **TODO cleanup + archive**: After initiative completion, consolidate all enrichment-lab-related initiatives in `TODO/initiatives/` to `docs/archive/initiatives/enrichment-lab/`. Preserve all deferred/future items in documentation so research is not lost. | All completed/superseded enrichment-lab initiatives archived; future work items listed in enrichment docs |

## Non-Goals

| ng_id | non_goal | rationale |
|-------|----------|-----------|
| NG-1 | "No Browser AI" constraint removal | Out of scope; already removed at project level but this initiative does not add browser-side AI |
| NG-2 | Small model for natural language hint generation | Parked as future work; requires signals from this initiative to be useful |
| NG-3 | Re-enrichment of published 2,000 puzzles | User's responsibility; this initiative builds the tooling |
| NG-4 | Pipeline DB mapping (DB-1 `attrs` column) | Lab enriches SGF only; pipeline's publish stage decides what goes into DB-1 |
| NG-5 | Taxonomy expansion (new tags in config/tags.json) | Level 5 change; not justified by current content scale |
| NG-6 | Full hinting unification (backend pipeline interface swap) | This initiative copies backend wins INTO the lab and marks backend as superseded. Actual pipeline interface swap is a follow-on when user authorizes backend changes. |
| NG-7 | NG-1 priority/urgency scoring on DetectionResult | Deferred; static TAG_PRIORITY + instinct classifier is adequate |
| NG-8 | NG-3 multi-tag evidence layering | Deferred; requires training data that doesn't exist |
| NG-9 | NG-5 alpha-beta capture search | Rejected; KataGo + KM optimizations are superior |
| NG-10 | Goal (`g:`) field in YX property | Redundant with YT tags + root comment puzzle intent (GQ-2 panel consensus) |

## Constraints

| constraint_id | constraint |
|---------------|------------|
| C1 | **Scope boundary**: ALL code changes stay inside `tools/puzzle-enrichment-lab/` unless explicitly authorized |
| C2 | **No backward compatibility required**; remove unused code after showing user which code |
| C3 | **Config-driven weights**: `qk` quality weights stored in `config/katago-enrichment.json` under `quality_weights` key. No hardcoded constants. |
| C4 | **Visit-count gate**: `correct_move_rank` is unreliable below 500 visits. `qk` formula must degrade gracefully (`qk_raw *= 0.7` when `total_visits < rank_min_visits`). Gate threshold is config: `rank_min_visits: 500`. |
| C5 | **Non-circular calibration**: Golden set labels use Cho Chikun published answer keys as correct-move identity + human expert classification (Method C+A hybrid). Lab MUST NOT use KataGo delta thresholds to generate calibration labels. |
| C6 | **Phased activation**: Features activate in governance-validated phase sequence (Phase 0→1a→1b→1c→2→3). No feature activates without its explicit gate condition met. |
| C7 | **Budget ceiling for Phase 2**: Worst-case query budget per puzzle must be documented before PI-2+PI-7+PI-8+PI-9 activation. Ceiling: ≤4x current budget (≤200 effective queries). |
| C8 | **Player-visible impact per phase**: Each phase must identify which player-visible output changes |
| C9 | **Threshold conservation**: Keep `t_good=0.05, t_bad=0.15, t_hotspot=0.30` until non-circular calibration evidence justifies tightening |
| C10 | **Goal comparison, not storage**: Implement `goal_agreement` as internal diagnostic in `DisagreementSink`/`BatchSummary`. Do NOT store `g:` in SGF. |
| C11 | **Definition of done**: Code + tests + config fully wired. No mock-only closure. |

## Acceptance Criteria

| ac_id | criterion | verification |
|-------|-----------|-------------|
| AC-1 | YX property outputs `d:;r:;s:;u:;w:;a:;b:;t:` (8 fields) for all enriched puzzles | Unit test on `_build_yx()` with all fields populated |
| AC-2 | YQ property outputs `q:;rc:;hc:;ac:;qk:` (5 fields) with `qk` computed from panel algorithm | Unit test on `_build_yq()` with qk calculation |
| AC-3 | `qk` weights are loaded from `config/katago-enrichment.json` `quality_weights` section | Config parsing test; no hardcoded weights in source |
| AC-4 | Visit-count gate: `qk` degrades when `total_visits < rank_min_visits` (default 500) | Unit test with low-visit and high-visit scenarios |
| AC-5 | All 16 feature gates activate successfully per phase gate conditions | Integration test per phase confirming enable/disable |
| AC-6 | Lab hint generator includes: atari relevance gating, depth-gated Tier 3, solution-aware fallback, structured logging (from backend), PLUS level-adaptive wording, detection evidence Tier 2, instinct phrases (from lab) | Unit tests for each ported capability |
| AC-7 | `policy_entropy` and `correct_move_rank` propagate from stage context → `AiAnalysisResult` → `BatchSummary` (OPP-1) | Integration test tracing signal end-to-end |
| AC-8 | Multi-orientation tests cover ≥12 of 28 detector families (OPP-2) | Test count per detector family in CI report |
| AC-9 | Trap/detection debug artifact exportable via CLI flag (OPP-3) | CLI test with `--debug-export` flag producing diagnostic JSON |
| AC-10 | Calibration run on 95 Cho Chikun fixtures produces `qk` distribution + instinct accuracy | Calibration script execution with results in `.lab-runtime/calibration-results/` |
| AC-11 | Player validation: 20+ puzzles per `qk` tier (1-5) reviewed by 5k-1d player confirm quality perception | Validation report with player feedback |
| AC-12 | 4 enrichment docs updated with enrichment content and cross-references | Doc files updated at specified paths with "See also" sections |
| AC-13 | `goal_agreement` diagnostic implemented in `DisagreementSink` and tracked in `BatchSummary` | Unit test on mismatch detection; batch summary includes mismatch rate |
| AC-14 | Backend `hints.py` marked as superseded in this initiative's docs; lab is canonical hint source for enriched puzzles | Documentation states supersession; lab hint tests cover all backend test scenarios |
| AC-15 | Per-puzzle enrichment diagnostic is a structured JSON object capturing: stages run, signals computed, goal_agreement, qk score, errors, timings | Unit test on diagnostic model; integration test on batch run producing per-puzzle diagnostics |
| AC-16 | Batch diagnostic summary aggregates per-puzzle records into queryable state | Batch run produces `.lab-runtime/diagnostics/{run_id}/` with per-puzzle JSON + batch summary |
| AC-17 | `docs/architecture/tools/katago-enrichment.md` expanded to cover: pipeline stages, signal formulas (English + math), quality algorithm, refutation analysis, decisions log, future work. Existing concept docs updated. Config reference consolidated. | Architecture doc ≥500 lines; every formula has English explanation; concept docs updated |
| AC-18 | All enrichment-lab TODO initiatives (≥15) archived; future work items preserved in docs | `docs/archive/initiatives/enrichment-lab/` contains archived initiatives; future work section in architecture doc lists all deferred items |

## Quality Algorithm (Panel-Validated)

### `qk` Formula

```
qk_raw = (
    0.40 * normalize(trap_density, 0.0, 1.0)
  + 0.30 * normalize(avg_refutation_depth, 0, 10)
  + 0.20 * normalize(clamp(correct_move_rank, 1, 8), 1, 8)
  + 0.10 * normalize(policy_entropy, 0.0, 1.0)
)

if total_visits < rank_min_visits:
    qk_raw *= 0.7    # degrade confidence for low-visit signals

qk = clamp(round(qk_raw * 5), 0, 5)
```

### Weight Rationale (7-member panel consensus)

| Weight | Signal | Professional Reasoning |
|--------|--------|----------------------|
| 40% | `trap_density` | "Most important quality signal" (Ke Jie). Tempting wrong moves = well-constructed puzzle. |
| 30% | `avg_refutation_depth` | "How deep must you read to learn from mistakes" (Cho Chikun). Pedagogical value. |
| 20% | `correct_move_rank` | "Puzzles that surprise even AI teach creative reading" (Lee Sedol). Diminishing returns above rank 5. |
| 10% | `policy_entropy` | "Secondary indicator — genuine complexity" (Cho Chikun). Bonus for ambiguous positions. |

### YX/YQ Partition

**YX (complexity metrics):** `d:5;r:13;s:24;u:1;w:3;a:2;b:4;t:65`
- Existing: `d` (depth), `r` (refutation count), `s` (solution length), `u` (unique), `w` (wrong count)
- New: `a` (avg refutation depth), `b` (branch count), `t` (trap density ×100, integer 0-100)

**YQ (quality metrics):** `q:3;rc:2;hc:1;ac:2;qk:4`
- Existing: `q` (structural quality 1-5), `rc` (refutation confidence), `hc` (hint confidence), `ac` (AI correctness 0-3)
- New: `qk` (KataGo quality assessment 0-5)

### Dual-Use Signals

`avg_refutation_depth` and `trap_density` appear in BOTH YX and the `qk` formula. This is NOT redundancy — YX stores the raw metric; YQ's `qk` consumes it as one input among several. Same data, different semantic layers.

## Feature Activation Phase Sequence

| Phase | Features | Gate Condition | Player-Visible Impact |
|-------|----------|---------------|----------------------|
| Phase 0 (infrastructure) | Instantiate `ai_solve=AiSolveConfig()`, populate `elo_anchor.calibrated_rank_elo` | None — prerequisites | None — internal wiring |
| Phase 1a (scoring) | PI-1, PI-3, PI-12 | Tests pass, no behavior regression | Better refutation quality |
| Phase 1b (engine) | PI-5, PI-6, `suboptimal_branches.enabled` | Phase 1a validated, budget delta < 20% | Suboptimal branch explanations |
| Phase 1c (text) | PI-10, PI-11 | Phase 1b validated | Opponent-response phrases in wrong-move comments |
| Phase 2 (budget) | PI-2, PI-7, PI-8, PI-9 | Budget cap ≤4x defined and monitored | Deeper/wider solution trees |
| Phase 3 (calibration) | `instinct_enabled`, `elo_anchor`, PI-4 | Golden set labeled, macro-F1 ≥ 0.85, instinct accuracy ≥ 70% | Instinct phrases in hints; Elo-validated difficulty |

## Calibration Methodology

**Source**: 95 Cho Chikun fixtures at `tests/fixtures/calibration/` (30 elementary + 30 intermediate + 30 advanced + 5 ko)

**Labeling protocol (C+A hybrid)**:
1. Correct move identity: Use Cho Chikun's published answer keys (Method C — author authority)
2. Move classification: Human expert (5d+) independently classifies KataGo's TE/BM assignments as correct/incorrect (Method A)
3. Golden-calibration `labels.json`: Populate with expert-labeled ground truth (currently empty)

**Calibration procedure**:
1. Run enrichment on 95 fixtures at 3 visit counts [500, 1000, 2000]
2. Compute `qk` distribution across fixtures
3. Human spot-check top/bottom 10% `qk` scores
4. Adjust weights if calibration misalignment found
5. Track instinct accuracy (≥70% threshold for Phase 3 gate)

## User Decisions (Binding)

| decision_id | decision | source |
|-------------|----------|--------|
| D1 | Both production pipeline + accretive features in single initiative | Q1:C |
| D2 | Supersedes stalled initiatives | Q2:C |
| D3 | Signals → YX (complexity) + YQ `qk` (quality). No raw entropy/rank exposure. No goal storage. | Q3 + GQ-1/2/3 |
| D4 | Use existing 95 Cho Chikun fixtures; C+A hybrid labeling | Q4 |
| D5 | Activate all features; governance decides sequence/thresholds | Q5:A + Q6 |
| D6 | NG-1: defer, NG-2: adequate, NG-3: defer, NG-5: reject | Q7-Q10 |
| D7 | Hinting: copy backend hints.py INTO lab, combine best of both, NOT separate initiative | Q11 (user directive) |
| D8 | Include all 4 missing docs | Q12:A |
| D9 | No backward compatibility; remove unused code after showing user which | Q13:C |
| D10 | Re-enrichment is user's responsibility; all work in puzzle-enrichment-lab | Q14 + D11 |
| D11 | Scope constraint: ALL work stays inside `tools/puzzle-enrichment-lab/` unless explicitly authorized | User directive |
| D12 | Include OPP-1 (observability), OPP-2 (rotation tests), OPP-3 (debug artifact) | User directive |
| D13 | Small model: parked as future work | Q16:C |
| D14 | Comprehensive enrichment docs as directory (one-stop-shop) with English formula explanations, decisions, future work | User directive |
| D15 | TODO cleanup: archive all enrichment-lab initiatives after completion; preserve future items in docs | User directive |

> **See also**:
>
> - [Research: Gap Synthesis](./15-research.md) — Full implementation state + gap analysis
> - [Research: Hinting Comparison](../20260318-research-hinting-system-comparison/15-research.md) — Backend vs Lab hinting audit
> - [Governance Decisions](./70-governance-decisions.md) — Panel reviews (Gates 1-3)
> - [Clarifications](./10-clarifications.md) — All resolved user decisions
