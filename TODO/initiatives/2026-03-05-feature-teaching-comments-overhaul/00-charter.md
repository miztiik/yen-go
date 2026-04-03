# Charter — Teaching Comments Overhaul

**Initiative**: `2026-03-05-feature-teaching-comments-overhaul`  
**Last Updated**: 2026-03-05

---

## Goals

1. **Centralize teaching comment templates into config** — Move all teaching comment text from hardcoded Python dicts (`TECHNIQUE_COMMENTS`, `WRONG_MOVE_TEMPLATES` in `teaching_comments.py`; `TECHNIQUE_HINTS`, `REASONING_HINTS` in lab `hint_generator.py`) into a single `config/teaching-comments.json` file.

2. **Tighten comment quality** — Replace verbose, generic 3-4 sentence paragraphs with precise, 1-2 sentence comments that name the technique and provide a single key insight. Remove all vague/generic Go instruction.

3. **Achieve full tag coverage with alias awareness** — Ensure every one of the 28 canonical tags in `config/tags.json` has a teaching comment entry. Identify and fill gaps (currently missing: `joseki`, `fuseki`, `clamp`, `double-atari`, `connect-and-die`, `vital-point`, `liberty-shortage` from the lab's `TECHNIQUE_COMMENTS`). For tags with high-value sub-concept aliases (e.g., `dead-shapes` → `bent-four`, `bulky-five`; `tesuji` → `crane's nest`, `hane`), support alias-specific teaching comments when the classifier provides a precise label. Include Japanese/Korean romanized terms in comments where standard.

4. **Embed teaching comments into SGF** — Extend `sgf_enricher.enrich_sgf()` to write teaching comments as `C[]` properties on solution-tree nodes (correct moves) and refutation-tree nodes (wrong moves) in the emitted SGF.

5. **Enforce precision-over-emission principle** — Add confidence gating so teaching comments are only emitted when tag classification confidence is HIGH+. Emit nothing when uncertain.

6. **Align lab and production** — Ensure the lab's `teaching_comments.py` and `hint_generator.py` both read from the new centralized config, eliminating the current duplication between lab and production `hints.py` template dictionaries.

---

## Non-Goals

- Dynamically generating comments with LLM/AI at build time (out of scope; templates only)
- Changing the frontend comment display system (already works with `C[]`)
- Modifying the production pipeline's `hints.py` `TECHNIQUE_HINTS` (the 3-tier YH system remains separate — it serves hint _disclosure_, not teaching _explanation_)
- Adding level-specific comment variants (future enhancement, not in this initiative)
- Refactoring the technique classifier itself (separate initiative)
- Modifying the production pipeline's enrichment stage (this targets the lab tool only; production wiring is a separate future step)

---

## Constraints

1. **Zero Runtime Backend** — Teaching comments are pre-computed and embedded in SGF at build time.
2. **Config-driven** — All template text must be in JSON config, never hardcoded in Python.
3. **Precision is inviolate** — Never emit a false, vague, or misleading comment. Suppress when uncertain.
4. **No new dependencies** — Use existing libraries only.
5. **Lab tool isolation** — `tools/` must NOT import from `backend/puzzle_manager/`. Config files are the shared contract.

---

## Acceptance Criteria

| #     | Criterion                                                            | Verification                                                    |
| ----- | -------------------------------------------------------------------- | --------------------------------------------------------------- |
| AC-1  | `config/teaching-comments.json` exists with entries for all 28 tags  | JSON schema validation + test                                   |
| AC-2  | `teaching_comments.py` reads from config, not hardcoded dicts        | Code review: no `TECHNIQUE_COMMENTS` dict in Python             |
| AC-3  | Lab `hint_generator.py` reads technique hints from config            | Code review: no `TECHNIQUE_HINTS` dict in `hint_generator.py`   |
| AC-4  | Each teaching comment is ≤2 sentences and technique-specific         | Config review + Governance Board sign-off                       |
| AC-5  | `sgf_enricher.enrich_sgf()` writes `C[]` on correct-move nodes       | Test: enriched SGF contains `C[...]` on solution nodes          |
| AC-6  | `sgf_enricher.enrich_sgf()` writes `C[]` on refutation-move nodes    | Test: enriched SGF contains `C[Wrong. ...]` on refutation nodes |
| AC-7  | Comments suppressed when tag confidence < HIGH                       | Test: LOW/MEDIUM confidence produces no `C[]` on correct moves  |
| AC-8  | Wrong-move comments suppress board-state claims when PV is truncated | Test: truncated PV doesn't produce "captured immediately" text  |
| AC-9  | All existing tests pass after migration                              | `pytest -m "not (cli or slow)"` green                           |
| AC-10 | Documentation updated in `docs/`                                     | `docs/concepts/teaching-comments.md` or equivalent              |
| AC-11 | Alias sub-comments for `dead-shapes` and `tesuji` high-value aliases | Config has entries; test parametrized                           |
| AC-12 | Comments include Japanese terms where standard                       | Config review: e.g., "Snapback (uttegaeshi)"                    |
