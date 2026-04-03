# Tasks — Instinct Calibration Golden Set

> Initiative: `20260325-1800-feature-instinct-calibration-golden-set`
> Selected Option: OPT-1 (Two Standalone Scripts)
> Last Updated: 2026-03-25

---

## Phase 1: Tool Development

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T1 | Create `puzzle_search.py` | `tools/puzzle_search.py` | — | [P] with T3 | not_started |
| T2 | Test `puzzle_search.py` | `tools/core/tests/test_puzzle_search.py` | T1 | — | not_started |
| T3 | Create `puzzle_copy_rename.py` | `tools/puzzle_copy_rename.py` | — | [P] with T1 | not_started |
| T4 | Test `puzzle_copy_rename.py` | `tools/core/tests/test_puzzle_copy_rename.py` | T3 | — | not_started |

### T1: Create `puzzle_search.py`

**Scope**: Standalone CLI script at `tools/` root.

**Interface**:
```bash
python tools/puzzle_search.py --source kisvadim-goproblems --pattern "kiri-*"
python tools/puzzle_search.py --comment "hane" --board-size 19
python tools/puzzle_search.py --property "C" --value "correct" --source sakata
python tools/puzzle_search.py --all --source "SAKATA EIO TESUJI"
```

**Behavior**:
- Search `external-sources/` directories for SGF files matching criteria
- Support: filename glob (`--pattern`), SGF comment text (`--comment`), SGF property match (`--property`/`--value`), board size filter (`--board-size`), source directory filter (`--source`)
- Output: One file path per line (absolute or relative to project root)
- Uses `tools.core.sgf_parser.parse_sgf()` for property/comment search
- Uses `tools.core.paths.get_project_root()` for path resolution
- Includes `--dry-run` (MH-1): same as normal mode (read-only tool)
- Includes `--count` for count-only output

### T2: Test `puzzle_search.py`

**Scope**: Unit tests in `tools/core/tests/test_puzzle_search.py`.

**Test cases**:
- Filename pattern matching (glob expansion)
- Comment text search (case-insensitive substring)
- Board size filter (19×19 only)
- Source directory filter
- Empty results handling
- Invalid source path handling

### T3: Create `puzzle_copy_rename.py`

**Scope**: Standalone CLI script at `tools/` root.

**Interface**:
```bash
python tools/puzzle_copy_rename.py \
  --input "external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/kiri-s-01.sgf" \
  --target "tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration" \
  --instinct cut --level intermediate --serial 1

python tools/puzzle_copy_rename.py --dry-run \
  --input "external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/kiri-s-*.sgf" \
  --target instinct-calibration --instinct cut --level intermediate --serial-start 1
```

**Behavior**:
- Copy SGF file(s) from source to target fixture directory
- Rename to standardized format: `{instinct}_{level}_{serial:03d}.sgf`
- Support glob input for batch copy
- `--serial-start` for batch serial numbering
- `--dry-run` (MH-1): print what would be copied without writing
- Validate: target directory exists, no overwrite without `--force`
- Uses `shutil.copy2()` for file copy
- Uses `tools.core.paths.get_project_root()` for path resolution

### T4: Test `puzzle_copy_rename.py`

**Scope**: Unit tests in `tools/core/tests/test_puzzle_copy_rename.py`.

**Test cases**:
- Single file copy + rename
- Batch copy with `--serial-start`
- `--dry-run` produces no file writes
- Overwrite prevention (no `--force`)
- Invalid input path handling
- Name format validation

---

## Phase 2: Fixture Setup

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T5 | Create fixture directory + labels.json scaffold | `tests/fixtures/instinct-calibration/labels.json`, `README.md` | — | [P] with T1/T3 | not_started |
| T6 | Copy Sakata Eio puzzles (~107 files) | `tests/fixtures/instinct-calibration/*.sgf` | T3, T5 | — | not_started |
| T7 | Copy Lee Changho gap-fill puzzles (~10-15 files) | `tests/fixtures/instinct-calibration/*.sgf` | T3, T5 | [P] with T6 | not_started |
| T8 | Copy Cho Chikun supplemental puzzles (~5-10 files) | `tests/fixtures/instinct-calibration/*.sgf` | T3, T5 | [P] with T6 | not_started |

### T5: Create fixture directory + labels.json scaffold

**Scope**: Create directory structure and empty labels schema.

**Files**:
- `tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration/labels.json` — Schema header with empty puzzles dict
- `tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration/README.md` — Purpose, naming convention, labeling instructions (DOC-2)

### T6: Copy Sakata Eio puzzles

