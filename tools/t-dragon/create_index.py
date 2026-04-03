#!/usr/bin/env python3
"""
Create an index of all SGF files in tsumegodragon external sources.

This utility scans all batch directories under external-sources/tsumegodragon/sgf/
and creates an index file listing all SGF filenames.

Usage:
    python -m tools.t-dragon.create_index
    # or from tools/t-dragon directory:
    python create_index.py

Output:
    external-sources/tsumegodragon/sgf-index.txt
"""

from pathlib import Path


def get_project_root() -> Path:
    """Get project root directory (yen-go)."""
    # This file is at: tools/t-dragon/create_index.py
    # Project root is: ../../
    return Path(__file__).resolve().parent.parent.parent


def create_sgf_index(
    sgf_dir: Path | None = None,
    output_file: Path | None = None,
) -> tuple[int, int, Path]:
    """
    Create an index of all SGF files across all batch directories.

    Args:
        sgf_dir: Directory containing batch subdirectories.
                 Defaults to external-sources/tsumegodragon/sgf/
        output_file: Path for the output index file.
                     Defaults to external-sources/tsumegodragon/sgf-index.txt

    Returns:
        Tuple of (batch_count, file_count, output_path)
    """
    project_root = get_project_root()

    if sgf_dir is None:
        sgf_dir = project_root / "external-sources" / "tsumegodragon" / "sgf"

    if output_file is None:
        output_file = project_root / "external-sources" / "tsumegodragon" / "sgf-index.txt"

    if not sgf_dir.exists():
        raise FileNotFoundError(f"SGF directory not found: {sgf_dir}")

    # Collect all batch directories (sorted)
    batch_dirs = sorted(
        [d for d in sgf_dir.iterdir() if d.is_dir() and d.name.startswith("batch-")]
    )

    if not batch_dirs:
        raise ValueError(f"No batch directories found in: {sgf_dir}")

    # Build the index
    lines: list[str] = []
    lines.append("# TsumeGo Dragon SGF Index")
    lines.append(f"# Generated from: {sgf_dir.relative_to(project_root)}")
    lines.append(f"# Total batches: {len(batch_dirs)}")
    lines.append("")

    total_files = 0

    for batch_dir in batch_dirs:
        # Get all .sgf files in this batch (sorted by name)
        sgf_files = sorted(batch_dir.glob("*.sgf"))
        batch_count = len(sgf_files)
        total_files += batch_count

        lines.append(f"## {batch_dir.name} ({batch_count} files)")
        for sgf_file in sgf_files:
            # Store filename only (without .sgf extension for compactness)
            lines.append(sgf_file.stem)
        lines.append("")

    # Update header with total count
    lines[2] = f"# Total batches: {len(batch_dirs)}"
    lines.insert(3, f"# Total files: {total_files}")

    # Write index file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("\n".join(lines), encoding="utf-8")

    return len(batch_dirs), total_files, output_file


def main() -> None:
    """Main entry point."""
    print("Creating SGF index for tsumegodragon...")

    try:
        batch_count, file_count, output_path = create_sgf_index()
        print(f"✓ Indexed {file_count} files across {batch_count} batches")
        print(f"✓ Output: {output_path}")
    except (FileNotFoundError, ValueError) as e:
        print(f"✗ Error: {e}")
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
