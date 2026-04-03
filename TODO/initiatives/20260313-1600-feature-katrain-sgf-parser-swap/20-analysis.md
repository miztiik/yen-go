# Analysis — KaTrain SGF Parser Swap (OPT-1)

**Initiative**: `20260313-1600-feature-katrain-sgf-parser-swap`
**Last Updated**: 2026-03-13

---

## Planning Confidence

| Metric | Value |
|--------|-------|
| Pre-research score | 45 |
| Post-research score | 82 |
| Post-plan score | 85 |
| Risk level | medium |
| Research invoked | yes (mandatory trigger: score < 70, risk medium) |

---

## 1. Cross-Artifact Consistency

| finding_id | severity | finding | resolution |
|------------|----------|---------|------------|
| F1 | low | Charter AC-3 says `core/sgf_parser.py` but plan A.2 describes it as `core/katrain_sgf_parser.py` style naming | AC-3 is correct for lab (`core/sgf_parser.py`). Backend uses `core/katrain_sgf_parser.py` (AC-4). Naming is consistent. |
| F2 | info | Charter scope says ~14 lab files but task list has T1-T17 (17 tasks) including test/doc/delete tasks | Task count includes operational tasks (test runs, deletes, docs). File-level scope is ~14 as stated. Consistent. |
| F3 | low | Options RC-2 integration proof covers 13 API calls but research §3 says "7 sgfmill call sites in enricher" | 7 unique call sites, but some are used multiple times (e.g., `from_bytes` appears twice at lines 235, 534). 13 total references. Both counts are correct for their context. |
| F4 | info | Plan says `compose_enriched_sgf()` is "Replaced" but tasks show it moving to tsumego_analysis.py | The function's implementation changes from string composition to `SGFNode` tree mutation + `sgf()`, but the logical capability (add refutation branches and serialize) remains. Tasks accurately describe the new implementation approach. |
| F5 | medium | Task T3 imports `Position`, `Stone`, `Color` from `models.position` but Q4 says "adopt KaTrain types fully" | `Position` model serves a KataGo integration purpose (not SGF parsing). `Stone`/`Color` are Pydantic models used across the lab. The wrapper converts FROM KaTrain → lab models at the boundary. This is the adapter layer, not a Q4 violation. KaTrain types are canonical for parsing; lab models are canonical for KataGo analysis. |

---

## 2. Coverage Map

| charter_goal | plan_section | task_ids | covered? |
|--------------|-------------|----------|----------|
| Replace sgfmill in lab | Phase A | T2, T7, T15, T16 | ✅ |
| Replace hand-rolled parser in backend | Phase B | T18, T19 | ✅ |
| Adopt KaTrain types | Phase A (consumers) | T4-T14 | ✅ |
| Remove sgfmill from requirements | Phase A.5 | T16 | ✅ |
| Maintain independence | Both phases | T2 (lab copy), T18 (backend copy) | ✅ |
| Tsumego wrapper separation | Phase A.2 | T3 | ✅ |
| Tests pass | Both phases | T17, T20 | ✅ |
| Documentation | Phase C | T21, T22, T23 | ✅ |

| acceptance_criterion | task_ids | verified_by |
|---------------------|----------|-------------|
| AC-1 (sgfmill removed from requirements) | T16 | File inspection |
| AC-2 (no sgfmill imports) | T7, T15,T16 | grep --include="*.py" |
| AC-3 (KaTrain parser in lab core) | T2 | File exists |
| AC-4 (KaTrain parser in backend core) | T18 | File exists |
| AC-5 (lab tests pass) | T17 | pytest output |
| AC-6 (backend tests pass) | T20 | pytest output |
| AC-7 (old lab parser deleted) | T15 | File absent |
| AC-8 (backend sgf_parser rewritten) | T19 | Code inspection |
| AC-9 (sgf_enricher sgfmill-free) | T7 | grep output |
| AC-10 (tsumego wrapper in separate file) | T3 | File exists |

---

## 3. Unmapped Tasks

None. All tasks trace to charter goals and acceptance criteria.

---

## 4. Ripple-Effects Table

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|-----------|------------|--------|
| R-1 | downstream | Lab `Position` model — 6+ files use stones from `extract_position()` | Low | `extract_position()` wrapper converts KaTrain `Move` → lab `Stone` at boundary. No downstream type change. | T3 | ✅ addressed |
| R-2 | downstream | Lab `compose_enriched_sgf()` callers — `sgf_enricher.py` line ~406 | Medium | Rewrite to use `SGFNode` tree mutation + `root.sgf()`. Same logical output. | T7 | ✅ addressed |
| R-3 | lateral | Lab test fixtures — tests create `SgfNode` directly | Medium | Update test factory methods to create `SGFNode` instead. | T14 | ✅ addressed |
| R-4 | downstream | Backend `SGFGame` consumers (15+ files) | None | Facade preserved. No consumer changes. | T19 | ✅ addressed |
| R-5 | downstream | Backend `parse_root_properties_only()` consumers (`inventory/reconcile.py`) | None | Function preserved as-is. No change. | T19 | ✅ addressed |
| R-6 | upstream | `tools/core/sgf_correctness.py` — imported by tsumego wrapper | None | Import mechanism unchanged (importlib.util spec loading). Module stays as-is. | T3 | ✅ addressed |
| R-7 | lateral | `tools/core/sgf_parser.py` — existing standalone parser | None | Non-goal. Not touched. Stays as-is. | — | ✅ addressed |
| R-8 | lateral | Frontend SGF handling | None | Non-goal. Out of scope. No SGF parsing in frontend (uses pre-built views). | — | ✅ addressed |
| R-9 | downstream | KaTrain `SGFNode.sgf()` output format vs sgfmill `serialise()` | Low | Both produce valid SGF. Whitespace/ordering may differ. Content correctness verified by test suite. | T17 | ✅ addressed |
| R-10 | lateral | CI/CD pipeline | Low | `requirements.txt` change may affect CI install step. Verify CI does `pip install -r requirements.txt` for lab. | T16 | ✅ addressed |

---

## 5. Severity Summary

| Severity | Count | Items |
|----------|-------|-------|
| Critical | 0 | — |
| High | 0 | — (`.move` type change is pervasive but mechanically caught by tests) |
| Medium | 2 | F5 (Position model boundary), R-2 (compose_enriched_sgf rewrite) |
| Low | 3 | F1, R-1, R-9 |
| Info | 2 | F2, F4 |

---

## 6. TDD Strategy

| Phase | Test approach |
|-------|--------------|
| T2 (KaTrain copy) | Verify `SGF.parse_sgf()` produces valid tree for sample SGF fixtures |
| T3 (tsumego wrapper) | Run existing `test_enrich_single.py`, `test_solve_position.py` — these cover extract_position, extract_correct_first_move |
| T7 (sgf_enricher rewrite) | Run `test_sgf_enricher.py` — covers enrichment round-trip, teaching comments, patches |
| T14 (test updates) | Update test imports; verify existing assertions still hold |
| T17 (lab test suite) | Full `pytest tests/` — gate before Phase B |
| T19 (backend rewrite) | Run `pytest -m "not (cli or slow)"` — covers all backend consumers through facade |
| T20 (backend test suite) | Same as T19 — gate before documentation |

---

> **See also**:
> - [Charter](./00-charter.md) — Acceptance criteria
> - [Plan](./30-plan.md) — Architecture and risks
> - [Tasks](./40-tasks.md) — Dependency graph
> - [Research](./15-research.md) — Consumer blast radius and type mappings
