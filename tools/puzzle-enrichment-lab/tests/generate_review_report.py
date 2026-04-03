"""Generate an HTML review report from enrichment benchmark results.

Standalone utility (NOT a pytest test). Run directly:

    python tests/generate_review_report.py output/benchmark-fresh

Reads JSON results + SGF fixtures, renders SVG Go boards for Go expert review,
and writes a self-contained HTML file to the output directory.
"""
from __future__ import annotations

# Guard against accidental pytest collection
__test__ = False

import json
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path

# ---------------------------------------------------------------------------
# Config loaders (resolve numeric IDs → human-readable names)
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

# Load enrichment config for quality gate thresholds
_LAB_DIR = Path(__file__).resolve().parent.parent
if str(_LAB_DIR) not in sys.path:
    sys.path.insert(0, str(_LAB_DIR))
from config import load_enrichment_config as _load_enrichment_config

_ENRICHMENT_CFG = _load_enrichment_config()


def _load_tag_lookup() -> dict[int, str]:
    """Load config/tags.json → {10: "Life & Death", ...}."""
    tags_path = CONFIG_DIR / "tags.json"
    if not tags_path.exists():
        return {}
    data = json.loads(tags_path.read_text(encoding="utf-8"))
    return {
        tag["id"]: tag["name"]
        for tag in data.get("tags", {}).values()
        if "id" in tag and "name" in tag
    }


def _load_level_lookup() -> dict[int, dict]:
    """Load config/puzzle-levels.json → {110: {slug, name, rankRange}, ...}."""
    levels_path = CONFIG_DIR / "puzzle-levels.json"
    if not levels_path.exists():
        return {}
    data = json.loads(levels_path.read_text(encoding="utf-8"))
    return {
        lv["id"]: {
            "slug": lv["slug"],
            "name": lv["name"],
            "rank": f'{lv["rankRange"]["min"]}–{lv["rankRange"]["max"]}',
        }
        for lv in data.get("levels", [])
        if "id" in lv
    }


TAG_LOOKUP = _load_tag_lookup()
LEVEL_LOOKUP = _load_level_lookup()


def tag_name(tag_id: int) -> str:
    return TAG_LOOKUP.get(tag_id, f"tag#{tag_id}")


def level_name(level_id: int) -> str:
    info = LEVEL_LOOKUP.get(level_id)
    if info:
        return f'{info["name"]} ({info["rank"]})'
    return f"level#{level_id}"


def level_slug(level_id: int) -> str:
    info = LEVEL_LOOKUP.get(level_id)
    return info["slug"] if info else "unknown"


# ---------------------------------------------------------------------------
# SGF parsing (shared utilities)
# ---------------------------------------------------------------------------

from _sgf_render_utils import parse_all_stones, parse_first_move, parse_sgf_properties

# ---------------------------------------------------------------------------
# SVG Go board renderer
# ---------------------------------------------------------------------------

BOARD_SIZE_PX = 320
MARGIN = 24
STAR_POINTS_19 = [(3, 3), (9, 3), (15, 3), (3, 9), (9, 9), (15, 9), (3, 15), (9, 15), (15, 15)]
STAR_POINTS_9 = [(2, 2), (6, 2), (4, 4), (2, 6), (6, 6)]
STAR_POINTS_13 = [(3, 3), (9, 3), (6, 6), (3, 9), (9, 9)]


def _star_points(size: int) -> list[tuple[int, int]]:
    if size == 19:
        return STAR_POINTS_19
    if size == 13:
        return STAR_POINTS_13
    if size == 9:
        return STAR_POINTS_9
    return []


