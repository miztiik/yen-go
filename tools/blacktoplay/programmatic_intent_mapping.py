"""Programmatic mapping of BTP categories and tags using resolve_intent.

Feeds BTP category names and tag names through the puzzle_intent resolver,
then cross-references with config/tags.json for direct slug matching.
Produces a NEW mapping file for comparison with the manual mapping.

Usage: python -m tools.blacktoplay.programmatic_intent_mapping
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# BTP categories (A-O)
BTP_CATEGORIES = {
    "A": "attachments",
    "B": "basics",
    "C": "capturing",
    "D": "endgame",
    "E": "eyes",
    "F": "ko",
    "G": "placements",
    "H": "reductions",
    "I": "sacrifice",
    "J": "seki",
    "K": "semeai",
    "L": "shape",
    "M": "shortage",
    "N": "tactics",
    "O": "vital-point",
}

# All 99 BTP tag names (from the plan doc)
BTP_TAGS = [
    "atari", "attachment", "bamboo-joint", "bent-four", "blocking",
    "broken-ladder", "cap", "capture", "carriers-pigeon", "clamp",
    "close-off", "combination", "connect", "connection-cut", "crane-neck",
    "cross-cut", "cut", "dead-shape", "descend", "diagonal-tesuji",
    "double-atari", "double-hane", "draw-back", "exchange", "extend",
    "eye-shape", "geta", "guzumi", "hane", "jump",
    "keima-jump", "ko", "ko-fight", "kosumi", "ladder",
    "large-capture", "large-kill-group", "making-territory", "monkey-jump",
    "more-than-one-solution", "nakade", "net", "peep", "placement",
    "probing", "push-through", "reduce", "sacrifice", "seal-in",
    "seki", "separation", "shortage-of-liberties", "snapback", "squeeze",
    "table-shape", "throw-in", "tigers-mouth", "tombstone", "under-the-stones",
    "vital-point", "wedge", "carpenters-square", "ten-thousand-year-ko",
    "semeai", "cranes-nest", "making-eyes", "denying-eyes", "permanent-ko",
    "mirror-symmetry", "eternal-life", "thick-shape", "breaking-connection",
    "maintaining-connection", "two-step-ko", "windmill", "running",
    "surrounding", "weakening", "preventing-escape", "oiotoshi",
    "turning-move", "approach-move", "contact-play", "loose-ladder",
    "multi-step", "l-group", "bent-three", "straight-three", "bulky-five",
    "j-group", "rabbity-six", "group-status", "good-shape", "bad-shape",
    "mannen-ko", "two-headed-dragon", "flower-six", "enclosure-joseki",
    "large-scale-reduction",
]


def load_yengo_tags() -> dict[str, dict]:
    """Load YenGo tag definitions from config/tags.json."""
    with open("config/tags.json", encoding="utf-8") as f:
        data = json.load(f)
    return data["tags"]


def load_yengo_tag_aliases() -> dict[str, str]:
    """Build a lookup from alias -> tag slug."""
    tags = load_yengo_tags()
    alias_map: dict[str, str] = {}
    for slug, tag_def in tags.items():
        # Direct slug match
        alias_map[slug.lower()] = slug
        # Name match
        if "name" in tag_def:
            alias_map[tag_def["name"].lower()] = slug
        # Alias matches
        for alias in tag_def.get("aliases", []):
            alias_map[alias.lower()] = slug
    return alias_map


def direct_tag_match(btp_name: str, alias_map: dict[str, str]) -> str | None:
    """Try direct matching of BTP name against YenGo tag slugs and aliases."""
    normalized = btp_name.lower().replace("_", "-")

    # Exact match
    if normalized in alias_map:
        return alias_map[normalized]

    # Try without hyphens
    no_hyphen = normalized.replace("-", " ")
    if no_hyphen in alias_map:
        return alias_map[no_hyphen]

    # Try common transforms
    transforms = [
        normalized,
        normalized.replace("-", ""),
        normalized + "s",  # plural
        normalized.rstrip("s"),  # singular
    ]
    for t in transforms:
        if t in alias_map:
            return alias_map[t]

    return None


def resolve_via_intent(name: str) -> dict | None:
    """Use puzzle_intent resolver on a BTP name.

    Returns dict with objective info, or None.
    """
    from tools.puzzle_intent import resolve_intent

    # Try with full descriptive phrases
    phrases = [
        name,
        name.replace("-", " "),
        "black to " + name.replace("-", " "),
        name.replace("-", " ") + " problem",
    ]

    best_result = None
    best_confidence = 0.0

    for phrase in phrases:
        result = resolve_intent(phrase, enable_semantic=False)
        if result.matched and result.confidence > best_confidence:
            best_result = result
            best_confidence = result.confidence

    if best_result is None or not best_result.matched:
        return None

    return {
        "objective_id": best_result.objective_id,
        "slug": best_result.objective.slug if best_result.objective else None,
        "name": best_result.objective.name if best_result.objective else None,
        "category": best_result.objective.category if best_result.objective else None,
        "confidence": best_result.confidence,
        "match_tier": best_result.match_tier.value,
        "matched_alias": best_result.matched_alias,
    }


def objective_to_tag(objective_slug: str | None) -> str | None:
    """Map an objective slug to the most likely YenGo tag slug.

    This is a heuristic mapping from objective->tag domains.
    """
    if not objective_slug:
        return None

    OBJECTIVE_TAG_MAP = {
        "black-to-live": "life-and-death",
        "white-to-live": "life-and-death",
        "black-to-kill": "life-and-death",
        "white-to-kill": "life-and-death",
        "black-to-escape": "escape",
        "white-to-escape": "escape",
        "black-to-capture": "life-and-death",
        "white-to-capture": "life-and-death",
        "black-to-connect": "connection",
        "white-to-connect": "connection",
        "black-to-cut": "cutting",
        "white-to-cut": "cutting",
        "black-to-win-semeai": "capture-race",
        "white-to-win-semeai": "capture-race",
        "black-to-win-ko": "ko",
        "white-to-win-ko": "ko",
        "make-seki": "seki",
        "black-tesuji": "tesuji",
        "white-tesuji": "tesuji",
        "black-endgame": "endgame",
        "white-endgame": "endgame",
    }
    return OBJECTIVE_TAG_MAP.get(objective_slug)


def map_categories() -> dict[str, dict]:
    """Map BTP categories through both direct match and intent resolver."""
    alias_map = load_yengo_tag_aliases()
    results = {}

    for code, name in sorted(BTP_CATEGORIES.items()):
        entry: dict = {
            "btp_code": code,
            "btp_name": name,
            "direct_tag_match": direct_tag_match(name, alias_map),
            "intent_result": None,
            "intent_tag": None,
        }

        intent = resolve_via_intent(name)
        if intent:
            entry["intent_result"] = intent
            entry["intent_tag"] = objective_to_tag(intent.get("slug"))

        results[name] = entry

    return results


def map_tags() -> dict[str, dict]:
    """Map all 99 BTP tags through both direct match and intent resolver."""
    alias_map = load_yengo_tag_aliases()
    results = {}

    for tag_name in sorted(BTP_TAGS):
        entry: dict = {
            "btp_tag": tag_name,
            "direct_tag_match": direct_tag_match(tag_name, alias_map),
            "intent_result": None,
            "intent_tag": None,
        }

        intent = resolve_via_intent(tag_name)
        if intent:
            entry["intent_result"] = intent
            entry["intent_tag"] = objective_to_tag(intent.get("slug"))

        # Determine best programmatic mapping
        if entry["direct_tag_match"]:
            entry["programmatic_tag"] = entry["direct_tag_match"]
            entry["method"] = "direct"
        elif entry["intent_tag"]:
            entry["programmatic_tag"] = entry["intent_tag"]
            entry["method"] = "intent"
        else:
            entry["programmatic_tag"] = None
            entry["method"] = "unmapped"

        results[tag_name] = entry

    return results


def compare_with_manual(
    programmatic: dict[str, dict],
    manual_path: str = "tools/blacktoplay/_local_tag_mapping.json",
) -> list[dict]:
    """Compare programmatic tag mapping with manual mapping."""
    with open(manual_path, encoding="utf-8") as f:
        manual_data = json.load(f)

    manual_mappings = manual_data["mappings"]
    mismatches = []

    for tag_name, prog_entry in sorted(programmatic.items()):
        manual_entry = manual_mappings.get(tag_name)
        if not manual_entry:
            mismatches.append({
                "tag": tag_name,
                "issue": "missing_from_manual",
                "programmatic": prog_entry.get("programmatic_tag"),
                "manual": None,
            })
            continue

        manual_tags = manual_entry.get("yengo_tags", [])
        prog_tag = prog_entry.get("programmatic_tag")

        # Compare
        if prog_tag is None and not manual_tags:
            continue  # Both unmapped, agree
        elif prog_tag is None and manual_tags:
            mismatches.append({
                "tag": tag_name,
                "issue": "programmatic_unmapped",
                "programmatic": None,
                "manual": manual_tags,
                "manual_confidence": manual_entry.get("confidence", "?"),
            })
        elif prog_tag is not None and not manual_tags:
            mismatches.append({
                "tag": tag_name,
                "issue": "manual_unmapped",
                "programmatic": prog_tag,
                "programmatic_method": prog_entry.get("method"),
                "manual": [],
                "manual_confidence": manual_entry.get("confidence", "unmapped"),
            })
        elif prog_tag not in manual_tags:
            mismatches.append({
                "tag": tag_name,
                "issue": "different_mapping",
                "programmatic": prog_tag,
                "programmatic_method": prog_entry.get("method"),
                "manual": manual_tags,
                "manual_confidence": manual_entry.get("confidence", "?"),
            })
        # else: agree

    return mismatches


def print_category_results(categories: dict[str, dict]) -> None:
    """Print category mapping results."""
    print("=" * 80)
    print("BTP CATEGORY -> YENGO MAPPING (Programmatic)")
    print("=" * 80)
    for name, entry in sorted(categories.items()):
        direct = entry["direct_tag_match"] or "-"
        intent = entry.get("intent_tag") or "-"
        intent_obj = ""
        if entry["intent_result"]:
            intent_obj = entry["intent_result"].get("slug", "")
        print(
            "  %s (%s): direct=%-20s intent_obj=%-25s intent_tag=%-18s"
            % (entry["btp_code"], "%-14s" % name, direct, intent_obj, intent)
        )
    print()


def print_tag_results(tags: dict[str, dict]) -> None:
    """Print tag mapping statistics."""
    total = len(tags)
    direct = sum(1 for t in tags.values() if t.get("method") == "direct")
    intent = sum(1 for t in tags.values() if t.get("method") == "intent")
    unmapped = sum(1 for t in tags.values() if t.get("method") == "unmapped")

    print("=" * 80)
    print("BTP TAG -> YENGO TAG MAPPING (Programmatic)")
    print("=" * 80)
    print("  Total: %d" % total)
    print("  Direct match: %d" % direct)
    print("  Intent-derived: %d" % intent)
    print("  Unmapped: %d" % unmapped)
    print()

    print("MAPPED TAGS:")
    for name, entry in sorted(tags.items()):
        prog_tag = entry.get("programmatic_tag")
        if prog_tag:
            method = entry.get("method", "?")
            print("  %-30s -> %-20s [%s]" % (name, prog_tag, method))

    print("\nUNMAPPED TAGS:")
    for name, entry in sorted(tags.items()):
        if not entry.get("programmatic_tag"):
            print("  %-30s" % name)
    print()


def print_mismatches(mismatches: list[dict]) -> None:
    """Print comparison mismatches."""
    if not mismatches:
        print("NO MISMATCHES - programmatic and manual mappings agree!")
        return

    print("=" * 80)
    print("MISMATCHES: Programmatic vs Manual (%d)" % len(mismatches))
    print("=" * 80)

    by_issue: dict[str, list[dict]] = {}
    for m in mismatches:
        by_issue.setdefault(m["issue"], []).append(m)

    for issue_type, items in sorted(by_issue.items()):
        print("\n--- %s (%d) ---" % (issue_type.upper(), len(items)))
        for m in items:
            tag = m["tag"]
            prog = m.get("programmatic") or "(unmapped)"
            manual = m.get("manual") or "(unmapped)"
            manual_conf = m.get("manual_confidence", "")
            method = m.get("programmatic_method", "")
            print(
                "  %-28s  prog=%-18s [%s]  manual=%-24s [%s]"
                % (tag, prog, method, str(manual), manual_conf)
            )
    print()


def main() -> int:
    print("Running programmatic intent mapping...\n")

    # Map categories
    print("Mapping 15 BTP categories...")
    categories = map_categories()
    print_category_results(categories)

    # Map tags
    print("Mapping %d BTP tags..." % len(BTP_TAGS))
    tags = map_tags()
    print_tag_results(tags)

    # Compare with manual
    manual_path = Path("tools/blacktoplay/_local_tag_mapping.json")
    if manual_path.exists():
        print("Comparing with manual mapping...")
        mismatches = compare_with_manual(tags, str(manual_path))
        print_mismatches(mismatches)
    else:
        print(f"Manual mapping not found at {manual_path}, skipping comparison.")

    # Save results
    output_dir = Path("tools/blacktoplay/verification_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    output = {
        "version": "1.0.0",
        "description": "Programmatic BTP->YenGo mapping via resolve_intent + direct tag matching",
        "categories": {},
        "tags": {},
    }

    # Serialize categories (strip non-serializable)
    for name, entry in categories.items():
        output["categories"][name] = {
            "btp_code": entry["btp_code"],
            "direct_tag_match": entry["direct_tag_match"],
            "intent_objective": entry["intent_result"]["slug"] if entry["intent_result"] else None,
            "intent_tag": entry["intent_tag"],
        }

    # Serialize tags
    for name, entry in tags.items():
        output["tags"][name] = {
            "programmatic_tag": entry.get("programmatic_tag"),
            "method": entry.get("method"),
            "direct_tag_match": entry.get("direct_tag_match"),
            "intent_objective": entry["intent_result"]["slug"] if entry.get("intent_result") else None,
            "intent_tag": entry.get("intent_tag"),
        }

    out_path = output_dir / "programmatic_intent_mapping.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"Results saved to {out_path}")

    # Save comparison
    if manual_path.exists():
        mismatches = compare_with_manual(tags, str(manual_path))
        comparison_path = output_dir / "manual_vs_programmatic_comparison.json"
        with open(comparison_path, "w", encoding="utf-8") as f:
            json.dump({"mismatches": mismatches, "total_mismatches": len(mismatches)}, f, indent=2)
        print(f"Comparison saved to {comparison_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
