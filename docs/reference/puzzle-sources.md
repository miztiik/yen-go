# Puzzle Sources Catalog

Complete catalog of external puzzle sources used in Yen-Go.

---

## Primary Sources

### 1. travisgk/tsumego-pdf

| Field               | Value                                     |
| ------------------- | ----------------------------------------- |
| **Repository**      | <https://github.com/travisgk/tsumego-pdf> |
| **Format**          | Custom text + SGF                         |
| **Solutions**       | ✅ Embedded                               |
| **Estimated Count** | ~4,000                                    |
| **License**         | Check repository                          |

**Collections**:

| Collection       | File                   | Count | Level |
| ---------------- | ---------------------- | ----- | ----- |
| Cho Elementary   | `cho-elementary.txt`   | 900   | 1-2   |
| Cho Intermediate | `cho-intermediate.txt` | 900   | 2-3   |
| Cho Advanced     | `cho-advanced.txt`     | 900   | 3-4   |
| Gokyo Shumyo     | `gokyo-shumyo.txt`     | ~500  | 3-5   |
| Xuanxuan Qijing  | `xuanxuan-qijing.txt`  | 347   | 4-5   |
| Igo Hatsuyoron   | `igo-hatsuyoron.txt`   | 183   | 5     |

**Reusable Code**:

- `load_sgf.py` - SGF parsing
- `problems_json.py` - Problem loading
- `playout.py` - Solution validation

---

### 2. sanderland/tsumego

| Field               | Value                                   |
| ------------------- | --------------------------------------- |
| **Repository**      | <https://github.com/sanderland/tsumego> |
| **Format**          | JSON (SGF-derived)                      |
| **Solutions**       | ✅ SOL field                            |
| **Estimated Count** | ~10,000+                                |
| **License**         | Check repository                        |

**JSON Structure**:

```json
{
  "AB": ["eb", "fb", "bc"],
  "AW": ["da", "ab", "bb"],
  "SZ": "19",
  "C": "Black to play",
  "SOL": [["B", "ba", "Correct.", ""]]
}
```

**Collections**:

| Folder                           | Contents                | Level |
| -------------------------------- | ----------------------- | ----- |
| `1a. Tsumego Beginner/`          | Cho, Fujisawa, Ishigure | 1     |
| `1b. Tsumego Intermediate/`      | Mid-level               | 2-3   |
| `1c. Tsumego Advanced/`          | Hard                    | 3-4   |
| `1d. Hashimoto Utaro/`           | Classic                 | 3-4   |
| `2a. Tesuji/`                    | Techniques              | 2-4   |
| `2b. Lee Changho Tesuji/`        | Modern                  | 2-4   |
| `2c. Great Tesuji Encyclopedia/` | Comprehensive           | 2-5   |

---

### 3. kisvadim/goproblems

| Field               | Value                                    |
| ------------------- | ---------------------------------------- |
| **Repository**      | <https://github.com/kisvadim/goproblems> |
| **Format**          | SGF                                      |
| **Solutions**       | ✅ Full trees                            |
| **Estimated Count** | 18,276                                   |
| **License**         | Check repository                         |

**Features**: 63 collections from professional masters.

---

### 4. gogameguru/go-problems

| Field               | Value                                       |
| ------------------- | ------------------------------------------- |
| **Repository**      | <https://github.com/gogameguru/go-problems> |
| **Format**          | SGF with variations                         |
| **Solutions**       | ✅ Rich trees + comments                    |
| **Estimated Count** | 422                                         |
| **License**         | Creative Commons                            |

**Quality**: Curated by An Younggil 8 dan pro.

**Structure**:

```text
weekly-go-problems/
├── easy/           # ~140 SGF
├── intermediate/   # ~140 SGF
├── hard/           # ~140 SGF
└── other/
```

---

### 5. blacktoplay.com

| Field               | Value                                                |
| ------------------- | ---------------------------------------------------- |
| **Website**         | <https://blacktoplay.com>                            |
| **Format**          | Proprietary JSON API                                 |
| **Solutions**       | ✅ Full trees                                        |
| **Estimated Count** | ~2,400                                               |
| **Features**        | Crowd-validated, 167 technique tags, position hashes |

---

### 6. Online-Go.com (OGS)

| Field               | Value                                               |
| ------------------- | --------------------------------------------------- |
| **Website**         | <https://online-go.com>                             |
| **API**             | <https://online-go.com/api/v1/puzzles/>             |
| **Format**          | JSON API (SGF via puzzle_data)                      |
| **Solutions**       | ✅ Full variation trees                             |
| **Estimated Count** | 58,000+                                             |
| **License**         | Check individual puzzle attribution                 |
| **Ingestion**       | Via standalone tool: `tools/ogs/` (adapter retired) |

