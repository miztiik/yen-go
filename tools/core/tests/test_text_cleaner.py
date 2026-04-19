"""Tests for tools.core.text_cleaner shared normalization module."""

import re

from tools.core.text_cleaner import (
    GO_TERMS,
    NON_LATIN_RE,
    clean_name,
    extract_english_portion,
    generate_slug,
    infer_curator,
    infer_type,
    sanitize_for_training,
)

# ==============================
# clean_name Tests
# ==============================

class TestCleanName:
    def test_strips_bracket_suffix(self) -> None:
        assert clean_name("Life and Death [Atorrante]") == "Life and Death"

    def test_strips_possessives(self) -> None:
        assert clean_name("Cho Chikun's Problems") == "Cho Chikun Problems"

    def test_strips_leading_number(self) -> None:
        assert clean_name("1. Elementary Problems") == "Elementary Problems"

    def test_collapses_whitespace(self) -> None:
        assert clean_name("Too   Many  Spaces") == "Too Many Spaces"

    def test_strips_trailing_dashes(self) -> None:
        assert clean_name("Collection -") == "Collection"

    def test_combined_cleanup(self) -> None:
        result = clean_name("3. Cho Chikun's Life & Death [kisvadim]")
        assert result == "Cho Chikun Life & Death"

    def test_extra_strip_patterns(self) -> None:
        """Extra patterns (e.g., website prefixes) applied before standard cleanup."""
        website_re = re.compile(r"^101Weiqi\s*[:.]\s*", re.IGNORECASE)
        result = clean_name("101Weiqi: Basic Problems", extra_strip_patterns=[website_re])
        assert result == "Basic Problems"

    def test_no_extra_patterns(self) -> None:
        """Without extra patterns, website prefixes are preserved."""
        result = clean_name("101Weiqi: Basic Problems")
        assert "101Weiqi" in result

    def test_cjk_brackets_normalized(self) -> None:
        """CJK brackets like \u3010\u3011 are replaced with spaces."""
        result = clean_name("Test\u3010content\u3011Name")
        assert "\u3010" not in result
        assert "\u3011" not in result

    def test_parenthesized_cjk_removed(self) -> None:
        result = clean_name("Collection (\u56f2\u7881\u554f\u984c)")
        assert "\u56f2" not in result


# ==============================
# generate_slug Tests
# ==============================

class TestGenerateSlug:
    def test_basic_slug(self) -> None:
        assert generate_slug("Tesuji Training") == "tesuji-training"

    def test_special_characters_replaced(self) -> None:
        assert generate_slug("Life & Death: Elementary") == "life-death-elementary"

    def test_consecutive_hyphens_collapsed(self) -> None:
        assert generate_slug("A -- B") == "a-b"

    def test_leading_trailing_hyphens_stripped(self) -> None:
        assert generate_slug("-Leading-") == "leading"

    def test_max_64_chars(self) -> None:
        long_name = "A" * 100
        slug = generate_slug(long_name)
        assert len(slug) <= 64

    def test_min_length_short_input(self) -> None:
        slug = generate_slug("X")
        assert len(slug) >= 2

    def test_empty_input(self) -> None:
        slug = generate_slug("")
        assert slug == "unknown"
        assert len(slug) >= 2

    def test_cyrillic_transliterated(self) -> None:
        slug = generate_slug("\u0431\u0430\u0437\u043e\u0432\u044b\u0435 \u0444\u043e\u0440\u043c\u044b")
        assert slug == "bazovye-formy"

    def test_cjk_transliterated(self) -> None:
        slug = generate_slug("\u56db\u8def\u5b98\u5b50\u8b5c")
        assert slug != "unknown"
        assert re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug)

    def test_thai_transliterated(self) -> None:
        slug = generate_slug("\u0e1b\u0e34\u0e14\u0e1b\u0e23\u0e30\u0e15\u0e39")
        assert slug != "unknown"
        assert re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug)


# ==============================
# infer_curator Tests
# ==============================

class TestInferCurator:
    def test_known_author_cho_chikun(self) -> None:
        assert infer_curator("Cho Chikun's Elementary Problems") == "Cho Chikun"

    def test_known_author_go_seigen(self) -> None:
        assert infer_curator("Go Seigen Tesuji Collection") == "Go Seigen"

    def test_known_author_lee_changho(self) -> None:
        assert infer_curator("Lee Changho's Life and Death") == "Lee Changho"

    def test_unknown_author_defaults_community(self) -> None:
        assert infer_curator("Random Collection XYZ") == "Community"

    def test_case_insensitive(self) -> None:
        assert infer_curator("CHO CHIKUN problems") == "Cho Chikun"


# ==============================
# infer_type Tests
# ==============================

class TestInferType:
    def test_known_curator_returns_author(self) -> None:
        assert infer_type("Anything", "Cho Chikun") == "author"

    def test_technique_keyword(self) -> None:
        assert infer_type("Life and Death Problems", "Community") == "technique"

    def test_tesuji_keyword(self) -> None:
        assert infer_type("Basic Tesuji", "Community") == "technique"

    def test_graded_keyword(self) -> None:
        assert infer_type("Beginner Collection", "Community") == "graded"

    def test_dan_keyword(self) -> None:
        assert infer_type("Dan Level Puzzles", "Community") == "graded"

    def test_default_reference(self) -> None:
        assert infer_type("Random Puzzles", "Community") == "reference"


