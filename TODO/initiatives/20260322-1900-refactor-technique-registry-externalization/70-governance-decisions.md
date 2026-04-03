# Governance Decisions — Externalize TECHNIQUE_REGISTRY

Last Updated: 2026-03-22

---

## Gate 1: Charter/Research Preflight

### Decision

| Field | Value |
|-------|-------|
| decision | approve |
| status_code | GOV-CHARTER-APPROVED |
| gate | charter |

### Member Reviews

| row_id | member | domain | vote | supporting_comment | evidence |
|--------|--------|--------|------|-------------------|----------|
| GV-1 | Software Architect | SOLID/Architecture | approve | Scope is well-bounded to one test file + data extraction. No architectural risk. Charter correctly excludes pipeline changes. C-6 (no backend imports) properly enforced. | In-scope files F-1 through F-4 are all within `tools/puzzle-enrichment-lab/`. |
| GV-2 | KataGo Engine Expert | Engine/Pipeline | approve | No engine behavior changes. Calibration data moves but assertions stay identical. The regen script (Q5:A) must use `enrich_single_puzzle()` — the same path integration tests use — preventing drift. | Parent initiative OPT-3 already validated the TechniqueSpec structure. |
| GV-3 | Go Domain Expert (1P) | Tsumego/Calibration | approve | Ground-truth values (correct moves, difficulty ranges, tag expectations) are domain-validated artifacts from the parent initiative. Externalizing preserves them. The regen script provides a path to re-derive when KataGo model or config changes. | 25 entries cover all active tsumego techniques. EXCLUDED_NON_TSUMEGO_TAGS={joseki,fuseki,endgame} remains unchanged. |
| GV-4 | Test Architecture Lead | Testing/Quality | approve | Tests are unchanged — only the data source changes. 3 unit tests + 5×25 parametrized tests provide strong regression coverage. Recommend: add one unit test that validates JSON structure on load (catches malformed JSON before test discovery). | Test file already has `test_all_tags_have_registry_entry()` which validates completeness. |

### Support Summary

4/4 approve. No blocking items. GV-4 recommends adding a JSON structural validation test — this is advisory, not blocking.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Refactor-Planner |
| message | Charter approved. Proceed to options. |
| required_next_actions | Generate options (minimum 2 meaningful proposals). |
| artifacts_to_update | 25-options.md, status.json |
| blocking_items | None |

---

## Gate 2: Options Election

### Decision

| Field | Value |
|-------|-------|
| decision | approve |
| status_code | GOV-OPTIONS-APPROVED |
| gate | options |

### Selected Option

| Field | Value |
|-------|-------|
| option_id | OPT-1 |
| title | JSON Data File + Thin Loader |
| selection_rationale | Achieves clean data/code separation (primary goal). JSON matches project conventions (`config/*.json`). KISS/YAGNI compliant. User explicitly selected JSON format (Q4:A). Regen script writes standard JSON. OPT-2 doesn't fully separate data from code. OPT-3 violates YAGNI with unnecessary schema machinery. |
| must_hold_constraints | (1) TechniqueSpec TypedDict remains in test file (C-1). (2) Loader must fail fast on malformed JSON. (3) Regen script must use `enrich_single_puzzle()` (same path as integration tests). (4) JSON metadata header must include version + last_updated. (5) AGENTS.md updated in same commit. |

### Member Reviews

