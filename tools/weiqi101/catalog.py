"""Books catalog: pure join of mechanical discovery + curatorial reviews.

The output ``books-catalog.jsonl`` is the SINGLE source of truth for the
``/books`` endpoint and any external prioritisation tooling. It is
**derived** — every CLI command that mutates an input MUST end with a
call to :func:`rebuild_books_catalog`.

Inputs
------
- ``book-ids.jsonl``         — per-book chapter+puzzle IDs (mechanical)
- ``discovery-catalog.json`` — site catalog: difficulty, sharer, tags
- ``book-reviews.jsonl``     — curatorial review records (one per book)

Output
------
- ``books-catalog.jsonl``    — joined entries, one JSON line per book
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("101weiqi.catalog")

CATALOG_FILE = "books-catalog.jsonl"
BOOK_IDS_FILE = "book-ids.jsonl"
DISCOVERY_CATALOG_FILE = "discovery-catalog.json"
REVIEWS_FILE = "book-reviews.jsonl"

# Sort ordering for ``/books`` and the catalog file. Lower = better.
# ``unrated`` is a sentinel for books with no review record; it sits
# between tier-3 and skip so unrated books surface above explicitly
# rejected ones.
TIER_VALUES: dict[str, int] = {
    "tier-1": 1,
    "tier-2": 2,
    "tier-3": 3,
    "unrated": 4,
    "skip": 5,
}

# Consensus computation uses only the four explicit tiers — ``unrated``
# is never a reviewer output, only a join-time fallback.
_CONSENSUS_VALUES: dict[str, int] = {"tier-1": 1, "tier-2": 2, "tier-3": 3, "skip": 4}
_CONSENSUS_VALUE_TO_TIER = {v: k for k, v in _CONSENSUS_VALUES.items()}

# Drift threshold: flag review_stale when |delta| / old > this.
PUZZLE_COUNT_DRIFT_THRESHOLD = 0.10


@dataclass(frozen=True)
class ReviewBundle:
    """Curatorial review payload for one book."""

    go_advisor: dict[str, Any] | None
    modern_player: dict[str, Any] | None
    puzzle_count_at_review: int | None


def consensus_tier(go_advisor_tier: str | None, modern_player_tier: str | None) -> str:
    """Average of both reviewers, rounded toward the better (lower) tier.

    Falls back to whichever reviewer rated. Returns ``"unrated"`` when
    neither rated.
    """
    ga = _CONSENSUS_VALUES.get(go_advisor_tier) if go_advisor_tier else None
    mp = _CONSENSUS_VALUES.get(modern_player_tier) if modern_player_tier else None
    if ga is None and mp is None:
        return "unrated"
    if ga is None:
        return _CONSENSUS_VALUE_TO_TIER[mp]  # type: ignore[index]
    if mp is None:
        return _CONSENSUS_VALUE_TO_TIER[ga]
    avg = (ga + mp) / 2
    return _CONSENSUS_VALUE_TO_TIER[max(1, min(4, int(avg)))]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed JSONL line in %s", path.name)
    return out


def load_reviews(output_dir: Path) -> dict[int, ReviewBundle]:
    """Read ``book-reviews.jsonl`` keyed by ``book_id``."""
    bundles: dict[int, ReviewBundle] = {}
    for entry in _read_jsonl(output_dir / REVIEWS_FILE):
        bid = entry.get("book_id")
        if not isinstance(bid, int):
            continue
        reviews = entry.get("reviews") or {}
        bundles[bid] = ReviewBundle(
            go_advisor=reviews.get("go_advisor"),
            modern_player=reviews.get("modern_player"),
            puzzle_count_at_review=entry.get("puzzle_count_at_review"),
        )
    return bundles


def _load_discovery_metadata(output_dir: Path) -> dict[int, dict[str, Any]]:
    """Read ``discovery-catalog.json`` keyed by ``book_id``."""
    path = output_dir / DISCOVERY_CATALOG_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Malformed %s — ignoring", path.name)
        return {}
    out: dict[int, dict[str, Any]] = {}
    for book in data.get("books") or []:
        bid = book.get("book_id")
        if isinstance(bid, int):
            out[bid] = book
    return out


def _book_ids_puzzle_count(entry: dict[str, Any]) -> int:
    chapters = entry.get("chapters")
    if chapters:
        return sum(len(ch.get("puzzle_ids") or []) for ch in chapters)
    return int(entry.get("puzzle_count") or 0)


def _is_stale(current: int, at_review: int | None) -> bool:
    if not at_review:
        return False
    if current == at_review:
        return False
    return abs(current - at_review) / max(at_review, 1) > PUZZLE_COUNT_DRIFT_THRESHOLD


def _build_entry(
    book_ids_entry: dict[str, Any],
    discovery: dict[str, Any] | None,
    review: ReviewBundle | None,
) -> dict[str, Any]:
    bid = int(book_ids_entry["book_id"])
    puzzle_count = _book_ids_puzzle_count(book_ids_entry)

    ga = review.go_advisor if review else None
    mp = review.modern_player if review else None
    consensus = consensus_tier(
        ga.get("tier") if ga else None,
        mp.get("tier") if mp else None,
    )

    chapters = book_ids_entry.get("chapters") or []
    chapter_count = (
        len(chapters)
        if chapters
        else (discovery.get("chapter_count") if discovery else 0) or 0
    )

    entry: dict[str, Any] = {
        "book_id": bid,
        "name": book_ids_entry.get("book_name_en") or book_ids_entry.get("book_name", ""),
        "name_cn": book_ids_entry.get("book_name", ""),
        "puzzle_count": puzzle_count,
        "chapter_count": chapter_count,
        "difficulty": (discovery or {}).get("difficulty", ""),
        "sharer": (discovery or {}).get("sharer", ""),
        "tags": list((discovery or {}).get("tags") or []),
        "consensus_tier": consensus,
        "review_stale": _is_stale(
            puzzle_count, review.puzzle_count_at_review if review else None
        ),
        "go_advisor_tier": ga.get("tier") if ga else None,
        "go_advisor_type": ga.get("type") if ga else None,
        "go_advisor_note": ga.get("note") if ga else None,
        "modern_player_tier": mp.get("tier") if mp else None,
        "modern_player_appeal": mp.get("appeal") if mp else None,
        "modern_player_target": mp.get("target") if mp else None,
        "discovered_at": book_ids_entry.get("discovered_at", ""),
    }
    return entry


def _sort_key(entry: dict[str, Any]) -> tuple[int, str]:
    return (TIER_VALUES.get(entry["consensus_tier"], 99), entry["name"].lower())


def rebuild_books_catalog(output_dir: Path) -> int:
    """Rebuild ``books-catalog.jsonl`` from inputs. Idempotent.

    Returns the number of entries written.
    """
    book_ids_entries = _read_jsonl(output_dir / BOOK_IDS_FILE)
    discovery = _load_discovery_metadata(output_dir)
    reviews = load_reviews(output_dir)

    entries: list[dict[str, Any]] = []
    for raw in book_ids_entries:
        bid = raw.get("book_id")
        if not isinstance(bid, int):
            continue
        entries.append(_build_entry(raw, discovery.get(bid), reviews.get(bid)))

    entries.sort(key=_sort_key)

    out_path = output_dir / CATALOG_FILE
    with out_path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    unrated = sum(1 for e in entries if e["consensus_tier"] == "unrated")
    stale = sum(1 for e in entries if e["review_stale"])
    if unrated:
        logger.warning(
            "[CATALOG] %d/%d books are unrated — consider adding review records",
            unrated,
            len(entries),
        )
    if stale:
        logger.warning(
            "[CATALOG] %d/%d books have review_stale=true (puzzle_count drift)",
            stale,
            len(entries),
        )
    logger.info("[CATALOG] Wrote %s with %d entries", CATALOG_FILE, len(entries))
    return len(entries)


def load_catalog(output_dir: Path) -> list[dict[str, Any]]:
    """Read ``books-catalog.jsonl``. Returns [] if missing."""
    return _read_jsonl(output_dir / CATALOG_FILE)
