"""
Unit tests configuration.

All tests in this directory are automatically marked with @pytest.mark.unit.
This enables explicit selection with `pytest -m unit` for fast isolated tests.

Unit tests should:
- Test a single function, class, or module in isolation
- Not require external resources (filesystem I/O, network, subprocess)
- Use mocks for dependencies
- Execute in < 100ms each

Commands:
    pytest -m unit                 # Run only unit tests (~20s)
    pytest -m "unit and not slow"  # Skip slow unit tests
    pytest tests/unit/             # Run all tests in this directory
"""

import pytest


def pytest_collection_modifyitems(items):
    """Auto-apply unit marker to all tests in this directory."""
    for item in items:
        # Only mark items in this directory (tests/unit/)
        if "/unit/" in str(item.fspath) or "\\unit\\" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
