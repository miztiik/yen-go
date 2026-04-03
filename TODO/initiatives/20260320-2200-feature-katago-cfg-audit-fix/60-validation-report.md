# Validation Report — KataGo .cfg Audit & Fix

**Initiative**: `20260320-2200-feature-katago-cfg-audit-fix`
**Date**: 2026-03-21

---

## Test Validation

### Config Tests (Direct)

| val_id | test_file | tests | result | evidence |
|--------|-----------|-------|--------|----------|
| VAL-1 | `test_tsumego_config.py` | 11 | ✅ 11 passed | `pytest tests/test_tsumego_config.py -q --tb=short` exit 0 |

### Enrichment Lab Regression

| val_id | scope | tests | result | evidence |
|--------|-------|-------|--------|----------|
| VAL-2 | Core enrichment (sgf_enricher, comment_assembler, teaching_comments, teaching_comment_embedding, tsumego_config) | 242 | ✅ 242 passed | exit code 0 |

### Backend Unit Regression

| val_id | scope | tests | result | evidence |
|--------|-------|-------|--------|----------|
| VAL-3 | `backend/ -m unit` | 1603 | ✅ 1603 passed, 430 deselected | exit code 0 |

---

## Acceptance Criteria Verification

| val_id | criterion | status | evidence |
|--------|-----------|--------|----------|
| VAL-4 | AC-1a: 4 unused keys removed from .cfg | ✅ | grep: `allowSelfAtari`, `analysisWideRootNoise`, `cpuctExplorationAtRoot`, `scoreUtilityFactor` → only in changelog comments |
| VAL-5 | AC-1b: Test verifies 4 removed keys are absent | ✅ | `test_removed_keys_absent` passes (11 passed) |
| VAL-6 | AC-2: Exploration params restored to defaults (cpuct=1.0, rootPolicyTemp=1.0) | ✅ | .cfg verified: `cpuctExploration = 1.0`, `rootPolicyTemperature = 1.0` |
| VAL-7 | AC-3: staticScoreUtilityFactor = 0.1 (uncommented + changed) | ✅ | .cfg line 151: `staticScoreUtilityFactor = 0.1`; test assertion passes |
| VAL-8 | AC-4: rootPolicyTemperatureEarly = 1.5 (OPT-B tesuji boost) | ✅ | .cfg: `rootPolicyTemperatureEarly = 1.5` |
| VAL-9 | AC-5: subtreeValueBiasFactor = 0.25 | ✅ | .cfg: `subtreeValueBiasFactor = 0.25` |
| VAL-10 | AC-6: Version header + changelog in .cfg | ✅ | Lines 1-20: `# Version: 2 (2026-03-20)` + full changelog |
| VAL-11 | AC-7: AGENTS.md updated | ✅ | Line 297: `.cfg v2 audit` bullet present |

---

## Ripple-Effects Validation

| impact_id | expected_effect | observed_effect | result | follow_up_task | status |
|-----------|-----------------|-----------------|--------|----------------|--------|
| RE-1 | Config tests still pass with changed assertions | 11/11 pass | ✅ match | — | ✅ verified |
| RE-2 | Enrichment pipeline tests unaffected by .cfg changes | 231 core tests pass | ✅ match | — | ✅ verified |
| RE-3 | Backend unit tests unaffected | 1603 pass | ✅ match | — | ✅ verified |
| RE-4 | No new KataGo warnings from removed keys | Keys only in comments | ✅ match | — | ✅ verified |

---

## Commands and Exit Codes

| cmd_id | command | exit_code | result |
|--------|---------|-----------|--------|
| CMD-1 | `pytest tests/test_tsumego_config.py -q --tb=short` | 0 | 11 passed |
| CMD-2 | `pytest tests/test_sgf_enricher.py ... tests/test_tsumego_config.py -q --tb=no` | 0 | 242 passed |
| CMD-3 | `pytest backend/ -m unit -q --no-header --tb=no` | 0 | 1603 passed |

---

Last Updated: 2026-03-21
