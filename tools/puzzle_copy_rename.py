"""Copy and rename SGF files to standardized instinct-calibration naming.

Naming convention: {instinct}_{level}_{serial:03d}.sgf

Usage:
    # Single file
    python tools/puzzle_copy_rename.py \\
      --input "external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/kiri-s-01.sgf" \\
      --target "tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration" \\
      --instinct cut --level intermediate --serial 1

    # Batch with glob
    python tools/puzzle_copy_rename.py \\
      --input "external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/kiri-s-*.sgf" \\
      --target "tools/puzzle-enrichment-lab/tests/fixtures/instinct-calibration" \\
      --instinct cut --level intermediate --serial-start 1

    # Dry run
    python tools/puzzle_copy_rename.py --dry-run \\
      --input "external-sources/kisvadim-goproblems/SAKATA EIO TESUJI/kiri-s-*.sgf" \\
      --target instinct-calibration --instinct cut --level intermediate --serial-start 1
"""

from __future__ import annotations

import argparse
import glob
import shutil
from pathlib import Path

from tools.core.paths import get_project_root

VALID_INSTINCTS: tuple[str, ...] = (
    "push", "hane", "cut", "descent", "extend", "null",
)

VALID_LEVELS: tuple[str, ...] = (
    "novice", "beginner", "elementary", "intermediate",
    "upper-intermediate", "advanced", "low-dan", "high-dan", "expert",
)


def _make_filename(instinct: str, level: str, serial: int) -> str:
    return f"{instinct}_{level}_{serial:03d}.sgf"


def copy_and_rename(
    input_paths: list[Path],
    target_dir: Path,
    instinct: str,
    level: str,
    serial_start: int = 1,
    dry_run: bool = False,
    force: bool = False,
) -> list[tuple[Path, Path]]:
    """Copy and rename SGF files to standardized naming.

    Args:
        input_paths: Source SGF file paths (must exist).
        target_dir: Destination directory (must exist).
        instinct: Instinct type (one of VALID_INSTINCTS).
        level: Difficulty level (one of VALID_LEVELS).
        serial_start: First serial number to assign.
        dry_run: If True, return planned copies without writing.
        force: If True, allow overwriting existing files.

    Returns:
        List of (source, destination) tuples.

    Raises:
        ValueError: If instinct or level is invalid.
        FileNotFoundError: If target_dir or a source file doesn't exist.
        FileExistsError: If destination exists and force is False.
    """
    if instinct not in VALID_INSTINCTS:
        raise ValueError(
            f"Invalid instinct '{instinct}'. Must be one of: {', '.join(VALID_INSTINCTS)}"
        )
    if level not in VALID_LEVELS:
        raise ValueError(
            f"Invalid level '{level}'. Must be one of: {', '.join(VALID_LEVELS)}"
        )
    if not target_dir.is_dir():
        raise FileNotFoundError(f"Target directory does not exist: {target_dir}")

    # Sort alphabetically for deterministic serial assignment
    sorted_paths = sorted(input_paths, key=lambda p: p.name)

    results: list[tuple[Path, Path]] = []
    serial = serial_start

    for src in sorted_paths:
        if not src.is_file():
            raise FileNotFoundError(f"Source file does not exist: {src}")
        dest = target_dir / _make_filename(instinct, level, serial)
        if not force and not dry_run and dest.exists():
            raise FileExistsError(
                f"Destination already exists (use --force to overwrite): {dest}"
            )
        if not dry_run:
            shutil.copy2(src, dest)
        results.append((src, dest))
        serial += 1

    return results


def _resolve_input(raw: str) -> list[Path]:
    """Resolve input argument to a list of existing file paths."""
    root = get_project_root()

    raw_path = Path(raw)
    if not raw_path.is_absolute():
        raw_path = root / raw

    # Use glob to expand wildcards
    matches = sorted(glob.glob(str(raw_path)))
    if not matches:
        raise FileNotFoundError(f"No files matched: {raw}")

    return [Path(m) for m in matches]


def _resolve_target(raw: str) -> Path:
    """Resolve target directory to an absolute path."""
    target = Path(raw)
    if not target.is_absolute():
        target = get_project_root() / target
    return target


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy and rename SGF files to standardized naming.",
    )
    parser.add_argument(
        "--input", required=True,
        help="Source SGF path (supports glob patterns). Relative to project root.",
    )
    parser.add_argument(
        "--target", required=True,
        help="Target directory. Relative to project root.",
    )
    parser.add_argument(
        "--instinct", required=True, choices=VALID_INSTINCTS,
        help="Instinct type.",
    )
    parser.add_argument(
        "--level", required=True, choices=VALID_LEVELS,
        help="Difficulty level.",
    )
    parser.add_argument(
        "--serial", type=int, default=None,
        help="Serial number for single-file copy (default: 1).",
    )
    parser.add_argument(
        "--serial-start", type=int, default=None,
        help="Starting serial number for batch copy (increments per file).",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Allow overwriting existing files.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview actions without writing any files.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_paths = _resolve_input(args.input)
    target_dir = _resolve_target(args.target)

    # Determine serial start
    if args.serial is not None and args.serial_start is not None:
        parser.error("Cannot specify both --serial and --serial-start.")
    serial_start = args.serial or args.serial_start or 1

    results = copy_and_rename(
        input_paths=input_paths,
        target_dir=target_dir,
        instinct=args.instinct,
        level=args.level,
        serial_start=serial_start,
        dry_run=args.dry_run,
        force=args.force,
    )

    action = "Would copy" if args.dry_run else "Copied"
    for src, dest in results:
        print(f"{action}: {src.name} -> {dest.name}")

    print(f"\n{len(results)} file(s) {'planned' if args.dry_run else 'copied'}.")


if __name__ == "__main__":
    main()
