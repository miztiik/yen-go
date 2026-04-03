"""Playwright screenshot verification of BTP hash decode results.

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
