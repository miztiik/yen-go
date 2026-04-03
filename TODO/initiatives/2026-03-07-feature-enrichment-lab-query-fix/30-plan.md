# Technical Plan

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07
**Selected Option:** OPT-B — Extract shared `prepare_tsumego_query()`

---

## 1. Architecture: The Shared Function

### 1.1 New Function: `prepare_tsumego_query()`

**Location:** `tools/puzzle-enrichment-lab/analyzers/query_builder.py`

**Signature:**

```python
@dataclass
class TsumegoQueryBundle:
    """Result of tsumego query preparation — all data needed to build AnalysisRequest."""
    framed_position: Position      # Position with tsumego frame applied
    region_moves: list[str]        # GTP coords for allowed_moves restriction
    rules: str                     # Ko-aware rules string ("chinese" or "tromp-taylor")
    pv_len: int | None             # Per-request PV length override (None = default)
    komi: float                    # Always 0.0 for tsumego

def prepare_tsumego_query(
    position: Position,
    *,
    config: EnrichmentConfig | None = None,
    ko_type: str = "none",
    puzzle_region_margin: int | None = None,
) -> TsumegoQueryBundle:
    """Single source of truth for tsumego query preparation.

    Steps (always in this order):
    1. Override komi to 0.0 (tsumego = life/death, not scoring)
    2. Compute puzzle region moves (bounding box + margin)
    3. Apply tsumego frame (fill empty areas with offense/defense stones)
    4. Resolve ko-aware rules and PV length from config

    This is a PURE function: no engine reference, no side effects, no I/O.
    All three query paths must call this function.

    Args:
        position: Raw board position (may have any komi).
        config: Enrichment config. Loaded automatically if None.
        ko_type: Ko context from YK property ("none", "direct", "approach").
        puzzle_region_margin: Margin around puzzle stones. If None, uses config default.

    Returns:
        TsumegoQueryBundle with all data needed to build an AnalysisRequest.
    """
```

**Rationale:**

- Pure function = easy to test, no hidden dependencies
- Returns a data bundle = callers compose their own AnalysisRequest with path-specific extras (crop metadata, moves sequence, symmetries, etc.)
- `allowed_moves` is structurally guaranteed — it's in the return type

### 1.2 Call-Site Changes

| Call Site                      | Before                                       | After                                                                                                                                    |
| ------------------------------ | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `build_query_from_sgf()`       | Inline steps 1-5 (~40 lines)                 | Call `prepare_tsumego_query(eval_position, config=config, ko_type=ko_type, puzzle_region_margin=margin)`, use result for AnalysisRequest |
| `build_query_from_position()`  | Inline steps 1-4 (~25 lines)                 | Call `prepare_tsumego_query(position, config=config, ko_type=ko_type, puzzle_region_margin=margin)`, use result for AnalysisRequest      |
| `SyncEngineAdapter.__init__()` | Inline steps 1-3 (~15 lines)                 | Call `prepare_tsumego_query(position, config=config)`, store `bundle.framed_position` and `bundle.region_moves`                          |
| `SyncEngineAdapter.query()`    | Builds AnalysisRequest WITHOUT allowed_moves | Builds AnalysisRequest WITH `allowed_moves=self._region_moves` (now guaranteed set from shared function)                                 |

### 1.3 What Gets Deleted

- `SyncEngineAdapter.__init__()`: Remove inline komi override, `get_puzzle_region_moves()`, `apply_tsumego_frame()` calls (~15 lines)
- `build_query_from_position()`: Remove inline komi override, `get_puzzle_region_moves()`, `apply_tsumego_frame()`, ko-aware rules resolution (~25 lines)
- `build_query_from_sgf()`: Remove inline komi override, `get_puzzle_region_moves()`, `apply_tsumego_frame()` (~15 lines, keep crop logic which is path-specific)

---

## 2. Bug Fixes (non-DRY)

### 2.1 BUG-3: Encoding in sgf_enricher.py

**Problem:** `_get_node_move_coord()` uses `.decode("latin-1")` — incorrect for UTF-8 SGF content.

**Fix:** Change to `.decode("utf-8", errors="replace")`. Additionally, ensure `_embed_teaching_comments()` only adds ASCII text (strip non-ASCII from any enrichment-generated text before embedding).

**File:** `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`

### 2.2 BUG-4: Diagnostic data in C[] comments

