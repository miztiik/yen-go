"""Tests for CJK stripping and move comment standardization.

Steps 4-6 of the analyzer enhancement plan.
"""


from backend.puzzle_manager.core.text_cleaner import (
    _is_cjk_remnant,
    clean_for_correctness,
    is_teaching_comment,
    standardize_move_comment,
    strip_cjk,
)

# ---------------------------------------------------------------------------
# strip_cjk tests
# ---------------------------------------------------------------------------


class TestStripCjk:
    """Tests for strip_cjk function."""

    def test_empty_string(self) -> None:
        assert strip_cjk("") == ""

    def test_ascii_only(self) -> None:
        assert strip_cjk("hello world") == "hello world"

    def test_cjk_only(self) -> None:
        """CJK-only comment becomes empty string."""
        assert strip_cjk("コウ") == ""

    def test_mixed_cjk_english(self) -> None:
        """English preserved, CJK removed."""
        result = strip_cjk("Black コウ ko")
        assert "ko" in result
        assert "コウ" not in result

    def test_hangul_stripped(self) -> None:
        assert strip_cjk("패 ko") == " ko"

    def test_chinese_stripped(self) -> None:
        assert strip_cjk("劫 fight") == " fight"

    def test_hiragana_stripped(self) -> None:
        assert strip_cjk("こう pattern") == " pattern"

    def test_cjk_punctuation_stripped(self) -> None:
        """CJK symbols and punctuation (U+3000-U+303F) stripped."""
        # U+3000 ideographic space, U+3001 ideographic comma
        assert strip_cjk("text\u3000more\u3001end") == "textmoreend"

    def test_preserves_latin_numbers_punctuation(self) -> None:
        assert strip_cjk("Move 1: correct!") == "Move 1: correct!"


# ---------------------------------------------------------------------------
# standardize_move_comment tests
# ---------------------------------------------------------------------------


class TestStandardizeMoveComment:
    """Tests for standardize_move_comment function."""

    # --- Correct signals ---

    def test_correct_preserved(self) -> None:
        assert standardize_move_comment("Correct!", True) == "Correct"

    def test_right_to_correct(self) -> None:
        assert standardize_move_comment("RIGHT", True) == "Correct"

    def test_plus_to_correct(self) -> None:
        assert standardize_move_comment("+", True) == "Correct"

    def test_ok_to_correct(self) -> None:
        assert standardize_move_comment("ok", True) == "Correct"

    def test_correct_with_suffix(self) -> None:
        result = standardize_move_comment("RIGHT — good tesuji", True)
        assert result == "Correct \u2014 good tesuji"

    # --- Wrong signals ---

    def test_wrong_preserved(self) -> None:
        assert standardize_move_comment("Wrong", False) == "Wrong"

    def test_incorrect_to_wrong(self) -> None:
        result = standardize_move_comment("Incorrect; leads to ko", False)
        assert result == "Wrong \u2014 leads to ko"

    def test_bad_to_wrong(self) -> None:
        assert standardize_move_comment("Bad move", False) == "Wrong \u2014 move"

    # --- Empty comments ---

    def test_empty_correct(self) -> None:
        assert standardize_move_comment("", True) == "Correct"

    def test_empty_wrong(self) -> None:
        assert standardize_move_comment("", False) == "Wrong"

    def test_none_correct(self) -> None:
        assert standardize_move_comment(None, True) == "Correct"

    def test_none_wrong(self) -> None:
        assert standardize_move_comment(None, False) == "Wrong"

    # --- No signal, prepend ---

    def test_no_signal_prepend_correct(self) -> None:
        result = standardize_move_comment("Threatens the corner", True)
        assert result == "Correct \u2014 Threatens the corner"

    def test_no_signal_prepend_wrong(self) -> None:
        result = standardize_move_comment("Loses the group", False)
        assert result == "Wrong \u2014 Loses the group"

    # --- CJK stripped from comment ---

    def test_cjk_stripped_before_standardization(self) -> None:
        """CJK in comment stripped; remaining text standardized."""
        result = standardize_move_comment("コウ ko fight", True)
        assert "コウ" not in result
        assert "Correct" in result

    def test_cjk_only_comment_correct(self) -> None:
        """CJK-only comment becomes just the label."""
        assert standardize_move_comment("コウ", True) == "Correct"

    # --- Signal disagrees with is_correct (trust is_correct) ---

    def test_wrong_signal_but_is_correct(self) -> None:
        """If is_correct=True but comment says 'Wrong', trust is_correct."""
        result = standardize_move_comment("Wrong move here", True)
        assert result.startswith("Correct")


