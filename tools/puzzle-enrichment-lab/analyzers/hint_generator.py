"""3-tier progressive hint generator (config-driven).

Generates progressive hints:
  - Tier 1 (technique): hint_text from config/teaching-comments.json
  - Tier 2 (reasoning): Analysis-based reasoning context
  - Tier 3 (coordinate): Where to play, using {!xy} coordinate tokens

Hints are stored in YH SGF property as pipe-delimited: YH[tier1|tier2|tier3]

Coordinate tokens use SGF notation: {!xy} where x=column, y=row (a-s for 1-19).
Example: {!cg} = column C, row G = C7 in GTP notation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from config.teaching import load_teaching_comments_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier 3: Coordinate hint templates (format strings — stay in code)
# ---------------------------------------------------------------------------

COORDINATE_TEMPLATES: dict[str, str] = {
    "snapback": "The snapback is at {!xy}.",
    "ladder": "The ladder starts at {!xy}.",
    "ko": "The ko starts at {!xy}.",
    "seki": "The vital point for seki is {!xy}.",
    "throw-in": "The throw-in point is {!xy}.",
    "sacrifice": "The sacrifice is at {!xy}.",
    "capture": "Capture at {!xy}.",
    "life-and-death": "The vital point is {!xy}.",
    "eye-shape": "The eye-shape vital point is {!xy}.",
    "connection": "Connect at {!xy}.",
    "cutting": "Cut at {!xy}.",
    "net": "The net move is {!xy}.",
    "semeai": "The liberty-filling move is {!xy}.",
    "capture-race": "Start the race at {!xy}.",
    "escape": "Break out at {!xy}.",
    "tesuji": "The tesuji is at {!xy}.",
    "atari": "Place atari at {!xy}.",
    "default": "The first move is at {!xy}.",
}

# ---------------------------------------------------------------------------
# T23: Atari relevance gating (ported from backend enrichment/hints.py)
# ---------------------------------------------------------------------------
# Tags where atari framing is misleading — the technique IS the point,
# so naming "atari" would obscure the actual teaching concept.
ATARI_SKIP_TAGS = frozenset({"capture-race", "ko", "sacrifice", "snapback", "throw-in"})

# ---------------------------------------------------------------------------
# T24: Depth-gated Tier 3 coordinate hints (spoiler prevention)
# ---------------------------------------------------------------------------
# A 1-move puzzle shouldn't get "The first move is at {!xy}" — too much spoiler.
TIER3_DEPTH_THRESHOLD = 3

# RC-2: Tags where the first move IS the answer — coordinate hints are spoilers
# regardless of depth. For these tactical techniques, knowing the move coordinate
# is equivalent to solving the puzzle.
TIER3_TACTICAL_SUPPRESS_TAGS = frozenset({
    "net", "ladder", "snapback", "throw-in", "oiotoshi",
})

# ---------------------------------------------------------------------------
# T27: Tags where liberty analysis enriches reasoning hints
# ---------------------------------------------------------------------------
SEMEAI_KO_TAGS = frozenset({"capture-race", "ko"})


# ---------------------------------------------------------------------------
# T25: Solution-aware inference (ported from backend solution_tagger.py)
# ---------------------------------------------------------------------------

class InferenceConfidence(IntEnum):
    """Confidence level for solution-inferred technique."""

    LOW = 0       # No detectable effect — do not emit hint
    MEDIUM = 1    # Ambiguous but plausible
    HIGH = 2      # Verifiable from analysis data


@dataclass(frozen=True)
class InferenceResult:
    """Result of solution-aware technique inference."""

    tag: str | None
    effect: str
    confidence: InferenceConfidence


# ---------------------------------------------------------------------------
# T26: Structured hint operation log (ported from backend enrichment/config.py)
# ---------------------------------------------------------------------------

@dataclass
class HintOperationLog:
    """Structured log for hint generation decisions per tier."""

    tier1_source: str = ""   # "config", "inference", "none"
    tier1_value: str = ""
    tier2_source: str = ""   # "detection", "analysis", "none"
    tier2_value: str = ""
    tier3_source: str = ""   # "coordinate", "suppressed_atari", "depth_gated", "none"
    tier3_value: str = ""
    tier3_depth_gated: bool = False
    tier3_atari_suppressed: bool = False
    inference_used: bool = False
    inference_confidence: str = ""


def infer_technique_from_solution(analysis: dict[str, Any]) -> InferenceResult:
    """Infer technique from analysis data when no tags were detected.

    Uses solution depth, refutation count, and PV moves to guess technique.
    Only HIGH+ confidence inferences produce usable tags for Tier 1 hints.
    MEDIUM confidence also produces tags but with lower certainty.
    LOW confidence returns None — coordinate-only hints are acceptable.
    """
    difficulty = analysis.get("difficulty", {})
    validation = analysis.get("validation", {})
    depth = difficulty.get("solution_depth", 0)
    refutation_count = difficulty.get("refutation_count", 0)
    pv = validation.get("pv", [])

    # Refutations + depth → life-and-death pattern (HIGH confidence)
    if refutation_count > 0 and depth >= 2:
        return InferenceResult(
            tag="life-and-death",
            effect="refutations_with_depth",
            confidence=InferenceConfidence.HIGH,
        )

    # Long PV suggests ko fight (MEDIUM)
    if len(pv) >= 6:
        return InferenceResult(
            tag="ko", effect="long_pv", confidence=InferenceConfidence.MEDIUM,
        )

    # Multi-move reading → tesuji (MEDIUM)
    if depth >= 3:
        return InferenceResult(
            tag="tesuji", effect="multi_move_reading", confidence=InferenceConfidence.MEDIUM,
        )

    return InferenceResult(
        tag=None, effect="insufficient_evidence", confidence=InferenceConfidence.LOW,
    )


def _resolve_hint_text(primary_tag: str) -> str:
    """Resolve Tier 1 hint text from config/teaching-comments.json.

    Uses the ``hint_text`` field (technique name + Japanese term only),
    NOT the full ``comment`` (which includes mechanism and is for C[] embedding).
    """
    tc_config = load_teaching_comments_config()
    comments = tc_config.correct_move_comments

    if primary_tag in comments:
        return comments[primary_tag].hint_text

    # Alias lookup: check alias_comments keys
    for entry in comments.values():
        if entry.alias_comments and primary_tag in entry.alias_comments:
            return entry.hint_text

    # No match found -- return empty (caller handles missing hints)
    return ""


def generate_hints(
    analysis: dict[str, Any],
    technique_tags: list[str],
    board_size: int = 19,
    *,
    detection_results: list | None = None,
    instinct_results: list | None = None,
    level_category: str = "entry",
    return_log: bool = False,
) -> list[str] | tuple[list[str], HintOperationLog]:
    """Generate 3-tier progressive hints for a puzzle.

    Args:
        analysis: AiAnalysisResult as dict
        technique_tags: Classified technique tags from technique_classifier
        board_size: Board size (9, 13, or 19). P0.3 fix: required for
            correct coordinate conversion on non-19×19 boards.
        detection_results: DetectionResult list from TechniqueStage (T14).
        instinct_results: InstinctResult list from InstinctStage (T15).
        level_category: 'entry'/'core'/'strong' for level-adaptive hints (T16).
        return_log: If True, return (hints, HintOperationLog) tuple.

    Returns:
        List of 3 strings: [tier1_technique, tier2_reasoning, tier3_coordinate].
        If return_log=True, returns (hints, HintOperationLog) tuple instead.
    """
    log = HintOperationLog()

    # T25: Solution-aware fallback when no tags detected
    if not technique_tags:
        inference = infer_technique_from_solution(analysis)
        log.inference_used = True
        log.inference_confidence = inference.confidence.name
        if inference.confidence >= InferenceConfidence.MEDIUM and inference.tag:
            technique_tags = [inference.tag]
            log.tier1_source = "inference"
        else:
            logger.warning(
                "No technique tags and inference too low -- returning empty hints",
                extra={"stage": 9},
            )
            hints: list[str] = ["", "", ""]
            if return_log:
                return (hints, log)
            return hints

    primary_tag = technique_tags[0]
    validation = analysis.get("validation", {})
    correct_move = validation.get("correct_move_gtp", "")
    difficulty = analysis.get("difficulty", {})
    solution_depth = difficulty.get("solution_depth", 0)

    # Tier 1: Technique hint from config (hint_text, not full comment)
    tier1 = _resolve_hint_text(primary_tag)
    if not log.tier1_source:
        log.tier1_source = "config" if tier1 else "none"

    # T15: Prefix Tier 1 with instinct phrase when available
    # RC-2: Gated behind instinct_enabled (C-3: requires AC-4 calibration)
    if instinct_results:
        from config.teaching import get_instinct_config
        instinct_cfg = get_instinct_config()
        if instinct_cfg.enabled:
            primary_instinct = instinct_results[0]  # Highest confidence
            instinct_phrase = instinct_cfg.instinct_phrases.get(
                primary_instinct.instinct, ""
            )
            if instinct_phrase and tier1:
                tier1 = f"{instinct_phrase} to {tier1[0].lower()}{tier1[1:]}" if len(tier1) > 1 else instinct_phrase
            elif instinct_phrase:
                tier1 = instinct_phrase

    # Tier 2: Reasoning hint (analysis-based)
    tier2 = _generate_reasoning_hint(
        primary_tag, analysis, technique_tags,
        detection_results=detection_results or [],
        level_category=level_category,
    )
    log.tier2_source = "analysis"

    # T27: Liberty analysis for capture-race/ko hints
    if primary_tag in SEMEAI_KO_TAGS:
        liberty_info = analysis.get("liberty_info")
        if liberty_info:
            tier2 = _enhance_with_liberty_info(tier2, liberty_info)

    # Tier 3: Coordinate hint with gating
    tier3 = ""

    # T23: Atari relevance gating — suppress coordinate for irrelevant atari
    if analysis.get("atari_at_correct_move") and primary_tag in ATARI_SKIP_TAGS:
        log.tier3_atari_suppressed = True
        log.tier3_source = "suppressed_atari"
    # RC-2: Tactical tag suppression — first move IS the answer for these tags
    elif primary_tag in TIER3_TACTICAL_SUPPRESS_TAGS:
        log.tier3_depth_gated = True
        log.tier3_source = "tactical_suppressed"
    # T24: Depth gating — suppress coordinate for shallow puzzles
    elif solution_depth < TIER3_DEPTH_THRESHOLD:
        log.tier3_depth_gated = True
        log.tier3_source = "depth_gated"
    else:
        tier3 = _generate_coordinate_hint(primary_tag, correct_move, board_size=board_size)
        log.tier3_source = "coordinate"

    log.tier1_value = tier1
    log.tier2_value = tier2
    log.tier3_value = tier3

    hints = [tier1, tier2, tier3]
    if return_log:
        return (hints, log)
    return hints


def format_yh_property(hints: list[str]) -> str:
    """Format hints as YH SGF property value (pipe-delimited, max 3).

    Args:
        hints: List of hint strings (typically 3)

    Returns:
        Pipe-delimited string e.g. "Focus on corner|Ladder pattern|{!cg}"
        Empty string if all hints are empty/whitespace.
    """
    # Filter out empty/whitespace-only hints, cap at 3 per SGF spec.
    # Strip pipe characters from content to prevent YH field corruption
    # (pipe is the tier delimiter in YH[tier1|tier2|tier3]).
    sanitized = [h.replace("|", " ") for h in hints[:3] if h and h.strip()]
    return "|".join(sanitized)


def _enhance_with_liberty_info(tier2: str, liberty_info: dict[str, Any]) -> str:
    """Enhance Tier 2 reasoning with liberty counts for capture-race/ko.

    Uses role-based labels ("Your"/"the opponent's") so hints remain
    correct when the frontend swaps stone colors via board transforms.
    """
    attacker_libs = liberty_info.get("attacker", 0)
    defender_libs = liberty_info.get("defender", 0)

    if attacker_libs > 0 and defender_libs > 0:
        if attacker_libs != defender_libs:
            return (
                f"{tier2} Your weakest group has {attacker_libs} liberties, "
                f"the opponent's has {defender_libs} — who needs to act first?"
            )
        return f"{tier2} Both sides have {attacker_libs} liberties — timing is critical."

    return tier2


def _generate_reasoning_hint(
    primary_tag: str,
    analysis: dict[str, Any],
    technique_tags: list[str],
    *,
    detection_results: list | None = None,
    level_category: str = "entry",
) -> str:
    """Generate Tier 2 reasoning hint from KataGo analysis context."""
    difficulty = analysis.get("difficulty", {})
    depth = difficulty.get("solution_depth", 0)
    refutation_count = difficulty.get("refutation_count", 0)

    # T14 (removed): DetectionResult.evidence is developer-facing diagnostic
    # text (e.g. "PV diagonal ratio 0.50", "2 adjacent race pair(s) found")
    # that must NOT appear in user-facing hints.  Evidence is preserved in
    # enrichment logs via the stage_runner; Tier 2 always uses the
    # level-adaptive templates below.

    # T16: Level-adaptive hint content
    if level_category == "strong" and depth > 0:
        base = f"{depth}-move sequence of reading required."
        if refutation_count > 0:
            base += f" Watch for {refutation_count} trap{'s' if refutation_count > 1 else ''}."
    elif level_category == "core":
        parts = []
        if depth > 0:
            parts.append(f"This requires {depth} moves of careful reading.")
        if refutation_count > 0:
            parts.append(
                f"There {'are' if refutation_count > 1 else 'is'} "
                f"{refutation_count} tempting wrong move{'s' if refutation_count > 1 else ''}."
            )
        base = " ".join(parts) if parts else "Read carefully before playing."
    else:
        # "entry" uses existing default behavior
        parts = []
        if depth > 0:
            parts.append(f"The solution requires {depth} move{'s' if depth > 1 else ''} of reading.")
        if refutation_count > 0:
            parts.append(
                f"There {'are' if refutation_count > 1 else 'is'} "
                f"{refutation_count} tempting wrong move{'s' if refutation_count > 1 else ''}."
            )
        base = " ".join(parts) if parts else "Read carefully before playing."

    # Add secondary technique context if multiple tags
    if len(technique_tags) > 1:
        secondary = technique_tags[1]
        if secondary != primary_tag:
            secondary_hint = _resolve_hint_text(secondary)
            if secondary_hint:
                base += f" Also consider: {secondary_hint.lower()}"

    return base


def _generate_coordinate_hint(
    primary_tag: str,
    correct_move: str,
    board_size: int = 19,
) -> str:
    """Generate Tier 3 coordinate hint with {!xy} token.

    Converts GTP coordinate (e.g., 'A19') to SGF coordinate token (e.g., '{!as}').
    P0.3 fix: board_size is now passed through for correct conversion.
    """
    template = COORDINATE_TEMPLATES.get(
        primary_tag,
        COORDINATE_TEMPLATES["default"],
    )

    if not correct_move or correct_move.lower() == "pass":
        return template.replace("{!xy}", "{!??}")

    sgf_coord = _gtp_to_sgf_token(correct_move, board_size=board_size)
    return template.replace("{!xy}", f"{{!{sgf_coord}}}")


def _gtp_to_sgf_token(gtp_move: str, board_size: int = 19) -> str:
    """Convert GTP coordinate (e.g., 'C7') to SGF coordinate (e.g., 'cg').

    GTP: columns A-T (skip I), rows 1-board_size (bottom=1)
    SGF: columns a-{last} (1-board_size), rows a-{last} (top=a)

    P0.3 fix: ``board_size`` is now a parameter (was hardcoded 19).
    On a 9×9 board:  GTP 'A1' → SGF 'ai' (row i = 9th from top).
    On a 19×19 board: GTP 'A1' → SGF 'as' (row s = 19th from top).
    """
    if not gtp_move or gtp_move.lower() == "pass":
        return "??"

    m = re.match(r"^([A-HJ-T])(\d{1,2})$", gtp_move.upper())
    if not m:
        return "??"

    col_letter = m.group(1)
    row_num = int(m.group(2))

    # GTP column to 1-indexed: A=1, B=2, ..., H=8, J=9 (skip I)
    col_idx = ord(col_letter) - ord("A") + 1
    if col_letter >= "J":
        col_idx -= 1  # Adjust for skipped 'I'

    # SGF column: a=1, b=2, ...
    sgf_col = chr(ord("a") + col_idx - 1)

    # SGF row: a=top, last=bottom
    # row_num=1 (bottom) → sgf_row = chr(a + board_size - 1)
    # row_num=board_size (top) → sgf_row = chr(a + 0) = 'a'
    sgf_row = chr(ord("a") + board_size - row_num)

    return f"{sgf_col}{sgf_row}"
