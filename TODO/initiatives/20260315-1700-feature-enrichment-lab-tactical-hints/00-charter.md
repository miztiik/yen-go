# Charter — Enrichment Lab Tactical Hints & Detection Improvements

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Type**: Feature
**Last Updated**: 2026-03-15
**Supersedes**: `20260315-1400-feature-tactical-analysis-wiring` (archived — wrong target system)

---

## Summary

Improve the puzzle enrichment lab's hint generation, teaching comments, difficulty estimation, and detection quality using concepts from external Go research (PLNech/gogogo instincts/tactics, gogamev4 analysis/territory). The key insight: the enrichment lab's 28 detectors generate rich `DetectionResult` evidence that is currently **discarded** before reaching hints — and KataGo's policy distribution contains untapped signals for move intent (instinct) classification and difficulty estimation (entropy). This initiative wires existing data into richer pedagogical output.

**Target system**: `tools/puzzle-enrichment-lab/` (NOT `backend/puzzle_manager/`)

## Goals

| G-ID | Goal | Acceptance Criteria |
|------|------|-------------------|
| G-1 | **Add policy entropy as difficulty signal** | Shannon entropy over KataGo policy distribution computed in `estimate_difficulty.py`; stored in YX complexity metrics; calibrated against golden set before weighting |
| G-2 | **Pass DetectionResult evidence to hint generator** | `DetectionResult` objects (with confidence + evidence strings) flow from `technique_stage` through to `teaching_stage` and `hint_generator`; evidence like "12-step ladder chase" appears in Tier 2 hints |
| G-3 | **Add instinct classification for hints and teaching comments** | New `instinct_classifier.py` classifies correct move intent (push, hane, cut, descent, extend) from KataGo policy direction relative to groups; instinct appears in teaching comments and Tier 1/2 hints |
| G-4 | **Build multi-orientation test infrastructure** | `Position.rotate(degrees)` and `Position.reflect(axis)` methods; tactical detectors (ladder, net, snapback, ko, throw-in) have parametrized 4-orientation tests |
| G-5 | **Add level-adaptive hint content** | Hint text varies by `get_level_category()`: beginner→consequence, intermediate→intent+position, dan→reading guidance; config-driven template sets |
| G-6 | **Add Top-K rank as observability metric** | `correct_move_rank` (position of SGF correct move in KataGo's candidate list) stored in `BatchSummary` and available for correlation analysis |

## Non-Goals

| NG-ID | Exclusion | Rationale |
|-------|-----------|-----------|
| NG-1 | Game phase taxonomy (opening/middle/endgame) | Governance 6/7: existing detectors (fuseki, joseki, endgame) + YC already cover this |
| NG-2 | Mistake severity grading (BLUNDER/MISTAKE/INACCURACY) | Existing 11 refutation conditions adequate for tsumego |
| NG-3 | Board-sim detectors alongside KataGo | User decision: improve KataGo signal interpretation, not parallel detection paths |
| NG-4 | Modify existing 28 detectors | Additive-only: new instinct classifier + rewired evidence pipeline; existing detection unchanged |
| NG-5 | Backend pipeline changes | This initiative targets enrichment lab only. Backend tactical_analyzer.py is out of scope. |
| NG-6 | AiAnalysisResult schema version bump | New signals fit within existing schema fields (YH, YX, teaching comments) |
| NG-7 | Expand dead shape catalog (6→30+) | Low-risk addition but separate, smaller initiative |
| NG-8 | Implement all 8 instincts | Only tsumego-relevant: push, hane, cut, descent, extend (5 of 8). Connect/block/jump are fuseki concepts. |

## Constraints

| C-ID | Constraint |
|------|-----------|
| C-1 | Zero new KataGo queries — all features derive from existing `AnalysisResponse` data (policy, PV, ownership, winrate) |
| C-2 | AiAnalysisResult backward compatible — new fields are additive, existing consumers unaffected |
| C-3 | Calibration-first — every new signal (instinct, entropy) requires golden set validation (50-100 puzzles) BEFORE production weighting |
| C-4 | Changes confined to `tools/puzzle-enrichment-lab/` (no backend/, no frontend/) |
| C-5 | Clean-room — Go patterns from Sensei's Library (public domain); no code from GPL-3.0 gogogo |
| C-6 | Config-driven — instinct templates, level-adaptive hint templates in config files, not hardcoded |
| C-7 | 15-word cap on teaching comments preserved (existing `comment_assembler.py` constraint) |

## Backward Compatibility

**Required**: Yes. `AiAnalysisResult` schema v9 is consumed by the backend pipeline's publish stage. New signals (instinct, entropy) are additive — they populate existing YH/YX/teaching-comment fields with richer content but don't change field structure. Existing hint text quality is maintained or improved, never degraded.

## Acceptance Criteria

| AC-ID | Criterion | Measurement |
|-------|-----------|-------------|
| AC-1 | Policy entropy computed for all puzzles in batch | `estimate_difficulty.py` outputs entropy value; appears in YX; batch run completes without regression |
| AC-2 | Entropy correlates with human difficulty | Golden set (≥50 puzzles): Spearman correlation ≥ 0.3 between entropy and human-assigned difficulty |
| AC-3 | DetectionResult evidence in Tier 2 hints | Known-ladder puzzle → Tier 2 hint references ladder chase length or PV detail (not generic "N moves of reading") |
| AC-4 | Instinct classification accurate | Golden set: ≥70% agreement between classifier output and manual instinct labels for push/hane/cut/descent/extend |
| AC-5 | Instinct appears in teaching comments | Ladder puzzle → teaching comment includes "push" or technique intent phrase |
| AC-6 | Multi-orientation tests pass for tactical detectors | Ladder/net/snapback/ko/throw-in detectors produce same `detected=True` for 4 rotations of identical positions |
| AC-7 | Level-adaptive hints differ by level | Same puzzle at beginner vs dan level → different Tier 2 hint text |
| AC-8 | Top-K rank observable | `BatchSummary` includes `correct_move_rank` per puzzle; distribution plottable |
| AC-9 | All existing tests pass (no regression) | `pytest tests/ --cache-clear` → 100% pass from `tools/puzzle-enrichment-lab/` |
| AC-10 | Existing hint quality maintained | Golden set: existing hints not degraded (manual review of 10 sample puzzles) |

---

> **See also**:
> - [15-research.md](./15-research.md) — Full gap analysis with external reference cross-referencing
> - [10-clarifications.md](./10-clarifications.md) — All 10 clarifications resolved with governance input
> - Archived: `TODO/initiatives/20260315-1400-feature-tactical-analysis-wiring/` — predecessor (wrong scope)
