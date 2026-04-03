"""Unit tests for config loader module."""


from backend.puzzle_manager.config.loader import ConfigLoader


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
