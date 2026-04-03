# Tasks — Teaching Comments V2

**Initiative**: `2026-03-06-feature-teaching-comments-v2`  
**Selected Option**: OPT-3 — Layered Composition  
**Last Updated**: 2026-03-06

---

## Task Dependency Graph

```
T1 (config extension) ─────────┬──────────────────────────────────┐
                                │                                  │
T2 (technique phrases) [P]  T3 (signal templates + assembly)  T5c (wrong-move config)
        │                       │                                  │
        │                   T4 (vital move detector)               │
        │                       │                                  │
        └──────────┬────────────┘                                  │
                   │                                               │
        T5 (wrong-move classifier) ←───────────────────────────────┘
                   │
        T6 (assembly engine + tests)
                   │
        T7 (integration: full comment generator)
                   │
        T8 (expert review: 50+ puzzles)
                   │
        T9 (full test suite + docs)
```

`[P]` = can run in parallel with adjacent tasks at same dependency level.

---

## Tasks

### T1 — Config Schema Extension

**Description**: Extend `config/teaching-comments.json` with V2 fields: `technique_phrase` per tag, `vital_move_comment` per tag, `signal_templates` section, `assembly_rules` section, `annotation_policy` section. Extend wrong-move templates with 5 new conditions. Bump version to 2.0. Update JSON schema.

**Files**:

- `config/teaching-comments.json` (modify)
- `config/schemas/teaching-comments.schema.json` (modify)

**Deps**: None  
**Acceptance**: Config parses without error. Schema validates. All existing fields preserved (including `delta_annotations` — carried forward unchanged per RC-3). New fields present with defaults.

---

### T2 — Technique Phrases for All 28 Tags [P]

**Description**: Add `technique_phrase` (2-4 word technique name + Japanese term) and `vital_move_comment` to each of the 28 tag entries. Technique phrases must be SHORT — they compose with signal phrases under 15-word cap. Vital move comments use alias-specific language where aliases exist.

**Files**:

- `config/teaching-comments.json` (modify — per-tag fields)

**Deps**: T1  
**Acceptance**: All 28 tags have `technique_phrase`. All tags with aliases have `vital_move_comment`. Word count of each `technique_phrase` ≤ 4 words.

**Reference** (B.4.1 tests): Verify each phrase matches Sensei's Library golden reference for terminology.

---

### T3 — Signal Templates + Assembly Rules [P]

**Description**: Add `signal_templates` section with 6 signal types: `vital_point`, `forcing`, `non_obvious`, `unique_solution`, `sacrifice_setup`, `opponent_takes_vital`. Add `assembly_rules` section with composition pattern, 15-word max, and overflow strategy.

**Files**:

- `config/teaching-comments.json` (modify — new sections)

**Deps**: T1  
**Acceptance**: 6 signal templates each ≤ 10 words (most ≤ 6). Assembly rules present with `overflow_strategy: "signal_replaces_mechanism"`, `parenthetical_counting` rule codified (RC-4), and `coord_token: "{!xy}"` — transform-safe coordinate format, never hardcoded board positions (same convention as YH hint tokens).

---

### T4 — Vital Move Detector

**Description**: Implement vital move detection that identifies the decisive tesuji in the solution tree. Uses the enriched solution tree (branching factor) and engine ownership data. Returns the node + its technique context.

**Algorithm**:

1. If `move_order != "strict"` → return None (GOV-V2-01)
2. Walk correct-move path beyond root
3. Find first node where correct alternatives > 1 (branching decision point)
4. OR find first node where ownership change exceeds threshold (engine confirmation)
5. Return vital node with alias selection (GOV-V2-02: alias at vital move, parent at first move)

**Files**:

- `tools/puzzle-enrichment-lab/phase_b/vital_move.py` (new)
- `tools/puzzle-enrichment-lab/tests/test_vital_move.py` (new)

**Deps**: T1  
**Tests**:

- `test_strict_order_finds_vital_move()` — multi-move sequence, vital at branch point
- `test_flexible_order_returns_none()` — YO=flexible → no vital move
- `test_miai_returns_none()` — YO=miai → no vital move
- `test_first_move_is_vital_skips()` — vital move == first move → None (avoid duplicate)
- `test_no_branching_returns_none()` — forced sequence → no vital move
- `test_alias_selection_at_vital()` — dead-shapes puzzle → "Bent Four" alias selected
- `test_ownership_change_confirmation()` — engine ownership confirms vital point

---

### T5 — Wrong-Move Refutation Classifier

