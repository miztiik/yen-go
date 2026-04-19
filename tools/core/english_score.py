"""English-likeness scoring for short text snippets.

Two methods:
1. ``heuristic`` (default, no extra deps): ASCII letter ratio + English
   stopword frequency per 100 chars. Fast, reliable for filtering CJK /
   non-English text from SGF comments.
2. ``wordfreq`` (optional): use the ``wordfreq`` library to compute mean
   Zipf frequency of tokens. Stricter — true dictionary check. Requires
   ``pip install wordfreq``.

Used by yen-sei curation pipeline. May be reused by any tool that needs
to score whether a short text snippet is meaningfully English.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Default English stopwords commonly found in Go teaching prose.
# Override at call-site via the ``stopwords`` argument.
DEFAULT_STOPWORDS: frozenset[str] = frozenset({
    "the", "a", "an", "is", "to", "and", "of", "in", "this", "that",
    "white", "black", "plays", "play", "move", "after", "if", "then",
    "because", "since", "so", "but", "with", "for", "on", "at",
    "be", "are", "was", "were", "will", "can", "must", "should", "would",
    "it", "its", "as", "or", "we", "you", "by", "from", "not",
})

_ASCII_LETTER_RE = re.compile(r"[A-Za-z]")
_TOKEN_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class EnglishScore:
    """Result of scoring a text snippet for English-ness."""
    ascii_letter_ratio: float
    stopword_hits: int
    stopword_hits_per_100_chars: float
    word_count: int
    is_english_heuristic: bool
    is_english_wordfreq: bool | None  # None when wordfreq not used
    mean_zipf: float | None  # None when wordfreq not used


def score_english(
    text: str,
    *,
    method: str = "heuristic",
    min_ascii_ratio: float = 0.6,
    min_stopword_per_100: float = 3.0,
    stopwords: frozenset[str] = DEFAULT_STOPWORDS,
    wordfreq_min_zipf: float = 2.0,
) -> EnglishScore:
    """Score a text snippet for English-ness.

    Args:
        text: Input text (any length, may contain CJK/HTML/markup).
        method: ``heuristic``, ``wordfreq``, or ``both``.
        min_ascii_ratio: Threshold for heuristic ASCII-letter pass.
        min_stopword_per_100: Threshold for heuristic stopword pass.
        stopwords: English stopword set.
        wordfreq_min_zipf: Mean Zipf threshold when using wordfreq.

    Returns:
        EnglishScore with all signals + boolean pass flags.
    """
    if not text:
        return EnglishScore(0.0, 0, 0.0, 0, False, None if method == "heuristic" else False, None)

    # Heuristic signals
    n = len(text)
    ascii_letters = len(_ASCII_LETTER_RE.findall(text))
    ascii_ratio = ascii_letters / n if n else 0.0

    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    word_count = len(tokens)
    stopword_hits = sum(1 for t in tokens if t in stopwords)
    stopword_per_100 = (stopword_hits * 100.0) / n if n else 0.0

    is_english_heuristic = (
        ascii_ratio >= min_ascii_ratio
        and stopword_per_100 >= min_stopword_per_100
    )

    # Optional wordfreq check
    is_english_wf: bool | None = None
    mean_zipf: float | None = None
    if method in ("wordfreq", "both"):
        try:
            from wordfreq import zipf_frequency
        except ImportError as e:
            raise ImportError(
                "method='wordfreq' requires the wordfreq package: pip install wordfreq"
            ) from e
        if tokens:
            zipfs = [zipf_frequency(t, "en") for t in tokens]
            mean_zipf = sum(zipfs) / len(zipfs)
            is_english_wf = mean_zipf >= wordfreq_min_zipf
        else:
            mean_zipf = 0.0
            is_english_wf = False

    return EnglishScore(
        ascii_letter_ratio=ascii_ratio,
        stopword_hits=stopword_hits,
        stopword_hits_per_100_chars=stopword_per_100,
        word_count=word_count,
        is_english_heuristic=is_english_heuristic,
        is_english_wordfreq=is_english_wf,
        mean_zipf=mean_zipf,
    )


def is_english(score: EnglishScore, method: str = "heuristic") -> bool:
    """Combine pass flags according to method."""
    if method == "heuristic":
        return score.is_english_heuristic
    if method == "wordfreq":
        return bool(score.is_english_wordfreq)
    if method == "both":
        return score.is_english_heuristic and bool(score.is_english_wordfreq)
    raise ValueError(f"Unknown method: {method}")