**Scope**: Use `puzzle_copy_rename.py` to copy all ~107 Sakata Eio SGFs.

**Mapping**:
| Source pattern | Instinct | Count |
|---------------|----------|-------|
| kiri-s-*.sgf | cut | 12 |
| Hane-s-*.sgf | hane | 13 |
| Sagari-s-*.sgf | descent | 12 |
| Tobi-s-*.sgf | extend (pending G-7 verification) | 10 |
| Kosumi-s-*.sgf | null | 19 |
| Tsuke-s-*.sgf | null | 17 |
| oki-s-*.sgf | null | 12 |
| Kake-s-*.sgf | null | 8 |
| Warikomi-s-*.sgf | null (pending verification) | 7 |

Serial numbering: per-instinct starting at 001.

### T7: Copy Lee Changho gap-fill puzzles

**Scope**: Use `puzzle_search.py` to find, then `puzzle_copy_rename.py` to copy ~10-15 puzzles from Lee Changho chapters.

**Priority fills**:
- Push instinct: "FIGHTING AND CAPTURING" chapter (~5-8 puzzles)
- Capture-race technique: "6.1 CAPTURING RACE" chapter (~3-5 puzzles)
- Snapback technique: "SNAPBACK AND SHORTAGE OF LIBERTIES" chapter (~2-3 puzzles)

### T8: Copy Cho Chikun supplemental puzzles

**Scope**: Copy ~5-10 puzzles from Cho Chikun L&D to fill technique tag gaps.

**Priority fills**:
- Nakade technique: Advanced L&D with inside-group kills
- Throw-in technique: L&D with liberty reduction
- Difficulty anchoring: Elementary/Intermediate/Advanced spread

---

## Phase 3: Expert Labeling

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T9 | Auto-label Sakata instinct from filenames | `labels.json` | T6 | — | not_started |
| T10 | Expert verify Tobi files (G-7) | `labels.json` | T9 | [P] with T11 | not_started |
| T11 | Expert verify Warikomi files | `labels.json` | T9 | [P] with T10 | not_started |
| T12 | Expert label technique_tag + objective for Sakata | `labels.json` | T9 | — | not_started |
| T13 | Expert label all dimensions for Lee/Cho puzzles | `labels.json` | T7, T8 | — | not_started |
| T14 | Validate coverage: ≥120 total, ≥10/instinct, ≥5/technique | `labels.json` | T12, T13 | — | not_started |

### T9: Auto-label Sakata instinct from filenames

**Scope**: Populate `labels.json` with instinct_primary and instinct_labels based on Sakata filename→instinct mapping from charter inventory table. Set `labeled_by: "auto-filename"` for these entries.

### T10: Expert verify Tobi files (G-7)

**Scope**: For each of 10 Tobi-s-* files:
1. Render ASCII board via `render_sgf_ascii()`
2. Expert determines: is the correct first move an axis-aligned one-point jump (extend) or a knight's move/other (null)?
3. Update labels.json: axis-aligned → `instinct_primary: "extend"`, knight's move → `instinct_primary: "null"`

### T11: Expert verify Warikomi files

**Scope**: For each of 7 Warikomi-s-* files:
1. Render ASCII board
2. Expert determines: is the correct first move a splitting cut (instinct: cut) or a wedge/null?
3. Update labels.json accordingly

### T12: Expert label technique_tag + objective for Sakata

**Scope**: For each Sakata puzzle, expert assigns:
- `technique_tag`: one of the top 10 tags from RC-1 analysis
- `objective`: one of `life-and-death`, `living`, `ko`, `seki`
- `human_difficulty`: novice through expert (9-level system)
- Update `labeled_by: "expert"` after review

### T13: Expert label all dimensions for Lee/Cho puzzles

**Scope**: For each Lee Changho and Cho Chikun puzzle:
1. Render ASCII board
2. Expert assigns: instinct_primary, instinct_labels[], technique_tag, objective, human_difficulty
3. Populate labels.json entries

### T14: Validate coverage thresholds

**Scope**: Verify labels.json meets acceptance criteria:
- AC-5: ≥120 puzzles with complete labels
- C-4: ≥10 per instinct category (6 categories)
- AC-6: ≥5 per technique tag (10 tags from RC-1)
- All entries have complete fields (no empty instinct_primary, no missing technique_tag)

If gaps found, return to T7/T8 for supplemental sourcing.

---

