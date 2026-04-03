"""Tests for fixture coverage — verifying all 28 tags have valid SGF fixtures.

This test suite exists to provide confidence that:
1. Every tag in config/tags.json has a corresponding fixture SGF.
2. Every fixture SGF is structurally valid (parseable, has a correct move,
   has at least one wrong branch with C[Wrong...] annotation).
3. The YT property in each fixture matches the expected tag slug.
4. The fixture can be dispatched by the tag-aware validator without crashing.
5. The "wrong answer → engine catches it" path is smoke-tested per technique.

Coverage goal: broad technique coverage so AI/model decisions are grounded
in empirical ground truth for every known technique category.

Integration tests (marked @pytest.mark.integration) require a real KataGo
engine binary in tools/puzzle-enrichment-lab/katago/katago.exe and a model
in tools/puzzle-enrichment-lab/models-data/*.bin.gz — they are skipped in CI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_LAB = _HERE.parent
from analyzers.validate_correct_move import ValidationStatus, validate_correct_move
from core.tsumego_analysis import (
    extract_correct_first_move,
    extract_position,
    parse_sgf,
)

FIXTURES = _HERE / "fixtures"

# ---------------------------------------------------------------------------
# Authoritative tag registration — derived from config/tags.json
#
# Each entry: (fixture_filename, tag_slug, expected_yt_substring)
#
# We do NOT load config/tags.json at test time — the test data is explicit
# so that any mismatch between the fixture and the config is visible
# as a clear assertion failure rather than a silent config miss.
# ---------------------------------------------------------------------------

# Non-tsumego tags excluded from fixture coverage (C2 governance decision).
# These tags exist in config/tags.json but are not testable as tsumego puzzles.
EXCLUDED_NON_TSUMEGO_TAGS: set[str] = {"joseki", "fuseki", "endgame"}

# fmt: off
ALL_TAG_FIXTURES: list[tuple[str, str, str]] = [
    # --- Objectives ---
    ("simple_life_death.sgf",   "life-and-death",  "life-and-death"),
    ("life_death_tagged.sgf",   "life-and-death",  "life-and-death"),
    ("living_puzzle.sgf",       "living",           "living"),
    ("ko_direct.sgf",           "ko",               "ko"),
    ("ko_approach.sgf",         "ko",               "ko"),
    ("ko_10000year.sgf",        "ko",               "ko"),
    ("ko_double.sgf",           "ko",               "ko"),
    ("ko_multistep.sgf",        "ko",               "ko"),
    ("seki_puzzle.sgf",         "seki",             "seki"),
    ("capture_race.sgf",        "capture-race",     "capture-race"),
    # --- Tesuji techniques ---
    ("snapback_puzzle.sgf",     "snapback",         "snapback"),
    ("double_atari.sgf",        "double-atari",     "double-atari"),
    ("ladder_puzzle.sgf",       "ladder",           "ladder"),
    ("net_puzzle.sgf",          "net",              "net"),
    ("throw_in.sgf",            "throw-in",         "throw-in"),
    ("clamp.sgf",               "clamp",            "clamp"),
    ("nakade.sgf",              "nakade",           "nakade"),
    ("connect_and_die.sgf",     "connect-and-die",  "connect-and-die"),
    ("under_the_stones.sgf",    "under-the-stones", "under-the-stones"),
    ("liberty_shortage.sgf",    "liberty-shortage",  "liberty-shortage"),
    ("vital_point.sgf",         "vital-point",      "vital-point"),
    ("tesuji.sgf",              "tesuji",           "tesuji"),
    # --- Techniques ---
    ("eye_shape.sgf",           "eye-shape",        "eye-shape"),
    ("dead_shapes.sgf",         "dead-shapes",      "dead-shapes"),
    ("escape.sgf",              "escape",           "escape"),
    ("connection_puzzle.sgf",   "connection",       "connection"),
    ("cutting.sgf",             "cutting",          "cutting"),
    ("sacrifice.sgf",           "sacrifice",        "sacrifice"),
    ("corner.sgf",              "corner",           "corner"),
    ("shape.sgf",               "shape",            "shape"),
]
# fmt: on

# Deduplicated fixture list for structural validation
UNIQUE_FIXTURES: list[str] = sorted(
    {fname for fname, _, _ in ALL_TAG_FIXTURES}
)


# ---------------------------------------------------------------------------
# Helper: extract YT property from raw SGF text
# ---------------------------------------------------------------------------

def _extract_yt(sgf_text: str) -> str:
    """Return the raw YT value from the SGF root node."""
    import re
    m = re.search(r"YT\[([^\]]*)\]", sgf_text)
    return m.group(1) if m else ""


def _extract_pc(sgf_text: str) -> str:
    """Return the raw PC value from the SGF root node."""
    import re
    m = re.search(r"PC\[([^\]]*)\]", sgf_text)
    return m.group(1) if m else ""


def _has_wrong_branch(sgf_text: str) -> bool:
    """Return True if any node has a C[Wrong...] comment."""
    import re
    return bool(re.search(r"C\[Wrong", sgf_text))


# ---------------------------------------------------------------------------
# 1. Structural integrity — every fixture referenced must exist and be valid
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFixtureFilesExist:
    """Verify every fixture file exists and is non-empty."""

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_file_exists(self, fname: str) -> None:
        """Fixture file must exist in tests/fixtures/."""
        path = FIXTURES / fname
        assert path.exists(), f"Fixture not found: fixtures/{fname}"
        assert path.stat().st_size > 0, f"Fixture is empty: fixtures/{fname}"


@pytest.mark.unit
class TestFixtureStructure:
    """Verify every fixture parses correctly and has required structural elements."""

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_parses_without_error(self, fname: str) -> None:
        """Every fixture SGF must parse without raising an exception."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        assert root is not None

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_has_correct_first_move(self, fname: str) -> None:
        """Every fixture must have at least one move in the main line (correct move)."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        correct = extract_correct_first_move(root)
        assert correct is not None, (
            f"fixtures/{fname} has no correct first move in main line"
        )
        assert len(correct) == 2, (
            f"fixtures/{fname} correct move coord '{correct}' is not length-2 SGF coord"
        )

    @pytest.mark.parametrize("fname", [
        # Lab-built fixtures with explicit C[Wrong...] annotations.
        # Goproblems-sourced fixtures use RIGHT/non-RIGHT convention instead.
        "throw_in.sgf",
        "clamp.sgf",
        "nakade.sgf",
        "connect_and_die.sgf",
        "under_the_stones.sgf",
        "liberty_shortage.sgf",
        "double_atari.sgf",
        "vital_point.sgf",
        "eye_shape.sgf",
        "dead_shapes.sgf",
        "escape.sgf",
        "sacrifice.sgf",
        "corner.sgf",
    ])
    def test_has_wrong_branch(self, fname: str) -> None:
        """Fixture must contain at least one wrong branch annotated C[Wrong...]."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        assert _has_wrong_branch(sgf), (
            f"fixtures/{fname} has no wrong branch — "
            "add at least one branch with C[Wrong...] comment"
        )

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_board_size_valid(self, fname: str) -> None:
        """Board size must be 9 or 19 (tsumego standard sizes)."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        sz = int(root.get("SZ", "19"))
        assert sz in (9, 13, 19), (
            f"fixtures/{fname} has unusual board size {sz}"
        )

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_has_yt_property(self, fname: str) -> None:
        """Every fixture must declare at least one tag via YT property."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        yt = _extract_yt(sgf)
        assert yt, (
            f"fixtures/{fname} is missing YT property — add YT[tag-slug] to root"
        )


