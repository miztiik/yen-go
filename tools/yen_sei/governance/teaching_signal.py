"""Extract teaching-quality signals from a single SGF puzzle.

Signals are computed from the parsed solution tree (not just root).
Used by the qualify stage to score every puzzle in external-sources/.
All thresholds come from CurationConfig — this module only computes raw signals.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tools.core.english_score import score_english
from tools.core.go_teaching_constants import EXPLANATION_KEYWORDS, GO_TECHNIQUE_PATTERN
from tools.core.sgf_parser import SgfNode, SgfTree, parse_sgf
from tools.core.text_cleaner import strip_cjk, strip_html, strip_urls
from tools.yen_sei.data_paths import to_posix_rel

from .config_loader import CurationConfig

# AI-enrichment detection: YQ[q:_;rc:_;hc:_;ac:N] where ac>0 means the puzzle
# was processed by an automated/LLM enrichment tool. We must NOT train on those.
_YQ_PROP_RE = re.compile(r"YQ\[([^\]]*)\]")
_YQ_AC_RE = re.compile(r"ac:(\d+)")
# AI-comment signature heuristics. Older OpenAI-template puzzles tend to
# emit prose with these tells. Each match increments ai_signature_hits.
_AI_SIGNATURE_PATTERNS = [
    re.compile(r"\bthe correct move is\b", re.IGNORECASE),
    re.compile(r"\bthe optimal (?:sequence|move)\b", re.IGNORECASE),
    re.compile(r"\bblack to play and (?:live|kill|win)\b", re.IGNORECASE),
    re.compile(r"\bas an ai\b", re.IGNORECASE),
    re.compile(r"\(B \d+-\d+\)\s*[\u2192>-]+\s*\(W \d+-\d+\)"),  # coordinate dump
    re.compile(r"\bin this puzzle,?\s+the (?:goal|objective|task)\b", re.IGNORECASE),
]


@dataclass
class TeachingSignals:
    """Raw signals extracted from one puzzle. No tier decision yet."""
    # Provenance
    source: str
    file_path: str
    original_stem: str

    # Board
    board_size: int = 0
    stone_count: int = 0
    variation_count: int = 0
    total_node_count: int = 0

    # Comment-based teaching signals
    correct_explanation_chars: int = 0
    wrong_explanation_chars: int = 0
    explanation_node_count: int = 0
    causal_phrase_count: int = 0
    technique_mentions: int = 0
    techniques_found: list[str] = field(default_factory=list)
    refutation_phrase_count: int = 0  # in-prose markers of wrong-move discussion (used by prose_fallback gate)

    # Marker-based structural hints (from TE/BM/DO/IT properties)
    te_count: int = 0  # tesuji / good move marker
    bm_count: int = 0  # bad move marker
    do_count: int = 0  # doubtful
    it_count: int = 0  # interesting

    # Language signals
    ascii_letter_ratio: float = 0.0
    stopword_hits_per_100_chars: float = 0.0
    english_word_ratio: float = 0.0  # 0..1, primary tier signal
    is_english: bool = False

    # AI-enrichment provenance (Schema v15 YQ property + heuristic).
    # ac: 0=untouched, 1=enriched, 2=ai_solved, 3=verified.
    # ai_signature_hits: count of AI-comment template phrases found in prose.
    yq_ac: int = 0
    ai_signature_hits: int = 0

    # Solution structure (used by eval test-set generation when there is no
    # teaching prose to verify against). The first move on each first-level
    # branch of the solution tree, classified as correct or wrong using the
    # same is_correct flag the walk already uses.
    correct_first_move: str = ""
    wrong_first_moves: list[str] = field(default_factory=list)

    # Hard-gate failure list (empty = passes all gates)
    gate_failures: list[str] = field(default_factory=list)


def _strip_markers(text: str, cfg: CurationConfig) -> str:
    """Remove leading marker prefix and core CJK/HTML noise."""
    if not text:
        return ""
    cleaned = text
    if cfg.language.strip_cjk_via_core:
        cleaned = strip_cjk(strip_html(strip_urls(cleaned)))
    # Strip leading marker (e.g. "Correct! Good ", "Wrong: ")
    cleaned = cfg.markers.prefix_regex.sub("", cleaned).strip()
    return cleaned


def _is_marker_only(text: str, cfg: CurationConfig) -> bool:
    """A comment is marker-only if AFTER stripping prefix + CJK + HTML it's
    too short to teach anything OR it's an exact match in the marker set."""
    if not text:
        return True
    stripped = _strip_markers(text, cfg)
    if not stripped:
        return True
    # Exact-match against base marker vocabulary (lowercased)
    if stripped.lower() in cfg.markers.all_markers:
        return True
    return len(stripped) < cfg.markers.min_chars_after_strip


