# Research Brief: Most Accretive Addition to the Puzzle Enrichment Lab

> **Last Updated**: 2026-03-17
> **Initiative**: `20260317-research-capability-audit`
> **Artifact**: `15-research-enrichment-lab-accretion.md`
> **Status**: Complete

---

## 1. Research Question and Boundaries

**Question**: Of five candidate capabilities (H1–H5), which single addition to the Puzzle Enrichment Lab would deliver the highest ratio of user-facing value to implementation cost, given existing architecture, signal inventory, and schema constraints?

| q_id | Hypothesis | Short Description |
|------|------------|-------------------|
| H1 | Multi-Dimensional Skill Fingerprinting | Replace scalar level with a vector of per-technique skill dimensions |
| H2 | Automated Difficulty Self-Calibration Loop | Closed feedback loop: run calibration fixtures → compare → auto-adjust weights |
| H3 | Cross-Puzzle Positional Similarity Indexing | Find "similar puzzles" via structural board hashing |
| H4 | Pedagogical Prerequisite Graph | DAG of technique dependencies enabling curriculum ordering |
| H5 | Enrichment Quality Self-Assessment | Per-puzzle confidence/completeness score based on solve metrics |

**Success Criteria**: Identify the candidate with (a) highest existing signal coverage, (b) lowest new-infrastructure requirement, (c) greatest frontend unlocking potential, and (d) strongest alignment with existing TODO plans.

**Boundaries**: Research covers the enrichment lab (`tools/puzzle-enrichment-lab/`), the backend pipeline (`backend/puzzle_manager/`), and frontend consumption (`frontend/src/`). External solver improvements (KataGo tuning, PNS search) are out of scope.

---

## 2. Internal Code Evidence

### 2A. Signal Inventory — Computed but NOT in Final Output

The enrichment lab computes far more data than it persists. This "signal gap" is the key finding:

| R-1 | Signal | Computed In | Stored In Final Output? | Notes |
|-----|--------|------------|------------------------|-------|
| R-2 | Difficulty components: policy (15%), visits (15%), trap (20%), structural (35%), complexity (15%) | `estimate_difficulty.py` | **NO** — only composite `raw_difficulty_score` survives to `DifficultySnapshot` | Logged but discarded |
| R-3 | `policy_entropy` (Shannon entropy, normalized 0-1) | `compute_policy_entropy()` in `estimate_difficulty.py` | **NO** | Computed, never stored |
| R-4 | `correct_move_rank` (rank of correct move among KataGo candidates) | `find_correct_move_rank()` in `estimate_difficulty.py` | **NO** | Computed, never stored |
| R-5 | `TreeCompletenessMetrics` (completed_branches, simulation_hits/misses, transposition_hits, forced_move_count, max_resolved_depth) | `solve_result.py` | **NO** — per-solve-run only | Rich solve quality data, discarded after run |
| R-6 | `EntropyROI` (contested_region, bounding_box, mean_entropy) | `entropy_roi.py` | **NO** — ROI detection only | Spatial entropy data, not stored |
| R-7 | `per_move_accuracy` | `ai_analysis_result.py` field | **Nullable, usually None** | Exists in model but rarely populated |
| R-8 | `MoveClassification` (quality, delta, policy, rank, score_lead) | `solve_result.py` | **NO** — per-move detail discarded | Available during analysis only |
| R-9 | `phase_timings` | `ai_analysis_result.py` | **NO** — runtime metric only | |
| R-10 | `goal`, `goal_confidence` | `ai_analysis_result.py` | **NO** | Inferred puzzle objective |
| R-11 | `tree_truncated`, `co_correct_detected`, `queries_used` | `ai_analysis_result.py` | **NO** | Solve process metadata |
| R-12 | `instinct_classifier` output (push/hane/cut/descent/extend) | `instinct_classifier.py` | **Unclear** — may feed into technique_tags | Geometry-based classification |
| R-13 | `BatchSummary` (disagreement rates, PI-1/PI-3, correct_move_ranks) | `observability.py` | **Batch-level only**, not per-puzzle | |
| R-14 | `enrichment_quality_level`, `enrichment_tier` | `ai_analysis_result.py` | **NO** | Internal enrichment status |

### 2B. What Reaches the Final Output

**SGF Properties** (via `sgf_enricher.py` `_build_yx()`):
- `YX[d:depth;r:refutations;s:solution_length;u:unique;w:wrong_count]` — **5 metrics only**
- `YG` (level slug), `YQ` (quality+ac), `YT` (technique tags), `YH` (hints), `YO` (move order), `YC` (corner), `YK` (ko context), `YR` (refutation coords)

