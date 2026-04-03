"""Unit tests for expanded tag taxonomy (Spec 126, Phase 3).

Validates:
- config/tags.json v6.0 loads correctly with 28 tags
- All adapter tag mappings produce only approved tags
- Tag deduplication and sorting in YT[] output
- Flat taxonomy guard: no colons or hierarchical syntax in tag IDs (FR-007)
"""

import json
import re
from pathlib import Path

# =============================================================================
# Helpers
# =============================================================================

def _load_tags_json() -> dict:
    """Load config/tags.json from global config directory."""
    tags_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "tags.json"
    assert tags_path.exists(), f"tags.json not found at {tags_path}"
    with open(tags_path, encoding="utf-8") as f:
        return json.load(f)


def _get_approved_tag_ids() -> set[str]:
    """Get the set of approved tag IDs from config/tags.json."""
    data = _load_tags_json()
    return set(data["tags"].keys())


# =============================================================================
# Tests: config/tags.json Structure
# =============================================================================

class TestTagsJsonStructure:
    """Validates config/tags.json structure and content."""

    def test_has_28_tags(self) -> None:
        """tags.json should contain exactly 28 tags."""
        data = _load_tags_json()
        assert len(data["tags"]) == 28, (
            f"Expected 28 tags, got {len(data['tags'])}: {sorted(data['tags'].keys())}"
        )

    def test_all_18_original_tags_preserved(self) -> None:
        """All 18 original tags from v5.0 must be preserved (additive only)."""
        original_tags = {
            "life-and-death", "living", "ko", "seki",
            "capture-race", "escape",
            "snapback", "throw-in", "ladder", "net",
            "liberty-shortage", "connect-and-die", "under-the-stones",
            "double-atari", "vital-point", "clamp",
            "eye-shape", "dead-shapes",
        }
        tag_ids = _get_approved_tag_ids()
        missing = original_tags - tag_ids
        assert not missing, f"Original tags missing: {missing}"

    def test_all_10_new_tags_present(self) -> None:
        """All 10 new Spec 126 tags should be present."""
        new_tags = {
            "nakade", "connection", "cutting", "corner",
            "sacrifice", "shape", "endgame", "tesuji",
            "joseki", "fuseki",
        }
        tag_ids = _get_approved_tag_ids()
        missing = new_tags - tag_ids
        assert not missing, f"New tags missing: {missing}"

    def test_each_tag_has_required_fields(self) -> None:
        """Each tag must have id, name, category, description, aliases."""
        data = _load_tags_json()
        required_fields = {"slug", "id", "name", "category", "description", "aliases"}
        for tag_id, tag_data in data["tags"].items():
            actual_fields = set(tag_data.keys())
            missing = required_fields - actual_fields
            assert not missing, f"Tag '{tag_id}' missing fields: {missing}"

    def test_tag_slug_matches_key(self) -> None:
        """Each tag's 'slug' field must match its key in the tags dict."""
        data = _load_tags_json()
        for key, tag_data in data["tags"].items():
            assert tag_data["slug"] == key, (
                f"Tag key '{key}' doesn't match slug '{tag_data['slug']}'"
            )

    def test_valid_categories(self) -> None:
        """Each tag must have a valid category."""
        valid_categories = {"objective", "technique", "tesuji"}
        data = _load_tags_json()
        for tag_id, tag_data in data["tags"].items():
            cat = tag_data["category"]
            assert cat in valid_categories, (
                f"Tag '{tag_id}' has invalid category '{cat}'"
            )

    def test_no_hierarchical_tag_ids(self) -> None:
        """No tag ID should contain colons or hierarchical syntax (FR-007)."""
        tag_ids = _get_approved_tag_ids()
        for tag_id in tag_ids:
            assert ":" not in tag_id, f"Tag '{tag_id}' contains colon (hierarchical)"
            assert "/" not in tag_id, f"Tag '{tag_id}' contains slash (hierarchical)"
            assert "." not in tag_id, f"Tag '{tag_id}' contains dot (hierarchical)"

    def test_tag_ids_are_lowercase_kebab_case(self) -> None:
        """All tag IDs should be lowercase kebab-case."""
        tag_ids = _get_approved_tag_ids()
        pattern = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
        for tag_id in tag_ids:
            assert pattern.match(tag_id), (
                f"Tag '{tag_id}' is not valid kebab-case"
            )

    def test_aliases_are_lists(self) -> None:
        """All aliases should be lists of strings."""
        data = _load_tags_json()
        for tag_id, tag_data in data["tags"].items():
            aliases = tag_data["aliases"]
            assert isinstance(aliases, list), f"Tag '{tag_id}' aliases not a list"
            assert all(isinstance(a, str) for a in aliases), (
                f"Tag '{tag_id}' has non-string alias"
            )

    def test_no_duplicate_aliases_across_tags(self) -> None:
        """No alias should map to multiple tags."""
        data = _load_tags_json()
        seen: dict[str, str] = {}
        duplicates: list[str] = []
        for tag_id, tag_data in data["tags"].items():
            for alias in tag_data.get("aliases", []):
                alias_lower = alias.lower()
                if alias_lower in seen and seen[alias_lower] != tag_id:
                    duplicates.append(
                        f"'{alias}' maps to both '{seen[alias_lower]}' and '{tag_id}'"
                    )
                seen[alias_lower] = tag_id
        assert not duplicates, f"Duplicate aliases: {duplicates}"


