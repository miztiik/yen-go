# Plan — KaTrain Score-Based Trap Density + Elo-Anchor Hard Gate (OPT-3)

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`  
**Selected Option**: OPT-3  
**Governance Status**: GOV-OPTIONS-APPROVED (unanimous)

---

## Architecture Overview

### Change Summary

Two features implemented in the enrichment lab's difficulty estimation pipeline:

1. **Score-based trap density** — Replace `|winrate_delta| × policy` with `|score_delta| × policy / (normalization_cap)` + configurable per-puzzle floor
2. **Elo-anchor level gate** — After composite scoring, cross-check against KaTrain's calibrated Elo table; override level when divergence exceeds threshold

### Data Flow (Modified)

```
KataGo analysis → MoveAnalysis.score_lead (EXISTING)
                → generate_single_refutation: compute score_delta (NEW)
                → Refutation.score_delta (NEW field)
                → _compute_trap_density: use score_delta (MODIFIED)
                → estimate_difficulty: composite score → _score_to_level (EXISTING)
                → _elo_anchor_gate: cross-check + override (NEW)
                → DifficultyEstimate (EXISTING model, no changes)
```

---

## Detailed Design

### D1: Refutation Model — Add `score_delta` Field

**File**: `tools/puzzle-enrichment-lab/models/refutation_result.py`

Add new field to `Refutation`:
```python
score_delta: float = Field(
    default=0.0,
    description="Score delta from root position (negative = points lost for puzzle player)")
```

**Backward compat**: Default value 0.0 means existing serialized Refutation objects still load correctly. Old code that doesn't set score_delta will get 0.0. The trap density formula will fall back to `|winrate_delta|` when `score_delta == 0.0` (see D3).

### D2: Thread score_lead Through Refutation Generation

**File**: `tools/puzzle-enrichment-lab/analyzers/generate_refutations.py`

Two changes:

1. **`generate_single_refutation()`** — Add `initial_score` parameter. After computing `winrate_delta`, also compute:
   ```python
   score_after = -opp_best.score_lead  # flip from opponent to puzzle player
   score_delta = score_after - initial_score
   ```
   Set `Refutation.score_delta = score_delta`.

2. **`generate_refutations()` orchestrator** — Extract `initial_score = initial_analysis.root_score` alongside `initial_winrate`. Pass to `generate_single_refutation()`.

3. **`_enrich_curated_policy()`** — Also enrich `score_delta` for curated refutations. Build `score_lookup` from `initial_analysis.move_infos` and compute `score_delta = mi.score_lead - root_score` (no flip needed — initial analysis move_infos are already in puzzle player perspective, matching the existing `winrate_delta = wr - root_wr` convention). Note: the perspective flip `-(opp_best.score_lead)` is only needed in `generate_single_refutation()` where analysis runs from the opponent's turn.

### D3: Score-Based Trap Density Formula (with Floor)

**File**: `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`

Replace `_compute_trap_density()`. New formula:

```python
def _compute_trap_density(refutation_result: RefutationResult) -> float:
    if not refutation_result.refutations:
        return 0.0
    
    cfg = load_enrichment_config()
    score_cap = cfg.difficulty.score_normalization_cap
    floor = cfg.difficulty.trap_density_floor
    
    weighted_sum = 0.0
    prior_sum = 0.0
    
    for ref in refutation_result.refutations:
        prior = ref.wrong_move_policy
        # Prefer score_delta; fall back to |winrate_delta| for legacy data
        if abs(ref.score_delta) > 1e-9:
            raw_loss = abs(ref.score_delta)
            normalized_loss = min(raw_loss / score_cap, 1.0)
        else:
            normalized_loss = abs(ref.winrate_delta)  # fallback [0, 1]
        weighted_sum += normalized_loss * prior
        prior_sum += prior
    
    if prior_sum < 1e-9:
        return 0.0
    
    raw_density = min(weighted_sum / prior_sum, 1.0)
    # Per-puzzle floor: when refutations exist, trap density ≥ floor
    return max(raw_density, floor)
