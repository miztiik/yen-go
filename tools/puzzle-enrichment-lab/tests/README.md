# Puzzle Enrichment Lab — Test Suite

**Last Updated:** 2026-03-02

## Test Tier System

Tests are organized into tiers by speed, scope, and when to run them.
Use pytest markers to select the right tier for your workflow.

### Tier 0 — Unit Tests (`pytest -m unit`, ~20s)

- **No KataGo required** — all external dependencies mocked
- Tests each analyzer in isolation with controlled inputs
- **Run after every code change** for instant feedback
- All bug fixes get their first regression test here

### Tier 1 — Golden 5 (`pytest -m golden5`, ~2–3 min)

- **Real KataGo** in `quick_only` mode (200 visits, b18c384 model)
- 5 canonical puzzles, each testing a specific capability end-to-end:

| #   | Fixture                 | SZ  | Capability Tested                           |
| --- | ----------------------- | --- | ------------------------------------------- |
| 1   | `simple_life_death.sgf` | 19  | L&D winrate validation, hint generation     |
| 2   | `ko_direct.sgf`         | 9   | Ko detection, YK property, ko thresholds    |
| 3   | `sacrifice.sgf`         | 9   | Low-policy tesuji acceptance                |
| 4   | `board_9x9.sgf`         | 9   | Coordinate conversion, small-board handling |
| 5   | `miai_puzzle.sgf`       | 19  | Multi-response (miai), move_order detection |

- **If it works for these 5, the algorithm is sound**
- Run after algorithm changes: `pytest -m golden5`

### Tier 1.5 — Technique Calibration (`pytest tests/test_technique_calibration.py`, ~5–10 min)

- **Real KataGo** in `quick_only` mode, one fixture per technique tag
- 25 techniques × 5 calibration dimensions = 125 parametrized assertions
- Validates: correct move, technique tags, difficulty range, refutations, teaching comments
- **Run after changing technique detectors or replacing fixtures**
- Unit-only subset (no KataGo): `pytest tests/test_technique_calibration.py -m unit`
- See [Concepts: Technique Calibration](../../docs/concepts/technique-calibration.md)

### Tier 2 — Regression (`pytest -m "not (slow or calibration)"`, ~10 min)

- Includes all unit + golden5 + integration tests
- Uses the `controls-10` mixed-difficulty set
- **Run before merging** to validate no regression

### Tier 3 — Calibration (`pytest -m calibration`, ~15–30 min)

- Full dual-engine analysis against Cho Chikun reference collections
- 15 puzzles (5 per collection × 3 collections)
- **Run only before releases or after difficulty algorithm changes**
- NEVER run as part of a bug fix validation cycle

### Tier 4 — Scale (`pytest -m slow`, hours–days)

- Performance benchmarks: perf-33, perf-100, perf-1k, perf-10k
- **Run only in CI/CD or overnight**
- NEVER run locally during development

## Recommended Commands

| Situation                    | Command                                      | Time     |
| ---------------------------- | -------------------------------------------- | -------- |
| After every code change      | `pytest -m unit`                             | ~20s     |
| After algorithm changes      | `pytest -m "unit or golden5"`                | ~3 min   |
| After detector changes       | `pytest tests/test_technique_calibration.py` | ~5–10 min|
| Before merging               | `pytest -m "unit or golden5"`                | ~3 min   |
| Pre-release                  | `pytest -m "not (slow or calibration)"`      | ~10 min  |
| Difficulty algorithm changes | `pytest -m "unit or golden5 or calibration"` | ~30 min  |
| Full suite (CI only)         | `pytest`                                     | ~15+ min |

## Available Markers

| Marker        | Description                                              |
| ------------- | -------------------------------------------------------- |
| `unit`        | Fast isolated tests, no external dependencies (~20s)     |
| `golden5`     | 5 canonical puzzle integration tests (~2–3 min)          |
| `integration` | Tests requiring KataGo binary and model files            |
| `calibration` | Cho Chikun reference collection calibration (~15–30 min) |
| `slow`        | Long-running performance/scale tests (hours)             |
| `technique`   | Per-tag technique calibration (~5–10 min, 25 techniques) |

## Fixture Organization

```
tests/fixtures/
├── *.sgf                          # Individual technique fixtures (40+)
├── calibration/
│   ├── cho-elementary/            # 30 SGFs — Cho Chikun elementary
│   ├── cho-intermediate/          # 30 SGFs — Cho Chikun intermediate
│   ├── cho-advanced/              # 30 SGFs — Cho Chikun advanced
│   ├── ko/                        # 5 ko-specific SGFs
│   └── results/                   # Calibration run snapshots (gitignored)
├── extended-benchmark/             # 13 difficulty-stratified SGFs (5 techniques × 2-3 levels)
├── controls-10/                   # 10 mixed-difficulty controls
├── evaluation/                    # 30 SGFs (10 per difficulty)
├── perf-33/                       # 33 technique-spanning performance set
└── scale/                         # Large sets (100, 1k, 10k)
```

## Adding New Fixtures

When adding fixtures for new capabilities (e.g., 13×13 boards, seki):

1. Place SGF file in `tests/fixtures/` with descriptive name
2. Add a golden5 test if the fixture tests a core capability
3. Document board size, player to move, tags, and solution depth
4. Ensure at least one wrong branch for refutation testing

> **See also:**
>
> - [Architecture: KataGo Enrichment](../../docs/architecture/tools/katago-enrichment.md) — Design rationale
> - [Concepts: Quality](../../docs/concepts/quality.md) — Quality metrics definitions
> - [TODO: Consolidated Action Plan](../../TODO/todo-opus-katago-enrichment-consolidated.md) — Full fix plan
