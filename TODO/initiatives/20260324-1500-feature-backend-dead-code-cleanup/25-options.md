# Options — Backend Dead Code Cleanup Post-Recovery

**Initiative**: 20260324-1500-feature-backend-dead-code-cleanup  
**Last Updated**: 2026-03-24

---

## Context

This initiative deletes ~13,390 lines of dead/obsolete content across ~48 files. User selected multi-phase execution (Q6:C). The question is **how to structure the phases** for maximum safety, independent verifiability, and governance review quality.

All options share identical scope — they differ only in **execution sequencing and risk grouping**.

---

## Options Matrix

| Attribute | OPT-1: 3-Phase Risk-Layered | OPT-2: 2-Phase Code-Then-Docs | OPT-3: 4-Phase Granular |
|-----------|---------------------------|-------------------------------|------------------------|
| **Approach** | Phase 1: Dead core modules + orphan tests. Phase 2: Adapter cleanup + `__init__.py` edit. Phase 3: Vestigial code + docs. | Phase 1: All dead code + adapters. Phase 2: All docs + vestigial code. | Phase 1: Dead core only. Phase 2: Orphan tests. Phase 3: Adapter cleanup. Phase 4: Docs + vestigial. |
| **Benefits** | Risk increases gradually; each phase is independently meaningful; clear failure isolation | Simpler 2-phase review; code review and docs review naturally separated | Maximum granularity; smallest blast radius per step |
| **Drawbacks** | 3 governance gates | Phase 1 is large (all code); adapter `__init__.py` edit mixed with core deletions | 4 governance gates; orphan test phase has no code change |
| **Risk Level** | Low per phase | Medium (Phase 1 is broad) | Low per phase but excessive overhead |
| **Test Isolation** | Excellent — each phase has self-contained test impact | Good — but harder to attribute test failures in Phase 1 | Excellent but Phase 2 (test-only deletion) has no code to verify |
| **Rollback** | Phase-level rollback via git branch | Phase-level but Phase 1 rollback reverses most work | Phase-level with fine granularity |
| **Governance Overhead** | 3 gates (balanced) | 2 gates (minimal) | 4 gates (heavy) |
| **Architecture Compliance** | ✅ Matches correction-levels L4 "Phased Execution" | ✅ Valid but less incremental | ✅ But over-engineered |
| **Test Strategy** | Before/after baseline at each phase; orphan test deletion in Phase 1 with their source code | Before/after baseline at each phase; orphan tests deleted with source code | Before/after baseline; orphan tests separate from source deletion (risky — tests may fail before their source is deleted) |

---

## Detailed Option Descriptions

### OPT-1: 3-Phase Risk-Layered (Recommended)

**Phase 1 — Dead Core Modules** (~8,920 lines):
- Delete 13 dead production files (~3,225 lines)
- Delete ~18 orphan test files that test only these modules (~5,695 lines)
- Gate: `pytest backend/ -m "not (cli or slow)"` passes, test count reduced by ~orphan count

**Phase 2 — Adapter Cleanup** (~2,682+ lines):
- Delete old adapter infra (`base.py`, `registry.py`)
- Delete 14 flat-file adapters + ghost `ogs/` directory
- Edit `adapters/__init__.py`: remove `UrlAdapter` import (L27) + `__all__` entry
- Gate: Tests pass + `python -m backend.puzzle_manager sources` lists only live adapters

**Phase 3 — Vestigial Code + Docs** (~23 files):
- Remove `StageContext.views_dir` (~3 lines)
- Delete/archive 5 obsolete docs
- Fix 18 stale docs
- Fix AGENTS.md (Typer→argparse, url/ ghost reference)
- Gate: Tests pass + docs content review

**Rationale**: Each phase removes a *semantically cohesive* group. Core modules have zero production imports — safest first. Adapter cleanup is slightly riskier (the `__init__.py` edit). Docs last because zero code risk.

### OPT-2: 2-Phase Code-Then-Docs

**Phase 1 — All Dead Code** (~11,602 lines):
- Everything from OPT-1 Phases 1+2 combined
- Delete 13 dead production files + 14 flat-file adapters + old adapter infra + orphan tests + ghost dir
- Edit `adapters/__init__.py`
- Remove `StageContext.views_dir`

**Phase 2 — All Docs** (~23 files):
- Fix all documentation

**Rationale**: Faster execution (2 phases). But Phase 1 is large — if tests fail, harder to identify which deletion caused it.

### OPT-3: 4-Phase Granular

**Phase 1**: Delete 13 dead production files only  
**Phase 2**: Delete ~18 orphan test files  
**Phase 3**: Adapter cleanup (14 files + `__init__.py` edit + ghost dir)  
**Phase 4**: Vestigial code + all docs

**Rationale**: Maximum isolation. But Phase 2 (test-only deletion) is awkward — some orphan tests may import dead code that was already deleted in Phase 1, requiring careful ordering. Also excessive governance overhead.

---

## Recommendation

**OPT-1 (3-Phase Risk-Layered)** is recommended because:

1. **Risk layering**: Each phase has a clear, increasing risk profile (core→adapters→docs)
2. **Semantic cohesion**: Each phase is a self-contained logical unit
3. **Test attribution**: If a phase breaks tests, the cause is clear
4. **Orphan co-deletion**: Deleting orphan tests WITH their source code (Phase 1) avoids the "dangling test" problem of OPT-3
5. **Governance efficiency**: 3 gates is balanced — meaningful review without review fatigue
6. **Matches user preference**: User selected "multiple phases as required" (Q6:C)
7. **Aligns with charter**: This is the phasing strategy already documented in `00-charter.md` §6

---

## Evaluation Criteria

| Criterion | Weight | OPT-1 | OPT-2 | OPT-3 |
|-----------|--------|-------|-------|-------|
| EC-1: Failure isolation | High | ✅ Excellent | ⚠️ Moderate | ✅ Excellent |
| EC-2: Governance efficiency | Medium | ✅ 3 gates | ✅ 2 gates | ⚠️ 4 gates |
| EC-3: Test attribution clarity | High | ✅ Clear per-phase | ⚠️ Mixed in Phase 1 | ⚠️ Phase 2 awkward |
| EC-4: Semantic cohesion | Medium | ✅ Each phase is logical | ✅ Code vs docs | ⚠️ Phase 2 is just tests |
| EC-5: Rollback granularity | Medium | ✅ Phase-level | ⚠️ Phase 1 too large | ✅ Fine-grained |
| EC-6: Architecture compliance | Low | ✅ Matches L4 | ✅ Valid | ✅ Valid |
