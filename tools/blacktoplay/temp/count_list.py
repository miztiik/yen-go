"""Count puzzles in cached BTP list."""
import json

with open("tools/blacktoplay/research/btp-list-response.json", encoding="utf-8-sig") as f:
    data = json.load(f)

puzzles = data["list"]
print(f"Total puzzles: {len(puzzles)}")

# Count by type
by_type = {}
for p in puzzles:
    t = p.get("type", "?")
    by_type[t] = by_type.get(t, 0) + 1

print(f"By type: {by_type}")

# Count numeric vs alphanumeric IDs
numeric = [p for p in puzzles if p["id"].isdigit()]
alphanum = [p for p in puzzles if not p["id"].isdigit()]
print(f"Numeric IDs: {len(numeric)}, Alphanumeric IDs: {len(alphanum)}")

# Show sample of each
print(f"\nSample numeric IDs: {[p['id'] for p in numeric[:5]]}")
print(f"Sample alphanum IDs: {[p['id'] for p in alphanum[:5]]}")
