# Tasks — KaTrain Score-Based Trap Density + Elo-Anchor Hard Gate (OPT-3)

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`  
**Selected Option**: OPT-3

---

## Task Dependency Graph

```
T1 (Refutation model) ──┐
                         ├── T3 (Trap density formula)  ── T5 (Test updates) ── T8 (Legacy removal)
T2 (Thread score_lead) ──┘                                                           │
                                                                                      ├── T9 (Docs)
T4 (Config additions) ─────── T6 (Elo-anchor gate) ── T7 (Elo tests) ───────────────┘
```

---

## Task List

### Phase 1: Data Plumbing (T1, T2 — parallel)

| ID | Task | Status | File(s) | Depends | Parallel |
|----|------|--------|---------|---------|----------|
| T1 | Add `score_delta` field to `Refutation` model | not-started | `models/refutation_result.py` | — | [P] with T2 |
| T2 | Thread `score_lead` through refutation generation | not-started | `analyzers/generate_refutations.py` | — | [P] with T1 |

**T1 details**:
- [ ] Add `score_delta: float = Field(default=0.0, description="Score delta from root (neg = loss)")` to `Refutation` class
- [ ] Verify default 0.0 doesn't break existing deserialization

**T2 details**:
- [ ] Add `initial_score: float` parameter to `generate_single_refutation()`
- [ ] After wrong-move analysis: `score_after = -opp_best.score_lead`, `score_delta = score_after - initial_score`
- [ ] Set `Refutation(..., score_delta=score_delta)` in return
- [ ] In `generate_refutations()`: extract `initial_score = initial_analysis.root_score`, pass to `generate_single_refutation()`
- [ ] In `_enrich_curated_policy()`: build `score_lookup` from `initial_analysis.move_infos`, compute `score_delta` for curated refutations, set `ref.score_delta`

---

### Phase 2: Config (T4 — independent, can start with Phase 1)

| ID | Task | Status | File(s) | Depends | Parallel |
|----|------|--------|---------|---------|----------|
| T4 | Add config keys for score trap density + Elo anchor | not-started | `config/katago-enrichment.json`, `tools/.../config.py` | — | [P] with T1, T2 |

**T4 details**:
- [ ] Add `difficulty.score_normalization_cap: 30.0` to JSON
- [ ] Add `difficulty.trap_density_floor: 0.05` to JSON
- [ ] Add `elo_anchor` section with `enabled`, `override_threshold_levels`, `min_covered_rank_kyu`, `max_covered_rank_dan`, `calibrated_rank_elo` table
- [ ] Add MIT attribution comment for KaTrain CALIBRATED_RANK_ELO (in JSON description field)
- [ ] Bump config `version` to `1.17`
- [ ] Add changelog entry for v1.17
- [ ] Add Pydantic models in `config.py`: `EloAnchorConfig`, `CalibratedRankElo`
- [ ] Add `score_normalization_cap` and `trap_density_floor` fields to `DifficultyConfig` Pydantic model
- [ ] Validate Pydantic model loads correctly with new fields

---

### Phase 3: Formula + Gate (T3, T6 — T3 depends on T1+T2, T6 depends on T4)

| ID | Task | Status | File(s) | Depends | Parallel |
|----|------|--------|---------|---------|----------|
| T3 | Replace trap density formula with score-based + floor | not-started | `analyzers/estimate_difficulty.py` | T1, T2 | [P] with T6 |
| T6 | Implement Elo-anchor hard gate function | not-started | `analyzers/estimate_difficulty.py` | T4 | [P] with T3 |

**T3 details**:
- [ ] Rewrite `_compute_trap_density()` to use `ref.score_delta` (prefer) with `ref.winrate_delta` fallback
- [ ] Normalize `|score_delta|` by `score_normalization_cap` (config-driven)
- [ ] Apply per-puzzle `trap_density_floor` when ≥1 refutation exists
- [ ] Update function docstring (remove "approximated by |winrate_delta|", add KaTrain attribution)
- [ ] Load config once at function start (already pattern in file)

**T6 details**:
- [ ] Create `_elo_anchor_gate(policy_prior, composite_slug, composite_id, cfg, puzzle_id)` function
- [ ] Implement policy_prior → Elo → kyu rank mapping using logarithmic interpolation:
  - **Approach**: Use `difficulty_elo = interp1d(POLICY_TO_ELO_TABLE, policy_prior)` where the table maps policy thresholds from `difficulty.policy_to_level` to approximate Elo values derived from KaTrain's `CALIBRATED_RANK_ELO`. Each policy threshold in `policy_to_level.thresholds` corresponds to a level slug → rank range → midpoint kyu rank → interpolated Elo from KaTrain table.
  - **Derivation**: For each Yen-Go level slug, take the midpoint of its rank range (e.g., elementary: 20k-16k → 18k). Look up 18k in `CALIBRATED_RANK_ELO` to get Elo ≈ -22. For the Elo-anchor gate, convert the composite-assigned level_slug to its midpoint rank, then convert policy_prior to its midpoint rank via `policy_to_level` thresholds. Compare the two rank midpoints.
  - **Simplification**: Since both composite-score level and policy-prior level already map to rank ranges via `puzzle-levels.json`, the Elo table's primary role is to validate that the rank-level mapping is physically plausible. The implementation can directly compare rank midpoints without explicit Elo conversion. The `CALIBRATED_RANK_ELO` table is embedded in config for future use and auditing.
- [ ] Implement KaTrain `CALIBRATED_RANK_ELO` interpolation: kyu rank → Elo (for logging/diagnostics)
- [ ] Map kyu rank → Yen-Go level via `config/puzzle-levels.json` rank ranges
- [ ] If outside covered range (novice, beginner, expert): log "no Elo anchor available", return original
- [ ] If within range and `|composite_level_id - elo_level_id| >= threshold`: override level, log INFO
- [ ] If within range and divergence < threshold: return original, log DEBUG
- [ ] Add MIT attribution code comment referencing KaTrain
- [ ] Integrate: call `_elo_anchor_gate()` after `_score_to_level()` in `estimate_difficulty()`

---

### Phase 4: Tests (T5, T7 — depend on T3, T6 respectively)

| ID | Task | Status | File(s) | Depends | Parallel |
|----|------|--------|---------|---------|----------|
| T5 | Update trap density tests | not-started | `tests/test_difficulty.py` | T3 | [P] with T7 |
| T7 | Add Elo-anchor gate tests | not-started | `tests/test_difficulty.py` | T6 | [P] with T5 |

**T5 details**:
- [ ] Update `_make_refutations()` helper to accept and set `score_delta`
- [ ] Update existing trap density test assertions for score-based values
- [ ] Add test: score-divergent vs winrate-divergent refutations → different densities
- [ ] Add test: floor activates when raw < floor but refutations exist
- [ ] Add test: floor does NOT activate when 0 refutations → density = 0.0
- [ ] Add test: fallback to `|winrate_delta|` when `score_delta == 0.0` (legacy compat)
- [ ] Add test: `score_normalization_cap` config respected
- [ ] Ensure monotonicity tests still pass with new formula

**T7 details**:
- [ ] Add test: Elo gate overrides level when divergence ≥ 2 levels (elementary→advanced range)
- [ ] Add test: Elo gate preserves level when divergence < 2 levels
- [ ] Add test: Elo gate skips novice → log "no Elo anchor available"
- [ ] Add test: Elo gate skips beginner → log "no Elo anchor available"
- [ ] Add test: Elo gate skips expert → log "no Elo anchor available"
- [ ] Add test: Elo gate works for elementary, intermediate, upper-intermediate, advanced, low-dan, high-dan
- [ ] Add test: `override_threshold_levels` config respected (mock config)
- [ ] Add test: Elo gate disabled when `elo_anchor.enabled = false` → return original level

---

### Phase 5: Cleanup + Docs (T8, T9 — depend on T5, T7)

| ID | Task | Status | File(s) | Depends | Parallel |
|----|------|--------|---------|---------|----------|
| T8 | Remove legacy code + update docstrings | not-started | `analyzers/estimate_difficulty.py`, `analyzers/generate_refutations.py` | T5, T7 | [P] with T9 |
| T9 | Documentation updates | not-started | Multiple | T5, T7 | [P] with T8 |

**T8 details**:
- [ ] Remove old docstring references to `|winrate_delta|` approximation
- [ ] Update `estimate_difficulty()` docstring to document score-based formula
- [ ] Update `_enrich_curated_policy()` docstring to include score enrichment
- [ ] Clean up any dead code / unreachable branches

**T9 details**:
- [ ] Add `v1.17` changelog entry in `katago-enrichment.json`: "Score-based trap density (KaTrain-inspired) replacing |winrate_delta| approximation. Configurable floor (trap_density_floor). Elo-anchor hard gate for level validation (elementary→high-dan). KaTrain MIT attribution."
- [ ] Update `tools/puzzle-enrichment-lab/README.md` with KaTrain-derived features mention
- [ ] Cross-reference in research initiative `15-research.md`

---

## Summary

| Phase | Tasks | Files Modified | Lines Changed (est.) |
|-------|-------|---------------|---------------------|
| 1: Data Plumbing | T1, T2 | 2 | ~30 |
| 2: Config | T4 | 2 | ~80 |
| 3: Formula + Gate | T3, T6 | 1 | ~120 |
| 4: Tests | T5, T7 | 1 | ~200 |
| 5: Cleanup + Docs | T8, T9 | 4 | ~30 |
| **Total** | **9 tasks** | **~7 unique files** | **~460 lines** |

---

> **See also**:
> - [Plan](./30-plan.md)
> - [Charter](./00-charter.md)
> - [Governance Decisions](./70-governance-decisions.md)