**Description**: Implement refutation outcome classification that examines each wrong-move branch using engine PV data and solution tree structure. Classifies the outcome into one of 8 conditions (ordered by priority). Ranks wrong moves by refutation depth, selects top 3 for causal annotation (GOV-V2-04).

**Conditions (priority order, GOV-V2-03)**:

1. `immediate_capture` — PV depth ≤ 1, capture verified
2. `opponent_escapes` — refutation PV shows escape
3. `opponent_lives` — ownership flip: dead→alive
4. `capturing_race_lost` — liberty comparison
5. `opponent_takes_vital` — refutation PV[0] coord == correct first move coord
6. `shape_death_alias` — tag=dead-shapes + alias match
7. `ko_involved` — ko detected in PV
8. `default` — always matches

**Files**:

- `tools/puzzle-enrichment-lab/phase_b/refutation_classifier.py` (new)
- `tools/puzzle-enrichment-lab/tests/test_refutation_classifier.py` (new)

**Deps**: T1 (for config conditions), T5c (wrong-move template config already added in T1)  
**Tests**:

- `test_immediate_capture_classified()` — PV depth 1 + capture → "immediate_capture"
- `test_opponent_escapes_classified()` — escape PV → "opponent_escapes"
- `test_opponent_lives_classified()` — ownership shows alive → "opponent_lives"
- `test_capturing_race_classified()` — liberty count comparison → "capturing_race_lost"
- `test_opponent_takes_vital_classified()` — refutation coord == correct coord → "opponent_takes_vital"
- `test_shape_death_alias_classified()` — dead-shapes + bent-four → "shape_death_alias"
- `test_ko_classified()` — ko in PV → "ko_involved"
- `test_default_fallback()` — no condition matches → "default"
- `test_priority_order()` — overlapping conditions → highest priority wins
- `test_top3_selection()` — 5 wrong moves → top 3 by refutation depth get causal, rest get default
- `test_shallow_tree_guard()` — refutation depth < threshold → "default" (no causal claim)

---

### T6 — Assembly Engine + Tests

**Description**: Implement the comment assembly engine that composes Layer 1 (technique phrase) and Layer 2 (signal phrase) into a final comment string. Handles: composition, 15-word cap enforcement, overflow strategy (signal replaces mechanism), V1 fallback (no signal → emit V1 `comment`), vital move assembly, wrong-move assembly.

**Files**:

- `tools/puzzle-enrichment-lab/phase_b/comment_assembler.py` (new)
- `tools/puzzle-enrichment-lab/tests/test_comment_assembler.py` (new)

**Deps**: T2, T3, T4, T5  
**Tests**:

- `test_compose_technique_and_signal()` — "Snapback (uttegaeshi) — this is the vital point at C3."
- `test_15_word_cap_enforced()` — over 15 words → signal replaces mechanism suffix
- `test_overflow_replaces_mechanism()` — verify GOV-C4 behavior
- `test_no_signal_falls_back_to_v1()` — no signal detected → emit V1 `comment` field verbatim
- `test_empty_signal_falls_back()` — empty signal phrase → V1 fallback
- `test_empty_technique_phrase()` — edge case: missing technique_phrase → V1 fallback
- `test_exact_15_words()` — exactly at cap → passes (no truncation)
- `test_vital_move_uses_alias()` — vital node → alias phrase + signal
- `test_vital_move_no_alias_skips()` — no alias available → skip vital move comment (avoid duplication)
- `test_wrong_move_assembly()` — causal template with {coord} substitution
- `test_coord_token_replaced()` — `{!xy}` token → actual SGF coordinate at assembly time
- `test_alias_token_replaced()` — `{alias}` → actual alias name
- `test_japanese_term_word_count()` — "(uttegaeshi)" counted as 1 word in parentheses

---

### T7 — Integration: Full Comment Generator

**Description**: Wire the complete comment generation pipeline: signal detection → Layer 1 → Layer 2 → assembly → placement on correct nodes, vital nodes, and wrong-move nodes. Integrates with `AiAnalysisResult` and enriched solution tree. Emits `teaching_comments` field in result. Sets `hc` quality level (hc:2 or hc:3).

**Files**:

- `tools/puzzle-enrichment-lab/phase_b/teaching_comments.py` (new — main entry point)
- `tools/puzzle-enrichment-lab/tests/test_teaching_comments_integration.py` (new)
- `tools/puzzle-enrichment-lab/analyzers/enrich_single.py` (modify — update import to V2 generator)
- `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py` (delete — V1 superseded, per RC-1)
- `tools/puzzle-enrichment-lab/tests/test_teaching_comments.py` (modify — migrate to V2 API)
- `tools/puzzle-enrichment-lab/tests/test_teaching_comments_config.py` (modify — update imports)
- `tools/puzzle-enrichment-lab/tests/test_teaching_comment_embedding.py` (modify — update to V2 embedding: vital move nodes + wrong-move top-3 placement)

