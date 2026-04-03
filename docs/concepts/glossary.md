# Go/Tsumego Glossary

> **See also**:
>
> - [Concepts: Tags](./tags.md) — Technique classification
> - [Concepts: SGF Properties](./sgf-properties.md) — SGF format

**Last Updated**: 2026-03-20

Common Go (Baduk) and tsumego terminology used in YenGo.

---

## Core Concepts

### Game Terms

| Term             | Japanese          | Description                    |
| ---------------- | ----------------- | ------------------------------ |
| **Go**           | 囲碁 (igo)        | The game (also: Baduk, Weiqi)  |
| **Stone**        | 石 (ishi)         | A playing piece                |
| **Board**        | 碁盤 (goban)      | The playing surface            |
| **Intersection** | -                 | Point where stones are placed  |
| **Liberty**      | 呼吸点 (kokyūten) | Empty adjacent point           |
| **Group**        | 石の塊            | Connected stones of same color |
| **Territory**    | 地 (ji)           | Controlled empty points        |

### Life and Death

| Term          | Japanese | Description                |
| ------------- | -------- | -------------------------- |
| **Tsumego**   | 詰碁     | Life-and-death puzzle      |
| **Eye**       | 眼 (me)  | Protected empty point      |
| **Two eyes**  | 二眼     | Living shape requirement   |
| **False eye** | 欠け目   | Non-working eye            |
| **Seki**      | セキ     | Mutual life (no eyes)      |
| **Ko**        | コウ     | Repeated capture situation |

---

## Capturing Techniques

| Term         | Japanese                  | Description                |
| ------------ | ------------------------- | -------------------------- |
| **Atari**    | アタリ                    | One liberty left           |
| **Ladder**   | シチョウ (shicho)         | Diagonal chase capture     |
| **Net**      | ゲタ (geta)               | Loose surrounding capture  |
| **Snapback** | ウッテガエシ (uttegaeshi) | Sacrifice and recapture    |
| **Throw-in** | ホウリコミ (horikomi)     | Liberty-reducing sacrifice |
| **Squeeze**  | ダメヅマリ (damezumari)   | Shortage of liberties      |

---

## Connection Techniques

| Term             | Japanese        | Description              |
| ---------------- | --------------- | ------------------------ |
| **Connect**      | ツグ (tsugu)    | Join groups              |
| **Cut**          | キリ (kiri)     | Separate groups          |
| **Peep**         | ノゾキ (nozoki) | Threatens to cut         |
| **Bamboo joint** | -               | Tiger's mouth connection |

---

## Move Types

| Term           | Japanese            | Description           |
| -------------- | ------------------- | --------------------- |
| **Tesuji**     | 手筋                | Clever tactical move  |
| **Hane**       | ハネ                | Diagonal wrap         |
| **Attachment** | ツケ (tsuke)        | Direct contact        |
| **Placement**  | ウチコミ (uchikomi) | Inside enemy group    |
| **Descent**    | サガリ (sagari)     | Move toward edge      |
| **Wedge**      | ワリコミ (warikomi) | Insert between stones |

---

## Problem Types

| Term               | Description                 |
| ------------------ | --------------------------- |
| **Life & death**   | Kill or save a group        |
| **Tesuji**         | Find the clever move        |
| **Capturing race** | Semeai - who captures first |
| **Connection**     | Connect or cut groups       |
| **Escape**         | Save a surrounded group     |

---

## SGF Terms

| Term          | Description                 |
| ------------- | --------------------------- |
| **SGF**       | Smart Game Format (.sgf)    |
| **Node**      | A position/move in SGF      |
| **Variation** | Alternative move sequence   |
| **Comment**   | Text annotation in SGF      |
| **Property**  | SGF metadata (e.g., `YG[]`) |

### SGF Coordinates

SGF uses `aa` to `ss` for 19x19 boards:

- `aa` = top-left corner (A19)
- `ss` = bottom-right corner (T1)
- Letters: columns a-s (left to right)
- Letters: rows a-s (top to bottom)

Example: `cg` = column C, row 7

---

## Difficulty Terms

| Term    | Japanese | Description                |
| ------- | -------- | -------------------------- |
| **Kyu** | 級       | Student rank (30k-1k)      |
| **Dan** | 段       | Master rank (1d-9d)        |
| **DDK** | -        | Double-digit kyu (10k-30k) |
| **SDK** | -        | Single-digit kyu (1k-9k)   |
| **Pro** | -        | Professional level         |

---

## Japanese Numbers

Common in puzzle naming:

| Number | Kanji | Reading |
| ------ | ----- | ------- |
| 1      | 一    | ichi    |
| 2      | 二    | ni      |
| 3      | 三    | san     |
| 4      | 四    | shi/yon |
| 5      | 五    | go      |
| 10     | 十    | jū      |
| 100    | 百    | hyaku   |

---

## Board Positions

| Term           | Description               |
| -------------- | ------------------------- |
| **Corner**     | Four corner areas         |
| **Side**       | Four edge areas           |
| **Center**     | Middle of board           |
| **Star point** | Marked intersections      |
| **3-3 point**  | San-san (corner invasion) |
| **4-4 point**  | Hoshi (star point corner) |

---

## Related Resources

- [Sensei's Library](https://senseis.xmp.net/) — Go encyclopedia
- [Go Terms Dictionary](https://www.britgo.org/glossary) — British Go Association
