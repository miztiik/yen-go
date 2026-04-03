# Architecture: SGF Directory Comparison Tool

**Last Updated:** 2026-03-25

---

## Purpose

A reusable tool for comparing two directories of SGF tsumego puzzle files. Identifies duplicates, matches puzzles by board position, classifies the degree of similarity on a granular 0–7 numeric scale, and produces structured JSONL + human-readable Markdown reports.

**Primary use case:** Determine whether two independently sourced collections of the same tsumego set (e.g., Xuan Xuan Qi Jing from two different digitizers) contain the same puzzles, and if not, precisely what differs.

**Secondary use case:** Cross-collection deduplication — find puzzles in one collection that also appear in another, even if filenames differ.

> **See also:**
>
> - [How-To: Compare SGF Directories](../../how-to/backend/cli-reference.md) — CLI usage
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — AB/AW/PL/SZ reference
> - [Tool Development Standards](../../how-to/backend/tool-development-standards.md) — Scaffolding conventions
> - [Local README](../../../tools/puzzle-manager-scripts/README-compare-dirs.md) — Quick-start & CLI flags

---

## Design Decisions

### D1: Two-File Architecture (Library + CLI Script)

**Decision:** Split the tool into two files:

- `tools/core/sgf_compare.py` — Reusable comparison library (position hashing, tree comparison, match classification)
- `tools/puzzle-manager-scripts/compare_dirs.py` — CLI script (directory walking, output formatting, checkpointing)

**Rationale:**

- **SRP (Single Responsibility Principle):** The comparison logic (hashing, tree diffing, match levels) is independent of how directories are walked or output is formatted. The library is testable in isolation — pass two `SgfTree` objects, get a `MatchLevel`.
- **Reusability:** Other tools or scripts may want to compare individual SGF files without directory scaffolding. The library exposes pure functions that work on parsed trees.
- **Existing pattern:** This mirrors the project convention where `tools/core/validation.py` provides reusable logic and scripts in `tools/puzzle-manager-scripts/` consume it.
- **Not three+ files:** There is no need for a separate output formatter, config loader, or abstract strategy. YAGNI.

**Why not a single file?** Mixing CLI `argparse`, directory I/O, checkpointing, and comparison logic in one file violates SRP and makes the comparison functions untestable without filesystem fixtures.

**Why not inside `backend/`?** Architecture boundary: `tools/core/` is self-contained and must NOT import from `backend/puzzle_manager/`. This tool is a standalone utility.

---

### D2: Board Position as Primary Matching Key

**Decision:** Match puzzles by their initial board position: `(board_size, black_stone_set, white_stone_set)`.

**Rationale (confirmed by Tsumego Domain Expert):**

- In tsumego, the initial stone configuration *is* the puzzle identity. Two files with identical stone placements on the same board size represent the same problem.
- Classical tsumego collections never reuse a position for a different puzzle within the same collection.
- Across different collections, position overlap indicates derivative or borrowed problems.

**How it works:** Parse `SZ[]` (board size), `AB[]` (black stones), and `AW[]` (white stones) into sorted, deduplicated sets. These are parsed from the SGF tree — NOT compared as raw strings (SGF does not mandate coordinate ordering within `AB[aa][bb]` vs `AB[bb][aa]`, and stones may be split across multiple `AB[]` properties).

**Edge cases handled:**

- Different `AB`/`AW` encoding order: Parsed to `frozenset`, order-independent.
- Multiple `AB[]`/`AW[]` properties: Accumulated into a single set per color.
- Empty stone sets: File is flagged as `"error": "no_stones"` and skipped.

---

### D3: No Rotation or Reflection Normalization

**Decision:** Rotations and reflections are NOT handled. Each orientation is treated as a different puzzle.

**Rationale:**

- Within the same collection (the primary use case), all files maintain their original orientation. The same problem number from two sources of the same compilation will have the same orientation.
- Rotation normalization requires choosing a canonical orientation (e.g., "most stones in top-right quadrant"), which is a non-trivial heuristic with edge cases.
- The user explicitly decided this is out of scope: "each rotation makes it a different kind of a problem."

