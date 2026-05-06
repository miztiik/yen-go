"""Tests for 101weiqi browser-capture receiver module."""

import json
import logging
import threading
import urllib.request
from pathlib import Path

import pytest

from tools.weiqi101.checkpoint import WeiQiCheckpoint
from tools.weiqi101.receiver import (
    PuzzleQueue,
    Telemetry,
    _ReceiverState,
    _make_handler,
    import_jsonl,
    process_qqdata,
)


def _sample_qqdata(puzzle_id: int = 78000) -> dict:
    """Return a minimal valid qqdata dict."""
    return {
        "publicid": puzzle_id,
        "boardsize": 19,
        "firsthand": 1,             # Black to play
        "levelname": "13K+",
        "qtypename": "死活题",
        "qtype": 1,
        "prepos": [
            ["pd", "pe", "qd"],      # Black stones
            ["oc", "oe", "rc"],      # White stones
        ],
        "andata": {
            "0": {"pt": "rd", "o": 1, "subs": [1, 2]},
            "1": {"pt": "pe", "f": 1, "subs": []},
            "2": {"pt": "qe", "o": 1, "subs": []},
        },
        "taskresult": {"ok_total": 1000, "fail_total": 500},
        "vote": 4.5,
    }


# ---------------------------------------------------------------------------
# process_qqdata tests
# ---------------------------------------------------------------------------


class TestProcessQqdata:
    """Tests for the core process_qqdata pipeline function."""

    def test_valid_puzzle_saves_sgf(self, tmp_path: Path):
        """Valid qqdata produces an SGF file."""
        known_ids: set[int] = set()
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        result = process_qqdata(
            qqdata=_sample_qqdata(),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
            match_collections=False,
            resolve_intent=False,
        )

        assert result["status"] == "ok"
        assert result["puzzle_id"] == 78000
        # SGF file should exist
        sgf_path = Path(result["message"])
        assert sgf_path.exists()
        content = sgf_path.read_text(encoding="utf-8")
        assert "(;FF[4]" in content
        assert "GM[1]" in content

    def test_duplicate_skipped(self, tmp_path: Path):
        """Second submission of the same puzzle_id is skipped."""
        known_ids: set[int] = {78000}
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        result = process_qqdata(
            qqdata=_sample_qqdata(),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
        )

        assert result["status"] == "skipped"
        assert result["puzzle_id"] == 78000
        assert "duplicate" in result["message"]

    def test_invalid_puzzle_returns_error(self, tmp_path: Path):
        """Invalid qqdata (e.g., no stones) returns error status."""
        bad = _sample_qqdata()
        bad["prepos"] = [[], []]  # No setup stones

        result = process_qqdata(
            qqdata=bad,
            output_dir=tmp_path,
            known_ids=set(),
            checkpoint=WeiQiCheckpoint(source_mode="browser-capture"),
        )

        assert result["status"] == "error"
        assert "validation" in result["message"]

    def test_parse_error_returns_error(self, tmp_path: Path):
        """Garbage qqdata returns an error status."""
        result = process_qqdata(
            qqdata={"not": "valid"},
            output_dir=tmp_path,
            known_ids=set(),
            checkpoint=WeiQiCheckpoint(source_mode="browser-capture"),
        )

        assert result["status"] == "error"

    def test_known_ids_updated_after_save(self, tmp_path: Path):
        """known_ids set is updated with the puzzle_id after success."""
        known_ids: set[int] = set()
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        process_qqdata(
            qqdata=_sample_qqdata(99001),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
            match_collections=False,
            resolve_intent=False,
        )

        assert 99001 in known_ids

    def test_multiple_puzzles_different_ids(self, tmp_path: Path):
        """Multiple distinct puzzles are all saved."""
        known_ids: set[int] = set()
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        for pid in [80001, 80002, 80003]:
            result = process_qqdata(
                qqdata=_sample_qqdata(pid),
                output_dir=tmp_path,
                known_ids=known_ids,
                checkpoint=checkpoint,
                match_collections=False,
                resolve_intent=False,
            )
            assert result["status"] == "ok"

        assert len(known_ids) == 3


# ---------------------------------------------------------------------------
# Qday (daily puzzle) routing tests
# ---------------------------------------------------------------------------


class TestQdayRouting:
    """Tests for /qday/ URL detection and storage routing."""

    def test_qday_url_saves_to_qday_directory(self, tmp_path: Path):
        """A qday URL routes the puzzle to qday/YYYY/MM/YYYYMMDD-N.sgf."""
        known_ids: set[int] = set()
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        result = process_qqdata(
            qqdata=_sample_qqdata(55761),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
            match_collections=False,
            resolve_intent=False,
            url="https://www.101weiqi.com/qday/2026/4/14/3/",
        )

        assert result["status"] == "ok"
        assert result["puzzle_id"] == 55761
        file_path = Path(result["message"])
        assert file_path.exists()
        assert file_path.name == "20260414-3-55761.sgf"
        assert "qday" in str(file_path)
        assert "2026" in str(file_path)
        assert "04" in str(file_path)

    def test_non_qday_url_saves_to_batch(self, tmp_path: Path):
        """A regular /q/ URL saves to batch directory as usual."""
        known_ids: set[int] = set()
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        result = process_qqdata(
            qqdata=_sample_qqdata(55762),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
            match_collections=False,
            resolve_intent=False,
            url="https://www.101weiqi.com/q/55762/",
        )

        assert result["status"] == "ok"
        file_path = Path(result["message"])
        assert "batch-" in str(file_path)

    def test_qday_dedup_on_reload(self, tmp_path: Path):
        """Qday entries in sgf-index.txt are loaded for dedup on restart."""
        from tools.weiqi101.index import load_puzzle_ids

        # Write a fake index with qday entry
        index_path = tmp_path / "sgf-index.txt"
        index_path.write_text(
            "batch-001/78000.sgf\n"
            "qday/2026/04/20260414-3.sgf:354411\n",
            encoding="utf-8",
        )

        ids = load_puzzle_ids(tmp_path)
        assert 78000 in ids      # batch entry
        assert 354411 in ids     # qday entry

    def test_qday_puzzle_skipped_as_duplicate(self, tmp_path: Path):
        """A qday puzzle already in known_ids is skipped."""
        known_ids: set[int] = {55761}
        checkpoint = WeiQiCheckpoint(source_mode="browser-capture")

        result = process_qqdata(
            qqdata=_sample_qqdata(55761),
            output_dir=tmp_path,
            known_ids=known_ids,
            checkpoint=checkpoint,
            url="https://www.101weiqi.com/qday/2026/4/14/3/",
        )

        assert result["status"] == "skipped"

    def test_parse_qday_url(self):
        """parse_qday_url extracts year, month, day, number."""
        from tools.weiqi101.storage import parse_qday_url

        assert parse_qday_url("https://www.101weiqi.com/qday/2026/4/14/3/") == (2026, 4, 14, 3)
        assert parse_qday_url("https://www.101weiqi.com/qday/2025/12/1/8/") == (2025, 12, 1, 8)
        assert parse_qday_url("https://www.101weiqi.com/q/55761/") is None
        assert parse_qday_url(None) is None
        assert parse_qday_url("") is None


