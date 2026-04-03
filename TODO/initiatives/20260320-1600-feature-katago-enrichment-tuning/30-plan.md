# Plan — KataGo Enrichment Threshold Fine-Tuning

**Initiative**: 20260320-1600-feature-katago-enrichment-tuning
**Date**: 2026-03-20
**Correction Level**: Level 3 (Multiple Files — config + code + tests + docs)

---

## Approach

Single-option approach: Apply all 14 consensus-backed config changes + 1 code fix in phased execution. No alternative options needed — the four-expert consensus matrix provides clear recommendations.

## Execution Phases

### Phase 1: Config Value Changes (14 parameters)

Update `config/katago-enrichment.json` with all consensus-backed threshold changes. Bump version 1.25→1.26. Add changelog entry documenting all changes.

### Phase 2: Code Fix (S-1)

Fix `solve_position.py` adaptive boost override. When `visit_allocation_mode=="adaptive"`, compound the edge-case boost with `branch_visits` instead of discarding it: `effective_visits = int(tree_config.branch_visits * boost)`.

### Phase 3: Tests

Add new test for adaptive+boost compounding. Verify all existing tests pass with new config values.

### Phase 4: Documentation

Update AGENTS.md to correct the adaptive mode documentation.

## Documentation Plan

| files_to_update | why_updated |
|----------------|-------------|
| `tools/puzzle-enrichment-lab/AGENTS.md` | Correct the note about adaptive mode overriding edge-case boosts — now compounds instead |

| files_to_create | why_created |
|----------------|-------------|
| (none) | |

## Constraints

- C1: Version bump 1.25→1.26
- C2: Constraint C9 from v1.23 satisfied — no C9-protected thresholds modified (D-4)
- C3: ~15% compute increase acceptable
- C4: Fixed mode behavior unchanged
- C5: Full test coverage

## Player-Facing Impact (RC-P1)

The combined threshold changes affect ~5% of edge-case moves:
- **t_bad 0.15→0.12**: Moves with winrate delta 0.12-0.15 reclassified from NEUTRAL to BM (bad move). These are moves that already had refutation trees generated (delta_threshold=0.08) but were not labeled "wrong." The TS expert (Dr. Shin Jinseo 9p) validated this reclassification as pedagogically correct: "a 4% buffer (0.12 vs 0.08) preserves the 'interesting wrong move' category while ensuring BM classification covers most refutated moves."
- **t_good 0.05→0.03**: Tighter correct-move classification. Moves with delta 0.03-0.05 reclassified from TE (technically equivalent) to NEUTRAL. The ENG expert confirmed 0.03 provides 1σ margin above the b18@500v noise floor (~0.02), preventing noise-induced false positives.
- **Net effect**: Puzzles become slightly more demanding (fewer "almost correct" moves accepted). This aligns with the Go teaching principle that in tsumego, there is one correct answer.