# ==============================
# extract_english_portion Tests
# ==============================

class TestExtractEnglishPortion:
    def test_pure_latin_returns_none(self) -> None:
        """Entirely Latin text returns None (no extraction needed)."""
        assert extract_english_portion("Simple English Name") is None

    def test_bilingual_cjk_extraction(self) -> None:
        """Extracts English from CJK + English bilingual name."""
        result = extract_english_portion("\u6b7b\u6d3b\u5c08\u9805\u8a13\u7df4 Life and Death Training")
        assert result is not None
        assert "Life" in result
        assert "Death" in result

    def test_bilingual_with_go_term(self) -> None:
        result = extract_english_portion("\u56f2\u7881 tesuji collection")
        assert result is not None
        assert "tesuji" in result

    def test_no_meaningful_english_returns_none(self) -> None:
        """CJK-only name without meaningful English returns None."""
        result = extract_english_portion("\u56db\u8def\u5b98\u5b50\u8b5c")
        assert result is None

    def test_short_fragments_rejected(self) -> None:
        """Single short Latin fragment without Go terms is rejected."""
        result = extract_english_portion("\u56f2\u7881 ab")
        assert result is None

    def test_camp_prefix_removed(self) -> None:
        """[camp] prefix is stripped from Thai names."""
        result = extract_english_portion("[camp] \u0e17\u0e49\u0e32\u0e22\u0e40\u0e01\u0e21 endgame problems")
        assert result is not None
        assert "[camp]" not in result

    def test_parenthesized_cjk_removed(self) -> None:
        result = extract_english_portion("Tesuji (\u56f2\u7881) Problems")
        assert result is not None
        assert "\u56f2\u7881" not in result


# ==============================
# Constants Tests
# ==============================

class TestConstants:
    def test_non_latin_re_matches_cjk(self) -> None:
        assert NON_LATIN_RE.search("\u56f2\u7881")

    def test_non_latin_re_matches_cyrillic(self) -> None:
        assert NON_LATIN_RE.search("\u0431\u0430\u0437\u043e\u0432\u044b\u0435")

    def test_non_latin_re_no_match_latin(self) -> None:
        assert NON_LATIN_RE.search("Hello World") is None

    def test_go_terms_has_common_terms(self) -> None:
        for term in ["tesuji", "life", "death", "ko", "ladder", "tsumego"]:
            assert term in GO_TERMS


# ==============================
# sanitize_for_training Tests
# ==============================

class TestSanitizeForTraining:
    def test_strips_bold_tags(self) -> None:
        assert sanitize_for_training("Correct! <b>CORRECT!</b>") == "Correct! CORRECT!"

    def test_strips_anchor_keeps_link_text(self) -> None:
        result = sanitize_for_training(
            'See <a href="https://senseis.xmp.net/?BentFour">Bent four</a>.'
        )
        assert "<a" not in result
        assert "href" not in result
        assert "Bent four" in result

    def test_strips_urls(self) -> None:
        result = sanitize_for_training("See https://senseis.xmp.net/?CaptureThree for details.")
        assert "senseis.xmp.net" not in result
        assert "https" not in result
        assert "See" in result

    def test_normalizes_crlf(self) -> None:
        result = sanitize_for_training("Line one\r\nLine two\r\nLine three")
        assert "\r" not in result
        assert result == "Line one\nLine two\nLine three"

    def test_normalizes_lone_cr(self) -> None:
        result = sanitize_for_training("Line one\rLine two")
        assert "\r" not in result
        assert result == "Line one\nLine two"

    def test_preserves_case(self) -> None:
        """Unlike clean_comment_text, case is preserved."""
        result = sanitize_for_training("Black is ALIVE in the corner.")
        assert "ALIVE" in result

    def test_preserves_cjk(self) -> None:
        """Unlike clean_comment_text, CJK characters are preserved."""
        result = sanitize_for_training("\u56f2\u7881 is Go in Japanese")
        assert "\u56f2\u7881" in result

    def test_none_returns_empty(self) -> None:
        assert sanitize_for_training(None) == ""

    def test_empty_returns_empty(self) -> None:
        assert sanitize_for_training("") == ""

    def test_collapses_excessive_whitespace(self) -> None:
        result = sanitize_for_training("Too    many   spaces")
        assert result == "Too many spaces"

    def test_collapses_excessive_newlines(self) -> None:
        result = sanitize_for_training("Para one\n\n\n\n\nPara two")
        assert result == "Para one\n\nPara two"

    def test_preserves_paragraph_breaks(self) -> None:
        result = sanitize_for_training("Para one\n\nPara two")
        assert result == "Para one\n\nPara two"

    def test_real_pollution_example(self) -> None:
        """Real example from OGS training data."""
        dirty = (
            'Correct! <b>CORRECT!</b>\r\n\r\nBlack is alive\r\n\r\n'
            'Black can easily make two real eyes.\r\n\r\n'
            'See <a href="https://senseis.xmp.net/?CaptureThreeToGetAnEye">'
            "Capture three to get an eye</a>."
        )
        result = sanitize_for_training(dirty)
        assert "<b>" not in result
        assert "<a" not in result
        assert "senseis.xmp.net" not in result
        assert "\r" not in result
        assert "Correct! CORRECT!" in result
        assert "Capture three to get an eye" in result
