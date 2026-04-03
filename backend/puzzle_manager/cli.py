"""
Command-line interface for puzzle_manager.

Usage:
    python -m backend.puzzle_manager run
    python -m backend.puzzle_manager run --stage ingest
    python -m backend.puzzle_manager ingest blacktoplay --batch-size 5
    python -m backend.puzzle_manager daily --date 2026-01-28
    python -m backend.puzzle_manager status
    python -m backend.puzzle_manager clean
    python -m backend.puzzle_manager validate
    python -m backend.puzzle_manager sources
    python -m backend.puzzle_manager rollback --run-id 20260129-abc12345
    python -m backend.puzzle_manager rollback --puzzle-id puzzle-001 puzzle-002
    python -m backend.puzzle_manager publish-log search --run-id 20260129-abc12345

Source Selection Behavior:
    The pipeline uses `active_adapter` from sources.json as the default source.

    - To use a different source temporarily: --source <id> --source-override
    - To change active adapter permanently: enable-adapter <id>
    - To require explicit --source: disable-adapter

    The --source flag affects ONLY the ingest stage. Analyze and publish
    stages process files from staging, not directly from sources.

Adapter Management:
    python -m backend.puzzle_manager enable-adapter sanderland    # Set default adapter
    python -m backend.puzzle_manager disable-adapter       # Clear default adapter
    python -m backend.puzzle_manager sources               # View current adapter
"""

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from backend.puzzle_manager import __version__
from backend.puzzle_manager.config.loader import ConfigLoader, ConfigWriter
from backend.puzzle_manager.core.datetime_utils import utc_now
from backend.puzzle_manager.core.enrichment import EnrichmentConfig
from backend.puzzle_manager.daily.generator import DailyGenerator
from backend.puzzle_manager.exceptions import PuzzleManagerError
from backend.puzzle_manager.inventory.cli import cmd_inventory
from backend.puzzle_manager.models.enums import RunStatus
from backend.puzzle_manager.models.publish_log import PublishLogEntry
from backend.puzzle_manager.paths import (
    get_output_dir,
    get_publish_log_dir,
    get_runtime_dir,
)
from backend.puzzle_manager.pipeline.cleanup import cleanup_old_files, cleanup_target
from backend.puzzle_manager.pipeline.coordinator import PipelineCoordinator, PipelineResult
from backend.puzzle_manager.pipeline.prerequisites import check_source_availability
from backend.puzzle_manager.pm_logging import setup_logging
from backend.puzzle_manager.publish_log import PublishLogReader
from backend.puzzle_manager.rollback import (
    RollbackError,
    RollbackManager,
)

logger = logging.getLogger("puzzle_manager.cli")


# ---------------------------------------------------------------------------
# Source Validation Helper (DRY compliance)
# ---------------------------------------------------------------------------