**DB-1 (Browser)** (from `sqlite-index-architecture.md`):
- `puzzles` table: `content_hash, batch, level_id, quality, content_type, cx_depth, cx_refutations, cx_solution_len, cx_unique_resp, ac`
- **`attrs` TEXT column** — JSON blob for extensible metadata (exists but currently unused)
- `puzzle_tags` table — many-to-many (all numeric IDs)

**Frontend** (from `entryDecoder.ts`, `puzzleQueryService.ts`):
- Decodes: `depth, refutations, solutionLength, uniqueResponses` (4 complexity fields)
- `attrs` string exists in `PuzzleRow` type but `entryDecoder.ts` does **not** decode it
- Filters: `levelId, tagIds, collectionId, quality, contentType, minDepth, maxDepth`

### 2C. Config System Findings

**`puzzle-levels.json`**: 9 levels with sparse IDs (110-230). Flat scalar — **no skill dimensions, no technique awareness**. Each level is slug + name + rankRange.

**`tags.json`** (v8.3): 28 tags in 3 categories (objective/tesuji/technique). Rich alias system with Sensei's Library URLs. **No prerequisite relationships between tags. No skill-dimension mapping.**

**`katago-enrichment.json`** (v1.21): Calibration section has `fixture_dirs` (cho-elementary/intermediate/advanced), `surprise_weighting` (disabled), `surprise_weight_scale` 2.0. Elo-anchor uses CALIBRATED_RANK_ELO table (18k to 5d). **No automated calibration loop — only manual fixture-based test config.**

### 2D. Existing TODO & Architecture Alignment

| R-15 | TODO/Plan | Relevant To | Status |
|------|-----------|-------------|--------|
| R-16 | `003-d2-classifier-research.md` — audits current 4-feature additive classifier, documents 5 fundamental limitations | H1, H2 | Research complete, improvement **explicitly deferred** |
| R-17 | `002-implementation-plan-strategy-d.md` — position fingerprinting (corner-normalized, 8-symmetry → TL canonical) for dedup | H3 | Phase 1 planned (exact-match only, not structural similarity) |
| R-18 | `puzzle-quality-scorer/README.md` — D2 classifier improvement deferred as standalone project | H1, H2 | Deferred |
| R-19 | No TODO for skill fingerprinting, prerequisite graph, or self-calibration loop | H1, H2, H4 | No existing plans |

---

## 3. External References

### 3A. Tsumego Platform Precedents

| R-20 | Platform | Relevant Technique | Applicability |
|------|----------|--------------------|---------------|
| R-21 | **101Weiqi** | Multi-dimensional tagging (by technique + difficulty), implicit "try simpler" flow | Supports H4 concept — but their implementation is manual editorial curation |
| R-22 | **Tsumego Pro** (mobile) | Per-technique difficulty progression, spaced repetition, "unlock next" gating | Strongest H4 precedent; uses hand-curated curriculum |
| R-23 | **OGS** (online-go.com) | Single scalar ELO per puzzle (Glicko-2 style), no multi-dimensional skill tracking | Validates scalar difficulty as industry standard |
| R-24 | **GoChild** (mobile) | Technique tree with unlocking (life-and-death → ko → seki), visual curriculum map | H4 precedent — kids-focused, simple DAG, hand-authored |
| R-25 | **KaTrain** | Policy prior + visits as difficulty signals, HumanSL model for strength-calibrated predictions | Directly relevant to H2 — closest external pattern to automated self-calibration |

### 3B. Algorithmic/Academic References

| R-26 | Pattern | Source | Relevance |
|------|---------|--------|-----------|
| R-27 | Multi-Dimensional Knowledge Modeling + IRT | Duolingo research papers | H1 — multi-dimensional skill vectors improve learning outcomes vs scalar difficulty. Requires user response data. |
| R-28 | Item Response Theory (IRT) | Educational measurement literature | H1/H2 — standard calibration framework. Yen-Go has **no response data** (local-first). |
| R-29 | Structural Board Hashing (Zobrist + symmetry normalization) | Standard in computer Go (Fuego, Pachi, GoGoGo) | H3 — well-understood. GoGoGo referenced in `TODO/puzzle-quality-scorer/`. |
| R-30 | DAG-based Curriculum Design | ITS literature | H4 — requires domain expert curation OR statistical prerequisite discovery from response data. |
| R-31 | Automated Quality Assessment in EdTech | Auto-grading/item quality literature | H5 — `TreeCompletenessMetrics` already provides needed raw data. |

---

## 4. Candidate Adaptations for Yen-Go

### H1: Multi-Dimensional Skill Fingerprinting

