# Governance Decisions — Tactical Analysis Pipeline Wiring

**Initiative**: `20260315-1400-feature-tactical-analysis-wiring`
**Last Updated**: 2026-03-15

---

## Charter Gate — Attempt 1

| Field | Value |
|-------|-------|
| **decision** | `change_requested` |
| **status_code** | `GOV-CHARTER-REVISE` |
| **rc_count** | 8 |
| **key_finding** | Auto-tag wiring IS already implemented at analyze.py L349-358. F-2 and F-5 in research were factually incorrect. |

### Required Changes (All Addressed)

| RC | Requirement | Status |
|----|-------------|--------|
| RC-1 | Reframe G-1: auto-tag wiring is already implemented | ✅ fixed |
| RC-2 | Correct F-2/F-5 in research | ✅ fixed |
| RC-3 | Fix AC-3/AC-4 direction: ladder → LOWER difficulty | ✅ fixed |
| RC-4 | Fix C-4: backward compat for non-tactical; improved for tactical | ✅ fixed |
| RC-5 | Update status.json phase tracking | ✅ fixed |
| RC-6 | Add AC-6 calibration methodology (≥100 puzzles) | ✅ added |
| RC-7 | Clarify G-4: beyond tag-mediated hints | ✅ clarified |
| RC-8 | Resolve Q3-Q8 in clarifications | ✅ all 8 resolved |

---

## Charter Gate — Attempt 2 (APPROVED)

| Field | Value |
|-------|-------|
| **decision** | `approve` |
| **status_code** | `GOV-CHARTER-APPROVED` |
| **unanimous** | `true` (7/7) |

### Member Reviews

| review_id | member | domain | vote | supporting_comment | evidence |
|-----------|--------|--------|------|--------------------|----------|
| GV-1 | Cho Chikun (9p) | Classical tsumego authority | approve | G-1 reframed correctly. AC-3 direction now correct: ladders are forced sequences → easier. C-3 precision-over-recall aligns with teaching principles. | AC-3 verified against Go pedagogy |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | G-4 targets specific tactical context ("ladder extends 5 moves") beyond tag labels. NG-3/NG-7 correctly exclude AI-dependent features. | G-4/AC-4 enrichment specificity |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Clean pipeline/enrichment-lab separation. C-1 zero deps correct — no KataGo in batch pipeline. | Research §3C; C-1; NG-4/NG-5/NG-7 |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Tactical complexity currently computed but discarded — wiring converts wasted computation to learning signal. AC-6 sample size adequate. | GAP-3 code audit; AC-6 methodology |
| GV-5 | Principal Staff Engineer A | Systems architect | approve | C-5 confines changes to backend/puzzle_manager/. ENRICH_IF_ABSENT verified at analyze.py L353. 3 gaps independently testable. | C-1/C-2/C-5 verified; analyze.py code |
| GV-6 | Principal Staff Engineer B | Data pipeline engineer | approve | Zero compute cost: tactical analysis already runs at ~6ms. Research confidence 88/100 appropriate. Governance_history properly tracked. | Performance data; 56 tests confirmed |
| GV-7 | Hana Park (1p) | Player experience | approve | AC-3 corrected direction now pedagogically sound. AC-6 prevents difficulty drift. G-4 hint enrichment improves learning. | Teaching pedagogy; difficulty calibration |

### Support Summary

Unanimous approval. All 8 RCs verified against artifacts and source code. Independent code audits confirmed: auto-tags live at analyze.py L349-358; 3 integration gaps (quality.py, classifier.py, hints.py) are real with zero tactical references; 56 unit tests exist; difficulty direction corrected.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Feature-Planner |
| message | Charter approved unanimously. Proceed to options. The 3 integration gaps are independently scoped. Consider parallel vs sequential wiring strategies. AC-6 measurement framework should be designed early as it gates the classifier change (G-3). |
| required_next_actions | 1. Create 25-options.md with 2-3 implementation approaches. 2. Each option must evaluate: integration order, test strategy, AC-6 timing, difficulty distribution risk. 3. Submit for governance options review. |
| blocking_items | (none) |
