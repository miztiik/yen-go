# Analysis — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Cross-Artifact Consistency Check

### Charter ↔ Plan

| Charter Goal                  | Plan Coverage                            | Status |
| ----------------------------- | ---------------------------------------- | ------ |
| G1: Centralize to config      | AD-1: config structure defined           | OK     |
| G2: Tighten quality           | AD-5: before/after examples, 15-word max | OK     |
| G3: Full tag + alias coverage | AD-1: alias_comments structure           | OK     |
| G4: Embed in SGF              | AD-3: Phase 3 implementation path        | OK     |
| G5: Confidence gating         | AD-4: gating rules defined               | OK     |
| G6: Align lab and production  | AD-2: separation table                   | OK     |

### Charter ↔ Tasks

| Charter AC                                       | Task(s)              | Status |
| ------------------------------------------------ | -------------------- | ------ |
| AC-1: config exists, 28 tags                     | T-01, T-20           | OK     |
| AC-2: no hardcoded dicts in teaching_comments.py | T-08, T-16           | OK     |
| AC-3: no hardcoded dicts in hint_generator.py    | T-11, T-16           | OK     |
| AC-4: ≤2 sentences, technique-specific           | T-01 (config review) | OK     |
| AC-5: C[] on correct-move                        | T-13, T-15           | OK     |
| AC-6: C[] on refutation-move                     | T-13, T-15           | OK     |
| AC-7: confidence suppression                     | T-08, T-10           | OK     |
| AC-8: PV truncation guard                        | T-09, T-10           | OK     |
| AC-9: existing tests pass                        | T-17                 | OK     |
| AC-10: docs updated                              | T-18, T-19           | OK     |
| AC-11: alias sub-comments                        | T-02, T-03, T-20     | OK     |
| AC-12: Japanese terms                            | T-01                 | OK     |

### Plan ↔ Tasks

| Plan Decision            | Task(s)                                   | Status |
| ------------------------ | ----------------------------------------- | ------ |
| AD-1: config structure   | T-01, T-02, T-03, T-04, T-05              | OK     |
| AD-2: separation         | T-11 (keeps COORDINATE_TEMPLATES in code) | OK     |
| AD-3: SGF embedding      | T-13, T-14, T-15                          | OK     |
| AD-4: confidence gating  | T-08, T-10                                | OK     |
| AD-5: comment tightening | T-01 (config text)                        | OK     |

---

## Coverage Analysis

### Tag Coverage Map

| Tag Slug         | Current TECHNIQUE_COMMENTS? | Current lab TECHNIQUE_HINTS? | Current Production TECHNIQUE_HINTS? | In-scope?                  |
| ---------------- | --------------------------- | ---------------------------- | ----------------------------------- | -------------------------- |
| life-and-death   | YES                         | YES                          | YES                                 | YES                        |
| living           | YES                         | YES                          | YES                                 | YES                        |
| ko               | YES                         | YES                          | YES                                 | YES                        |
| seki             | YES                         | YES                          | YES                                 | YES                        |
| capture-race     | YES (as "semeai")           | YES                          | YES                                 | YES                        |
| escape           | YES                         | YES                          | YES                                 | YES                        |
| snapback         | YES                         | YES                          | YES                                 | YES                        |
| throw-in         | YES                         | YES                          | YES                                 | YES                        |
| ladder           | YES                         | YES                          | YES                                 | YES                        |
| net              | YES                         | YES                          | YES                                 | YES                        |
| liberty-shortage | NO (only "squeeze" alias)   | NO                           | YES                                 | YES — gap to fill          |
| connect-and-die  | NO                          | NO                           | YES                                 | YES — gap to fill          |
| under-the-stones | YES                         | YES                          | YES                                 | YES                        |
| double-atari     | NO                          | NO                           | YES                                 | YES — gap to fill          |
| vital-point      | NO                          | NO                           | YES                                 | YES — gap to fill          |
| clamp            | NO                          | NO                           | YES                                 | YES — gap to fill          |
| nakade           | NO                          | NO                           | YES                                 | YES                        |
| eye-shape        | YES                         | YES                          | YES                                 | YES                        |
| dead-shapes      | YES                         | YES                          | YES                                 | YES (+ alias sub-comments) |
| connection       | YES                         | YES                          | YES                                 | YES                        |
| cutting          | YES                         | YES                          | YES                                 | YES                        |
| corner           | YES                         | YES                          | YES                                 | YES                        |
| sacrifice        | YES                         | YES                          | YES                                 | YES                        |
| shape            | YES                         | YES                          | YES                                 | YES                        |
| endgame          | YES                         | YES                          | YES                                 | YES                        |
| tesuji           | YES                         | YES                          | YES                                 | YES (+ alias sub-comments) |
| joseki           | NO                          | NO                           | YES                                 | YES — gap to fill          |
| fuseki           | NO                          | NO                           | YES                                 | YES — gap to fill          |

