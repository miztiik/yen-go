"""Tests for multi-book PuzzleQueue support (v5.40.0).

The receiver maintains a dict of PuzzleQueue instances keyed by
``book_id`` so two browser profiles can drive two different books in
parallel against the same receiver. The legacy (no ``book_id``) API
still routes to a shared ``"default"`` queue so single-book callers
keep working unchanged.
"""

from __future__ import annotations

import json
import threading
import urllib.request
from http.server import HTTPServer
from pathlib import Path

import pytest

from tools.weiqi101.receiver import PuzzleQueue, _ReceiverState, _make_handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_book_ids_jsonl(output_dir: Path, books: list[dict]) -> None:
    """Materialize a minimal ``book-ids.jsonl`` for queue.load_book."""
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "book-ids.jsonl").open("w", encoding="utf-8") as f:
        for entry in books:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@pytest.fixture()
def two_book_state(tmp_path: Path, monkeypatch):
    """A _ReceiverState pre-seeded with two distinct books."""
    # The /queue/book handler reads book-ids.jsonl from
    # config.get_output_dir(None). Point it at our temp dir so tests
    # don't depend on the real workspace data.
    from tools.weiqi101 import receiver as rcv

    monkeypatch.setattr(rcv, "get_output_dir", lambda _src: tmp_path)

    _write_book_ids_jsonl(tmp_path, [
        {"book_id": 197, "book_name": "Book A", "puzzle_ids": [101, 102, 103]},
        {"book_id": 201, "book_name": "Book B", "puzzle_ids": [201, 202, 203, 204]},
    ])

    state = _ReceiverState(
        tmp_path,
        batch_size=100,
        match_collections=False,
        resolve_intent=False,
    )
    return state


@pytest.fixture()
def server_with_two_books(two_book_state):
    """Spin up an HTTP server bound to a multi-book state."""
    handler = _make_handler(two_book_state)
    server = HTTPServer(("127.0.0.1", 0), handler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield host, port, two_book_state
    finally:
        server.shutdown()


def _post_json(host: str, port: int, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"http://{host}:{port}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _get_json(host: str, port: int, path: str) -> dict:
    with urllib.request.urlopen(f"http://{host}:{port}{path}") as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------------------
# Unit tests: _resolve_queue / queues dict
# ---------------------------------------------------------------------------

class TestResolveQueue:
    def test_default_queue_lazy_created(self, tmp_path: Path):
        state = _ReceiverState(tmp_path, batch_size=10,
                               match_collections=False, resolve_intent=False)
        assert state.queues == {}
        q = state._resolve_queue(None)
        assert isinstance(q, PuzzleQueue)
        assert "default" in state.queues
        # Same instance on second call.
        assert state._resolve_queue(None) is q

    def test_queues_isolated_per_book_id(self, tmp_path: Path):
        state = _ReceiverState(tmp_path, batch_size=10,
                               match_collections=False, resolve_intent=False)
        qa = state._resolve_queue(197)
        qb = state._resolve_queue(201)
        assert qa is not qb
        assert state.queues["197"] is qa
        assert state.queues["201"] is qb

    def test_legacy_queue_property_aliases_default(self, tmp_path: Path):
        state = _ReceiverState(tmp_path, batch_size=10,
                               match_collections=False, resolve_intent=False)
        assert state.queue is state._resolve_queue(None)
        assert state.queue is state._resolve_queue("default")


class TestPuzzleQueueMarkDone:
    def test_mark_done_skips_unknown_pid(self):
        q = PuzzleQueue()
        q.load_ids([1, 2, 3], known_ids=set())
        # Capture of pid=999 (not in this queue's ids) must not pollute
        # visited — that would lie about progress in multi-book mode.
        q.mark_done(999)
        status = q.status()
        assert status["visited"] == 0

    def test_mark_done_records_known_pid(self):
        q = PuzzleQueue()
        q.load_ids([1, 2, 3], known_ids=set())
        q.mark_done(2)
        assert q.status()["visited"] == 1


# ---------------------------------------------------------------------------
# HTTP-level tests: routing by ?book_id= and POST body
# ---------------------------------------------------------------------------

class TestMultiBookQueueHttp:
    def test_load_two_books_independently(self, server_with_two_books):
        host, port, state = server_with_two_books

        a = _post_json(host, port, "/queue/book", {"book_id": 197})
        b = _post_json(host, port, "/queue/book", {"book_id": 201})

        assert a["status"] == "ok" and a["book_id"] == 197 and a["pending"] == 3
        assert b["status"] == "ok" and b["book_id"] == 201 and b["pending"] == 4

        # Two distinct queues exist server-side.
        assert "197" in state.queues
        assert "201" in state.queues
        assert state.queues["197"] is not state.queues["201"]

    def test_next_routes_by_book_id(self, server_with_two_books):
        host, port, _ = server_with_two_books
        _post_json(host, port, "/queue/book", {"book_id": 197})
        _post_json(host, port, "/queue/book", {"book_id": 201})

        # Pull from book A — must come from A's pending.
        na = _get_json(host, port, "/next?book_id=197")
        assert na["status"] == "ok"
        assert na["puzzle_id"] in (101, 102, 103)

        # Pull from book B — must come from B's pending and be unaffected
        # by A's pop.
        nb = _get_json(host, port, "/next?book_id=201")
        assert nb["status"] == "ok"
        assert nb["puzzle_id"] in (201, 202, 203, 204)

        # Statuses are independent.
        sa = _get_json(host, port, "/queue/status?book_id=197")
        sb = _get_json(host, port, "/queue/status?book_id=201")
        assert sa["pending"] == 2 and sa["visited"] == 1
        assert sb["pending"] == 3 and sb["visited"] == 1

    def test_stop_one_book_does_not_stop_other(self, server_with_two_books):
        host, port, _ = server_with_two_books
        _post_json(host, port, "/queue/book", {"book_id": 197})
        _post_json(host, port, "/queue/book", {"book_id": 201})

        _get_json(host, port, "/queue/stop?book_id=197")

        sa = _get_json(host, port, "/queue/status?book_id=197")
        sb = _get_json(host, port, "/queue/status?book_id=201")
        assert sa["active"] is False
        assert sb["active"] is True

    def test_status_exposes_all_queues(self, server_with_two_books):
        host, port, _ = server_with_two_books
        _post_json(host, port, "/queue/book", {"book_id": 197})
        _post_json(host, port, "/queue/book", {"book_id": 201})

        data = _get_json(host, port, "/status")
        assert "queues" in data
        assert set(data["queues"].keys()) >= {"197", "201"}
        assert data["queues"]["197"]["book_id"] == 197
        assert data["queues"]["201"]["book_id"] == 201


class TestLegacySingleQueueCompat:
    """Old callers that don't pass ``book_id`` still work."""

    def test_next_without_book_id_uses_default(self, server_with_two_books):
        host, port, state = server_with_two_books
        # Pre-load default queue directly so we can drive /next without
        # a book_id and confirm the default bucket is used.
        state._resolve_queue(None).load_ids([10, 11], known_ids=set())

        n = _get_json(host, port, "/next")
        assert n["status"] == "ok"
        assert n["puzzle_id"] in (10, 11)

    def test_status_keeps_legacy_queue_field(self, server_with_two_books):
        host, port, _ = server_with_two_books
        data = _get_json(host, port, "/status")
        # Legacy single-queue field is still present and points at default.
        assert "queue" in data
        assert data["queue"]["active"] is False
