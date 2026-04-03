# Tasks — Consolidated Backlog Index

**Initiative**: `20260310-docs-consolidated-backlog`  
**Last Updated**: 2026-03-20

---

## Task Dependency Graph

```
T1 (create backlog directory + index doc) [P]
        │
T2 (populate backlog entries from root TODO files) [P]
        │
T3 (add cross-reference links)
        │
T4 (validation — verify all root TODO files represented)
```

---

## Tasks

### T1 — Create Backlog Directory and Index Document

**Description**: Create `docs/reference/backlog/` directory and `consolidated-backlog.md` with frontmatter, header, and "See also" cross-references.

**Files**: `docs/reference/backlog/consolidated-backlog.md` (create)

**Deps**: None  
**Definition of Done**: File exists with proper header and cross-references.

### T2 — Populate Backlog Entries [P]

**Description**: Scan root `TODO/*.md` files and create a prioritized table linking each to its source.

**Files**: `docs/reference/backlog/consolidated-backlog.md` (modify)

**Deps**: T1  
**Definition of Done**: All 7 root TODO markdown files appear in the Active Backlog Items table.

### T3 — Add Cross-Reference Links

**Description**: Add "See also" callout linking to initiative mirror and archive index per documentation rules.

**Files**: `docs/reference/backlog/consolidated-backlog.md` (modify)

**Deps**: T2  
**Definition of Done**: Cross-reference callout present with valid links.

### T4 — Validation

**Description**: Verify all root `TODO/*.md` files are represented in the backlog index. Verify no code files were modified.

**Deps**: T3  
**Definition of Done**: 1:1 mapping between root TODO files and backlog entries. Zero code changes.

---

## Summary

| Metric              | Value                                     |
| ------------------- | ----------------------------------------- |
| Total tasks         | 4                                         |
| Files created       | 1 (consolidated-backlog.md)               |
| Files modified      | 0 code files                              |
| Initiative type     | docs-only                                 |
