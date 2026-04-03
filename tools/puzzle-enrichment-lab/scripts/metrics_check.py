"""T6: Quantitative metrics verification — density, components, eyes.

Reports two views:
  1. ALL stones (puzzle + frame) — total board metrics
  2. FRAME-ONLY stones — measures fill quality in isolation
"""
import random
from collections import deque
from pathlib import Path

from analyzers.liberty import is_eye
from analyzers.sgf_parser import extract_position, parse_sgf
from analyzers.tsumego_frame import apply_tsumego_frame
from models.position import Color

FIXTURE = Path("tests/fixtures/scale/scale-10k")


def count_components(coords):
    if not coords:
        return 0
    visited = set()
    comps = 0
    for start in coords:
        if start in visited:
            continue
        comps += 1
        q = deque([start])
        visited.add(start)
        while q:
            x, y = q.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nc = (x + dx, y + dy)
                if nc in coords and nc not in visited:
                    visited.add(nc)
                    q.append(nc)
    return comps


def count_eyes(color, occupied, bs):
    eyes = 0
    for x in range(bs):
        for y in range(bs):
            if (x, y) not in occupied and is_eye((x, y), color, occupied, bs):
                eyes += 1
    return eyes


def main():
    sgfs = sorted(FIXTURE.glob("*.sgf"))
    random.seed(42)
    sample = random.sample(sgfs, min(20, len(sgfs)))

    # ── Section 1: All stones (total board) ─────────────────
    print("=" * 100)
    print("SECTION 1: ALL STONES (puzzle + frame)")
    print("=" * 100)
    hdr = f"{'File':<45} {'Dens':>6} {'W-c':>5} {'B-c':>5} {'W-e':>5} {'B-e':>5} {'Added':>6} {'Skip':>5}"
    print(hdr)
    print("-" * 88)

    rows = []  # (name, density, w_comp, b_comp, w_eyes, b_eyes, added, skipped)
    errors = 0

    for sgf_path in sample:
        try:
            sgf_text = sgf_path.read_text(encoding="utf-8", errors="replace")
            root = parse_sgf(sgf_text)
            pos = extract_position(root)
            orig_stones = {(s.x, s.y): s.color for s in pos.stones}

            framed = apply_tsumego_frame(pos)
            bs = framed.board_size
            occ = {(s.x, s.y): s.color for s in framed.stones}
            added = len(occ) - len(orig_stones)
            skipped = added == 0  # frame was skipped
            density = len(occ) / (bs * bs)

            w_coords = {c for c, v in occ.items() if v == Color.WHITE}
            b_coords = {c for c, v in occ.items() if v == Color.BLACK}
            w_comp = count_components(w_coords)
            b_comp = count_components(b_coords)
            w_eyes = count_eyes(Color.WHITE, occ, bs)
            b_eyes = count_eyes(Color.BLACK, occ, bs)

            # Frame-only stones
            frame_only = {c: v for c, v in occ.items() if c not in orig_stones}
            fw_coords = {c for c, v in frame_only.items() if v == Color.WHITE}
            fb_coords = {c for c, v in frame_only.items() if v == Color.BLACK}
            fw_comp = count_components(fw_coords)
            fb_comp = count_components(fb_coords)

            name = sgf_path.stem[:42]
            skip_mark = " SKIP" if skipped else ""
            print(f"{name:<45} {density:>5.1%} {w_comp:>5} {b_comp:>5} {w_eyes:>5} {b_eyes:>5} {added:>6}{skip_mark}")

            rows.append({
                "name": name, "density": density,
                "w_comp": w_comp, "b_comp": b_comp,
                "w_eyes": w_eyes, "b_eyes": b_eyes,
                "added": added, "skipped": skipped,
                "fw_comp": fw_comp, "fb_comp": fb_comp,
                "orig_w": len({c for c, v in orig_stones.items() if v == Color.WHITE}),
                "orig_b": len({c for c, v in orig_stones.items() if v == Color.BLACK}),
                "frame_w": len(fw_coords), "frame_b": len(fb_coords),
            })
        except Exception as e:
            errors += 1
            print(f"{sgf_path.stem[:42]:<45} ERROR: {e}")

    # Filter to actually-framed puzzles
    framed_rows = [r for r in rows if not r["skipped"]]
    n = len(framed_rows)

    print("-" * 88)
    print(f"Total: {len(rows)} puzzles, {n} framed, {len(rows)-n} skipped, {errors} errors")

    if n > 0:
        def mean(vals):
            return sum(vals) / len(vals)

        densities = [r["density"] for r in framed_rows]
        wc = [r["w_comp"] for r in framed_rows]
        bc = [r["b_comp"] for r in framed_rows]
        we = [r["w_eyes"] for r in framed_rows]
        be = [r["b_eyes"] for r in framed_rows]

        print(f"\n{'ALL-STONES SUMMARY (framed only)':}")
        print(f"  Density:  mean={mean(densities):.1%}  min={min(densities):.1%}  max={max(densities):.1%}")
        print(f"  W-comps:  mean={mean(wc):.1f}  min={min(wc)}  max={max(wc)}")
        print(f"  B-comps:  mean={mean(bc):.1f}  min={min(bc)}  max={max(bc)}")
        print(f"  W-eyes:   mean={mean(we):.1f}  min={min(we)}  max={max(we)}")
        print(f"  B-eyes:   mean={mean(be):.1f}  min={min(be)}  max={max(be)}")

        # ── Section 2: Frame-only components ─────────────────
        print("\n" + "=" * 100)
        print("SECTION 2: FRAME-ONLY COMPONENTS (excluding original puzzle stones)")
        print("=" * 100)
        hdr2 = f"{'File':<45} {'FrmW':>5} {'FrmB':>5} {'FW-c':>5} {'FB-c':>5} {'OrigW':>6} {'OrigB':>6}"
        print(hdr2)
        print("-" * 80)
        for r in framed_rows:
            print(f"{r['name']:<45} {r['frame_w']:>5} {r['frame_b']:>5} {r['fw_comp']:>5} {r['fb_comp']:>5} {r['orig_w']:>6} {r['orig_b']:>6}")

        fwc = [r["fw_comp"] for r in framed_rows]
        fbc = [r["fb_comp"] for r in framed_rows]
        print("-" * 80)
        print(f"  Frame W-comps:  mean={mean(fwc):.1f}  min={min(fwc)}  max={max(fwc)}")
        print(f"  Frame B-comps:  mean={mean(fbc):.1f}  min={min(fbc)}  max={max(fbc)}")

        # ── Section 3: Gate results ─────────────────
        print("\n" + "=" * 100)
        print("GATE RESULTS (framed puzzles only)")
        print("=" * 100)
        in_density = sum(1 for d in densities if 0.25 <= d <= 0.55)
        in_comp_all = sum(1 for w, b in zip(wc, bc, strict=False) if w <= 2 and b <= 2)
        in_comp_frame = sum(1 for w, b in zip(fwc, fbc, strict=False) if w <= 2 and b <= 2)
        in_eyes = sum(1 for w, b in zip(we, be, strict=False) if 2 <= w <= 15 and 2 <= b <= 15)
        print(f"  Density 25-55%:           {in_density}/{n}  {'PASS' if in_density > n*0.5 else 'NEEDS WORK'}")
        print(f"  Components<=2 (all):      {in_comp_all}/{n}  {'PASS' if in_comp_all > n*0.5 else 'NEEDS WORK'}")
        print(f"  Components<=2 (frame):    {in_comp_frame}/{n}  {'PASS' if in_comp_frame > n*0.5 else 'NEEDS WORK'}")
        print(f"  Eyes 2-15 (both):         {in_eyes}/{n}  {'PASS' if in_eyes > n*0.7 else 'NEEDS WORK'}")


if __name__ == "__main__":
    main()
