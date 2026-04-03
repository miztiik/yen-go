# SGF Architecture

> **See also**:
> - [Concepts: SGF Properties](../../concepts/sgf-properties.md) — Property reference (single source of truth)
> - [Concepts: Hints](../../concepts/hints.md) — Hint system
> - [Reference: Schema](../../../config/schemas/sgf-properties.schema.json) — JSON schema

**Last Updated**: 2026-03-25

Design decisions and rationale for YenGo's SGF extensions.

---

## Overview

YenGo extends the standard SGF (Smart Game Format) with custom properties for puzzle metadata. All YenGo properties use the `Y*` prefix. The current schema version is **15**.

For the full property-by-property reference, see [Concepts: SGF Properties](../../concepts/sgf-properties.md).

---

## File Locations

- **Published puzzles**: `yengo-puzzle-collections/sgf/`
- **Properties schema**: `config/schemas/sgf-properties.schema.json`
- **Naming schema**: `config/schemas/sgf-naming.schema.json` (16-char hash standard)
- **Property policies**: `config/sgf-property-policies.json`
- **Parser**: `backend/puzzle_manager/core/sgf_parser.py`
- **Builder**: `backend/puzzle_manager/core/sgf_builder.py`
- **Naming utility**: `backend/puzzle_manager/core/naming.py`

---

## Why Custom Properties?

SGF FF[4] provides **no standard properties** for puzzle difficulty, technique classification, progressive hints, quality metrics, or board region focus. YenGo keeps this metadata in a consistent `Y*` namespace so files remain compact, parseable, and easy to validate.

---

## Design Decisions

### Why `Y*` Prefix?

| Reason                 | Explanation                                    |
| ---------------------- | ---------------------------------------------- |
| **Standard-compliant** | SGF allows application-defined properties      |
| **Collision-free**     | Won't conflict with future standard properties |
| **Recognizable**       | Easy to identify YenGo-specific properties     |
| **Short**              | Single character keeps files compact           |

### Why 9 Levels?

The original 5-level system was too coarse. 9 levels provide ~5 rank granularity per level and a clean mapping to DDK/SDK/Dan progression.

| Ranks   | Level              |
| ------- | ------------------ |
| 30k-26k | novice             |
| 25k-21k | beginner           |
| 20k-16k | elementary         |
| 15k-11k | intermediate       |
| 10k-6k  | upper-intermediate |
| 5k-1k   | advanced           |
| 1d-3d   | low-dan            |
| 4d-6d   | high-dan           |
| 7d+     | expert             |

### Why Three Hints?

Progressive disclosure is pedagogically effective:

| Hint | Purpose               | Example                   |
| ---- | --------------------- | ------------------------- |
| 1    | What concept to apply | "Look for a snapback"     |
| 2    | Why it works          | "Direct capture fails..." |
| 3    | The answer            | "Play at {!cg}."          |

Players can request increasing help without skipping straight to the solution.

### Why Compact YH Format?

Earlier drafts used separate `YH1`/`YH2`/`YH3` properties. The current compact `YH[hint1|hint2|hint3]` format is a single property, simpler to parse, smaller in file size, and preserves hint ordering.

### Why Separate YQ and YX?

Two orthogonal concerns:

| Property            | Measures            | Example               |
| ------------------- | ------------------- | --------------------- |
| **YQ** (Quality)    | How well-documented | Comments, refutations |
| **YX** (Complexity) | How difficult       | Depth, reading count  |

A simple 3-move problem might have premium documentation. A deep 20-move problem might have minimal documentation.

### Why YL (Collection Membership)?

Collections (curated sets like "Cho Chikun" or "Gokyo Shumyo") are distinct from technical tags ("ko", "ladder").

Considered: Combining into `YT` (Tags). Rejected because:
- **Semantics**: `YT` = *what* it is (technique). `YL` = *where* it belongs (curation).
- **UI**: Tags are for filtering; Collections are for browsing/progress tracking.
- **Source-driven**: `YL` is derived from file paths/authorship, not board analysis.

### Why Not JSON Inside Properties?

Considered: `Y[{"level":"intermediate","tags":["ko"]}]`. Rejected because SGF parsers don't expect JSON, it's harder to grep, uses more bytes, and violates SGF's simple key-value model.

The exception is `YM` (pipeline metadata), which benefits from a structured JSON payload for cross-stage correlation.

### Why Config-Driven Values?

All valid values come from config files (`config/puzzle-levels.json`, `config/tags.json`, `config/source-quality.json`). This ensures a single source of truth shared by frontend and backend, with easy validation against known values.

### Why Remove SO Property?

**SO (Source)** was removed from published SGF because provenance is tracked in pipeline state (publish logs) rather than embedded in the puzzle file. This avoids cluttering SGF with operational metadata and addresses privacy/licensing concerns.

Source adapter ID is now tracked via the CLI `--source` flag and publish records, not as a standalone SGF property.

---

## Deprecated Properties

| Property | Status | Replaced By |
| -------- | ------ | ----------- |
| `YH1`/`YH2`/`YH3` | Removed in v8 | Compact `YH[hint1\|hint2\|hint3]` |
| `YG[slug:sublevel]` | Sub-levels deprecated | Plain slug: `YG[intermediate]` |
| `SO` | Removed in v8 | Provenance in pipeline state |
| `YS` (Source Adapter ID) | Removed | Source tracked via CLI `--source` and publish logs |
| `YI` (Run ID) | Removed in v13 | `YM.i` field carries run_id |

---

## Current Conventions

- Use compact `YH[hint1|hint2|hint3]` instead of separate hint fields.
- Keep `YT` alphabetically sorted and deduplicated.
- Store collection membership separately in `YL` rather than mixing it into `YT`.
- Preserve SGF structure as SGF properties rather than embedding broad JSON blobs.
- Keep provenance in `YM` and pipeline records instead of scattering it across multiple custom properties.
- Root `C[]` comments are **preserved by default** (configurable via `preserve_root_comment`). Move `C[]` comments are standardized with Correct/Wrong prefix.

---

## References

- [SGF FF[4] Specification](https://www.red-bean.com/sgf/)
- [KGS SGF Extensions](https://www.gokgs.com/help/sgf.html)
