"""HTML parser for Senseis Library problem and solution pages.

Extracts structured data from Senseis wiki HTML using BeautifulSoup4.
"""

from __future__ import annotations

import html
import logging
import re

from bs4 import BeautifulSoup, Tag

from tools.senseis_enrichment.models import (
    SenseisDiagram,
    SenseisPageData,
    SenseisSolutionData,
)

logger = logging.getLogger("senseis_enrichment.html_parser")


def parse_problem_page(
    html_content: str, problem_number: int, page_name: str
) -> SenseisPageData:
    """Extract metadata from a Senseis problem page.

    Extracts: title (English/Chinese/Pinyin), difficulty, instruction, cross-refs.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    data = SenseisPageData(problem_number=problem_number, page_name=page_name)

    # Difficulty: from page headers div
    _extract_difficulty(soup, data)

    # Title: from the first <h3> tag
    _extract_title(soup, data)

    # Instruction: text associated with the problem diagram
    _extract_instruction(soup, data)

    # Problem diagram SGF URL (for position matching)
    _extract_diagram_sgf_url(soup, data)

    # Cross-references: from "See also" section
    _extract_cross_references(soup, data)

    return data


def _extract_difficulty(soup: BeautifulSoup, data: SenseisPageData) -> None:
    """Extract difficulty rating from the page headers."""
    headers_div = soup.find("div", id="pageheaders")
    if not headers_div:
        return
    # Look for "Difficulty" link: <A HREF="/?header=difficulty&term=Advanced">Advanced</A>
    diff_link = headers_div.find(
        "a", href=re.compile(r"header=difficulty.*term=", re.IGNORECASE)
    )
    if diff_link:
        data.difficulty = diff_link.get_text(strip=True)


def _extract_title(soup: BeautifulSoup, data: SenseisPageData) -> None:
    """Extract the problem title from the first h3 heading.

    Senseis titles are formatted like:
    "Bright Pearl Comes out from the Sea - 明珠出海 - míng zhū chū hǎi"

    Some titles have CJK in parentheses mixed with English, e.g.:
    "Beheading the Snake (斩蛇)"
    """
    h3 = soup.find("h3")
    if not h3:
        return

    raw_text = h3.get_text(strip=True)
    if not raw_text:
        return

    # Decode HTML entities
    decoded = html.unescape(raw_text)

    # Remove any leading [edit] markers
    decoded = re.sub(r"^\[edit\]\s*", "", decoded)

    # Split on " - " to separate English, Chinese, and Pinyin parts
    parts = [p.strip() for p in decoded.split(" - ") if p.strip()]
    if not parts:
        return

    for part in parts:
        # Pure CJK string (no Latin letters mixed in)
        if _is_pure_cjk(part):
            data.title_chinese = part
        elif _looks_like_pinyin(part):
            data.title_pinyin = part
        elif not data.title_english:
            # Extract CJK from parentheses within English title
            cjk_match = re.search(r"\(([^)]*[\u4e00-\u9fff]+[^)]*)\)", part)
            if cjk_match and not data.title_chinese:
                data.title_chinese = cjk_match.group(1)
            # English title is the full text (including parenthetical CJK)
            data.title_english = part


def _is_pure_cjk(text: str) -> bool:
    """Check if text is primarily CJK characters (>50% CJK)."""
    cjk_count = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    alpha_count = sum(1 for c in text if c.isalpha())
    return alpha_count > 0 and cjk_count > alpha_count * 0.5


def _looks_like_pinyin(text: str) -> bool:
    """Check if text looks like pinyin (Latin with diacritics, all lowercase-ish)."""
    # Pinyin has tone marks: ā á ǎ à ē é ě è etc.
    has_diacritics = bool(re.search(r"[\u0100-\u017f\u01cd-\u01dc]", text))
    mostly_latin = sum(1 for c in text if c.isalpha()) > len(text) * 0.5
    return has_diacritics and mostly_latin


def _extract_instruction(soup: BeautifulSoup, data: SenseisPageData) -> None:
    """Extract the problem instruction (e.g., 'White to play and escape').

    The instruction is in the diagram form area. We look for the pattern
    in form text or the text immediately around the diagram.
    """
    # Look in form elements within diagram divs — these have clean text
    for form in soup.find_all("form"):
        form_text = form.get_text()
        match = re.search(r"((?:White|Black) to play[^/\[\n]*)", form_text)
        if match:
            instruction = match.group(1).strip()
            # Clean trailing "Search position" and whitespace
            instruction = re.sub(r"\s*Search position\s*$", "", instruction)
            data.instruction = re.sub(r"\s+", " ", instruction).strip()
            return


def _extract_diagram_sgf_url(soup: BeautifulSoup, data: SenseisPageData) -> None:
    """Extract the problem diagram SGF URL for position matching.

    This is the initial position diagram on the problem page (not the solution).
    """
    diagram_div = soup.find("div", class_="diagram")
    if not diagram_div:
        return
    sgf_link = diagram_div.find("a", href=re.compile(r"\.sgf$"))
    if sgf_link:
        data.diagram_sgf_url = sgf_link.get("href", "")


def _extract_cross_references(soup: BeautifulSoup, data: SenseisPageData) -> None:
    """Extract cross-references from 'See also' section."""
    # Find "See also" heading
    for h3 in soup.find_all("h3"):
        if "See also" in h3.get_text():
            # Get the next <ul> after this heading
            ul = h3.find_next("ul")
            if ul:
                for li in ul.find_all("li"):
                    text = li.get_text(strip=True)
                    if text:
                        data.cross_references.append(text)
            break


def parse_solution_page(
    html_content: str, problem_number: int
) -> SenseisSolutionData:
    """Extract diagrams and commentary from a Senseis solution page.

    Senseis solution pages have two 'contentsize' divs — the first contains
    only the <h1> title; the second contains the actual diagram wrappers.
    Each wrapper div holds a 'diagram' div + <p> commentary tags.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    result = SenseisSolutionData(problem_number=problem_number)

    # Use the LAST contentsize div (the one with diagrams, not the h1)
    all_content_divs = soup.find_all("div", class_="contentsize")
    content_div = None
    for cd in all_content_divs:
        if cd.find("div", class_="diagram"):
            content_div = cd
            break
    if not content_div:
        result.status = "empty"
        return result

    # Each diagram lives in a wrapper <div> (no class) that contains
    # the 'diagram' div + <p> commentary tags.
    # Section headings (e.g. "Resistance 'a'") appear as <p><strong>...</strong></p>
    # or <h2>/<h3>/<h4> between wrapper divs — track the most recent heading.
    last_heading = ""
    for child in content_div.children:
        if not isinstance(child, Tag):
            continue

        # Check if this is a heading element (not containing a diagram)
        if child.name in ("h2", "h3", "h4", "p") and not child.find(
            "div", class_="diagram"
        ):
            strong = child.find("strong")
            if strong:
                last_heading = strong.get_text(strip=True)
            elif child.name in ("h2", "h3", "h4"):
                last_heading = child.get_text(strip=True)
        elif child.name == "div":
            diagram_div = child.find("div", class_="diagram")
            if not diagram_div:
                continue
            diagram = _extract_diagram_from_wrapper(child, diagram_div)
            if diagram:
                if not diagram.diagram_name and last_heading:
                    diagram.diagram_name = last_heading
                result.diagrams.append(diagram)
                last_heading = ""

    if not result.diagrams:
        result.status = "empty"

    return result


