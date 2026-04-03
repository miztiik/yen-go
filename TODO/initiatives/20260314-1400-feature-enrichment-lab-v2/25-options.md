# Options — Enrichment Lab V2

**Initiative**: `20260314-1400-feature-enrichment-lab-v2`  
**Last Updated**: 2026-03-14

---

## Option Evaluation Axes

Per governance RC-1, options MUST evaluate two dimensions:
1. **Delivery strategy**: Phased (correctness → features) vs monolithic (all at once)
2. **Architecture approach**: Minimal cleanup vs moderate restructure vs full annotator redesign

---

## OPT-1: Phased Delivery — Correctness First, Then Features

### Approach Summary

Split the 13 goals into two ordered phases:

**Phase 1 — Correctness (G-2, G-4, G-5, G-6, G-13)**: Remove cropping, fix refutation consistency (framed position), increase visit tiers, pipeline stage cleanup (formalize solve-paths, eliminate double-parsing), KataGo query improvements (reportAnalysisWinratesAs, rootNumSymmetries). All correctness-critical fixes that improve existing enrichment quality without adding new capabilities.

**Phase 2 — Features (G-1, G-3, G-7, G-8, G-9, G-10, G-11, G-12)**: New technique detectors (28 tags), entropy-based ROI module, board-state technique analysis, pattern-based ladder, complexity metric, graceful degradation, HumanSL feature-gate.

### Benefits

| ID | Benefit |
|----|---------|
| B-1 | Correctness fixes ship fast — high-value low-risk improvements to existing enrichment |
| B-2 | Phase 1 can be validated independently before building features on top |
| B-3 | If Phase 2 takes longer, production enrichment is already better from Phase 1 |
| B-4 | Clean foundation (no cropping, consistent queries) makes Phase 2 features easier to build |
| B-5 | Lower risk per delivery — smaller blast radius per phase |

### Drawbacks

| ID | Drawback |
|----|----------|
| D-1 | Two separate review/governance cycles |
| D-2 | Phase 1 removes cropping but doesn't add entropy ROI — temporarily relies on `allowMoves` only for region restriction |
| D-3 | Technique detection stays broken until Phase 2 ships |

### Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Phase 2 deprioritized after Phase 1 ships | Low | Both phases defined up-front with committed scope |
| Phase 1 breaks technique detection further (removing cropping changes policy distribution) | Medium | Phase 1 test suite validates no regression in detectable techniques |

### Complexity: Medium (two deliveries, ~3 weeks total)
### Test Impact: Phase 1 modifies existing tests. Phase 2 adds ~22 new test modules.
### Rollback: Phase 1 independently rollbackable. Phase 2 independently rollbackable.

---

## OPT-2: Monolithic Delivery — All Goals Together

### Approach Summary

Deliver all 13 goals (G-1 through G-13) in a single coordinated implementation. Task ordering respects dependencies (cropping removal before entropy ROI, pipeline cleanup before new detectors) but ships as one atomic set of changes.

### Benefits

| ID | Benefit |
|----|---------|
| B-1 | Single review cycle — one governance approval, one validation |
| B-2 | Entropy ROI (G-3) ships at same time as cropping removal (G-2) — no gap where region restriction is weakened |
| B-3 | New technique detectors can immediately use cropping-free pipeline and increased visits |
| B-4 | Tests written once against final architecture, no intermediate states to maintain |

### Drawbacks

| ID | Drawback |
|----|----------|
| D-1 | Large blast radius — many simultaneous changes increase debugging complexity |
| D-2 | Correctness fixes delayed until all features are ready |
| D-3 | Higher risk of merge conflicts if other lab work proceeds in parallel |
| D-4 | Harder to pinpoint regressions — was it the cropping removal or the new ladder detector? |

### Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Feature scope creep delays correctness fixes | High | Strict task ordering with correctness tasks first in dependency graph |
| 22 new detectors take longer than estimated | High | Accept heuristic quality for context-dependent tags |
| Large PR hard to review | Medium | Internal task checkpoints with intermediate test runs |

### Complexity: High (one large delivery, ~4 weeks)
### Test Impact: All new tests written against final architecture.
### Rollback: All-or-nothing rollback. Cannot partially revert.

