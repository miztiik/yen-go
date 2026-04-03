# Analysis — Enrichment Lab Consolidated Initiative

Last Updated: 2026-03-10

## Planning Confidence

| metric | value |
|--------|-------|
| Planning Confidence Score | 90 |
| Risk Level | low |
| Feature-Researcher invoked | Yes — tsumego-solver research + sgfmill replacement feasibility |
| Post-research adjustment | +10 (from 80) — verified KM code, perspective tasks, sgfmill complexity |

## Cross-Artifact Consistency

| finding_id | artifact_pair | finding | severity | resolution |
|------------|--------------|---------|----------|------------|
| F1 | charter AC16 ↔ plan doc paths | AC16 had wrong path — FIXED to `docs/how-to/tools/katago-enrichment-lab.md` | RESOLVED | ✅ Fixed in charter |
| F2 | tasks T40 ↔ charter NG1 | T40 reviews S5-G18 (calibration) but charter NG1 excludes calibration | LOW | T40 correctly records "Deferred" sign-off — no conflict. |
| F3 | plan Phase B ↔ tasks T9-T10 | Plan describes 2 functions in `benson_check.py`; tasks match exactly | OK | ✅ Consistent |
| F4 | plan Phase A doc stubs ↔ tasks T7 | Plan RC-1 lists 3 files for stubs; T7 matches exactly | OK | ✅ Consistent |
| F5 | plan Phase C review criteria ↔ tasks RC-2 | Plan defines 6-point checklist; tasks reproduce it | OK | ✅ Consistent |
| F6 | options MHC-1 through MHC-5 ↔ task dependencies | MHC-1: A before B ✓, MHC-2: B before C ✓, MHC-3: D droppable ✓, MHC-4: C reviews individual ✓, MHC-5: no YK ✓ | OK | ✅ All constraints respected |
| F7 | charter G7 (4 doc deliverables) ↔ tasks T45-T48 | G7 = 4 docs, tasks = 4 doc tasks + cross-ref + regression | OK | ✅ Consistent |
| F8 | charter AC18 ↔ tasks T41-T43 | AC18 says "replaced OR evaluated and kept", tasks include drop criterion | OK | ✅ Consistent |
| F9 | plan Benson API ↔ tasks T9/T11/T12 | `find_unconditionally_alive_groups()` returns set of groups; caller checks contest-group membership. T11 integration code filters by `puzzle_region`. T12 includes framework false-positive fixture. | OK | ✅ Consistent (fixed per GOV-PLAN-REVISE RC-1) |
| F10 | plan tsumego_frame API ↔ tasks T10 | T10 references `compute_regions(position, config).puzzle_region` — matches actual `tsumego_frame.py` API | OK | ✅ Consistent (fixed per GOV-PLAN-REVISE RC-2) |
| F11 | tasks T6 file scope ↔ plan | T6 targets include `sgf_enricher.py` L83 reference + grep pre-step | OK | ✅ Consistent (fixed per GOV-PLAN-REVISE RC-3/RC-4) |

## Severity Summary

| severity | count | items |
|----------|-------|-------|
| RESOLVED | 1 | F1 (charter path mismatch — fixed) |
| LOW | 1 | F2 (T40 deferral, no conflict) |
| OK | 9 | F3-F11 |

**No open blocking findings.**

