# Options — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Last Updated: 2026-03-25

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Planning Confidence Score | 85/100 |
| Risk Level | low |
| Research Invoked | No — score ≥70, risk low, sources verified, architecture clear |

Deductions: -10 (tool design has two viable approaches), -5 (technique tag coverage verification).

---

## RC-1 Resolution: Top 10 Technique Tags for AC-6

Verified against `config/tags.json` (28 tags total: 4 objective, 12 tesuji, 12 technique). Selected the 10 most tsumego-relevant tags with confirmed source coverage:

| rank | tag | id | category | source_coverage | min_puzzles |
|------|-----|----|----------|-----------------|-------------|
| T-1 | cutting | 70 | technique | Sakata kiri-s-* (12), Lee 3.2/5.5/6.2 | ≥12 |
| T-2 | eye-shape | 62 | technique | Lee 5.2, Cho Chikun L&D (all tiers) | ≥8 |
| T-3 | capture-race | 60 | technique | Lee 1/6.1 (dedicated chapters) | ≥6 |
| T-4 | nakade | 42 | tesuji | Cho Chikun L&D, Lee 5.4 | ≥6 |
| T-5 | throw-in | 38 | tesuji | Cho Chikun L&D, Lee 5.4 | ≥5 |
| T-6 | snapback | 30 | tesuji | Lee 2 (dedicated chapter) | ≥5 |
| T-7 | ladder | 34 | tesuji | Lee 1 (subset), goproblems supplement | ≥5 |
| T-8 | net | 36 | tesuji | Lee 4 (dedicated chapter) | ≥5 |
| T-9 | vital-point | 50 | tesuji | Sakata oki-s-* (12), Cho Chikun L&D | ≥8 |
| T-10 | sacrifice | 72 | technique | Lee 1/6.2, Cho Chikun L&D | ≥5 |

**Tag selection rationale**: These 10 tags span both the `tesuji` and `technique` categories from `config/tags.json`. They represent the most common first-move techniques in tsumego puzzles and are the tags most frequently assigned by the enrichment pipeline's technique detection stage. Each tag has confirmed source material from at least one of our primary collections, ensuring ≥5 puzzles per tag is achievable.

**Excluded tags with reasoning**:
- `endgame` (78), `joseki` (80), `fuseki` (82) — Not tsumego
- `corner` (74), `shape` (76) — Positional context, not first-move techniques
- `connection` (68), `escape` (66) — Available in Lee Changho but less common as primary technique in calibration puzzles
- `double-atari` (32), `clamp` (40), `connect-and-die` (44), `under-the-stones` (46), `liberty-shortage` (48), `dead-shapes` (64) — Important but lower frequency; can be added in follow-up expansion

---

## Design Space

The charter locks in: ~120 puzzles, new fixture directory, multi-dimensional labels (instinct + technique + objective), two permanent tools, expert labeling via ASCII render, and `labels.json` schema.

The key design decision is **tool architecture and labeling workflow**.

---

## OPT-1: Two Standalone Scripts (Root-Level Pattern)

### Approach

Two independent Python scripts at `tools/` root, following the existing pattern of `collections_align.py` and `update_sgf_collections.py`:

- `tools/puzzle_search.py` — Search `external-sources/` by filename pattern, SGF property, or comment text
- `tools/puzzle_copy_rename.py` — Copy SGFs to target fixture directory with standardized naming

Labels are managed in a flat `labels.json` keyed by filename. Expert labeling is a manual step (agent or human edits the JSON directly after reviewing ASCII renders).

### Architecture

```
tools/
├── puzzle_search.py        # Standalone CLI: search external-sources/
├── puzzle_copy_rename.py   # Standalone CLI: copy + rename SGFs
├── core/                   # Existing shared infra (sgf_parser, paths, etc.)
└── puzzle-enrichment-lab/
    └── tests/fixtures/
        └── instinct-calibration/
            ├── labels.json
            └── *.sgf
```

### labels.json Schema

