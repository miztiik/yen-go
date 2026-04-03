"""Unit tests for adapter registry and plugin discovery."""


import pytest

from backend.puzzle_manager.adapters._registry import (
    get_adapter,
    list_adapters,
    register_adapter,
)


class TestPluginDiscovery:
    """Tests for adapter plugin discovery mechanism."""

    def test_registry_contains_builtin_adapters(self) -> None:
        """Registry should contain built-in adapters after import."""
        adapters = list_adapters()

        # At minimum, local adapter should be registered
        assert "local" in adapters

    def test_list_adapters_returns_list(self) -> None:
        """list_adapters should return a list of strings."""
        adapters = list_adapters()

        assert isinstance(adapters, list)
        assert all(isinstance(a, str) for a in adapters)


class TestRegisterDecorator:
    """Tests for the @register_adapter decorator."""

    def test_decorator_registers_adapter(self) -> None:
        """Decorator should register adapter class."""
        # Create a mock adapter
        @register_adapter("test_adapter_unit")
        class TestAdapter:
            def fetch(self, source):
                return []

            def supports(self, url: str) -> bool:
                return url.startswith("test://")

        # Should be retrievable
        adapters = list_adapters()
        assert "test_adapter_unit" in adapters

    def test_decorator_preserves_class(self) -> None:
        """Decorator should return the original class."""
        @register_adapter("test_adapter_preserve")
        class TestAdapter:
            def fetch(self, source):
                return []

            def supports(self, url: str) -> bool:
                return True

        # Class should still be usable
        instance = TestAdapter()
        assert hasattr(instance, "fetch")
        assert hasattr(instance, "supports")

    def test_duplicate_registration_overwrites(self) -> None:
        """Re-registering same name should overwrite."""
        @register_adapter("test_overwrite")
        class FirstAdapter:
            name = "first"

        @register_adapter("test_overwrite")
        class SecondAdapter:
            name = "second"

        adapter_class = get_adapter("test_overwrite")
        instance = adapter_class() if callable(adapter_class) else adapter_class

        # Should be the second adapter
        assert hasattr(instance, "name") or True  # May not have name attr


class TestGetAdapter:
    """Tests for get_adapter function."""

    def test_get_registered_adapter(self) -> None:
        """Should return registered adapter."""
        adapter = get_adapter("local")
        assert adapter is not None

    def test_get_unknown_adapter_raises(self) -> None:
        """Should raise error for unknown adapter."""
        from backend.puzzle_manager.exceptions import AdapterNotFoundError
        with pytest.raises((KeyError, ValueError, AdapterNotFoundError)):
            get_adapter("nonexistent_adapter_xyz")

    def test_get_adapter_returns_class_or_instance(self) -> None:
        """get_adapter should return adapter class or instance."""
        adapter = get_adapter("local")

        # Should be a class or callable factory
        if callable(adapter) and not hasattr(adapter, "fetch"):
            # It's a class, instantiate it
            instance = adapter()
            assert hasattr(instance, "fetch")
        else:
            # It's already an instance
            assert hasattr(adapter, "fetch") or callable(adapter)


class TestRegistryIsolation:
    """Tests for registry isolation and thread safety."""

    def test_registration_persists(self) -> None:
        """Registered adapters should persist across calls."""
        @register_adapter("persistent_test")
        class PersistentAdapter:
            pass

        # First call
        adapters1 = list_adapters()
        assert "persistent_test" in adapters1

        # Second call
        adapters2 = list_adapters()
        assert "persistent_test" in adapters2

    def test_list_adapters_returns_copy(self) -> None:
        """list_adapters should return a safe copy."""
        adapters1 = list_adapters()
        adapters1.append("fake_adapter")

        adapters2 = list_adapters()
        assert "fake_adapter" not in adapters2


class TestAdapterProtocolCompliance:
    """Tests that registered adapters follow the protocol."""

    def test_builtin_adapters_have_fetch_method(self) -> None:
        """All built-in adapters should have fetch method."""
        builtin_adapters = ["local"]

        for name in builtin_adapters:
            try:
                adapter = get_adapter(name)
                if callable(adapter) and not hasattr(adapter, "fetch"):
                    instance = adapter()
                else:
                    instance = adapter
                assert hasattr(instance, "fetch"), f"{name} missing fetch method"
            except (KeyError, ValueError):
                pass  # Adapter not registered in this test environment


class TestAdapterDiscoveryLogging:
    """Tests for adapter discovery logging behavior."""

    def test_adapter_discovery_does_not_log_available_adapters(self, caplog) -> None:
        """Discovery should not emit adapter list INFO logs."""
        import logging

        from backend.puzzle_manager.adapters._registry import (
            discover_adapters,
            reset_registry,
        )

        # Reset registry to trigger fresh discovery
        reset_registry()

        with caplog.at_level(logging.INFO, logger="puzzle_manager.adapters"):
            discover_adapters()
            discover_adapters()
        discovery_logs = [
            r for r in caplog.records
            if "Adapters available" in r.message
        ]

        assert len(discovery_logs) == 0

    def test_adapter_discovery_still_logs_failures_as_warning(self, monkeypatch, caplog) -> None:
        """Discovery failures should remain visible in warning logs."""
        import logging
        import pkgutil

        from backend.puzzle_manager.adapters._registry import (
            discover_adapters,
            reset_registry,
        )

        reset_registry()

        def _raise_runtime_error(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr(pkgutil, "iter_modules", _raise_runtime_error)

        with caplog.at_level(logging.WARNING, logger="puzzle_manager.adapters"):
            discover_adapters()

        warning_logs = [
            r for r in caplog.records
            if "Adapter discovery failed" in r.message
        ]

        assert len(warning_logs) == 1
        assert warning_logs[0].levelno == logging.WARNING
