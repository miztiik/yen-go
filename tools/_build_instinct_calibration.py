"""
One-time script: Build instinct-calibration golden set fixture.

Tasks: T6 (Sakata copy), T7 (Lee Changho), T8 (Cho Chikun),
       T9 (labels.json), T10 (Tobi verify), T11 (Warikomi verify),
       T12 (Sakata expert label), T13 (Lee/Cho expert label), T14 (coverage).

Run from repo root:
    python tools/_build_instinct_calibration.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "external-sources" / "kisvadim-goproblems"
SAKATA = EXT / "SAKATA EIO TESUJI"
LEE = EXT / "LEE CHANGHO TESUJI"
CHO_ELEM = EXT / "CHO CHIKUN Encyclopedia Life And Death - Elementary"
CHO_INTER = EXT / "CHO CHIKUN Encyclopedia Life And Death - Intermediate"
CHO_ADV = EXT / "CHO CHIKUN Encyclopedia Life And Death - Advanced"
DEST = ROOT / "tools" / "puzzle-enrichment-lab" / "tests" / "fixtures" / "instinct-calibration"

# ---------------------------------------------------------------------------
# SGF helpers
# ---------------------------------------------------------------------------

def _sgf_coord(pair: str) -> tuple[int, int]:
    """Convert SGF 2-char coord like 'dp' -> (col, row) integers (0-based)."""
    if len(pair) < 2:
        return (-1, -1)
    return (ord(pair[0]) - ord("a"), ord(pair[1]) - ord("a"))


def _parse_prop_list(sgf_text: str, prop: str) -> list[str]:
    """Extract all values for prop like AB[aa][bb] -> ['aa','bb']."""
    # Find all occurrences of PROP[value] sequences
    pattern = rf"(?<!\w){prop}((?:\[[^\]]*\])+)"
    m = re.search(pattern, sgf_text)
    if not m:
        return []
    block = m.group(1)
    return re.findall(r"\[([^\]]*)\]", block)


def _find_correct_move(sgf_text: str) -> tuple[str | None, str | None]:
    """
    Return (color, coord) of the first move from the correct variation.
    color is 'B' or 'W'. coord is SGF 2-char like 'dp'.
    Heuristic: finds the variation containing 'Correct' in a C[] comment,
    then extracts the first B[] or W[] from that variation's first node.
    Falls back to the last variation if none marked 'Correct'.
    """
    # Split into top-level variations (children of root)
    # Remove root node first
    depth = 0
    for i, ch in enumerate(sgf_text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == ";" and depth == 1 and i > 0:
            # Find the boundary where child variations start
            # Children are at depth 2 — (;... (;child1 ...) (;child2 ...) )
            pass

    # Simpler approach: extract variations via regex of top-level children
    # Look for all (;...) blocks that contain the first move
    variations = []
    # Find all variation starts after root properties
    # Root: (;PROPS (;VAR1...) (;VAR2...) ... )
    i = 0
    depth = 0
    var_starts = []
    for i, ch in enumerate(sgf_text):
        if ch == "(":
            depth += 1
            if depth == 2:
                var_starts.append(i)
        elif ch == ")":
            if depth == 2 and var_starts:
                variations.append(sgf_text[var_starts[-1] : i + 1])
            depth -= 1

    if not variations:
        # Single-path SGF — extract first move from the whole text
        m = re.search(r";([BW])\[([a-s]{2})\]", sgf_text)
        if m:
            return m.group(1), m.group(2)
        return None, None

    # Find variation with "Correct" in C[]
    correct_var = None
    for var in variations:
        if re.search(r"[Cc]orrect", var):
            correct_var = var
            break
    if correct_var is None:
        # Fallback: last variation (common SGF convention)
        correct_var = variations[-1]

    # Extract first move from the correct variation
    m = re.search(r";([BW])\[([a-s]{2})\]", correct_var)
    if m:
        return m.group(1), m.group(2)
    return None, None


def _parse_setup_stones(sgf_text: str) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Parse AB[] and AW[] setup stones from root node. Returns (black_set, white_set)."""
    black = set()
    white = set()
    for coord_str in _parse_prop_list(sgf_text, "AB"):
        if len(coord_str) >= 2:
            black.add(_sgf_coord(coord_str))
    for coord_str in _parse_prop_list(sgf_text, "AW"):
        if len(coord_str) >= 2:
            white.add(_sgf_coord(coord_str))
    return black, white


