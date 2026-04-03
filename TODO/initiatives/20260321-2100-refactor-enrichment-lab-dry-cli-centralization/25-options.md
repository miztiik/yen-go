# Options — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-21  
> Initiative: 20260321-2100-refactor-enrichment-lab-dry-cli-centralization  
> Status: options_drafted

---

## Options Comparison Matrix

| Criterion | OPT-1: Bootstrap-First | OPT-2: Full CLI Absorption | OPT-3: Hybrid (Recommended) |
|-----------|----------------------|---------------------------|----------------------------|
| **Approach** | Create `bootstrap()` in `log_config.py`; add `__aenter__/__aexit__` to engine; extract SGF utils; make `_model_paths` lazy. Keep ALL scripts standalone. | Absorb `run_calibration`, `download_models`, `measure_quality`, `generate_report` as CLI subcommands. Move bootstrap + engine CM + SGF dedup inside CLI framework. | Bootstrap + engine CM + SGF dedup + lazy `_model_paths` (like OPT-1). Absorb ONLY `run_calibration` as CLI subcommand. Other scripts use bootstrap but stay standalone. Consolidate `_resolve_katago_config()`. |
| **Files Modified** | ~8 | ~15 | ~12 |
| **Net Lines** | -120 (80 new, 200 deleted) | -60 (250 new, 310 deleted) | -150 (90 new, 240 deleted) |
| **Risk** | Low | Medium-High | Low-Medium |
| **Regression Risk** | Minimal — callers change ceremony, not behavior | Higher — CLI surface grows, argparse conflicts possible | Low — incremental, testable phases |
| **SOLID Compliance** | SRP: good. OCP: good. | SRP: cli.py grows significantly (violation). OCP: ok. | SRP: good. OCP: good. |
| **DRY Impact** | Eliminates 80% of duplication | Eliminates 95% of duplication | Eliminates 90% of duplication |
| **KISS** | Simplest — minimal new abstractions | Complex — large cli.py, many subcommands | Balanced — targeted absorption |
| **YAGNI** | Does not build unneeded CLI subcommands | Builds CLI for scripts used <monthly | Only absorbs actively-used production script |
| **Test Impact** | Existing tests pass unchanged | New tests needed for 4+ subcommands | New tests needed for 1 subcommand |
| **Rollback** | Easy — each change reversible | Hard — entangled changes | Moderate — phased rollback |

---

## OPT-1: Bootstrap-First (Minimal DRY Fix)

### Summary
Focus purely on DRY violations without changing CLI surface. All scripts remain standalone but use a shared `bootstrap()` function from `log_config.py`.

### Changes
1. **Add `bootstrap()` to `log_config.py`**: Wraps `generate_run_id() → setup_logging() → set_run_id()` into one call. All 5 entry points reduce to 1 line.
2. **Add `__aenter__/__aexit__` to `SingleEngineManager`**: 8 lines added. Callers optionally use `async with`.
3. **Extract `tests/_sgf_render_utils.py`**: Move regex SGF parsers from `render_fixtures.py` and `generate_review_report.py` to shared module.
4. **Make `_model_paths.py` lazy**: Use `@lru_cache` for config-dependent values.
5. **Consolidate `_resolve_katago_config()`**: Move to `analyzers/single_engine.py`, remove from `cli.py` and `run_calibration.py`.

### Benefits
- Lowest risk — no CLI surface changes
- Each item independently testable
- Maximum reversibility
- Scripts remain easy to find and run

### Drawbacks
- 13 scripts still have independent `argparse` setups
- `run_calibration.py` still duplicates engine lifecycle ceremony (even with context manager, it has restart logic)
- Doesn't address Q8 (CLI absorption question)

### Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| lru_cache vs clear_cache interaction | Low | `_model_paths` values are per-process constants |
| Import order changes from lazy loading | Low | Only defers WHEN config loads, not IF |

---

## OPT-2: Full CLI Absorption

### Summary
Absorb all production scripts as CLI subcommands. Every enrichment lab operation goes through `cli.py`.

