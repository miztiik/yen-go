# Clarifications — Enrichment Lab Test Suite Consolidation

> Last Updated: 2026-03-22

## Resolved Clarifications

| Q_ID | Question | Resolution | Source |
|------|----------|------------|--------|
| Q1 | Are sprint files superseded by test_remediation_sprints.py? | **NO.** They use completely different gap ID namespaces (P0.x/G.x vs S.x-G.x) and test different functions. Zero overlap. | CR-ALPHA finding CRA-1 |
| Q2 | Are perf 100/1K/10K files placeholders? | **NO.** They contain full implementations with `run_batch()`, assertions, skip conditions, and timing thresholds. Properly gated by `@pytest.mark.slow`. | CR-ALPHA finding CRA-7 |
| Q3 | Should we create subdirectories (config/, teaching/, detectors/)? | **NO.** Too disruptive for current scope. File naming improvement is sufficient. | Governance Panel decision |
| Q4 | Which initiative hosts this work? | **New initiative** — DRY initiative (20260321-2100) is in closeout with different scope. | Governance Panel Q1 |
| Q5 | Lane ordering? | **L2 → L3 → L1 → L4.** Trivial rename first, then sys.path cleanup creates clean base, then migration, then optional perf consolidation. | Governance Panel Q4, RC-2 |
| Q6 | Migration atomicity? | **One commit per sprint file** (5 atomic commits for Lane 1). | Governance Panel RC-5, GV-2 concern |
| Q7 | pythonpath approach? | **`pythonpath` in pyproject.toml** `[tool.pytest.ini_options]` — cleanest, single-line, pytest-native. Verify with representative file per pattern first. | Governance Panel RC-6 |
| Q8 | Lane 4 scope? | **Extract shared helpers only** — `_prepare_input` signatures differ enough that forced parametrization would reduce readability. | Governance Panel Q5 |
| Q9 | Test count verification method? | **`pytest --co -q` output** — no fewer tests + explicit justification for any removals. | Governance Panel RC-8 |
| Q10 | DRY initiative interaction? | **Minimal.** DRY initiative modified conftest.py (adding `_sgf_render_utils.py`). Our Lane 3 removes sys.path boilerplate which DRY initiative did NOT address. No conflict. | Governance Panel RC-4 |
