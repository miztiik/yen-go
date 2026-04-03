# Analysis — Enrichment Lab Tactical Hints & Detection Improvements

**Initiative**: `20260315-1700-feature-enrichment-lab-tactical-hints`
**Last Updated**: 2026-03-15

---

## 1. Planning Confidence

| Metric | Value | Rationale |
|--------|-------|-----------|
| **Planning Confidence Score** | 82/100 | -5 novel instinct classification, -5 hint interface change, -3 stage boundary change, -5 new test infrastructure |
| **Risk Level** | medium | New detection capability + hint architecture expansion |
| **Research invoked** | Yes | Feature-Researcher + Deep Audit + Governance Panel |

---

## 2. Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | downstream | AiAnalysisResult schema | Low | New fields additive; existing consumers unaffected (C-2) | T5, T7 | ✅ addressed |
| RE-2 | lateral | PipelineContext fields | Low | Context is in-memory, not serialized; None defaults | T4 | ✅ addressed |
| RE-3 | downstream | hint_generator interface | Medium | Backward-compatible: new params optional with None defaults | T13, T14 | ✅ addressed |
| RE-4 | downstream | teaching_comments interface | Medium | Backward-compatible: instinct is additive Layer 0 (≤3 words) | T15, T17 | ✅ addressed |
| RE-5 | lateral | comment_assembler 15-word cap | Low | Instinct phrase ≤3 words; overflow strategy already handles excess | T17 | ✅ addressed |
| RE-6 | lateral | existing 28 detectors | None | Zero modifications to any detector (NG-4) | — | ✅ addressed |
| RE-7 | lateral | config/teaching-comments.json | Low | Additive: new instinct template section; existing templates unchanged | T12 | ✅ addressed |
| RE-8 | upstream | KataGo engine queries | None | Zero new queries (C-1); all data from existing AnalysisResponse | — | ✅ addressed |
| RE-9 | lateral | Multi-orientation test bugs | High (intentional) | Multi-orientation tests (T2) may reveal existing detector bugs; fixing them is the purpose | T2 | ✅ addressed |
| RE-10 | downstream | difficulty model weights | Medium | Entropy weight calibrated against golden set before production (C-3, T20) | T20, T21 | ✅ addressed |
| RE-11 | lateral | BatchSummary (observability) | Low | Additive field: correct_move_rank | T7 | ✅ addressed |
| RE-12 | lateral | AGENTS.md | Low | Updated in same commit as structural changes (T24) | T24 | ✅ addressed |
| RE-13 | downstream | backend pipeline (out of scope) | None | C-4: changes confined to tools/puzzle-enrichment-lab/ | — | ✅ addressed |

---

## 3. Charter/Plan/Task Consistency

| F-ID | Finding | Severity | Resolution |
|------|---------|----------|------------|
| F-1 | All 6 charter goals (G-1 through G-6) have corresponding tasks | ✅ Pass | G-1→T5+T6, G-2→T8+T13+T14, G-3→T3+T9+T10+T11+T15, G-4→T1+T2, G-5→T12+T16, G-6→T7 |
| F-2 | All 10 acceptance criteria have verification tasks | ✅ Pass | AC-1→T6, AC-2→T20, AC-3→T14, AC-4→T19, AC-5→T15, AC-6→T2, AC-7→T16, AC-8→T7, AC-9→T23, AC-10→T22 |
| F-3 | All 7 constraints are respected in plan | ✅ Pass | C-1 through C-7 verified against task scope |
| F-4 | 8 non-goals are not addressed by any task | ✅ Pass | NG-1 through NG-8 excluded |
| F-5 | Stage ordering matches actual code | ✅ Pass | Plan §1 uses real ordering from enrich_single.py L189-199 |
| F-6 | Must-hold constraints from options election addressed | ✅ Pass | MH-1→T10 (DEGRADE), MH-2→T4, MH-3→Plan §1, MH-4→T9, MH-5→T18-T21 |
| F-7 | Task dependencies are acyclic | ✅ Pass | Parallel map in 40-tasks.md shows valid DAG |
| F-8 | Documentation tasks included | ✅ Pass | T24 (AGENTS.md update) |
| F-9 | Calibration tasks before production weighting | ✅ Pass | T18→T19→T21 (instinct); T18→T20 (entropy); both before T23 regression |
| F-10 | Backward compatibility verified | ✅ Pass | All new parameters use Optional/None defaults; no schema version bump needed |

---

## 4. Coverage Map

| Area | Covered By | Status |
|------|-----------|--------|
| Policy entropy as difficulty signal | T5, T6, T20 | ✅ |
| DetectionResult evidence pipeline | T4, T8, T13, T14 | ✅ |
| Instinct classification | T3, T9, T10, T11, T15 | ✅ |
| Multi-orientation testing | T1, T2 | ✅ |
| Level-adaptive hints | T12, T16 | ✅ |
| Top-K rank observability | T7 | ✅ |
| Golden set calibration | T18, T19, T20, T21, T22 | ✅ |
| Regression testing | T23 | ✅ |
| Documentation | T24 | ✅ |
| Governance closeout | T25 | ✅ |

**Unmapped tasks**: None. All 25 tasks trace to charter goals.

---

## 5. External Reference Digest Verification

| Reference | Digested | Cross-Referenced | Finding |
|-----------|----------|-----------------|---------|
| `sensei_instincts.py` (gogogo) | ✅ | XR-1: 8 instincts → 5 tsumego-relevant selected | Instinct classification (G-3) |
| `tactics.py` (gogogo) | ✅ | XR-3, XR-4: 17/28 detectors already use board-sim | Validates NG-3 (no parallel board-sim) |
| `test_instincts.py` (gogogo) | ✅ | XR-2: multi-orientation methodology | G-4 (multi-orientation tests) |
| `compare_moves.py` (gogogo) | ✅ | XR-6: Top-K rank accuracy | G-6 (observability metric) |
| `gogogo-tactics.md` (attached) | ✅ | Algorithm descriptions for clean-room | Research §4 |
| `gogogo-instincts.md` (attached) | ✅ | 8 instinct definitions | G-3 instinct selection |
| `gogamev4-analysis.md` (attached) | ✅ | Mistake classification → deferred (NG-2) | Research §4, Tier 3 |
| `gogamev4-territory.md` (attached) | ✅ | Eye/seki/territory → covered by existing detectors | Research XR-5, XR-9, XR-10 |
| `training/` directory (gogogo) | ✅ | Feature-Researcher full exploration | Research R-1 |

All 9 previously provided materials have been digested and cross-referenced with the enrichment lab's actual implementation.

---

> **See also**:
> - [15-research.md](./15-research.md) — Full cross-reference table (XR-1 through XR-15)
> - [40-tasks.md](./40-tasks.md) — Task dependency graph
> - [30-plan.md](./30-plan.md) — Architecture and data flow
