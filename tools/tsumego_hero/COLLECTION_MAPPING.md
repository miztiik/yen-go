# Tsumego Hero Collection Mapping

> Decision record for how 65 Tsumego Hero (TH) collections are mapped to the
> global collection registry (`config/collections.json`) for YL[] embedding.
>
> Date: 2026-04-13

## Overview

| Metric | Count |
|--------|-------|
| Total TH collections (curated) | 65 |
| Mapped to existing global slugs | 20 |
| Mapped with new global entries | 6 new slugs |
| Renamed global entries | 2 |
| Merged into `general-practice` | 18 |
| Dropped | 1 |
| Uses chapter/subdirectory structure | 9 parent collections |
| Unique global slugs in output | 25 |

## Key Design Decisions

### 1. Numbered subdirectory convention

Multi-volume collections use a **numbered chapter prefix** for deterministic ordering:

```
kano-yoshinori-graded-go-problems/
  01-volume-1/      # Introductory (35-25k)
  02-volume-2/      # Elementary (25-20k)
  03-volume-3/      # Intermediate (20-15k)
  04-volume-4/      # Advanced (10k-1k)
```

The two-digit numeral prefix (`01-`, `02-`, ...) ensures:
- Filesystem `ls` always shows volumes in correct order.
- Adding future subdirectories is unambiguous (next number is obvious).
- The YL[] chapter maps 1:1 to the directory name: `YL[kano-yoshinori-graded-go-problems:01-volume-1/42]`.

### 2. Cho Chikun = Life & Death (TH naming)

TH's "Life & Death - Elementary/Intermediate/Advanced" are actually
**Cho Chikun's Encyclopedia of Life & Death** (趙治勲 基本死活事典).
Confirmed by puzzle content cross-reference with existing kisvadim imports.

| TH Slug | Global Slug | Global ID |
|---------|------------|-----------|
| `lad-elementary` | `cho-chikun-life-death-elementary` | 6 |
| `lad-intermediate` | `cho-chikun-life-death-intermediate` | 7 |
| `lad-advanced` | `cho-chikun-life-death-advanced` | 5 |

These are flat collections (no subdirectories) because each level is already
a separate global entry.

### 3. Kanzufu = Guanzi Pu (官子谱)

"Kanzufu" is the Japanese on'yomi reading of the Chinese classic Guanzi Pu (官子谱),
published by Guo Bailing in 1660, ~1,450 problems. The TH split is:
- `kanzufu` → life-and-death section → `guanzi-pu/01-life-death/`
- `kanzufu-tesuji` → tesuji section → `guanzi-pu/02-tesuji/`

### 4. Yi Kuo (弈括) — Classical text, keep standalone

Yi Kuo is by **Huang Longshi** (黄龙士, 1651-1700), a Qing Dynasty Go master.
Published 1710, contains 361 problems. This is a recognized classic on par with
Gokyo Shumyo and Xuanxuan Qijing. Assigned `tier: editorial`.

### 5. Korean Problem Academy — Published series, keep unified

A real 4-volume published series by Yangji Book (양지북) with ISBNs.
Digital solutions by Pierre Audouard. Well-known pedagogical resource.

Renamed from `korean-problem-academy-1` → `korean-problem-academy` with
volumes as chapters:
- `01-volume-1` (25-15k)
- `02-volume-2` (15-5k)
- `03-volume-3` (5k-1k)
- `04-volume-4` (1k-4d)

The stale mapping in `sources.json` (set_id 81="KPA 1" when website shows KPA 3)
is a pre-existing issue, not addressed here.

### 6. Kano Yoshinori — Renamed and unified

Renamed from `kano-yoshinori-graded-go-problems-beginners-1` (misleading "beginners")
to `kano-yoshinori-graded-go-problems`. The series covers:
- Vol 1: Introductory (35-25k)
- Vol 2: Elementary (25-20k)
- Vol 3: Intermediate (20-15k)
- Vol 4: Advanced (10k-1k)

### 7. Weiqi Problems — Merged from 1000-prefix

Removed the "1000" prefix. Three chapters under `weiqi-problems`:
- `01-first-half` (from `1000-weiqi-problems-1st-half`)
- `02-second-half` (from `1000-weiqi-problems-2nd-half`)
- `03-life-death-drills` (from `weiqi-life-death-drills`)

### 8. Small Board Problems — Unified by board size

All non-standard board sizes merged under one parent:
- `01-4x4` (0 files — all 404, irrecoverable)
- `02-5x5` (105 puzzles)
- `03-9x9` (180 puzzles)
- `04-13x13-easy` (50 puzzles)
- `05-13x13-hard` (47 puzzles)

### 9. general-practice bucket

18 collections merged into `general-practice` (id=127):
- **TH originals** (no published source): attack-hero, blind-spot, boundless-sky,
  diabolical, level-evaluation-set-beginner, single-digit-kyu-problems,
  tsumego-grandmaster, tsumego-master, tsumego-of-fortitude,
  tesujis-in-real-board-positions, problems-from-professional-games
- **Small Tier C originals**: carnage (12), giants (13), hunting (17),
  pretty-area (20), the-j-group (22), the-l-group (46)
- **French Go Review** (difficulty-split): french-easy (38),
  french-intermediate (58), french-advanced (32)
- **Hong Dojo**: Already an alias in general-practice
- **Beautiful Tsumego**: TH compilation, no provenance

### 10. Dropped

- `the-ghost`: 1 puzzle. Not worth tracking.

## Tsumego Dictionary

Author/provenance unknown. Kept as new entry `tsumego-dictionary` (id=188)
because the 3-volume structure and ~600 puzzles suggest a real published work.
If provenance is later identified, the slug and metadata should be updated.

## Capturing Races (Unsolved)

`capturing-races-unsolved` (id=193) contains 200 puzzles downloaded with
`min_solution_depth=0` from TH's "The Rules of Capturing Races" set.
These have **no pre-computed solutions** — they are for open-ended semeai practice.

Note: The existing `capturing-race` (id=4) is for standard semeai problems
WITH solutions. The `-unsolved` suffix distinguishes the two.

## Files

| File | Purpose |
|------|---------|
| `collection_slug_mapping.json` | Machine-readable mapping (65 entries) |
| `curated_collections.json` | TH collections with tier/level assignments |
| `curation_rules.json` | Tier assignments and merge/rename rules |
| `package_collections.py` | Builds `sgf-by-global-slug/` from mapping |
| `organize_collections.py` | Builds per-TH-slug manifests in `sgf-by-collection/` |

## Pipeline

```
1. scrape_collections.py     → local_collections.json (raw scrape)
2. curate_collections.py     → curated_collections.json (tier/level)
3. organize_collections.py   → sgf-by-collection/ (per-TH-slug manifests)
4. package_collections.py    → sgf-by-global-slug/ (final structure)
```

## YL[] Property Format

```
YL[global-slug]                           # flat collection
YL[global-slug:NN-chapter-name/position]  # chaptered collection
```

Examples:
```
YL[capture-problems]
YL[gokyo-shumyo:01-volume-i/15]
YL[kano-yoshinori-graded-go-problems:03-volume-3/42]
YL[korean-problem-academy:04-volume-4/100]
YL[small-board-problems:02-5x5/7]
YL[weiqi-problems:03-life-death-drills/8]
YL[general-practice]
```
