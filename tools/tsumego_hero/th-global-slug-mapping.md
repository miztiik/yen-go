# Tsumego Hero → Global Collection Slug Mapping

> **Decision document.** Review each row and tell me the action: `map`, `new`, `merge`, or `drop`.
> 
> - **map** = assign to existing global slug (already in `config/collections.json`)
> - **new** = create a new entry in `config/collections.json`
> - **merge** = combine with another TH collection under one slug
> - **drop** = exclude from collection mapping (puzzles stay in `_uncollected`)

## Current State

- **TH curated collections**: 65
- **Global config entries**: 186
- **Currently matched**: 4 of 65 (see MATCHED section)
- **Unmatched**: 61 (need your decision)

---

## MATCHED (4) — already mapped, no action needed

| # | TH Slug | TH Name | Puz | Global Slug | Match Method |
|---|---------|---------|-----|-------------|-------------|
| 1 | `easy-capture` | Easy Capture | 200 | `capture-problems` (id=3) | bridge |
| 9 | `kanzufu` | Kanzufu | 144 | `guanzi-pu` (id=27) | alias |
| 21 | `xuanxuan-qijing` | Xuanxuan Qijing | 200 | `xuanxuan-qijing` (id=67) | slug |
| 43 | `tesuji-training` | Tesuji Training | 200 | `tesuji-training` (id=62) | slug |

---

## TIER A — Must-Have (17 unmatched)

### Classical Books (likely need new global entries)

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 4 | `gokyo-1` | Gokyo Shumyo I | 100 | `gokyo-shumyo` (id=26) | YES | Could merge #4-7 into one |
| 5 | `gokyo-shumyo-ii` | Gokyo Shumyo II | 68 | `gokyo-shumyo` (id=26) | YES | |
| 6 | `gokyo-shumyo-iii` | Gokyo Shumyo III | 75 | `gokyo-shumyo` (id=26) | YES | |
| 7 | `gokyo-shumyo-iv` | Gokyo Shumyo IV | 200 | `gokyo-shumyo` (id=26) | YES | |
| 8 | `hatsuyoron` | Igo Hatsuyoron | 65 | `igo-hatsuyoron` (id=36) | YES | |
| 10 | `kanzufu-tesuji` | Kanzufu - Tesuji | 155 | `guanzi-pu` (id=27) or NEW? | ? | Tesuji section of Guanzipu |
| 18 | `tsumego-dict-1` | Tsumego Dictionary Vol I | 200 | NEW `tsumego-dictionary` | NO | |
| 19 | `tsumego-dict-2` | Tsumego Dictionary Vol II | 200 | NEW `tsumego-dictionary` | NO | Merge #18-20 into one? |
| 20 | `tsumego-dictionary-volume-iii` | Tsumego Dictionary Vol III | 200 | NEW `tsumego-dictionary` | NO | |

### Korean Collections

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 11 | `korean-problem-academy-3` | Korean Problem Academy 3 | 150 | `korean-problem-academy-1` (id=137)? | PARTIAL | Global has "Vol. 1" only |
| 12 | `korean-problem-academy-4` | Korean Problem Academy 4 | 200 | NEW or expand id=137? | ? | |
| 13 | `kpa-1` | Korean Problem Academy 1 | 200 | `korean-problem-academy-1` (id=137) | YES | |
| 14 | `kpa-2` | Korean Problem Academy 2 | 200 | NEW `korean-problem-academy-2`? | NO | |

### Life & Death Series

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 15 | `lad-advanced` | Life & Death - Advanced | 200 | `life-and-death` (id=47)? | YES | Generic bucket, or NEW per tier? |
| 16 | `lad-elementary` | Life & Death - Elementary | 200 | `life-and-death` (id=47)? | YES | |
| 17 | `lad-intermediate` | Life & Death - Intermediate | 200 | `life-and-death` (id=47)? | YES | |

---

## TIER B — Good (27 unmatched)

### Known Authors / Series

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 32 | `kano-yoshinori-volume-1` | Kano Yoshinori Volume 1 | 200 | `kano-yoshinori-graded-go-problems-beginners-1` (id=85)? | PARTIAL | Global has Vol 1 only. Or merge #32-35 into new? |
| 33 | `kano-yoshinori-volume-2` | Kano Yoshinori Volume 2 | 200 | NEW `kano-yoshinori-volume-2`? | NO | |
| 34 | `kano-yoshinori-volume-3` | Kano Yoshinori Volume 3 | 200 | NEW `kano-yoshinori-volume-3`? | NO | |
| 35 | `kano-yoshinori-volume-4` | Kano Yoshinori Volume 4 | 118 | NEW `kano-yoshinori-volume-4`? | NO | |
| 41 | `segoe-tesuji-dictionary-part-1` | Segoe Tesuji Dict Part 1 | 200 | `segoe-kensaku-tesuji-dictionary` (id=58) | YES | |
| 40 | `secret-by-kim-jiseok` | Secret by Kim Jiseok | 53 | NEW `kim-jiseok-tsumego`? | NO | |
| 49 | `yi-kuo` | Yi Kuo | 200 | NEW `yi-kuo`? | NO | |

