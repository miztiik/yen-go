"""
Apply re-translated Shokyuu comments to SGF files.
Replaces garbled machine-translated C[] values with proper English.

Usage:
    python tools/kisvadim_goproblems/_apply_shokyuu_retranslation.py [--dry-run]
"""
import argparse
import json
import re
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent
SHOKYUU_DIR = BASE / "external-sources" / "kisvadim-goproblems" / "GO SEIGEN Tsumego Collection 1 - Shokyuu"


def load_mapping() -> dict[str, str]:
    """Load translation mapping from _translations_shokyuu.json."""
    trans_file = Path(__file__).resolve().parent / "_translations_shokyuu.json"
    if trans_file.exists():
        return json.loads(trans_file.read_text(encoding="utf-8"))
    raise FileNotFoundError(f"Translation file not found: {trans_file}")


def apply_translations(dry_run: bool = False) -> None:
    mapping = load_mapping()
    print(f"Loaded {len(mapping)} translation mappings")

    c_pattern = re.compile(r"C\[([^\]]*)\]")
    files_changed = 0
    replacements_total = 0

    for sgf_file in sorted(SHOKYUU_DIR.glob("*.sgf")):
        text = sgf_file.read_text(encoding="utf-8", errors="replace")
        new_text = text
        file_replacements = 0

        for old_val, new_val in mapping.items():
            old_c = f"C[{old_val}]"
            new_c = f"C[{new_val}]"
            if old_c in new_text:
                new_text = new_text.replace(old_c, new_c)
                file_replacements += 1

        if file_replacements > 0:
            files_changed += 1
            replacements_total += file_replacements
            if dry_run:
                print(f"  [DRY-RUN] {sgf_file.name}: {file_replacements} replacements")
            else:
                sgf_file.write_text(new_text, encoding="utf-8")
                print(f"  {sgf_file.name}: {file_replacements} replacements")

    print(f"\n{'[DRY-RUN] ' if dry_run else ''}Files changed: {files_changed}, Total replacements: {replacements_total}")


def main():
    parser = argparse.ArgumentParser(description="Apply Shokyuu re-translations")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply_translations(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
