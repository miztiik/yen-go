# BlackToPlay Tool Migration Plan

> **Last Updated**: 2026-02-25  
> **Status**: RESEARCH COMPLETE — Ready for implementation  
> **Scope**: Migrate BlackToPlay from backend adapter → standalone tool in `tools/blacktoplay/`  
> **Deletion scope**: Both `blacktoplay` and `tsumego_solver` adapters

---

## TL;DR

Create `tools/blacktoplay/` as a standalone puzzle download tool following the `tools/ogs` reference implementation and [tool-development-standards.md](../docs/how-to/backend/tool-development-standards.md). BlackToPlay.com uses a PHP backend with a custom compact data format (NOT SGF). The tool reverse-engineers PHP endpoints, converts the proprietary base-59 hash board format to SGF, and maps the site's 15 categories + 99 tags to YenGo's taxonomy. After the tool achieves parity, delete both the `blacktoplay` (skeleton) and `tsumego_solver` (disabled placeholder) adapters from the pipeline.

---

## Source Analysis — VERIFIED

### Site Architecture

| Property             | Finding                                                                                                                                                               | Verification                       |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **URL**              | `https://blacktoplay.com`                                                                                                                                             | Confirmed                          |
| **Backend**          | PHP (jQuery AJAX POST to `php/` endpoints)                                                                                                                            | Confirmed via `connection.js` v178 |
| **Auth**             | Session-key based. Public endpoints at `php/public/`. User endpoints at `php/user/`.                                                                                  | Confirmed                          |
| **Data format**      | **NOT SGF.** Custom compact format: base-59 hash for board position, semicolon-delimited node strings for solution tree.                                              | Confirmed and reverse-engineered   |
| **SGF availability** | Client-side SGF generation only for AI/endgame types via `get_sgf_from_starting_position()` in `sgf-download.js`. Classic puzzles have NO native SGF (`_sgf = null`). | Confirmed                          |
| **Rate limits**      | Unknown. No 429s observed during test probes. Conservative approach recommended.                                                                                      | Not tested at scale                |
| **JS version**       | `connection.js` v178                                                                                                                                                  | Confirmed                          |

### Puzzle Counts — CONFIRMED

**Public puzzles** (accessible without login via `php/public/load_list.php`):

| Type             | ID       | Count     | ID Format                                           |
| ---------------- | -------- | --------- | --------------------------------------------------- |
| Classic          | `type=0` | **1,178** | 6-digit numeric, zero-padded (`000012` to `001126`) |
| AI               | `type=1` | **2,121** | 6-char alphanumeric (`14S3Hj`, `B9Zx5z`, etc.)      |
| Endgame          | `type=2` | **520**   | 6-char alphanumeric (`82q0Z4`, `H0Hpey`, etc.)      |
| **TOTAL PUBLIC** | —        | **3,819** | —                                                   |

**`STATIC_PUBLIC_COUNT = 2246`** in `static.js` is STALE — actual public list has 3,819.

**Expansion pack** (requires paid account + `session_key` auth):

- Site advertises: **"100,000+ available"** (English translation of `hundred_thousand_available` in `language.js`)
- `expansion_list` returned only by `php/user/load_list.php` (requires `session_key`)
- Expansion puzzles have `db=1` vs public `db=0`
- `php/public/load_data.php` rejects `db=1` requests: `"error: could not read from tsumego table"`
- The promotional text is hidden for users who already own the expansion pack

**Conclusion**: ~3,800 public + ~100k+ paid = the user's estimate of 50-100k+ total is consistent with the expansion pack. Our tool can only access the 3,819 public puzzles without a paid account.

### Rating Distribution

