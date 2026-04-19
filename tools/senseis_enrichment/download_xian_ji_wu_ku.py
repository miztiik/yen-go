"""Download, clean, and prepare Xian Ji Wu Ku Leather Scroll SGFs.

Complete pipeline:
  1. Download SGF diagrams from Sensei's Library (with checkpoint/resume)
  2. Clean SGF content (strip \\r, remove noise properties, clean comments)
  3. Save with section-based naming + YL tags (LooseCorner-001.sgf, etc.)
  4. Create sequential copies (0001.sgf..0148.sgf) for enrichment tool

After this script completes, run the enrichment tool:
    python -m tools.senseis_enrichment --config tools/senseis_enrichment/xian_ji_wu_ku_config.json

Then rename enriched output to section-based names:
    python -m tools.senseis_enrichment.rename_to_sections --config tools/senseis_enrichment/xian_ji_wu_ku_config.json

Usage:
    python tools/senseis_enrichment/download_xian_ji_wu_ku.py [--dry-run] [--clean-only]
"""

import json
import re
import time
import random
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://senseis.xmp.net"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
RATE_LIMIT = 3.0
RATE_JITTER = 1.0
COLLECTION_SLUG = "xian-ji-wu-ku"

# Section definitions: (section_number, prefix, global_start, global_end)
SECTIONS = [
    (1, "LooseCorner", 1, 49),
    (2, "InnerCorner", 50, 61),
    (3, "LongLivingCorner", 62, 65),
    (4, "ClusteredCorner", 66, 80),
    (5, "SolidRodCorner", 81, 84),
    (6, "DiagonalCorner", 85, 88),
    (7, "ConnectedString", 89, 97),
    (8, "TwoHouses", 98, 108),
    (9, "EntangledCorner", 109, 115),
    (10, "HighRisingSide", 116, 122),
    (11, "HighRisingCorner", 123, 124),
    (12, "SharpFoldCorner", 125, 125),
    (13, "CornerToSideConnection", 126, 129),
    (14, "LayeredCorner", 130, 141),
    (15, "LShapeCorner", 142, 146),
    (16, "TightCorner", 147, 147),
    (17, "OrderlyCorner", 148, 148),
]

OUTPUT_DIR = Path("external-sources/authors/TSUMEGO CLASSIC - Xian Ji Wu Ku")
CHECKPOINT_FILE = OUTPUT_DIR / ".download_checkpoint.json"

# SGF properties to remove (noise from Senseis diagrams)
_NOISE_PROPS = re.compile(
    r"(?:PC|AP|DT)\[[^\]]*\]"
)
# Carriage returns
_CR = re.compile(r"\r")
# Multiple consecutive newlines (3+ -> 1)
_MULTI_NEWLINE = re.compile(r"\n{3,}")
# Empty trailing node: just a semicolon before closing paren
_EMPTY_TRAILING_NODE = re.compile(r";\s*\)")
# GN property (replace with proper one)
_GN_PROP = re.compile(r"GN\[[^\]]*\]")
# URL in comments
_URL_IN_COMMENT = re.compile(r"https?://\S+")


def get_section_info(global_num: int) -> tuple[int, str, int]:
    """Return (section_number, filename_prefix, position_within_section)."""
    for sec_num, prefix, start, end in SECTIONS:
        if start <= global_num <= end:
            pos = global_num - start + 1
            return sec_num, prefix, pos
    raise ValueError(f"Problem {global_num} not in any section")


def section_filename(global_num: int) -> str:
    """Get section-based filename for a global problem number."""
    _, prefix, pos = get_section_info(global_num)
    return f"{prefix}-{pos:02d}.sgf"


def fetch_url(url: str) -> str:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_sgf_url(html: str) -> str | None:
    """Extract the first SGF diagram URL from a Senseis problem page."""
    match = re.search(r'href="(diagrams/[^"]+\.sgf)"', html)
    if match:
        return f"{BASE_URL}/{match.group(1)}"
    return None


