"""HTML parsers for Harada tsumego archive pages.

Parses three page types:
1. Index page — extracts year links with problem ranges
2. Year page — extracts individual problem/answer URLs with dates
3. Problem/Answer page — extracts board images and text content

All parsers return structured data models. BeautifulSoup is used
for HTML parsing, following the senseis_enrichment pattern.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from tools.minoru_harada_tsumego.models import PuzzleEntry, PuzzleImage, YearEntry


# --- URL Utilities ---


def extract_original_url(wayback_url: str) -> str:
    """Extract original URL from a Wayback Machine URL.

    Example:
        /web/20230319095212/https://www.hitachi.co.jp/Sp/tsumego/past/2019-e.html
        → https://www.hitachi.co.jp/Sp/tsumego/past/2019-e.html
    """
    # Match: /web/{timestamp}/{modifier}/{original_url}
    # Modifiers: if_ (iframe), im_ (image), js_ (javascript), cs_ (css), etc.
    match = re.search(r"/web/\d+(?:[a-z]{2}_)?/(https?://.*)", wayback_url)
    if match:
        return match.group(1)

    # Match: relative (no scheme) with wayback prefix
    match = re.search(r"/web/\d+(?:[a-z]{2}_)?/(.*)", wayback_url)
    if match:
        return match.group(1)

    return wayback_url


def extract_wayback_timestamp(wayback_url: str) -> str:
    """Extract timestamp from a Wayback Machine URL.

    Example:
        /web/20230319095212/https://www.hitachi.co.jp/...
        → 20230319095212
    """
    match = re.search(r"/web/(\d{14})", wayback_url)
    return match.group(1) if match else ""


def normalize_original_url(url: str, base_url: str) -> str:
    """Ensure an original URL has full scheme + host."""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    # Relative URL — prepend base
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if url.startswith("/"):
        return base + url
    return base + "/" + url


# --- Index Page Parser ---


def parse_index_page(html: str) -> list[YearEntry]:
    """Parse the main index page to extract year links.

    The index page has links like:
        <a href="/web/.../past/2019-e.html">2019 (No.1165 - No.1182)</a>

    Returns list of YearEntry with year, URL, and problem range.
    """
    soup = BeautifulSoup(html, "html.parser")
    years: list[YearEntry] = []
    seen_years: set[int] = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = link.get_text(strip=True)

        # Match year page links like "2019  (No.1165 - No.1182)" or just "2019"
        year_match = re.match(r"^(\d{4})\s*(?:\((.+?)\))?$", text)
        if not year_match:
            continue

        # Verify the href points to a year page
        if "/past/" not in href or "-e.html" not in href:
            continue

        year = int(year_match.group(1))
        if year in seen_years:
            continue
        seen_years.add(year)

        problem_range = year_match.group(2) or ""
        original_url = extract_original_url(href)

        # Ensure full URL
        if not original_url.startswith("http"):
            original_url = f"http://www.hitachi.co.jp/Sp/tsumego/past/{year}-e.html"

        wayback_ts = extract_wayback_timestamp(href)

        years.append(YearEntry(
            year=year,
            original_url=original_url,
            wayback_url=href if href.startswith("http") else "",
            wayback_ts=wayback_ts,
            problem_range=problem_range.strip(),
        ))

    # Sort by year
    years.sort(key=lambda y: y.year)
    return years


# --- Year Page Helpers ---


def _extract_links(links: list[Tag]) -> tuple[str, str, str, str]:
    """Extract problem/answer URLs and timestamps from a list of <a> tags.

    Returns (problem_url, answer_url, problem_ts, answer_ts).
    """
    problem_url = ""
    answer_url = ""
    problem_ts = ""
    answer_ts = ""
    base = "http://www.hitachi.co.jp"

    for link in links:
        link_text = link.get_text(strip=True).lower()
        href = link["href"]

        if "problem" in link_text:
            problem_url = extract_original_url(href)
            problem_ts = extract_wayback_timestamp(href)
        elif "answer" in link_text:
            answer_url = extract_original_url(href)
            answer_ts = extract_wayback_timestamp(href)

    # Normalize URLs
    if problem_url and not problem_url.startswith("http"):
        problem_url = base + (problem_url if problem_url.startswith("/") else "/" + problem_url)
    if answer_url and not answer_url.startswith("http"):
        answer_url = base + (answer_url if answer_url.startswith("/") else "/" + answer_url)

    return problem_url, answer_url, problem_ts, answer_ts


def _make_full_date(year: int, date_str: str) -> str:
    """Convert 'M/D' date string to ISO format 'YYYY-MM-DD'."""
    if not date_str:
        return ""
    parts = date_str.split("/")
    if len(parts) == 2:
        month, day = int(parts[0]), int(parts[1])
        return f"{year}-{month:02d}-{day:02d}"
    return ""


def _make_entry(
    problem_number: int, year: int, date_str: str, full_date: str,
    problem_url: str, answer_url: str, problem_ts: str, answer_ts: str,
) -> PuzzleEntry:
    """Create a PuzzleEntry from parsed data."""
    return PuzzleEntry(
        problem_number=problem_number,
        year=year,
        date_str=date_str,
        full_date=full_date,
        problem_page_url=problem_url,
        answer_page_url=answer_url,
        problem_wayback_ts=problem_ts,
        answer_wayback_ts=answer_ts,
        status="discovered",
    )


# --- Year Page Parser ---


def parse_year_page(html: str, year: int) -> list[PuzzleEntry]:
    """Parse a year page to extract problem/answer links.

    Year pages have table cells with entries like:
        No.10 (6/24)
        <a href="/.../igo010/010pe.htm">Problems</a> &
        <a href="/.../igo011/010ae.htm">Answers</a>

    Newer format (post-~2015):
        No.1165 (1/7)
        <a href="/.../igo1165/problems-e.htm">Problems</a> &
        <a href="/.../igo1165/answers-e.htm">Answers</a>
    """
    soup = BeautifulSoup(html, "html.parser")
    puzzles: list[PuzzleEntry] = []
    seen_numbers: set[int] = set()

    # --- Strategy 1: Table-based layout (1996-2007) ---
    # Each <td> contains: No.{N} ({date}) <a>Problems</a> & <a>Answers</a>
    for td in soup.find_all("td"):
        td_text = td.get_text()
        num_match = re.search(r"No\.(\d+)", td_text)
        if not num_match:
            continue

        problem_number = int(num_match.group(1))
        if problem_number in seen_numbers:
            continue

        date_match = re.search(r"\((\d{1,2}/\d{1,2})\)", td_text)
        date_str = date_match.group(1) if date_match else ""

        links = td.find_all("a", href=True)
        problem_url, answer_url, problem_ts, answer_ts = _extract_links(links)
        if not problem_url and not answer_url:
            continue

        full_date = _make_full_date(year, date_str)
        seen_numbers.add(problem_number)
        puzzles.append(_make_entry(
            problem_number, year, date_str, full_date,
            problem_url, answer_url, problem_ts, answer_ts,
        ))

    # --- Strategy 2: Definition list layout (2008+) ---
    # <dl><dt>No.{N} ({date})</dt><dd><ul><li><a>Problems</a> & <a>Answers</a></li></ul></dd></dl>
    for dt in soup.find_all("dt"):
        dt_text = dt.get_text()
        num_match = re.search(r"No\.(\d+)", dt_text)
        if not num_match:
            continue

        problem_number = int(num_match.group(1))
        if problem_number in seen_numbers:
            continue

        date_match = re.search(r"\((\d{1,2}/\d{1,2})\)", dt_text)
        date_str = date_match.group(1) if date_match else ""

        # Find the corresponding <dd> sibling
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue

        links = dd.find_all("a", href=True)
        problem_url, answer_url, problem_ts, answer_ts = _extract_links(links)
        if not problem_url and not answer_url:
            continue

        full_date = _make_full_date(year, date_str)
        seen_numbers.add(problem_number)
        puzzles.append(_make_entry(
            problem_number, year, date_str, full_date,
            problem_url, answer_url, problem_ts, answer_ts,
        ))

    # Sort by problem number
    puzzles.sort(key=lambda p: p.problem_number)
    return puzzles


# --- Problem/Answer Page Parser ---


def parse_problem_page(html: str, problem_number: int) -> list[PuzzleImage]:
    """Parse a problem page to extract board images.

    Old format images:
        {NNN}ep.gif (elementary problem)
        {NNN}mp.gif (intermediate problem)

    New format may differ. We detect all tsumego-related images.
    """
    soup = BeautifulSoup(html, "html.parser")
    images: list[PuzzleImage] = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue

        # Extract original URL from wayback-wrapped src
        original = extract_original_url(src)
        if "igo" not in original.lower() and "tsumego" not in original.lower():
            continue

        # Skip navigation/decoration images
        if any(skip in original.lower() for skip in [
            "igohome", "igoup", "icon", "site_id", "sitename",
            "blank", "dot_", "common/", "images_igo/",
        ]):
            continue

        # Determine image type from filename
        filename = original.split("/")[-1].lower()
        level = ""
        img_type = ""

        # Pattern: {NNN}ep.gif or {NNN}mp.gif (standard problem format)
        if re.match(r"\d+ep\.", filename):
            level = "elementary"
            img_type = "problem"
        elif re.match(r"\d+mp\.", filename):
            level = "intermediate"
            img_type = "problem"
        # Old format (1996): {N}p{V}.gif / {N}c{V}.gif
        elif re.match(r"\d+[pc]\d+\.", filename):
            img_type = "problem"
        else:
            # Unrecognised filename — skip (e.g. space.gif, igotop.gif)
            continue

        images.append(PuzzleImage(
            url=original,
            image_type=img_type,
            level=level,
        ))

    return images


# --- Text cleanup for answer pages ---

# Footer/boilerplate patterns from Hitachi website pages
_FOOTER_PATTERNS = re.compile(
    r"(?:"
    r"page top"
    r"|Problems No\.\d+"
    r"|Answers No\.\d+"
    r"|Term of Use"
    r"|Privacy Policy"
    r"|Update History"
    r"|All Rights Reserved.*"
    r"|\u00a9\s*Hitachi.*"  # © Hitachi copyright
    r"|\xa9\s*Hitachi.*"    # same, alternate encoding
    r")",
    re.IGNORECASE,
)


def _clean_answer_text(raw: str) -> str:
    """Clean extracted answer text by removing footer boilerplate.

    Strips Hitachi website navigation/footer elements that leak through
    BeautifulSoup text extraction (pipe separators, "page top", copyright,
    "Term of Use", etc.).
    """
    lines = raw.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Skip empty lines, bare pipe separators, footer patterns
        if not stripped or stripped == "|":
            continue
        if _FOOTER_PATTERNS.search(stripped):
            continue
        cleaned.append(stripped)
    result = "\n".join(cleaned).strip()
    return result[:500] if result else ""


def parse_answer_page(html: str, problem_number: int) -> tuple[list[PuzzleImage], dict[str, str]]:
    """Parse an answer page to extract images and text.

    Old format images:
        {NNN}ea0.gif (elementary correct answer)
        {NNN}ew0.gif (elementary wrong answer)
        {NNN}ma0.gif (intermediate correct answer)
        {NNN}mw0.gif, {NNN}mw1.gif (intermediate wrong answers)

    Returns (images, texts) where texts has keys like
    'elementary_answer', 'intermediate_answer'.
    """
    soup = BeautifulSoup(html, "html.parser")
    images: list[PuzzleImage] = []
    texts: dict[str, str] = {}

    # Extract images
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue

        original = extract_original_url(src)
        if "igo" not in original.lower() and "tsumego" not in original.lower():
            continue

        # Skip navigation
        if any(skip in original.lower() for skip in [
            "igohome", "igoup", "icon", "site_id", "sitename",
            "blank", "dot_", "common/", "images_igo/",
        ]):
            continue

        filename = original.split("/")[-1].lower()
        level = ""
        img_type = ""
        variant = 0

        # Elementary correct: {NNN}ea{V}.gif
        ea_match = re.match(r"\d+ea(\d+)\.", filename)
        if ea_match:
            level = "elementary"
            img_type = "answer_correct"
            variant = int(ea_match.group(1))

        # Elementary wrong: {NNN}ew{V}.gif
        ew_match = re.match(r"\d+ew(\d+)\.", filename)
        if ew_match:
            level = "elementary"
            img_type = "answer_wrong"
            variant = int(ew_match.group(1))

        # Intermediate correct: {NNN}ma{V}.gif
        ma_match = re.match(r"\d+ma(\d+)\.", filename)
        if ma_match:
            level = "intermediate"
            img_type = "answer_correct"
            variant = int(ma_match.group(1))

        # Intermediate wrong: {NNN}mw{V}.gif
        mw_match = re.match(r"\d+mw(\d+)\.", filename)
        if mw_match:
            level = "intermediate"
            img_type = "answer_wrong"
            variant = int(mw_match.group(1))

        if not img_type:
            img_type = "answer_unknown"

        images.append(PuzzleImage(
            url=original,
            image_type=img_type,
            level=level,
            variant=variant,
        ))

    # Extract text content
    body_text = soup.get_text(separator="\n", strip=True)

    # Look for elementary/intermediate answer descriptions.
    # Two page formats exist:
    #   Early (1996-2003): "Elementary level: Answer" / "Elementary level: Variation" / ...
    #   Later (2004+): "Elementary level\nAnswer" with "page top" separator
    # Stop markers handle both formats.
    elem_match = re.search(
        r"Elementary level[:\s]*Answer\s*(.*?)"
        r"(?=Elementary level[:\s]*(?:Variation|Wrong)|Intermediate level|page top|Problems No|Answers No|$)",
        body_text,
        re.DOTALL | re.IGNORECASE,
    )
    if elem_match:
        texts["elementary_answer"] = _clean_answer_text(elem_match.group(1))

    inter_match = re.search(
        r"Intermediate level[:\s]*Answer\s*(.*?)"
        r"(?=Intermediate level[:\s]*(?:Variation|Wrong)|Answer \(Variation\)|page top|Problems No|Answers No|All Rights|$)",
        body_text,
        re.DOTALL | re.IGNORECASE,
    )
    if inter_match:
        texts["intermediate_answer"] = _clean_answer_text(inter_match.group(1))

    # Capture variation text separately (if present)
    for section in ["Elementary", "Intermediate"]:
        var_match = re.search(
            rf"(?:{section} level[:\s]*Variation|Answer \(Variation\))\s*(.*?)"
            rf"(?={section} level[:\s]*Wrong|Intermediate level|page top|Problems No|Answers No|All Rights|$)",
            body_text,
            re.DOTALL | re.IGNORECASE,
        )
        if var_match:
            var_text = _clean_answer_text(var_match.group(1))
            if var_text:
                key = f"{section.lower()}_answer"
                existing = texts.get(key, "")
                if existing:
                    texts[key] = existing + "\n(Variation) " + var_text
                else:
                    texts[key] = "(Variation) " + var_text

    return images, texts
