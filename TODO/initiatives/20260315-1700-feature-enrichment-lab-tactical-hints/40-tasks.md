# Tasks — Enrichment Lab Tactical Hints & Detection Improvements

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Selected Option**: OPT-2 — New InstinctStage
**Last Updated**: 2026-03-15

---

## Task List (Dependency-Ordered)

### Phase 1: Infrastructure & Foundations (No Behavioral Changes)

| T-ID | Task | Scope | Dependencies | Parallel? | Files |
|------|------|-------|-------------|-----------|-------|
| T1 | **Add `Position.rotate(degrees)` and `Position.reflect(axis)` methods** | G-4 | None | [P] | `models/position.py`, tests |
| T2 | **Add multi-orientation test parametrization for tactical detectors** | G-4 | T1 | [P] | `tests/test_detectors_high_frequency.py`, `tests/test_detectors_intermediate.py` |
| T3 | **Create `InstinctResult` model** | G-3 | None | [P] | `models/instinct_result.py` (NEW) |
| T4 | **Add `detection_results` and `instinct_results` fields to `PipelineContext`** | G-2, G-3 | T3 | | `analyzers/stages/protocols.py` |

**T1 detail**: Add `rotate(degrees: int)` accepting 0/90/180/270 and `reflect(axis: str)` accepting "x"/"y" to `Position` model. Rotate/reflect all stone coordinates. Return new `Position` with transformed coordinates. Test with known positions.

**T2 detail**: Parametrize existing positive-detection tests for `LadderDetector`, `NetDetector`, `SnapbackDetector`, `KoDetector`, `ThrowInDetector` with `@pytest.mark.parametrize("rotation", [0, 90, 180, 270])`. Use `Position.rotate()` on test fixtures. Fix any detector bugs discovered.

**T3 detail**: 
```python
@dataclass
class InstinctResult:
    instinct: str       # "push", "hane", "cut", "descent", "extend"
    confidence: float   # 0.0-1.0
    evidence: str       # "Adjacent push toward edge at D4"
```

**T4 detail**: Add optional `detection_results: list[DetectionResult] | None = None` and `instinct_results: list[InstinctResult] | None = None` to `PipelineContext`.

### Phase 2: Core Features (Behavioral Changes)

| T-ID | Task | Scope | Dependencies | Parallel? | Files |
|------|------|-------|-------------|-----------|-------|
| T5 | **Add `compute_policy_entropy()` to `estimate_difficulty.py`** | G-1 | None | [P] | `analyzers/estimate_difficulty.py`, tests |
| T6 | **Wire entropy into `DifficultyStage`** | G-1 | T5 | | `analyzers/stages/difficulty_stage.py` |
| T7 | **Add `find_correct_move_rank()` and wire into `DifficultyStage`** | G-6 | None | [P] | `analyzers/estimate_difficulty.py`, `analyzers/stages/difficulty_stage.py`, tests |
| T8 | **Stop discarding `DetectionResult` in `TechniqueStage`** | G-2 | T4 | [P] | `analyzers/stages/technique_stage.py` |
| T9 | **Create `instinct_classifier.py`** | G-3 | T3 | | `analyzers/instinct_classifier.py` (NEW), tests |
| T10 | **Create `InstinctStage`** | G-3 | T4, T9 | | `analyzers/stages/instinct_stage.py` (NEW), tests |
| T11 | **Register `InstinctStage` in pipeline** | G-3 | T10 | | `analyzers/enrich_single.py` |

**T5 detail**: Shannon entropy `H = -Σ(p * log2(p))` over top-K policy priors from `AnalysisResponse.move_infos[i].prior`. Normalize to 0.0-1.0 range. Config-driven K (default: 10). Return as float.

**T7 detail**: Find position of the correct SGF move in KataGo's `move_infos` list (sorted by visits). Return rank (1-based). Store on `ctx.result.correct_move_rank`. Add to `BatchSummary` in `observability.py`.

**T8 detail**: In `TechniqueStage.run()`, after `run_detectors()`, store `ctx.detection_results = detection_results` instead of only extracting tag slugs. One line change.

**T9 detail**: `classify_instinct(position, analysis_response, config) -> list[InstinctResult]`:
- Identify correct move coordinate from `analysis_response` (top move) or solution tree
- Determine move's relationship to nearby groups using position data:
  - **Push**: Move adjacent to opponent stone, same line, extending toward opponent
  - **Hane**: Move diagonal to own stone, turning corner around opponent
  - **Cut**: Move between two opponent groups (group BFS check)
  - **Descent**: Move one step toward board edge from own stone
  - **Extend**: Move adjacent to own stone, extending along line
- Return list of detected instincts with confidence and evidence
- Config-driven confidence thresholds per instinct type
- **DRY note (RC-2)**: Group BFS / adjacency logic already exists in multiple detectors: `capture_race_detector._find_groups()`, `connect_and_die_detector._NEIGHBORS`, `connection_detector._NEIGHBORS`. Executor should evaluate: (a) extract shared utility to a common module (e.g., `analyzers/board_utils.py`) if reuse exceeds 2 functions, or (b) accept controlled duplication with comments citing detector sources. Prefer option (a) if Cut instinct needs the same BFS as CuttingDetector.

**T10 detail**: `InstinctStage` implementing `EnrichmentStage` protocol. `name = "instinct"`, `error_policy = ErrorPolicy.DEGRADE`. Calls `classify_instinct()`, stores `ctx.instinct_results`.

