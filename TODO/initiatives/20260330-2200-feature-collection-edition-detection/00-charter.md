# Charter: Collection Edition Detection

**Initiative**: `20260330-2200-feature-collection-edition-detection`  
**Type**: Feature  
**Supersedes**: `20260330-1400-feature-cross-source-collection-editions` (over-engineered, 32 tasks)  
**Last Updated**: 2026-03-30

---

## Problem Statement

Two problems occur when multiple sources contribute puzzles to the same collection:

### Problem 1: Content Loss (Silent)

The dedup checker at ingest rejects any puzzle whose board position already exists in the content database — even if it's from a different source with richer annotations. The second source's version is silently discarded into a `failed/` directory. No error, no notification. Better content is permanently lost.

### Problem 2: Interleaved Ordering (Visible)

When both sources' puzzles land in the same collection (via `YL[]` aliases), they're merged into one flat list at publish. The sort tiebreaker (`content_hash`) scrambles the pedagogical order. Users see random difficulty jumps, duplicate puzzles, and a broken teaching flow.

### What Happens If We Do Nothing

- **Problem 1**: We permanently lose whichever source runs second. If OGS has better annotations than kisvadim for the same puzzle, they're silently deleted.
- **Problem 2**: Collections with 2+ sources are unusable scrambled messes. A book designed to teach concepts progressively shows problem #823 (advanced ko) before problem #1 (basic eye).

### Scale

This affects ALL collection types — author, technique, graded. The `aliases` field in `collections.json` proves overlaps exist: each alias was added because a source used that name. With 159 collections and 1000+ OGS sub-collections, collisions are guaranteed.

## Goals

| ID | Goal | Acceptance Criteria |
|----|------|-------------------|
| G1 | Cross-source puzzles are not rejected at ingest | Puzzle from source B with same position as source A is stored (not discarded) |
| G2 | User can choose which source's version to study | Frontend shows edition picker on multi-source collection pages |
| G3 | Each source's pedagogical order is preserved | Each edition has independent sequence numbers 1-N |
| G4 | Detection is automatic — no manual config per collection | Collision detected from data in content DB, not from config fields |

## Non-Goals

| ID | Non-Goal | Rationale |
|----|----------|-----------|
| NG1 | Auto-best / richness scoring | Deferred to v2. No calibration data. Editions for all types is sufficient for v1. |
| NG2 | Collection-type-specific strategies | All types get same treatment: 2+ sources → editions. KISS. |
| NG3 | Solution tree merging | Go-domain correctness risk (different analysis depths = contradictory moves) |
| NG4 | Exposing raw source identifiers to users | "kisvadim" / "ogs" are meaningless to Go players |
| NG5 | Per-collection config fields (edition_policy etc.) | Eliminated. Detection is data-driven, not config-driven. |

## Constraints

| ID | Constraint |
|----|-----------|
| C1 | Zero Runtime Backend — static files on GitHub Pages |
| C2 | `yengo-content.db` schema change: add `collection_slug` column (one-time migration) |
| C3 | No new config fields in `collections.json` |
| C4 | Must work for ALL collection types identically |
| C5 | Pipeline runs are single-source (`--source X`) |