# ---------------------------------------------------------------------------
# import_jsonl tests
# ---------------------------------------------------------------------------


class TestImportJsonl:
    """Tests for JSONL offline import."""

    def test_import_basic(self, tmp_path: Path):
        """Import a JSONL file with two valid records."""
        jsonl_file = tmp_path / "input.jsonl"
        records = [
            {"qqdata": _sample_qqdata(90001)},
            {"qqdata": _sample_qqdata(90002)},
        ]
        jsonl_file.write_text(
            "\n".join(json.dumps(r) for r in records),
            encoding="utf-8",
        )

        output = tmp_path / "output"
        stats = import_jsonl(
            jsonl_path=jsonl_file,
            output_dir=output,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )

        assert stats["ok"] == 2
        assert stats["skipped"] == 0
        assert stats["error"] == 0

    def test_import_dedup_within_file(self, tmp_path: Path):
        """Duplicate puzzle_id within the same file is skipped."""
        jsonl_file = tmp_path / "dup.jsonl"
        records = [
            {"qqdata": _sample_qqdata(90010)},
            {"qqdata": _sample_qqdata(90010)},  # duplicate
        ]
        jsonl_file.write_text(
            "\n".join(json.dumps(r) for r in records),
            encoding="utf-8",
        )

        output = tmp_path / "output"
        stats = import_jsonl(
            jsonl_path=jsonl_file,
            output_dir=output,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )

        assert stats["ok"] == 1
        assert stats["skipped"] == 1

    def test_import_bad_json_line(self, tmp_path: Path):
        """Invalid JSON lines are counted as errors, not crashes."""
        jsonl_file = tmp_path / "bad.jsonl"
        content = json.dumps({"qqdata": _sample_qqdata(90020)}) + "\n{bad json\n"
        jsonl_file.write_text(content, encoding="utf-8")

        output = tmp_path / "output"
        stats = import_jsonl(
            jsonl_path=jsonl_file,
            output_dir=output,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )

        assert stats["ok"] == 1
        assert stats["error"] == 1

    def test_import_raw_qqdata_format(self, tmp_path: Path):
        """JSONL lines can be raw qqdata dicts (no 'qqdata' wrapper)."""
        jsonl_file = tmp_path / "raw.jsonl"
        jsonl_file.write_text(
            json.dumps(_sample_qqdata(90030)),
            encoding="utf-8",
        )

        output = tmp_path / "output"
        stats = import_jsonl(
            jsonl_path=jsonl_file,
            output_dir=output,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )

        assert stats["ok"] == 1


# ---------------------------------------------------------------------------
# HTTP server tests
# ---------------------------------------------------------------------------