**Future extension point:** The library could accept an optional `normalize_orientation` flag in the future, but implementing the normalization heuristic is deferred.

---

### D4: Board Size Is Part of Puzzle Identity

**Decision:** Different board sizes = different puzzles. A 19×19 position and a 13×13 crop of the same position are treated as distinct.

**Rationale (confirmed by Tsumego Domain Expert):**

- SGF coordinates are board-size-relative. `AB[aa]` means `(1,1)` regardless of board size, but the semantic meaning changes — corner vs center depends on the board.
- Normalizing board sizes would require a "relevant area" detector (non-trivial Go engine feature involving liberty analysis). This is massive scope creep.
- In practice, collections are internally consistent — a collection uses one board size throughout. Cross-collection comparison between a 19×19 source and a 9×9 crop is a deduplication problem, not a comparison problem.
- `SZ` is already part of the hash in the backend's `canonical_position_hash()` algorithm.

---

### D5: PL[] (Player to Move) — No Inference, Dual-Hash Strategy

**Decision:** When `PL[]` is present in the SGF, include it in the hash. When `PL[]` is absent, compute only a position hash (without PL). **Never infer PL from the solution tree.**

**Rationale:**

- The user's principle: "I want to look at actual facts, not do inference. If inference produces noise there is no way to validate it."
- Missing `PL[]` is common in raw historical SGF collections (e.g., eidogo Xuanlan has zero PL properties). Skipping these entirely would make whole collections non-comparable.
- Inferring PL from the first solution move works ~99.5% of the time, but introduces code paths, edge cases (empty solution trees, wrong-answer branches listed first), and silent failures — a design smell for a comparison tool.
- The dual-hash approach avoids inference entirely while still enabling matching.

**How it works:**

| Hash              | Formula                                                    | When Computed                          |
| ----------------- | ---------------------------------------------------------- | -------------------------------------- |
| **Full hash**     | `SHA256("SZ{n}:B[sorted_ab]:W[sorted_aw]:PL[X]")[:16]`   | Only when `PL[]` is explicitly present |
| **Position hash** | `SHA256("SZ{n}:B[sorted_ab]:W[sorted_aw]")[:16]`          | Always computed for every file         |

**Matching logic:**

1. Both files have PL → compare full hashes. If equal → high-confidence match (Level 3+). If full hashes differ but position hashes match → same stones, different PL → `pl_conflict` flag.
2. One or both files lack PL → compare position hashes only → lower-confidence match (Level 2 max), flagged as `pl_absent`.

**Why not default to Black?** SGF convention defaults to Black when PL is absent, but this creates false positives. Two files with the same position but genuinely different players to move would appear as "matching" when they represent fundamentally different puzzles. The Tsumego Expert confirmed: "Black-to-live vs White-to-kill is a fundamentally different puzzle — different difficulty, different solution tree, different technique."

**Why not skip files missing PL entirely?** The user initially considered this ("mark as not comparable"), but the experts showed that entire historical collections lack PL. The dual-hash approach handles them without inference.

**Same position, different explicit PL:** This is flagged as `pl_conflict` at Level 2. The Tsumego Expert confirmed this IS a genuinely different puzzle — the Xuan Xuan Qi Jing has explicit examples of paired problems (same position, both sides to play).

---

### D6: SHA-256 Position Hashing (Replicating Backend Algorithm)

**Decision:** Use SHA-256 truncated to 16 hex characters, matching the backend's `canonical_position_hash()` algorithm.

**Rationale:**

- The backend pipeline already uses this exact formula for deduplication in `content_db.py`. Replicating the algorithm (not importing it — architecture boundary) ensures cross-system consistency.
- Python's `hash(frozenset(...))` is session-dependent (`PYTHONHASHSEED`), making it non-deterministic across runs. SHA-256 is deterministic.
- 16 hex chars = 64 bits = astronomically low collision probability for puzzle-scale data.

**Algorithm:**

