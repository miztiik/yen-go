"""refine stage: Filter, normalize, and format into SFT-ready JSONL.

Reads raw harvest output, applies quality filters, restructures
comments into ChatML conversations matching the TeachingOutput schema.
"""

from __future__ import annotations

import json
import logging
import random
from hashlib import sha256
from pathlib import Path

from tools.core.go_teaching_constants import GO_TECHNIQUE_PATTERN, MARKER_ONLY_PATTERNS
from tools.core.teaching_schema import TeachingComments, TeachingOutput
from tools.yen_sei.config import (
    DEFAULT_MIN_COMMENT_LENGTH,
    RAW_JSONL,
    REFINED_DIR,
    SFT_JSONL,
    SFT_METADATA_JSONL,
    SPLIT_RATIOS,
    TEST_JSONL,
    TRAIN_JSONL,
    VAL_JSONL,
)
from tools.yen_sei.governance.config_loader import load_config
from tools.yen_sei.models.raw_extract import RawExtract
from tools.yen_sei.models.training_example import ChatMessage, ExampleMetadata, TrainingExample
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)

# System prompt for SFT training — voice/tone only; training examples teach the JSON structure.
SYSTEM_PROMPT = (
    "You are a professional Go teacher. Explain why moves work or fail by describing "
    "board consequences — liberties, shape, technique. Be concise and strategic. "
    "Respond in JSON."
)


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


def _extract_hints(record: RawExtract) -> list[str]:
    """Extract up to 3 progressive hints from raw puzzle data.

    Hint 1 (technique): Go technique name found in comments or tags.
    Hint 2 (reasoning): Short reasoning phrase from correct-move comment.
    Hint 3 (coordinate): First correct move as {!xy} coordinate token.
    """
    hints: list[str] = []

    # Hint 1: Technique name
    technique = ""
    # Check comments first
    all_comments = [record.root_comment] + [n.comment for n in record.solution_nodes]
    for comment in all_comments:
        if not comment or _is_marker_only(comment):
            continue
        match = GO_TECHNIQUE_PATTERN.search(comment)
        if match:
            technique = match.group(1).capitalize()
            break
    # Fallback: check tags
    if not technique and record.tags:
        for tag in record.tags:
            tag_clean = tag.strip().lower().replace("-", " ")
            match = GO_TECHNIQUE_PATTERN.search(tag_clean)
            if match:
                technique = match.group(1).capitalize()
                break
    hints.append(technique if technique else "Tactical reading")

    # Hint 2: Reasoning phrase from correct-move comment
    reasoning = ""
    for node in record.solution_nodes:
        if node.is_correct and node.comment and not _is_marker_only(node.comment):
            # Take the first sentence or clause (up to first period, comma, or dash)
            text = node.comment.strip()
            for sep in (".", "—", " - ", ", "):
                idx = text.find(sep)
                if 10 < idx < 80:
                    reasoning = text[:idx].strip()
                    break
            if not reasoning and len(text) <= 80:
                reasoning = text
            elif not reasoning:
                reasoning = text[:80].strip()
            break
    hints.append(reasoning if reasoning else "Read the forcing sequence carefully.")

    # Hint 3: First correct move coordinate as {!xy}
    for node in record.solution_nodes:
        if node.is_correct and node.move:
            hints.append(f"The first move is at {{!{node.move}}}.")
            break
    else:
        # No correct move found — omit this hint
        pass

    return hints


def _build_user_prompt(record: RawExtract) -> str:
    """Build the user prompt from puzzle context.

    EVAL HONESTY: we deliberately do NOT include `record.root_comment` here.
    The root comment often paraphrases the answer; including it leaks the
    label into the prompt and inflates val/test scores. The model sees only
    board + side-to-move + setup stones + level + tags. It must generate the
    teaching commentary from the position alone.
    """
    lines = [
        f"Board: {record.board_size}x{record.board_size}",
        f"{record.player_to_move} to play",
    ]
    if record.setup_black:
        lines.append(f"Black stones: {', '.join(record.setup_black[:20])}")
    if record.setup_white:
        lines.append(f"White stones: {', '.join(record.setup_white[:20])}")
    if record.level:
        lines.append(f"Level: {record.level}")
    if record.tags:
        lines.append(f"Tags: {', '.join(record.tags)}")
    return "\n".join(lines)