| charter_item | tasks_covering | status |
|-------------|---------------|--------|
| G1 (Benson gate) | T9, T11, T12 | ✅ covered |
| G2 (Interior-point) | T10, T11, T13 | ✅ covered |
| G3 (Ko capture verification) | T4 | ✅ covered |
| G4 (5 perspective fixes) | T1, T2, T3, T5, T6 | ✅ covered |
| G5 (6 KM gate reviews) | T15-T20 | ✅ covered |
| G6 (20 remediation sign-offs) | T21-T40 | ✅ covered |
| G7 (4 doc deliverables) | T45-T48 | ✅ covered |
| G8 (Global doc updates) | T45-T49 | ✅ covered |
| G9 (Dead code removal) | T5, T6 | ✅ covered |
| G10 (sgfmill evaluation) | T41-T44 | ✅ covered |
| AC1-AC3 (Benson behavior) | T9, T12 | ✅ covered |
| AC4-AC5 (Interior-point behavior) | T10, T13 | ✅ covered |
| AC6 (Ko capture) | T4 | ✅ covered |
| AC7 (estimate_difficulty logging) | T1 | ✅ covered |
| AC8 (ko_validation logging) | T2 | ✅ covered |
| AC9 (conftest run_id) | T3 | ✅ covered |
| AC10 (ai_solve_active removal) | T5 | ✅ covered |
| AC11 (level_mismatch removal) | T6 | ✅ covered |
| AC12 (6 KM sign-offs) | T15-T20 | ✅ covered |
| AC13 (20 remediation sign-offs) | T21-T40 | ✅ covered |
| AC14 (quality.md) | T45 | ✅ covered |
| AC15 (architecture doc) | T46 | ✅ covered |
| AC16 (how-to doc) | T47 | ✅ covered (path corrected per F1) |
| AC17 (reference doc) | T48 | ✅ covered |
| AC18 (sgfmill) | T41-T43 | ✅ covered |
| AC19 (regression) | T8, T14, T44, T50 | ✅ covered (4 regression gates) |
| AC20 (new tests) | T12, T13 | ✅ covered |

**Unmapped tasks:** None. All 50 tasks trace to at least one AC.

## Ripple-Effects Analysis

| impact_id | direction | area | risk | mitigation | owner_task | status |
|-----------|-----------|------|------|-----------|------------|--------|
| RE-1 | downstream | solve_position.py callers | LOW | Benson gate returns same SolutionNode type — callers unaffected | T11 | ✅ addressed |
| RE-2 | upstream | tsumego_frame.py boundary | LOW | Read-only reuse — no changes to tsumego_frame | T10 | ✅ addressed |
| RE-3 | lateral | enrich_single.py flow | LOW | ai_solve_active removal is pure simplification — no behavior change | T5 | ✅ addressed |
| RE-4 | lateral | Pydantic config model | LOW | level_mismatch removal may need model field deletion — test config loading | T6 | ✅ addressed |
| RE-5 | downstream | test fixtures | MEDIUM | New Benson tests need Go board fixtures — create purpose-built ones, don't modify existing | T12, T13 | ✅ addressed |
| RE-6 | lateral | sgfmill imports | MEDIUM | Phase D replacement affects 2 files; regression gate T44 catches any breakage | T41-T44 | ✅ addressed |
| RE-7 | downstream | docs cross-references | LOW | 4 doc files must cross-reference each other — T49 verifies | T49 | ✅ addressed |
| RE-8 | lateral | ko_validation behavior | MEDIUM | T4 changes ko detection logic — existing ko tests may need updating | T4, T8 | ✅ addressed |
| RE-9 | upstream | config/katago-enrichment.json | LOW | Removing level_mismatch section — other tools may reference it | T6 | ❌ needs action |
| RE-10 | lateral | KM/remediation review findings | MEDIUM | Phase C reviews may uncover NEW gaps not in the current task list | T15-T40 | ✅ addressed (fix inline per RC-2 protocol) |

### RE-9 Investigation Required

Before executing T6, verify no other tool or module reads `level_mismatch` from `config/katago-enrichment.json`. The executor should run: `grep -r "level_mismatch" tools/ config/ backend/` and confirm zero external references.

## Constraint Compliance

| constraint | tasks enforcing | verified |
|-----------|----------------|----------|
| C1 (forward only) | All tasks — no backward compat logic | ✅ |
| C2 (no YK in Benson) | T9 — algorithm spec excludes YK | ✅ |
| C3 (seki falls through) | T9, T12 — seki test fixture required | ✅ |
| C4 (reuse tsumego_frame) | T10 — imports boundary from tsumego_frame | ✅ |
| C5 (no new external deps) | T9, T10 — pure Python | ✅ |
| C6 (individual reviews) | T15-T40 — each is separate task | ✅ |
| C7 (sgfmill conditional) | T41-T43 — drop criterion in T41 | ✅ |
| C8 (no calibration) | T40 — records deferral only | ✅ |
| C9 (no code copying from tsumego-solver) | T9, T10 — original implementation from algorithm papers | ✅ |


