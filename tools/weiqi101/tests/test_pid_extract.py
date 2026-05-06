from __future__ import annotations

from tools.weiqi101.pid_extract import pid_from_filename


def test_qday_format():
    assert pid_from_filename("20180315-4-15661.sgf") == 15661


def test_book_chapter_form():
    assert pid_from_filename("ch01_001_destroy-eye_15659.sgf") == 15659


def test_book_chapter_form_with_cjk_slug():
    # Slug contains CJK; trailing pid still extracted.
    assert pid_from_filename("ch07_012_围棋死活_28566.sgf") == 28566


def test_book_legacy_pos_form():
    assert pid_from_filename("0042_some-slug_007_9538.sgf") == 9538


def test_bare_numeric_stem():
    assert pid_from_filename("78000.sgf") == 78000


def test_trailing_hyphen_pid():
    # Hyphen-separated trailing pid (covers th-style filenames if ever reused).
    assert pid_from_filename("anything-12345.sgf") == 12345


def test_underscore_takes_priority_over_hyphen():
    # Mixed: last underscore wins because we try ``_`` before ``-``.
    assert pid_from_filename("foo-bar_999.sgf") == 999


def test_no_pid_returns_none():
    assert pid_from_filename("not-an-sgf.txt") is None
    assert pid_from_filename("noPidHere.sgf") is None
    assert pid_from_filename("trailing-not-digits-abc.sgf") is None


def test_empty_or_garbage():
    assert pid_from_filename("") is None
    assert pid_from_filename(".sgf") is None