# Causal/explanation regex: same vocabulary as GO_TECHNIQUE_PATTERN style
_EXPLANATION_RE = None  # lazily compiled


def _explanation_pattern():
    global _EXPLANATION_RE
    if _EXPLANATION_RE is None:
        import re as _re
        words = sorted(EXPLANATION_KEYWORDS, key=len, reverse=True)
        _EXPLANATION_RE = _re.compile(r"\b(" + "|".join(_re.escape(w) for w in words) + r")\b", _re.IGNORECASE)
    return _EXPLANATION_RE


def _walk(node: SgfNode, on_correct_path: bool, signals: TeachingSignals, cfg: CurationConfig, all_text: list[str]) -> None:
    """Recurse the solution tree, accumulating signals."""
    signals.total_node_count += 1

    # Marker-property counts (independent of comment text)
    props = node.properties or {}
    if "TE" in props:
        signals.te_count += 1
    if "BM" in props:
        signals.bm_count += 1
    if "DO" in props:
        signals.do_count += 1
    if "IT" in props:
        signals.it_count += 1

    # Determine correctness: SGF flag + TE/BM hint
    is_correct = on_correct_path and node.is_correct
    if "TE" in props:
        is_correct = True
    if "BM" in props:
        is_correct = False

    comment = node.comment or ""
    if comment and not _is_marker_only(comment, cfg):
        stripped = _strip_markers(comment, cfg)
        n_chars = len(stripped)
        all_text.append(stripped)

        if is_correct:
            signals.correct_explanation_chars += n_chars
        else:
            signals.wrong_explanation_chars += n_chars

        signals.explanation_node_count += 1

        # Causal phrases
        signals.causal_phrase_count += len(_explanation_pattern().findall(stripped))

        # Technique mentions
        techs = [m.group(1).lower() for m in GO_TECHNIQUE_PATTERN.finditer(stripped)]
        signals.technique_mentions += len(techs)
        for t in techs:
            if t not in signals.techniques_found:
                signals.techniques_found.append(t)

    for child in node.children:
        # Children of an incorrect branch stay incorrect
        next_correct = is_correct and child.is_correct
        _walk(child, next_correct, signals, cfg, all_text)


