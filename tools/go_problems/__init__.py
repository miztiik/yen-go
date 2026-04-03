"""
GoProblems.com Puzzle Downloader Tool.

Standalone tool to download puzzles from goproblems.com API v2 and store them
as SGF files in external-sources/goproblems/sgf/batch-XXX/ directories.

Features:
- ID range fetch (--start-id N --end-id M)
- Specific ID fetch (--ids 42,100,250)
- Paginated listing (--list) for puzzle discovery
- Checkpoint/resume functionality (per-file)
- Structured logging (console + JSON file)
- Rate limiting with jitter
- Optional --canon-only filtering
- YQ quality score from stars/votes/isCanon
- 1000 files per batch directory
- Index file (sgf-index.txt) for duplicate prevention
- YG[] level from rank mapping (kyu/dan -> 9-level system)
- YT[] tags from genre mapping
- YL[] collection slugs via phrase matching

SGF Output:
- Enriched source SGF with injected YenGo properties
- FF[4], GM[1], CA[UTF-8], PL[] (standard)
- YV[], YG[], YT[], YL[], YQ[] (YenGo custom)
- Root C[] stripped, move C[] preserved (per project spec)
- SO[] stripped (per project spec)

Usage:
    python -m tools.go_problems --help
    python -m tools.go_problems --start-id 1 --end-id 5000 --resume
    python -m tools.go_problems --ids 42,100,250
    python -m tools.go_problems --list --max-puzzles 500
"""

__version__ = "1.0.0"
