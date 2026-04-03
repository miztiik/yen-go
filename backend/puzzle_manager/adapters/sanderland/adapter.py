"""
Sanderland adapter for importing puzzles from sanderland collection.

Local collection adapter for pre-downloaded JSON puzzle files.
Converts JSON format to SGF.

Features:
- Folder filtering (include_folders, exclude_folders)
- Checkpoint/resume support for interrupted imports
"""

import json
import logging
from pathlib import Path

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import register_adapter
from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.core.checkpoint import AdapterCheckpoint
from backend.puzzle_manager.core.collection_assigner import (
    assign_collections,
    normalize,
    tokenize,
)
from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleData,
    PuzzleValidator,
)
from backend.puzzle_manager.paths import get_project_root, rel_path

logger = logging.getLogger("puzzle_manager.adapters.sanderland")
# Ingest logger for operational messages (fetching, waiting) - goes to ingest.log
ingest_logger = logging.getLogger("ingest")


@register_adapter("sanderland")
class SanderlandAdapter:
    """Adapter for Sanderland puzzle collection.

    Reads from external-sources/sanderland/ directory.

    Features:
        - Folder filtering via include_folders/exclude_folders
        - Checkpoint/resume support for interrupted imports
        - Centralized puzzle validation
    """

    def __init__(
        self,
        source_dir: str | None = None,
        **kwargs,
    ):
        """Initialize adapter.

        Args:
            source_dir: Path to sanderland collection (default: external-sources/sanderland)
            **kwargs: Additional config options
        """
        if source_dir:
            self.source_dir = Path(source_dir)
        else:
            self.source_dir = get_project_root() / "external-sources" / "sanderland"

        self._processed_ids: set[str] = set()

        # Folder filtering configuration
        self._include_folders: list[str] = []
        self._exclude_folders: list[str] = []
        self._resume: bool = False
        self._config_signature: str = ""

        # Centralized puzzle validator (spec 108)
        self._validator = PuzzleValidator()

        # Load collection aliases for enrichment (spec 128)
        try:
            self._alias_map = ConfigLoader().get_collection_aliases()
        except Exception as e:
            logger.warning(f"Failed to load collection aliases: {e}")
            self._alias_map = {}

    @property
    def name(self) -> str:
        """Human-readable adapter name."""
        return "Sanderland Collection"

    @property
    def source_id(self) -> str:
        """Unique source identifier."""
        return "sanderland"

    def configure(self, config: dict) -> None:
        """Apply adapter-specific configuration.

        Args:
            config: Configuration dictionary with keys:
                - source_dir (str, optional): Path to sanderland collection
                - include_folders (list[str], optional): Folders to include (empty = all)
                - exclude_folders (list[str], optional): Folders to exclude
                - resume (bool, optional): If True, load existing checkpoint
        """
        if "source_dir" in config:
            self.source_dir = Path(config["source_dir"])

        # Folder filtering (spec 109)
        self._include_folders = config.get("include_folders", [])
        self._exclude_folders = config.get("exclude_folders", [])
        self._resume = config.get("resume", False)

        # Store config signature for resume validation
        self._config_signature = self._compute_config_signature()

        # Log configuration
        folders_to_process = self._get_folders_to_process()
        folder_names = [f.name for f in folders_to_process]
        logger.info(f"Sanderland configured: {len(folder_names)} folders to process")
        if self._include_folders:
            logger.debug(f"Include folders: {self._include_folders}")
        if self._exclude_folders:
            logger.debug(f"Exclude folders: {self._exclude_folders}")

    def supports_resume(self) -> bool:
        """Whether adapter supports resuming from checkpoint.

        Returns:
            True (always supported)
        """
        return True

    def get_checkpoint(self) -> str | None:
        """Get current checkpoint as JSON string.

        Returns:
            JSON string of checkpoint state, or None if no checkpoint
        """
        checkpoint = AdapterCheckpoint.load(self.source_id)
        if checkpoint is None:
            return None
        return json.dumps(checkpoint["state"])

    def set_checkpoint(self, checkpoint: str) -> None:
        """Set checkpoint from JSON string.

        Args:
            checkpoint: JSON string of checkpoint state
        """
        state = json.loads(checkpoint)
        AdapterCheckpoint.save(self.source_id, state)

    def _get_folders_to_process(self) -> list[Path]:
        """Get list of folders to process based on filtering config.

        Returns:
            List of folder Paths to process, in order:
            - If include_folders specified, use that order
            - If only exclude_folders, alphabetical order minus excluded
            - If neither, alphabetical order of all folders
        """
        # Find base directory with problems
        base_dirs = [
            self.source_dir / "problems",  # Real sanderland structure
            self.source_dir,                # Test structure
        ]

        base_dir = None
        for bd in base_dirs:
            if bd.exists() and bd.is_dir():
                base_dir = bd
                break

        if base_dir is None:
            return []

        # Get all folders in base directory (case-sensitive)
        all_folders = sorted([
            d for d in base_dir.iterdir()
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

    def _save_checkpoint(self, state: dict) -> None:
        """Save checkpoint state."""
        AdapterCheckpoint.save(self.source_id, state)

    def _load_checkpoint(self) -> dict | None:
        """Load checkpoint state.

        Returns:
            Checkpoint state dict or None if not found/invalid
        """
        checkpoint = AdapterCheckpoint.load(self.source_id)
        if checkpoint is None:
            return None
        return checkpoint["state"]

    def _clear_checkpoint(self) -> None:
        """Clear checkpoint after successful completion."""
        AdapterCheckpoint.clear(self.source_id)

    def _compute_config_signature(self) -> str:
        """Compute a signature of the folder filtering config.

        Used to detect when config has changed between resume runs.
        Uses JSON serialization for deterministic, explicit representation.

        Returns:
            String signature of include_folders + exclude_folders (8-char MD5)
        """
        import hashlib
        config_dict = {
            "include": sorted(self._include_folders),
            "exclude": sorted(self._exclude_folders),
        }
        config_str = json.dumps(config_dict, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]

    def _to_puzzle_data(self, data: dict) -> PuzzleData:
        """Convert Sanderland JSON to PuzzleData for centralized validation.

        This helper bridges the Sanderland-specific JSON format to the
        adapter-agnostic PuzzleData used by PuzzleValidator (spec 108).

        Args:
            data: Sanderland puzzle JSON data

        Returns:
            PuzzleData for validation
        """
        # Parse board size - can be "9" or "7:9" format
        sz = data.get("SZ", "19")
        if ":" in str(sz):
            # Non-square: "7:9" means 7 wide, 9 tall
            parts = str(sz).split(":")
            width = int(parts[0])
            height = int(parts[1])
        else:
            # Square board
            width = height = int(sz)

        # Parse stones as coordinate lists
        def parse_coords(coords: list) -> list[tuple[int, int]]:
            """Parse Sanderland coordinate list to (x, y) tuples."""
            result = []
            for coord in coords or []:
                if len(coord) >= 2:
                    x = ord(coord[0]) - ord('a')
                    y = ord(coord[1]) - ord('a')
                    result.append((x, y))
            return result

        black_stones = parse_coords(data.get("AB", []))
        white_stones = parse_coords(data.get("AW", []))

        # Determine if has solution
        sol = data.get("SOL", [])
        has_solution = len(sol) > 0

        # Calculate solution depth (count moves in SOL)
        solution_depth = len(sol) if sol else None

        return PuzzleData(
            board_width=width,
            board_height=height,
            black_stones=black_stones,
            white_stones=white_stones,
            has_solution=has_solution,
            solution_depth=solution_depth,
        )

    def fetch(self, batch_size: int = 100):
        """Fetch puzzles from sanderland collection.

        The sanderland collection uses JSON format, not SGF.
        This adapter converts JSON to SGF.

        Puzzles are validated using PuzzleValidator (spec 108) before
        conversion to ensure consistent validation across adapters.

        Supports folder filtering and checkpoint/resume (spec 109).

        Yields:
            FetchResult for each puzzle
        """
        if not self.source_dir.exists():
            logger.warning(f"Sanderland directory not found: {rel_path(self.source_dir)}")
            yield FetchResult.failed(
                puzzle_id="sanderland-init",
                error=f"Directory not found: {rel_path(self.source_dir)}",
            )
            return

        # Get folders to process
        folders = self._get_folders_to_process()
        if not folders:
            logger.info("No folders to process")
            return

        # Initialize or load checkpoint state
        state = {
            "current_folder": folders[0].name,
            "current_folder_index": 0,
            "files_completed": 0,  # 1-indexed: how many files done in current folder
            "total_processed": 0,
            "total_failed": 0,
            "config_signature": self._config_signature,
        }

        if self._resume:
            loaded_state = self._load_checkpoint()
            if loaded_state:
                # Check if config has changed since checkpoint was saved
                saved_signature = loaded_state.get("config_signature", "")
                if saved_signature and saved_signature != self._config_signature:
                    logger.warning(
                        f"Config changed since checkpoint (was: {saved_signature}, "
                        f"now: {self._config_signature}). Folder positions may not align. "
                        f"Consider using --no-resume for a fresh start."
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
        start_folder_index = min(state["current_folder_index"], len(folders) - 1)

        try:
            for folder_idx, folder in enumerate(folders[start_folder_index:], start=start_folder_index):
                # Get JSON files in this folder
                json_files = sorted(folder.rglob("*.json"))

                # Determine starting file index (files_completed is 1-indexed count)
                start_file_index = 0
                if folder_idx == state["current_folder_index"]:
                    start_file_index = state["files_completed"]  # Skip already completed files

                for file_idx, json_path in enumerate(json_files[start_file_index:], start=start_file_index):
                    if count >= batch_size:
                        # Save checkpoint before returning
                        state["current_folder"] = folder.name
                        state["current_folder_index"] = folder_idx
                        state["files_completed"] = file_idx  # file_idx is 0-indexed, so this = count of completed
                        self._save_checkpoint(state)
                        files_since_checkpoint = 0
                        logger.info(f"Sanderland: fetched {count} puzzles (batch complete)")
                        return

                    puzzle_id = self._generate_id(json_path)
                    if puzzle_id in self._processed_ids:
                        continue

                    try:
                        raw_data = json.loads(json_path.read_text(encoding="utf-8"))

                        # Validate puzzle using centralized validator (spec 108)
                        puzzle_data = self._to_puzzle_data(raw_data)
                        validation_result = self._validator.validate(puzzle_data)

                        if not validation_result.is_valid:
                            self._processed_ids.add(puzzle_id)
                            state["total_failed"] += 1
                            yield FetchResult.skipped(
                                puzzle_id=puzzle_id,
                                reason=validation_result.rejection_reason,
                            )
                            continue

                        # Convert to SGF only after validation passes
                        sgf_content = self._json_to_sgf(raw_data, json_path, puzzle_id)
                        self._processed_ids.add(puzzle_id)
                        state["total_processed"] += 1
                        count += 1

                        yield FetchResult.success(
                            puzzle_id=puzzle_id,
                            sgf_content=sgf_content,
                            source_link=str(json_path),
                        )

                        # Update checkpoint state in memory after each yield
                        state["current_folder"] = folder.name
                        state["current_folder_index"] = folder_idx
                        state["files_completed"] = file_idx + 1  # 1-indexed: count of files done
                        files_since_checkpoint += 1

                        # Throttle disk writes: save every checkpoint_interval puzzles
                        # to reduce PermissionError risk from Windows file locking
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0

                    except Exception as e:
                        # Extract error type and message without exposing full paths
                        error_type = type(e).__name__
                        # Use only the error message, not args which may contain paths
                        error_msg = str(e).split(":")[-1].strip() if ":" in str(e) else str(e)
                        logger.info(f"Error reading {rel_path(json_path)}: {error_type} - {error_msg}")
                        state["total_failed"] += 1
                        yield FetchResult.failed(
                            puzzle_id=puzzle_id,
                            error=f"{error_type}: {error_msg}",
                        )

                        # Update checkpoint after failure too - advance files_completed so we
                        # don't retry the same failed file on resume, and persist total_failed
                        state["current_folder"] = folder.name
                        state["current_folder_index"] = folder_idx
                        state["files_completed"] = file_idx + 1  # 1-indexed: count of files done
                        files_since_checkpoint += 1

                        # Throttle disk writes on failure path too
                        if files_since_checkpoint >= checkpoint_interval:
                            self._save_checkpoint(state)
                            files_since_checkpoint = 0

            # All folders complete - clear checkpoint
            completed_all = True
            self._clear_checkpoint()
            logger.info(f"Sanderland: fetched {count} puzzles (all complete)")
        finally:
            # Flush pending checkpoint when generator is closed early (consumer breaks)
            if files_since_checkpoint > 0 and not completed_all:
                self._save_checkpoint(state)

    def _json_to_sgf(self, data: dict, path: Path, puzzle_id: str) -> str:
        """Convert sanderland JSON format to SGF.

        JSON format:
            AB: list of black stone coords
            AW: list of white stone coords
            SZ: board size
            C: comment
            SOL: solution tree [[color, coord, comment, next], ...]
        """
        # Spec 128: Enrich with collections in ingest phase using rich path metadata
        # Reconstruct processing steps for logging (always log for verification)
        # Use relative path to exclude system paths from matching/logging
        path_str = rel_path(path)
        combined = f"{path_str} {puzzle_id}"
        norm = normalize(combined)
        tokens = tokenize(norm)

        collections = assign_collections(
            source_link=path_str,
            puzzle_id=puzzle_id,
            existing_collections=[],
            alias_map=self._alias_map,
        )

        ingest_logger.debug(
            f"[Collection Assignment] Input Phrase: '{combined}' | "
            f"Tokens: {tokens} | "
            f"Match Result: {collections if collections else 'None'}"
        )

        # Build SGF
        parts = ["(;FF[4]GM[1]"]

        # Add collections if found
        if collections:
            parts.append(f"YL[{','.join(collections)}]")

        # Board size
        sz = data.get("SZ", "19")
        parts.append(f"SZ[{sz}]")

        # Comment (contains level info like "Black to play: Elementary")
        comment = data.get("C", "")
        if comment:
            parts.append(f"C[{comment}]")

        # Add puzzle name from path
        parts.append(f"GN[{path.stem}]")

        # Black stones (AB)
        ab = data.get("AB", [])
        if ab:
            parts.append("AB" + "".join(f"[{coord}]" for coord in ab))

        # White stones (AW)
        aw = data.get("AW", [])
        if aw:
            parts.append("AW" + "".join(f"[{coord}]" for coord in aw))

        # Determine player to move from comment or solution
        sol = data.get("SOL", [])
        if sol and sol[0]:
            first_move = sol[0]
            if first_move[0] == "B":
                parts.append("PL[B]")
            else:
                parts.append("PL[W]")

        # Build solution tree
        solution_sgf = self._build_solution_tree(sol)
        parts.append(solution_sgf)

        parts.append(")")
        return "".join(parts)

    @staticmethod
    def _is_pass_coord(coord: str) -> bool:
        """Check if a Sanderland coordinate represents a pass move.

        Sanderland uses "zz" to encode pass/tenuki. Empty string is
        also treated as pass for robustness.
        """
        return coord == "zz" or coord == ""

    def _build_solution_tree(self, sol: list) -> str:
        """Build SGF solution tree from sanderland SOL format.

        SOL format: [[color, coord, comment, next_moves], ...]
        where next_moves can be another list of moves.

        Detects miai patterns (same-color consecutive moves) and creates
        SGF variations instead of sequential moves per Spec 117.
        Pass moves ("zz") are converted to SGF-standard empty moves
        with a descriptive comment.

        Examples:
            Sequential: [["B", "aa"], ["W", "bb"]] -> ";B[aa];W[bb]"
            Miai: [["B", "aa"], ["B", "bb"]] -> "(;B[aa])(;B[bb])"
            Pass: [["W", "zz"]] -> ";W[]C[White passes]"
        """
        if not sol:
            return ""

        # Filter valid moves first
        valid_moves = [m for m in sol if m and len(m) >= 2]
        if not valid_moves:
            return ""

        # Detect miai pattern using MoveAlternationDetector
        from backend.puzzle_manager.core.move_alternation import (
            MoveAlternationDetector,
            MoveAlternationResult,
        )

        # Build move tuples for analysis (color, coord)
        move_tuples = [(m[0], m[1]) for m in valid_moves]

        detector = MoveAlternationDetector()
        result_type = detector.analyze(move_tuples)

        if result_type == MoveAlternationResult.MIAI:
            # Create sibling variations for alternative first moves
            variations = []
            for move in valid_moves:
                color = move[0]
                coord = move[1]
                comment = move[2] if len(move) > 2 and move[2] else ""

                if self._is_pass_coord(coord):
                    color_name = "White" if color == "W" else "Black"
                    pass_text = f"{color_name} passes"
                    comment = f"{comment} \u2014 {pass_text}" if comment else pass_text
                    var = f";{color}[]"
                else:
                    var = f";{color}[{coord}]"
                if comment:
                    var += f"C[{comment}]"
                variations.append(f"({var})")
            return "".join(variations)

        # Standard sequential behavior for alternating or single moves
        result = []
        for move in valid_moves:
            color = move[0]
            coord = move[1]
            comment = move[2] if len(move) > 2 else ""

            if self._is_pass_coord(coord):
                color_name = "White" if color == "W" else "Black"
                pass_text = f"{color_name} passes"
                comment = f"{comment} \u2014 {pass_text}" if comment else pass_text
                result.append(f";{color}[]")
            else:
                result.append(f";{color}[{coord}]")
            if comment:
                result.append(f"C[{comment}]")

        return "".join(result)

    def is_available(self) -> bool:
        """Check if sanderland collection exists."""
        return self.source_dir.exists() and any(self.source_dir.rglob("*.json"))

    def _generate_id(self, path: Path) -> str:
        """Generate unique ID from file path."""
        # Use relative path from source dir, cleaned up
        rel_path = path.relative_to(self.source_dir)
        parts = list(rel_path.parts)
        # Remove .json extension from last part
        if parts:
            parts[-1] = parts[-1].replace(".json", "")
        # Clean up special characters
        clean_parts = []
        for part in parts:
            clean = part.replace(" ", "-").replace(".", "")
            clean_parts.append(clean)
        return f"sanderland-{'-'.join(clean_parts)}"