def extract_signals(sgf_path: Path, source: str, cfg: CurationConfig) -> TeachingSignals:
    """Parse one SGF and compute all teaching signals."""
    signals = TeachingSignals(
        source=source,
        file_path=to_posix_rel(sgf_path),
        original_stem=sgf_path.stem,
    )

    # Read raw text first for fast pre-parse complexity gate.
    try:
        raw = sgf_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        signals.gate_failures.append(f"unreadable:{type(e).__name__}")
        return signals

    # AI-enrichment detection
    yq_match = _YQ_PROP_RE.search(raw)
    if yq_match:
        ac_match = _YQ_AC_RE.search(yq_match.group(1))
        if ac_match:
            signals.yq_ac = int(ac_match.group(1))
    if signals.yq_ac > 0:
        signals.gate_failures.append("ai_enriched")

    # Cheap structural gates. Do these first.
    open_paren_count = raw.count("(;")
    if open_paren_count > 500:
        signals.variation_count = open_paren_count
        signals.gate_failures.append("too_many_branches")
        return signals
    if len(raw) > 200_000:
        signals.gate_failures.append("file_too_large")
        return signals

    try:
        tree: SgfTree = parse_sgf(raw)
    except Exception as e:
        signals.gate_failures.append(f"parse_error:{type(e).__name__}")
        return signals

    signals.board_size = tree.board_size
    signals.stone_count = len(tree.black_stones) + len(tree.white_stones)

    # Variation count = nodes in solution tree with siblings
    if tree.solution_tree:
        signals.variation_count = sum(
            1 for n in _all_nodes(tree.solution_tree) if len(n.children) > 1
        ) + 1  # +1 for root having ≥1 child counts as 1 variation point baseline
    # Use raw "(;" count fallback
    if signals.variation_count < 2:
        signals.variation_count = max(signals.variation_count, open_paren_count)

    # Walk the tree and accumulate text/marker signals
    all_text: list[str] = []
    if tree.root_comment and not _is_marker_only(tree.root_comment, cfg):
        root_clean = _strip_markers(tree.root_comment, cfg)
        signals.correct_explanation_chars += len(root_clean)
        signals.explanation_node_count += 1
        all_text.append(root_clean)
        signals.causal_phrase_count += len(_explanation_pattern().findall(root_clean))
        for m in GO_TECHNIQUE_PATTERN.finditer(root_clean):
            t = m.group(1).lower()
            signals.technique_mentions += 1
            if t not in signals.techniques_found:
                signals.techniques_found.append(t)

    if tree.solution_tree:
        _walk(tree.solution_tree, True, signals, cfg, all_text)

    # First-move classification: examine the first-level children of the
    # solution-tree root. Each branch's first move is the candidate; whether
    # it's correct/wrong follows the same flag the walk uses. Used by eval
    # test-set generation when there is no teaching prose to verify against.
    if tree.solution_tree:
        for child in tree.solution_tree.children:
            if child.move is None:
                continue
            try:
                move = child.move.to_sgf()
            except Exception:
                continue
            child_correct = bool(child.is_correct)
            props = child.properties or {}
            if "TE" in props:
                child_correct = True
            if "BM" in props:
                child_correct = False
            if child_correct and not signals.correct_first_move:
                signals.correct_first_move = move
            elif not child_correct and move not in signals.wrong_first_moves:
                signals.wrong_first_moves.append(move)

    # English-ness on the concatenation of all teaching text
    combined = " ".join(all_text)
    es = score_english(
        combined,
        method=cfg.language.method,
        min_ascii_ratio=cfg.language.min_ascii_letter_ratio,
        min_stopword_per_100=cfg.language.min_stopword_hits_per_100_chars,
        stopwords=cfg.language.stopwords,
        wordfreq_min_zipf=cfg.language.wordfreq_min_zipf,
    )
    signals.ascii_letter_ratio = round(es.ascii_letter_ratio, 3)
    signals.stopword_hits_per_100_chars = round(es.stopword_hits_per_100_chars, 2)
    signals.english_word_ratio = round(es.ascii_letter_ratio, 3)  # primary signal = ascii ratio
    signals.is_english = (
        es.is_english_heuristic
        if cfg.language.method == "heuristic"
        else (es.is_english_heuristic and bool(es.is_english_wordfreq))
    )

    # Hard gates
    g = cfg.hard_gates
    if signals.board_size not in g.valid_board_sizes:
        signals.gate_failures.append("invalid_board_size")
    if signals.stone_count < g.min_stones:
        signals.gate_failures.append("too_few_stones")
    if signals.stone_count > g.max_stones:
        signals.gate_failures.append("too_many_stones")

    # Count in-prose refutation phrases on the combined teaching text.
    # Used by the teachable_content gate (variation tree OR prose monologue).
    pf = g.prose_fallback
    if pf.refutation_phrases:
        combined_lower = combined.lower()
        signals.refutation_phrase_count = sum(
            combined_lower.count(p) for p in pf.refutation_phrases
        )

    # AI-comment signature heuristic (fires on ac==0 puzzles whose authors
    # nonetheless used templated prose). Counts once per pattern occurrence.
    if combined:
        signals.ai_signature_hits = sum(
            len(p.findall(combined)) for p in _AI_SIGNATURE_PATTERNS
        )
        if signals.ai_signature_hits >= 2:
            signals.gate_failures.append("ai_signature_prose")

    # teachable_content gate: structural OR prose path.
    has_tree_branches = signals.variation_count >= g.min_variations
    has_prose_teaching = (
        pf.enabled
        and signals.correct_explanation_chars >= pf.min_correct_explanation_chars
        and signals.refutation_phrase_count >= pf.min_refutation_phrase_count
    )
    if not (has_tree_branches or has_prose_teaching):
        # Preserve old failure code for back-compat with anyone grepping logs.
        signals.gate_failures.append("no_variations")

    if g.exclude_full_games and signals.total_node_count > g.max_total_moves:
        signals.gate_failures.append("looks_like_full_game")

    return signals


def _all_nodes(node: SgfNode):
    """Yield every node in the subtree (preorder)."""
    yield node
    for child in node.children:
        yield from _all_nodes(child)


def signals_to_dict(s: TeachingSignals) -> dict:
    """Serialize for JSONL output. Lists become lists."""
    return asdict(s)
