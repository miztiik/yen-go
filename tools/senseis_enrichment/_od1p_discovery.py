"""Discovery crawl for One Day 1 Problem (OD1P) collection on Sensei's Library.

Fetches the index page and each individual problem page to catalog:
- Page existence / HTTP status
- Difficulty, keywords, instruction, attributions
- Diagram SGF URLs
- Solution/Failure sub-page availability
- Cross-references (goproblems.com, classical collections)

Output: _working/one-day-1-problem/_crawl_results.json
        _working/one-day-1-problem/_crawl_summary.md

Usage:
    python -m tools.senseis_enrichment._od1p_discovery [--no-cache]
"""

from __future__ import annotations

import json
import logging
import random
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("od1p_discovery")

_SCRIPT_DIR = Path(__file__).parent
_WORKING_DIR = _SCRIPT_DIR / "_working" / "one-day-1-problem"

BASE_URL = "https://senseis.xmp.net"
INDEX_PAGE = "/?OneDay1Problem"

# All candidate date-based page names (May, July, Aug series)
CANDIDATE_PAGES: list[str] = (
    [f"OD1PMay{d}Problem" for d in [22, 23]]
    + [f"OD1PJuly{d}Problem" for d in range(26, 32)]
    + [f"OD1PAug{d}Problem" for d in range(1, 26)]
)

RATE_LIMIT_SEC = 3.0
RATE_LIMIT_JITTER = 1.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class OD1PProblemInfo:
    page_name: str
    url: str
    status: str = "unknown"  # "ok", "404", "error"
    difficulty: str = ""
    keywords: list[str] = field(default_factory=list)
    instruction: str = ""
    diagram_sgf_url: str = ""
    source_attribution: str = ""
    goproblems_url: str = ""
    has_solution_page: bool = False
    has_failure_page: bool = False
    has_attempts_page: bool = False
    commentary_snippet: str = ""


def _rate_limited_get(
    client: httpx.Client, url: str, last_time: float
) -> tuple[httpx.Response | None, float]:
    """GET with rate limiting. Returns (response | None, timestamp)."""
    now = time.monotonic()
    delay = RATE_LIMIT_SEC + random.uniform(0, RATE_LIMIT_JITTER)
    if (now - last_time) < delay:
        time.sleep(delay - (now - last_time))

    logger.info("GET %s", url)
    try:
        resp = client.get(url)
        if resp.status_code == 404:
            logger.info("  -> 404")
            return None, time.monotonic()
        resp.raise_for_status()
        return resp, time.monotonic()
    except httpx.HTTPError as e:
        logger.error("  -> Error: %s", e)
        return None, time.monotonic()


def _parse_problem_page(html: str, page_name: str) -> OD1PProblemInfo:
    """Extract key fields from a problem page HTML."""
    info = OD1PProblemInfo(
        page_name=page_name,
        url=f"{BASE_URL}/?{page_name}",
        status="ok",
    )

    # Difficulty: "Difficulty: Advanced" in page headers
    diff_match = re.search(
        r'header=difficulty[^"]*term=([^"]+)', html, re.IGNORECASE
    )
    if diff_match:
        info.difficulty = diff_match.group(1).strip()

    # Keywords from header links
    kw_matches = re.findall(
        r'header=keywords[^"]*term=([^"]+)', html, re.IGNORECASE
    )
    info.keywords = [kw.strip().replace("+", " ") for kw in kw_matches]

    # Diagram SGF URL (relative paths like "diagrams/11/hash.sgf")
    sgf_match = re.search(r'href="(diagrams/[^"]+\.sgf)"', html)
    if sgf_match:
        info.diagram_sgf_url = f"{BASE_URL}/{sgf_match.group(1)}"

    # Instruction text near the diagram (e.g., "Black to play and live")
    instr_match = re.search(
        r'\.sgf[^>]*>.*?</a>\s*(.*?)(?:<br|<p|<div|<h[234])',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if instr_match:
        raw = re.sub(r"<[^>]+>", "", instr_match.group(1)).strip()
        if raw and len(raw) < 200:
            info.instruction = raw

    # Goproblems.com link
    gp_match = re.search(r'(https?://(?:www\.)?goproblems\.com/problems/\d+)', html)
    if gp_match:
        info.goproblems_url = gp_match.group(1)

    # Source attribution (look for known collection names)
    for pattern, label in [
        (r"Xuanxuan\s+Qi(?:jing)?", "Xuanxuan Qijing"),
        (r"Gokyo\s+Shumyo", "Gokyo Shumyo"),
        (r"Kessaku\s+Tsumego\s+Jiten", "Kessaku Tsumego Jiten"),
        (r"Dictionary\s+of\s+Tsumego\s+Masterpieces", "Kessaku Tsumego Jiten"),
    ]:
        if re.search(pattern, html, re.IGNORECASE):
            info.source_attribution = label
            break

    # Sub-page detection (Solution, Failure, Attempts links)
    lower = html.lower()
    info.has_solution_page = "/solution" in lower or "%2fsolution" in lower
    info.has_failure_page = "/failure" in lower or "%2ffailure" in lower
    info.has_attempts_page = "/attempts" in lower or "%2fattempts" in lower

    return info


def run_discovery(use_cache: bool = True) -> list[OD1PProblemInfo]:
    """Crawl all candidate OD1P pages and collect metadata."""
    _WORKING_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _WORKING_DIR / "_crawl_results.json"

    if use_cache and cache_path.exists():
        logger.info("Loading cached crawl results from %s", cache_path)
        with open(cache_path, encoding="utf-8") as f:
            raw = json.load(f)
        return [OD1PProblemInfo(**entry) for entry in raw]

    results: list[OD1PProblemInfo] = []
    last_time = 0.0

    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        for page_name in CANDIDATE_PAGES:
            url = f"{BASE_URL}/?{page_name}"
            resp, last_time = _rate_limited_get(client, url, last_time)

            if resp is None:
                results.append(
                    OD1PProblemInfo(
                        page_name=page_name, url=url, status="404"
                    )
                )
                continue

            info = _parse_problem_page(resp.text, page_name)
            results.append(info)

    # Save cache
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)
    logger.info("Saved %d results to %s", len(results), cache_path)

    return results


