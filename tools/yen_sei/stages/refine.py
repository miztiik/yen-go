"""refine stage: Filter, normalize, and format into SFT-ready JSONL.

Reads raw harvest output, applies quality filters, restructures
comments into ChatML conversations with tagged text assistant responses.
"""

from __future__ import annotations

import json
import logging
import random
from hashlib import sha256
from pathlib import Path

from tools.core.go_teaching_constants import GO_TECHNIQUE_PATTERN, MARKER_ONLY_PATTERNS
from tools.core.teaching_schema import format_tagged_text, parse_tagged_text
from tools.yen_sei.governance.text_normalizer import normalize_section_body
from tools.yen_sei.config import (
    DEFAULT_MIN_COMMENT_LENGTH,
    RAW_JSONL,
    RAW_POLISHED_JSONL,
    REFINED_DIR,
    SFT_JSONL,
    SFT_METADATA_JSONL,
    SPLIT_RATIOS,
    SYSTEM_PROMPT,
    TRAIN_JSONL,
    VAL_JSONL,
)
from tools.yen_sei.governance.config_loader import load_config
from tools.yen_sei.models.raw_extract import RawExtract
from tools.yen_sei.models.training_example import ChatMessage, ExampleMetadata, TrainingExample
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)


def _is_marker_only(text: str) -> bool:
    """Check if comment is just a correctness marker."""
    return text.strip().lower() in MARKER_ONLY_PATTERNS


def _compute_quality_score(record: RawExtract) -> float:
    """Heuristic quality score 0.0-1.0 based on comment richness."""
    if record.total_comment_chars == 0:
        return 0.0

    # Count teaching-quality comments (non-marker, 40+ chars)
    teaching_count = sum(
        1
        for n in record.solution_nodes
        if len(n.comment) >= 40 and not _is_marker_only(n.comment)
    )
    root_teaching = 1 if len(record.root_comment) >= 40 and not _is_marker_only(record.root_comment) else 0

    total_nodes = len(record.solution_nodes) + 1  # +1 for root
    teaching_ratio = (teaching_count + root_teaching) / max(total_nodes, 1)

    # Length bonus
    length_score = min(record.total_comment_chars / 500, 1.0)

    return min((teaching_ratio * 0.6 + length_score * 0.4), 1.0)


# Concept-level fallback hints derived from tags. The OLD hint #2
# implementation copied a 50-char prefix of the correct-move comment
# into the hint, which trained the model to copy answer prefixes
# instead of reasoning. We now emit a *concept* (vital point, eye shape,
# liberty race, etc.) drawn from tags; if no tag matches we omit hint #2
# entirely rather than leak the answer.
#
# See IMPROVEMENT_PLAN.md §1.1 [P0-4].
_TAG_TO_CONCEPT: dict[str, str] = {
    "life-and-death": "Eye shape and vital point",
    "life": "Make two eyes",
    "death": "Destroy the eye shape",
    "kill": "Find the vital point",
    "alive": "Make two eyes",
    "ko": "Ko fight — timing and threats",
    "semeai": "Capturing race — count liberties",
    "liberty": "Liberty count decides this",
    "liberties": "Liberty count decides this",
    "shortage": "Shortage of liberties",
    "ladder": "Ladder reading",
    "net": "Net the cutting stone",
    "snapback": "Snapback — sacrifice and recapture",
    "throw-in": "Throw-in tesuji",
    "placement": "Vital-point placement",
    "hane": "Hane at the head",
    "connect": "Connection problem",
    "cut": "Cutting point matters",
    "endgame": "Endgame — sente vs gote",
    "tesuji": "Find the tesuji",
    "seki": "Seki — mutual life",
    "capture": "Capture sequence",
    "sacrifice": "Sacrifice for shape",
    "nakade": "Nakade — dead shape inside",
}


def _extract_hints(record: RawExtract) -> list[str]:
    """Extract up to 2 progressive hints from raw puzzle data.

    Hint 1 (technique): Go technique name found in comments or tags.
    Hint 2 (concept): Concept phrase derived from tags.

    Coordinate hints ({!xy}) are NOT generated — they are computed from the
    SGF solution tree at publish/serve time.

    Hint 2 used to copy a 50-char prefix of the correct-move comment, which
    trained the model to leak answer prefixes. Now it emits a concept from
    tags or is omitted entirely. See IMPROVEMENT_PLAN.md §1.1 [P0-4].
    """
    hints: list[str] = []

    # Hint 1: Technique name (from comments first, then tags)
    technique = ""
    all_comments = [record.root_comment] + [n.comment for n in record.solution_nodes]
    for comment in all_comments:
        if not comment or _is_marker_only(comment):
            continue
        match = GO_TECHNIQUE_PATTERN.search(comment)
        if match:
            technique = match.group(1).capitalize()
            break
    if not technique and record.tags:
        for tag in record.tags:
            tag_clean = tag.strip().lower().replace("-", " ")
            match = GO_TECHNIQUE_PATTERN.search(tag_clean)
            if match:
                technique = match.group(1).capitalize()
                break
    if technique:
        hints.append(technique)

    # Hint 2: Concept derived from tags. NEVER copy from the answer.
    if record.tags:
        for tag in record.tags:
            concept = _TAG_TO_CONCEPT.get(tag.strip().lower())
            if concept and concept != (hints[0] if hints else ""):
                hints.append(concept)
                break

    return hints


