"""Configure pytest for t-dragon tests.

This conftest handles the import issues caused by the hyphenated directory name.
"""

import sys
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import modules using importlib due to the hyphen in directory name
import importlib.util


def _load_module_from_path(name: str, path: Path):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Pre-load the modules we need for tests
T_DRAGON_DIR = Path(__file__).parent.parent

# Load logging_config module
logging_config = _load_module_from_path(
    "t_dragon_logging_config",
    T_DRAGON_DIR / "logging_config.py"
)

# We can't easily load orchestrator because it has many dependencies
# that also need to be loaded. For DownloadStats tests, we'll define
# a minimal version in the test file itself.
