"""Independently fetch and process puzzle 719."""
import sys

sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tools/", 1)[0])

from tools.blacktoplay.client import BTPClient
from tools.blacktoplay.sgf_converter import convert_puzzle_to_sgf


def main():
    puzzle_id = "000719"
    puzzle_type = 0  # Classic

    print(f"Fetching puzzle {puzzle_id}...")

    with BTPClient() as client:
        try:
            puzzle = client.fetch_puzzle(puzzle_id, puzzle_type)
            print(f"Fetched: viewport_size={puzzle.viewport_size}, board_size={puzzle.board_size}")
            print(f"Rating: {puzzle.rating}, to_play: {puzzle.to_play}")
            print(f"Nodes: {len(puzzle.nodes)}")

            # Convert to SGF
            print("\nConverting to SGF...")
            sgf = convert_puzzle_to_sgf(puzzle)
            print(f"\nSGF ({len(sgf)} chars):")
            print(sgf)

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