# ---------------------------------------------------------------------------
# 2. Tag coverage — every tag has at least one fixture with that YT value
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestTagCoverage:
    """Verify every known tag slug appears in at least one fixture's YT property."""

    # Canonical list of 25 active tsumego tag slugs from config/tags.json.
    # 3 non-tsumego tags (joseki, fuseki, endgame) are excluded per C2.
    ALL_KNOWN_TAG_SLUGS: list[str] = [
        "life-and-death",   # 10
        "living",           # 14 (was "miai" — fixed per C3)
        "ko",               # 12
        "seki",             # 16
        "capture-race",     # 60
        "double-atari",     # 32
        "ladder",           # 34
        "net",              # 36
        "throw-in",         # 38
        "clamp",            # 40
        "nakade",           # 42
        "connect-and-die",  # 44
        "under-the-stones", # 46
        "liberty-shortage", # 48
        "vital-point",      # 50
        "tesuji",           # 52
        "snapback",         # 30
        "connection",       # 68
        "eye-shape",        # 62
        "dead-shapes",      # 64
        "escape",           # 66
        "cutting",          # 70
        "sacrifice",        # 72
        "corner",           # 74
        "shape",            # 76
    ]

    def _all_yt_values(self) -> list[str]:
        """Collect all YT values from all fixture files."""
        yt_values: list[str] = []
        for fpath in sorted(FIXTURES.glob("*.sgf")):
            sgf = fpath.read_text(encoding="utf-8")
            yt = _extract_yt(sgf)
            if yt:
                # YT can be comma-separated: "ko,ladder,life-and-death"
                yt_values.extend(t.strip() for t in yt.split(","))
        return yt_values

    @pytest.mark.parametrize("slug", ALL_KNOWN_TAG_SLUGS)
    def test_tag_has_fixture(self, slug: str) -> None:
        """Every tag slug must appear in at least one fixture's YT property."""
        all_yt = self._all_yt_values()
        assert slug in all_yt, (
            f"Tag '{slug}' has no fixture — create a fixture with YT[{slug}]"
        )


