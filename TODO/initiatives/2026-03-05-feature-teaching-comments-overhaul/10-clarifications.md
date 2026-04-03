# Clarifications — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Q1: Backward compatibility and legacy removal

**Answer**: No backward compatibility required. Old hardcoded `TECHNIQUE_COMMENTS` dict in `teaching_comments.py` and `WRONG_MOVE_TEMPLATES` will be removed. The lab's `hint_generator.py` `TECHNIQUE_HINTS` dict (a duplicate of production) will also be migrated.

**Decision**: `remove_old_code = true`

---

## Q2: Where should teaching comment templates live?

**Answer**: Move to config — a centralized JSON config file (e.g., `config/teaching-comments.json`), following the pattern of `config/go-tips.json`. This gives non-developers the ability to review and refine comment text without touching Python code.

---

## Q3: Intended consumer of teaching comments

**Answer**: Teaching comments **will be embedded into SGF** as move `C[]` properties on the solution tree nodes (correct moves and wrong/refutation moves). This is the target end state.

**Current state**: The enrichment lab computes `teaching_comments` (stored in JSON result via `AiAnalysisResult.teaching_comments`) but `sgf_enricher.enrich_sgf()` does **not** write them into the SGF solution tree. The `--emit-sgf` CLI flag writes enriched SGF but only handles root properties (YR, YG, YX, YQ) and refutation branch structure — not solution move comments.

**Gap identified**: A new Phase in `sgf_enricher.py` is needed to embed teaching comments as `C[]` on correct-move nodes and refutation-move nodes.

**Frontend**: The frontend already has the ability to display move comments (`C[]`). No new frontend work is needed.

---

## Q4: Verbosity vs precision — target style

**Answer**: **High quality, highly precise, targeted, and never misleading**. This is an **inviolate design rule**:

1. **Precision over verbosity** — comments must be factual and technique-specific
2. **Never false, never vague, never wrong** — if there is any doubt, do not emit the comment
3. **Add only when absolutely certain** — if a tag classification has LOW or MEDIUM confidence, suppress the comment entirely
4. **Grounded in the position** — comments should help the student identify what to look for, not generic Go instruction

This must be recorded as a formal design principle in the documentation.

---

## Q5: Coverage scope

**Answer**: **All tsumego-focused tags — and alias-aware teaching**. Not a mechanical coverage of 28 slugs. The 28 canonical tags normalize ~250+ aliases representing real Go concepts students encounter: `semeai` (alias of `capture-race`), `damezumari` (alias of `liberty-shortage`), `oiotoshi` (alias of `connect-and-die`), `uttegaeshi` (alias of `snapback`), etc. The `dead-shapes` tag alone has 30+ aliases representing distinct shapes: `bent-four`, `bulky-five`, `rabbity-six`, `l-group`, `straight-three`, etc.

Teaching comments should:

1. **Cover all 28 canonical tags** for the primary comment
2. **Include Japanese/Korean romanized terms** in comments where standard (e.g., "Snapback (uttegaeshi)" not just "Snapback") so students learn the terminology
3. **For tags with high-value sub-concept aliases** (especially `dead-shapes` and `tesuji`), the config should support sub-comments keyed by alias when the classifier or source provides a more specific label. Example: If the tagger identifies `bent-four` specifically (not just generic `dead-shapes`), the comment should say "Bent four in the corner — this shape is unconditionally dead" rather than the generic dead-shapes comment.
4. The `tesuji` tag has 35+ aliases representing distinct techniques (hane, kosumi, keima, crane's nest, wedge, etc.) — many are themselves tsumego-relevant. Sub-comments for the most common ones help students learn.

The objective is **helping the student learn**, not covering a count of 28. Check with Governance Board.

### Objectives coverage (`config/puzzle-objectives.json`)

The 23 objectives (LIVE, KILL, ESCAPE, CAPTURE, CONNECT, CUT, SEMEAI, KO, SEKI, TESUJI, ENDGAME, etc.) are side-specific but their `objective_type` maps to teaching concepts. The teaching comment system should be aware of the objective (e.g., "Your group needs to live" vs "Kill the opponent's group") to frame the comment correctly.

---

## Governance Board Questions (to be resolved)

1. Should teaching comments be 1-sentence (technique naming + key insight) or 2-3 sentences (with reasoning)?
2. Should `joseki` and `fuseki` tags get teaching comments? They are rarely tsumego but exist in the tag taxonomy.
3. What is the confidence threshold for emitting a teaching comment? Same as hint threshold (HIGH+)?
4. Should wrong-move comments reference specific board-state signals (delta, liberty count) or remain template-based?
5. How should the config structure teaching comments — flat dict, or nested with alias sub-comments?
6. For sub-concept aliases (bent-four, crane's nest, hane, etc.), should specific comments be emitted only when the classifier provides the specific alias, or should the system attempt to detect them?
