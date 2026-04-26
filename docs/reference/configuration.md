# Configuration Reference

> **Spec Reference**: 035-puzzle-manager-refactor

Complete reference for Yen-Go configuration files.

---

## Configuration Architecture

### Single Source of Truth Pattern

Configuration follows a **global vs local** split to maintain Single Source of Truth:

| Scope | Location | Purpose |
|-------|----------|--------|
| **Global** | `config/` (repository root) | Shared across all components (frontend, backend, tools) |
| **Local** | `backend/puzzle_manager/config/` | Puzzle manager specific settings |

### Global Configuration Files (`config/`)

| File | Purpose |
|------|---------|
| `puzzle-levels.json` | 9-level difficulty system (shared) |
| **`tags.json`** | **Technique tags and aliases (Single Source of Truth)** |
| `logging.json` | Centralized logging configuration |
| `schemas/` | JSON schemas for validation |

### Local Configuration Files (`backend/puzzle_manager/config/`)

| File | Purpose |
|------|---------|
| `pipeline.json` | Pipeline settings (batch size, retention) |
| `sources.json` | Puzzle source definitions |
| `puzzle-levels.json` | Local copy of level definitions |

---

## puzzle-levels.json

Defines the 9-level difficulty system.

```json
{
  "version": "2.0",
  "levels": [
    {
      "id": 1,
      "name": "novice",
      "display_name": "Novice",
      "rank_range": "DDK30-DDK25",
      "description": "First steps in tsumego"
    },
    {
      "id": 2,
      "name": "beginner",
      "display_name": "Beginner",
      "rank_range": "DDK25-DDK20",
      "description": "Basic capture patterns"
    }
  ]
}
```

### Level Mapping

| ID | Name | Display | Rank Range |
|----|------|---------|------------|
| 1 | novice | Novice | DDK30-DDK25 |
| 2 | beginner | Beginner | DDK25-DDK20 |
| 3 | basic | Basic | DDK20-DDK15 |
| 4 | elementary | Elementary | DDK15-DDK10 |
| 5 | intermediate | Intermediate | DDK10-DDK5 |
| 6 | advanced | Advanced | DDK5-SDK |
| 7 | challenging | Challenging | SDK-1d |
| 8 | difficult | Difficult | 1d-3d |
| 9 | expert | Expert | 3d-Pro |

---

## tags.json (Single Source of Truth)

> **Location**: `config/tags.json` (repository root)  
> **⚠️ This is the ONLY tags.json** — the puzzle manager loads from here.

Defines technique tags and aliases used by both frontend and backend.

```json
{
  "version": "1.0",
  "tags": [
    "ladder",
    "snapback",
    "ko",
    "net",
    "throw_in"
  ],
  "aliases": {
    "shicho": "ladder",
    "snap back": "snapback",
    "geta": "net",
    "semeai": "capturing_race",
    "tiger's mouth": "bamboo_joint"
  },
  "categories": {
    "capture": ["ladder", "snapback", "ko", "throw_in", "net"],
    "connection": ["connect", "cut", "cross_cut", "bamboo_joint"],
    "eye": ["eye_steal", "false_eye", "seki", "killing", "living"],
    "shape": ["hane", "clamp", "placement", "descent", "wedge"]
  }
}
```

See [reference/technique-tags.md](technique-tags.md) for complete tag list.

---

## logging.json

Centralized logging configuration.

```json
{
  "version": "1.0",
  "log_root": "logs",
  "subdirectories": {
    "puzzle_manager": "puzzle_manager",
    "tools": "tools"
  },
  "default_level": "INFO",
  "format": "%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
  "rotation": {
    "when": "midnight",
    "backup_count": 45
  }
}
```

### Log Levels

| Level | Usage |
|-------|-------|
| DEBUG | Detailed diagnostic info |
| INFO | Normal operation events |
| WARNING | Unexpected but handled |
| ERROR | Operation failed |
| CRITICAL | System-level failure |

### Log Directories

```
logs/
├── puzzle_manager/
│   ├── puzzle_manager.log
│   ├── fetch.log
│   ├── parse.log
│   └── ...
└── tools/
    ├── 101weiqi/
    └── gotools/
```

---