```json
{
  "schema_version": "1.0",
  "description": "Instinct calibration golden set labels",
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

### Benefits

| benefit_id | description |
|------------|-------------|
| B-1 | Consistent with existing `tools/` root-level script pattern |
| B-2 | Zero new directory structure — just 2 files at root level |
| B-3 | Each tool independently testable with `--dry-run` |
| B-4 | Minimal maintenance — no package overhead |
| B-5 | Labels.json is simple to hand-edit or agent-edit |

### Drawbacks

| drawback_id | description |
|-------------|-------------|
| D-1 | Two separate CLIs — user must learn two interfaces |
| D-2 | No shared state between search results and copy operations (copy-paste paths) |
| D-3 | Label editing is fully manual (no validation at edit time) |
| D-4 | No `--verify` command to sanity-check labels against SGF files |

### Risk Assessment

| risk_id | risk | probability | impact | mitigation |
|---------|------|-------------|--------|------------|
| R-1 | Search output format incompatible with copy input | Low | Low | Document expected format, use consistent path output |
| R-2 | Manual label editing introduces typos | Medium | Medium | Test validates labels.json schema |

### Test Impact

- Add tests for `puzzle_search.py` in `tools/core/tests/` or alongside
- Add tests for `puzzle_copy_rename.py` similarly
- Extend `test_instinct_calibration.py` to validate labels.json schema

### Rollback

- Delete 2 script files and the fixture directory. Zero impact on production code.

### Architecture Compliance

- ✅ C-1: Scripts use `tools.core.sgf_parser`, NOT `backend/`
- ✅ C-2: Read-only access to `external-sources/`
- ✅ No new dependencies (uses stdlib `argparse`, `shutil`, `re`, `json`)

---

## OPT-2: Calibration Toolkit Package with Subcommands

### Approach

Dedicated package at `tools/calibration/` with a unified CLI entrypoint (`python -m tools.calibration`) and subcommands: `search`, `copy`, `validate`, `stats`.

Labels stored in a structured `labels.json` with built-in schema validation via a `validate` subcommand.

### Architecture

```
tools/
├── calibration/
│   ├── __init__.py
│   ├── __main__.py         # CLI entrypoint: python -m tools.calibration
│   ├── search.py           # Subcommand: search external-sources/
│   ├── copy_rename.py      # Subcommand: copy + rename SGFs
│   ├── validate.py         # Subcommand: validate labels.json against fixtures
│   ├── stats.py            # Subcommand: report coverage (instinct/technique/objective)
│   └── tests/
│       ├── test_search.py
│       ├── test_copy_rename.py
│       └── test_validate.py
├── core/                   # Existing shared infra
└── puzzle-enrichment-lab/
    └── tests/fixtures/
        └── instinct-calibration/
            ├── labels.json
            └── *.sgf
```

### CLI Interface

```bash
# Search for puzzles matching pattern
python -m tools.calibration search --source sakata --pattern "kiri-*"
python -m tools.calibration search --comment "hane" --board-size 19

# Copy and rename
python -m tools.calibration copy --input external-sources/kisvadim-goproblems/SAKATA\ EIO\ TESUJI/kiri-s-01.sgf \
  --target instinct-calibration --instinct cut --level intermediate --serial 1

# Validate labels against fixtures
python -m tools.calibration validate --fixture-dir instinct-calibration

