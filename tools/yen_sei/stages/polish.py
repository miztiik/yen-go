"""Polish stage (P0-3): LLM-assisted English cleanup of broken comments.

Operates on ``raw.jsonl`` (output of harvest), emits ``raw_polished.jsonl``
(input to refine) with per-node ``comment_polished`` and
``comment_polish_status`` fields. Refine prefers the polished comment
when present and falls back to the original otherwise.

Three filter stages, cost-ascending:

- **Stage A — Deterministic regex normalization** (free).
  Reuses ``governance.text_normalizer.normalize_section_body``. If the
  body is already clean after stage A, status = ``clean_after_regex``
  and stage C is skipped.
- **Stage B — Language-quality scoring** (free).
  Counts CN→EN markers, English-word ratio, repeated-token runs. If
  the comment scores **above** the broken threshold, it is flagged for
  stage C. Otherwise status = ``clean_native``.
- **Stage C — LLM rewrite of flagged comments only** (paid, opt-in via
  ``--llm``). The LLM sees the comment + tags + technique + role
  (``correct`` / ``wrong`` / ``root``) but **never the board ASCII** —
  this is deliberate: full board context invites the LLM to invent
  technical claims. Hallucination guards reject outputs that grow >3×,
  contain coordinate regex, or contain ordinal-move references.

Default behaviour (no ``--llm`` flag) is **dry-run**: every comment is
classified into A/B status and a histogram is printed; no LLM is called
and no file is written. This lets us see what would be flagged without
spending tokens.

Cache: per-comment SHA256 of ``original + system_prompt_version`` keys
into ``data/raw/polish_cache/{hash}.json``. Re-runs are free unless the
prompt version bumps.

See also:
- [IMPROVEMENT_PLAN.md §3](../IMPROVEMENT_PLAN.md) — full design.
- ``tools/yen_sei/governance/text_normalizer.py`` — Stage A regexes.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from tools.yen_sei.config import (
    POLISH_CACHE_DIR,
    RAW_JSONL,
    RAW_POLISHED_JSONL,
)
from tools.yen_sei.governance.text_normalizer import (
    broken_english_score,
    contains_vietnamese,
    has_coordinate_leak,
    normalize_section_body,
)
from tools.yen_sei.models.raw_extract import RawExtract
from tools.yen_sei.telemetry.logger import set_context, setup_logger

logger = setup_logger(__name__)


# ── Versioning ──────────────────────────────────────────────────────────
# Bump when the LLM rewrite prompt changes — invalidates the cache.
POLISH_PROMPT_VERSION = "v1"

# ── Stage B thresholds ──────────────────────────────────────────────────
BROKEN_EN_THRESHOLD = 1            # >= this many MT markers → flag for stage C
ENGLISH_WORD_RATIO_THRESHOLD = 0.55 # below this → flag for stage C
MIN_LENGTH_FOR_LLM = 30            # below this, rewrite isn't worth a token

# ── Stage C hallucination guards ────────────────────────────────────────
LLM_MAX_GROWTH_RATIO = 3.0         # polished > 3x original → reject
LLM_MIN_LEN = 4                     # polished < 4 chars → treat as skip
SKIP_TOKEN = "__SKIP__"             # LLM signal "uninterpretable"

# Reuses the audit's coordinate detector (same regexes that drove
# the 44.7% → 0.1% drop on day 1).
_COORD_REJECT = has_coordinate_leak

# Cheap "is it English?" word list. Tiny on purpose — just the most
# common 1-3-letter function words. We don't need a full dictionary
# because we're discriminating between "broken MT" and "any reasonable
# English at all", not between English and a foreign language.
_COMMON_EN_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in",
    "on", "at", "by", "for", "with", "from", "this", "that", "these",
    "those", "is", "are", "was", "were", "be", "been", "has", "have",
    "had", "do", "does", "did", "can", "could", "will", "would", "should",
    "may", "might", "must", "not", "no", "yes", "as", "so", "such", "all",
    "any", "some", "more", "most", "less", "few", "two", "one", "three",
    "black", "white", "stone", "stones", "move", "moves", "play", "plays",
    "after", "before", "now", "here", "there", "then", "when", "while",
    "because", "since", "however", "instead", "only", "also", "even",
})

_TOKEN_RE = re.compile(r"[a-zA-Z]+")


def english_word_ratio(text: str) -> float:
    """Fraction of alphabetic tokens that are common English words.

    Returns 1.0 for empty input (treated as "no signal").
    """
    if not text:
        return 1.0
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return 1.0
    matches = sum(1 for t in tokens if t in _COMMON_EN_WORDS)
    return matches / len(tokens)


# ── Status enum (string-valued so it survives JSON round-trip) ─────────
STATUS_CLEAN_NATIVE = "clean_native"             # passed B, no rewrite needed
STATUS_CLEAN_AFTER_REGEX = "clean_after_regex"   # A fixed it; B passed
STATUS_FLAGGED_NEEDS_LLM = "flagged_needs_llm"   # would call C; dry-run only
STATUS_REWRITTEN = "rewritten"                    # C succeeded
STATUS_KEPT_ORIGINAL = "kept_original"            # C ran, output rejected → keep original
STATUS_REJECTED_TOO_LONG = "rejected_too_long"
STATUS_REJECTED_COORDS = "rejected_coords"
STATUS_SKIPPED_UNINTERPRETABLE = "skipped_uninterpretable"
STATUS_TOO_SHORT_FOR_LLM = "too_short_for_llm"   # below MIN_LENGTH_FOR_LLM
STATUS_EMPTY = "empty"


@dataclass
class CommentClassification:
    """Stage A+B verdict for one comment."""

    status: str
    cleaned: str            # text after stage A (may equal original if no changes)
    needs_llm: bool
    cn_marker_hits: int
    en_word_ratio: float

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "cleaned": self.cleaned,
            "needs_llm": self.needs_llm,
            "cn_marker_hits": self.cn_marker_hits,
            "en_word_ratio": round(self.en_word_ratio, 3),
        }


def classify(comment: str) -> CommentClassification:
    """Run Stage A + Stage B on one comment. Pure function.

    Args:
        comment: Raw SGF comment text.

    Returns:
        Verdict with status, regex-normalized text, and the signals
        that drove the decision.
    """
    if not comment or not comment.strip():
        return CommentClassification(
            status=STATUS_EMPTY,
            cleaned="",
            needs_llm=False,
            cn_marker_hits=0,
            en_word_ratio=1.0,
        )

    # Vietnamese-translated SGFs leak in from a handful of mixed-language
    # sources. We can't reliably round-trip them to English without
    # losing meaning, so drop them up-front rather than spending tokens.
    if contains_vietnamese(comment):
        return CommentClassification(
            status=STATUS_SKIPPED_UNINTERPRETABLE,
            cleaned="",
            needs_llm=False,
            cn_marker_hits=broken_english_score(comment),
            en_word_ratio=english_word_ratio(comment),
        )

    cleaned = normalize_section_body(comment)
    if not cleaned:
        # Stage A reduced it to nothing → inherently uninterpretable
        return CommentClassification(
            status=STATUS_SKIPPED_UNINTERPRETABLE,
            cleaned="",
            needs_llm=False,
            cn_marker_hits=broken_english_score(comment),
            en_word_ratio=english_word_ratio(comment),
        )

    cn_hits = broken_english_score(cleaned)
    ratio = english_word_ratio(cleaned)

    if cn_hits >= BROKEN_EN_THRESHOLD or ratio < ENGLISH_WORD_RATIO_THRESHOLD:
        if len(cleaned) < MIN_LENGTH_FOR_LLM:
            # Too short to be worth an LLM call — keep the regex output as-is.
            return CommentClassification(
                status=STATUS_TOO_SHORT_FOR_LLM,
                cleaned=cleaned,
                needs_llm=False,
                cn_marker_hits=cn_hits,
                en_word_ratio=ratio,
            )
        return CommentClassification(
            status=STATUS_FLAGGED_NEEDS_LLM,
            cleaned=cleaned,
            needs_llm=True,
            cn_marker_hits=cn_hits,
            en_word_ratio=ratio,
        )

    status = (
        STATUS_CLEAN_AFTER_REGEX
        if cleaned != comment.strip()
        else STATUS_CLEAN_NATIVE
    )
    return CommentClassification(
        status=status,
        cleaned=cleaned,
        needs_llm=False,
        cn_marker_hits=cn_hits,
        en_word_ratio=ratio,
    )


# ── Stage C: LLM rewrite ───────────────────────────────────────────────

POLISH_SYSTEM_PROMPT = """\
You rewrite Go teaching comments into fluent English.