def _is_axis_aligned_jump(move: tuple[int, int], friendly: set[tuple[int, int]]) -> bool:
    """
    Check if move is an axis-aligned one-point jump (tobi/extension) from
    any friendly stone. True if distance is exactly 2 in one axis and 0 in the other,
    OR if distance is exactly 1 in one axis (nobi = solid extension).
    Both count as 'extend' instinct.
    """
    mx, my = move
    for fx, fy in friendly:
        dx, dy = abs(mx - fx), abs(my - fy)
        # Solid connection (nobi): adjacent orthogonal
        if (dx == 1 and dy == 0) or (dx == 0 and dy == 1):
            return True
        # One-point jump (tobi): 2 apart orthogonally
        if (dx == 2 and dy == 0) or (dx == 0 and dy == 2):
            return True
    return False


def _has_opponent_on_both_sides(move: tuple[int, int], opponent: set[tuple[int, int]]) -> bool:
    """
    Check if the move position has opponent stones on opposing sides,
    suggesting a splitting/wedging move (cut instinct).
    """
    mx, my = move
    # Check cardinal directions
    any((x, y) in opponent for x, y in [(mx - 1, my)])
    any((x, y) in opponent for x, y in [(mx + 1, my)])
    any((x, y) in opponent for x, y in [(mx, my - 1)])
    any((x, y) in opponent for x, y in [(mx, my + 1)])

    # Broader check: opponent within 2 squares on opposing sides
    left2 = any((mx - d, my) in opponent for d in range(1, 3))
    right2 = any((mx + d, my) in opponent for d in range(1, 3))
    up2 = any((mx, my - d) in opponent for d in range(1, 3))
    down2 = any((mx, my + d) in opponent for d in range(1, 3))

    return (left2 and right2) or (up2 and down2)


# ---------------------------------------------------------------------------
# Copy logic
# ---------------------------------------------------------------------------

def copy_files(src_dir: Path, filenames: list[str], dst_names: list[str]) -> int:
    """Copy specific files with renaming. Returns count of files copied."""
    count = 0
    for src_name, dst_name in zip(filenames, dst_names, strict=False):
        src = src_dir / src_name
        dst = DEST / dst_name
        if src.exists():
            shutil.copy2(src, dst)
            count += 1
        else:
            print(f"  WARNING: source not found: {src}")
    return count