| row_id | member | domain | vote | supporting_comment | evidence |
|--------|--------|--------|------|-------------------|----------|
| GV-5 | Software Architect | SOLID/Architecture | approve OPT-1 | Clean SRP: test file tests, JSON file holds data, script regenerates. No new dependencies. Loader is ~15 lines, fits in existing file. Recommend: loader should use `TechniqueSpec(**entry)` for structural validation at load time. | OPT-1 comparison matrix shows KISS ✅, YAGNI ✅ vs OPT-3 KISS ❌, YAGNI ❌. |
| GV-6 | KataGo Engine Expert | Engine/Pipeline | approve OPT-1 | Regen script using `enrich_single_puzzle()` ensures data stays pipeline-consistent. JSON `correct_move_gtp` is explicit — no derivation ambiguity. Must-hold #3 (same enrichment path) is critical. | OPT-2 regen would need to write Python source code, which is fragile. JSON serialization is standard. |
| GV-7 | Go Domain Expert (1P) | Tsumego/Calibration | approve OPT-1 | JSON is readable by non-developers reviewing calibration quality. `notes` field preserves provenance (puzzle sources, audit references). Human reviewers can examine expected values without Python knowledge. | OPT-2's Python-only access limits review audience. |
| GV-8 | Test Architecture Lead | Testing/Quality | approve OPT-1 | JSON format enables future CI validation (e.g., JSON linting). Loader with `TechniqueSpec(**v)` provides runtime TypedDict validation. Regen script should include `--dry-run` mode that shows diffs without writing. | OPT-1 migration path is straightforward: export → replace → verify. |

### Support Summary

4/4 approve OPT-1. Must-hold constraints:
1. TechniqueSpec TypedDict stays in test file (C-1)
2. Loader fails fast on malformed JSON
3. Regen script uses `enrich_single_puzzle()` (pipeline consistency)
4. JSON metadata: version + last_updated
5. AGENTS.md updated in same commit

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Refactor-Planner |
| message | OPT-1 (JSON Data File + Thin Loader) approved unanimously. Proceed to plan + tasks. |
| required_next_actions | Draft 30-plan.md and 40-tasks.md for OPT-1. Include regen script (Q5:A). Include AGENTS.md update. |
| artifacts_to_update | 30-plan.md, 40-tasks.md, 20-analysis.md, status.json |
| blocking_items | None |

---

## Gate 3: Plan Review

### Decision

| Field | Value |
|-------|-------|
| decision | approve |
| status_code | GOV-PLAN-APPROVED |
| gate | plan |

### Member Reviews

| row_id | member | domain | vote | supporting_comment | evidence |
|--------|--------|--------|------|-------------------|----------|
| GV-9 | Software Architect | SOLID/Architecture | approve | Plan correctly separates 4 file transformations. SOLID/DRY/KISS/YAGNI mapping is thorough. Rollback is trivial (single commit revert). The `_load_registry()` pattern with `TechniqueSpec(**entry)` provides runtime validation without adding dependencies. | AD-1 through AD-7 are all well-justified. No architectural concerns. |
| GV-10 | KataGo Engine Expert | Engine/Pipeline | approve | Regen script design (T6–T8) correctly uses `enrich_single_puzzle()` + `SingleEngineManager` in `quick_only` mode — identical to test suite. `--dry-run` mode is valuable for CI smoke testing. Must-hold #3 satisfied. | Task dependency graph correctly sequences T6 parallel with T3, both dependent on T1. |
| GV-11 | Go Domain Expert (1P) | Tsumego/Calibration | approve | 25 technique entries preserve all domain-validated ground truth from parent initiative. `notes` field preserves provenance (puzzle IDs, sources). JSON `expected_tags` as list (not set) preserves ordering for human readability. | Invariants INV-1 through INV-6 cover all calibration integrity checks. |
| GV-12 | Test Architecture Lead | Testing/Quality | approve | 11-task breakdown is appropriately granular. T5 and T11 are explicit regression gates before and after cleanup. Ripple-effects analysis (RE-1 through RE-9) is comprehensive — no unaddressed downstream impacts. Analysis finding F4 (JSON load test) is acceptable as advisory. | Coverage map: all 5 goals mapped to tasks. Zero unmapped tasks. |

### Support Summary

4/4 approve. No blocking items. Plan is execution-ready.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Plan approved. Execute T1–T11 per dependency graph. JSON file first, then parallel tracks (test refactor + regen script), converge at T9–T11. |
| required_next_actions | Execute tasks T1 through T11 per dependency order. Create feature branch before starting. |
| artifacts_to_update | 50-execution-log.md, status.json |
| blocking_items | None |

---

## Gate 4: Implementation Review

### Decision

| Field | Value |
|-------|-------|
| decision | approve_with_conditions |
| status_code | GOV-REVIEW-CONDITIONAL |
| gate | review |

### Member Reviews

