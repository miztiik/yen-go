"""Entry point for ``python -m tools.liryan1_tianlongtu``."""

import sys

from tools.liryan1_tianlongtu.tianlongtu_ingestor import main

sys.exit(main() or 0)
