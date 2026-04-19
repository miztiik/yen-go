import json

nb = json.load(open('tools/yen_sei/notebooks/02_train_tier1.ipynb', encoding='utf-8'))
for i, c in enumerate(nb['cells'][:5]):
    src = c.get('source') or []
    s = ''.join(src) if isinstance(src, list) else src
    print(f"cell {i} type={c.get('cell_type')} src_len={len(s)} first_80={s[:80]!r}")

# Now find bundle cell
print()
for i, c in enumerate(nb['cells']):
    src = c.get('source') or []
    s = ''.join(src) if isinstance(src, list) else src
    if 'BUNDLE_ROOT' in s:
        print(f"BUNDLE found in cell {i}, len={len(s)}")
    if '_GO_CONST' in s:
        print(f"_GO_CONST found in cell {i}")