### Phase 3: Hint & Teaching Integration

| T-ID | Task | Scope | Dependencies | Parallel? | Files |
|------|------|-------|-------------|-----------|-------|
| T12 | **Add instinct config models and level-adaptive templates** | G-3, G-5 | None | [P] | `config/teaching.py`, config JSON |
| T13 | **Modify `TeachingStage` to pass detection + instinct + level to hint/teaching** | G-2, G-3, G-5 | T4, T8, T10, T12 | | `analyzers/stages/teaching_stage.py` |
| T14 | **Add detection evidence to Tier 2 hints in `hint_generator.py`** | G-2 | T13 | [P] | `analyzers/hint_generator.py`, tests |
| T15 | **Add instinct classification to Tier 1 hints and teaching comments** | G-3 | T13 | [P] | `analyzers/hint_generator.py`, `analyzers/teaching_comments.py`, tests |
| T16 | **Add level-adaptive hint content** | G-5 | T12, T13 | [P] | `analyzers/hint_generator.py`, tests |
| T17 | **Update `comment_assembler.py` for 3-layer composition** | G-3 | T15 | | `analyzers/comment_assembler.py`, tests |

**T14 detail**: When `detection_results` are available, use `DetectionResult.evidence` string to enrich Tier 2 reasoning hints. E.g., ladder with evidence "12-step chase confirmed by PV" → "The solution involves a 12-step ladder chase." Fall back to existing generic hints when evidence is absent.

**T15 detail**: When `instinct_results` are available, prefix Tier 1 with instinct phrase. E.g., instinct "push" + technique "ladder" → "Push to force a ladder (shicho)." Teaching comment Layer 0: instinct phrase (≤3 words).

**T16 detail**: Use `get_level_category()` to select template set:
- `beginner`: Tier 2 = tactical consequence ("This captures the group")
- `intermediate`: Tier 2 = intent + position ("Push in the corner to restrict escape")
- `dan`: Tier 2 = reading guidance ("5-move sequence; watch for counter at move 3")

### Phase 4: Calibration & Validation

| T-ID | Task | Scope | Dependencies | Parallel? | Files |
|------|------|-------|-------------|-----------|-------|
| T18 | **Build golden calibration set (≥50 puzzles with manual labels)** | C-3 | T9 | | `tests/fixtures/golden-calibration/` (NEW), JSON labels |
| T19 | **Run instinct classifier calibration (AC-4: ≥70% accuracy)** | AC-4 | T9, T18 | | Calibration script, results |
| T20 | **Run entropy-difficulty correlation (AC-2: Spearman ≥ 0.3)** | AC-2 | T5, T18 | [P] | Calibration script, results |
| T21 | **Tune instinct confidence thresholds based on calibration** | G-3 | T19 | | Config JSON |
| T22 | **Sample review: 10 puzzles per level for hint quality (AC-10)** | AC-10 | T14, T15, T16 | | Manual review |

### Phase 5: Finalization

| T-ID | Task | Scope | Dependencies | Parallel? | Files |
|------|------|-------|-------------|-----------|-------|
| T23 | **Run full regression test suite (AC-9)** | AC-9 | T1-T22 | | `pytest tests/ --cache-clear` |
| T24 | **Update `AGENTS.md`** | Docs | T1-T22 | [P] | `tools/puzzle-enrichment-lab/AGENTS.md` |
| T25 | **Update global docs (`docs/concepts/hints.md`, `docs/how-to/tools/katago-enrichment-lab.md`)** | Docs | T14, T15, T16 | [P] | `docs/concepts/hints.md`, `docs/how-to/tools/katago-enrichment-lab.md` |
| T26 | **Update `70-governance-decisions.md` with plan review results** | Governance | T23 | | Initiative artifacts |

---

## Parallel Execution Map

```
Phase 1 (foundations):
  T1 ─┬─── T2
  T3 ─┴─── T4

Phase 2 (core):
  T5 ──── T6
  T7 ────────────   [P] with T5
  T8 ────────────   [P] with T5, T7
  T9 ──── T10 ── T11

Phase 3 (integration):
  T12 ───────────   [P] with Phase 2
  T13 (waits for T4, T8, T10, T12)
  T14 ─┬─ [P]
  T15 ─┤  [P]
  T16 ─┘  [P]
  T17 (waits for T15)

Phase 4 (calibration):
  T18 ── T19 ── T21
  T20 ──────── [P] with T19

Phase 5 (finalization):
  T23 (waits for all)
  T24 [P]
  T25
```

---

## Definition of Done

- [ ] All 10 acceptance criteria (AC-1 through AC-10) pass
- [ ] `pytest tests/ --cache-clear` from `tools/puzzle-enrichment-lab/` → 100% pass
- [ ] AGENTS.md updated in same commit as structural changes
- [ ] Golden calibration set created with ≥50 puzzles
- [ ] Instinct accuracy ≥ 70% on golden set
- [ ] Entropy Spearman correlation ≥ 0.3 on golden set
- [ ] No existing hint degradation (AC-10 sample review)

---

> **See also**:
> - [30-plan.md](./30-plan.md) — Architecture and data flow details
> - [00-charter.md](./00-charter.md) — Goals and acceptance criteria
> - [25-options.md](./25-options.md) — OPT-2 selection rationale
