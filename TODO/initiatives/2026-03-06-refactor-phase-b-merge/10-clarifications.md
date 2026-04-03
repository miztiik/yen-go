# Clarifications — Phase B Merge Refactor

**Initiative**: `2026-03-06-refactor-phase-b-merge`  
**Last Updated**: 2026-03-06

---

## Investigation Summary

### What is `phase_b/`?

The `tools/puzzle-enrichment-lab/phase_b/` directory contains 4 modules created during the Teaching Comments V2 initiative (`2026-03-06-feature-teaching-comments-v2`):

| File                       | LOC  | Responsibility                                                           |
| -------------------------- | ---- | ------------------------------------------------------------------------ |
| `teaching_comments.py`     | ~200 | V2 two-layer composition engine (correct/vital/wrong comments)           |
| `vital_move.py`            | ~100 | Vital move detector (identifies decisive tesuji in solution tree)        |
| `refutation_classifier.py` | ~170 | Wrong-move classifier (8 priority-ordered conditions)                    |
| `comment_assembler.py`     | ~170 | Assembly engine (15-word cap, overflow, V1 fallback, token substitution) |
| `__init__.py`              | 1    | Package marker                                                           |

### Why does it exist as a separate directory?

The enrichment lab was developed in **phases of work**, not functional modules:

- **Phase A** (implicit) = all existing `analyzers/` modules (validate, refute, rate, classify, enrich)
- **Phase B** = teaching comments V2 enhancement — given its own directory `phase_b/`

The V2 initiative explicitly deleted V1 `analyzers/teaching_comments.py` (RC-1) and put the replacement in `phase_b/teaching_comments.py` instead of back in `analyzers/`. There is **no `phase_a/` directory** — the "phase" naming reflects development timeline, not architecture.

### Where should these modules live?

The natural home is `analyzers/` — which already contains 15 sibling analyzer modules:

| Existing analyzers/ module | Relationship to phase_b                                                           |
| -------------------------- | --------------------------------------------------------------------------------- |
| `technique_classifier.py`  | **Produces** technique_tags consumed by `phase_b/teaching_comments.py`            |
| `hint_generator.py`        | **Sibling** — generates YH hints, `teaching_comments` generates C[] comments      |
| `generate_refutations.py`  | **Upstream** — produces refutations consumed by `refutation_classifier.py`        |
| `enrich_single.py`         | **Orchestrator** — calls `phase_b.teaching_comments.generate_teaching_comments()` |
| `sgf_enricher.py`          | **Downstream** — embeds teaching_comments into SGF C[] properties                 |

### Overlap analysis

| phase_b module             | Overlaps with analyzers/?                                                      | Assessment                                                        |
| -------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| `teaching_comments.py`     | V1 was deleted (RC-1). No current overlap.                                     | Clean replacement — goes back as `analyzers/teaching_comments.py` |
| `vital_move.py`            | No overlap                                                                     | New capability, belongs in `analyzers/`                           |
| `refutation_classifier.py` | Related to `generate_refutations.py` but different role (generate vs classify) | Complementary — no conflict                                       |
| `comment_assembler.py`     | No overlap                                                                     | New, purely compositional                                         |

### Import chain (what changes)

**Current imports:**

1. `analyzers/enrich_single.py:49` → `from phase_b.teaching_comments import generate_teaching_comments`
2. `phase_b/teaching_comments.py:30-39` → `from phase_b.vital_move`, `from phase_b.refutation_classifier`, `from phase_b.comment_assembler`
3. Tests (5 files) → `from phase_b.*` imports

**Documentation referencing `phase_b/`:**

1. `CHANGELOG.md:19` — lists `phase_b/` modules
2. `docs/architecture/tools/katago-enrichment.md:365-371` — D37 architecture decision
3. Multiple TODO initiative docs (historical record)

### Confidence assessment

| Factor              | Deduction  | Rationale                               |
| ------------------- | ---------- | --------------------------------------- |
| Module boundaries   | -0         | Crystal clear: all are analyzers        |
| Migration impact    | -5         | Localized, same package hierarchy level |
| Refactor strategies | -0         | Straightforward directory merge         |
| Test coverage       | -5         | Tests exist, just need import updates   |
| Rollback            | -0         | Simple git revert                       |
| **Total Score**     | **90/100** |                                         |
| **Risk Level**      | **Low**    | Localized refactor with clear ownership |

---

## Clarification Questions

| q_id | question                                                                                                                                               | options                                                                                                                                              | recommended                                                                                                           | user_response | status     |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------- | ---------- |
| Q1   | Is backward compatibility required for any external consumers of the `phase_b` package path?                                                           | A: No external consumers, clean merge / B: Some external scripts reference `phase_b` / C: Other                                                      | A — The only consumer is `analyzers/enrich_single.py` (internal). No external tools import from `phase_b`.            |               | ❌ pending |
| Q2   | Should we update historical TODO/initiative docs that reference `phase_b/`?                                                                            | A: Update all docs to reflect new paths / B: Only update living docs (CHANGELOG, architecture), leave historical initiative records as-is / C: Other | B — Historical initiative docs are records of what happened; updating them rewrites history. Update only living docs. |               | ❌ pending |
| Q3   | Should `phase_b/` directory be fully removed (including `__init__.py` and `__pycache__`) after merge?                                                  | A: Yes, remove entirely / B: Leave a deprecation marker                                                                                              | A — Dead code policy says "Delete, don't deprecate." No reason to keep an empty directory.                            |               | ❌ pending |
| Q4   | The CHANGELOG says `phase_b/` modules were "new modules" — should we add a separate CHANGELOG entry for the rename, or just update the existing entry? | A: Add new CHANGELOG entry under [Unreleased] noting the rename / B: Update existing entry in-place / C: Both                                        | A — The CHANGELOG records changes chronologically. This is a new change.                                              |               | ❌ pending |