RULES:
1. Preserve ONLY what the original asserts. Do not add new technical claims.
2. Do not output board coordinates (e.g. cd, D17, {!xy}).
3. Do not output ordinal move references (e.g. "Black 1", "White 2").
4. Maximum 2 short sentences. Concrete, no filler.
5. If the original is uninterpretable or contains no teaching content,
   return the literal string __SKIP__ and nothing else.

Return JSON: {"rewritten": "<text>"}
"""


@dataclass
class PolishStats:
    """Aggregated counts across an entire polish run."""

    total_comments: int = 0
    by_status: Counter = field(default_factory=Counter)

    def record(self, status: str) -> None:
        self.total_comments += 1
        self.by_status[status] += 1

    def fmt(self) -> str:
        lines = ["", "=" * 60, "YEN-SEI POLISH STATS", "=" * 60]
        lines.append(f"Total comments processed: {self.total_comments}")
        lines.append("")
        lines.append("By status:")
        # Stable display order
        order = [
            STATUS_CLEAN_NATIVE,
            STATUS_CLEAN_AFTER_REGEX,
            STATUS_FLAGGED_NEEDS_LLM,
            STATUS_REWRITTEN,
            STATUS_KEPT_ORIGINAL,
            STATUS_TOO_SHORT_FOR_LLM,
            STATUS_REJECTED_TOO_LONG,
            STATUS_REJECTED_COORDS,
            STATUS_SKIPPED_UNINTERPRETABLE,
            STATUS_EMPTY,
        ]
        for status in order:
            n = self.by_status.get(status, 0)
            if n:
                pct = 100.0 * n / max(self.total_comments, 1)
                lines.append(f"  {status:<28} {n:>6} ({pct:5.1f}%)")
        return "\n".join(lines)


def _cache_key(original: str) -> str:
    return sha256(
        f"{POLISH_PROMPT_VERSION}|{original}".encode("utf-8")
    ).hexdigest()[:16]


def _cache_load(key: str) -> dict | None:
    path = POLISH_CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _cache_save(key: str, payload: dict) -> None:
    POLISH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (POLISH_CACHE_DIR / f"{key}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )


def _validate_llm_output(original: str, candidate: str) -> tuple[str, str]:
    """Apply hallucination guards to one LLM rewrite.

    Returns (final_text, status). If status indicates rejection, the
    caller should fall back to the original (regex-cleaned) comment.
    """
    candidate = (candidate or "").strip()
    if not candidate or candidate == SKIP_TOKEN:
        return "", STATUS_SKIPPED_UNINTERPRETABLE
    if len(candidate) < LLM_MIN_LEN:
        return original, STATUS_KEPT_ORIGINAL
    if len(candidate) > LLM_MAX_GROWTH_RATIO * max(len(original), 1):
        return original, STATUS_REJECTED_TOO_LONG
    if _COORD_REJECT(candidate):
        return original, STATUS_REJECTED_COORDS
    return candidate, STATUS_REWRITTEN


def _build_polish_user_prompt(
    original: str,
    role: str,
    tags: list[str],
    level: str,
) -> str:
    bits = [f'role: "{role}"']
    if tags:
        bits.append(f'tags: {tags[:5]}')
    if level:
        bits.append(f'level: "{level}"')
    bits.append(f'\noriginal:\n"""\n{original.strip()}\n"""')
    return "\n".join(bits)


# ── Public batch interface (provider-agnostic) ─────────────────────────
# These let any LLM backend (subagents, OpenAI Batch API, local Ollama,
# manual human review) populate the polish cache without coupling to a
# specific HTTP client.
#
# Workflow:
#   1.  `polish dump-batch --output batch.jsonl` writes one JSON line
#       per pending (uncached) flagged comment, each containing the
#       cache_key and the full system+user prompt.
#   2.  Any backend processes those prompts and writes a response JSONL
#       with `{cache_key, rewritten}` per line.
#   3.  `polish load-batch --input batch_responses.jsonl` writes those
#       responses into the cache directory.
#   4.  `polish --llm` then runs against the populated cache with zero
#       network calls.


class NullLLMClient:
    """Stand-in client that refuses to make network calls.

    Used with ``--cache-only``: when every row should already be cached
    (e.g. after ``polish-load-batch`` ingested subagent responses), we
    want a cache miss to fail loudly rather than silently fall through
    to an unconfigured paid backend.
    """

    def generate(self, system_prompt: str, user_prompt: str) -> dict:  # noqa: D401
        raise RuntimeError(
            "NullLLMClient.generate called: a cache miss occurred in "
            "cache-only mode. Dump pending requests with polish-dump-batch "
            "and populate the cache via polish-load-batch before retrying."
        )


def dump_batch(
    *,
    input_path: Path | None = None,
    output_path: Path,
    limit: int | None = None,
    skip_cached: bool = True,
) -> int:
    """Dump pending Stage-C rewrite requests to a JSONL file.

    Each line is::

        {"cache_key": "...", "system": "...", "user": "...", "original": "..."}

    Args:
        input_path: Source raw JSONL. Default = ``RAW_JSONL``.
        output_path: Destination batch JSONL.
        limit: Process at most N source records.
        skip_cached: If True (default), omit requests whose cache file
            already exists — so re-running ``dump-batch`` only emits
            the still-pending work.

    Returns:
        Number of requests written.
    """
    in_path = input_path or RAW_JSONL
    if not in_path.exists():
        raise FileNotFoundError(f"Input not found: {in_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen_keys: set[str] = set()
    written = 0

    with in_path.open("r", encoding="utf-8") as src, \
         output_path.open("w", encoding="utf-8") as dst:
        n_in = 0
        for line in src:
            line = line.strip()
            if not line:
                continue
            if limit is not None and n_in >= limit:
                break
            n_in += 1
            try:
                rec = RawExtract.model_validate_json(line)
            except Exception:  # noqa: BLE001
                continue

            for role_text, role in _iter_polishable(rec):
                cls = classify(role_text)
                if not cls.needs_llm:
                    continue
                key = _cache_key(cls.cleaned)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                if skip_cached and (POLISH_CACHE_DIR / f"{key}.json").exists():
                    continue
                payload = {
                    "cache_key": key,
                    "system": POLISH_SYSTEM_PROMPT,
                    "user": _build_polish_user_prompt(
                        cls.cleaned, role, rec.tags, rec.level
                    ),
                    "original": cls.cleaned,
                }
                dst.write(json.dumps(payload, ensure_ascii=False) + "\n")
                written += 1

    return written


def load_batch(*, input_path: Path) -> tuple[int, int]:
    """Load batch rewrite responses into the polish cache.

    Each line in ``input_path`` must be a JSON object with at least
    ``cache_key`` and ``rewritten``. Lines missing required fields or
    with empty ``rewritten`` are counted as skipped.

    Args:
        input_path: Path to the responses JSONL.

    Returns:
        Tuple of (loaded, skipped).
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    loaded = 0
    skipped = 0
    POLISH_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue
            key = obj.get("cache_key")
            rewritten = obj.get("rewritten", "")
            if not key or not isinstance(rewritten, str):
                skipped += 1
                continue
            _cache_save(key, {"rewritten": rewritten})
            loaded += 1
    return loaded, skipped