def _extract_diagram_from_wrapper(
    wrapper: Tag, diagram_div: Tag
) -> SenseisDiagram | None:
    """Extract diagram SGF URL, name, and commentary from a wrapper div.

    The wrapper div contains:
    - A 'diagram' div with an <a> link to the SGF and a <form> with the name
    - One or more <p> tags with commentary text
    """
    # SGF URL from the <a> wrapping the diagram image
    sgf_link = diagram_div.find("a", href=re.compile(r"\.sgf$"))
    if not sgf_link:
        return None
    sgf_url = sgf_link.get("href", "")

    # Diagram name from the form text (e.g., "Main line", "variation 'a'")
    form = diagram_div.find("form")
    diagram_name = ""
    if form:
        form_text = form.get_text(strip=True)
        diagram_name = re.sub(r"\s*Search position\s*$", "", form_text).strip()

    # Commentary: all <p> tags inside the wrapper div
    commentary_parts = []
    for p in wrapper.find_all("p"):
        para_text = _clean_commentary(p)
        if para_text:
            commentary_parts.append(para_text)

    commentary = " ".join(commentary_parts)

    return SenseisDiagram(
        diagram_name=diagram_name,
        sgf_url=sgf_url,
        commentary=commentary,
    )


def _clean_commentary(p_tag: Tag) -> str:
    """Clean a commentary paragraph, replacing stone images with text references."""
    # Replace <img ... alt="B1"> with "B1", <img ... alt="W2"> with "W2"
    for img in p_tag.find_all("img"):
        alt = img.get("alt", "")
        if alt:
            img.replace_with(alt)

    # Replace <strong><em>x</em></strong> with 'x' (letter references)
    for strong in p_tag.find_all("strong"):
        em = strong.find("em")
        if em:
            letter = em.get_text(strip=True)
            strong.replace_with(f"'{letter}'")

    text = p_tag.get_text()
    # Normalize whitespace
    return re.sub(r"\s+", " ", text).strip()
