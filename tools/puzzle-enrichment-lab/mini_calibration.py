"""Quick mini-calibration: 3 puzzles per collection with Phase S code."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cli import run_batch
from config import load_enrichment_config

lab_dir = Path(__file__).parent
katago = lab_dir / "katago" / "katago.exe"
quick_model = lab_dir / "models-data" / "kata1-b18c384nbt-s9996604416-d4316597426.bin.gz"

cfg = load_enrichment_config()
print(f"lab_mode enabled={cfg.lab_mode.enabled}, visits={cfg.lab_mode.visits}, model={cfg.lab_mode.model}")
print(f"weights: {cfg.difficulty.weights}")
print()

collections = {
    "elementary": lab_dir / "tests/fixtures/calibration/cho-elementary",
    "intermediate": lab_dir / "tests/fixtures/calibration/cho-intermediate",
    "advanced": lab_dir / "tests/fixtures/calibration/cho-advanced",
}

all_results = {}

for coll_name, coll_dir in collections.items():
    sgfs = sorted(coll_dir.glob("*.sgf"))[:3]
    print(f"=== {coll_name.upper()} — {len(sgfs)} puzzles: {[s.name for s in sgfs]} ===")

    with tempfile.TemporaryDirectory() as inp_dir, tempfile.TemporaryDirectory() as out_dir:
        for sgf in sgfs:
            shutil.copy2(sgf, inp_dir)

        ec = run_batch(
            input_dir=inp_dir,
            output_dir=out_dir,
            katago_path=str(katago),
            quick_model_path=str(quick_model),
            referee_model_path="",
            config_path=None,
        )
        print(f"  run_batch exit_code={ec}")

        levels = []
        for jf in sorted(Path(out_dir).glob("*.json")):
            d = json.loads(jf.read_text())
            diff = d.get("difficulty", {})
            eng = d.get("engine", {})
            val = d.get("validation", {})
            level_id = diff.get("suggested_level_id", "?")
            score = diff.get("composite_score", 0)
            policy = val.get("correct_move_policy", 0)
            visits = eng.get("visits", 0)
            model = eng.get("model", "?")
            status = val.get("status", "?")
            trap = diff.get("trap_density", "?")
            levels.append(level_id)
            print(
                f"  {jf.stem}: level={level_id} score={score:.1f} "
                f"policy={policy:.4f} visits={visits} model={model} "
                f"status={status} trap={trap:.3f}"
            )

        if levels:
            valid = [lvl for lvl in levels if isinstance(lvl, int)]
            avg = sum(valid) / len(valid) if valid else 0
            print(f"  avg_level={avg:.1f} (target for {coll_name}: elementary=130, intermediate=140, advanced=160)")
        all_results[coll_name] = levels
    print()

print("=== SUMMARY ===")
for name, levels in all_results.items():
    valid = [lvl for lvl in levels if isinstance(lvl, int)]
    avg = sum(valid) / len(valid) if valid else 0
    print(f"{name}: avg={avg:.1f}, levels={levels}")