def _build_user_prompt(record: RawExtract) -> str:
    """Build the user prompt from puzzle context.

    EVAL HONESTY: we deliberately do NOT include `record.root_comment` here.
    The root comment often paraphrases the answer; including it leaks the
    label into the prompt and inflates val/test scores.

    SIMPLICITY: Level and Tags are omitted — they are yen-go custom terms
    (not standard Go kyu/dan) and add noise (25-44% missing, heavily skewed).
    The model sees only board + side-to-move + setup stones.
    """
    lines = [
        f"Board: {record.board_size}x{record.board_size}",
        f"{record.player_to_move} to play",
    ]
    if record.setup_black:
        lines.append(f"Black stones: {', '.join(record.setup_black[:20])}")
    if record.setup_white:
        lines.append(f"White stones: {', '.join(record.setup_white[:20])}")
    return "\n".join(lines)


def _build_assistant_response(record: RawExtract) -> str:
    """Build the assistant response as tagged text.

    Maps freeform SGF comments into a structured tagged text format.
    Picks the LONGEST teaching comment on the correct path (not just the first)
    so deep teaching nodes aren't lost when the first correct node is just a marker.

    No summary field. No JSON. No coordinates in output.
    """
    correct_candidates: list[str] = []
    wrong_comments: dict[str, str] = {}

    for node in record.solution_nodes:
        if _is_marker_only(node.comment):
            continue
        if not node.comment:
            continue

        if node.is_correct:
            correct_candidates.append(node.comment)
        else:
            # Keep the first non-empty comment per move (avoid overwriting rich text)
            if node.move not in wrong_comments:
                wrong_comments[node.move] = node.comment

    correct_raw = max(correct_candidates, key=len) if correct_candidates else ""

    # P0-1 + P0-2: deterministic inner-content normalization. Strips
    # boilerplate (Correct!, **->**, (;Correct), etc.), CN→EN markers,
    # coordinates, and ordinal-move references BEFORE the text reaches
    # the SFT target. Idempotent.
    correct_comment = normalize_section_body(correct_raw)
    wrong_comments = {
        coord: normalized
        for coord, raw in wrong_comments.items()
        if (normalized := normalize_section_body(raw))
    }

    hints = _extract_hints(record)

    return format_tagged_text(correct_comment, wrong_comments, hints)


def _position_hash(record: RawExtract) -> str:
    """Hash board position for deduplication."""
    key = f"{record.board_size}|{sorted(record.setup_black)}|{sorted(record.setup_white)}|{record.player_to_move}"
    return sha256(key.encode()).hexdigest()[:16]


