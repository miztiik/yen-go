# Agent Correction Levels

> This document defines criteria for assessing the scale of modifications.
> AI Agents should always evaluate the correction level before making changes and choose the appropriate workflow.

---

## 1. Interaction Levels

| Level | Name           | Scale/Scope                                     | Action / Workflow                            |
| :---: | -------------- | ----------------------------------------------- | -------------------------------------------- |
|   0   | Super Minor    | Comments, typos, logs (behavior unchanged)      | Direct fix                                   |
|   1   | Minor          | 1 file, ~50 lines of logic fix                  | Direct fix                                   |
|   2   | Medium Single  | 1-2 files, ~100 lines, explicit behavior change | `Plan Mode -> Approve -> Execute`            |
|   3   | Multiple Files | 2-3 files, UI + Logic etc.                      | `Plan Mode -> Phased Execution`              |
|   4   | Large Scale    | 4+ files, involves structure changes            | `Propose breakdown first`                    |
|   5   | Fundamental    | Core design changes                             | `Design consultation only (Pause execution)` |

_Note: Line counts are rough estimates. If unsure, default to a higher (safer) level._

---

## 2. Docs-only vs Code-change Boundaries

### docs-only

- `docs/**/*.md`
- `README.md`, `CHANGELOG.md`
- Configuration schemas/docs (when not affecting runtime immediately)

### code-change

- `.py`, `.ts`, `.tsx` (Execution-affecting files)
- Changing display strings or comments in `.py`/`.tsx` files is treated as code-change.

**=> Requires branch + PR/Approval.**

_When in doubt, apply the code-change (safe) rule._

---

## 3. Detailed Workflow by Level

### Level 0: Super Minor

- **Target**: Text wording, comments, log additions.
- **Agent response must include**: File modified, 1-2 line summary, Quick check steps.

### Level 1: Minor

- **Target**: Small bug fix in a single file.
- **Agent response must include**: Specific diff summary, verification points.

### Level 2: Medium Single

- **Target**: Modifies logic across 1-2 files with an explicit behavior change.
- **Agent response must include**: Declare "Level 2", Impact surface (what feature breaks/changes), simple repro steps.

### Level 3: Multiple Files

- **Target**: Cross-cutting changes like Frontend UI + Backend Logic + Config.
- **Agent response must include**: Declare "Level 3", Target file list, Assessment of breaking changes (e.g. data schema compatibility).

### Level 4: Large Scale

- **Target**: State management refactoring, structural class changes.
- **Agent response must include**: Phased execution proposal, boundary definition ("What we will do now vs later").

### Level 5: Fundamental Change

- **Target**: E.g. Engine foundations or Core data model overhauls.
- **Agent response must include**: Declare "Level 5", Goals/Non-goals, Component breakdown for future Lv2/Lv3 execution, Architectural questions to resolve first.
