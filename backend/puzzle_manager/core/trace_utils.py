"""
Trace ID generation and pipeline metadata utilities.

This module provides functions for generating unique trace IDs that follow
each SGF file through the pipeline stages (ingest → analyze → publish),
and for serializing/parsing the YM pipeline metadata property.
"""

import json
import logging
import uuid
from dataclasses import dataclass

from backend.puzzle_manager.core.sgf_utils import unescape_sgf_value

logger = logging.getLogger("puzzle_manager.trace_utils")


def generate_trace_id() -> str:
    """
    Generate a unique 16-character hex trace ID.

    Uses UUID4 (random) and takes the first 16 characters of the hex
    representation. This provides:
    - Collision-proof uniqueness (2^64 possibilities)
    - Compact representation (16 chars vs 36 for full UUID)
    - Consistent format with run_id and puzzle_id

    Returns:
        16-character lowercase hex string (e.g., "a1b2c3d4e5f67890")

    Example:
        >>> trace_id = generate_trace_id()
        >>> len(trace_id)
        16
        >>> int(trace_id, 16)  # Valid hex
        ...
    """
    return uuid.uuid4().hex[:16]


def build_pipeline_meta(
    trace_id: str,
    original_filename: str = "",
    run_id: str = "",
    *,
    content_type: int | None = None,
    trivial_capture: bool = False,
) -> str:
    """Build a JSON string for the YM SGF property (v13+).

    Source adapter ID is tracked via context.source_id and publish log,
    not embedded in YM (removed in schema v13 cleanup).

    Args:
        trace_id: 16-char hex trace ID.
        original_filename: Optional original filename from source adapter.
        run_id: Pipeline run ID (e.g., "20260220-abc12345").
        content_type: Content-type classification (1=curated, 2=practice, 3=training).
        trivial_capture: Whether the puzzle is a trivial capture.

    Returns:
        JSON string, e.g. '{"t":"a1b2...","i":"20260220-abc12345"}'.
    """
    meta: dict[str, str | int | bool] = {"t": trace_id}
    if original_filename:
        meta["f"] = original_filename
    if run_id:
        meta["i"] = run_id
    if content_type is not None:
        meta["ct"] = content_type
    if trivial_capture:
        meta["tc"] = True
    return json.dumps(meta, separators=(",", ":"))


def parse_pipeline_meta(ym_value: str | None) -> tuple[str, str, str, str]:
    """Parse the YM property value (v13).

    Defensive parsing — never raises. Returns ("", "", "", "") on any failure.

    Note: The 3rd element (source) is always empty string for new SGFs.
    Retained in the return signature for backward compatibility with
    callers that destructure the 4-tuple. Old SGFs with "s" in YM
    will still have the value parsed and returned.

    Args:
        ym_value: Raw YM property string from SGF, or None if absent.

    Returns:
        Tuple of (trace_id, original_filename, source, run_id). Any may be empty string.
    """
    if not ym_value:
        return ("", "", "", "")
    try:
        # Unescape SGF escaping before JSON parsing (SGF escapes ] and \ chars)
        unescaped = unescape_sgf_value(ym_value)
        data = json.loads(unescaped)
        if not isinstance(data, dict):
            logger.warning(f"YM value is not a JSON object: {ym_value!r}")
            return ("", "", "", "")
        return (data.get("t", ""), data.get("f", ""), data.get("s", ""), data.get("i", ""))
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse YM value: {ym_value!r}: {e}")
        return ("", "", "", "")


@dataclass(frozen=True, slots=True)
class PipelineMeta:
    """Parsed pipeline metadata from YM property.

    Extended structure supporting content-type classification
    and trivial capture flags.
    """

    trace_id: str = ""
    original_filename: str = ""
    source: str = ""  # Legacy; always empty for new SGFs
    run_id: str = ""
    content_type: int | None = None  # 1=curated, 2=practice, 3=training
    trivial_capture: bool = False  # True if trivial capture puzzle


def parse_pipeline_meta_extended(ym_value: str | None) -> PipelineMeta:
    """Parse the YM property value into structured PipelineMeta.

    Supports all v13+ fields including content-type and trivial capture.
    Defensive — never raises.

    Args:
        ym_value: Raw YM property string from SGF, or None if absent.

    Returns:
        PipelineMeta with all parsed fields.
    """
    if not ym_value:
        return PipelineMeta()
    try:
        unescaped = unescape_sgf_value(ym_value)
        data = json.loads(unescaped)
        if not isinstance(data, dict):
            logger.warning(f"YM value is not a JSON object: {ym_value!r}")
            return PipelineMeta()
        ct_raw = data.get("ct")
        ct = int(ct_raw) if ct_raw is not None else None
        return PipelineMeta(
            trace_id=data.get("t", ""),
            original_filename=data.get("f", ""),
            source=data.get("s", ""),
            run_id=data.get("i", ""),
            content_type=ct,
            trivial_capture=bool(data.get("tc", False)),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"Failed to parse YM value: {ym_value!r}: {e}")
        return PipelineMeta()
