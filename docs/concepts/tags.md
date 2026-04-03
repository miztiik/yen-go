# Tags (Technique Classification)

> **See also**:
>
> - [Concepts: SGF Properties](./sgf-properties.md) — YT property format
> - [Reference: Tags Config](../../config/tags.json) — Canonical tag list
> - [Architecture: Pipeline](../architecture/backend/pipeline.md) — How tags flow through the pipeline
> - [Architecture: Tagging Strategy](../architecture/backend/tagging-strategy.md) — Precision-first detection design

**Last Updated**: 2026-03-09

**Single Source of Truth**: [`config/tags.json`](../../config/tags.json)

Tags classify puzzles by technique, enabling filtering and study by skill type. All tags are flat identifiers (no hierarchy) stored in the `YT` SGF property.

---

## YT Property Format

Tags are stored in the `YT` property:

```sgf
YT[corner,ko,ladder,nakade]
```

**Rules**:

- Comma-separated
- Alphabetically sorted
- Deduplicated
- No maximum count
- All tag IDs must exist in `config/tags.json`
- Lowercase kebab-case only (no colons, slashes, or dots)

---

## Tag Categories

Tags are organized into three categories for display purposes. The category is metadata in `config/tags.json` — the `YT` property itself is a flat list.

### Objectives (4 tags)

Describe what the puzzle asks you to achieve.

| Tag              | Name         | Description                                   | Japanese        |
| ---------------- | ------------ | --------------------------------------------- | --------------- |
| `life-and-death` | Life & Death | Kill opponent's group or make your group live | 死活 (shikatsu) |
| `living`         | Living       | Make your group live with two eyes            | 生きる (ikiru)  |
| `ko`             | Ko           | Solution involves ko fight or ko threat       | コウ (kō)       |
| `seki`           | Seki         | Mutual life — neither side can kill           | セキ (seki)     |

### Techniques (11 tags)

Describe the strategic method used.

| Tag            | Name         | Description                                     | Japanese          |
| -------------- | ------------ | ----------------------------------------------- | ----------------- |
| `capture-race` | Capture Race | Liberty race between groups                     | 攻め合い (semeai) |
| `escape`       | Escape       | Save a group by running or connecting out       | —                 |
| `eye-shape`    | Eye Shape    | Creating, stealing, or destroying eyes          | —                 |
| `dead-shapes`  | Dead Shapes  | Recognizing shapes that cannot live             | —                 |
| `connection`   | Connection   | Connecting stones/groups to strengthen position | 繋ぐ (tsugu)      |
| `cutting`      | Cutting      | Separating opponent's stones/groups             | 切り (kiri)       |
| `corner`       | Corner       | Problems focused on corner positions            | 隅 (sumi)         |
| `sacrifice`    | Sacrifice    | Intentionally giving up stones for advantage    | 捨て石 (suteishi) |
| `shape`        | Shape        | Efficient stone formations and good shape       | 形 (katachi)      |
| `endgame`      | Endgame      | Late-game tactics and yose techniques           | ヨセ (yose)       |
| `joseki`       | Joseki       | Standard corner sequences and variations        | 定石 (jōseki)     |
| `fuseki`       | Fuseki       | Opening patterns and whole-board strategy       | 布石 (fuseki)     |

### Tesuji Patterns (13 tags)

Describe specific tactical moves.

| Tag                | Name             | Description                                                 | Japanese                  |
| ------------------ | ---------------- | ----------------------------------------------------------- | ------------------------- |
| `snapback`         | Snapback         | Sacrifice stone(s) to immediately recapture                 | ウッテガエシ (uttegaeshi) |
| `throw-in`         | Throw-in         | Sacrifice inside opponent's shape to reduce liberties       | ホウリコミ (hōrikomi)     |
| `ladder`           | Ladder           | Diagonal staircase chase pattern                            | シチョウ (shichō)         |
| `net`              | Net              | Loose surrounding capture                                   | ゲタ (geta)               |
| `liberty-shortage` | Liberty Shortage | Exploit shortage of liberties to capture                    | ダメヅマリ (damezumari)   |
| `connect-and-die`  | Connect & Die    | Opponent's stones connect but still get captured            | 追い落とし (oiotoshi)     |
| `under-the-stones` | Under the Stones | Capture stones then play in the space they occupied         | 石の下 (ishi no shita)    |
| `double-atari`     | Double Atari     | Simultaneous atari on two groups                            | 両アタリ (ryō-atari)      |
| `vital-point`      | Vital Point      | Interior placement to reduce eyes or liberties              | 急所 (kyūsho)             |
| `clamp`            | Clamp            | Attachment reducing opponent's eye space from inside        | ハサミツケ (hasamitsuke)  |
| `tesuji`           | Tesuji           | General tactical move or brilliant play                     | 手筋 (tesuji)             |
| `nakade`           | Nakade           | Killing technique using vital point inside opponent's group | ナカデ (nakade)           |

---

## Coverage Model

Tag assignment combines three signal types:

1. **Source metadata**: Category and theme metadata supplied during ingest.
2. **Comment keywords**: Whole-word English and Japanese keyword matches.
3. **Board verification**: Rule-checked detection for a small subset of techniques.

Board verification is currently limited to `ko`, `ladder`, and `snapback`. All other tags rely on source metadata and/or comments.

---

## Aliases

Aliases are defined in `config/tags.json` and normalized to canonical tag IDs during processing.

Use `config/tags.json` as the only source of truth for alias mappings. This document intentionally avoids listing alias examples so it stays accurate as mappings evolve.

---

## Tag Detection

> **See also**: [Architecture: Tagging Strategy](../architecture/backend/tagging-strategy.md) — Full design rationale, confidence system, and detector algorithms

The pipeline detects tags using a **precision-over-recall** approach — a misleading tag is worse than no tag. Only HIGH-confidence detections are emitted.

1. **Source metadata** — Adapter-specific mappings from ingest metadata. Source tags are **preserved** as the primary classification signal.
2. **Comment keywords** — English and Japanese keywords matched as **whole words** (no substring false positives). HIGH confidence.
3. **Board pattern analysis** — Only three techniques are board-verified:
   - **Ko** — Board's built-in `_ko_point` detection (Go rules verified)
   - **Ladder** — 3+ chase move simulation using `Board.play()`
   - **Snapback** — Sacrifice-recapture geometry check
4. **No fallback** — Empty tag list is valid. The previous `life-and-death` fallback was removed because not all tsumego are life-and-death problems.

All detected tags are validated against `config/tags.json` before being written to the `YT` property.

---

## Referential Pattern (SGF → config)

Tags follow a strict referential pattern:

1. SGF stores only canonical IDs in `YT`.
2. `config/tags.json` defines canonical metadata.

Key principle: **SGF files contain only tag IDs**. Display metadata can evolve in config without re-processing SGF files.

---

## Adding New Tags

1. Get 1P Go player approval for the new tag
2. Add to `config/tags.json` with `id`, `name`, `category`, `description`, `aliases`
3. Update adapter mappings in `tools/` modules that perform tag normalization/mapping
4. Update tagger detection in `backend/puzzle_manager/core/tagger.py` if applicable
5. Update this documentation
6. Run `pytest -m unit -k tag` to validate
