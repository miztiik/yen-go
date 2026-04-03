# Tasks — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Compatibility Strategy

- **Backward compatibility**: NOT required
- **Legacy removal**: YES — remove all hardcoded template dicts from Python code

---

## Task Checklist

### Phase A: Config Creation (foundation — all other phases depend on this)

- [ ] **T-01** Create `config/teaching-comments.json` with all 28 canonical tag entries
  - Files: `config/teaching-comments.json`
  - Each entry: `{ "comment": "...", "hint_text": "...", "min_confidence": "HIGH" }`
  - `hint_text`: technique name + Japanese term only (no mechanism suffix). Used for YH Tier 1 hints.
  - `comment`: full teaching comment with mechanism. Used for SGF C[] embedding.
  - Include Japanese/Korean romanized terms where standard
  - Comments: max 15 words, format = `{Technique} ({jp_term}) — {one key mechanism}`
  - Set `joseki` and `fuseki` entries to `"min_confidence": "CERTAIN"` (stricter gate, per Governance)
  - Dependency: none

- [ ] **T-02** Add alias sub-comments for `dead-shapes` tag (high-value aliases)
  - Files: `config/teaching-comments.json`
  - Sub-entries for: `bent-four`, `bulky-five`, `rabbity-six`, `l-group`, `straight-three`, `flower-six`, `table-shape`
  - Dependency: T-01
  - [P] parallel with T-03

- [ ] **T-03** Add alias sub-comments for `tesuji` tag (high-value aliases)
  - Files: `config/teaching-comments.json`
  - Sub-entries for: `hane`, `crane's nest`, `wedge`, `tiger's mouth`, `kosumi`, `keima`
  - Dependency: T-01
  - [P] parallel with T-02

- [ ] **T-04** Add wrong-move comment templates to config
  - Files: `config/teaching-comments.json`
  - Templates: `pv_depth_lte_1_AND_captures_verified`, `ko_involved`, `default`
  - Delta annotation thresholds: `significant_loss`, `moderate_loss`
  - Guards for PV truncation
  - Dependency: T-01
  - [P] parallel with T-02, T-03

- [ ] **T-05** Create JSON schema `config/schemas/teaching-comments.schema.json`
  - Files: `config/schemas/teaching-comments.schema.json`
  - Validates: required fields per tag (`comment`, `hint_text`, `min_confidence`), min_confidence enum (HIGH, CERTAIN), alias_comments structure
  - Dependency: T-01
  - [P] parallel with T-02, T-03, T-04

### Phase B: Config Loader (depends on Phase A)

- [ ] **T-06** Add config loader to `tools/puzzle-enrichment-lab/config.py`
  - Files: `tools/puzzle-enrichment-lab/config.py`
  - New Pydantic models: `TeachingCommentEntry`, `WrongMoveTemplate`, `TeachingCommentsConfig`
  - Load from `config/teaching-comments.json`
  - Cache after first load (same pattern as existing `load_enrichment_config`)
  - Dependency: T-01

- [ ] **T-07** Write unit tests for config loader
  - Files: `tools/puzzle-enrichment-lab/tests/` (new test file)
  - Test: all 28 tags present, schema validates, alias sub-comments load, confidence enums valid
  - Dependency: T-06

### Phase C: Migrate `teaching_comments.py` (depends on Phase B)

- [ ] **T-08** Rewrite `generate_teaching_comments()` to read from config
  - Files: `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py`
  - Remove `TECHNIQUE_COMMENTS` dict (25 entries)
  - Remove `WRONG_MOVE_TEMPLATES` dict (4 entries)
  - Load from config via T-06 loader
  - Implement alias-aware lookup: if technique_tags contain a recognized alias, use alias_comment; else use tag comment
  - Add confidence gating: suppress comment when tag confidence < entry's `min_confidence`
  - Dependency: T-06

- [ ] **T-09** Fix PV truncation bug in wrong-move comments
  - Files: `tools/puzzle-enrichment-lab/analyzers/teaching_comments.py`
  - Guard: only emit "captured immediately" when PV depth verified ≥ actual (not truncated)
  - Fallback to generic "Wrong. The opponent has a strong response." when PV is truncated
  - Dependency: T-08
  - [P] parallel with T-10

- [ ] **T-10** Write unit tests for migrated `generate_teaching_comments()`
  - Files: `tools/puzzle-enrichment-lab/tests/` (new/updated test file)
  - Test: correct tag → correct comment, alias → alias sub-comment, confidence gating, PV truncation guard
  - Dependency: T-08
  - [P] parallel with T-09

### Phase D: Migrate `hint_generator.py` (depends on Phase B; parallel with Phase C)

- [ ] **T-11** Rewrite lab `hint_generator.py` to read from config
  - Files: `tools/puzzle-enrichment-lab/analyzers/hint_generator.py`
  - Remove `TECHNIQUE_HINTS` dict (25 entries)
  - Remove `REASONING_HINTS` dict (~12 entries)
  - Load `hint_text` field (NOT `comment`) from `config/teaching-comments.json` for YH Tier 1 hints
  - **Governance condition**: `hint_text` = technique name only (e.g. "Snapback (uttegaeshi)"), NOT the full teaching comment with mechanism suffix. This preserves AD-2 hint/teaching separation.
  - Keep `COORDINATE_TEMPLATES` in code (they are format strings with `{!xy}`, not teaching content)
  - Dependency: T-06
  - [P] parallel with Phase C