## Inventory File

> **Location**: `yengo-puzzle-collections/puzzle-collection-inventory.json`  
> **Schema**: `config/schemas/puzzle-collection-inventory-schema.json`

Tracks puzzle collection statistics and metrics.

```json
{
  "schema_version": "1.0.0",
  "last_updated": "2026-01-30T10:00:00Z",
  "last_run_id": "20260130-abc12345",
  "collection": {
    "total_puzzles": 15000,
    "by_puzzle_level": { "beginner": 3000, "intermediate": 5000 },
    "by_tag": { "life-and-death": 8000 }
  },
  "stages": {
    "ingest": { "attempted": 16000, "passed": 15500, "failed": 500 },
    "analyze": { "enriched": 15200, "skipped": 300 },
    "publish": { "new": 15000 }
  },
  "audit": { "total_rollbacks": 3 }
}
```

### Update Triggers

| Operation | Action |
|-----------|--------|
| `publish` | Increments collection counts |
| `rollback` | Decrements counts, increments `audit.total_rollbacks` |
| `--rebuild` | Reconstructs from publish logs |

See [How-To: Monitor Pipeline](../how-to/backend/monitor.md) for detailed usage.

---

## Pipeline Configuration

> **Location**: `backend/puzzle_manager/config/pipeline.json`

Puzzle manager local configuration:

```json
{
  "paths": {
    "staging": "../staging",
    "output": "../../yengo-puzzle-collections"
  },
  "batch": {
    "size": 100
  },
  "solve": {
    "solver": "katago",
    "fallback_solver": "smargo",
    "skip_on_unavailable": true,
    "timeout_seconds": 60,
    "visits": 200
  }
}
```

### Solve Options

| Option | Default | Description |
|--------|---------|-------------|
| `solver` | "katago" | Primary solver |
| `fallback_solver` | "smargo" | Fallback solver |
| `skip_on_unavailable` | true | Skip if no solver |
| `timeout_seconds` | 60 | Per-puzzle timeout |
| `visits` | 200 | MCTS visits |
| `rejection_policy` | "enhancement" | strict/lenient/enhancement |

---

## Sources Configuration

> **Location**: `backend/puzzle_manager/config/sources.json`

Puzzle source definitions:

```json
{
  "version": "3.0",
  "sources": {
    "local-collection": {
      "name": "Local Puzzles",
      "adapter": "local_sgf",
      "path": "./external-sources/local",
      "pattern": "**/*.sgf",
      "enabled": true,
      "license": "MIT"
    }
  }
}
```

### Source Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Display name |
| `adapter` | Yes | Ingester type |
| `path` | Varies | Path to files |
| `enabled` | No | Enable/disable |
| `license` | No | Source license |
| `metadata` | No | Extra data |

---

## Adapter Configuration

### OGS Adapter (`config/adapters/ogs.json`)

Configuration for importing from Online-Go.com:

```json
{
  "base_url": "https://example.com/api/v1",
  "puzzles_endpoint": "/puzzles/",
  "batch_size": 50,
  "page_delay_seconds": 3,
  "puzzle_delay_seconds": 1,
  "backoff_base_seconds": 30,
  "backoff_max_seconds": 240,
  "backoff_multiplier": 2,
  "valid_board_sizes": [9, 13, 19],
  "user_agent": "YenGo-PuzzleManager/1.0",
  "timeout_seconds": 30
}
```

#### Source Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `base_url` | `https://example.com/api/v1` | Source API base URL |
| `puzzles_endpoint` | `/puzzles/` | Puzzles endpoint path |
| `batch_size` | 50 | Puzzles per page request |
| `page_delay_seconds` | 3 | Delay between page fetches |
| `puzzle_delay_seconds` | 1 | Delay between puzzle fetches |
| `backoff_base_seconds` | 30 | Initial backoff for rate limits |
| `backoff_max_seconds` | 240 | Maximum backoff duration |
| `backoff_multiplier` | 2 | Backoff multiplier (exponential) |
| `valid_board_sizes` | `[9, 13, 19]` | Accepted board sizes |
| `user_agent` | `YenGo-PuzzleManager/1.0` | HTTP User-Agent header |
| `timeout_seconds` | 30 | HTTP request timeout |

