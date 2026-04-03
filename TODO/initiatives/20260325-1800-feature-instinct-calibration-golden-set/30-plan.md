# Plan — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Selected Option: OPT-1 (Two Standalone Scripts)
> Last Updated: 2026-03-25

---

## Architecture Overview

```
tools/
├── puzzle_search.py              # NEW: Search external-sources/ by pattern/property
├── puzzle_copy_rename.py         # NEW: Copy + rename SGFs to fixture dirs
├── core/
│   ├── sgf_parser.py             # EXISTING: SGF parsing (used by both tools)
│   ├── paths.py                  # EXISTING: Project root, path utils
│   └── tests/
│       ├── test_puzzle_search.py      # NEW: Tests for search tool
│       └── test_puzzle_copy_rename.py # NEW: Tests for copy tool
└── puzzle-enrichment-lab/
    └── tests/
        ├── test_instinct_calibration.py  # MODIFY: Point at instinct-calibration/, implement AC tests
        └── fixtures/
            ├── golden-calibration/        # EXISTING: Untouched (Q9:A)
            └── instinct-calibration/      # NEW: ~120 labeled SGFs
                ├── labels.json            # NEW: Multi-dimensional labels
                └── *.sgf                  # NEW: Standardized names
```

---

## Design Decisions

### D-1: Tool Placement at `tools/` Root

Both scripts live at `tools/` root following existing convention (`collections_align.py`, `update_sgf_collections.py`). Each is a standalone CLI with argparse and `--dry-run`. Uses `tools.core.sgf_parser` for SGF parsing, `tools.core.paths` for path resolution. No imports from `backend/`.

### D-2: labels.json Schema

Flat JSON dict keyed by standardized filename. Multi-dimensional labels per charter C-5:

```json
{
  "schema_version": "1.0",
  "description": "Instinct calibration golden set — multi-dimensional labels",
  "last_updated": "2026-03-25",
  "puzzles": {
    "cut_intermediate_001.sgf": {
      "instinct_primary": "cut",
      "instinct_labels": ["cut"],
      "technique_tag": "cutting",
      "objective": "life-and-death",
      "human_difficulty": "intermediate",
      "source": "kisvadim-goproblems/SAKATA EIO TESUJI",
      "original_filename": "kiri-s-01.sgf",
      "labeled_by": "expert",
      "notes": ""
    }
  }
}
```

**Must-hold MH-3**: `instinct_labels` is always an array (even for single instinct). For null category puzzles: `"instinct_primary": "null"`, `"instinct_labels": []`.

### D-3: Naming Convention

Per charter C-3: `{instinct}_{level}_{serial:03d}.sgf`

Examples:
- `cut_intermediate_001.sgf` (from kiri-s-01)
- `hane_advanced_005.sgf` (from Hane-s-05)
- `null_elementary_012.sgf` (from Kosumi-s-12)
- `push_low-dan_003.sgf` (from Lee Changho Fighting)

### D-4: Calibration Test Architecture

Extend `test_instinct_calibration.py` to point at `instinct-calibration/` and implement four AC test methods:

| Test | AC | Threshold | Logic |
|------|-----|-----------|-------|
| `test_instinct_macro_accuracy` | AC-1 | ≥70% | For each puzzle: run `classify_instinct()`, check if `primary ∈ human instinct_labels` |
| `test_per_instinct_accuracy` | AC-2 | ≥60% each | Group by `instinct_primary`, compute per-group accuracy |
| `test_high_tier_precision` | AC-3 | ≥85% | Filter classifier results where `tier == HIGH`, compute precision |
| `test_null_false_positive` | AC-4 | 0% | If `instinct_labels == []`, classifier must return no instinct or empty primary |

Tests import `classify_instinct` from `tools.puzzle-enrichment-lab.analyzers.instinct_classifier` — no `backend/` dependency.

### D-5: Source Selection Strategy

Phased sourcing per charter:

