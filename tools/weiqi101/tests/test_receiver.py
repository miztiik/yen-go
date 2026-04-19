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
        """GET /books lists available books from book-ids.jsonl."""
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

    def test_books_endpoint_no_file(self, server_addr):
        """GET /books returns empty list when no book-ids.jsonl exists."""
        host, port, _ = server_addr
        url = f"http://{host}:{port}/books"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
        assert data["books"] == []

    def test_books_endpoint_sorting(self, server_addr):
        """GET /books sorts incomplete books first, by remaining desc."""
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
        # Mark book 3 as fully downloaded
        state.known_ids.add(301)

        url = f"http://{host}:{port}/books"
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())

        books = data["books"]
        assert len(books) == 3
        # Incomplete first, by remaining desc
        assert books[0]["book_id"] == 2  # 5 remaining
        assert books[1]["book_id"] == 1  # 2 remaining
        assert books[2]["book_id"] == 3  # complete
        assert books[2]["complete"] is True


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
