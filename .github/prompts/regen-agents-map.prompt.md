---
mode: agent
description: Regenerate the AGENTS.md architecture map for a module after structural code changes.
---

Regenerate the `AGENTS.md` for the module at the path provided by the user.

## Steps

1. List all files in the module directory (recursive, skip `__pycache__`, `.pytest_cache`, `.lab-runtime`, `node_modules`, `dist`, `build`).
2. For each non-trivial source file, read its public API surface: exported functions/classes, their signatures and return types.
3. Identify all data models (dataclasses, TypedDicts, Pydantic models, TypeScript interfaces).
4. Trace the primary entry points to leaf calls (call graph).
5. Identify external dependencies (imports not from this module).

## Output Format

Overwrite (or create) the `AGENTS.md` in the module root with **exactly** these sections:

```markdown
# {Module Name} — Agent Architecture Map

> Agent-facing reference. NOT user documentation. Dense structural facts only.
> _Last updated: {YYYY-MM-DD} | Trigger: {reason provided by user}_

---

## 1. Directory Structure

| Path | Purpose |
|------|---------|
| `relative/path/file.py` | One-sentence descriptor |
...

## 2. Core Entities

| Class/Type | Key Fields | Represents |
|------------|-----------|------------|
...

## 3. Key Methods & Call Sites

For critical public functions:
| Function | Signature | Called By |
|----------|-----------|-----------|
...

## 4. Data Flow

Brief technical narrative. Use ASCII flow diagram if the pipeline has clear stages.

## 5. External Dependencies

| Library | Used For |
|---------|----------|
...

## 6. Known Gotchas

- Bullet list of non-obvious behaviors, coordinate system quirks, state coupling, async patterns, etc.
```

## Rules

- Maximum 450 lines total.
- Every line must help an agent navigate code faster. No padding prose.
- Line references welcome (`[Lines 140-295]`) but not required.
- Do NOT copy content from README.md (that is user-facing).
- Source of truth is the actual code, NOT the old AGENTS.md.
- After writing, verify the file was saved.
