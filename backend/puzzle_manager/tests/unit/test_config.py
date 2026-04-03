"""Unit tests for config loader module."""


import pytest

from backend.puzzle_manager.config.loader import ConfigLoader
from backend.puzzle_manager.models.config import PipelineConfig


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_loader_creates(self) -> None:
        """Loader should be creatable."""
        loader = ConfigLoader()
        assert loader is not None

    def test_load_pipeline_config(self) -> None:
        """Loader should load pipeline config."""
        loader = ConfigLoader()
        config = loader.load_pipeline_config()

        assert config is not None

    def test_load_sources(self) -> None:
        """Loader should load sources config."""
        loader = ConfigLoader()
        sources = loader.load_sources()

        assert sources is not None
        assert isinstance(sources, list)


class TestConfigLoaderValidation:
    """Tests for config validation."""

    def test_pipeline_config_has_retention(self) -> None:
        """Config should have retention settings."""
        loader = ConfigLoader()
        config = loader.load_pipeline_config()

        assert hasattr(config, 'retention')

    def test_pipeline_config_has_batch(self) -> None:
        """Config should have batch settings."""
        loader = ConfigLoader()
        config = loader.load_pipeline_config()

        assert hasattr(config, 'batch')

    def test_pipeline_config_has_daily(self) -> None:
        """Config should have daily settings."""
        loader = ConfigLoader()
        config = loader.load_pipeline_config()

        assert hasattr(config, 'daily')


class TestPipelineConfigReconcileInterval:
    """Tests for PipelineConfig.reconcile_interval field."""

    def test_default_value(self) -> None:
        """Default reconcile_interval is 20."""
        config = PipelineConfig()
        assert config.reconcile_interval == 20

    def test_custom_value(self) -> None:
        """reconcile_interval can be set to a custom value."""
        config = PipelineConfig(reconcile_interval=50)
        assert config.reconcile_interval == 50

    def test_zero_disables(self) -> None:
        """reconcile_interval=0 is valid (disables periodic reconcile)."""
        config = PipelineConfig(reconcile_interval=0)
        assert config.reconcile_interval == 0

    def test_rejects_negative(self) -> None:
        """reconcile_interval rejects negative values."""
        with pytest.raises(Exception):
            PipelineConfig(reconcile_interval=-1)

    def test_rejects_above_max(self) -> None:
        """reconcile_interval rejects values above 1000."""
        with pytest.raises(Exception):
            PipelineConfig(reconcile_interval=1001)