# ---------------------------------------------------------------------------
# 3. PC property — Sensei's Library reference present in new fixtures
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestSenseisReferences:
    """Spot-check that new fixtures include a Sensei's Library PC[] property."""

    @pytest.mark.parametrize("fname,expected_fragment", [
        ("throw_in.sgf",           "ThrowIn"),
        ("clamp.sgf",              "Clamp"),
        ("nakade.sgf",             "Nakade"),
        ("connect_and_die.sgf",    "Oiotoshi"),
        ("under_the_stones.sgf",   "UnderTheStones"),
        ("liberty_shortage.sgf",   "ShortageOfLiberties"),
        ("double_atari.sgf",       "DoubleAtari"),
        ("vital_point.sgf",        "VitalPoint"),
        ("eye_shape.sgf",          "EyeShape"),
        ("dead_shapes.sgf",        "KillableEyeshapes"),
        ("escape.sgf",             "Escape"),
        ("sacrifice.sgf",          "Sacrifice"),
        ("corner.sgf",             "CornerShapes"),
    ])
    def test_pc_contains_senseis_fragment(self, fname: str, expected_fragment: str) -> None:
        """Each new fixture must have a PC[] pointing to Sensei's Library."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        pc = _extract_pc(sgf)
        assert "senseis.xmp.net" in pc, (
            f"fixtures/{fname} PC property does not point to Sensei's Library: '{pc}'"
        )
        assert expected_fragment in pc, (
            f"fixtures/{fname} PC property '{pc}' does not mention '{expected_fragment}'"
        )


# ---------------------------------------------------------------------------
# 4. Dispatch compatibility — every fixture's YT tag is recognised by the
#    tag-aware dispatcher without throwing exceptions
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDispatchCompatibility:
    """Verify each fixture's primary tag dispatches to a known validator bucket."""

    FIXTURE_TAG_IDS: dict[str, list[int]] = {
        # Maps fixture filename → list of numeric tag IDs for dispatch
        "simple_life_death.sgf":    [10],
        "ladder_puzzle.sgf":        [34],
        "net_puzzle.sgf":           [36],
        "snapback_puzzle.sgf":      [30],
        "ko_direct.sgf":            [12],
        "seki_puzzle.sgf":          [16],
        "capture_race.sgf":         [60],
        "connection_puzzle.sgf":    [68],
        "miai_puzzle.sgf":          [10],
        "life_death_tagged.sgf":    [10],
        "living_puzzle.sgf":        [14],
        "double_atari.sgf":         [32],
        "throw_in.sgf":             [38],
        "clamp.sgf":                [40],
        "nakade.sgf":               [42],
        "connect_and_die.sgf":      [44],
        "under_the_stones.sgf":     [46],
        "liberty_shortage.sgf":     [48],
        "vital_point.sgf":          [50],
        "tesuji.sgf":               [52],
        "eye_shape.sgf":            [62],
        "dead_shapes.sgf":          [64],
        "escape.sgf":               [66],
        "cutting.sgf":              [70],
        "sacrifice.sgf":            [72],
        "corner.sgf":               [74],
        "shape.sgf":                [76],
    }

    @pytest.mark.parametrize("fname,tag_ids", list(FIXTURE_TAG_IDS.items()))
    def test_dispatch_does_not_raise(self, fname: str, tag_ids: list[int]) -> None:
        """Dispatching by tag IDs must not raise KeyError or AttributeError."""
        from analyzers.validate_correct_move import _dispatch_by_tags
        # Should return a string name, not raise
        result = _dispatch_by_tags(tag_ids)
        assert isinstance(result, str), (
            f"_dispatch_by_tags({tag_ids}) for {fname} returned {result!r}, expected str"
        )
        assert result in {
            "life_and_death", "ko", "seki", "capture_race",
            "tactical", "connection",
        }, (
            f"_dispatch_by_tags({tag_ids}) for {fname} returned unknown validator '{result}'"
        )


