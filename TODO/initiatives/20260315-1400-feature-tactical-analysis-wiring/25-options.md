# Options — Tactical Analysis Pipeline Wiring

**Initiative**: `20260315-1400-feature-tactical-analysis-wiring`
**Last Updated**: 2026-03-15

---

## Context

Charter approved (GOV-CHARTER-APPROVED, unanimous). Three integration gaps confirmed:

1. **quality.py** — `compute_puzzle_quality_level()` takes only `SGFGame`, scores based on `has_solution`, `refutation_count`, `comment_level`. No tactical input.
2. **classifier.py** — `classify_difficulty()` takes only `SGFGame`, scores based on `depth`, `variations`, `stones`, `board_size`. No tactical input.
3. **hints.py** — `HintGenerator.generate_*()` takes `tags` + `SGFGame`, uses tag-mediated lookup only. No `TacticalAnalysis` parameter.

All three read from `SGFGame` but not from `TacticalAnalysis`. The wiring point is `stages/analyze.py` (lines 340-400) where `tactical_analysis` is already computed and `auto_tags` are already merged.

**Available TacticalAnalysis signals** (from `core/tactical_analyzer.py`):
- `has_ladder: LadderResult | None` — includes `length`, `has_breaker`, `breaker_point`
- `has_snapback: bool`
- `capture_type: CaptureType` (NONE, SIMPLE, APPROACH, SQUEEZE)
- `has_seki: bool`
- `instinct: InstinctType | None`
- `player_weak_groups: list[WeakGroup]` — includes `liberties`, `size`, `eye_count`
- `opponent_weak_groups: list[WeakGroup]`
- `tactical_complexity: int` (0-6 scale)
- `position_valid: bool`
- `validation_notes: list[str]`

---

## Option OPT-1: Pass-Through Parameter Injection

**Approach**: Extend the signatures of `classify_difficulty()`, `compute_puzzle_quality_level()`, and `HintGenerator.generate_*()` to accept an optional `TacticalAnalysis` parameter. Wire in `stages/analyze.py` at the existing call sites.

**Architecture**:
```
stages/analyze.py
  ├─ L330: level = classify_difficulty(game, tactical_analysis=tactical_analysis)
  ├─ L395: quality = compute_quality_metrics(game, tactical_analysis=tactical_analysis)
  └─ L410: hints = hint_gen.generate_hints(tags, game, tactical_analysis=tactical_analysis)
```

Each consumer module gets an `Optional[TacticalAnalysis] = None` parameter. When `None`, behavior is identical to current (zero regression). When provided, the module uses the signals:

- **classifier.py**: Ladder → score -1 (forced sequence = easier). Seki/weak groups → score +1. Tactical complexity 4+ → score +1.
- **quality.py**: Validation notes (broken position) → quality cap at 2. Tactical complexity ≥ 3 → quality boost +1 (richer puzzle).
- **hints.py**: Ladder → "The ladder extends {length} moves" in YH2. Snapback → "After the capture, recapture the {count} stones". Weak groups → "The opponent's group has only {liberties} liberties".

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Minimal code change — add 1 optional parameter per function (~15 lines each) |
| B-2 | Zero regression risk — `None` default preserves all existing behavior |
| B-3 | No new modules/classes/abstractions |
| B-4 | Each integration independently testable and independently deployable |
| B-5 | No schema changes — tactical signals feed into existing YQ/YG/YH properties |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | Caller (analyze.py) must thread the `tactical_analysis` variable to each call site |
| D-2 | If more consumers appear later, each needs the parameter added manually |
| D-3 | Dual-API surface: some callers pass `tactical_analysis`, others don't |

**Risks**:
| R-ID | Risk | Mitigation |
|------|------|------------|
| R-1 | Difficulty scores shift for tactical puzzles | AC-6 measurement framework logs before/after for ≥100 puzzles |
| R-2 | Quality boost false positives (complexity ≥ 3 but poor puzzle) | Cap quality at refutation-based tier (never exceed structural quality) |
| R-3 | Hint text too verbose (ladder sequence detail) | Max hint length enforced by existing YH compact format (128 chars) |

**Complexity**: Low. ~50 lines of logic + ~100 lines of tests per module.  
**Test impact**: Add parametrized tests per module. No test infrastructure changes.  
**Rollback**: Remove optional parameter; callers revert to `None` default. Zero-risk rollback.  
**AC-6 timing**: Measurement framework built as first task, runs before/after classifier change.

---

## Option OPT-2: Enrichment Context Object

**Approach**: Create a lightweight `EnrichmentContext` dataclass that bundles `SGFGame` + `TacticalAnalysis` + `tags` + metadata. All enrichment functions accept `EnrichmentContext` instead of individual parameters.

**Architecture**:
```
core/enrichment_context.py (NEW)
  └─ @dataclass EnrichmentContext:
       game: SGFGame
       tactical_analysis: TacticalAnalysis | None
       tags: list[str]
       puzzle_id: str

stages/analyze.py
  └─ ctx = EnrichmentContext(game, tactical_analysis, tags, puzzle_id)
     level = classify_difficulty(ctx)
     quality = compute_quality_metrics(ctx)
     hints = hint_gen.generate_hints(ctx)
```

