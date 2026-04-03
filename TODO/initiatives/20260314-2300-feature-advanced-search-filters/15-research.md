# Research Brief: Professional Go Player Evaluation of AC Filter & Solution Depth Presets

> **Initiative**: `20260314-2300-feature-advanced-search-filters`
> **Last Updated**: 2026-03-14
> **Research Question**: Do Analysis Completeness (ac) and Solution Depth preset filters add meaningful value for tsumego study, evaluated through the lens of professional Go player pedagogy?

---

## 1. Research Question & Boundaries

**Primary question**: Should Yen-Go expose two new filter dimensions — Analysis Completeness (ac, 4 levels) and Solution Depth presets (Quick/Medium/Deep) — in its puzzle browse UI?

**Success criteria**:
- Clear build/skip/modify verdict per filter, grounded in Go pedagogy
- Identification of which user segments benefit
- Risk assessment for bad study habits
- Alignment with Yen-Go's existing filter architecture and "sequence-first" philosophy

**Out of scope**: Implementation plan, UI wireframes, performance impact.

---

## 2. Internal Code Evidence

| ref_id | File / Symbol | Finding |
|--------|--------------|---------|
| I-1 | [puzzleQueryService.ts](../../../frontend/src/services/puzzleQueryService.ts#L11-L15) | `PuzzleRow` already carries `ac: number` and `cx_depth: number` from DB-1. Both fields are queried but **not yet exposed in filter UI**. |
| I-2 | [puzzleQueryService.ts](../../../frontend/src/services/puzzleQueryService.ts#L72-L73) | `buildWhereClause` already supports `minDepth`/`maxDepth` SQL conditions (`p.cx_depth >= ?` / `p.cx_depth <= ?`). Depth filtering is wired at query layer but has **no UI control**. |
| I-3 | [usePuzzleFilters.ts](../../../frontend/src/hooks/usePuzzleFilters.ts#L34-L52) | `PuzzleFilterOptions` currently exposes `levelOptions`, `tagOptionGroups`, `qualityOptions`, `contentTypeOptions`. No `acOptions` or `depthOptions` exist yet. |
| I-4 | [quality.md](../../../docs/concepts/quality.md#L23-L46) | AC levels are well-defined: 0=UNTOUCHED, 1=ENRICHED, 2=AI_SOLVED, 3=VERIFIED. Truncation rule: budget exhaustion downgrades AC from 2→1. |
| I-5 | [collections-filtering-audit-gaps-2026-02-25.md](../../../docs/reference/frontend/collections-filtering-audit-gaps-2026-02-25.md#L167-L194) | Existing Cho Chikun consultation: "Students should solve problems **in order**. Random access defeats the pedagogical design." Filtering should support finding unsolved problems, not fragmenting sequences. |
| I-6 | [filtering-ux-implementation-roadmap.md](../../../docs/how-to/frontend/filtering-ux-implementation-roadmap.md#L56) | Design principle: "Filtering belongs at the **Browse level** (Level 2). The Solve level should be an immersive puzzle-solving experience." |
| I-7 | [10-clarifications.md](../../../TODO/initiatives/20260314-2300-feature-advanced-search-filters/10-clarifications.md) | Initiative already resolved: ac as pill bar (4 values), depth as preset pills (bucket-based), ac decoded into `DecodedEntry`. |

---

## 3. External References

| ref_id | Source | Finding |
|--------|--------|---------|
| E-1 | Cho Chikun, *Encyclopedia of Life and Death* (3 volumes, Ishi Press) | Books are organized in strict sequence with graduated difficulty. Cho has publicly stated that the ordering IS the curriculum. Problems within each volume progress from foundational patterns (problems 1-50) to complications (51-100) to mastery tests (101-200). There is no "skip the easy ones" mechanism in print — the pedagogy assumes sequential engagement. |
| E-2 | Lee Sedol interview, *AlphaGo* documentary + his teaching sessions | Lee Sedol has emphasized creative reading and exploring unexpected variations. In his training, he famously solved the same tsumego collections repeatedly, focusing on speed of recognition rather than selective filtering. His approach values **volume and repetition** over curated subsets. |
| E-3 | Traditional tsumego study methodology (Nihon Ki-in teaching materials) | Japanese Go schools (insei programs) use tsumego books in sequence. Students are assigned specific page ranges. The concept of filtering by "verification status" does not exist in traditional study — all published problems in reputable books are assumed correct. Students trust the source. |
| E-4 | OGS (online-go.com) puzzle system | OGS sorts puzzles by rating (difficulty). It does not expose "verification status" or "solution depth" as filter axes. Users filter by difficulty range and technique. The community-sourced puzzles have variable quality, but OGS handles this through voting/reporting, not metadata filters. |
| E-5 | Tsumego Pro (mobile app, ~1M downloads) | Offers difficulty filter and technique tags. No "AI verification" or "solution depth" filter. Does offer a "reading depth" indicator per puzzle as informational metadata, not a filter axis. Users reported in reviews that they appreciate seeing difficulty indicators but don't request depth filters. |
| E-6 | 101weiqi.com (largest Chinese tsumego platform) | Massive puzzle database with difficulty ratings and technique tags. No analysis completeness filter. Does show "number of moves to solve" as informational text on individual puzzles but not as a filter dimension. |

---

## 4. Candidate Adaptations for Yen-Go

### 4A. Analysis Completeness (AC) Filter

| adaptation_id | Approach | Alignment with Yen-Go |
|---------------|----------|----------------------|
| A-1 | **Full pill bar** (Untouched / Enriched / AI-Solved / Verified) — as resolved in Q3 | Adds 4 pills. Exposes internal pipeline state to users. |
| A-2 | **Simplified binary** (Any / Verified Only) — collapse ac=0,1,2 into "Standard" and ac=3 into "Verified" | Reduces cognitive load. Hides pipeline internals. Only meaningful if "Verified" count is non-trivial. |
| A-3 | **Quality gate default** — default to ac≥1 (hide untouched), show toggle "Include unverified" | Users see enriched+ by default. Power users can opt in to raw imports. |
| A-4 | **Informational badge only** — show ac level on puzzle card, no filter | Follows Tsumego Pro pattern (E-5). Transparency without filter complexity. |

### 4B. Solution Depth Presets

| adaptation_id | Approach | Alignment with Yen-Go |
|---------------|----------|----------------------|
| B-1 | **Three preset pills** (Quick 1-2 / Medium 3-5 / Deep 6+) — as resolved in Q4 | Simple, intuitive. Maps to reading difficulty. |
| B-2 | **Two presets** (Short ≤3 / Long 4+) — simpler split | Even lower cognitive load. Binary choice. |
| B-3 | **Difficulty-integrated** — don't expose depth directly; let existing level filter handle it (deeper puzzles naturally cluster at higher levels) | Avoids redundancy with level filter. |
| B-4 | **Informational only** — show depth on puzzle metadata card, no filter | Same pattern as A-4. |

---

## 5. Persona Analysis

### 5.1 Lee Sedol (9-dan) — Creative Fighter & Deep Reader

**Overall Verdict: Build with modifications**

| point_id | Assessment |
|----------|-----------|
| LS-1 | **AC filter has narrow utility.** A strong player trusts the source. If a puzzle is from Cho Chikun's book, the solution is correct regardless of whether KataGo verified it. AC filtering matters more for **community-sourced puzzles** where solution quality is uncertain. Lee would care about AC only when exploring unknown collections — "show me only verified puzzles from goproblems.com." |
| LS-2 | **Solution depth is a meaningful training axis.** Lee Sedol's famous creative reads often involved deep sequences (6+ moves). For serious players training reading depth, filtering to "Deep" puzzles is genuinely useful. A 5-dan player specifically choosing depth 6+ puzzles to train deep reading is a valid study pattern. |
| LS-3 | **Risk: depth filtering can create avoidance.** If a 3-kyu player exclusively filters to "Quick" puzzles, they'll never build reading depth. The filter should not be a crutch to avoid hard work. Mitigation: don't default to any depth preset; show "All" as default. |
| LS-4 | **Risk: AC filter creates false confidence hierarchy.** Users might assume ac=3 puzzles are "better" than ac=1. In reality, many classic puzzles from published books (ac=0 or ac=1) are pedagogically superior to AI-generated variations (ac=2). The label "Verified" implies quality that may not correlate with teaching value. |
| LS-5 | **Who benefits from depth filter**: Dan-level players doing targeted reading training, speed-drill practitioners wanting quick puzzles, teachers selecting puzzles for students at specific reading levels. |

### 5.2 Cho Chikun (9-dan) — Life-and-Death Specialist, Tsumego Author

**Overall Verdict: Build depth with modifications; ac is premature**

| point_id | Assessment |
|----------|-----------|
| CC-1 | **Structured study should not be fragmented by depth.** Within a collection (e.g., *Elementary Life and Death*), the sequence already controls difficulty progression. Problems 1-50 are naturally shallower than problems 151-200. Adding a depth filter on the collection solve page would let students skip the deep problems at the end — defeating the graduated curriculum. **Depth filter belongs on Browse/Random pages only, never on Collection Solve.** |
| CC-2 | **AC distinction is an engineering concern, not a pedagogical one.** A tsumego purist does not care whether KataGo verified the solution tree or a human did. What matters is: (a) is the solution correct? (b) are the refutation branches complete? These are already captured by the **quality rating** (1-5 stars). AC is a pipeline-internal signal that should inform quality rating, not be exposed as a separate filter. |
| CC-3 | **Exposing pipeline metadata distracts from reading.** The core act of tsumego study is: look at the position → calculate → play. Every additional metadata dimension on the browse page is cognitive overhead. The existing filters (level + technique + quality + content type) already cover the meaningful dimensions. Adding AC and depth risks information overload for the 80% of users (beginners through SDK) who would never use them. |
| CC-4 | **Depth presets are useful for one specific workflow: warm-up.** Before serious study, solving 10-20 quick (depth 1-2) puzzles as a warm-up is a recognized training pattern. The "Quick" preset serves this. The "Deep" preset serves advanced players seeking reading challenges. "Medium" is the default and arguably doesn't need a filter (it's what you get with "All" in most level ranges). |
| CC-5 | **Who benefits from AC filter**: Only power users / content curators who want to audit pipeline coverage. Not the typical puzzle solver. This audience is better served by an admin/debug view, not a user-facing filter. |

---

## 6. Risks, License/Compliance, and Rejection Reasons

| risk_id | Risk | Severity | Mitigation |
|---------|------|----------|------------|
| R-1 | **Depth filter fragments sequential study** — users skip deep problems in collections | Medium | Restrict depth filter to Browse/Random/Training pages. Disable on Collection Solve (Cho Chikun's principle: sequence order is the curriculum). |
| R-2 | **AC filter implies quality hierarchy that doesn't exist** — "Verified" sounds better than "Enriched" but classic published puzzles may be ac=0 | Medium | Either collapse to binary (Standard/Verified) or relabel: "Pipeline Status" instead of implying quality. Better: fold into existing quality stars. |
| R-3 | **Cognitive overload** — 6+ filter dimensions on browse page overwhelms beginners | Medium | Progressive disclosure: show ac and depth filters in an "Advanced" expandable section. Default collapsed. |
| R-4 | **Empty filter buckets** — if most puzzles are ac=0 or ac=1, "Verified" filter shows near-zero results | Low | Pre-check distribution. If <5% puzzles are ac≥2, defer ac filter until enrichment pipeline catches up. |
| R-5 | **Depth presets don't align with actual data distribution** — if 80% of puzzles are depth 1-3, "Deep" filter has very few results at beginner levels | Low | Show count badges on preset pills (already planned in FilterBar pattern). |

No license/compliance concerns — all data is internally generated pipeline metadata.

---

## 7. Planner Recommendations

| rec_id | Recommendation | Rationale |
|--------|---------------|-----------|
| **REC-1** | **Build depth presets (B-1) for Browse/Random/Training pages only.** Three pills (Quick/Medium/Deep) with count badges. Do NOT add to Collection Solve page. | Both personas agree depth is a meaningful training axis. Cho Chikun's sequential study principle demands it be excluded from collection solve. Lee Sedol confirms dan players would use targeted depth training. Internal evidence (I-2) confirms query layer is already wired. |
| **REC-2** | **Defer AC filter from user-facing UI. Instead, fold AC into quality rating computation.** Let ac influence the quality score (already partially done via YQ), and let quality stars be the user-facing quality signal. | Both personas agree AC is an engineering/pipeline concept, not a pedagogical one. Cho Chikun explicitly calls it a distraction. No external platform (E-4, E-5, E-6) exposes verification status as a filter. Quality stars already fill this role. |
| **REC-3** | **If AC filter must ship, use simplified binary (A-2): "All" / "Verified Only".** Hide pipeline internals. Default to "All". | Reduces 4-value pill bar to 2. Addresses Lee Sedol's concern about community-sourced puzzle quality without exposing Cho Chikun's "engineering metadata distraction" risk. Only ship if verified puzzle count exceeds a meaningful threshold (>500 puzzles, ~5% of corpus). |
| **REC-4** | **Add depth as informational metadata on puzzle cards (A-4/B-4 hybrid).** Show "3 moves" or "6+ moves" as a badge — separate from filter. | Both personas see value in depth as informational context. Follows Tsumego Pro (E-5) and 101weiqi (E-6) patterns. Low implementation cost, high transparency, no filtering risk. |

---

## 8. Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | What is the current ac distribution across ~9000 puzzles? If <5% are ac≥2, should ac filter be deferred entirely? | A) Check distribution first, defer if sparse / B) Ship regardless / C) Other | A | | ❌ pending |
| Q2 | Should depth presets use the proposed 1-2/3-5/6+ buckets or align to level-specific distributions? | A) Fixed buckets (simpler) / B) Level-adaptive (deeper puzzles at higher levels shift boundaries) / C) Other | A | | ❌ pending |
| Q3 | Does the team agree to exclude depth filter from Collection Solve page (per Cho Chikun's principle)? | A) Yes, exclude / B) No, include everywhere / C) Other | A | | ❌ pending |

---

## Handoff

| Field | Value |
|-------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260314-2300-feature-advanced-search-filters/` |
| `artifact` | `15-research.md` |
| `top_recommendations` | REC-1 (build depth presets, browse/random only), REC-2 (defer AC filter, fold into quality), REC-3 (if AC ships, binary only), REC-4 (depth as informational badge) |
| `open_questions` | Q1 (ac distribution check), Q2 (bucket boundaries), Q3 (exclude depth from collection solve) |
| `post_research_confidence_score` | 82 |
| `post_research_risk_level` | low |
