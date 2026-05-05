"""Entry point: ``python -m tools.pm_cockpit``."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from tools.pm_cockpit import __version__
from tools.pm_cockpit.server.app import create_app


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tools.pm_cockpit",
        description="Localhost browser UI for backend.puzzle_manager.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8201, help="Bind port (default: 8201)")
    parser.add_argument("--version", action="version", version=f"pm_cockpit {__version__}")
    args = parser.parse_args(argv)

    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
