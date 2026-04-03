"""Cross-validation: config/teaching-comments.json covers all config/tags.json slugs.

Ensures the teaching comment config stays in sync with the tag taxonomy.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_TAGS_PATH = _PROJECT_ROOT / "config" / "tags.json"
_TC_PATH = _PROJECT_ROOT / "config" / "teaching-comments.json"


@pytest.fixture(scope="module")
def tags_slugs() -> list[str]:
    with open(_TAGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return list(data.get("tags", {}).keys())


@pytest.fixture(scope="module")
def tc_config() -> dict:
    with open(_TC_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def tags_aliases() -> dict[str, list[str]]:
    """Build slug \u2192 aliases mapping from tags.json."""
    with open(_TAGS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    result = {}
    for slug, entry in data.get("tags", {}).items():
        result[slug] = entry.get("aliases", [])
    return result


class TestTagCoverage:
    """Every tag slug must have an entry in teaching-comments.json."""

    def test_all_tag_slugs_have_entries(self, tags_slugs, tc_config):
        comments = tc_config.get("correct_move_comments", {})
        missing = [s for s in tags_slugs if s not in comments]
        assert missing == [], f"Tags missing from teaching-comments.json: {missing}"

    @pytest.mark.parametrize("field", ["comment", "hint_text", "min_confidence"])
    def test_all_entries_have_required_fields(self, tags_slugs, tc_config, field):
        comments = tc_config.get("correct_move_comments", {})
        missing = [
            s for s in tags_slugs
            if s in comments and field not in comments[s]
        ]
        assert missing == [], f"Tags missing '{field}': {missing}"


class TestAliasCoverage:
    """Alias sub-comments should reference valid aliases from tags.json."""

    def test_alias_comments_reference_valid_aliases(self, tc_config, tags_aliases):
        comments = tc_config.get("correct_move_comments", {})
        invalid = []
        for slug, entry in comments.items():
            alias_comments = entry.get("alias_comments", {})
            if not alias_comments:
                continue
            known_aliases = tags_aliases.get(slug, [])
            for alias_key in alias_comments:
                if alias_key not in known_aliases:
                    invalid.append(f"{slug}.alias_comments.{alias_key}")
        assert invalid == [], f"Alias comments not in tags.json aliases: {invalid}"
