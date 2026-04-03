# Options — Enrichment Lab Tactical Hints & Detection Improvements

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Last Updated**: 2026-03-15

---

## Context

Charter approved (GOV-CHARTER-APPROVED, 7/7 unanimous). Six goals:
- G-1: Policy entropy as difficulty signal
- G-2: Pass DetectionResult evidence to hint generator
- G-3: Instinct classification for hints and teaching comments
- G-4: Multi-orientation test infrastructure
- G-5: Level-adaptive hint content
- G-6: Top-K rank as observability metric

**Key architecture decisions** identified by governance handover:
1. Instinct classifier placement (new stage vs integrated)
2. DetectionResult propagation mechanism (PipelineContext field vs explicit parameter)
3. Golden set construction methodology
4. Level-adaptive template structure

All options share: zero new KataGo queries (C-1), additive schema changes (C-2), calibration-first (C-3), confined to `tools/puzzle-enrichment-lab/` (C-4).

---

## Option OPT-1: PipelineContext-Enriched (Single Integration Point)

**Approach**: Extend `PipelineContext` to carry `DetectionResult` list and instinct classification alongside existing stage outputs. All new data flows through the context object — stages read from it, teaching/hint stages consume it.

**Architecture**:
```
TechniqueStage
  ├─ Runs 28 detectors → list[DetectionResult]
  ├─ Runs instinct_classifier(position, analysis_response) → list[InstinctResult]
  ├─ Stores ctx.detection_results = [...] (NEW field)
  ├─ Stores ctx.instinct_results = [...] (NEW field)
  └─ Stores ctx.result.technique_tags = [slugs] (existing)

DifficultyStage
  └─ Reads ctx.response.move_infos → compute_entropy() → ctx.result.entropy (additive)

TeachingStage
  ├─ Reads ctx.detection_results (evidence for Tier 2 hints)
  ├─ Reads ctx.instinct_results (instinct for Tier 1 hints + teaching comments)
  ├─ Reads get_level_category(ctx.result.level_slug) (for level-adaptive gating)
  └─ generate_hints(analysis, tags, detections, instincts, level_category)

AssemblyStage
  └─ ctx.result includes entropy, correct_move_rank (AC-8)
```

**Instinct classifier**: New `analyzers/instinct_classifier.py` module called within `TechniqueStage.run()` after detector execution. Classifies move intent by analyzing the correct move's position relative to nearby groups using already-loaded `Position` and `AnalysisResponse`:
- **Push**: Move adjacent to opponent stone on same line → pushes opponent toward edge/center
- **Hane**: Move diagonal to own stones, turning around opponent corner
- **Cut**: Move between two opponent groups (BFS group check, similar to CuttingDetector) 
- **Descent**: Move one intersection closer to edge than own stone (vertical/horizontal step down)
- **Extend**: Move adjacent to own stone, extending group along a line

Returns `list[InstinctResult(instinct: str, confidence: float, evidence: str)]`. Filter to `confidence >= threshold`. Config-driven threshold per instinct.

**Golden set**: Extend existing `tests/fixtures/perf-33/` (33 puzzles) with manual instinct and difficulty labels. Add ~20 more puzzles (total ~53) to meet C-3 (≥50 puzzles). Labels stored as JSON sidecar files alongside SGFs.

**Level-adaptive templates**: New config section in `config/teaching.py` with `LEVEL_HINT_TEMPLATES: dict[str, dict[str, str]]` keyed by `(level_category, hint_tier)`. Teaching stage selects template based on `get_level_category()`.

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Single integration point — `PipelineContext` is the natural carrier for cross-stage data |
| B-2 | No new pipeline stages — instinct runs inside `TechniqueStage`, entropy inside `DifficultyStage` |
| B-3 | Existing stage protocol unchanged — just new fields on context |
| B-4 | `DetectionResult` propagation is trivial — stop discarding, add `ctx.detection_results` field |
| B-5 | Instinct + detection evidence + level category all arrive at TeachingStage together |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | `PipelineContext` grows — 2 new list fields (detection_results, instinct_results) |
| D-2 | TechniqueStage does both detection AND instinct — potentially too much in one stage |
| D-3 | Instinct classifier isn't independently runnable/testable outside the pipeline |

