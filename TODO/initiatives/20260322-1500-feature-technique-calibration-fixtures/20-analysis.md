# Analysis — Technique Calibration Fixtures

Last Updated: 2026-03-22

## Planning Confidence

| Metric | Value |
|--------|-------|
| planning_confidence_score | 75 |
| risk_level | medium |
| research_invoked | true |
| post_research_confidence | 75 |
| research_artifact | `TODO/initiatives/20260322-research-external-sources-fixture-sourcing/15-research.md` |

---

## Cross-Artifact Consistency Check

### Charter ↔ Plan Coverage

| ac_id | Acceptance Criterion | Plan Section | Tasks | Status |
|-------|---------------------|-------------|-------|--------|
| AC-1 | ≥85% fixture pass rate | AD-3 (parametrized tests) + PH-B measurement | T22 | ✅ covered |
| AC-2 | All 28 technique tags covered | AD-4 (cross-check test) | T20 | ✅ covered |
| AC-3 | Live tests assert on 5 dimensions | AD-3 (5 parametrized test methods) | T19 | ✅ covered |
| AC-4 | Extended-benchmark with ≥3 × top-5 | AD-6 (directory structure) | T14, T15 | ✅ covered |
| AC-5 | Zero structural SGF bugs | AD-2 (registry excludes broken fixtures) | T8 (normalized replacements) | ✅ covered |
| AC-6 | Quality criteria formally defined | Charter QC-1 through QC-8 table | — (already in charter) | ✅ covered |
| AC-7 | All broken fixtures replaced | PH-B (atomic swap) | T7, T8, T9 | ✅ covered |

### Must-Hold Constraint ↔ Plan Coverage

| mh_id | Constraint | Plan Section | Tasks | Status |
|-------|-----------|-------------|-------|--------|
| MH-1 | All 5 calibration dimensions per entry | AD-2 (TechniqueSpec TypedDict) | T17 | ✅ covered |
| MH-2 | expected_tags as list[str], subset check | AD-2 (type), AD-3 (subset assertion) | T17, T19 | ✅ covered |
| MH-3 | Cross-check against config/tags.json | AD-4 (unit test) | T20 | ✅ covered |
| MH-4 | @pytest.mark.slow + .integration | AD-3 (markers) | T18 | ✅ covered |
| MH-5 | Exclude REMOVE/REPLACE fixtures | AD-5 (skip markers) | T17 | ✅ covered |
| MH-6 | Optional edge-case fields with defaults | AD-2 (NotRequired fields) | T17 | ✅ covered |
| MH-7 | Module-level registry dict | AD-2 (module-level placement) | T17 | ✅ covered |

### Goal ↔ Task Traceability

| goal_id | Goal | Tasks | Status |
|---------|------|-------|--------|
| G-1 | Define 8 quality criteria | Charter QC-1..QC-8 (already done) | ✅ complete (in charter) |
| G-2 | Replace 7+1 fixtures | T5, T6, T7, T8, T9 | ✅ covered |
| G-3 | 28-tag coverage | T20 (cross-check test) | ✅ covered |
| G-4 | Live KataGo test suite | T17–T22 | ✅ covered |
| G-5 | Extended-benchmark directory | T14, T15, T16 | ✅ covered |
| G-6 | ≥85% pass rate | T22 (validation run) | ✅ covered |
| G-7 | Delete broken fixtures | T7 | ✅ covered |

---

## Severity-Based Findings

| finding_id | Severity | Finding | Resolution |
|------------|----------|---------|------------|
| F1 | **Critical** | `miai` tag is in ALL_TAG_FIXTURES but NOT in config/tags.json's 28 slugs. The miai_puzzle.sgf fixture references a non-existent tag. | Investigate: either `miai` was removed from tags, or it's an alias. Likely `miai` is a move_order property (YO[miai]), not a technique tag. The registry should NOT have a `miai` entry — instead test miai via the `move_order` optional field on life-and-death fixtures. |
| F2 | **High** | `living` tag exists in config/tags.json (slug: "living") but has NO fixture in current ALL_TAG_FIXTURES. This is a gap. | T1 sourcing must prioritize a `living` fixture (goproblems YT[living] or goproblems_difficulty_based life_and_death/). |
| F3 | **Medium** | ko_double_seki.sgf covers both `ko` and `seki` tags but is only registered once in ALL_TAG_FIXTURES. | Registry entry should have `expected_tags: ["ko", "seki"]` per MH-2. Cross-check test (T20) will verify both tags are covered. |
| F4 | **Medium** | The 7 REMOVE fixtures (connection, endgame, fuseki, joseki, shape, simple_life_death, tesuji) remove 6 tag coverages. `connection`, `shape`, `endgame`, `joseki`, `fuseki`, `tesuji` all need replacement fixtures or the tag needs removal. | `joseki`, `fuseki`, `endgame` are strategic (not tsumego) per domain expert. These tags exist in config/tags.json but may be inappropriate for technique calibration. Check if they should be excluded from the calibration registry with documented rationale. `connection`, `shape`, `tesuji` need sourced replacements. |
| F5 | **Low** | `test_technique_calibration.py` will take ~60-90 min with live KataGo. This may exceed CI timeout limits. | Not a CI concern — tests are @pytest.mark.slow (excluded from CI). Run locally or in nightly batches. |
| F6 | **Low** | The temp script `_render_all_techniques.py` still exists in the enrichment lab root. | T24 explicitly deletes it. |

