# Research: How the Pipeline Assigns Collections (YL) to Puzzles

**Initiative**: 20260329-research-collection-assignment-pipeline  
**Date**: 2026-03-29  
**Status**: Complete

---

## 1. Research Question and Boundaries

**Question**: How does the Yen-Go pipeline assign YL (collection) tags to puzzles during ingest and analyze? What metadata survives from external sources through to collection assignment? Where is information lost?

**Scope**: OGS, Sanderland, GoProblems adapters → ingest stage → analyze stage → `assign_collections()` function.

---

## 2. Internal Code Evidence

### Finding F-1: `assign_collections()` Core Algorithm

| ID | Attribute | Detail |
|----|-----------|--------|
| R-1 | File | `backend/puzzle_manager/core/collection_assigner.py` (L1–83) |
| R-2 | Inputs | `source_link`, `puzzle_id`, `existing_collections`, `alias_map` |
| R-3 | Algorithm | Tokenized Sequence Matching — normalizes (NFKC + lowercase), splits on non-alphanumeric chars, checks if alias tokens appear as a **contiguous subsequence** in the haystack |
| R-4 | Haystack | `f"{source_link or ''} {puzzle_id or ''}"` — combines both into one token stream |
| R-5 | Alias source | `config/collections.json` → each collection has a `slug` (self-resolving) + `aliases[]` list |
| R-6 | Matching | Phrase matching: multi-word alias like `"lee changho"` must match contiguously in haystack tokens |

### Finding F-2: Two Collection Assignment Points

| ID | Where | File:Line | `source_link` value | `puzzle_id` value |
|----|-------|-----------|---------------------|-------------------|
| R-7 | **Sanderland adapter** (ingest-time) | `adapters/sanderland/adapter.py:485` | `rel_path(json_path)` — relative path preserving full directory structure | `sanderland-{folder}-{file}` style ID |
| R-8 | **Analyze stage** (all adapters) | `stages/analyze.py:374-377` | **Empty string `""`** — comment says "source_link not persisted to SGF" | `sgf_path.stem` — the **filename** from staging directory |

