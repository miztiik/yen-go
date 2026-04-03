# Data Flow

How puzzles flow from external sources to the browser.

## Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   External  │────▶│   Puzzle    │────▶│   GitHub    │────▶│   Browser   │
│   Sources   │     │   Manager   │     │   Pages     │     │  (Frontend) │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
     SGF            Python pipeline      Static CDN        Preact + Canvas
```

## Stage-by-Stage Flow

### 1. Sources → INGEST

```
external-sources/           adapters/
├── kisvadim-goproblems/   ──▶ LocalSgfAdapter
├── sanderland/            ──▶ UrlSgfAdapter
└── manual-imports/        ──▶ LocalSgfAdapter
                               │
                               ▼
                          staging/ingest/
                          └── {source_id}/
                              └── *.json (validated puzzles)
```

### 2. INGEST → ANALYZE

```
staging/ingest/                  staging/analyzed/
└── {source_id}/         ──▶  └── {level}/
    └── *.json                    └── *.json (with tags, hints)
```

### 3. ANALYZE → PUBLISH

```
staging/analyzed/             yengo-puzzle-collections/
└── {level}/             ──▶  ├── sgf/
    └── *.json                │   └── {level}/{YYYY}/{MM}/batch_{NNN}/
                              │       └── *.sgf
                              ├── views/
                              │   ├── by-level/{level}.json
                              │   ├── by-tag/{tag}.json
                              │   └── daily/{YYYY-MM-DD}/
                              ├── publish-log/
                              │   └── {YYYY-MM-DD}.jsonl
                              └── puzzle-collection-inventory.json  ← Updated on publish
```

### 4. GitHub Pages → Browser

```
yengo-puzzle-collections/     Browser
├── sgf/                 ──▶  fetch('/sgf/{level}/...')
│   └── *.sgf                 │
└── views/                    ├── SGF Parser (~5KB)
    └── *.json           ──▶  │
                              ├── Move Validator
                              │
                              └── localStorage
                                  └── progress.json
```

## File Formats

### SGF (Storage)
```
(;FF[4]GM[1]SZ[9]
YV[1]YG[intermediate]YT[snapback,throw_in]
AB[aa][ba][ca]AW[ab][bb]
PL[B]
(;B[cb];W[da];B[db];W[ea]))
```

### JSON Views (Index)
```json
{
  "indexVersion": "1.0",
  "level": "intermediate",
  "puzzles": ["2026-01-20-001", "2026-01-20-002"]
}
```

### localStorage (Progress)
```json
{
  "version": 1,
  "solved": ["2026-01-20-001"],
  "streak": 5,
  "lastPlayed": "2026-01-27"
}
```

## Key Principles

1. **SGF is source of truth** — All puzzle data stored as SGF with YenGo extensions
2. **JSON for indexes** — Fast browser lookups
3. **localStorage for progress** — No server-side storage
4. **Sharding** — Max 100 files per directory