**Deps**: T4, T5, T6  
**Tests**:

- `test_full_pipeline_snapback()` — snapback puzzle → first move comment + vital move comment
- `test_full_pipeline_dead_shapes()` — dead-shapes→bent-four → alias progression
- `test_full_pipeline_wrong_moves()` — 5 wrong moves → top 3 get causal, 2 get default
- `test_full_pipeline_no_vital()` — depth-1 puzzle → first move only, no vital
- `test_full_pipeline_flexible_order()` — YO=flexible → no vital move annotation
- `test_hc3_set_when_signal_present()` — signal detected → hc:3
- `test_hc2_set_when_no_signal()` — V1 fallback → hc:2
- `test_confidence_gate_suppressed()` — low confidence → no comment emitted (hc:0)
- `test_one_insight_per_node()` — never more than one comment per node
- `test_max_correct_annotations()` — max 2 correct-node annotations
- `test_10_reference_puzzles()` — cover each category (life-and-death, tesuji, dead shapes, capture-race, etc.)

**V1 Removal Subtask (RC-1)**:

1. Delete `analyzers/teaching_comments.py` (V1 generator)
2. Update `analyzers/enrich_single.py` import chain → point to `phase_b.teaching_comments`
3. Migrate `tests/test_teaching_comments.py` to test V2 API via `phase_b.teaching_comments`
4. Update `tests/test_teaching_comments_config.py` imports
5. Update `tests/test_teaching_comment_embedding.py` → add tests for V2 embedding (vital move node placement, wrong-move top-3 node placement, `{!xy}` token resolution in embedded `C[]`)
6. Verify no other files import from `analyzers.teaching_comments`

---

### T8 — Expert Review: 50+ Puzzles

**Description**: Run the comment generator on a diverse set of ≥50 puzzles from reference collections. Go expert reviews ALL outputs for: Go accuracy, naturalness of composed language, pedagogical quality, Japanese terminology correctness, misleading comments, noise level. Feedback drives template iteration.

**Puzzle selection**: Cover all 28 tags, multiple difficulty levels, flexible/miai/strict move orders, puzzles with deep trees, puzzles with multiple wrong moves.

**Files**:

- Test fixtures + review notes

**Deps**: T7  
**Acceptance**: Expert confirms ≥90% of comments are pedagogically sound. Any flagged comments → template iteration.

---

### T9 — Full Test Suite + Documentation

**Description**: Run complete test suite. Update documentation: `docs/concepts/teaching-comments.md` (V2 architecture, two-layer model, signal types), `docs/architecture/backend/hint-architecture.md` (V2 teaching comment section). CHANGELOG entry.

**Files**:

- `docs/concepts/teaching-comments.md` (modify — V2 architecture: two-layer model, 6 signal types, vital move detection, wrong-move classification, `{!xy}` token system)
- `docs/architecture/backend/hint-architecture.md` (modify — add V2 teaching comment section)
- `docs/architecture/backend/enrichment.md` (modify — update teaching comment pipeline references to V2)
- `CHANGELOG.md` (modify — add V2 entry)

**Deps**: T7, T8  
**Tests**: Full `pytest` suite — all existing + new tests pass. Zero regressions.

---

## Summary

| Metric           | Count                                                                                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------ |
| Total tasks      | 9                                                                                                            |
| New files        | 6 (vital_move.py, refutation_classifier.py, comment_assembler.py, teaching_comments.py, + 4 test files)      |
| Modified files   | 8 (config JSON, config schema, enrich_single.py, 3 existing test files, enrichment.md, hint-architecture.md) |
| Deleted files    | 1 (analyzers/teaching_comments.py — V1 superseded per RC-1)                                                  |
| Test tasks       | T4-T7 each include unit/integration tests                                                                    |
| Expert review    | T8 (50+ puzzles)                                                                                             |
| Parallel markers | T2 ∥ T3 (config edits in parallel after T1)                                                                  |

### Compatibility

| Question                | Answer                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Backward compatibility? | Not required — one system, clean break                                                                                    |
| Legacy removal?         | V1 `analyzers/teaching_comments.py` deleted in T7 (RC-1). Imports migrated to `phase_b.teaching_comments`. Tests updated. |
| Config migration?       | Additive extension (`version: 1.0 → 2.0`), all V1 fields preserved                                                        |
| Breaking changes?       | None — new fields are additive                                                                                            |
