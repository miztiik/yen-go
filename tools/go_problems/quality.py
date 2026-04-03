"""
YQ quality score computation for GoProblems puzzles.

Computes the quality score from GoProblems API fields (stars, votes, isCanon)
for the YQ[] SGF property.

YQ format: q:{score};rc:{refutation_count};hc:{comment_level}
- q = quality score (1-5 integer)
- rc = refutation count (0 at ingest, computed during analyze stage)
- hc = comment level (0=none, 1=correctness markers, 2=teaching text;
       0 at ingest, computed during analyze stage)
"""

from __future__ import annotations

from .models import GoProblemsRating


def compute_quality_score(
    rating: GoProblemsRating | None,
    is_canon: bool,
) -> int:
    """Compute quality score from GoProblems API fields.

    Algorithm:
    - If no votes: q = 2 (neutral default)
    - If votes < 3: q = min(round(stars), 3) (cap uncertain ratings)
    - If votes >= 3: q = round(stars) (use actual rating)
    - Canon bonus: +1 if isCanon and q < 5
    - Clamped to 1-5 range

    Args:
        rating: Rating info with stars and votes
        is_canon: Whether the puzzle is canonical

    Returns:
        Quality score integer (1-5)
    """
    if rating is None or rating.votes == 0:
        base = 2  # neutral default
    elif rating.votes < 3:
        base = min(round(rating.stars), 3)  # cap uncertain ratings
    else:
        base = round(rating.stars)  # use actual rating

    # Clamp to 1-5
    base = max(1, min(5, base))

    # Canon bonus
    if is_canon and base < 5:
        base += 1

    return min(5, base)


def format_yq(quality_score: int, refutation_count: int = 0, comment_level: int = 0) -> str:
    """Format YQ property value.

    Args:
        quality_score: Quality score (1-5)
        refutation_count: Number of refutation paths (0 at ingest)
        comment_level: Comment level 0-2 (0=none, 1=markers, 2=teaching; 0 at ingest)

    Returns:
        YQ value string like "q:3;rc:0;hc:0"
    """
    return f"q:{quality_score};rc:{refutation_count};hc:{comment_level}"
