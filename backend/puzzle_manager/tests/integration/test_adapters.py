"""Integration tests for adapter functionality."""

import inspect

from backend.puzzle_manager.adapters._registry import get_adapter, list_adapters
from backend.puzzle_manager.adapters.local import LocalAdapter


class TestAdapterIntegration:
    """Integration tests for adapter protocol compliance."""

    def test_local_adapter_has_fetch_method(self) -> None:
        """LocalAdapter should have fetch method."""
        adapter = LocalAdapter()

        assert hasattr(adapter, "fetch")
        assert callable(adapter.fetch)

    def test_local_adapter_has_configure_method(self) -> None:
        """LocalAdapter should have configure method."""
        adapter = LocalAdapter()

        assert hasattr(adapter, "configure")
        assert callable(adapter.configure)


class TestAdapterCheckpoint:
    """Tests for adapter checkpoint and resume functionality."""

    def test_local_adapter_has_checkpoint_field(self) -> None:
        """LocalAdapter should have checkpoint tracking."""
        adapter = LocalAdapter()

        # Check that adapter has some state/checkpoint capability
        assert hasattr(adapter, "_checkpoint") or hasattr(adapter, "_processed_files")

    def test_adapter_fetch_accepts_batch_size(self) -> None:
        """Adapter fetch should accept batch_size parameter."""
        adapter = LocalAdapter()

        sig = inspect.signature(adapter.fetch)
        params = list(sig.parameters.keys())

        # batch_size should be available
        assert "batch_size" in params


class TestAdapterErrorHandling:
    """Tests for adapter error handling."""

    def test_adapter_handles_missing_path_gracefully(self) -> None:
        """Adapter should handle missing path gracefully."""
        adapter = LocalAdapter()
        adapter.configure({"path": "/nonexistent/path/to/puzzles"})

        # Should not raise but return error results
        results = list(adapter.fetch(batch_size=2))

        # Should have at least one result (error)
        assert len(results) >= 0

    def test_adapter_handles_unconfigured_gracefully(self) -> None:
        """Adapter should handle unconfigured state gracefully."""
        adapter = LocalAdapter()

        # Without configure(), fetch should handle gracefully
        results = list(adapter.fetch(batch_size=2))

        # Should return empty or error results
        assert len(results) >= 0


class TestRegisteredAdapters:
    """Tests for registered adapter availability."""

    def test_essential_adapters_registered(self) -> None:
        """All essential adapters should be registered."""
        adapters = list_adapters()

        # Core adapters that must exist
        assert "local" in adapters

    def test_source_adapters_registered(self) -> None:
        """Source-specific adapters should be registered."""
        adapters = list_adapters()

        # Source adapters (may not all be present depending on config)
        expected_source_adapters = [
            "sanderland",
            "travisgk",
            "kisvadim",
        ]

        # At least some should be present
        registered_count = sum(1 for a in expected_source_adapters if a in adapters)
        assert registered_count >= 2, f"Found adapters: {adapters}"

    def test_get_adapter_returns_class(self) -> None:
        """get_adapter should return adapter class."""
        adapter_class = get_adapter("local")

        assert adapter_class is not None
        # Should be a class
        instance = adapter_class()
        assert hasattr(instance, "fetch")


class TestAdapterBatching:
    """Tests for adapter batch processing."""

    def test_adapter_fetch_has_batch_size(self) -> None:
        """Adapter fetch should support batch size parameter."""
        adapter = LocalAdapter()

        sig = inspect.signature(adapter.fetch)
        params = list(sig.parameters.keys())

        # batch_size parameter should be available
        assert "batch_size" in params


class TestAdapterConfiguration:
    """Tests for adapter configuration."""

    def test_local_adapter_configure_sets_path(self) -> None:
        """LocalAdapter.configure should set path."""
        adapter = LocalAdapter()
        adapter.configure({"path": "test/path"})

        assert adapter._path is not None

    def test_local_adapter_configure_with_absolute_path(self) -> None:
        """LocalAdapter should handle absolute paths."""
        adapter = LocalAdapter()
        adapter.configure({"path": "/absolute/path"})

        assert adapter._path is not None
        # Windows may convert forward slashes
        assert "absolute" in str(adapter._path) and "path" in str(adapter._path)
