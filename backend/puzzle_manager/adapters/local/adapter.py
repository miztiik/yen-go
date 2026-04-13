"""
Local adapter for importing SGF files from local directories.

Features (spec 111):
- Folder filtering (include_folders, exclude_folders)
- Checkpoint/resume support for interrupted imports
- Centralized puzzle validation via PuzzleValidator
- Progress logging at INFO/DEBUG levels
- Supports move_processed_to for organizing processed files
"""

import hashlib
import json
import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import register_adapter
from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint
from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleData,
    PuzzleValidator,
)
from backend.puzzle_manager.core.sgf_parser import parse_sgf
from backend.puzzle_manager.paths import get_project_root, rel_path

logger = logging.getLogger("puzzle_manager.adapters.local")


@register_adapter("local")
class LocalAdapter:
    """Adapter for importing SGF files from local directories.

    Features:
        - Folder filtering via include_folders/exclude_folders
        - Checkpoint/resume support for interrupted imports
        - Centralized puzzle validation
    """

    def __init__(self) -> None:
        self._path: Path | None = None
        self._move_processed_to: Path | None = None
        self._processed_files: set[str] = set()

        # Folder filtering configuration (spec 111)
        self._include_folders: list[str] = []
        self._exclude_folders: list[str] = []
        self._resume: bool = False
        self._validate: bool = True
        self._config_signature: str = ""

        # Centralized puzzle validator (spec 108)
        self._validator: PuzzleValidator = PuzzleValidator()

        # Track processed IDs for deduplication
        self._processed_ids: set[str] = set()

        # Config-based source ID for multi-source checkpoint separation
        self._source_id_override: str | None = None

    @property
    def name(self) -> str:
        return "Local Files"

    @property
    def source_id(self) -> str:
        """Unique source identifier.

        If configured with an explicit ID (e.g., from sources.json), use that.
        This allows multiple local sources with separate checkpoints.
        """
        if self._source_id_override:
            return self._source_id_override
        return "local"

    def configure(self, config: dict) -> None:
        """Configure the adapter.

        Config options:
            path: Directory containing SGF files (relative to project root)
            move_processed_to: Directory to move processed files to
            include_folders: List of folder names to include (empty = all)
            exclude_folders: List of folder names to exclude
            resume: Whether to load existing checkpoint (default: False)
            validate: Whether to validate puzzles (default: True)
            id: Optional explicit source ID for multi-source support
        """
        # Handle explicit source ID for multi-source support
        if "id" in config:
            self._source_id_override = config["id"]

        if "path" in config:
            path_str = config["path"]
            if Path(path_str).is_absolute():
                self._path = Path(path_str)
            else:
                self._path = get_project_root() / path_str

        if "move_processed_to" in config and config["move_processed_to"]:
            move_path = config["move_processed_to"]
            if Path(move_path).is_absolute():
                self._move_processed_to = Path(move_path)
            else:
                self._move_processed_to = get_project_root() / move_path

        # Folder filtering (spec 111)
        self._include_folders = config.get("include_folders", [])
        self._exclude_folders = config.get("exclude_folders", [])
        self._resume = config.get("resume", False)
        self._validate = config.get("validate", True)

        # Compute config signature for resume validation
        self._config_signature = self._compute_config_signature()

        # Log configuration
        folders_to_process = self._get_folders_to_process()
        folder_names = [f.name for f in folders_to_process]
        logger.info(
            "Local adapter configured: %s folders to process from %s",
            len(folder_names),
            self._format_log_path(self._path),
        )
        if self._include_folders:
            logger.debug(f"Include folders: {self._include_folders}")
        if self._exclude_folders:
            logger.debug(f"Exclude folders: {self._exclude_folders}")

    def _format_log_path(self, path: Path | None) -> str:
        """Format a path for logging without exposing absolute full paths.

        Returns a project-relative POSIX path when available, otherwise a
        redacted POSIX tail path prefixed with ``.../``.
        """
        if path is None:
            return "<unset>"

        path_obj = Path(path)
        formatted = rel_path(path_obj)

        # rel_path falls back to absolute POSIX paths for external locations.
        # Redact those by logging only a short tail segment.
        if path_obj.is_absolute() and formatted == path_obj.as_posix():
            tail_parts = [p for p in path_obj.parts if p and p != path_obj.anchor][-3:]
            tail = "/".join(tail_parts) if tail_parts else path_obj.name
            return f".../{tail}" if tail else "..."

        return formatted

    def _compute_config_signature(self) -> str:
        """Compute a signature of the folder filtering config.

        Used to detect when config has changed between resume runs.
        Uses JSON serialization for deterministic representation.

        Returns:
            8-character MD5 hash of include/exclude folders config.
        """
        config_dict = {
            "include": sorted(self._include_folders),
            "exclude": sorted(self._exclude_folders),
        }
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    def _get_folders_to_process(self) -> list[Path]:
        """Get list of folders to process based on filtering config.

        Returns:
            List of folder Paths to process, in order:
            - If include_folders specified, use that order
            - If only exclude_folders, alphabetical order minus excluded
            - If neither, alphabetical order of all folders
        """
        if not self._path or not self._path.exists():
            return []

        # Get all folders in base directory (case-sensitive)
        all_folders = sorted([
            d for d in self._path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ], key=lambda p: p.name)

        # Create lookup by folder name
        folder_by_name = {f.name: f for f in all_folders}

        if self._include_folders:
            # Use include_folders order, skip non-existent
            result = []
            for name in self._include_folders:
                if name in folder_by_name:
                    result.append(folder_by_name[name])
                else:
                    logger.warning(
                        f"Folder not found in collection: '{name}'. "
                        f"Available folders: {list(folder_by_name.keys())}"
                    )
            return result
        elif self._exclude_folders:
            # All folders except excluded
            return [f for f in all_folders if f.name not in self._exclude_folders]
        else:
            # All folders
            return all_folders

    def _sgf_to_puzzle_data(self, content: str) -> PuzzleData | None:
        """Convert SGF content to PuzzleData for centralized validation.

        Args:
            content: SGF file content.

        Returns:
            PuzzleData for validation, or None if parse fails.
        """
        try:
            game = parse_sgf(content)
        except Exception as e:
            logger.debug(f"SGF parse error: {e}")
            return None

        # Extract board size
        board_size = game.board_size if hasattr(game, 'board_size') else 19
        if isinstance(board_size, tuple):
            width, height = board_size
        else:
            width = height = board_size

        # Extract initial stones from parsed SGFGame (list[Point] → list[tuple])
        black_stones = [(p.x, p.y) for p in game.black_stones]
        white_stones = [(p.x, p.y) for p in game.white_stones]

        # Check for solution tree
        has_solution = game.has_solution

        return PuzzleData(
            board_width=width,
            board_height=height,
            black_stones=black_stones,
            white_stones=white_stones,
            has_solution=has_solution,
            solution_depth=None,  # Not calculated for performance
        )

    def _save_checkpoint(self, state: dict) -> None:
        """Save checkpoint state using AdapterCheckpoint."""
        AdapterCheckpoint.save(self.source_id, state)

    def _load_checkpoint(self) -> dict | None:
        """Load checkpoint state using AdapterCheckpoint.

        Returns:
            Checkpoint state dict or None if not found.
        """
        checkpoint = AdapterCheckpoint.load(self.source_id)
        if checkpoint is None:
            return None
        return checkpoint["state"]

    def _clear_checkpoint(self) -> None:
        """Clear checkpoint after successful completion."""
        AdapterCheckpoint.clear(self.source_id)

    def fetch(self, batch_size: int = 100) -> Iterator[FetchResult]:
        """Fetch SGF files from local directory.

        Supports folder filtering and checkpoint/resume (spec 111).
        Validates puzzles using PuzzleValidator (spec 108) before yielding.

        Args:
            batch_size: Maximum files to process.

        Yields:
            FetchResult for each file (success, skipped, or failed).
        """
        if not self._path:
            yield FetchResult.failed("", "No path configured")
            return

        if not self._path.exists():
            yield FetchResult.failed("", f"Path does not exist: {self._format_log_path(self._path)}")
            return

        # Get folders to process
        folders = self._get_folders_to_process()

        # Handle case where path exists but has no subfolders (flat structure)
        if not folders:
            # Process files directly in path (legacy behavior)
            sgf_files = sorted(self._path.glob("*.sgf"))
            if not sgf_files:
                logger.info("No SGF files found in path")
                return
            folders = [self._path]  # Treat path itself as the single "folder"

        # Initialize checkpoint state with explicit types
        state: dict[str, str | int] = {
            "current_folder": folders[0].name,
            "current_folder_index": 0,
            "files_completed": 0,  # 1-indexed: how many files done in current folder
            "total_processed": 0,
            "total_skipped": 0,
            "total_failed": 0,
            "config_signature": self._config_signature,
        }

        # Load existing checkpoint if resume enabled
        if self._resume:
            loaded_state = self._load_checkpoint()
            if loaded_state:
                # Check if config has changed
                saved_signature = loaded_state.get("config_signature", "")
                if saved_signature and saved_signature != self._config_signature:
                    logger.warning(
                        f"Config changed since checkpoint (was: {saved_signature}, "
                        f"now: {self._config_signature}). Folder positions may not align. "
                        f"Consider using resume=false for a fresh start."
                    )

                # Validate folder_index is within bounds
                saved_folder_index = loaded_state.get("current_folder_index", 0)
                if saved_folder_index >= len(folders):
                    logger.warning(
                        f"Checkpoint folder_index ({saved_folder_index}) exceeds "
                        f"available folders ({len(folders)}). Starting from beginning."
                    )
                    loaded_state["current_folder_index"] = 0
                    loaded_state["files_completed"] = 0

                state = loaded_state
                logger.info(
                    f"Resuming from checkpoint: folder={state['current_folder']}, "
                    f"files_completed={state['files_completed']}"
                )

        count = 0
        # Checkpoint save interval: save every N puzzles instead of every puzzle
        # to reduce PermissionError risk on Windows (antivirus/indexer file locking)
        checkpoint_interval = 10
        files_since_checkpoint = 0
        completed_all = False
        start_folder_index = min(int(state["current_folder_index"]), len(folders) - 1)

        try:
            for folder_idx, folder in enumerate(folders[start_folder_index:], start=start_folder_index):
                # Log folder progress at INFO level
                logger.info(f"Processing folder: {folder.name} ({folder_idx + 1}/{len(folders)})")

                # Get SGF files in this folder
                if folder == self._path:
                    # Flat structure - files directly in path
                    sgf_files = sorted(folder.glob("*.sgf"))
                else:
                    # Subfolder structure - include nested files
                    sgf_files = sorted(folder.rglob("*.sgf"))

                if not sgf_files:
                    logger.info(f"No SGF files in folder: {folder.name}")
                    continue

                # Determine starting file index (files_completed is 1-indexed count)
                start_file_index = 0
                if folder_idx == int(state["current_folder_index"]):
                    start_file_index = int(state["files_completed"])  # Skip already completed files

                for file_idx, sgf_path in enumerate(sgf_files[start_file_index:], start=start_file_index):
                    if count >= batch_size:
                        # Save checkpoint before returning
                        state["current_folder"] = folder.name
                        state["current_folder_index"] = folder_idx
                        state["files_completed"] = file_idx  # file_idx is 0-indexed, so this = count of completed
                        self._save_checkpoint(state)
                        files_since_checkpoint = 0
                        logger.info(
                            f"Local adapter: fetched {state['total_processed']}, "
                            f"skipped {state['total_skipped']}, failed {state['total_failed']} "
                            f"(batch complete)"
                        )
                        return

                    # Log file details at DEBUG level
                    logger.debug(f"Processing file: {self._format_log_path(sgf_path)}")

                    try:
                        content = sgf_path.read_text(encoding="utf-8")
                        puzzle_id = self._generate_id(content)

                        # Skip if already processed
                        if puzzle_id in self._processed_ids:
                            continue

                        # Validate puzzle if enabled
                        if self._validate:
                            puzzle_data = self._sgf_to_puzzle_data(content)
                            if puzzle_data is None:
                                # Parse error - yield failed
                                state["total_failed"] = int(state["total_failed"]) + 1
                                self._processed_ids.add(puzzle_id)
                                state["files_completed"] = file_idx + 1  # 1-indexed: count of files done
                                files_since_checkpoint += 1
                                if files_since_checkpoint >= checkpoint_interval:
                                    self._save_checkpoint(state)
                                    files_since_checkpoint = 0
                                yield FetchResult.failed(
                                    puzzle_id=puzzle_id,
                                    error=f"SGF parse error: {self._format_log_path(sgf_path)}",
                                )
                                continue

                            validation_result = self._validator.validate(puzzle_data)
                            if not validation_result.is_valid:
                                # Validation failure - yield skipped
                                state["total_skipped"] = int(state["total_skipped"]) + 1
                                self._processed_ids.add(puzzle_id)
                                state["files_completed"] = file_idx + 1  # 1-indexed: count of files done
                                files_since_checkpoint += 1
                                if files_since_checkpoint >= checkpoint_interval:
                                    self._save_checkpoint(state)
                                    files_since_checkpoint = 0
                                yield FetchResult.skipped(
                                    puzzle_id=puzzle_id,
                                    reason=validation_result.rejection_reason or "validation failed",
                                )
                                continue

                        # Success - yield the puzzle
                        self._processed_ids.add(puzzle_id)
                        state["total_processed"] = int(state["total_processed"]) + 1
                        count += 1

                        # Update checkpoint state in memory
                        state["current_folder"] = folder.name
                        state["current_folder_index"] = folder_idx
                        state["files_completed"] = file_idx + 1  # 1-indexed: count of files done
                        files_since_checkpoint += 1

                        # Throttle disk writes: save every checkpoint_interval puzzles
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0

                        yield FetchResult.success(
                            puzzle_id=puzzle_id,
                            sgf_content=content,
                            source_link=str(sgf_path),
                        )

                        # Move processed file if configured
                        if self._move_processed_to:
                            self._move_file(sgf_path)

                    except UnicodeDecodeError as e:
                        state["total_failed"] = int(state["total_failed"]) + 1
                        state["files_completed"] = file_idx + 1
                        files_since_checkpoint += 1
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0
                        safe_path = self._format_log_path(sgf_path)
                        yield FetchResult.failed(safe_path, f"Encoding error: {e}")
                    except OSError as e:
                        state["total_failed"] = int(state["total_failed"]) + 1
                        state["files_completed"] = file_idx + 1
                        files_since_checkpoint += 1
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0
                        safe_path = self._format_log_path(sgf_path)
                        yield FetchResult.failed(safe_path, f"File I/O error: {e}")
                    except ValueError as e:
                        state["total_failed"] = int(state["total_failed"]) + 1
                        state["files_completed"] = file_idx + 1
                        files_since_checkpoint += 1
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0
                        safe_path = self._format_log_path(sgf_path)
                        yield FetchResult.failed(safe_path, f"Data error: {e}")

            # All files processed - clear checkpoint and log summary
            completed_all = True
            self._clear_checkpoint()
            logger.info(
                f"Local adapter: fetched {state['total_processed']}, "
                f"skipped {state['total_skipped']}, failed {state['total_failed']}"
            )
        finally:
            # Flush pending checkpoint when generator is closed early (consumer breaks)
            if files_since_checkpoint > 0 and not completed_all:
                self._save_checkpoint(state)

    def _generate_id(self, content: str) -> str:
        """Generate puzzle ID from content hash.

        Uses SHA256 hash of content to ensure:
        - Deterministic IDs for same content
        - Collision resistance
        - Deduplication of identical puzzles

        Args:
            content: SGF file content string.

        Returns:
            16-character hex string (first 16 chars of SHA256 hash).
        """
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return content_hash[:16]

    def is_available(self) -> bool:
        """Check if local path is configured and exists."""
        return self._path is not None and self._path.exists()

    def _move_file(self, source: Path) -> None:
        """Move processed file to destination."""
        if not self._move_processed_to:
            return

        self._move_processed_to.mkdir(parents=True, exist_ok=True)
        dest = self._move_processed_to / source.name

        # Handle name conflicts
        counter = 1
        while dest.exists():
            stem = source.stem
            suffix = source.suffix
            dest = self._move_processed_to / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.move(str(source), str(dest))
        logger.debug(
            "Moved processed file: %s -> %s",
            self._format_log_path(source),
            self._format_log_path(dest),
        )

    def supports_resume(self) -> bool:
        """Whether adapter supports resuming from checkpoint."""
        return True

    def get_checkpoint(self) -> str | None:
        """Get current checkpoint as JSON string.

        Returns:
            JSON string of checkpoint state, or None if no checkpoint.
        """
        checkpoint = AdapterCheckpoint.load(self.source_id)
        if checkpoint is None:
            return None
        return json.dumps(checkpoint["state"])

    def set_checkpoint(self, checkpoint: str) -> None:
        """Set checkpoint from JSON string.

        Args:
            checkpoint: JSON string of checkpoint state.
        """
        state = json.loads(checkpoint)
        AdapterCheckpoint.save(self.source_id, state)
