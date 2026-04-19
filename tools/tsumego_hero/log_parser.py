"""
Parse Tsumego Hero download logs to extract rejection reasons.

Reads JSONL log files produced by the download orchestrator and maps
puzzle URL IDs to canonical rejection reason codes.

Used by organize_collections.py to enrich manifests with skip reasons.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("tsumego_hero.log_parser")

# Canonical reason codes
REASON_NO_SOLUTION = "no_solution"
REASON_SOLUTION_TOO_DEEP = "solution_too_deep"
REASON_BOARD_TOO_SMALL = "board_too_small"
REASON_INVALID_SGF = "invalid_sgf"
REASON_ZERO_STONES = "zero_stones"
REASON_UNKNOWN = "unknown"


def _classify_reason(raw_reason: str) -> str:
    """Map a raw log reason string to a canonical reason code."""
    if "No solution found" in raw_reason:
        return REASON_NO_SOLUTION
    if re.search(r"Solution too deep", raw_reason):
        return REASON_SOLUTION_TOO_DEEP
    if re.search(r"Board (width|height) \d+ below minimum", raw_reason):
        return REASON_BOARD_TOO_SMALL
    if re.search(r"Only 0 stone\(s\)", raw_reason):
        return REASON_ZERO_STONES
    if "invalid" in raw_reason.lower() or "parse" in raw_reason.lower():
        return REASON_INVALID_SGF
    return REASON_UNKNOWN


def parse_rejection_log(log_path: Path) -> dict[int, str]:
    """Parse a download log JSONL file and extract rejection reasons.

    Args:
        log_path: Path to the JSONL log file.

    Returns:
        Dict mapping puzzle url_id (int) to canonical reason code string.
    """
    rejections: dict[int, str] = {}

    with open(log_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.debug(f"Skipping malformed JSON at line {line_num}")
                continue

            event_type = entry.get("event_type")
            if event_type != "item_skip":
                continue

            data = entry.get("data", {})
            item_id_str = data.get("item_id", "")
            raw_reason = data.get("reason", "")

            try:
                url_id = int(item_id_str)
            except (ValueError, TypeError):
                logger.debug(f"Non-integer item_id at line {line_num}: {item_id_str}")
                continue

            reason_code = _classify_reason(raw_reason)
            rejections[url_id] = reason_code

    logger.info(f"Parsed {len(rejections)} rejection entries from {log_path.name}")
    return rejections