def _iter_polishable(rec: RawExtract):
    """Yield (text, role) pairs for every polishable field on a record."""
    if rec.root_comment:
        yield rec.root_comment, "root"
    for node in rec.solution_nodes:
        if node.comment:
            role = "correct" if node.is_correct else "wrong"
            yield node.comment, role


# ── Public entry: classify-only OR classify-and-rewrite ────────────────


def run_polish(
    *,
    input_path: str | None = None,
    output_path: str | None = None,
    use_llm: bool = False,
    sample: int | None = None,
    limit: int | None = None,
    llm_client=None,
) -> int:
    """Run the polish stage.

    Args:
        input_path: Path to ``raw.jsonl``. Default = config.RAW_JSONL.
        output_path: Path to ``raw_polished.jsonl``. Default =
            config.RAW_POLISHED_JSONL.
        use_llm: If False (default), Stage C is skipped — comments that
            would be sent to the LLM are tagged ``flagged_needs_llm``
            but not rewritten. If True, ``llm_client`` must be provided.
        sample: If set, print N before/after pairs of *flagged* comments
            to stdout (manual prompt-tuning aid). Implies dry-run.
        limit: If set, process at most N records (smoke testing).
        llm_client: Object with ``.generate(system_prompt, user_prompt)
            -> dict`` returning ``{"rewritten": "<text>"}``. Required
            if ``use_llm=True``. See ``tools/oshie/agent/llm_client``.

    Returns:
        Exit code (0 = OK).
    """
    set_context(stage="polish")
    in_path = Path(input_path) if input_path else RAW_JSONL
    out_path = Path(output_path) if output_path else RAW_POLISHED_JSONL

    if not in_path.exists():
        logger.error("Input not found: %s. Run harvest first.", in_path)
        return 1

    if use_llm and llm_client is None:
        logger.error("--llm requires an llm_client. Aborting.")
        return 1

    stats = PolishStats()
    sampled: list[tuple[str, str, CommentClassification]] = []
    sample_target = sample if sample else 0
    dry_run = bool(sample) or not use_llm

    out_records: list[RawExtract] = []
    n_in = 0
    with in_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if limit is not None and n_in >= limit:
                break
            n_in += 1
            try:
                rec = RawExtract.model_validate_json(line)
            except Exception as e:  # noqa: BLE001 - log and skip
                logger.warning("Skipping unparseable record: %s", e)
                continue

            new_rec = rec.model_copy(deep=True)
            extras: dict[str, dict] = {}

            # --- root ---
            cls = classify(rec.root_comment)
            stats.record(cls.status)
            polished_root, root_status = _maybe_rewrite(
                cls,
                rec.root_comment,
                role="root",
                tags=rec.tags,
                level=rec.level,
                use_llm=use_llm,
                llm_client=llm_client,
                stats=stats,
            )
            if polished_root != rec.root_comment:
                # Mutate in place — refine reads root_comment directly.
                new_rec.root_comment = polished_root
            extras["root_polish"] = {
                "original": rec.root_comment,
                "status": root_status,
                "cls": cls.to_dict(),
            }
            if cls.needs_llm and len(sampled) < sample_target:
                sampled.append(("root", rec.file_path, cls))

            # --- nodes ---
            node_meta: list[dict] = []
            for i, node in enumerate(rec.solution_nodes):
                cls_n = classify(node.comment)
                stats.record(cls_n.status)
                role = "correct" if node.is_correct else "wrong"
                polished, status = _maybe_rewrite(
                    cls_n,
                    node.comment,
                    role=role,
                    tags=rec.tags,
                    level=rec.level,
                    use_llm=use_llm,
                    llm_client=llm_client,
                    stats=stats,
                )
                if polished != node.comment:
                    new_rec.solution_nodes[i].comment = polished
                node_meta.append({"status": status, "cls": cls_n.to_dict()})
                if cls_n.needs_llm and len(sampled) < sample_target:
                    sampled.append((f"node[{i}]:{role}", rec.file_path, cls_n))
            extras["node_polish"] = node_meta

            out_records.append(new_rec)

    print(stats.fmt())

    if sampled:
        print("\n" + "=" * 60)
        print(f"FLAGGED-FOR-LLM SAMPLES ({len(sampled)})")
        print("=" * 60)
        for role, fp, cls in sampled:
            print(f"\n[{role}] {fp}  cn_hits={cls.cn_marker_hits} en_ratio={cls.en_word_ratio:.2f}")
            print(f"  ORIGINAL (post-regex): {cls.cleaned[:240]}")

    if dry_run:
        logger.info("Dry-run complete (sample=%s, use_llm=%s). No file written.",
                    sample, use_llm)
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in out_records:
            f.write(rec.model_dump_json() + "\n")
    logger.info("Wrote %d polished records to %s", len(out_records), out_path)
    return 0