| row_id | member | domain | vote | supporting_comment | evidence |
|--------|--------|--------|------|-------------------|----------|
| GV-13 | Software Architect | Architecture | approve | Clean SRP: JSON holds data, test file tests, script regenerates. Loader provides fail-fast via json.load. TechniqueSpec(**entry) catches key mismatches at import time. | All 5 must-hold constraints verified. |
| GV-14 | KataGo Engine Expert | Pipeline | approve | Regen script uses enrich_single_puzzle() via SingleEngineManager in quick_only mode — identical to test suite path. Must-hold #3 satisfied. | Task dependency graph correctly sequenced. |
| GV-15 | Go Domain Expert (1P) | Calibration | approve | 25 technique entries preserve all domain-validated ground truth. notes field preserves provenance. No domain knowledge lost. | JSON validates, all entries present. |
| GV-16 | Test Architecture Lead | Testing | approve | 11-task breakdown verified complete. 3/3 unit tests pass. JSON structural + load validation confirmed. | Coverage map complete. |

### Required Changes

| rc_id | severity | description | status |
|-------|----------|-------------|--------|
| RC-1 | major | Regen script write mode did not update technique values — only timestamp was written. | ✅ resolved — `_update_entry()` added to apply enriched values before serialization. |

### Support Summary

4/4 approve. RC-1 issued and resolved. Core refactor complete and correct.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Implementation approved after RC-1 fix. Proceed to closeout. |
| required_next_actions | Run closeout audit. |
| artifacts_to_update | status.json, 70-governance-decisions.md |
| blocking_items | None |

---

## Gate 5: Closeout Audit

### Decision

| Field | Value |
|-------|-------|
| decision | approve |
| status_code | GOV-CLOSEOUT-APPROVED |
| gate | closeout |

### Member Reviews

| row_id | member | domain | vote | supporting_comment | evidence |
|--------|--------|--------|------|-------------------|----------|
| GV-17 | Cho Chikun (9p) | Go domain authority | approve | 25 technique calibration entries preserved identically. Stability tiers intact. No domain knowledge lost. | JSON file validated, INV-1 through INV-6 verified. |
| GV-18 | Lee Sedol (9p) | Intuitive fighter | approve | `_update_entry()` correctly widens ranges rather than overwriting — respects KataGo non-determinism. | RC-1 fix uses floor/ceiling logic. |
| GV-19 | Shin Jinseo (9p) | AI-era professional | approve | Regen script uses enrich_single_puzzle() with quick_only — identical to test path. | Must-hold #3 satisfied. |
| GV-20 | Principal Staff Engineer A | Systems architect | approve | Clean SRP: JSON data, test file loads+tests, script regenerates. Rollback is trivial single-commit revert. | All 5 charter goals met. |
| GV-21 | Principal Staff Engineer B | Data pipeline | approve | Pipeline untouched (C-3). JSON serialization clean and reproducible. | INV-1 through INV-6 verified. |
| GV-22 | Hana Park (1p) | Player experience | approve | Zero player-facing impact. Calibration ground truth preserved identically. | 3/3 unit tests pass, INV-6 verified. |
| GV-23 | Mika Chen | DevTools UX | approve | Regen script provides good DX: --dry-run, per-technique diffs, clear errors. RC-1 fix prevents stale data. | Script validates prerequisites before proceeding. |
| GV-24 | Dr. David Wu | KataGo engine | approve | No engine config changes. quick_only mode preserved. | No changes to katago-enrichment.json or tsumego_analysis.cfg. |
| GV-25 | Dr. Shin Jinseo | Tsumego calibration | approve | All 25 entries preserved with identical values. EXCLUDED_NON_TSUMEGO_TAGS intact. | INV-1 through INV-6 all verified. |

### Support Summary

9/9 approve. Unanimous. All 4 prior governance gates passed. All 11 tasks + RC-1 complete. No unresolved concerns.

### Handover

| Field | Value |
|-------|-------|
| from_agent | Governance-Panel |
| to_agent | Plan-Executor |
| message | Closeout approved. Initiative complete. Can be archived. |
| required_next_actions | None — initiative is closed. |
| artifacts_to_update | None |
| blocking_items | None |
