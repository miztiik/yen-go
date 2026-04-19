"""Validate the new bundle cell in both notebooks."""
import json
import shutil
import tempfile
from pathlib import Path

nb1 = json.load(open('tools/yen_sei/notebooks/02_train_tier1.ipynb', encoding='utf-8'))
nb2 = json.load(open('tools/yen_sei/notebooks/02a_model_evaluation.ipynb', encoding='utf-8'))
print(f"02 cells: {len(nb1['cells'])}, 02a cells: {len(nb2['cells'])}")


def get_bundle_cell(nb):
    for c in nb['cells']:
        src = ''.join(c.get('source') or [])
        if 'BUNDLE_ROOT' in src and '_GO_CONST' in src:
            return src
    return None


bundle1 = get_bundle_cell(nb1)
bundle2 = get_bundle_cell(nb2)
print(f"02 bundle cell: {len(bundle1) if bundle1 else 0} bytes")
print(f"02a bundle cell: {len(bundle2) if bundle2 else 0} bytes")
assert bundle1 == bundle2, "bundle cells differ between notebooks!"

# Execute the bundle cell with a tmpdir as BUNDLE_ROOT
tmp = Path(tempfile.mkdtemp())
patched = bundle1.replace('Path("/content/yen_sei_bundle")', f'Path(r"{tmp}")')
exec(patched, {"__name__": "__test__"})
print(f"\nBundle test PASSED. Files written under {tmp}:")
for p in sorted(tmp.rglob('*.py')):
    print(f"  {p.relative_to(tmp)} ({p.stat().st_size} bytes)")
shutil.rmtree(tmp)
print("\nOK")