#### OGS Runtime Options (CLI)

| Option | Type | Description |
|--------|------|-------------|
| `puzzle_id` | int | Single puzzle ID to import |
| `puzzle_type` | str | Filter: life_and_death, tesuji, fuseki, joseki, endgame, best_move |
| `collection_id` | int | Filter by collection ID |
| `fetch_only` | bool | Two-phase: fetch raw JSON only |
| `transform_only` | bool | Two-phase: transform raw to SGF only |
| `strict_translation` | bool | Skip puzzles that can't be cleanly translated |
| `verbose` | bool | Enable verbose logging |

#### OGS Type to YenGo Tag Mapping

| OGS Type | YenGo Tag |
|----------|-----------|
| life_and_death | life-and-death |
| tesuji | tesuji |
| fuseki | opening |
| joseki | corner-joseki |
| endgame | endgame |
| best_move | best-move |

#### OGS Two-Phase Architecture

For large imports (thousands of puzzles), use two-phase mode:

```bash
# Phase 1: Fetch raw JSON (supports checkpoint/resume)
python -m backend.puzzle_manager run --source ogs --fetch-only

# Phase 2: Transform to SGF (offline, no API calls)
python -m backend.puzzle_manager run --source ogs --transform-only
```

**Checkpoint Files**:
- `.pm-runtime/state/ogs_fetch_checkpoint.json` - Tracks fetched pages/puzzles
- `.pm-runtime/state/ogs_transform_checkpoint.json` - Tracks transformed files

**Runtime Directories**:
- `.pm-runtime/raw/ogs/` - Raw JSON puzzle data
- `.pm-runtime/staging/ogs/{level}/` - Generated SGF files

---

## Environment Variables

Override configuration via environment:

| Variable | Description | Default |
|----------|-------------|---------|
| `YENGO_CONFIG` | Config file path | `config/pipeline.json` |
| `YENGO_LOG_LEVEL` | Log level override | `INFO` |
| `YENGO_MOCK_SOLVER` | Use mock solver | `0` |
| `KATAGO_PATH` | KataGo binary | Auto-detect |
| `KATAGO_MODEL` | KataGo model | Auto-detect |
| `KATAGO_CONFIG` | KataGo config | Optional |

---

## SGF Properties Schema

Located in `config/schemas/sgf-properties.schema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "properties": {
    "YV": {
      "description": "YenGo format version",
      "pattern": "^[0-9]+$"
    },
    "YG": {
      "description": "Level (name:sublevel)",
      "pattern": "^[a-z]+:[0-9]$"
    },
    "YT": {
      "description": "Technique tags",
      "pattern": "^[a-z_,]+$"
    }
  }
}
```

### Y* Properties

| Property | Example | Description |
|----------|---------|-------------|
| `YV[1]` | Version | Format version |
| `YG[beginner:2]` | Level | Difficulty level |
| `YT[ko,snapback]` | Tags | Technique tags |
| `YH1[cd]` | Hint 1 | First hint position |
| `YH2[dd]` | Hint 2 | Area hint |
| `YH3[de]` | Hint 3 | Solution hint |
| `YR[source:id]` | Reference | Source reference |
| `YC[Name #N]` | Citation | Source citation |
| `YK[hash]` | Key | Position hash |
| `YO[quality]` | Quality | Quality score |
| `YQ[rating]` | Rating | Numeric rating |
| `YX[extra]` | Extra | Extended data |

---

## Validation

### Validate Configuration

```python
from puzzle_manager.config import get_config_loader

config = get_config_loader()

# Validate tags
valid, invalid = config.validate_tags(["ladder", "unknown"])

# Get all levels
levels = config.get_all_levels()

# Get level by name
level = config.get_level_by_name("intermediate")
```

### Schema Validation

```bash
# Validate levels.json
python -m json.tool config/levels.json

# Validate tags.json
python -m json.tool config/tags.json
```

---

## See Also

- [architecture/backend/sgf.md](../architecture/backend/sgf.md) - SGF design decisions
- [reference/technique-tags.md](technique-tags.md) - Tag reference
- [reference/puzzle-manager-cli.md](puzzle-manager-cli.md) - CLI reference
