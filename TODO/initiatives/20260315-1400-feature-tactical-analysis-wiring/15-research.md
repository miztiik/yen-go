# Research: Tactical Analysis Integration — External References vs Implementation Reality

**Last Updated**: 2026-03-15
**Initiative**: 20260315-1400-feature-tactical-analysis-wiring

---

## 1. Research Question

**Can the algorithmic approaches from PLNech/gogogo and zhoumeng-creater/gogamev4.0 complete the puzzle quality scorer integration, and what exactly remains to be wired?**

The puzzle-quality-scorer implementation plan (Feb 2026) was 4 phases. A code audit reveals Phase 1 (core algorithms) is 95% built but Phases 2-4 (integration/wiring) are 0-40% connected. This research cross-references 5 external source files with 6 internal modules to determine the exact wiring gap.

---

## 2. External Source Inventory

| S-ID | Source File | Repo | License | Relevance | Reference Doc |
|------|-------------|------|---------|-----------|---------------|
| S-1 | `training/sensei_instincts.py` | PLNech/gogogo | GPL-3.0 | 8 Basic Instincts: pattern detection for auto-tagging + hints | `reference/gogogo-instincts.md` |
| S-2 | `training/tactics.py` | PLNech/gogogo | GPL-3.0 | Ladder/snapback/capture/life-death: algorithm design | `reference/gogogo-tactics.md` |
| S-3 | `training/test_instincts.py` | PLNech/gogogo | GPL-3.0 | Test patterns: positive/negative/orientation | (new from prev session) |
| S-4 | `training/compare_moves.py` | PLNech/gogogo | GPL-3.0 | Move quality comparison: rank-based accuracy, phase taxonomy | (new — this session) |
| S-5 | `features/analysis.py` | zhoumeng-creater/gogamev4.0 | MIT | Mistake classification, weak group detection, suggestion engine | `reference/gogamev4-analysis.md` |
| S-6 | `core/territory.py` | zhoumeng-creater/gogamev4.0 | MIT | Eye counting, group status, seki detection, influence map | `reference/gogamev4-territory.md` |

---

## 3. Internal Implementation Audit

### 3A. What IS Built (Phase 1 — 95% complete)

| IA-ID | Component | File | Functions | Status |
|-------|-----------|------|-----------|--------|
| IA-1 | Ladder detection | `core/tactical_analyzer.py` | `detect_ladder()` — board chase simulation, 3+ move verification | ✅ Working |
| IA-2 | Snapback detection | `core/tactical_analyzer.py` | `detect_snapback()` — sacrifice-then-recapture group-size comparison | ✅ Working |
| IA-3 | Capture pattern classification | `core/tactical_analyzer.py` | `detect_capture_pattern()` — TRIVIAL/FORCED/NET/LADDER/SNAPBACK | ✅ Working |
| IA-4 | Eye counting | `core/tactical_analyzer.py` | `count_eyes()` — orthogonal + diagonal + real-eye test | ✅ Working |
| IA-5 | Group status assessment | `core/tactical_analyzer.py` | `assess_group_status()` — ALIVE/DEAD/UNSETTLED decision tree | ✅ Working |
| IA-6 | Weak group finder | `core/tactical_analyzer.py` | `find_weak_groups()` — scans ≤3 liberty groups with escape assessment | ✅ Working |
| IA-7 | Seki detection | `core/tactical_analyzer.py` | `detect_seki()` — shared liberty, mutual-capture verification | ✅ Working |
| IA-8 | Instinct detection | `core/tactical_analyzer.py` | `detect_instinct_pattern()` — 4 of 8 instincts (extend-atari, connect-peep, hane-head, block-thrust) | ✅ Working |
| IA-9 | Position validation | `core/tactical_analyzer.py` | `validate_position()` — checks objective vs board state | ✅ Working |
| IA-10 | Tactical complexity | `core/tactical_analyzer.py` | `compute_tactical_complexity()` — 0-6 scale feature count | ✅ Working |
| IA-11 | Auto-tag derivation | `core/tactical_analyzer.py` | `derive_auto_tags()` — ladder→YT, snapback→YT, etc. | ✅ Function exists |
| IA-12 | Board infrastructure | `core/board.py` | `Board`, `Group`, `Point`, `Color` + `get_group()`, `copy()`, `play()`, `count_liberties()` | ✅ Full API |
| IA-13 | Unit tests | `tests/unit/test_tactical_analyzer.py` | 50+ test cases for all detectors | ✅ Passing |

### 3B. What Is NOT Wired (Phases 2-4 — 0-40% connected)