class TestHttpEndpoints:
    """Tests for the receiver HTTP server endpoints."""

    @pytest.fixture()
    def server_addr(self, tmp_path: Path):
        """Start a receiver HTTP server on an ephemeral port and yield (host, port)."""
        from http.server import HTTPServer

        state = _ReceiverState(
            tmp_path,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )
        handler = _make_handler(state)
        # Port 0 = OS assigns an available port
        server = HTTPServer(("127.0.0.1", 0), handler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        yield host, port, state

        server.shutdown()

    def test_health_endpoint(self, server_addr):
        host, port, _ = server_addr
        url = f"http://{host}:{port}/health"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "ok"

    def test_status_endpoint(self, server_addr):
        host, port, _ = server_addr
        url = f"http://{host}:{port}/status"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert "stats" in data
        assert "known_count" in data

    def test_capture_valid_puzzle(self, server_addr):
        host, port, state = server_addr
        url = f"http://{host}:{port}/capture"
        payload = json.dumps({"qqdata": _sample_qqdata(70001)}).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

        assert data["status"] == "ok"
        assert data["puzzle_id"] == 70001
        assert state.stats["ok"] == 1

    def test_capture_duplicate(self, server_addr):
        host, port, state = server_addr
        url = f"http://{host}:{port}/capture"
        payload = json.dumps({"qqdata": _sample_qqdata(70010)}).encode("utf-8")

        # First request
        req1 = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req1)

        # Second (duplicate) request
        req2 = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req2) as resp:
            data = json.loads(resp.read())

        assert data["status"] == "skipped"

    def test_capture_empty_body(self, server_addr):
        host, port, _ = server_addr
        url = f"http://{host}:{port}/capture"
        req = urllib.request.Request(
            url,
            data=b"",
            headers={
                "Content-Type": "application/json",
                "Content-Length": "0",
            },
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    def test_capture_invalid_json(self, server_addr):
        host, port, _ = server_addr
        url = f"http://{host}:{port}/capture"
        req = urllib.request.Request(
            url,
            data=b"not json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    def test_not_found_path(self, server_addr):
        host, port, _ = server_addr
        url = f"http://{host}:{port}/nonexistent"
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(url)
        assert exc_info.value.code == 404

    def test_status_includes_queue(self, server_addr):
        """Status endpoint includes queue summary."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/status"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert "queue" in data
        assert data["queue"]["active"] is False

    def test_telemetry_endpoint(self, server_addr):
        """Telemetry endpoint returns session summary."""
        host, port, _ = server_addr
        # Capture one puzzle first to have telemetry data
        capture_url = f"http://{host}:{port}/capture"
        payload = json.dumps({"qqdata": _sample_qqdata(70050)}).encode("utf-8")
        req = urllib.request.Request(
            capture_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req)

        url = f"http://{host}:{port}/telemetry"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        assert "counts" in data
        assert data["counts"]["ok"] == 1
        assert data["total_processed"] == 1
        assert "avg_duration_ms" in data
        assert "started_at" in data
        assert "recent_events" in data
        assert len(data["recent_events"]) == 1
        assert data["recent_events"][0]["puzzle_id"] == 70050

    def test_telemetry_records_errors(self, server_addr):
        """Telemetry tracks error events."""
        host, port, _ = server_addr
        # Submit invalid qqdata
        capture_url = f"http://{host}:{port}/capture"
        bad_data = _sample_qqdata(70060)
        bad_data["prepos"] = [[], []]  # no stones = validation error
        payload = json.dumps({"qqdata": bad_data}).encode("utf-8")
        req = urllib.request.Request(
            capture_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError:
            pass

        url = f"http://{host}:{port}/telemetry"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        assert data["counts"]["error"] == 1
        assert len(data["recent_errors"]) == 1
        assert data["last_error_at"] is not None

    def test_next_without_queue(self, server_addr):
        """GET /next returns inactive when no queue is loaded."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/next"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "inactive"

    def test_queue_ids_and_next(self, server_addr):
        """POST /queue/ids loads IDs, GET /next returns them in order."""
        host, port, _ = server_addr

        # Load IDs
        load_url = f"http://{host}:{port}/queue/ids"
        payload = json.dumps({"ids": [5001, 5002, 5003], "label": "test"}).encode("utf-8")
        req = urllib.request.Request(
            load_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "ok"
        assert data["total_ids"] == 3
        assert data["pending"] == 3

        # Get next — should be 5001
        next_url = f"http://{host}:{port}/next"
        with urllib.request.urlopen(next_url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "ok"
        assert data["puzzle_id"] == 5001
        assert data["remaining"] == 2
        assert "101weiqi.com/q/5001/" in data["url"]

        # Get next — should be 5002
        with urllib.request.urlopen(next_url) as resp:
            data = json.loads(resp.read())
        assert data["puzzle_id"] == 5002

        # Get next — should be 5003
        with urllib.request.urlopen(next_url) as resp:
            data = json.loads(resp.read())
        assert data["puzzle_id"] == 5003
        assert data["remaining"] == 0

        # Get next — queue exhausted
        with urllib.request.urlopen(next_url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "done"

    def test_queue_ids_skips_known(self, server_addr):
        """IDs already in known_ids are excluded from queue."""
        host, port, state = server_addr
        # Pre-populate known IDs
        state.known_ids.add(6001)
        state.known_ids.add(6003)

        load_url = f"http://{host}:{port}/queue/ids"
        payload = json.dumps({"ids": [6001, 6002, 6003, 6004]}).encode("utf-8")
        req = urllib.request.Request(
            load_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        assert data["total_ids"] == 4
        assert data["pending"] == 2
        assert data["already_downloaded"] == 2

    def test_queue_status_endpoint(self, server_addr):
        """GET /queue/status returns current queue state."""
        host, port, _ = server_addr

        # Load some IDs
        load_url = f"http://{host}:{port}/queue/ids"
        payload = json.dumps({"ids": [7001, 7002]}).encode("utf-8")
        req = urllib.request.Request(
            load_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req)

        url = f"http://{host}:{port}/queue/status"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert data["active"] is True
        assert data["total_ids"] == 2
        assert data["pending"] == 2
        assert data["source"] == "manual"

    def test_queue_stop_endpoint(self, server_addr):
        """GET /queue/stop deactivates the queue."""
        host, port, _ = server_addr

        # Load and stop
        load_url = f"http://{host}:{port}/queue/ids"
        payload = json.dumps({"ids": [8001, 8002]}).encode("utf-8")
        req = urllib.request.Request(
            load_url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req)

        stop_url = f"http://{host}:{port}/queue/stop"
        with urllib.request.urlopen(stop_url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "stopped"

        # Next should return inactive
        next_url = f"http://{host}:{port}/next"
        with urllib.request.urlopen(next_url) as resp:
            data = json.loads(resp.read())
        assert data["status"] == "inactive"

    def test_queue_book_not_found(self, server_addr):
        """POST /queue/book returns 404 when book-ids.jsonl missing."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/queue/book"
        payload = json.dumps({"book_id": 99999}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 404

    def test_queue_ids_invalid_payload(self, server_addr):
        """POST /queue/ids with invalid data returns 400."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/queue/ids"
        payload = json.dumps({"ids": "not-a-list"}).encode("utf-8")
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req)
        assert exc_info.value.code == 400

    def test_books_endpoint_with_data(self, server_addr):
        """GET /books lists available books from books-catalog.jsonl."""
        from tools.weiqi101 import catalog as catalog_mod

        host, port, state = server_addr
        # Write a minimal book-ids.jsonl
        jsonl_path = state.output_dir / "book-ids.jsonl"
        entry = {
            "book_id": 197,
            "book_name_en": "Test Book",
            "book_name": "测试",
            "difficulty": "10K+",
            "puzzle_ids": [10001, 10002, 10003],
        }
        jsonl_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        # Build the derived catalog the endpoint reads from
        catalog_mod.rebuild_books_catalog(state.output_dir)
        # Mark one as already downloaded
        state.known_ids.add(10001)

        url = f"http://{host}:{port}/books"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        assert len(data["books"]) == 1
        book = data["books"][0]
        assert book["book_id"] == 197
        assert book["total"] == 3
        assert book["downloaded"] == 1
        assert book["remaining"] == 2
        assert book["complete"] is False
        # New fields surfaced from catalog
        assert "consensus_tier" in book
        assert "review_stale" in book
        # No reviews -> unrated
        assert book["consensus_tier"] == "unrated"

    def test_books_endpoint_no_file(self, server_addr):
        """GET /books returns empty list when no books-catalog.jsonl exists."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/books"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert data["books"] == []

    def test_books_endpoint_sorting(self, server_addr):
        """GET /books sorts incomplete books first, then by tier, then remaining desc."""
        from tools.weiqi101 import catalog as catalog_mod

        host, port, state = server_addr
        jsonl_path = state.output_dir / "book-ids.jsonl"
        entries = [
            {"book_id": 1, "book_name_en": "Small", "book_name": "小", "difficulty": "5K+",
             "puzzle_ids": [101, 102]},
            {"book_id": 2, "book_name_en": "Big", "book_name": "大", "difficulty": "1D+",
             "puzzle_ids": [201, 202, 203, 204, 205]},
            {"book_id": 3, "book_name_en": "Done", "book_name": "完", "difficulty": "3K+",
             "puzzle_ids": [301]},
        ]
        jsonl_path.write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8"
        )
        catalog_mod.rebuild_books_catalog(state.output_dir)
        # Mark book 3 as fully downloaded
        state.known_ids.add(301)

        url = f"http://{host}:{port}/books"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        books = data["books"]
        assert len(books) == 3
        # Incomplete first; books 1 & 2 share tier (unrated), so remaining
        # desc orders 2 ahead of 1.
        assert books[0]["book_id"] == 2
        assert books[1]["book_id"] == 1
        assert books[2]["book_id"] == 3
        assert books[2]["complete"] is True

    def test_books_endpoint_refresh_rebuilds_catalog(self, server_addr):
        """GET /books?refresh=1 rebuilds catalog and reloads known_ids."""
        from tools.weiqi101 import catalog as catalog_mod

        host, port, state = server_addr
        jsonl_path = state.output_dir / "book-ids.jsonl"
        entry = {
            "book_id": 42,
            "book_name_en": "Refreshable",
            "book_name": "刷新",
            "puzzle_ids": [501, 502, 503],
        }
        jsonl_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        # Catalog is missing — refresh should build it
        url = f"http://{host}:{port}/books?refresh=1"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert len(data["books"]) == 1
        assert data["books"][0]["book_id"] == 42
        assert (state.output_dir / catalog_mod.CATALOG_FILE).exists()


class TestBookManifestPartial:
    """POST /book/manifest with partial=true (interleaved discovery↔capture).

    Validates the v5.38.0 contract:
      * Two partial POSTs accumulate chapters by chapter_id (no wholesale
        replace), discovery.status stays "in_progress".
      * A subsequent partial=false POST flips discovery.status to
        "complete" and writes completed_at.
      * Server-managed skip flags on chapters absent from a partial
        payload are preserved (relies on merge_discovery_state).
    """

    @pytest.fixture()
    def server_addr(self, tmp_path: Path):
        from http.server import HTTPServer

        state = _ReceiverState(
            tmp_path,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )
        handler = _make_handler(state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield host, port, state
        server.shutdown()

    @staticmethod
    def _post_manifest(host: str, port: int, body: dict) -> dict:
        url = f"http://{host}:{port}/book/manifest"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def test_partial_then_partial_then_final(self, server_addr):
        host, port, state = server_addr
        from tools.weiqi101 import book_state

        # First partial: only chapter 1 known
        r1 = self._post_manifest(host, port, {
            "book_id": 9001,
            "book_name": "Test Book",
            "partial": True,
            "chapters": [
                {"chapter_id": 100, "chapter_number": 1,
                 "name": "Chapter A", "puzzle_ids": [501, 502]},
            ],
        })
        assert r1["status"] == "ok"
        assert r1["partial"] is True

        books_dir = state.output_dir / "books"
        book_dir = book_state.find_book_dir(books_dir, 9001)
        assert book_dir is not None
        data = book_state.load(book_dir)
        assert data["discovery"]["status"] == "in_progress"
        assert len(data["chapters"]) == 1

        # Second partial: chapter 2 added; chapter 1 omitted from this
        # payload but must be preserved by the merge.
        r2 = self._post_manifest(host, port, {
            "book_id": 9001,
            "book_name": "Test Book",
            "partial": True,
            "chapters": [
                {"chapter_id": 100, "chapter_number": 1,
                 "name": "Chapter A", "puzzle_ids": [501, 502]},
                {"chapter_id": 101, "chapter_number": 2,
                 "name": "Chapter B", "puzzle_ids": [503, 504, 505]},
            ],
        })
        assert r2["partial"] is True
        data = book_state.load(book_dir)
        assert data["discovery"]["status"] == "in_progress"
        chapter_ids = sorted(c["chapter_id"] for c in data["chapters"])
        assert chapter_ids == [100, 101]
        # positions[] should now span both chapters
        assert len(data["positions"]) == 5

        # Final POST: marks discovery complete.
        r3 = self._post_manifest(host, port, {
            "book_id": 9001,
            "book_name": "Test Book",
            "partial": False,
            "chapters": [
                {"chapter_id": 100, "chapter_number": 1,
                 "name": "Chapter A", "puzzle_ids": [501, 502]},
                {"chapter_id": 101, "chapter_number": 2,
                 "name": "Chapter B", "puzzle_ids": [503, 504, 505]},
            ],
        })
        assert r3["partial"] is False
        data = book_state.load(book_dir)
        assert data["discovery"]["status"] == "complete"
        assert data["discovery"].get("completed_at")

    def test_partial_preserves_server_skip_flag(self, server_addr):
        """A skip flag set on a chapter must survive a partial POST that
        omits that chapter from its payload."""
        host, port, state = server_addr
        from tools.weiqi101 import book_state

        # Seed: two chapters discovered.
        self._post_manifest(host, port, {
            "book_id": 9002,
            "book_name": "Skip Test",
            "partial": True,
            "chapters": [
                {"chapter_id": 200, "chapter_number": 1,
                 "name": "A", "puzzle_ids": [1]},
                {"chapter_id": 201, "chapter_number": 2,
                 "name": "B", "puzzle_ids": [2]},
            ],
        })
        books_dir = state.output_dir / "books"
        book_dir = book_state.find_book_dir(books_dir, 9002)
        # Mark chapter 201 as manually skipped on the server.
        data = book_state.load(book_dir)
        for ch in data["chapters"]:
            if ch["chapter_id"] == 201:
                ch["skip_status"] = "manual"
                ch["skip_reason"] = "test"
        book_state.save(book_dir, data)

        # Partial POST that only re-sends chapter 200. Chapter 201's
        # skip flag must survive.
        self._post_manifest(host, port, {
            "book_id": 9002,
            "book_name": "Skip Test",
            "partial": True,
            "chapters": [
                {"chapter_id": 200, "chapter_number": 1,
                 "name": "A", "puzzle_ids": [1]},
            ],
        })
        data = book_state.load(book_dir)
        ch201 = next(c for c in data["chapters"] if c["chapter_id"] == 201)
        assert ch201["skip_status"] == "manual"
        assert ch201["skip_reason"] == "test"


class TestBookContextRouting:
    """Multi-layer reconciliation: receiver routes captures by detected
    book_id (which may differ from the active capture target) and persists
    `_capture_provenance` into `capture-log.jsonl` for audit.

    Pairs with the browser-side reconcileAttribution() — see
    ``tools/weiqi101/browser/101weiqi-capture.user.js``.
    """

    @pytest.fixture()
    def server_addr(self, tmp_path: Path):
        from http.server import HTTPServer

        state = _ReceiverState(
            tmp_path,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )
        handler = _make_handler(state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield host, port, state, tmp_path
        server.shutdown()

    @staticmethod
    def _post_capture(host, port, payload):
        url = f"http://{host}:{port}/capture"
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    def test_capture_with_book_context_writes_to_book_dir(self, server_addr):
        """Capture with `_book_context` lands under books/<slug>-<id>/sgf/."""
        host, port, _, tmp_path = server_addr
        payload = {
            "qqdata": _sample_qqdata(81001),
            "url": "https://www.101weiqi.com/book/5120/45791/81001/",
            "_book_context": {
                "book_id": 5120,
                "book_name": "Test Book",
                "chapter_id": 45791,
                "chapter_number": 1,
                "chapter_name": "Ch1",
                "chapter_position": 5,
                "global_position": 5,
                "puzzle_id": 81001,
                "capture_mode": "chapter",
            },
        }
        data = self._post_capture(host, port, payload)
        assert data["status"] == "ok"

        books_dir = tmp_path / "books"
        assert books_dir.exists()
        # Find the book dir (auto-resolved by slug)
        book_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
        assert len(book_dirs) == 1
        sgf_files = list((book_dirs[0] / "sgf").glob("*.sgf"))
        assert len(sgf_files) == 1
        # Chapter-mode naming: ch01_005_*_81001.sgf
        assert sgf_files[0].name.startswith("ch01_005_")
        assert sgf_files[0].name.endswith("_81001.sgf")

    def test_capture_with_unknown_book_id_auto_creates_dir(self, server_addr):
        """Cross-book salvage: capture detected for a book we've never
        seen — receiver auto-creates a fresh book dir for it."""
        host, port, _, tmp_path = server_addr
        payload = {
            "qqdata": _sample_qqdata(82002),
            "url": "https://www.101weiqi.com/book/9999/12345/82002/",
            "_book_context": {
                "book_id": 9999,  # never seen
                "book_name": "Salvaged Book",
                "chapter_id": 12345,
                "chapter_number": 3,
                "chapter_name": "X",
                "chapter_position": 7,
                "puzzle_id": 82002,
                "capture_mode": "chapter",
            },
        }
        data = self._post_capture(host, port, payload)
        assert data["status"] == "ok"
        books_dir = tmp_path / "books"
        # Some directory was created for book 9999
        book_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
        assert len(book_dirs) == 1
        log = book_dirs[0] / "capture-log.jsonl"
        assert log.exists()

    def test_capture_provenance_persisted_to_jsonl(self, server_addr):
        """`_capture_provenance` from the userscript is written into the
        per-book capture-log.jsonl row so downstream audit can see which
        layers agreed and which routing decision was made."""
        host, port, _, tmp_path = server_addr
        provenance = {
            "reconciled_pid": 83003,
            "pid_agreed_layers": ["qqdata", "url", "visible"],
            "pid_conflicts": [],
            "pid_candidates": {"qqdata": 83003, "url": 83003, "visible": 83003},
            "book_id": 5120,
            "book_source": "qqdata+breadcrumb",
            "chapter_id": 45791,
            "chapter_source": "breadcrumb",
            "chapter_number": 2,
            "chapter_number_source": "manifest+pid",
            "position": 11,
            "position_source": "breadcrumb",
            "all_known_books": [{"book_id": 5120, "name": "T"}],
            "active_book_id": 5120,
            "expected_pid_from_manifest": 83003,
            "drift_from_active": False,
            "drift_streak": 0,
        }
        payload = {
            "qqdata": _sample_qqdata(83003),
            "url": "https://www.101weiqi.com/book/5120/45791/83003/",
            "_book_context": {
                "book_id": 5120,
                "book_name": "T",
                "chapter_id": 45791,
                "chapter_number": 2,
                "chapter_name": "Ch2",
                "chapter_position": 11,
                "puzzle_id": 83003,
                "capture_mode": "chapter",
            },
            "_capture_provenance": provenance,
        }
        data = self._post_capture(host, port, payload)
        assert data["status"] == "ok"

        books_dir = tmp_path / "books"
        book_dirs = [d for d in books_dir.iterdir() if d.is_dir()]
        log_path = book_dirs[0] / "capture-log.jsonl"
        rows = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        # Last row is the puzzle capture
        capture_rows = [r for r in rows if r.get("event_type") == "puzzle_captured"]
        assert len(capture_rows) == 1
        assert capture_rows[0]["puzzle_id"] == 83003
        assert capture_rows[0]["capture_provenance"] == provenance

    def test_capture_drift_to_different_book_routes_to_detected_book(
        self, server_addr,
    ):
        """When the page lands on book 9999 while the active capture is
        for book 5120, the receiver files the SGF under book 9999's dir
        (auto-created), not 5120. Provenance records the drift."""
        host, port, _, tmp_path = server_addr
        # First, anchor an active book at 5120
        self._post_capture(host, port, {
            "qqdata": _sample_qqdata(84001),
            "url": "https://www.101weiqi.com/book/5120/45791/84001/",
            "_book_context": {
                "book_id": 5120, "book_name": "Active",
                "chapter_id": 45791, "chapter_number": 1, "chapter_name": "A",
                "chapter_position": 1, "puzzle_id": 84001,
                "capture_mode": "chapter",
            },
        })
        # Now a drifted capture: detected book is 9999, active was 5120
        self._post_capture(host, port, {
            "qqdata": _sample_qqdata(84002),
            "url": "https://www.101weiqi.com/book/9999/12345/84002/",
            "_book_context": {
                "book_id": 9999, "book_name": "Drifted",
                "chapter_id": 12345, "chapter_number": 1, "chapter_name": "X",
                "chapter_position": 1, "puzzle_id": 84002,
                "capture_mode": "chapter",
            },
            "_capture_provenance": {
                "reconciled_pid": 84002,
                "pid_agreed_layers": ["qqdata", "url"],
                "active_book_id": 5120,
                "drift_from_active": True,
                "drift_streak": 1,
            },
        })
        books_dir = tmp_path / "books"
        book_dirs = sorted(d.name for d in books_dir.iterdir() if d.is_dir())
        # Two distinct book directories created
        assert len(book_dirs) == 2
        # The drifted SGF lives under the dir whose capture-log mentions 9999
        for d in books_dir.iterdir():
            log = d / "capture-log.jsonl"
            if not log.exists():
                continue
            rows = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]
            for r in rows:
                if r.get("puzzle_id") == 84002:
                    assert r.get("capture_provenance", {}).get("drift_from_active") is True
                    return
        pytest.fail("Drifted capture not found in any book's capture-log")


# ---------------------------------------------------------------------------
# PuzzleQueue unit tests
# ---------------------------------------------------------------------------


class TestPuzzleQueue:
    """Tests for PuzzleQueue class."""

    def test_load_ids_basic(self):
        q = PuzzleQueue()
        result = q.load_ids([100, 200, 300], known_ids=set(), label="test")
        assert result["status"] == "ok"
        assert result["total_ids"] == 3
        assert result["pending"] == 3

    def test_load_ids_filters_known(self):
        q = PuzzleQueue()
        result = q.load_ids([100, 200, 300], known_ids={200}, label="test")
        assert result["pending"] == 2
        assert result["already_downloaded"] == 1

    def test_next_url_returns_in_order(self):
        q = PuzzleQueue()
        q.load_ids([10, 20, 30], known_ids=set())

        r1 = q.next_url()
        assert r1["puzzle_id"] == 10
        assert r1["remaining"] == 2

        r2 = q.next_url()
        assert r2["puzzle_id"] == 20

        r3 = q.next_url()
        assert r3["puzzle_id"] == 30
        assert r3["remaining"] == 0

        r4 = q.next_url()
        assert r4["status"] == "done"


class TestPuzzleDomMissing:
    """End-to-end Phase A: capture-time DOM bulk-prune is recorded.

    Covers the contract introduced in v5.40.0 / receiver Phase A:
      * POST /book/log/event {event_type: puzzle_dom_missing} mutates
        book.json positions[] entry to status=dom_missing.
      * Subsequent /book/{id}/manifest reflects:
          - the pid in known_ids (so resume-skip logic skips it)
          - chapter_audit shows it under dom_missing, NOT under remaining.
      * A real capture for the same pid wins over an existing
        dom_missing flag (status priority captured > dom_missing).
    """

    @pytest.fixture()
    def server_addr(self, tmp_path: Path):
        from http.server import HTTPServer

        state = _ReceiverState(
            tmp_path,
            batch_size=100,
            match_collections=False,
            resolve_intent=False,
        )
        handler = _make_handler(state)
        server = HTTPServer(("127.0.0.1", 0), handler)
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield host, port, state
        server.shutdown()

    @staticmethod
    def _post(host: str, port: int, path: str, body: dict) -> dict:
        url = f"http://{host}:{port}{path}"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _get(host: str, port: int, path: str) -> dict:
        url = f"http://{host}:{port}{path}"
        with urllib.request.urlopen(url) as resp:
            return json.loads(resp.read())

    def _seed_book(self, host, port):
        # Manifest with one chapter, three pids — pid 7702 will be marked
        # dom_missing; pid 7701 captured later; pid 7703 stays pending.
        self._post(host, port, "/book/manifest", {
            "book_id": 7700,
            "book_name": "DomMissing Test",
            "partial": False,
            "chapters": [
                {"chapter_id": 200, "chapter_number": 1,
                 "name": "Ch", "puzzle_ids": [7701, 7702, 7703]},
            ],
        })

    def test_event_marks_pid_dom_missing_in_book_state(self, server_addr):
        from tools.weiqi101 import book_state

        host, port, state = server_addr
        self._seed_book(host, port)

        self._post(host, port, "/book/log/event", {
            "book_id": 7700,
            "event_type": "puzzle_dom_missing",
            "detail": {
                "pid": 7702,
                "chapter_id": 200,
                "chapter_number": 1,
                "chapter_position": 2,
                "page": 1,
                "visible_count": 2,
                "reason": "absent_from_listing_page",
            },
        })

        books_dir = state.output_dir / "books"
        book_dir = book_state.find_book_dir(books_dir, 7700)
        data = book_state.load(book_dir)
        target = next(
            (p for p in data["positions"] if p.get("pid") == 7702), None,
        )
        assert target is not None, "pid 7702 not in positions[]"
        assert target["status"] == "dom_missing"
        assert target.get("dom_missing_reason") == "absent_from_listing_page"
        assert target.get("dom_missing_at"), "dom_missing_at not stamped"

    def test_audit_subtracts_dom_missing_from_remaining(self, server_addr):
        host, port, state = server_addr
        self._seed_book(host, port)

        self._post(host, port, "/book/log/event", {
            "book_id": 7700,
            "event_type": "puzzle_dom_missing",
            "detail": {
                "pid": 7702, "chapter_id": 200, "chapter_number": 1,
                "chapter_position": 2, "page": 1, "reason": "x",
            },
        })

        manifest = self._get(host, port, "/book/7700/manifest")
        # known_ids includes the dom_missing pid so the userscript
        # skip-forward logic skips it on resume.
        assert 7702 in manifest["known_ids"]
        # chapter_audit splits captured / dom_missing / remaining cleanly.
        ca = manifest["chapter_audit"][0]
        assert ca["total"] == 3
        assert ca["captured"] == 0
        assert ca["dom_missing"] == 1
        assert 7702 in ca["dom_missing_pids"]
        # Remaining excludes dom_missing.
        assert ca["remaining"] == 2
        assert sorted(ca["remaining_pids"]) == [7701, 7703]

    def test_real_capture_overrides_dom_missing(self, server_addr):
        from tools.weiqi101 import book_state

        host, port, state = server_addr
        self._seed_book(host, port)

        # Mark pid 7702 dom_missing.
        self._post(host, port, "/book/log/event", {
            "book_id": 7700,
            "event_type": "puzzle_dom_missing",
            "detail": {
                "pid": 7702, "chapter_id": 200, "chapter_number": 1,
                "chapter_position": 2, "reason": "x",
            },
        })

        # Now suppose the site recovered and the puzzle DOES appear:
        # simulate by directly applying a capture (mirrors what
        # _save_to_book_dir does after a successful POST /capture).
        books_dir = state.output_dir / "books"
        book_dir = book_state.find_book_dir(books_dir, 7700)
        data = book_state.load(book_dir)
        book_state.apply_capture(
            data,
            pid=7702,
            file="ch_001/Ch_001_007702.sgf",
            chapter_number=1,
            chapter_position=2,
            chapter_name="Ch",
        )
        book_state.save(book_dir, data)

        data = book_state.load(book_dir)
        target = next(p for p in data["positions"] if p.get("pid") == 7702)
        assert target["status"] == "captured"
        # Captured wins; reapplying dom_missing now is a no-op.
        book_state.apply_dom_missing(
            data, pid=7702, reason="should_not_apply",
        )
        target = next(p for p in data["positions"] if p.get("pid") == 7702)
        assert target["status"] == "captured"

    def test_next_url_inactive(self):
        q = PuzzleQueue()
        result = q.next_url()
        assert result["status"] == "inactive"

    def test_stop(self):
        q = PuzzleQueue()
        q.load_ids([1, 2, 3], known_ids=set())
        q.next_url()  # consume one
        result = q.stop()
        assert result["status"] == "stopped"
        assert result["visited"] == 1
        assert result["remaining"] == 2

        # After stop, next returns inactive
        assert q.next_url()["status"] == "inactive"

    def test_status(self):
        q = PuzzleQueue()
        q.load_ids([1, 2, 3, 4], known_ids={3}, label="my-batch")
        q.next_url()

        s = q.status()
        assert s["active"] is True
        assert s["source"] == "my-batch"
        assert s["total_ids"] == 4
        assert s["pending"] == 2  # started with 3 pending (4 minus known 3), consumed 1
        assert s["visited"] == 1
        assert s["already_downloaded"] == 1
        assert s["progress_pct"] == 25.0  # 1/4

    def test_load_book_from_jsonl(self, tmp_path: Path):
        """Load book from a book-ids.jsonl file."""
        jsonl = tmp_path / "book-ids.jsonl"
        entry = {
            "book_id": 42,
            "book_name": "Test Book",
            "book_name_en": "Test Book EN",
            "puzzle_ids": [1001, 1002, 1003, 1004],
        }
        jsonl.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        q = PuzzleQueue()
        result = q.load_book(42, output_dir=tmp_path, known_ids={1002})
        assert result["status"] == "ok"
        assert result["book_id"] == 42
        assert result["book_name"] == "Test Book EN"
        assert result["total_ids"] == 4
        assert result["pending"] == 3
        assert result["already_downloaded"] == 1

    def test_load_book_with_chapters(self, tmp_path: Path):
        """Load book with chapter structure from book-ids.jsonl."""
        jsonl = tmp_path / "book-ids.jsonl"
        entry = {
            "book_id": 99,
            "book_name_en": "Chapter Book",
            "chapters": [
                {"chapter_number": 1, "puzzle_ids": [2001, 2002]},
                {"chapter_number": 2, "puzzle_ids": [2003, 2004]},
            ],
        }
        jsonl.write_text(json.dumps(entry) + "\n", encoding="utf-8")

        q = PuzzleQueue()
        result = q.load_book(99, output_dir=tmp_path, known_ids=set())
        assert result["total_ids"] == 4
        assert result["pending"] == 4

    def test_load_book_not_found(self, tmp_path: Path):
        """Returns error when book is not in JSONL."""
        jsonl = tmp_path / "book-ids.jsonl"
        jsonl.write_text('{"book_id": 1}\n', encoding="utf-8")

        q = PuzzleQueue()
        result = q.load_book(999, output_dir=tmp_path, known_ids=set())
        assert "error" in result

    def test_load_book_no_jsonl(self, tmp_path: Path):
        """Returns error when book-ids.jsonl does not exist."""
        q = PuzzleQueue()
        result = q.load_book(1, output_dir=tmp_path, known_ids=set())
        assert "error" in result

    def test_empty_ids_rejected(self):
        q = PuzzleQueue()
        result = q.load_ids([], known_ids=set())
        assert "error" in result


# ---------------------------------------------------------------------------
# Telemetry unit tests
# ---------------------------------------------------------------------------


class TestTelemetry:
    """Tests for Telemetry class."""

    def test_record_ok(self):
        t = Telemetry()
        t.record(123, "ok", "/path/to/file.sgf", 42.5)
        s = t.summary()
        assert s["counts"]["ok"] == 1
        assert s["total_processed"] == 1
        assert s["avg_duration_ms"] == 42.5
        assert s["last_ok_at"] is not None
        assert len(s["recent_events"]) == 1

    def test_record_error(self):
        t = Telemetry()
        t.record(456, "error", "validation: bad stones", 10.0)
        s = t.summary()
        assert s["counts"]["error"] == 1
        assert s["last_error_at"] is not None
        assert len(s["recent_errors"]) == 1
        assert s["recent_errors"][0]["puzzle_id"] == 456

    def test_multiple_events(self):
        t = Telemetry()
        t.record(1, "ok", "file1.sgf", 30.0)
        t.record(2, "skipped", "duplicate", 5.0)
        t.record(3, "error", "bad data", 15.0)
        s = t.summary()
        assert s["total_processed"] == 3
        assert s["counts"] == {"ok": 1, "skipped": 1, "error": 1}
        assert s["avg_duration_ms"] == round((30.0 + 5.0 + 15.0) / 3, 1)

    def test_set_book(self):
        t = Telemetry()
        t.set_book(197, "Wu Qingyuan Tsumego")
        s = t.summary()
        assert s["book_id"] == 197
        assert s["book_name"] == "Wu Qingyuan Tsumego"

    def test_max_recent_events(self):
        t = Telemetry()
        for i in range(250):
            t.record(i, "ok", f"file{i}.sgf", 1.0)
        s = t.summary()
        assert len(s["recent_events"]) == Telemetry.MAX_RECENT
        assert s["total_processed"] == 250

    def test_summary_empty(self):
        t = Telemetry()
        s = t.summary()
        assert s["total_processed"] == 0
        assert s["avg_duration_ms"] == 0
        assert s["last_ok_at"] is None
        assert s["last_error_at"] is None

    def test_record_ok_with_level_meta_and_slog(self):
        """`level` metadata should not override StructuredLogger.event(level=...)."""
        from tools.core.logging import StructuredLogger

        slog = StructuredLogger(logging.getLogger("tools.weiqi101.tests.telemetry"))
        t = Telemetry(slog=slog)

        t.record(
            999,
            "ok",
            "file999.sgf",
            12.3,
            meta={
                "level": "13K+",
                "type": "life-and-death",
                "stones": 42,
            },
        )

        s = t.summary()
        assert s["counts"]["ok"] == 1
        assert s["total_processed"] == 1

    def test_rolling_rate_windows(self):
        """rolling_rate filters by status + age; summary surfaces 5m/15m rates."""
        import time as _time

        t = Telemetry()
        # Record 6 ok events in the last minute, 4 ok events 10 min ago,
        # and 3 skipped events sprinkled across (must be excluded).
        now = _time.time()
        for i in range(6):
            t.record(i, "ok", f"f{i}.sgf", 10.0)
        for e in list(t._events)[-6:]:
            e.ts_epoch = now - 30  # 30 s ago

        for i in range(4):
            t.record(100 + i, "ok", f"old{i}.sgf", 10.0)
        for e in list(t._events)[-4:]:
            e.ts_epoch = now - 600  # 10 min ago

        for i in range(3):
            t.record(200 + i, "skipped", "duplicate", 5.0)
        for e in list(t._events)[-3:]:
            e.ts_epoch = now - 60

        c5, r5 = t.rolling_rate(300, now_epoch=now)
        c15, r15 = t.rolling_rate(900, now_epoch=now)

        assert c5 == 6                       # only the 6 recent oks
        assert r5 == round(6 * 60 / 300, 2)  # 1.2/min
        assert c15 == 10                     # 6 recent + 4 ten-min-old
        assert r15 == round(10 * 60 / 900, 2)

        s = t.summary()
        assert "ok_per_min_5m" in s
        assert "ok_per_min_15m" in s
        assert s["window_ok_count_5m"] >= 0  # uses real wall clock; sanity only

