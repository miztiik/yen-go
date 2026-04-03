"""
Base adapter protocol for puzzle sources.

All adapters must implement this protocol to integrate with the pipeline.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


@dataclass
class FetchResult:
    """Result of fetching a single puzzle.

    Represents either a successful fetch, a skipped item, or a failure.
    """

    status: Literal["success", "skipped", "failed"]
    puzzle_id: str | None = None
    sgf_content: str | None = None
    source_link: str | None = None
    error: str | None = None

    @classmethod
    def success(
        cls,
        puzzle_id: str,
        sgf_content: str,
        source_link: str | None = None,
    ) -> "FetchResult":
        """Create a successful fetch result."""
        return cls(
            status="success",
            puzzle_id=puzzle_id,
            sgf_content=sgf_content,
            source_link=source_link,
        )

    @classmethod
    def skipped(cls, puzzle_id: str, reason: str) -> "FetchResult":
        """Create a skipped fetch result."""
        return cls(
            status="skipped",
            puzzle_id=puzzle_id,
            error=reason,
        )

    @classmethod
    def failed(cls, puzzle_id: str, error: str) -> "FetchResult":
        """Create a failed fetch result."""
        return cls(
            status="failed",
            puzzle_id=puzzle_id,
            error=error,
        )

    @property
    def is_success(self) -> bool:
        """Check if fetch was successful."""
        return self.status == "success"

    @property
    def is_skipped(self) -> bool:
        """Check if item was skipped."""
        return self.status == "skipped"

    @property
    def is_failed(self) -> bool:
        """Check if fetch failed."""
        return self.status == "failed"


@runtime_checkable
class BaseAdapter(Protocol):
    """Core protocol for ALL puzzle source adapters.

    Implements adapter-protocol.md contract (v2.0.0).

    All adapters MUST:
    1. Implement all 4 protocol methods
    2. Use @register_adapter decorator
    3. Handle errors gracefully (yield FetchResult.failed)
    4. Support configuration via configure()
    5. Follow SGF property standards (GN=filename, SO=empty, YG from puzzle-levels.json)

    For checkpoint/resume support, implement ResumableAdapter instead.
    """

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        ...

    @property
    def source_id(self) -> str:
        """Unique source identifier (e.g., 'blacktoplay', 'ogs')."""
        ...

    def configure(self, config: dict) -> None:
        """Apply adapter-specific configuration.

        Args:
            config: Adapter config from sources.json entry's 'config' object
        """
        ...

    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
        """Fetch puzzles from source.

        Args:
            batch_size: Maximum items per batch

        Yields:
            FetchResult for each puzzle (success, skipped, or failed)
        """
        ...

    def is_available(self) -> bool:
        """Check if source is available/accessible.

        Returns:
            True if source can be reached, False otherwise
        """
        ...


@runtime_checkable
class ResumableAdapter(BaseAdapter, Protocol):
    """Extended protocol for adapters supporting checkpoint/resume.

    Use this protocol for:
    - API-based adapters with large datasets
    - Adapters that may be interrupted and need to resume
    - Any adapter requiring state persistence between runs

    Examples: OGS, GoProblems (API-based with thousands of puzzles)
    """

    def supports_resume(self) -> bool:
        """Whether adapter supports resuming from checkpoint.

        Returns:
            True if checkpoint methods are functional
        """
        ...

    def get_checkpoint(self) -> str | None:
        """Get current checkpoint for resume support.

        Returns:
            Checkpoint string or None if no checkpoint saved
        """
        ...

    def set_checkpoint(self, checkpoint: str) -> None:
        """Set checkpoint for resume support.

        Args:
            checkpoint: Checkpoint string from previous run
        """
        ...