| GAP-ID | Gap | Planned Phase | Current State | Root Cause |
|--------|-----|---------------|---------------|------------|
| ~~GAP-1~~ | ~~Auto-tags not merged into YT~~ | ~~Phase 2~~ | **ALREADY IMPLEMENTED** at analyze.py L349-358: `derive_auto_tags()` → merge → `sorted(set(tags))` with ENRICH_IF_ABSENT | N/A — working |
| ~~GAP-2~~ | ~~ENRICH_IF_ABSENT policy~~ | ~~Phase 2~~ | **ALREADY IMPLEMENTED**: `if tag not in existing_tag_set: tags.append(tag)` | N/A — working |
| GAP-3 | **Tactical complexity not feeding quality.py** | Phase 3 | `compute_tactical_complexity()` computed but quality.py has zero tactical references | quality.py interface doesn't accept tactical signals |
| GAP-4 | **Classifier has no tactical signals** | Phase 3 | `classify_difficulty()` uses only depth/variations/stones/board_size; no tactical inputs | classifier.py interface doesn't accept tactical signals |
| GAP-5 | **Position validation not reflected in YQ** | Phase 3 | Validation flags broken puzzles (logged) but doesn't affect quality score | No write-back from validation notes to quality score |
| GAP-6 | **HintGenerator has only tag-mediated path, no tactical-detail path** | Phase 4 | Hints read tags from tagger.py (and auto-tags now flow via auto-merge), but NO direct tactical analysis consumption (e.g., ladder depth, snapback stone count) | HintGenerator API doesn't accept TacticalAnalysis |
| ~~GAP-7~~ | ~~Results not persisted to SGF~~ | ~~All phases~~ | **PARTIALLY IMPLEMENTED**: Tags persist via auto-merge; validation notes logged. Quality and classifier signals still disconnected. | N/A — tag persistence works |

**Root cause**: NOT a single variable-scope issue (original F-5 was incorrect). Auto-tags DO flow to YT via analyze.py L349-358. The real gaps are 3 independent consumer integration tasks:
1. **quality.py** needs a new parameter interface to accept tactical complexity and validation flags
2. **classifier.py** needs new feature inputs (tactical pattern presence, weak group count)
3. **hints.py** needs tactical-detail hints beyond tag-mediated fallback (e.g., ladder depth, snapback stone count)

### 3C. Parallel Systems Comparison

| Dimension | Pipeline (`core/tactical_analyzer.py`) | Enrichment Lab (`detectors/*.py`) |
|-----------|----------------------------------------|-----------------------------------|
| Detection approach | 100% board simulation + Go rules | Hybrid KataGo PV/winrate + pattern matching |
| Dependencies | Pure Python, no external process | KataGo engine (external subprocess) |
| Speed | ~6ms per puzzle | ~2-5s per puzzle (KataGo) |
| Scope | 9 detectors (focused) | 28 detectors (comprehensive) |
| Usage | Backend pipeline (batch) | Enrichment lab tool (single-puzzle) |
| Integration | Called but results discarded | Results written to enriched SGF |
| Tag coverage | ladder, snapback, seki, connection, escape, eye-shape, tesuji, life-and-death | All 28 tags |

**Key insight**: The enrichment lab (28 detectors) IS wired end-to-end. The pipeline tactical analyzer (9 detectors) is NOT. The enrichment lab uses KataGo signals; the pipeline uses board simulation. They are complementary but disconnected.

---

## 4. External Reference Gap Analysis

### 4A. What gogogo Reference Docs Describe vs What's Built

| REF-ID | Reference Doc Says | Implementation Status | Gap |
|--------|--------------------|-----------------------|-----|
| REF-1 | Ladder trace with diagonal scan + zobrist caching | Implemented as board chase (no diagonal scan, no zobrist cache) | Minor: optimization not needed per Phase 1 |
| REF-2 | Snapback detect: atari-first, simulate capture, check recapture | ✅ Implemented per spec | None |
| REF-3 | Alpha-beta capture verification (depth 4) | ✅ Implemented as `detect_capture_pattern()` | None |
| REF-4 | Life/death minimax with eye counting | ✅ Implemented as `assess_group_status()` + `count_eyes()` | None |
| REF-5 | 8 instinct patterns with priority ordering | Implemented 4 of 8 (extend-atari, connect-peep, hane-head, block-thrust); missing stretch-from-kosumi, block-angle, stretch-from-bump, hane-response | 4 instincts missing |
| REF-6 | Tactical feature planes (6 planes) → complexity count | ✅ Implemented as `compute_tactical_complexity()` (0-6 scale) | None |
| REF-7 | Instinct boost multipliers (3.0 survival → 1.0 shape) | NOT implemented — no priority/boost concept | Priority scoring not planned |

### 4B. What gogamev4.0 Reference Docs Describe vs What's Built

| REF-ID | Reference Doc Says | Status | Gap |
|--------|--------------------|-----------------------|-----|
| REF-8 | Mistake classification (BLUNDER/MISTAKE/INACCURACY/GOOD/EXCELLENT) | NOT built — requires AI winrate analysis we don't have | Out of scope (see plan exclusions) |
| REF-9 | Weak group detection (critical/weak/unsettled) | ✅ Implemented | None |
| REF-10 | Eye counting (true eye vs false eye) | ✅ Implemented | None |
| REF-11 | Group status assessment (alive/dead/unsettled) | ✅ Implemented | None |
| REF-12 | Escape potential assessment | ✅ Implemented in `find_weak_groups()` | None |
| REF-13 | Seki detection | ✅ Implemented | None |
| REF-14 | Influence map (distance-decay strength) | NOT built | Deferred — not critical for current scope |
| REF-15 | Territory flood-fill | NOT built | Deferred — requires post-solution board state |