# ---------------------------------------------------------------------------
# 5. Position extraction — every fixture position can be extracted
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestPositionExtraction:
    """Verify extract_position works on all fixtures without error."""

    @pytest.mark.parametrize("fname", UNIQUE_FIXTURES)
    def test_extract_position(self, fname: str) -> None:
        """extract_position must succeed for every fixture."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        pos = extract_position(root)
        assert pos is not None
        assert pos.board_size in (9, 13, 19)
        # Should have at least one stone for a puzzle to make sense
        # (board_9x9 is an exception — it's a template)
        if fname != "board_9x9.sgf":
            assert len(pos.stones) > 0, (
                f"fixtures/{fname} position has no stones — is this a valid puzzle?"
            )


# ---------------------------------------------------------------------------
# 6. Wrong-branch detection — validate the adversarial paths are present
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestWrongBranchSanity:
    """Verify the wrong branches in new fixtures are structurally complete."""

    @pytest.mark.parametrize("fname", [
        "throw_in.sgf", "clamp.sgf", "nakade.sgf", "connect_and_die.sgf",
        "under_the_stones.sgf", "liberty_shortage.sgf", "double_atari.sgf",
        "vital_point.sgf", "eye_shape.sgf", "dead_shapes.sgf",
        "escape.sgf", "sacrifice.sgf", "corner.sgf",
    ])
    def test_wrong_branch_present(self, fname: str) -> None:
        """New fixture must have at least one wrong-move branch."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        assert _has_wrong_branch(sgf), (
            f"fixtures/{fname} lacks a C[Wrong...] annotated branch. "
            "Add wrong-move variations so AI can be tested against them."
        )

    @pytest.mark.parametrize("fname", [
        "throw_in.sgf", "clamp.sgf", "nakade.sgf", "connect_and_die.sgf",
        "under_the_stones.sgf", "liberty_shortage.sgf", "double_atari.sgf",
        "vital_point.sgf", "eye_shape.sgf", "dead_shapes.sgf",
        "escape.sgf", "sacrifice.sgf", "corner.sgf",
    ])
    def test_root_has_children(self, fname: str) -> None:
        """The parsed tree must have at least 2 children (correct + wrong branches)."""
        sgf = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf)
        # Each new fixture has a correct main line + at least one wrong variation
        # The root's first child is the correct move node, which has branches
        assert root.children, f"fixtures/{fname} root has no children"
        first_child = root.children[0]
        # First child should have at least one alternative (wrong branch)
        # OR the wrong branch is a sibling at root level (both are valid SGF styles)
        total_branches = len(root.children) + len(first_child.children)
        assert total_branches >= 2, (
            f"fixtures/{fname} needs at least 2 branches (correct + wrong) — "
            f"found root children={len(root.children)}, first_child children={len(first_child.children)}"
        )


# ---------------------------------------------------------------------------
# 7. Smoke test — validate_correct_move with mocked response per tag
#    (no real engine required — tests the dispatch + validator plumbing)
# ---------------------------------------------------------------------------

from models.analysis_response import AnalysisResponse, MoveAnalysis


def _mock_accept_response(correct_move_gtp: str) -> AnalysisResponse:
    """Mock response where KataGo agrees with the correct move."""
    return AnalysisResponse(
        request_id="mock",
        move_infos=[
            MoveAnalysis(
                move=correct_move_gtp,
                visits=100,
                winrate=0.92,
                policy_prior=0.65,
                pv=[correct_move_gtp],
            )
        ],
        root_winrate=0.85,
        root_score=5.0,
        total_visits=200,
    )


def _mock_reject_response(correct_move_gtp: str) -> AnalysisResponse:
    """Mock response where KataGo disagrees — top move is somewhere else entirely."""
    wrong_move = "A1" if correct_move_gtp != "A1" else "B2"
    return AnalysisResponse(
        request_id="mock",
        move_infos=[
            MoveAnalysis(
                move=wrong_move,
                visits=100,
                winrate=0.95,
                policy_prior=0.75,
                pv=[wrong_move],
            )
        ],
        root_winrate=0.92,
        root_score=8.0,
        total_visits=200,
    )


