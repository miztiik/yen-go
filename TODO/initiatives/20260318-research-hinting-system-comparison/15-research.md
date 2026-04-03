# Research Brief: Hinting System Comparison — Backend vs Enrichment Lab

**Last Updated:** 2026-03-18
**Status:** Research complete
**Initiative:** `20260318-research-hinting-system-comparison`

---

## 1. Research Question & Boundaries

**Question:** How do the two independent hint generation systems compare, and is consolidation into the enrichment lab feasible?

**Boundaries:**
- Backend pipeline hinting: `backend/puzzle_manager/core/enrichment/hints.py` + `solution_tagger.py`
- Lab hinting: `tools/puzzle-enrichment-lab/analyzers/hint_generator.py`
- Shared config: `config/teaching-comments.json`
- Existing transition plan: `TODO/hinting-unification-transition-plan-v1.md`

**Out of scope:** Frontend hint rendering, `{!xy}` token resolution, teaching comments (C[] system).

---

## 2. Internal Code Evidence

### 2.1 File Inventory

| ID | System | File | LOC (approx) | Role |
|----|--------|------|---------------|------|
| R-1 | Backend | `backend/puzzle_manager/core/enrichment/hints.py` | ~1000 | `HintGenerator` class — tag-driven 3-tier hints with board analysis |
| R-2 | Backend | `backend/puzzle_manager/core/enrichment/solution_tagger.py` | ~100 | Confidence-gated solution-aware fallback (when tagger gives 0 tags) |
| R-3 | Backend | `backend/puzzle_manager/core/enrichment/__init__.py` | ~200 | Orchestrator: `enrich_puzzle()` — calls HintGenerator, assembles YH |
| R-4 | Backend | `backend/puzzle_manager/core/enrichment/config.py` | ~100 | `EnrichmentConfig` + `HintOperationLog` structured logging |
| R-5 | Lab | `tools/puzzle-enrichment-lab/analyzers/hint_generator.py` | ~260 | `generate_hints()` function — config-driven 3-tier hints |
| R-6 | Lab | `tools/puzzle-enrichment-lab/analyzers/stages/teaching_stage.py` | ~130 | `TeachingStage` — orchestrates hint generation within enrichment pipeline |
| R-7 | Shared | `config/teaching-comments.json` | — | `hint_text` field shared by both systems for Tier 1 |
| R-8 | Docs | `docs/architecture/backend/hint-architecture.md` | ~300 | Canonical architecture doc (backend-centric) |
| R-9 | Plan | `TODO/hinting-unification-transition-plan-v1.md` | ~350 | 9-phase unification transition plan (draft) |

### 2.2 Backend System: `HintGenerator` Class

**Architecture:** OOP class instantiated per `enrich_puzzle()` call. Receives `EnrichmentConfig`.

**Three-tier generation:**
- **YH1 (Technique):** 3-path cascade: (1) Atari detection (relevance-gated — correct move must capture the atari group), (2) Tag-based lookup from `teaching-comments.json` via `_load_teaching_comments()`, (3) Solution-aware fallback via `solution_tagger.infer_technique_from_solution()` (HIGH+ confidence only: ko=CERTAIN, connection=HIGH, captures=MEDIUM/skip, unknown=LOW/skip).
- **YH2 (Reasoning):** `TECHNIQUE_HINTS` dict — 28 tags mapped to `(technique_hint, reasoning_template)`. Dynamic enrichment from solution tree depth + refutation count + secondary tag context. Liberty analysis gated to `capture-race`/`ko` only.
- **YH3 (Coordinate):** `_point_to_token()` converts `Point(x,y)` → `{!xy}` SGF token. Depth gating: ≤3 moves = coordinate only; ≥4 = coordinate + technique outcome from `COORDINATE_TEMPLATES` dict.

**Unique capabilities:**
- Board simulation via `Board` class — plays correct move on board copy to verify atari relevance, group connections, ko creation
- `LibertyAnalysis` dataclass — liberty counting for weakest groups
- `move_captures_stones()` function — verifies correct move actually captures the atari group before emitting atari hint
- `_move_saves_atari_group()` — verifies correct move saves player group from atari
- Solution-aware fallback with explicit `InferenceConfidence` enum (CERTAIN/HIGH/MEDIUM/LOW)
- Tag priority ordering: 4-tier priority system (specific tesuji > tactical > general > category)
- Depth gating for YH3 outcome text
- Last-resort fallback in orchestrator: bare coordinate if all generators fail
- Full structured logging (`HintOperationLog`) per tier

**Coordinate system:** Works with `Point` objects (0-indexed x,y). Converts to `{!xy}` SGF tokens directly.

### 2.3 Lab System: `generate_hints()` Function

