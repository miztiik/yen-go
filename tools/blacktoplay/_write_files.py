"""Helper script to write the three BTP verification files."""
from pathlib import Path

BASE = Path(__file__).parent

# ===== File 1: hash_decoder.py =====
(BASE / "hash_decoder.py").write_text(r'''"""BTP hash decoding/encoding -- Python port of btp-tsumego.js position_from_hash / get_hash_from_position.

Converts BTP's base-59 encoded board hashes to/from 2D board positions.
"""

from __future__ import annotations

# Base-59 charset (missing: lowercase 'l', uppercase 'I', uppercase 'O')
CHARSET = "0123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ"

# Index = board_size, value = hash string length
HASH_LENGTHS = [0, 2, 2, 4, 6, 8, 12, 14, 20, 24, 30, 36, 42, 50, 56, 66, 74, 84, 94, 104]

EMPTY, BLACK, WHITE = ".", "B", "W"


def decode_hash(hash_str: str, board_size: int) -> list[str]:
    """Decode a BTP hash string into a 2D board position.

    Args:
        hash_str: Base-59 encoded hash from BTP.
        board_size: Board size (e.g. 9, 19).

    Returns:
        List of strings, each representing a row. Characters: '.', 'B', 'W'.
    """
    expected_len = HASH_LENGTHS[board_size]
    if len(hash_str) > expected_len:
        hash_str = hash_str[-expected_len:]

    position_string = ""
    for n in range(0, len(hash_str), 2):
        if n + 1 >= len(hash_str):
            break
        c0 = CHARSET.index(hash_str[n])
        c1 = CHARSET.index(hash_str[n + 1])
        number = c1 * 59 + c0

        part = ""
        for i in range(6, -1, -1):
            power = 3 ** i
            if number >= power * 2:
                part = WHITE + part
                number -= power * 2
            elif number >= power:
                part = BLACK + part
                number -= power
            else:
                part = EMPTY + part

        position_string += part

    total = board_size * board_size
    if len(position_string) > total:
        position_string = position_string[:total]

    rows: list[str] = []
    for i in range(board_size):
        start = i * board_size
        end = start + board_size
        row = position_string[start:end]
        while len(row) < board_size:
            row += EMPTY
        rows.append(row)

    while len(rows) < board_size:
        rows.append(EMPTY * board_size)

    return rows


def encode_position(position: list[str], visible_size: int) -> str:
    """Encode a 2D board position into a BTP hash string."""
    chars = ".BW"
    flat = ""
    for y in range(visible_size):
        for x in range(visible_size):
            if y < len(position) and x < len(position[y]):
                flat += position[y][x]
            else:
                flat += EMPTY

    result = ""
    for i in range(0, len(flat), 7):
        number = 0
        for c in range(7):
            if (i + c) < len(flat):
                number += chars.index(flat[i + c]) * (3 ** c)
        result += CHARSET[number % 59] + CHARSET[number // 59]

    return result


def board_to_ascii(position: list[str]) -> str:
    """Pretty-print a board position with spaces between cells."""
    return "\n".join(" ".join(row) for row in position)


def count_stones(position: list[str]) -> tuple[int, int]:
    """Count (black_stones, white_stones) on the board."""
    flat = "".join(position)
    return flat.count("B"), flat.count("W")
''', encoding='utf-8')
print("Written: hash_decoder.py")