```python
b_sorted = ",".join(sorted(p.to_sgf() for p in tree.black_stones))
w_sorted = ",".join(sorted(p.to_sgf() for p in tree.white_stones))

# Full hash (when PL present):
canonical = f"SZ{tree.board_size}:B[{b_sorted}]:W[{w_sorted}]:PL[{tree.player_to_move}]"
full_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]

# Position hash (always):
pos_canonical = f"SZ{tree.board_size}:B[{b_sorted}]:W[{w_sorted}]"
position_hash = hashlib.sha256(pos_canonical.encode()).hexdigest()[:16]
```

**Collision mitigation:** After a hash match, the tool verifies that the actual stone sets are equal before classifying at Level 2+. This guards against the (extremely unlikely) 64-bit hash collision.

---

### D7: Match Level System — Pure Numeric 0–7

**Decision:** Use a purely numeric scale from 0 (no match) to 7 (byte-identical). No letter suffixes (an earlier proposal used "3S" and "3D" — rejected by the user for simplicity).

**Rationale:**

- The user explicitly requested: "Can we not have it as numeric only instead of having alphabets?"
- A linear numeric scale is sortable, filterable, and unambiguous. Higher number = closer match.
- The scale is fine-grained enough to distinguish every meaningful comparison dimension without being so granular as to create confusion.

#### Level Definitions

| Level | Name              | Definition | Detection Method |
| ----- | ----------------- | ---------- | ---------------- |
| **7** | Byte-Identical | The raw SGF file content is exactly the same, byte-for-byte. | `raw_sgf_a == raw_sgf_b` |
| **6** | Tree-Identical | Board position matches AND every move sequence in the solution tree is identical. Only non-tree content differs (SGF header properties like `GM`, `FF`, `GN`, YenGo custom properties, comments, whitespace). | Extract all root-to-leaf move paths as sets; compare sorted path sets. |
| **5** | Superset | Board position matches AND the correct main line matches AND the target file's solution tree contains every path from the source file plus additional paths. The target is an enriched version of the source. | `source_path_set ⊆ target_path_set` (Python set containment). |
| **4** | Divergent | Board position matches AND the correct main line matches, BUT the trees have incompatible variation branches — neither is a subset of the other. Two sources independently annotated wrong-answer branches differently. | Correct lines match but `source_paths ⊄ target_paths` AND `target_paths ⊄ source_paths`. |
| **3** | Solution-Differs | Board position matches, but the first correct move differs between the two files. This indicates either a data error in one source or a position with miai (two equally correct first moves). | Compare first child node of solution tree. |
| **2** | Position-Only | Position hash matches but either PL is absent in one/both files (`pl_absent`) or PL values conflict (`pl_conflict`). Lower confidence because player-to-move cannot be verified. | Position hash hit, but full hash doesn't match or cannot be computed. |
| **1** | Filename-Mismatch | The filename exists in both directories but the position hash differs. This catches renumbering errors, file corruption, or different editions of the same book. | Filename correlation check after hash-based matching. |
| **0** | Unmatched | The file exists in only one directory and no match was found by any method. | No hash hit in other directory, no filename correlation. |

#### Why This Scale (Design Rationale per Level)

**Level 7 vs 6:** Level 7 is a fast `O(1)` string comparison — if bytes match, everything matches. Level 6 is needed because two files can represent the exact same puzzle with different SGF formatting (different header properties, different whitespace, different property ordering). Level 6 confirms the *puzzle content* is identical even when the *file encoding* differs.

**Level 6 vs 5:** Level 6 means the entire solution tree is the same. Level 5 means the target has *more* content (additional refutation branches, more wrong-move responses) but everything in the source also exists in the target. This is the "enriched vs. original" tier — it tells you the target is strictly richer. Level 5 is safe for auto-merge (take the richer tree).

**Level 5 vs 4:** Level 5 is a strict subset/superset relationship (one tree contains the other). Level 4 means both trees share the correct main line but *diverge* on wrong-answer branches — they disagree on how wrong moves play out. Level 4 requires human review; Level 5 does not.

**Level 4 vs 3:** Level 4 still agrees on the correct first move and correct main line — the disagreement is only in how opponent's wrong moves are handled. Level 3 means the files disagree on the *correct answer itself* — either a data error or a genuine miai situation. This is a data quality red flag.

