# Clarifications — Enrichment Lab Production Readiness

> Initiative: `20260318-1400-feature-enrichment-lab-production-readiness`
> Last Updated: 2026-03-20
> Status: Round 3 complete — 16/16 resolved + 2 new questions resolved (Q17, Q18). All clarifications closed.

---

## Context

After comprehensive research across 15+ TODO plans, 65+ initiative folders, docs/archive, and the live enrichment lab codebase, we've found:

- **550+ tests passing**, 28 detectors, 12 pipeline stages, 4 phases of refutation quality — all implemented
- **16 features gated/disabled** awaiting calibration benchmarks
- **6-8 computed signals discarded** before reaching SGF output
- **95 calibration fixtures** exist (Cho Chikun 30 elem + 30 inter + 30 adv + 5 ko); **golden-calibration labels.json is empty (0 entries)**
- **4 docs never created** (S5-G19)
- **5 NG items from gogogo research** — 3 correctly deferred, 1 rejected, 1 partially implemented

The enrichment lab is architecturally sound and feature-rich, but sits in an "advanced prototype" limbo where nothing reaches production puzzles because the final-mile wiring (SGF signal output, calibration, feature activation) hasn't been completed.

---

## Round 1: Decision-Critical Questions

### Section A: Scope & Priority

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | What is the primary goal: production-ready enrichment pipeline, or accretive feature additions first? | A: Production pipeline / B: Add more features / C: Both in a single pass | **A** | **C: Both** — production pipeline AND accretive features in a single initiative | ✅ resolved |
| Q2 | Data Liberation: should this be part of this initiative, or is the stalled `20260317-1400-feature-enrichment-data-liberation` initiative the vehicle? | A: Absorb / B: Keep separate / C: Supersede | **C** | **C: Supersede** — this initiative supersedes stalled ones | ✅ resolved |
| Q3 | Which signals should be persisted and where? | A: All to SGF / B: Top 6 to DB attrs / C: Difficulty only | **B** | **Nuanced**: (1) Entropy + correct_move_rank → feed into quality `qk` sub-field in YQ, NOT exposed raw. (2) Add `a:` (avg refutation depth), `b:` (branch count), `t:` (trap density ×100) to YX. (3) `g:` (goal) dropped — redundant with YT tags + puzzle intent. (4) `composite_score` feeds into `YG` (level), NOT quality. Panel-validated algorithm: trap 40%, depth 30%, rank 20%, entropy 10%. | ✅ resolved |

### Section B: Calibration & Activation

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q4 | Are you willing to create/curate a golden set for calibration? | A: Curate manually / B: Auto-generate + spot-check / C: Skip / D: Other | **B** | **D: Check existing** — 95 Cho Chikun fixtures exist at `tests/fixtures/calibration/`. Golden-5 integration tests also exist. User says: check what already exists before adding more. | ✅ resolved |
| Q5 | Feature activation: which gated features should be activated for production? | A: All 16 / B: Proven-safe only / C: None / D: Calibration decides | **D** | **A: Activate all if no conflicts** — governance to decide threshold configuration | ✅ resolved |
| Q6 | Threshold values (t_good=0.05, t_bad=0.15, t_hotspot=0.30) — calibrate before production? | A: Blocker / B: Acceptable / C: Calibrate but don't block | **C** | **Governance decides** — thresholds deferred to governance panel | ✅ resolved |

### Section C: NG Items from GoGoGo Research

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q7 | NG-1 (Priority/urgency scoring on DetectionResult): defer? | A: Defer / B: Implement / C: Research | **A** | **A: Defer** — subsumed/consumed by existing implementation | ✅ resolved |
| Q8 | NG-2 (Static life/death evaluation): adequate as-is? | A: Adequate / B: Full evaluator / C: Pre-filter only | **A** | **A: Adequate** — Benson check + KataGo covers it | ✅ resolved |
| Q9 | NG-3 (Multi-tag evidence layering): worth exploring? | A: Defer / B: Research item / C: Experimental | **B** | **A: Defer** — subsumed/consumed | ✅ resolved |
| Q10 | NG-5 (Alpha-beta capture search): reject? | A: Reject / B: Future option / C: Parallel engine | **A** | **A: Reject** — subsumed by KataGo + KM optimizations | ✅ resolved |

