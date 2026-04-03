"""Tests for text_cleaner module."""

from tools.core.text_cleaner import (
    clean_comment_text,
    normalize_text,
    strip_boilerplate,
    strip_cjk,
    strip_html,
    strip_urls,
)


class TestStripHtml:
    def test_removes_tags(self):
        assert "Incorrect" in strip_html("<h1>Incorrect</h1>")

    def test_removes_nested_tags(self):
        assert "text" in strip_html("<div><span>text</span></div>")

    def test_decodes_entities(self):
        assert "life & death" in strip_html("life &amp; death")

    def test_decodes_numeric_entities(self):
        assert strip_html("&#39;") == "'"

    def test_no_html_passthrough(self):
        assert strip_html("plain text") == "plain text"

    def test_empty_string(self):
        assert strip_html("") == ""


class TestStripCjk:
    def test_removes_japanese_hiragana(self):
        assert "black" in strip_cjk("ひらがな black")

    def test_removes_katakana(self):
        assert "test" in strip_cjk("カタカナ test")

    def test_removes_cjk_ideographs(self):
        assert "play" in strip_cjk("黒先 play")

    def test_removes_hangul(self):
        assert "test" in strip_cjk("한글 test")

    def test_preserves_latin(self):
        assert strip_cjk("black to play") == "black to play"

    def test_replaces_with_space(self):
        result = strip_cjk("黒先black")
        assert "black" in result

    def test_empty_string(self):
        assert strip_cjk("") == ""


class TestNormalizeText:
    def test_lowercases(self):
        assert normalize_text("Black To Play") == "black to play"

    def test_collapses_whitespace(self):
        assert normalize_text("black  to   play") == "black to play"

    def test_strips_leading_trailing(self):
        assert normalize_text("  black to play  ") == "black to play"

    def test_nfkc_normalization(self):
        assert normalize_text("\uff22lack") == "black"  # Fullwidth B

    def test_empty_string(self):
        assert normalize_text("") == ""


class TestCleanCommentText:
    def test_html_and_cjk(self):
        result = clean_comment_text("<b>黒先</b> Black to play")
        assert result == "black to play"

    def test_preamble_with_objective(self):
        result = clean_comment_text("Welcome to Go! Black to play")
        assert "black to play" in result

    def test_cjk_followed_by_english(self):
        result = clean_comment_text("黒先 white to live")
        assert result == "white to live"

    def test_html_entities_and_cjk(self):
        result = clean_comment_text("生き &amp; 死 life &amp; death")
        assert "life & death" in result

    def test_empty_string(self):
        assert clean_comment_text("") == ""

    def test_none_input(self):
        assert clean_comment_text(None) == ""

    def test_only_cjk(self):
        result = clean_comment_text("黒先白死")
        assert result == ""

    def test_preserves_go_terminology(self):
        result = clean_comment_text("semeai problem")
        assert result == "semeai problem"

    def test_multiple_spaces_after_cjk_removal(self):
        result = clean_comment_text("黒先  黒先  Black to play")
        assert result == "black to play"

    def test_strips_urls_in_pipeline(self):
        result = clean_comment_text("https://example.com Black to play")
        assert "example.com" not in result
        assert "black to play" in result

    def test_strips_boilerplate_in_pipeline(self):
        result = clean_comment_text("Question 6. Black to play")
        assert "question" not in result
        assert "black to play" in result

    def test_strips_urls_and_cjk_combined(self):
        result = clean_comment_text("黒先 https://go.example.com White to live")
        assert "example" not in result
        assert "white to live" in result

class TestStripUrls:
    def test_removes_https_url(self):
        result = strip_urls('Visit https://example.com/go for more')
        assert 'example.com' not in result
        assert 'Visit' in result
        assert 'for more' in result

    def test_removes_http_url(self):
        result = strip_urls('http://foo.com/bar?baz=1 text')
        assert 'foo.com' not in result
        assert 'text' in result

    def test_removes_url_with_path(self):
        result = strip_urls('https://youtube.com/watch?v=abc123&t=10s info')
        assert 'youtube' not in result
        assert 'info' in result

    def test_preserves_non_url_text(self):
        assert strip_urls('no urls here') == 'no urls here'

    def test_empty_string(self):
        assert strip_urls('') == ''

    def test_multiple_urls(self):
        result = strip_urls('https://a.com https://b.com text')
        assert 'a.com' not in result
        assert 'b.com' not in result
        assert 'text' in result


class TestStripBoilerplate:
    def test_removes_question_number(self):
        result = strip_boilerplate('Question 6. Black to play')
        assert 'question' not in result.lower()
        assert 'Black to play' in result

    def test_removes_problem_hash(self):
        result = strip_boilerplate('Problem #3 White to live')
        assert 'problem' not in result.lower()
        assert 'White to live' in result

    def test_removes_exercise_number(self):
        result = strip_boilerplate('Exercise 12 capture')
        assert 'exercise' not in result.lower()
        assert 'capture' in result

    def test_removes_puzzle_number(self):
        result = strip_boilerplate('Puzzle 42. solve this')
        assert 'puzzle' not in result.lower()

    def test_preserves_non_boilerplate(self):
        assert strip_boilerplate('black to play') == 'black to play'

    def test_empty_string(self):
        assert strip_boilerplate('') == ''
