"""Puzzle pool sampler -- draws diverse puzzles from the SGF collection.

Sampling strategies:
1. DB-backed: Query yengo-search.db for stratified sampling by level + tag
2. SGF-scan: Walk external-sources/ SGF dirs, parse YT/YG properties
3. Seed puzzles: Hand-crafted test cases for known techniques (fallback)

The pool avoids overfitting by never reusing the same puzzle set twice.
Each run draws a fresh sample stratified across technique x difficulty.
"""
from __future__ import annotations

import json
import logging
import random
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Project root (tools/oshie/eval/ -> project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SEARCH_DB = _PROJECT_ROOT / "yengo-puzzle-collections" / "yengo-search.db"
_SGF_ROOT = _PROJECT_ROOT / "yengo-puzzle-collections" / "sgf"
_TAGS_JSON = _PROJECT_ROOT / "config" / "tags.json"
_EXTERNAL_SOURCES = _PROJECT_ROOT / "external-sources"
_EVAL_FIXTURES = _PROJECT_ROOT / "tools" / "train_test_dataset" / "fixtures" / "evaluation"

# Level ID -> slug mapping (from config/puzzle-levels.json)
LEVEL_SLUGS = {
    110: "novice", 120: "beginner", 130: "elementary",
    140: "intermediate", 150: "upper-intermediate", 160: "advanced",
    210: "low-dan", 220: "high-dan", 230: "expert",
}

# Technique tag IDs for stratification (from config/tags.json)
TECHNIQUE_TAG_IDS = {
    30: "snapback", 32: "double-atari", 34: "ladder", 36: "net",
    38: "throw-in", 40: "clamp", 42: "nakade", 44: "connect-and-die",
    46: "under-the-stones", 48: "liberty-shortage", 50: "vital-point",
    52: "tesuji", 60: "capture-race", 62: "eye-shape", 64: "dead-shapes",
    66: "escape", 68: "connection", 70: "cutting",
}


@dataclass
class TestPuzzle:
    """A puzzle ready for LLM evaluation."""
    puzzle_id: str               # content_hash or seed name
    source: str                  # "db", "sgf-scan", or "seed"
    board_size: int
    difficulty: str              # level slug
    technique: str               # primary technique tag
    technique_tags: list[str]    # all technique tags
    color_to_play: str           # "B" or "W"
    setup_black: list[str]       # SGF coords
    setup_white: list[str]       # SGF coords
    correct_move_sgf: str        # e.g. "dg"
    correct_move_gtp: str        # e.g. "D7"
    wrong_moves: list[dict] = field(default_factory=list)
    situation: str = ""          # text description for LLM prompt
    expected_keywords: list[str] = field(default_factory=list)

    def to_user_prompt(self) -> str:
        """Format this puzzle as a user prompt for the LLM."""
        lines = [
            f"Board: {self.board_size}x{self.board_size}, {'Black' if self.color_to_play == 'B' else 'White'} to play",
            f"Difficulty: {self.difficulty.replace('-', ' ').title()}",
            f"Technique: {self.technique.replace('-', ' ').title()}",
            "",
        ]
        if self.setup_black:
            lines.append(f"Black stones: {', '.join(self.setup_black)}")
        if self.setup_white:
            lines.append(f"White stones: {', '.join(self.setup_white)}")
        if self.situation:
            lines.append(self.situation)
        lines.append("")
        lines.append(
            f"Correct move: {self.correct_move_gtp} (SGF: {self.correct_move_sgf})"
        )
        for i, wm in enumerate(self.wrong_moves):
            lines.append(
                f"Wrong move {i+1}: {wm.get('gtp', '?')} (SGF: {wm.get('sgf', '?')}) -- {wm.get('reason', '')}"
            )
        lines.append("")
        lines.append("Explain why the correct move works and why the wrong moves fail. Provide 3-tier hints.")
        return "\n".join(lines)


def _load_tag_map() -> dict[int, str]:
    """Load tag ID -> slug mapping from config/tags.json."""
    if not _TAGS_JSON.exists():
        return dict(TECHNIQUE_TAG_IDS)
    data = json.loads(_TAGS_JSON.read_text(encoding="utf-8"))
    tags = data.get("tags", data) if isinstance(data, dict) else {}
    result = {}
    for slug_key, info in tags.items():
        if isinstance(info, dict) and "id" in info:
            result[info["id"]] = info.get("slug", slug_key)
    return result if result else dict(TECHNIQUE_TAG_IDS)


def _sgf_coord_to_gtp(sgf: str, board_size: int = 19) -> str:
    """Convert SGF coordinate (e.g. 'dg') to GTP (e.g. 'D7')."""
    if not sgf or len(sgf) != 2:
        return sgf
    col = ord(sgf[0]) - ord('a')
    row = ord(sgf[1]) - ord('a')
    # GTP: columns A-T (skip I), rows 1-19 from bottom
    gtp_col = chr(ord('A') + col + (1 if col >= 8 else 0))  # skip I
    gtp_row = board_size - row
    return f"{gtp_col}{gtp_row}"


def _parse_sgf_for_puzzle(sgf_path: Path) -> TestPuzzle | None:
    """Parse an SGF file and extract puzzle data for evaluation."""
    try:
        content = sgf_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    # Extract YenGo properties via regex (fast, no heavy parser needed)
    def _prop(name: str) -> str:
        m = re.search(rf"{name}\[([^\]]*)\]", content)
        return m.group(1) if m else ""

    board_size = 19
    sz = _prop("SZ")
    if sz and sz.isdigit():
        board_size = int(sz)

    level_slug = _prop("YG") or "unknown"
    tags_str = _prop("YT")
    technique_tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
    primary_technique = technique_tags[0] if technique_tags else "unknown"
    puzzle_id = _prop("GN").replace("YENGO-", "")
    color = _prop("PL") or "B"

    # Extract setup stones from AB[]/AW[] properties
    setup_b = re.findall(r"AB\[([a-s]{2})\]", content)
    setup_w = re.findall(r"AW\[([a-s]{2})\]", content)
    # Handle concatenated AB[aa][bb][cc] format
    for m in re.finditer(r"AB((?:\[[a-s]{2}\])+)", content):
        setup_b = re.findall(r"\[([a-s]{2})\]", m.group(0))
    for m in re.finditer(r"AW((?:\[[a-s]{2}\])+)", content):
        setup_w = re.findall(r"\[([a-s]{2})\]", m.group(0))

    # Extract correct first move from solution tree
    # After root node properties, the first B[] or W[] is the correct move
    root_end = content.find(")")
    first_move_match = re.search(r";([BW])\[([a-s]{2})\]", content[content.find(";", 1):] if ";" in content[1:] else "")
    if not first_move_match:
        return None
    correct_sgf = first_move_match.group(2)
    correct_gtp = _sgf_coord_to_gtp(correct_sgf, board_size)

    # Extract wrong moves from YR property
    wrong_moves = []
    yr = _prop("YR")
    if yr:
        for coord in yr.split(","):
            coord = coord.strip()
            if coord and len(coord) == 2:
                wrong_moves.append({
                    "sgf": coord,
                    "gtp": _sgf_coord_to_gtp(coord, board_size),
                    "reason": "refutation move",
                })

    # Also extract wrong moves from WV[] markers (Cho Chikun format)
    # Pattern: (;B[xy]WV[] or (;W[xy]WV[] marks wrong first moves
    for wm_match in re.finditer(r"\(;[BW]\[([a-s]{2})\]WV\[\]", content):
        wm_coord = wm_match.group(1)
        if not any(w["sgf"] == wm_coord for w in wrong_moves):
            wrong_moves.append({
                "sgf": wm_coord,
                "gtp": _sgf_coord_to_gtp(wm_coord, board_size),
                "reason": "wrong variation",
            })

    if not puzzle_id:
        puzzle_id = sgf_path.stem

    return TestPuzzle(
        puzzle_id=puzzle_id,
        source="sgf-scan",
        board_size=board_size,
        difficulty=level_slug,
        technique=primary_technique,
        technique_tags=technique_tags,
        color_to_play=color,
        setup_black=setup_b,
        setup_white=setup_w,
        correct_move_sgf=correct_sgf,
        correct_move_gtp=correct_gtp,
        wrong_moves=wrong_moves,
        expected_keywords=[t for t in technique_tags[:3]],
    )


def sample_from_db(
    n: int = 10,
    seed: int | None = None,
    level_ids: list[int] | None = None,
    tag_ids: list[int] | None = None,
    exclude_hashes: set[str] | None = None,
) -> list[TestPuzzle]:
    """Sample puzzles from yengo-search.db with stratification.

    Stratifies across level x tag combinations. Falls back to random
    sampling if stratification yields fewer than n puzzles.
    """
    if not _SEARCH_DB.exists():
        logger.warning("yengo-search.db not found at %s", _SEARCH_DB)
        return []

    rng = random.Random(seed)
    exclude = exclude_hashes or set()
    conn = sqlite3.connect(str(_SEARCH_DB))
    tag_map = _load_tag_map()

    try:
        # Get all puzzles with their tags
        rows = conn.execute("""
            SELECT p.content_hash, p.batch, p.level_id, p.cx_depth,
                   GROUP_CONCAT(pt.tag_id) as tag_ids
            FROM puzzles p
            LEFT JOIN puzzle_tags pt ON p.content_hash = pt.content_hash
            GROUP BY p.content_hash
        """).fetchall()

        # Filter and organize into buckets
        buckets: dict[str, list[dict]] = {}
        for row in rows:
            content_hash, batch, level_id, cx_depth, tag_ids_str = row
            if content_hash in exclude:
                continue
            if level_ids and level_id not in level_ids:
                continue

            tags = []
            if tag_ids_str:
                for tid in tag_ids_str.split(","):
                    tid = int(tid)
                    if tid in tag_map:
                        tags.append(tag_map[tid])
                    if tag_ids and tid not in tag_ids:
                        continue

            level_slug = LEVEL_SLUGS.get(level_id, "unknown")
            primary_tag = tags[0] if tags else "general"
            bucket_key = f"{level_slug}:{primary_tag}"
            if bucket_key not in buckets:
                buckets[bucket_key] = []
            buckets[bucket_key].append({
                "content_hash": content_hash,
                "batch": batch,
                "level_id": level_id,
                "level_slug": level_slug,
                "tags": tags,
                "primary_tag": primary_tag,
                "cx_depth": cx_depth,
            })

        # Stratified sampling: round-robin across buckets
        selected: list[dict] = []
        bucket_keys = sorted(buckets.keys())
        rng.shuffle(bucket_keys)
        idx = 0
        while len(selected) < n and bucket_keys:
            bk = bucket_keys[idx % len(bucket_keys)]
            items = buckets[bk]
            if items:
                choice = rng.choice(items)
                items.remove(choice)
                selected.append(choice)
            else:
                bucket_keys.remove(bk)
            idx += 1
            if idx > n * 10:
                break

        # Convert to TestPuzzle by reading actual SGF files
        puzzles = []
        for item in selected:
            sgf_path = _SGF_ROOT / item["batch"] / f"{item['content_hash']}.sgf"
            if sgf_path.exists():
                puzzle = _parse_sgf_for_puzzle(sgf_path)
                if puzzle:
                    puzzle.source = "db"
                    puzzle.difficulty = item["level_slug"]
                    puzzle.technique = item["primary_tag"]
                    puzzle.technique_tags = item["tags"]
                    puzzles.append(puzzle)

        return puzzles

    finally:
        conn.close()


def sample_from_external_sources(
    n: int = 10,
    seed: int | None = None,
    sources: list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> list[TestPuzzle]:
    """Sample puzzles from external-sources/ SGF directories.

    This reads raw SGFs (read-only) from external-sources/ and parses
    YenGo properties. Good for testing on unpublished puzzles.
    """
    if not _EXTERNAL_SOURCES.exists():
        logger.warning("external-sources/ not found")
        return []

    rng = random.Random(seed)
    exclude = exclude_ids or set()
    candidates: list[Path] = []

    source_dirs = list(_EXTERNAL_SOURCES.iterdir()) if sources is None else [
        _EXTERNAL_SOURCES / s for s in sources
    ]

    for source_dir in source_dirs:
        sgf_dir = source_dir / "sgf"
        if not sgf_dir.exists():
            continue
        for sgf_path in sgf_dir.rglob("*.sgf"):
            if sgf_path.stem not in exclude:
                candidates.append(sgf_path)

    if not candidates:
        return []

    sample_size = min(len(candidates), n * 3)
    sampled_paths = rng.sample(candidates, sample_size)

    puzzles: list[TestPuzzle] = []
    for sgf_path in sampled_paths:
        if len(puzzles) >= n:
            break
        puzzle = _parse_sgf_for_puzzle(sgf_path)
        if puzzle and puzzle.correct_move_sgf:
            puzzle.source = f"ext:{sgf_path.parent.parent.parent.name}"
            puzzles.append(puzzle)

    return puzzles


# ── Difficulty mapping for evaluation fixture subdirectories ─────────
_FIXTURE_DIFFICULTY_MAP = {
    "cho-elementary": "elementary",
    "cho-intermediate": "intermediate",
    "cho-advanced": "advanced",
}


def sample_from_evaluation_fixtures(
    n: int = 5,
    seed: int | None = None,
    exclude_ids: set[str] | None = None,
) -> list[TestPuzzle]:
    """Sample puzzles from train_test_dataset/fixtures/evaluation/.

    Reads professional Cho Chikun SGFs (read-only) with full solution
    trees. These are proper tsumego with correct/wrong move branches --
    much better evaluation material than hand-crafted seed puzzles.

    Args:
        n: Number of puzzles to sample.
        seed: Random seed for reproducibility.
        exclude_ids: Puzzle IDs to skip (prevents repetition across runs).

    Returns:
        List of TestPuzzle with source="eval-fixture".
    """
    if not _EVAL_FIXTURES.exists():
        logger.warning("Evaluation fixtures not found at %s", _EVAL_FIXTURES)
        return []

    rng = random.Random(seed)
    exclude = exclude_ids or set()
    candidates: list[tuple[Path, str]] = []  # (path, difficulty)

    for subdir in sorted(_EVAL_FIXTURES.iterdir()):
        if not subdir.is_dir():
            continue
        difficulty = _FIXTURE_DIFFICULTY_MAP.get(subdir.name, subdir.name)
        for sgf_path in sorted(subdir.glob("*.sgf")):
            if sgf_path.stem not in exclude:
                candidates.append((sgf_path, difficulty))

    if not candidates:
        logger.warning("No SGF files found in evaluation fixtures")
        return []

    # Sample more than needed since some may fail to parse
    sample_size = min(len(candidates), n * 3)
    sampled = rng.sample(candidates, sample_size)

    puzzles: list[TestPuzzle] = []
    for sgf_path, difficulty in sampled:
        if len(puzzles) >= n:
            break
        puzzle = _parse_sgf_for_puzzle(sgf_path)
        if puzzle and puzzle.correct_move_sgf:
            # Use filename as puzzle_id (GN may be generic across a collection)
            puzzle.puzzle_id = f"{sgf_path.parent.name}/{sgf_path.stem}"
            # Filter out wrong moves that duplicate the correct move
            puzzle.wrong_moves = [
                wm for wm in puzzle.wrong_moves
                if wm["sgf"] != puzzle.correct_move_sgf
            ]
            puzzle.source = "eval-fixture"
            puzzle.difficulty = difficulty
            # Tag as life-and-death (Cho Chikun collections are L&D)
            if not puzzle.technique_tags:
                puzzle.technique_tags = ["life-and-death"]
                puzzle.technique = "life-and-death"
            puzzles.append(puzzle)

    logger.info(
        "Sampled %d/%d evaluation fixtures (from %d candidates)",
        len(puzzles), n, len(candidates),
    )
    return puzzles


def sample_diverse(
    n: int = 10,
    seed: int | None = None,
    include_eval_fixtures: int = 2,
    exclude_hashes: set[str] | None = None,
) -> list[TestPuzzle]:
    """Sample a diverse puzzle set mixing DB puzzles and evaluation fixtures.

    Args:
        n: Total puzzles to return.
        seed: Random seed for reproducibility (None = random each time).
        include_eval_fixtures: How many evaluation fixtures to mix in (0 = none).
        exclude_hashes: Puzzle IDs to exclude (prevents repetition across runs).

    Returns:
        List of TestPuzzle with mixed sources and diverse techniques.
    """
    rng = random.Random(seed)
    puzzles: list[TestPuzzle] = []
    exclude = exclude_hashes or set()

    # Mix in evaluation fixtures (professional Cho Chikun puzzles)
    if include_eval_fixtures > 0:
        fixtures = sample_from_evaluation_fixtures(
            n=include_eval_fixtures, seed=seed, exclude_ids=exclude,
        )
        puzzles.extend(fixtures)
        for f in fixtures:
            exclude.add(f.puzzle_id)

    # Fill remaining from DB
    remaining = n - len(puzzles)
    if remaining > 0:
        db_puzzles = sample_from_db(
            n=remaining, seed=seed, exclude_hashes=exclude
        )
        puzzles.extend(db_puzzles)

    # If DB didn't have enough, fill from evaluation fixtures
    if len(puzzles) < n:
        more = sample_from_evaluation_fixtures(
            n=n - len(puzzles), seed=seed, exclude_ids=exclude,
        )
        for p in more:
            if p.puzzle_id not in exclude and len(puzzles) < n:
                puzzles.append(p)
                exclude.add(p.puzzle_id)

    rng.shuffle(puzzles)
    return puzzles[:n]


def puzzles_to_json(puzzles: list[TestPuzzle]) -> list[dict]:
    """Serialize puzzles to JSON-compatible dicts."""
    return [asdict(p) for p in puzzles]


def puzzles_from_json(data: list[dict]) -> list[TestPuzzle]:
    """Deserialize puzzles from JSON dicts."""
    result = []
    for d in data:
        # Remove 'situation' and 'expected_keywords' defaults
        p = TestPuzzle(**{k: v for k, v in d.items() if k in TestPuzzle.__dataclass_fields__})
        result.append(p)
    return result
