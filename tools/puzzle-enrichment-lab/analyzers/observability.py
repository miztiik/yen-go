"""AI-Solve observability — batch summary and disagreement sinks (DD-11).

Sprint 4 implementation:
- S4-G8: BatchSummaryAccumulator — collects per-puzzle outcomes, emits structured summary
- S4-G9: DisagreementSink — writes JSONL disagreement records
- S4-G10: Collection-level disagreement monitoring with WARNING threshold

This module does NOT import from backend/puzzle_manager/.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

try:
    from models.solve_result import (
        AiCorrectnessLevel,
        BatchSummary,
        DisagreementRecord,
        HumanSolutionConfidence,
    )
except ImportError:
    from ..models.solve_result import (
        BatchSummary,
        DisagreementRecord,
    )

logger = logging.getLogger(__name__)


class DisagreementSink:
    """JSONL disagreement sink for recording AI vs human disagreements (S4-G9).

    Writes one JSONL record per line to a run-specific file.
    Path: {sink_dir}/{run_id}.jsonl

    Usage:
        sink = DisagreementSink(sink_dir="/path/to/logs/disagreements", run_id="20260304-abc12345")
        sink.write(record)
        sink.close()
    """

    def __init__(self, sink_dir: str, run_id: str):
        """Initialize the sink.

        Args:
            sink_dir: Directory for disagreement JSONL files.
            run_id: Pipeline run identifier (YYYYMMDD-8charhex).
        """
        self._dir = Path(sink_dir)
        self._run_id = run_id
        self._file = None
        self._count = 0

    def _ensure_open(self) -> None:
        """Lazily open the JSONL file on first write."""
        if self._file is not None:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{self._run_id}.jsonl"
        self._file = open(path, "a", encoding="utf-8")
        logger.info("Opened disagreement sink: %s", path)

    def write(self, record: DisagreementRecord) -> None:
        """Write a single disagreement record as JSONL.

        Args:
            record: DisagreementRecord to serialize and append.
        """
        self._ensure_open()
        # Set timestamp if not already set
        if not record.timestamp:
            record.timestamp = datetime.now(UTC).isoformat()
        assert self._file is not None
        self._file.write(record.model_dump_json() + "\n")
        self._file.flush()
        self._count += 1

    def close(self) -> None:
        """Close the JSONL file."""
        if self._file is not None:
            self._file.close()
            logger.info(
                "Closed disagreement sink: %d records written (run_id=%s)",
                self._count, self._run_id,
            )
            self._file = None

    @property
    def records_written(self) -> int:
        """Number of records written so far."""
        return self._count

    def log_goal_agreement(
        self,
        puzzle_id: str,
        inferred_goal: str,
        existing_goal: str,
        agreement: str,
    ) -> None:
        """Log goal agreement diagnostic (T11, C10: diagnostic only, no SGF storage).

        Args:
            puzzle_id: Puzzle identifier.
            inferred_goal: Goal inferred by AI (kill, live, ko, capture, unknown).
            existing_goal: Existing goal from metadata (or empty).
            agreement: 'match', 'mismatch', or 'unknown'.
        """
        if agreement == "mismatch":
            logger.warning(
                "Goal disagreement: puzzle_id=%s inferred=%s existing=%s",
                puzzle_id, inferred_goal, existing_goal,
            )
        else:
            logger.debug(
                "Goal agreement: puzzle_id=%s inferred=%s existing=%s result=%s",
                puzzle_id, inferred_goal, existing_goal, agreement,
            )


class BatchSummaryAccumulator:
    """Accumulates per-puzzle outcomes and emits a BatchSummary (S4-G8).

    Usage:
        acc = BatchSummaryAccumulator(batch_id="run-001")
        for puzzle in puzzles:
            acc.record_puzzle(...)
        summary = acc.emit()
    """

    def __init__(self, batch_id: str, collection: str = ""):
        """Initialize accumulator.

        Args:
            batch_id: Batch identifier (e.g. run_id or collection slug).
            collection: Collection slug for per-collection tracking.
        """
        self._batch_id = batch_id
        self._collection = collection
        self._total = 0
        self._position_only = 0
        self._has_solution = 0
        self._ac_counts = {0: 0, 1: 0, 2: 0}
        self._disagreements = 0
        self._total_queries = 0
        self._co_correct_count = 0
        self._truncated_trees = 0
        self._errors = 0
        self._correct_move_ranks: list[int] = []
        # T7: Entropy and rank aggregates for qk observability
        self._entropy_values: list[float] = []
        self._rank_values: list[int] = []
        # T7: Goal agreement tracking
        self._goal_agreement_matches: int = 0
        self._goal_agreement_mismatches: int = 0
        self._goal_agreement_unknown: int = 0
        # PI-1/PI-3: Refutation quality Phase A counters
        self._ownership_delta_used = 0
        self._score_delta_rescues = 0
        # PI-10: Opponent-response observability
        self._opponent_response_emitted = 0
        # MH-7: Per-puzzle query tracking for compute monitoring
        self._max_queries_per_puzzle = 0
        # S4-G10: Per-collection counters
        self._collection_counters: dict[str, dict[str, int]] = {}
        # G10: Per-puzzle diagnostic aggregates
        self._diagnostic_count: int = 0
        self._diagnostic_error_count: int = 0
        self._diagnostic_qk_scores: list[int] = []
        self._diagnostic_ac_levels: list[int] = []
        # P2b: Frame imbalance tracking
        self._frame_imbalance_count: int = 0
        self._frame_imbalance_by_tag: dict[str, int] = {}
        self._tree_validation_overrides: int = 0

    def record_puzzle(
        self,
        *,
        has_solution: bool,
        ac_level: int = 0,
        disagreement: bool = False,
        queries_used: int = 0,
        co_correct: bool = False,
        truncated: bool = False,
        error: bool = False,
        collection: str = "",
        correct_move_rank: int = 0,
        ownership_delta_used: bool = False,
        score_delta_rescues: int = 0,
        opponent_response_emitted: bool = False,
        policy_entropy: float | None = None,
        goal_agreement: str | None = None,
        frame_imbalance: bool = False,
        tree_validation_override: bool = False,
        frame_imbalance_tags: list[str] | None = None,
    ) -> None:
        """Record outcome for a single puzzle.

        Args:
            has_solution: True if puzzle had existing solution.
            ac_level: AI Correctness level (0-3).
            disagreement: True if AI disagrees with human solution.
            queries_used: Engine queries consumed.
            co_correct: True if co-correct was detected.
            truncated: True if solution tree was truncated.
            error: True if processing errored.
            collection: Collection slug for per-collection tracking.
            correct_move_rank: Correct move's rank in KataGo candidate list.
            ownership_delta_used: PI-1: True if ownership delta reranked candidates.
            score_delta_rescues: PI-3: Number of candidates rescued by score delta.
            opponent_response_emitted: PI-10: True if opponent-response was appended.
            policy_entropy: T7: Policy entropy value for this puzzle (None if unavailable).
            goal_agreement: T7: 'match', 'mismatch', or None (unknown).
            frame_imbalance: True if frame-vs-unframed winrate delta > 0.5.
            tree_validation_override: True if REJECTED was upgraded to FLAGGED by P1 override.
            frame_imbalance_tags: Tag names for frame-imbalanced puzzles (for per-tag breakdown).
        """
        self._total += 1
        if has_solution:
            self._has_solution += 1
        else:
            self._position_only += 1

        if ac_level in self._ac_counts:
            self._ac_counts[ac_level] += 1

        if disagreement:
            self._disagreements += 1
        if co_correct:
            self._co_correct_count += 1
        if truncated:
            self._truncated_trees += 1
        if error:
            self._errors += 1

        self._total_queries += queries_used
        # MH-7: Track max queries per puzzle for compute monitoring
        if queries_used > self._max_queries_per_puzzle:
            self._max_queries_per_puzzle = queries_used

        # PI-1/PI-3: Refutation quality counters
        if ownership_delta_used:
            self._ownership_delta_used += 1
        self._score_delta_rescues += score_delta_rescues
        # PI-10: Opponent-response counter
        if opponent_response_emitted:
            self._opponent_response_emitted += 1

        # T7: Entropy and rank aggregates
        if policy_entropy is not None and policy_entropy >= 0:
            self._entropy_values.append(policy_entropy)
        if correct_move_rank > 0:
            self._rank_values.append(correct_move_rank)

        # T7: Goal agreement tracking
        if goal_agreement == "match":
            self._goal_agreement_matches += 1
        elif goal_agreement == "mismatch":
            self._goal_agreement_mismatches += 1
        else:
            self._goal_agreement_unknown += 1

        # G-6: Track correct move rank for observability
        if correct_move_rank > 0:
            self._correct_move_ranks.append(correct_move_rank)

        # P2b: Frame imbalance tracking
        if frame_imbalance:
            self._frame_imbalance_count += 1
            if frame_imbalance_tags:
                for tag in frame_imbalance_tags:
                    self._frame_imbalance_by_tag[tag] = (
                        self._frame_imbalance_by_tag.get(tag, 0) + 1
                    )
        if tree_validation_override:
            self._tree_validation_overrides += 1

        # S4-G10: Per-collection tracking
        coll = collection or self._collection
        if coll:
            if coll not in self._collection_counters:
                self._collection_counters[coll] = {
                    "total": 0, "has_solution": 0, "disagreements": 0,
                }
            self._collection_counters[coll]["total"] += 1
            if has_solution:
                self._collection_counters[coll]["has_solution"] += 1
            if disagreement:
                self._collection_counters[coll]["disagreements"] += 1

    def record_diagnostic(self, diagnostic: object) -> None:
        """Record a PuzzleDiagnostic for batch-level aggregation (G10).

        Args:
            diagnostic: PuzzleDiagnostic instance (duck-typed to avoid import).
        """
        self._diagnostic_count += 1
        if getattr(diagnostic, "errors", None):
            self._diagnostic_error_count += 1
        qk = getattr(diagnostic, "qk_score", 0)
        self._diagnostic_qk_scores.append(qk)
        ac = getattr(diagnostic, "ac_level", 0)
        self._diagnostic_ac_levels.append(ac)

        ga = getattr(diagnostic, "goal_agreement", "unknown")
        if ga == "match":
            self._goal_agreement_matches += 1
        elif ga == "mismatch":
            self._goal_agreement_mismatches += 1

    @property
    def diagnostic_count(self) -> int:
        """Number of diagnostics recorded."""
        return self._diagnostic_count

    @property
    def diagnostic_error_count(self) -> int:
        """Number of diagnostics with errors."""
        return self._diagnostic_error_count

    @property
    def diagnostic_qk_scores(self) -> list[int]:
        """All qk_score values recorded."""
        return list(self._diagnostic_qk_scores)

    def emit(self, *, warning_threshold: float = 0.20) -> BatchSummary:
        """Build and emit the BatchSummary, logging at INFO level.

        Also checks per-collection disagreement rates and emits WARNING
        for collections exceeding the threshold (S4-G10).

        Args:
            warning_threshold: Disagreement rate threshold for WARNING.

        Returns:
            Populated BatchSummary.
        """
        disagreement_rate = (
            self._disagreements / self._has_solution
            if self._has_solution > 0
            else 0.0
        )

        summary = BatchSummary(
            batch_id=self._batch_id,
            total_puzzles=self._total,
            position_only=self._position_only,
            has_solution=self._has_solution,
            ac_0_count=self._ac_counts[0],
            ac_1_count=self._ac_counts[1],
            ac_2_count=self._ac_counts[2],
            disagreements=self._disagreements,
            total_queries=self._total_queries,
            co_correct_count=self._co_correct_count,
            truncated_trees=self._truncated_trees,
            errors=self._errors,
            collection=self._collection,
            disagreement_rate=disagreement_rate,
            correct_move_ranks=list(self._correct_move_ranks),
            ownership_delta_used=self._ownership_delta_used,
            score_delta_rescues=self._score_delta_rescues,
            opponent_response_emitted=self._opponent_response_emitted,
            max_queries_per_puzzle=self._max_queries_per_puzzle,
            entropy_values=list(self._entropy_values),
            rank_values=list(self._rank_values),
            goal_agreement_matches=self._goal_agreement_matches,
            goal_agreement_mismatches=self._goal_agreement_mismatches,
            goal_agreement_unknown=self._goal_agreement_unknown,
            frame_imbalance_count=self._frame_imbalance_count,
            tree_validation_overrides=self._tree_validation_overrides,
        )

        # Emit at INFO level (DD-11, LOG-1)
        logger.info(
            "BatchSummary: %s",
            summary.model_dump_json(),
        )

        # S4-G10: Per-collection disagreement monitoring
        for coll, counters in self._collection_counters.items():
            coll_has_solution = counters["has_solution"]
            coll_disagreements = counters["disagreements"]
            if coll_has_solution > 0:
                coll_rate = coll_disagreements / coll_has_solution
                if coll_rate > warning_threshold:
                    logger.warning(
                        "Collection '%s' disagreement rate %.1f%% exceeds "
                        "threshold %.1f%% (%d/%d puzzles)",
                        coll,
                        coll_rate * 100,
                        warning_threshold * 100,
                        coll_disagreements,
                        coll_has_solution,
                    )

        # P2b: Frame imbalance batch warning
        if self._total > 0 and self._frame_imbalance_count > 0:
            imbalance_rate = self._frame_imbalance_count / self._total
            logger.warning(
                "Frame imbalance: %d/%d puzzles (%.1f%%) had frame-vs-unframed "
                "winrate delta > 0.5",
                self._frame_imbalance_count,
                self._total,
                imbalance_rate * 100,
            )
            if self._frame_imbalance_by_tag:
                top_tags = sorted(
                    self._frame_imbalance_by_tag.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                logger.warning(
                    "Frame imbalance by tag (top 5): %s",
                    ", ".join(f"{tag}={count}" for tag, count in top_tags),
                )

        return summary