---

## Coverage Map

### Tags with Current Fixtures (KEEP status)

| tag | fixture | audit status | registry ready |
|-----|---------|:---:|:---:|
| life-and-death | center_puzzle.sgf, life_death_tagged.sgf, miai_puzzle.sgf | KEEP/FIX/KEEP | ✅ (after FIX) |
| ko | ko_direct.sgf, ko_approach.sgf, ko_10000year.sgf, ko_double.sgf, ko_multistep.sgf, ko_double_seki.sgf | FIX(5)/KEEP(1) | ✅ (after FIX) |
| seki | seki_puzzle.sgf, ko_double_seki.sgf | KEEP/KEEP | ✅ |
| capture-race | capture_race.sgf | KEEP | ✅ |
| ladder | ladder_puzzle.sgf | KEEP | ✅ |
| net | net_puzzle.sgf | KEEP | ✅ |
| snapback | snapback_puzzle.sgf | FIX | ✅ (after FIX) |
| double-atari | double_atari.sgf | KEEP | ✅ |
| clamp | clamp.sgf | KEEP | ✅ |
| nakade | nakade.sgf | MERGE→BM | ⚠️ needs copy in fixtures/ |
| connect-and-die | connect_and_die.sgf | KEEP | ✅ |
| under-the-stones | under_the_stones.sgf | KEEP | ✅ |
| liberty-shortage | liberty_shortage.sgf | KEEP | ✅ |
| vital-point | vital_point.sgf | FIX | ✅ (after FIX) |
| dead-shapes | dead_shapes.sgf | MERGE→BM | ⚠️ needs copy in fixtures/ |
| escape | escape.sgf | FIX | ✅ (after FIX retag) |
| cutting | cutting.sgf | REPLACE | ✅ (after REPLACE) |
| sacrifice | sacrifice.sgf | FIX | ✅ (after FIX) |
| corner | corner.sgf | FIX | ✅ (after FIX retag) |
| eye-shape | eye_shape.sgf | FIX | ✅ (after FIX) |
| throw-in | throw_in.sgf | VERIFY | ⚠️ pending expert tiebreak |

### Tags Needing Sourced Fixtures

| tag | current fixture | issue | source plan |
|-----|----------------|-------|-------------|
| **living** | NONE | Gap — tag exists in config/tags.json | goproblems YT[living], goproblems_difficulty_based life_and_death/ |
| **connection** | connection_puzzle.sgf (REMOVE) | Trivially obvious, zero calibration value | goproblems YT[connection] or ogs |
| **shape** | shape.sgf (REMOVE) | No engine signal | goproblems YT[shape] |
| **tesuji** | tesuji.sgf (REMOVE) | Generic, no specificity | goproblems YT[tesuji] (specific sub-type) |
| **endgame** | endgame.sgf (REMOVE) | Not tsumego — strategic | ⚠️ May exclude from calibration with rationale |
| **joseki** | joseki.sgf (REMOVE) | Not tsumego — strategic | ⚠️ May exclude from calibration with rationale |
| **fuseki** | fuseki.sgf (REMOVE) | Not tsumego — strategic | ⚠️ May exclude from calibration with rationale |

### Resolution for Non-Tsumego Tags (F4)

`endgame`, `joseki`, `fuseki` are strategic tags that exist in config/tags.json but are NOT tsumego techniques per domain expert consensus (GV-3). Two options:
1. **Exclude from registry** with documented skip + rationale (preferred — these 3 tags are for pipeline classification, not technique calibration)
2. **Source strategic puzzles** that demonstrate the tag in a tsumego-adjacent context

