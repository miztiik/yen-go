# Documentation Artifact Contract

Last Updated: 2026-03-08

Defines the minimum documentation contract for initiatives so that documentation quality is governed like code quality.

## Purpose

This contract ensures every initiative records:

- why decisions were made,
- where canonical docs were updated,
- how readers navigate related docs.

## Core Principles

1. Why in docs, how in code.
2. Update existing global docs first.
3. Create new docs only when no canonical destination exists.
4. Cross-reference all related docs to preserve navigability.

## Required Planning Fields

`30-plan.md` MUST include a `## Documentation Plan` section with:

- `files_to_update`: list of existing docs that will be updated.
- `files_to_create`: list of new docs (must include rationale for why new file is needed).
- `why_updated`: one-line reason per file that captures design rationale.
- `cross_references`: links to architecture/how-to/concepts/reference docs.

Example:

```markdown
## Documentation Plan

- files_to_update:
  - docs/architecture/backend/pipeline.md
  - docs/reference/enrichment-config.md
- files_to_create:
  - docs/concepts/example-topic.md (new canonical topic not covered elsewhere)
- why_updated:
  - docs/architecture/backend/pipeline.md: explain why stage boundary changed
  - docs/reference/enrichment-config.md: document new config constraints
- cross_references:
  - docs/how-to/backend/run-pipeline.md
  - docs/concepts/quality.md
```

## Required Task Mapping

`40-tasks.md` MUST contain explicit documentation tasks that map 1:1 to Documentation Plan items.

Example:

```markdown
- T12 Update docs/architecture/backend/pipeline.md (why + cross-refs)
- T13 Update docs/reference/enrichment-config.md
- T14 Add docs/concepts/example-topic.md
```

## Required Governance Fields

`70-governance-decisions.md` (plan gate output) MUST include:

```yaml
docs_plan_verification:
  present: true
  coverage: complete
  notes: "All code-impacting changes have matching doc updates"
```

If `present=false` or `coverage!=complete`, plan gate must return `change_requested`.

## Required Validation Evidence

`60-validation-report.md` MUST include a docs verification table:

`| doc_id | file | why_recorded | cross_refs_checked | status |`

Status values:

- `✅ verified`
- `❌ missing`

Any `❌ missing` row is a closeout blocker unless explicitly deferred with owner and follow-up task.

## Closeout Checklist

Before final closeout approval:

1. All planned docs were updated/created.
2. Each updated doc contains rationale aligned with the initiative changes.
3. Existing global docs were preferred over new doc creation where possible.
4. Cross-references are present and valid.
5. `Last Updated` dates were refreshed.

## Governance Enforcement

- `charter`: check documentation intent exists for non-trivial changes.
- `plan`: enforce `Documentation Plan` completeness and mapping to tasks.
- `review`: verify docs were actually updated and evidence is present.
- `closeout`: verify rationale quality and cross-reference integrity.

## Fast-Track Exception

Fast-track initiatives still require documentation updates when behavior, contracts, or operations change.
Fast-track only reduces panel size; it does not waive documentation obligations.

> **See also**:
>
> - [Reference: Planning Artifact Contract](./planning-artifact-contract.md) - Full initiative artifact lifecycle
> - [Reference: copilot-instructions](../../.github/copilot-instructions.md) - Repository-wide doc rules
> - [Architecture: System Overview](../architecture/system-overview.md) - Global architecture context