# ---------------------------------------------------------------------------
# clean_for_correctness with CJK
# ---------------------------------------------------------------------------


class TestCleanForCorrectnessWithCjk:
    """Tests that clean_for_correctness now strips CJK."""

    def test_html_and_cjk_stripped(self) -> None:
        result = clean_for_correctness("<b>Wrong</b> コウ move")
        assert "Wrong" in result
        assert "コウ" not in result
        assert "move" in result

    def test_cjk_only_returns_empty(self) -> None:
        assert clean_for_correctness("コウ") == ""

    def test_none_returns_empty(self) -> None:
        assert clean_for_correctness(None) == ""


# ---------------------------------------------------------------------------
# _is_cjk_remnant tests
# ---------------------------------------------------------------------------


class TestIsCjkRemnant:
    """Tests for _is_cjk_remnant — detects orphaned text after CJK strip."""

    def test_empty_string(self) -> None:
        assert _is_cjk_remnant("") is True

    def test_whitespace_only(self) -> None:
        assert _is_cjk_remnant("   ") is True

    def test_scattered_numbers(self) -> None:
        """Orphaned numbers from Korean comment: '흑 9까지..백10에서'."""
        assert _is_cjk_remnant("9    10 .") is True

    def test_scattered_single_letters(self) -> None:
        """Orphaned letters from Korean: '백A로..흑B로..백C에는..흑D로'."""
        assert _is_cjk_remnant("A  B , C D   .") is True

    def test_mixed_numbers_and_letters(self) -> None:
        """Full Korean remnant from OGS puzzle 63232."""
        assert _is_cjk_remnant("3     5   .\n\n A  B ,\n C D   .\n\n  1 2  .") is True

    def test_single_number(self) -> None:
        assert _is_cjk_remnant("9") is True

    def test_single_letter(self) -> None:
        assert _is_cjk_remnant("A") is True

    def test_punctuation_only(self) -> None:
        assert _is_cjk_remnant(".,;:") is True

    def test_meaningful_english_text(self) -> None:
        assert _is_cjk_remnant("White escapes via ladder") is False

    def test_two_letter_word_ko(self) -> None:
        """'ko' is a meaningful 2-letter Go term."""
        assert _is_cjk_remnant("ko") is False

    def test_short_meaningful_text(self) -> None:
        assert _is_cjk_remnant("ko fight") is False

    def test_mixed_meaningful_with_numbers(self) -> None:
        """English explanation with embedded numbers is not a remnant."""
        assert _is_cjk_remnant("Move 3 captures the group") is False

    def test_single_meaningful_word(self) -> None:
        assert _is_cjk_remnant("ladder") is False


# ---------------------------------------------------------------------------
# standardize_move_comment with CJK remnant detection
# ---------------------------------------------------------------------------


class TestStandardizeMoveCommentCjkRemnant:
    """Tests that CJK remnant text is discarded, not kept as garbage suffix."""

    def test_korean_wrong_comment_becomes_just_label(self) -> None:
        """OGS puzzle 63232: Korean wrong-move comment → just 'Wrong'."""
        comment = (
            "Wrong 흑 9까지 계속 단수로 몰아떨구려해도 "
            "백10에서 막혀버립니다.\n\n"
            "백 네모가 길목에서 기다리고 있었기 때문입니다."
        )
        result = standardize_move_comment(comment, is_correct=False)
        assert result == "Wrong"

    def test_korean_correct_comment_becomes_just_label(self) -> None:
        """OGS puzzle 63232: Korean correct-move comment → just 'Correct'."""
        comment = (
            "Correct! 흑 3으로 한번 더 몰은 다음 흑5로 씌우는 수가 있습니다.\n\n"
            "다음 백A로 나오려해도 흑B로 막고,\n"
            "백C에는 흑D로 막을 수 있습니다.\n\n"
            "장문은 이처럼 1선과 2선에서도 요긴하게 쓰입니다."
        )
        result = standardize_move_comment(comment, is_correct=True)
        assert result == "Correct"

    def test_pure_korean_no_signal_becomes_label(self) -> None:
        """Pure Korean text with no English signal → just label."""
        comment = "장문으로 접근하려는 시도는 좋았으나 너무 성급한 수."
        result = standardize_move_comment(comment, is_correct=False)
        assert result == "Wrong"

    def test_english_suffix_preserved(self) -> None:
        """English suffix after signal is preserved (not a remnant)."""
        result = standardize_move_comment("Wrong — White escapes via ladder", False)
        assert result == "Wrong \u2014 White escapes via ladder"

    def test_mixed_cjk_english_preserves_english(self) -> None:
        """If meaningful English words survive CJK strip, keep them."""
        result = standardize_move_comment("Correct コウ ko fight", True)
        assert "ko fight" in result

    def test_ogs_puzzle_63253_wrong(self) -> None:
        """OGS puzzle 63253: Korean wrong-move comment."""
        comment = (
            "Wrong 흑 2로 덥석 단수를 치는 것은 빵점입니다.\n"
            "백3으로 나가면 축이 안 되지 않습니까?\n\n"
            "백 세모가 바로 축머리로 이것은 상대의 주문에 걸려드는 것입니다."
        )
        result = standardize_move_comment(comment, is_correct=False)
        assert result == "Wrong"


