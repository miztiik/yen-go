# Documentation Structure Reference

**Last Updated**: 2026-03-24

This document is the authoritative reference for how Yen-Go documentation is organized, where each kind of content belongs, and the non-negotiable rules every contributor and AI agent must follow.

> **See also**:
>
> - [Documentation Artifact Contract](./documentation-artifact-contract.md) — Initiative documentation governance
> - [Docs README](../README.md) — Navigation entry point

---

## Framework: Diataxis-Inspired Four-Tier System

Yen-Go documentation follows the [Diataxis](https://diataxis.fr/) framework, the same model used by Kubernetes, Django, and major open source projects. Every document belongs to **exactly one tier** based on what the reader needs when they open it.

| Tier              | Directory            | Reader Need              | Content Type                                          |
| ----------------- | -------------------- | ------------------------ | ----------------------------------------------------- |
| **Architecture**  | `docs/architecture/` | *Understanding* — why    | Design decisions, rationale, constraints, data flows  |
| **How-To**        | `docs/how-to/`       | *Doing* — step-by-step   | Guides, commands, walkthroughs for specific goals     |
| **Concepts**      | `docs/concepts/`     | *Learning* — shared knowledge | Cross-cutting topics: tags, levels, SGF, hints   |
| **Reference**     | `docs/reference/`    | *Looking up* — pure data | Config options, CLI tables, catalogs, quick-ref cards |

Two additional non-tier directories exist for entry points and historical records:

| Directory           | Purpose                                     |
| ------------------- | ------------------------------------------- |
| `docs/getting-started/` | Onboarding entry points (play, develop, operate) |
| `docs/archive/`     | Historical design docs, old research, retired specs |

---

## Placement Decision Flowchart

Use this flowchart to decide where a new document belongs:

```
Is this historical, retired, or superseded content?
  └─ YES → docs/archive/

Is this onboarding content for a first-time user?
  └─ YES → docs/getting-started/

Is the reader asking "WHY does this work this way?"
  └─ YES → docs/architecture/

Is the reader asking "HOW do I do X?" (step-by-step task)
  └─ YES → docs/how-to/

Is this a cross-cutting concept that multiple tiers reference?
  └─ YES → docs/concepts/

Is this pure lookup data (tables, config keys, CLI flags)?
  └─ YES → docs/reference/
```

### Side-by-Side Tier Examples

| Content | Wrong placement | Correct placement |
|---------|----------------|-------------------|
| Why we chose SQLite over JSON indexes | `docs/how-to/` | `docs/architecture/database-deployment-topology.md` |
| How to run the pipeline | `docs/architecture/` | `docs/how-to/backend/run-pipeline.md` |
| What the `YT` SGF property means | `docs/architecture/` | `docs/concepts/sgf-properties.md` |
| CLI flag table for `puzzle_manager` | `docs/architecture/` | `docs/reference/puzzle-manager-cli.md` |
| Playwright visual test walkthrough | `docs/how-to/` root | `docs/how-to/frontend/playwright-visual-testing.md` |
| Old design doc from Jan 2026 | `docs/architecture/` | `docs/archive/` |

---

## Directory Structure Rules

### Rule 1: Maximum 3-Level Depth

```
docs/
└── tier/              ← Level 1 (architecture, how-to, concepts, reference)
    └── subsystem/     ← Level 2 (backend, frontend, tools, sgf, adapters)
        └── file.md    ← Level 3 (the document)
```

**Valid:**
```
docs/how-to/frontend/playwright-visual-testing.md    ✅
docs/architecture/backend/sgf.md                     ✅
docs/concepts/sgf-properties.md                      ✅
```

**Forbidden:**
```
docs/how-to/backend/adapters/ogs/config.md           ❌  (4 levels)
docs/architecture/frontend/testing/vitest/unit.md    ❌  (5 levels)
```

### Rule 2: Subsystem Directories per Tier

| Tier | Allowed subsystem directories |
|------|-------------------------------|
| `architecture/` | `backend/`, `frontend/`, `tools/`, `backend/adapters/` |
| `how-to/` | `backend/`, `frontend/`, `tools/` |
| `concepts/` | No subdirectories (all flat) |
| `reference/` | `frontend/`, `adapters/`, `backend/` |
| `getting-started/` | No subdirectories (flat: `play.md`, `develop.md`, `operate.md`) |
| `archive/` | No subdirectories (flat) |

### Rule 3: Single Source of Truth

Each concept has **one canonical location**. Cross-references point to it; they do not duplicate it.

- ❌ Don't write the same tag definitions in both `docs/architecture/` and `docs/concepts/`
- ✅ Write them once in `docs/concepts/tags.md`, then link from everywhere else

---

## Required Document Elements

Every document must include:

### 1. Title (`# H1`)

One title at the top. No subtitle lines.

### 2. Last Updated Date

```markdown
**Last Updated**: YYYY-MM-DD
```

Place immediately after the title (or after the See Also callout if one exists).

### 3. See Also Callout (mandatory for architecture/how-to/concepts)

```markdown
> **See also**:
>
> - [Architecture: X](../architecture/x.md) — Why this was designed this way
> - [How-To: Y](../how-to/y.md) — Step-by-step guide
> - [Reference: Z](../reference/z.md) — Configuration options
```

Place immediately after the `# Title` line, before body content.

### 4. Content

Keep content in its tier. Do not put HOW-TO steps inside architecture docs or design rationale inside how-to guides.

---

## Naming Conventions

### Files

- Lowercase, hyphen-separated: `sgf-properties.md` not `SgfProperties.md`
- Verb-first for how-to guides: `run-pipeline.md`, `create-adapter.md`, `add-documentation.md`
- Noun-first for reference/concepts: `sgf-properties.md`, `puzzle-manager-cli.md`
- No date suffixes in canonical docs (dates belong in archive filenames)

### Directories

- Lowercase, hyphen-separated: `backend/`, `getting-started/`, `puzzle-enrichment-lab/`
- Tier name is singular: `architecture/`, not `architectures/`
- Subsystem name matches product area: `frontend/`, `backend/`, `tools/`

---

## Subsystem Scope Rules

### Backend content

Goes under `backend/` in both architecture and how-to:
- `docs/architecture/backend/` — pipeline design, adapter design, SGF schema
- `docs/how-to/backend/` — how to run pipeline, create adapters, do rollbacks

### Frontend content

Goes under `frontend/` in both architecture and how-to:
- `docs/architecture/frontend/` — state design, testing architecture, board integration
- `docs/how-to/frontend/` — local dev setup, build/deploy, visual testing guide

**Rule**: If a guide is for a frontend task (even if it touches Playwright/Vitest), it belongs under `docs/how-to/frontend/`, NOT at the `docs/how-to/` root.

### Cross-cutting content

Belongs in `docs/concepts/` — not under backend or frontend:
- SGF properties (`docs/concepts/sgf-properties.md`) — used by both pipeline and frontend
- Tags (`docs/concepts/tags.md`) — used by both pipeline and frontend
- Hints (`docs/concepts/hints.md`) — same

---

## What Goes in Archive

Move a document to `docs/archive/` when:

1. It has been **superseded** by a newer canonical doc
2. It is a **research/analysis document** that informed a decision (the decision now lives in architecture/)
3. It is a **historical spec or design narrative** from a past initiative
4. It references **retired systems or deprecated pipelines**

Archive docs must include a deprecation header:

```markdown
> ⚠️ **ARCHIVED** — This document is preserved for historical context.
> Current canonical documentation: [link to replacement]
> Archived: YYYY-MM-DD
```

---

## What NOT to Do

| Rule | Bad | Good |
|------|-----|------|
| Don't place docs at `docs/` root | `docs/sgf-format-analysis.md` | `docs/archive/sgf-format-analysis.md` |
| Don't maintain parallel guide systems | `docs/guides/` + `docs/how-to/` | Just `docs/how-to/` |
| Don't put frontend guides in how-to root | `docs/how-to/playwright-visual-testing.md` | `docs/how-to/frontend/playwright-visual-testing.md` |
| Don't exceed 3 directory levels | `docs/how-to/backend/adapters/ogs.md` | `docs/architecture/backend/adapters/ogs-adapter.md` |
| Don't duplicate concepts across tiers | Tag definitions in both arch + concepts | Single source in `docs/concepts/tags.md` |
| Don't skip See Also callouts | Doc with no cross-references | Every doc links to ≥1 related doc in another tier |
| Don't omit Last Updated date | No date on doc | `**Last Updated**: 2026-03-24` |

---

## Current Known Violations (Tracked for Fix)

These are documented deviations from this standard, pending the docs-cleanup initiative:

| File | Violation | Target location |
|------|-----------|-----------------|
| `docs/sgf-architecture-design.md` | At `docs/` root | `docs/archive/` (superseded by `docs/architecture/backend/sgf.md`) |
| `docs/sgf-format-analysis.md` | At `docs/` root, research doc | `docs/archive/sgf-format-analysis.md` |
| `docs/puzzle-sources.md` | Duplicate of `docs/reference/puzzle-sources.md` | Delete (superseded) |
| `docs/guides/` | Parallel to `docs/how-to/backend/` | Merge unique content → `docs/how-to/backend/`, delete `docs/guides/` |

---

## Governance Integration

The [Documentation Artifact Contract](./documentation-artifact-contract.md) governs initiative-level documentation. This file governs structural placement. Both must be satisfied for any documentation change to be considered complete.

When creating or moving docs as part of an initiative:

1. Determine the correct tier using the flowchart above
2. Verify depth ≤ 3 levels
3. Add all required elements (title, Last Updated, See Also)
4. Update the README index for the target tier directory
5. Update all cross-references in related docs