**FOR**:
- Individual difficulty components already computed (policy, visits, trap, structural, complexity) but discarded → could be persisted (R-2)
- 28 technique tags exist and are assigned per-puzzle → cross-reference possible
- `attrs` JSON column in DB-1 provides schema headroom without table migration
- `DifficultySnapshot` model stores raw inputs (policy_prior_correct, visits_to_solve, etc.)
- Frontend already loads `attrs` string but doesn't decode it → incremental unlock

**AGAINST**:
- The 5 difficulty components are not per-technique — they're composite scores across the whole puzzle
- No user response data (Holy Law: local-first, no telemetry) → cannot calibrate skill vectors from performance
- Frontend filtering queries would need new SQL patterns (`json_extract`)

**Adaptation**: Persist the 5 existing component scores + policy_entropy + correct_move_rank into `attrs` JSON. Frontend can then "sort by reading difficulty" or "sort by trap density".

### H2: Automated Difficulty Self-Calibration Loop

**FOR**:
- `fixture_dirs` configured in katago-enrichment.json (cho-elementary/intermediate/advanced)
- Elo-anchor cross-check exists (CALIBRATED_RANK_ELO table)
- D2 classifier audit documents 5 known limitations → improvement target
- `surprise_weighting` config exists (disabled) → infrastructure partially ready

**AGAINST**:
- No automated loop exists — fixture_dirs are for manual test comparison only
- Would require: (a) fixture runner, (b) comparison metrics, (c) weight optimizer, (d) CI job
- 5-component weights in `estimate_difficulty.py` are hardcoded constants
- Self-calibration without user response data measures internal consistency only, not pedagogical accuracy

**Adaptation**: Build a pytest-based calibration runner that scores fixtures and reports drift. Initially a diagnostic, not auto-adjuster.

### H3: Cross-Puzzle Positional Similarity Indexing

**FOR**:
- Position fingerprinting planned in Strategy D Phase 1 (R-17)
- `entropy_roi.py` computes bounding box/contested region
- GoGoGo repo referenced for tactical patterns

**AGAINST**:
- Strategy D plans exact-match dedup, NOT structural similarity (fundamentally different)
- Needs distance metric (Jaccard? Graph isomorphism?) — no existing infrastructure
- Storage: pairwise for 9K puzzles = 81M pairs. Needs ANN library.
- No frontend UX for "similar puzzles" exists

**Adaptation**: Ship exact-match dedup first (Strategy D Phase 1), then explore LSH on corner-normalized positions.

### H4: Pedagogical Prerequisite Graph

**FOR**:
- 28 tags with 3 categories → natural DAG structure
- Daily challenge has `technique_of_day` → could follow curriculum path
- Collections have `sequence_number` → ordering mechanism exists

**AGAINST**:
- No prerequisite data in `tags.json` — requires domain expert curation
- Statistical prerequisite discovery requires user response data (blocked by Holy Law)
- Static DAG risks being wrong for many users
- Collections already provide curated sequences (Cho Chikun books)

**Adaptation**: Manual curation in `tags.json` with `prerequisites: ["life-and-death"]` field. Frontend renders as a visual map.

### H5: Enrichment Quality Self-Assessment

**FOR**:
- `TreeCompletenessMetrics` already computed (R-5): completed_branches, simulation_hits/misses, forced_move_count
- `ac` field exists in DB-1 (0=untouched → 3=verified) — basic quality tracking
- `enrichment_quality_level` field exists in `AiAnalysisResult` but NOT persisted (R-14)
- `tree_truncated` flag computed but not stored (R-11)
- `YQ` property already has a quality framework

**AGAINST**:
- `ac` field already covers the coarse case (4 levels)
- Additional granularity may not unlock meaningful frontend features
- Frontend does not currently filter or sort by quality beyond `ac`

**Adaptation**: Persist `enrichment_quality_level` + `tree_truncated` + `completed_branches` into `attrs` JSON.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| R-32 | Risk | Affects | Severity |
|------|------|---------|----------|
| R-33 | **Schema migration overhead** — adding DB-1 columns requires coordinated backend + frontend change | H1, H3 | Low — `attrs` JSON bypass exists |
| R-34 | **No user telemetry** — Holy Law "local-first, no accounts" blocks response-data-dependent features | H1 (calibration), H2 (accuracy), H4 (statistical discovery) | High — fundamental constraint |
| R-35 | **YAGNI violation** — building curriculum/similarity before 10K user base exists | H3, H4 | Medium |
| R-36 | **Domain curation cost** — H4 requires Go expert to define prerequisite DAG accurately | H4 | Medium |
| R-37 | **DB size growth** — `attrs` JSON per puzzle increases yengo-search.db | H1, H5 | Low — estimated <50KB for 9K puzzles |
| R-38 | **External library dependency** — H3 similarity indexing may need ANN library (annoy, faiss) | H3 | Medium — violates "static-first" architecture |