# ---------------------------------------------------------------------------
# is_teaching_comment with CJK remnant detection
# ---------------------------------------------------------------------------


class TestIsTeachingCommentCjkRemnant:
    """Tests that CJK-only teaching text is not falsely detected as teaching."""

    def test_pure_korean_not_teaching(self) -> None:
        """Korean-only comment is not considered teaching content."""
        assert is_teaching_comment("장문으로 접근하려는 시도는 좋았으나") is False

    def test_korean_with_numbers_not_teaching(self) -> None:
        """Korean comment with interspersed numbers → not teaching."""
        comment = "흑 9까지 계속 단수로 몰아떨구려해도 백10에서 막혀버립니다."
        assert is_teaching_comment(comment) is False

    def test_english_teaching_still_detected(self) -> None:
        """English teaching text is still correctly detected."""
        assert is_teaching_comment("Wrong — White escapes via ladder") is True

    def test_english_ko_teaching(self) -> None:
        assert is_teaching_comment("Only ko.") is True


# ---------------------------------------------------------------------------
# HTML, URL, and boilerplate stripping in move comments
# ---------------------------------------------------------------------------


class TestStandardizeMoveCommentNoiseStripping:
    """Move comments strip HTML tags, URLs, and boilerplate labels."""

    def test_html_tags_stripped(self) -> None:
        result = standardize_move_comment("<b>Excellent</b> tesuji", True)
        assert result == "Correct — Excellent tesuji"

    def test_html_entities_decoded(self) -> None:
        result = standardize_move_comment("Wrong &amp; bad move", False)
        assert result == "Wrong — & bad move"

    def test_url_stripped(self) -> None:
        result = standardize_move_comment(
            "Wrong — see https://example.com/puzzle for details", False
        )
        assert result == "Wrong — see for details"

    def test_url_only_comment_becomes_label(self) -> None:
        result = standardize_move_comment("https://example.com/puzzle", True)
        assert result == "Correct"

    def test_boilerplate_numbering_stripped(self) -> None:
        result = standardize_move_comment("Problem #42. Correct path", True)
        assert result == "Correct — path"

    def test_html_and_url_combined(self) -> None:
        result = standardize_move_comment(
            "<p>Wrong</p> Visit https://go.com &amp; try again", False
        )
        assert result == "Wrong — Visit & try again"

    def test_korean_with_html_cleared(self) -> None:
        """Korean wrapped in HTML → all noise stripped → label only."""
        result = standardize_move_comment(
            "<b>흑선</b> https://example.com 9까지", False
        )
        assert result == "Wrong"

    def test_pure_url_not_teaching(self) -> None:
        """URL-only comment is not teaching content."""
        assert is_teaching_comment("https://example.com/puzzle") is False

    def test_html_wrapped_teaching_detected(self) -> None:
        """HTML tags stripped before teaching check."""
        assert is_teaching_comment("<b>Wrong</b> — White escapes") is True

    def test_boilerplate_only_not_teaching(self) -> None:
        """Boilerplate label with no real content → not teaching."""
        assert is_teaching_comment("Problem #1.") is False
