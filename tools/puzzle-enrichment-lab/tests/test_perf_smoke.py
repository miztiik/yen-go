"""Performance smoke test — 33 reference puzzles through the enrichment pipeline.

Task P.1.1: Fixture selection and initial smoke test.
Task P.1.2: SGF enrichment review with Go expert (manual, after P.1.1).

These tests are @pytest.mark.slow AND @pytest.mark.integration — they require
KataGo binary and model files. They run real analysis on 33 curated puzzles
spanning the full difficulty range, all canonical tags, and all objectives.

Fixture selection (33 real puzzles from goproblems.com + tsumego-hero.com):

  Core set (10 — difficulty spread + primary objectives):
    #01 novice_ld_9x9           —  9×9,  life-and-death, novice
    #02 beginner_ld_corner      — 19×19, life-and-death, corner, beginner
    #03 elementary_ko           — 19×19, ko problem, elementary
    #04 intermediate_semeai     — 19×19, capture-race, intermediate
    #05 intermediate_seki       — 13×13, seki problem, intermediate
    #06 upper_int_semeai        — 19×19, capture-race, upper-intermediate
    #07 advanced_semeai_ko      — 19×19, capture-race + ko, advanced
    #08 low_dan_ld_edge         — 19×19, life-and-death, edge, low-dan
    #09 novice_tesuji           — 19×19, tesuji (net), novice
    #10 expert_ld_ko            — 19×19, life-and-death + ko, expert

  Tag/technique coverage (23 — one per remaining canonical tag):
    #11 snapback               — 19×19, snapback tesuji, intermediate
    #12 double_atari            — 19×19, double-atari / connection, beginner
    #13 ladder                  — 19×19, ladder, intermediate
    #14 net                     — 19×19, net (geta), intermediate
    #15 throw_in                — 13×13, throw-in (horikomi), novice
    #16 clamp                   — 19×19, clamp (belly attachment), intermediate
    #17 nakade                  — 19×19, nakade (bulky-5), intermediate
    #18 connect_and_die         — 19×19, connect-and-die (oiotoshi), elementary
    #19 under_the_stones        — 13×13, under-the-stones, intermediate
    #20 liberty_shortage         — 19×19, liberty-shortage (semeai), elementary
    #21 vital_point             — 19×19, vital-point L&D, intermediate
    #22 eye_shape               — 13×13, eye-shape recognition, intermediate
    #23 dead_shapes             — 19×19, dead-shapes (nakade form), intermediate
    #24 escape                  — 19×19, escape / connect out, advanced
    #25 connection              — 19×19, connection tesuji, intermediate
    #26 cutting                 — 19×19, cutting tesuji, intermediate
    #27 sacrifice               — 13×13, sacrifice stones, elementary
    #28 corner                  — 19×19, corner L&D, intermediate
    #29 shape                   — 19×19, shape problem, elementary
    #30 endgame                 — 19×19, endgame / yose, elementary
    #31 joseki                  — 19×19, joseki, low-dan
    #32 fuseki                  — 19×19, fuseki / opening, elementary
    #33 living                  — 19×19, black-to-live, elementary

Coverage:
  - Difficulty: novice(3), beginner(2), elementary(8), intermediate(13),
    upper-int(1), advanced(2), low-dan(2), expert(1)
  - Board: 1× 9×9, 4× 13×13, 28× 19×19
  - Tags (28/28): life-and-death, living, ko, seki, snapback, double-atari,
    ladder, net, throw-in, clamp, nakade, connect-and-die, under-the-stones,
    liberty-shortage, vital-point, tesuji, capture-race, eye-shape,
    dead-shapes, escape, connection, cutting, sacrifice, corner, shape,
    endgame, joseki, fuseki
  - Sources: 32× goproblems.com, 1× tsumego-hero.com (#16 clamp)
"""

import json
import time
from pathlib import Path

import pytest

# Ensure tools/puzzle-enrichment-lab is importable
_LAB_DIR = Path(__file__).resolve().parent.parent

from cli import run_batch

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------

_PERF_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "perf-33"

from config.helpers import KATAGO_PATH, model_path

_KATAGO_PATH = KATAGO_PATH
_QUICK_MODEL = model_path("test_fast")    # b10 — fast integration workhorse
_REFEREE_MODEL = model_path("referee")    # b28 — referee tier

_EXPECTED_PUZZLE_COUNT = 33
_TIMEOUT_SECONDS = 1000  # ~17 minutes (proportional: 300s for 10 → ~1000s for 33)