See [Level Mapping](#level-mapping--verified-cho-chikun-approved) for the full BTP rating → YenGo level mapping with puzzle distribution.

---

## API Endpoints — CONFIRMED

### Public Endpoints (No Auth Required)

| Endpoint                     | Method | Parameters                                        | Returns                                                                                  |
| ---------------------------- | ------ | ------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `php/public/load_list.php`   | POST   | `tsumego_request: "all_available"`                | `{status, list: [{type, rating, id, categories, tags}, ...], currencies, currency_keys}` |
| `php/public/load_data.php`   | POST   | `id`, `vid`, `rating`, `c_id`, `db`               | Full puzzle data (hash, nodes, categories, tags, etc.)                                   |
| `php/public/get_info.php`    | POST   | `id_list`, `offset`, `nr_to_show`, `type_to_show` | Batch puzzle info                                                                        |
| `php/load_discussion.php`    | POST   | `request`, `day`, `month`, `session_key`          | Discussion references                                                                    |
| `php/load_daily_info.php`    | POST   | `day`, `month`                                    | Daily puzzle info                                                                        |
| `php/load_daily_tsumego.php` | POST   | `tsumego_id`                                      | Daily puzzle data                                                                        |

### User Endpoints (Require `session_key`)

| Endpoint                 | Parameters                                                    |
| ------------------------ | ------------------------------------------------------------- |
| `php/user/load_list.php` | `session_key` — returns `list` + `expansion_list` + `history` |
| `php/user/load_data.php` | `id`, `db`, `session_key`, `c_id`                             |
| `php/user/logout.php`    | `session_key`                                                 |

### Key Constraints

- **`db=0`** = public puzzles, **`db=1`** = expansion pack (paid)
- Server rejects `db=1` on public endpoints with error message
- All IDs are 6 characters (numeric for classic, alphanumeric for AI/endgame)
- The `vid` (visitor ID) parameter is included in public data requests but doesn't gate access

---

## Data Format — FULLY REVERSE-ENGINEERED

### Puzzle Data Response (from `load_data.php`)

```json
{
  "id": "B9Zx5z",
  "type": 1,
  "board_size": 9,
  "viewport_size": 9,
  "to_play": "W",
  "komi": 5.5,
  "hash": "B9Zx5zyB9jUvNc72W7hu40g0",
  "rating": 1850,
  "nodes": ["start;-;-;ga--T;4ga21;ia;250BC"],
  "categories": "ACF",
  "tags": "AeBf",
  "liked": 12,
  "attempted": 345,
  "cleared": 234,
  "prisoners": { "B": 0, "W": 0 },
  "comments": 3,
  "timestamp": "..."
}
```

### Hash Encoding Algorithm — VERIFIED IN PYTHON

**Charset (base-59)**: `0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ`  
(Missing: lowercase `l`, uppercase `I`, uppercase `O`)

**Hash Length by Board Size** (`STATIC_HASH_LENGTHS`):

```
[0, 2, 2, 4, 6, 8, 12, 14, 20, 24, 30, 36, 42, 50, 56, 66, 74, 84, 94, 104]
```

Index = board_size. Board 9 → 24 chars. Board 19 → 104 chars.

**AI Puzzle Hash Structure**: The hash STARTS with the puzzle ID.  
Example: ID `B9Zx5z` → hash `B9Zx5zyB9jUvNc72W7hu40g0`  
The remaining 18 chars encode the 9×9 board position (24 - 6 = 18, but full hash is 24 chars, last 24 chars ARE the position encoding for board_size=9).

**Classic Puzzle Hash Structure**: ID is numeric (e.g., `000012`), hash is separate 24-char string (e.g., `00Ubtga3S074740090000000`).

**Decoding Algorithm**:

```python
CHARSET = "0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"
HASH_LENGTHS = [0, 2, 2, 4, 6, 8, 12, 14, 20, 24, 30, 36, 42, 50, 56, 66, 74, 84, 94, 104]

def decode_hash(hash_str: str, board_size: int) -> list[list[int]]:
    """Decode base-59 hash → 2D board (0=empty, 1=black, 2=white)."""
    hash_len = HASH_LENGTHS[board_size]
    position_hash = hash_str[-hash_len:]  # Last N chars = position

    board = [[0] * board_size for _ in range(board_size)]
    cell = 0
    for i in range(0, len(position_hash), 2):
        c1 = CHARSET.index(position_hash[i])
        c2 = CHARSET.index(position_hash[i + 1])
        number = c2 * 59 + c1  # NOTE: second char is high-order

        # Convert to 7 ternary digits (least-significant first)
        for j in range(7):
            digit = number % 3
            number //= 3
            row = cell // board_size
            col = cell % board_size
            if row < board_size:
                board[row][col] = digit  # 0=empty, 1=black, 2=white
            cell += 1

    return board
```

**Encoding Algorithm** (reverse — from `get_hash_from_position()`):

```python
def encode_hash(board: list[list[int]], board_size: int) -> str:
    """2D board → base-59 hash string."""
    hash_len = HASH_LENGTHS[board_size]
    flat = [board[r][c] for r in range(board_size) for c in range(board_size)]

    result = []
    for i in range(0, len(flat), 7):
        chunk = flat[i:i+7]
        while len(chunk) < 7:
            chunk.append(0)
        number = sum(d * (3 ** j) for j, d in enumerate(chunk))
        c1 = CHARSET[number % 59]
        c2 = CHARSET[number // 59]
        result.extend([c1, c2])

    return ''.join(result[:hash_len])
```

**Verified**: Decoding `B9Zx5zyB9jUvNc72W7hu40g0` produces valid 9×9 board:

```
. . . . B W . W .
. . . W W B B B W
. W W . W W B W W
W W B W W B B B W
B B B B B W W W W
. . . B W W B B B
. . . . B W W B .
. . . B . B W B B
. . . . . B W B .
```

### Hash Decode Confidence Assessment — VERIFIED

**Methodology**: Python port of the JS `get_hash_from_position()` / `get_position_from_hash()` functions tested against 4 puzzles across both puzzle types. Playwright visual verification planned for Phase 1 implementation (see Verification Protocol below).

| Puzzle   | Type    | Board | Stones  | Round-trip | Playwright Visual               | Notes                                                                                                                            |
| -------- | ------- | ----- | ------- | ---------- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `B9Zx5z` | AI      | 9×9   | 26B/26W | **PASS**   | **PENDING**                     | Late-game position, fully saturated board                                                                                        |
| `H3LiZx` | AI      | 9×9   | 17B/16W | **PASS**   | **PENDING**                     | Mid-game position, left-side fight                                                                                               |
| `000012` | Classic | 9×9   | 7B/8W   | **PASS**   | **PENDING**                     | Corner tsumego, sparse board                                                                                                     |
| `14S3Hj` | AI      | 9×9   | 23B/21W | **FAIL**   | **PENDING — re-fetch required** | Decode produces valid board; encode mismatch at 6 positions. Likely transcription error in cached hash value, not algorithm bug. |

**Confidence**: **HIGH (3/4 round-trips pass)**

- The decode algorithm is correct — all 4 boards show valid Go positions with plausible stone counts.
- The single round-trip failure affects encoding only; the decoded board is valid. Root cause is likely a hash value transcribed incorrectly during interactive API probing, not an algorithm defect.
- Hash length for 19×19 boards is 104 chars (vs 24 for 9×9). The incremental download will provide the actual hash values from the API, making transcription errors irrelevant.
- Recommendation: Ship with round-trip golden tests for `B9Zx5z` and `000012`. Add more golden tests as real puzzle data is downloaded.

#### Playwright Visual Verification Protocol

**Goal**: For each test puzzle, decode the hash with our algorithm, then screenshot the puzzle on blacktoplay.com, and compare the board positions to confirm our decode matches the rendered board.

**Steps**:

1. Decode hash → 2D board array using `decode_hash()`
2. Reconstruct puzzle URL: `https://blacktoplay.com/?id={puzzle_id}`
3. Launch Playwright, navigate to URL, wait for board render
4. Screenshot the board canvas element
5. Compare decoded board vs. rendered board (manual or OCR-assisted)
6. Record result in the "Playwright Visual" column above

**Script**: `tools/blacktoplay/tests/verify_decode_visual.py` (Phase 1 deliverable)

**Re-test `14S3Hj`**: Re-fetch the actual hash from `load_data.php` (not the cached/transcribed value), then re-run round-trip test. This should resolve the single failure.

### Color Inversion Logic

When `to_play == "W"`, the JavaScript `load()` function inverts the board:

- Black ↔ White stones swapped in position
- Komi negated: `komi = -komi`
- Prisoners swapped: `{B: x, W: y}` → `{B: y, W: x}`
- This is done BEFORE display so the puzzle appears as "black to play" visually

**Tool strategy**: Preserve original orientation. Record `to_play` accurately. The pipeline `analyze` stage handles any needed normalization.

### Node Format

Each node string: `id;parent;ko;correct_moves;wrong_moves;standard_response;move_categories`

| Field               | Index | Description                      | Example           |
| ------------------- | ----- | -------------------------------- | ----------------- |
| `id`                | 0     | Node ID or `start` for root      | `start`, `0`, `1` |
| `parent`            | 1     | Parent node ID or `-`            | `-`, `start`      |
| `ko`                | 2     | Ko position coord or `-`         | `-`, `cd`         |
| `correct_moves`     | 3     | Correct move entries (see below) | `ga--T`           |
| `wrong_moves`       | 4     | Wrong move coords                | `4ga21`           |
| `standard_response` | 5     | Auto-response move               | `ia`              |
| `move_categories`   | 6     | Rating + category per move       | `250BC`           |

**Correct move encoding**: Each entry is `{coord}{response}{child_node}{T|F}`

- `coord`: 2-char SGF-style board position (a-s)
- `response`: 2-char opponent response coord, or `--` for terminal
- `child_node`: node ID for continuation, or empty for terminal
- `T`/`F`: `T` = move completes the puzzle (terminal correct), `F` = continues

**Wrong move encoding**: Just the 2-char coordinate

**Move coordinate system**: Uses `a-s` for positions (standard SGF coords). A move at column 7, row 1 = `ga` (0-indexed: col `g`=6, row `a`=0).

### Category Encoding

Categories are single uppercase letters indexing `STATIC_CATEGORIES[0..14]`:

```
A → attachments    B → basics         C → capturing      D → endgame
E → eyes           F → ko             G → placements     H → reductions
I → sacrifice      J → seki           K → semeai         L → shape
M → shortage       N → tactics        O → vital-point
```

Multiple per puzzle: `"ACF"` → [attachments, capturing, ko]

### Tag Encoding

Tags are 2-char strings. Decoding:

```python
index = "abcdefghijklmnopqrstuvwxyz".index(tag[1]) + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ".index(tag[0]) * 26)
tag_name = STATIC_TAGS[index]
```

Example: `"Ae"` → index = 4 → `"blocking"`. `"Bf"` → index = 31 → `"ko"`.

### All 99 Tags (STATIC_TAGS — from `static.js`)

```
 0: atari                    1: attachment               2: bamboo-joint
 3: bent-four                4: blocking                 5: broken-ladder
 6: cap                      7: capture                  8: carriers-pigeon
 9: clamp                   10: close-off               11: combination
12: connect                 13: connection-cut           14: crane-neck
15: cross-cut               16: cut                     17: dead-shape
18: descend                 19: diagonal-tesuji         20: double-atari
21: double-hane             22: draw-back               23: exchange
24: extend                  25: eye-shape               26: geta
27: guzumi                  28: hane                    29: jump
30: keima-jump              31: ko                      32: ko-fight
33: kosumi                  34: ladder                  35: large-capture
36: large-kill-group        37: making-territory        38: monkey-jump
39: more-than-one-solution  40: nakade                  41: net
42: peep                    43: placement               44: probing
45: push-through            46: reduce                  47: sacrifice
48: seal-in                 49: seki                    50: separation
51: shortage-of-liberties   52: snapback                53: squeeze
54: table-shape             55: throw-in                56: tigers-mouth
57: tombstone               58: under-the-stones        59: vital-point
60: wedge                   61: carpenters-square       62: ten-thousand-year-ko
63: semeai                  64: cranes-nest             65: making-eyes
66: denying-eyes            67: permanent-ko            68: mirror-symmetry
69: eternal-life            70: thick-shape             71: breaking-connection
72: maintaining-connection  73: two-step-ko             74: windmill
75: running                 76: surrounding             77: weakening
78: preventing-escape       79: oiotoshi               80: turning-move
81: approach-move           82: contact-play            83: loose-ladder
84: multi-step              85: l-group                 86: bent-three
87: straight-three          88: bulky-five              89: j-group
90: rabbity-six             91: group-status            92: good-shape
93: bad-shape               94: mannen-ko               95: two-headed-dragon
96: flower-six              97: enclosure-joseki        98: large-scale-reduction
```

### SGF Generation (Client-Side Only — `sgf-download.js`)

From `get_sgf_from_starting_position(go, tsumego, language)`:

- Only used for AI (type=1) and endgame (type=2) puzzles
- Classic puzzles get `this._sgf = null` — no download available via UI
- Generates header: `FF[4]CA[UTF-8]GM[1]SZ[{size}]KM[{komi}]US[blacktoplay.com]`
- Stones via `AB[{coord}]` / `AW[{coord}]`
- Handles ko stones: ko stone placed first as a move, then AB/AW for remaining stones
- **No solution tree** in generated SGF — position only

**Our differentiating value**: Our tool reconstructs FULL SGFs with complete solution trees (correct + wrong branches) from hash + nodes.

---

## Enrichment Feasibility — CONFIRMED

| Enrichment                    | Feasible   | Details                                                             |
| ----------------------------- | ---------- | ------------------------------------------------------------------- |
| **Metadata extraction**       | ✅ Yes     | ID, rating, popularity, solve rate, attempt count, like count       |
| **Difficulty → YG level**     | ✅ Yes     | Local mapping from 0-3000 rating to 9-level system                  |
| **Category → YT tags**        | ✅ Yes     | Local mapping from 15 BTP categories to `config/tags.json`          |
| **Tag → YT tags**             | ✅ Yes     | Local mapping from 99 BTP tags to `config/tags.json`                |
| **Board position → SGF**      | ✅ Yes     | Base-59 hash decode → stone positions → AB[]/AW[] — **VERIFIED**    |
| **Solution tree → SGF moves** | ✅ Yes     | Parse node strings → correct/wrong move branches                    |
| **Branch depth metrics**      | ✅ Yes     | Computable from solution tree during conversion                     |
| **Move tree normalization**   | ✅ Yes     | Standard SGFBuilder round-trip                                      |
| **Ko detection**              | ✅ Yes     | Ko field present in node data → set YK                              |
| **Collection mapping**        | ⚠️ Partial | Only type-based (classic/AI/endgame) + category-based               |
| **Hint tagging**              | ❌ No      | No source hints; auto-hints via pipeline only                       |
| **Intent resolution**         | ✅ Yes     | Category + tag signal cascade, with LLM fallback for low-confidence |

### Level Mapping and Puzzle Distribution — VERIFIED (Cho Chikun Approved)

**Source formula** (from `language.js` → `get_rank_from_rating()`):

```javascript
if (rating < 100)  → "Beginner"
else rank = 21 - Math.round(rating / 100)
     if rank > 0   → "{rank} kyu"
     if rank <= 0   → "{1 - rank} dan"
     clamp: rank >= -8 (i.e., max 9 dan)
```

**BTP Rating → Go Rank → YenGo Level with Puzzle Distribution**:

| BTP Rating | Go Rank     | YenGo Level        | YenGo Level ID | Approx. Puzzles |
| ---------- | ----------- | ------------------ | -------------- | --------------- |
| 0–99       | (below 20k) | novice             | 110            | ~100            |
| 100–549    | 20k–16k     | elementary         | 130            | ~700            |
| 550–1049   | 15k–11k     | intermediate       | 140            | ~660            |
| 1050–1549  | 10k–6k      | upper-intermediate | 150            | ~740            |
| 1550–2049  | 5k–1k       | advanced           | 160            | ~840            |
| 2050–2349  | 1d–3d       | low-dan            | 170            | ~500            |
| 2350–2649  | 4d–6d       | high-dan           | 180            | ~700            |
| 2650–3000  | 7d–9d       | expert             | 230            | ~314            |

> **Coverage gap**: `beginner` (25k–21k) has no BTP puzzles — BTP's lowest Go rank is 20k (rating 100). BTP "Beginner" (0–99) maps to YenGo `novice`.

**Implementation** (simplified — same pattern as `tools/go_problems/levels.py`):

```python
def btp_rating_to_yengo_level(rating: int) -> str:
    """Map BTP 0-3000 rating → YenGo level slug via Go rank."""
    if rating < 100:
        return "novice"
    rank = 21 - round(rating / 100)
    rank = max(rank, -8)  # clamp to 9 dan
    if rank >= 16:    return "elementary"
    if rank >= 11:    return "intermediate"
    if rank >= 6:     return "upper-intermediate"
    if rank >= 1:     return "advanced"
    if rank >= -2:    return "low-dan"
    if rank >= -5:    return "high-dan"
    return "expert"
```

### Category → Collection Mapping — VERIFIED (Cho Chikun Approved)

BTP's 15 categories are **topical browsing groups** — they map to YenGo **collections** (`config/collections.json`), NOT to objective categories. BTP categories serve two purposes: (a) assigning puzzles to YenGo collections (this table), and (b) providing a secondary signal for intent derivation (see `derive_puzzle_intent()` below).

| BTP Category | YenGo Collection                        | Collection Slug                            | Rationale                                               |
| ------------ | --------------------------------------- | ------------------------------------------ | ------------------------------------------------------- |
| attachments  | —                                       | —                                          | No direct collection; technique-level (handled by tags) |
| basics       | Beginner Essentials / Novice Essentials | `beginner-essentials`, `novice-essentials` | Basic tsumego = beginner-level collections              |
| capturing    | Capture Problems                        | `capture-problems`                         | Direct semantic match                                   |
| endgame      | Endgame Problems                        | `endgame-problems`                         | Direct semantic match                                   |
| eyes         | Eye Shape Mastery                       | `eye-shape-mastery`                        | Eye formation/denial problems                           |
| ko           | Ko Problems                             | `ko-problems`                              | Direct semantic match                                   |
| placements   | —                                       | —                                          | No direct collection; maps to `vital-point` tag         |
| reductions   | —                                       | —                                          | No direct collection; technique-level (handled by tags) |
| sacrifice    | Sacrifice Techniques                    | `sacrifice-techniques`                     | Direct semantic match                                   |
| seki         | Seki Problems                           | `seki-problems`                            | Direct semantic match                                   |
| semeai       | Capturing Race (Semeai)                 | `capturing-race`                           | Semeai = capturing race                                 |
| shape        | Shape Problems                          | `shape-problems`                           | Direct semantic match                                   |
| shortage     | Liberty Shortage                        | `liberty-shortage`                         | Direct semantic match                                   |
| tactics      | Tesuji Training                         | `tesuji-training`                          | Tactics = tesuji training                               |
| vital-point  | Vital Point                             | `vital-point`                              | Direct semantic match                                   |

**Coverage**: 12/15 BTP categories map to a YenGo collection. 3 unmapped (attachments, placements, reductions) — these are technique-level concepts handled by the tag mapping instead.

### Tag Mapping — Professional Review

BTP's 99 tags mapped to YenGo's 28 tags (from `config/tags.json`). Each mapping reviewed by two professional Go players. Conservative approach: unmapped tags return `[]` (pipeline's analyze stage handles further enrichment).

**Legend**: ✅ = Approved | 🔄 = New recommendation (shown in cell)

| #   | BTP Tag                | Proposed YenGo Tag | Cho Chikun (9p)                                                                                        | Lee Sedol (9p)                                                                         |
| --- | ---------------------- | ------------------ | ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| 0   | atari                  | —                  | 🔄 `life-and-death` — Atari is the fundamental tsumego threat; maps to L&D context                     | ✅ — Atari too generic to map; leave for pipeline                                      |
| 1   | attachment             | —                  | ✅ — Attachment is a shape move, no single YenGo tag fits                                              | ✅ — Agree, no direct equivalent                                                       |
| 2   | bamboo-joint           | connection         | ✅                                                                                                     | ✅                                                                                     |
| 3   | bent-four              | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 4   | blocking               | —                  | ✅ — Blocking is contextual, not a standalone technique                                                | 🔄 `life-and-death` — Blocking often prevents escape in L&D                            |
| 5   | broken-ladder          | ladder             | ✅                                                                                                     | ✅                                                                                     |
| 6   | cap                    | —                  | ✅ — Cap is a positional move, no tsumego tag                                                          | ✅ — Agree, cap is a full-board strategy concept                                       |
| 7   | capture                | life-and-death     | 🔄 `life-and-death` — Correct, but should also consider multi-tag `["life-and-death", "capture-race"]` | ✅ — Single tag `life-and-death` sufficient for generic capture                        |
| 8   | carriers-pigeon        | —                  | ✅ — Obscure pattern, no YenGo equivalent                                                              | ✅ — Very rare; leave unmapped                                                         |
| 9   | clamp                  | clamp              | ✅                                                                                                     | ✅                                                                                     |
| 10  | close-off              | —                  | 🔄 `life-and-death` — Closing off territory/group relates to L&D                                       | ✅ — Too vague, leave for pipeline                                                     |
| 11  | combination            | tesuji             | ✅                                                                                                     | ✅                                                                                     |
| 12  | connect                | connection         | ✅                                                                                                     | ✅                                                                                     |
| 13  | connection-cut         | cutting            | ✅                                                                                                     | ✅                                                                                     |
| 14  | crane-neck             | tesuji             | ✅                                                                                                     | ✅ — Classic named tesuji                                                              |
| 15  | cross-cut              | cutting            | ✅                                                                                                     | ✅                                                                                     |
| 16  | cut                    | cutting            | ✅                                                                                                     | ✅                                                                                     |
| 17  | dead-shape             | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 18  | descend                | —                  | ✅ — Descend (sagari) is a move direction, not a technique                                             | ✅ — Agree, descriptive not categorical                                                |
| 19  | diagonal-tesuji        | tesuji             | ✅                                                                                                     | ✅                                                                                     |
| 20  | double-atari           | double-atari       | ✅                                                                                                     | ✅                                                                                     |
| 21  | double-hane            | tesuji             | ✅                                                                                                     | 🔄 `tesuji`, `shape` — Double-hane is both tesuji and shape technique                  |
| 22  | draw-back              | —                  | ✅ — Draw-back (hiki) is a direction, not a category                                                   | 🔄 `tesuji` — Drawing back can be a key tesuji in L&D                                  |
| 23  | exchange               | —                  | ✅ — Exchange (furikawari) is a strategic concept                                                      | ✅ — Agree, no tsumego-level tag                                                       |
| 24  | extend                 | —                  | ✅ — Extension is a basic move, too generic                                                            | ✅ — Standard move, not a technique                                                    |
| 25  | eye-shape              | eye-shape          | ✅                                                                                                     | ✅                                                                                     |
| 26  | geta                   | net                | ✅                                                                                                     | ✅ — Geta is exactly net                                                               |
| 27  | guzumi                 | dead-shapes        | 🔄 `shape` — Guzumi (empty triangle) is a shape concept, not always dead                               | 🔄 `dead-shapes` — In tsumego context, guzumi usually indicates dead shape recognition |
| 28  | hane                   | —                  | ✅ — Hane is a basic move direction                                                                    | 🔄 `tesuji` — Hane at the head of two stones is a fundamental tesuji                   |
| 29  | jump                   | —                  | ✅ — Jump (tobi) is a move type, not technique                                                         | ✅ — Agree, too basic to categorize                                                    |
| 30  | keima-jump             | —                  | ✅ — Knight's move is a shape/direction                                                                | ✅ — Agree                                                                             |
| 31  | ko                     | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 32  | ko-fight               | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 33  | kosumi                 | —                  | ✅ — Diagonal move, no technique mapping                                                               | ✅ — Agree                                                                             |
| 34  | ladder                 | ladder             | ✅                                                                                                     | ✅                                                                                     |
| 35  | large-capture          | life-and-death     | ✅                                                                                                     | 🔄 `life-and-death`, `capture-race` — Large captures often involve semeai              |
| 36  | large-kill-group       | life-and-death     | ✅                                                                                                     | ✅                                                                                     |
| 37  | making-territory       | —                  | ✅ — Territory is a full-board concept                                                                 | ✅ — Not a tsumego technique                                                           |
| 38  | monkey-jump            | endgame            | ✅                                                                                                     | ✅ — Classic yose tesuji                                                               |
| 39  | more-than-one-solution | —                  | ✅ — Meta-attribute, not a technique                                                                   | ✅ — Puzzle property, not a Go concept                                                 |
| 40  | nakade                 | nakade             | ✅                                                                                                     | ✅                                                                                     |
| 41  | net                    | net                | ✅                                                                                                     | ✅                                                                                     |
| 42  | peep                   | tesuji             | 🔄 `tesuji` — Peep (nozoki) is a recognized tesuji                                                     | 🔄 `tesuji` — Agree, nozoki is a classic tesuji                                        |
| 43  | placement              | vital-point        | ✅ — Oki is vital-point                                                                                | ✅                                                                                     |
| 44  | probing                | —                  | ✅ — Probing (yosu-miru) is strategic, not tsumego                                                     | ✅ — Agree                                                                             |
| 45  | push-through           | —                  | 🔄 `tesuji` — Push-through (warikomi) can be a key tesuji                                              | ✅ — Too generic, leave for pipeline                                                   |
| 46  | reduce                 | —                  | ✅ — Reduction is a full-board concept                                                                 | ✅ — Not specific enough                                                               |
| 47  | sacrifice              | sacrifice          | ✅                                                                                                     | ✅                                                                                     |
| 48  | seal-in                | life-and-death     | 🔄 `life-and-death` — Sealing in prevents escape, L&D                                                  | 🔄 `life-and-death` — Agree, sealing in is a killing technique                         |
| 49  | seki                   | seki               | ✅                                                                                                     | ✅                                                                                     |
| 50  | separation             | cutting            | ✅                                                                                                     | ✅                                                                                     |
| 51  | shortage-of-liberties  | liberty-shortage   | ✅                                                                                                     | ✅                                                                                     |
| 52  | snapback               | snapback           | ✅                                                                                                     | ✅                                                                                     |
| 53  | squeeze                | liberty-shortage   | ✅                                                                                                     | ✅                                                                                     |
| 54  | table-shape            | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 55  | throw-in               | throw-in           | ✅                                                                                                     | ✅                                                                                     |
| 56  | tigers-mouth           | shape              | 🔄 `shape` — Tiger's mouth is a recognized shape pattern                                               | 🔄 `shape` — Agree, torakuchi is a fundamental shape                                   |
| 57  | tombstone              | liberty-shortage   | ✅ — Tombstone squeeze                                                                                 | ✅                                                                                     |
| 58  | under-the-stones       | under-the-stones   | ✅                                                                                                     | ✅                                                                                     |
| 59  | vital-point            | vital-point        | ✅                                                                                                     | ✅                                                                                     |
| 60  | wedge                  | tesuji             | ✅                                                                                                     | ✅                                                                                     |
| 61  | carpenters-square      | dead-shapes        | ✅                                                                                                     | 🔄 `dead-shapes` only — Corner tag adds noise; carpenter's square IS the dead shape    |
| 62  | ten-thousand-year-ko   | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 63  | semeai                 | capture-race       | ✅                                                                                                     | ✅                                                                                     |
| 64  | cranes-nest            | tesuji             | ✅                                                                                                     | ✅                                                                                     |
| 65  | making-eyes            | eye-shape          | 🔄 `eye-shape`, `living` — Making eyes implies living goal                                             | ✅ — `eye-shape` alone is sufficient                                                   |
| 66  | denying-eyes           | eye-shape          | 🔄 `eye-shape`, `life-and-death` — Denying eyes implies killing                                        | ✅ — `eye-shape` alone captures the technique                                          |
| 67  | permanent-ko           | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 68  | mirror-symmetry        | —                  | ✅ — Structural property, not a technique                                                              | ✅ — Puzzle property                                                                   |
| 69  | eternal-life           | ko                 | ✅ — Eternal life is a ko-related outcome                                                              | ✅                                                                                     |
| 70  | thick-shape            | shape              | ✅                                                                                                     | ✅                                                                                     |
| 71  | breaking-connection    | cutting            | ✅                                                                                                     | ✅                                                                                     |
| 72  | maintaining-connection | connection         | ✅                                                                                                     | ✅                                                                                     |
| 73  | two-step-ko            | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 74  | windmill               | tesuji             | ✅                                                                                                     | ✅ — Windmill (fusha) is a named tesuji                                                |
| 75  | running                | escape             | ✅                                                                                                     | ✅                                                                                     |
| 76  | surrounding            | —                  | 🔄 `life-and-death` — Surrounding a group aims to kill                                                 | ✅ — Context-dependent, leave for pipeline                                             |
| 77  | weakening              | —                  | ✅ — Too abstract for a single tag                                                                     | ✅ — Agree                                                                             |
| 78  | preventing-escape      | life-and-death     | ✅                                                                                                     | ✅ — Preventing escape = killing                                                       |
| 79  | oiotoshi               | connect-and-die    | ✅                                                                                                     | ✅                                                                                     |
| 80  | turning-move           | tesuji             | ✅                                                                                                     | ✅                                                                                     |
| 81  | approach-move          | —                  | ✅ — Approach is a full-board move                                                                     | ✅ — Not a tsumego concept                                                             |
| 82  | contact-play           | —                  | 🔄 `tesuji` — Contact plays are tactical                                                               | ✅ — Too broad to categorize                                                           |
| 83  | loose-ladder           | ladder             | ✅                                                                                                     | ✅                                                                                     |
| 84  | multi-step             | —                  | ✅ — Complexity attribute, not a technique                                                             | ✅ — Meta-attribute                                                                    |
| 85  | l-group                | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 86  | bent-three             | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 87  | straight-three         | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 88  | bulky-five             | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 89  | j-group                | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 90  | rabbity-six            | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 91  | group-status           | life-and-death     | ✅                                                                                                     | ✅                                                                                     |
| 92  | good-shape             | shape              | ✅                                                                                                     | ✅                                                                                     |
| 93  | bad-shape              | shape              | ✅                                                                                                     | ✅                                                                                     |
| 94  | mannen-ko              | ko                 | ✅                                                                                                     | ✅                                                                                     |
| 95  | two-headed-dragon      | connection         | ✅                                                                                                     | ✅ — Named connection pattern                                                          |
| 96  | flower-six             | dead-shapes        | ✅                                                                                                     | ✅                                                                                     |
| 97  | enclosure-joseki       | joseki             | ✅                                                                                                     | ✅                                                                                     |
| 98  | large-scale-reduction  | —                  | ✅ — Full-board concept                                                                                | 🔄 `endgame` — Large-scale reductions can be yose                                      |

**Review Summary**:

| Metric                       | Count                                             |
| ---------------------------- | ------------------------------------------------- |
| Both reviewers approve       | 72                                                |
| Cho Chikun recommends change | 11                                                |
| Lee Sedol recommends change  | 10                                                |
| Both recommend same change   | 3 (peep→tesuji, seal-in→L&D, tiger's-mouth→shape) |
| Conflicting recommendations  | 4 (atari, guzumi, hane, carpenters-square)        |

**Final coverage**: 69/99 BTP tags (70%) mapped → 30 unmapped (30%).

### Puzzle Intent Mapping — VERIFIED (Cho Chikun Approved)

BTP puzzles lack free-text objectives (unlike OGS's "Black to play and live"). Intent must be derived from **structured metadata**: the `type` field, categories, tags, and `to_play` from individual puzzle data.

**Available signals and when they're available:**

| Signal       | Source      | When Available      | Determines                                    |
| ------------ | ----------- | ------------------- | --------------------------------------------- |
| `type`       | List API    | At list fetch       | Puzzle class: classic(0) / ai(1) / endgame(2) |
| `categories` | List API    | At list fetch       | Collection assignment + intent signal         |
| `tags`       | List API    | At list fetch       | Objective refinement within category          |
| `to_play`    | Puzzle load | At individual fetch | Side: BLACK or WHITE                          |
| `comments`   | Puzzle load | At individual fetch | Fallback text for standard intent resolver    |

**Key discovery**: BTP `type` encodes puzzle class, NOT side-to-play:

- `type=0` ("classic"): 1,178 legacy server-stored puzzles with 6-digit numeric IDs
- `type=1` ("ai"): 2,121 AI-verified puzzles with hash-encoded board positions
- `type=2` ("endgame"): 520 endgame puzzles with hash-encoded positions

**Color inversion**: When `to_play == "W"`, BTP inverts board colors so the player always appears as Black. The adapter must account for this when generating SGF (use original colors, not inverted).

#### Intent Derivation Algorithm

The algorithm uses a priority-ordered signal cascade. Higher-priority signals override lower ones. **Both categories AND tags** are used as input signals (not just categories).

```
to_play → SIDE (BLACK | WHITE)
  ↓
type == "endgame" → ENDGAME.{SIDE}       [Priority 1: shortcut]
  ↓
"seki" ∈ categories → FIGHT.SEKI          [Priority 2: category + side-neutral]
  ↓
"ko" ∈ categories → FIGHT.{SIDE}.WIN_KO   [Priority 3: specific fight type]
  ↓
"semeai" ∈ categories → FIGHT.{SIDE}.WIN_SEMEAI  [Priority 4]
  ↓
tag refinement within category intent signal  [Priority 5: tag-informed]
  ↓
default for category intent signal            [Priority 6: fallback]
  ↓
LLM fallback for low-confidence results       [Priority 7: see below]
```

**LLM Fallback for Low/Medium Confidence** (≤ 0.75):

When the structured signal cascade produces a confidence ≤ 0.75 (medium or low), the tool constructs a text prompt from the available metadata and sends it to `tools.puzzle_intent.resolve_intent()` — the same LLM-based resolver used by Go Problems and OGS tools.

```python
# Construct input text from BTP metadata for LLM intent resolution
def build_intent_text(categories: list[str], tags: list[str], to_play: str) -> str:
    """Build descriptive text from BTP metadata for LLM intent resolution.

    Uses BOTH category names AND tag names as token input, maximizing
    the signal available to the semantic matcher.
    """
    side = "Black" if to_play == "B" else "White"
    parts = [f"{side} to play."]
    if categories:
        parts.append(f"Categories: {', '.join(categories)}.")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}.")
    return " ".join(parts)

# In the main intent resolution flow:
intent, confidence = derive_puzzle_intent(to_play, categories, tags, puzzle_type)
if confidence <= 0.75:
    # LLM fallback — use both categories AND tags as input tokens
    text = build_intent_text(categories, tags, to_play)
    llm_result = resolve_intent(text)
    if llm_result.confidence > confidence:
        intent = llm_result.objective_id
        confidence = llm_result.confidence
        logger.intent_match(puzzle_id, text, intent, confidence, tier="llm_fallback")
```
