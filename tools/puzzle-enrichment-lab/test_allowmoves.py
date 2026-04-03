"""Test KataGo allowMoves dict format with multiple moves."""
import json
import subprocess
import time

proc = subprocess.Popen(
    ['katago/katago.exe', 'analysis', '-model',
     'models-data/g170-b6c96-s175395328-d26788732.bin.gz',
     '-config', 'katago/tsumego_analysis.cfg'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True
)

time.sleep(5)

# Test 1: dict format for allowMoves with multiple moves
req = {
    'id': 'test_dict',
    'initialStones': [['B', 'D4'], ['W', 'E5']],
    'moves': [],
    'rules': 'chinese',
    'komi': 7.5,
    'boardXSize': 9,
    'boardYSize': 9,
    'analyzeTurns': [0],
    'maxVisits': 10,
    'initialPlayer': 'B',
    'allowMoves': [{'player': 'B', 'moves': ['C3', 'D3', 'E3', 'F5'], 'untilDepth': 1}]
}
proc.stdin.write(json.dumps(req) + '\n')
proc.stdin.flush()

line = proc.stdout.readline()
data = json.loads(line)
if 'error' in data:
    print('DICT FORMAT ERROR:', data['error'])
else:
    print('DICT FORMAT: SUCCESS with multiple moves!')
    moves = data.get('moveInfos', [])
    print(f'  Got {len(moves)} moveInfos')
    for m in moves[:5]:
        move = m.get('move', 'none')
        visits = m.get('visits', 0)
        wr = m.get('winrate', 0)
        print(f'  {move} visits={visits} winrate={wr:.3f}')

# Test 2: old list-of-lists format (what our code was generating)
req2 = {
    'id': 'test_list',
    'initialStones': [['B', 'D4'], ['W', 'E5']],
    'moves': [],
    'rules': 'chinese',
    'komi': 7.5,
    'boardXSize': 9,
    'boardYSize': 9,
    'analyzeTurns': [0],
    'maxVisits': 10,
    'initialPlayer': 'B',
    'allowMoves': [['B', 'C3'], ['B', 'D3'], ['B', 'E3'], ['B', 'F5']]
}
proc.stdin.write(json.dumps(req2) + '\n')
proc.stdin.flush()

line2 = proc.stdout.readline()
data2 = json.loads(line2)
if 'error' in data2:
    print(f'\nLIST FORMAT ERROR: {data2["error"]}')
else:
    print('\nLIST FORMAT: SUCCESS')

proc.terminate()