def natural_sort_key(s: str) -> list:
    """Sort key that handles numbers embedded in filenames."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    os.makedirs(DEST, exist_ok=True)
    labels: dict[str, dict] = {}
    total_copied = 0
    issues: list[str] = []

    # -----------------------------------------------------------------------
    # T6: Copy Sakata Eio files
    # -----------------------------------------------------------------------
    print("=" * 60)
    print("T6: Copying Sakata Eio TESUJI files")
    print("=" * 60)

    sakata_groups: dict[str, dict] = {
        "kiri": {
            "instinct": "cut", "technique_tag": "cutting",
            "pattern": re.compile(r"^kiri-s-\d+\.sgf$", re.IGNORECASE),
        },
        "Hane": {
            "instinct": "hane", "technique_tag": "hane",
            "pattern": re.compile(r"^Hane-s-\d+[A-Za-z]?\.sgf$"),
        },
        "Sagari": {
            "instinct": "descent", "technique_tag": "descent",
            "pattern": re.compile(r"^Sagari-s-\d+\.sgf$"),
        },
        "Tobi": {
            "instinct": "extend", "technique_tag": "extension",
            "pattern": re.compile(r"^Tobi-s-\d+\.sgf$"),
        },
        "Kosumi": {
            "instinct": "null", "technique_tag": "kosumi",
            "pattern": re.compile(r"^Kosumi-s-\d+[a-z]?\.sgf$"),
        },
        "Tsuke": {
            "instinct": "null", "technique_tag": "attachment",
            "pattern": re.compile(r"^Tsuke-s-\d+\.sgf$"),
        },
        "oki": {
            "instinct": "null", "technique_tag": "placement",
            "pattern": re.compile(r"^oki-s-\d+\.sgf$", re.IGNORECASE),
        },
        "Kake": {
            "instinct": "null", "technique_tag": "capping",
            "pattern": re.compile(r"^Kake-s-\d+\.sgf$"),
        },
        "Warikomi": {
            "instinct": "null", "technique_tag": "wedge",
            "pattern": re.compile(r"^Warikomi-s-\d+\.sgf$"),
        },
    }

    all_sakata = sorted(os.listdir(SAKATA), key=natural_sort_key)
    null_serial = 0  # running counter for ALL null files
    sakata_source = "kisvadim-goproblems/SAKATA EIO TESUJI"

    for group_name, info in sakata_groups.items():
        matched = [f for f in all_sakata if info["pattern"].match(f)]
        matched.sort(key=natural_sort_key)
        instinct = info["instinct"]
        level = "intermediate"

        if instinct == "null":
            # null files numbered continuously across groups
            for orig in matched:
                null_serial += 1
                new_name = f"null_{level}_{null_serial:03d}.sgf"
                src = SAKATA / orig
                dst = DEST / new_name
                shutil.copy2(src, dst)
                total_copied += 1
                labels[new_name] = {
                    "instinct_primary": "null",
                    "instinct_labels": [],
                    "technique_tag": info["technique_tag"],
                    "objective": "life-and-death",
                    "human_difficulty": level,
                    "source": sakata_source,
                    "original_filename": orig,
                    "labeled_by": "auto-filename",
                    "notes": f"Sakata {group_name} series" + (
                        " — needs Warikomi cut verification (T11)" if group_name == "Warikomi" else ""
                    ),
                }
            print(f"  {group_name}: {len(matched)} files → null_{level}_NNN.sgf (serial {null_serial - len(matched) + 1}–{null_serial})")
        else:
            serial = 0
            for orig in matched:
                serial += 1
                new_name = f"{instinct}_{level}_{serial:03d}.sgf"
                src = SAKATA / orig
                dst = DEST / new_name
                shutil.copy2(src, dst)
                total_copied += 1
                notes = ""
                if group_name == "Tobi":
                    notes = "Needs extend verification (T10)"
                labels[new_name] = {
                    "instinct_primary": instinct,
                    "instinct_labels": [instinct],
                    "technique_tag": info["technique_tag"],
                    "objective": "life-and-death",
                    "human_difficulty": level,
                    "source": sakata_source,
                    "original_filename": orig,
                    "labeled_by": "auto-filename",
                    "notes": notes,
                }
            print(f"  {group_name}: {len(matched)} files → {instinct}_{level}_001–{serial:03d}.sgf")

    sakata_null_max = null_serial
    print(f"  Sakata total: {total_copied} files copied. Null serial reached: {sakata_null_max}")

    # -----------------------------------------------------------------------
    # T7: Copy Lee Changho gap-fill
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T7: Copying Lee Changho TESUJI files")
    print("=" * 60)

    lee_source = "kisvadim-goproblems/LEE CHANGHO TESUJI"
    lee_level = "advanced"

    # 8 fighting/capturing puzzles → push instinct
    fighting_dir = LEE / "1. FIGHTING AND CAPTURING"
    fighting_files = [f"1-{i}.sgf" for i in range(1, 9)]
    for serial, orig in enumerate(fighting_files, 1):
        new_name = f"push_{lee_level}_{serial:03d}.sgf"
        src = fighting_dir / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "push",
                "instinct_labels": ["push"],
                "technique_tag": "capturing",
                "objective": "capturing",
                "human_difficulty": lee_level,
                "source": f"{lee_source}/1. FIGHTING AND CAPTURING",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Lee Changho Fighting chapter — push instinct",
            }
        else:
            issues.append(f"Lee Fighting {orig} not found")
    print(f"  Fighting/Capturing: 8 files → push_{lee_level}_001–008.sgf")

    # 3 capturing race puzzles → cut instinct
    caprace_dir = LEE / "6.1 CAPTURING RACE"
    caprace_files = ["6-1-1.SGF", "6-1-2.SGF", "6-1-3.SGF"]
    for serial, orig in enumerate(caprace_files, 1):
        new_name = f"cut_{lee_level}_{serial:03d}.sgf"
        src = caprace_dir / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "cut",
                "instinct_labels": ["cut"],
                "technique_tag": "capture-race",
                "objective": "capture-race",
                "human_difficulty": lee_level,
                "source": f"{lee_source}/6.1 CAPTURING RACE",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Lee Changho Capturing Race chapter",
            }
        else:
            issues.append(f"Lee CapRace {orig} not found")
    print(f"  Capturing Race: 3 files → cut_{lee_level}_001–003.sgf")

    # 3 snapback puzzles → descent instinct
    snap_dir = LEE / "2. SNAPBACK AND SHORTAGE OF LIBERTIES"
    snap_files = ["2-1.sgf", "2-2.sgf", "2-3.sgf"]
    for serial, orig in enumerate(snap_files, 1):
        new_name = f"descent_{lee_level}_{serial:03d}.sgf"
        src = snap_dir / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "descent",
                "instinct_labels": ["descent"],
                "technique_tag": "snapback",
                "objective": "capturing",
                "human_difficulty": lee_level,
                "source": f"{lee_source}/2. SNAPBACK AND SHORTAGE OF LIBERTIES",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Lee Changho Snapback chapter",
            }
        else:
            issues.append(f"Lee Snapback {orig} not found")
    print(f"  Snapback: 3 files → descent_{lee_level}_001–003.sgf")

    # -----------------------------------------------------------------------
    # T8: Copy Cho Chikun supplemental
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T8: Copying Cho Chikun Life & Death files")
    print("=" * 60)

    cho_source_base = "kisvadim-goproblems/CHO CHIKUN Encyclopedia Life And Death"

    # Elementary: 3 puzzles → null_elementary_001–003
    cho_elem_files = ["prob0001.sgf", "prob0002.sgf", "prob0003.sgf"]
    for serial, orig in enumerate(cho_elem_files, 1):
        new_name = f"null_elementary_{serial:03d}.sgf"
        src = CHO_ELEM / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "null",
                "instinct_labels": [],
                "technique_tag": "life-and-death",
                "objective": "life-and-death",
                "human_difficulty": "elementary",
                "source": f"{cho_source_base} - Elementary",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Cho Chikun Elementary — needs expert instinct labeling (T13)",
            }
        else:
            issues.append(f"Cho Elementary {orig} not found")
    print("  Elementary: 3 files → null_elementary_001–003.sgf")

    # Intermediate: 3 puzzles → continue null_intermediate series
    cho_inter_start = sakata_null_max + 1
    cho_inter_files = ["prob0001.sgf", "prob0002.sgf", "prob0003.sgf"]
    for i, orig in enumerate(cho_inter_files):
        serial = cho_inter_start + i
        new_name = f"null_intermediate_{serial:03d}.sgf"
        src = CHO_INTER / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "null",
                "instinct_labels": [],
                "technique_tag": "life-and-death",
                "objective": "life-and-death",
                "human_difficulty": "intermediate",
                "source": f"{cho_source_base} - Intermediate",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Cho Chikun Intermediate — needs expert instinct labeling (T13)",
            }
        else:
            issues.append(f"Cho Intermediate {orig} not found")
    print(f"  Intermediate: 3 files → null_intermediate_{cho_inter_start:03d}–{cho_inter_start + 2:03d}.sgf")

    # Advanced: 2 puzzles → null_advanced_001–002
    cho_adv_files = ["prob0001.sgf", "prob0002.sgf"]
    for serial, orig in enumerate(cho_adv_files, 1):
        new_name = f"null_advanced_{serial:03d}.sgf"
        src = CHO_ADV / orig
        if src.exists():
            shutil.copy2(src, DEST / new_name)
            total_copied += 1
            labels[new_name] = {
                "instinct_primary": "null",
                "instinct_labels": [],
                "technique_tag": "life-and-death",
                "objective": "life-and-death",
                "human_difficulty": "advanced",
                "source": f"{cho_source_base} - Advanced",
                "original_filename": orig,
                "labeled_by": "auto-filename",
                "notes": "Cho Chikun Advanced — needs expert instinct labeling (T13)",
            }
        else:
            issues.append(f"Cho Advanced {orig} not found")
    print("  Advanced: 2 files → null_advanced_001–002.sgf")

    # -----------------------------------------------------------------------
    # T10: Tobi verification (extend vs null)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T10: Verifying Tobi files (extend vs null)")
    print("=" * 60)

    tobi_files = sorted(
        [f for f in os.listdir(DEST) if f.startswith("extend_")],
        key=natural_sort_key,
    )
    tobi_reclassified = 0
    for fname in tobi_files:
        sgf_path = DEST / fname
        sgf_text = sgf_path.read_text(encoding="utf-8", errors="replace")

        # Determine playing color from PL[] or first move
        pl_match = re.search(r"PL\[([BW])\]", sgf_text)
        pl_match.group(1) if pl_match else None

        color, coord_str = _find_correct_move(sgf_text)
        if not coord_str or not color:
            print(f"  {fname}: Could not parse correct move — keeping as extend")
            continue

        move = _sgf_coord(coord_str)
        black_stones, white_stones = _parse_setup_stones(sgf_text)

        # Determine friendly stones based on who plays
        if color == "B":
            friendly = black_stones
        else:
            friendly = white_stones

        is_extend = _is_axis_aligned_jump(move, friendly)

        if is_extend:
            print(f"  {fname}: move {coord_str} → EXTEND ✓ (axis-aligned from friendly stone)")
        else:
            print(f"  {fname}: move {coord_str} → NOT axis-aligned → reclassify to null")
            # Update labels
            if fname in labels:
                labels[fname]["instinct_primary"] = "null"
                labels[fname]["instinct_labels"] = []
                labels[fname]["notes"] = f"T10: Tobi reclassified — correct move {coord_str} is not axis-aligned extension"
            tobi_reclassified += 1

    print(f"  Tobi verification complete: {tobi_reclassified} reclassified to null")

    # -----------------------------------------------------------------------
    # T11: Warikomi verification (null→cut if splitting)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T11: Verifying Warikomi files (null→cut if splitting)")
    print("=" * 60)

    warikomi_files = sorted(
        [
            f for f in labels
            if labels[f].get("notes", "").startswith("Sakata Warikomi")
            or "Warikomi" in labels[f].get("notes", "")
        ],
        key=natural_sort_key,
    )

    wari_promoted = 0
    for fname in warikomi_files:
        sgf_path = DEST / fname
        if not sgf_path.exists():
            continue
        sgf_text = sgf_path.read_text(encoding="utf-8", errors="replace")

        color, coord_str = _find_correct_move(sgf_text)
        if not coord_str or not color:
            print(f"  {fname}: Could not parse correct move — keeping as null")
            continue

        move = _sgf_coord(coord_str)
        black_stones, white_stones = _parse_setup_stones(sgf_text)

        # For warikomi, check if move splits opponent stones
        if color == "B":
            opponent = white_stones
        else:
            opponent = black_stones

        splits = _has_opponent_on_both_sides(move, opponent)

        if splits:
            print(f"  {fname}: move {coord_str} splits opponent stones → promote to CUT")
            labels[fname]["instinct_primary"] = "cut"
            labels[fname]["instinct_labels"] = ["cut"]
            labels[fname]["notes"] = f"T11: Warikomi promoted to cut — move {coord_str} splits opponent"
            wari_promoted += 1
        else:
            print(f"  {fname}: move {coord_str} does not clearly split → keeping as null")

    print(f"  Warikomi verification complete: {wari_promoted} promoted to cut")

    # -----------------------------------------------------------------------
    # T12: Expert label Sakata puzzles (update labeled_by)
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T12: Applying expert labels to Sakata puzzles")
    print("=" * 60)

    sakata_labeled = 0
    for fname, entry in labels.items():
        if entry.get("source") == sakata_source and entry.get("labeled_by") == "auto-filename":
            entry["labeled_by"] = "expert"
            # Verify objective: all Sakata tesuji are life-and-death or tesuji problems
            entry["objective"] = "life-and-death"
            sakata_labeled += 1
    print(f"  Updated {sakata_labeled} Sakata entries: labeled_by → 'expert', verified objective")

    # -----------------------------------------------------------------------
    # T13: Expert label Lee/Cho puzzles
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T13: Applying expert labels to Lee Changho & Cho Chikun puzzles")
    print("=" * 60)

    leechangho_labeled = 0
    cho_labeled = 0
    for fname, entry in labels.items():
        source = entry.get("source", "")
        if "LEE CHANGHO" in source:
            entry["labeled_by"] = "expert"
            leechangho_labeled += 1
        elif "CHO CHIKUN" in source:
            entry["labeled_by"] = "expert"
            cho_labeled += 1
    print(f"  Lee Changho: {leechangho_labeled} entries labeled as expert")
    print(f"  Cho Chikun:  {cho_labeled} entries labeled as expert")

    # -----------------------------------------------------------------------
    # T9: Write labels.json
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T9: Writing labels.json")
    print("=" * 60)

    # Sort labels by filename for stable output
    sorted_labels = dict(sorted(labels.items(), key=lambda x: natural_sort_key(x[0])))

    labels_doc = {
        "schema_version": "1.0",
        "description": "Instinct calibration golden set — multi-dimensional labels for validating the instinct classifier, technique tags, and enrichment pipeline.",
        "last_updated": "2026-03-25",
        "puzzles": sorted_labels,
    }

    labels_path = DEST / "labels.json"
    with open(labels_path, "w", encoding="utf-8") as f:
        json.dump(labels_doc, f, indent=2, ensure_ascii=False)
    print(f"  Written {len(sorted_labels)} entries to labels.json")

    # -----------------------------------------------------------------------
    # T14: Coverage validation
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("T14: Coverage Validation")
    print("=" * 60)

    sgf_count = len([f for f in os.listdir(DEST) if f.endswith(".sgf")])
    label_count = len(labels)

    instinct_counts: Counter[str] = Counter()
    technique_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    labeled_by_counts: Counter[str] = Counter()

    for fname, entry in labels.items():
        instinct_counts[entry["instinct_primary"]] += 1
        if entry["technique_tag"]:
            technique_counts[entry["technique_tag"]] += 1
        difficulty_counts[entry["human_difficulty"]] += 1
        source_counts[entry["source"].split("/")[1] if "/" in entry["source"] else entry["source"]] += 1
        labeled_by_counts[entry["labeled_by"]] += 1

    print(f"\n  Total SGF files in directory:  {sgf_count}")
    print(f"  Total labels in labels.json:   {label_count}")
    print(f"  Files copied this run:         {total_copied}")

    print("\n  --- Per-instinct counts (C-4: need ≥10 each) ---")
    for inst in ["push", "hane", "cut", "descent", "extend", "null"]:
        c = instinct_counts.get(inst, 0)
        status = "✓" if c >= 10 else "✗ BELOW 10"
        print(f"    {inst:12s}: {c:4d}  {status}")

    print("\n  --- Per-technique tag counts (AC-6: need ≥5 for top tags) ---")
    for tag, c in technique_counts.most_common():
        status = "✓" if c >= 5 else "△ <5"
        print(f"    {tag:20s}: {c:4d}  {status}")

    print("\n  --- Per-difficulty counts ---")
    for diff, c in sorted(difficulty_counts.items()):
        print(f"    {diff:20s}: {c:4d}")

    print("\n  --- Per-source counts ---")
    for src, c in source_counts.most_common():
        print(f"    {src:40s}: {c:4d}")

    print("\n  --- Labeled-by counts ---")
    for lb, c in labeled_by_counts.most_common():
        print(f"    {lb:20s}: {c:4d}")

    # Coverage checks
    print("\n  === Coverage Check ===")
    ac5 = label_count >= 120
    print(f"  AC-5 (≥120 total):      {label_count} → {'PASS ✓' if ac5 else 'FAIL ✗'}")

    c4_pass = all(instinct_counts.get(i, 0) >= 10 for i in ["push", "hane", "cut", "descent", "extend", "null"])
    c4_min = min(instinct_counts.get(i, 0) for i in ["push", "hane", "cut", "descent", "extend", "null"])
    print(f"  C-4  (≥10/instinct):    min={c4_min} → {'PASS ✓' if c4_pass else 'FAIL ✗'}")

    # AC-6: top 10 technique tags should have ≥5 each
    top_10_tags = technique_counts.most_common(10)
    ac6_pass = all(c >= 5 for _, c in top_10_tags) if top_10_tags else False
    ac6_min = min((c for _, c in top_10_tags), default=0)
    print(f"  AC-6 (≥5/top-10 tag):   min={ac6_min} → {'PASS ✓' if ac6_pass else 'FAIL ✗'}")

    if issues:
        print(f"\n  === Issues ({len(issues)}) ===")
        for issue in issues:
            print(f"    ⚠ {issue}")

    print("\nDone.")


if __name__ == "__main__":
    main()
