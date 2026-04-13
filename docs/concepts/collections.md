# Collections

_Last Updated: 2026-03-29_

Collections are curated groups of tsumego puzzles organized by technique, difficulty, classical canon, author, or system function. They provide structured learning paths and browsing experiences beyond the basic level and tag indexes. Every collection is **Go-domain-meaningful** — no source-branded or website-reference collections exist.

> **This document is the canonical reference for the collections taxonomy.** The machine-readable source of truth is `config/collections.json` (which references this document).

## Source of Truth

- **Machine-readable**: `config/collections.json` — the single source of truth for all collections. Every collection slug used in SGF files (via `YL[]`) must exist in this configuration.
- **Human-readable**: This document — the authoritative reference describing the taxonomy, aliases, and design rationale.

## Collection Schema (v5.0)

Each collection entry has these fields:

| Field         | Type     | Required | Description                                                                                    |
| ------------- | -------- | -------- | ---------------------------------------------------------------------------------------------- |
| `slug`        | string   | Yes      | Unique kebab-case identifier (`^[a-z0-9][a-z0-9-]*[a-z0-9]$`, ≤64 chars)                       |
| `name`        | string   | Yes      | Human-readable display name (≤128 chars)                                                       |
| `description` | string   | Yes      | 1–2 sentence description (≤512 chars)                                                          |
| `curator`     | string   | Yes      | Author name, "Curated", or "System"                                                            |
| `source`      | string   | Yes      | Source adapter ID (e.g., `"source-adapter-id"`) or `"mixed"`                                   |
| `type`        | enum     | Yes      | `author` · `technique` · `graded` · `reference` · `system`                                     |
| `ordering`    | enum     | Yes      | `source` · `difficulty` · `manual`                                                             |
| `tier`        | enum     | Yes      | `editorial` · `premier` · `curated` · `community`                                              |
| `aliases`     | string[] | No       | Alternate names for runtime matching (see [Aliases](#aliases))                                 |
| `level_hint`  | enum     | No       | Difficulty level override slug (see [Level Hint](#level-hint-collection-based-level-override)) |

## Collection Types

| Type        | Count   | Purpose                                                                                    | Curator          |
| ----------- | ------- | ------------------------------------------------------------------------------------------ | ---------------- |
| `author`    | 60      | Classical works + modern author-curated books/series                                       | Real author name |
| `reference` | 45      | School curricula, publication series, book-specific, and other domain-meaningful groupings | Varies           |
| `technique` | 43      | Focused on a specific Go technique or problem category                                     | "Curated"        |
| `graded`    | 9       | Curated learning paths per skill level, pedagogically sequenced                            | "Curated"        |
| `system`    | 2       | Auto-generated or scheduled collections                                                    | "System"         |
| **Total**   | **159** |                                                                                            |                  |

> **v3.0 consolidation**: 738 original source collections were consolidated into 159 canonical collections. All original names are preserved as aliases (1,270 total). The `reference` type was activated for school curricula, publication series, and other domain-meaningful groupings that are neither technique-focused nor author-specific.

## Ordering Modes

| Mode         | Description                                      | Used by                       |
| ------------ | ------------------------------------------------ | ----------------------------- |
| `source`     | Original order from source material              | Classical canon, author works |
| `difficulty` | Ordered by computed puzzle difficulty (YG level) | Technique collections         |
| `manual`     | Hand-curated pedagogical sequence                | Graded essentials             |

## Quality Tiers

Collections are classified into tiers based on their provenance and curation level:

| Tier        | Count | Description                                                             | Assigned By           |
| ----------- | ----- | ----------------------------------------------------------------------- | --------------------- |
| `editorial` | 68    | Hand-curated by domain experts. All original YenGo collections.         | Human review          |
| `premier`   | 44    | Top 10% source quality score (community engagement + rating + content). | `sort_collections.py` |
| `curated`   | 47    | Top 10–30% source quality score. Solid educational value.               | `sort_collections.py` |
| `community` | 0     | 30–60% source quality score. Usable but less validated.                 | `sort_collections.py` |

The `unvetted` tier from source sorting (bottom 40%) is intentionally excluded from the schema — those collections are filtered out during bootstrap and never appear in `config/collections.json`.

See [Collection Grading](./collection-grading.md) for scoring methodology.

## Level Hint (Collection-Based Level Override)

The optional `level_hint` field (added in v5.0) allows a collection to declare the expected difficulty level for all its puzzles. When a puzzle is assigned to a collection with a `level_hint`, the hint **overrides** the heuristic classifier's output for the `YG` property.

### Why This Exists

The heuristic classifier uses structural features (solution depth, variation count, stone count, board size) to estimate difficulty. This works reasonably well for unaffiliated puzzles, but often disagrees with expert curation. For example, a short 2-move problem from _Cho Chikun's Encyclopedia of Life & Death — Advanced_ would be classified as "novice" by the heuristic, when the author specifically designed it for advanced players.

### Which Collections Have `level_hint`

**15 collections** currently have a `level_hint`:

| Category               | Collections                                                      | Level Hint                               |
| ---------------------- | ---------------------------------------------------------------- | ---------------------------------------- |
| Graded essentials (9)  | `novice-essentials` through `expert-essentials`                  | Matches the level in the slug            |
| Cho Chikun (3)         | `cho-chikun-life-death-elementary`, `-intermediate`, `-advanced` | `elementary`, `intermediate`, `advanced` |
| Maeda (4)              | `maeda-nobuaki-beginner-tsumego`, `-intermediate-tsumego`, `-advanced-tsumego`, `-newly-selected-100` | `beginner`, `intermediate`, `advanced`, `intermediate` |
| Graded Go Problems (1) | `graded-go-problems-beginners-1`                                 | `beginner`                               |

**Technique collections** (e.g., `capture-problems`, `ko-problems`) do **not** have `level_hint` because they span all difficulty levels by design.

### Resolution Priority (3-Tier)

| Priority     | Signal                  | When Applied                                        |
| ------------ | ----------------------- | --------------------------------------------------- |
| 1 (highest)  | Collection `level_hint` | Puzzle belongs to a collection with `level_hint`    |
| 2            | Source-provided `YG`    | Source SGF has a valid YG value, no collection hint |
| 3 (fallback) | Heuristic classifier    | No collection hint and no source YG                 |

### Conflict Resolution

When a puzzle belongs to **multiple** level-bearing collections with different hints, the **lowest (easiest) level wins**. This is the conservative choice — better to present a puzzle as slightly easier than to frustrate a student with mislabeled difficulty.

Mismatches are logged for observability:

```
INFO  Level override for puzzle xyz: collection 'beginner-essentials' implies 'beginner' (2),
      heuristic classified as 'intermediate' (4). Using collection level.
```

### Valid Values

`level_hint` must be one of the 9 level slugs: `novice`, `beginner`, `elementary`, `intermediate`, `upper-intermediate`, `advanced`, `low-dan`, `high-dan`, `expert`.

---

## Aliases

Aliases are **runtime-active** — they serve two purposes:

1. **Ingest matching**: During pipeline ingest/analyze, source metadata (folder paths, puzzle IDs, comments) is matched against aliases to auto-assign `YL[]` collection membership. This uses **Tokenized Sequence Matching** (spec 128), allowing multi-word phrases to match across directory delimiters (e.g. `["Lee Changho"]` matches paths like `.../Lee-Changho-Tesuji/...`).
2. **Frontend search**: Users can search for collections using alternate names, Japanese/Chinese terms, or abbreviations.

**Rules**:

- Every alias must be **globally unique** across all collections — no alias may appear in two different collections
- Slugs are self-resolving (e.g., `resolve_collection_alias("gokyo-shumyo")` → `"gokyo-shumyo"`)
- Matching is case-insensitive with Unicode NFC normalization
- An empty or absent `aliases` array means the collection cannot be matched by alias during ingest

---

## Collection Taxonomy (159 entries)

> The complete list of all 159 collections with their aliases is in `config/collections.json`. This section documents the taxonomy categories and representative examples.

### Technique Collections (43)

Problems organized by Go technique or problem category. These are curated from mixed sources (`source: "mixed"`) and typically ordered by difficulty.

| Slug                    | Name                      | Key Aliases                                         | Notes                                                               |
| ----------------------- | ------------------------- | --------------------------------------------------- | ------------------------------------------------------------------- |
| `life-and-death`        | Life and Death Problems   | 基本死活, fundamental L&D, essential life and death | Core life-and-death problems (66 aliases from consolidated sources) |
| `tesuji-training`       | Tesuji Training           | 手筋, tactical problems, tesuji                     | Cross-technique tactical problem set                                |
| `capture-problems`      | Capture Problems          | captura, capturing, eat time                        | Capturing techniques (40+ aliases, multilingual)                    |
| `ladder-problems`       | Ladder Problems           | シチョウ, shicho, 征                                | Shicho reading and ladder-related tactics                           |
| `net-problems`          | Net (Geta) Problems       | ゲタ, geta, loose net                               | Net capture technique                                               |
| `ko-problems`           | Ko Problems               | コウ, 劫, ko fight                                  | Ko fights and ko-related life-and-death                             |
| `snapback-problems`     | Snapback Problems         | ウッテガエシ, uttegaeshi, oiotoshi                  | Sacrifice-and-recapture technique                                   |
| `nakade-problems`       | Nakade Problems           | ナカデ, 中手                                        | Filling inside to prevent two eyes                                  |
| `capturing-race`        | Capturing Race (Semeai)   | 攻め合い, semeai                                    | Liberty-counting races between groups                               |
| `eye-shape-mastery`     | Eye Shape Mastery         | 眼形, eye space                                     | Standard eye formations and vital points                            |
| `shape-problems`        | Shape Problems            | 形, katachi, good shape                             | Efficient stone formations (51 aliases)                             |
| `double-atari-problems` | Double Atari Problems     | atari, mutual atari                                 | Double atari and atari techniques                                   |
| `opening-problems`      | Opening Problems          | 布石, fuseki, opening                               | Opening-phase problems                                              |
| `joseki-problems`       | Joseki Problems           | 定石, joseki                                        | Corner sequences and standard patterns                              |
| `connection-problems`   | Connection Problems       | つなぎ, connect                                     | Connecting stones                                                   |
| `cutting-problems`      | Cutting Problems          | 切り, kiri, cut                                     | Cutting opponent's connections                                      |
| `kill-problems`         | Killing Problems          | 殺し, to kill                                       | Killing opponent groups                                             |
| `living-problems`       | Living Problems           | 生き, survive                                       | Making groups alive                                                 |
| `escape-problems`       | Escape Problems           | 凌ぎ, shinogi                                       | Saving weak groups under attack                                     |
| `endgame-problems`      | Endgame Problems          | ヨセ, yose                                          | Endgame boundary plays                                              |
| `corner-life-and-death` | Corner Life and Death     | 隅の死活                                            | Corner-specific life and death                                      |
| `seki-problems`         | Seki Problems             | セキ, mutual life                                   | Mutual life situations                                              |
| `liberty-shortage`      | Liberty Shortage Problems | ダメヅマリ, damezumari                              | Shortage of liberties                                               |
| `sacrifice-techniques`  | Sacrifice Techniques      | 捨て石, suteishi                                    | Strategic stone sacrifice                                           |
| `under-the-stones`      | Under the Stones          | 石の下                                              | Recapture technique                                                 |
| `vital-point`           | Vital Point Problems      | 急所                                                | Finding the decisive move                                           |
| `connect-underneath`    | Connect Underneath        | 渡り, watari                                        | Connecting under opponent's stones                                  |

Plus 16 additional technique collections. See `config/collections.json` for the full list.

### Graded Collections (9)

Curated, pedagogically-sequenced learning paths for each skill level. These are **NOT** exhaustive level listings — the full corpus at each level is available via SQL queries on `yengo-search.db` (e.g., `WHERE level_id = ?`). Graded collections have `ordering: "manual"` because problems are sequenced for learning progression, not just sorted by difficulty.

> **Naming rationale**: Uses `*-essentials` instead of `*-100` because at scale (150K+ puzzles, ~16K per level), a fixed count creates an artificial curation bottleneck. The collection may contain 50, 100, or 200 problems — the value is in pedagogical sequencing, not counting.

| Slug                            | Name                          | Level Range                 |
| ------------------------------- | ----------------------------- | --------------------------- |
| `novice-essentials`             | Novice Essentials             | Novice (30k+)               |
| `beginner-essentials`           | Beginner Essentials           | Beginner (25k–20k)          |
| `elementary-essentials`         | Elementary Essentials         | Elementary (20k–15k)        |
| `intermediate-essentials`       | Intermediate Essentials       | Intermediate (15k–10k)      |
| `upper-intermediate-essentials` | Upper Intermediate Essentials | Upper Intermediate (10k–5k) |
| `advanced-essentials`           | Advanced Essentials           | Advanced (5k–1d)            |
| `low-dan-essentials`            | Low Dan Essentials            | Low Dan (1d–3d)             |
| `high-dan-essentials`           | High Dan Essentials           | High Dan (3d–5d)            |
| `expert-essentials`             | Expert Essentials             | Expert (5d+)                |

Each graded collection absorbs generic level-named source collections as aliases (e.g., `novice-essentials` has 55+ aliases including multilingual variants).

### Author Collections (60)

Classical works and modern author-curated books/series. Each titled Go professional's published work maintains its own collection. Multiple source uploads of the same book are merged as aliases.

#### Classical Canon (6)

| Slug              | Name                        | Curator                  | Era          |
| ----------------- | --------------------------- | ------------------------ | ------------ |
| `gokyo-shumyo`    | Gokyo Shumyo (碁経衆妙)     | Hayashi Genbi            | Edo (1812)   |
| `igo-hatsuyoron`  | Igo Hatsuyoron (囲碁発陽論) | Inoue Dosetsu Inseki     | Edo (1713)   |
| `xuanxuan-qijing` | Xuanxuan Qijing (玄玄棋經)  | Yan Defu & Yan Tianzhang | Yuan (1349)  |
| `guanzi-pu`       | Guanzi Pu (官子谱)          | Guo Bailing              | Qing (1660s) |
| `genran`          | Genran (玄覧)               | Traditional              | Classical    |
| `gokyo-seimyo`    | Gokyo Seimyo (碁経精妙)     | Hayashi Genbi            | Edo          |

#### Notable Modern Authors

| Author                       | Collections | Example Slugs                                                                    |
| ---------------------------- | ----------- | -------------------------------------------------------------------------------- |
| Cho Chikun (趙治勲)          | 3           | `cho-chikun-life-death-elementary`, `-intermediate`, `-advanced`                 |
| Hashimoto Utaro (橋本宇太郎) | 5           | `hashimoto-1-year-tsumego`, `hashimoto-famous-creations-300`, etc.               |
| Maeda Nobuaki (前田陳爾)     | 9           | `maeda-nobuaki-god-of-tsumego`, `maeda-nobuaki-beginner-tsumego`, `maeda-nobuaki-advanced-tsumego`, etc. |
| Go Seigen (吴清源)           | 2           | `go-seigen-tsumego-dojo`, `go-seigen-evil-moves`                                 |
| Segoe Kensaku & Go Seigen    | 1           | `segoe-tesuji-dictionary`                                                        |
| Fujisawa Shuuko (藤沢秀行)   | 3           | `fujisawa-tsumego-masterpiece`, `fujisawa-tsumego-graded`, `fujisawa-classroom`  |
| James Davies                 | 3           | `james-davies-tesuji`, `james-davies-life-death`, `james-davies-endgame`         |
| Lee Changho (李昌鎬)         | 1           | `lee-changho-tesuji`                                                             |
| Ishida Akira                 | 2           | `ishida-tsumego-masterpieces`, `ishida-davies-attack-and-defense`                |
| Ishida Yoshio (石田芳夫)     | 1           | `ishida-yoshio-3dan-challenge`                                                   |
| Wang Zhipeng                 | 1           | `wang-zhipeng-life-death`                                                        |
| Yang Yilun                   | 1           | `yang-yilun-life-death`                                                          |

Plus 30+ additional author collections. See `config/collections.json` for the full list.

### Reference Collections (45)

School curricula, publication series, book-specific collections, and other domain-meaningful groupings.

| Category             | Example Slugs                                                               | Notes                                            |
| -------------------- | --------------------------------------------------------------------------- | ------------------------------------------------ |
| `school-curricula-1` | `school-curricula-1`, `rennes-go-school`, `pim-go-school`, `krun-go-school` | Consolidated numbered series into single entries |
| Publication series   | `dutch-go-magazine`, `british-go-journal`                                   | Periodical problem compilations                  |
| Training series      | `life-death-training-series`, `1200igo-quizzes`, `level-up-series`          | Numbered training sets                           |
| Book-specific        | `graded-go-problems-beginners-1`, `internet-tsumego-book`                   | Specific published books                         |
| General practice     | `general-practice`, `easy-mixed-problems`                                   | Mixed/unclassified problem sets                  |

### System Collections (2)

Auto-generated or scheduled collections managed by the pipeline.

| Slug               | Name             | Notes                         |
| ------------------ | ---------------- | ----------------------------- |
| `daily-warmup`     | Daily Warmup     | Quick daily practice problems |
| `weekly-challenge` | Weekly Challenge | Weekly curated challenge      |

---

## SGF Integration

Collections are stored in the SGF `YL[]` property (added in schema v10):

```
YL[life-and-death]
YL[ko-problems,tesuji-training]
```

- Comma-separated, alphabetically sorted, deduplicated
- Each slug must exist in `config/collections.json`
- A puzzle can belong to multiple collections (many-to-many)
- Omit `YL` entirely if the puzzle is not in any collection

## Database Indexes

Collection data is stored in the `puzzle_collections` table of `yengo-search.db`. Each row links a `content_hash` to a `collection_id` with an optional `sequence_number`. See [Numeric ID Scheme](numeric-id-scheme.md) for how IDs map to slugs.

### Query Example

```sql
SELECT p.*, pc.sequence_number FROM puzzles p
JOIN puzzle_collections pc ON p.content_hash = pc.content_hash
WHERE pc.collection_id = 1
ORDER BY pc.sequence_number;
```

Collection entries include a `sequence_number` (1-indexed position within the collection). See [SQLite Index Schema](../reference/view-index-schema.md) for the full schema.

## Graded Collections vs Level Queries

| Aspect   | Graded Collection (`*-essentials`)     | Level query (`WHERE level_id = ?`)       |
| -------- | -------------------------------------- | ---------------------------------------- |
| Contents | Curated pedagogical subset             | Full corpus at that level                |
| Ordering | `manual` (hand-sequenced for learning) | `difficulty` (sorted by content_hash)    |
| Size     | 50–200 problems                        | Thousands (paginated via SQL LIMIT/OFFSET) |
| Purpose  | Structured learning path               | Browse/search everything                 |

## Design Decisions

- **No source-branded collections** (v2.0) — Source brands removed. Source identity is tracked in `YS[]` and adapter metadata, not collections.
- **v3.0 consolidation** — 738 source collections merged into 168 canonical collections. All original names preserved as aliases (1,270+ total). See `tools/consolidate_collections.py` for the full mapping.
- **Aliases are runtime-active** — not just documentation. Used during ingest to auto-assign `YL[]` and in frontend for search/filter.
- **One collection per major work** — multi-volume works (e.g., Hashimoto "Moments of the Wind" vols 1–3) share one entry. Volume info is in source metadata, not collection structure.
- **`reference` type for non-technique, non-author groupings** — school curricula, publication series, and domain-meaningful groupings that don't fit `technique` or `author`.
- **No `display_order` field** — array position in `config/collections.json` is implicit order (YAGNI).
- **No `added_date` field** — git history tracks when collections were added (YAGNI).

## Pre-Pipeline Collection Embedding

Collection membership (`YL[]`) can be embedded into SGF files **before** pipeline ingest using the `tools/core/collection_embedder.py` utility. This is useful for sources where directory structure or filenames encode collection identity.

### Embedding Strategies

The embedder supports three resolution strategies via the `EmbedStrategy` protocol:

| Strategy | Class | Resolution Method |
|----------|-------|-------------------|
| Phrase match | `PhraseMatchStrategy` | Matches directory names against `CollectionMatcher` aliases |
| Manifest lookup | `ManifestLookupStrategy` | Reads a `_collections_manifest.json` mapping dirs → slugs |
| Filename pattern | `FilenamePatternStrategy` | Extracts slug from filename regex patterns |

### Chapter 0 Convention

Sources without explicit chapter structure use **chapter 0** as a sentinel:

```
YL[life-and-death:0/42]
```

Chapter 0 means "chapterless" — the position number (42) is the global sequence within the collection. The pipeline and frontend treat chapter 0 identically to omitting the chapter, but it preserves ordering information.

### YL Format

The embedder writes the full `YL[slug:chapter/position]` format:

- `slug` — collection slug from `config/collections.json`
- `chapter` — source chapter/section number (0 for chapterless sources)
- `position` — puzzle position within the chapter (1-indexed)

### Write Safety

The embedder uses a defensive write strategy:

- **Atomic writes** via `tools.core.atomic_write` (temp + rename)
- **Backups** created as `{file}.yl-backup` before modification
- **Dry-run mode** for previewing changes without writing
- **Restore command** (`restore_backups()`) to revert all modifications
- **Checkpoint support** for resuming interrupted embedding runs

> **See also**: [Tool Development Standards — SGF Output Standards](../how-to/backend/tool-development-standards.md#4-sgf-output-standards) for the minimal-edit exception that applies to pre-ingest annotation tools.

---

> **See also**:

> - [Tags concept](tags.md) — Tag taxonomy (tags are distinct from collections)
> - [Concepts: Numeric ID Scheme](numeric-id-scheme.md) — ID ranges for levels, tags, and collections
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) — How collections are published
> - [config/collections.json](../../config/collections.json) — Machine-readable source of truth
> - [config/schemas/collections.schema.json](../../config/schemas/collections.schema.json) — JSON Schema (v5.0)
