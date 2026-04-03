"""Unit tests for core/text_cleaner.py.

Tests for SGF comment text cleaning utilities: HTML stripping, URL removal,
boilerplate removal, and normalization.
"""


from backend.puzzle_manager.core.text_cleaner import (
    clean_comment_text,
    clean_for_correctness,
    normalize_text,
    strip_boilerplate,
    strip_html,
    strip_urls,
)


class TestStripHtml:
    """Tests for strip_html function."""

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_no_html(self):
        assert strip_html("plain text") == "plain text"

    def test_simple_tag(self):
        result = strip_html("<h1>Wrong</h1>")
        assert "Wrong" in result
        assert "<h1>" not in result
        assert "</h1>" not in result

    def test_multiple_tags(self):
        result = strip_html("<b>Bold</b> and <i>italic</i>")
        assert "Bold" in result
        assert "italic" in result
        assert "<b>" not in result
        assert "<i>" not in result

    def test_nested_tags(self):
        result = strip_html("<div><p>Text</p></div>")
        assert "Text" in result
        assert "<" not in result

    def test_html_entities_amp(self):
        assert "& bad" in strip_html("&amp; bad")

    def test_html_entities_lt_gt(self):
        result = strip_html("&lt;result&gt;")
        assert "<result>" == result

    def test_numbered_entity(self):
        # &#65; is 'A'
        assert "A" in strip_html("&#65;")

    def test_combined_tags_and_entities(self):
        result = strip_html("<h1>Wrong</h1> &amp; bad")
        assert "Wrong" in result
        assert "& bad" in result
        assert "<h1>" not in result


class TestStripUrls:
    """Tests for strip_urls function."""

    def test_empty_string(self):
        assert strip_urls("") == ""

    def test_no_urls(self):
        assert strip_urls("plain text") == "plain text"

    def test_http_url(self):
        result = strip_urls("See http://example.com for details")
        assert "http" not in result
        assert "example.com" not in result
        assert "See" in result
        assert "for details" in result

    def test_https_url(self):
        result = strip_urls("Visit https://example.com/page")
        assert "https" not in result
        assert "example.com" not in result

    def test_url_with_path(self):
        result = strip_urls("Check https://go.org/puzzles/123?foo=bar#anchor end")
        assert "https" not in result
        assert "go.org" not in result
        assert "end" in result

    def test_multiple_urls(self):
        result = strip_urls("A http://a.com B https://b.com C")
        assert "http" not in result
        assert "a.com" not in result
        assert "b.com" not in result


class TestStripBoilerplate:
    """Tests for strip_boilerplate function."""

    def test_empty_string(self):
        assert strip_boilerplate("") == ""

    def test_no_boilerplate(self):
        assert strip_boilerplate("Black to play") == "Black to play"

    def test_problem_number(self):
        result = strip_boilerplate("Problem 1. Black to play")
        assert "Problem 1" not in result
        assert "Black to play" in result

    def test_problem_hash(self):
        result = strip_boilerplate("Problem #42 Find the tesuji")
        assert "Problem #42" not in result
        assert "Find the tesuji" in result

    def test_question_number(self):
        result = strip_boilerplate("Question 123. What move?")
        assert "Question 123" not in result
        assert "What move?" in result

    def test_exercise_number(self):
        result = strip_boilerplate("Exercise #5 Capture stones")
        assert "Exercise #5" not in result
        assert "Capture stones" in result

    def test_puzzle_number(self):
        result = strip_boilerplate("Puzzle 99 - Kill white")
        assert "Puzzle 99" not in result
        assert "Kill white" in result

    def test_case_insensitive(self):
        result = strip_boilerplate("PROBLEM #1 text")
        assert "PROBLEM #1" not in result
        assert "text" in result


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_whitespace_only(self):
        assert normalize_text("   ") == ""

    def test_lowercase(self):
        assert normalize_text("HELLO WORLD") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize_text("hello    world") == "hello world"

    def test_strip_leading_trailing(self):
        assert normalize_text("  hello  ") == "hello"

    def test_tabs_and_newlines(self):
        assert normalize_text("hello\t\nworld") == "hello world"

    def test_nfkc_normalization(self):
        # Full-width characters should normalize
        result = normalize_text("ＡＢＣ")  # Full-width ABC
        assert result == "abc"


