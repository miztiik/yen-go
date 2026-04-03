# Research Brief — Teaching Comments V2: Depth, Scope & Placement

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-06  
**Research Question**: How should teaching comments evolve beyond V1 (technique-only, first-move-only) to explain _why_ a move is good/bad, and where in the solution tree should they be placed — without introducing noise or false claims?

---

## Sourcing Legend

Throughout this document, recommendations are labeled by origin:

| Label              | Meaning                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------- |
| **[PANEL-V1]**     | Decided or flagged by the governance panel during V1 review (70-governance-decisions.md)                      |
| **[RESEARCHER]**   | Recommendation by the researcher, backed by external references or internal analysis. Not yet panel-reviewed. |
| **[PROPOSED-GOV]** | Proposed governance decision — needs formal panel deliberation before enforcement.                            |

---

## 1. Research Question & Boundaries

### Core Questions

1. **Scope**: Should teaching comments remain technique-label-only (`"Snapback (uttegaeshi) — allow capture, then recapture"`), or should they also explain _why this specific move is correct/wrong in this position_?
2. **Placement**: Is placing comments only on the first correct move sufficient, or should they also appear on "vital moves" (the decisive tesuji deeper in the tree)?
3. **Wrong moves**: Should wrong-move explanations go beyond the generic `"Wrong. The opponent has a strong response."` to explain _what goes wrong_?
4. **Noise budget**: How to add depth without creating a wall of text that disrupts the solve experience?

### Boundaries

- No LLM-generated comments at build time (templates only, per charter constraint)
- No runtime computation (Zero Runtime Backend)
- Must satisfy the "precision over emission" principle — suppress when uncertain
- Must stay within the existing `config/teaching-comments.json` + `C[]` SGF property architecture

---

## 2. Internal Code Evidence

### IE-1: Current V1 placement is first-correct-move-only

From [docs/concepts/teaching-comments.md](../../docs/concepts/teaching-comments.md) — Known Limitations (V1):

> "Teaching comments are placed on the first correct-move node only. In multi-move forcing sequences, the actual tesuji may be on move 3 or 5."

The `_build_tree()` → `_build_node()` loop in [sgf_builder.py](../../backend/puzzle_manager/core/sgf_builder.py) already walks _every_ node and calls `standardize_move_comment()`. The infrastructure to place comments deeper exists — only the _generation logic_ is missing.

### IE-2: Wrong-move comments are pass-through, not generated

From [enrichment/hints.py](../../backend/puzzle_manager/core/enrichment/hints.py): wrong-move branches get either the source SGF's original comment (cleaned/standardized) or a generic template from `wrong_move_comments.templates` in config. The pipeline does **not** generate causal explanations ("White escapes because of the ladder breaker at E7").

Three templates exist today:
| Condition | Template |
|-----------|----------|
| `pv_depth_lte_1_AND_captures_verified` | "This stone is captured immediately." |
| `ko_involved` | "This leads to a ko, but the direct solution avoids it." |
| `default` | "Wrong. The opponent has a strong response." |

### IE-3: KataGo enrichment deferred teaching comments to Phase B

From [006-implementation-plan-final.md](../../TODO/katago-puzzle-enrichment/006-implementation-plan-final.md) — B.4: The plan has 28 technique templates with `{coord}` token substitution and a comment generator that applies templates to `AiAnalysisResult`. This is the intended future engine for position-aware comments. It is not yet implemented.

### IE-4: Complexity metrics already capture tree shape

`YX[d:1;r:2;s:19;u:1]` stores depth/refutations/solution_length/unique_responses. The `d` (depth) and `u` (unique responses) fields could identify which node in the tree is the "decision point" where the solver's choice actually matters — i.e., the vital move.

### IE-5: Governance panel already flagged the V1 limitation

From [70-governance-decisions.md](70-governance-decisions.md) — Cho Chikun's concern:

> "First-move-only embedding is a real limitation for multi-move forcing sequences — accept as V1 but document."

This was accepted as V1 with a documented expansion path.

---

## 3. External References

### ER-1: Professional tsumego books — comment placement patterns

