# Hitachi Tsumego Archive — Research & Discovery Log

## Collection Overview
- **Title**: Tsumego - Life and Death Problems of Go by Minoru Harada
- **Source**: hitachi.co.jp/Sp/tsumego/ (discontinued, archived on Wayback Machine)
- **Scope**: No.1 (1996-04-22) through No.1182 (2019), 25 years of weekly problems
- **Author**: Minoru Harada (原田 実) — likely strong amateur under Hitachi contract
- **Format**: GIF images only (no SGF anywhere in the archive)

## Site Structure
```
index-e.html → [1996-e.html ... 2020-e.html]  (25 year pages)
  └→ Each year: No.X (M/D) → Problem page + Answer page
       └→ Problem: Elementary GIF + Intermediate GIF
       └→ Answer: Correct GIF + Wrong answer GIF(s) + text explanation
```

## HTML Format Changes
| Period | Year Page Format | Problem/Answer URL Pattern |
|--------|-----------------|--------------------------|
| 1996-2007 | `<table><td>` cells | `igo{NNN}/{NNN}pe.htm`, `igo{NNN+1}/{NNN}ae.htm` |
| 2008+ | `<dl><dt>/<dd>` lists | `igo{NNN}/{NNN}pe.html`, `igo{NNN}/{NNN}ae.html` |
| 2015+ (redesign) | Same `<dl>` format | `igo{NNNN}/problems-e.htm`, `igo{NNNN}/answers-e.htm` |

## Image Naming Conventions
### Standard format (No.6+):
- `{NNN}ep.gif` — Elementary problem
- `{NNN}mp.gif` — Intermediate problem
- `{NNN}ea{V}.gif` — Elementary correct answer (V=variant number)
- `{NNN}ew{V}.gif` — Elementary wrong answer
- `{NNN}ma{V}.gif` — Intermediate correct answer
- `{NNN}mw{V}.gif` — Intermediate wrong answer

### Early format (No.1-5): Non-standard naming, e.g., `4p2.gif`, `4c2.gif`

## Image Characteristics
- Format: GIF89a
- Size: ~12KB-35KB per image
- Content: Clean, computer-generated partial board diagrams
- Grid: Visible grid lines with black/white stones
- Answer images: Numbered move sequences (1, 2, 3...)

## Go-Advisor Assessment (Cho Chikun persona)
- Pedagogical quality: 8/10
- Difficulty: Elementary ≈ 25k-16k, Intermediate ≈ 20k-11k
- Uniqueness: HIGH — no known SGF digitization exists
- Recommendation: Digitize (pilot 50 problems first)
- Copyright warning: Hitachi, Ltd. owns copyright

## Image-to-SGF Libraries
| Library | Stars | Notes |
|---------|-------|-------|
| `skolchin/gbr` | 82 | OpenCV HoughLines/Circles, works on computer boards |
| `daniel-bandstra/watchGo` | 53 | OpenCV, finds board in images |

## Discovery Results (2026-04-09)
- Years found: 25 (1996-2020)
- Puzzles cataloged: 1,182
- 2020 page: Not properly archived (404)
- All year pages cached locally

## Known Issues
- Early problems (No.1-5) have non-standard image naming
- Some Wayback captures may be incomplete (newer years)
- Image classification for early puzzles shows as "answer_unknown"
