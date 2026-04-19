"""One-shot generator for the in-notebook eval bundle setup cell."""
from pathlib import Path

scorers = Path('tools/yen_sei/eval/scorers.py').read_text(encoding='utf-8')
judges = Path('tools/yen_sei/eval/judges.py').read_text(encoding='utf-8')
runner = Path('tools/yen_sei/eval/runner.py').read_text(encoding='utf-8')

GO_CONST = '''"""Colab stub: only GO_TECHNIQUE_PATTERN is used by scorers.py."""
import re

GO_TECHNIQUES = frozenset({
    "net", "geta", "ladder", "shicho", "snapback", "ko", "seki",
    "tesuji", "life", "death", "kill", "capture", "connect", "cut",
    "eye", "liberty", "liberties", "atari", "shortage", "semeai",
    "throw-in", "squeeze", "placement", "hane", "descent", "clamp",
    "wedge", "peep", "bamboo", "tiger", "empty triangle", "ponnuki",
    "alive", "dead", "unconditionally", "approach", "invasion",
    "shape", "joseki", "proverb", "sacrifice", "damezumari",
    "nakade", "bent four", "bulky five", "rabbity six",
    "false eye", "double atari", "under the stones",
})

GO_TECHNIQUE_PATTERN = re.compile(
    r"\\b(" + "|".join(re.escape(t) for t in sorted(GO_TECHNIQUES, key=len, reverse=True)) + r")\\b",
    re.IGNORECASE,
)
'''

# Verify safe to wrap with r'''...'''
for name, src in [('scorers', scorers), ('judges', judges), ('runner', runner), ('GO_CONST', GO_CONST)]:
    if "'''" in src:
        raise SystemExit(name + ' contains triple-single-quote')

HEADER = '''# =====================================================================
# Cell 1.5 - Bundle tools.yen_sei.eval into Colab.
#
# The notebook imports `from tools.yen_sei.eval.runner import evaluate_test_sets`
# but Colab does not have the yen-go repo. This cell writes the 4 small
# files (~22 KB total) that the eval runner needs into /content/yen_sei_bundle/
# and adds it to sys.path. No repo clone, no extra upload required.
# =====================================================================
import sys
from pathlib import Path

BUNDLE_ROOT = Path("/content/yen_sei_bundle")

'''

FOOTER = '''
_FILES = {
    "tools/__init__.py": "",
    "tools/core/__init__.py": "",
    "tools/core/go_teaching_constants.py": _GO_CONST,
    "tools/yen_sei/__init__.py": "",
    "tools/yen_sei/eval/__init__.py": "",
    "tools/yen_sei/eval/scorers.py": _SCORERS,
    "tools/yen_sei/eval/judges.py": _JUDGES,
    "tools/yen_sei/eval/runner.py": _RUNNER,
}
for _rel, _content in _FILES.items():
    _p = BUNDLE_ROOT / _rel
    _p.parent.mkdir(parents=True, exist_ok=True)
    _p.write_text(_content, encoding="utf-8")

if str(BUNDLE_ROOT) not in sys.path:
    sys.path.insert(0, str(BUNDLE_ROOT))

from tools.yen_sei.eval.runner import evaluate_test_sets  # noqa: F401 sanity check
print(f"yen_sei eval bundle ready at {BUNDLE_ROOT}")
'''

TQ = "'" * 3
cell = (
    HEADER
    + "_GO_CONST = r" + TQ + GO_CONST + TQ + "\n\n"
    + "_SCORERS = r" + TQ + scorers + TQ + "\n\n"
    + "_JUDGES = r" + TQ + judges + TQ + "\n\n"
    + "_RUNNER = r" + TQ + runner + TQ + "\n"
    + FOOTER
)

# Compile-check
compile(cell, '<setup_cell>', 'exec')

Path('tools/yen_sei/notebooks/_setup_cell_content.txt').write_text(cell, encoding='utf-8')
print('OK', len(cell), 'bytes')