**Level 3 vs 2:** Level 3 has confirmed PL agreement (same player to move) but solutions differ. Level 2 cannot even confirm PL — the match is based solely on stone positions. Level 2 needs the most cautious interpretation.

**Level 2 vs 1:** Level 2 is a genuine position match (same stones). Level 1 is only a filename correlation — `prob0047.sgf` exists in both directories but the actual puzzle content is completely different. This is a diagnostic curiosity, not a real match.

**Level 1 vs 0:** Level 1 at least has a filename correlate to investigate. Level 0 means the file is truly orphaned — no match by content or name.

#### What "Tree Isomorphism" Means (Simplified)

The term "tree isomorphism" from the initial design phase was replaced with a simpler concrete algorithm. For Level 6 comparison:

1. Walk the solution tree from root to every leaf node.
2. At each node, record the move as `"{color}[{coord}]"` (e.g., `"B[cd]"`).
3. Concatenate each root-to-leaf path as a string: `"B[cd]→W[de]→B[ef]"`.
4. Collect all such path strings into a Python `set`.
5. Sort and compare the two sets.

This is ~10 lines of code. No graph theory library is needed. The sorting of child tuples ensures that variation ordering in the SGF file (which is not semantically meaningful) does not affect comparison.

#### The `is_correct` Default Caveat

`SgfNode.is_correct` defaults to `True` when no correctness markers or comment signals are found. This means:

- When **both** trees lack correctness markers entirely, **every branch appears "correct."**
- In this scenario, Level 5 ("correct line match, target is superset") degenerates to Level 6 ("full tree match"), because there are no "wrong" branches to distinguish.
- The tool documents this in the summary report when detected.

---

### D8: Content-Based Matching, Not Filename-Based

**Decision:** The primary matching method is content-based (position hash), not filename-based. Filename correlation is a secondary diagnostic check (Level 1).

**Rationale:**

- The user stated: "Even if the filename is different, the hash will find it. Even if the filename is the same, content might be different. Ultimately we need to check with the contents."
- A file named `prob0047.sgf` in directory A might match `prob0052.sgf` in directory B (if one collection renumbered problems). Content-based matching catches this.
- Conversely, `prob0047.sgf` might exist in both directories with completely different puzzles (different editions of a book). Filename matching would give a false positive.

**Algorithm:**

| Step | Action                                                      | Data Structure                                  |
| ---- | ----------------------------------------------------------- | ----------------------------------------------- |
| 1    | Glob `source_dir/**/*.sgf`                                  | `list[Path]`                                    |
| 2    | Parse each source file → compute both hashes                | `dict[position_hash → list[(path, tree, raw)]]` |
| 3    | Glob `target_dir/**/*.sgf`                                  | `list[Path]`                                    |
| 4    | Parse each target file → compute both hashes                | Same structure                                  |
| 5    | For each source entry, look up position hash in target index | O(1) dict lookup                                |
| 6    | If position hash matches, attempt full hash match           | Classify Level 2–7                              |
| 7    | If no content match, check filename correlation             | Level 1 or Level 0                              |

**Time complexity:** O(N + M) where N = source files, M = target files. Hash-map join, not O(N × M) nested loop.

**Duplicate positions in same directory:** The tool uses `dict[hash → list]` (not `dict[hash → single]`), so it reports 1:N and N:M matches when multiple files share the same position.

---

### D9: First Correct Move as Fast Discriminator

**Decision:** After establishing a position match (Level 2+), compare the first correct move before performing full tree comparison.

**Rationale (from Tsumego Expert):** In classical tsumego, the first move is almost always the "key move" (急所). Two versions of the same problem that disagree on the first move indicates a serious discrepancy — either a data error or a miai situation.

**How it works:** Extract the first child node from the solution tree root. Compare `(color, coordinate)`. If they differ → Level 3 (Solution-Differs). If they match → proceed to full tree comparison (Level 4–7).

**Cost:** O(1) — read a single node. Avoids expensive tree traversal when the simplest comparison already shows disagreement.

