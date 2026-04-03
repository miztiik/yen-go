"""BlackToPlay puzzle download tool.

Downloads tsumego puzzles from BlackToPlay.com, converts the proprietary
hash-encoded board format to SGF, and maps BTP metadata to YenGo taxonomy.

Modules:
    config          -- Paths, constants, API URLs
    models          -- Data classes for BTP puzzle data
    go_engine       -- Minimal Go legality engine for wrong-move enumeration
    hash_decoder    -- Base-59 hash decode/encode
    node_parser     -- BTP node string → SgfNode solution tree
    enrichment      -- Rating/tag/category → YenGo level/tags/collections
    sgf_converter   -- BTP puzzle → SGF string via SGFBuilder
    client          -- HTTP client for BTP API (POST with browser headers)
    btp_checkpoint  -- Download checkpoint state
    storage         -- Batch directory file saving + index
    logging_config  -- Structured logging setup
    orchestrator    -- Main download loop with resume support

Usage:
    python -m tools.blacktoplay --help
    python -m tools.blacktoplay --max-puzzles 100 --dry-run
    python -m tools.blacktoplay --resume
"""