### Section D: Hinting & Documentation

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q11 | Hinting Unification Phase 1 (drift inventory): in scope? | A: Include Phase 1 / B: Separate initiative / C: Full unification | **B** | **C+: Full swap in THIS initiative.** User directive: "Copy backend hints.py into the lab. Combine backend wins. It is only one file, why not bring it up? Mark pipeline hints as superseded. Build interfaces for future swap." NOT a separate initiative. | ✅ resolved |
| Q12 | 4 missing docs from S5-G19: include? | A: All 4 / B: 2 most critical / C: Separate initiative | **A** | **A: All 4** — include quality.md, katago-enrichment architecture, enrichment-lab how-to, enrichment-config reference | ✅ resolved |

### Section E: Governance & Compatibility

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q13 | Is backward compatibility required, and should old code be removed? | A: Compat + remove / B: Compat + keep / C: No compat needed | **A** | **C: No backward compat needed.** Remove unused code but show user which code first. | ✅ resolved |
| Q14 | Should scope include running enrichment on all 2,000 published puzzles? | A: Full re-enrichment / B: New puzzles only / C: Sample first | **C** | **User handles re-enrichment.** All work stays in `tools/puzzle-enrichment-lab/` unless explicitly authorized. | ✅ resolved |

---

## Round 2: Remaining Questions

### Q3 Resolution Analysis — Signal → SGF Property Mapping

User directive: "Maximize SGF output. Pipeline handles DB separately."

This means the enrichment lab should write ALL computed signals to SGF custom properties. The pipeline's publish stage decides what goes into DB-1. The lab doesn't concern itself with DB schema.

**Current SGF output (what `_build_yx()` writes today):**
- `YX` property: `d:{depth};r:{refutations};s:{solution_length};u:{unique}[;w:{wrong_count}]`

**Signals computed but NOT written to SGF:**
- `policy_entropy` (from `estimate_difficulty.py`)
- `correct_move_rank` (from `estimate_difficulty.py`)
- `goal` (from technique detectors)
- `trap_density` (from refutation analysis)
- `composite_score` (from quality scoring)
- `branch_count` (from solution tree)
- `avg_refutation_depth` (the documented `a:` field in YX)

**Proposed: Extend `_build_yx()` to write all computed signals to YX property.**

### Q11 Resolution Analysis — Hinting Unification

## Round 2: Resolved

### Q3 Resolution — Signal → SGF Property Mapping (Panel-Validated)

**User directive**: "Policy entropy should feed into quality, not be exposed directly. Quality subsumes complexity."

**Panel decision (GQ-1/2/3 — unanimous 7/7):**
- YX gets 3 new fields: `a:` (avg refutation depth), `b:` (branch count), `t:` (trap density ×100)
- YQ gets 1 new field: `qk:` (KataGo quality assessment 0-5) from formula: trap 40%, depth 30%, rank 20%, entropy 10%
- `g:` (goal) NOT stored — redundant with YT tags + puzzle intent system
- `composite_score` is DIFFICULTY (→ YG level), NOT quality

### Q11 Resolution — Hinting Consolidation

**User directive**: "Copy backend hints.py into the lab. It's only one file. Combine the backend wins. NOT a separate initiative."

**What gets copied from backend `hints.py` (~900 LOC):**
- Atari relevance gating (board simulation to verify hints)
- Depth-gated Tier 3 coordinate hints
- Solution-aware fallback (`solution_tagger.py` ~100 LOC)
- Structured logging (`HintOperationLog`)
- Liberty analysis for capture-race/ko hints