---

### D10: Comment Comparison as Sub-Dimension (Not a Match Level)

**Decision:** Comments are NOT a separate match level. They are a boolean flag (`comments_differ`) in the output record.

**Rationale (from Tsumego Expert):** Comments in tsumego SGF serve three distinct functions:

| Comment Type          | Example                                       | What It Means                                  |
| --------------------- | --------------------------------------------- | ---------------------------------------------- |
| Correctness label | `C[Correct]`, `C[Wrong]` | Functional — changes puzzle UX |
| Teaching explanation | `C[This is a snapback]` | Pedagogical — adds value |
| Metadata/attribution | `C[From Xuan Xuan Qi Jing, Problem 47]` | Provenance — irrelevant to puzzle identity |

Correctness labels are already captured by the tree comparison (they map to `is_correct` during parsing). Teaching text and metadata are enrichment — they don't change the puzzle identity. Including them as a match tier would create noise.

**Output:** The JSONL record includes `comments_differ: true/false` and `markers_differ: true/false` as informational flags, but these do NOT affect the numeric match level.

---

### D11: Output — Timestamped Run Directories

**Decision:** Every run creates a unique timestamped directory under `tools/puzzle-manager-scripts/output/`.

**Rationale:**

- The user wants: "Every output is unique — date/timestamp prefix in a directory for every run."
- Timestamped directories prevent overwriting previous results. Old comparisons are preserved for reference.
- This follows the `tools/*/output/` convention which is `.gitignore`-protected (per Git Safety Rules, tools output directories are "Protected Directories" for runtime data).

**Structure:**

```text
tools/puzzle-manager-scripts/output/
  compare-20260325-143022/
    comparison.jsonl      # One JSONL record per source file
    summary.md            # Aggregate statistics + notable findings
    .checkpoint.json      # Resume state (deleted on completion)
    run.log               # Structured event log
```

**Why under `tools/puzzle-manager-scripts/output/`?** CR-Beta identified that placing output at the project root (e.g., `_compare_output/`) risks accidental deletion by git operations. The `tools/*/output/` location is protected by existing `.gitignore` patterns and the project's git safety rules.

---

### D12: JSONL Output Schema

**Decision:** One JSONL record per source file, containing all comparison dimensions.

**Rationale:**

- JSONL is streaming-friendly — can be processed with `jq`, loaded into pandas, or parsed line-by-line.
- One record per source file means every source file appears exactly once in the output.
- All dimensions (match level, hashes, depths, node counts, flags) are in a single record for easy filtering.

**Schema:**

```json
{
  "source_file": "prob0047.sgf",
  "target_file": "prob0047.sgf",
  "match_level": 7,
  "position_hash": "a1b2c3d4e5f67890",
  "full_hash": "b2c3d4e5f6789012",
  "board_size": 19,
  "player_to_move_source": "B",
  "player_to_move_target": "B",
  "pl_status": "confirmed",
  "first_move_match": true,
  "correct_line_match": true,
  "source_nodes": 7,
  "target_nodes": 7,
  "source_depth": 5,
  "target_depth": 5,
  "comments_differ": false,
  "markers_differ": false,
  "detail": "Byte-identical"
}
```

**Field reference:**

| Field                    | Type            | Description                                                                                      |
| ------------------------ | --------------- | ------------------------------------------------------------------------------------------------ |
| `source_file`            | string          | Relative path of source SGF file                                                                 |
| `target_file` | string or null | Relative path of matched target file, or `null` if unmatched |
| `match_level` | int (0–7) | Numeric match level per the scale defined in D7 |
| `position_hash` | string | 16-char hex SHA-256 of position (without PL) |
| `full_hash` | string or null | 16-char hex SHA-256 of position + PL, or `null` if PL absent |
| `board_size` | int | Board size from `SZ[]` property |
| `player_to_move_source` | string or null | `"B"` or `"W"` from source PL, or `null` if absent |
| `player_to_move_target` | string or null | `"B"` or `"W"` from target PL, or `null` if absent |
| `pl_status` | string | `"confirmed"` (both PL match), `"absent_source"`, `"absent_target"`, `"absent_both"`, `"conflict"` |
| `first_move_match` | bool or null | Whether first correct move matches, `null` if one/both have no solution |
| `correct_line_match` | bool or null | Whether correct main line matches, `null` if not applicable |
| `source_nodes` | int | Total nodes in source solution tree |
| `target_nodes` | int or null | Total nodes in target solution tree, `null` if unmatched |
| `source_depth` | int | Max depth of source solution tree |
| `target_depth` | int or null | Max depth of target solution tree, `null` if unmatched |
| `comments_differ` | bool | Whether any move-level comments differ |
| `markers_differ` | bool | Whether correctness markers (TE/BM/WV) differ |
| `detail` | string | Human-readable explanation of the match |
| `error` | string or null | Error message if file failed to parse, `null` otherwise |