**Architecture:** Stateless function. Receives `analysis: dict` (from `AiAnalysisResult.model_dump()`), `technique_tags: list[str]`, `board_size`, plus optional `detection_results`, `instinct_results`, `level_category`.

**Three-tier generation:**
- **Tier 1 (Technique):** `_resolve_hint_text(primary_tag)` → looks up `hint_text` from `config/teaching-comments.json` via `config.teaching.load_teaching_comments_config()`. Optionally prefixed with instinct phrase (T15, gated behind `instinct_enabled` flag).
- **Tier 2 (Reasoning):** `_generate_reasoning_hint()` — First tries `DetectionResult.evidence` text from `TechniqueStage` (T14). Falls back to level-adaptive templates: `entry`/`core`/`strong` categories produce different wording. Uses `solution_depth` and `refutation_count` from analysis dict. Secondary tag context appended if multiple tags.
- **Tier 3 (Coordinate):** `_generate_coordinate_hint()` — Selects template from `COORDINATE_TEMPLATES` dict by primary tag. Converts GTP coordinate (e.g., `C7`) → SGF token via `_gtp_to_sgf_token()`. Board-size aware.

**Unique capabilities:**
- KataGo engine-derived signals: `DetectionResult` evidence (from TechniqueStage) produces richer Tier 2 reasoning
- Instinct integration (T15): `InstinctResult` adds "instinct phrase" prefix to Tier 1 (e.g., "Your instinct says to...")
- Level-adaptive hints (T16): `entry`/`core`/`strong` categories produce pedagogically-tuned wording
- `format_yh_property()` — pipe-delimited serialization with pipe-character sanitization
- `DetectionResult` evidence can provide specific, context-rich Tier 2 text that no template can match

**Coordinate system:** Works with GTP strings (e.g., `C7`). Converts via `_gtp_to_sgf_token()` to SGF notation. Board-size parameter required.

---

## 3. External References

| ID | Reference | Relevance |
|----|-----------|-----------|
| R-10 | OGS hint system (online-go.com) | OGS uses 2-tier hints (region → coordinate). Yen-Go's 3-tier (technique → reasoning → coordinate) is pedagogically superior per expert review. |
| R-11 | KaTrain hint approach (github.com/sanderland/katrain) | KaTrain uses KataGo policy network top-N moves as hints. Yen-Go lab follows a similar pattern but converts engine output to pedagogical text instead of raw move suggestions. |
| R-12 | Tsumego Pro (iOS app) | Uses technique-name hints similar to Yen-Go's Tier 1. No reasoning tier. |
| R-13 | GoProblems.com | Minimal hinting — only "correct/wrong" feedback. No progressive disclosure. |

---

## 4. Structured Comparison

### 4.1 Input Signals

| ID | Signal | Backend | Lab | Assessment |
|----|--------|---------|-----|------------|
| R-14 | Technique tags | ✅ From `game.yengo_props.tags` | ✅ From `result.technique_tags` | Parity — both use tagger output |
| R-15 | Solution tree depth | ✅ `_get_solution_depth()` traverses tree | ✅ `analysis["difficulty"]["solution_depth"]` | Parity — same data, different access path |
| R-16 | Refutation count | ✅ `_count_refutations()` counts wrong children | ✅ `analysis["difficulty"]["refutation_count"]` | Parity |
| R-17 | Board position (stones) | ✅ Full `Board` simulation | ❌ No board simulation | **Backend advantage** — enables atari verification, group analysis |
| R-18 | Liberty analysis | ✅ `LibertyAnalysis` for semeai/ko | ❌ Not available | **Backend advantage** — richer capture-race hints |
| R-19 | Correct move coordinate | ✅ `Point` from solution tree | ✅ GTP string from `analysis["validation"]["correct_move_gtp"]` | Parity — different format, same data |
| R-20 | KataGo engine analysis | ❌ Not available | ✅ Full analysis dict from engine | **Lab advantage** — engine-validated signals |
| R-21 | DetectionResult evidence | ❌ Not available | ✅ T14: evidence text from `TechniqueStage` | **Lab advantage** — context-rich Tier 2 |
| R-22 | InstinctResult | ❌ Not available | ✅ T15: instinct phrase prefix | **Lab advantage** (currently gated/experimental) |
| R-23 | Level category | ❌ Not available | ✅ T16: `entry`/`core`/`strong` adaptation | **Lab advantage** — level-adaptive wording |
| R-24 | Solution-aware fallback | ✅ `solution_tagger` with confidence gating | ❌ Not needed (engine tags always available) | **Backend advantage** for untagged puzzles |
| R-25 | teaching-comments.json | ✅ Direct JSON loading + caching | ✅ Via `config.teaching` module | Parity — same source file |

### 4.2 Output Format

