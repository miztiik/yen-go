#!/usr/bin/env python3
"""
Syougo.jp Puzzle Ingestor

A configuration-driven utility to ingest Go/Baduk puzzles from syougo.jp (将碁友の会).
Downloads puzzles from the skill assessment (棋力判定) section.

Features:
- Downloads puzzles from 5 difficulty levels (123 total puzzles)
- Configurable delay with jitter factor for rate limiting
- Exponential backoff on errors
- Per-run log files with unique identifiers
- Idempotent operations with state tracking
- SGF conversion with solution trees

Usage (from project root):
    python -m tools.syougo --all                       # Download all levels
    python -m tools.syougo --levels 1,2,3              # Specific levels
    python -m tools.syougo --status                    # Show progress
    python -m tools.syougo --retry                     # Retry failed

Author: YenGo Project
License: MIT
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library required. Install with: pip install requests")
    sys.exit(1)

# Import centralized path utilities for consistent logging
from tools.core.checkpoint import (
    ToolCheckpoint,
)
from tools.core.checkpoint import (
    load_checkpoint as core_load,
)
from tools.core.checkpoint import (
    save_checkpoint as core_save,
)

# Core infrastructure
from tools.core.logging import setup_logging as core_setup_logging
from tools.core.paths import rel_path
from tools.core.validation import validate_sgf_puzzle

# ============================================================================
# CONSTANTS
# ============================================================================

VERSION = "1.0.0"
TOOL_NAME = "syougo"
CONFIG_FILE = "config.json"
SOURCES_FILE = "sources.json"

# All output (downloads, logs, checkpoint) co-located per tool-development-standards §12, §18
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # yen-go/
OUTPUT_DIR = PROJECT_ROOT / "external-sources" / "syougo"


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

@dataclass
class NetworkConfig:
    """Network/HTTP configuration."""
    base_delay_seconds: float = 2.0
    jitter_factor: float = 0.5
    max_delay_seconds: float = 60.0
    request_timeout_seconds: int = 30
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    referer: str = "https://www.syougo.jp/jk/khantei.html"


@dataclass
class OutputConfig:
    """Output configuration."""
    directory: str = "./downloads"
    save_sgf: bool = True
    save_metadata: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    to_file: bool = True
    include_timestamp: bool = True
    include_run_id: bool = True


@dataclass
class BehaviorConfig:
    """Behavior configuration."""
    skip_existing: bool = True
    stop_on_consecutive_failures: int = 3


@dataclass
class Config:
    """Main configuration container."""
    network: NetworkConfig = field(default_factory=NetworkConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)

    @classmethod
    def load(cls, config_path: Path) -> Config:
        """Load configuration from JSON file."""
        config = cls()

        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    data = json.load(f)

                if "network" in data:
                    for key, value in data["network"].items():
                        if hasattr(config.network, key):
                            setattr(config.network, key, value)

                if "output" in data:
                    for key, value in data["output"].items():
                        if hasattr(config.output, key):
                            setattr(config.output, key, value)

                if "logging" in data:
                    for key, value in data["logging"].items():
                        if hasattr(config.logging, key):
                            setattr(config.logging, key, value)

                if "behavior" in data:
                    for key, value in data["behavior"].items():
                        if hasattr(config.behavior, key):
                            setattr(config.behavior, key, value)

            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")

        return config


# ============================================================================
# SOURCE DEFINITIONS
# ============================================================================

@dataclass
class LevelInfo:
    """Information about a puzzle level."""
    level_num: str
    name: str
    japanese: str
    description: str
    puzzle_count: int
    board_size: int
    output_dir: str
    yengo_level: str  # Mapped level for YenGo


class SourceRegistry:
    """Registry of puzzle levels from sources.json."""

    def __init__(self, sources_path: Path):
        self.base_url: str = "https://www.syougo.jp"
        self.endpoint: str = "/jk/php/khantei.php"
        self.levels: dict[str, LevelInfo] = {}
        self._load_sources(sources_path)

    def _load_sources(self, sources_path: Path) -> None:
        """Load sources from JSON file."""
        if not sources_path.exists():
            self._create_default()
            return

        try:
            with open(sources_path, encoding="utf-8") as f:
                data = json.load(f)

            self.base_url = data.get("base_url", self.base_url)
            self.endpoint = data.get("endpoint", self.endpoint)
            level_mapping = data.get("level_mapping", {})

            for level_num, level_data in data.get("levels", {}).items():
                self.levels[level_num] = LevelInfo(
                    level_num=level_num,
                    name=level_data.get("name", f"Level {level_num}"),
                    japanese=level_data.get("japanese", ""),
                    description=level_data.get("description", ""),
                    puzzle_count=level_data.get("puzzle_count", 25),
                    board_size=level_data.get("board_size", 9),
                    output_dir=level_data.get("output_dir", f"level_{level_num}"),
                    yengo_level=level_mapping.get(level_num, "intermediate")
                )

        except Exception as e:
            print(f"Error loading sources: {e}")
            self._create_default()

    def _create_default(self) -> None:
        """Create default level configuration."""
        defaults = [
            ("1", "Beginner", "初級", 25, 9, "novice"),
            ("2", "Intermediate", "中級", 25, 9, "beginner"),
            ("3", "Advanced", "上級", 25, 9, "intermediate"),
            ("4", "Dan-level", "有段", 24, 9, "advanced"),
            ("5", "High-Dan", "高段", 24, 13, "expert"),
        ]
        for lnum, name, jp, count, size, yengo in defaults:
            self.levels[lnum] = LevelInfo(
                level_num=lnum,
                name=name,
                japanese=jp,
                description=f"{name} level puzzles",
                puzzle_count=count,
                board_size=size,
                output_dir=f"level_{lnum}_{name.lower().replace('-', '')}",
                yengo_level=yengo
            )

    def get_url(self, level_num: str) -> str:
        """Get the URL for a specific level."""
        return f"{self.base_url}{self.endpoint}?lno={level_num}"

    def list_levels(self) -> list[tuple[str, LevelInfo]]:
        """List all levels."""
        return sorted(self.levels.items(), key=lambda x: int(x[0]))


# ============================================================================
# STATE TRACKING
# ============================================================================

@dataclass
class DownloadState(ToolCheckpoint):
    """Tracks download progress for resume capability."""

    completed: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed: dict[str, dict[str, Any]] = field(default_factory=dict)
    runs: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def load(cls, output_dir: Path) -> DownloadState:
        """Load state from checkpoint."""
        state = core_load(output_dir, cls)
        return state if state else cls()

    def save(self, output_dir: Path) -> None:
        """Save state atomically via core checkpoint."""
        core_save(self, output_dir)

    def mark_completed(self, puzzle_id: str, metadata: dict[str, Any]) -> None:
        """Mark a puzzle as successfully downloaded."""
        self.completed[puzzle_id] = {
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
        }
        self.failed.pop(puzzle_id, None)

    def mark_failed(self, puzzle_id: str, error: str) -> None:
        """Mark a puzzle as failed."""
        attempts = self.failed.get(puzzle_id, {}).get("attempts", 0) + 1
        self.failed[puzzle_id] = {
            "timestamp": datetime.now().isoformat(),
            "error": error,
            "attempts": attempts
        }

    def is_completed(self, puzzle_id: str) -> bool:
        """Check if a puzzle has already been downloaded."""
        return puzzle_id in self.completed

    def record_run(self, run_id: str, summary: dict[str, Any]) -> None:
        """Record a run in history."""
        self.runs.append({
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            **summary
        })

    def clear(self) -> None:
        """Clear all state."""
        self.completed.clear()
        self.failed.clear()


# ============================================================================
# LOGGING SETUP
# ============================================================================

def generate_run_id() -> str:
    """Generate a unique run ID."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{timestamp}_{short_uuid}"


