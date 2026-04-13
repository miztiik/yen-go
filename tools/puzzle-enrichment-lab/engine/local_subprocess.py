"""Local KataGo subprocess driver.

Starts KataGo in analysis mode, sends JSON requests via stdin,
receives JSON responses via stdout.
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import threading
from pathlib import Path

try:
    from models.analysis_request import AnalysisRequest
    from models.analysis_response import AnalysisResponse

    from engine.config import EngineConfig
except ImportError:
    from ..models.analysis_request import AnalysisRequest
    from ..models.analysis_response import AnalysisResponse
    from .config import EngineConfig

logger = logging.getLogger(__name__)


class LocalEngine:
    """Drives a local KataGo process via stdin/stdout JSON protocol."""

    def __init__(self, config: EngineConfig):
        self.config = config
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._request_counter = 0
        self._stderr_thread: threading.Thread | None = None
        self._stderr_lines: list[str] = []

    async def start(self) -> None:
        """Start the KataGo subprocess.

        P2.2: Validates file existence before spawning process.
        """
        if self._process is not None:
            logger.warning("Engine already running")
            return

        # P2.2: Resolve relative paths to absolute before spawning subprocess
        # (subprocess cwd may differ from the caller's cwd, breaking relative paths)
        from pathlib import Path
        katago = Path(self.config.katago_path).resolve()
        if not katago.exists():
            raise FileNotFoundError(
                f"KataGo binary not found: {katago}. "
                "Download from https://github.com/lightvector/KataGo/releases"
            )
        self.config.katago_path = str(katago)
        if self.config.model_path:
            model = Path(self.config.model_path).resolve()
            if not model.exists():
                raise FileNotFoundError(
                    f"KataGo model file not found: {model}. "
                    "Run scripts/download_models.py or download from "
                    "https://katagotraining.org/networks/"
                )
            self.config.model_path = str(model)
        if self.config.config_path:
            config = Path(self.config.config_path).resolve()
            if config.exists():
                self.config.config_path = str(config)

        cmd = [self.config.katago_path, "analysis"]
        if self.config.model_path:
            cmd.extend(["-model", self.config.model_path])
        if self.config.config_path:
            cmd.extend(["-config", self.config.config_path])
            # Q10: Use config-driven KataGo log directory, centralized under .lab-runtime/
            try:
                from config import load_enrichment_config, resolve_path
                _cfg = load_enrichment_config()
                katago_log_dir = resolve_path(_cfg, "katago_logs_dir")
            except Exception:
                lab_dir = Path(self.config.config_path).resolve().parent.parent
                katago_log_dir = lab_dir / ".lab-runtime" / "katago-logs"
            katago_log_dir.mkdir(parents=True, exist_ok=True)
            cmd.extend(["-override-config", f"logDir={katago_log_dir.as_posix()}"])
        else:
            # Minimal inline config via command-line args
            cmd.extend([
                "-override-config",
                f"numAnalysisThreads={self.config.num_threads},"
                f"nnMaxBatchSize={self.config.num_threads}"
            ])

        logger.info(f"Starting KataGo: {' '.join(cmd)}")

        # Log resolved config summary for diagnostics
        model_name = Path(self.config.model_path).name if self.config.model_path else "<default>"
        config_name = Path(self.config.config_path).name if self.config.config_path else "<none>"
        logger.info(
            f"KataGo config: model={model_name}, "
            f"max_visits={self.config.default_max_visits}, "
            f"board_size={self.config.default_board_size}, "
            f"threads={self.config.num_threads}, "
            f"analysis_cfg={config_name}"
        )

        # Pin CWD to lab root so KataGo resolves relative paths (e.g. logDir)
        # within the tool directory, not whatever the caller's working directory is.
        process_cwd = (
            str(Path(self.config.config_path).resolve().parent.parent)
            if self.config.config_path
            else None
        )
        def _spawn():
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line-buffered
                cwd=process_cwd,
            )
            # Wait briefly and check it didn't crash
            try:
                self._process.wait(timeout=0.5)
                stderr = self._process.stderr.read() if self._process.stderr else ""
                raise RuntimeError(f"KataGo exited immediately: {stderr}")
            except subprocess.TimeoutExpired:
                pass  # Good — process is still running

        await asyncio.to_thread(_spawn)

        # Start a daemon thread to drain stderr so the pipe buffer never fills.
        # Without this, KataGo can deadlock when its stderr output exceeds the
        # OS pipe buffer size (~4-8 KB on Windows), blocking both stderr writes
        # and stdout responses.
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, daemon=True, name="katago-stderr"
        )
        self._stderr_thread.start()

        logger.info("KataGo engine started successfully")

    async def shutdown(self) -> None:
        """Stop the KataGo subprocess."""
        if self._process is None:
            return

        logger.info("Shutting down KataGo engine")
        try:
            if self._process.stdin:
                self._process.stdin.close()
            self._process.terminate()
            self._process.wait(timeout=5)
        except Exception as e:
            logger.warning(f"Error during shutdown: {e}")
            self._process.kill()
        finally:
            self._process = None
            # Wait for stderr drain thread to finish (it will exit on EOF)
            if self._stderr_thread is not None:
                self._stderr_thread.join(timeout=2)
                self._stderr_thread = None
        logger.info("KataGo engine stopped")

    async def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """Send an analysis request and wait for the response."""
        if self._process is None:
            raise RuntimeError("Engine not started. Call start() first.")

        # Use threading.Lock so this works across event loops (e.g. when
        # SyncEngineAdapter.query() calls asyncio.run() in a worker thread).
        # The blocking _read_response() call holds the lock until KataGo
        # responds, which is acceptable for this single-user tool.
        with self._lock:
            # Guard: check the process hasn't died since startup
            if self._process.poll() is not None:
                stderr_tail = "\n".join(self._stderr_lines[-10:])
                raise RuntimeError(
                    f"KataGo process has exited (rc={self._process.returncode}). "
                    f"Last stderr:\n{stderr_tail}"
                )

            self._request_counter += 1
            request.request_id = f"req_{self._request_counter:04d}"

            payload = request.to_katago_json()
            payload_str = json.dumps(payload) + "\n"

            # P3.9: Compact summary log (Plan 010, D45)
            stone_count = len(payload.get("initialStones", []))
            board_x = payload.get("boardXSize", 0)
            max_v = payload.get("maxVisits", 0)
            allow_moves = payload.get("allowMoves", [])
            allow_count = len(allow_moves[0]["moves"]) if allow_moves else 0
            logger.info(
                "Sending request %s: board=%dx%d, stones=%d, visits=%d, "
                "initialPlayer=%s, allowMoves_count=%d, rules=%s",
                request.request_id, board_x, board_x, stone_count, max_v,
                payload.get("initialPlayer", "?"), allow_count,
                payload.get("rules", "?"),
            )

            # Send request
            assert self._process.stdin is not None
            self._process.stdin.write(payload_str)
            self._process.stdin.flush()

            # Read response (blocking — serialized by threading lock)
            response_line = self._read_response(request.request_id)

        if response_line is None:
            raise RuntimeError("No response from KataGo engine")

        data = json.loads(response_line)

        # Log raw KataGo response summary for diagnostics
        move_count = len(data.get("moveInfos", []))
        root_info = data.get("rootInfo", {})
        logger.info(
            "KataGo response %s: moveInfos=%d, rootInfo.visits=%d, "
            "rootInfo.winrate=%.4f, rootInfo.scoreLead=%.2f",
            data.get("id", "?"), move_count,
            root_info.get("visits", 0),
            root_info.get("winrate", -1),
            root_info.get("scoreLead", 0),
        )
        if move_count == 0:
            logger.warning(
                "KataGo returned 0 moveInfos! Raw response (truncated): %s",
                response_line[:2000],
            )

        # Check for error
        if "error" in data:
            raise RuntimeError(f"KataGo error: {data['error']}")

        return AnalysisResponse.from_katago_json(data)

    def _read_response(self, expected_id: str) -> str | None:
        """Read lines from stdout until we find our response.

        KataGo may output responses out of order if multiple requests
        are in flight. We read line by line, looking for our ID.
        """
        if self._process is None or self._process.stdout is None:
            return None

        # Read up to 100 lines looking for our response
        for _ in range(100):
            line = self._process.stdout.readline()
            if not line:
                return None  # EOF

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                if data.get("id") == expected_id:
                    # KataGo may emit per-request warning JSON before the
                    # actual analysis response.  These have our ID but
                    # contain "warning" + "field" instead of moveInfos.
                    # Log the warning and keep reading for the real response.
                    if "warning" in data and "moveInfos" not in data:
                        logger.warning(
                            "KataGo field warning for %s: field=%s — %s",
                            expected_id,
                            data.get("field", "?"),
                            data.get("warning", "")[:200],
                        )
                        continue
                    return line
                # Not our response — could be from a previous request; skip
                logger.debug(f"Skipping response for {data.get('id')}")
            except json.JSONDecodeError:
                # Might be a log line from KataGo, skip
                logger.debug(f"Non-JSON line from KataGo: {line[:100]}")
                continue

        return None

    def _drain_stderr(self) -> None:
        """Continuously read stderr to prevent pipe buffer deadlock.

        Called in a daemon thread. Logs each line and keeps the last
        N lines for diagnostics. Exits when the subprocess closes stderr
        (i.e. process terminates).
        """
        max_lines = 200
        try:
            proc = self._process
            if proc is None or proc.stderr is None:
                return
            for line in proc.stderr:
                text = line.rstrip()
                if text:
                    logger.debug(f"KataGo log: {text}")
                    self._stderr_lines.append(text)
                    if len(self._stderr_lines) > max_lines:
                        self._stderr_lines.pop(0)
        except (ValueError, OSError):
            # Pipe closed during shutdown — expected
            pass

    async def wait_for_ready(self, timeout: float = 60.0) -> bool:
        """Wait until KataGo has loaded and is ready to accept queries.

        Sends a minimal probe query and waits for a response. This blocks
        until KataGo finishes initialization (model loading, OpenCL compile).

        Args:
            timeout: Maximum seconds to wait for readiness.

        Returns:
            True if engine is ready, False if timed out.

        Raises:
            RuntimeError: If engine is not started.
        """
        if self._process is None:
            raise RuntimeError("Engine not started. Call start() first.")

        probe = {
            "id": "probe_ready",
            "initialStones": [],
            "moves": [],
            "rules": "chinese",
            "komi": 7.5,
            "boardXSize": 9,
            "boardYSize": 9,
            "analyzeTurns": [0],
            "maxVisits": 1,
        }

        assert self._process.stdin is not None
        self._process.stdin.write(json.dumps(probe) + "\n")
        self._process.stdin.flush()

        # Wait for response with timeout
        try:
            loop = asyncio.get_running_loop()
            response_line = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._read_response, "probe_ready"
                ),
                timeout=timeout,
            )
            return response_line is not None
        except TimeoutError:
            logger.warning(f"Engine readiness probe timed out after {timeout}s")
            return False

    async def health(self) -> dict:
        """Check engine health."""
        running = self._process is not None and self._process.poll() is None
        model_name = Path(self.config.model_path).name if self.config.model_path else "not configured"
        model_exists = Path(self.config.model_path).exists() if self.config.model_path else False

        status = "ready" if running else "stopped"
        issues = []
        if not model_exists:
            issues.append(f"model file not found: {model_name}")
        if not running:
            issues.append("KataGo process not running")

        return {
            "engine": "local",
            "status": status,
            "model": model_name,
            "model_exists": model_exists,
            "katago_path": self.config.katago_path,
            "issues": issues,
        }

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None
