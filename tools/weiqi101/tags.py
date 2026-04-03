"""
Tag mapping: 101weiqi qtypename → YenGo tag slug.

Maps Chinese puzzle category names to YenGo canonical tags
from config/tags.json.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("101weiqi.tags")

# Chinese qtypename → YenGo tag slug
# null entries are intentionally unmapped (too generic for a single tag).
# Sub-technique tags (ladder, snapback, ko, etc.) are discovered by the
# pipeline enrichment stage, not at ingest time.
TAG_MAPPING: dict[str, str | None] = {
    # Primary categories (from qqdata.qtypename)
    "死活题": "life-and-death",
    "手筋": "tesuji",
    "布局": "fuseki",
    "定式": "joseki",
    "官子": "endgame",
    "官子题": "endgame",  # Variant with 题 suffix (seen in book-6)
    "手筋题": "tesuji",  # Variant with 题 suffix (seen in book-6)
    "对杀": "capture-race",
    "对杀题": "capture-race",  # Variant with 题 suffix
    "综合": None,  # Mixed/comprehensive — let pipeline tagger detect
    "中盘": None,  # Middle game — too broad, pipeline tagger refines
    # Additional categories (discovered from /questionlib/ URL paths)
    "吃子": None,   # Capture stones — NOT capture-race! Pipeline detects ladder/net/snapback
    "骗招": "tesuji",  # Trick moves — closest available tag (future: trick-play)
    "实战": None,   # Real game positions — too broad
    "棋理": None,   # Go theory/principles — conceptual, not technique
    "模仿": None,   # Imitation/mirror-go — defer until sampled
    "欣赏题": None,  # Appreciation/demonstration — educational, not technique
}


def map_tag(type_name: str) -> str | None:
    """Map a 101weiqi qtypename to a YenGo tag slug.

    Args:
        type_name: Chinese category string, e.g., "死活题"

    Returns:
        Tag slug (e.g., "life-and-death") or None if unmappable.
    """
    if not type_name:
        return None

    tag = TAG_MAPPING.get(type_name)
    if tag is not None:
        logger.debug(f"Tag '{type_name}' → '{tag}'")
    elif type_name in TAG_MAPPING:
        logger.debug(f"Tag '{type_name}' → None (intentionally unmapped)")
    else:
        logger.warning(f"Unknown qtypename: '{type_name}'")

    return tag