**License notes**: No external code would be copied. All adaptations are to existing Yen-Go code patterns.

**Rejection reasons by hypothesis**:
- **H3 rejected as "most accretive"**: Requires fundamentally new infrastructure (ANN index, distance metrics), no frontend UX exists, and Strategy D Phase 1 (exact dedup) should come first.
- **H4 rejected as "most accretive"**: Requires either domain expert curation (unavailable) or user response data (blocked by Holy Law). Collections already provide curated sequences.
- **H2 partially rejected**: Valuable but is a pipeline-internal improvement that doesn't unlock new frontend features. Calibration fixtures exist but automated loop ROI is unclear without user validation data.

---

## 6. Planner Recommendations

### R-1 (RECOMMENDED): Persist the Signal Gap — "Enrichment Data Liberation"

**Persist existing computed-but-discarded signals into `attrs` JSON.** This is the single highest-ROI action because:

1. **Zero new computation** — signals are already computed (R-2 through R-14), just not stored
2. **Zero schema migration** — `attrs` TEXT column already exists in DB-1 with `json_extract()` support via sql.js
3. **Frontend unlock** — enables "sort by reading difficulty", "sort by trap density", "filter by solve confidence", technique-aware difficulty display
4. **Foundation for H1, H2, H5** — once signals are persisted, skill fingerprinting / self-calibration / quality scoring become incremental additions rather than new projects

**Concrete deliverables**:
- Store in `attrs`: `{"pc": 0.42, "vc": 0.31, "tc": 0.55, "sc": 0.68, "xc": 0.22, "pe": 0.73, "cr": 2, "tt": false, "cb": 8}` (policy/visits/trap/structural/complexity components + policy_entropy + correct_move_rank + tree_truncated + completed_branches)
- Update `entryDecoder.ts` to parse `attrs`
- Add 1-2 frontend filter/sort options using the new data

### R-2: Build Calibration Diagnostic (H2-lite)

After R-1, build a pytest-based calibration test that runs cho-elementary/intermediate/advanced fixtures through the enrichment lab and reports mean absolute error vs known difficulty, plus component-level drift per fixture set. Not an auto-adjuster — a diagnostic for manual tuning.

### R-3: Add Prerequisite Edges to tags.json (H4-lite)

Add a minimal `prerequisites` field to `tags.json` entries based on Go pedagogy:
- `ko → life-and-death`, `seki → ko`, `ladder → capture`, etc.
- Frontend can render as a technique map without building a full curriculum engine
- Lightweight enough to be a docs + config change only

### R-4: Defer H3 (Similarity) Until Strategy D Phase 1 Ships

Position fingerprinting for exact-match dedup (Strategy D) is the necessary precursor. Structural similarity is a Phase 2+ concern.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 85 |
| `post_research_risk_level` | low |

**Confidence rationale**: High confidence in R-1 because the signal inventory is well-documented, the `attrs` column already exists, and no architectural changes are needed. Lower confidence in estimated frontend impact (depends on UX design decisions).

**Open questions**:

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should `attrs` JSON include ALL discarded signals or a curated subset? | A: All 10+ signals / B: Top 5 highest-value / C: Start with difficulty components only | B | | ❌ pending |
| Q2 | What frontend feature should prototype the `attrs` data first? | A: "Sort by reading depth" / B: "Difficulty radar chart" / C: "Filter by solve confidence" / Other | A | | ❌ pending |
| Q3 | Should prerequisite edges (R-3) be authored by a Go expert or inferred from tag co-occurrence? | A: Expert curation / B: Statistical inference / C: Both / Other | A | | ❌ pending |

---

## Handoff

```yaml
research_completed: true
initiative_path: TODO/initiatives/20260317-research-capability-audit/
artifact: 15-research-enrichment-lab-accretion.md
top_recommendations:
  - "R-1: Persist computed-but-discarded enrichment signals into attrs JSON (zero new computation, zero schema migration)"
  - "R-2: Build calibration diagnostic (H2-lite) as pytest fixture runner"
  - "R-3: Add prerequisite edges to tags.json (H4-lite, config-only)"
  - "R-4: Defer similarity indexing until Strategy D Phase 1 ships"
open_questions:
  - "Q1: Curated subset vs all signals in attrs"
  - "Q2: First frontend feature to prototype"
  - "Q3: Prerequisite edge authoring method"
post_research_confidence_score: 85
post_research_risk_level: low
```