**Critical finding**: The analyze stage passes `source_link=""` to `assign_collections()`. This means the only text available for matching at analyze-time is the `puzzle_id` (the staging file's stem name).

### Finding F-3: OGS Adapter Configuration

| ID | Attribute | Detail |
|----|-----------|--------|
| R-9 | Adapter type | `local` (generic adapter) — no dedicated OGS adapter exists |
| R-10 | Source config | `config/sources.json:74-84` — `"adapter": "local"`, `"path": "external-sources/ogs/sgf"` |
| R-11 | Directory structure | `external-sources/ogs/sgf/batch-NNN/{numeric_id}.sgf` — flat numeric files like `10.sgf`, `1000.sgf` |
| R-12 | `puzzle_id` | Content-hash (SHA256[:16]) — **no directory or collection info** |
| R-13 | `source_link` | Absolute path to SGF file: e.g., `C:\...\external-sources\ogs\sgf\batch-001\1000.sgf` |
| R-14 | `source_link` at analyze | **Lost** — set to `""` in analyze stage |

### Finding F-4: OGS `sgf-by-collection/` Is NOT Used by Pipeline

| ID | Attribute | Detail |
|----|-----------|--------|
| R-15 | Tool | `external-sources/ogs/organize_by_collection.py` — standalone script |
| R-16 | Output | `external-sources/ogs/sgf-by-collection/{tier}/{batch}/{id-slug}/` with `manifest-index.json` |
| R-17 | Pipeline input | `config/sources.json` points to `external-sources/ogs/sgf` (flat), NOT `sgf-by-collection/` |
| R-18 | Conclusion | The `sgf-by-collection/` structure is a pre-organized reference copy; pipeline does NOT read from it |

### Finding F-5: Sanderland Adapter — Rich Path Metadata

| ID | Attribute | Detail |
|----|-----------|--------|
| R-19 | `source_link` | `rel_path(json_path)` preserving full directory like `external-sources/sanderland/problems/1a-tsumego-beginner/Cho Chikun Encyclopedia Life And Death - Elementary/Prob0001.json` |
| R-20 | `puzzle_id` | `sanderland-{folder}-{subfolder}-{stem}` — directory path encoded in the ID |
| R-21 | Collection assignment timing | **During ingest** (in `_json_to_sgf()`) — before SGF is written to staging |
| R-22 | YL persisted | Yes — written directly into SGF as `YL[slug1,slug2]` at ingest |
| R-23 | Analyze skips | If YL already present in SGF (from ingest), analyze stage preserves it via policy `is_enrichment_needed("YL", ...)` |

### Finding F-6: GoProblems Adapter Configuration

| ID | Attribute | Detail |
|----|-----------|--------|
| R-24 | Adapter type | `local` (generic) |
| R-25 | Source config | `config/sources.json:86-95` — `"path": "external-sources/goproblems/sgf"` |
| R-26 | Directory structure | `external-sources/goproblems/sgf/batch-NNN/{numeric_id}.sgf` — same flat structure as OGS |
| R-27 | `puzzle_id` | Content-hash (SHA256[:16]) — no collection info |
| R-28 | Collection matching | Relies entirely on analyze stage, which passes `source_link=""` and the content-hash `puzzle_id`. **No collection info survives.** |

### Finding F-7: `source_link` Lifecycle

| ID | Stage | Value | Persisted? |
|----|-------|-------|------------|
| R-29 | Adapter `fetch()` | Absolute/relative file path or URL | In `FetchResult.source_link` |
| R-30 | Ingest `_process_puzzle()` | Only `Path(source_link).name` extracted as `original_filename` (L327-328) | Encoded in `YM` property (filename only) |
| R-31 | Ingest file write | File saved as `{puzzle_id}.sgf` in staging | Directory path info **lost** |
| R-32 | Analyze stage | Reads SGF from staging; `source_link` field **not available** in SGF | Passes `""` to `assign_collections()` |
| R-33 | Conclusion | **Full `source_link` (path) is discarded during ingest** — only filename basename survives in YM |

### Finding F-8: Local Adapter `_generate_id()` — Content-Based

| ID | Attribute | Detail |
|----|-----------|--------|
| R-34 | File | `adapters/local/adapter.py:465-480` |
| R-35 | Method | `SHA256(content)[:16]` — purely content-based hash |
| R-36 | Implication | **No directory info encoded in puzzle_id** for `local` adapter |
| R-37 | Contrast | Sanderland's `_generate_id()` uses `rel_path` parts → `sanderland-{folder}-{file}` (path-based) |

---

## 3. External References

| ID | Reference | Relevance |
|----|-----------|-----------|
| R-38 | Common pattern: "enrich-at-ingest" | Sanderland follows this — assigns collections during ingest when directory metadata is available. This is the correct pattern for sources with meaningful directory hierarchies. |
| R-39 | Content-addressable storage pattern | Local adapter's SHA256-based ID is a content-addressable approach, good for dedup but destroys provenance metadata. |

---

## 4. Candidate Adaptations for Yen-Go

### Option A: Enrich OGS Collections at Ingest (Like Sanderland)

Create a dedicated OGS adapter (or enhance `local` adapter) that reads from `sgf-by-collection/` instead of flat `sgf/`. The directory path `curated/01/10149-alex-s-introduction-to-bad-results/` would provide rich tokens for `assign_collections()`.

- **Pro**: Mirrors proven sanderland pattern; no analyze-stage changes needed.
- **Con**: Requires new adapter or `local` adapter enhancement; changes source config.

### Option B: Persist `source_link` into SGF for Analyze-Stage Matching

Add a new SGF property or extend `YM` to carry the full `source_link` through to the analyze stage. The analyze stage would then read it and pass it to `assign_collections()`.

- **Pro**: Works for all adapters without per-adapter code; single fix in ingest + analyze.
- **Con**: Increases SGF size slightly; adds a new property to maintain.

### Option C: Use `sgf-by-collection/` Manifests as a Lookup Table

Build a mapping from `{puzzle_numeric_id} → collection_slug` using `manifest-index.json`, and inject this as a supplementary alias map or direct assignment during ingest.

- **Pro**: Uses existing data; no directory path parsing needed.
- **Con**: Requires new lookup mechanism; OGS-specific; doesn't generalize.

### Option D: Encode Directory Path in `puzzle_id` for Local Adapter

Change `local` adapter's `_generate_id()` to include directory info (like sanderland does), so the analyze stage's `puzzle_id`-based matching can work.

- **Pro**: Minimal change; improves analyze-stage matching for all local sources.
- **Con**: Changes existing puzzle IDs (breaking change for existing data); content-hash dedup would need separate mechanism.

---

## 5. Risks, License/Compliance Notes, and Rejection Reasons

| ID | Risk | Severity | Notes |
|----|------|----------|-------|
| R-40 | OGS puzzles currently get **zero** collection assignments | High | Flat numeric filenames + content-hash IDs mean no alias tokens match |
| R-41 | GoProblems has same problem as OGS | High | Same flat `batch-NNN/{id}.sgf` structure, same `local` adapter |
| R-42 | Option D is backward-incompatible | Medium | Changing `puzzle_id` format invalidates existing staging data and dedup tracking |
| R-43 | No license concerns | None | All approaches use internal code patterns |

---

## 6. Planner Recommendations

1. **Option A is recommended for OGS** — Create an OGS-specific adapter (or configure `local` to read from `sgf-by-collection/`) and assign collections at ingest time, exactly like sanderland. The `organize_by_collection.py` tool already created the directory hierarchy with collection names in the paths. This is the lowest-risk, highest-value approach.

2. **Option B is a good follow-up for generalization** — Persisting `source_link` into SGF (via `YM` extension or a new property) fixes the root cause for ALL future adapters. But it's a cross-cutting change that should be planned carefully.

3. **Option C is a viable quick-win alternative** — If modifying the adapter path is undesirable, a manifest lookup table injected during ingest can directly assign collections to OGS puzzles by numeric ID.

4. **GoProblems needs separate investigation** — It has the same structural problem (flat batches), but may not have an equivalent `organize_by_collection.py` tool. Its collection assignment strategy needs its own research.

---

## 7. Confidence and Risk Update

| Metric | Value |
|--------|-------|
| `post_research_confidence_score` | 92 |
| `post_research_risk_level` | low |
| **Open questions** | See below |

### Open Questions

| q_id | question | options | recommended | user_response | status |
|------|----------|---------|-------------|---------------|--------|
| Q1 | Should OGS adapter read from `sgf-by-collection/` (organized) or `sgf/` (flat) as its primary source? | A: sgf-by-collection/ (rich paths), B: sgf/ with manifest lookup, C: Other | A | — | ❌ pending |
| Q2 | Is changing the OGS source config path in `sources.json` acceptable, or do we need backward compat with existing staged data? | A: Clean break OK, B: Must support both, C: Other | A | — | ❌ pending |
| Q3 | Should we also fix the analyze stage's `source_link=""` gap (Option B) as part of this initiative, or defer? | A: Fix now, B: Defer to separate initiative | B | — | ❌ pending |
| Q4 | Does GoProblems have collection metadata available anywhere (directory structure, manifest, SGF properties)? | A: Yes (needs research), B: No — flat numeric only | — | — | ❌ pending |

---

## Appendix: Data Flow Diagrams

### Sanderland (Working — Collections Assigned)

```
external-sources/sanderland/problems/{folder}/{book}/{Prob0001.json}
    │
    ├─ SanderlandAdapter.fetch() → source_link = rel_path(json_path)  [FULL PATH]
    │                              puzzle_id = "sanderland-{folder}-{book}-Prob0001"
    │
    ├─ _json_to_sgf() → assign_collections(source_link=rel_path, puzzle_id=...) → YL[slug]
    │
    └─ staging/ingest/sanderland-{...}.sgf  (YL already embedded)
        │
        └─ Analyze → YL already present → PRESERVED by policy
```

### OGS (Broken — No Collections Assigned)

```
external-sources/ogs/sgf/batch-001/{1000.sgf}
    │
    ├─ LocalAdapter.fetch() → source_link = "C:\...\ogs\sgf\batch-001\1000.sgf"  [ABS PATH]
    │                          puzzle_id = SHA256(content)[:16]  [CONTENT HASH]
    │
    ├─ Ingest._process_puzzle() → original_filename = "1000.sgf"  [ONLY BASENAME KEPT]
    │                              file saved as: staging/ingest/{content_hash}.sgf
    │
    └─ Analyze → assign_collections(source_link="", puzzle_id="{content_hash}") → NO MATCH
                  ↑ source_link lost, puzzle_id is opaque hash
```

### OGS `sgf-by-collection/` (NOT Used by Pipeline)

```
external-sources/ogs/sgf-by-collection/curated/01/10149-alex-s-introduction.../1000.sgf
    │
    └─ organize_by_collection.py (standalone tool) — copies from sgf/ to organized dirs
       └─ manifest-index.json maps {id, tier, slug, dir, puzzles}
       └─ NOT referenced by config/sources.json → pipeline ignores this entirely
```