### 4C. compare_moves.py (NEW — S-4) Relevance Assessment

| CM-ID | Feature from compare_moves.py | Yen-Go Applicability | Recommendation |
|-------|-------------------------------|----------------------|----------------|
| CM-1 | Rank-based move accuracy (Top-1/3/5/10) | **Relevant for refutation quality** — could rank "how wrong" a wrong first move is by comparing to correct move's rank in KataGo policy | Medium priority: enrichment lab only (requires KataGo) |
| CM-2 | Game phase taxonomy (opening/middle/endgame by move #) | **Not directly relevant** — tsumego puzzles are positions, not full games | Low |
| CM-3 | Disagreement tracking (rank>10 AND prob<1%) | **Relevant for puzzle difficulty** — puzzles where KataGo's top choice ≠ correct move (high disagreement) are harder | Already partially captured by enrichment lab policy/winrate deltas |
| CM-4 | Per-phase accuracy breakdown | Not relevant for static puzzle analysis | Skip |
| CM-5 | SGF parsing with move extraction | Already handled by sgfmill in Yen-Go pipeline | Skip |

**Verdict**: compare_moves.py offers one usable concept (CM-1: rank-based refutation scoring) but it requires KataGo policy output, making it enrichment-lab-only. Not applicable to the pipeline's pure-board-simulation tactical analyzer.

---

## 5. Findings Summary — Enumerated

| F-ID | Finding | Category | Impact | Priority |
|------|---------|----------|--------|----------|
| F-1 | **Phase 1 is 95% built** — all 9 core tactical detectors work with 50+ passing tests | Validation | High (confirms foundation is solid) | — |
| ~~F-2~~ | ~~Phase 2 auto-tagging has zero integration~~ — **CORRECTED**: `derive_auto_tags()` IS wired at analyze.py L349-358; auto-tags merge into YT via ENRICH_IF_ABSENT policy. **ALREADY WORKING.** | ~~Critical gap~~ Validated | N/A | — |
| F-3 | **Phase 3 quality/classifier signals disconnected** — tactical_complexity computed but not consumed | Critical gap | High (difficulty scoring blind to tactics) | **P1** |
| F-4 | **Phase 4 hints disconnected** — HintGenerator reads tagger.py not tactical_analyzer | Gap | Medium (hints work via fallback paths) | **P2** |
| ~~F-5~~ | ~~Single root cause~~ — **CORRECTED**: The `tactical_analysis` variable IS consumed for auto-tags. Real gaps are **3 independent consumer integrations**: quality.py (no tactical input interface), classifier.py (no tactical features), hints.py (no tactical-detail path) | ~~Root cause~~ Corrected | Moderate (3 independent integration tasks) | **P1** |
| F-6 | **4 of 8 instinct patterns missing** — stretch-from-kosumi, block-angle, stretch-from-bump, hane-response not implemented | Gap | Low (most tsumego puzzles need only the 4 implemented) | **P3** |
| F-7 | **Enrichment lab is separately wired end-to-end** — 28 detectors work with KataGo; pipeline tactical analyzer is the disconnected system | Architecture | Informational | — |
| F-8 | **compare_moves.py adds rank-based refutation scoring concept** — only useful in enrichment lab (requires KataGo), not pipeline | New external input | Low (enrichment lab already has policy/winrate delta) | **P4** |
| F-9 | **Reference docs accurately describe what was built** — gogogo-tactics.md and gogamev4-territory.md align with `tactical_analyzer.py` implementation | Validation | Confirms clean-room adaptation was faithful | — |
| F-10 | **Influence map and territory flood-fill not built** — both deferred in original plan, still not needed for core wiring | Deferred scope | None (correctly excluded) | — |
| F-11 | **Test methodology from gogogo test_instincts.py** — negative tests, multi-orientation, boost-stacking patterns could improve enrichment lab test suite | Test quality | Medium (23/28 detectors lack multi-orientation tests) | **P2** |

---

## 6. Confidence and Risk

- **Planning Confidence Score**: 88/100 (post-correction)
- **Risk Level**: low
- **Rationale**: Core algorithms are built and tested. Auto-tagging is already live. The remaining gap is 3 independent consumer integrations (quality.py, classifier.py, hints.py) — well-understood, low-risk wiring work. No new dependencies, no architecture changes, no schema evolution required.
- **Research triggered**: No (confidence > 70, risk = low, no external patterns needed).
- **Governance correction applied**: F-2 and F-5 corrected after Governance Panel independent code audit found auto-tag wiring IS implemented at analyze.py L349-358.

---

## 7. Pre-Research from Previous Session

The previous research session (20260315-research-gogogo-tactics-patterns) analyzed the same external sources from a test-improvement perspective. Key findings that carry forward:

- Instinct-to-tag mapping table (8 mappings, all map to existing tags)
- Test gap quantification (5/28 detectors have multi-orientation tests)
- Governance panel approved test improvements as highest-ROI action

That initiative focused on enrichment lab test quality. This initiative focuses on **pipeline tactical analyzer integration** — a different codebase and different problem.