**Risks**:
| R-ID | Risk | Mitigation |
|------|------|------------|
| R-1 | Instinct accuracy < 70% (AC-4) | Calibrate against golden set; tune confidence thresholds per instinct; fall back to "no instinct" gracefully |
| R-2 | Level-adaptive hints degrade for one level category | AC-10: golden set review of 10 samples ensures quality per level |
| R-3 | PipelineContext bloat | 2 list fields is minor; measure serialization overhead in batch |

**Complexity**: Medium. ~200 LOC new code + ~200 LOC tests.
**Rollback**: Remove `ctx.detection_results` / `ctx.instinct_results` fields. TeachingStage reverts to existing behavior.

---

## Option OPT-2: New InstinctStage (Parallel Stage Architecture)

**Approach**: Add a new `InstinctStage` to the pipeline stage list, running AFTER `TechniqueStage` and BEFORE `TeachingStage`. Each new feature (instinct, entropy, Top-K) gets its own stage or is added to the most appropriate existing stage.

**Architecture**:
```
Stages (ordered):
  1. parse_stage          (existing)
  2. validation_stage     (existing)
  3. query_stage          (existing)
  4. analyze_stage        (existing)
  5. technique_stage      (existing — now also stores ctx.detection_results)
  6. instinct_stage       (NEW — instinct_classifier → ctx.instinct_results)
  7. difficulty_stage     (existing — now also computes entropy + Top-K rank)
  8. refutation_stage     (existing)
  9. teaching_stage       (existing — now reads detection_results + instinct_results + level_category)
  10. assembly_stage      (existing)
  11. sgf_writeback_stage (existing)
```

