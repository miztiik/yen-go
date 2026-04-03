# Charter: Backend Test Remediation

## Context

Full backend test suite run: **2502 tests, 91 failures, 2375 passing, 36 skipped**.  
Failures cluster into 7 root-cause categories indicating code-test drift, not systemic code breakage.

## Goals

1. Bring backend test suite to 0 failures  
2. Delete stale/obsolete tests that test removed APIs  
3. Update tests that test valid behavior but use outdated assertions  
4. Consolidate redundant test coverage  
5. Document decision log for each verdict (delete/update/fix)

## Non-Goals

- Refactoring production code to match old test expectations  
- Adding new test coverage beyond what exists  
- Changing production behavior to satisfy obsolete tests  

## Constraints

- No production code changes (tests-only remediation) unless analysis shows a genuine production bug  
- Must not reduce effective coverage — only remove tests for removed APIs  
- Follow correction-level rules (each cluster assessed independently)  

## Success Criteria

- `pytest backend/ --no-header --tb=short` → 0 failures  
- No tests deleted that cover live production APIs  
- Decision log in this initiative for every deleted/modified test  

_Last updated: 2026-03-24_