```

### D4: Config Additions

**File**: `config/katago-enrichment.json`

Add to `difficulty` section:
```json
"score_normalization_cap": 30.0,
"trap_density_floor": 0.05
```

Add new `elo_anchor` section:
```json
"elo_anchor": {
  "enabled": true,
  "override_threshold_levels": 2,
  "min_covered_rank_kyu": 18,
  "max_covered_rank_dan": 5,
  "calibrated_rank_elo": [
    {"elo": -21.679, "kyu_rank": 18},
    {"elo": 42.602, "kyu_rank": 17},
    ...
    {"elo": 1700, "kyu_rank": -4}
  ]
}
```

**File**: `tools/puzzle-enrichment-lab/config.py`

Add Pydantic models for new config sections.

Bump config version to `1.17`.

### D5: Elo-Anchor Gate

**File**: `tools/puzzle-enrichment-lab/analyzers/estimate_difficulty.py`

New function `_elo_anchor_gate()`:

```python
def _elo_anchor_gate(
    policy_prior: float,
    composite_level_slug: str,
    composite_level_id: int,
    cfg: EnrichmentConfig,
    puzzle_id: str = "",
) -> tuple[str, int]:
    """Apply Elo-anchor hard gate: override level if divergence exceeds threshold.
    
    Uses KaTrain's CALIBRATED_RANK_ELO (MIT licensed, github.com/sanderland/katrain)
    to map policy_prior → approximate kyu rank → Yen-Go level.
    
    Returns (level_slug, level_id) — either original or overridden.
    Logs "no Elo anchor" for uncovered ranges (novice, beginner, expert).
    """
```

**Logic**:
1. Convert `policy_prior` → approximate difficulty (lower policy = harder)
2. Interpolate `CALIBRATED_RANK_ELO` table to get kyu rank
3. Map kyu rank to Yen-Go level
4. If within covered range and divergence ≥ threshold → override
5. If outside covered range → log and return original

**Integration**: Called after `_score_to_level()` in `estimate_difficulty()`.

### D6: Legacy Code Removal

Remove:
- Old docstring in `_compute_trap_density()` that says "approximated by |winrate_delta|"
- Update docstring in `estimate_difficulty()` to reflect score-based formula
- No configuration branch — single code path

### D7: Test Updates

**File**: `tools/puzzle-enrichment-lab/tests/test_difficulty.py`

- Update `_make_refutations()` helper to include `score_delta`
- Update all trap density assertions to reflect score-based values
- Add test: score-divergent vs winrate-divergent refutations produce different densities
- Add test: floor activates when raw density < floor but refutations exist
- Add test: floor does NOT activate when 0 refutations
- Add test: fallback to `|winrate_delta|` when `score_delta == 0`

New test file or section for Elo-anchor:
- Test: Elo gate overrides when divergence ≥ 2 levels
- Test: Elo gate preserves when divergence < 2 levels
- Test: Elo gate skips for novice (log "no data")
- Test: Elo gate skips for beginner (log "no data")
- Test: Elo gate skips for expert (log "no data")
- Test: Elo gate works for elementary through high-dan

---

## Risks and Mitigations

| ID | Risk | Mitigation |
|----|------|-----------|
| RK1 | Score-based formula changes all difficulty scores | D1 accepted (no backward compat). All puzzles re-enriched. |
| RK2 | Elo hard gate overrides correct levels at edges | Config-driven threshold (2 levels). Can increase post-calibration. |
| RK3 | `score_normalization_cap: 30` may be too low for capturing races | Config-driven. PSE-B observation: adjust after first batch run. |
| RK4 | Fallback to winrate_delta distorts results for mixed data | Only fires when `score_delta == 0` (legacy/curated). Score enrichment in D2 ensures new data always has score_delta. |

---

## Documentation Plan

| ID | Action | File | Why |
|----|--------|------|-----|
| DOC-1 | Update | `config/katago-enrichment.json` changelog | New version 1.17 entry documenting score-based trap density and Elo anchor |
| DOC-2 | Update | `tools/puzzle-enrichment-lab/README.md` | Mention KaTrain-derived calibration and Elo-anchor feature |
| DOC-3 | Create | Code comment in `estimate_difficulty.py` | KaTrain MIT attribution for CALIBRATED_RANK_ELO |
| DOC-4 | Update | `TODO/initiatives/20260313-research-katrain-config-comparison/15-research.md` | Cross-reference this implementation initiative |

---

> **See also**:
> - [Charter](./00-charter.md)
> - [Options](./25-options.md)
> - [Governance Decisions](./70-governance-decisions.md)
