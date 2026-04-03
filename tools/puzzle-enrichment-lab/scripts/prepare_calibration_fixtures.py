"""Prepare calibration & scale test fixtures by copying from external-sources.

This script copies a CURATED SUBSET of SGFs from external-sources/kisvadim-goproblems
into local fixture directories under tests/fixtures/. Tests MUST NEVER reference
external-sources directly — all test inputs come from these local copies.

Usage:
    python scripts/prepare_calibration_fixtures.py                  # Copy all
    python scripts/prepare_calibration_fixtures.py --calibration    # Calibration only (90 SGFs)
    python scripts/prepare_calibration_fixtures.py --scale          # Scale tests only
    python scripts/prepare_calibration_fixtures.py --check          # Verify fixtures exist

Fixture layout after running:
    tests/fixtures/
    ├── perf-33/                          # (existing) 33 smoke test SGFs
    ├── calibration/
    │   ├── cho-elementary/               # 30 SGFs (seed=42 sample)
    │   ├── cho-intermediate/             # 30 SGFs (seed=42 sample)
    │   └── cho-advanced/                 # 30 SGFs (seed=42 sample)
    └── scale/
        ├── scale-100/                    # 100 SGFs (elementary, first 100)
        ├── scale-1k/                     # 1,000 SGFs (400+300+300 mixed)
        └── scale-10k/                    # Up to 10,000 SGFs (all collections)

Reproducibility: Calibration fixtures use seed=42 with sorted file lists,
so the same 30 SGFs are selected every time.
"""

import argparse
import random
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LAB_DIR = SCRIPT_DIR.parent
WORKSPACE_ROOT = LAB_DIR.parent.parent  # tools/puzzle-enrichment-lab → tools → yen-go
FIXTURES_DIR = LAB_DIR / "tests" / "fixtures"

KISVADIM_ROOT = WORKSPACE_ROOT / "external-sources" / "kisvadim-goproblems"

# ── Cho Chikun collections for calibration ──
CHO_COLLECTIONS = {
    "cho-elementary": "CHO CHIKUN Encyclopedia Life And Death - Elementary",
    "cho-intermediate": "CHO CHIKUN Encyclopedia Life And Death - Intermediate",
    "cho-advanced": "CHO CHIKUN Encyclopedia Life And Death - Advanced",
}

# ── Scale test configuration ──
SCALE_100_SOURCE = "CHO CHIKUN Encyclopedia Life And Death - Elementary"
SCALE_100_COUNT = 100

SCALE_1K_SOURCES = [
    ("CHO CHIKUN Encyclopedia Life And Death - Elementary", 400),
    ("CHO CHIKUN Encyclopedia Life And Death - Intermediate", 300),
    ("CHO CHIKUN Encyclopedia Life And Death - Advanced", 300),
]

CALIBRATION_SAMPLE_SIZE = 30
CALIBRATION_SEED = 42

# ── Evaluation population (S.4 — disjoint from calibration) ──
EVALUATION_SEED = 99
EVALUATION_SAMPLE_SIZE = 10  # per collection, 10×3 = 30 total
# Evaluation uses the SAME Cho collections but different puzzles (different seed,
# excluding calibration filenames). This ensures evaluation measures accuracy on
# unseen puzzles from the same distribution.
EVALUATION_COLLECTIONS = CHO_COLLECTIONS  # same collections, different sample

# Collections to include in 10K scale test (all with >0 SGFs)
SCALE_10K_COLLECTIONS = [
    "CHO CHIKUN Encyclopedia Life And Death - Elementary",
    "CHO CHIKUN Encyclopedia Life And Death - Intermediate",
    "CHO CHIKUN Encyclopedia Life And Death - Advanced",
    "CHO CHIKUN Encyclopedia Life And Death - Others",
    "GO SEIGEN - SEGOE TESUJI DICTIONARY",
    "GO SEIGEN Evil Moves Tsumego",
    "GO SEIGEN Striving Constantly For Self-Improvement",
    "GO SEIGEN Tsumego Collection - The Long-Lived Stone Is Not Old",
    "GO SEIGEN Tsumego Collection 1 - Shokyuu",
    "GO SEIGEN Tsumego Collection 2 - Jokyuu",
    "GO SEIGEN TSUMEGO DOJO VOL 1",
    "GO SEIGEN TSUMEGO DOJO VOL 2",
    "Hashimoto Utaro - 1 Year Tsumego",
    "Hashimoto Utaro - Fifty Three To Go",
    "Hashimoto Utaro - Nakasendo, Enjoy Tsumego and Get Stronger",
    "Hashimoto Utaro 179 Skillful Life and Death",
    "Hashimoto Utaro Famous Creations Three Hundred Selections",
    "Hashimoto Utaro The Moments of the Wind VOL.1",
    "Hashimoto Utaro The Moments of the Wind VOL.2",
    "Hashimoto Utaro The Moments of the Wind VOL.3",
    "Hashimoto Utaro Tsumego for the Millions vol.2",
    "Ishigure Ikuro 123 BASIC TSUMEGO",
    "KADA KATSUJI Tsumego Class",
    "KAKU KYUSHIN 200 TSUMEGO PROBLEM",
    "Kano Yoshinori - 239 Graded Go Problems",
    "KOBAYASHI SATORU 105 BASIC TESUJI FOR 1~3 DAN",
    "MAEDA NOBUAKI Delightful Tsumego (selected 160 from God of Tsumego)",
    "MAEDA NOBUAKI Newly Selected Tsumego 100 Problems (Continued) for 1-8k",
    "MAEDA NOBUAKI Newly Selected Tsumego 100 Problems for 1-8k",
    "MAEDA NOBUAKI The God of Tsumego VOL1",
    "MAEDA NOBUAKI The God of Tsumego VOL2",
    "MAEDA TSUMEGO - Tsumego for the Millions 100 VOL 1",
    "MAEDA TSUMEGO Collection - CHUKYU",
    "MAEDA TSUMEGO Collection - JOKYU",
    "MAEDA TSUMEGO Collection - SHOKYU",
    "MAEDA TSUMEGO Tsumego Masterpieces",
    "MAKING SHAPE TESUJI",
    "SAKATA EIO TESUJI",
    "SATO SUNAO - FLEXIBLE TSUMEGO",
    "SATO SUNAO - REFRESHING TSUMEGO",
    "TESUJI GREAT DICTIONARY",
    "TSUMEGO CLASSIC - GENRAN",
    "TSUMEGO CLASSIC - GOKYO SHUMYO",
    "TSUMEGO CLASSIC - XUAN XUAN QI JING",
]

