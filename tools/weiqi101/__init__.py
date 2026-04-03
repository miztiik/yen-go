"""
101weiqi.com Puzzle Downloader Tool.

Standalone tool to download Go/Baduk tsumego puzzles from 101weiqi.com
and store them as SGF files in external-sources/101weiqi/sgf/batch-XXX/ directories.

Features:
- Multiple source modes: daily puzzles, individual puzzle by ID
- Batch directories (1000 files per batch)
- Checkpoint/resume functionality
- Structured logging (console + JSONL file)
- Rate limiting with jitter + exponential backoff
- Chinese level/tag mapping to YenGo properties (YG[], YT[])
- Index file (sgf-index.txt) for duplicate prevention
- Validates puzzles have setup stones and solution tree

SGF Output:
- Mandatory: FF, GM, CA, SZ, PL, AB, AW
- YG[] level slug mapped from Chinese kyu/dan levelname
- YT[] tags mapped from Chinese qtypename
- Move C[] comments preserved (Correct/Wrong)
- No GN, PC, EV, or root C[] metadata dump

Usage:
    python -m tools.weiqi101 --help
    python -m tools.weiqi101 daily --start-date 2026-01-01 --end-date 2026-01-31
    python -m tools.weiqi101 puzzle --start-id 1 --end-id 100
    python -m tools.weiqi101 puzzle --ids 78000,78001
"""

__version__ = "1.0.0"