**Unmatched file record (Level 0):**

```json
{
  "source_file": "prob0348.sgf",
  "target_file": null,
  "match_level": 0,
  "position_hash": "f1e2d3c4b5a69870",
  "full_hash": "a1b2c3d4e5f67890",
  "board_size": 19,
  "player_to_move_source": "B",
  "player_to_move_target": null,
  "pl_status": "absent_target",
  "first_move_match": null,
  "correct_line_match": null,
  "source_nodes": 8,
  "target_nodes": null,
  "source_depth": 3,
  "target_depth": null,
  "comments_differ": false,
  "markers_differ": false,
  "detail": "No position match in target directory."
}
```

**Parse-error record:**

```json
{
  "source_file": "corrupt.sgf",
  "target_file": null,
  "match_level": 0,
  "position_hash": null,
  "full_hash": null,
  "board_size": null,
  "player_to_move_source": null,
  "player_to_move_target": null,
  "pl_status": null,
  "first_move_match": null,
  "correct_line_match": null,
  "source_nodes": null,
  "target_nodes": null,
  "source_depth": null,
  "target_depth": null,
  "comments_differ": false,
  "markers_differ": false,
  "detail": "Parse error",
  "error": "SGF must start with '('"
}
```

---

### D13: Markdown Summary Report

**Decision:** In addition to JSONL, generate a human-readable Markdown summary.

**Structure:**

```markdown
## SGF Directory Comparison Report
- **Run:** 2026-03-25 14:30:22 UTC
- **Source:** external-sources/Xuan Xuan Qi Jing/ (347 files)
- **Target:** external-sources/kisvadim-goproblems/TSUMEGO CLASSIC - XUAN XUAN QI JING/ (347 files)

### Match Distribution
| Level | Name | Count | % |
|-------|------|------:|--:|
| 7 | Byte-Identical | 347 | 100.0% |
| 6 | Tree-Identical | 0 | 0.0% |
| 5 | Superset | 0 | 0.0% |
| 4 | Divergent | 0 | 0.0% |
| 3 | Solution-Differs | 0 | 0.0% |
| 2 | Position-Only | 0 | 0.0% |
| 1 | Filename-Mismatch | 0 | 0.0% |
| 0 | Unmatched | 0 | 0.0% |

### Statistics
- Source files: 347
- Target files: 347
- Parse errors (source): 0
- Parse errors (target): 0
- PL-absent files: 0
- PL-conflict matches: 0

### Notable Findings
- (any Level 3 or below matches listed here with details)
```

---

### D14: Checkpointing for Large Collections

**Decision:** Use the existing `tools.core.checkpoint.ToolCheckpoint` infrastructure for resume support.

**Rationale:**

- For small collections (< 500 files), comparison completes in seconds. Checkpointing is still useful for interrupted runs.
- For large collections (10K+ files), checkpoint every 50 files balances disk I/O against progress loss.
- The project already has a proven checkpoint pattern in `tools/core/checkpoint.py` with JSON serialization, versioning, and timestamp tracking.

**Checkpoint schema:**

```python
@dataclass
class CompareCheckpoint(ToolCheckpoint):
    source_dir: str = ""
    target_dir: str = ""
    compared_files: list[str] = field(default_factory=list)    # JSON-serializable
    match_counts: dict[str, int] = field(default_factory=dict) # running totals
```

