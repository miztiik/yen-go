"""Real-fixture tests for /api/adapter/* and /api/publish-log/search.

Same env-driven shim pattern as ``test_routes_lock.py``: a tmp
``backend/puzzle_manager`` package whose ``__main__.py`` recognises the
three subcommands the admin router invokes and shapes its output from
environment variables. We never touch the real ``sources.json`` or
``.pm-runtime/publish-log/`` files.

Subcommand contracts the shim mimics:

  - ``enable-adapter ADAPTER_ID [--force]``   → exit ``YENGO_FAKE_RC`` (default 0),
                                                stdout/stderr from env, ADAPTER_ID echoed
  - ``disable-adapter [--force]``             → same env-driven exit/output shape
  - ``publish-log search --format json [...]``→ ``YENGO_FAKE_PL_RC`` controls exit;
                                                on success prints
                                                ``YENGO_FAKE_PL_JSON`` (must parse)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from fastapi.testclient import TestClient

from tools.pm_cockpit.server.app import create_app
from tools.pm_cockpit.server.run_controller import RunController


def _make_fake_admin_repo(tmp_path: Path) -> Path:
    pkg = tmp_path / "backend" / "puzzle_manager"
    pkg.mkdir(parents=True)
    (pkg.parent / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__main__.py").write_text(
        textwrap.dedent(
            """
            import json
            import os
            import sys

            argv = sys.argv[1:]
            # Allow a leading "--config PATH" pair (cockpit may inject it).
            if argv[:1] == ["--config"] and len(argv) >= 2:
                argv = argv[2:]

            cmd = argv[0] if argv else ""

            if cmd == "enable-adapter":
                rc = int(os.environ.get("YENGO_FAKE_RC", "0"))
                stdout = os.environ.get("YENGO_FAKE_STDOUT", "")
                stderr = os.environ.get("YENGO_FAKE_STDERR", "")
                # Echo argv so tests can confirm flag forwarding.
                if stdout:
                    print(stdout, flush=True)
                print("argv: " + " ".join(argv[1:]), flush=True)
                if stderr:
                    print(stderr, file=sys.stderr, flush=True)
                sys.exit(rc)

            if cmd == "disable-adapter":
                rc = int(os.environ.get("YENGO_FAKE_RC", "0"))
                stdout = os.environ.get("YENGO_FAKE_STDOUT", "")
                stderr = os.environ.get("YENGO_FAKE_STDERR", "")
                if stdout:
                    print(stdout, flush=True)
                print("argv: " + " ".join(argv[1:]), flush=True)
                if stderr:
                    print(stderr, file=sys.stderr, flush=True)
                sys.exit(rc)

            if argv[:2] == ["publish-log", "search"]:
                rc = int(os.environ.get("YENGO_FAKE_PL_RC", "0"))
                if rc != 0:
                    msg = os.environ.get("YENGO_FAKE_PL_STDERR", "search failed")
                    print(msg, file=sys.stderr, flush=True)
                    sys.exit(rc)
                payload = os.environ.get(
                    "YENGO_FAKE_PL_JSON", json.dumps({"results": [], "argv": argv[2:]})
                )
                # Inject the captured argv so tests can assert flag wiring.
                try:
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict):
                        parsed.setdefault("_argv", argv[2:])
                        payload = json.dumps(parsed)
                except Exception:
                    pass
                print(payload, flush=True)
                sys.exit(0)

            print(f"unknown subcommand {cmd!r}", file=sys.stderr, flush=True)
            sys.exit(2)
            """
        ).strip(),
        encoding="utf-8",
    )
    return tmp_path


def _make_test_client(tmp_path: Path) -> TestClient:
    fake_repo = _make_fake_admin_repo(tmp_path)
    controller = RunController(repo_root=fake_repo)
    app = create_app(repo_root=fake_repo, controller=controller)
    return TestClient(app)


# ---------------- enable-adapter ----------------


class TestEnableAdapter:
    def test_success_returns_ok_true_and_forwards_id(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("YENGO_FAKE_RC", "0")
        monkeypatch.setenv("YENGO_FAKE_STDOUT", "active adapter set to ogs")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/enable", json={"adapter_id": "ogs"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["returncode"] == 0
        assert "active adapter set to ogs" in body["stdout"]
        # The argv echo line confirms the positional ID arrived as expected.
        assert "argv: ogs" in body["stdout"]

    def test_force_flag_threaded_through(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("YENGO_FAKE_RC", "0")
        monkeypatch.setenv("YENGO_FAKE_STDOUT", "")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post(
                "/api/adapter/enable",
                json={"adapter_id": "sanderland", "force": True},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "argv: sanderland --force" in body["stdout"]

    def test_failure_returns_ok_false_not_502(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # Lock conflict / unknown id / etc. is the operator's business — must
        # surface as ok=false with stderr, not a generic 502.
        monkeypatch.setenv("YENGO_FAKE_RC", "1")
        monkeypatch.setenv("YENGO_FAKE_STDOUT", "")
        monkeypatch.setenv("YENGO_FAKE_STDERR", "config locked, use --force")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/enable", json={"adapter_id": "ogs"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert body["returncode"] == 1
        assert "use --force" in body["stderr"]

    def test_missing_adapter_id_returns_422(self, tmp_path: Path) -> None:
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/enable", json={})
        assert resp.status_code == 422

    def test_empty_adapter_id_returns_422(self, tmp_path: Path) -> None:
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/enable", json={"adapter_id": ""})
        assert resp.status_code == 422


# ---------------- disable-adapter ----------------


class TestDisableAdapter:
    def test_default_invocation_succeeds(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("YENGO_FAKE_RC", "0")
        monkeypatch.setenv("YENGO_FAKE_STDOUT", "active adapter cleared")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/disable", json={})
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "cleared" in body["stdout"]

    def test_force_flag_threaded_through(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("YENGO_FAKE_RC", "0")
        monkeypatch.setenv("YENGO_FAKE_STDOUT", "")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.post("/api/adapter/disable", json={"force": True})
        assert resp.status_code == 200
        assert "argv: --force" in resp.json()["stdout"]


# ---------------- publish-log search ----------------


class TestPublishLogSearch:
    def test_returns_raw_payload_verbatim(self, tmp_path: Path, monkeypatch) -> None:
        # The cockpit must NOT reshape the CLI's payload — the publish-log
        # schema is owned by the pipeline.
        sample = {"results": [{"trace_id": "abc", "puzzle_id": "deadbeef"}]}
        monkeypatch.setenv("YENGO_FAKE_PL_JSON", json.dumps(sample))
        client = _make_test_client(tmp_path)
        with client:
            resp = client.get("/api/publish-log/search", params={"run_id": "20260505-x"})
        assert resp.status_code == 200
        raw = resp.json()["raw"]
        assert raw["results"] == sample["results"]

    def test_filter_flags_translated_to_kebab_case(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        monkeypatch.setenv("YENGO_FAKE_PL_JSON", json.dumps({"results": []}))
        client = _make_test_client(tmp_path)
        with client:
            resp = client.get(
                "/api/publish-log/search",
                params={
                    "run_id": "rid-1",
                    "puzzle_id": "abc123",
                    "trace_id": "tid",
                    "from": "2026-01-01",
                    "to": "2026-05-05",
                    "limit": 10,
                },
            )
        assert resp.status_code == 200
        # The shim echoed argv into _argv. Confirm the cockpit translated
        # python_case → kebab-case and forwarded the limit as a string.
        argv = resp.json()["raw"]["_argv"]
        assert "--format" in argv and argv[argv.index("--format") + 1] == "json"
        assert "--run-id" in argv and argv[argv.index("--run-id") + 1] == "rid-1"
        assert "--puzzle-id" in argv and argv[argv.index("--puzzle-id") + 1] == "abc123"
        assert "--trace-id" in argv and argv[argv.index("--trace-id") + 1] == "tid"
        assert "--from" in argv and argv[argv.index("--from") + 1] == "2026-01-01"
        assert "--to" in argv and argv[argv.index("--to") + 1] == "2026-05-05"
        assert "--limit" in argv and argv[argv.index("--limit") + 1] == "10"

    def test_empty_filters_drop_to_no_filter_call(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        # No params at all: the cockpit forwards just `--format json`. The
        # CLI rejects it (no filter), and the cockpit translates the
        # PipelineCommandError to 400 (not 502) so the operator sees a useful
        # message.
        monkeypatch.setenv("YENGO_FAKE_PL_RC", "2")
        monkeypatch.setenv("YENGO_FAKE_PL_STDERR", "must provide at least one filter")
        client = _make_test_client(tmp_path)
        with client:
            resp = client.get("/api/publish-log/search")
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "must provide at least one filter" in detail["stderr"]