Recommendation: Exclude with skip markers. The cross-check test (MH-3) should have an explicit exclusion list for non-tsumego tags, documented in the test file.

---

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|------------|------------|--------|
| RE-1 | upstream | config/tags.json — tag additions/removals | Tag list change breaks cross-check test | Cross-check test (T20) fails loudly, forcing registry update | T20 | ✅ addressed |
| RE-2 | upstream | analyzers/detectors/ — detector behavior change | Expected tags may not match if detector is updated | Use tolerance (subset check, not exact) + review after pipeline changes | T19 | ✅ addressed |
| RE-3 | upstream | analyzers/enrich_single.py — API change | Import breaks in test_technique_calibration.py | Same risk as golden5 — shared dependency. No additional mitigation needed. | T18 | ✅ addressed |
| RE-4 | downstream | test_fixture_coverage.py ALL_TAG_FIXTURES | Fixture renames break existing tests | Atomic commit (PH-B): update ALL_TAG_FIXTURES in same commit as file changes | T10 | ✅ addressed |
| RE-5 | downstream | test_fixture_integrity.py population checks | New extended-benchmark/ needs population rule | T16 adds extended-benchmark to integrity checks | T16 | ✅ addressed |
| RE-6 | downstream | test_golden5.py — shared fixtures | Golden5 uses some of the same fixtures (ko_direct, sacrifice, simple_life_death, tesuji) | simple_life_death.sgf and tesuji.sgf are REMOVE'd but golden5 references them. **Resolved (C1/C6)**: replace content in-place (keep filename), update GOLDEN5_PUZZLES board_size if needed, same atomic commit. | T8.1 | ✅ addressed |
| RE-7 | lateral | benchmark/expert-review.md | MERGE→BM for nakade.sgf and dead_shapes.sgf needs doc update | Add entries to expert-review.md for merged fixtures | T13 | ✅ addressed |
| RE-8 | lateral | AGENTS.md | New test file + directory | T23 updates AGENTS.md in same commit per CLAUDE.md rule | T23 | ✅ addressed |
| RE-9 | lateral | conftest.py / _model_paths.py | Test file needs KataGo path resolution | Import from _model_paths.py same as golden5 — no additional risk | T18 | ✅ addressed |

### RE-6 Resolution Required

`test_golden5.py` references `simple_life_death.sgf` which is REMOVE'd in T7. **Resolution options**:
- (a) Keep simple_life_death.sgf but exclude from technique calibration registry (not from disk)
- (b) Update golden5 to use a different L&D fixture (e.g., center_puzzle.sgf or life_death_tagged.sgf)
- (c) Source a new L&D fixture that serves both golden5 and technique calibration

**Recommendation**: (a) — keep the file on disk for golden5, but exclude from TECHNIQUE_REGISTRY and ALL_TAG_FIXTURES. It's a valid integration test fixture even if it lacks metadata for calibration.

---

## Unmapped Tasks — RESOLVED

| finding_id | Observation | Resolution |
|------------|-------------|------------|
| F7 | `miai` tag discrepancy (F1) | Resolved (C3): T17 uses 'living' (ID 14), T10 fixes ALL_KNOWN_TAG_SLUGS miai→living |
| F8 | golden5 ↔ simple_life_death.sgf conflict (RE-6) | Resolved (C1/C6): T8.1 replaces content in-place, same atomic commit |
| F9 | FIX vs "don't fix" clarification for metadata | Metadata normalization (FF[4], SZ, YT tags) is NOT the same as structural SGF repair. "Don't fix" applies to stone-placement bugs. Metadata normalization proceeds in T8, T10. |

---

## Summary

| Dimension | Score |
|-----------|-------|
| Charter ↔ Plan coverage | 7/7 AC covered ✅ |
| Must-hold ↔ Plan coverage | 7/7 MH covered ✅ |
| Goal ↔ Task traceability | 7/7 goals covered ✅ |
| Ripple-effects | 9/9 addressed ✅ |
| Findings | 3 critical/high (F1, F2, F4) — all resolved via governance conditions C1-C6 |
| Unmapped tasks | 3 (F7, F8, F9) — all resolved |
| Research confidence | 75 (medium risk — data sourcing resolved, test architecture locked via OPT-3) |

> **See also**:
> - [Charter](./00-charter.md) — Acceptance criteria and quality definitions
> - [Plan](./30-plan.md) — Architecture decisions
> - [Tasks](./40-tasks.md) — Full task decomposition
