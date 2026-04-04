"""Prepare external-source SGF files: re-encode to UTF-8 and clean properties.

Uses the established parse_sgf → SGFBuilder.from_tree → build() round-trip
pattern (same as tools/tsumego_hero/storage.py:rebuild_sgf).

The parser's metadata whitelist automatically drops EV[]. We additionally
remove AP[] and GN[] from builder.metadata. The builder outputs clean
FF[4]GM[1]CA[UTF-8] SGF.

Does NOT import from backend/ (architecture boundary).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.core.atomic_write import atomic_write_text
from tools.core.sgf_builder import SGFBuilder
from tools.core.sgf_parser import SGFParseError, parse_sgf

logger = logging.getLogger("kisvadim.prepare")

# Detect CA[] encoding in raw bytes
_RE_CA_BYTES = re.compile(rb"CA\[([^\]]+)\]")


@dataclass
class PrepareStats:
    """Aggregate statistics for a prepare run."""

    total: int = 0
    converted: int = 0
    already_utf8: int = 0
    skipped: int = 0
    errors: int = 0
    error_files: list[str] = field(default_factory=list)


def _decode_sgf_bytes(raw: bytes) -> tuple[str, str]:
    """Decode raw SGF bytes, detecting encoding from CA[] property.

    Returns (decoded_text, detected_encoding).
    """
    ca_match = _RE_CA_BYTES.search(raw)
    if ca_match:
        encoding = ca_match.group(1).decode("ascii", errors="replace").strip().lower()
        if encoding in ("gb2312", "gbk", "gb18030"):
            # GBK is a superset of GB2312, try it first for better coverage
            for enc in ("gbk", "gb2312"):
                try:
                    return raw.decode(enc), encoding
                except UnicodeDecodeError:
                    continue
            return raw.decode("gbk", errors="replace"), encoding
        if encoding in ("utf-8", "utf8"):
            return raw.decode("utf-8", errors="replace"), "utf-8"

    # No CA[] or unknown encoding: try UTF-8, fallback to GBK
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("gbk", errors="replace"), "gbk-fallback"


def _rebuild_clean(sgf_text: str) -> str:
    """Parse SGF and rebuild with clean properties.

    The parser's metadata whitelist (sgf_parser.py:528) captures only:
    GN, GC, PB, PW, DT, RE, SO, AP, MN — EV is automatically dropped.

    We additionally remove AP and GN from builder.metadata.
    The builder outputs FF[4]GM[1] with proper formatting.
    """
    tree = parse_sgf(sgf_text)
    builder = SGFBuilder.from_tree(tree)

    # Remove unwanted metadata properties
    builder.metadata.pop("AP", None)
    builder.metadata.pop("GN", None)

    return builder.build()


def prepare_sgf_files(
    source_dir: Path,
    *,
    dry_run: bool = False,
) -> PrepareStats:
    """Re-encode and clean all SGF files under source_dir.

    For each .sgf file:
    1. Read raw bytes, detect encoding from CA[]
    2. Decode to Python str (GB2312/GBK → Unicode)
    3. Round-trip through parse_sgf → SGFBuilder → build() to clean properties
    4. Write back as UTF-8

    Args:
        source_dir: Directory containing SGF files (searched recursively).
        dry_run: Report changes without writing.

    Returns:
        PrepareStats with counts.
    """
    stats = PrepareStats()

    sgf_files = sorted(source_dir.rglob("*.sgf"))
    if not sgf_files:
        logger.warning("No SGF files found in %s", source_dir)
        return stats

    logger.info(
        "Preparing %d SGF files in %s (dry_run=%s)",
        len(sgf_files), source_dir, dry_run,
    )

    for sgf_path in sgf_files:
        stats.total += 1
        rel = sgf_path.relative_to(source_dir)

        try:
            raw = sgf_path.read_bytes()
            decoded, detected_enc = _decode_sgf_bytes(raw)

            # Round-trip through parser/builder to clean properties
            cleaned = _rebuild_clean(decoded)

            if dry_run:
                logger.info("[DRY-RUN] Would prepare %s (enc=%s)", rel, detected_enc)
                stats.converted += 1
                continue

            atomic_write_text(sgf_path, cleaned)
            stats.converted += 1
            logger.debug("Prepared %s (enc=%s)", rel, detected_enc)

        except SGFParseError as exc:
            logger.error("Parse error in %s: %s", rel, exc)
            stats.errors += 1
            stats.error_files.append(str(rel))
        except Exception as exc:
            logger.error("Error preparing %s: %s", rel, exc)
            stats.errors += 1
            stats.error_files.append(str(rel))

    logger.info(
        "Prepare complete: total=%d converted=%d errors=%d",
        stats.total, stats.converted, stats.errors,
    )
    return stats