Authoritative tsumego collections (Cho Chikun's "Encyclopedia of Life and Death", Igo Hatsuyoron, Gokyo Shumyo) use a consistent pattern:

| Location                               | Content                                                            | Frequency                                    |
| -------------------------------------- | ------------------------------------------------------------------ | -------------------------------------------- |
| **Solution root** (first correct move) | Technique name + brief explanation                                 | Always                                       |
| **Vital move** (the decisive tesuji)   | "This is the vital point (急所)" or technique-specific annotation  | When move ≠ first move                       |
| **Wrong-move branch**                  | _Why_ it fails: "White plays here → Black's group loses liberties" | Selective — only for instructive refutations |
| **Forced intermediate moves**          | Nothing (or "Forced")                                              | Almost never annotated                       |

**Key insight**: Professional sources annotate at most **2 nodes** per variation: the first move and the vital move. They do NOT annotate every node.

### ER-2: OGS puzzle platform — comment display UX

OGS shows comments inline below the board. Puzzles with comments on every node create a "flicker" effect that disrupts reading. OGS's most-praised puzzles have comments only on: (a) the initial position, (b) the key tesuji, (c) wrong moves where the refutation is non-obvious.

### ER-3: SmartGo / GoBooks app — tiered annotations

SmartGo's digital tsumego books use a three-level system:

1. **Solution node 1**: Technique label ("Snapback")
2. **Vital node**: Board-position explanation ("This placement creates a shortage of liberties for White")
3. **Wrong branches**: Only annotated when the refutation teaches something ("White can escape via ladder")

Non-instructive wrong moves (e.g., random off-topic placements) get no comment.

### ER-4: Pedagogical research — Spaced retrieval + interleaving

Cognitive science (Roediger & Karpicke, 2006; Bjork, 2011) shows that minimal, well-timed feedback aids learning more than verbose explanations. The optimal pattern is:

- **One concept name** (technique labeling → strengthens recall)
- **One causal insight** (why it works → strengthens understanding)
- **Zero extra text** (avoids cognitive overload in a puzzle-solving context)

---

## 4. Candidate Adaptations for Yen-Go

### Option A: "V1.5 — Vital Move Comment" (Conservative) **[RESEARCHER]**

Add a **second** comment placement point in the tree: the "vital move." Motivated by Cho Chikun's V1 concern **[PANEL-V1]** that first-move-only misses the actual tesuji.

| What                     | Detail                                                                                                                                                                                                                       |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Vital move detection** | Walk the solution tree. The vital move is the node where `unique_responses > 1` (the solver must choose among alternatives) AND it's not the first move. If the first move IS the vital move, no change.                     |
| **Comment content**      | Same technique template from `teaching-comments.json` but with a "vital point" framing: `"This is the key move — {existing_comment}"`                                                                                        |
| **Noise budget**         | **[PROPOSED-GOV]** Max 2 annotated correct nodes per solution (first + vital). Forced moves (only 1 child, 0 wrong alternatives) get nothing. Based on professional tsumego book patterns (ER-1), not yet panel-deliberated. |
| **Wrong moves**          | No change from V1.                                                                                                                                                                                                           |
| **Confidence gate**      | Same HIGH+ gate **[PANEL-V1]**. If technique confidence is insufficient, the vital move also gets no comment.                                                                                                                |
| **Complexity**           | Low — tree walk + branching factor check. No new data sources needed.                                                                                                                                                        |

### Option B: "V2 — Causal Wrong-Move Explanations" (Medium) **[RESEARCHER]**

Extend wrong-move comments to explain _what goes wrong_, using signals available from the existing solution tree.

| What                         | Detail                                                                                                                                                                                                                                                                                        |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **New wrong-move templates** | Extend `wrong_move_comments.templates` with tree-structure-based conditions: "The opponent can escape" (wrong move has child where opponent lives), "This loses the capturing race" (opponent has more liberties), "This creates a ko, but a direct kill exists" (already partially covered). |
| **Comment source**           | Solution tree structure only — NOT KataGo. If the wrong move's subtree shows the opponent living/escaping, the template says so. If the tree is unexplored (leaf node), use generic template.                                                                                                 |
| **Guard**                    | Only emit causal wrong-move explanation when the refutation subtree has ≥2 nodes (enough evidence to see the consequence). Single refutation leaf → generic "Wrong."                                                                                                                          |
| **Noise budget**             | Wrong-move comments only shown AFTER the solver plays the wrong move. No pre-solve noise.                                                                                                                                                                                                     |
| **Complexity**               | Medium — requires walking wrong-move subtrees to classify outcomes.                                                                                                                                                                                                                           |

### Option C: "V2 — Position-Aware Correct Move Explanations" (Larger) **[RESEARCHER — DEFERRED]**

Replace the single technique-label template with position-aware templates that use `{!xy}` coordinate tokens and board state to explain _why this specific move works_.

| What                    | Detail                                                                                                                                                    |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **New template format** | `"This throw-in at {!cd} reduces the eye space to one — the group cannot make two eyes."`                                                                 |
| **Data sources**        | Requires KataGo enrichment Phase B (`AiAnalysisResult`) for ownership delta, liberty counts, capture sequences. Not yet available in production pipeline. |
| **Complexity**          | High — depends on KataGo integration. Deferred to Phase B per existing plan.                                                                              |

### Option D: "Composite V1.5+V2a" (Recommended) **[RESEARCHER]**

Combine Option A (vital move comment) + Option B (causal wrong-move explanations) as a self-contained improvement that stays within current data sources.

| Aspect               | Detail                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Correct moves**    | First move + vital move get technique comments (max 2 nodes)                                                             |
| **Wrong moves**      | Tree-structure-based causal explanations replace generic templates when evidence exists                                  |
| **No new data deps** | Uses existing solution tree structure only                                                                               |
| **Confidence**       | Same HIGH+ gate. Causal wrong-move comments also gated: only emit when tree evidence is unambiguous                      |
| **Noise ceiling**    | **[PROPOSED-GOV]** Max 2 correct-node comments + selective wrong-move comments. Forced intermediate moves remain silent. |

---

## 5. Risks, Compliance & Rejection Reasons

### Risks

| Risk                                                                                      | Severity | Mitigation                                                                                  |
| ----------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- |
| **Vital move misidentification** — branching factor heuristic picks the wrong node        | MEDIUM   | Conservative: require `unique_responses > 1` AND `depth > 1`. If ambiguous, don't annotate. |
| **Wrong-move tree too shallow** — source SGF doesn't explore the refutation deeply enough | MEDIUM   | Guard: only emit causal explanation when subtree depth ≥ 2. Otherwise use generic template. |
| **Comment duplication** — vital move = first move in depth-1 puzzles                      | LOW      | Skip vital-move annotation when first move is already the vital move.                       |
| **Noise in collection puzzles** — long sequences with many branch points                  | LOW      | Hard cap: max 2 annotated correct nodes regardless of tree depth.                           |

### Rejection Reasons for Excluded Options **[RESEARCHER]**

| Rejected                              | Reason                                                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **LLM-generated comments**            | Charter constraint: templates only; no runtime AI                                                      |
| **Comment on every correct node**     | Noise — professional sources annotate max 2 nodes per variation (external evidence, not panel-decided) |
| **KataGo-dependent explanations now** | Phase B dependency not yet available; deferred per existing plan                                       |
| **Level-specific comment variants**   | Charter non-goal; would multiply templates by 9                                                        |

### Compliance & License

- All teaching text is original (authored via config templates); no copyright concerns
- Japanese terminology sourced from Sensei's Library (public reference) — terminology, not text
- No new dependencies required

---

## 6. Planner Recommendations (Decision-Ready)

### Recommendation 1: Implement "Vital Move" detection and annotation (Option A) **[RESEARCHER]**

**Priority: HIGH.** Walk the solution tree to find the first node with `unique_responses > 1` that isn't the root move. Place the technique comment there instead of (or in addition to) the first move. This addresses the primary V1 limitation flagged by Cho Chikun **[PANEL-V1]**. The implementation is ~50 lines of tree-walk logic + a branching factor check. No new data sources needed.

### Recommendation 2: Expand wrong-move templates with tree-structure conditions (Option B) **[RESEARCHER]**

**Priority: MEDIUM.** Extend `wrong_move_comments.templates` with ~5 new condition-based templates that classify what happens in the refutation subtree: opponent escapes, opponent lives with two eyes, capturing race lost, ko created (already partially covered). Guard with subtree-depth ≥ 2. This converts the generic "Wrong — The opponent has a strong response" into specific feedback without requiring KataGo.

### Recommendation 3: Defer position-aware explanations to KataGo Phase B (Option C) **[RESEARCHER]**

**Priority: DEFERRED.** Coordinate-aware causal explanations like "This throw-in at {!cd} reduces the eye space to one" require ownership delta and liberty analysis from KataGo enrichment. This is already planned as B.4 in the KataGo enrichment roadmap. Do not build a parallel mechanism.

### Recommendation 4: Enforce annotation noise controls **[PROPOSED-GOV]**

**Priority: HIGH (design constraint).** Professional tsumego books (Cho Chikun's Encyclopedia, Gokyo Shumyo) annotate at most the first move and the key tesuji (external reference ER-1). This pattern is a researcher recommendation based on external evidence — it has **not** been deliberated by the governance panel. The existing V1 panel decisions only cover:

- **[PANEL-V1]** "One insight rule" — one actionable insight per move node
- **[PANEL-V1]** "Precision over emission" — suppress when uncertain
- **[PANEL-V1]** "Confidence gating" — HIGH+ threshold

**Proposed for governance**: Max 2 annotated correct nodes per variation; forced moves never annotated; max 3 causal wrong-move annotations per puzzle. These need a formal panel round before becoming hard constraints.

---

## 7. Governance Decision Proposals

The following 4 open questions require governance deliberation. Each includes domain analysis to inform the panel.

### GOV-V2-01: Vital move annotation for flexible/miai move-order puzzles

**Question**: Should vital-move annotation be suppressed when `YO != strict`?

**Domain analysis:**

| Perspective                          | Position                                 | Reasoning                                                                                                                                                                                                   |
| ------------------------------------ | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Classical tsumego (Cho Chikun lens)  | **Suppress for both**                    | In flexible-order puzzles, there is no single "vital point" — the concept is that multiple moves achieve the same result. Annotating one path as "the key move" is pedagogically misleading.                |
| Tactical creativity (Lee Sedol lens) | **Suppress for miai, keep for flexible** | True miai (A or B equally good) has no vital move. But `flexible` often means the _order_ is flexible while the _moves_ are still required — the hardest move in the sequence is still a valid vital point. |
| AI-era safety (Shin Jinseo lens)     | **Suppress both**                        | If the engine says order doesn't matter, annotating any single node as "key" contradicts the puzzle's own metadata.                                                                                         |
| Systems architecture                 | **Suppress both — simplest safe rule**   | `YO` already classifies this. Branching into "which kind of flexible" adds complexity for edge cases.                                                                                                       |

**Researcher recommendation**: Suppress vital-move annotation when `YO != strict`. Safe, simple, no false claims. Can always relax later.

**Proposed decision**: `vital_move_annotation_scope: "strict_only"` — configurable in `teaching-comments.json`.

---

### GOV-V2-02: Alias sub-comment vs parent tag comment at vital move

**Question**: When alias sub-comments exist (e.g., "bent-four" under "dead-shapes"), what goes on the first move vs the vital move?

**Domain analysis:**

| Perspective                           | Position                          | Reasoning                                                                                                                                                                                 |
| ------------------------------------- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tsumego pedagogy (Cho/Ke lens)        | **Alias when available**          | A student seeing "bent-four" should be told it's bent-four, not generic "dead shapes." Specificity is the entire point of alias sub-comments.                                             |
| Progressive teaching (Lee Sedol lens) | **General→specific progression**  | First move gets parent tag ("Dead Shapes — this shape cannot make two eyes"). Vital move gets alias ("Bent Four — dead in the corner without ko"). Avoids identical text appearing twice. |
| Systems (Staff Engineer lens)         | **Lee Sedol's progression model** | First move = parent tag. Vital move = alias. No duplication, clear pedagogical arc.                                                                                                       |

**Researcher recommendation**: Use the general→specific progression model.

- First correct move: parent tag comment (e.g., "Dead Shapes — this shape cannot make two eyes")
- Vital move: alias sub-comment if available (e.g., "Bent Four — dead in the corner without ko"), else same parent tag comment (skip to avoid duplication)

**Proposed decision**: `alias_placement: "vital_move_preferred"` — alias comment on the vital move, parent tag on the first move. If no alias exists, no vital-move comment (to avoid duplication).

---

### GOV-V2-03: Wrong-move template condition priority

**Question**: When a wrong move's subtree matches multiple conditions (e.g., opponent escapes AND wins capturing race), which template wins?

**Domain analysis:**

| Perspective                          | Position                           | Reasoning                                                                                                                                 |
| ------------------------------------ | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| AI-era precision (Shin Jinseo lens)  | **Most specific condition wins**   | "This loses the capturing race" is more informative than "The opponent escapes." Priority = specificity.                                  |
| Classical pedagogy (Cho Chikun lens) | **Immediate consequence first**    | The first thing that happens to the student's stones matters most. If captured immediately, say that — don't explain downstream strategy. |
| Systems (Staff Engineer lens)        | **Static priority list in config** | Define condition priority in `wrong_move_comments.templates` array order. First matching condition wins. Already how V1 works.            |

**Researcher recommendation**: Keep the existing ordered-array pattern. Add new conditions above `default`, ordered by immediacy of consequence:

```json
"templates": [
  { "condition": "pv_depth_lte_1_AND_captures_verified", "comment": "This stone is captured immediately." },
  { "condition": "opponent_escapes",                      "comment": "The opponent's group breaks out of encirclement." },
  { "condition": "opponent_lives_two_eyes",               "comment": "The opponent makes two eyes and lives." },
  { "condition": "capturing_race_lost",                   "comment": "This loses the capturing race — the opponent has more liberties." },
  { "condition": "ko_involved",                           "comment": "This leads to a ko, but the direct solution avoids it." },
  { "condition": "default",                               "comment": "Wrong. The opponent has a strong response." }
]
```

**Proposed decision**: First-match-wins on ordered array. Conditions ordered by immediacy: immediate capture → escape → lives → semeai loss → ko → default.

---

### GOV-V2-04: Maximum causal wrong-move annotations per puzzle

**Question**: How many wrong-move branches should receive causal explanations (vs generic "Wrong")?

**Domain analysis:**

| Perspective                        | Position                       | Reasoning                                                                                                              |
| ---------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Classical (Cho Chikun lens)        | **Top 3**                      | Professional problem books annotate at most 2-3 wrong variations. More creates a "reference manual" feel.              |
| Tactical/creative (Lee Sedol lens) | **All with evidence, cap 3-5** | If the tree provides clear evidence for 5 wrong moves, why suppress 2? But beyond 5 it gets noisy.                     |
| Learning value (Ke Jie lens)       | **Top 3 by pedagogical value** | Rank by how _instructive_ the refutation is (deeper tree = more instructive). Top 3 get causal text; rest get generic. |
| Systems (Staff Engineer lens)      | **Cap at 3, configurable**     | `max_causal_wrong_moves: 3` in config. Tunable without code changes.                                                   |

**Researcher recommendation**: Cap at 3 causal wrong-move annotations. Rank wrong-move branches by refutation subtree depth (deepest = most evidence = most instructive). Top 3 get causal explanations; remaining wrong moves get the generic template. Make configurable.

**Proposed decision**: `max_causal_wrong_moves: 3` in `teaching-comments.json`. Selection criteria: deepest refutation subtree first.

---

## 8. V2 Implementation Plan Outline

> **Note**: V1 initiative is at closeout. This plan outlines a V2 initiative that builds on the completed V1 foundation. A new initiative (`teaching-comments-v2-depth`) should be created once governance proposals GOV-V2-01 through GOV-V2-04 are decided.

### Correction Level Assessment

**Level 3 — Multiple Files**: 2-3 files changed (config + enrichment logic + tree walker), UI + Logic. Requires phased execution.

### Prerequisites

- V1 initiative completed (config/teaching-comments.json exists, 28 tags, SGF embedding works for first-move)
- Governance decisions on GOV-V2-01 through GOV-V2-04

### Phase 1: Config Extension (foundation)

| Task       | Description                                                 | Files                                          | Deps          |
| ---------- | ----------------------------------------------------------- | ---------------------------------------------- | ------------- |
| **V2-T01** | Add `annotation_policy` section to `teaching-comments.json` | `config/teaching-comments.json`                | GOV decisions |
| **V2-T02** | Add new wrong-move condition templates to config            | `config/teaching-comments.json`                | GOV-V2-03     |
| **V2-T03** | Update JSON schema for new config fields                    | `config/schemas/teaching-comments.schema.json` | V2-T01        |

New config section (pending governance):

```json
{
  "annotation_policy": {
    "max_correct_node_annotations": 2,
    "vital_move_annotation_scope": "strict_only",
    "alias_placement": "vital_move_preferred",
    "max_causal_wrong_moves": 3,
    "causal_wrong_move_ranking": "refutation_depth_desc"
  }
}
```

### Phase 2: Vital Move Detection (core logic)

| Task       | Description                                                            | Files                                                        | Deps                                                         |
| ---------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ---- |
| **V2-T04** | Implement `find_vital_move(solution_tree) -> SolutionNode              | None`                                                        | `backend/puzzle_manager/core/enrichment/vital_move.py` (new) | None |
| **V2-T05** | Unit tests for vital move detection                                    | `backend/puzzle_manager/tests/unit/test_vital_move.py` (new) | V2-T04                                                       |
| **V2-T06** | Wire vital move into enrichment — place teaching comment on vital node | `backend/puzzle_manager/core/enrichment/__init__.py`         | V2-T04, V2-T01                                               |

**Vital move detection algorithm** (V2-T04):

```python
def find_vital_move(root: SolutionNode, move_order: str) -> SolutionNode | None:
    """Find the first decision point in the correct-move path beyond the root.

    Returns None if:
    - move_order is not "strict" (per GOV-V2-01)
    - The first move IS the vital move (no deeper decision point)
    - All correct moves are forced (single child, no alternatives)
    """
    if move_order != "strict":
        return None

    node = root
    for correct_child in walk_correct_path(node):
        if correct_child is root.children[0]:
            continue  # Skip first move (already annotated)
        if count_siblings(correct_child) > 1:  # branching point
            return correct_child
    return None
```

### Phase 3: Wrong-Move Subtree Classification (causal explanations)

| Task       | Description                                                | Files                                                                | Deps           |
| ---------- | ---------------------------------------------------------- | -------------------------------------------------------------------- | -------------- |
| **V2-T07** | Implement `classify_refutation_outcome(wrong_node) -> str` | `backend/puzzle_manager/core/enrichment/refutation.py` (extend)      | None           |
| **V2-T08** | Unit tests for refutation outcome classification           | `backend/puzzle_manager/tests/unit/test_refutation_outcome.py` (new) | V2-T07         |
| **V2-T09** | Wire causal wrong-move templates into SGF builder          | `backend/puzzle_manager/core/sgf_builder.py`                         | V2-T07, V2-T02 |
| **V2-T10** | Integration tests: wrong-move comments in enriched SGF     | `backend/puzzle_manager/tests/`                                      | V2-T09         |

**Refutation outcome classification** (V2-T07):

```python
def classify_refutation_outcome(wrong_node: SolutionNode) -> str:
    """Classify what happens in a wrong-move subtree.

    Returns a condition key matching wrong_move_comments.templates.
    Guard: only returns specific condition when subtree depth >= 2.
    """
    if subtree_depth(wrong_node) < 2:
        return "default"  # Not enough evidence

    # Walk the refutation subtree to classify outcome
    if leads_to_immediate_capture(wrong_node):
        return "pv_depth_lte_1_AND_captures_verified"
    if opponent_escapes(wrong_node):
        return "opponent_escapes"
    if opponent_makes_two_eyes(wrong_node):
        return "opponent_lives_two_eyes"
    if semeai_lost(wrong_node):
        return "capturing_race_lost"
    if involves_ko(wrong_node):
        return "ko_involved"
    return "default"
```

### Phase 4: Comment Placement Orchestration

| Task       | Description                                                     | Files                                                | Deps              |
| ---------- | --------------------------------------------------------------- | ---------------------------------------------------- | ----------------- |
| **V2-T11** | Implement alias-aware comment selection for vital vs first move | `backend/puzzle_manager/core/enrichment/__init__.py` | V2-T06, GOV-V2-02 |
| **V2-T12** | Implement causal wrong-move annotation with ranking + cap       | `backend/puzzle_manager/stages/analyze.py`           | V2-T09, GOV-V2-04 |
| **V2-T13** | Integration test: full enrichment pipeline with V2 comments     | `backend/puzzle_manager/tests/integration/`          | V2-T11, V2-T12    |

### Phase 5: Documentation & Validation

| Task       | Description                                                                                | Files                                            | Deps   |
| ---------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------ | ------ |
| **V2-T14** | Update `docs/concepts/teaching-comments.md` — V2 placement rules, noise budgets            | `docs/concepts/teaching-comments.md`             | V2-T13 |
| **V2-T15** | Update `docs/architecture/backend/hint-architecture.md` — V2 teaching comment architecture | `docs/architecture/backend/hint-architecture.md` | V2-T13 |
| **V2-T16** | Run full test suite: `pytest -m "not (cli or slow)"`                                       | —                                                | All    |

### Dependency Graph

```
                       GOV-V2-01..04 (governance decisions)
                              │
Phase 1:   V2-T01 ─── V2-T02 [P] V2-T03
                │         │
Phase 2:   V2-T04 → V2-T05      Phase 3: V2-T07 → V2-T08
                │                              │
           V2-T06                          V2-T09 → V2-T10
                │                              │
Phase 4:   V2-T11 ────────────────── V2-T12
                │                       │
           V2-T13 (integration)
                │
Phase 5:   V2-T14 [P] V2-T15
                │
           V2-T16 (full test)
```

### Summary

| Metric                | Count                                                             |
| --------------------- | ----------------------------------------------------------------- |
| Total tasks           | 16                                                                |
| New files             | 3 (vital_move.py, test_vital_move.py, test_refutation_outcome.py) |
| Modified files        | 5 (config, schema, enrichment init, refutation.py, analyze.py)    |
| Test tasks            | 5 (V2-T05, V2-T08, V2-T10, V2-T13, V2-T16)                        |
| Blocked on governance | 4 decisions (GOV-V2-01..04)                                       |
| Estimated scope       | ~200 lines new code + ~100 lines test code + config + docs        |

### Breaking Change Assessment

- **Config schema**: Additive (new `annotation_policy` section) — no breaking change
- **SGF output**: Enriched SGFs will have MORE `C[]` nodes (vital move + causal wrong) — no breaking change to frontend (already renders any `C[]`)
- **Quality metrics**: `hc` score may increase for puzzles that gain deeper annotations — positive impact on quality metrics

---

## 9. Confidence & Risk Assessment

| Metric                       | Value      |
| ---------------------------- | ---------- |
| **Post-research confidence** | 82/100     |
| **Post-research risk level** | **medium** |

### Confidence rationale

- Internal architecture is well-understood; tree-walk infrastructure exists
- The vital-move heuristic (branching factor) is sound but needs validation against real puzzles — some edge cases in miai/flexible move order may produce false positives
- Wrong-move tree-structure classification is straightforward for deep trees but gracefully degrades (via guards) for shallow ones

### What's been decided (V1 panel) vs what needs deliberation (V2)

| Item                                           | Status                                                          |
| ---------------------------------------------- | --------------------------------------------------------------- |
| Technique-label comments on first correct move | **[PANEL-V1]** Decided and implemented                          |
| Confidence gating at HIGH+                     | **[PANEL-V1]** Decided and implemented                          |
| One-insight-rule, precision-over-emission      | **[PANEL-V1]** Decided and implemented                          |
| First-move-only is a limitation                | **[PANEL-V1]** Flagged by Cho Chikun, accepted as V1            |
| Vital move annotation                          | **[PROPOSED-GOV]** Needs panel round                            |
| Max annotation cap (2 correct nodes)           | **[PROPOSED-GOV]** Researcher recommendation from external refs |
| Causal wrong-move templates                    | **[PROPOSED-GOV]** Needs panel round                            |
| Wrong-move annotation cap (3)                  | **[PROPOSED-GOV]** Needs panel round                            |
| Noise budget as system invariant               | **[PROPOSED-GOV]** Not yet deliberated                          |

---

## Handoff

```yaml
handover:
  research_completed: true
  initiative_path: "TODO/initiatives/2026-03-05-feature-teaching-comments-overhaul/"
  artifact: "15-research.md"
  governance_review: "GOV-V2-PROPOSAL-CONDITIONAL (Section 10)"
  panel_decision: "approve_with_conditions"
  conditions:
    - "C1: Mandatory scope split — V2a (tree-derived, ship now) vs V2b (engine-derived, deferred)"
    - "C2: No new abstraction layer — extend enrichment/, not a new 'move_quality_signals' module"
    - "C3: Vital move confidence: CERTAIN for category tags, HIGH for specific technique tags"
    - "C4: Signal replaces mechanism suffix (comment_with_signal field), does not append"
  approved_without_conditions:
    - "Wrong move: shape-death alias context"
    - "Preserve 15-word cap, root-first, confidence gate, one-insight-rule"
    - "Wrong move: opponent takes vital point (tree-derivable)"
    - "New hc:3 quality level for signal-enriched comments"
  deferred_to_phase_b:
    - "Low-policy 'non-obvious' signal"
    - "Policy surprise spike detection"
    - "_annotate_delta equivalent in production"
  v2a_scope:
    signals:
      [
        "vital_point_branching",
        "forcing_single_response",
        "unique_solution",
        "opponent_takes_vital_point",
        "shape_death_alias",
      ]
    data_source: "solution tree structure only"
    target: "production pipeline"
  v2b_scope:
    signals:
      [
        "non_obvious_low_policy",
        "policy_surprise_spike",
        "engine_pv_wrong_move",
      ]
    data_source: "KataGo AiAnalysisResult"
    target: "lab tool → backfill"
  post_research_confidence_score: 85
  post_research_risk_level: "medium"
```

top_recommendations: - "[RESEARCHER] Implement vital-move detection + annotation (Option A) — addresses primary V1 limitation" - "[RESEARCHER] Expand wrong-move templates with tree-structure conditions (Option B)" - "[RESEARCHER] Defer position-aware explanations to KataGo Phase B (Option C)" - "[PROPOSED-GOV] Enforce annotation noise controls via governance round"
governance_proposals: - "GOV-V2-01: Suppress vital-move annotation when YO != strict" - "GOV-V2-02: Alias on vital move, parent tag on first move (general→specific)" - "GOV-V2-03: Wrong-move condition priority by immediacy (first-match-wins on ordered array)" - "GOV-V2-04: Max 3 causal wrong-move annotations, ranked by refutation depth"
v2_plan:
phases: 5
tasks: 16
new_files: 3
blocked_on: "GOV-V2-01 through GOV-V2-04"
open_questions: []
post_research_confidence_score: 82
post_research_risk_level: "medium"

```

---

## 11. Governance Panel Re-Consultation — Corrected Enrichment Framing

**Submitted**: 2026-03-06
**Trigger**: Product owner challenged the V2a/V2b split assumption
**Core issue**: Section 10's V2a/V2b scope split assumed production will never have engine data. This is incorrect — all puzzles go through the lab, and Phase B.4 generates teaching comments with full engine access.

### Corrected Understanding

The Section 10 panel review made a factual error about the data availability model. Here is the corrected picture:

#### What the panel assumed (Section 10)

> "The production pipeline processes ~50K puzzles with NO engine access."
> → Therefore split into V2a (tree-only, ship now) and V2b (engine, deferred)

#### What the plans actually say

From `ai-solve-enrichment-plan-v3.md` (DD-5):

> "Build complete solution trees for position-only SGFs, and enrich ALL puzzles through AI — whether they already have solutions or not. AI enrichment is universal, not opt-in."

From `006-implementation-plan-final.md` (Phase B.4):

> Teaching Comments Template Engine lives in `tools/puzzle-enrichment-lab/phase_b/teaching_comments.py`. It generates comments by applying 28 technique templates to `AiAnalysisResult` — which contains policy, winrate, PV, and the ENGINE-ENRICHED solution tree.

The actual data flow:

```

Lab tool (Phase B.4) Production pipeline
┌───────────────────────────────────────┐ ┌──────────────────────────┐
│ 1. KataGo builds/extends solution tree│ │ │
│ 2. Generates AiAnalysisResult JSON │ │ Reads pre-computed JSON │
│ - policy, winrate, PV │ │ (including teaching │
│ - enriched solution tree │ │ comments from B.4) │
│ 3. B.4 generates teaching comments │ ───→ │ │
│ WITH full engine + tree access │ │ Applies to SGF C[] │
│ 4. Comments written into JSON sidecar │ │ │
└───────────────────────────────────────┘ └──────────────────────────┘

````

**Three corrected facts:**

1. **Solution trees will be RICHER after enrichment** — position-only SGFs get full trees built; existing SGFs get validated + extended with new branches. Tree-derived signals work BETTER on enriched trees.

2. **Phase B.4 generates teaching comments WITH full engine access** — the 28 technique templates with `{coord}` tokens are applied to `AiAnalysisResult`, which includes everything (policy, winrate, PV, enriched tree). This is not a "someday" capability — it is already scoped as the next phase of the enrichment plan.

3. **The V2a/V2b split is about deployment timing, not permanent capability** — eventually ALL puzzles will have lab-processed data. The question is what happens in the gap between now and when all puzzles are lab-processed.

### Strategic Question for Panel

Given the corrected framing, three strategic options exist:

| Option | Description | Time to value | Throwaway risk | Coverage |
|--------|-------------|---------------|----------------|----------|
| **X: V2a now → B.4 later** | Ship tree-only improvements to production now. B.4 supersedes them later. | Immediate (50K puzzles) | HIGH — V2a logic replaced by B.4 comments | 100% now (V1+tree), 100% later (B.4) |
| **Y: Skip V2a → focus on B.4** | Keep V1 in production. Design all V2 improvements directly inside B.4 (with engine + enriched tree). | Delayed (requires lab processing) | ZERO — no throwaway code | V1 until lab processes, then B.4 |
| **Z: Unified interface** | Define the teaching comment generation interface in B.4 architecture. Implement tree-only subset first (reusable), then add engine signals. Both run through same code path. | Moderate | LOW — tree-only subset is the B.4 fallback | Tree-only now, full B.4 later |

The product owner's challenge implies Option Y or Z is preferred — "don't design around the engine not being available when the entire plan is to make it available."

---

### Panel Member Re-Reviews

#### Cho Chikun (9p) — Tsumego Pedagogy

**Revised vote: Option Z (Unified interface)**

> I accept the correction. If the lab is going to build richer solution trees and then generate comments with full engine access, we should design for that target state.
>
> However — and this matters — not all puzzles have been lab-processed today. There is a real window where students will encounter puzzles with only V1 comments. The question is how long that window lasts and whether it's acceptable.
>
> My position: **Design the comment generation for the enriched state. But the generation logic should degrade gracefully when engine signals are absent.** A tree-only vital move detection (branching factor heuristic) should be the fallback INSIDE the same system, not a separate V2a module.
>
> This means:
> - If `AiAnalysisResult` is available → use policy, ownership, and enriched tree
> - If NOT available → use solution tree structure alone (same vital-move heuristic from V2a)
> - Same code path, same output format, same confidence gates
>
> **The V2a insights are not wasted — they become the degraded-mode behavior of the unified system.**

---

#### Lee Sedol (9p) — Tactical Creativity

**Revised vote: Option Z with clarification**

> My "tree-derivable" insight from Section 10 is MORE valid now, not less — it becomes the fallback tier of the unified system:
>
> | Tier | Data available | Signals | When |
> |------|---------------|---------|------|
> | **Tier 1 (full)** | AiAnalysisResult + enriched tree | Policy surprise, ownership delta, engine PV, vital point, forcing, unique solution | After lab processing |
> | **Tier 2 (tree-only)** | Solution tree structure only | Vital point (branching), forcing (single response), unique solution (no alternatives) | Before lab processing OR engine data missing |
>
> The tree-derivable signals I identified aren't throwaway — they're the production baseline that runs for every puzzle regardless. Engine signals are an upgrade layer.
>
> **Critical addition**: The enriched solution trees built by the AI-Solve pipeline have MORE branches than the originals. A position-only SGF that had zero solution tree now has a full one. So "tree-derived" signals after enrichment are dramatically better than "tree-derived" signals on the original sparse trees.
>
> **I now recommend: Design for the enriched tree as the primary input. The pre-enrichment tree is the fallback.**

---

#### Shin Jinseo (9p) — AI-Era Professional

**Revised vote: Option Y → Z (shifted)**

> The product owner is correct to challenge Section 10. My V2a/V2b split assumed a permanent architectural boundary. In fact:
>
> - The boundary is temporal, not architectural
> - ALL puzzles will be lab-processed (DD-5: "universal, not opt-in")
> - The AiAnalysisResult JSON sidecar is the data contract between lab and production
>
> **I now agree with Cho Chikun's graceful degradation model.** The teaching comment generator should:
> 1. Accept `AiAnalysisResult | None` as input
> 2. When present → Tier 1 (full signals including policy surprise, coordinate-aware explanations)
> 3. When absent → Tier 2 (tree-structure signals only, same as original V2a scope)
> 4. Same confidence gates, same noise budget, same output format
>
> **Where should this code live?** It should live in Phase B.4 (`tools/puzzle-enrichment-lab/phase_b/teaching_comments.py`) since that's where the 28 templates and generation logic are planned. The production pipeline reads the output via JSON sidecar — it does NOT run the generation logic itself.
>
> Wait — this raises a question. If the generation logic is ONLY in the lab, what happens to puzzles that haven't been lab-processed? They keep V1 comments from production. **The graceful degradation happens during lab processing, not during production publishing.** Every puzzle goes through the lab eventually. The degradation tier handles the case where the LAB runs on a puzzle that doesn't have engine data (unlikely but possible — e.g., engine timeout).

---

#### Ke Jie (9p) — Learning Value

**Revised vote: Option Z**

> The practical learning value doesn't change — students still need to see "this is the vital point" and "this move fails because the opponent escapes." The question is only WHERE and WHEN that logic runs.
>
> I agree with the consensus:
> - The `comment_with_signal` field from Section 10 Condition 4 is still the right config design — it just lives in Phase B.4 templates, not a separate V2a production module.
> - The general→specific progression (GOV-V2-02) and wrong-move condition priority (GOV-V2-03) still apply.
> - The cap of 3 causal wrong-move annotations (GOV-V2-04) still applies.
>
> **What changes**: GOV-V2-01 through GOV-V2-04 are now design inputs to Phase B.4, not a separate V2 initiative. The V2 initiative becomes "define the teaching comment requirements for Phase B.4" rather than "build a separate V2a system."

---

#### Staff Engineer A — Systems Architecture

**Revised vote: Option Z — correct previous concern**

> I retract the non-blocking concern from Section 10. The concern was about scope confusion between production and lab. The corrected framing resolves it:
>
> **Architecture is now clear:**
>
> ```
> tools/puzzle-enrichment-lab/
> └── phase_b/
>     └── teaching_comments.py     ← ALL generation logic lives here
>         ├── generate_comment(result: AiAnalysisResult, tree, config)
>         │   ├── Tier 1: engine signals available → full comment
>         │   └── Tier 2: tree-only fallback → degraded comment
>         └── Output → AiAnalysisResult.teaching_comments field
>
> backend/puzzle_manager/
> └── core/enrichment/hints.py     ← Reads pre-computed comments from JSON
>     └── apply_teaching_comments(sidecar: AiAnalysisResult) → C[] properties
> ```
>
> **What this means for the V2 plan:**
> - Phase 1 (Config Extension): Still needed — GOV-V2-01..04 decisions become config fields in `teaching-comments.json` that Phase B.4 reads.
> - Phase 2 (Vital Move Detection): Moves to Phase B.4, not production. Detection algorithm is the same — it just runs in the lab on enriched trees.
> - Phase 3 (Wrong-Move Classification): Moves to Phase B.4 with RICHER data (engine PV available, deeper refutation trees).
> - Phase 4 (Orchestration): Lives in B.4.2 comment generator.
> - Phase 5 (Docs): Still needed.
>
> **No throwaway code. No two-system problem. Single generation path with graceful degradation.**

---

#### Staff Engineer B — Data Pipeline

**Revised vote: Option Z**

> Agree with the consensus. One pipeline observation:
>
> The production pipeline's `hints.py` already has a stub for reading `AiAnalysisResult`. This stub should consume pre-computed teaching comments from the sidecar JSON — it should NOT implement a parallel generation path. The "apply" is simple: read the `teaching_comments` field from the sidecar, map to SGF `C[]` properties.
>
> **Performance note**: If the lab has already generated comments, the production pipeline's job is trivial — just read and write. No tree-walking at publish time. This is FASTER than V2a would have been.
>
> **Observability**: The two-tier model (Tier 1 full, Tier 2 tree-only) should emit which tier was used, so we can track enrichment coverage. This feeds into the `hc` quality metric:
> - `hc:0` — no teaching comment
> - `hc:1` — V1 basic comment (technique label only, production)
> - `hc:2` — V2 Tier 2 comment (tree-derived signals, lab fallback)
> - `hc:3` — V2 Tier 1 comment (engine + tree signals, full B.4)

---

### Consolidated Revised Decision

**Decision**: `Option Z — Unified two-tier generation in Phase B.4`
**Status Code**: `GOV-V2-REVISED`
**Unanimous**: Yes (6/6)

### What changes from Section 10

| Section 10 decision | Revised decision | Why |
|---------------------|------------------|-----|
| V2a (tree-only) ships independently in production | V2a design becomes Tier 2 fallback inside Phase B.4 | No throwaway code; same algorithm, better location |
| V2b (engine) deferred indefinitely | V2b becomes Tier 1 inside Phase B.4, primary path | Design for the enriched state |
| `vital_move.py` as new production module | Vital move detection lives in Phase B.4 | Runs on enriched trees in lab, not sparse trees in production |
| Wrong-move classification in production `refutation.py` | Wrong-move classification in Phase B.4 with engine PV available | Richer data → better classification |
| New V2 initiative (`teaching-comments-v2-depth`) | V2 becomes requirements input to Phase B.4 | No separate initiative — GOV-V2-01..04 feed B.4 design |

### What stays the same from Section 10

| Decision | Status |
|----------|--------|
| GOV-V2-01: Suppress vital-move annotation when `YO != strict` | **Retained** — applies in B.4 |
| GOV-V2-02: General→specific (parent tag on first move, alias on vital move) | **Retained** — applies in B.4 |
| GOV-V2-03: Wrong-move condition priority by immediacy | **Retained** — conditions richer with engine PV |
| GOV-V2-04: Max 3 causal wrong-move annotations | **Retained** — applies in B.4 |
| C2: No new abstraction layer | **Retained** — even more relevant (no separate V2a module) |
| C3: Confidence gate relaxed to HIGH for specific techniques | **Retained** — applies in B.4 |
| C4: Signal replaces mechanism, `comment_with_signal` field | **Retained** — config schema serves B.4 |
| `hc:3` quality level for signal-enriched comments | **Retained + extended** — hc:2 for Tier 2, hc:3 for Tier 1 |
| 15-word cap, one-insight-rule, precision-over-emission | **Retained** — non-negotiable |

### Revised Phasing

````

Phase 1: Config extension (same as Section 8 Phase 1)
└── GOV-V2-01..04 decisions encoded in teaching-comments.json
└── comment_with_signal field added to tag entries
└── annotation_policy section with caps and gates

Phase 2: Phase B.4 implementation (in tools/puzzle-enrichment-lab/)
└── B.4.1: 28 technique templates with {coord} tokens
└── B.4.2: Two-tier comment generator
├── Tier 1: AiAnalysisResult available → policy + ownership + PV signals
└── Tier 2: Tree-only fallback → branching vital move, forcing, unique solution
└── Vital move detection (enriched tree input)
└── Wrong-move classification (engine PV when available, tree fallback)
└── Comment with signal selection (C4)

Phase 3: Production integration (in backend/puzzle_manager/)
└── hints.py reads pre-computed teaching comments from AiAnalysisResult JSON
└── Maps to SGF C[] properties
└── Emits hc quality level (hc:2 or hc:3 based on tier)

Phase 4: Documentation
└── Update docs/concepts/teaching-comments.md
└── Update docs/architecture/backend/hint-architecture.md

````

### Open Questions (for next planning round)

1. **Transition period**: What happens to the ~50K puzzles between now and when the lab processes them? They stay at V1 (`hc:1`). Is this acceptable, or should the lab prioritize puzzles with the weakest teaching comments?
2. **Lab processing order**: Should the lab batch-process puzzles that currently have `hc:0` or `hc:1` first?
3. **Config location**: Should `annotation_policy` live in `teaching-comments.json` (production config) or `katago-enrichment.json` (lab config)? Since the generation logic is in the lab, the lab config may be more appropriate — but the policy applies globally.

---

## Revised Handoff

```yaml
handover:
  research_completed: true
  initiative_path: "TODO/initiatives/2026-03-05-feature-teaching-comments-overhaul/"
  artifact: "15-research.md"
  governance_review_v1: "GOV-V2-PROPOSAL-CONDITIONAL (Section 10)"
  governance_review_v2: "GOV-V2-REVISED (Section 11) — supersedes Section 10"
  panel_decision: "Option Z — Unified two-tier generation in Phase B.4"
  unanimous: true
  key_correction: "V2a/V2b split replaced by two-tier generation in Phase B.4 with graceful degradation"
  retained_decisions:
    - "GOV-V2-01: Suppress vital-move annotation when YO != strict"
    - "GOV-V2-02: General→specific alias progression"
    - "GOV-V2-03: Wrong-move priority by immediacy"
    - "GOV-V2-04: Max 3 causal wrong-move annotations"
    - "C3: HIGH confidence for specific techniques"
    - "C4: Signal replaces mechanism (comment_with_signal)"
    - "hc:2 for Tier 2, hc:3 for Tier 1"
  what_changes:
    - "No separate V2 initiative — V2 becomes requirements for Phase B.4"
    - "All generation logic in tools/puzzle-enrichment-lab/phase_b/teaching_comments.py"
    - "Production only reads pre-computed comments from JSON sidecar"
    - "Vital move detection runs on enriched trees, not sparse originals"
  open_questions:
    - "Transition period: 50K puzzles stay at V1 until lab-processed"
    - "Lab processing priority order"
    - "Config location: teaching-comments.json vs katago-enrichment.json"
  post_research_confidence_score: 90
  post_research_risk_level: "low"
````

---

## 10. Governance Panel Review — V2 Proposal (Move Quality Signals + Vital Move + Wrong Move Enrichment)

**Submitted**: 2026-03-06  
**Proposal source**: Product owner review  
**Scope**: 5 proposed changes to teaching comments system

### Proposal Summary (Under Review)

| #   | Change                                                                              | Priority | Gate                                       |
| --- | ----------------------------------------------------------------------------------- | -------- | ------------------------------------------ |
| P1  | Move quality signals (vital point, forcing, unique solution) from KataGo            | High     | KataGo policy + delta thresholds           |
| P2  | Vital move node comment deeper in tree                                              | Medium   | CERTAIN confidence + policy surprise spike |
| P3  | Wrong move: "Opponent takes the vital point first"                                  | Medium   | PV depth ≥ 2, not truncated                |
| P4  | Wrong move: shape-death alias context                                               | Low      | Tag = dead-shapes alias + PV confirmed     |
| P5  | No changes to: 15-word cap, root-first placement, confidence gate, one-insight-rule | —        | Preserved                                  |

### Critical Fact: KataGo Data Availability

Before per-member review, the panel must acknowledge a **material constraint** that affects proposals P1, P2, and P3:

| Data source                                 | Production pipeline (`backend/puzzle_manager/`) | Lab tool (`tools/puzzle-enrichment-lab/`)    |
| ------------------------------------------- | ----------------------------------------------- | -------------------------------------------- |
| KataGo policy prior (`correct_move_policy`) | **NOT AVAILABLE**                               | ✅ Available (`AiAnalysisResult.validation`) |
| KataGo winrate data                         | **NOT AVAILABLE**                               | ✅ Available                                 |
| KataGo PV sequences                         | **NOT AVAILABLE**                               | ✅ Available                                 |
| Solution tree structure                     | ✅ Available                                    | ✅ Available                                 |
| Tag classification                          | ✅ Available                                    | ✅ Available                                 |

**Implication**: Proposals P1 (move quality signals) and P2 (policy surprise spike) are **lab-only** unless the backfill mechanism from the lab is used to write signals into the SGF before the production pipeline consumes them. P3 (opponent takes vital point) requires PV data which is similarly lab-only. The production pipeline processes ~50K puzzles with NO engine access.

---

### Panel Member Reviews

#### Cho Chikun (9p) — Tsumego Pedagogy

**Vote: approve_with_conditions**

> The gap analysis is correct and welcome. "What technique?" and "Why does this move achieve it?" are indeed different pedagogical questions. Both belong in a well-annotated tsumego collection.

**On P1 (move quality signals):**

> Approve in principle. "This is the vital point of the shape" and "Only move — all alternatives fail" are precisely the kind of annotations I put in my own published collections. However, gating on KataGo policy alone is insufficient — policy reflects neural network priors, not Go truth. A move with 0.3% policy that is the only correct answer is not "non-obvious" — it is simply hard. The comment should reflect the _pedagogical_ quality, not the _engine's_ assessment.
>
> **Condition**: The "vital point" signal must be grounded in board topology (the move IS at a shape's vital point per eye-shape analysis), not just policy prior. Policy can be a secondary signal for "non-obvious" labeling only.

**On P2 (vital move annotation):**

> This is the right direction. The three-condition gate (forcing first move + policy spike + CERTAIN confidence) is appropriately strict. The proposed comment phrasing is good: "This is the key move" or "Now the {technique} completes" — both are exactly what I write in my problem books.
>
> **Concern**: CERTAIN confidence gate may be too strict. Very few puzzles have CERTAIN tag confidence — most are HIGH. This would make the vital move annotation trigger extremely rarely. Suggest: CERTAIN for the _vital move_ annotation when the technique tag is ambiguous, but HIGH is acceptable when alias sub-comments provide sufficient specificity (e.g., tag = `snapback` is unambiguous at HIGH).

**On P5 (preserving 15-word cap, one-insight-rule):**

> Non-negotiable. Correct decision.

---

#### Lee Sedol (9p) — Tactical Creativity

**Vote: approve**

> The proposal correctly identifies signal underutilization. KataGo gives policy, winrate, and PV — we currently use only winrate delta for wrong-move annotations. The remaining signals should be harvested.

**On P1 (move quality signals):**

> "PV depth = 1, single response → Forcing move" — this is derivable from the solution tree alone, no KataGo needed. If the correct move has exactly one opponent response, it IS forcing. The solution tree already encodes this. Similarly, "short PV with no alternatives → unique solution" = solution tree with no branching.
>
> **Key insight**: Some of these "KataGo signals" can be derived from solution tree structure without any engine. Split the proposal:
>
> - **Tree-derivable signals**: forcing (single opponent response), unique solution (no alternatives at any depth), vital point (branching decision point) → implement NOW in production
> - **Engine-derivable signals**: non-obvious (low policy), surprise move (policy spike) → implement in lab, backfill via Phase B

**On P3 (opponent takes vital point):**

> Excellent addition. "If refutation PV move 1 == correct move coordinate" — this is a powerful insight check. But this requires PV data. For the production pipeline, approximate it: if the wrong move's refutation subtree has the opponent playing on the same intersection as the correct first move, that's the same signal from the tree alone.

---

#### Shin Jinseo (9p) — AI-Era Professional

**Vote: approve_with_conditions**

> The proposal is technically sound but conflates two scopes: what can be built NOW from the solution tree vs. what needs KataGo data.

**On P1 (move quality signals):**

> The table of "KataGo Signal → Derivable Insight" is accurate but misleading about current readiness:
>
> | Signal                             | Actually needs KataGo? | Alternative                                     |
> | ---------------------------------- | ---------------------- | ----------------------------------------------- |
> | High policy → vital point          | Not necessarily        | Solution tree: node with `unique_responses > 1` |
> | Low policy → non-obvious           | **YES** — lab only     | No tree-based equivalent                        |
> | PV depth = 1 → forcing             | **NO**                 | Tree: opponent has exactly 1 child              |
> | Large winrate delta on wrong       | Already implemented    | `_annotate_delta()` in lab                      |
> | Short PV, no alternatives → unique | **NO**                 | Tree: solution_length with no branching         |
>
> **Condition**: Split into two phases. Phase V2a (tree-derivable, production-ready NOW) and Phase V2b (engine-derivable, deferred to KataGo Phase B backfill). Do NOT block tree-based improvements on KataGo availability.

**On P2 (vital move — policy surprise spike):**

> The gate of "policy surprise spike" is the right concept but the WRONG signal source for production. In the solution tree, the "surprise" is structurally apparent: it's where the solver has multiple choices and only one (or few) are correct. Use **branching factor** as a proxy for surprise in production. Reserve policy-based surprise detection for the lab.

---

#### Ke Jie (9p) — Learning Value

**Vote: approve**

> Strong practical value. The "technique ≠ why" gap is real — I see it in my own teaching. Students who know "this is a snapback" still play the wrong move because they don't see _which stone_ is the vital point.

**On P1 (move quality signals):**

> The "one signal per comment, appended to existing technique comment" rule is correct. Example:
>
> - V1: `"Snapback (uttegaeshi) — allow the capture, then recapture the larger group."`
> - V2: `"Snapback (uttegaeshi) — allow the capture, then recapture. This is the vital point."`
>
> But the 15-word cap is tight. "Snapback (uttegaeshi) — allow the capture, then recapture the larger group. This is the vital point." = 17 words. Need to decide: does the signal _replace_ the mechanism suffix or _append_ to it?
>
> **Recommendation**: Replace, not append. The signal IS the mechanism when it's more specific: `"Snapback (uttegaeshi) — this is the vital point that triggers recapture."` (11 words). Config should have two fields: `comment` (technique + mechanism, current) and `comment_with_signal` (technique + signal, when available). Fallback to `comment` when no signal.

**On P4 (wrong move: shape-death alias):**

> High learning value, low risk. "This creates a bent-four — unconditionally dead" is exactly what a teacher would say. And the alias data is already in config. Approve unconditionally.

---

#### Staff Engineer A — Systems Architecture

**Vote: concern (non-blocking)**

> The proposal is pedagogically strong but architecturally tangled. It mixes three different scopes without clear boundary lines.

**Architectural concerns:**

1. **Scope confusion**: The proposal says "KataGo already gives you the signal" — but KataGo signals exist ONLY in the lab tool (`tools/puzzle-enrichment-lab/`). Production (`backend/puzzle_manager/`) has NO engine access. This isn't a minor detail — it determines whether 50K+ existing puzzles can benefit or only lab-enriched puzzles.

2. **Two-system problem**: Teaching comments currently live in `config/teaching-comments.json` and production enrichment. Adding KataGo-dependent signals creates a second path that only works for lab-processed puzzles. This violates the "single source of truth" principle and creates an A/B quality split in the puzzle corpus.

3. **"move_quality_signals enrichment layer"**: This is a NEW abstraction. Per the architecture rules, new abstraction layers require explicit justification. What problem does a separate layer solve that extending `enrich_puzzle()` doesn't?

**Required conditions:**

- **C1**: Split tree-derivable signals (production-ready) from engine-derivable signals (lab-only). Ship tree-based improvements first.
- **C2**: No new `move_quality_signals` module. Extend existing `enrichment/` with the tree-walking logic. New file OK for `vital_move.py`, but not a new "layer."
- **C3**: Engine-dependent signals must wait for the KataGo Phase B backfill mechanism. Do not create a parallel path.

---

#### Staff Engineer B — Data Pipeline

**Vote: approve**

> The gating logic is well-designed. Each proposed signal has an explicit guard condition, and the "emit nothing when uncertain" principle is preserved.

**Pipeline observations:**

1. **Tree-derivable signals are cheap**: Walking the solution tree to classify forcing/unique/branching adds negligible cost (~1ms per puzzle). No pipeline performance concern.

2. **Wrong-move cross-reference** ("opponent takes vital point"): Checking if refutation subtree move == correct first move coordinate is a simple point comparison. No engine needed for production puzzles where the solution tree already contains this data.

3. **Config extension is clean**: Adding `comment_with_signal` to the config schema is additive and backward-compatible. Puzzles without signals fall back to `comment`.

4. **Observability**: Suggest adding a new `hc:3` level to `YQ` for "signal-enriched teaching comment" to distinguish from `hc:2` (basic teaching text). This lets us track rollout impact.

---

### Panel Consolidated Decision

**Decision**: `approve_with_conditions`  
**Status Code**: `GOV-V2-PROPOSAL-CONDITIONAL`  
**Unanimous**: No (5 approve/approve_with_conditions, 1 non-blocking concern)

### Required Conditions (4)

#### Condition 1: Mandatory scope split — tree vs engine

The proposal MUST be split into two phases:

| Phase              | Signals                                                                                                                              | Data source               | Target                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | ------------------------- | --------------------------------------------- |
| **V2a** — Ship now | Vital point (branching), forcing (single response), unique solution (no alternatives), opponent takes vital point (coordinate match) | Solution tree structure   | Production pipeline                           |
| **V2b** — Deferred | Non-obvious (low policy), surprise spike (policy prior delta), KataGo-specific wrong-move PV analysis                                | KataGo `AiAnalysisResult` | Lab tool → backfill to production via Phase B |

**Rationale** (Shin Jinseo, Staff Engineer A): "Do not block tree-based improvements on KataGo availability."

#### Condition 2: No new abstraction layer

Extend existing `enrichment/` package. `vital_move.py` as a new module is acceptable. A separate "move_quality_signals layer" is not. Teaching comment signal logic lives alongside existing enrichment code.

**Rationale** (Staff Engineer A): YAGNI. One call site in `enrich_puzzle()`, not a new architectural layer.

#### Condition 3: Vital move confidence gate — relax from CERTAIN to HIGH for unambiguous tags

The proposal requires CERTAIN for vital move annotation. The panel recommends:

- **CERTAIN**: When primary tag is a category label (life-and-death, tesuji, shape) — ambiguous, needs higher gate
- **HIGH**: When primary tag is a specific technique (snapback, ladder, net, throw-in, nakade) — unambiguous, HIGH is sufficient

This avoids making vital move annotation so rare it never triggers.

**Rationale** (Cho Chikun): "CERTAIN on everything means almost no puzzles get the annotation. The point is to annotate the decisive moment, which is well-defined for specific techniques."

#### Condition 4: Comment signal replaces mechanism suffix, does not append

When a move quality signal is available, it replaces the mechanism text — it does NOT stack on top:

| Without signal                                                                  | With signal                                                                  |
| ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `"Snapback (uttegaeshi) — allow the capture, then recapture the larger group."` | `"Snapback (uttegaeshi) — this is the vital point that triggers recapture."` |

This preserves the 15-word cap and one-insight-rule.

Config schema adds `comment_with_signal` field (optional, per-tag). When absent, falls back to `comment`.

**Rationale** (Ke Jie): "The signal IS the mechanism when it's more specific. Replace, not stack."

---

### Items Approved Without Conditions

| Item                                                                    | Status               | Notes                                                                                                               |
| ----------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------------------------------- |
| P4: Wrong move shape-death alias context                                | **Approved**         | Low risk, high learning value. Alias data already in config. Gate: tag = dead-shapes + alias confirmed.             |
| P5: Preserve 15-word cap, root-first, confidence gate, one-insight-rule | **Approved**         | Non-negotiable. Correct decision.                                                                                   |
| Wrong-move "opponent takes vital point" template                        | **Approved for V2a** | Tree-derivable: check if refutation subtree contains opponent playing at correct-move coordinate. No engine needed. |
| New `hc:3` quality level for signal-enriched comments                   | **Approved**         | Observability improvement. Track separately from `hc:2`.                                                            |

### Items Deferred

| Item                                       | Deferred to    | Reason                        |
| ------------------------------------------ | -------------- | ----------------------------- |
| Low-policy "non-obvious" signal            | KataGo Phase B | Engine data not in production |
| Policy surprise spike detection            | KataGo Phase B | Engine data not in production |
| `_annotate_delta` equivalent in production | KataGo Phase B | Requires winrate data         |

---

### Revised V2 Phasing (Post-Panel)

```
V2a (Ship now — tree-derived, production pipeline)
├── Vital move detection (branching factor heuristic)
├── Forcing move signal (single opponent response)
├── Unique solution signal (no alternatives at any depth)
├── Wrong move: opponent takes vital point (coordinate match)
├── Wrong move: shape-death alias context
├── comment_with_signal config field
└── hc:3 quality level

V2b (Deferred — KataGo Phase B backfill)
├── Non-obvious signal (low policy prior)
├── Policy surprise spike (vital move via policy delta)
├── Engine-derived wrong-move PV analysis
└── Winrate delta annotations in production
```
