"""
Collections alignment utility.

Validates that tool-local collection mappings reference valid slugs
from the global config/collections.json and reports coverage gaps.

Usage:
    python -m tools.collections_align --tool t-dragon
    python -m tools.collections_align --tool tsumego-hero
    python -m tools.collections_align --check-all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# Project root detection (same logic as tools.core.paths)
def _get_project_root() -> Path:
    """Walk up from this file to find .git directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    raise RuntimeError("Cannot detect project root")


PROJECT_ROOT = _get_project_root()
GLOBAL_CONFIG = PROJECT_ROOT / "config" / "collections.json"

# Tool registry: tool name -> (local JSON path, description)
TOOL_REGISTRY: dict[str, tuple[Path, str]] = {
    "t-dragon": (
        PROJECT_ROOT / "tools" / "t-dragon" / "collections.json",
        "TsumegoDragon category -> collection slug mappings",
    ),
    "tsumego-hero": (
        PROJECT_ROOT / "tools" / "tsumego_hero" / "collections_local.json",
        "Tsumego Hero collection name -> collection slug mappings",
    ),
}


def load_global_slugs() -> set[str]:
    """Load all collection slugs from global config."""
    if not GLOBAL_CONFIG.exists():
        print(f"ERROR: Global config not found: {GLOBAL_CONFIG}", file=sys.stderr)
        sys.exit(1)

    with open(GLOBAL_CONFIG, encoding="utf-8") as f:
        data = json.load(f)

    return {c["slug"] for c in data.get("collections", [])}


def load_local_mappings(tool_name: str) -> tuple[dict[str, str | None], Path]:
    """Load tool-local collection mappings.

    Returns:
        Tuple of (mappings dict, config file path).
    """
    if tool_name not in TOOL_REGISTRY:
        print(f"ERROR: Unknown tool '{tool_name}'", file=sys.stderr)
        print(f"Available tools: {', '.join(TOOL_REGISTRY.keys())}", file=sys.stderr)
        sys.exit(1)

    config_path, _desc = TOOL_REGISTRY[tool_name]

    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    return data.get("mappings", {}), config_path


def check_tool(tool_name: str, global_slugs: set[str]) -> tuple[int, int, int]:
    """Check alignment for a single tool.

    Returns:
        Tuple of (matched_count, unmapped_count, invalid_count).
    """
    mappings, config_path = load_local_mappings(tool_name)
    _path, description = TOOL_REGISTRY[tool_name]

    print(f"\n{'='*60}")
    print(f"Tool: {tool_name}")
    print(f"Config: {config_path.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Description: {description}")
    print(f"{'='*60}")

    # Classify entries
    matched: list[tuple[str, str]] = []
    unmapped: list[str] = []
    invalid: list[tuple[str, str]] = []

    for source_key, target_slug in sorted(mappings.items()):
        if target_slug is None:
            unmapped.append(source_key)
        elif target_slug in global_slugs:
            matched.append((source_key, target_slug))
        else:
            invalid.append((source_key, target_slug))

    # Report matched
    print(f"\nMatched ({len(matched)}):")
    if matched:
        max_key_len = max(len(k) for k, _ in matched)
        for source_key, target_slug in matched:
            print(f"  {source_key:<{max_key_len}}  ->  {target_slug}")
    else:
        print("  (none)")

    # Report unmapped (null values -- intentionally skipped)
    if unmapped:
        print(f"\nUnmapped / intentionally null ({len(unmapped)}):")
        for key in unmapped:
            print(f"  {key}")

    # Report invalid (slug not in global config -- needs fixing)
    if invalid:
        print(f"\nINVALID -- slug not in global config ({len(invalid)}):")
        for source_key, target_slug in invalid:
            print(f"  {source_key}  ->  {target_slug}  *** NOT FOUND ***")

    # Coverage stats
    referenced_slugs = {v for v in mappings.values() if v is not None}
    total_global = len(global_slugs)
    covered = len(referenced_slugs & global_slugs)

    print("\nCoverage:")
    print(f"  Local entries: {len(mappings)}")
    print(f"  Matched: {len(matched)}")
    print(f"  Unmapped (null): {len(unmapped)}")
    print(f"  Invalid: {len(invalid)}")
    print(f"  Unique target slugs: {len(referenced_slugs)}")
    print(f"  Global collections referenced: {covered}/{total_global} ({covered/total_global*100:.1f}%)")

    if invalid:
        print(f"\n  *** {len(invalid)} INVALID entries need fixing ***")

    return len(matched), len(unmapped), len(invalid)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate tool-local collection mappings against global config.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m tools.collections_align --tool t-dragon
    python -m tools.collections_align --tool tsumego-hero
    python -m tools.collections_align --check-all
        """,
    )

    parser.add_argument(
        "--tool",
        type=str,
        choices=list(TOOL_REGISTRY.keys()),
        help="Check alignment for a specific tool",
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Check alignment for all registered tools",
    )

    args = parser.parse_args()

    if not args.tool and not args.check_all:
        parser.print_help()
        return 1

    # Load global config
    global_slugs = load_global_slugs()
    print(f"Global config: {GLOBAL_CONFIG.relative_to(PROJECT_ROOT).as_posix()}")
    print(f"Global collections: {len(global_slugs)}")

    tools_to_check = list(TOOL_REGISTRY.keys()) if args.check_all else [args.tool]
    total_invalid = 0

    for tool_name in tools_to_check:
        _matched, _unmapped, invalid = check_tool(tool_name, global_slugs)
        total_invalid += invalid

    # Final summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"Tools checked: {len(tools_to_check)}")
    print(f"Global collections: {len(global_slugs)}")

    if total_invalid == 0:
        print("Status: ALL VALID")
    else:
        print(f"Status: {total_invalid} INVALID entries found")

    print(f"{'='*60}")

    return 1 if total_invalid > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
