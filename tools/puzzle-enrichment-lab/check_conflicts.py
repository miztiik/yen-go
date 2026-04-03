import re
from pathlib import Path

FIXTURES = Path('tests/fixtures')

def check(fname):
    text = (FIXTURES / fname).read_text(encoding='utf-8')
    def multi(key):
        r = []
        for block in re.findall(rf'{key}((?:\[[^\]]*\])+)', text):
            r.extend(re.findall(r'\[([^\]]*)\]', block))
        return set(r)
    ab = multi('AB')
    aw = multi('AW')
    for seg in text.split(';')[1:]:
        m = re.match(r'\s*([BW])\[([a-s]{0,2})\]', seg.strip())
        if m:
            color, coord = m.group(1), m.group(2)
            conflict = ''
            if color == 'B' and coord in ab:
                conflict = 'BLACK ON OWN STONE'
            elif color == 'B' and coord in aw:
                conflict = 'BLACK ON WHITE STONE'
            elif color == 'W' and coord in aw:
                conflict = 'WHITE ON OWN STONE'
            elif color == 'W' and coord in ab:
                conflict = 'WHITE ON BLACK STONE'
            else:
                conflict = 'OK'
            print(f'{fname}: {color}[{coord}] -> {conflict}')
            break

for f in sorted(FIXTURES.glob('*.sgf')):
    check(f.name)