def _build_assistant_response(record: RawExtract) -> str:
    """Build the assistant response from existing comments.

    Maps freeform SGF comments into a validated TeachingOutput JSON structure.
    Picks the LONGEST teaching comment on the correct path (not just the first)
    so deep teaching nodes aren't lost when the first correct node is just a marker.
    """
    correct_candidates: list[str] = []
    wrong_comments: dict[str, str] = {}
    summary = record.root_comment if not _is_marker_only(record.root_comment) else ""

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

    correct_comment = max(correct_candidates, key=len) if correct_candidates else ""

    hints = _extract_hints(record)

    output = TeachingOutput(
        teaching_comments=TeachingComments(
            correct_comment=correct_comment,
            wrong_comments=wrong_comments,
            summary=summary[:200] if summary else "",
        ),
        hints=hints,
    )
    return output.model_dump_json()


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
    raw_path = Path(input_path) if input_path else RAW_JSONL
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
        assistant_json = _build_assistant_response(record)
        try:
            payload = json.loads(assistant_json)
            tc = payload.get("teaching_comments", {})
            cc_len = len((tc.get("correct_comment") or "").strip())
            wc = tc.get("wrong_comments") or {}
            max_wc_len = max((len(v.strip()) for v in wc.values()), default=0)
        except (ValueError, AttributeError):
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
                ChatMessage(role="assistant", content=assistant_json),
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

    # Stratified splits per tier (so val/test contain proportional gold/silver/bronze)
    random.seed(42)
    split_buckets: dict[str, list[TrainingExample]] = {"train": [], "val": [], "test": []}
    by_tier: dict[str, list[TrainingExample]] = {}
    for ex in examples:
        by_tier.setdefault(ex.metadata.tier, []).append(ex)
    for tier, group in by_tier.items():
        random.shuffle(group)
        n = len(group)
        n_train = int(n * SPLIT_RATIOS["train"])
        n_val = int(n * SPLIT_RATIOS["val"])
        for i, ex in enumerate(group):
            if i < n_train:
                ex.metadata.split = "train"
            elif i < n_train + n_val:
                ex.metadata.split = "val"
            else:
                ex.metadata.split = "test"
            split_buckets[ex.metadata.split].append(ex)

    REFINED_DIR.mkdir(parents=True, exist_ok=True)
    split_files = {
        "train": TRAIN_JSONL,
        "val": VAL_JSONL,
        "test": TEST_JSONL,
    }

    # Write outputs. Train split applies tier-weight upsampling (integer multiplier);
    # val/test are written 1x for clean evaluation. sft.jsonl mirrors train + val + test.
    with out_path.open("w", encoding="utf-8-sig") as f_all, \
         SFT_METADATA_JSONL.open("w", encoding="utf-8-sig") as f_meta:
        writers = {split: path.open("w", encoding="utf-8-sig") for split, path in split_files.items()}
        try:
            written_per_split: dict[str, int] = {"train": 0, "val": 0, "test": 0}
            written_per_tier: dict[str, int] = {}
            for split_name, group in split_buckets.items():
                for ex in group:
                    messages_only = {"messages": [m.model_dump() for m in ex.messages]}
                    line = json.dumps(messages_only, ensure_ascii=False) + "\n"
                    meta_line = json.dumps(ex.metadata.model_dump(), ensure_ascii=False) + "\n"
                    multiplier = int(round(ex.metadata.sample_weight)) if split_name == "train" else 1
                    if multiplier <= 0:
                        continue  # bronze with weight 0 is dropped from train
                    for _ in range(multiplier):
                        writers[split_name].write(line)
                        f_all.write(line)
                        f_meta.write(meta_line)
                        written_per_split[split_name] += 1
                        written_per_tier[ex.metadata.tier] = written_per_tier.get(ex.metadata.tier, 0) + 1
        finally:
            for w in writers.values():
                w.close()

    logger.info("Refine complete: %d unique → %d emitted (with upsampling)",
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
        print(f"Total rows emitted (upsampled): {sum(written_per_split.values())}")
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