@pytest.mark.unit
class TestSmokeMockedDispatchPerTechnique:
    """Per-technique smoke tests: correct move → ACCEPTED, wrong move → REJECTED/FLAGGED.

    This is the 'give the puzzle with wrong answer and expect the engine to catch it'
    test for all technique categories, using mocked engine responses.

    The mock directly simulates the engine's decision: the correct response accepts
    the correct move; the reject response puts a totally different move at the top.
    """

    TECHNIQUE_CASES: list[tuple[str, list[int], str, str]] = [
        # (fixture, tag_ids, correct_sgf_coord, corner)
        ("simple_life_death.sgf",   [10],  "br", "BL"),
        ("living_puzzle.sgf",      [14],  "ba", "TL"),
        ("throw_in.sgf",           [38],  "bb", "TL"),
        ("clamp.sgf",              [40],  "cb", "TL"),
        ("nakade.sgf",             [42],  "cb", "TL"),
        ("connect_and_die.sgf",    [44],  "db", "TL"),
        ("under_the_stones.sgf",   [46],  "bb", "TL"),
        ("liberty_shortage.sgf",   [48],  "ee", "C"),
        ("double_atari.sgf",       [32],  "cb", "TL"),
        ("vital_point.sgf",        [50],  "ca", "TL"),
        ("tesuji.sgf",             [52],  "es", "BL"),
        ("eye_shape.sgf",          [62],  "ea", "TL"),
        ("dead_shapes.sgf",        [64],  "cb", "TL"),
        ("escape.sgf",             [66],  "ac", "TL"),
        ("cutting.sgf",            [70],  "of", "TR"),
        ("sacrifice.sgf",          [72],  "ea", "TL"),
        ("corner.sgf",             [74],  "cc", "TL"),
        ("shape.sgf",              [76],  "sg", "TR"),
        ("ladder_puzzle.sgf",      [34],  None, "TL"),  # correct move from fixture
        ("net_puzzle.sgf",         [36],  None, "TL"),
        ("snapback_puzzle.sgf",    [30],  None, "TL"),
        ("capture_race.sgf",       [60],  None, "TL"),
        ("connection_puzzle.sgf",  [68],  None, "TL"),
        ("seki_puzzle.sgf",        [16],  None, "TL"),
        ("miai_puzzle.sgf",        [10],  None, "TL"),
    ]

    @pytest.mark.parametrize("fname,tag_ids,correct_sgf,corner", TECHNIQUE_CASES)
    def test_correct_move_accepted_by_mocked_engine(
        self,
        fname: str,
        tag_ids: list[int],
        correct_sgf: str | None,
        corner: str,
    ) -> None:
        """Mocked engine agreeing with correct move → ACCEPTED (not REJECTED)."""
        from models.analysis_response import sgf_to_gtp

        sgf_text = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf_text)

        if correct_sgf is None:
            correct_sgf = extract_correct_first_move(root)

        assert correct_sgf is not None, f"No correct move in {fname}"

        pos = extract_position(root)
        correct_gtp = sgf_to_gtp(correct_sgf, pos.board_size)
        response = _mock_accept_response(correct_gtp)

        result = validate_correct_move(
            response=response,
            correct_move_gtp=correct_gtp,
            tags=tag_ids,
            corner=corner,
        )
        assert result.status != ValidationStatus.REJECTED, (
            f"[{fname}] tags={tag_ids}: correct move {correct_gtp} "
            f"should not be REJECTED when engine agrees — got {result.status}"
        )

    @pytest.mark.parametrize("fname,tag_ids,correct_sgf,corner", TECHNIQUE_CASES)
    def test_wrong_move_not_accepted_by_mocked_engine(
        self,
        fname: str,
        tag_ids: list[int],
        correct_sgf: str | None,
        corner: str,
    ) -> None:
        """Mocked engine disagreeing (putting another move at top) → REJECTED or FLAGGED.

        This is the 'wrong answer → engine catches it' test for every technique.
        """
        from models.analysis_response import sgf_to_gtp

        sgf_text = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf_text)

        if correct_sgf is None:
            correct_sgf = extract_correct_first_move(root)

        assert correct_sgf is not None, f"No correct move in {fname}"

        pos = extract_position(root)
        correct_gtp = sgf_to_gtp(correct_sgf, pos.board_size)
        response = _mock_reject_response(correct_gtp)

        result = validate_correct_move(
            response=response,
            correct_move_gtp=correct_gtp,
            tags=tag_ids,
            corner=corner,
        )
        assert result.status in (ValidationStatus.REJECTED, ValidationStatus.FLAGGED), (
            f"[{fname}] tags={tag_ids}: when engine disagrees with {correct_gtp}, "
            f"expected REJECTED or FLAGGED — got {result.status}"
        )


