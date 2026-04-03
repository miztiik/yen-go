"""Debug integration test: what does KataGo think about simple_life_death?"""
import asyncio
from pathlib import Path

from analyzers.query_builder import build_query_from_sgf
from analyzers.sgf_parser import extract_correct_first_move, parse_sgf
from analyzers.validate_correct_move import validate_correct_move
from engine.config import EngineConfig
from engine.local_subprocess import LocalEngine
from models.analysis_response import sgf_to_gtp

sgf = Path('tests/fixtures/simple_life_death.sgf').read_text()
root = parse_sgf(sgf)
correct_sgf = extract_correct_first_move(root)
print(f"Correct SGF move: {correct_sgf}")

request = build_query_from_sgf(sgf, max_visits=200)
correct_gtp = sgf_to_gtp(correct_sgf, request.position.board_size)
print(f"Correct GTP move: {correct_gtp}")

payload = request.to_katago_json()
print(f"\nallowMoves: {payload.get('allowMoves')}")
print(f"Board: {payload['boardXSize']}x{payload['boardYSize']}")
print(f"Initial stones: {len(payload['initialStones'])}")
print(f"Visits: {payload['maxVisits']}")

config = EngineConfig(
    katago_path='katago/katago.exe',
    model_path='models-data/g170-b6c96-s175395328-d26788732.bin.gz',
    config_path='katago/tsumego_analysis.cfg',
    default_max_visits=200,
)

async def run():
    engine = LocalEngine(config)
    await engine.start()
    await engine.wait_for_ready(timeout=60.0)

    response = await asyncio.wait_for(engine.analyze(request), timeout=30.0)

    print("\nKataGo top moves:")
    for i, m in enumerate(response.move_infos[:10]):
        print(f"  #{i+1}: {m.move} visits={m.visits} winrate={m.winrate:.3f}")

    result = validate_correct_move(
        response=response,
        correct_move_gtp=correct_gtp,
        tags=[10],
        corner="TL",
    )
    print(f"\nValidation status: {result.status}")
    print(f"Rank: {result.rank}")
    print(f"Winrate: {result.winrate}")
    print(f"Policy: {result.policy}")

    await engine.shutdown()

asyncio.run(run())