# =============================================================================
# Tests: Adapter Tag Mappings
# =============================================================================

class TestOgsAdapterTags:
    """Verify OGS adapter produces only approved tags."""

    def test_all_mapped_tags_are_approved(self) -> None:
        """All non-None OGS_TYPE_TO_TAG values must be in tags.json."""
        import sys
        # Import from tools/ogs/tags.py
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.ogs.tags import OGS_TYPE_TO_TAG
        finally:
            sys.path.pop(0)

        approved = _get_approved_tag_ids()
        for ogs_type, yengo_tag in OGS_TYPE_TO_TAG.items():
            if yengo_tag is not None:
                assert yengo_tag in approved, (
                    f"OGS type '{ogs_type}' maps to unapproved tag '{yengo_tag}'"
                )

    def test_maps_fuseki_joseki_endgame(self) -> None:
        """OGS should now map fuseki, joseki, endgame to valid tags."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.ogs.tags import OGS_TYPE_TO_TAG
        finally:
            sys.path.pop(0)

        assert OGS_TYPE_TO_TAG["fuseki"] == "fuseki"
        assert OGS_TYPE_TO_TAG["joseki"] == "joseki"
        assert OGS_TYPE_TO_TAG["endgame"] == "endgame"
        assert OGS_TYPE_TO_TAG["tesuji"] == "tesuji"


class TestTsumegoDragonAdapterTags:
    """Verify TsumegoDragon adapter produces only approved tags."""

    def test_all_mapped_tags_are_approved(self) -> None:
        """All TD tags must be in tags.json."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.t_dragon import mappers as td_mappers  # noqa: F401
        except ImportError:
            # Module may use hyphen in directory name
            pass

        # Direct import of the dict
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        assert td_mappers_path.exists(), f"TsumegoDragon mappers not at {td_mappers_path}"

        # Load by exec since t-dragon has a hyphen in directory
        import importlib.util
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        td_map = module.TD_CATEGORY_TO_YENGO_TAGS
        approved = _get_approved_tag_ids()

        for category, tags in td_map.items():
            if tags is not None:
                for tag in tags:
                    assert tag in approved, (
                        f"TD category '{category}' maps to unapproved tag '{tag}'"
                    )

    def test_connecting_maps_to_connection(self) -> None:
        """connecting → connection (not connect)."""
        import importlib.util
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert module.TD_CATEGORY_TO_YENGO_TAGS["connecting"] == ["connection"]

    def test_disconnect_maps_to_cutting(self) -> None:
        """disconnect → cutting (not cut)."""
        import importlib.util
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert module.TD_CATEGORY_TO_YENGO_TAGS["disconnect"] == ["cutting"]
        assert module.TD_CATEGORY_TO_YENGO_TAGS["discovered-cut"] == ["cutting"]

    def test_corner_tag_added(self) -> None:
        """corner-life--death and corner-pattern should include corner tag."""
        import importlib.util
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert "corner" in module.TD_CATEGORY_TO_YENGO_TAGS["corner-life--death"]
        assert "corner" in module.TD_CATEGORY_TO_YENGO_TAGS["corner-pattern"]

    def test_endgame_categories_mapped(self) -> None:
        """endgame-yose and endgame-traps should map to endgame tag."""
        import importlib.util
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert module.TD_CATEGORY_TO_YENGO_TAGS["endgame-yose"] == ["endgame"]
        assert module.TD_CATEGORY_TO_YENGO_TAGS["endgame-traps"] == ["endgame"]

    def test_shape_maps_to_shape(self) -> None:
        """shape → shape (not dead-shapes)."""
        import importlib.util
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        td_mappers_path = tools_dir / "t-dragon" / "mappers.py"
        spec = importlib.util.spec_from_file_location("td_mappers", td_mappers_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        assert module.TD_CATEGORY_TO_YENGO_TAGS["shape"] == ["shape"]


class TestGoProblemsAdapterTags:
    """Verify GoProblems tag mappings produce only approved tags."""

    def test_all_genre_tags_are_approved(self) -> None:
        """All GENRE_TO_TAG values must be in tags.json."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.go_problems.tags import GENRE_TO_TAG
        finally:
            sys.path.pop(0)

        approved = _get_approved_tag_ids()
        for genre, tag in GENRE_TO_TAG.items():
            assert tag in approved, (
                f"GoProblems genre '{genre}' maps to unapproved tag '{tag}'"
            )

    def test_default_collection_mapping_approved(self) -> None:
        """DEFAULT_COLLECTION_TAG_MAPPING values must be in tags.json."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.go_problems.tags import DEFAULT_COLLECTION_TAG_MAPPING
        finally:
            sys.path.pop(0)

        approved = _get_approved_tag_ids()
        for collection, tag in DEFAULT_COLLECTION_TAG_MAPPING.items():
            assert tag in approved, (
                f"Collection '{collection}' maps to unapproved tag '{tag}'"
            )

    def test_nakade_maps_to_nakade(self) -> None:
        """Nakade collection should map to nakade tag."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.go_problems.tags import DEFAULT_COLLECTION_TAG_MAPPING
        finally:
            sys.path.pop(0)
        assert DEFAULT_COLLECTION_TAG_MAPPING["Nakade"] == "nakade"

    def test_connect_maps_to_connection(self) -> None:
        """Connect collection should map to connection tag."""
        import sys
        tools_dir = Path(__file__).parent.parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        try:
            from tools.go_problems.tags import DEFAULT_COLLECTION_TAG_MAPPING
        finally:
            sys.path.pop(0)
        assert DEFAULT_COLLECTION_TAG_MAPPING["Connect"] == "connection"


# =============================================================================
# Tests: Tag Output Format
# =============================================================================

class TestTagOutputFormat:
    """Verify tags are deduplicated and sorted in YT[] output."""

    def test_validate_tags_filters_unapproved(self) -> None:
        """validate_tags() should remove unapproved tags."""
        from backend.puzzle_manager.core.tagger import validate_tags

        result = validate_tags(["life-and-death", "fake-tag", "ladder"])
        assert "fake-tag" not in result
        assert "life-and-death" in result
        assert "ladder" in result

    def test_validate_tags_keeps_new_tags(self) -> None:
        """validate_tags() should keep v6.0 new tags."""
        from backend.puzzle_manager.core.tagger import validate_tags

        new_tags = ["nakade", "connection", "cutting", "endgame", "tesuji"]
        result = validate_tags(new_tags)
        assert set(result) == set(new_tags)

    def test_detect_techniques_returns_sorted(self) -> None:
        """detect_techniques() should return sorted tags."""
        from backend.puzzle_manager.core.sgf_parser import parse_sgf
        from backend.puzzle_manager.core.tagger import detect_techniques

        sgf = """(;GM[1]FF[4]SZ[9]PL[B]AB[cc][cd]AW[dd];B[dc])"""
        game = parse_sgf(sgf)
        tags = detect_techniques(game)
        assert tags == sorted(tags)


# =============================================================================
# Tests: Tagger Comment-based Detection Uses Valid Tags
# =============================================================================

class TestTaggerUsesValidTags:
    """Verify comment-based detection in tagger.py produces only valid tag names."""

    def test_tagger_fallback_tags_are_approved(self) -> None:
        """_FALLBACK_TAGS should all be in config/tags.json."""
        from backend.puzzle_manager.core.tagger import _FALLBACK_TAGS

        approved = _get_approved_tag_ids()
        unapproved = _FALLBACK_TAGS - approved
        assert not unapproved, f"Fallback tags not in tags.json: {unapproved}"

    def test_approved_tags_count_is_28(self) -> None:
        """get_approved_tags() should return 28 tags."""
        from backend.puzzle_manager.core.tagger import get_approved_tags

        tags = get_approved_tags()
        assert len(tags) == 28, f"Expected 28, got {len(tags)}: {sorted(tags)}"
