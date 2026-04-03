"""
OGS Puzzle Downloader Tool.

Standalone tool to download puzzles from Online-Go.com (OGS) and store them
as SGF files in external-sources/ogs/sgf/batch-XXX/ directories.

Features:
- Pagination support (downloads all puzzles)
- Single page mode (--page N)
- Checkpoint/resume functionality (per-file)
- Structured logging (console + JSON file)
- Rate limiting with jitter
- Validates puzzles have solutions by traversing move tree
- 1000 files per batch directory
- Index file (sgf-index.txt) for duplicate prevention
- YT[] tag embedding from puzzle_type

SGF Output:
- Minimal properties: FF, GM, CA, SZ, PL, AB, AW
- YT[] tags mapped from OGS puzzle_type
- No GN, PC, EV, or root C[] (per project spec)
- Move comments preserved for correct/wrong feedback

Usage:
    python -m tools.ogs --help
    python -m tools.ogs --max-puzzles 5000 --resume
    python -m tools.ogs --page 10  # Download specific page only

Log Analysis:
    python -m tools.ogs.analyze_logs --summary
    python -m tools.ogs.analyze_logs --failures
"""

__version__ = "1.1.0"
