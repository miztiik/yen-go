# Pipeline Stages

The Puzzle Manager uses a **3-stage pipeline** (v3.2, Spec 013).

## Overview

| Stage   | Input               | Output                      | Purpose                  |
| ------- | ------------------- | --------------------------- | ------------------------ |
| INGEST  | Sources             | `staging/ingest/`           | Fetch + Parse + Validate |
| ANALYZE | `staging/ingest/`   | `staging/analyzed/`         | Classify + Tag + Enrich  |
| PUBLISH | `staging/analyzed/` | `yengo-puzzle-collections/` | Index + Daily + Output   |

```
INGEST ────────▶ ANALYZE ────────▶ PUBLISH
   │                │                  │
   ▼                ▼                  ▼
staging/ingest/   staging/analyzed/   yengo-puzzle-collections/
```

---

## Stage 1: INGEST

**Purpose**: Fetch puzzles from sources, parse SGF, validate structure.

**Operations**:

1. **Fetch** — Download or read SGF files via adapters
2. **Parse** — Tokenize SGF, build game tree, extract properties
3. **Validate** — Check board size, stones, solution exists

**CLI**:

```bash
python -m backend.puzzle_manager run --source <source_id> --stage ingest --batch-size 100
python -m backend.puzzle_manager run --source <source_id> --stage ingest
```

**Validation Checks**:

- Valid board size (9, 13, 19)
- Stones within bounds
- Player to move specified
- Solution exists (at least one move)

---

## Stage 2: ANALYZE

**Purpose**: Classify difficulty, detect techniques, generate hints.

**Operations**:

1. **Classify** — Assign difficulty level (9-level system, with collection-based override)
2. **Tag** — Detect techniques (ladder, ko, snapback, etc.)
3. **Collection assign** — Match source metadata against `config/collections.json` aliases
4. **Level override** — If any assigned collection has a `level_hint`, override the heuristic level (lowest wins on conflict)
5. **Enrich** — Generate pedagogical hints (`YH[hint1|hint2|hint3]`) and quality metrics (YQ)

**CLI**:

```bash
python -m backend.puzzle_manager run --stage analyze --batch-size 100
```

### Hint Generation (Enrich Sub-stage)

The hint system generates **pedagogical hints** designed by a 1P professional Go player.

**Format**: `YH[hint1|hint2|hint3]` (pipe-delimited, max 3 hints)

| Hint # | Content                  | Pedagogical Goal                             |
| ------ | ------------------------ | -------------------------------------------- |
| 1      | Area + Liberty Analysis  | Prompts player to COUNT liberties            |
| 2      | Technique + Reasoning    | Explains WHY technique applies               |
| 3      | Move hint or Consequence | Shows specific move or what happens if wrong |

**Example YH1:** "Focus on top-left. Black has 2 liberties, White has 3 - who needs to act first?"

**See:** [Hint Concepts](../../concepts/hints.md) for full documentation.

**9-Level System**:
| Level | Name | Rank Range |
|-------|------|------------|
| 1 | Novice | 30k-26k |
| 2 | Beginner | 25k-21k |
| 3 | Elementary | 20k-16k |
| 4 | Intermediate | 15k-11k |
| 5 | Upper Intermediate | 10k-6k |
| 6 | Advanced | 5k-1k |
| 7 | Low Dan | 1d-3d |
| 8 | High Dan | 4d-6d |
| 9 | Expert | 7d-9d |

---

## Stage 3: PUBLISH

**Purpose**: Build SQLite search databases, generate daily challenges, write output.

**Operations**:

1. **SGF Output** — Write enriched SGF files to flat batch directories
2. **Database Build** — Build yengo-search.db and yengo-content.db via db_builder/content_db
3. **Daily** — Create daily challenge sets
4. **Inventory** — Update puzzle collection statistics

**CLI**:

```bash
python -m backend.puzzle_manager run --stage publish
```

**Output Structure**:

```
yengo-puzzle-collections/
├── sgf/{NNNN}/{content_hash}.sgf
├── yengo-search.db          # Search/metadata + daily schedule (~500 KB)
├── yengo-content.db         # SGF content + dedup (backend only)
├── db-version.json           # Version pointer
```

---

## Running the Full Pipeline

```bash
# All stages in sequence (--source is REQUIRED)
python -m backend.puzzle_manager run --source <source_id>

# Individual stages
python -m backend.puzzle_manager run --source <source_id> --stage ingest
python -m backend.puzzle_manager run --stage analyze
python -m backend.puzzle_manager run --stage publish
```

---

## Note: Removed Stages

The solve/verify stages from the old 11-stage pipeline were removed in v3.2 (Spec 013). Curated puzzle sources are pre-validated, so KataGo/Smargo verification is no longer needed.