| ID | Aspect | Backend | Lab | Assessment |
|----|--------|---------|-----|------------|
| R-26 | Output structure | `EnrichmentResult.hints: list[str]` | `list[str]` (always 3 elements) | Lab always returns exactly 3; backend returns 0-3 non-empty |
| R-27 | YH serialization | Done by `SgfBuilder.add_hints()` | `format_yh_property()` in hint_generator.py | Different serializers, same `|`-delimited format |
| R-28 | Pipe sanitization | ❌ Not in hint generator (relies on SgfBuilder) | ✅ `h.replace("\|", " ")` in `format_yh_property()` | Lab is more defensive |
| R-29 | Empty hint handling | Filters out empty hints, compact list | Returns `["", "", ""]` if no technique tags | Backend is cleaner (no empty strings in output) |
| R-30 | Coordinate token | `{!xy}` from Point (0-indexed) | `{!xy}` from GTP→SGF conversion | Same output format, different conversion path |

### 4.3 Quality Assessment

| ID | Quality Dimension | Backend | Lab | Winner |
|----|-------------------|---------|-----|--------|
| R-31 | Tier 1 accuracy | Config-driven + atari verification + solution-aware fallback | Config-driven + instinct prefix (experimental) | **Backend** — atari relevance gating prevents misleading hints |
| R-32 | Tier 2 richness | Template-based reasoning + liberty analysis (semeai/ko only) + solution depth/refutation context | Engine evidence text (when available) + level-adaptive templates + secondary tag context | **Lab** — DetectionResult evidence produces contextually richer text |
| R-33 | Tier 3 accuracy | Board-size aware; depth-gated outcome text; technique-specific templates | Board-size aware; technique-specific templates (no depth gating) | **Backend** — depth gating prevents information overload for simple puzzles |
| R-34 | Pedagogical safety | "Do No Harm" principle enforced via confidence gating | No explicit safety gating beyond tag presence | **Backend** — explicit confidence thresholds prevent misleading hints |
| R-35 | Coverage (no-tag case) | `solution_tagger` fallback with confidence model | Silently returns `["", "", ""]` | **Backend** — still produces coordinate hints for untagged puzzles |
| R-36 | Level adaptation | No level-based wording variation | `entry`/`core`/`strong` categories with different templates | **Lab** — hints adapt to solver level |
| R-37 | Structured logging | `HintOperationLog` with per-tier status/reason/value/duration | Minimal logging in `TeachingStage` | **Backend** — full diagnostics per tier |

### 4.4 Shared vs Unique Capabilities

| ID | Capability | Backend Only | Lab Only | Shared |
|----|-----------|-------------|----------|--------|
| R-38 | Tag-driven Tier 1 from teaching-comments.json | | | ✅ |
| R-39 | Tag priority ordering (4-tier) | ✅ | | |
| R-40 | Atari relevance verification (board simulation) | ✅ | | |
| R-41 | Solution-aware fallback (confidence-gated) | ✅ | | |
| R-42 | Liberty analysis (semeai/ko gated) | ✅ | | |
| R-43 | Depth-gated YH3 outcome text | ✅ | | |
| R-44 | Last-resort coordinate fallback | ✅ | | |
| R-45 | Structured per-tier logging | ✅ | | |
| R-46 | KataGo DetectionResult Tier 2 evidence | | ✅ | |
| R-47 | Instinct phrase prefix (T15) | | ✅ | |
| R-48 | Level-adaptive hint wording (T16) | | ✅ | |
| R-49 | Pipe sanitization in output formatter | | ✅ | |
| R-50 | Technique-specific coordinate templates | | | ✅ (different dicts, ~70% overlap) |
| R-51 | Secondary tag context in reasoning | | | ✅ (both append secondary technique) |
| R-52 | Solution depth + refutation count in Tier 2 | | | ✅ |

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R-53 | Loss of board-simulation safety (atari relevance, group analysis) | **High** | Lab would need to add Board-equivalent logic or import from backend (violates `tools/ MUST NOT import from backend/` constraint) |
| R-54 | Loss of solution-aware fallback for untagged puzzles | **Medium** | Lab always has KataGo tags, so this is only relevant for puzzles processed without engine |
| R-55 | Coordinate system drift (Point vs GTP) | **Medium** | Backend uses Point→SGF; lab uses GTP→SGF. Different conversion paths can produce different results on edge cases |
| R-56 | Loss of structured logging (`HintOperationLog`) | **Medium** | Lab would need equivalent observability infrastructure |
| R-57 | `tools/` cannot import `backend/` (architecture rule) | **Blocking** | Lab cannot reuse backend Board class. Would need tools/core equivalent or standalone implementation |
| R-58 | Transition plan already exists (9 phases, draft) | **Low** | Must align any consolidation with existing `TODO/hinting-unification-transition-plan-v1.md` |
| R-59 | No license/IP concerns | N/A | Both systems are internal, same repo, same author |

