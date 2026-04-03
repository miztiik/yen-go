"""Fresh hash decode verification -- fetches puzzles from BTP API and tests round-trip.

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


def fetch_puzzle_list():
    if LOCAL_LIST_PATH.exists():
        print("Loading puzzle list from: " + str(LOCAL_LIST_PATH))
        data = json.loads(LOCAL_LIST_PATH.read_text(encoding="utf-8-sig"))
        return data["list"]
    raise RuntimeError("Local list not found: " + str(LOCAL_LIST_PATH))


def fetch_puzzle_data(puzzle_id):
    resp = httpx.post(
        LOAD_DATA_URL,
        data={"id": puzzle_id, "vid": "visitor", "rating": "1500", "c_id": "", "db": "0"},
        headers=BROWSER_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def select_diverse_puzzles(puzzle_list, count_per_type=3):
    by_type = {"0": [], "1": [], "2": []}
    for p in puzzle_list:
        if p["type"] in by_type:
            by_type[p["type"]].append(p)

    selected = []
    seen_ids = set()
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

    for p in puzzle_list:
        if p["id"] in {"B9Zx5z", "000012", "14S3Hj", "H3LiZx"} and p["id"] not in seen_ids:
            seen_ids.add(p["id"])
            selected.append(p)
    return selected


def run_round_trip_test(puzzle_id, puzzle_data):
    result = {
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
        return result

    result["original_hash"] = hash_str
    result["expected_hash_len"] = HASH_LENGTHS[board_size]
    result["actual_hash_len"] = len(hash_str)
    try:
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

        decode_size = viewport_size if puzzle_data.get("type") in (0, "0") else board_size
        position = decode_hash(hash_str, decode_size)
        re_encoded = encode_position(position, decode_size)
        b_count, w_count = count_stones(position)
        result["black_stones"] = b_count
        result["white_stones"] = w_count
        result["board_ascii"] = board_to_ascii(position)
        result["re_encoded_hash"] = re_encoded
        result["status"] = "FAIL"
        result["mismatch_count"] = sum(1 for a, b in zip(hash_str, re_encoded, strict=False) if a != b)
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
    return result


def _make_board_html(r):
    if "board_ascii" not in r:
        return ""
    rows = r["board_ascii"].replace(" ", "").split("\n")
    gs = len(rows[0]) if rows else 9
    parts = ['<div class="board-grid" style="grid-template-columns: repeat(%d, 1fr);">' % gs]
    for row in rows:
        for cell in row:
            cc = {"B": "black", "W": "white", ".": "empty"}.get(cell, "empty")
            parts.append(f'<div class="cell {cc}"></div>')
    parts.append("</div>")
    return "".join(parts)


def _make_result_html(r):
    sc = {"PASS": "pass", "FAIL": "fail", "ERROR": "error", "SKIP": "skip"}.get(
        r.get("status", ""), "unknown"
    )
    board = _make_board_html(r)
    return (
        '<div class="result {}" data-puzzle-id="{}">'
        '<div class="result-header">'
        '<span class="puzzle-id">{}</span>'
        '<span class="status-badge {}">{}</span>'
        '<span class="meta">type={} size={}x{} rating={} to_play={}</span>'
        '</div>'
        '<div class="result-body">'
        '<div class="board-container">{}</div>'
        '<div class="hash-info">'
        '<p><strong>Original:</strong> <code>{}</code></p>'
        '<p><strong>Re-encoded:</strong> <code>{}</code></p>'
        '<p><strong>Stones:</strong> {}B / {}W</p>'
        '</div></div></div>'
    ).format(
        sc, r["id"], r["id"], sc, r.get("status", "?"),
        r.get("type", "?"), r.get("board_size", "?"), r.get("viewport_size", "?"),
        r.get("rating", "?"), r.get("to_play", "?"),
        board, r.get("original_hash", "N/A"), r.get("re_encoded_hash", "N/A"),
        r.get("black_stones", "?"), r.get("white_stones", "?"),
    )


CSS = (
    "body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #e0e0e0; }\n"
    "h1 { color: #e94560; }\n"
    ".summary { background: #16213e; padding: 16px; border-radius: 8px; margin-bottom: 24px; display: flex; gap: 20px; }\n"
    ".stat { text-align: center; padding: 8px 16px; }\n"
    ".stat .num { font-size: 2em; font-weight: bold; }\n"
    ".stat.pass .num { color: #4caf50; }\n"
    ".stat.fail .num { color: #f44336; }\n"
    ".stat.error .num { color: #ff9800; }\n"
    ".result { background: #16213e; border-radius: 8px; margin-bottom: 16px; padding: 16px; border-left: 4px solid #666; }\n"
    ".result.pass { border-left-color: #4caf50; }\n"
    ".result.fail { border-left-color: #f44336; }\n"
    ".result.error { border-left-color: #ff9800; }\n"
    ".result-header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }\n"
    ".puzzle-id { font-family: monospace; font-size: 1.2em; font-weight: bold; }\n"
    ".status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; }\n"
    ".status-badge.pass { background: #4caf50; color: white; }\n"
    ".status-badge.fail { background: #f44336; color: white; }\n"
    ".status-badge.error { background: #ff9800; color: white; }\n"
    ".meta { color: #888; font-size: 0.85em; }\n"
    ".result-body { display: flex; gap: 20px; align-items: flex-start; }\n"
    ".board-grid { display: grid; gap: 1px; background: #333; padding: 2px; border-radius: 4px; }\n"
    ".cell { width: 20px; height: 20px; border-radius: 50%; }\n"
    ".cell.black { background: #222; border: 1px solid #555; }\n"
    ".cell.white { background: #fff; border: 1px solid #ccc; }\n"
    ".cell.empty { background: transparent; border: 1px solid #444; border-radius: 0; }\n"
    ".hash-info code { word-break: break-all; color: #64ffda; }"
)


def generate_verification_html(results):
    rows_html = "\n".join(_make_result_html(r) for r in results)
    pc = sum(1 for r in results if r.get("status", "").startswith("PASS"))
    fc = sum(1 for r in results if r.get("status") == "FAIL")
    ec = sum(1 for r in results if r.get("status") == "ERROR")
    sk = sum(1 for r in results if r.get("status") == "SKIP")
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

    return (
        "<!DOCTYPE html>\n<html><head><meta charset=\"UTF-8\">\n"
        "<title>BTP Hash Decode Verification</title>\n"
        "<style>%s</style></head>\n<body>\n"
        "<h1>BTP Hash Decode Verification</h1>\n"
        "<p>Generated: %s</p>\n"
        '<div class="summary">\n'
        '<div class="stat pass"><div class="num">%d</div>PASS</div>\n'
        '<div class="stat fail"><div class="num">%d</div>FAIL</div>\n'
        '<div class="stat error"><div class="num">%d</div>ERROR</div>\n'
        '<div class="stat"><div class="num">%d</div>SKIP</div>\n'
        '<div class="stat"><div class="num">%d</div>TOTAL</div>\n'
        "</div>\n%s\n</body></html>"
    ) % (CSS, ts, pc, fc, ec, sk, len(results), rows_html)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    puzzle_list = fetch_puzzle_list()
    print("Loaded %d puzzles" % len(puzzle_list))

    test_puzzles = select_diverse_puzzles(puzzle_list, count_per_type=3)
    print("\nSelected %d puzzles for testing:" % len(test_puzzles))
    for p in test_puzzles:
        print("  {} (type={}, rating={})".format(p["id"], p["type"], p["rating"]))

    results = []
    for i, p in enumerate(test_puzzles):
        pid = p["id"]
        print("\n[%d/%d] Testing %s..." % (i + 1, len(test_puzzles), pid), end=" ")
        try:
            data = fetch_puzzle_data(pid)
            result = run_round_trip_test(pid, data)
            print(result["status"])
            results.append(result)
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "id": pid, "status": "ERROR", "error": str(e),
                "type": p["type"], "board_size": "?", "rating": p["rating"],
            })
        time.sleep(0.5)

    results_file = OUTPUT_DIR / "hash_verification_results.json"
    results_file.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {results_file}")

    html = generate_verification_html(results)
    html_file = OUTPUT_DIR / "hash_verification.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"HTML report saved to {html_file}")

    pc = sum(1 for r in results if r["status"].startswith("PASS"))
    fc = sum(1 for r in results if r["status"] == "FAIL")
    ec = sum(1 for r in results if r["status"] == "ERROR")
    print("\n" + "=" * 60)
    print("SUMMARY: %d/%d PASS, %d FAIL, %d ERROR" % (pc, len(results), fc, ec))
    print("=" * 60)

    if fc > 0:
        print("\nFailed puzzles:")
        for r in results:
            if r["status"] == "FAIL":
                print("  {}: mismatches={}".format(r["id"], r.get("mismatch_count", "?")))

    return 0 if fc == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