def render_svg_board(
    size: int,
    black: list[tuple[int, int]],
    white: list[tuple[int, int]],
    correct_move: tuple[str, tuple[int, int] | None] | None = None,
    katago_move_gtp: str = "",
) -> str:
    """Render a Go board position as an SVG string.

    Parameters
    ----------
    size : Board size (9, 13, or 19).
    black : List of (x, y) for black stones.
    white : List of (x, y) for white stones.
    correct_move : ("B"/"W", (x, y)) for the correct first move marker.
    katago_move_gtp : GTP coordinate of KataGo's top move (e.g. "D4").
    """
    cell = (BOARD_SIZE_PX - 2 * MARGIN) / (size - 1)
    total = BOARD_SIZE_PX

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{total}" height="{total}" '
        f'style="background:#DCB35C;border-radius:4px">'
    )

    # Grid lines
    for i in range(size):
        x = MARGIN + i * cell
        y = MARGIN + i * cell
        parts.append(f'<line x1="{x}" y1="{MARGIN}" x2="{x}" y2="{MARGIN + (size-1)*cell}" stroke="#222" stroke-width="0.8"/>')
        parts.append(f'<line x1="{MARGIN}" y1="{y}" x2="{MARGIN + (size-1)*cell}" y2="{y}" stroke="#222" stroke-width="0.8"/>')

    # Star points
    for sx, sy in _star_points(size):
        cx = MARGIN + sx * cell
        cy = MARGIN + sy * cell
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="2.5" fill="#222"/>')

    # Coordinate labels
    col_labels = "ABCDEFGHJKLMNOPQRST"
    for i in range(size):
        lx = MARGIN + i * cell
        parts.append(f'<text x="{lx}" y="12" text-anchor="middle" font-size="9" fill="#555" font-family="monospace">{col_labels[i]}</text>')
        parts.append(f'<text x="{lx}" y="{total - 4}" text-anchor="middle" font-size="9" fill="#555" font-family="monospace">{col_labels[i]}</text>')
    for i in range(size):
        ly = MARGIN + i * cell
        row_num = size - i
        parts.append(f'<text x="6" y="{ly + 3}" text-anchor="middle" font-size="9" fill="#555" font-family="monospace">{row_num}</text>')
        parts.append(f'<text x="{total - 6}" y="{ly + 3}" text-anchor="middle" font-size="9" fill="#555" font-family="monospace">{row_num}</text>')

    # Stones
    r = cell * 0.44
    for x, y in black:
        cx = MARGIN + x * cell
        cy = MARGIN + y * cell
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#111" stroke="#000" stroke-width="0.5"/>')
    for x, y in white:
        cx = MARGIN + x * cell
        cy = MARGIN + y * cell
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#f8f8f0" stroke="#333" stroke-width="0.8"/>')

    # Correct first move marker (green triangle)
    if correct_move and correct_move[1]:
        color, (mx, my) = correct_move
        cx = MARGIN + mx * cell
        cy = MARGIN + my * cell
        marker_r = r * 0.6
        parts.append(
            f'<polygon points="{cx},{cy - marker_r} {cx - marker_r*0.87},{cy + marker_r*0.5} {cx + marker_r*0.87},{cy + marker_r*0.5}" '
            f'fill="#2e7d32" stroke="#1b5e20" stroke-width="1" opacity="0.9"/>'
        )

    # KataGo top move marker (red diamond) — only if different from correct
    if katago_move_gtp:
        katago_coord = _gtp_to_xy(katago_move_gtp, size)
        correct_xy = correct_move[1] if correct_move else None
        if katago_coord and katago_coord != correct_xy:
            kx, ky = katago_coord
            cx = MARGIN + kx * cell
            cy = MARGIN + ky * cell
            d = r * 0.5
            parts.append(
                f'<polygon points="{cx},{cy - d} {cx + d},{cy} {cx},{cy + d} {cx - d},{cy}" '
                f'fill="#c62828" stroke="#b71c1c" stroke-width="1" opacity="0.85"/>'
            )

    parts.append("</svg>")
    return "\n".join(parts)


def _gtp_to_xy(gtp: str, size: int) -> tuple[int, int] | None:
    """Convert GTP coordinate (e.g. 'D4') to (x, y) board coords."""
    if not gtp or len(gtp) < 2:
        return None
    col_letter = gtp[0].upper()
    col_labels = "ABCDEFGHJKLMNOPQRST"
    if col_letter not in col_labels:
        return None
    x = col_labels.index(col_letter)
    try:
        row = int(gtp[1:])
    except ValueError:
        return None
    y = size - row
    if 0 <= x < size and 0 <= y < size:
        return (x, y)
    return None