**Implementation detail:** `compared_files` is stored as `list[str]` for JSON serialization but loaded into a Python `set` in memory for O(1) lookup. This was flagged by CR-Beta as critical — naive `list` lookup is O(N) and degrades with large collections.

**Checkpoint frequency:** Every 50 files (not every file — reduces disk I/O overhead). On graceful exit (SIGINT), the current state is saved immediately.

---

### D15: Error Handling Strategy

**Decision:** Non-fatal for file-level errors, fatal only for infrastructure failures.

| Scenario                      | Action                                                                          | Severity    |
| ----------------------------- | ------------------------------------------------------------------------------- | ----------- |
| Permission denied on file | Skip file, log ERROR, emit Level 0 record with `error` field | Non-fatal |
| Empty SGF file | Skip file, log WARN, emit Level 0 record with `error` field | Non-fatal |
| SGF with no stones (AB/AW missing) | Skip comparison, log WARN, emit Level 0 record with `"error": "no_stones"` | Non-fatal |
| Missing PL property | NOT an error — compute position hash only, match at Level 2 max | Informational |
| SGF parse failure (`SGFParseError`) | Skip file, log ERROR with filename and message, continue | Non-fatal |
| Output directory creation fails | **Fatal exit** (SystemExit) | Fatal |
| Corrupt checkpoint JSON | Backup corrupt file to `.checkpoint.json.bak`, start fresh, log WARN | Non-fatal |

**Rationale:** A comparison tool should process as many files as possible and report failures in the output. One corrupt file should not prevent comparison of the remaining 9,999 files.

---

### D16: Using Existing `tools/core/` SGF Infrastructure

**Decision:** All SGF parsing uses `tools.core.sgf_parser.parse_sgf()`. No regex, no `sgfmill`, no custom parsing.

**Rationale:**

- The project already has a proven recursive-descent SGF parser in `tools/core/sgf_parser.py` that returns `SgfTree` objects with all needed fields: `board_size`, `black_stones`, `white_stones`, `player_to_move`, `solution_tree`, `metadata`.
- `tools.core.sgf_types.Point` is `@dataclass(frozen=True, slots=True)` — frozen and hashable, safe for `frozenset` operations.
- `tools.core.sgf_analysis` provides `count_total_nodes()`, `compute_solution_depth()`, `get_all_paths()` for tree comparison metrics.
- `tools.core.sgf_correctness` provides `infer_correctness()` — already used by the parser to annotate `SgfNode.is_correct`.

**What we reuse:**

| Module               | What We Use                                                       | For                                                  |
| -------------------- | ----------------------------------------------------------------- | ---------------------------------------------------- |
| `sgf_parser.py` | `parse_sgf()` → `SgfTree` | Parsing every SGF file |
| `sgf_types.py` | `Point`, `Color` | Position hashing (sorted `Point.to_sgf()` strings) |
| `sgf_analysis.py` | `count_total_nodes()`, `compute_solution_depth()`, `get_all_paths()` | Tree metrics and path extraction |
| `sgf_correctness.py` | `infer_correctness()` | Already called by parser — nodes annotated at parse time |
| `checkpoint.py` | `ToolCheckpoint`, `save_checkpoint()`, `load_checkpoint()` | Resume support |
| `logging.py` | `StructuredLogger`, `EventType` | Run logging |
| `paths.py` | `get_project_root()`, `rel_path()` | Path normalization |
| `atomic_write.py` | `atomic_write_json()` | Safe checkpoint writes |

**Zero new dependencies.** Only stdlib (`hashlib`, `pathlib`, `json`, `argparse`, `datetime`) + existing `tools.core` modules.

---

### D17: Performance Characteristics

**Decision:** O(N + M) hash-map join algorithm with no parallelism needed for expected scale.

**Rationale:**

- SGF parsing is ~1ms/file (pure Python recursive descent). 10,000 files ≈ 10 seconds.
- Hash computation is negligible (SHA-256 of ~200-char strings).
- The hash-map join (build index for one dir, look up from the other) is O(N + M), not O(N × M).
- For the expected scale (hundreds to low thousands of files), this completes in seconds. No multiprocessing, no batching, no streaming optimization needed.

