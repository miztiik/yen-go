"""Data models for Harada tsumego archive crawler."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ImageError:
    """Structured error record for a failed image download."""

    status: str = ""  # "404", "html_not_image", "timeout", "http_error", "transient"
    url: str = ""  # The URL that was attempted
    fallback_url: str = ""  # Fallback URL attempted (if any)
    http_code: int = 0  # HTTP status code (0 if not applicable)
    reason: str = ""  # Human-readable reason
    timestamp: str = ""  # ISO timestamp of the failure

    def to_dict(self) -> dict:
        # Only serialize non-empty fields to keep catalog compact
        return {k: v for k, v in asdict(self).items() if v}

    @classmethod
    def from_dict(cls, d: dict) -> ImageError:
        if isinstance(d, str):
            # Backward compat: old format was just a string like "404" or "transient"
            return cls(status=d, reason=d)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @property
    def is_permanent(self) -> bool:
        """True if this error means we should never retry."""
        return self.status in ("404", "html_not_image")

    def __bool__(self) -> bool:
        return bool(self.status)


@dataclass
class PuzzleImage:
    """A single Go board image (problem or answer diagram)."""

    url: str  # Original source URL
    wayback_url: str = ""  # Full Wayback URL used to download
    local_path: str = ""  # Relative path within _images/
    image_type: str = ""  # "problem", "answer_correct", "answer_wrong"
    level: str = ""  # "elementary" or "intermediate"
    variant: int = 0  # 0 for first, 1+ for additional wrong answers
    downloaded: bool = False
    file_size: int = 0
    error: str | dict = ""  # Backward compat: str for old data, dict for new ImageError
    semantic_id: str = ""  # e.g., "1996_001_problem_elementary"

    def to_dict(self) -> dict:
        d = asdict(self)
        # Serialize error as structured dict if it's an ImageError-like dict
        if isinstance(self.error, dict):
            d["error"] = {k: v for k, v in self.error.items() if v}
        elif isinstance(self.error, ImageError):
            d["error"] = self.error.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PuzzleImage:
        img = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        return img

    @property
    def error_obj(self) -> ImageError:
        """Get error as a structured ImageError object."""
        if isinstance(self.error, ImageError):
            return self.error
        if isinstance(self.error, dict):
            return ImageError.from_dict(self.error)
        if isinstance(self.error, str) and self.error:
            return ImageError.from_dict(self.error)
        return ImageError()

    @property
    def has_permanent_error(self) -> bool:
        """True if this image has a permanent (non-retryable) error."""
        err = self.error_obj
        return err.is_permanent if err else False

    @property
    def has_error(self) -> bool:
        """True if this image has any error."""
        if isinstance(self.error, dict):
            return bool(self.error.get("status"))
        if isinstance(self.error, str):
            return bool(self.error)
        return False


@dataclass
class PuzzleEntry:
    """One weekly Harada tsumego problem.

    Each problem has two difficulty levels (elementary + intermediate)
    with problem images, correct answer images, and wrong answer images.
    """

    problem_number: int  # No.1 through No.1183+
    year: int  # Publication year
    date_str: str  # Date as shown on page, e.g. "5/27"
    full_date: str = ""  # ISO format: "1996-05-27"

    # URLs from year page (original source URLs)
    problem_page_url: str = ""
    answer_page_url: str = ""

    # Wayback timestamps found for these pages
    problem_wayback_ts: str = ""
    answer_wayback_ts: str = ""

    # Text content extracted from pages
    elementary_instruction: str = ""
    intermediate_instruction: str = ""
    elementary_answer_text: str = ""
    intermediate_answer_text: str = ""

    # Images discovered from problem/answer pages
    images: list[PuzzleImage] = field(default_factory=list)

    # Processing status
    status: str = "pending"  # pending, discovered, page_cached, images_downloaded, error
    error_detail: str = ""
    problem_page_cached: bool = False
    answer_page_cached: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["images"] = [img.to_dict() for img in self.images]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> PuzzleEntry:
        images_data = d.pop("images", [])
        entry = cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
        entry.images = [PuzzleImage.from_dict(img) for img in images_data]
        return entry

    def image_count(self) -> int:
        return len(self.images)

    def downloaded_count(self) -> int:
        return sum(1 for img in self.images if img.downloaded)

    @property
    def asset_summary(self) -> dict[str, int | bool]:
        """Per-puzzle availability rollup."""
        return {
            "images_total": len(self.images),
            "images_downloaded": sum(1 for i in self.images if i.downloaded),
            "images_404": sum(1 for i in self.images if i.has_permanent_error),
            "images_pending": sum(
                1 for i in self.images
                if not i.downloaded and not i.has_permanent_error
            ),
            "problem_available": any(
                i.image_type == "problem" and i.downloaded for i in self.images
            ),
            "answer_available": any(
                i.image_type == "answer_correct" and i.downloaded for i in self.images
            ),
        }

    @property
    def is_complete(self) -> bool:
        """True if all discoverable assets are downloaded (or permanently failed)."""
        return all(
            i.downloaded or i.has_permanent_error for i in self.images
        ) and (self.problem_page_cached or not self.problem_page_url)


@dataclass
class YearEntry:
    """Index entry for one year of problems."""

    year: int
    original_url: str  # Original source URL
    wayback_url: str = ""  # Wayback URL with timestamp
    wayback_ts: str = ""  # Best Wayback timestamp found
    problem_range: str = ""  # e.g., "No.1 - No.36"
    problem_count: int = 0
    status: str = "pending"  # pending, crawled, error
    error_detail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> YearEntry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Catalog:
    """Complete catalog of the Harada tsumego collection.

    This is the master tracking structure — serialized to catalog.json.
    """

    version: str = "1.1.0"
    collection_name: str = "Weekly Tsumego by Minoru Harada"
    collection_slug: str = "harada-tsumego"

    # Discovery state
    years: list[YearEntry] = field(default_factory=list)
    puzzles: list[PuzzleEntry] = field(default_factory=list)

    # Summary stats
    total_years_discovered: int = 0
    total_puzzles_discovered: int = 0
    total_images_discovered: int = 0
    total_images_downloaded: int = 0
    total_pages_cached: int = 0
    total_errors: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "collection_name": self.collection_name,
            "collection_slug": self.collection_slug,
            "summary": {
                "total_years": self.total_years_discovered,
                "total_puzzles": self.total_puzzles_discovered,
                "total_images_discovered": self.total_images_discovered,
                "total_images_downloaded": self.total_images_downloaded,
                "total_pages_cached": self.total_pages_cached,
                "total_errors": self.total_errors,
            },
            "years": [y.to_dict() for y in self.years],
            "puzzles": [p.to_dict() for p in self.puzzles],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Catalog:
        summary = d.get("summary", {})
        catalog = cls(
            version=d.get("version", "1.0.0"),
            collection_name=d.get("collection_name", ""),
            collection_slug=d.get("collection_slug", ""),
            total_years_discovered=summary.get("total_years", 0),
            total_puzzles_discovered=summary.get("total_puzzles", 0),
            total_images_discovered=summary.get("total_images_discovered", 0),
            total_images_downloaded=summary.get("total_images_downloaded", 0),
            total_pages_cached=summary.get("total_pages_cached", 0),
            total_errors=summary.get("total_errors", 0),
        )
        catalog.years = [YearEntry.from_dict(y) for y in d.get("years", [])]
        catalog.puzzles = [PuzzleEntry.from_dict(p) for p in d.get("puzzles", [])]
        return catalog

    def update_stats(self) -> None:
        """Recompute summary statistics from actual data."""
        self.total_years_discovered = len(self.years)
        self.total_puzzles_discovered = len(self.puzzles)
        self.total_images_discovered = sum(p.image_count() for p in self.puzzles)
        self.total_images_downloaded = sum(p.downloaded_count() for p in self.puzzles)
        self.total_pages_cached = sum(
            1 for p in self.puzzles if p.problem_page_cached
        ) + sum(1 for p in self.puzzles if p.answer_page_cached)
        self.total_errors = sum(1 for p in self.puzzles if p.status == "error")

    def get_puzzle(self, number: int) -> PuzzleEntry | None:
        """Look up puzzle by number."""
        for p in self.puzzles:
            if p.problem_number == number:
                return p
        return None

    def per_year_summary(self) -> dict[int, dict[str, int]]:
        """Compute per-year rollup from puzzle data.

        Returns {year: {total, complete, pending, errors, images_total,
        images_downloaded, images_404, images_pending, pct}}.
        """
        by_year: dict[int, list[PuzzleEntry]] = defaultdict(list)
        for p in self.puzzles:
            by_year[p.year].append(p)

        result: dict[int, dict[str, int]] = {}
        for year in sorted(by_year):
            puzzles = by_year[year]
            imgs_total = sum(p.image_count() for p in puzzles)
            imgs_dl = sum(p.downloaded_count() for p in puzzles)
            imgs_404 = sum(
                sum(1 for i in p.images if i.has_permanent_error) for p in puzzles
            )
            complete = sum(1 for p in puzzles if p.is_complete)
            pending = sum(
                1 for p in puzzles
                if p.status in ("pending", "discovered", "page_cached")
                and not p.is_complete
            )
            errors = sum(1 for p in puzzles if p.status == "error")
            pct = round(100 * complete / len(puzzles)) if puzzles else 0
            result[year] = {
                "total": len(puzzles),
                "complete": complete,
                "pending": pending,
                "errors": errors,
                "images_total": imgs_total,
                "images_downloaded": imgs_dl,
                "images_404": imgs_404,
                "images_pending": imgs_total - imgs_dl - imgs_404,
                "pct": pct,
            }
        return result
