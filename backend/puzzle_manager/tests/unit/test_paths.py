"""Unit tests for paths module."""

from pathlib import Path

from backend.puzzle_manager.paths import (
    clear_cache,
    ensure_runtime_dirs,
    get_backend_dir,
    get_logs_dir,
    get_output_dir,
    get_pm_staging_dir,
    get_pm_state_dir,
    get_project_root,
    get_sgf_output_dir,
    get_views_dir,
)


class TestProjectRoot:
    """Tests for project root detection."""

    def test_get_project_root_returns_path(self) -> None:
        """Project root should be a valid Path."""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.exists()

    def test_project_root_is_directory(self) -> None:
        """Project root should be a directory."""
        root = get_project_root()
        assert root.is_dir()


class TestBackendDir:
    """Tests for backend directory."""

    def test_get_backend_dir_returns_path(self) -> None:
        """Backend dir should be a valid Path."""
        backend = get_backend_dir()
        assert isinstance(backend, Path)

    def test_backend_dir_is_under_project_root(self) -> None:
        """Backend dir should be under project root."""
        root = get_project_root()
        backend = get_backend_dir()
        assert str(backend).startswith(str(root))


class TestStateDir:
    """Tests for state directory."""

    def test_get_state_dir_default(self) -> None:
        """State dir should be .pm-runtime/state/."""
        state_dir = get_pm_state_dir()
        assert ".pm-runtime" in str(state_dir)
        assert state_dir.name == "state"

    def test_state_dir_is_absolute(self) -> None:
        """State dir should be an absolute path."""
        state_dir = get_pm_state_dir()
        assert state_dir.is_absolute()


class TestLogsDir:
    """Tests for logs directory."""

    def test_get_logs_dir_default(self) -> None:
        """Logs dir should be logs/."""
        logs_dir = get_logs_dir()
        assert "logs" in str(logs_dir)

    def test_logs_dir_is_absolute(self) -> None:
        """Logs dir should be an absolute path."""
        logs_dir = get_logs_dir()
        assert logs_dir.is_absolute()


class TestStagingDir:
    """Tests for staging directory."""

    def test_get_staging_dir_default(self) -> None:
        """Staging dir should be .pm-runtime/staging/."""
        staging_dir = get_pm_staging_dir()
        assert ".pm-runtime" in str(staging_dir)
        assert staging_dir.name == "staging"

    def test_staging_dir_is_absolute(self) -> None:
        """Staging dir should be an absolute path."""
        staging_dir = get_pm_staging_dir()
        assert staging_dir.is_absolute()


class TestOutputDir:
    """Tests for output directory."""

    def test_get_output_dir_default(self) -> None:
        """Output dir should be yengo-puzzle-collections/."""
        output_dir = get_output_dir()
        assert "yengo-puzzle-collections" in str(output_dir)

    def test_output_dir_is_absolute(self) -> None:
        """Output dir should be an absolute path."""
        output_dir = get_output_dir()
        assert output_dir.is_absolute()


class TestDerivedDirs:
    """Tests for derived directories."""

    def test_sgf_output_dir_under_output(self) -> None:
        """SGF dir should be under output dir."""
        output_dir = get_output_dir()
        sgf_dir = get_sgf_output_dir()
        assert str(sgf_dir).startswith(str(output_dir))

    def test_views_dir_under_output(self) -> None:
        """Views dir should be under output dir."""
        output_dir = get_output_dir()
        views_dir = get_views_dir()
        assert str(views_dir).startswith(str(output_dir))


class TestEnsureRuntimeDirs:
    """Tests for runtime directory creation."""

    def test_ensure_runtime_dirs_is_callable(self) -> None:
        """ensure_runtime_dirs should be callable."""
        assert callable(ensure_runtime_dirs)


class TestClearCache:
    """Tests for cache clearing."""

    def test_clear_cache_is_callable(self) -> None:
        """clear_cache should be callable."""
        assert callable(clear_cache)

    def test_clear_cache_runs_without_error(self) -> None:
        """clear_cache should run without error."""
        # Should not raise
        clear_cache()
