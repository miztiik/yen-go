"""Check if 719 is in the puzzle list."""
import sys

sys.path.insert(0, str(__file__).replace("\\", "/").rsplit("/tools/", 1)[0])

from tools.blacktoplay.client import BTPClient


def main():
    puzzle_type = 0  # Classic
    target_id = "000719"

    print(f"Fetching puzzle list for type {puzzle_type}...")

    with BTPClient() as client:
        items = client.list_puzzles(puzzle_type, use_cache=True)
        print(f"Total items: {len(items)}")

        # Find 719
        found = [item for item in items if item.puzzle_id == target_id]
        if found:
            print(f"\nFound {target_id}: {found[0]}")
        else:
            print(f"\n{target_id} NOT FOUND in list!")

            # Show sample IDs
            print(f"\nSample IDs: {[item.puzzle_id for item in items[:10]]}")

            # Check for any ID containing 719
            contains_719 = [item for item in items if "719" in item.puzzle_id]
            print(f"IDs containing '719': {[i.puzzle_id for i in contains_719]}")

if __name__ == "__main__":
    main()