1. **Sakata Eio auto-map** (~107 puzzles): Filenames provide instinct mapping (kiri→cut, Hane→hane, Sagari→descent, Tobi→extend/verify, Kosumi/Tsuke/oki/Kake→null, Warikomi→verify)
2. **Lee Changho gap-fill** (~10-15 puzzles): Push instinct from "FIGHTING AND CAPTURING", technique diversity from chapter-level organization
3. **Cho Chikun supplemental** (~5-10 puzzles): Life-and-death with nakade/throw-in technique variety, difficulty anchoring

### D-6: Expert Labeling Workflow

1. Use `puzzle_search.py` to find candidate puzzles by filename/property
2. Use `puzzle_copy_rename.py` to copy SGFs with standardized names
3. For each puzzle, render ASCII board via `render_sgf_ascii()` 
4. Expert (domain agent or human) assigns: instinct_primary, instinct_labels[], technique_tag, objective, human_difficulty
5. Labels written to `labels.json` incrementally

---

## Data Model Impact

No production data model changes. All artifacts are test fixtures:
- `labels.json` — New file, consumed only by `test_instinct_calibration.py`
- `*.sgf` — Copies from external-sources, read-only test fixtures
- No database schema changes, no frontend changes

---

## Risks and Mitigations

| risk_id | risk | probability | impact | mitigation |
|---------|------|-------------|--------|------------|
| R-1 | Tobi files include knight's-move (keima), not axis-aligned extension | Medium | Medium | G-7: Expert verifies all 10 Tobi files individually |
| R-2 | Warikomi ambiguity (null vs cut) | Medium | Low | Expert labels each of 7 files individually |
| R-3 | Push instinct under-represented in sources | Medium | Medium | Lee Changho Fighting chapter as primary source, goproblems as supplement |
| R-4 | Classifier accuracy below 70% threshold | Medium | Low | Expected — calibration reveals gaps for next iteration. Doesn't block initiative. |
| R-5 | SGF files from external-sources have encoding issues | Low | Low | `tools.core.sgf_parser` handles common encoding variants |

---

## Constraints Satisfaction

| constraint_id | description | how_satisfied |
|---------------|-------------|---------------|
| C-1 | Tools isolation | Scripts use `tools.core.sgf_parser`, NOT `backend/` |
| C-2 | No external-sources modification | Tools only read; copies go to fixture dir |
| C-3 | Naming convention | `{instinct}_{level}_{serial:03d}.sgf` |
| C-4 | Minimum counts | ≥10 per instinct, ~120 total |
| C-5 | Multi-dimensional labels | instinct + technique_tag + objective per puzzle |
| C-6 | ASCII render for labeling | Uses `render_sgf_ascii()` from `analyzers/ascii_board.py` |
| C-7 | 19×19 only | All sources are 19×19 (verified in Sakata inventory) |

## Must-Hold Satisfaction

| MH-ID | constraint | how_satisfied |
|-------|-----------|---------------|
| MH-1 | `--dry-run` flags | Both tools include `--dry-run` that previews actions without writing |
| MH-2 | Tests in consistent location | Tools tests in `tools/core/tests/`; calibration tests in `tools/puzzle-enrichment-lab/tests/` |
| MH-3 | `instinct_labels[]` array | Schema design D-2 always uses array |
| MH-4 | Use `tools.core.sgf_parser` | Architecture decision D-1 |
| MH-5 | RC-2 addressed | ✅ Forward references removed from charter |

---

## Documentation Plan

| doc_id | action | file | why_updated |
|--------|--------|------|-------------|
| DOC-1 | Update | `tools/puzzle-enrichment-lab/AGENTS.md` | New fixture directory, calibration test changes |
| DOC-2 | Create | `tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration/README.md` | Describe golden set purpose, labels schema, naming convention |
| DOC-3 | Create | `docs/how-to/backend/enrichment-calibration.md` | New calibration workflow guide (file does not yet exist) |

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope and constraints
> - [25-options.md](./25-options.md) — Option analysis (OPT-1 selected)
> - [40-tasks.md](./40-tasks.md) — Task breakdown
> - [70-governance-decisions.md](./70-governance-decisions.md) — Governance decisions