class ColorFormatter(logging.Formatter):
    """Formatter with ANSI color support."""
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(config: LoggingConfig, run_id: str) -> logging.Logger:
    """Configure structured JSONL + console logging via core infrastructure."""
    return core_setup_logging(
        output_dir=OUTPUT_DIR,
        logger_name=TOOL_NAME,
        verbose=(config.level.upper() == "DEBUG"),
        log_suffix=TOOL_NAME,
    )


# ============================================================================
# HTTP CLIENT
# ============================================================================

class HttpClient:
    """HTTP client with rate limiting and retry logic."""

    def __init__(self, config: NetworkConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5,ja;q=0.3",
            "Referer": config.referer,
            "Connection": "keep-alive",
        })
        self._last_request_time = 0.0

    def _calculate_delay(self) -> float:
        """Calculate delay with jitter."""
        base = self.config.base_delay_seconds
        jitter = base * self.config.jitter_factor * random.random()
        return base + jitter

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        base = self.config.base_delay_seconds * (self.config.backoff_multiplier ** attempt)
        jitter = base * self.config.jitter_factor * random.random()
        delay = base + jitter
        return min(delay, self.config.max_delay_seconds)

    def _wait_for_rate_limit(self) -> None:
        """Enforce rate limiting with jitter."""
        delay = self._calculate_delay()
        elapsed = time.time() - self._last_request_time

        if elapsed < delay:
            sleep_time = delay - elapsed
            self.logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)

    def get(self, url: str) -> str | None:
        """Fetch URL with retry logic."""
        self._wait_for_rate_limit()

        for attempt in range(self.config.max_retries):
            try:
                self.logger.debug(f"GET {url} (attempt {attempt + 1})")
                self._last_request_time = time.time()

                response = self.session.get(
                    url,
                    timeout=self.config.request_timeout_seconds
                )
                response.raise_for_status()
                return response.text

            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")

                if attempt < self.config.max_retries - 1:
                    backoff = self._calculate_backoff(attempt)
                    self.logger.info(f"Backing off for {backoff:.2f}s")
                    time.sleep(backoff)

        return None


