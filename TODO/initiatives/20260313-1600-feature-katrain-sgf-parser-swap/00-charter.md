# Charter — KaTrain SGF Parser Swap

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Last Updated**: 2026-03-13

---

## Goals

1. **Replace sgfmill dependency** in the enrichment lab with KaTrain's pure-Python SGF parser
2. **Replace hand-rolled SGFParser** in the backend puzzle manager with KaTrain's parser
3. **Adopt KaTrain types** (`Move`, `SGFNode`, `SGF`) as the canonical SGF primitives in both subsystems
4. **Remove sgfmill** from `tools/puzzle-enrichment-lab/requirements.txt`
5. **Maintain independence** — Lab code stays in lab, backend code stays in backend, no cross-imports

## Non-Goals

- Merging lab and backend parsers into a shared library (future work)
- Adding GIB/NGF format support (strip multi-format parsers from KaTrain copy)
- Modifying the frontend SGF handling (out of scope)
- Changing `tools/core/sgf_parser.py` (not used; stays as-is)
- Adding new SGF parsing features beyond what exists today

## Constraints

1. **Independence**: Each copy of KaTrain's parser is self-contained. Lab's `core/` and backend's `core/` do not import from each other.
2. **KaTrain fidelity**: Stay as close to upstream KaTrain as possible so future updates can drop in with minimal diff.
3. **No new external deps**: The KaTrain copy must be stdlib-only (strip `chardet`, `parse_file`, `parse_gib`, `parse_ngf`).
4. **Backward compat NOT required**: All consumers will be updated to use KaTrain types (Q1 resolved).
5. **Dead code policy**: Old parsers deleted, not deprecated. Git history preserves.
6. **Tests are definition of done**: All existing tests must pass after migration.
7. **Git safety**: No `git add .`, no `git stash`, no `git reset --hard`. Selective staging only.

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | `sgfmill` removed from enrichment lab `requirements.txt` | File inspection |
| AC-2 | No `import sgfmill` or `from sgfmill` in any project Python file | `grep -r "sgfmill" --include="*.py" .` returns 0 |
| AC-3 | KaTrain parser in `tools/puzzle-enrichment-lab/core/sgf_parser.py` | File exists, contains `class SGFNode`, `class SGF`, `class Move` |
| AC-4 | KaTrain parser in `backend/puzzle_manager/core/katrain_sgf_parser.py` | File exists, contains same classes |
| AC-5 | All enrichment lab tests pass | `cd tools/puzzle-enrichment-lab && pytest tests/` |
| AC-6 | All backend tests pass (excluding slow/cli) | `pytest -m "not (cli or slow)"` |
| AC-7 | Old `tools/puzzle-enrichment-lab/analyzers/sgf_parser.py` deleted | File does not exist |
| AC-8 | Backend `sgf_parser.py` rewritten to use KaTrain internally | `SGFParser` class replaced with KaTrain conversion |
| AC-9 | `sgf_enricher.py` has zero sgfmill usage | No `sgfmill_sgf` calls in file |
| AC-10 | Tsumego-specific functions (extract_position, extract_correct_first_move, etc.) in a separate wrapper file | Thin wrapper exists alongside KaTrain parser |

## Scope Summary

| Subsystem | What Changes | Estimated Files |
|-----------|-------------|-----------------|
| Enrichment Lab | New `core/sgf_parser.py` (KaTrain copy), new `core/tsumego_analysis.py` (thin wrapper), delete old `analyzers/sgf_parser.py`, update ~10 consumers, rewrite sgfmill code in `sgf_enricher.py` | ~14 files |
| Backend | New `core/katrain_sgf_parser.py` (KaTrain copy), rewrite `core/sgf_parser.py` internals, keep `SGFGame`/`SolutionNode`/`YenGoProperties` facade | ~3 files |
| Config | Remove sgfmill from `requirements.txt` | 1 file |

**Correction Level**: Level 4 (Large Scale) — 4+ files, structure changes, two subsystems.

## Rollback Strategy

Changes are committed **per-subsystem in phased commits**:

1. **Phase A**: Enrichment Lab (new `core/`, wrapper, consumer updates, sgfmill removal)
2. **Phase B**: Backend Puzzle Manager (new KaTrain parser, sgf_parser.py rewrite)

Each phase is independently revertible via `git revert <commit>`. If Phase A passes all tests but Phase B regresses, Phase B can be reverted without affecting Phase A.

No shared state between phases — the two subsystems have no cross-imports.

> **See also**:
> - [Prior research](../20260310-research-sgfmill-replacement/15-research.md) — sgfmill replacement complexity assessment
> - [Research brief](./15-research.md) — KaTrain swap-specific findings