### Themed Collections

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 2 | `easy-kill` | Easy Kill | 200 | `kill-problems` (id=41)? | YES | |
| 3 | `easy-life` | Easy Life | 200 | `life-and-death` (id=47)? | YES | |
| 22 | `1000-weiqi-problems-1st-half` | 1000 Weiqi problems 1st half | 200 | NEW `1000-weiqi-problems`? | NO | Merge #22-23 |
| 23 | `1000-weiqi-problems-2nd-half` | 1000 Weiqi problems 2nd half | 198 | NEW or merge with #22? | | |
| 24 | `attack-hero` | Attack Hero | 145 | NEW? | NO | TH original |
| 25 | `beautiful-tsumego` | Beautiful Tsumego | 200 | NEW `beautiful-tsumego`? | NO | |
| 26 | `blind-spot` | Blind Spot | 30 | NEW? | NO | TH original |
| 27 | `boundless-sky` | Boundless Sky | 100 | NEW `boundless-sky`? | NO | |
| 28 | `diabolical` | Diabolical | 100 | NEW? | NO | TH original, very deep |
| 29 | `direction-of-the-play` | Direction of the Play | 69 | `kajiwara-direction-of-play` (id=134)? | YES-ish | Same concept, diff source? |
| 30 | `endgame-tesujis` | Endgame Tesujis | 200 | `endgame-problems` (id=15)? | YES | |
| 31 | `hong-dojo` | Secret Tsumego from Hong Dojo | 105 | NEW `hong-dojo-tsumego`? | NO | |
| 36 | `ko-gems` | Ko Gems | 50 | `ko-problems` (id=42)? | YES | Or NEW? |
| 37 | `level-evaluation-set-beginner` | Level Evaluation Set: Beginner | 200 | NEW? | NO | TH original |
| 38 | `problems-from-professional-games` | Problems from Professional Games | 45 | NEW? | NO | |
| 39 | `sacrificial-tsumego` | Sacrificial Tsumego | 136 | `sacrifice-techniques` (id=57)? | YES | |
| 42 | `single-digit-kyu-problems` | Single-Digit-Kyu Problems | 100 | NEW? | NO | TH original |
| 44 | `tesujis-in-real-board-positions` | Tesujis in Real Board Positions | 120 | NEW? | NO | |
| 45 | `tsumego-grandmaster` | Tsumego Grandmaster | 101 | NEW? | NO | TH original |
| 46 | `tsumego-master` | Tsumego Master | 200 | NEW? | NO | TH original |
| 47 | `tsumego-of-fortitude` | Tsumego of Fortitude | 142 | NEW `tsumego-of-fortitude`? | NO | |
| 48 | `weiqi-life-death-drills` | Weiqi Life&Death Drills | 145 | `life-and-death` (id=47)? | YES | Or NEW? |

---

## TIER C — Marginal (16 unmatched)

### Board Size Variants

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 52 | `4x4-problems` | 4x4 Problems | 119 | NEW `small-board-problems`? | NO | Merge #52-53? (none downloaded for 4x4) |
| 53 | `5x5-problems` | 5x5 Problems | 105 | NEW `small-board-problems`? | NO | |
| 54 | `9x9-endgame-problems` | 9x9 Endgame Problems | 181 | `endgame-problems` (id=15)? | YES | Or NEW? |
| 50 | `13x13-endgame-problems-difficult` | 13x13 Endgame (difficult) | 47 | NEW `13x13-endgame`? | NO | Merge #50-51? |
| 51 | `13x13-endgame-problems-easy` | 13x13 Endgame (easy) | 50 | NEW `13x13-endgame`? | NO | |

### French / Regional

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Exists? | Notes |
|---|---------|---------|-----|----------------------|---------|-------|
| 56 | `french-advanced` | French Go Review - Advanced | 32 | NEW `french-go-review`? | NO | Merge #56-58? |
| 57 | `french-easy` | French Go Review - Easy | 38 | NEW `french-go-review`? | NO | |
| 58 | `french-intermediate` | French Go Review - Intermediate | 58 | NEW `french-go-review`? | NO | |

### TH Originals (Small)

| # | TH Slug | TH Name | Puz | Suggested Global Slug | Notes |
|---|---------|---------|-----|----------------------|-------|
| 55 | `carnage` | Carnage | 12 | NEW? or drop? | TH original, very small |
| 59 | `giants` | Giants | 13 | NEW? or drop? | TH original, very small |
| 60 | `hunting` | Hunting | 17 | NEW? or drop? | TH original, very small |
| 61 | `pretty-area` | Pretty Area | 20 | NEW? or drop? | TH original, very small |
| 62 | `the-ghost` | The Ghost | 1 | drop? | 1 puzzle |
| 63 | `the-j-group` | The J Group | 22 | NEW `j-group`? | Shape problems |
| 64 | `the-l-group` | The L Group | 46 | NEW `l-group`? | Shape problems |
| 65 | `the-rules-of-capturing-races` | The Rules of Capturing Races | 200 | `capturing-race` (id=4)? | Or NEW `capturing-races-unsolved` |

---

## NEW: No-Solution Collection

| TH Slug | Name | Puz | Action |
|---------|------|-----|--------|
| (from #65) | Capturing Races Unsolved | 200 | NEW `capturing-races-unsolved` — board positions only, no solution tree |

---

## Summary of Decisions Needed

1. **Gokyo Shumyo I-IV** (#4-7): All → `gokyo-shumyo` (id=26)? Or keep separate?
2. **Tsumego Dict I-III** (#18-20): Merge into NEW `tsumego-dictionary`? Or separate?
3. **KPA 1-4** (#11-14): Map #13 to existing id=137, create new for #14, #11, #12?
4. **L&D Elem/Int/Adv** (#15-17): All → `life-and-death` (id=47)? Or keep level-separated?
5. **Kano Vol 1-4** (#32-35): Map #32 to existing id=85? Or create new per-volume?
6. **Small board** (#52-53): Merge into `small-board-problems`?
7. **13x13 endgame** (#50-51): Merge into `13x13-endgame`?
8. **French Go Review** (#56-58): Merge into `french-go-review`?
9. **Tiny originals** (#55, 59-62): Drop the 1-20 puzzle collections? Or bundle into `th-originals`?
10. **Capturing Races** (#65): → `capturing-race` (id=4) or NEW `capturing-races-unsolved`?
