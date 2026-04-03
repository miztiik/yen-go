"""
Main daily challenge generator.

Coordinates generation of all daily challenge types.
Callers are responsible for persisting via inject_daily_schedule.
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.core.datetime_utils import utc_now
from backend.puzzle_manager.daily.by_tag import generate_tag_challenge
from backend.puzzle_manager.daily.standard import generate_standard_daily
from backend.puzzle_manager.daily.timed import generate_timed_challenge
from backend.puzzle_manager.exceptions import DailyGenerationError
from backend.puzzle_manager.models.config import DailyConfig
from backend.puzzle_manager.models.daily import (
    DailyChallenge,
)

logger = logging.getLogger("puzzle_manager.daily")


@dataclass
class GenerationResult:
    """Result of daily challenge generation."""
    challenges: list[DailyChallenge] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class DailyGenerator:
    """Generates daily challenges for a date range.

    Creates StandardDaily, TimedChallenge, and TagChallenge for each day.
    Returns a GenerationResult; callers are responsible for persistence.
    """

    def __init__(
        self,
        db_path: Path,
        config: DailyConfig | None = None,
        dry_run: bool = False,
    ):
        """Initialize generator.

        Args:
            db_path: Path to yengo-search.db
            config: Daily config (loads default if not provided)
            dry_run: If True, log writes but don't actually write files
        """
        if config is None:
            loader = ConfigLoader()
            pipeline_config = loader.load_pipeline_config()
            config = pipeline_config.daily

        self.config = config
        self.db_path = db_path
        self.dry_run = dry_run

    def generate(
        self,
        start_date: datetime,
        end_date: datetime | None = None,
        force: bool = False,
    ) -> GenerationResult:
        """Generate daily challenges for a date range.

        Args:
            start_date: First date to generate
            end_date: Last date to generate (default: start_date)
            force: Overwrite existing files

        Returns:
            GenerationResult with challenges and any failures.
        """
        if end_date is None:
            end_date = start_date

        if end_date < start_date:
            raise DailyGenerationError("end_date must be >= start_date")

        results = []
        failures: list[str] = []
        current = start_date

        while current <= end_date:
            try:
                challenge = self._generate_for_date(current, force=force)
                results.append(challenge)
                logger.debug(f"Generated daily for {current.date()}")
            except Exception as e:
                logger.error(f"Failed to generate for {current.date()}: {e}", exc_info=True)
                failures.append(str(e))

            current += timedelta(days=1)

        if failures:
            logger.error(f"{len(failures)} date(s) failed during generation")
        logger.info(f"Generated {len(results)} daily challenges")
        return GenerationResult(challenges=results, failures=failures)

    def generate_next_n_days(
        self,
        n: int = 7,
        start_date: datetime | None = None,
        force: bool = False,
    ) -> GenerationResult:
        """Generate challenges for the next N days.

        Args:
            n: Number of days to generate
            start_date: Starting date (default: today)
            force: Overwrite existing files

        Returns:
            GenerationResult with challenges and any failures.
        """
        if start_date is None:
            start_date = utc_now()

        end_date = start_date + timedelta(days=n - 1)
        return self.generate(start_date, end_date, force=force)

    def _generate_for_date(
        self,
        date: datetime,
        force: bool = False,
    ) -> DailyChallenge:
        """Generate all challenge types for a single date."""
        date_str = date.strftime("%Y-%m-%d")

        logger.info(f"Generating daily challenge for {date_str}")

        # Load puzzle pool
        pool = self._load_puzzle_pool()

        if not pool:
            raise DailyGenerationError("No puzzles available for daily generation")

        # Generate each challenge type
        standard = generate_standard_daily(date, pool, self.config)
        timed = generate_timed_challenge(date, pool, self.config)
        tag_challenge = generate_tag_challenge(date, pool, self.config)

        # Get the featured tag from tag_challenge for technique_of_day
        technique_of_day = tag_challenge.tag if tag_challenge.tag else ""

        # Create combined challenge with proper field assignment (spec 112)
        challenge = DailyChallenge(
            date=date_str,
            standard=standard,
            timed=timed,
            by_tag={technique_of_day: tag_challenge} if technique_of_day else {},
            technique_of_day=technique_of_day,
        )

        logger.info(f"Successfully generated daily challenge for {date_str}")

        return challenge

    def _load_puzzle_pool(self) -> list[dict]:
        """Load available puzzles for daily generation from the search database.

        Reads from ``yengo-search.db``.

        Applies quality and content-type filtering based on DailyConfig:
        - Excludes puzzles below ``config.min_quality`` (default: 2)
        - Excludes puzzles with content types in ``config.excluded_content_types``
          (default: [3] = training)

        Returns entries sorted by compact path for deterministic ordering.
        """
        if not self.db_path.exists():
            raise DailyGenerationError(f"yengo-search.db not found at {self.db_path}")
        return self._load_puzzle_pool_from_db(self.db_path)

    def _load_puzzle_pool_from_db(self, db_path: Path) -> list[dict]:
        """Load puzzle pool from yengo-search.db.

        Queries the ``puzzles`` and ``puzzle_tags`` tables, applies quality
        and content-type filtering, and returns compact-entry dicts compatible
        with the downstream daily generators.
        """
        min_quality = self.config.min_quality
        excluded_ct = set(self.config.excluded_content_types)

        puzzles: list[dict] = []

        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                # Build WHERE clause for quality / content-type filtering
                placeholders = ",".join("?" for _ in excluded_ct)
                params: list[int] = [min_quality]
                query = (
                    "SELECT content_hash, batch, level_id, quality, content_type, "
                    "cx_depth, cx_refutations, cx_solution_len, cx_unique_resp "
                    "FROM puzzles WHERE quality >= ?"
                )
                if excluded_ct:
                    query += f" AND content_type NOT IN ({placeholders})"
                    params.extend(sorted(excluded_ct))
                query += " ORDER BY batch, content_hash"

                rows = conn.execute(query, params).fetchall()

                # Pre-load all tag mappings in one query for efficiency
                tag_map: dict[str, list[int]] = {}
                for tag_row in conn.execute(
                    "SELECT content_hash, tag_id FROM puzzle_tags"
                ):
                    tag_map.setdefault(tag_row[0], []).append(tag_row[1])

                for row in rows:
                    entry: dict = {
                        "p": f"{row['batch']}/{row['content_hash']}",
                        "l": row["level_id"],
                        "t": sorted(tag_map.get(row["content_hash"], [])),
                        "q": row["quality"],
                        "ct": row["content_type"],
                        "x": [
                            row["cx_depth"],
                            row["cx_refutations"],
                            row["cx_solution_len"],
                            row["cx_unique_resp"],
                        ],
                    }
                    puzzles.append(entry)
            finally:
                conn.close()
        except sqlite3.Error as e:
            raise DailyGenerationError(f"Failed to load puzzle pool from DB: {e}") from e

        logger.debug(f"Loaded {len(puzzles)} puzzles from {db_path.name}")
        return puzzles


def generate_daily_for_date(
    date: datetime,
    db_path: Path,
    config: DailyConfig | None = None,
    force: bool = False,
) -> DailyChallenge | None:
    """Convenience function to generate daily for a single date.

    Args:
        date: Date to generate for
        db_path: Path to yengo-search.db
        config: Optional config override
        force: Overwrite existing

    Returns:
        Generated DailyChallenge, or None if no puzzles are available.
    """
    generator = DailyGenerator(db_path=db_path, config=config)
    result = generator.generate(date, force=force)
    return result.challenges[0] if result.challenges else None
