"""Layer A (structural) + Layer B (grounded) + weighted dimension scorers.

Extends the yen_sei eval scoring pattern with 5-dimension weighted scoring
specific to oshie teaching comment evaluation.

Dimensions and weights:
  go_correctness:      0.25  -- correct move mentioned, technique identified
  pedagogical_quality: 0.35  -- board consequences explained, move sequences
  voice_compliance:    0.10  -- VP-1..VP-5 style rules
  hint_progression:    0.15  -- tier1=technique, tier2=reasoning, tier3=coord
  completeness:        0.15  -- all fields present, all wrong moves covered
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from tools.core.go_teaching_constants import GO_TECHNIQUE_PATTERN
from tools.core.teaching_schema import TeachingOutput, parse_teaching_output

# ── Constants ────────────────────────────────────────────────────────

WEIGHTS = {
    "go_correctness": 0.25,
    "pedagogical_quality": 0.35,
    "voice_compliance": 0.10,
    "hint_progression": 0.15,
    "completeness": 0.15,
}

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_COORD_TOKEN_RE = re.compile(r"\{!([a-s]{2})\}")
_YOU_SHOULD_RE = re.compile(r"\byou should\b", re.IGNORECASE)
_DOUBLE_DASH_RE = re.compile(r"\s--\s")
# Consequence language patterns
_CONSEQUENCE_WORDS = re.compile(
    r"\b(captures?|dies?|kills?|escapes?|lives?|connects?|separates?|"
    r"recaptures?|sacrifices?|threatens?|atari|trapped|dead|alive)\b",
    re.IGNORECASE,
)
_MOVE_SEQUENCE_RE = re.compile(
    r"\b(after|if|then|when|forces?|responds?|plays?)\b.*\b[A-T]\d{1,2}\b",
    re.IGNORECASE,
)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    """Score for a single evaluation dimension."""
    name: str           # e.g. "go_correctness"
    score: float        # 0.0 - 1.0
    weight: float       # from WEIGHTS
    details: str        # human-readable explanation
    checks: dict = field(default_factory=dict)  # individual check results


@dataclass
class EvalResult:
    """Complete evaluation result for a single puzzle."""
    puzzle_id: str
    puzzle_name: str
    prompt_version: str
    technique: str
    difficulty: str
    raw_content: str               # raw LLM output
    parsed: dict | None            # parsed TeachingOutput as dict
    parse_error: str | None
    dimensions: list[DimensionScore] = field(default_factory=list)
    weighted_total: float = 0.0    # 0.0 - 1.0
    think_tokens: int = 0
    content_tokens: int = 0
    elapsed_s: float = 0.0
    finish_reason: str = ""


# ── Parsing ──────────────────────────────────────────────────────────

def _try_parse_json(content: str) -> tuple[dict | None, str | None]:
    """Try to parse LLM output as JSON teaching output."""
    blob = _JSON_BLOCK_RE.search(content or "")
    if not blob:
        return None, "No JSON object found in output"
    try:
        obj = json.loads(blob.group(0))
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    try:
        validated = parse_teaching_output(obj)
        return obj, None
    except Exception as e:
        # Still return the raw parsed dict even if validation fails
        return obj, f"Schema validation warning: {e}"


def _get_teaching_comments(obj: dict) -> dict:
    """Extract teaching_comments from parsed JSON."""
    return obj.get("teaching_comments", {}) if isinstance(obj, dict) else {}


def _get_hints(obj: dict) -> list[str]:
    """Extract hints from parsed JSON."""
    hints = obj.get("hints", []) if isinstance(obj, dict) else []
    return hints if isinstance(hints, list) else []


def _flatten_text(obj: dict) -> str:
    """Concatenate all string values for prose-level checks."""
    out: list[str] = []
    def walk(x):
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return " ".join(out)


# ── Dimension Scorers ────────────────────────────────────────────────

def _score_go_correctness(
    obj: dict,
    correct_move_sgf: str,
    correct_move_gtp: str,
    technique_tags: list[str],
) -> DimensionScore:
    """Go Correctness (25%): Is the Go analysis accurate?"""
    checks = {}
    text = _flatten_text(obj).lower()

    # Check 1: Correct move mentioned
    checks["correct_move_mentioned"] = (
        correct_move_sgf.lower() in text
        or correct_move_gtp.lower() in text
        or correct_move_gtp.upper() in _flatten_text(obj)
    )

    # Check 2: Technique keyword present
    tag_tokens: set[str] = set()
    for t in technique_tags:
        for piece in re.split(r"[-_,\s]+", t.lower()):
            if piece:
                tag_tokens.add(piece)
    techniques_found = [m.group(1).lower() for m in GO_TECHNIQUE_PATTERN.finditer(text)]
    checks["technique_mentioned"] = bool(
        set(techniques_found) & tag_tokens
    ) or not tag_tokens

    # Check 3: Wrong move consequences stated (not just coordinates)
    tc = _get_teaching_comments(obj)
    wc = tc.get("wrong_comments", {})
    if isinstance(wc, dict):
        consequence_count = sum(
            1 for v in wc.values()
            if isinstance(v, str) and _CONSEQUENCE_WORDS.search(v)
        )
        checks["wrong_move_consequences"] = consequence_count >= len(wc) * 0.5 if wc else True
    else:
        checks["wrong_move_consequences"] = False

    # Score: weighted average of checks
    score = (
        0.4 * checks["correct_move_mentioned"]
        + 0.3 * checks["technique_mentioned"]
        + 0.3 * checks["wrong_move_consequences"]
    )

    details_parts = []
    if not checks["correct_move_mentioned"]:
        details_parts.append(f"missing correct move {correct_move_gtp}")
    if not checks["technique_mentioned"]:
        details_parts.append(f"no technique keyword from {technique_tags}")
    if not checks["wrong_move_consequences"]:
        details_parts.append("wrong moves lack consequence language")

    return DimensionScore(
        name="go_correctness",
        score=score,
        weight=WEIGHTS["go_correctness"],
        details="; ".join(details_parts) if details_parts else "all checks passed",
        checks=checks,
    )


def _score_pedagogical_quality(obj: dict) -> DimensionScore:
    """Pedagogical Quality (35%): Does the teaching have depth?"""
    checks = {}
    tc = _get_teaching_comments(obj)

    # Check 1: Correct comment has substance (> 8 words)
    cc = tc.get("correct_comment", "")
    cc_words = len(cc.split()) if isinstance(cc, str) else 0
    checks["correct_comment_substantive"] = cc_words > 8

    # Check 2: Board consequence language present
    text = _flatten_text(obj)
    consequence_matches = _CONSEQUENCE_WORDS.findall(text)
    checks["consequence_language"] = len(consequence_matches) >= 2

    # Check 3: Move sequence reasoning (e.g. "after F5, White G4 escapes")
    checks["move_sequence_present"] = bool(_MOVE_SEQUENCE_RE.search(text))

    # Check 4: Summary is meaningful (> 5 words)
    summary = tc.get("summary", "")
    checks["summary_meaningful"] = len(summary.split()) > 5 if isinstance(summary, str) else False

    score = (
        0.30 * checks["correct_comment_substantive"]
        + 0.30 * checks["consequence_language"]
        + 0.25 * checks["move_sequence_present"]
        + 0.15 * checks["summary_meaningful"]
    )

    details_parts = []
    if not checks["correct_comment_substantive"]:
        details_parts.append(f"correct_comment too short ({cc_words} words)")
    if not checks["consequence_language"]:
        details_parts.append("lacks board consequence language")
    if not checks["move_sequence_present"]:
        details_parts.append("no move sequence reasoning")
    if not checks["summary_meaningful"]:
        details_parts.append("summary too brief")

    return DimensionScore(
        name="pedagogical_quality",
        score=score,
        weight=WEIGHTS["pedagogical_quality"],
        details="; ".join(details_parts) if details_parts else "rich teaching content",
        checks=checks,
    )


def _score_voice_compliance(obj: dict) -> DimensionScore:
    """Voice Compliance (10%): VP-1 through VP-5 style rules."""
    checks = {}
    tc = _get_teaching_comments(obj)
    text = _flatten_text(obj)

    # VP-1: Board speaks first (no "you should" phrases)
    checks["no_you_should"] = not _YOU_SHOULD_RE.search(text)

    # VP-2: Action--consequence with double-dash
    cc = tc.get("correct_comment", "")
    checks["double_dash_pattern"] = bool(_DOUBLE_DASH_RE.search(cc)) if isinstance(cc, str) else False

    # VP-3: Verb-forward (correct comment starts with verb, not article)
    if isinstance(cc, str) and cc.strip():
        first_word = cc.strip().split()[0].lower()
        checks["verb_forward"] = first_word not in {"the", "a", "an", "this", "that", "it", "there"}
    else:
        checks["verb_forward"] = False

    # VP-4: 15-word cap on wrong move explanations
    wc = tc.get("wrong_comments", {})
    if isinstance(wc, dict) and wc:
        over_cap = sum(1 for v in wc.values() if isinstance(v, str) and len(v.split()) > 15)
        checks["wrong_comment_word_cap"] = over_cap == 0
    else:
        checks["wrong_comment_word_cap"] = True

    score = (
        0.25 * checks["no_you_should"]
        + 0.30 * checks["double_dash_pattern"]
        + 0.20 * checks["verb_forward"]
        + 0.25 * checks["wrong_comment_word_cap"]
    )

    details_parts = []
    if not checks["no_you_should"]:
        details_parts.append("contains 'you should' (VP-1)")
    if not checks["double_dash_pattern"]:
        details_parts.append("missing action--consequence pattern (VP-2)")
    if not checks["verb_forward"]:
        details_parts.append("correct comment not verb-forward (VP-3)")
    if not checks["wrong_comment_word_cap"]:
        details_parts.append("wrong comment exceeds 15-word cap (VP-4)")

    return DimensionScore(
        name="voice_compliance",
        score=score,
        weight=WEIGHTS["voice_compliance"],
        details="; ".join(details_parts) if details_parts else "voice rules followed",
        checks=checks,
    )


def _score_hint_progression(obj: dict) -> DimensionScore:
    """Hint Progression (15%): 3-tier hint quality."""
    checks = {}
    hints = _get_hints(obj)

    # Check 1: Has exactly 3 hints
    checks["has_3_hints"] = len(hints) == 3

    if len(hints) >= 1:
        # Check 2: Tier 1 is technique-only (short, <= 4 words after "tier1:" prefix)
        t1 = hints[0]
        t1_body = re.sub(r"^tier\s*1\s*:\s*", "", t1, flags=re.IGNORECASE).strip()
        checks["tier1_concise"] = len(t1_body.split()) <= 4
    else:
        checks["tier1_concise"] = False

    if len(hints) >= 2:
        # Check 3: Tier 2 has no coordinates (no {!xy} tokens, no SGF coords)
        t2 = hints[1]
        checks["tier2_no_coords"] = not _COORD_TOKEN_RE.search(t2) and not re.search(r"\b[A-T]\d{1,2}\b", t2)
    else:
        checks["tier2_no_coords"] = False

    if len(hints) >= 3:
        # Check 4: Tier 3 has coordinate token {!xy}
        t3 = hints[2]
        checks["tier3_has_coord"] = bool(_COORD_TOKEN_RE.search(t3))
    else:
        checks["tier3_has_coord"] = False

    score = (
        0.25 * checks["has_3_hints"]
        + 0.25 * checks["tier1_concise"]
        + 0.25 * checks["tier2_no_coords"]
        + 0.25 * checks["tier3_has_coord"]
    )

    details_parts = []
    if not checks["has_3_hints"]:
        details_parts.append(f"has {len(hints)} hints, expected 3")
    if not checks["tier1_concise"]:
        details_parts.append("tier1 not concise")
    if not checks["tier2_no_coords"]:
        details_parts.append("tier2 leaks coordinates")
    if not checks["tier3_has_coord"]:
        details_parts.append("tier3 missing {!xy} token")

    return DimensionScore(
        name="hint_progression",
        score=score,
        weight=WEIGHTS["hint_progression"],
        details="; ".join(details_parts) if details_parts else "proper hint progression",
        checks=checks,
    )


def _score_completeness(
    obj: dict,
    expected_wrong_coords: list[str],
) -> DimensionScore:
    """Completeness (15%): Are all required fields present?"""
    checks = {}
    tc = _get_teaching_comments(obj)
    hints = _get_hints(obj)

    # Check 1: Has correct_comment
    checks["has_correct_comment"] = bool(tc.get("correct_comment", "").strip())

    # Check 2: Has summary
    checks["has_summary"] = bool(tc.get("summary", "").strip())

    # Check 3: Has wrong_comments
    wc = tc.get("wrong_comments", {})
    checks["has_wrong_comments"] = bool(wc) and isinstance(wc, dict)

    # Check 4: Covers expected wrong move coordinates
    if expected_wrong_coords and isinstance(wc, dict):
        covered = sum(1 for coord in expected_wrong_coords if coord in wc)
        checks["wrong_moves_covered"] = covered / len(expected_wrong_coords) if expected_wrong_coords else 1.0
    else:
        checks["wrong_moves_covered"] = 1.0 if not expected_wrong_coords else 0.0

    # Check 5: Has hints
    checks["has_hints"] = len(hints) > 0

    score = (
        0.20 * checks["has_correct_comment"]
        + 0.15 * checks["has_summary"]
        + 0.20 * checks["has_wrong_comments"]
        + 0.25 * (checks["wrong_moves_covered"] if isinstance(checks["wrong_moves_covered"], float) else float(checks["wrong_moves_covered"]))
        + 0.20 * checks["has_hints"]
    )

    details_parts = []
    if not checks["has_correct_comment"]:
        details_parts.append("missing correct_comment")
    if not checks["has_summary"]:
        details_parts.append("missing summary")
    if not checks["has_wrong_comments"]:
        details_parts.append("missing wrong_comments")
    if isinstance(checks["wrong_moves_covered"], float) and checks["wrong_moves_covered"] < 1.0:
        details_parts.append(f"only {checks['wrong_moves_covered']:.0%} wrong moves covered")
    if not checks["has_hints"]:
        details_parts.append("no hints")

    return DimensionScore(
        name="completeness",
        score=score,
        weight=WEIGHTS["completeness"],
        details="; ".join(details_parts) if details_parts else "complete output",
        checks=checks,
    )


# ── Main Scoring Function ───────────────────────────────────────────

def score_response(
    content: str,
    puzzle_id: str,
    puzzle_name: str,
    prompt_version: str,
    technique: str,
    difficulty: str,
    correct_move_sgf: str,
    correct_move_gtp: str,
    technique_tags: list[str],
    expected_wrong_coords: list[str],
    think_tokens: int = 0,
    content_tokens: int = 0,
    elapsed_s: float = 0.0,
    finish_reason: str = "",
) -> EvalResult:
    """Score a single LLM response across all 5 dimensions.

    Returns a fully populated EvalResult with per-dimension scores
    and a weighted total.
    """
    parsed_obj, parse_error = _try_parse_json(content)

    if parsed_obj is None:
        # Total failure: return zero scores
        return EvalResult(
            puzzle_id=puzzle_id,
            puzzle_name=puzzle_name,
            prompt_version=prompt_version,
            technique=technique,
            difficulty=difficulty,
            raw_content=content,
            parsed=None,
            parse_error=parse_error,
            dimensions=[
                DimensionScore(name=name, score=0.0, weight=w, details=f"parse failed: {parse_error}")
                for name, w in WEIGHTS.items()
            ],
            weighted_total=0.0,
            think_tokens=think_tokens,
            content_tokens=content_tokens,
            elapsed_s=elapsed_s,
            finish_reason=finish_reason,
        )

    # Score each dimension
    dims = [
        _score_go_correctness(parsed_obj, correct_move_sgf, correct_move_gtp, technique_tags),
        _score_pedagogical_quality(parsed_obj),
        _score_voice_compliance(parsed_obj),
        _score_hint_progression(parsed_obj),
        _score_completeness(parsed_obj, expected_wrong_coords),
    ]

    weighted_total = sum(d.score * d.weight for d in dims)

    return EvalResult(
        puzzle_id=puzzle_id,
        puzzle_name=puzzle_name,
        prompt_version=prompt_version,
        technique=technique,
        difficulty=difficulty,
        raw_content=content,
        parsed=parsed_obj,
        parse_error=parse_error,
        dimensions=dims,
        weighted_total=weighted_total,
        think_tokens=think_tokens,
        content_tokens=content_tokens,
        elapsed_s=elapsed_s,
        finish_reason=finish_reason,
    )


def to_dict(result: EvalResult) -> dict:
    """Serialize an EvalResult to a JSON-compatible dict."""
    return asdict(result)
