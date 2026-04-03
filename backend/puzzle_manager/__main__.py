"""
Entry point for running puzzle_manager as a module.

Usage:
    python -m backend.puzzle_manager run
    python -m backend.puzzle_manager status
"""

import sys

from backend.puzzle_manager.cli import main

if __name__ == "__main__":
    sys.exit(main())
