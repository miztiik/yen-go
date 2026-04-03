# Clarifications — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-21

## Clarification Rounds

### Round 1 — User-Provided Direction (Pre-session)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Is backward compatibility required? | A: Yes / B: No | B: No — internal tooling, no external consumers | **B: No** — user wants centralization, old patterns removed | ✅ resolved |
| Q2 | Should old code be removed? | A: Yes / B: Deprecate first / C: Keep both | A: Yes — dead code policy | **A: Yes** — user explicitly wants DRY cleanup | ✅ resolved |
| Q3 | Should P5 (probe_frame merge) be included? | A: Yes / B: No | B: No — user concern about regression | **B: No** — user: "Let us not do P5", probe_frame_gp is production, probe_frame may be broken | ✅ resolved |
| Q4 | Which tests should gate each phase? | A: All tests / B: Unit + functional only / C: Custom selection | C: All except calibration, performance, golden5, ai_solve_calibration | **C** — user: "leave the calibration test and performance test" | ✅ resolved |
| Q5 | Should a clean commit be made before starting? | A: Yes / B: No | A: Yes — safety checkpoint | **A: Yes** — user explicitly requested | ✅ resolved |
| Q6 | Should governance gate each implementation phase? | A: Yes / B: Skip for minor phases | A: Yes — every phase reviewed | **A: Yes** — user: "every single phase is checked" | ✅ resolved |
| Q7 | Zero regressions tolerance? | A: Zero tolerance / B: Allow non-functional | A: Zero tolerance | **A: Zero tolerance** — user: "Do not create any regression for any reason" | ✅ resolved |
| Q8 | Should new CLI subcommands be created to absorb scripts? | A: Yes new subcommands / B: Keep scripts but centralize internals / C: Hybrid | Pending — options phase will evaluate | Pending — needs options phase | ❌ pending |

### Round 2 — Inferred from Audit (Agent-Resolved)

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q9 | Scope: Which DRY items are in-scope? | P0-P4, P6 from audit | All except P5 | P0 (bootstrap), P1 (katago config), P2 (argparse), P3 (engine lifecycle), P4 (regex SGF), P6 (CLI subcommands for scripts) | ✅ resolved |
| Q10 | Should bridge.py be refactored to use centralized bootstrap? | A: Yes / B: No (separate concern) | A: Yes — it's the #2 entry point | A: Yes — DRY applies to bridge too | ✅ resolved |
| Q11 | Should test conftest.py use the same bootstrap? | A: Yes with test-specific overrides / B: Keep separate | A: Yes — but console_format="human" override | A: Yes — consistent logging init | ✅ resolved |

## Excluded Scope (Explicit)

- **P5**: Do NOT touch `probe_frame.py` or `probe_frame_gp.py` — user directive
- **Calibration tests**: Not part of regression gating
- **Performance/golden5 tests**: Not part of regression gating
- **ai_solve_calibration tests**: Not part of regression gating

## Test Regression Command (Agreed)

```bash
cd c:\Users\kumarsnaveen\Downloads\NawiN\personal\gitrepos\yen-go
python -B -m pytest tools/puzzle-enrichment-lab/tests/ -m "not slow" --ignore=tools/puzzle-enrichment-lab/tests/test_golden5.py --ignore=tools/puzzle-enrichment-lab/tests/test_calibration.py --ignore=tools/puzzle-enrichment-lab/tests/test_ai_solve_calibration.py -q --no-header --tb=short -p no:cacheprovider
```
