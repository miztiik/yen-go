"""Allow running as ``python -m tools.tasuki``."""

import sys

from tools.tasuki.extract import main

sys.exit(main())