# ===== File 2: verify_hash_decode.py =====
(BASE / "verify_hash_decode.py").write_text(r'''"""Fresh hash decode verification -- fetches puzzles from BTP API and tests round-trip.

Usage: python -m tools.blacktoplay.verify_hash_decode
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

from tools.blacktoplay.hash_decoder import (
    HASH_LENGTHS,
    board_to_ascii,
    count_stones,
    decode_hash,
    encode_position,
)

LOAD_DATA_URL = "https://blacktoplay.com/php/public/load_data.php"
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://blacktoplay.com/",
    "Origin": "https://blacktoplay.com",
    "X-Requested-With": "XMLHttpRequest",
}
LOCAL_LIST_PATH = Path("TODO/btp-list-response.json")
OUTPUT_DIR = Path("tools/blacktoplay/verification_output")
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"


def fetch_puzzle_list() -> list[dict]:
    """Load puzzle list from local cache."""
    if LOCAL_LIST_PATH.exists():
        print(f"Loading puzzle list from: {LOCAL_LIST_PATH}")
        data = json.loads(LOCAL_LIST_PATH.read_text(encoding="utf-8"))
        return data["list"]
    raise RuntimeError(f"Local list not found: {LOCAL_LIST_PATH}")


def fetch_puzzle_data(puzzle_id: str) -> dict:
    """Fetch detailed puzzle data from BTP API."""
    resp = httpx.post(
        LOAD_DATA_URL,
        data={"id": puzzle_id, "vid": "visitor", "rating": "1500", "c_id": "", "db": "0"},
        headers=BROWSER_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def select_diverse_puzzles(puzzle_list: list[dict], count_per_type: int = 3) -> list[dict]:
    """Select diverse puzzles: mix of types and ratings."""
    by_type: dict[str, list[dict]] = {"0": [], "1": [], "2": []}
    for p in puzzle_list:
        if p["type"] in by_type:
            by_type[p["type"]].append(p)

    selected: list[dict] = []
    seen_ids: set[str] = set()

    for puzzles in by_type.values():
        if not puzzles:
            continue
        sorted_p = sorted(puzzles, key=lambda x: int(x.get("rating", "0")))
        n = len(sorted_p)
        indices = [0, n // 4, n // 2, 3 * n // 4, n - 1]
        count = 0
        for idx in indices:
            if count >= count_per_type:
                break
            p = sorted_p[idx]
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                selected.append(p)
                count += 1

    # Add known test cases
    for p in puzzle_list:
        if p["id"] in {"B9Zx5z", "000012", "14S3Hj", "H3LiZx"} and p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            selected.append(p)

    return selected


def run_round_trip_test(puzzle_id: str, puzzle_data: dict) -> dict:
    """Run decode -> encode round-trip test."""
    result: dict = {
        "id": puzzle_id,
        "type": puzzle_data.get("type"),
        "board_size": puzzle_data.get("board_size"),
        "viewport_size": puzzle_data.get("viewport_size"),
        "to_play": puzzle_data.get("to_play"),
        "rating": puzzle_data.get("rating"),
    }

    hash_str = puzzle_data.get("hash", "")
    board_size = int(puzzle_data.get("board_size", 9))
    viewport_size = int(puzzle_data.get("viewport_size", board_size))

    if not hash_str:
        result["status"] = "SKIP"
        result["reason"] = "No hash"
        return result

    result["original_hash"] = hash_str
    result["expected_hash_len"] = HASH_LENGTHS[board_size]
    result["actual_hash_len"] = len(hash_str)

    try:
        # Try viewport_size first (classic), then board_size
        for decode_size in [viewport_size, board_size]:
            position = decode_hash(hash_str, decode_size)
            re_encoded = encode_position(position, decode_size)
            if re_encoded == hash_str:
                b_count, w_count = count_stones(position)
                result["black_stones"] = b_count
                result["white_stones"] = w_count
                result["board_ascii"] = board_to_ascii(position)
                result["re_encoded_hash"] = re_encoded
                result["decode_size"] = decode_size
                result["status"] = "PASS"
                return result

        # If no exact match, report FAIL with viewport_size decode
        decode_size = viewport_size if puzzle_data.get("type") in (0, "0") else board_size
        position = decode_hash(hash_str, decode_size)
        re_encoded = encode_position(position, decode_size)
        b_count, w_count = count_stones(position)
        result["black_stones"] = b_count
        result["white_stones"] = w_count
        result["board_ascii"] = board_to_ascii(position)
        result["re_encoded_hash"] = re_encoded
        result["status"] = "FAIL"
        result["mismatch_count"] = sum(1 for a, b in zip(hash_str, re_encoded) if a != b)

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    return result


def generate_verification_html(results: list[dict]) -> str:
    """Generate HTML page with board visualizations."""
    rows_html = ""
    for r in results:
        sc = {"PASS": "pass", "FAIL": "fail", "ERROR": "error", "SKIP": "skip"}.get(r.get("status", ""), "unknown")

        board_html = ""
        if "board_ascii" in r:
            rows = r["board_ascii"].replace(" ", "").split("\\n")
            gs = len(rows[0]) if rows else 9
            board_html = f'<div class="board-grid" style="grid-template-columns: repeat({gs}, 1fr);">'
            for y, row in enumerate(rows):
                for x, cell in enumerate(row):
                    cc = {"B": "black", "W": "white", ".": "empty"}.get(cell, "empty")
                    board_html += f'<div class="cell {cc}"></div>'
            board_html += "</div>"

        rows_html += f\'\'\'
        <div class="result {sc}" data-puzzle-id="{r['id']}">
            <div class="result-header">
                <span class="puzzle-id">{r['id']}</span>
                <span class="status-badge {sc}">{r.get('status', '?')}</span>
                <span class="meta">type={r.get('type', '?')} size={r.get('board_size', '?')}x{r.get('viewport_size', '?')} rating={r.get('rating', '?')} to_play={r.get('to_play', '?')}</span>
            </div>
            <div class="result-body">
                <div class="board-container">{board_html}</div>
                <div class="hash-info">
                    <p><strong>Original:</strong> <code>{r.get('original_hash', 'N/A')}</code></p>
                    <p><strong>Re-encoded:</strong> <code>{r.get('re_encoded_hash', 'N/A')}</code></p>
                    <p><strong>Stones:</strong> {r.get('black_stones', '?')}B / {r.get('white_stones', '?')}W</p>
                </div>
            </div>
        </div>\'\'\'

    pc = sum(1 for r in results if r.get("status", "").startswith("PASS"))
    fc = sum(1 for r in results if r.get("status") == "FAIL")
    ec = sum(1 for r in results if r.get("status") == "ERROR")
    sk = sum(1 for r in results if r.get("status") == "SKIP")

    return f\'\'\'<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>BTP Hash Decode Verification</title>
<style>
body {{ font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }}
h1 {{ color: #e94560; }}
.summary {{ background: #16213e; padding: 16px; border-radius: 8px; margin-bottom: 24px; display: flex; gap: 20px; }}
.stat {{ text-align: center; padding: 8px 16px; }}
.stat .num {{ font-size: 2em; font-weight: bold; }}
.stat.pass .num {{ color: #4caf50; }}
.stat.fail .num {{ color: #f44336; }}
.stat.error .num {{ color: #ff9800; }}
.result {{ background: #16213e; border-radius: 8px; margin-bottom: 16px; padding: 16px; border-left: 4px solid #666; }}
.result.pass {{ border-left-color: #4caf50; }}
.result.fail {{ border-left-color: #f44336; }}
.result.error {{ border-left-color: #ff9800; }}
.result-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }}
.puzzle-id {{ font-family: monospace; font-size: 1.2em; font-weight: bold; }}
.status-badge {{ padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }}
.status-badge.pass {{ background: #4caf50; color: white; }}
.status-badge.fail {{ background: #f44336; color: white; }}
.status-badge.error {{ background: #ff9800; color: white; }}
.meta {{ color: #888; font-size: 0.85em; }}
.result-body {{ display: flex; gap: 20px; align-items: flex-start; }}
.board-grid {{ display: grid; gap: 1px; background: #333; padding: 2px; border-radius: 4px; }}
.cell {{ width: 20px; height: 20px; border-radius: 50%; }}
.cell.black {{ background: #222; border: 1px solid #555; }}
.cell.white {{ background: #fff; border: 1px solid #ccc; }}
.cell.empty {{ background: transparent; border: 1px solid #444; border-radius: 0; }}
.hash-info code {{ word-break: break-all; color: #64ffda; }}
</style></head>
<body>
<h1>BTP Hash Decode Verification</h1>
<p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</p>
<div class="summary">
<div class="stat pass"><div class="num">{pc}</div>PASS</div>
<div class="stat fail"><div class="num">{fc}</div>FAIL</div>
<div class="stat error"><div class="num">{ec}</div>ERROR</div>
<div class="stat"><div class="num">{sk}</div>SKIP</div>
<div class="stat"><div class="num">{len(results)}</div>TOTAL</div>
</div>
{rows_html}
</body></html>\'\'\'


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    puzzle_list = fetch_puzzle_list()
    print(f"Loaded {len(puzzle_list)} puzzles")

    test_puzzles = select_diverse_puzzles(puzzle_list, count_per_type=3)
    print(f"\\nSelected {len(test_puzzles)} puzzles for testing:")
    for p in test_puzzles:
        print(f"  {p['id']} (type={p['type']}, rating={p['rating']})")

    results: list[dict] = []
    for i, p in enumerate(test_puzzles):
        pid = p["id"]
        print(f"\\n[{i+1}/{len(test_puzzles)}] Testing {pid}...", end=" ")
        try:
            data = fetch_puzzle_data(pid)
            result = run_round_trip_test(pid, data)
            print(result["status"])
            results.append(result)
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"id": pid, "status": "ERROR", "error": str(e),
                           "type": p["type"], "board_size": "?", "rating": p["rating"]})
        time.sleep(0.5)

    results_file = OUTPUT_DIR / "hash_verification_results.json"
    results_file.write_text(json.dumps(results, indent=2))
    print(f"\\nResults saved to {results_file}")

    html = generate_verification_html(results)
    html_file = OUTPUT_DIR / "hash_verification.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"HTML report saved to {html_file}")

    pc = sum(1 for r in results if r["status"].startswith("PASS"))
    fc = sum(1 for r in results if r["status"] == "FAIL")
    ec = sum(1 for r in results if r["status"] == "ERROR")
    print(f"\\n{'='*60}")
    print(f"SUMMARY: {pc}/{len(results)} PASS, {fc} FAIL, {ec} ERROR")
    print(f"{'='*60}")

    if fc > 0:
        print("\\nFailed puzzles:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  {r['id']}: mismatches={r.get('mismatch_count', '?')}")

    return 0 if fc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
''', encoding='utf-8')
print("Written: verify_hash_decode.py")