# ============================================================================
# SGF PARSING AND CONVERSION
# ============================================================================

def parse_raw_puzzles(raw_data: str) -> list[str]:
    """Parse raw response into individual puzzle SGF strings."""
    # Puzzles are separated by |
    puzzles = raw_data.strip().split("|")
    return [p.strip() for p in puzzles if p.strip()]


def extract_puzzle_metadata(sgf: str, puzzle_num: int, level_info: LevelInfo) -> dict[str, Any]:
    """Extract metadata from SGF puzzle."""
    metadata = {
        "source": "syougo.jp",
        "level_num": level_info.level_num,
        "level_name": level_info.name,
        "puzzle_num": puzzle_num,
        "puzzle_id": f"syougo_L{level_info.level_num}_P{puzzle_num:02d}",
        "yengo_level": level_info.yengo_level,
    }

    # Extract board size
    sz_match = re.search(r'SZ\[(\d+)\]', sgf)
    if sz_match:
        metadata["board_size"] = int(sz_match.group(1))
    else:
        metadata["board_size"] = level_info.board_size

    # Extract problem prompt (first C[] comment)
    comment_match = re.search(r'C\[([^\]]+)\]', sgf)
    if comment_match:
        prompt_jp = comment_match.group(1)
        metadata["prompt_japanese"] = prompt_jp
        metadata["prompt_english"] = translate_japanese(prompt_jp)

    # Determine player to move
    metadata["player_to_move"] = determine_player_to_move(sgf)

    # Count solution moves
    moves = re.findall(r';[BW]\[[a-s][a-s]\]', sgf)
    metadata["solution_length"] = len(moves)

    # Count variations (wrong answers)
    variations = sgf.count('(;')
    metadata["variation_count"] = variations

    return metadata