---

## OPT-3: Phased Delivery with Integrated Entropy — Recommended

### Approach Summary

Three-phase delivery that moves entropy ROI into Phase 1 alongside correctness fixes, ensuring no gap in region restriction quality:

**Phase 1 — Foundation (G-2, G-3, G-4, G-5, G-6, G-10, G-13)**: Remove cropping, add entropy ROI module (separate file), fix refutation consistency, increase visit tiers, pipeline stage cleanup, modular design enforcement, KataGo query improvements. This phase delivers a working, correct, well-configured pipeline that all future features build on.

**Phase 2 — Detection (G-1, G-7, G-8, G-9, G-11)**: All 28 technique detectors including board-state analysis, pattern-based ladder, complexity metric, graceful degradation. This phase adds the intelligence layer.

**Phase 3 — Stretch (G-12)**: HumanSL feature-gated interface (deferred, ships when model files are available).

### Benefits

| ID | Benefit |
|----|---------|
| B-1 | Phase 1 ships correct AND complete region handling (cropping removed + entropy ROI added simultaneously) |
| B-2 | Phase 2 technique detectors build on a stable, well-tested foundation |
| B-3 | Entropy ROI + frame in Phase 1 enables graceful degradation to be designed correctly from the start |
| B-4 | Phase 3 is independently gated — doesn't block anything |
| B-5 | Each phase has a clear, testable acceptance gate |

### Drawbacks

| ID | Drawback |
|----|----------|
| D-1 | Phase 1 is larger than OPT-1's Phase 1 (adds entropy ROI) |
| D-2 | Three phases means three review checkpoints |
| D-3 | Technique detection still delayed to Phase 2 |

### Risks

| Risk | Level | Mitigation |
|------|-------|------------|
| Entropy ROI in Phase 1 increases Phase 1 scope | Low | Entropy ROI is ~100 lines (H formula + region computation). Well-bounded. |
| Phase 2 detection work is still ambitious | Medium | Prioritize by corpus frequency. Tiered quality expectations for context-dependent tags. |

### Complexity: Medium (three phases, ~4-5 weeks total but with intermediate checkpoints)
### Test Impact: Phase 1 modifies and adds tests. Phase 2 adds ~22 test modules. Phase 3 adds ~2 test modules.
### Rollback: Each phase independently rollbackable.

---

## Comparison Matrix

| Dimension | OPT-1 (Phased Correctness-First) | OPT-2 (Monolithic) | OPT-3 (Phased + Entropy) |
|-----------|-----------------------------------|--------------------|--------------------------| 
| Delivery speed for correctness | **Fast** (Phase 1 only) | Slow (waits for all) | **Fast** (Phase 1) |
| Region restriction gap | Yes (between cropping removal and entropy ROI) | No gap | **No gap** |
| Blast radius per delivery | Small | **Large** | Small |
| Debugging complexity | Low | **High** | Low |
| Foundation quality for features | Good | Good | **Best** (entropy + frame ready) |
| Total effort | ~3 weeks | ~4 weeks | ~4-5 weeks |
| Rollback granularity | 2 rollback points | 1 rollback point | **3 rollback points** |
| Governance overhead | 2 cycles | 1 cycle | 3 cycles |
| Risk level | Low-Medium | High | **Low** |

---

## Architecture Compliance

All three options comply with:
- C-3: `tools/` isolation maintained
- C-5: Config-driven thresholds
- C-7: SRP / modular files (each feature in own file)
- GPL compliance for Lizgoban (clean-room implementation)
- MIT compliance for KaTrain (attribution)

---

## Recommendation

**OPT-3 (Phased Delivery with Integrated Entropy)** is the recommended option.

**Rationale**: It combines the low-risk phased approach of OPT-1 with the region-restriction completeness of OPT-2. Moving entropy ROI into Phase 1 eliminates the gap where region restriction would be weakened (user explicitly asked for entropy-based ROI as the replacement for cropping). The third phase cleanly isolates the deferred HumanSL work. Each phase has a clear, testable acceptance gate and can be independently rolled back.