**Instinct classifier**: Same `analyzers/instinct_classifier.py` module but invoked from a dedicated `InstinctStage`. This stage has its own `ErrorPolicy` (CONTINUE — instinct failure doesn't block pipeline).

**DetectionResult propagation**: Same as OPT-1 — `TechniqueStage` stores `ctx.detection_results` instead of discarding.

**Golden set / level-adaptive**: Same as OPT-1.

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Clean stage separation — instinct classification is independently runnable/testable |
| B-2 | ErrorPolicy per stage — instinct failures don't block detection or hints |
| B-3 | GV-5 recommended this approach in consultation: "instinct should be a new detector stage" |
| B-4 | Timing/observability automatic — `StageRunner` tracks per-stage duration |
| B-5 | Naturally extensible — future analysis additions get their own stage |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | New stage file + registration in stage list — more boilerplate |
| D-2 | One extra stage invocation overhead per puzzle (~negligible for pure Python) |
| D-3 | Instinct stage reads same `ctx.position` + `ctx.response` that TechniqueStage already has — slight redundancy in context access pattern |

**Risks**:
| R-ID | Risk | Mitigation |
|------|------|------------|
| R-1 | Stage ordering dependency — instinct needs technique tags for context? | No dependency: instinct classifies from position + analysis, not from tags |
| R-2 | Same AC-4/AC-10 risks as OPT-1 | Same mitigations |

**Complexity**: Medium. ~220 LOC new code (includes stage boilerplate) + ~200 LOC tests.
**Rollback**: Remove `InstinctStage` from stage list. Zero impact on other stages.

---

## Option OPT-3: Detector-Pattern Instinct Classification (28+5 Detectors)

**Approach**: Implement each instinct (push, hane, cut, descent, extend) as a new `TechniqueDetector` subclass within the existing detector infrastructure. Instinct tags are emitted alongside technique tags. The existing `TechniqueStage` → `TeachingStage` pipeline handles them through the same path.

**Architecture**:
```
analyzers/detectors/
  ├─ push_instinct_detector.py    (NEW TechniqueDetector subclass)
  ├─ hane_instinct_detector.py    (NEW)
  ├─ cut_instinct_detector.py     (NEW)
  ├─ descent_instinct_detector.py (NEW)
  ├─ extend_instinct_detector.py  (NEW)
  └─ ... (existing 28 detectors unchanged)

# Instinct detectors emit:
DetectionResult(detected=True, confidence=0.85, tag_slug="instinct:push", evidence="Adjacent push toward edge")
```

**Instinct tags**: Prefixed with `instinct:` (e.g., `instinct:push`) to distinguish from technique tags in the same list. Hint generator checks for `instinct:` prefix and generates instinct-layer hint text.

**DetectionResult propagation**: Same fix as OPT-1/OPT-2 — stop discarding, carry through to TeachingStage.

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Uses existing detector infrastructure — no new stage, no new protocol |
| B-2 | Each instinct independently testable via existing test patterns |
| B-3 | Multi-orientation testing (G-4) automatically applies to instinct detectors too |
| B-4 | Confidence scoring uses existing DetectionResult model |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | Mixes technique and instinct dimensions in the same tag list — conceptually different |
| D-2 | 5 new files in `detectors/` (28→33 detectors) |
| D-3 | `instinct:` prefix is an ad-hoc namespace — not clean in config/tags.json |
| D-4 | Each instinct detector sees only Position + AnalysisResponse individually — can't reason about which instinct is PRIMARY when multiple apply (no cross-instinct ranking) |
| D-5 | Instinct is about the move's INTENT, not the position's PATTERN — forcing it through the detector protocol (which analyzes the position) creates a semantic mismatch |

**Risks**:
| R-ID | Risk | Mitigation |
|------|------|------------|
| R-1 | Tag namespace pollution | `instinct:` prefix convention; separate priority tier in TAG_PRIORITY |
| R-2 | Cross-instinct ranking impossible per detector | Post-filter: pick highest-confidence instinct after all 5 run |
| R-3 | Semantic mismatch leads to unclear API | Accept as trade-off for infrastructure reuse |

**Complexity**: Medium. ~250 LOC (5 detector files) + ~150 LOC tests. More files but simpler per-file.
**Rollback**: Remove 5 detector files from `detectors/`. Zero impact on existing 28.

---

## Recommendation Matrix

| Criterion | OPT-1: PipelineContext | OPT-2: InstinctStage | OPT-3: Detector-Pattern |
|-----------|----------------------|---------------------|------------------------|
| **Architecture clarity** | Good (context carries data) | Best (clean stage separation) | Fair (semantic mismatch) |
| **Instinct testability** | Module-level unit tests | Stage-level + unit tests | Per-detector tests |
| **Error isolation** | Shared with TechniqueStage | Independent ErrorPolicy | Shared with all detectors |
| **Governance alignment** | Partially (GV-5 wanted separate stage) | Full (GV-5 recommended new stage) | Partial |
| **File count** | +1 new module | +2 new modules (classifier + stage) | +5 new files |
| **Stage protocol change** | None — just new ctx fields | New stage registration | None |
| **Semantic correctness** | Good (instinct is NOT a technique) | Best (instinct has own concept space) | Poor (forces instinct through detector protocol) |
| **Cross-instinct ranking** | Natural (classifier returns ranked list) | Natural (stage returns ranked list) | Requires post-filter |
| **Rollback ease** | Remove ctx fields + TeachingStage refs | Remove stage from list | Remove 5 detector files |
| **KISS compliance** | ✅ Minimal new abstractions | ✅ Clean separation | ❌ Overloads detector concept |
| **YAGNI compliance** | ✅ | ✅ | ✅ |
| **Future extensibility** | Good | Best (new stages for new concepts) | Limited (detector pattern has limits) |

**Recommended**: **OPT-2** — New InstinctStage.

**Rationale**: Instinct classification is a conceptually distinct analysis dimension from technique detection — it classifies move INTENT, not position PATTERNS. A dedicated stage:
1. Matches GV-5's explicit recommendation: "instinct should be a new detector stage, not a modification to existing detectors"
2. Provides independent `ErrorPolicy.CONTINUE` — instinct failure doesn't block hints
3. Naturally supports cross-instinct ranking (single classifier returns ranked list)
4. `StageRunner` automatically tracks instinct timing for observability
5. Clean rollback: remove one stage from the ordered list

OPT-1 is close but bundles instinct inside TechniqueStage, violating stage single-responsibility. OPT-3 forces a semantic mismatch — instinct is not a technique, and the `tag_slug` prefix hack (`instinct:push`) is an anti-pattern in the existing tag system.

The remaining features (entropy, DetectionResult propagation, level-adaptive hints, Top-K rank) are identical across all options — they're straightforward additions to existing stages (DifficultyStage for entropy/Top-K, TechniqueStage for DetectionResult retention, TeachingStage for level-adaptive templates).

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Approved goals (G-1 through G-6)
> - [15-research.md](./15-research.md) — Enrichment lab audit and external research cross-reference
> - [70-governance-decisions.md](./70-governance-decisions.md) — Pre-charter consultation + charter approval