def _maybe_rewrite(
    cls: CommentClassification,
    original: str,
    *,
    role: str,
    tags: list[str],
    level: str,
    use_llm: bool,
    llm_client,
    stats: PolishStats,
) -> tuple[str, str]:
    """Apply Stage C (LLM rewrite) when needed and use_llm is True.

    Returns (final_text, final_status). Updates stats with stage-C
    outcomes.
    """
    if not cls.needs_llm:
        return cls.cleaned or original, cls.status
    if not use_llm:
        return cls.cleaned or original, STATUS_FLAGGED_NEEDS_LLM

    # Cache lookup keyed on (prompt_version, original).
    key = _cache_key(cls.cleaned)
    cached = _cache_load(key)
    if cached is not None:
        candidate = cached.get("rewritten", "")
    else:
        try:
            payload = llm_client.generate(
                POLISH_SYSTEM_PROMPT,
                _build_polish_user_prompt(cls.cleaned, role, tags, level),
            )
            candidate = (payload or {}).get("rewritten", "")
            _cache_save(key, {"rewritten": candidate})
        except Exception as e:  # noqa: BLE001 - cache + log + fall back
            logger.warning("LLM call failed; keeping regex output: %s", e)
            return cls.cleaned, STATUS_KEPT_ORIGINAL

    final, final_status = _validate_llm_output(cls.cleaned, candidate)
    stats.record(final_status)
    if final_status == STATUS_REWRITTEN:
        return final, final_status
    if final_status == STATUS_SKIPPED_UNINTERPRETABLE:
        return "", final_status
    # Reject paths fall back to the regex-cleaned text.
    return cls.cleaned, final_status
