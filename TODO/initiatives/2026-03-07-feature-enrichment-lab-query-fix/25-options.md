# Options: DRY/SRP Refactor of Query Paths

**Initiative:** `2026-03-07-feature-enrichment-lab-query-fix`
**Last Updated:** 2026-03-07

---

## DRY/SRP Violation Audit

### What is duplicated

Three code paths independently implement tsumego query preparation. Here is a line-by-line comparison of the duplicated steps:

| Step                     | `build_query_from_sgf()` (query_builder.py:109-230) | `build_query_from_position()` (query_builder.py:241-340) | `SyncEngineAdapter.__init__+query()` (solve_position.py:449-530) |
| ------------------------ | --------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------- |
| 1. Override komi to 0    | `Position(..., komi=_TSUMEGO_KOMI)`                 | `Position(..., komi=_TSUMEGO_KOMI)`                      | `PositionModel(..., komi=0.0)`                                   |
| 2. Compute puzzle region | `eval_position.get_puzzle_region_moves(margin=m)`   | `tsumego_position.get_puzzle_region_moves(margin=m)`     | `tsumego_position.get_puzzle_region_moves(margin=2)`             |
| 3. Apply tsumego frame   | `apply_tsumego_frame(eval_position, margin=m)`      | `apply_tsumego_frame(tsumego_position, margin=m)`        | `apply_tsumego_frame(tsumego_position, margin=2)`                |
| 4. Set allowed_moves     | `allowed_moves=region_moves`                        | `allowed_moves=region_moves`                             | **MISSING** (BUG-1)                                              |
| 5. Ko-aware rules        | Full config lookup                                  | Full config lookup (duplicated)                          | Not implemented                                                  |
| 6. Symmetries override   | Config-driven                                       | Not implemented                                          | Not implemented                                                  |
| 7. max_time              | Config-driven                                       | Not implemented                                          | Not implemented                                                  |

### Severity

- **DRY violation**: Steps 1-3 are implemented identically in 3 places (100+ lines of duplicated intent)
- **SRP violation**: `SyncEngineAdapter.__init__()` performs tsumego preparation (query_builder's job) AND async-to-sync bridging (adapter's job). Two responsibilities in one class.
- **Consistency failure**: BUG-1 is a direct consequence — `allowed_moves` was correctly set in 2/3 paths but missed in the 3rd, precisely because the logic was copy-pasted rather than shared.
- **Feature gap**: Ko-aware rules, symmetries override, and max_time are only in `build_query_from_sgf()`. The other two paths silently use worse defaults.

---

## Options

### OPT-A: Minimal Patch (add 1 line to SyncEngineAdapter)

| Aspect                    | Detail                                                                                                                                                                                                      |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**              | Add `allowed_moves=self._region_moves` to `AnalysisRequest` in `SyncEngineAdapter.query()`. Leave DRY violation in place.                                                                                   |
| **Files changed**         | 1: solve_position.py                                                                                                                                                                                        |
| **Benefits**              | Minimal risk, fixes BUG-1 immediately                                                                                                                                                                       |
| **Drawbacks**             | DRY violation remains. 3 paths still diverge. Ko-aware rules, symmetries, max_time still missing from adapter. Next developer will face the same copy-paste trap.                                           |
| **SOLID compliance**      | DRY: violated. SRP: violated (adapter still does prep + bridging).                                                                                                                                          |
| **Risk**                  | Low (implementation), **High** (architectural — violation persists, invites future regressions)                                                                                                             |
| **Governance assessment** | Per `.claude/rules/03-architecture-rules.md`: "Agents should not add new tech-debt/dependency exceptions." This option preserves existing tech debt rather than adding new debt, but does not remediate it. |

### OPT-B: Extract shared `prepare_tsumego_query()` + simplify adapter (RECOMMENDED)