def validate_source_selection(
    source: str | None,
    source_override: bool,
    loader: ConfigLoader,
    command_name: str,
    stages: list[str] | None = None,
) -> tuple[str | None, int]:
    """Validate and resolve source selection for pipeline commands.

    Implements the source selection behavior documented in the module docstring:
    - If source is not specified, uses active_adapter from sources.json
    - If source matches active_adapter, proceeds normally
    - If source differs from active_adapter without --source-override, exits with error
    - If source differs with --source-override, logs warning and proceeds
    - If source used with non-ingest stages, logs warning

    Args:
        source: Source ID from CLI argument (may be None)
        source_override: Whether --source-override flag was set
        loader: ConfigLoader instance for reading config
        command_name: Name of command for error messages ("run" or "ingest")
        stages: List of stages being run (for non-ingest warning)

    Returns:
        Tuple of (resolved_source_id, exit_code)
        - If exit_code is 0, resolved_source_id is the source to use
        - If exit_code is non-zero, validation failed and command should exit
    """
    # Get active adapter
    try:
        active_adapter = loader.get_active_adapter()
    except Exception:
        active_adapter = None

    # Validate source selection
    if source:
        # Source was explicitly specified
        if active_adapter and source != active_adapter:
            # Mismatch - require override flag
            if not source_override:
                print(f"[ERROR] --source '{source}' differs from active_adapter '{active_adapter}'")
                print("   To proceed, either:")
                print(f"   1. Add --source-override flag: {command_name} --source {source} --source-override")
                print(f"   2. Change active adapter: enable-adapter {source}")
                return None, 1
            else:
                # Override flag present - log warning and proceed
                msg = f"Source overridden to '{source}' (active_adapter is '{active_adapter}'). --source-override flag present."
                logger.warning(msg)
                print(f"[WARN] {msg}")
        else:
            # Source matches active_adapter (or no active_adapter)
            logger.info(f"Using source '{source}' (matches active_adapter)")

        # Warn if source used with non-ingest stages (only for 'run' command)
        if stages and 'ingest' not in stages:
            non_ingest = [s for s in stages if s != 'ingest']
            msg = f"--source '{source}' only affects 'ingest' stage; ignored for {non_ingest}"
            logger.warning(msg)
            print(f"[WARN] {msg}")

        return source, 0
    else:
        # No source specified - use active_adapter
        if not active_adapter:
            print("[ERROR] No --source specified and no active_adapter configured")
            print("   To proceed, either:")
            if command_name == "ingest":
                print("   1. Specify a source: ingest sanderland")
            else:
                print("   1. Specify a source: run --source sanderland")
            print("   2. Set an active adapter: enable-adapter sanderland")
            return None, 1

        logger.info(f"Using active_adapter: {active_adapter}")
        return active_adapter, 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="puzzle_manager",
        description="Yen-Go puzzle manager - 3-stage pipeline for Go puzzles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s run                    Run full pipeline
  %(prog)s run --stage ingest     Run ingest stage only
  %(prog)s run --dry-run          Preview without changes
  %(prog)s status                 Show pipeline status
  %(prog)s clean                  Clean old files
  %(prog)s validate               Validate configuration
  %(prog)s sources                List configured sources
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (use -vv for debug)",
    )

    parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to config directory",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run command
    run_parser = subparsers.add_parser(
        "run",
        help="Run the pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Source Selection Behavior:
  The --source flag specifies which adapter to use for the INGEST stage only.
  The analyze and publish stages process files from staging, not directly from sources.

  - Without --source: Uses active_adapter from sources.json
  - With --source matching active_adapter: Proceeds normally
  - With --source different from active_adapter: Requires --source-override
  - With --source-override: Logs warning and proceeds

Examples:
  # Run full pipeline with default adapter (active_adapter from sources.json)
  python -m backend.puzzle_manager run

  # Run only ingest stage for specific source
  python -m backend.puzzle_manager run --source sanderland --stage ingest

  # Override active_adapter (with explicit confirmation)
  python -m backend.puzzle_manager run --source kisvadim --source-override

  # Change active adapter permanently
  python -m backend.puzzle_manager enable-adapter kisvadim
  python -m backend.puzzle_manager run
""",
    )
    run_parser.add_argument(
        "--stage",
        type=str,
        choices=["ingest", "analyze", "publish"],
        action="append",
        dest="stages",
        help="Run specific stage(s) only",
    )
    run_parser.add_argument(
        "--batch-size",
        type=int,
        metavar="N",
        help="Override batch size",
    )
    run_parser.add_argument(
        "--drain",
        action="store_true",
        help="Process all pending files (overrides --batch-size)",
    )
    run_parser.add_argument(
        "--flush-interval",
        type=int,
        metavar="N",
        help="Flush batch state every N processed files (default: 500)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    run_parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Skip cleanup of old files after run",
    )
    run_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint if pipeline was interrupted",
    )
    run_parser.add_argument(
        "--source",
        type=str,
        required=False,
        metavar="SOURCE_ID",
        help="Source adapter for ingest stage. If different from active_adapter, requires --source-override",
    )
    run_parser.add_argument(
        "--source-override",
        action="store_true",
        help="Allow --source to override active_adapter. Logs warning when active",
    )
    # Enrichment control flags (per spec 042-sgf-enrichment)
    run_parser.add_argument(
        "--no-enrichment",
        action="store_true",
        help="Disable all enrichment (hints, region, ko, etc.)",
    )
    run_parser.add_argument(
        "--no-hints",
        action="store_true",
        help="Disable hint generation (YH)",
    )
    run_parser.add_argument(
        "--no-region",
        action="store_true",
        help="Disable region detection (YC)",
    )
    run_parser.add_argument(
        "--no-ko",
        action="store_true",
        help="Disable ko context detection (YK)",
    )

    # ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest puzzles from a source",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Source Selection Behavior:
  The source argument specifies which adapter to use for ingestion.

  - Without source: Uses active_adapter from sources.json
  - With source matching active_adapter: Proceeds normally
  - With source different from active_adapter: Requires --source-override
  - With --source-override: Logs warning and proceeds

Examples:
  # Ingest from default adapter (active_adapter from sources.json)
  python -m backend.puzzle_manager ingest

  # Ingest from specific source (must match active_adapter or use override)
  python -m backend.puzzle_manager ingest sanderland

  # Override active_adapter (with explicit confirmation)
  python -m backend.puzzle_manager ingest kisvadim --source-override

  # Change active adapter permanently before ingesting
  python -m backend.puzzle_manager enable-adapter kisvadim
  python -m backend.puzzle_manager ingest
""",
    )
    ingest_parser.add_argument(
        "source",
        type=str,
        nargs="?",
        default=None,
        help="Source ID to ingest from (default: active_adapter from sources.json)",
    )
    ingest_parser.add_argument(
        "--source-override",
        action="store_true",
        help="Allow source to override active_adapter. Logs warning when active",
    )
    ingest_parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        metavar="N",
        help="Maximum puzzles to ingest (default: 100)",
    )
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )

    # daily command
    daily_parser = subparsers.add_parser("daily", help="Generate daily challenges")
    daily_parser.add_argument(
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Generate for specific date (default: today)",
    )
    daily_parser.add_argument(
        "--from",
        dest="from_date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Start date for range generation",
    )
    daily_parser.add_argument(
        "--to",
        dest="to_date",
        type=str,
        metavar="YYYY-MM-DD",
        help="End date for range generation",
    )
    daily_parser.add_argument(
        "--by-tag",
        type=str,
        action="append",
        dest="tags",
        metavar="TAG",
        help="Generate for specific tag(s)",
    )
    daily_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files",
    )
    daily_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        default=False,
        help="Log actions without writing any files",
    )
    daily_parser.add_argument(
        "--rolling-window",
        type=int,
        default=None,
        help="Rolling window size in days (default: 90, from config)",
    )

    # status command
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    status_parser.add_argument(
        "--history",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help="Show last N runs (default: 10)",
    )

    # clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Clean old files and directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cleanup Modes:
  Without --target    RETENTION-BASED: Deletes files older than N days (default: 45)
                      Affects: .pm-runtime/logs/*.log, .pm-runtime/state/runs/*.json
  With --target       COMPLETE CLEANUP: Deletes ALL files in target directory
                      Use with caution - ignores retention days!

Runtime Directory:
  Runtime artifacts are stored in .pm-runtime/ at project root.
  Override with YENGO_RUNTIME_DIR environment variable for CI/custom locations.

Examples:
  %(prog)s                            Retention-based cleanup (files > 45 days old)
  %(prog)s --retention-days 30        Delete files older than 30 days
  %(prog)s --target staging           Delete ALL files in .pm-runtime/staging/
  %(prog)s --target logs              Delete ALL files in .pm-runtime/logs/
  %(prog)s --target logs --dry-run    Preview what would be deleted
  %(prog)s --target puzzles-collection --dry-run false
                                      Delete ALL files in yengo-puzzle-collections/
  %(prog)s --target publish-logs --retention-days 90
                                      Delete publish logs older than 90 days

Targets (for --target):
  staging             Pipeline staging directory (.pm-runtime/staging/) - ALL files deleted
  state               State files (.pm-runtime/state/) - ALL files deleted
  logs                Log files (.pm-runtime/logs/) - ALL files deleted
  puzzles-collection  Published puzzles, search DB, and indexes (yengo-puzzle-collections/) - CAUTION!
  publish-logs        Publish logs (yengo-puzzle-collections/publish-log/) - uses retention days

Safety:
  --target puzzles-collection defaults to dry-run mode for safety.
  You must explicitly pass --dry-run false to delete files.
  --target publish-logs NEVER deletes the audit log (FR-052).
        """,
    )
    clean_parser.add_argument(
        "--target",
        type=str,
        choices=["staging", "state", "logs", "puzzles-collection", "publish-logs"],
        metavar="TARGET",
        help="Target to clean: staging, state, logs, puzzles-collection, publish-logs (default: retention-based cleanup)",
    )
    clean_parser.add_argument(
        "--retention-days",
        type=int,
        default=45,
        metavar="N",
        help="Days to retain files when no target specified (default: 45)",
    )
    clean_parser.add_argument(
        "--dry-run",
        type=str,
        nargs="?",
        const="true",
        default=None,
        metavar="BOOL",
        help="Preview changes without deleting. For puzzles-collection, defaults to true (must pass 'false' to delete)",
    )

    # validate command
    subparsers.add_parser("validate", help="Validate configuration")

    # inventory command
    inventory_parser = subparsers.add_parser(
        "inventory",
        help="View puzzle collection inventory statistics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Display aggregate statistics for the published puzzle collection including:
- Total puzzle count and breakdowns by level/tag
- Stage-level metrics (ingest/analyze/publish)
- Computed error rates and daily throughput
- Rollback audit trail

Examples:
  %(prog)s                  Show human-readable summary
  %(prog)s --json           Output raw JSON
  %(prog)s --rebuild        Rebuild inventory from publish logs
  %(prog)s --reconcile      Reconcile inventory from SGF files on disk
  %(prog)s --check          Check inventory integrity
  %(prog)s --fix            Fix inventory by rebuilding
  %(prog)s -v               Verbose output

File Locations:
  Inventory: yengo-puzzle-collections/puzzle-collection-inventory.json
  Schema:    config/schemas/puzzle-collection-inventory-schema.json
        """,
    )
    inventory_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    inventory_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild inventory from publish logs",
    )
    inventory_parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Reconcile inventory by scanning SGF files on disk (most accurate)",
    )
    inventory_parser.add_argument(
        "--check",
        action="store_true",
        help="Check inventory integrity (detect discrepancies)",
    )
    inventory_parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix inventory by rebuilding from publish logs",
    )

    # sources command
    sources_parser = subparsers.add_parser("sources", help="List configured sources")
    sources_parser.add_argument(
        "--check",
        action="store_true",
        help="Check source availability",
    )
    sources_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # enable-adapter command
    enable_adapter_parser = subparsers.add_parser(
        "enable-adapter",
        help="Set the active adapter for pipeline operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sets the active adapter in sources.json. This adapter will be used by default
when running pipeline commands without the --source flag.

Examples:
  %(prog)s ogs           Set OGS as the active adapter
  %(prog)s sanderland    Set Sanderland as the active adapter
  %(prog)s goproblems    Set GoProblems as the active adapter

After setting, verify with:
  puzzle_manager sources   Show current active adapter
        """,
    )
    enable_adapter_parser.add_argument(
        "adapter_id",
        type=str,
        metavar="ADAPTER_ID",
        help="The adapter ID to enable (e.g., 'ogs', 'sanderland', 'goproblems')",
    )
    enable_adapter_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Override lock if a pipeline is running",
    )

    # disable-adapter command
    disable_adapter_parser = subparsers.add_parser(
        "disable-adapter",
        help="Disable the active adapter (require --source for operations)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Clears the active adapter in sources.json. After disabling, you must specify
--source explicitly for pipeline operations.

Example:
  %(prog)s                  Disable the active adapter
  puzzle_manager run --source ogs   Now requires explicit --source
        """,
    )
    disable_adapter_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Override lock if a pipeline is running",
    )

    # vacuum-db command
    vacuum_parser = subparsers.add_parser(
        "vacuum-db",
        help="Clean orphaned entries from content DB and optionally rebuild search DB",
        description="""\
Maintenance Operations:
  Default          Remove orphaned entries from yengo-content.db
  --rebuild        Also rebuild yengo-search.db from disk

Examples:
  %(prog)s                   Clean orphans only
  %(prog)s --rebuild         Clean orphans + rebuild search DB
  %(prog)s --dry-run         Preview what would be cleaned
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    vacuum_parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Also rebuild yengo-search.db from disk after vacuum",
    )
    vacuum_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes",
    )

    # rollback command
    rollback_parser = subparsers.add_parser(
        "rollback",
        help="Rollback published puzzles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Rollback Modes:
  --run-id ID        Rollback all puzzles from a specific pipeline run
  --puzzle-id ID...  Rollback specific puzzle(s) by ID

Options:
  --dry-run          Preview what would be rolled back without making changes
  --yes              Skip confirmation prompt for large rollbacks
  --reason TEXT      Required reason for the rollback (audit trail)

Examples:
  %(prog)s --run-id 20260129-abc12345           Roll back all puzzles from run
  %(prog)s --run-id 20260129-abc12345 --dry-run Preview rollback
  %(prog)s --puzzle-id puzzle-001 puzzle-002    Roll back specific puzzles
  %(prog)s --run-id a1b2c3d4e5f6 --yes          Legacy format also supported

Run ID Formats:
  New format: YYYYMMDD-xxxxxxxx (e.g., 20260129-abc12345)
  Legacy format: 12-char hex (e.g., a1b2c3d4e5f6) - for backward compatibility

Safety:
  Rollbacks > 10 puzzles require confirmation (use --yes to skip)
  Rollbacks > 100 puzzles are blocked (safety limit)
  Daily tables are regenerated after rollback (post-step)
        """,
    )
    rollback_group = rollback_parser.add_mutually_exclusive_group(required=True)
    rollback_group.add_argument(
        "--run-id",
        type=str,
        metavar="ID",
        help="Rollback all puzzles from a pipeline run (YYYYMMDD-xxxxxxxx or legacy 12-char hex)",
    )
    rollback_group.add_argument(
        "--puzzle-id",
        type=str,
        nargs="+",
        metavar="ID",
        help="Rollback specific puzzle(s) by ID",
    )
    rollback_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without deleting files",
    )
    rollback_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt for large rollbacks",
    )
    rollback_parser.add_argument(
        "--reason",
        type=str,
        metavar="TEXT",
        help="Reason for rollback (required for audit trail)",
    )
    rollback_parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify file counts after rollback (T037)",
    )

    # publish-log command
    publog_parser = subparsers.add_parser(
        "publish-log",
        help="Search and manage publish logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Search Modes:
  search --run-id ID        Find all puzzles from a run
  search --puzzle-id ID     Find entries for a puzzle
  search --source NAME      Find puzzles by source
  search --trace-id ID      Find entry by trace ID
  search --date YYYY-MM-DD  Find puzzles published on date
  search --from/--to        Find puzzles in date range

Examples:
  %(prog)s search --run-id abc123def456
  %(prog)s search --source blacktoplay
  %(prog)s search --trace-id a1b2c3d4e5f67890
  %(prog)s search --date 2025-01-15
  %(prog)s search --from 2025-01-01 --to 2025-01-31
        """,
    )
    publog_subparsers = publog_parser.add_subparsers(dest="publog_command")

    # publish-log list (T040)
    publog_list = publog_subparsers.add_parser("list", help="List available publish log dates")
    publog_list.add_argument(
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Show entries for specific date",
    )
    publog_list.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Maximum dates to show (default: 10)",
    )

    # publish-log search (T041)
    publog_search = publog_subparsers.add_parser("search", help="Search publish logs")
    publog_search.add_argument(
        "--run-id",
        type=str,
        metavar="ID",
        help="Search by run ID",
    )
    publog_search.add_argument(
        "--puzzle-id",
        type=str,
        metavar="ID",
        help="Search by puzzle ID",
    )
    publog_search.add_argument(
        "--source",
        type=str,
        metavar="NAME",
        help="Search by source name",
    )
    publog_search.add_argument(
        "--trace-id",
        type=str,
        metavar="ID",
        help="Search by trace ID",
    )
    publog_search.add_argument(
        "--date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Search by publish date",
    )
    publog_search.add_argument(
        "--from",
        dest="from_date",
        type=str,
        metavar="YYYY-MM-DD",
        help="Start date for range search",
    )
    publog_search.add_argument(
        "--to",
        dest="to_date",
        type=str,
        metavar="YYYY-MM-DD",
        help="End date for range search",
    )
    publog_search.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    publog_search.add_argument(
        "--format",
        type=str,
        choices=["table", "json", "jsonl"],
        default="table",
        metavar="FORMAT",
        help="Output format: table, json, jsonl (default: table)",
    )
    publog_search.add_argument(
        "--limit",
        type=int,
        default=50,
        metavar="N",
        help="Maximum results to show (default: 50)",
    )

    # config-lock command (for managing pipeline config lock)
    config_lock_parser = subparsers.add_parser(
        "config-lock",
        help="Manage config lock for pipeline execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The pipeline automatically locks config while running to prevent modifications.
Use this command to check lock status or release a stuck lock.

Subcommands:
  status    Show current lock status
  release   Release the lock (use --force if held by another process)

Examples:
  %(prog)s status             Check if config is locked
  %(prog)s release            Release lock (same process only)
  %(prog)s release --force    Force release (use with caution)
        """,
    )
    config_lock_subparsers = config_lock_parser.add_subparsers(dest="lock_action", help="Lock actions")

    # config-lock status
    config_lock_status = config_lock_subparsers.add_parser("status", help="Show config lock status")
    config_lock_status.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    # config-lock release
    config_lock_release = config_lock_subparsers.add_parser("release", help="Release config lock")
    config_lock_release.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force release even if lock is held by another process",
    )

    return parser


def _format_stage_counts(result: "PipelineResult") -> str:
    """Format per-stage processed counts for display.

    Returns empty string for single-stage runs, parenthesized breakdown for multi-stage.
    Example: " (analyze: 57, publish: 57)"
    """
    if len(result.stages) <= 1:
        return ""
    parts = [f"{name}: {s.processed}" for name, s in result.stages.items()]
    return f" ({', '.join(parts)})"


def _ensure_console_info_level() -> None:
    """Ensure console handler shows INFO-level messages for real-time progress.

    The run command always needs streaming progress output visible.
    This upgrades the console handler level to INFO if it's currently
    at WARNING (the default when -v is not specified).

    Applies to both the main puzzle_manager logger and stage loggers
    (ingest, analyze, publish) which have their own console handlers.
    """
    logger_names = ["puzzle_manager", "ingest", "analyze", "publish"]
    for name in logger_names:
        target_logger = logging.getLogger(name)
        for handler in target_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                if handler.level > logging.INFO:
                    handler.setLevel(logging.INFO)


def cmd_run(args: argparse.Namespace) -> int:
    """Execute the run command.

    Source selection is handled by validate_source_selection() helper.
    Always enables INFO-level console output for real-time progress visibility.
    """
    # Ensure run command always shows progress (INFO level minimum)
    # Users see streaming progress without needing -v flag
    _ensure_console_info_level()

    try:
        loader = ConfigLoader(args.config)
        source = getattr(args, 'source', None)
        source_override = getattr(args, 'source_override', False)
        stages = getattr(args, 'stages', None)

        # Validate and resolve source selection (DRY: shared helper)
        resolved_source, exit_code = validate_source_selection(
            source=source,
            source_override=source_override,
            loader=loader,
            command_name="run",
            stages=stages,
        )
        if exit_code != 0:
            return exit_code
        source = resolved_source

        # Build enrichment config from CLI flags
        enrichment_config = None
        if not getattr(args, 'no_enrichment', False):
            enrichment_config = EnrichmentConfig(
                enable_hints=not getattr(args, 'no_hints', False),
                enable_region=not getattr(args, 'no_region', False),
                enable_ko=not getattr(args, 'no_ko', False),
                enable_move_order=True,  # No CLI flag for this yet
                enable_refutation=True,  # No CLI flag for this yet
                include_liberty_analysis=True,
                include_technique_reasoning=True,
                include_consequence=True,
                verbose=getattr(args, 'verbose', 0) > 1,
            )

        # Resolve --drain: overrides batch_size with effectively unlimited
        effective_batch_size = args.batch_size
        if getattr(args, 'drain', False):
            effective_batch_size = 10_000_000  # Effectively unlimited

        coordinator = PipelineCoordinator(
            config_path=args.config,
            dry_run=args.dry_run,
            batch_size=effective_batch_size,
            source_id=source,  # Use resolved source (from --source or active_adapter)
            enrichment_config=enrichment_config,
            flush_interval=getattr(args, 'flush_interval', None),
        )

        result = coordinator.run(
            stages=args.stages,
            skip_cleanup=args.skip_cleanup,
            resume=args.resume,
        )

        # Build output message
        source_msg = f" for '{source}'"
        stage_detail = _format_stage_counts(result)

        if result.success:
            print(f"[OK] Pipeline completed successfully{source_msg}")
            print(f"  Processed: {result.total_processed}{stage_detail}")
            # Show remaining files if any
            total_remaining = result.total_remaining
            if total_remaining > 0:
                print(f"  Remaining: {total_remaining} in staging")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            return 0
        else:
            print(f"[FAIL] Pipeline failed{source_msg}")
            print(f"  Processed: {result.total_processed}{stage_detail}")
            print(f"  Failed: {result.total_failed}")
            # Show remaining files if any
            total_remaining = result.total_remaining
            if total_remaining > 0:
                print(f"  Remaining: {total_remaining} in staging")
            for error in result.errors[:5]:
                print(f"  Error: {error}")
            return 1

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Execute the status command."""
    try:
        coordinator = PipelineCoordinator(
            config_path=args.config,
        )
        status = coordinator.get_status()

        # Check for history flag
        if args.history:
            history = coordinator.state_manager.get_history(limit=args.history)
            if args.json:
                result = {
                    **status,
                    "history": [r.model_dump(mode="json") for r in history],
                }
                print(json.dumps(result, indent=2, default=str))
            else:
                _print_status(status)
                _print_history(history)
            return 0

        if args.json:
            print(json.dumps(status, indent=2, default=str))
        else:
            _print_status(status)

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def _print_history(history: list) -> None:
    """Pretty print run history."""
    if not history:
        print("\nNo run history")
        return

    print("\nRun History")
    print("-" * 60)
    for run in history:
        if run.status == RunStatus.COMPLETED:
            status_icon = "[OK]"
        elif run.status == RunStatus.FAILED:
            status_icon = "[FAIL]"
        else:
            status_icon = "[...]"
        processed = run.get_total_processed()
        print(f"  {status_icon} {run.run_id} | {run.started_at.strftime('%Y-%m-%d %H:%M')} | {processed} processed")


def _print_status(status: dict) -> None:
    """Pretty print pipeline status."""
    print("Pipeline Status")
    print("=" * 40)

    # Show runtime directory location
    runtime_dir = get_runtime_dir()
    print(f"\nRuntime Directory: {runtime_dir}")

    if status["current_run"]:
        run = status["current_run"]
        print(f"\nCurrent Run: {run.get('run_id', 'N/A')}")
        print(f"  Status: {run.get('status', 'N/A')}")
        print(f"  Started: {run.get('started_at', 'N/A')}")
    else:
        print("\nNo current run")

    if status["last_run"]:
        run = status["last_run"]
        print(f"\nLast Run: {run.get('run_id', 'N/A')}")
        print(f"  Status: {run.get('status', 'N/A')}")
        print(f"  Processed: {run.get('processed', 0)}")
        print(f"  Completed: {run.get('completed_at', 'N/A')}")

    print(f"\nTotal Runs: {status['runs_total']}")
    print(f"Available Stages: {', '.join(status['available_stages'])}")


def cmd_ingest(args: argparse.Namespace) -> int:
    """Execute the ingest command.

    Source selection is handled by validate_source_selection() helper.
    """
    try:
        # Validate source exists
        loader = ConfigLoader(args.config)
        sources = loader.load_sources()
        source_ids = {s.id for s in sources}

        # Get source and override flag
        source = args.source
        source_override = getattr(args, 'source_override', False)

        # Validate and resolve source selection (DRY: shared helper)
        resolved_source, exit_code = validate_source_selection(
            source=source,
            source_override=source_override,
            loader=loader,
            command_name="ingest",
            stages=None,  # ingest doesn't have stages concept
        )
        if exit_code != 0:
            return exit_code
        source_id = resolved_source

        # Print message if using active adapter
        if source is None:
            print(f"Using active adapter: {source_id}")

        if source_id not in source_ids:
            print(f"Error: Unknown source '{source_id}'")
            print("\nAvailable sources:")
            for s in sources:
                print(f"  - {s.id} ({s.name})")
            return 1

        # Run ingest for this source
        # Note: PipelineCoordinator handles adapter resolution via source config
        coordinator = PipelineCoordinator(
            config_path=args.config,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
            source_id=source_id,  # Filter to specific source
        )

        result = coordinator.run(
            stages=["ingest"],
            skip_cleanup=True,
        )

        if result.success:
            stage_detail = _format_stage_counts(result)
            print(f"[OK] Ingest completed for '{source_id}'")
            print(f"  Processed: {result.total_processed}{stage_detail}")
            return 0
        else:
            print(f"[FAIL] Ingest failed for '{source_id}'")
            for error in result.errors[:5]:
                print(f"  Error: {error}")
            return 1

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_daily(args: argparse.Namespace) -> int:
    """Execute the daily command."""
    try:
        # Parse dates
        if args.date:
            try:
                start_date = datetime.strptime(args.date, "%Y-%m-%d")
                end_date = start_date
            except ValueError:
                print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
                return 1
        elif args.from_date:
            try:
                start_date = datetime.strptime(args.from_date, "%Y-%m-%d")
                if args.to_date:
                    end_date = datetime.strptime(args.to_date, "%Y-%m-%d")
                else:
                    end_date = start_date
            except ValueError as e:
                print(f"Error: Invalid date format. Use YYYY-MM-DD. {e}")
                return 1
        else:
            # Default to today
            start_date = utc_now()
            end_date = start_date

        db_path = get_output_dir() / "yengo-search.db"
        generator = DailyGenerator(db_path=db_path, dry_run=args.dry_run)

        # Generate for date range
        result = generator.generate(
            start_date=start_date,
            end_date=end_date,
            force=args.force,
        )

        # Persist to DB (generator no longer writes on its own)
        if result.challenges and not args.dry_run:
            from backend.puzzle_manager.daily.db_writer import inject_daily_schedule
            inject_daily_schedule(db_path, result.challenges)

        if result.failures:
            print(f"[WARN] {len(result.failures)} date(s) failed during generation")

        print(f"[OK] Generated {len(result.challenges)} daily challenge(s)")
        for r in result.challenges:
            print(f"  - {r.date}")

        # Prune expired daily schedules
        if result.challenges and not args.dry_run:
            from backend.puzzle_manager.daily.db_writer import prune_daily_window
            rolling_window = getattr(args, 'rolling_window', None) or generator.config.rolling_window_days
            pruned = prune_daily_window(db_path, rolling_window)
            if pruned > 0:
                print(f"[OK] Pruned {pruned} expired daily schedule(s)")

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def _parse_dry_run_flag(dry_run_arg: str | None, target: str | None) -> bool:
    """Parse the --dry-run flag value.

    Args:
        dry_run_arg: Raw value from argparse (None, or string like "true"/"false")
        target: The cleanup target (affects default behavior)

    Returns:
        True if dry-run mode should be enabled, False otherwise.
        Default: True for 'puzzles-collection' (safety), False for others.
    """
    if dry_run_arg is None:
        # No --dry-run specified: safe default for destructive targets
        return target == "puzzles-collection"
    # Explicit value provided: parse as boolean
    return dry_run_arg.lower() not in ("false", "no", "0")


def cmd_clean(args: argparse.Namespace) -> int:
    """Execute the clean command."""
    try:
        dry_run = _parse_dry_run_flag(args.dry_run, args.target)

        # For puzzles-collection dry-run, show helpful message about how to actually delete
        if args.target == "puzzles-collection" and dry_run:
            print("🔍 DRY-RUN: Previewing what would be deleted from yengo-puzzle-collections/")
            print("   To actually delete, run: --target puzzles-collection --dry-run false\n")

        # Check if specific target requested
        if args.target:
            # Handle publish-logs target specially (T046)
            if args.target == "publish-logs":
                reader = PublishLogReader(log_dir=get_publish_log_dir())
                counts = reader.cleanup_old_logs(
                    retention_days=args.retention_days,
                    dry_run=dry_run,
                )
                action = "Would delete" if dry_run else "Deleted"
                print(f"{action} publish-logs:")
                print(f"  Log files: {counts['deleted']} files")
                print(f"  Preserved: {counts['preserved']} files")
                if counts['skipped_audit'] > 0:
                    print("  Audit log: preserved (never deleted)")
            else:
                counts = cleanup_target(
                    target=args.target,
                    dry_run=dry_run,
                )
                action = "Would clean" if dry_run else "Cleaned"
                total = sum(counts.values())
                print(f"{action} {args.target}: {total} files")
                # Show per-category breakdown for puzzles-collection
                if args.target == "puzzles-collection" and total > 0:
                    for cat, n in counts.items():
                        if n > 0:
                            print(f"  {cat}: {n}")
        else:
            # Retention-based cleanup (default)
            counts = cleanup_old_files(
                retention_days=args.retention_days,
                dry_run=dry_run,
            )
            action = "Would delete" if dry_run else "Deleted"
            print(f"{action}:")
            print(f"  Logs: {counts['logs']} files")
            print(f"  State: {counts['state']} files")
            print(f"  Failed: {counts['failed']} files")

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_vacuum_db(args: argparse.Namespace) -> int:
    """Execute the vacuum-db command."""
    from backend.puzzle_manager.core.content_db import vacuum_orphans
    from backend.puzzle_manager.inventory.reconcile import rebuild_search_db_from_disk
    from backend.puzzle_manager.paths import get_output_dir

    try:
        output_dir = get_output_dir()
        sgf_dir = output_dir / "sgf"
        content_db_path = output_dir / "yengo-content.db"
        has_content_db = content_db_path.exists()

        if not has_content_db and not args.rebuild:
            print("Content database not found — nothing to vacuum.")
            return 0

        # Collect published hashes from disk
        published_hashes: set[str] = set()
        if sgf_dir.exists():
            for sgf_path in sgf_dir.rglob("*.sgf"):
                published_hashes.add(sgf_path.stem)

        print(f"Found {len(published_hashes)} published SGF files on disk.")

        if args.dry_run:
            if has_content_db:
                # Count orphans without deleting
                import sqlite3

                conn = sqlite3.connect(
                    f"file:{content_db_path}?mode=ro", uri=True
                )
                try:
                    all_hashes = {
                        r[0]
                        for r in conn.execute(
                            "SELECT content_hash FROM sgf_files"
                        ).fetchall()
                    }
                    orphan_count = len(all_hashes - published_hashes)
                    print(
                        f"Would remove {orphan_count} orphaned entries"
                        " from content DB."
                    )
                finally:
                    conn.close()
            if args.rebuild:
                print(
                    f"Would rebuild search DB from"
                    f" {len(published_hashes)} SGF files."
                )
            return 0

        if has_content_db:
            removed = vacuum_orphans(content_db_path, published_hashes)
            print(f"Removed {removed} orphaned entries from content DB.")

        if args.rebuild:
            count = rebuild_search_db_from_disk(output_dir)
            print(f"Search DB rebuilt: {count} puzzles indexed.")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Execute the validate command."""
    try:
        loader = ConfigLoader(args.config)

        # Try to load all configs
        errors = []

        try:
            loader.load_pipeline_config()
            print("[OK] Pipeline config valid")
        except Exception as e:
            errors.append(f"Pipeline config: {e}")
            print(f"[FAIL] Pipeline config: {e}")

        try:
            loader.load_tags()
            print("[OK] Tags config valid")
        except Exception as e:
            errors.append(f"Tags config: {e}")
            print(f"[FAIL] Tags config: {e}")

        try:
            loader.load_levels()
            print("[OK] Levels config valid")
        except Exception as e:
            errors.append(f"Levels config: {e}")
            print(f"[FAIL] Levels config: {e}")

        try:
            sources = loader.load_sources()
            print(f"[OK] Sources config valid ({len(sources)} sources)")
        except Exception as e:
            errors.append(f"Sources config: {e}")
            print(f"[FAIL] Sources config: {e}")

        return 0 if not errors else 1

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_sources(args: argparse.Namespace) -> int:
    """Execute the sources command."""
    try:
        loader = ConfigLoader(args.config)
        sources = loader.load_sources()

        # Get active adapter (spec-051)
        try:
            active_adapter_id = loader.get_active_adapter()
        except Exception:
            active_adapter_id = None

        if args.check:
            availability = check_source_availability()

            if args.json:
                result = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "adapter": s.adapter,
                        "active": s.id == active_adapter_id,
                        "available": availability.get(s.id, False),
                    }
                    for s in sources
                ]
                print(json.dumps(result, indent=2))
            else:
                print("Configured Sources")
                if active_adapter_id:
                    print(f"Active adapter: {active_adapter_id}")
                print("=" * 60)
                for source in sources:
                    status = "[OK]" if availability.get(source.id, False) else "[FAIL]"
                    active = " [ACTIVE]" if source.id == active_adapter_id else ""
                    print(f"  {status} {source.name} ({source.adapter}){active}")
        else:
            if args.json:
                result = [
                    {
                        **s.model_dump(),
                        "active": s.id == active_adapter_id,
                    }
                    for s in sources
                ]
                print(json.dumps(result, indent=2, default=str))
            else:
                print("Configured Sources")
                if active_adapter_id:
                    print(f"Active adapter: {active_adapter_id}")
                print("=" * 60)
                for source in sources:
                    active = " [ACTIVE]" if source.id == active_adapter_id else ""
                    print(f"  {source.name} ({source.adapter}){active}")

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_enable_adapter(args: argparse.Namespace) -> int:
    """Execute the enable-adapter command.

    Sets the active adapter in sources.json to the specified adapter ID.
    Uses ConfigWriter for mutation operations (SRP compliance).
    """
    try:
        loader = ConfigLoader(args.config)
        writer = ConfigWriter(args.config)

        # Validate adapter exists
        available_sources = loader.get_available_sources()
        if args.adapter_id not in available_sources:
            print(f"[ERROR] Adapter '{args.adapter_id}' not found")
            print(f"   Available adapters: {', '.join(available_sources)}")
            return 1

        # Set the active adapter (use writer, not loader)
        writer.set_active_adapter(args.adapter_id, force=getattr(args, 'force', False))
        print(f"[OK] Active adapter set to: {args.adapter_id}")

        # Show helpful next steps
        print()
        print("Next steps:")
        print(f"  puzzle_manager run                Run pipeline with '{args.adapter_id}'")
        print("  puzzle_manager sources            Verify active adapter")

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_disable_adapter(args: argparse.Namespace) -> int:
    """Execute the disable-adapter command.

    Clears the active adapter in sources.json. After disabling, the --source
    flag must be specified explicitly for pipeline operations.
    Uses ConfigWriter for mutation operations (SRP compliance).
    """
    try:
        loader = ConfigLoader(args.config)
        writer = ConfigWriter(args.config)

        # Get current active adapter for feedback
        try:
            current = loader.get_active_adapter()
        except Exception:
            current = None

        if not current:
            print("[WARN] No active adapter is currently set")
            return 0

        # Clear the active adapter (use writer, not loader)
        writer.set_active_adapter(None, force=getattr(args, 'force', False))
        print(f"[OK] Active adapter disabled (was: {current})")

        # Show helpful next steps
        print()
        print("Next steps:")
        print("  When running pipeline commands, you must now specify --source:")
        print("    puzzle_manager run --source ogs")
        print("    puzzle_manager ingest ogs")

        return 0

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_config_lock(args: argparse.Namespace) -> int:
    """Execute the config-lock command.

    Manages the pipeline lock used during pipeline/rollback execution.
    """
    import json as json_module

    from backend.puzzle_manager.pipeline.lock import PipelineLock, PipelineLockError

    action = getattr(args, 'lock_action', None)

    if action == "status":
        lock_info = PipelineLock.get_lock_info()
        if lock_info:
            if getattr(args, 'json', False):
                print(json_module.dumps({"locked": True, **lock_info}, indent=2))
            else:
                print("[LOCKED] Pipeline is locked")
                print(f"  Run ID:      {lock_info.get('run_id', 'unknown')}")
                print(f"  Acquired at: {lock_info.get('acquired_at', 'unknown')}")
                print(f"  Process:     PID {lock_info.get('pid', 'unknown')}")
                print(f"  Host:        {lock_info.get('hostname', 'unknown')}")
                print()
                print("To release: puzzle_manager config-lock release --force")
            return 0
        else:
            if getattr(args, 'json', False):
                print(json_module.dumps({"locked": False}, indent=2))
            else:
                print("[UNLOCKED] Pipeline is not locked")
            return 0

    elif action == "release":
        getattr(args, 'force', False)
        try:
            if PipelineLock.force_release():
                print("[OK] Pipeline lock released")
            else:
                print("[INFO] No lock to release")
            return 0
        except PipelineLockError as e:
            print(f"[ERROR] {e}")
            return 1

    else:
        print("Usage: puzzle_manager config-lock {status|release}")
        print("  status   Show current lock status")
        print("  release  Release the lock (use --force if needed)")
        return 1


def _verify_rollback(
    output_dir: Path,
    target: str | list[str],
    expected_deleted: int,
    log_reader: PublishLogReader,
) -> list[str]:
    """Verify rollback was successful (T037).

    Args:
        output_dir: Output directory root
        target: Run ID or list of puzzle IDs that were rolled back
        expected_deleted: Number of files expected to be deleted
        log_reader: Publish log reader instance

    Returns:
        List of verification errors (empty if all passed)
    """
    errors = []

    # Get entries for target
    if isinstance(target, str):
        entries = list(log_reader.search_by_run_id(target))
    else:
        entries = []
        for pid in target:
            entries.extend(log_reader.search_by_puzzle_id(pid))

    # Verify files are actually deleted
    still_exist = []
    for entry in entries:
        file_path = output_dir / entry.path
        if file_path.exists():
            still_exist.append(entry.path)

    if still_exist:
        errors.append(f"{len(still_exist)} files still exist after rollback")
        for path in still_exist[:5]:  # Show first 5
            errors.append(f"  Still exists: {path}")
        if len(still_exist) > 5:
            errors.append(f"  ... and {len(still_exist) - 5} more")

    return errors


def cmd_rollback(args: argparse.Namespace) -> int:
    """Execute the rollback command (rebuild-centric v12)."""
    try:
        output_dir = get_output_dir()
        log_dir = get_publish_log_dir()
        log_reader = PublishLogReader(log_dir=log_dir)

        manager = RollbackManager(
            output_dir=output_dir,
            log_reader=log_reader,
        )

        # Execute rollback by run_id
        if not args.run_id:
            print("Error: --run-id is required for rollback")
            return 1

        result = manager.rollback_by_run(
            run_id=args.run_id,
            dry_run=args.dry_run,
        )

        # Print result
        if args.dry_run:
            print("[DRY-RUN] Preview of rollback operation")
            print(f"   Puzzles affected: {result.puzzles_affected}")
            if result.errors:
                for error in result.errors:
                    print(f"   Note: {error}")
            if result.puzzles_affected > 0:
                print("\n   Run without --dry-run to execute")
        else:
            if result.success:
                print("[OK] Rollback completed successfully")
                print(f"  Puzzles rolled back: {result.puzzles_affected}")
                print(f"  Files deleted: {result.files_deleted}")
                print(f"  Indexes rebuilt: {result.indexes_updated}")
            else:
                print("[FAIL] Rollback failed")
                for error in result.errors:
                    print(f"  Error: {error}")
                return 1

        return 0

    except RollbackError as e:
        print(f"[FAIL] Rollback error: {e}")
        return 1

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def cmd_publish_log(args: argparse.Namespace) -> int:
    """Execute the publish-log command (T039-T043)."""
    try:
        log_dir = get_publish_log_dir()
        reader = PublishLogReader(log_dir=log_dir)

        if args.publog_command == "list":
            return _cmd_publish_log_list(args, reader)
        elif args.publog_command == "search":
            return _cmd_publish_log_search(args, reader)
        else:
            print("Usage: publish-log [list|search] [options]")
            print("  list             - List available publish log dates")
            print("  search           - Search publish logs by criteria")
            return 1

    except PuzzleManagerError as e:
        print(f"Error: {e}")
        return 1


def _cmd_publish_log_list(args: argparse.Namespace, reader: PublishLogReader) -> int:
    """Handle publish-log list subcommand (T040)."""
    if args.date:
        # Show entries for specific date (read_date takes string YYYY-MM-DD)
        try:
            # Validate date format
            datetime.strptime(args.date, "%Y-%m-%d")
            entries = list(reader.read_date(args.date))
            if not entries:
                print(f"No entries for {args.date}")
                return 0
            print(f"Entries for {args.date}: {len(entries)}")
            for entry in entries[:args.limit]:
                print(f"  {entry.puzzle_id} ({entry.source_id})")
            if len(entries) > args.limit:
                print(f"  ... and {len(entries) - args.limit} more")
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            return 1
    else:
        # List available dates
        dates = reader.list_dates()
        if not dates:
            print("No publish logs found")
            return 0

        sorted_dates = sorted(dates, reverse=True)
        display_dates = sorted_dates[:args.limit]

        print(f"Publish log dates ({len(dates)} total):")
        for d in display_dates:
            # Count entries for each date (read_date takes string YYYY-MM-DD)
            try:
                count = len(list(reader.read_date(d)))
                print(f"  {d} ({count} entries)")
            except Exception:
                print(f"  {d}")

        if len(dates) > args.limit:
            print(f"  ... showing {args.limit} of {len(dates)} dates")

    return 0


def _cmd_publish_log_search(args: argparse.Namespace, reader: PublishLogReader) -> int:
    """Handle publish-log search subcommand (T041, T042)."""
    entries: list[PublishLogEntry] = []
    limit = args.limit

    # Determine output format (--format takes precedence over --json)
    output_format = args.format if hasattr(args, 'format') else "table"
    if args.json:
        output_format = "json"

    if args.run_id:
        entries = list(reader.search_by_run_id(args.run_id))
    elif args.puzzle_id:
        # search_by_puzzle_id returns single entry or None
        entry = reader.search_by_puzzle_id(args.puzzle_id)
        entries = [entry] if entry else []
    elif args.source:
        entries = list(reader.search_by_source(args.source))
    elif args.trace_id:
        entry = reader.find_by_trace_id(args.trace_id)
        entries = [entry] if entry else []
    elif args.date:
        try:
            entries = list(reader.read_date(args.date))
        except ValueError:
            print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
            return 1
    elif args.from_date:
        try:
            from_date = args.from_date
            to_date = args.to_date if args.to_date else utc_now().strftime("%Y-%m-%d")
            entries = reader.search_by_date_range(from_date, to_date)
        except ValueError as e:
            print(f"Error: Invalid date format. Use YYYY-MM-DD. {e}")
            return 1
    else:
        # Show help hint
        print("Use one of: --run-id, --puzzle-id, --source, --trace-id, --date, --from/--to")
        print("Or use 'publish-log list' to see available dates")
        return 0

    # Apply limit
    if len(entries) > limit:
        entries = entries[:limit]
        truncated = True
    else:
        truncated = False

    if not entries:
        print("No matching entries found")
        return 0

    # Output based on format (T042)
    if output_format == "json":
        result = [_entry_to_dict(e) for e in entries]
        print(json.dumps(result, indent=2, default=str))
    elif output_format == "jsonl":
        for entry in entries:
            print(json.dumps(_entry_to_dict(entry), separators=(",", ":"), default=str))
    else:  # table format
        print(f"Found {len(entries)} entries" + (" (truncated)" if truncated else ""))
        print("-" * 70)
        for entry in entries:
            print(f"  {entry.puzzle_id}")
            print(f"    Run: {entry.run_id} | Source: {entry.source_id}")
            print(f"    Path: {entry.path}")
            print()

    return 0


def _entry_to_dict(entry: PublishLogEntry) -> dict:
    """Convert PublishLogEntry to dict for JSON output."""
    return {
        "run_id": entry.run_id,
        "puzzle_id": entry.puzzle_id,
        "source_id": entry.source_id,
        "path": entry.path,
        "trace_id": entry.trace_id,
        "quality": entry.quality,
        "level": entry.level,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Set up logging
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    setup_logging(level=log_level)

    # Execute command
    if args.command == "run":
        return cmd_run(args)
    elif args.command == "ingest":
        return cmd_ingest(args)
    elif args.command == "daily":
        return cmd_daily(args)
    elif args.command == "status":
        return cmd_status(args)
    elif args.command == "clean":
        return cmd_clean(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "inventory":
        return cmd_inventory(args)
    elif args.command == "sources":
        return cmd_sources(args)
    elif args.command == "enable-adapter":
        return cmd_enable_adapter(args)
    elif args.command == "disable-adapter":
        return cmd_disable_adapter(args)
    elif args.command == "rollback":
        return cmd_rollback(args)
    elif args.command == "vacuum-db":
        return cmd_vacuum_db(args)
    elif args.command == "publish-log":
        return cmd_publish_log(args)
    elif args.command == "config-lock":
        return cmd_config_lock(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
