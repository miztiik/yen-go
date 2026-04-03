"""
SGF publisher for serializing SGFGame to string.

Converts internal SGFGame representation to valid SGF format.
Delegates to SGFBuilder for the actual serialization (DRY principle).
"""

from backend.puzzle_manager.core.sgf_builder import SGFBuilder
from backend.puzzle_manager.core.sgf_parser import SGFGame


def publish_sgf(game: SGFGame) -> str:
    """Serialize SGFGame to SGF string.

    This function is a thin wrapper around SGFBuilder.from_game().build(),
    providing a simple functional interface for SGF serialization.

    Args:
        game: SGFGame object to serialize.

    Returns:
        Valid SGF string.
    """
    return SGFBuilder.from_game(game).build()