- [ ] **T-12** Write unit tests for migrated `hint_generator.py`
  - Files: `tools/puzzle-enrichment-lab/tests/`
  - Test: all tags resolve, coordinate templates work, reasoning fallback
  - Dependency: T-11

### Phase E: SGF Embedding (depends on Phase C)

- [ ] **T-13** Add Phase 3 to `sgf_enricher.enrich_sgf()` — embed teaching comments
  - Files: `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`
  - New function: `_embed_teaching_comments(sgf_text, correct_comment, wrong_comments) -> str`
  - Use sgfmill to parse → walk solution tree → set `C[]` on first correct-move node → re-serialize
  - Append to existing `C[]` with `\n\n` separator (never overwrite)
  - No-op when `teaching_comments` is empty (confidence gate upstream)
  - Dependency: T-08

- [ ] **T-14** Clean up dead `comments` parameter in `sgf_parser.py`
  - Files: `tools/puzzle-enrichment-lab/analyzers/sgf_parser.py`
  - Remove unused `comments` parameter from `compose_enriched_sgf()` signature
  - Update all callers of `compose_enriched_sgf()` to remove `comments=` kwarg if any
  - **Governance decision (Condition 1)**: AD-3b removed. Phase 3 uses sgfmill-based `_embed_teaching_comments()` (AD-3), not `_compose_node()` wiring.
  - Dependency: T-13
  - [P] parallel with T-15

- [ ] **T-15** Write integration tests for SGF embedding
  - Files: `tools/puzzle-enrichment-lab/tests/`
  - Test: enriched SGF contains `C[]` on correct-move node, refutation nodes get wrong-move comment, existing `C[]` preserved with append
  - Test: confidence-gated suppression → no `C[]` added
  - Dependency: T-13
  - [P] parallel with T-14

### Phase F: Cleanup and Legacy Removal (depends on Phases C, D)

- [ ] **T-16** Remove old hardcoded dicts and verify no references remain
  - Files: `teaching_comments.py`, `hint_generator.py`
  - Grep for `TECHNIQUE_COMMENTS`, `WRONG_MOVE_TEMPLATES`, `TECHNIQUE_HINTS`, `REASONING_HINTS`
  - Confirm zero matches in lab code
  - Dependency: T-08, T-11

- [ ] **T-17** Run full lab test suite
  - Command: `cd tools/puzzle-enrichment-lab && pytest`
  - Verify all existing tests pass after migration
  - Dependency: T-16

### Phase G: Documentation (parallel with Phase F)

- [ ] **T-18** Create `docs/concepts/teaching-comments.md`
  - Files: `docs/concepts/teaching-comments.md`
  - Content: design principles (precision-over-emission, confidence gating, one-insight-rule), config schema reference, relationship to hints/tips, alias sub-comment rationale
  - **Governance condition**: Include "Known Limitations (V1)" section: teaching comment placed on first correct-move node only; may miss actual tesuji in multi-move forcing sequences. Include rationale (simplicity, redundancy avoidance) and future expansion path.
  - Cross-references to `docs/architecture/backend/hint-architecture.md`, `docs/concepts/hints.md`
  - Dependency: T-01
  - [P] parallel with Phase F

- [ ] **T-19** Update `docs/architecture/backend/hint-architecture.md` with teaching comments relationship
  - Files: `docs/architecture/backend/hint-architecture.md`
  - Add section: "Teaching Comments vs. Hints vs. Tips" table
  - Cross-reference to `docs/concepts/teaching-comments.md`
  - Dependency: T-18
  - [P] parallel with T-18

### Phase H: Validation tag coverage (final gate)

- [ ] **T-20** Add cross-validation test: `config/teaching-comments.json` covers all `config/tags.json` slugs
  - Files: `tools/puzzle-enrichment-lab/tests/`
  - Parametrized test: for each slug in `tags.json`, assert entry exists in `teaching-comments.json`
  - Bonus: validate alias sub-comments reference valid aliases from `tags.json`
  - Dependency: T-01, T-07

---

## Dependency Graph

```
Phase A: T-01 → T-02 [P] T-03 [P] T-04 [P] T-05
                  ↓
Phase B: T-06 → T-07
           ↓           ↓
Phase C: T-08 → T-09 [P] T-10     Phase D: T-11 → T-12 [P]
           ↓
Phase E: T-13 → T-14 [P] T-15
           ↓           ↓
Phase F: T-16 → T-17
           ↓
Phase G: T-18 [P] T-19  (parallel with Phase F)
           ↓
Phase H: T-20
```

## Summary

| Metric          | Count                                                                                  |
| --------------- | -------------------------------------------------------------------------------------- |
| Total tasks     | 20                                                                                     |
| New files       | 4 (config, schema, 2 docs)                                                             |
| Modified files  | 5 (teaching_comments.py, hint_generator.py, sgf_enricher.py, sgf_parser.py, config.py) |
| Test tasks      | 6 (T-07, T-10, T-12, T-15, T-17, T-20)                                                 |
| Parallel phases | C∥D, F∥G                                                                               |