**Problem:** `_build_refutation_branches()` embeds "Winrate drops by X%." and "Refutation line N/M." in C[] comments. This is diagnostic data, not teaching content.

**Fix:**

- Remove winrate drop annotation from the branch comment. Keep only `"Wrong."` prefix.
- Refutation line numbering (`Refutation line N/M.`) can be kept as structural metadata if desired, or removed.
- Log the delta/score data instead via `logger.info(...)`.

**File:** `tools/puzzle-enrichment-lab/analyzers/sgf_enricher.py`

### 2.3 BUG-6: Logging namespace filter

**Problem:** `_LabNamespaceFilter` checks `record.name.startswith("puzzle_enrichment_lab")` but modules use `logging.getLogger(__name__)` which produces names like `analyzers.enrich_single`.

**Fix:** Update the filter to match actual module prefixes used in the enrichment lab. Use an allowlist approach:

```python
_LAB_MODULE_PREFIXES = (
    "analyzers", "engine", "models", "config", "cli", "log_config",
    "puzzle_enrichment_lab",  # keep for backward compat
    "conftest",
)

class _LabNamespaceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return any(record.name.startswith(p) for p in _LAB_MODULE_PREFIXES)
```

**File:** `tools/puzzle-enrichment-lab/log_config.py`

### 2.4 Log file naming alignment

**Problem:** Enrichment logs use `{run_id}-enrichment.log` where run_id = `YYYYMMDD-8hex`. KataGo logs use `YYYYMMDD-HHMMSS-8HEX.log`.

**Fix:** Update `generate_run_id()` in `models/ai_analysis_result.py` to include HHMMSS:

```python
def generate_run_id() -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%Y%m%d}-{now:%H%M%S}-{secrets.token_hex(4).upper()}"
```

Update `setup_logging()` file naming to match: `{run_id}-enrichment.log` → `{run_id}.log` (since the run_id itself now contains the timestamp).

**Files:** `models/ai_analysis_result.py`, `log_config.py`

---

## 3. Golden Fixture Test

**File:** New or addition to `tests/test_solve_position.py`

**Fixture:** Original puzzle SGF:

```
(;SZ[19]FF[4]GM[1]PL[B]C[problem 1 ]AB[fb][bb][cb][db]AW[ea][dc][cc][eb][bc])
```

**Test assertions:**

1. After `prepare_tsumego_query()`: `region_moves` only contains moves in columns A-F, rows 17-19 (± margin)
2. `allowed_moves` is non-empty
3. No move in `region_moves` is outside the puzzle bounding box + margin
4. (When engine is mocked): `SyncEngineAdapter.query()` builds `AnalysisRequest` WITH `allowed_moves`

---

## 4. Documentation Updates

**File:** `tools/puzzle-enrichment-lab/README.md` or inline code comments

Document:

1. The single query preparation path via `prepare_tsumego_query()`
2. Why `allowed_moves` is mandatory for all tsumego queries
3. Comment policy: only teaching comments in C[], diagnostics go to logs
4. Log file naming convention: `YYYYMMDD-HHMMSS-8HEX.log` or `YYYYMMDD-HHMMSS-8HEX-enrichment.log`

---

## 5. Risks and Mitigations

| risk_id | risk                                                                      | probability | impact | mitigation                                                                                                                                                      |
| ------- | ------------------------------------------------------------------------- | ----------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R-1     | Existing tests use internal details of `SyncEngineAdapter.__init__()`     | Low         | Medium | Run full test suite after each change. The adapter's external API (`.query()`) is unchanged.                                                                    |
| R-2     | `generate_run_id()` format change breaks downstream consumers             | Low         | Low    | Search for all consumers of `run_id` format. The format is only used in log file names and JSON metadata — no parsing is done on the format.                    |
| R-3     | Logging filter change over-admits or under-admits records                 | Low         | Low    | Test with actual log output. The prefix allowlist is explicit.                                                                                                  |
| R-4     | `prepare_tsumego_query()` signature doesn't cover all path-specific needs | Low         | Medium | Include all shared parameters in the function. Path-specific concerns (crop, moves, symmetries) remain with callers — they compose the final `AnalysisRequest`. |

> **See also**:
>
> - [25-options.md](./25-options.md) — Options analysis
> - [40-tasks.md](./40-tasks.md) — Task decomposition
> - [70-governance-decisions.md](./70-governance-decisions.md) — OPT-B approval
