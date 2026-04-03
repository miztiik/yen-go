# Analysis — KaTrain Score-Based Trap Density + Elo-Anchor Hard Gate

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 85 |
| `risk_level` | medium |
| `research_invoked` | Yes (KaTrain constants.py + ai.py, sub-agent code audit) |

**Score breakdown**:
- Start: 100
- -5: Elo → level mapping has an indirect chain (policy → Elo → rank → level)
- -5: `score_normalization_cap` needs empirical validation (PSE-B observation)
- -5: adj_weight pattern adapted, not verbatim — small translation risk

---

## Cross-Artifact Consistency

| finding_id | artifact_a | artifact_b | check | result |
|------------|-----------|-----------|-------|--------|
| F1 | Charter G1 | Tasks T3 | Score-based formula covered | ✅ T3 implements D3 of plan |
| F2 | Charter G2 | Tasks T1, T2 | score_delta threading covered | ✅ T1 (model) + T2 (generation) |
| F3 | Charter G3 | Tasks T6 | Elo hard gate covered | ✅ T6 implements D5 of plan |
| F4 | Charter G4 | Tasks T7 | Log "no data" for uncovered ranges | ✅ T7 tests skip for novice/beginner/expert |
| F5 | Charter G5 | Tasks T8 | Legacy removal covered | ✅ T8 removes old docstrings/code |
| F6 | Charter G6 | Tasks T4, T9 | Config + docs covered | ✅ T4 (config) + T9 (changelog) |
| F7 | Clarifications D3 | Tasks T1 | score_delta is model field (not inline) | ✅ T1 adds field to Refutation model |
| F8 | Governance must-hold-1 | Tasks T4 | floor + cap are config keys | ✅ T4 adds both to JSON + Pydantic |
| F9 | Governance must-hold-2 | Tasks T3 | Floor fires only when ≥1 refutation | ✅ T3 formula: `if not refutations: return 0.0` |
| F10 | Governance must-hold-3 | Tasks T4 | override_threshold_levels is config | ✅ T4 adds `elo_anchor.override_threshold_levels` |
| F11 | Governance must-hold-4 | Tasks T4, T6 | KaTrain MIT attribution | ✅ T4 (config description), T6 (code comment) |
| F12 | Governance must-hold-5 | Tasks T1 | score_delta is model field | ✅ T1 adds Pydantic field |

---

## Coverage Map

| Charter Goal | Plan Section | Task(s) | Test(s) | Doc(s) |
|---|---|---|---|---|
| G1: Score-based trap density | D3 | T3 | T5 | T9 |
| G2: Thread score_delta | D1, D2 | T1, T2 | T5 (fallback test) | T8 (docstring) |
| G3: Elo hard gate | D5 | T6 | T7 | T9 |
| G4: Log "no data" | D5 | T6 | T7 | — |
| G5: Remove legacy | D6 | T8 | — | T8 |
| G6: Config update | D4 | T4 | T5/T7 (config mocking) | T9 |

**Unmapped tasks**: None. All 9 tasks trace to at least one charter goal.

---

## Ripple Effects

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|-----------|------------|--------|
| RE-1 | downstream | `test_difficulty.py` — all trap density assertions | Values change from winrate-based to score-based | T5 updates all assertions | T5 | ✅ addressed |
| RE-2 | downstream | `DifficultyEstimate.trap_density` — semantics change | Field still [0,1] float, but values shift. Consumers keyed on _level_ not _density_ | No consumer reads trap_density directly — only raw_score → level | T3 | ✅ addressed |
| RE-3 | lateral | `bridge.py` — already computes `pointsLost` independently | No change needed; confirms score data available | — | — | ✅ no action |
| RE-4 | lateral | `_enrich_curated_policy()` — needs score enrichment | T2 extends enrichment to cover score_delta | T2 | ✅ addressed |
| RE-5 | lateral | `assembly_stage.py` — computes `pre_score_lead/post_score_lead` | Independent path; no collision. Confirms score data flows. | — | — | ✅ no action |
| RE-6 | upstream | `AnalysisResponse.root_score` — already parsed | No change needed upstream | — | — | ✅ no action |
| RE-7 | downstream | `test_calibration.py` — Cho Chikun reference puzzles | May need threshold updates if score-based density shifts levels | T5 run validates; adjust if needed | T5 | ✅ addressed |
| RE-8 | lateral | `observability.py` — DisagreementSink | Elo-anchor overrides would show up as level changes in batch summary | Natural fit — no code change needed | — | ✅ no action |
| RE-9 | downstream | `config.py` Pydantic validation | New fields must validate on load | T4 adds Pydantic models + validation tests | T4 | ✅ addressed |

---

## Severity-Based Findings

| finding_id | severity | description | resolution |
|------------|----------|-------------|------------|
| SA-1 | INFO | `score_normalization_cap: 30.0` may need empirical tuning for capturing races (PSE-B) | Config-driven; adjust after first batch run. Non-blocking. |
| SA-2 | INFO | Elo table covers 6/9 levels only | Accepted limitation (D5). Logged as "no data". |
| SA-3 | LOW | Fallback to `|winrate_delta|` when `score_delta == 0` creates a mixed-signal path | Transitional only — T2 ensures all new refutations have score_delta. Curated refutations enriched in `_enrich_curated_policy()`. |
| SA-4 | LOW | `policy_prior → Elo` mapping is an approximation (policy ≠ difficulty in all cases) | Known limitation of Elo-anchor approach. The 2-level threshold absorbs noise. Config-driven for tuning. |
| SA-5 | INFO | Score delta sign convention: KataGo reports from side-to-move perspective; flipping needed | Addressed in D2: `score_after = -opp_best.score_lead`. Same pattern as existing winrate flip (L228). |

---

> **See also**:
> - [Plan](./30-plan.md)
> - [Tasks](./40-tasks.md)
> - [Governance Decisions](./70-governance-decisions.md)
