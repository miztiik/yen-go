# Governance Decisions — Enrichment Lab DRY / CLI Centralization

> Last Updated: 2026-03-21  
> Initiative: 20260321-2100-refactor-enrichment-lab-dry-cli-centralization

---

## Gate 1: Charter Review

| Field | Value |
|-------|-------|
| Decision | `approve_with_conditions` |
| Status Code | `GOV-CHARTER-CONDITIONAL` |
| Date | 2026-03-21 |
| Vote | 7 approve, 1 concern (GV-5) |

### Required Changes (Resolved)
| RC | Description | Status |
|----|-------------|--------|
| RC-1 | Update `status.json` scores post-research (65→88, medium→low) | ✅ resolved |
| RC-2 | Correct charter "15 scripts" → "13 in-scope scripts" | ✅ resolved |

---

## Gate 2: Options Election

| Field | Value |
|-------|-------|
| Decision | `approve` |
| Status Code | `GOV-OPTIONS-APPROVED` |
| Date | 2026-03-21 |
| Vote | 8/8 unanimous approve |
| Selected Option | OPT-3: Hybrid Bootstrap + Targeted CLI Absorption |

### Must-Hold Constraints (from panel)
| MH | Constraint | Source | Task Mapping |
|----|-----------|--------|-------------|
| MH-1 | Phase 6 `calibrate` subcommand must preserve exact engine restart cadence | GV-3, GV-7 | T6.x |
| MH-2 | `clear_cache()` must invalidate `_model_paths` lru_cache | GV-5 | T4.x |
| MH-3 | `calibrate` subcommand flags must align with `enrich/batch` naming | GV-8 | T6.x |

### Member Support Table
| GV-ID | Member | Domain | Vote | Key Comment |
|-------|--------|--------|------|-------------|
| GV-1 | Cho Chikun (9p) | Classical tsumego | approve | No domain-level risk; enrichment output invariant |
| GV-2 | Lee Sedol (9p) | Intuitive fighter | approve | OPT-3 finds creative middle ground |
| GV-3 | Shin Jinseo (9p) | AI-era professional | approve | Engine restart cadence must be preserved (MH-1) |
| GV-4 | Ke Jie (9p) | Strategic thinker | approve | Calibration under CLI improves difficulty ranking process |
| GV-5 | PSE-A | Systems architect | approve | Architecturally sound; cache coherence required (MH-2) |
| GV-6 | PSE-B | Data pipeline | approve | Observability improvement from unified logging |
| GV-7 | Hana Park (1p) | Player experience | approve | Zero player-facing risk; phased gating is strong safety net |
| GV-8 | Mika Chen | DevTools UX | approve | Flag naming consistency required (MH-3) |

---

## Gate 3: Plan Review

| Field | Value |
|-------|-------|
| Decision | `approve_with_conditions` |
| Status Code | `GOV-PLAN-CONDITIONAL` |
| Date | 2026-03-21 |
| Vote | 7 approve, 1 concern (GV-5) |

### Required Changes (Resolved)
| RC | Description | Status |
|----|-------------|--------|
| RC-1 | Align charter AC5 with plan AD-5 (regex dedup approach) | ✅ resolved — charter AC5 updated |

### Key Panel Feedback
- GV-5 concern: Charter AC5 vs plan AD-5 deviation on regex SGF parsing → resolved by updating AC5
- GV-3/GV-7: Engine restart cadence (MH-1) properly mapped to T6.4
- GV-5: Cache coherence (MH-2) properly mapped to T4.2
- GV-8: Flag naming (MH-3) properly mapped to T6.6
- All 7 phases have regression test gates
- Planning confidence 88 ≥ 80 threshold

> **See also:**
> - [Charter](./00-charter.md)
> - [Options](./25-options.md)
> - [Plan](./30-plan.md) _(pending)_

---

## Gate 4: Implementation Review

| Field | Value |
|-------|-------|
| Decision | `approve` |
| Status Code | `GOV-IMPL-APPROVED` |
| Date | 2026-03-22 |
| Vote | Self-review (executor) |

### Scope Verification

| GV-R1 | Check | Result | Status |
|--------|-------|--------|--------|
| GV-R1a | All 7 phases complete | Phases 1-7 executed, all tasks T1.1-T7.1 done | ✅ |
| GV-R1b | 13 files modified (12 existing + 1 new) | Matches plan scope exactly | ✅ |
| GV-R1c | probe_frame.py untouched | Not in modified file list | ✅ |
| GV-R1d | No new external dependencies | Only stdlib imports used (functools.lru_cache, module __getattr__) | ✅ |
| GV-R1e | Zero compile/lint errors across all files | `get_errors` returns clean on all 13 files | ✅ |
| GV-R1f | AGENTS.md updated in execution | Phase 7 task T7.1 completed | ✅ |

### Must-Hold Constraint Verification

| GV-R2 | Constraint | Verified | Evidence |
|--------|-----------|----------|----------|
| GV-R2a | MH-1: restart cadence | ✅ | `_run_calibrate()` implements restart loop with `--restart-cadence` arg |
| GV-R2b | MH-2: cache coherence | ✅ | `clear_cache()` calls `_get_cfg.cache_clear()` + pops TEST_* globals |
| GV-R2c | MH-3: flag naming | ✅ | `_add_common_args()` shares --katago, --katago-config, --config, --quick-only, --visits, --symmetries across enrich/validate/batch/calibrate |

### Test Results

| GV-R3 | Metric | Value |
|--------|--------|-------|
| GV-R3a | Total tests run | 2385 (full suite) |
| GV-R3b | Passed | 2351 |
| GV-R3c | Failed | 31 (all pre-existing) |
| GV-R3d | New failures introduced | **0** |
| GV-R3e | Modified files with errors | 0 / 13 |

### Dead Code Cleanup (Bonus)

Identified and removed `_setup_logging()` in cli.py — dead after bootstrap adoption. Import cleaned.

---

## Gate 5: Closeout Audit

| Field | Value |
|-------|-------|
| Decision | `approve` |
| Status Code | `GOV-CLOSEOUT-APPROVED` |
| Date | 2026-03-22 |

### Artifact Completeness

| GV-C1 | Artifact | Updated | Evidence |
|--------|----------|---------|----------|
| GV-C1a | 50-execution-log.md | ✅ | Full per-phase log with task IDs |
| GV-C1b | 60-validation-report.md | ✅ | Created with test results, scope checks, ripple effects |
| GV-C1c | 70-governance-decisions.md | ✅ | Appended Gate 4 + Gate 5 |
| GV-C1d | status.json | ✅ | Updated to validate=approved |

### Documentation Quality

| GV-C2 | Check | Status |
|--------|-------|--------|
| GV-C2a | AGENTS.md reflects all structural changes | ✅ (cli.py, log_config.py, _model_paths.py, single_engine.py, tests/ sections updated) |
| GV-C2b | No stale cross-references | ✅ (all imports resolve, no broken references) |
| GV-C2c | Execution log has row IDs | ✅ (EX-1 through EX-10) |