def extract_instruction(html: str) -> str:
    """Extract the move instruction (e.g. 'White to move') from a problem page."""
    # Look in the diagram form: "White to move" or "Black to move"
    match = re.search(r'(?:White|Black)\s+to\s+(?:move|play)[^<]*', html, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""


def clean_sgf(sgf: str, problem_num: int, section_num: int, position: int) -> str:
    """Clean raw Senseis SGF content.

    Removes:
      - Carriage returns (\\r)
      - PC[], AP[], DT[] noise properties
      - URLs in C[] comments
      - 'Diagram from ...' boilerplate in comments
      - GN[] (replaced with problem reference)
      - Empty trailing nodes (bare ; before ))
      - Excessive blank lines
    Adds:
      - YL[xian-ji-wu-ku:section/position]
    """
    # Strip carriage returns
    sgf = _CR.sub("", sgf)

    # Remove noise properties
    sgf = _NOISE_PROPS.sub("", sgf)

    # Clean GN[] - replace with Leather Scroll problem reference
    sgf = _GN_PROP.sub(f"GN[Leather Scroll Problem {problem_num}]", sgf)

    # Clean comments: strip URLs and 'Diagram from' boilerplate
    def _clean_comment(m: re.Match) -> str:
        content = m.group(1)
        # Remove URLs
        content = _URL_IN_COMMENT.sub("", content)
        # Remove "Diagram from" boilerplate line
        content = re.sub(r"Diagram from\s*", "", content)
        # Collapse multiple newlines within comment
        content = re.sub(r"\n{2,}", "\n", content)
        # Strip leading/trailing whitespace
        content = content.strip()
        if not content:
            return ""
        return f"C[{content}]"

    sgf = re.sub(r"C\[([^\]]*)\]", _clean_comment, sgf)

    # Remove empty trailing node
    sgf = _EMPTY_TRAILING_NODE.sub(")", sgf)

    # Collapse excessive blank lines
    sgf = _MULTI_NEWLINE.sub("\n", sgf)

    # Strip trailing whitespace on each line
    sgf = "\n".join(line.rstrip() for line in sgf.split("\n"))

    # Inject YL tag after opening (;
    yl_tag = f"YL[{COLLECTION_SLUG}:{section_num}/{position}]"
    if sgf.startswith("(;"):
        sgf = f"(;{yl_tag}" + sgf[2:]

    # Final strip
    sgf = sgf.strip() + "\n"

    return sgf


def load_checkpoint() -> set[int]:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return set(data.get("completed", []))
    return set()


def save_checkpoint(completed: set[int]) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"completed": sorted(completed)}, indent=2),
        encoding="utf-8",
    )


def download_and_clean(n: int, dry_run: bool = False) -> bool:
    """Download problem N, clean, save with section-based naming. Returns True on success."""
    sec_num, prefix, pos = get_section_info(n)
    filename = f"{prefix}-{pos:02d}.sgf"
    filepath = OUTPUT_DIR / filename

    problem_url = f"{BASE_URL}/?LeatherScrollProblem{n}"
    print(f"  [{n:3d}/148] {filename} <- {problem_url}")

    if dry_run:
        return True

    try:
        html = fetch_url(problem_url)
    except (HTTPError, URLError) as e:
        print(f"    ERROR fetching page: {e}")
        return False

    sgf_url = extract_sgf_url(html)
    if not sgf_url:
        print(f"    ERROR: no SGF diagram found on page")
        return False

    try:
        sgf_content = fetch_url(sgf_url)
    except (HTTPError, URLError) as e:
        print(f"    ERROR fetching SGF: {e}")
        return False

    # Clean and save
    sgf_content = clean_sgf(sgf_content, n, sec_num, pos)
    filepath.write_bytes(sgf_content.encode("utf-8"))

    # Also save sequential copy for enrichment tool
    seq_path = OUTPUT_DIR / f"{n:04d}.sgf"
    seq_path.write_bytes(sgf_content.encode("utf-8"))

    return True


def clean_existing_files() -> int:
    """Clean all existing section-named SGFs in-place and create sequential copies."""
    cleaned = 0
    for n in range(1, 149):
        sec_num, prefix, pos = get_section_info(n)
        filename = f"{prefix}-{pos:02d}.sgf"
        filepath = OUTPUT_DIR / filename

        if not filepath.exists():
            print(f"  MISSING: {filename}")
            continue

        sgf = filepath.read_text(encoding="utf-8")
        # Remove old YL tag if present (will be re-injected by clean_sgf)
        sgf = re.sub(r"YL\[[^\]]*\]", "", sgf)
        # If starts with (; after YL removal, re-add it cleanly
        if not sgf.startswith("(;"):
            sgf = "(;" + sgf.lstrip("(;")

        cleaned_sgf = clean_sgf(sgf, n, sec_num, pos)
        filepath.write_bytes(cleaned_sgf.encode("utf-8"))

        # Create sequential copy for enrichment tool
        seq_path = OUTPUT_DIR / f"{n:04d}.sgf"
        seq_path.write_bytes(cleaned_sgf.encode("utf-8"))

        cleaned += 1

    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser(description="Download & clean Xian Ji Wu Ku SGFs")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--clean-only", action="store_true",
                        help="Only clean existing files (no download)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.clean_only:
        print("Cleaning existing files...")
        count = clean_existing_files()
        print(f"Cleaned {count} files, sequential copies created for enrichment tool.")
        return

    completed = load_checkpoint()
    remaining = [n for n in range(1, 149) if n not in completed]

    print(f"Xian Ji Wu Ku Leather Scroll pipeline")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Total: 148, completed: {len(completed)}, remaining: {len(remaining)}")
    print()

    if not remaining:
        print("All 148 problems already downloaded. Running clean-only...")
        count = clean_existing_files()
        print(f"Cleaned {count} files.")
        return

    for i, n in enumerate(remaining):
        if i > 0 and not args.dry_run:
            delay = RATE_LIMIT + random.uniform(0, RATE_JITTER)
            time.sleep(delay)

        ok = download_and_clean(n, dry_run=args.dry_run)
        if ok and not args.dry_run:
            completed.add(n)
            save_checkpoint(completed)

    print()
    print(f"Done. {len(completed)}/148 downloaded + cleaned to {OUTPUT_DIR}")
    print(f"Sequential copies (0001.sgf..0148.sgf) ready for enrichment tool.")


if __name__ == "__main__":
    main()
