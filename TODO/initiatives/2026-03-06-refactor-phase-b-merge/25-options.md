# Options — Phase B Merge Refactor

**Initiative**: `2026-03-06-refactor-phase-b-merge`  
**Planning Confidence Score**: 90/100  
**Risk Level**: Low  
**Last Updated**: 2026-03-06

---

## Context

The `phase_b/` directory contains 4 modules (teaching_comments, vital_move, refutation_classifier, comment_assembler) that are functionally analyzers. The question is where they should live and how the refactor should be structured.

---

## Option Comparison Matrix

| Dimension                | OPT-1: Flat Merge into analyzers/                                           | OPT-2: Sub-package analyzers/teaching/                                | OPT-3: Rename phase_b → teaching_v2                     |
| ------------------------ | --------------------------------------------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------- |
| **Approach**             | Move all 4 files directly into `analyzers/` as siblings of existing modules | Create `analyzers/teaching/` sub-package with the 4 modules           | Rename `phase_b/` to `teaching_v2/` at same level       |
| **File count change**    | +4 files in analyzers/, -5 files in phase_b/                                | +5 files in analyzers/teaching/, -5 in phase_b/                       | 0 (rename only)                                         |
| **Import path**          | `from analyzers.teaching_comments import ...`                               | `from analyzers.teaching.teaching_comments import ...`                | `from teaching_v2.teaching_comments import ...`         |
| **Consistency**          | Matches existing analyzers pattern exactly                                  | Creates new sub-package precedent                                     | Still a separate package, still confusing               |
| **Complexity**           | Low                                                                         | Medium (new **init**.py, deeper imports)                              | Very low                                                |
| **SOLID**                | SRP: each module in its natural home                                        | SRP: grouped by concern but double-nested                             | SRP: no improvement (rename only)                       |
| **DRY**                  | No impact                                                                   | Potential for `analyzers/teaching/__init__.py` to re-export (DRY-ish) | No impact                                               |
| **KISS**                 | Simplest — flat list of analyzer modules                                    | More structure than needed                                            | Preserves confusing separate-package pattern            |
| **YAGNI**                | No unnecessary structure                                                    | Sub-package may be over-engineering for 4 files                       | No unnecessary structure but doesn't fix the root issue |
| **Migration effort**     | ~13 files touched, all import path changes                                  | ~13 files touched, longer import paths                                | ~13 files touched, cosmetic improvement only            |
| **Rollback**             | git revert                                                                  | git revert                                                            | git revert                                              |
| **Future extensibility** | Easy to add more analyzers                                                  | Good if many more teaching modules expected                           | Poor — still isolated from analyzers                    |
| **Risk**                 | Low — analyzers/ already works this way                                     | Low but introduces new structural precedent                           | Very low but doesn't solve the problem                  |

---

## Detailed Options

### OPT-1: Flat Merge into analyzers/ (Recommended)

**Approach**: Move all 4 `phase_b/` modules directly into `analyzers/` as top-level siblings of the 15 existing analyzer modules.

**Benefits**:

- Follows the existing pattern exactly (KISS)
- `analyzers/teaching_comments.py` is the natural successor location (V1 lived there)
- Import paths become consistent: all analyzer imports are `from analyzers.X import Y`
- No new directory structure or abstractions
- The orchestrator (`enrich_single.py`) imports from its own package

**Drawbacks**:

- `analyzers/` grows from 15 to 19 modules (still well under the 100-file limit)
- No explicit grouping of teaching-comment-related modules

**Risks**:

- R1: Import collision if `analyzers/teaching_comments.py` ever gets recreated by separate work → **Mitigated**: V1 was explicitly deleted, this IS the replacement
- R2: Merge conflicts if concurrent work touches `enrich_single.py` imports → **Mitigated**: Quick atomic change

**Migration implications**: All `from phase_b.X` → `from analyzers.X`. Clean, predictable.

**Rollback**: Single git revert restores all files.

---

### OPT-2: Sub-package analyzers/teaching/

**Approach**: Create `analyzers/teaching/` sub-package and move the 4 modules there, with an `__init__.py` that re-exports public APIs.

**Benefits**:

- Groups teaching-comment-related modules explicitly
- Clear boundary for future teaching-related additions
- Public API surface managed via `__init__.py`

**Drawbacks**:

- Over-engineering for 4 files (YAGNI violation)
- Creates structural precedent — should `validate_correct_move` get its own sub-package too?
- Longer import paths: `from analyzers.teaching.teaching_comments import ...`
- No existing sub-packages in `analyzers/` — this would be the first

**Risks**:

- R1: Sub-package precedent could lead to fragmentation of `analyzers/` → **No mitigation** — architectural creep
- R2: Double-nested import may confuse contributors

**Migration implications**: Slightly more complex imports. New `__init__.py` to maintain.

**Rollback**: git revert.

---

### OPT-3: Rename phase_b → teaching_v2

**Approach**: Simply rename the directory from `phase_b/` to `teaching_v2/` (or `teaching/`) at the same level.

**Benefits**:

- Minimal structural change
- Fixes the confusing "phase_b" name
- Very fast to implement

**Drawbacks**:

- Still a separate package from `analyzers/` — doesn't fix the architectural inconsistency
- Still requires import updates in the same files
- Doesn't match the pattern of all other analyzer modules
- "v2" in directory name is another temporal artifact (KISS violation)

**Risks**:

- R1: Future developers still wonder "why is teaching separate from analyzers?"
- R2: If a V3 comes, do we create `teaching_v3/`?

**Migration implications**: Same number of files touched as OPT-1, but doesn't solve the root problem.

**Rollback**: git revert.

---

## Recommendation

**OPT-1 (Flat Merge into analyzers/)** is the recommended option because:

1. It follows the existing pattern — every other analyzer is a flat sibling in `analyzers/`
2. `teaching_comments.py` literally used to live in `analyzers/` (V1) — this puts V2 back where V1 was
3. It's the simplest structural change (KISS) with no new abstractions (YAGNI)
4. Import paths become consistent across the entire enrichment lab
5. The analyzers/ directory at 19 modules is still very manageable

OPT-2 is over-engineering. OPT-3 doesn't fix the architectural issue.

---

## Go Domain Considerations

The phase_b modules implement Go/Baduk domain logic:

- **Vital move detection** — identifies the decisive tesuji (tactical move) in multi-move sequences. Uses branching factor and ownership delta from KataGo engine analysis.
- **Refutation classification** — classifies why wrong moves fail using Go-specific conditions: immediate capture, opponent escapes, opponent lives, capturing race (semeai) loss, opponent takes vital point, shape death alias (e.g., bent four in the corner), ko involvement.
- **Teaching comment assembly** — composes pedagogical comments using technique terminology (Japanese Go terms like uttegaeshi/snapback, shicho/ladder, ko).

**Domain question for governance**: Are these modules correctly scoped as "analyzers"? They analyze engine output and produce derived data — this is analysis. The alternative interpretation is that they are "generators" (they generate comments). However, the existing pattern (`generate_refutations.py`, `estimate_difficulty.py`) shows that generators already live in `analyzers/`. The `analyzers/` package is really "enrichment processors", and all 4 phase_b modules fit that definition.