def write_summary(results: list[OD1PProblemInfo]) -> None:
    """Write a human-readable crawl summary."""
    ok = [r for r in results if r.status == "ok"]
    missing = [r for r in results if r.status == "404"]

    lines = [
        "# OD1P Discovery Crawl Summary\n",
        f"**Candidates probed**: {len(results)}",
        f"**Pages found**: {len(ok)}",
        f"**Pages 404**: {len(missing)}",
        "",
        "## Found Problems\n",
        "| # | Page | Difficulty | Keywords | Instruction | Diagram | GP | Source | Sol | Fail | Att |",
        "|---|------|-----------|----------|-------------|---------|----|----|-----|------|-----|",
    ]

    for i, r in enumerate(ok, 1):
        kw = ", ".join(r.keywords) if r.keywords else "—"
        dgm = "✓" if r.diagram_sgf_url else "—"
        gp = f"[GP]({r.goproblems_url})" if r.goproblems_url else "—"
        src = r.source_attribution or "—"
        sol = "✓" if r.has_solution_page else "—"
        fail = "✓" if r.has_failure_page else "—"
        att = "✓" if r.has_attempts_page else "—"
        diff = r.difficulty or "—"
        instr = r.instruction[:40] if r.instruction else "—"
        lines.append(
            f"| {i} | {r.page_name} | {diff} | {kw} | {instr} | {dgm} | {gp} | {src} | {sol} | {fail} | {att} |"
        )

    if missing:
        lines.extend(["", "## Not Found (404)\n"])
        for r in missing:
            lines.append(f"- {r.page_name}")

    # Stats
    with_diff = sum(1 for r in ok if r.difficulty)
    with_sol = sum(1 for r in ok if r.has_solution_page)
    with_fail = sum(1 for r in ok if r.has_failure_page)
    with_gp = sum(1 for r in ok if r.goproblems_url)
    with_src = sum(1 for r in ok if r.source_attribution)

    lines.extend([
        "",
        "## Stats\n",
        f"- Difficulty labeled: {with_diff}/{len(ok)}",
        f"- Has solution page: {with_sol}/{len(ok)}",
        f"- Has failure page: {with_fail}/{len(ok)}",
        f"- GP cross-ref: {with_gp}/{len(ok)}",
        f"- Source attribution: {with_src}/{len(ok)}",
    ])

    summary_path = _WORKING_DIR / "_crawl_summary.md"
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Summary written to %s", summary_path)


def main() -> None:
    use_cache = "--no-cache" not in sys.argv
    results = run_discovery(use_cache=use_cache)
    write_summary(results)

    ok = [r for r in results if r.status == "ok"]
    print(f"\nDiscovery complete: {len(ok)} problems found out of {len(results)} candidates.")
    print(f"Results: {_WORKING_DIR / '_crawl_results.json'}")
    print(f"Summary: {_WORKING_DIR / '_crawl_summary.md'}")


if __name__ == "__main__":
    main()
