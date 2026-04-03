# Options

**Initiative**: `20260321-1400-feature-html-report-redesign`
**Date**: 2026-03-21

## Options Matrix

| field | OPT-1: Inline HTML String Builder | OPT-2: Jinja2 Template Engine |
|-------|-----------------------------------|-------------------------------|
| **Approach** | Python f-string/list-join building inline CSS+HTML. Same pattern as existing markdown generator. | Add Jinja2 dependency, separate `.html.j2` template files. |
| **Benefits** | Zero new dependencies. Self-contained, easy to test. All logic in one file. Matches existing pattern. | Cleaner separation of template vs logic. Easier to maintain complex layouts. |
| **Drawbacks** | HTML escaping must be manual. Complex layouts harder to read as Python strings. | New dependency (violates "buy don't build" only if needed). Template files add file count. Overkill for operator diagnostic. |
| **Risks** | R1: String concatenation bugs → mitigate with thorough tests | R2: Dependency bloat. Template caching complexity. |
| **Complexity** | Low — extends existing pattern | Medium — new dependency + template management |
| **Test impact** | Minimal — same test pattern (assert on output string) | Medium — need to test template rendering separately |
| **Rollback** | Revert single file | Revert file + remove dependency + remove templates |
| **Architecture compliance** | ✅ No new deps, KISS, YAGNI | ⚠️ Adds dependency for single-use case |
| **Recommendation** | ✅ **SELECTED** | ❌ Over-engineered for scope |

## Selection Rationale

**OPT-1** selected. The report is an operator diagnostic tool with a fixed schema (10 sections). The layout is predetermined and unlikely to change frequently. Python string building is the simplest approach that satisfies all constraints (C4: no external dependencies, KISS, YAGNI). XSS is not a concern since all data is internally generated (no user input).
