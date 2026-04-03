"""Pytest configuration for tools/puzzle_intent tests.

Provides lazy skip handling for sentence-transformers dependencies so
pytest collection does not trigger PyTorch loading (~12s).

The key pattern: sentence_transformers is only imported inside
pytest_runtest_setup (called at test execution time, not collection time).
This means --collect-only and test collection are instant for this module.
"""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "requires_semantic: tests requiring sentence-transformers (PyTorch); "
        "automatically skipped if not installed",
    )


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip requires_semantic tests at RUN time (not collection time).

    Deferring the import to run time means collection stays fast —
    sentence-transformers/PyTorch is only loaded when a test is actually
    about to execute, not when the test module is imported by pytest.
    """
    if "requires_semantic" in item.keywords:
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            pytest.skip("sentence-transformers not installed")