---

## 6. Candidate Adaptations for Yen-Go

### Option A: Consolidate into Lab (Lab replaces Backend)

**Approach:** Lab becomes canonical hint generator. Backend pipeline calls lab hints (or a shared library extracted from lab).

**Pros:** Single source of truth, KataGo-enriched hints for all puzzles.
**Cons:** Loses board simulation safety (R-53), violates architecture rule (R-57), lab is tools/ scope only. Would require extracting shared hint logic to `tools/core/` or a new shared package.

### Option B: Consolidate into Backend (Backend absorbs Lab innovations)

**Approach:** Port lab's unique capabilities (DetectionResult evidence, level-adaptive wording, instinct prefix) into backend's `HintGenerator` class.

**Pros:** Preserves all safety features (atari gating, confidence model, structured logging). Single authoritative pipeline. No architecture violation.
**Cons:** Backend doesn't have KataGo signals at runtime — would need an "enrichment data import" path where lab results feed into pipeline. Requires designing a stable interface.

### Option C: Shared Contract, Independent Implementations (Current Plan)

**Approach:** Define shared hint contract (as per existing transition plan Phase 2), keep both systems independent, enforce parity via test fixtures.

**Pros:** No risk of regression. Both systems can evolve independently. Existing transition plan already covers this.
**Cons:** Ongoing maintenance of two systems. Semantic drift will continue unless actively managed.

### Option D: Shared Hint Library in `tools/core/`

**Approach:** Extract common hint logic (Tier 1 config lookup, coordinate conversion, formatting) into `tools/core/hints.py`. Both backend and lab import from there.

**Pros:** Eliminates duplication for 60%+ of logic. Preserves system-specific extensions.
**Cons:** Backend importing from `tools/` isn't explicitly forbidden but is unusual. Adds cross-cutting dependency.

---

## 7. Planner Recommendations

1. **Do NOT consolidate yet.** The backend's board-simulation safety (atari relevance gating, solution-aware confidence model) is a quality advantage that the lab cannot replicate without importing Board logic or building an equivalent. The architecture constraint (`tools/ MUST NOT import from backend/`) makes full consolidation into the lab infeasible without restructuring.

2. **Adopt Option B incrementally:** Port the lab's three unique innovations into the backend `HintGenerator`:
   - (a) Level-adaptive hint wording (T16 `entry`/`core`/`strong`) — low risk, ~50 LOC
   - (b) DetectionResult-style evidence for Tier 2 — medium risk, requires defining an enrichment data import format
   - (c) Instinct phrase prefix (T15) — defer until instinct calibration is complete (currently gated)

3. **Align with existing transition plan.** The 9-phase plan in `TODO/hinting-unification-transition-plan-v1.md` is the correct governance framework. This research maps directly to Phase 1 (Baseline Inventory) — the drift matrix is now captured in sections 4.1–4.4 above.

4. **Immediate wins (no architecture change needed):**
   - Port pipe sanitization (R-49) from lab to backend's SgfBuilder or HintGenerator
   - Port coordinate template coverage — lab has templates for `atari`, `semeai`, `capture`, `eye-shape`, `connection`, `cutting`, `escape`, `tesuji` that backend's `COORDINATE_TEMPLATES` also has, but verify 1:1 match
   - Add level-adaptive Tier 2 wording to backend (R-36) — pure template change

---

## 8. Confidence & Risk Update

| Metric | Value |
|--------|-------|
| `research_completed` | true |
| `initiative_path` | `TODO/initiatives/20260318-research-hinting-system-comparison/` |
| `artifact` | `15-research.md` |
| `post_research_confidence_score` | 85 |
| `post_research_risk_level` | medium |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should level-adaptive Tier 2 (T16) be ported to backend as a standalone initiative? | A: Yes, standalone / B: Bundle with transition plan Phase 6 / C: Defer / Other | A | — | ❌ pending |
| Q2 | Is the existing transition plan (9 phases) still the desired governance framework, or should a lighter-weight approach be adopted? | A: Keep 9-phase plan / B: Reduce to 3-phase (contract → port → parity) / C: Abandon plan, consolidate directly / Other | B | — | ❌ pending |
| Q3 | Should the backend accept a pre-computed "engine evidence" field in analyzed SGFs (to import lab DetectionResult text for Tier 2)? | A: Yes, define new YE property / B: Yes, embed in YM metadata / C: No, keep systems separate / Other | B | — | ❌ pending |

### Top Recommendations (ordered)

1. Port level-adaptive Tier 2 wording to backend (immediate, low risk)
2. Port pipe sanitization to backend hint output path
3. Align this research as Phase 1 deliverable of existing transition plan
4. Define engine-evidence import format for future Tier 2 enrichment
