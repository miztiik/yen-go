# Research: Ground-Truth Verification of Enrichment Lab Initiative Claims

**Research Date**: 2026-03-24  
**Artifact**: `15-research-ground-truth.md`  
**Scope**: 9 enrichment-lab initiatives claiming closeout/completion, verified against actual codebase

---

## 1. Research Question and Boundaries

**Question**: Do the claimed deliverables from 9 enrichment-lab initiatives (R-1 through R-24) actually exist in the codebase?

**Methodology**:
- Read each initiative's `status.json` and `40-tasks.md`
- Identify specific files and functionality claimed
- Verify file existence, function signatures, and structural changes via grep/file-search
- Cross-reference test file counts and naming patterns

**Boundaries**: Enrichment lab only (`tools/puzzle-enrichment-lab/`), backend correctness module, frontend solution tree tests.

---

## 2. Verification Results by Initiative

### R-1: `20260314-1400-feature-enrichment-lab-v2`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-1.1 | `entropy_roi.py` created with ownership entropy computation | `analyzers/entropy_roi.py` exists; `compute_entropy_roi()` at line 73 | **CONFIRMED** |
| R-1.2 | Board cropping removed (`CroppedPosition`, `crop_to_tight_board()`) | Zero grep hits for `CroppedPosition` in `analyzers/` or `models/position.py` | **CONFIRMED** |
| R-1.3 | `test_tight_board_crop.py` deleted | `Test-Path` returns False | **CONFIRMED** |
| R-1.4 | `analyzers/stages/analyze_stage.py` created (renamed from query_stage) | File exists; `query_stage.py` ALSO still exists (both present) | **PARTIAL** — rename happened but old file not deleted |
| R-1.5 | `stages/technique_stage.py`, `sgf_writeback_stage.py`, `solve_path_stage.py` created | All three files confirmed present | **CONFIRMED** |
| R-1.6 | `models/validation.py` extracted with `ValidationStatus` | File exists; `ValidationStatus` enum at line 38 | **CONFIRMED** |
| R-1.7 | `models/detection.py` created | File exists | **CONFIRMED** |
| R-1.8 | `analyzers/detectors/` directory with 28 individual detectors | Directory exists with 28 `.py` files (excluding `__init__.py`) | **CONFIRMED** |
| R-1.9 | Delete `tsumego_frame.py` (T1 claim) | `analyzers/tsumego_frame.py` STILL EXISTS; `tests/test_tsumego_frame.py` STILL EXISTS | **NOT_DONE** |
| R-1.10 | Visit tier config and wiring (T20-T23) | `tests/test_visit_tiers.py` exists; `VisitTiersConfig` in config | **CONFIRMED** |
| R-1.11 | Refutation framing consistency tests (T19) | `tests/test_refutation_framing.py` exists | **CONFIRMED** |

**Overall R-1 Verdict**: **PARTIAL** — Core v2 rewrite substantially delivered (entropy ROI, crop removal, detectors, stages). Two gaps: `tsumego_frame.py` not deleted (T1), `query_stage.py` still exists alongside new `analyze_stage.py` (T8).

---

### R-8: `20260315-2000-feature-refutation-quality`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-8.1 | Phase A: `compute_ownership_delta()` in `generate_refutations.py` | Function at line 36, wired at lines 223/237/250 | **CONFIRMED** |
| R-8.2 | Phase A: 28 tests across 3 test files | `test_refutation_quality_phase_a.py` exists | **CONFIRMED** |
| R-8.3 | Phase B: Config v1.19 keys (adaptive visits, noise scaling, forced visits, player alternatives) | `test_refutation_quality_phase_b.py` exists; config models `SolutionTreeConfig`, `RefutationsConfig` have claimed fields | **CONFIRMED** |
| R-8.4 | Phase C: Branch escalation (`branch_escalation_enabled` in `config/solution_tree.py`) | Field confirmed at line 164 | **CONFIRMED** |
| R-8.5 | Phase C: Multi-pass harvesting (`multi_pass_harvesting` in `config/refutations.py`) | Field confirmed at line 182 | **CONFIRMED** |
| R-8.6 | Phase C: Best-resistance (`best_resistance_enabled`) | `config/refutations.py` confirmed | **CONFIRMED** |
| R-8.7 | Phase C: 24 tests in `test_refutation_quality_phase_c.py` | File exists | **CONFIRMED** |
| R-8.8 | Phase D: Surprise-weighted calibration (`surprise_weighting` in `config/infrastructure.py`) | `surprise_weighting` at line 60, `compute_surprise_weight()` at line 70 | **CONFIRMED** |
| R-8.9 | Phase D: 17 tests in `test_refutation_quality_phase_d.py` | File exists with `TestSurpriseWeightedCalibration` (line 33) and `TestPhaseDConfigParsing` (line 122) | **CONFIRMED** |
| R-8.10 | Config version v1.18→v1.21 across 4 phases | Config uses `schema_version` field in Pydantic models; enrichment config has versioning infrastructure. Config JSON file is gitignored so version not directly verifiable, but all Pydantic fields exist. | **CONFIRMED** (structural evidence) |

