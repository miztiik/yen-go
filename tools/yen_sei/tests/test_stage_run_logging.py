from __future__ import annotations

import json
import logging
from pathlib import Path

from tools.yen_sei.telemetry import logger as logger_module


def _json_lines(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def test_configure_stage_file_logging_writes_timestamped_and_latest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(logger_module, "DATA_DIR", tmp_path)

    test_logger = logging.getLogger("tools.yen_sei.tests.stage_run_logging.write")
    test_logger.handlers.clear()
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)

    stamped, latest, deleted = logger_module.configure_stage_file_logging(
        "harvest",
        logger=test_logger,
        keep=3,
        stamp="20260419T1200",
    )

    assert stamped == tmp_path / "20260419120000_harvest_run.log"
    assert latest == tmp_path / "20260419120000_harvest_run_latest.log"
    assert deleted == []

    logger_module.set_context(stage="harvest")
    test_logger.info("Harvesting 2 SGF files from tools/yen_sei/data/sources")
    for handler in test_logger.handlers:
        handler.flush()

    stamped_rows = _json_lines(stamped)
    latest_rows = _json_lines(latest)
    assert stamped_rows
    assert stamped_rows[-1]["stage"] == "harvest"
    assert stamped_rows[-1]["msg"].endswith("tools/yen_sei/data/sources")
    assert latest_rows[-1]["msg"] == stamped_rows[-1]["msg"]


def test_configure_stage_file_logging_prunes_old_timestamped_logs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(logger_module, "DATA_DIR", tmp_path)

    for ts in ("20260418100000", "20260418110000", "20260418120000"):
        (tmp_path / f"{ts}_ingest_run.log").write_text("old\n", encoding="utf-8")
        (tmp_path / f"{ts}_ingest_run_latest.log").write_text("old\n", encoding="utf-8")

    test_logger = logging.getLogger("tools.yen_sei.tests.stage_run_logging.prune")
    test_logger.handlers.clear()
    test_logger.propagate = False
    test_logger.setLevel(logging.INFO)

    stamped, latest, deleted = logger_module.configure_stage_file_logging(
        "ingest",
        logger=test_logger,
        keep=2,
        stamp="20260419T1200",
    )

    assert stamped.exists()
    assert latest.exists()
    assert len(deleted) == 4

    remaining_runs = sorted(p.name for p in tmp_path.glob("*_ingest_run.log"))
    assert remaining_runs == ["20260418120000_ingest_run.log", "20260419120000_ingest_run.log"]

    remaining_latest = sorted(p.name for p in tmp_path.glob("*_ingest_run_latest.log"))
    assert remaining_latest == [
        "20260418120000_ingest_run_latest.log",
        "20260419120000_ingest_run_latest.log",
    ]