# Japanese to English translation dictionary
JAPANESE_TRANSLATIONS = {
    # Problem prompts (longer phrases first)
    "白を取ってください": "Capture the white stones",
    "白を取って下さい": "Capture the white stones",
    "黒を取ってください": "Capture the black stones",
    "黒を取って下さい": "Capture the black stones",
    "白３子を取ってください": "Capture the 3 white stones",
    "白４子を取ってください": "Capture the 4 white stones",
    "白２子を取ってください": "Capture the 2 white stones",
    "白３目を取ってください": "Capture the 3 white stones",
    "黒３子を助けてください": "Save the 3 black stones",
    "黒４子を助けてください": "Save the 4 black stones",
    "黒４子を逃げてください": "Save the 4 black stones",
    "黒５子を助けて下さい": "Save the 5 black stones",
    "黒６子を助けてください": "Save the 6 black stones",
    "黒生きてください": "Make black live",
    "黒生きて下さい": "Make black live",
    "白生きてください": "Make white live",
    "白生きて下さい": "Make white live",
    "黒番です": "Black to play",
    "白番です": "White to play",
    "コウになります": "It becomes ko",
    "隅の白を取ってください": "Capture the white stones in the corner",
    "隅の白を取って下さい": "Capture the white stones in the corner",
    "隅の黒を助けてください": "Save the black stones in the corner",
    "隅の黒を助けて下さい": "Save the black stones in the corner",
    "どう守るのが得ですか": "What is the best defense",
    "どうヨセますか": "What is the best endgame move",
    "最善にヨセてください": "Find the best endgame sequence",
    "次の一手はA・Bのどちらが良いでしょう": "Which is better: A or B",
    "黒どう打ちますか": "How should black play",
    "黒正しく受けてください": "Find the correct response for black",
    "初手のツギがこの一手です": "The first connection is the key move",
    "白石を分断して下さい": "Cut off the white stones",
    "捕らわれの黒": "the captured black stones",
    "を助けてください": "Save",
    "３手まで示してください": "Show the first 3 moves",

    # Result comments
    "正解です": "Correct!",
    "良く出来ました": "Well done!",
    "良くできました": "Well done!",
    "残念": "Wrong",
    "残念！": "Wrong!",
    "黒は生きました": "Black lives",
    "白は死にました": "White is dead",
    "黒は死にました": "Black is dead",
    "白の死にを確認してください": "Confirm that white is dead",
    "黒の死にを確認してください": "Confirm that black is dead",
    "白手も足もでません": "White cannot escape",

    # Techniques and patterns (longer phrases first)
    "ダメ詰まり": "shortage of liberties",
    "うってがえし": "snapback",
    "殺しのテクニック": "killing technique",
    "一発即死の妙手筋": "a one-move killing tesuji",
    "手筋": "tesuji",
    "花六": "flower six (dead shape)",
    "２眼できません": "cannot make two eyes",
    "二眼できません": "cannot make two eyes",
    "眼ができません": "cannot make eyes",
    "この図": "This shape is",
    "白地": "white territory",
    "黒地": "black territory",
    "という": " is a ",
    "です": "",
    "眼": " eye",
    "目": " point ",

    # Common particles and connectors (translate last)
    "。": ". ",
    "、": ",",
    "！": "!",
    "？": "?",
}