# ---------------------------------------------------------------------------
# Status badge colors
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "accepted": ("#2e7d32", "#c8e6c9"),  # green
    "flagged": ("#e65100", "#ffe0b2"),  # orange
    "rejected": ("#c62828", "#ffcdd2"),  # red
}

CONFIDENCE_COLORS = {
    "high": "#2e7d32",
    "medium": "#e65100",
    "low": "#c62828",
}


def _status_badge(status: str) -> str:
    fg, bg = STATUS_COLORS.get(status, ("#333", "#eee"))
    return f'<span class="badge" style="background:{bg};color:{fg}">{escape(status.upper())}</span>'


def _confidence_dot(confidence: str) -> str:
    color = CONFIDENCE_COLORS.get(confidence, "#999")
    return f'<span style="color:{color};font-weight:700">{escape(confidence)}</span>'


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


def _collect_results(output_dir: Path) -> list[dict]:
    """Collect all JSON results paired with SGF fixture data."""
    results: list[dict] = []
    for json_path in sorted(output_dir.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Find the corresponding SGF fixture
        sgf_path = output_dir / data.get("source_file", json_path.stem + ".sgf")
        sgf_text = ""
        if sgf_path.exists():
            sgf_text = sgf_path.read_text(encoding="utf-8")
        else:
            # Try perf-33 fixtures
            fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "perf-33"
            alt_sgf = fixtures_dir / data.get("source_file", json_path.stem + ".sgf")
            if alt_sgf.exists():
                sgf_text = alt_sgf.read_text(encoding="utf-8")

        results.append({"json": data, "sgf": sgf_text, "file": json_path.name})
    return results


def _build_summary(results: list[dict]) -> dict:
    """Compute summary statistics."""
    total = len(results)
    accepted = sum(1 for r in results if r["json"].get("validation", {}).get("status") == "accepted")
    flagged = sum(1 for r in results if r["json"].get("validation", {}).get("status") == "flagged")
    rejected = sum(1 for r in results if r["json"].get("validation", {}).get("status") == "rejected")
    pass_rate = (accepted + flagged) / total * 100 if total else 0
    accept_rate = accepted / total * 100 if total else 0

    run_ids = {r["json"].get("run_id", "") for r in results}
    run_ids.discard("")
    trace_ids = [r["json"].get("trace_id", "") for r in results if r["json"].get("trace_id")]

    # Model info
    models = {r["json"].get("engine", {}).get("model", "") for r in results}
    models.discard("")

    # Confidence breakdown
    confidences = {"high": 0, "medium": 0, "low": 0}
    for r in results:
        conf = r["json"].get("difficulty", {}).get("confidence", "low")
        confidences[conf] = confidences.get(conf, 0) + 1

    return {
        "total": total,
        "accepted": accepted,
        "flagged": flagged,
        "rejected": rejected,
        "pass_rate": pass_rate,
        "accept_rate": accept_rate,
        "run_ids": sorted(run_ids),
        "trace_count": len(trace_ids),
        "unique_traces": len(set(trace_ids)),
        "models": sorted(models),
        "confidences": confidences,
    }


def _render_puzzle_card(result: dict, index: int) -> str:
    """Render a single puzzle card as HTML."""
    data = result["json"]
    sgf = result["sgf"]
    v = data.get("validation", {})
    d = data.get("difficulty", {})
    e = data.get("engine", {})
    refs = data.get("refutations", [])

    status = v.get("status", "unknown")
    puzzle_id = data.get("puzzle_id", "unknown")

    # Parse SGF for board rendering
    props = parse_sgf_properties(sgf) if sgf else {}
    size = int(props.get("SZ", "19"))
    black, white = parse_all_stones(sgf) if sgf else ([], [])
    first_color, first_coord = parse_first_move(sgf) if sgf else ("?", None)
    correct_move = (first_color, first_coord) if first_coord else None

    # Tags
    tag_ids = data.get("tags", [])
    tag_names = [tag_name(t) for t in tag_ids]

    # Level
    suggested_level_id = d.get("suggested_level_id", 0)
    d.get("suggested_level", "unknown")

    svg = render_svg_board(
        size, black, white,
        correct_move=correct_move,
        katago_move_gtp=v.get("katago_top_move_gtp", ""),
    )

    # Flags as list
    flags = v.get("flags", [])
    flags_html = ""
    if flags:
        flags_html = '<div class="flags">' + " ".join(
            f'<span class="flag-chip">{escape(f)}</span>' for f in flags
        ) + "</div>"

    # Refutations
    refutation_html = ""
    if refs:
        rows = "".join(
            f'<tr><td><code>{escape(r.get("wrong_move", ""))}</code></td>'
            f'<td>{r.get("refutation_depth", 0)}</td>'
            f'<td>{r.get("delta", 0):.3f}</td>'
            f'<td><code>{" ".join(r.get("refutation_pv", []))}</code></td></tr>'
            for r in refs
        )
        refutation_html = f"""
        <details class="refutation-details">
          <summary>Refutations ({len(refs)})</summary>
          <table class="mini-table">
            <tr><th>Wrong move</th><th>Depth</th><th>Delta</th><th>PV</th></tr>
            {rows}
          </table>
        </details>"""

    return f"""
    <div class="puzzle-card status-{escape(status)}" id="puzzle-{index}">
      <div class="card-header">
        <span class="puzzle-number">#{index + 1}</span>
        <span class="puzzle-id">{escape(puzzle_id)}</span>
        {_status_badge(status)}
      </div>
      <div class="card-body">
        <div class="board-col">
          {svg}
          <div class="board-meta">
            {size}&times;{size} &middot; {escape(first_color)} to play &middot;
            Correct: <code>{escape(v.get("correct_move_gtp", "?"))}</code>
            {' &middot; KataGo: <code>' + escape(v.get("katago_top_move_gtp", "?")) + '</code>' if not v.get("katago_agrees") else ""}
          </div>
        </div>
        <div class="data-col">
          <table class="prop-table">
            <tr><th>KataGo agrees</th><td>{"Yes &#10004;" if v.get("katago_agrees") else '<span class="disagree">No &#10008;</span>'}</td></tr>
            <tr><th>Winrate</th><td>{v.get("correct_move_winrate", 0):.1%}</td></tr>
            <tr><th>Policy</th><td>{v.get("correct_move_policy", 0):.1%}</td></tr>
            <tr><th>Validator</th><td><code>{escape(v.get("validator_used", ""))}</code></td></tr>
            <tr><th>Tags</th><td>{escape(", ".join(tag_names)) if tag_names else "<em>none</em>"}</td></tr>
            <tr><th>Corner</th><td>{escape(data.get("corner", "?"))}</td></tr>
            <tr><th>Move order</th><td>{escape(data.get("move_order", "?"))}</td></tr>
          </table>
          <div class="difficulty-box">
            <strong>Difficulty:</strong>
            {escape(level_name(suggested_level_id))}
            &middot; {_confidence_dot(d.get("confidence", "low"))} confidence
            <br/>
            <small>
              Composite: {d.get("composite_score", 0):.1f}
              &middot; Trap density: {d.get("trap_density", 0):.2f}
              &middot; Visits to solve: {d.get("visits_to_solve", 0)}
            </small>
          </div>
          <div class="trace-box">
            <small>
              trace_id: <code>{escape(data.get("trace_id", ""))}</code>
              &middot; model: <code>{escape(e.get("model", ""))}</code>
              &middot; visits: {e.get("visits", 0)}
            </small>
          </div>
          {flags_html}
          {refutation_html}
        </div>
      </div>
    </div>
    """


CSS = """
:root {
  --bg: #fafafa;
  --card-bg: #fff;
  --border: #ddd;
  --text: #222;
  --muted: #666;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: var(--bg); color: var(--text); padding: 20px; max-width: 1200px; margin: 0 auto; }
h1 { font-size: 1.6rem; margin-bottom: 8px; }
.subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 20px; }

/* Summary */
.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
.summary-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }
.summary-card .value { font-size: 1.8rem; font-weight: 700; }
.summary-card .label { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; }
.pass-rate .value { color: #2e7d32; }
.accept-rate .value { color: #1565c0; }

/* Legend */
.legend { display: flex; gap: 16px; align-items: center; padding: 10px 16px; background: var(--card-bg);
          border: 1px solid var(--border); border-radius: 8px; margin-bottom: 24px; font-size: 0.85rem; }
.legend svg { vertical-align: middle; }

/* Filter buttons */
.filter-bar { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.filter-btn { border: 1px solid var(--border); background: var(--card-bg); border-radius: 16px;
              padding: 6px 16px; cursor: pointer; font-size: 0.85rem; transition: all 0.15s; }
.filter-btn:hover { background: #e8e8e8; }
.filter-btn.active { background: #333; color: #fff; border-color: #333; }

/* Puzzle cards */
.puzzle-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
               margin-bottom: 16px; overflow: hidden; transition: box-shadow 0.15s; }
.puzzle-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
.card-header { display: flex; align-items: center; gap: 10px; padding: 10px 16px;
               border-bottom: 1px solid var(--border); background: #f7f7f7; }
.puzzle-number { font-weight: 700; color: var(--muted); font-size: 0.9rem; }
.puzzle-id { font-family: monospace; font-size: 0.9rem; }
.badge { padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px; }
.card-body { display: flex; gap: 20px; padding: 16px; flex-wrap: wrap; }
.board-col { flex: 0 0 auto; }
.board-meta { font-size: 0.8rem; color: var(--muted); margin-top: 6px; text-align: center; }
.data-col { flex: 1; min-width: 280px; }
.prop-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-bottom: 10px; }
.prop-table th { text-align: left; padding: 3px 8px 3px 0; color: var(--muted); font-weight: 500; white-space: nowrap; width: 100px; }
.prop-table td { padding: 3px 0; }
.disagree { color: #c62828; font-weight: 700; }
code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 0.85em; }
.difficulty-box { background: #f5f5f5; padding: 8px 12px; border-radius: 6px; margin-bottom: 8px; font-size: 0.85rem; }
.trace-box { font-size: 0.8rem; color: var(--muted); margin-bottom: 6px; }
.flags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; }
.flag-chip { background: #fff3e0; border: 1px solid #ffe0b2; padding: 2px 8px; border-radius: 10px; font-size: 0.75rem; font-family: monospace; }
.refutation-details { font-size: 0.85rem; }
.refutation-details summary { cursor: pointer; color: #1565c0; font-weight: 500; }
.mini-table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 0.8rem; }
.mini-table th, .mini-table td { padding: 3px 8px; border-bottom: 1px solid #eee; text-align: left; }
.mini-table th { color: var(--muted); }

/* Status left-border accents */
.status-accepted { border-left: 4px solid #2e7d32; }
.status-flagged  { border-left: 4px solid #e65100; }
.status-rejected { border-left: 4px solid #c62828; }

/* Hidden state for filters */
.puzzle-card.hidden { display: none; }

/* Gate badge */
.gate-result { font-size: 1.2rem; font-weight: 700; padding: 8px 20px; border-radius: 8px; display: inline-block; margin: 12px 0; }
.gate-pass { background: #c8e6c9; color: #2e7d32; }
.gate-fail { background: #ffcdd2; color: #c62828; }
"""

SCRIPT = """
document.addEventListener('DOMContentLoaded', () => {
  const btns = document.querySelectorAll('.filter-btn');
  const cards = document.querySelectorAll('.puzzle-card');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;
      cards.forEach(card => {
        if (filter === 'all') { card.classList.remove('hidden'); }
        else { card.classList.toggle('hidden', !card.classList.contains('status-' + filter)); }
      });
    });
  });
});
"""


def generate_report(output_dir: Path) -> str:
    """Generate the full HTML report string."""
    results = _collect_results(output_dir)
    if not results:
        return "<html><body><h1>No results found</h1></body></html>"

    summary = _build_summary(results)
    acceptance_threshold = _ENRICHMENT_CFG.quality_gates.acceptance_threshold
    gate_pass = (summary["accept_rate"] / 100) >= acceptance_threshold or (summary["pass_rate"] / 100) >= acceptance_threshold

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Build puzzle cards
    cards_html = "\n".join(_render_puzzle_card(r, i) for i, r in enumerate(results))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Enrichment Benchmark Report</title>
<style>{CSS}</style>
</head>
<body>
<h1>KataGo Enrichment Benchmark Report</h1>
<p class="subtitle">
  Generated: {now}
  &middot; Run ID: <code>{escape(", ".join(summary["run_ids"]) if summary["run_ids"] else "N/A")}</code>
  &middot; Model: <code>{escape(", ".join(summary["models"]) if summary["models"] else "N/A")}</code>
  &middot; Schema v{results[0]["json"].get("schema_version", "?")}
</p>

<!-- Summary Cards -->
<div class="summary-grid">
  <div class="summary-card">
    <div class="value">{summary["total"]}</div>
    <div class="label">Total Puzzles</div>
  </div>
  <div class="summary-card">
    <div class="value" style="color:#2e7d32">{summary["accepted"]}</div>
    <div class="label">Accepted</div>
  </div>
  <div class="summary-card">
    <div class="value" style="color:#e65100">{summary["flagged"]}</div>
    <div class="label">Flagged</div>
  </div>
  <div class="summary-card">
    <div class="value" style="color:#c62828">{summary["rejected"]}</div>
    <div class="label">Rejected</div>
  </div>
  <div class="summary-card accept-rate">
    <div class="value">{summary["accept_rate"]:.0f}%</div>
    <div class="label">Accept Rate</div>
  </div>
  <div class="summary-card pass-rate">
    <div class="value">{summary["pass_rate"]:.0f}%</div>
    <div class="label">Pass Rate (A+F)</div>
  </div>
  <div class="summary-card">
    <div class="value">{summary["unique_traces"]}</div>
    <div class="label">Unique Traces</div>
  </div>
  <div class="summary-card">
    <div class="value">{summary["confidences"]["high"]}/{summary["confidences"]["medium"]}/{summary["confidences"]["low"]}</div>
    <div class="label">High/Med/Low Conf</div>
  </div>
</div>

<!-- Gate result -->
<div style="text-align:center">
  <div class="gate-result {"gate-pass" if gate_pass else "gate-fail"}">
    {"GATE PASS" if gate_pass else "GATE FAIL"} &mdash;
    Accept rate {summary["accept_rate"]:.0f}% / Pass rate {summary["pass_rate"]:.0f}%
    (threshold: {acceptance_threshold:.0%})
  </div>
</div>

<!-- Legend -->
<div class="legend">
  <span><svg width="14" height="14"><polygon points="7,2 2,12 12,12" fill="#2e7d32"/></svg> Correct first move</span>
  <span><svg width="14" height="14"><polygon points="7,2 12,7 7,12 2,7" fill="#c62828"/></svg> KataGo top move (when different)</span>
</div>

<!-- Filter bar -->
<div class="filter-bar">
  <button class="filter-btn active" data-filter="all">All ({summary["total"]})</button>
  <button class="filter-btn" data-filter="accepted">Accepted ({summary["accepted"]})</button>
  <button class="filter-btn" data-filter="flagged">Flagged ({summary["flagged"]})</button>
  <button class="filter-btn" data-filter="rejected">Rejected ({summary["rejected"]})</button>
</div>

<!-- Puzzle Cards -->
{cards_html}

<script>{SCRIPT}</script>
</body>
</html>"""
    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python tests/generate_review_report.py <output-dir>")
        print("Example: python tests/generate_review_report.py output/benchmark-fresh")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    if not output_dir.is_dir():
        print(f"Error: {output_dir} is not a directory")
        sys.exit(1)

    html = generate_report(output_dir)
    report_path = output_dir / "review-report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"Report written to {report_path}")
    print(f"Open in browser: file:///{report_path.resolve().as_posix()}")


if __name__ == "__main__":
    main()
