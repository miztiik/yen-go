# Research — KaTrain Trap Density + Elo-Anchor

**Last Updated**: 2026-03-13  
**Initiative**: `20260313-2000-feature-katrain-trap-density-elo-anchor`

---

## Source Research

Full KaTrain analysis documented in:
- [Research: KaTrain Config Comparison](../20260313-research-katrain-config-comparison/15-research.md)

## Implementation-Specific Findings

### F1: score_lead availability in refutation path

**Current state**: `generate_single_refutation()` in `generate_refutations.py` already calls `engine.analyze()` and gets a full `AnalysisResponse` with `MoveAnalysis` objects. Each `MoveAnalysis` has `score_lead: float`. The opponent's best response (`opp_best`) has `score_lead`. Currently only `winrate` is extracted:

```python
# Line ~228 in generate_refutations.py
winrate_after = 1.0 - opp_best.winrate
winrate_delta = winrate_after - initial_winrate
```

The fix: also extract `score_lead` and compute `score_delta`:
```python
score_after = -opp_best.score_lead  # flip perspective
score_delta = score_after - initial_score
```

**Requires**: `initial_score` (root score) to be passed into `generate_single_refutation()`. Currently only `initial_winrate` is passed.

### F2: Root score availability

Root score is available in two places:
1. `AnalysisResponse.root_score` — the score at the initial position
2. In `assembly_stage.py`, `pre_score_lead` is already computed and passed to the solve result

The refutation orchestrator (`generate_refutations_for_puzzle()`) has access to the initial analysis response. We need to extract `root_score` and thread it through.

### F3: KaTrain CALIBRATED_RANK_ELO table

```python
CALIBRATED_RANK_ELO = [
    (-21.679, 18),    # 18k
    (42.602, 17),     # 17k
    (106.884, 16),    # 16k
    (171.166, 15),    # 15k
    (235.448, 14),    # 14k
    (299.730, 13),    # 13k
    (364.012, 12),    # 12k
    (428.294, 11),    # 11k
    (492.576, 10),    # 10k
    (556.858, 9),     # 9k
    (621.140, 8),     # 8k
    (685.422, 7),     # 7k
    (749.703, 6),     # 6k
    (813.985, 5),     # 5k
    (878.267, 4),     # 4k
    (942.549, 3),     # 3k
    (1006.831, 2),    # 2k
    (1071.113, 1),    # 1k
    (1135.395, 0),    # 1d
    (1199.677, -1),   # 2d
    (1263.959, -2),   # 3d
    (1700, -4),       # 5d
]
```

### F4: Elo → Yen-Go level mapping

To use as hard gate, need: policy_prior → approximate Elo → kyu rank → Yen-Go level.

KaTrain's `ai_rank_estimation()` uses `interp1d(CALIBRATED_RANK_ELO, elo)` to convert Elo→rank. We need the reverse: rank→Elo, then Yen-Go level→rank range→Elo range.

Simpler approach: derive policy_prior → approximate "difficulty Elo" using the fact that higher policy = easier puzzle = lower Elo player can solve it. Then map Elo to kyu/dan rank via the table, then to Yen-Go level. If the Elo-derived level differs from the composite-score-derived level by more than threshold, override.

### F5: Confidence score

| Metric | Value |
|--------|-------|
| `planning_confidence_score` | 82 |
| `risk_level` | medium |
| `research_invoked` | Yes (prior initiative + sub-agent) |

**Rationale**: All data paths verified. Main uncertainty is calibration quality of Elo→level mapping and the Q6 adj_weight decision.
