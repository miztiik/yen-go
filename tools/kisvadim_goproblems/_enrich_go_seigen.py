"""
Go Seigen enrichment script: translate CJK, strip watermarks, merge N[], embed YL[].

Usage:
    python -m tools.kisvadim_goproblems._enrich_go_seigen [--dry-run] [--step STEP]

Steps:
    translate   - Apply CJK translations to C[] and N[] properties
    merge-n     - Merge N[] into C[] for Shokyuu files
    embed-yl    - Embed YL[] collection membership tags
    all         - Run all steps in order (default)
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
EXT_SRC = BASE / "external-sources" / "kisvadim-goproblems"
TRANS_DIR = Path(__file__).resolve().parent


def load_translations() -> dict[str, str]:
    """Load all translation JSON files and merge into a single mapping."""
    mapping: dict[str, str] = {}
    trans_files = sorted(TRANS_DIR.glob("_translations_*.json"))
    for tf in trans_files:
        data = json.loads(tf.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            mapping.update(data)
        else:
            print(f"WARNING: {tf.name} is not a dict, skipping")
    print(f"Loaded {len(mapping)} translations from {len(trans_files)} files")
    return mapping


# Structural text replacements (no sub-agent needed)
STRUCTURAL_REPLACEMENTS: dict[str, str] = {
    "正解图": "Solution diagram",
    "正解": "Correct",
    "失败图1": "Failure 1",
    "失败图2": "Failure 2",
    "失败图": "Failure",
    "变化图1": "Variation 1",
    "变化图2": "Variation 2",
    "变化图": "Variation",
    "飞扬围棋出品": "",  # watermark removal
}


def translate_comment(text: str, mapping: dict[str, str]) -> str:
    """Translate a C[] or N[] value using the mapping."""
    original = text

    # Strip watermark patterns first
    text = text.replace("\r\n飞扬围棋出品", "")
    text = text.replace("飞扬围棋出品", "")

    # Try exact match first
    stripped = text.strip()
    if stripped in mapping:
        return mapping[stripped]

    # Try structural replacements for standalone labels
    if stripped in STRUCTURAL_REPLACEMENTS:
        return STRUCTURAL_REPLACEMENTS[stripped]

    # For compound texts like "正解图\r\n飞扬围棋出品", after stripping watermark
    # we may have just "正解图" left
    stripped_clean = stripped.replace("\r\n", "").strip()
    if stripped_clean in STRUCTURAL_REPLACEMENTS:
        return STRUCTURAL_REPLACEMENTS[stripped_clean]
    if stripped_clean in mapping:
        return mapping[stripped_clean]

    # If no match, return cleaned text (watermarks stripped)
    return text


def has_cjk(text: str) -> bool:
    """Check if text contains CJK characters."""
    return any(ord(c) > 0x7F for c in text)


def apply_translations(dry_run: bool = False) -> None:
    """Apply CJK translations across all Go Seigen directories."""
    mapping = load_translations()
    mapping.update(STRUCTURAL_REPLACEMENTS)

    dirs_to_translate = [
        "GO SEIGEN Striving Constantly For Self-Improvement",
        "GO SEIGEN Tsumego Collection - The Long-Lived Stone Is Not Old",
        "GO SEIGEN Tsumego Collection 1 - Shokyuu",
        "segoe-kensaku-tesuji-dictionary_split",
    ]

    total_files = 0
    total_translated = 0
    total_untranslated: set[str] = set()

    for dirname in dirs_to_translate:
        dirpath = EXT_SRC / dirname
        if not dirpath.exists():
            print(f"SKIP: {dirname} not found")
            continue

        sgf_files = sorted(dirpath.glob("*.sgf"))
        dir_translated = 0

        for sgf_file in sgf_files:
            data = sgf_file.read_text(encoding="utf-8")
            modified = False

            # Translate C[] properties
            def replace_c(m: re.Match) -> str:
                nonlocal modified
                val = m.group(1)
                if not has_cjk(val):
                    return m.group(0)
                translated = translate_comment(val, mapping)
                if translated != val:
                    modified = True
                    return f"C[{translated}]"
                total_untranslated.add(val.strip()[:60])
                return m.group(0)

            new_data = re.sub(r"C\[([^\]]*)\]", replace_c, data)

            # Translate N[] properties
            def replace_n(m: re.Match) -> str:
                nonlocal modified
                val = m.group(1)
                if not has_cjk(val):
                    return m.group(0)
                translated = translate_comment(val, mapping)
                if translated != val:
                    modified = True
                    return f"N[{translated}]"
                total_untranslated.add(val.strip()[:60])
                return m.group(0)

            new_data = re.sub(r"N\[([^\]]*)\]", replace_n, new_data)

            if modified:
                dir_translated += 1
                if not dry_run:
                    sgf_file.write_text(new_data, encoding="utf-8")

        total_files += len(sgf_files)
        total_translated += dir_translated
        action = "would translate" if dry_run else "translated"
        print(f"  {dirname}: {action} {dir_translated}/{len(sgf_files)} files")

    print(f"\nTotal: {total_translated}/{total_files} files")
    if total_untranslated:
        print(f"Untranslated CJK texts ({len(total_untranslated)}):")
        for t in sorted(total_untranslated)[:20]:
            print(f"  {t}")
        if len(total_untranslated) > 20:
            print(f"  ... and {len(total_untranslated) - 20} more")


def merge_n_into_c(dry_run: bool = False) -> None:
    """Merge N[] properties into C[] for Shokyuu files that have them."""
    # N[] in SGF is the "node name" — we merge it as a prefix to C[]
    dirpath = EXT_SRC / "GO SEIGEN Tsumego Collection 1 - Shokyuu"
    sgf_files = sorted(dirpath.glob("*.sgf"))
    merged_count = 0

    for sgf_file in sgf_files:
        data = sgf_file.read_text(encoding="utf-8")
        if "N[" not in data:
            continue

        # Find all nodes with N[] and optionally C[]
        # Strategy: for each N[...] occurrence, if the same node has C[...],
        # prepend N value to C value. If no C[], convert N[] to C[].
        modified = False

        # Simple approach: within each node (between ; and next ;/)),
        # find N[] and C[] and merge them
        def merge_node(node: str) -> str:
            nonlocal modified
            n_match = re.search(r"N\[([^\]]*)\]", node)
            if not n_match:
                return node
            n_val = n_match.group(1).strip()
            if not n_val:
                return node

            c_match = re.search(r"C\[([^\]]*)\]", node)
            if c_match:
                c_val = c_match.group(1)
                # Prepend N[] value to C[] with separator
                new_c = f"{n_val}: {c_val}" if c_val.strip() else n_val
                node = node.replace(c_match.group(0), f"C[{new_c}]")
            else:
                # Convert N[] to C[]
                node = node.replace(n_match.group(0), f"C[{n_val}]")

            # Remove original N[]
            node = re.sub(r"N\[[^\]]*\]", "", node)
            modified = True
            return node

        # Split by nodes (;...) — process each node
        parts = re.split(r"(;)", data)
        result = []
        current_node = ""
        for part in parts:
            if part == ";":
                if current_node:
                    result.append(merge_node(current_node))
                current_node = ";"
            else:
                current_node += part
        if current_node:
            result.append(merge_node(current_node))

        new_data = "".join(result)

        if modified:
            merged_count += 1
            if not dry_run:
                sgf_file.write_text(new_data, encoding="utf-8")

    action = "Would merge" if dry_run else "Merged"
    print(f"{action} N[] into C[] for {merged_count}/{len(sgf_files)} Shokyuu files")


def embed_yl(dry_run: bool = False) -> None:
    """Embed YL[] collection membership tags in all Go Seigen SGF files."""
    state = json.loads(
        (BASE / "tools" / "kisvadim_goproblems" / "_enrichment_state.json")
        .read_text(encoding="utf-8")
    )

    yl_configs: list[dict] = []

    # Build YL config for each directory
    go_seigen_dirs = {
        k: v for k, v in state["directories"].items()
        if k.startswith("GO SEIGEN") and v.get("slug")
    }

    for name, info in go_seigen_dirs.items():
        slug = info["slug"]
        chapters = info.get("chapters")
        chapter = info.get("chapter")
        vol_offset = info.get("volume_offset", 0)

        if name == "GO SEIGEN - SEGOE TESUJI DICTIONARY":
            # Skip — split files are the enrichment target
            continue

        if chapters:
            # Has chapter subdirectories (Reading+Training)
            for ch_dir, ch_slug in chapters.items():
                yl_configs.append({
                    "dir": os.path.join(name, ch_dir),
                    "slug": slug,
                    "chapter": ch_slug,
                    "offset": 0,  # Each chapter starts from 1
                })
        elif chapter:
            yl_configs.append({
                "dir": name,
                "slug": slug,
                "chapter": chapter,
                "offset": vol_offset,
            })
        else:
            yl_configs.append({
                "dir": name,
                "slug": slug,
                "chapter": None,
                "offset": vol_offset,
            })

    # Segoe split: derive chapter from filename technique prefix
    yl_configs.append({
        "dir": "segoe-kensaku-tesuji-dictionary_split",
        "slug": "segoe-kensaku-tesuji-dictionary",
        "chapter": "__from_filename__",
        "offset": 0,
    })

    total_embedded = 0
    total_files = 0

    for cfg in yl_configs:
        dirpath = EXT_SRC / cfg["dir"]
        if not dirpath.exists():
            print(f"  SKIP: {cfg['dir']} not found")
            continue

        sgf_files = sorted(dirpath.glob("*.sgf"))
        dir_count = 0

        for sgf_file in sgf_files:
            data = sgf_file.read_text(encoding="utf-8")

            # Skip if already has YL[]
            if "YL[" in data:
                continue

            # Determine sequence number
            fname = sgf_file.stem
            if cfg["chapter"] == "__from_filename__":
                # Segoe: derive technique and problem number from filename
                m = re.match(r"^([a-z]+)\d+_(\d+[ab]?)$", fname)
                if not m:
                    print(f"  WARNING: can't parse {sgf_file.name}")
                    continue
                technique = m.group(1)
                prob_num = m.group(2)
                yl_val = f"{cfg['slug']}:{technique}/{prob_num}"
            else:
                # Extract number from 4-digit filename
                try:
                    num = int(fname)
                except ValueError:
                    print(f"  WARNING: non-numeric filename {sgf_file.name}")
                    continue

                seq = num + cfg["offset"]

                if cfg["chapter"]:
                    yl_val = f"{cfg['slug']}:{cfg['chapter']}/{seq}"
                else:
                    yl_val = f"{cfg['slug']}:{seq}"

            # Insert YL[] after the root node opening
            # Find first ; and insert after the root properties
            # Pattern: insert before the first move or child node
            insert_pos = data.find(";")
            if insert_pos < 0:
                continue

            # Find the end of root properties (before first B[/W[ move or child ;)
            # Simple: insert right before the first move semicolon or first B[/W[
            root_end = None
            # Find first occurrence of ;B[ or ;W[ after the root ;
            for pattern in [";B[", ";W[", "(;"]:
                idx = data.find(pattern, insert_pos + 1)
                if idx >= 0 and (root_end is None or idx < root_end):
                    root_end = idx

            if root_end is None:
                # No moves found, insert at end of root node
                root_end = data.rfind(")")

            yl_prop = f"YL[{yl_val}]"
            new_data = data[:root_end] + yl_prop + data[root_end:]

            dir_count += 1
            if not dry_run:
                sgf_file.write_text(new_data, encoding="utf-8")

        total_embedded += dir_count
        total_files += len(sgf_files)
        action = "would embed" if dry_run else "embedded"
        print(f"  {cfg['dir']}: {action} YL[] in {dir_count}/{len(sgf_files)} files")

    print(f"\nTotal: embedded YL[] in {total_embedded}/{total_files} files")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich Go Seigen SGF files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--step", default="all",
                        choices=["translate", "merge-n", "embed-yl", "all"],
                        help="Which enrichment step to run")
    args = parser.parse_args()

    steps = ["translate", "merge-n", "embed-yl"] if args.step == "all" else [args.step]

    for step in steps:
        print(f"\n{'='*60}")
        print(f"Step: {step}")
        print(f"{'='*60}")

        if step == "translate":
            apply_translations(dry_run=args.dry_run)
        elif step == "merge-n":
            merge_n_into_c(dry_run=args.dry_run)
        elif step == "embed-yl":
            embed_yl(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