# Per-puzzle expected data for validation
_EXPECTED_SGF_FILES = [
    # Core set (10) — difficulty spread + primary objectives
    "01_novice_ld_9x9.sgf",
    "02_beginner_ld_corner.sgf",
    "03_elementary_ko.sgf",
    "04_intermediate_semeai.sgf",
    "05_intermediate_seki.sgf",
    "06_upper_int_semeai.sgf",
    "07_advanced_semeai_ko.sgf",
    "08_low_dan_ld_edge.sgf",
    "09_novice_tesuji.sgf",
    "10_expert_ld_ko.sgf",
    # Tag/technique coverage (23)
    "11_snapback.sgf",
    "12_double_atari.sgf",
    "13_ladder.sgf",
    "14_net.sgf",
    "15_throw_in.sgf",
    "16_clamp.sgf",
    "17_nakade.sgf",
    "18_connect_and_die.sgf",
    "19_under_the_stones.sgf",
    "20_liberty_shortage.sgf",
    "21_vital_point.sgf",
    "22_eye_shape.sgf",
    "23_dead_shapes.sgf",
    "24_escape.sgf",
    "25_connection.sgf",
    "26_cutting.sgf",
    "27_sacrifice.sgf",
    "28_corner.sgf",
    "29_shape.sgf",
    "30_endgame.sgf",
    "31_joseki.sgf",
    "32_fuseki.sgf",
    "33_living.sgf",
]

# Known source domains for PC[] property validation
_KNOWN_SOURCES = ("goproblems.com", "tsumego-hero.com")


def _get_referee_model() -> str:
    """Return path to referee model, or empty string if unavailable."""
    if _REFEREE_MODEL.exists():
        return str(_REFEREE_MODEL)
    return ""


# Markers for KataGo-dependent tests (TestPerfSmoke only)
_katago_required = [
    pytest.mark.slow,
    pytest.mark.integration,
    pytest.mark.skipif(
        not _KATAGO_PATH.exists(),
        reason=f"KataGo binary not found at {_KATAGO_PATH}",
    ),
    pytest.mark.skipif(
        not _QUICK_MODEL.exists(),
        reason=f"Quick model not found at {_QUICK_MODEL}",
    ),
]


@pytest.mark.slow
@pytest.mark.integration
class TestPerfSmoke:
    """P.1.1 — Smoke test: 33 puzzles through the enrichment pipeline.

    Renamed from test_10_puzzles_* to test_33_puzzles_* after fixture
    expansion (previously 10, now 33 real puzzles).
    """

    @pytest.fixture(autouse=True)
    def _setup_output_dir(self, tmp_path: Path):
        """Create a temporary output directory for batch results."""
        self.output_dir = tmp_path / "perf-33-output"
        self.output_dir.mkdir()

    @pytest.fixture(autouse=True)
    def _verify_fixtures_present(self):
        """Verify all 33 expected SGF fixture files exist."""
        sgf_files = sorted(_PERF_FIXTURES.glob("*.sgf"))
        assert len(sgf_files) == _EXPECTED_PUZZLE_COUNT, (
            f"Expected {_EXPECTED_PUZZLE_COUNT} SGFs in {_PERF_FIXTURES}, "
            f"found {len(sgf_files)}: {[f.name for f in sgf_files]}"
        )
        for expected_name in _EXPECTED_SGF_FILES:
            assert (_PERF_FIXTURES / expected_name).exists(), (
                f"Missing expected fixture: {expected_name}"
            )

    def _run_batch(self) -> tuple[int, float]:
        """Run the batch CLI and return (exit_code, elapsed_seconds)."""
        start = time.monotonic()
        exit_code = run_batch(
            input_dir=str(_PERF_FIXTURES),
            output_dir=str(self.output_dir),
            katago_path=str(_KATAGO_PATH),
            quick_model_path=str(_QUICK_MODEL),
            referee_model_path=_get_referee_model(),
            config_path=None,
        )
        elapsed = time.monotonic() - start
        return exit_code, elapsed

    def test_33_puzzles_complete(self):
        """All 33 puzzles produce valid JSON output files."""
        exit_code, elapsed = self._run_batch()

        # Verify exit code is not a hard crash (0=accepted, 1=rejected, 2=flagged all OK)
        assert exit_code in (0, 1, 2), (
            f"Batch returned unexpected exit code {exit_code}"
        )

        # Check JSON output files
        json_files = sorted(self.output_dir.glob("*.json"))
        assert len(json_files) == _EXPECTED_PUZZLE_COUNT, (
            f"Expected {_EXPECTED_PUZZLE_COUNT} JSON outputs, "
            f"found {len(json_files)}: {[f.name for f in json_files]}"
        )

        # Check enriched SGF output files
        sgf_files = sorted(self.output_dir.glob("*.sgf"))
        assert len(sgf_files) == _EXPECTED_PUZZLE_COUNT, (
            f"Expected {_EXPECTED_PUZZLE_COUNT} enriched SGFs, "
            f"found {len(sgf_files)}: {[f.name for f in sgf_files]}"
        )

        # Validate each JSON output
        for json_file in json_files:
            data = json.loads(json_file.read_text(encoding="utf-8"))

            # Required top-level fields
            assert "puzzle_id" in data, f"{json_file.name}: missing puzzle_id"
            assert "schema_version" in data, f"{json_file.name}: missing schema_version"
            assert "validation" in data, f"{json_file.name}: missing validation"
            assert "difficulty" in data, f"{json_file.name}: missing difficulty"

            # Validation section
            validation = data["validation"]
            assert "status" in validation, f"{json_file.name}: missing validation.status"
            assert validation["status"] in ("accepted", "flagged", "rejected"), (
                f"{json_file.name}: unexpected status '{validation['status']}'"
            )
            assert "correct_move_gtp" in validation, (
                f"{json_file.name}: missing correct_move_gtp"
            )

            # Difficulty section
            difficulty = data["difficulty"]
            assert "suggested_level" in difficulty, (
                f"{json_file.name}: missing difficulty.suggested_level"
            )

            # Refutations section (may be empty list but must exist)
            assert "refutations" in data, f"{json_file.name}: missing refutations"
            assert isinstance(data["refutations"], list), (
                f"{json_file.name}: refutations should be a list"
            )

    def test_33_puzzles_under_timeout(self):
        """Total processing time is under the timeout."""
        _exit_code, elapsed = self._run_batch()

        assert elapsed < _TIMEOUT_SECONDS, (
            f"Batch took {elapsed:.1f}s, exceeds {_TIMEOUT_SECONDS}s timeout "
            f"({elapsed / 60:.1f} min)"
        )