def translate_fullwidth_numbers(text: str) -> str:
    """Convert full-width Japanese numbers and letters to ASCII equivalents."""
    # Full-width to ASCII mapping
    fullwidth_map = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
        'Ａ': 'A', 'Ｂ': 'B', 'Ｃ': 'C', 'Ｄ': 'D', 'Ｅ': 'E',
        'Ｆ': 'F', 'Ｇ': 'G', 'Ｈ': 'H', 'Ｉ': 'I', 'Ｊ': 'J',
        'Ｋ': 'K', 'Ｌ': 'L', 'Ｍ': 'M', 'Ｎ': 'N', 'Ｏ': 'O',
        'Ｐ': 'P', 'Ｑ': 'Q', 'Ｒ': 'R', 'Ｓ': 'S', 'Ｔ': 'T',
        'Ｕ': 'U', 'Ｖ': 'V', 'Ｗ': 'W', 'Ｘ': 'X', 'Ｙ': 'Y', 'Ｚ': 'Z',
        'ａ': 'a', 'ｂ': 'b', 'ｃ': 'c', 'ｄ': 'd', 'ｅ': 'e',
        'ｆ': 'f', 'ｇ': 'g', 'ｈ': 'h', 'ｉ': 'i', 'ｊ': 'j',
        'ｋ': 'k', 'ｌ': 'l', 'ｍ': 'm', 'ｎ': 'n', 'ｏ': 'o',
        'ｐ': 'p', 'ｑ': 'q', 'ｒ': 'r', 'ｓ': 's', 'ｔ': 't',
        'ｕ': 'u', 'ｖ': 'v', 'ｗ': 'w', 'ｘ': 'x', 'ｙ': 'y', 'ｚ': 'z',
    }
    result = text
    for fw, ascii_char in fullwidth_map.items():
        result = result.replace(fw, ascii_char)
    return result


def translate_japanese(text: str) -> str:
    """Translate Japanese text to English using dictionary lookup."""
    if not text:
        return ""

    result = text

    # First convert full-width numbers and letters to ASCII
    result = translate_fullwidth_numbers(result)

    # Convert CJK punctuation to ASCII equivalents
    result = result.replace('「', '"').replace('」', '"')
    result = result.replace('『', '"').replace('』', '"')
    result = result.replace('（', '(').replace('）', ')')
    result = result.replace('【', '[').replace('】', ']')
    result = result.replace('・', '-')
    result = result.replace('　', ' ')  # Full-width space

    # Apply translations from longest to shortest to avoid partial matches
    sorted_translations = sorted(JAPANESE_TRANSLATIONS.items(), key=lambda x: -len(x[0]))
    for jp, en in sorted_translations:
        result = result.replace(jp, en)

    # Clean up any remaining Japanese characters (Hiragana, Katakana, Kanji, CJK punctuation)
    # Ranges: Hiragana (3040-309F), Katakana (30A0-30FF), CJK (4E00-9FFF), CJK Punct (3000-303F)
    # Replace with space (not empty) to avoid merging adjacent tokens
    result = re.sub(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]+', ' ', result)

    # Insert spaces between letters and digits that got stuck together
    # e.g. "is6 point" → "is 6 point", "1shortage" → "1 shortage"
    result = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', result)
    result = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', result)

    # Clean up multiple spaces and trim
    result = re.sub(r'\s+', ' ', result).strip()

    # Remove empty brackets or orphaned punctuation
    result = re.sub(r'\(\s*\)', '', result)
    result = re.sub(r'^\s*[.,!?]\s*', '', result)

    return result if result else ""


def has_japanese(text: str) -> bool:
    """Check if text contains Japanese characters."""
    return bool(re.search(r'[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]', text))


def determine_player_to_move(sgf: str) -> str:
    """Determine which player moves first based on SGF content."""
    # Look for the first move in the main line
    first_move = re.search(r';([BW])\[[a-s][a-s]\]', sgf)
    if first_move:
        return first_move.group(1)
    return "B"  # Default to black


def translate_all_comments(sgf: str) -> str:
    """Translate all C[] comments in the SGF from Japanese to English."""
    def translate_comment(match):
        comment = match.group(1)
        translated = translate_japanese(comment)
        if translated:
            return f"C[{translated}]"
        return ""  # Remove empty comments

    return re.sub(r'C\[([^\]]*)\]', translate_comment, sgf)


