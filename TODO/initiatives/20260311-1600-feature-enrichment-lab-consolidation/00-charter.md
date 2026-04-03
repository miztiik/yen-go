# Charter — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

## Initiative ID

`20260311-1600-feature-enrichment-lab-consolidation`

## Problem Statement

The puzzle-enrichment-lab (`tools/puzzle-enrichment-lab/`) has accumulated incomplete work across 6 source documents:
1. **6 KM gate reviews** never signed off (code complete, governance missing)
2. **20 remediation sprint items** implemented but unsigned (governance missing)
3. **5 partially-done perspective-fix tasks** (small code gaps: logging detail, conftest, ko capture verification, dead code cleanup)
4. **2 new algorithmic techniques** from research: Benson's unconditional life gate (R-A-1) and interior-point two-eye exit (R-A-2)
5. **4 missing documentation deliverables** (docs/concepts/quality.md, architecture docs, how-to docs, reference docs)
6. **sgfmill undeclared dependency** in 3 files (replace if feasible)

This fragmentation blocks progress. No single authoritative task list exists.

## Goals

| g_id | goal | source |
|------|------|--------|
| G1 | Implement Benson's unconditional-life pre-query gate in solve_position.py | Research R-A-1 |
| G2 | Implement interior-point two-eye exit check using tsumego_frame boundary | Research R-A-2 |
| G3 | Fix ko detection: add capture verification to `detect_ko_in_pv()` | Perspective T16, Principal P0.1 |
| G4 | Complete 5 partially-done perspective-fix tasks (logging gaps, conftest, ai_solve_active cleanup, level_mismatch removal) | Perspective T9, T11, T14, T19, T20 |
| G5 | Conduct individual gate reviews for 6 KM phases (T017a–T063a) | KM tasks doc |
| G6 | Conduct individual sign-off reviews for 20 remediation sprint items | Remediation sprints doc |
| G7 | Create 4 missing documentation deliverables (S5-G19) | Remediation S5-G19 |
| G8 | Update global docs (architecture, design, concepts, reference) for ALL changes in this initiative | User directive D2 |
| G9 | Remove dead code: `level_mismatch` JSON section, `ai_solve_active` gating variable | Perspective T19, T20, User Q6 |
| G10 | Evaluate and conditionally replace sgfmill with native code | User Q7 |

## Non-Goals

| ng_id | non-goal | rationale |
|-------|----------|-----------|
| NG1 | KataGo performance calibration (S5-G18) | User directive D3: excluded from this initiative |
| NG2 | BitBoard representation replacement | Research rejected: I/O-bound, not CPU-bound |
| NG3 | Full refutation tree upgrade (Principal P1.4) | Larger scope — separate initiative |
| NG4 | Teaching comments upgrade (Principal P2.7) | Larger scope — separate initiative |
| NG5 | Non-19 board hint coordinate fix (Principal P0.3) | Separate concern, not part of tree builder |
| NG6 | Besogo solution tree swap | Frontend concern, separate initiative |
| NG7 | Hinting unification | Separate initiative |
| NG8 | Backend trace search optimization | Backend concern, separate initiative |
| NG9 | YK property reliance for ko bypass | User directive D1: YK is heuristic, not guaranteed |

## Constraints

| c_id | constraint |
|------|-----------|
| C1 | No backward compatibility required — forward only. Re-process all puzzles. |
| C2 | Benson gate must NOT use YK property as ko signal (D1) |
| C3 | Benson gate must handle seki correctly: if result is "dead", fall through to KataGo (Q2-R) |
| C4 | Interior-point check must reuse `tsumego_frame.py` boundary (Q4) |
| C5 | No new external dependencies (Benson implemented in pure Python) |
| C6 | All gate reviews must be individual, not batched (Q8, Q9) |
| C7 | sgfmill replacement only if complexity is manageable (Q7) |
| C8 | No calibration work in scope (D3) |
| C9 | Conceptual reference to tsumego-solver is fine; no code copying (Q3-R) |

## Acceptance Criteria

| ac_id | criterion |
|-------|-----------|
| AC1 | Benson gate correctly classifies unconditionally alive groups as "defender wins" without engine query |
| AC2 | Benson gate falls through to KataGo for seki, ko, and uncertain positions |
| AC3 | Benson gate does NOT use YK property |
| AC4 | Interior-point check correctly identifies positions where defender cannot form two eyes |
| AC5 | Interior-point check uses tsumego_frame.py boundary computation |
| AC6 | Ko detection uses capture verification (stone actually removed), not just coordinate adjacency |
| AC7 | estimate_difficulty logging includes per-component score breakdown |
| AC8 | ko_validation logging includes recurrence details and adjacency check parameters |
| AC9 | conftest.py uses `generate_run_id()` format |
| AC10 | `ai_solve_active` variable removed from enrich_single.py (always-on) |
| AC11 | `level_mismatch` section removed from katago-enrichment.json |
| AC12 | All 6 KM gate reviews individually signed off |
| AC13 | All 20 remediation items individually signed off |
| AC14 | docs/concepts/quality.md updated with Benson gate and interior-point quality signals |
| AC15 | docs/architecture/tools/katago-enrichment.md updated with Benson gate + interior-point |
| AC16 | docs/how-to/tools/katago-enrichment-lab.md updated |
| AC17 | docs/reference/enrichment-config.md updated |
| AC18 | sgfmill either replaced with native code OR evaluated and kept with documented rationale |
| AC19 | All existing tests continue to pass |
| AC20 | New tests written for Benson gate, interior-point check, ko capture verification |

## Scope Summary

**In scope:** Benson gate, interior-point exit, ko capture verification, 5 perspective gaps, 6 KM gate reviews (individual), 20 remediation sign-offs (individual), 4 doc deliverables, global doc updates, dead code removal, sgfmill evaluation.

**Out of scope:** Calibration, BitBoard, refutation tree depth, teaching comments, hint coordinates, frontend, hinting unification, backend trace optimization.

## Research Reference

- Research artifact: `TODO/initiatives/20260310-research-tsumego-solver-pns/15-research.md`
- Planning confidence: 90 | Risk: low
- Key source: David B. Benson (1976) "Life in the Game of Go" — unconditional life algorithm
- Design authority: Kishimoto & Müller (2005) AAAI-05 — df-pn search