SCALE_10K_TARGET = 10_000


def _sample_sgfs(collection_dir: Path, n: int, seed: int) -> list[Path]:
    """Deterministically sample n SGFs from a directory."""
    all_sgfs = sorted(collection_dir.glob("*.sgf"))
    if len(all_sgfs) <= n:
        return all_sgfs
    rng = random.Random(seed)
    return sorted(rng.sample(all_sgfs, n))


def _sample_sgfs_excluding(
    collection_dir: Path,
    n: int,
    seed: int,
    exclude_names: set[str],
) -> list[Path]:
    """Deterministically sample n SGFs, excluding specific filenames."""
    all_sgfs = sorted(collection_dir.glob("*.sgf"))
    available = [p for p in all_sgfs if p.name not in exclude_names]
    if len(available) <= n:
        return available
    rng = random.Random(seed)
    return sorted(rng.sample(available, n))
    if len(all_sgfs) <= n:
        return all_sgfs
    rng = random.Random(seed)
    return sorted(rng.sample(all_sgfs, n))


def _copy_sgfs(sgf_paths: list[Path], dest_dir: Path, prefix: str = "") -> int:
    """Copy SGF files to destination. Returns count copied."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for sgf in sgf_paths:
        dest_name = f"{prefix}{sgf.name}" if prefix else sgf.name
        dest = dest_dir / dest_name
        if not dest.exists():
            shutil.copy2(sgf, dest)
        count += 1
    return count


def prepare_calibration() -> int:
    """Copy 30 SGFs per Cho Chikun collection for P.1.3 calibration."""
    total = 0
    for fixture_name, coll_name in CHO_COLLECTIONS.items():
        source_dir = KISVADIM_ROOT / coll_name
        if not source_dir.exists():
            print(f"  SKIP: {coll_name} (not found)")
            continue

        dest_dir = FIXTURES_DIR / "calibration" / fixture_name
        sampled = _sample_sgfs(source_dir, CALIBRATION_SAMPLE_SIZE, CALIBRATION_SEED)
        count = _copy_sgfs(sampled, dest_dir)
        total += count
        print(f"  {fixture_name}: {count} SGFs → {dest_dir.relative_to(LAB_DIR)}")

    return total


def prepare_evaluation() -> int:
    """Copy 10 SGFs per Cho Chikun collection for S.4 evaluation population.

    Uses a different seed (99) and EXCLUDES all calibration filenames to ensure
    the two populations are completely disjoint. This guarantees that accuracy
    measurements on evaluation fixtures are unbiased by threshold tuning.
    """
    # First, collect ALL calibration filenames to exclude
    calibration_names: set[str] = set()
    for fixture_name in CHO_COLLECTIONS:
        cal_dir = FIXTURES_DIR / "calibration" / fixture_name
        if cal_dir.exists():
            calibration_names.update(p.name for p in cal_dir.glob("*.sgf"))

    total = 0
    for fixture_name, coll_name in EVALUATION_COLLECTIONS.items():
        source_dir = KISVADIM_ROOT / coll_name
        if not source_dir.exists():
            print(f"  SKIP: {coll_name} (not found)")
            continue

        dest_dir = FIXTURES_DIR / "evaluation" / fixture_name
        sampled = _sample_sgfs_excluding(
            source_dir, EVALUATION_SAMPLE_SIZE, EVALUATION_SEED, calibration_names
        )
        count = _copy_sgfs(sampled, dest_dir)
        total += count
        print(f"  {fixture_name}: {count} SGFs → {dest_dir.relative_to(LAB_DIR)}")

    return total


def prepare_scale_100() -> int:
    """Copy 100 SGFs for P.3 scale test."""
    source_dir = KISVADIM_ROOT / SCALE_100_SOURCE
    if not source_dir.exists():
        print(f"  SKIP: {SCALE_100_SOURCE} (not found)")
        return 0

    dest_dir = FIXTURES_DIR / "scale" / "scale-100"
    sgfs = sorted(source_dir.glob("*.sgf"))[:SCALE_100_COUNT]
    count = _copy_sgfs(sgfs, dest_dir)
    print(f"  scale-100: {count} SGFs → {dest_dir.relative_to(LAB_DIR)}")
    return count


def prepare_scale_1k() -> int:
    """Copy 1,000 SGFs for P.4 scale test."""
    dest_dir = FIXTURES_DIR / "scale" / "scale-1k"
    total = 0

    for coll_name, count in SCALE_1K_SOURCES:
        source_dir = KISVADIM_ROOT / coll_name
        if not source_dir.exists():
            print(f"  SKIP: {coll_name} (not found)")
            continue

        prefix = coll_name.split(" - ")[-1][:3].lower() + "_"
        sgfs = sorted(source_dir.glob("*.sgf"))[:count]
        copied = _copy_sgfs(sgfs, dest_dir, prefix=prefix)
        total += copied
        print(f"  {coll_name}: {copied} SGFs")

    print(f"  scale-1k total: {total} SGFs → {dest_dir.relative_to(LAB_DIR)}")
    return total


def prepare_scale_10k() -> int:
    """Copy up to 10,000 SGFs for P.5 scale test."""
    dest_dir = FIXTURES_DIR / "scale" / "scale-10k"
    total = 0

    for coll_name in SCALE_10K_COLLECTIONS:
        if total >= SCALE_10K_TARGET:
            break
        source_dir = KISVADIM_ROOT / coll_name
        if not source_dir.exists():
            continue

        prefix = coll_name[:20].replace(" ", "_").lower() + "__"
        sgfs = sorted(source_dir.glob("*.sgf"))
        remaining = SCALE_10K_TARGET - total
        sgfs = sgfs[:remaining]
        copied = _copy_sgfs(sgfs, dest_dir, prefix=prefix)
        total += copied

    print(f"  scale-10k: {total} SGFs → {dest_dir.relative_to(LAB_DIR)}")
    return total


def check_fixtures() -> bool:
    """Verify all fixture directories exist and have expected counts."""
    ok = True

    checks = [
        ("calibration/cho-elementary", CALIBRATION_SAMPLE_SIZE),
        ("calibration/cho-intermediate", CALIBRATION_SAMPLE_SIZE),
        ("calibration/cho-advanced", CALIBRATION_SAMPLE_SIZE),
        ("evaluation/cho-elementary", EVALUATION_SAMPLE_SIZE),
        ("evaluation/cho-intermediate", EVALUATION_SAMPLE_SIZE),
        ("evaluation/cho-advanced", EVALUATION_SAMPLE_SIZE),
        ("scale/scale-100", SCALE_100_COUNT),
        ("scale/scale-1k", 900),  # at least 900 of 1000
        ("scale/scale-10k", 2500),  # at least 2500
    ]

    for subdir, min_count in checks:
        d = FIXTURES_DIR / subdir
        if not d.exists():
            print(f"  MISSING: {subdir}")
            ok = False
            continue

        count = len(list(d.glob("*.sgf")))
        status = "OK" if count >= min_count else "LOW"
        if count < min_count:
            ok = False
        print(f"  {subdir}: {count} SGFs (need ≥{min_count}) [{status}]")

    return ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare calibration & scale test fixtures"
    )
    parser.add_argument("--calibration", action="store_true",
                       help="Copy calibration fixtures only (90 SGFs)")
    parser.add_argument("--evaluation", action="store_true",
                       help="Copy evaluation fixtures only (30 SGFs, disjoint from calibration)")
    parser.add_argument("--scale", action="store_true",
                       help="Copy scale test fixtures only")
    parser.add_argument("--check", action="store_true",
                       help="Verify fixtures exist (no copy)")
    args = parser.parse_args()

    if not KISVADIM_ROOT.exists() and not args.check:
        print(f"ERROR: kisvadim-goproblems not found at {KISVADIM_ROOT}")
        print("Run from workspace root with external-sources available.")
        return 1

    if args.check:
        print("\nFixture Status:")
        ok = check_fixtures()
        return 0 if ok else 1

    do_all = not args.calibration and not args.scale and not args.evaluation

    total = 0
    if do_all or args.calibration:
        print("\n── Calibration fixtures ──")
        total += prepare_calibration()

    if do_all or args.evaluation:
        print("\n── Evaluation fixtures (S.4) ──")
        total += prepare_evaluation()

    if do_all or args.scale:
        print("\n── Scale-100 fixtures ──")
        total += prepare_scale_100()

        print("\n── Scale-1K fixtures ──")
        total += prepare_scale_1k()

        print("\n── Scale-10K fixtures ──")
        total += prepare_scale_10k()

    print(f"\nTotal: {total} SGF files copied")
    print("\nRun --check to verify:")
    print(f"  python {Path(__file__).name} --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
