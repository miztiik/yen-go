"""Tests for collection assignment logic.

Tests: assign_collections() with phrase matching (Tokenized Sequence Matching).
"""

import pytest

from backend.puzzle_manager.core.collection_assigner import assign_collections


@pytest.fixture
def alias_map() -> dict[str, str]:
    """Build a representative alias map for testing."""
    return {
        # Single word alias
        "ladder": "ladder-problems",
        # Multi-word alias (phrase)
        "lee changho": "lee-changho-tesuji",
        "ishida akira": "ishida-tsumego-masterpieces",
        # Directory name style
        "gokyo shumyo": "gokyo-shumyo",
        "enjoy tsumego": "hashimoto-enjoy-tsumego",
    }


class TestPhraseMatching:
    """Spec 128: Tokenized Sequence Matching."""

    def test_single_token_match(self, alias_map: dict[str, str]) -> None:
        """Single token alias matches path."""
        # path contains 'ladder'
        result = assign_collections(
            source_link="problems/ladder/001.sgf",
            puzzle_id="ladder-001",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "ladder-problems" in result

    def test_phrase_match_dashed_path(self, alias_map: dict[str, str]) -> None:
        """Multi-word alias matches dashed path tokens."""
        # path has 'lee-changho', alias is 'lee changho'
        # tokens: ['lee', 'changho'] vs ['lee', 'changho']
        result = assign_collections(
            source_link="problems/2b-lee-changho-tesuji/01.json",
            puzzle_id="sanderland-lee-changho-01",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "lee-changho-tesuji" in result

    def test_phrase_match_spaced_path(self, alias_map: dict[str, str]) -> None:
        """Multi-word alias matches spaced path (unlikely but possible)."""
        result = assign_collections(
            source_link="problems/Ishida Akira Masterpiece/01.json",
            puzzle_id="ishida-01",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "ishida-tsumego-masterpieces" in result

    def test_partial_phrase_no_match(self, alias_map: dict[str, str]) -> None:
        """Partial sequence does not match."""
        # 'lee' alone is not mapped, 'Changho' alone is not mapped.
        # Only 'lee changho' is mapped.
        # Path has 'lee' but not 'changho'
        result = assign_collections(
            source_link="problems/lee-other/01.json",
            puzzle_id="lee-01",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "lee-changho-tesuji" not in result

    def test_interrupted_sequence_no_match(self, alias_map: dict[str, str]) -> None:
        """Sequence must be contiguous."""
        # 'lee' ... 'changho' separated by 'other'
        result = assign_collections(
            source_link="problems/lee-other-changho/01.json",
            puzzle_id="id",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "lee-changho-tesuji" not in result

    def test_directory_boundary_match(self, alias_map: dict[str, str]) -> None:
        """Sequence matches across directory separators (treated as token separators)."""
        # "enjoy tsumego" alias
        # Path: "hashimoto/enjoy/tsumego/01.json" -> tokens [hashimoto, enjoy, tsumego, ...]
        result = assign_collections(
            source_link="hashimoto/enjoy/tsumego/01.json",
            puzzle_id="id",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "hashimoto-enjoy-tsumego" in result

    def test_normalization(self, alias_map: dict[str, str]) -> None:
        """Matching is case-insensitive and normalized."""
        result = assign_collections(
            source_link="problems/LEE-CHANGHO/01.json",
            puzzle_id="id",
            existing_collections=[],
            alias_map=alias_map,
        )
        assert "lee-changho-tesuji" in result

class TestRealWorldScenarios:
    """Tests confirming fixes for identified issues (e.g. Cho Chikun)."""

    @pytest.fixture
    def real_world_alias_map(self) -> dict[str, str]:
        """Partial alias map reflecting production config/collections.json."""
        return {
            # Verified updated aliases for Cho Chikun
            "cho elementary": "cho-chikun-life-death-elementary",
            "encyclopedia life death elementary": "cho-chikun-life-death-elementary",
            "encyclopedia life and death elementary": "cho-chikun-life-death-elementary",

            "cho intermediate": "cho-chikun-life-death-intermediate",
            "encyclopedia life death intermediate": "cho-chikun-life-death-intermediate",
            "encyclopedia life and death intermediate": "cho-chikun-life-death-intermediate",

            # Other real examples
            "hashimoto-1-year-tsumego": "hashimoto-1-year-tsumego",
            "1 year tsumego": "hashimoto-1-year-tsumego",
            "gokyo shumyo": "gokyo-shumyo",
            "shumyo": "gokyo-shumyo",
            "igo hatsuyoron": "igo-hatsuyoron",
            "fundamental l&d": "life-and-death",
        }

    def test_cho_chikun_elementary_long_path(self, real_world_alias_map: dict[str, str]) -> None:
        """Verify 'Encyclopedia Life And Death - Elementary' matches new aliases."""
        path = "sanderland/1a-tsumego-beginner/Cho Chikun Encyclopedia Life And Death - Elementary/Prob0001.json"
        result = assign_collections(
            source_link=path,
            puzzle_id="Prob0001",
            existing_collections=[],
            alias_map=real_world_alias_map,
        )
        assert "cho-chikun-life-death-elementary" in result

    def test_cho_chikun_intermediate_long_path(self, real_world_alias_map: dict[str, str]) -> None:
        """Verify 'Encyclopedia Life And Death - Intermediate' matches new aliases."""
        path = "sanderland/1a-tsumego-beginner/Cho Chikun Encyclopedia Life And Death - Intermediate/Prob0001.json"
        result = assign_collections(
            source_link=path,
            puzzle_id="Prob0001",
            existing_collections=[],
            alias_map=real_world_alias_map,
        )
        assert "cho-chikun-life-death-intermediate" in result

    def test_igo_hatsuyoron_match(self, real_world_alias_map: dict[str, str]) -> None:
        """Verify Igo Hatsuyoron matching."""
        path = "some/path/Igo Hatsuyoron/file.sgf"
        result = assign_collections(
            source_link=path,
            puzzle_id="id",
            existing_collections=[],
            alias_map=real_world_alias_map,
        )
        assert "igo-hatsuyoron" in result

    def test_gokyo_shumyo_fallback_match(self, real_world_alias_map: dict[str, str]) -> None:
        """Verify matching on broad alias 'shumyo'."""
        path = "some/random/path/Gokyo Shumyo/file.sgf"
        result = assign_collections(
            source_link=path,
            puzzle_id="id",
            existing_collections=[],
            alias_map=real_world_alias_map,
        )
        assert "gokyo-shumyo" in result

    def test_hashimoto_year_match(self, real_world_alias_map: dict[str, str]) -> None:
        """Verify matching for Hashimoto 1 Year."""
        path = "kisvadim/hashimoto/1 Year Tsumego/problem.sgf"
        result = assign_collections(
            source_link=path,
            puzzle_id="id",
            existing_collections=[],
            alias_map=real_world_alias_map,
        )
        assert "hashimoto-1-year-tsumego" in result