def normalize_sgf(sgf: str, metadata: dict[str, Any]) -> str:
    """Normalize SGF to YenGo-compliant format.

    Produces SGF with:
    - Standard headers: FF[4]GM[1]CA[UTF-8]
    - Board size: SZ[n]
    - Game name: GN[] (empty, no Japanese)
    - Player to move: PL[B] or PL[W]
    - Initial position: AB[...] AW[...]
    - YenGo properties: YG[level:sublevel]
    - All comments translated to English
    """
    # Ensure it starts with (;
    if not sgf.startswith("(;"):
        sgf = "(;" + sgf.lstrip("(").lstrip(";")

    # Extract board size
    sz_match = re.search(r'SZ\[(\d+)\]', sgf)
    board_size = int(sz_match.group(1)) if sz_match else metadata.get('board_size', 9)

    # Extract initial stones
    re.findall(r'AB(\[[a-s][a-s]\])+', sgf)
    re.findall(r'AW(\[[a-s][a-s]\])+', sgf)

    # Get all AB and AW stones
    ''.join(re.findall(r'AB(\[[a-s][a-s]\])+', sgf))
    ''.join(re.findall(r'AW(\[[a-s][a-s]\])+', sgf))

    # Actually extract properly
    ab_full = re.search(r'AB((?:\[[a-s][a-s]\])+)', sgf)
    aw_full = re.search(r'AW((?:\[[a-s][a-s]\])+)', sgf)

    ab_section = f"AB{ab_full.group(1)}" if ab_full else ""
    aw_section = f"AW{aw_full.group(1)}" if aw_full else ""

    # Determine player to move
    player = determine_player_to_move(sgf)

    # Get YenGo level slug (no sublevel suffix)
    yengo_level = metadata.get('yengo_level', 'intermediate')

    # Build standard header
    puzzle_id = metadata.get('puzzle_id', '')
    header = f"(;FF[4]GM[1]SZ[{board_size}]CA[UTF-8]GN[{puzzle_id}]PL[{player}]"
    header += f"{ab_section}{aw_section}"
    header += f"YG[{yengo_level}]"

    # Find where moves/variations start (after initial setup)
    # Look for first move or first variation after setup
    rest_match = re.search(r'(;[BW]\[[a-s][a-s]\].*)', sgf, re.DOTALL)
    if rest_match:
        rest = rest_match.group(1)
    else:
        # No moves, just close
        rest = ")"

    # Translate all comments in the rest
    rest = translate_all_comments(rest)

    # Remove any old GN[], C[] from header area that might have Japanese
    # (we've already extracted what we need)

    return header + rest


# ============================================================================
# MAIN INGESTOR
# ============================================================================