# ===== File 3: screenshot_verify.py =====
(BASE / "screenshot_verify.py").write_text(r'''"""Playwright screenshot verification of BTP hash decode results.

Usage: python -m tools.blacktoplay.screenshot_verify
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed.")
    sys.exit(1)

OUTPUT_DIR = Path("tools/blacktoplay/verification_output")
SCREENSHOT_DIR = OUTPUT_DIR / "screenshots"


def take_screenshots() -> int:
    html_file = OUTPUT_DIR / "hash_verification.html"
    if not html_file.exists():
        print(f"ERROR: {html_file} not found. Run verify_hash_decode first.")
        return 1

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        file_url = html_file.resolve().as_uri()
        page.goto(file_url)
        page.wait_for_load_state("networkidle")

        full_path = SCREENSHOT_DIR / "full_report.png"
        page.screenshot(path=str(full_path), full_page=True)
        print(f"Full report screenshot: {full_path}")

        summary_el = page.query_selector(".summary")
        if summary_el:
            summary_el.screenshot(path=str(SCREENSHOT_DIR / "summary.png"))
            print("Summary screenshot saved")

        results = page.query_selector_all(".result")
        for i, el in enumerate(results):
            pid = el.get_attribute("data-puzzle-id") or f"puzzle_{i}"
            badge = el.query_selector(".status-badge")
            status = badge.text_content().strip() if badge else "unknown"
            path = SCREENSHOT_DIR / f"puzzle_{pid}_{status.lower().replace(' ', '_')}.png"
            el.screenshot(path=str(path))
            print(f"  {pid} [{status}]: {path}")

        browser.close()

    print(f"\nAll screenshots saved to {SCREENSHOT_DIR}/")
    return 0


if __name__ == "__main__":
    sys.exit(take_screenshots())
''', encoding='utf-8')
print("Written: screenshot_verify.py")

print("\nAll 3 files written successfully!")
