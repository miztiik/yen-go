"""
Local intent mapping: 101weiqi qtypename → puzzle objective text.

Maps Chinese puzzle category names to puzzle intent descriptions
for root C[] comment. Follows the t-dragon pattern (static mapping
without semantic resolution, since 101weiqi provides structured
category signals rather than free-text descriptions).

101weiqi always specifies first-to-move via firsthand/blackfirst,
so intent text uses the actual player color at runtime.
"""

from __future__ import annotations

# Chinese qtypename → intent description template.
# {player} is replaced with "Black" or "White" at resolution time.
CATEGORY_TO_INTENT: dict[str, str] = {
    # Primary categories (from qqdata.qtypename)
    "死活题": "{player} to live or kill",
    "手筋": "{player} to find the tesuji",
    "布局": "{player} to find the best opening move",
    "定式": "{player} to find the correct joseki",
    "官子": "{player} to find the best endgame move",
    "官子题": "{player} to find the best endgame move",  # Variant with 题 suffix
    "手筋题": "{player} to find the tesuji",  # Variant with 题 suffix
    "对杀": "{player} to win the capturing race",
    "对杀题": "{player} to win the capturing race",
    "综合": "{player} to find the best move",
    "中盘": "{player} to find the best middle game move",
    # Additional categories (discovered from /questionlib/ URL paths)
    "吃子": "{player} to capture the stones",
    "骗招": "{player} to find the trap move",
    "实战": "{player} to find the best move",
    "棋理": "{player} to find the correct move",
    # 模仿 — needs live sampling before committing intent
    "欣赏题": "{player} to find the best move",  # Appreciation/demonstration
    # English aliases (from qday sweep, 2015+ daily puzzles)
    "Life & Death": "{player} to live or kill",
    "Fight": "{player} to win the capturing race",
    "Tesuji": "{player} to find the tesuji",
    "Opening": "{player} to find the best opening move",
    "Joseki": "{player} to find the correct joseki",
    "Endgame": "{player} to find the best endgame move",
    "Comprehensive": "{player} to find the best move",
    "Middle Game": "{player} to find the best middle game move",
    "Principles": "{player} to find the correct move",
}


def resolve_intent(
    type_name: str,
    player_to_move: str,
) -> str | None:
    """Resolve puzzle intent from 101weiqi category.

    Args:
        type_name: Chinese category string (e.g., "死活题").
        player_to_move: "B" or "W".

    Returns:
        Intent description string (e.g., "Black to live or kill")
        or None if category is unknown.
    """
    template = CATEGORY_TO_INTENT.get(type_name)
    if template is None:
        return None

    player = "Black" if player_to_move == "B" else "White"
    return template.format(player=player)