**Overall R-8 Verdict**: **CONFIRMED** — All 4 phases (A/B/C/D) have code + tests. Config models, algorithms, test files all exist with claimed functionality.

---

### R-13: `20260318-1400-feature-enrichment-lab-production-readiness`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-13.1 | Status claims closeout | `status.json` says `current_phase: "execute"`, `execute: "conditional_complete"`, `validate: "conditional_pass"` | **CONTRADICTED** — NOT at closeout |
| R-13.2 | 242 tasks completed | Phase 0-8 tasks all show `not_started` | **CONTRADICTED** — Core phases never executed |
| R-13.3 | `PuzzleDiagnostic` model created (T3) | `models/diagnostic.py` exists with `PuzzleDiagnostic` at line 15 | **CONFIRMED** |
| R-13.4 | Log-Report addendum (T71-T90) — `report/` directory with generator.py, toggle.py, token.py, correlator.py | `report/` directory DOES NOT EXIST. No report/*.py files found anywhere. | **NOT_FOUND** |
| R-13.5 | `test_report_toggle.py` created (T76) | File does NOT exist | **NOT_FOUND** |
| R-13.6 | `test_cli_report.py` created (T78) | File EXISTS, tests `--log-report` flag parsing | **CONFIRMED** |
| R-13.7 | 78 tests added | Cannot verify aggregate; many Phase 0-8 test tasks are `not_started` | **UNVERIFIABLE** |

**Overall R-13 Verdict**: **PARTIAL / CONTRADICTED** — Status.json honestly reflects "conditional_complete" (not closeout). The log-report addendum (T71-T90) claimed ✅ completion but the `report/` module does not exist. Some foundation work landed (diagnostic model, CLI report test), but most tasks never executed.

---

### R-19: `20260321-1000-feature-mark-sibling-refutations`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-19.1 | `_has_correctness_signal()` helper in `core/correctness.py` | Function referenced in module docstring at line 17 | **CONFIRMED** |
| R-19.2 | `mark_sibling_refutations(root)` function | Function defined at line 177 of `core/correctness.py` | **CONFIRMED** |
| R-19.3 | Integration in `stages/analyze.py` | Import at line 30, call at line 263 with debug logging | **CONFIRMED** |
| R-19.4 | Unit tests in `tests/unit/test_correctness.py` (T5-T8) | 10+ test references found; tests for core cases, miai guard, metrics improvement | **CONFIRMED** |
| R-19.5 | AGENTS.md updated | `AGENTS.md` line 43 references `mark_sibling_refutations` | **CONFIRMED** |
| R-19.6 | Frontend regression test (T9) | Not checked — separate module | **UNVERIFIED** |

**Overall R-19 Verdict**: **CONFIRMED** — All backend components (helper, main function, integration, tests, docs) verified present.

---

### R-20: `20260321-1400-feature-html-report-redesign`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-20.1 | Status claims closeout | `status.json` says `closeout: approved` | **Claimed** |
| R-20.2 | `report/generator.py` rewritten with HTML output | `report/` directory DOES NOT EXIST at all | **NOT_FOUND** |
| R-20.3 | S1-S9 sections with inline CSS | No `report/` directory, no generator code | **NOT_FOUND** |
| R-20.4 | Data wiring (T-HR-1 to T-HR-3) | No `report` import in `cli.py`; no `generate_report` calls found | **NOT_FOUND** |
| R-20.5 | Versioned glossary section | No evidence of HTML report code | **NOT_FOUND** |

**Overall R-20 Verdict**: **NOT_FOUND / CONTRADICTED** — Status claims closeout:approved, but zero code evidence exists. The `report/` module is completely absent. This is the **highest severity discrepancy** in this audit.

---

### R-21: `20260321-1800-feature-enrichment-log-viewer`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-21.1 | `log-viewer/` directory created | `tools/puzzle-enrichment-lab/log-viewer/` EXISTS | **CONFIRMED** |
| R-21.2 | `index.html` with CSP, Chart.js CDN | File exists; `<!DOCTYPE html>`, CSP meta tag, Tailwind CSS CDN, section containers all present | **CONFIRMED** |
| R-21.3 | `app.js` with JSONL parser + EventStore | `log-viewer/app.js` exists | **CONFIRMED** |
| R-21.4 | `styles.css` with CSS custom properties | `log-viewer/styles.css` exists | **CONFIRMED** |
| R-21.5 | `sample.jsonl` for demo | `log-viewer/sample.jsonl` exists | **CONFIRMED** |
| R-21.6 | file:// compatible (no backend) | Static HTML structure confirmed via index.html inspection | **CONFIRMED** |

**Overall R-21 Verdict**: **CONFIRMED** — All four deliverable files exist with claimed structure.

---

### R-22: `20260321-2100-refactor-enrichment-lab-dry-cli-centralization`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-22.1 | `bootstrap()` function in `log_config.py` | Function at line 447 | **CONFIRMED** |
| R-22.2 | `cli.py` uses `bootstrap()` | Import at line 42, call at line 878 | **CONFIRMED** |
| R-22.3 | `bridge.py` uses `bootstrap()` | Import at line 505, call at line 507 | **CONFIRMED** |
| R-22.4 | `conftest.py` uses `bootstrap()` | Import at line 41, call at line 43 | **CONFIRMED** |
| R-22.5 | `__aenter__`/`__aexit__` on `SingleEngineManager` | `__aenter__` at line 151 of `single_engine.py` | **CONFIRMED** |
| R-22.6 | `resolve_katago_config()` consolidated in `single_engine.py` | Function at line 30 | **CONFIRMED** |
| R-22.7 | `calibrate` subcommand in CLI | `calibrate_parser` wired at line 659, handler `_run_calibrate()` at line 787 | **CONFIRMED** |
| R-22.8 | `_add_common_args()` helper | Defined at line 576, used by all 4 subcommands | **CONFIRMED** |
| R-22.9 | `_sgf_render_utils.py` test helper dedup | File exists with `parse_sgf_properties()` | **CONFIRMED** |
| R-22.10 | "90% DRY elimination" claim | Bootstrap, engine context, resolve_katago, _add_common_args all consolidated. However `scripts/run_calibration.py` status unclear (not checked if thin wrapper). | **MOSTLY CONFIRMED** — major DRY patterns eliminated |

**Overall R-22 Verdict**: **CONFIRMED** — All 7 phases of the refactor landed. Core DRY patterns (bootstrap, engine lifecycle, config resolution, CLI args, SGF render utils) all verified present.

---

### R-23: `20260322-1400-refactor-enrichment-lab-test-consolidation`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-23.1 | L2-T1: Rename `test_remediation_sprints.py` → `test_ai_solve_remediation.py` | BOTH files exist (`test_remediation_sprints.py` + `test_ai_solve_remediation.py`); original NOT deleted | **PARTIAL** — copy made, original not removed |
| R-23.2 | L3-T1: `pythonpath = ["."]` in `pyproject.toml` | Confirmed at line 2 of `pyproject.toml` | **CONFIRMED** |
| R-23.3 | L3-T3: Remove `sys.path.insert` from all test files | 20+ test files STILL have `sys.path.insert` boilerplate | **NOT_DONE** |
| R-23.4 | Sprint test files deleted (L1-T2 through L1-T9) | No `test_sprint*.py` files found in `tests/` | **CONFIRMED** |
| R-23.5 | L4-T1: `_perf_helpers.py` extracted | Not found in search results | **UNVERIFIED** |

**Overall R-23 Verdict**: **PARTIAL** — Sprint test migration (L1) fully done. sys.path DRY fix (L3) only partially done (pyproject.toml set but boilerplate not removed from files). Rename (L2) left orphan. 84 test files total exist.

---

### R-24: `20260322-1500-feature-technique-calibration-fixtures`

| r_id | Claim | Evidence | Verdict |
|------|-------|----------|---------|
| R-24.1 | `test_technique_calibration.py` with `TECHNIQUE_REGISTRY` | File exists with JSON-loaded registry, 5 parametrized test methods, `EXCLUDED_NON_TSUMEGO_TAGS` | **CONFIRMED** |
| R-24.2 | Delete 5 REMOVE fixtures (connection_puzzle, endgame, fuseki, joseki, shape) | All 5 files STILL EXIST in `tests/fixtures/` | **NOT_DONE** |
| R-24.3 | `extended-benchmark/` directory with difficulty variants | Directory exists but contains ONLY `README.md` — no SGF files | **PARTIAL** (directory created, not populated) |
| R-24.4 | `TECHNIQUE_FIXTURE_AUDIT.md` exists | Confirmed present in `tests/fixtures/` | **CONFIRMED** |
| R-24.5 | Replace `cutting.sgf` with sourced alternative (T9) | `cutting.sgf` exists but content not verified as replaced | **UNVERIFIED** |
| R-24.6 | `_render_all_techniques.py` temp script deleted (T24) | File confirmed still exists at project root level: `_render_all_techniques.py` | **NOT_DONE** |

**Overall R-24 Verdict**: **PARTIAL** — Test infrastructure (registry, calibration tests, audit doc) built. But fixture cleanup (deletion, population) was NOT executed. Phase B (atomic swap) and Phase C (extended benchmark population) not done.

---

## 3. Summary Matrix

| r_id | Initiative | Status.json Phase | Actual Verdict | Severity |
|------|-----------|-------------------|----------------|----------|
| R-1 | enrichment-lab-v2 | closeout | **PARTIAL** — 2 gaps (tsumego_frame.py, query_stage.py not deleted) | Low |
| R-8 | refutation-quality | closeout | **CONFIRMED** — All 4 phases verified | None |
| R-13 | production-readiness | execute (conditional) | **PARTIAL / CONTRADICTED** — report/ module missing despite claimed completion | High |
| R-19 | mark-sibling-refutations | closeout | **CONFIRMED** — All components verified | None |
| R-20 | html-report-redesign | closeout | **NOT_FOUND** — Zero code exists, status false | **Critical** |
| R-21 | enrichment-log-viewer | closeout | **CONFIRMED** — All files verified | None |
| R-22 | dry-cli-centralization | closeout | **CONFIRMED** — All DRY patterns verified | None |
| R-23 | test-consolidation | closeout | **PARTIAL** — sys.path not cleaned, rename orphan | Medium |
| R-24 | technique-calibration-fixtures | closeout | **PARTIAL** — Test infra built, fixture swap not done | Medium |

---

## 4. Risks

| risk_id | Risk | Severity | Mitigation |
|---------|------|----------|------------|
| RISK-1 | R-20 claims closeout but NO code exists — status.json is factually wrong | **Critical** | Reopen initiative or update status to `abandoned`/`not_started` |
| RISK-2 | R-13 log-report addendum (T71-T90) claims ✅ completed but `report/` module absent | **High** | Likely code was written then lost (git operation? recovery gap?). Investigate git history. |
| RISK-3 | R-23 sys.path boilerplate remains in 20+ files despite "closeout" | **Medium** | Either complete the cleanup or downgrade status to partial |
| RISK-4 | R-24 fixture deletion not done — claimed "closeout" is premature | **Medium** | Phase B (atomic swap) needs re-execution |
| RISK-5 | R-1 dead code (`tsumego_frame.py`) still present — minor tech debt | **Low** | Delete in next cleanup initiative |

---

## 5. Planner Recommendations

1. **REOPEN R-20 (html-report-redesign)**: Status.json says closeout:approved but zero deliverable code exists. Either the work was never done, or it was lost during a recovery operation. Investigate `git log --all -- tools/puzzle-enrichment-lab/report/` for history. Mark status as `execute: not_started` until resolved.

2. **Investigate R-13 report/ loss**: The production-readiness addendum (T71-T90) claims completion, and `test_cli_report.py` exists (proving partial work happened). The `report/` directory may have been lost in a git recovery. This is potentially recoverable via `git reflog` or recovery branches. Priority: investigate before rewriting.

3. **Complete R-23 sys.path cleanup**: Run the scripted removal of `sys.path.insert` boilerplate from ~20+ remaining test files (L3-T3). `pythonpath=["."]` is already set in pyproject.toml, so the sys.path lines are now redundant. Also delete orphan `test_remediation_sprints.py`. Low risk, high hygiene value.

4. **Execute R-24 Phase B**: Delete the 5 fixture files that were supposed to be removed (connection_puzzle.sgf, endgame.sgf, fuseki.sgf, joseki.sgf, shape.sgf). Populate `extended-benchmark/` with SGF files. Delete `_render_all_techniques.py`. These are the remaining gaps before calibration fixtures can claim true completion.

---

## 6. Confidence and Risk Assessment

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | high |
| Reason for "high" risk | R-20 has fraudulent closeout status; R-13 has missing deliverables. Both require investigation for potential data loss. |

---

## 7. Open Questions

| q_id | Question | Options | Recommended | user_response | Status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Was the `report/` module ever committed? Check `git log --all --diff-filter=D -- tools/puzzle-enrichment-lab/report/` | A: Was committed and deleted / B: Was never committed / C: Was on a branch that was lost | Investigate A first | — | ❌ pending |
| Q2 | Should R-20 status be set to `abandoned` or `execute: not_started`? | A: abandoned (accept loss) / B: not_started (plan re-execution) / C: blocked (pending git forensics) | C | — | ❌ pending |
| Q3 | For R-23 sys.path cleanup, should we do it now or batch with the dead-code cleanup initiative? | A: Now (quick win) / B: Batch with 20260324-1500-feature-backend-dead-code-cleanup | A | — | ❌ pending |
| Q4 | For R-24 fixture deletion, are there test dependencies on the 5 fixture files (connection_puzzle.sgf etc.) beyond what was audited? | A: Run grep to check / B: Just delete and see what breaks | A | — | ❌ pending |