class SyougoIngestor:
    """Main ingestor class for syougo.jp puzzles."""

    def __init__(self, script_dir: Path, run_id: str):
        self.script_dir = script_dir
        self.run_id = run_id

        # Load configuration
        self.config = Config.load(script_dir / CONFIG_FILE)

        # Setup logging
        self.logger = setup_logging(self.config.logging, run_id)
        self.logger.info(f"Syougo Ingestor v{VERSION} starting (run: {run_id})")

        # Load sources
        self.sources = SourceRegistry(script_dir / SOURCES_FILE)

        # Load state from output directory (co-located per standards)
        self.state = DownloadState.load(OUTPUT_DIR)

        # Setup HTTP client
        self.http = HttpClient(self.config.network, self.logger)

        # Statistics
        self.stats = {
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "total": 0
        }

    def download_level(self, level_num: str, force: bool = False) -> bool:
        """Download all puzzles for a specific level."""
        if level_num not in self.sources.levels:
            self.logger.error(f"Unknown level: {level_num}")
            return False

        level_info = self.sources.levels[level_num]
        self.logger.info(f"Downloading level {level_num}: {level_info.name} ({level_info.japanese})")

        # Fetch puzzles from endpoint
        url = self.sources.get_url(level_num)
        self.logger.debug(f"Fetching: {url}")

        raw_data = self.http.get(url)
        if not raw_data:
            self.logger.error(f"Failed to fetch level {level_num}")
            return False

        puzzles = parse_raw_puzzles(raw_data)
        self.logger.info(f"Found {len(puzzles)} puzzles for level {level_num}")

        # Create output directory
        output_dir = OUTPUT_DIR / "downloads" / level_info.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        consecutive_failures = 0

        for idx, sgf in enumerate(puzzles, start=1):
            puzzle_id = f"syougo_L{level_num}_P{idx:02d}"
            self.stats["total"] += 1

            # Skip if already completed
            if not force and self.config.behavior.skip_existing and self.state.is_completed(puzzle_id):
                self.logger.debug(f"Skipping {puzzle_id} (already completed)")
                self.stats["skipped"] += 1
                continue

            try:
                # Extract metadata
                metadata = extract_puzzle_metadata(sgf, idx, level_info)

                # Normalize SGF
                normalized_sgf = normalize_sgf(sgf, metadata)

                # Validate puzzle
                validation = validate_sgf_puzzle(normalized_sgf)
                if not validation.is_valid:
                    self.logger.warning(f"Skipping {puzzle_id}: {validation.rejection_reason}")
                    self.stats["skipped"] += 1
                    continue

                # Save SGF file
                if self.config.output.save_sgf:
                    sgf_path = output_dir / f"{puzzle_id}.sgf"
                    with open(sgf_path, "w", encoding="utf-8") as f:
                        f.write(normalized_sgf)
                    self.logger.debug(f"Saved SGF: {rel_path(sgf_path)}")

                # Save metadata
                if self.config.output.save_metadata:
                    meta_path = output_dir / f"{puzzle_id}.json"
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)

                # Update state
                self.state.mark_completed(puzzle_id, metadata)
                self.stats["downloaded"] += 1
                consecutive_failures = 0

                self.logger.info(f"Downloaded {puzzle_id}: {metadata.get('prompt_japanese', 'N/A')[:30]}...")

            except Exception as e:
                self.logger.error(f"Failed to process {puzzle_id}: {e}")
                self.state.mark_failed(puzzle_id, str(e))
                self.stats["failed"] += 1
                consecutive_failures += 1

                if consecutive_failures >= self.config.behavior.stop_on_consecutive_failures:
                    self.logger.error("Too many consecutive failures, stopping")
                    return False

        return True

    def download_levels(self, level_nums: list[str], force: bool = False) -> None:
        """Download puzzles for multiple levels."""
        for level_num in level_nums:
            self.download_level(level_num, force)
            # Small delay between levels
            time.sleep(1.0)

        # Save state
        self.state.record_run(self.run_id, self.stats)
        self.state.save(OUTPUT_DIR)

        # Print summary
        self.logger.info("=" * 50)
        self.logger.info("Download Summary:")
        self.logger.info(f"  Downloaded: {self.stats['downloaded']}")
        self.logger.info(f"  Skipped:    {self.stats['skipped']}")
        self.logger.info(f"  Failed:     {self.stats['failed']}")
        self.logger.info(f"  Total:      {self.stats['total']}")

    def show_status(self) -> None:
        """Display current download status."""
        print(f"\n{'=' * 50}")
        print("Syougo.jp Puzzle Ingestor - Status")
        print(f"{'=' * 50}")

        print(f"\nCompleted: {len(self.state.completed)} puzzles")
        print(f"Failed:    {len(self.state.failed)} puzzles")

        print("\nPuzzles per level:")
        for level_num, level_info in self.sources.list_levels():
            completed = sum(1 for pid in self.state.completed if f"_L{level_num}_" in pid)
            print(f"  Level {level_num} ({level_info.name}): {completed}/{level_info.puzzle_count}")

        if self.state.failed:
            print("\nFailed puzzles:")
            for puzzle_id, info in list(self.state.failed.items())[:5]:
                print(f"  {puzzle_id}: {info.get('error', 'Unknown')[:50]}")
            if len(self.state.failed) > 5:
                print(f"  ... and {len(self.state.failed) - 5} more")

        if self.state.runs:
            last_run = self.state.runs[-1]
            print(f"\nLast run: {last_run.get('timestamp', 'Unknown')}")

    def list_levels(self) -> None:
        """List available levels."""
        print(f"\n{'=' * 50}")
        print("Available Levels")
        print(f"{'=' * 50}")

        for level_num, level_info in self.sources.list_levels():
            print(f"\nLevel {level_num}: {level_info.name} ({level_info.japanese})")
            print(f"  Description: {level_info.description}")
            print(f"  Puzzles: {level_info.puzzle_count}")
            print(f"  Board size: {level_info.board_size}x{level_info.board_size}")
            print(f"  YenGo level: {level_info.yengo_level}")