**If scale increases beyond 50K files:** Consider adding `--parallel` flag with `concurrent.futures.ProcessPoolExecutor` for parsing. But this is YAGNI for now.

---

### D18: What This Tool Does NOT Do

Explicitly out of scope (to prevent scope creep):

| Out of Scope                              | Reason                                                                           |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| Rotation/reflection normalization | Non-trivial heuristic; different orientation = different puzzle for this tool |
| Board size normalization (19×19 ↔ 9×9) | Requires "relevant area" detector — Go engine feature |
| PL inference from solution moves | Introduces unverifiable guesses |
| Automatic merging of files | The tool reports; humans decide |
| Modifying source or target files | Read-only operation |
| Solution quality assessment | This is comparison, not enrichment |
| Cross-run deduplication | Each run is independent |

---

## Expert Consultation Log

This tool's design was reviewed by three specialized agents in two consultation rounds:

### Round 1 — Initial Design

| Agent                        | Role                              | Key Contributions                                                                                                                                                                              |
| ---------------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **KataGo-Tsumego-Expert** | Tsumego domain expertise | Validated board position as primary key; recommended PL inclusion; proposed Level 3S/3D split; identified first-move as fast discriminator; stratified comments into correctness/teaching/metadata |
| **Code-Reviewer-Alpha** | Charter alignment, correctness | Proposed 2-file architecture; defined position hash algorithm matching backend; designed tree serialization; identified `is_correct` default caveat; comprehensive JSONL schema |
| **Code-Reviewer-Beta** | Architecture compliance, quality | Proposed separation of concerns; confirmed O(N+M) algorithm; designed dual-hash approach; defined error handling matrix; recommended `tools/puzzle-manager-scripts/output/` location |

### Round 2 — User Refinements

| Refinement                        | Expert Consulted       | Outcome                                                                         |
| --------------------------------- | ---------------------- | ------------------------------------------------------------------------------- |
| No PL inference | KataGo-Tsumego-Expert | Agreed. Dual-hash is correct middle ground. Full skip is too aggressive. |
| Pure numeric levels (no 3S/3D) | KataGo-Tsumego-Expert | Agreed. Expanded to 0–7 scale. Levels 4 and 5 replace 3S/3D. |
| Timestamped output dirs | Code-Reviewer-Beta | Confirmed `tools/puzzle-manager-scripts/output/` per git safety rules |
| Checkpoint batching (every 50 files) | Code-Reviewer-Beta | Agreed. `list[str]` in JSON, `set` in memory for O(1) |
| Error handling | Code-Reviewer-Beta | Non-fatal for file errors, fatal for infra failures |

---

## Modification Guide

### Adding a New Match Level

1. Add the level constant to the `MatchLevel` enum in `tools/core/sgf_compare.py`.
2. Add detection logic to `classify_match()` in the same file.
3. Update the level table in this document (D7).
4. Update the JSONL schema reference in this document (D12) if new fields are needed.
5. Update the summary report template in `compare_dirs.py`.

### Changing the Hash Algorithm

1. Modify `position_hash()` and/or `full_hash()` in `tools/core/sgf_compare.py`.
2. Update the algorithm documentation in this document (D6).
3. Note: Changing the hash invalidates all existing checkpoints. The tool should detect a hash algorithm change and warn.

### Supporting Rotation Normalization (Future)

1. Add a `normalize_orientation()` function to `tools/core/sgf_compare.py` that maps stone positions to a canonical corner.
2. Add `--normalize-rotation` CLI flag to `compare_dirs.py`.
3. Compute a third hash (normalized position hash) alongside the existing two.
4. This does NOT change match levels — it changes how position hashes are computed.

### Adding New Output Formats

1. The library (`sgf_compare.py`) returns `CompareResult` dataclasses. It is format-agnostic.
2. Output formatting lives entirely in `compare_dirs.py`. Add new serializers there.
3. Add a `--format` CLI flag if multiple formats become needed.
