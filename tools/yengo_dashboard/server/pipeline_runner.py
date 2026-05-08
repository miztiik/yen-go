"""Wrappers around ``python -m backend.puzzle_manager`` subprocess invocations.

Per principle #6, the cockpit never imports from ``backend/``. Anything that
requires pipeline domain logic (status interpretation, source resolution,
config loading, etc.) is delegated to the CLI via subprocess, and we parse the
machine-readable JSON it emits.

Cost note: a cold ``python -m backend.puzzle_manager source-status --json``
takes ~300–600 ms on a typical machine. Acceptable at the ~3 s poll cadence
documented in PLAN.md §6. If callers ever need finer cadence, the right answer
is "have the pipeline expose a polling daemon", not "reach into the SQLite
files from the cockpit".
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class PipelineCommandError(RuntimeError):
    """Raised when the puzzle_manager CLI exits non-zero or emits invalid JSON."""

    def __init__(self, command: list[str], returncode: int, stderr: str, stdout: str) -> None:
        super().__init__(
            f"command {command!r} failed: returncode={returncode}; "
            f"stderr={stderr.strip()[:200]!r}; stdout={stdout.strip()[:200]!r}"
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout


@dataclass(frozen=True)
class PipelineRunner:
    """Invokes the puzzle_manager CLI and parses ``--json`` output.

    Args:
        repo_root: Repository root containing ``backend/puzzle_manager``.
            Used both as the subprocess CWD and as ``PYTHONPATH``.
        config_dir: Optional config directory (passed to ``--config`` when set).
            When ``None``, the CLI uses its own default
            (``backend/puzzle_manager/config/``).
        python_executable: Interpreter to invoke. Defaults to ``sys.executable``
            so the cockpit always uses the same Python it was launched under.
        timeout_s: Subprocess timeout. Conservative default for read-only
            commands; set higher for long-running ones (not used in this read
            module).
    """

    repo_root: Path
    config_dir: Path | None = None
    python_executable: str = sys.executable
    timeout_s: float = 30.0

    def _base_cmd(self) -> list[str]:
        return [self.python_executable, "-m", "backend.puzzle_manager"]

    def _run_json(self, subcommand: list[str]) -> dict:
        # ``--json`` is the conventional flag for the puzzle_manager CLI's
        # subcommands that have a structured-output mode. ``--config`` is a
        # top-level argparse flag and lives at the front of the command line
        # (handled by ``_run_json_from_args``).
        return self._run_json_from_args([*subcommand, "--json"])

    def _env(self) -> dict[str, str]:
        import os

        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        repo = str(self.repo_root)
        if repo not in existing.split(os.pathsep):
            env["PYTHONPATH"] = (repo + os.pathsep + existing) if existing else repo
        # Force UTF-8 stdout in the child so a non-ASCII byte in CLI output
        # (e.g. a stray emoji) never crashes it on a cp1252 Windows console.
        # The cockpit side decodes with errors="replace" as belt-and-braces.
        env["PYTHONIOENCODING"] = "utf-8"
        return env

    def source_status(self) -> dict:
        """Wraps ``puzzle_manager source-status --json``.

        Returns the parsed JSON ``{"sources": [...]}`` as-is; the cockpit does
        not transform field names or values.
        """
        return self._run_json(["source-status"])

    def lock_status(self) -> dict:
        """Wraps ``puzzle_manager config-lock status --json``.

        Returns the parsed JSON dict verbatim. Schema is owned by the CLI;
        currently ``{"locked": bool, ...}``.
        """
        return self._run_json(["config-lock", "status"])

    def clean_preview(
        self,
        *,
        target: str | None = None,
        retention_days: int | None = None,
    ) -> dict:
        """Wraps ``puzzle_manager clean --dry-run --json``.

        Returns the parsed CleanPreview JSON. Schema is owned by the CLI
        (``backend.puzzle_manager.models.previews.CleanPreview``); the
        cockpit forwards the dict verbatim per principle #6.
        """
        args = ["clean", "--dry-run", "--json"]
        if target is not None:
            args += ["--target", target]
        if retention_days is not None:
            args += ["--retention-days", str(retention_days)]
        return self._run_json_from_args(args)

    def rollback_preview(self, *, run_id: str, reason: str) -> dict:
        """Wraps ``puzzle_manager rollback --dry-run --json``.

        Returns the parsed RollbackPreview JSON. ``reason`` is required
        by the CLI even in preview mode (it pre-validates the audit
        message that the real run will use).
        """
        args = [
            "rollback",
            "--dry-run",
            "--json",
            "--run-id", run_id,
            "--reason", reason,
        ]
        return self._run_json_from_args(args)

    def vacuum_db_preview(self, *, rebuild: bool = False) -> dict:
        """Wraps ``puzzle_manager vacuum-db --dry-run --json``.

        Returns the parsed VacuumDbPreview JSON.
        """
        args = ["vacuum-db", "--dry-run", "--json"]
        if rebuild:
            args.append("--rebuild")
        return self._run_json_from_args(args)

    def lock_release(self, *, force: bool = False) -> dict:
        """Wraps ``puzzle_manager config-lock release [--force]``.

        The CLI does not emit JSON on release — it prints a human line and
        exits 0 on success or non-zero on failure. We surface the raw output
        so the cockpit doesn't reinterpret it.

        Returns ``{"ok": bool, "returncode": int, "stdout": str, "stderr": str}``.
        Never raises ``PipelineCommandError`` — release failure is a
        legitimate outcome the UI must show, not a 502.
        """
        args = ["config-lock", "release"]
        if force:
            args.append("--force")
        return self._run_capture(args)

    def _run_capture(self, subcommand: list[str]) -> dict:
        """Generic short-CLI invocation that captures all output.

        Like ``lock_release``: never raises on non-zero exit, returns the
        ``{ok, returncode, stdout, stderr}`` shape the cockpit forwards.
        """
        cmd = self._base_cmd()
        if self.config_dir is not None:
            cmd += ["--config", str(self.config_dir)]
        cmd += subcommand
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_s,
            env=self._env(),
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def enable_adapter(self, adapter_id: str, *, force: bool = False) -> dict:
        """Wraps ``puzzle_manager enable-adapter ADAPTER_ID [--force]``."""
        args = ["enable-adapter", adapter_id]
        if force:
            args.append("--force")
        return self._run_capture(args)

    def disable_adapter(self, *, force: bool = False) -> dict:
        """Wraps ``puzzle_manager disable-adapter [--force]``."""
        args = ["disable-adapter"]
        if force:
            args.append("--force")
        return self._run_capture(args)

    def publish_log_search(self, params: dict) -> dict:
        """Wraps ``puzzle_manager publish-log search --json …``.

        ``params`` keys map 1:1 to CLI flags after the ``--`` prefix. None /
        empty values are skipped. The CLI rejects calls with no filter, so
        the cockpit forwards that error verbatim via ``PipelineCommandError``.
        """
        args = ["publish-log", "search", "--format", "json"]
        for key, val in params.items():
            if val is None or val == "" or val == []:
                continue
            flag = f"--{key.replace('_', '-')}"
            if isinstance(val, list):
                args.append(flag)
                args.extend(str(v) for v in val)
            elif isinstance(val, bool):
                if val:
                    args.append(flag)
            else:
                args += [flag, str(val)]
        return self._run_json_from_args(args)

    def logs_grep(
        self,
        *,
        pattern: str,
        stage: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int | None = None,
    ) -> list:
        """Wraps ``puzzle_manager logs grep --json …``.

        Returns the parsed JSON list verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.logs.LogsGrepHit``); the cockpit
        forwards the items unchanged per principle #6.
        """
        args = ["logs", "grep", "--json"]
        if stage:
            args += ["--stage", stage]
        if from_date:
            args += ["--from", from_date]
        if to_date:
            args += ["--to", to_date]
        if limit is not None:
            args += ["--limit", str(limit)]
        # PATTERN is positional and must come after the flags so argparse
        # doesn't try to consume the following value as another flag arg.
        args.append(pattern)
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def failures_summary(self, *, last: int = 10) -> list:
        """Wraps ``puzzle_manager status --failures-summary --last N --json``.

        Returns the parsed JSON list verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.failures.FailureGroup``); the cockpit
        forwards the items unchanged per principle #6.
        """
        args = ["status", "--failures-summary", "--last", str(last), "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def runtime_info(self) -> dict:
        """Wraps ``puzzle_manager runtime-info --json``.

        Returns the parsed JSON dict verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.runtime_info.RuntimeInfo``); the
        cockpit forwards fields unchanged per principle #6.
        """
        args = ["runtime-info", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def ops_catalog(self) -> list:
        """Wraps ``puzzle_manager ops catalog --json`` (Theme 16a).

        Returns the parsed JSON list verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.ops_catalog.OpsCatalogEntry``); the
        cockpit forwards rows unchanged so a backend-only edit can re-classify
        a button's blast-radius without a coordinated cockpit release.
        """
        args = ["ops", "catalog", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def tags_list(self, *, with_usage: bool = True) -> list:
        """Wraps ``puzzle_manager tags list [--with-usage] --json`` (Theme 5).

        Returns the parsed JSON list verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.taxonomy.TagUsageEntry``); the
        cockpit forwards rows unchanged per principle #6.
        """
        args = ["tags", "list", "--json"]
        if with_usage:
            args.append("--with-usage")
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def levels_list(self, *, with_usage: bool = True) -> list:
        """Wraps ``puzzle_manager levels list [--with-usage] --json`` (Theme 5)."""
        args = ["levels", "list", "--json"]
        if with_usage:
            args.append("--with-usage")
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def source_details(self, source_id: str) -> dict:
        """Wraps ``puzzle_manager source-status --source ID --details --json`` (Theme 6a).

        Returns the parsed JSON dict verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.source_details.SourceDetails``);
        the cockpit forwards it unchanged per principle #6.
        """
        args = ["source-status", "--source", source_id, "--details", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def source_ingest_state(self, source_id: str) -> dict:
        """Theme 6b: wraps ``source-ingest-state ID --json`` (read-only).

        CLI returncode 2 (unknown source / no path) surfaces as
        :class:`PipelineCommandError` so the route layer can map it to 400.
        """
        args = ["source-ingest-state", source_id, "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def source_ingest_state_reset_preview(self, source_id: str) -> dict:
        """Theme 6b: wraps ``source-ingest-state ID --reset --dry-run --json``."""
        args = ["source-ingest-state", source_id, "--reset", "--dry-run", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def source_ingest_state_reset_apply(self, source_id: str) -> dict:
        """Theme 6b: wraps ``source-ingest-state ID --reset --json`` (apply path)."""
        args = ["source-ingest-state", source_id, "--reset", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def adapter_config_list(self) -> dict:
        """Theme 7a: wraps ``adapter-config list --json``."""
        args = ["adapter-config", "list", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def adapter_config_show(self, source_id: str) -> dict:
        """Theme 7a: wraps ``adapter-config show ID --json``."""
        args = ["adapter-config", "show", source_id, "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def adapter_config_validate_all(self) -> dict:
        """Theme 7a: wraps ``adapter-config validate-all --json``."""
        args = ["adapter-config", "validate-all", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def adapter_config_add(
        self, *, source_id: str, name: str, adapter: str, config: dict,
    ) -> dict:
        """Theme 7b: wraps ``adapter-config add --json``."""
        args = [
            "adapter-config", "add",
            "--id", source_id, "--name", name, "--adapter", adapter,
            "--config-json", json.dumps(config or {}),
            "--json",
        ]
        return self._run_json_any(args)

    def adapter_config_clone(
        self, *, source_id: str, new_id: str, new_name: str,
    ) -> dict:
        """Theme 7b: wraps ``adapter-config clone --json``."""
        args = [
            "adapter-config", "clone", source_id,
            "--new-id", new_id, "--new-name", new_name, "--json",
        ]
        return self._run_json_any(args)

    def adapter_config_update(
        self, *, source_id: str, set_pairs: list[str], name: str | None = None,
    ) -> dict:
        """Theme 7b: wraps ``adapter-config update --json``."""
        args = ["adapter-config", "update", source_id, "--json"]
        for pair in set_pairs:
            args.extend(["--set", pair])
        if name is not None:
            args.extend(["--name", name])
        return self._run_json_any(args)

    def adapter_config_remove(
        self, *, source_id: str, force: bool = False,
    ) -> dict:
        """Theme 7b: wraps ``adapter-config remove --json``."""
        args = ["adapter-config", "remove", source_id, "--json"]
        if force:
            args.append("--force")
        return self._run_json_any(args)

    def pipeline_config_show(self) -> dict:
        """Theme 7d: wraps ``pipeline-config show --json``."""
        args = ["pipeline-config", "show", "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def daily_list(
        self, *, from_date: str | None = None, to_date: str | None = None,
    ) -> dict:
        """Theme 8a: wraps ``daily-list --json``."""
        args = ["daily-list", "--json"]
        if from_date:
            args += ["--from", from_date]
        if to_date:
            args += ["--to", to_date]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def daily_status(
        self, *, window_days: int = 30, stale_days: int = 14,
    ) -> dict:
        """Theme 8a: wraps ``daily-status --json``."""
        args = [
            "daily-status", "--json",
            "--window-days", str(window_days),
            "--stale-days", str(stale_days),
        ]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def daily_preview(self, *, date: str) -> dict:
        """Theme 8b: wraps ``daily-preview --date DATE --json`` (read-only)."""
        args = ["daily-preview", "--date", date, "--json"]
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def daily_cancel(
        self, *, date: str | None = None,
        from_date: str | None = None, to_date: str | None = None,
        dry_run: bool = True, force: bool = False,
    ) -> dict:
        """Theme 8c: wraps ``daily-cancel ... --json`` (preview + apply)."""
        args = ["daily-cancel", "--json"]
        if date:
            args += ["--date", date]
        if from_date:
            args += ["--from", from_date]
        if to_date:
            args += ["--to", to_date]
        if dry_run:
            args.append("--dry-run")
        if force:
            args.append("--force")
        result = self._run_json_any(args)
        if not isinstance(result, dict):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON object, got {type(result).__name__}", "",
            )
        return result

    def pipeline_config_set(
        self, *, set_pairs: list[str], force: bool = False,
    ) -> dict:
        """Theme 7d: wraps ``pipeline-config set --json``."""
        args = ["pipeline-config", "set", "--json"]
        for pair in set_pairs:
            args.extend(["--set", pair])
        if force:
            args.append("--force")
        return self._run_json_any(args)

    def adapter_config_bootstrap(
        self, *, from_folder: str, adapter: str = "local",
        id_prefix: str = "", dry_run: bool = True,
    ) -> dict:
        """Theme 7c: wraps ``adapter-config bootstrap --json``."""
        args = [
            "adapter-config", "bootstrap",
            "--from-folder", from_folder,
            "--adapter", adapter,
            "--id-prefix", id_prefix,
            "--json",
        ]
        if dry_run:
            args.append("--dry-run")
        return self._run_json_any(args)

    def activity(
        self,
        *,
        from_ts: str | None = None,
        to_ts: str | None = None,
        kinds: list[str] | None = None,
        limit: int = 100,
    ) -> list:
        """Wraps ``puzzle_manager activity --json``.

        Returns the parsed JSON list verbatim. Schema is owned by the CLI
        (``backend.puzzle_manager.models.activity.ActivityEvent``); the
        cockpit forwards items unchanged per principle #6.
        """
        args = ["activity", "--json", "--limit", str(limit)]
        if from_ts:
            args += ["--from", from_ts]
        if to_ts:
            args += ["--to", to_ts]
        if kinds:
            args += ["--kinds", ",".join(kinds)]
        result = self._run_json_any(args)
        if not isinstance(result, list):
            raise PipelineCommandError(
                self._base_cmd() + args, 0,
                f"expected JSON list, got {type(result).__name__}", "",
            )
        return result

    def inventory_check(self) -> dict:
        """Wraps ``puzzle_manager inventory --check --json``.

        Returns the parsed ``IntegrityReport`` JSON dict verbatim. Schema is
        owned by the CLI (``backend.puzzle_manager.models.integrity``); the
        cockpit forwards fields unchanged per principle #6.

        Exit-code nuance: the CLI exits 1 when issues exist (matches the
        pre-Theme-14a human-output behavior). That is a *valid* report — not
        a crash — so we tolerate returncode 0 *and* 1 as long as stdout parses
        as JSON. Any other returncode, or unparseable stdout, raises.
        """
        args = ["inventory", "--check", "--json"]
        cmd = self._base_cmd()
        if self.config_dir is not None:
            cmd += ["--config", str(self.config_dir)]
        cmd += args
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_s,
            env=self._env(),
        )
        if result.returncode not in (0, 1):
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout) from exc
        if not isinstance(payload, dict):
            raise PipelineCommandError(
                cmd, result.returncode,
                f"expected JSON object, got {type(payload).__name__}", result.stdout,
            )
        return payload

    def inventory_mutation_preview(self, op: str) -> dict:
        """Wraps ``puzzle_manager inventory --{op} --dry-run --json`` (Theme 14c1).

        ``op`` must be one of ``rebuild``/``reconcile``/``fix``. Returns the
        parsed ``InventoryMutationPreview`` dict verbatim.
        """
        if op not in ("rebuild", "reconcile", "fix"):
            raise ValueError(f"unknown inventory op: {op!r}")
        return self._run_inventory_json(["inventory", f"--{op}", "--dry-run", "--json"])

    def inventory_mutation_apply(self, op: str) -> dict:
        """Wraps ``puzzle_manager inventory --{op} --json`` (Theme 14c2).

        ``op`` must be one of ``rebuild``/``reconcile``/``fix``. Returns the
        parsed ``InventoryMutationResult`` dict verbatim. Tolerates rc=1 from
        ``--fix`` when post-fix issues remain (still a valid result row).
        """
        if op not in ("rebuild", "reconcile", "fix"):
            raise ValueError(f"unknown inventory op: {op!r}")
        return self._run_inventory_json(["inventory", f"--{op}", "--json"])

    def _run_inventory_json(self, args: list[str]) -> dict:
        """Subprocess wrapper shared by inventory_check / preview / apply.

        Tolerates rc=0 *and* rc=1 — for ``--check`` and ``--fix`` rc=1 means
        "issues present" rather than crash. Any other rc, or unparseable
        stdout, raises ``PipelineCommandError``.
        """
        cmd = self._base_cmd()
        if self.config_dir is not None:
            cmd += ["--config", str(self.config_dir)]
        cmd += args
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_s,
            env=self._env(),
        )
        if result.returncode not in (0, 1):
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout)
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout) from exc
        if not isinstance(payload, dict):
            raise PipelineCommandError(
                cmd, result.returncode,
                f"expected JSON object, got {type(payload).__name__}", result.stdout,
            )
        return payload

    def _run_json_any(self, subcommand: list[str]) -> object:
        """Like ``_run_json_from_args`` but returns parsed JSON of any type
        (list or dict). Used by subcommands whose JSON output is a bare list."""
        cmd = self._base_cmd()
        if self.config_dir is not None:
            cmd += ["--config", str(self.config_dir)]
        cmd += subcommand
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_s,
            env=self._env(),
        )
        if result.returncode != 0:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout) from exc

    def _run_json_from_args(self, subcommand: list[str]) -> dict:
        """Like ``_run_json`` but does not append ``--json`` (caller has already
        chosen the format flag). Used by subcommands whose JSON flag is
        non-standard, e.g. ``publish-log search --format json``."""
        cmd = self._base_cmd()
        if self.config_dir is not None:
            cmd += ["--config", str(self.config_dir)]
        cmd += subcommand
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_s,
            env=self._env(),
        )
        if result.returncode != 0:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout)
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise PipelineCommandError(cmd, result.returncode, result.stderr, result.stdout) from exc