| Aspect                    | Detail                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach**              | Extract a new shared function `prepare_tsumego_query(position, config, ko_type, margin) → (framed_position, region_moves, rules, pv_len)` in `query_builder.py`. All three paths call this single function. `SyncEngineAdapter.__init__()` calls it instead of reimplementing steps 1-3. `SyncEngineAdapter.query()` uses the precomputed `region_moves` and `framed_position` from the shared function output. |
| **Files changed**         | 2: query_builder.py, solve_position.py                                                                                                                                                                                                                                                                                                                                                                          |
| **Benefits**              | Eliminates DRY violation. Single source of truth for tsumego prep. SyncEngineAdapter only does async-to-sync bridging (SRP restored). Ko-aware rules, symmetries, max_time automatically available to all paths. BUG-1 fixed by construction.                                                                                                                                                                   |
| **Drawbacks**             | Slightly larger change (~40 lines restructured). Requires test verification.                                                                                                                                                                                                                                                                                                                                    |
| **SOLID compliance**      | DRY: compliant. SRP: compliant (adapter = bridging only, query_builder = query prep only). OCP: compliant (new features like ko-awareness auto-propagate).                                                                                                                                                                                                                                                      |
| **Risk**                  | Low — restructuring existing correct logic, not new behavior                                                                                                                                                                                                                                                                                                                                                    |
| **Governance assessment** | Directly addresses the DRY concern raised by user. Prevents future regressions of this class.                                                                                                                                                                                                                                                                                                                   |

### OPT-C: Merge SyncEngineAdapter into query_builder.py entirely

| Aspect               | Detail                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Approach**         | Move `SyncEngineAdapter` class from solve_position.py into query_builder.py. Consolidate all query logic in one module.                                                                                                                                                                                                                                                                                                                                            |
| **Files changed**    | 2: query_builder.py, solve_position.py                                                                                                                                                                                                                                                                                                                                                                                                                             |
| **Benefits**         | All query code in one file. Maximum cohesion.                                                                                                                                                                                                                                                                                                                                                                                                                      |
| **Drawbacks**        | `SyncEngineAdapter` has a dependency on `SingleEngineManager` (from `engine/`), which query_builder.py currently doesn't import. Moving it would create an import of `engine.single_engine` in query_builder — violating the current dependency direction (analyzers → models, not analyzers → engine). Also, the async-to-sync bridging concern is fundamentally different from query building — keeping them in separate files respects SRP at the module level. |
| **SOLID compliance** | DRY: compliant. SRP: _worse_ at module level (query_builder would mix query building + engine interaction). DIP: violated (query_builder gains dependency on engine module).                                                                                                                                                                                                                                                                                       |
| **Risk**             | Medium — dependency direction change could cause import cycles                                                                                                                                                                                                                                                                                                                                                                                                     |

---

## Comparison Matrix

| Criterion                    | OPT-A                          | OPT-B       | OPT-C          |
| ---------------------------- | ------------------------------ | ----------- | -------------- |
| DRY compliance               | FAIL                           | PASS        | PASS           |
| SRP compliance               | FAIL                           | PASS        | MIXED          |
| DIP compliance               | PASS                           | PASS        | FAIL           |
| Risk                         | Low impl / High arch           | Low         | Medium         |
| Lines changed                | ~1                             | ~40         | ~60            |
| Future regression prevention | NO                             | YES         | YES            |
| Ko-aware rules in adapter    | NO                             | YES (auto)  | YES (auto)     |
| Governance council alignment | Rejected (preserves tech debt) | Recommended | Too much scope |

---

## Recommendation

**OPT-B** — Extract `prepare_tsumego_query()` as the single source of truth.

This is the minimum change that fully eliminates the DRY violation, restores SRP, and fixes BUG-1 by construction. It follows KISS (no new abstractions, just extraction) and YAGNI (no speculative features).

> **See also**:
>
> - [00-charter.md](./00-charter.md) — Goals
> - [30-plan.md](./30-plan.md) — Technical implementation plan