def run_refine(
    input_path: str | None = None,
    output_path: str | None = None,
    min_length: int = DEFAULT_MIN_COMMENT_LENGTH,
    show_stats: bool = False,
    config_path: str | None = None,
) -> None:
    """Run the refine stage with tier-aware weighted upsampling."""
    set_context(stage="refine")
    cfg = load_config(config_path)
    # Prefer the polished raw if present (P0-3). Falls through to RAW_JSONL
    # otherwise, so this is a no-op for runs that haven't polished yet.
    if input_path:
        raw_path = Path(input_path)
    elif RAW_POLISHED_JSONL.exists():
        raw_path = RAW_POLISHED_JSONL
        logger.info("Using polished raw input: %s", raw_path)
    else:
        raw_path = RAW_JSONL
    out_path = Path(output_path) if output_path else SFT_JSONL

    if not raw_path.exists():
        logger.error("Input file not found: %s. Run 'harvest' first.", raw_path)
        return

    # Load raw extracts
    records: list[RawExtract] = []
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            records.append(RawExtract.model_validate_json(line))

    logger.info("Loaded %d raw extracts", len(records))

    # Tier-aware dedup: on position-hash collision, keep highest-tier record
    tier_rank = {"gold": 3, "silver": 2, "bronze": 1}
    best_by_hash: dict[str, RawExtract] = {}
    filter_stats = {"too_short": 0, "marker_only": 0, "duplicate_lower_tier": 0, "passed": 0}

    for record in records:
        # Min length filter (after stripping marker-only comments)
        non_marker_chars = sum(
            len(n.comment) for n in record.solution_nodes if not _is_marker_only(n.comment)
        )
        if not _is_marker_only(record.root_comment):
            non_marker_chars += len(record.root_comment)

        if non_marker_chars < min_length:
            filter_stats["too_short"] += 1
            continue

        pos_hash = _position_hash(record)
        existing = best_by_hash.get(pos_hash)
        if existing is not None:
            if tier_rank.get(record.tier, 0) > tier_rank.get(existing.tier, 0):
                best_by_hash[pos_hash] = record
                filter_stats["duplicate_lower_tier"] += 1
            else:
                filter_stats["duplicate_lower_tier"] += 1
            continue
        best_by_hash[pos_hash] = record

    filtered = list(best_by_hash.values())
    filter_stats["passed"] = len(filtered)
    logger.info("Filtered: %s", filter_stats)

    # Build training examples (one per unique position)
    # Tiers with weight==0 are dropped here so they don't leak into val/test.
    # Final response-quality gate: the assembled assistant JSON must contain at
    # least MIN_CORRECT_RESPONSE_CHARS of teaching prose OR have at least one
    # wrong_comment with MIN_WRONG_RESPONSE_CHARS — anything thinner is dropped
    # because per-tree signals (used in qualify) can be richer than what the
    # first/longest correct node actually says.
    MIN_CORRECT_RESPONSE_CHARS = 40
    MIN_WRONG_RESPONSE_CHARS = 40

    examples: list[TrainingExample] = []
    weights = cfg.training_weights
    excluded_zero_weight = 0
    excluded_thin_response = 0
    for record in filtered:
        weight = float(weights.get(record.tier, 1.0))
        if weight <= 0.0:
            excluded_zero_weight += 1
            continue
        assistant_text = _build_assistant_response(record)
        try:
            correct, wrongs, _ = parse_tagged_text(assistant_text)
            cc_len = len(correct.strip())
            max_wc_len = max((len(w.strip()) for w in wrongs), default=0)
        except ValueError:
            excluded_thin_response += 1
            continue
        if cc_len < MIN_CORRECT_RESPONSE_CHARS and max_wc_len < MIN_WRONG_RESPONSE_CHARS:
            excluded_thin_response += 1
            continue
        quality = _compute_quality_score(record)
        example = TrainingExample(
            messages=[
                ChatMessage(role="system", content=SYSTEM_PROMPT),
                ChatMessage(role="user", content=_build_user_prompt(record)),
                ChatMessage(role="assistant", content=assistant_text),
            ],
            metadata=ExampleMetadata(
                source=record.source,
                tier=record.tier,
                file_path=record.file_path,
                split="train",  # Reassigned below (stratified)
                comment_quality_score=quality,
                sample_weight=weight,
            ),
        )
        examples.append(example)
    if excluded_zero_weight:
        logger.info("Excluded %d examples with tier weight 0.0", excluded_zero_weight)
    if excluded_thin_response:
        logger.info("Excluded %d examples with thin assembled response", excluded_thin_response)

    # P0-5: Cap any single templated `correct_comment` cluster to <=15% of corpus.
    # After P0-1 normalization, templated rows like "Black has formed two eyes
    # and is alive." collapse to identical text, so exact-text grouping is
    # sufficient (no SimHash needed). Excess rows are dropped, not reweighted.
    # See IMPROVEMENT_PLAN.md §1.1 [P0-5].
    TEMPLATE_CAP_RATIO = 0.15
    cap = max(1, int(len(examples) * TEMPLATE_CAP_RATIO))
    by_correct: dict[str, list[TrainingExample]] = {}
    for ex in examples:
        # Last message is assistant; parse out the CORRECT body for clustering
        try:
            correct, _, _ = parse_tagged_text(ex.messages[-1].content)
        except ValueError:
            continue
        by_correct.setdefault(correct.strip().lower(), []).append(ex)
    capped: list[TrainingExample] = []
    capped_dropped = 0
    capped_clusters: list[tuple[str, int, int]] = []
    for key, group in by_correct.items():
        if len(group) > cap:
            capped_dropped += len(group) - cap
            capped_clusters.append((key[:60], len(group), cap))
            random.Random(42).shuffle(group)
            capped.extend(group[:cap])
        else:
            capped.extend(group)
    if capped_dropped:
        logger.info(
            "Template cap (<=%d, %.0f%% of %d): dropped %d duplicate-target rows across %d clusters",
            cap, TEMPLATE_CAP_RATIO * 100, len(examples), capped_dropped, len(capped_clusters),
        )
        for preview, n_before, n_after in capped_clusters[:3]:
            logger.info("  cluster %r: %d -> %d", preview, n_before, n_after)
    examples = capped

    # Stratified splits per tier (so val contains proportional gold/silver/bronze).
    # No test split — test sets are built separately by eval_prep from marker-only pools.
    random.seed(42)
    split_buckets: dict[str, list[TrainingExample]] = {"train": [], "val": []}
    by_tier: dict[str, list[TrainingExample]] = {}
    for ex in examples:
        by_tier.setdefault(ex.metadata.tier, []).append(ex)
    for tier, group in by_tier.items():
        random.shuffle(group)
        n = len(group)
        n_val = int(n * SPLIT_RATIOS["val"])
        n_train = n - n_val
        for i, ex in enumerate(group):
            if i < n_train:
                ex.metadata.split = "train"
            else:
                ex.metadata.split = "val"
            split_buckets[ex.metadata.split].append(ex)

    REFINED_DIR.mkdir(parents=True, exist_ok=True)
    split_files = {
        "train": TRAIN_JSONL,
        "val": VAL_JSONL,
    }

    # Write outputs. NO upsampling — each unique example is written exactly
    # once. Tier balance is achieved at INGEST time via bronze_selection cap.
    # If a tier has training_weights == 0 the example is dropped entirely
    # (used to fully exclude a tier from train+val+test).
    with out_path.open("w", encoding="utf-8-sig") as f_all, \
         SFT_METADATA_JSONL.open("w", encoding="utf-8-sig") as f_meta:
        writers = {split: path.open("w", encoding="utf-8-sig") for split, path in split_files.items()}
        try:
            written_per_split: dict[str, int] = {"train": 0, "val": 0}
            written_per_tier: dict[str, int] = {}
            for split_name, group in split_buckets.items():
                for ex in group:
                    if ex.metadata.sample_weight <= 0.0:
                        continue  # excluded tier
                    messages_only = {"messages": [m.model_dump() for m in ex.messages]}
                    line = json.dumps(messages_only, ensure_ascii=False) + "\n"
                    meta_line = json.dumps(ex.metadata.model_dump(), ensure_ascii=False) + "\n"
                    writers[split_name].write(line)
                    f_all.write(line)
                    f_meta.write(meta_line)
                    written_per_split[split_name] += 1
                    written_per_tier[ex.metadata.tier] = written_per_tier.get(ex.metadata.tier, 0) + 1
        finally:
            for w in writers.values():
                w.close()

    logger.info("Refine complete: %d unique → %d emitted (no upsampling)",
                len(examples), sum(written_per_split.values()))
    logger.info("Per split: %s", written_per_split)
    logger.info("Per tier (post-weight): %s", written_per_tier)

    if show_stats:
        source_counts: dict[str, int] = {}
        for ex in examples:
            src = ex.metadata.source
            source_counts[src] = source_counts.get(src, 0) + 1
        unique_per_tier: dict[str, int] = {}
        for ex in examples:
            unique_per_tier[ex.metadata.tier] = unique_per_tier.get(ex.metadata.tier, 0) + 1

        print(f"\n{'='*50}")
        print("REFINE STATISTICS")
        print(f"{'='*50}")
        print(f"Input records:                  {len(records)}")
        print(f"Unique positions kept:          {len(examples)}")
        print(f"Total rows emitted:             {sum(written_per_split.values())}")
        print("\nFilter breakdown:")
        for reason, count in filter_stats.items():
            print(f"  {reason}: {count}")
        print("\nUnique examples by tier:")
        for tier in ("gold", "silver", "bronze"):
            if unique_per_tier.get(tier):
                w = cfg.training_weights.get(tier, 1.0)
                print(f"  {tier}: {unique_per_tier[tier]:>5} (weight {w})")
        print("\nEmitted rows by tier (post-weight):")
        for tier in ("gold", "silver", "bronze"):
            if written_per_tier.get(tier):
                print(f"  {tier}: {written_per_tier[tier]:>5}")
        print("\nBy source (unique):")
        for src, count in sorted(source_counts.items()):
            print(f"  {src}: {count}")
        print("\nSplit (rows written):")
        for split, count in written_per_split.items():
            print(f"  {split}: {count}")
        print("\nQuality score distribution (unique):")
        scores = [e.metadata.comment_quality_score for e in examples]
        for bucket in [0.0, 0.2, 0.4, 0.6, 0.8]:
            count = sum(1 for s in scores if bucket <= s < bucket + 0.2)
            print(f"  {bucket:.1f}-{bucket+0.2:.1f}: {count}")