## Phase 4: Calibration Tests

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T15 | Update test_instinct_calibration.py for instinct-calibration/ | `test_instinct_calibration.py` | T14 | — | not_started |
| T16 | Implement AC-1: macro instinct accuracy test | `test_instinct_calibration.py` | T15 | [P] with T17, T18, T19 | not_started |
| T17 | Implement AC-2: per-instinct accuracy test | `test_instinct_calibration.py` | T15 | [P] with T16, T18, T19 | not_started |
| T18 | Implement AC-3: HIGH-tier precision test | `test_instinct_calibration.py` | T15 | [P] with T16, T17, T19 | not_started |
| T19 | Implement AC-4: null false-positive test | `test_instinct_calibration.py` | T15 | [P] with T16, T17, T18 | not_started |
| T20 | Run calibration and report results | — | T16-T19 | — | not_started |

### T15: Update test_instinct_calibration.py

**Scope**: Add new fixture path constant and label loader:
```python
INSTINCT_DIR = Path(__file__).parent / "fixtures" / "instinct-calibration"
INSTINCT_LABELS_FILE = INSTINCT_DIR / "labels.json"
```

Load labels from new `"puzzles"` dict format (keyed by filename). Keep existing `golden_labels` fixture untouched.

### T16: Implement AC-1 macro accuracy

**Scope**: `test_instinct_macro_accuracy`:
1. For each puzzle in labels.json with non-empty `instinct_labels`
2. Parse SGF, extract position + correct move
3. Run `classify_instinct(position, correct_move)`
4. Check if classifier's primary result `∈ human instinct_labels`
5. Assert accuracy ≥ 0.70

### T17: Implement AC-2 per-instinct accuracy

**Scope**: `test_per_instinct_accuracy`:
1. Group puzzles by `instinct_primary`
2. For each group (cut, push, hane, descent, extend), compute accuracy
3. Assert each ≥ 0.60

### T18: Implement AC-3 HIGH-tier precision

**Scope**: `test_high_tier_precision`:
1. For all puzzles, run classifier
2. Filter results where `tier == "HIGH"`
3. Compute precision (correct / total HIGH-tier)
4. Assert ≥ 0.85

### T19: Implement AC-4 null false-positive

**Scope**: `test_null_false_positive`:
1. For puzzles where `instinct_labels == []` (null category)
2. Run classifier
3. Assert classifier returns empty results or no primary instinct
4. Assert FP rate == 0%

### T20: Run calibration

**Scope**: Execute full calibration test suite, capture results, document in initiative.

---

## Phase 5: Documentation

| task_id | title | files | depends_on | parallel | status |
|---------|-------|-------|------------|----------|--------|
| T21 | Update AGENTS.md for puzzle-enrichment-lab | `tools/puzzle-enrichment-lab/AGENTS.md` | T20 | [P] with T22 | not_started |
| T22 | Create fixture README.md (DOC-2) | `tests/fixtures/instinct-calibration/README.md` | T14 | [P] with T21 | not_started |
| T23 | Update/create enrichment calibration guide (DOC-3) | `docs/how-to/backend/enrichment-calibration.md` | T20 | — | not_started |

### T21: Update AGENTS.md

**Scope**: Add `instinct-calibration/` fixture directory description, calibration test section, reference to labels.json schema.

### T22: Create fixture README.md

**Scope**: Document purpose, naming convention, labels schema, source provenance, how to add new puzzles.

### T23: Create enrichment calibration guide

**Scope**: How-to guide for running calibration, interpreting results, adding puzzles. Check if `docs/how-to/backend/enrichment-calibration.md` exists; create or update.

---

## Task Dependency Graph

```
T1 ──→ T2
  ↘        ↘
T3 ──→ T4   T6 ──→ T9 ──→ T10 ──→ T12 ──→ T14 ──→ T15 ──→ T16 ┐
  ↘          ↗       ↗      ↘               ↗                T17 │──→ T20 ──→ T21
T5 ─────────┘   T7 ──────→ T13 ────────────┘                T18 │         ↗
                T8 ──────→ T13                               T19 ┘    T22─┘
                                                                      T23
```

**Parallel markers**: T1∥T3∥T5, T6∥T7∥T8, T10∥T11, T16∥T17∥T18∥T19, T21∥T22

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 23 |
| New files | ~130 (2 tools + 2 tool tests + ~120 SGFs + labels.json + README + calibration tests + docs) |
| Modified files | 1 (test_instinct_calibration.py) |
| Production code changes | 0 |
| New dependencies | 0 |

---

> **See also**:
> - [30-plan.md](./30-plan.md) — Architecture and design decisions
> - [20-analysis.md](./20-analysis.md) — Consistency and coverage analysis
> - [25-options.md](./25-options.md) — Option selection rationale