class TestCleanCommentText:
    """Tests for clean_comment_text (full pipeline)."""

    def test_none_input(self):
        assert clean_comment_text(None) == ""

    def test_empty_string(self):
        assert clean_comment_text("") == ""

    def test_plain_text(self):
        result = clean_comment_text("simple text")
        assert result == "simple text"

    def test_html_and_entities(self):
        result = clean_comment_text("<h1>Wrong</h1> &amp; bad move")
        assert "wrong" in result
        assert "& bad" in result or "bad" in result
        assert "<h1>" not in result

    def test_url_removal(self):
        result = clean_comment_text("See https://example.com for info")
        assert "https" not in result
        assert "example.com" not in result

    def test_boilerplate_removal(self):
        result = clean_comment_text("Problem #1. Black to play")
        assert "problem #1" not in result
        assert "black to play" in result

    def test_combined_cleaning(self):
        text = "<b>Problem #1</b> Visit http://go.com &amp; play"
        result = clean_comment_text(text)
        assert "<b>" not in result
        assert "problem #1" not in result
        assert "http" not in result
        assert "play" in result

    def test_lowercase_output(self):
        result = clean_comment_text("WRONG MOVE")
        assert result == "wrong move"

    def test_whitespace_normalized(self):
        result = clean_comment_text("  multiple   spaces  ")
        assert "  " not in result  # No double spaces


class TestCleanForCorrectness:
    """Tests for clean_for_correctness (lighter cleaning for prefix matching)."""

    def test_none_input(self):
        assert clean_for_correctness(None) == ""

    def test_empty_string(self):
        assert clean_for_correctness("") == ""

    def test_preserves_case(self):
        result = clean_for_correctness("Wrong Move")
        assert result == "Wrong Move"

    def test_preserves_boilerplate(self):
        # clean_for_correctness should NOT strip boilerplate
        # to avoid over-processing when we just need HTML cleaned
        result = clean_for_correctness("Problem #1 Wrong")
        # Boilerplate is preserved
        assert "Wrong" in result

    def test_strips_html(self):
        result = clean_for_correctness("<h1>Wrong</h1>")
        assert "Wrong" in result
        assert "<h1>" not in result

    def test_decodes_entities(self):
        result = clean_for_correctness("Wrong &amp; bad")
        assert "& bad" in result or "Wrong" in result

    def test_html_wrapped_prefix_correct(self):
        """HTML-wrapped 'Correct' should be extractable."""
        result = clean_for_correctness("<b>Correct!</b>")
        assert result.startswith("Correct")

    def test_html_wrapped_prefix_wrong(self):
        """HTML-wrapped 'Wrong' should be extractable."""
        result = clean_for_correctness("<h1>Wrong</h1> move")
        assert result.lower().startswith("wrong")

    def test_whitespace_normalized(self):
        result = clean_for_correctness("  Wrong   move  ")
        assert result == "Wrong move"


class TestIntegration:
    """Integration tests for text_cleaner with correctness inference."""

    def test_html_wrong_detected(self):
        """HTML-wrapped 'Wrong' should be detectable by correctness inference."""
        from backend.puzzle_manager.core.correctness import infer_correctness_from_comment

        # This was the failing case before text_cleaner integration
        result = infer_correctness_from_comment("<h1>Wrong</h1>")
        assert result is False

    def test_html_correct_detected(self):
        """HTML-wrapped 'Correct' should be detectable by correctness inference."""
        from backend.puzzle_manager.core.correctness import infer_correctness_from_comment

        result = infer_correctness_from_comment("<b>Correct!</b>")
        assert result is True

    def test_plus_marker_still_works(self):
        """Exact '+' marker should still work after cleaning."""
        from backend.puzzle_manager.core.correctness import infer_correctness_from_comment

        result = infer_correctness_from_comment("+")
        assert result is True

    def test_plain_wrong_still_works(self):
        """Plain 'Wrong' without HTML should still work."""
        from backend.puzzle_manager.core.correctness import infer_correctness_from_comment

        result = infer_correctness_from_comment("Wrong move, try again")
        assert result is False