**API Features**:

- RESTful pagination with `page` and `page_size` params
- Filter by `type` (life_and_death, fuseki, tesuji, best_move, joseki, endgame)
- Filter by `collection` ID
- Public access (no API key required)
- Rate limit: ~60 requests/minute

**Tool Usage** (replaces former adapter):

```bash
python -m tools.ogs --help
```

**Checkpointing**: Supports resume on interruption via checkpoint files.

---

### 7. 101books/101books.github.io

| Field               | Value                                            |
| ------------------- | ------------------------------------------------ |
| **Repository**      | <https://github.com/101books/101books.github.io> |
| **Format**          | SGF extracted from 101weiqi.com                  |
| **Estimated Count** | ~13,000 (60 books)                               |
| **License**         | Check repository                                 |

---

## User-Uploaded Puzzles

| Field          | Value                      |
| -------------- | -------------------------- |
| **Source ID**  | `user-upload`              |
| **Format**     | SGF (submitted via web UI) |
| **Solutions**  | ✅ Required                |
| **Validation** | Validated via pipeline     |

**Upload Flow**:

1. User submits SGF via upload interface
2. SGF stored in staging area
3. Pipeline validates solution correctness
4. Pipeline classifies difficulty automatically
5. Pipeline assigns technique tags
6. Validated puzzle merged to main collection

**Validation Criteria**:

- SGF must parse successfully
- Solution must be verifiable
- Solution depth ≤ 7 moves
- Single optimal solution (not ambiguous)

---

## Potential Future Sources

### smargo (Sun-Yize/smargo)

| Field             | Value                                |
| ----------------- | ------------------------------------ |
| **Repository**    | <https://github.com/Sun-Yize/smargo> |
| **Format**        | JSON                                 |
| **Purpose**       | MCTS-based tsumego solver + dataset  |
| **Dataset Count** | smargo_30 (~30k), smargo_50 (~50k)   |

---

## Reference Sites

| URL                                               | Description           |
| ------------------------------------------------- | --------------------- |
| <https://senseis.xmp.net>                         | Go encyclopedia       |
| <https://www.red-bean.com/sgf/>                   | SGF FF4 specification |
| <https://senseis.xmp.net/?XuanxuanQijingProblems> | Xuanxuan Qijing wiki  |
| <https://senseis.xmp.net/?GokyoShumyoTsumego>     | Gokyo Shumyo wiki     |

---

## Classical Collections (Reference)

| URL                                    | Description                    |
| -------------------------------------- | ------------------------------ |
| <http://www.u-go.net/classic/>         | Classical SGF collections      |
| <http://dl.u-go.net/problems/xxqj.zip> | Xuanxuan Qijing (347 problems) |
| <http://tsumego.tasuki.org/xxqj.pdf>   | Xuanxuan Qijing PDF            |
| <http://tsumego.tasuki.org/gksy.pdf>   | Gokyo Shumyo (520 problems)    |
| <http://eidogo.com/problems>           | EidoGo interactive             |

---

## Difficulty Mapping

| Source Difficulty | YenGo Level | Rank Range  |
| ----------------- | ----------- | ----------- |
| Elementary/Easy   | 1-2         | DDK30-DDK20 |
| Low-Intermediate  | 3-4         | DDK20-DDK10 |
| High-Intermediate | 5-6         | DDK10-SDK   |
| Advanced          | 7-8         | SDK-Dan     |
| Expert/Hard       | 9           | Dan-Pro     |

---

## Solutions Status

| Source      | Has Solutions | Format           |
| ----------- | ------------- | ---------------- |
| travisgk    | ✅            | Custom notation  |
| sanderland  | ✅            | JSON SOL array   |
| gogameguru  | ✅            | Full SGF tree    |
| blacktoplay | ✅            | API response     |
| ogs         | ✅            | JSON puzzle_data |
| kisvadim    | ✅            | SGF variations   |

---

## Adding New Sources

When adding a new source:

1. Add entry to this document with all metadata
2. Create adapter in `backend/puzzle_manager/adapters/`
3. Register in `backend/puzzle_manager/config/sources.json`
4. Test with `python -m backend.puzzle_manager sources`
5. Run import: `python -m backend.puzzle_manager run --source <id> --stage ingest`

See [How-To: Create Adapter](../how-to/backend/create-adapter.md) for details.

---

## See Also

- [How-To: Create Adapter](../how-to/backend/create-adapter.md) — Add sources guide
- [Architecture: Adapters](../architecture/backend/adapters.md) — Adapter architecture
- [Concepts: Tags](../concepts/tags.md) — Tag reference