# ============================================================================
# CLI
# ============================================================================

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Download Go puzzles from syougo.jp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                  Download all levels
  %(prog)s --levels 1,2,3         Download beginner through advanced
  %(prog)s --status               Show download status
  %(prog)s --list-levels          List available levels
  %(prog)s --retry                Retry failed downloads
  %(prog)s --force --all          Re-download everything
        """
    )

    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"%(prog)s {VERSION}"
    )

    # Download options
    download_group = parser.add_argument_group("Download Options")
    download_group.add_argument(
        "--all", "-a",
        action="store_true",
        help="Download all levels (1-5)"
    )
    download_group.add_argument(
        "--levels", "-l",
        type=str,
        help="Comma-separated list of levels to download (e.g., 1,2,3)"
    )
    download_group.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download even if already completed"
    )
    download_group.add_argument(
        "--retry", "-r",
        action="store_true",
        help="Retry failed downloads"
    )

    # Info options
    info_group = parser.add_argument_group("Information")
    info_group.add_argument(
        "--status", "-s",
        action="store_true",
        help="Show download status"
    )
    info_group.add_argument(
        "--list-levels",
        action="store_true",
        help="List available levels"
    )

    # State management
    state_group = parser.add_argument_group("State Management")
    state_group.add_argument(
        "--clear-state",
        action="store_true",
        help="Clear download state (use with caution)"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    script_dir = Path(__file__).parent
    run_id = generate_run_id()

    ingestor = SyougoIngestor(script_dir, run_id)

    # Handle info commands
    if args.status:
        ingestor.show_status()
        return 0

    if args.list_levels:
        ingestor.list_levels()
        return 0

    # Handle state management
    if args.clear_state:
        confirm = input("Are you sure you want to clear all state? [y/N] ")
        if confirm.lower() == 'y':
            ingestor.state.clear()
            ingestor.state.save(OUTPUT_DIR)
            print("State cleared.")
        return 0

    # Determine levels to download
    levels_to_download = []

    if args.all:
        levels_to_download = [str(i) for i in range(1, 6)]
    elif args.levels:
        levels_to_download = [lvl.strip() for lvl in args.levels.split(",")]
    elif args.retry:
        # Get levels from failed puzzles
        failed_levels = set()
        for puzzle_id in ingestor.state.failed:
            match = re.search(r'_L(\d)_', puzzle_id)
            if match:
                failed_levels.add(match.group(1))
        levels_to_download = sorted(failed_levels)
        if not levels_to_download:
            ingestor.logger.info("No failed puzzles to retry")
            return 0

    if not levels_to_download:
        print("No levels specified. Use --all, --levels, or --help for usage.")
        return 1

    # Download
    ingestor.download_levels(levels_to_download, force=args.force)

    return 0


if __name__ == "__main__":
    sys.exit(main())
