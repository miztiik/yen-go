"""
Sanderland adapter for importing puzzles from sanderland collection.

Local collection adapter for pre-downloaded JSON puzzle files.
Converts JSON format to SGF.

Features:
- Folder filtering (include_folders, exclude_folders)
- Content-aware skip + resume via SourceIngestDB (per-source SQLite at
  ``<source_dir>/.yengo-ingest.sqlite``); see
  ``docs/architecture/backend/source-ingest-db.md``
"""

import hashlib
import json
import logging
from pathlib import Path

from backend.puzzle_manager.adapters._base import FetchResult
from backend.puzzle_manager.adapters._registry import register_adapter
from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.core.collection_assigner import (
    assign_collections,
    normalize,
    tokenize,
)
from backend.puzzle_manager.core.puzzle_validator import (
    PuzzleData,
    PuzzleValidator,
)
from backend.puzzle_manager.core.source_ingest_db import (
    FileStatus,
    SourceIngestDB,
    migrate_legacy_checkpoint,
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

        # Folder filtering configuration
        self._include_folders: list[str] = []
        self._exclude_folders: list[str] = []

        # Optional override for source.id (set by IngestStage via
        # ``configure({"_source_id": ...})``). When unset, falls back to the
        # default ``"sanderland"`` so per-source ingest DBs stamp ``meta.source_id``
        # consistently with sources.json.
        self._source_id_override: str | None = None

        # Pipeline-injected run_id (set via configure(); IngestStage passes
        # ``context.run_id`` through ``adapter_config['_run_id']``).
        self._run_id: str = "unknown"

        # Centralized puzzle validator
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
        """Unique source identifier.

        Falls back to ``"sanderland"`` if no IngestStage-injected override is set.
        """
        return self._source_id_override or "sanderland"

    def configure(self, config: dict) -> None:
        """Apply adapter-specific configuration.

        Args:
            config: Configuration dictionary with keys:
                - source_dir (str, optional): Path to sanderland collection
                - include_folders (list[str], optional): Folders to include (empty = all)
                - exclude_folders (list[str], optional): Folders to exclude
                - _run_id (str, optional): Pipeline-injected run identifier.
                - resume (bool, optional): Deprecated. Resume is now always-on
                  via SourceIngestDB; use ``--fresh`` to start over.
        """
        if "source_dir" in config:
            self.source_dir = Path(config["source_dir"])

        # Pipeline-injected source.id (private key — adapters never touch sources.json).
        if "_source_id" in config and config["_source_id"]:
            self._source_id_override = str(config["_source_id"])

        # Pipeline-injected run_id (private key — adapters never touch sources.json).
        if "_run_id" in config and config["_run_id"]:
            self._run_id = str(config["_run_id"])

        # Folder filtering
        self._include_folders = config.get("include_folders", [])
        self._exclude_folders = config.get("exclude_folders", [])

        # Log configuration
        folders_to_process = self._get_folders_to_process()
        folder_names = [f.name for f in folders_to_process]
        logger.info(f"Sanderland configured: {len(folder_names)} folders to process")
        if self._include_folders:
            logger.debug(f"Include folders: {self._include_folders}")
        if self._exclude_folders:
            logger.debug(f"Exclude folders: {self._exclude_folders}")

    def supports_resume(self) -> bool:
        """Resume is always-on now via SourceIngestDB."""
        return True

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

        The sanderland collection uses JSON format, not SGF. This adapter
        converts JSON to SGF.

        Uses :class:`SourceIngestDB` (co-located at
        ``<source_dir>/.yengo-ingest.sqlite``) for content-aware skip,
        resume, and rename detection. See
        ``docs/architecture/backend/source-ingest-db.md``.

        Tier-3 skip policy: files are always re-read and re-hashed, then the
        hash is compared against the stored row. If hashes match, downstream
        stages are skipped (no yield, no batch consumption).

        Args:
            batch_size: Maximum NEW puzzles to yield per call. Already-known
                files (skipped via the ingest DB) do not consume batch slots.

        Yields:
            FetchResult for each NEW file (success, skipped, or failed).
        """
        if not self.source_dir.exists():
            logger.warning(f"Sanderland directory not found: {rel_path(self.source_dir)}")
            yield FetchResult.failed(
                puzzle_id="sanderland-init",
                error=f"Directory not found: {rel_path(self.source_dir)}",
            )
            return

        folders = self._get_folders_to_process()
        if not folders:
            logger.info("No folders to process")
            return

        yielded = 0  # NEW puzzles yielded this call (counts toward batch_size)

        # One-shot migration of any legacy AdapterCheckpoint JSON for this source.
        migrate_legacy_checkpoint(
            self.source_dir, source_id=self.source_id, run_id=self._run_id
        )

        ingest_db = SourceIngestDB.open(
            self.source_dir, source_id=self.source_id, run_id=self._run_id
        )
        try:
            for folder in folders:
                json_files = sorted(folder.rglob("*.json"))
                if not json_files:
                    continue

                ingest_db.begin()
                folder_writes = 0
                try:
                    for json_path in json_files:
                        if yielded >= batch_size:
                            ingest_db.commit()
                            logger.info(
                                "Sanderland: yielded %d new puzzles (batch full)",
                                yielded,
                            )
                            return

                        result = self._process_file(
                            json_path=json_path, ingest_db=ingest_db
                        )
                        if result is None:
                            continue
                        folder_writes += 1
                        if result.is_success:
                            yielded += 1
                        yield result

                        if folder_writes >= 100:
                            ingest_db.commit()
                            ingest_db.begin()
                            folder_writes = 0
                finally:
                    ingest_db.commit()

            progress = ingest_db.progress()
            if yielded == 0 and progress.ingested > 0:
                logger.info(
                    "Sanderland: source '%s' is up to date — 0 new files "
                    "(DB: ingested=%d, skipped=%d, failed=%d). "
                    "Use --fresh to reprocess.",
                    self._source_id_override or self.source_id,
                    progress.ingested,
                    progress.skipped,
                    progress.failed,
                )
            else:
                logger.info(
                    "Sanderland: fetched %d (this run), DB totals — ingested=%d skipped=%d failed=%d",
                    yielded,
                    progress.ingested,
                    progress.skipped,
                    progress.failed,
                )
        finally:
            ingest_db.close()

    # ------------------------------------------------------------------ #
    # Per-file processing helpers
    # ------------------------------------------------------------------ #

    def _process_file(
        self, *, json_path: Path, ingest_db: SourceIngestDB
    ) -> FetchResult | None:
        """Read, classify, and (when new) yield one Sanderland JSON file.

        Returns:
            ``None`` when the file is already-known and unchanged (caller
            should skip silently). Otherwise a ``FetchResult`` to yield.
        """
        rel = self._rel_path(json_path)
        try:
            stat = json_path.stat()
            raw_bytes = json_path.read_bytes()
        except OSError as exc:
            return FetchResult.failed(
                puzzle_id=self._generate_id(json_path),
                error=f"File I/O error: {exc}",
            )

        content_hash = hashlib.sha256(raw_bytes).hexdigest()[:16]

        existing = ingest_db.find_by_path(rel)
        if existing is not None and existing.content_hash == content_hash:
            ingest_db.upsert(
                rel_path=rel,
                content_hash=content_hash,
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                status=existing.status,
                skip_reason=existing.skip_reason,
            )
            return None

        if existing is None:
            renamed_from = self._detect_rename(content_hash, rel, ingest_db)
            if renamed_from is not None:
                ingest_db.rename(old_rel_path=renamed_from.rel_path, new_rel_path=rel)
                logger.info(
                    "Detected rename: %s -> %s (hash %s)",
                    renamed_from.rel_path,
                    rel,
                    content_hash,
                )
                return None

        puzzle_id = self._generate_id(json_path)
        try:
            raw_data = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ingest_db.upsert(
                rel_path=rel,
                content_hash=content_hash,
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                status=FileStatus.FAILED,
                skip_reason=f"json_parse_error:{type(exc).__name__}",
            )
            return FetchResult.failed(
                puzzle_id=puzzle_id,
                error=f"{type(exc).__name__}: {exc}",
            )

        try:
            puzzle_data = self._to_puzzle_data(raw_data)
            validation_result = self._validator.validate(puzzle_data)
        except Exception as exc:
            ingest_db.upsert(
                rel_path=rel,
                content_hash=content_hash,
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                status=FileStatus.FAILED,
                skip_reason=f"validation_error:{type(exc).__name__}",
            )
            return FetchResult.failed(
                puzzle_id=puzzle_id,
                error=f"{type(exc).__name__}: {exc}",
            )

        if not validation_result.is_valid:
            ingest_db.upsert(
                rel_path=rel,
                content_hash=content_hash,
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                status=FileStatus.SKIPPED,
                skip_reason=validation_result.rejection_reason or "validation_failed",
            )
            return FetchResult.skipped(
                puzzle_id=puzzle_id,
                reason=validation_result.rejection_reason,
            )

        try:
            sgf_content = self._json_to_sgf(raw_data, json_path, puzzle_id)
        except Exception as exc:
            ingest_db.upsert(
                rel_path=rel,
                content_hash=content_hash,
                size_bytes=stat.st_size,
                mtime_ns=stat.st_mtime_ns,
                status=FileStatus.FAILED,
                skip_reason=f"sgf_conversion_error:{type(exc).__name__}",
            )
            return FetchResult.failed(
                puzzle_id=puzzle_id,
                error=f"{type(exc).__name__}: {exc}",
            )

        ingest_db.upsert(
            rel_path=rel,
            content_hash=content_hash,
            size_bytes=stat.st_size,
            mtime_ns=stat.st_mtime_ns,
            status=FileStatus.INGESTED,
        )
        return FetchResult.success(
            puzzle_id=puzzle_id,
            sgf_content=sgf_content,
            source_link=str(json_path),
        )

    def _detect_rename(
        self, content_hash: str, new_rel_path: str, ingest_db: SourceIngestDB
    ):
        """Return a candidate prior row if this content_hash represents a rename."""
        if not content_hash:
            return None
        candidates = [
            r for r in ingest_db.find_by_hash(content_hash)
            if r.rel_path != new_rel_path
        ]
        if not candidates:
            return None
        for cand in sorted(candidates, key=lambda r: r.run_id, reverse=True):
            old_abs = self.source_dir / cand.rel_path
            if not old_abs.exists():
                return cand
        return None

    def _rel_path(self, file_path: Path) -> str:
        """POSIX path relative to source root, used as DB primary key."""
        try:
            return file_path.relative_to(self.source_dir).as_posix()
        except ValueError:
            return file_path.name

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