**Gaps identified**: 7 tags missing from lab `TECHNIQUE_COMMENTS`:
`liberty-shortage`, `connect-and-die`, `double-atari`, `vital-point`, `clamp`, `joseki`, `fuseki`

**Alias duplication issues**: Lab has `semeai`, `squeeze`, `surround`, `atari`, `capture` as separate entries — these are aliases of canonical tags and should collapse into their canonical entries.

### Findings

#### Severity: HIGH

1. **F-01: PV truncation → false "captured immediately" claims** (known bug, documented in katago-enrichment-review.md)
   - Current: `ref_depth <= 1` → "This move is captured immediately" even for deep net sequences
   - Fix: T-09 guards with PV truncation detection
   - Risk: misleading teaching comments violate the "never false" principle

2. **F-02: 7 canonical tags have NO teaching comment** — students encountering liberty-shortage, double-atari, connect-and-die, vital-point, clamp, joseki, or fuseki puzzles get generic fallback
   - Fix: T-01 fills all 28 entries

3. **F-03: Teaching comments not in SGF** — the entire teaching comment system is compute-and-discard; results live only in JSON, never reach the student
   - Fix: T-13, T-14 wire Phase 3 embedding

#### Severity: MEDIUM

4. **F-04: Verbose comments (30-40 words) dilute learning** — generic Go instruction ("The key is recognizing that the capture creates a self-atari for the opponent") adds no precision
   - Fix: T-01 tightens to ≤15 words per comment

5. **F-05: Alias-rich tags (dead-shapes: 30+ aliases, tesuji: 35+ aliases) lose specificity** — student sees "dead shapes" when the actual concept is "bent four in the corner"
   - Fix: T-02, T-03 add alias sub-comments for high-value aliases

6. **F-06: Templates hardcoded in Python across 3 files** — `teaching_comments.py`, `hint_generator.py`, and production `hints.py` all have overlapping dicts
   - Fix: T-01, T-06, T-08, T-11 centralize to config

#### Severity: LOW

7. **F-07: `joseki` and `fuseki` rarely appear as tsumego but exist in taxonomy** — Governance Board to confirm inclusion vs. explicit exclusion
   - Recommendation: include with conservative comments and HIGH confidence gate

---

## Unmapped Tasks

No unmapped tasks found. All charter goals, plan decisions, and acceptance criteria have corresponding tasks.

---

## Risk Summary

| Risk                                     | Severity | Mitigation Task              |
| ---------------------------------------- | -------- | ---------------------------- |
| PV truncation → false claims             | HIGH     | T-09                         |
| Missing tag coverage                     | HIGH     | T-01, T-20                   |
| Teaching comments unreachable to student | HIGH     | T-13, T-14                   |
| Verbose/vague comments                   | MEDIUM   | T-01                         |
| Alias specificity loss                   | MEDIUM   | T-02, T-03                   |
| Config-code divergence                   | MEDIUM   | T-20 (cross-validation test) |