# ---------------------------------------------------------------------------
# 8. Integration tests — real KataGo engine (skipped if binary absent)
#    Uses shared integration_engine fixture from conftest.py (D42).
# ---------------------------------------------------------------------------

from config.helpers import KATAGO_PATH, model_path


@pytest.mark.integration
@pytest.mark.skipif(
    not KATAGO_PATH.exists(),
    reason="KataGo binary not found",
)
@pytest.mark.skipif(
    not model_path("test_smallest").exists(),
    reason="Model file not found",
)
class TestIntegrationNewFixtures:
    """Integration tests: real engine validates new technique-specific fixtures.

    Tests:
    - Correct move from fixture → engine accepts (ACCEPTED or FLAGGED)
    - Deliberately wrong move → engine rejects (REJECTED or FLAGGED)

    These are the definitive 'wrong answer → engine catches it' tests for
    categories previously lacking fixture coverage.
    """

    # Subset chosen to be engine-verifiable with b6 model (3.6MB).
    # Positions must be simple enough for the smallest model to evaluate correctly.
    # dead_shapes.sgf and throw_in.sgf excluded: Go-correct but b6 too weak.
    INTEGRATION_FIXTURES: list[tuple[str, list[int], str]] = [
        # simple_life_death.sgf excluded: 19x19 internal-capture too complex for b6
        ("nakade.sgf",             [42],  "TL"),
        ("double_atari.sgf",       [32],  "TL"),
    ]

    @pytest.mark.parametrize("fname,tag_ids,corner", INTEGRATION_FIXTURES)
    def test_correct_move_accepted_by_real_engine(
        self,
        fname: str,
        tag_ids: list[int],
        corner: str,
        integration_engine,
    ) -> None:
        """Real engine should not reject the correct move from these fixtures."""
        from analyzers.query_builder import build_query_from_sgf
        from models.analysis_response import sgf_to_gtp

        sgf_text = (FIXTURES / fname).read_text(encoding="utf-8")
        root = parse_sgf(sgf_text)
        correct_sgf = extract_correct_first_move(root)
        assert correct_sgf is not None

        pos = extract_position(root)
        correct_gtp = sgf_to_gtp(correct_sgf, pos.board_size)

        request = build_query_from_sgf(sgf_text, max_visits=1000)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(request.request), timeout=60.0
            )
            return validate_correct_move(
                response=response,
                correct_move_gtp=correct_gtp,
                tags=tag_ids,
                corner=corner,
            )

        result = asyncio.run(_run())
        # Should never be REJECTED — a known valid puzzle's correct move
        # must register as at minimum FLAGGED with the real engine.
        assert result.status in (ValidationStatus.ACCEPTED, ValidationStatus.FLAGGED), (
            f"[{fname}] Real engine unexpectedly REJECTED correct move {correct_gtp}. "
            "If this fixture's position is wrong, fix the SGF."
        )

    @pytest.mark.parametrize("fname,tag_ids,corner", INTEGRATION_FIXTURES)
    def test_wrong_move_caught_by_real_engine(
        self,
        fname: str,
        tag_ids: list[int],
        corner: str,
        integration_engine,
    ) -> None:
        """Real engine should catch a deliberately wrong first move as REJECTED/FLAGGED.

        This is the definitive 'give puzzle with wrong answer, expect engine to catch it'
        test using real KataGo analysis.

        We inject 'pass' (tt in SGF coords) as the 'correct' move — always wrong in tsumego.
        """
        from analyzers.query_builder import build_query_from_sgf

        sgf_text = (FIXTURES / fname).read_text(encoding="utf-8")
        extract_position(parse_sgf(sgf_text))

        # 'pass' is always wrong in a life-and-death tsumego puzzle
        dummy_wrong_gtp = "pass"

        request = build_query_from_sgf(sgf_text, max_visits=1000)

        async def _run():
            response = await asyncio.wait_for(
                integration_engine.analyze(request.request), timeout=60.0
            )
            return validate_correct_move(
                response=response,
                correct_move_gtp=dummy_wrong_gtp,
                tags=tag_ids,
                corner=corner,
            )

        result = asyncio.run(_run())
        assert result.status in (ValidationStatus.REJECTED, ValidationStatus.FLAGGED), (
            f"[{fname}] Real engine accepted 'pass' as a correct move — "
            "this means the engine validation is too permissive."
        )