Each consumer accesses `ctx.tactical_analysis` as needed. If `None`, falls back to current behavior.

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Single parameter for all enrichment context — cleaner signatures as features grow |
| B-2 | Future-proof: adding signals means updating the context, not every function signature |
| B-3 | Self-documenting: `EnrichmentContext` makes the data flow explicit |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | New abstraction layer for 3 consumers — YAGNI concern |
| D-2 | Requires refactoring ALL callers of classify_difficulty, quality, hints to pass context |
| D-3 | Existing tests that call these functions directly need adapter or context construction |
| D-4 | Creates coupling between all enrichment modules via shared context type |
| D-5 | Violates KISS — the problem is 3 optional parameters, not a data-threading problem |

**Risks**:
| R-ID | Risk | Mitigation |
|------|------|------------|
| R-1 | Context object grows into god-object | Lint rule: max 6 fields on EnrichmentContext |
| R-2 | Breaking change for all existing callers | Keep old signatures as deprecated wrappers |
| R-3 | Same difficulty/quality/hint risks as OPT-1 | Same mitigations apply |

**Complexity**: Medium. New file + refactor 3 modules + update ~30 test callsites.  
**Test impact**: All existing test callsites must construct `EnrichmentContext`. Moderate friction.  
**Rollback**: Delete context class, revert to individual parameters. Medium effort.  
**AC-6 timing**: Same as OPT-1.

---

## Option OPT-3: Staged Sequential Rollout (Classifier-First)

**Approach**: Same technical mechanism as OPT-1 (optional parameter injection), but executed in 3 strict sequential phases with measurement gates between each.

**Execution order**:
1. **Phase A: Classifier** (G-3 + AC-6) — Add tactical signals to classifier. Run AC-6 measurement on ≥100 puzzles. Gate: difficulty shifts are pattern-appropriate (ladder → easier, seki → harder).
2. **Phase B: Quality** (G-2) — Add tactical complexity + validation to quality. Gate: AC-1/AC-2 pass.
3. **Phase C: Hints** (G-4) — Add tactical-detail hints to HintGenerator. Gate: AC-4 pass.
4. **Phase D: Validation** (G-1 + G-5) — Write end-to-end integration tests for existing auto-tag wiring + measurement summary.

**Benefits**:
| B-ID | Benefit |
|------|---------|
| B-1 | Smallest possible blast radius per phase |
| B-2 | AC-6 measurement gates the riskiest change (classifier) |
| B-3 | Each phase is independently reviewable and revertable |
| B-4 | Difficulty calibration verified before quality/hints depend on it |

**Drawbacks**:
| D-ID | Drawback |
|------|----------|
| D-1 | 4 separate review/merge cycles instead of 1 |
| D-2 | Same technical mechanism as OPT-1 — phases add process overhead, not technical value |
| D-3 | Phases B and C don't depend on Phase A (they're independent consumers) — sequencing is artificial |

**Risks**: Same as OPT-1. Sequential gates add time but not risk reduction beyond OPT-1's `None`-default safety.

**Complexity**: Same as OPT-1 per module. Higher process overhead.  
**Test impact**: Same as OPT-1.  
**Rollback**: Same as OPT-1 (per-phase revert).

---

## Recommendation Matrix

| Criterion | OPT-1: Pass-Through | OPT-2: Context Object | OPT-3: Staged Sequential |
|-----------|---------------------|----------------------|--------------------------|
| **Code complexity** | Low (~50 LOC/module) | Medium (~150 LOC + new file) | Low (~50 LOC/module) |
| **Regression risk** | None (`None` default) | Low (wrapper compat) | None (`None` default) |
| **Test friction** | Low (add params) | Medium (refactor ~30 callsites) | Low (add params) |
| **Rollback effort** | Trivial | Medium | Trivial per phase |
| **YAGNI compliance** | ✅ Minimal | ❌ Premature abstraction | ✅ Minimal |
| **KISS compliance** | ✅ Simple | ❌ Over-engineered for 3 consumers | ✅ Simple |
| **Future extensibility** | Moderate | High | Moderate |
| **Process overhead** | Low (1 PR) | Low (1 PR) | High (4 PRs) |
| **AC-6 measurement timing** | First task, before all wiring | First task, before all wiring | Built into Phase A gate |
| **Architecture alignment** | ✅ No new abstractions | ❌ New shared type in core/ | ✅ No new abstractions |

**Recommended**: **OPT-1** — Pass-Through Parameter Injection.

**Rationale**: The problem is straightforwardly "3 functions need 1 more input." OPT-1 solves it with minimum abstraction. The `None`-default pattern means zero regression. OPT-2 violates YAGNI (a context object for 3 consumers). OPT-3 has the same technical mechanism as OPT-1 but adds unnecessary sequential process gates — the 3 integrations are independent (no dependency between classifier, quality, and hints) so sequencing them provides no risk reduction beyond OPT-1's `None`-default safety.

AC-6 measurement framework should still be built first regardless of option — it gates the classifier change and provides evidence for governance.

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Approved scope (G-1 through G-5)
> - [15-research.md](./15-research.md) — Gap analysis and TacticalAnalysis dataclass details
> - [70-governance-decisions.md](./70-governance-decisions.md) — Charter approval decision