@pytest.mark.unit
class TestPerfFixtureIntegrity:
    """Verify the perf-33 fixture files are well-formed SGFs."""

    @pytest.fixture(params=_EXPECTED_SGF_FILES, ids=_EXPECTED_SGF_FILES)
    def sgf_fixture(self, request) -> tuple[str, str]:
        """Load each fixture SGF and return (filename, text)."""
        path = _PERF_FIXTURES / request.param
        if not path.exists():
            pytest.skip(f"Fixture not found: {request.param}")
        return request.param, path.read_text(encoding="utf-8")

    def test_sgf_has_required_properties(self, sgf_fixture):
        """Each SGF has FF, GM, SZ, PL (or inferable), and stones."""
        name, text = sgf_fixture

        assert "FF[4]" in text, f"{name}: missing FF[4]"
        assert "GM[1]" in text, f"{name}: missing GM[1]"
        assert "SZ[" in text, f"{name}: missing SZ"
        # PL or inferrable from first move
        assert "PL[" in text or ";B[" in text or ";W[" in text, (
            f"{name}: no player to move (PL, B, or W)"
        )
        # Must have stones
        assert "AB[" in text or "AW[" in text, f"{name}: no initial stones"

    def test_sgf_has_solution_tree(self, sgf_fixture):
        """Each SGF has at least one child node with a move (solution tree)."""
        name, text = sgf_fixture
        import re

        # Look for child move: ;B[xx] or ;W[xx]
        has_move = bool(re.search(r';[BW]\[[a-s]{2}\]', text))
        assert has_move, f"{name}: no solution move found (;B[..] or ;W[..])"

    def test_sgf_has_source_reference(self, sgf_fixture):
        """Each SGF has a PC[] (place/source) property with a known source URL."""
        name, text = sgf_fixture
        assert "PC[" in text, f"{name}: missing PC[] source reference"
        assert any(src in text for src in _KNOWN_SOURCES), (
            f"{name}: PC[] should reference a known source "
            f"({', '.join(_KNOWN_SOURCES)})"
        )

    def test_difficulty_spread(self):
        """The 33 fixtures span the intended difficulty range."""
        # This is a structural check — actual difficulty is determined by KataGo
        # Here we verify the file naming convention signals intent
        files = sorted(_PERF_FIXTURES.glob("*.sgf"))
        if not files:
            pytest.skip("No perf fixtures found")

        names = [f.stem for f in files]
        # At least one "beginner" and one "dan" or "expert" puzzle
        assert any("beginner" in n for n in names), "No beginner-level fixture found"
        assert any("dan" in n or "expert" in n for n in names), (
            "No dan/expert-level fixture found"
        )
        # At least one 9x9
        nine_by_nine = 0
        for f in files:
            text = f.read_text(encoding="utf-8")
            if "SZ[9]" in text:
                nine_by_nine += 1
        assert nine_by_nine >= 1, "Need at least one 9×9 puzzle"
        # Board size diversity: at least three different board sizes
        board_sizes = set()
        for f in files:
            text = f.read_text(encoding="utf-8")
            for sz in ("9", "13", "19"):
                if f"SZ[{sz}]" in text:
                    board_sizes.add(sz)
        assert len(board_sizes) >= 3, (
            f"Need at least 3 different board sizes, found: {board_sizes}"
        )
        # Tag/technique diversity: verify technique fixtures exist
        technique_names = {
            "snapback", "double_atari", "ladder", "net", "throw_in",
            "clamp", "nakade", "connect_and_die", "under_the_stones",
            "liberty_shortage", "vital_point", "eye_shape", "dead_shapes",
            "escape", "connection", "cutting", "sacrifice", "corner",
            "shape", "endgame", "joseki", "fuseki", "living",
        }
        found_techniques = {t for t in technique_names if any(t in n for n in names)}
        missing = technique_names - found_techniques
        assert not missing, f"Missing technique fixtures: {sorted(missing)}"