# Coverage statistics
python -m tools.calibration stats --fixture-dir instinct-calibration
```

### labels.json Schema

```json
{
  "schema_version": "1.0",
  "description": "Instinct calibration golden set labels",
  "last_updated": "2026-03-25",
  "counts": {
    "total": 120,
    "by_instinct": {"cut": 15, "push": 12, "hane": 18, "descent": 14, "extend": 12, "null": 49},
    "by_technique": {"cutting": 15, "eye-shape": 10, "capture-race": 8, "nakade": 7, "throw-in": 6, "snapback": 6, "ladder": 5, "net": 5, "vital-point": 8, "sacrifice": 5}
  },
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

### Benefits

| benefit_id | description |
|------------|-------------|
| B-1 | Unified CLI interface — single entrypoint, discoverable subcommands |
| B-2 | Built-in `validate` subcommand catches label/fixture drift immediately |
| B-3 | `stats` subcommand reports coverage gaps (AC-6 progress tracking) |
| B-4 | Co-located tests — clear ownership boundary |
| B-5 | Extensible for future calibration sets (technique-calibration, objective-calibration) |
| B-6 | `counts` in labels.json header provides at-a-glance status |

### Drawbacks

| drawback_id | description |
|-------------|-------------|
| D-1 | New package directory breaks the root-level script pattern |
| D-2 | More files to create and maintain (7 vs 2) |
| D-3 | Heavier structure for what is essentially 2 core operations |
| D-4 | `validate` and `stats` could be one-off scripts, not permanent |

### Risk Assessment

| risk_id | risk | probability | impact | mitigation |
|---------|------|-------------|--------|------------|
| R-1 | Over-engineering for 120-puzzle scope | Medium | Low | Keep modules focused, defer extensibility until needed |
| R-2 | Package structure unclear for contributors | Low | Low | README.md with usage examples |

### Test Impact

- Tests co-located in `tools/calibration/tests/`
- Extend `test_instinct_calibration.py` unchanged

### Rollback

- Delete `tools/calibration/` directory and fixture directory. Zero impact on production code.

### Architecture Compliance

- ✅ C-1: Package uses `tools.core.sgf_parser`, NOT `backend/`
- ✅ C-2: Read-only access to `external-sources/`
- ✅ No new dependencies

---

## Comparison Matrix

| dimension | OPT-1: Standalone Scripts | OPT-2: Toolkit Package |
|-----------|--------------------------|------------------------|
| **Files created** | 2 (+ tests) | 7 (+ tests) |
| **Pattern consistency** | ✅ Matches existing root-level tools | ❌ New package pattern |
| **Unified CLI** | ❌ Two separate CLIs | ✅ Single entrypoint |
| **Built-in validation** | ❌ Manual | ✅ `validate` subcommand |
| **Coverage tracking** | ❌ Manual | ✅ `stats` subcommand |
| **Complexity** | Low | Medium |
| **YAGNI compliance** | ✅ Minimum needed | ⚠️ validate/stats may be premature |
| **Reusability** | ✅ Each tool reusable independently | ✅ Package reusable as whole |
| **Extensibility** | ⚠️ Add more root scripts over time | ✅ Add subcommands |
| **Maintenance** | Low (2 files) | Medium (7 files) |
| **Test isolation** | Tests in tools/core/tests/ | Tests co-located |
| **Rollback** | Delete 2 files | Delete 1 directory |

---

## Recommendation

**OPT-1 (Two Standalone Scripts)** is recommended.

**Rationale**:
1. **YAGNI**: The `validate` and `stats` subcommands in OPT-2 are achievable via the existing `test_instinct_calibration.py` test and simple `grep`/`jq` commands. Building them as permanent CLI subcommands is premature.
2. **Pattern consistency**: All existing tools at `tools/` root are standalone scripts (`collections_align.py`, `update_sgf_collections.py`, `consolidate_collections.py`). A package directory would be the first of its kind at this level.
3. **Scope proportionality**: For ~120 puzzles, 2 focused scripts are sufficient. The package overhead of OPT-2 (7 files, `__main__.py`, `__init__.py`) is disproportionate to the work.
4. **The charter explicitly says "two permanent tools"** — OPT-1 delivers exactly that.

**If validation becomes a repeating need** (e.g., for future technique-calibration or objective-calibration sets), a `tools/calibration/` package can be extracted from the standalone scripts at that time — a straightforward Level 2 refactor.

---

> **See also**:
> - [00-charter.md](./00-charter.md) — Feature scope and constraints
> - [10-clarifications.md](./10-clarifications.md) — Resolved design decisions
> - [70-governance-decisions.md](./70-governance-decisions.md) — Charter approval