**What stays from lab `hint_generator.py`:**
- KataGo detection evidence for Tier 2
- Level-adaptive wording (entry/core/strong)
- Instinct phrase prefix (T15)
- Pipe sanitization in output formatter

**Architecture**: Copy code (don't import — `tools/` cannot import `backend/`). Board simulation reimplemented using KataGo position data.

### Q15 — OPP-3 Debug Artifact: Included (user directive)

### Q16 — Small Model: Parked as future work (charter NG-2)

---

## Round 3: Log-Report Feature Scope Extension (GOV-PLAN-REVISE Response)

### Section F: Log-Report Feature + Production Boundary

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q17 | For production default OFF, should backend enforce OFF even if lab config default is ON? | A: Backend hard-forces OFF. B: Backend inherits lab default unless CLI override. C: Environment-based auto profile. Other | **A**, safest operational default and least accidental report generation in production. | **A: Backend hard-forces OFF.** User directive: "Production enforcement: backend hard-forces report OFF by default." | ✅ resolved |
| Q18 | Change-magnitude section policy source for Level 1/2/3 text? | A: Fixed governance glossary in docs. B: Config-driven labels. C: Disabled until separate approval. Other | **C now, then A after approval** to keep semantics stable and auditable. | **C: Disabled until separate governance approval.** User directive: "Change-magnitude glossary: blocked until governance text approval is finalized." | ✅ resolved |

### Log-Report Feature Decisions (Binding)

- **Output format**: Markdown-only report file. No ASCII table rendering. No CSV output.
- **Default matrix**: Lab = ON, Production = OFF.
- **Precedence** (highest to lowest): CLI explicit on/off → env override → profile policy (lab ON, production OFF) → config fallback OFF.
- **Auto-trigger**: Non-blocking at end of enrich and batch runs. Reporter failure must NOT cause enrichment failure.
- **Filename**: Reuse exact timestamp token from enrichment log filename for report filename pairing.
- **Change-magnitude section**: Governance-blocked placeholder until glossary text is approved.
- **Glossary**: Versioned and stable; changes require governance review.

---

## Binding Decisions Summary

| decision_id | decision | source |
|-------------|----------|--------|
| D1 | Both production pipeline + accretive features | Q1:C |
| D2 | This initiative supersedes stalled ones | Q2:C |
| D3 | Signals → YX (a,b,t) + YQ (qk). No raw entropy/rank. No goal. Panel-validated algorithm. | Q3 + GQ-1/2/3 |
| D4 | Use existing 95 Cho Chikun calibration fixtures | Q4 |
| D5 | Activate all features; governance decides sequence/thresholds | Q5:A + Q6 |
| D6 | NG-1: defer, NG-2: adequate, NG-3: defer, NG-5: reject | Q7-Q10 |
| D7 | Copy backend hints.py INTO lab; combine best of both; NOT separate initiative | Q11 (user directive) |
| D8 | Include all 4 missing docs | Q12:A |
| D9 | No backward compatibility; remove unused code after showing user | Q13:C |
| D10 | Re-enrichment is user's responsibility; all work in puzzle-enrichment-lab | Q14 |
| D11 | Scope: ALL work inside `tools/puzzle-enrichment-lab/` unless explicitly authorized | User directive |
| D12 | Include OPP-1 (observability), OPP-2 (rotation tests), OPP-3 (debug artifact) | User directive |
| D13 | Small model: parked as future work | Q16:C |
| D14 | Production enforcement: backend hard-forces log-report OFF regardless of lab default | Q17:A |
| D15 | Change-magnitude levels: disabled until separate governance glossary approval | Q18:C |
| D16 | Log-report feature: markdown-only, no ASCII, no CSV. Lab default ON, production default OFF. | User directive |
| D17 | Log-report auto-trigger: non-blocking at end of enrich/batch run. Reporter failure must NOT fail enrichment. | User directive |