### Changes
1. Everything in OPT-1, PLUS:
2. **New `calibrate` subcommand** absorbing `run_calibration.py` (~200 lines moved)
3. **New `download-models` subcommand** absorbing `download_models.py` (~100 lines moved)
4. **New `measure-quality` subcommand** absorbing `measure_enrichment_quality.py` (~200 lines moved)
5. **New `report` subcommand** absorbing `generate_review_report.py` (~400 lines moved)
6. Shared argparse builder for common flags (`--verbose`, `--log-dir`, `--config`)

### Benefits
- Single entry point for all operations
- Consistent argument handling across all commands
- Unified `--help` documentation

### Drawbacks
- `cli.py` grows from ~900 lines to ~1600+ lines — SRP violation
- Scripts lose standalone usability (must go through `python -m cli calibrate ...`)
- High regression risk — 4 new subcommands to test
- YAGNI: most scripts are used infrequently
- `generate_review_report.py` is 500+ lines with SVG rendering — doesn't belong in CLI

### Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| cli.py SRP violation | Medium | Could split into cli_calibrate.py, cli_report.py modules |
| argparse conflicts between subcommands | Medium | Careful argument namespacing |
| Breaking standalone scripts during transition | Medium | Dual-path operation during migration |

---

## OPT-3: Hybrid Bootstrap + Targeted CLI Absorption (Recommended)

### Summary
Apply all bootstrap DRY fixes (like OPT-1), plus absorb ONLY `run_calibration.py` as a CLI subcommand — it's the only production workflow that actively uses the enrichment API and would benefit from shared CLI infrastructure. Other scripts stay standalone but use the bootstrap function.

### Changes
1. **Add `bootstrap()` to `log_config.py`**: Same as OPT-1.
2. **Add `__aenter__/__aexit__` to `SingleEngineManager`**: Same as OPT-1.
3. **Extract `tests/_sgf_render_utils.py`**: Same as OPT-1.
4. **Make `_model_paths.py` lazy**: Same as OPT-1.
5. **Consolidate `_resolve_katago_config()`**: Move to `analyzers/single_engine.py`.
6. **Move common argparse builder** to shared helper — `--verbose`, `--log-dir` flags reusable.
7. **Add `calibrate` subcommand to `cli.py`**: Absorb `run_calibration.py` core logic. Keep `scripts/run_calibration.py` as thin wrapper that calls `cli.py calibrate`.

### Benefits
- Eliminates 90% of DRY violations
- `run_calibration.py` (most complex script) gets full CLI integration
- Other scripts remain lightweight and standalone
- `cli.py` grows modestly (~100 lines for calibrate subcommand)
- Each phase independently testable and reversible
- YAGNI-compliant: only absorbs what's actively needed

### Drawbacks
- Still leaves some argparse duplication in lesser-used scripts
- `scripts/run_calibration.py` becomes a thin wrapper (some may prefer it stays standalone)

### Risks
| Risk | Severity | Mitigation |
|------|----------|------------|
| Calibrate subcommand complexity | Low-Medium | `run_calibration.py` already has clean `run_calibration()` function |
| Bootstrap adoption in bridge.py | Low | Bridge uses FastAPI lifespan — bootstrap for logging only |

### Phased Execution Plan
| Phase | What | Risk | Reversible? |
|-------|------|------|-------------|
| Phase 1 | Bootstrap function + all callers | Low | Yes |
| Phase 2 | Engine `__aenter__/__aexit__` + caller updates | Low | Yes |
| Phase 3 | `_resolve_katago_config()` consolidation | Low | Yes |
| Phase 4 | `_model_paths.py` lazy loading | Low | Yes |
| Phase 5 | SGF regex parser dedup → `_sgf_render_utils.py` | Low | Yes |
| Phase 6 | `calibrate` CLI subcommand + run_calibration wrapper | Medium | Yes (revert wrapper) |

---

## Recommendation

**OPT-3 (Hybrid)** provides the best balance of DRY elimination, risk management, and YAGNI compliance. It addresses 6 of 7 charter goals fully (G1-G5, G7) and G6 partially (absorbs the primary production script). The phased execution plan ensures each step is independently testable with zero-regression gates.

> **See also:**
> - [Charter](./00-charter.md) — Scope and constraints
> - [Research](./15-research.md) — Evidence base (35 internal refs)
> - [Clarifications](./10-clarifications.md) — Resolved decisions
