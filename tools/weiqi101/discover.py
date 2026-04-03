"""
Discovery utilities for 101weiqi.com collections and books.

Scrapes the 101weiqi website to discover:
- Book catalog: book IDs, names, puzzle counts, difficulty, tags
- Category pagination: page counts for each puzzle category URL
- Book tag structure: tag IDs and associated book counts

This module is designed for offline research/exploration, not production
downloading. It builds a catalog JSON that can later guide bulk imports.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from tools.core.chinese_translator import translate_chinese_text

from .client import WeiQiClient
from .config import BASE_URL

logger = logging.getLogger("101weiqi.discover")


# ---------- Data models ----------


@dataclass
class BookInfo:
    """Metadata for a single book on 101weiqi.com."""

    book_id: int
    name: str
    puzzle_count: int = 0
    difficulty: str = ""       # e.g., "2D", "3K", "1K+"
    sharer: str = ""           # Username who shared
    tags: list[str] = field(default_factory=list)
    url: str = ""
    name_en: str = ""          # English translation of name

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "name": self.name,
            "name_en": self.name_en,
            "puzzle_count": self.puzzle_count,
            "difficulty": self.difficulty,
            "sharer": self.sharer,
            "tags": self.tags,
            "url": self.url,
        }


@dataclass
class BookTag:
    """A book tag/category on the website."""

    tag_id: int
    name: str
    book_count: int = 0
    url: str = ""
    name_en: str = ""          # English translation of name

    def to_dict(self) -> dict:
        return {
            "tag_id": self.tag_id,
            "name": self.name,
            "name_en": self.name_en,
            "book_count": self.book_count,
            "url": self.url,
        }


@dataclass
class CategoryInfo:
    """Metadata about a puzzle category URL path."""

    slug: str               # URL slug, e.g., "chizi"
    chinese_name: str       # e.g., "吃子"
    page_count: int = 0     # Total pages of pagination
    url: str = ""
    name_en: str = ""       # English translation of chinese_name

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "chinese_name": self.chinese_name,
            "name_en": self.name_en,
            "page_count": self.page_count,
            "url": self.url,
        }


@dataclass
class DiscoveryCatalog:
    """Complete discovery results."""

    books: list[BookInfo] = field(default_factory=list)
    book_tags: list[BookTag] = field(default_factory=list)
    categories: list[CategoryInfo] = field(default_factory=list)
    total_active_puzzles: int = 0

    def to_dict(self) -> dict:
        return {
            "total_active_puzzles": self.total_active_puzzles,
            "books_count": len(self.books),
            "book_tags_count": len(self.book_tags),
            "categories_count": len(self.categories),
            "books": [b.to_dict() for b in self.books],
            "book_tags": [t.to_dict() for t in self.book_tags],
            "categories": [c.to_dict() for c in self.categories],
        }

    def save(self, path: Path) -> None:
        """Save catalog to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info(f"Saved discovery catalog to {path}")


@dataclass
class BookPuzzleIndex:
    """Puzzle IDs and aggregate metadata discovered from a single book.

    Sources:
    - puzzle_ids: scraped from /book/levelorder/{book_id}/ (ordered by difficulty)
    - view_count, like_count, finish_count: embedded JS ``bookinfo`` on the same page
                                            (0 if not available on the page)
    """

    book_id: int
    puzzle_ids: list[int] = field(default_factory=list)
    book_name: str = ""
    book_name_en: str = ""
    difficulty: str = ""
    discovered_at: str = ""
    # Aggregate book stats (availability depends on site JS structure)
    view_count: int = 0     # Page views / attempts
    like_count: int = 0     # Likes / bookmarks
    finish_count: int = 0   # Users who completed the book

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "book_name": self.book_name,
            "book_name_en": self.book_name_en,
            "difficulty": self.difficulty,
            "puzzle_count": len(self.puzzle_ids),
            "view_count": self.view_count,
            "like_count": self.like_count,
            "finish_count": self.finish_count,
            "puzzle_ids": self.puzzle_ids,
            "discovered_at": self.discovered_at,
        }


# ---------- Parsing helpers ----------


# Pagination: last page number from "... N 下一页"
_LAST_PAGE_RE = re.compile(r'(?:href=["\'][^"\']*\?page=(\d+)["\']|>\s*(\d+)\s*</a>)\s*\n?\s*下一页')

# Backup pagination: all page numbers
_PAGE_NUMBERS_RE = re.compile(r'>\s*(\d+)\s*</a>')


def _extract_pagination(html: str) -> int:
    """Extract the last page number from pagination HTML."""
    # Try to find the pattern right before 下一页
    m = _LAST_PAGE_RE.search(html)
    if m:
        return int(m.group(1) or m.group(2))

    # Fallback: find all page numbers and take the max
    page_nums = _PAGE_NUMBERS_RE.findall(html)
    if page_nums:
        nums = [int(n) for n in page_nums if int(n) < 10000]
        if nums:
            return max(nums)

    return 1


def _extract_js_var(html: str, var_name: str) -> list | dict | None:
    """Extract a JavaScript variable value from embedded JS in HTML.

    The site embeds data as JS variables. Matches ``var``, ``const``, or
    ``let`` declarations.  Some pages wrap data inside a ``nodedata``
    envelope (e.g. ``var nodedata = {"pagedata": {...}}``); when the
    requested *var_name* is not found as a top-level variable we
    transparently unwrap ``nodedata.<var_name>``.
    """
    result = _extract_js_var_direct(html, var_name)
    if result is not None:
        return result

    # Fallback: check inside nodedata wrapper (chapter pages use this)
    if var_name != "nodedata":
        nodedata = _extract_js_var_direct(html, "nodedata")
        if isinstance(nodedata, dict) and var_name in nodedata:
            return nodedata[var_name]

    return None


def _extract_js_var_direct(html: str, var_name: str) -> list | dict | None:
    """Low-level extraction of a single JS variable declaration."""
    pattern = re.compile(
        rf"(?:var|const|let)\s+{re.escape(var_name)}\s*=\s*([\[{{])"
    )
    m = pattern.search(html)
    if not m:
        return None

    start = m.start(1)
    depth = 1
    i = start + 1
    while i < len(html) and depth > 0:
        c = html[i]
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
        i += 1
    val_str = html[start:i]
    try:
        return json.loads(val_str)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JS var '{var_name}' (len={len(val_str)})")
        return None


def _extract_book_info_from_tag_page(html: str) -> list[BookInfo]:
    """Extract book listings from a /book/tag/{id}/ page.

    The site embeds book data as ``var books = [...]`` in AngularJS pages.
    Each entry has: id, name, ba.qcount, ba.qlevelname, username, tags, etc.
    """
    books: list[BookInfo] = []

    data = _extract_js_var(html, "books")
    if not isinstance(data, list):
        return books

    for entry in data:
        if not isinstance(entry, dict):
            continue
        book_id = entry.get("id")
        name = entry.get("name", "")
        if not book_id or not name:
            continue

        ba = entry.get("ba") or {}
        puzzle_count = ba.get("qcount", 0)
        difficulty = ba.get("qlevelname", "")
        sharer = entry.get("username", "")
        tag_names = [t.get("name", "") for t in (entry.get("tags") or []) if t.get("name")]

        books.append(BookInfo(
            book_id=int(book_id),
            name=name.strip(),
            name_en=translate_chinese_text(name.strip()),
            puzzle_count=int(puzzle_count),
            difficulty=str(difficulty).strip(),
            sharer=sharer,
            tags=tag_names,
            url=f"{BASE_URL}/book/{book_id}/",
        ))

    return books


def _extract_book_tags_from_main(html: str) -> list[BookTag]:
    """Extract book tags from the /book/ main page.

    The site embeds tag data as ``var tags = [...]`` with each entry
    containing: id, name, bookcount.
    """
    tags: list[BookTag] = []

    data = _extract_js_var(html, "tags")
    if not isinstance(data, list):
        return tags

    for entry in data:
        if not isinstance(entry, dict):
            continue
        tag_id = entry.get("id")
        name = entry.get("name", "")
        if not tag_id or not name:
            continue

        tags.append(BookTag(
            tag_id=int(tag_id),
            name=name.strip(),
            name_en=translate_chinese_text(name.strip()),
            book_count=int(entry.get("bookcount", 0)),
            url=f"{BASE_URL}/book/tag/{tag_id}/",
        ))

    return tags


def _extract_puzzle_ids_from_levelorder(html: str) -> list[int]:
    """Extract puzzle IDs from a /book/levelorder/{id}/ page.

    Tries three strategies:
    1. Parse ``var pagedata = {qs: [{qid: ...}, ...]}`` (current site format)
    2. Parse embedded JS variable (legacy names: questions, puzzles, data, list)
    3. Extract from ``/question/{id}/`` href patterns as fallback
    """
    ids: set[int] = set()

    # Strategy 1: pagedata.qs[] — current site format (Alpine.js)
    pagedata = _extract_js_var(html, "pagedata")
    if isinstance(pagedata, dict):
        qs = pagedata.get("qs")
        if isinstance(qs, list):
            for entry in qs:
                if isinstance(entry, dict):
                    raw = entry.get("qid") or entry.get("publicid") or entry.get("id")
                    if raw:
                        try:
                            ids.add(int(raw))
                        except (ValueError, TypeError):
                            pass
            if ids:
                return sorted(ids)

    # Strategy 2: legacy embedded JS variable
    for var_name in ("questions", "puzzles", "data", "list"):
        data = _extract_js_var(html, var_name)
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, dict):
                    raw = entry.get("id") or entry.get("question_id") or entry.get("qid")
                    if raw:
                        try:
                            ids.add(int(raw))
                        except (ValueError, TypeError):
                            pass
            if ids:
                return sorted(ids)

    # Strategy 3: href patterns like /question/12345/
    for m in re.finditer(r'/question/(\d+)/', html):
        ids.add(int(m.group(1)))

    return sorted(ids)


def _extract_book_meta_from_page(html: str) -> dict[str, int]:
    """Extract aggregate book stats from an embedded JS variable.

    Tries ``pagedata`` (current format), then legacy ``bookinfo``/``book``/``bookdata``.
    Probes common Chinese game-site field names for:
    - ``view_count``: page views / attempts
    - ``like_count``: likes / bookmarks
    - ``finish_count``: users who completed all puzzles in the book

    Returns an empty dict on any failure — callers must handle missing fields.
    """
    meta: dict[str, int] = {}

    for var_name in ("pagedata", "bookinfo", "book", "bookdata"):
        data = _extract_js_var(html, var_name)
        if not isinstance(data, dict):
            continue

        # View / attempt count
        for field_name in ("pv", "viewnum", "view_num", "view_count", "clicknum"):
            if field_name in data:
                try:
                    meta["view_count"] = int(data[field_name])
                except (ValueError, TypeError):
                    pass
                break

        # Like / favourite count
        for field_name in ("likenum", "like_num", "like_count", "marknum", "starnum", "mark_num"):
            if field_name in data:
                try:
                    meta["like_count"] = int(data[field_name])
                except (ValueError, TypeError):
                    pass
                break

        # Completion count
        for field_name in ("finishnum", "finish_num", "finish_count", "successnum", "donenum"):
            if field_name in data:
                try:
                    meta["finish_count"] = int(data[field_name])
                except (ValueError, TypeError):
                    pass
                break

        if meta:
            break

    return meta


def _extract_book_info_from_levelorder(html: str) -> dict[str, str]:
    """Extract book name and difficulty from the levelorder page JS.

    Current format uses ``var pagedata = {bookname: ..., qs: [{levelname}, ...]}``.
    Legacy format used ``var bookinfo = {name, qlevelname, ...}``.
    Returns a dict with ``name`` and ``difficulty`` keys (empty strings if absent).
    """
    # Current format: pagedata
    pagedata = _extract_js_var(html, "pagedata")
    if isinstance(pagedata, dict):
        name = str(pagedata.get("bookname") or pagedata.get("name") or "").strip()
        difficulty = str(
            pagedata.get("qlevelname") or pagedata.get("difficulty") or ""
        ).strip()
        if name:
            return {"name": name, "difficulty": difficulty}

    # Legacy format: bookinfo, book, bookdata
    for var_name in ("bookinfo", "book", "bookdata"):
        data = _extract_js_var(html, var_name)
        if isinstance(data, dict):
            name = str(data.get("name") or "").strip()
            difficulty = str(
                data.get("qlevelname") or data.get("difficulty") or ""
            ).strip()
            if name:
                return {"name": name, "difficulty": difficulty}
    return {"name": "", "difficulty": ""}


def _extract_puzzle_count_from_status(html: str) -> int:
    """Extract total active puzzle count from /status/ page."""
    # Original format: "正式使用题目 : 181098道"
    m = re.search(r'正式使用题目\s*[:：]\s*(\d+)', html)
    if m:
        return int(m.group(1))
    # New format: label and count in separate divs, first statusnum is active count
    # <div class="statusnum">:  181101道</div>
    m = re.search(r'class="statusnum">\s*:?\s*(\d+)', html)
    if m:
        return int(m.group(1))
    return 0


# ---------- Discovery functions ----------

# Known puzzle category URL paths and their Chinese names
KNOWN_CATEGORIES: list[tuple[str, str]] = [
    ("chizi", "吃子"),
    ("pianzhao", "骗招"),
    ("buju", "布局"),
    ("guanzi", "官子"),
    ("zhongpan", "中盘"),
    ("shizhan", "实战"),
    ("qili", "棋理"),
]


def discover_book_tags(client: WeiQiClient, delay: float = 2.0) -> list[BookTag]:
    """Discover all book tags from the /book/ main page.

    Args:
        client: HTTP client instance.
        delay: Polite delay between requests (seconds).

    Returns:
        List of BookTag objects.
    """
    logger.info("Discovering book tags from /book/...")
    html = client.fetch_page(f"{BASE_URL}/book/")
    if not html:
        logger.error("Failed to fetch /book/ page")
        return []

    tags = _extract_book_tags_from_main(html)
    logger.info(f"Found {len(tags)} book tags")
    return tags


def discover_books_by_tag(
    client: WeiQiClient,
    tag_id: int,
    delay: float = 2.0,
) -> list[BookInfo]:
    """Discover all books under a specific tag.

    BFS: Fetches the tag page and extracts book listings.

    Args:
        client: HTTP client instance.
        tag_id: Book tag numeric ID.
        delay: Polite delay between requests (seconds).

    Returns:
        List of BookInfo objects.
    """
    url = f"{BASE_URL}/book/tag/{tag_id}/"
    logger.info(f"Discovering books under tag {tag_id}: {url}")
    html = client.fetch_page(url)
    if not html:
        logger.warning(f"Failed to fetch book tag page: {url}")
        return []

    books = _extract_book_info_from_tag_page(html)
    logger.info(f"Tag {tag_id}: found {len(books)} books")
    return books


def discover_category_pages(
    client: WeiQiClient,
    delay: float = 2.0,
) -> list[CategoryInfo]:
    """Discover page counts for each known puzzle category.

    BFS-style: Fetches the first page of each category to extract
    pagination info (total pages).

    Args:
        client: HTTP client instance.
        delay: Polite delay between requests (seconds).

    Returns:
        List of CategoryInfo with page counts.
    """
    categories: list[CategoryInfo] = []

    for slug, chinese_name in KNOWN_CATEGORIES:
        url = f"{BASE_URL}/question/{slug}/"
        logger.info(f"Probing category '{chinese_name}' ({slug}): {url}")

        html = client.fetch_page(url)
        if not html:
            logger.warning(f"Failed to fetch category page: {url}")
            categories.append(CategoryInfo(
                slug=slug, chinese_name=chinese_name,
                name_en=translate_chinese_text(chinese_name), url=url,
            ))
            time.sleep(delay)
            continue

        page_count = _extract_pagination(html)
        logger.info(f"  Category '{chinese_name}': {page_count} pages")

        categories.append(CategoryInfo(
            slug=slug,
            chinese_name=chinese_name,
            name_en=translate_chinese_text(chinese_name),
            page_count=page_count,
            url=url,
        ))
        time.sleep(delay)

    return categories


def discover_total_puzzles(client: WeiQiClient) -> int:
    """Fetch total active puzzle count from /status/ page.

    Args:
        client: HTTP client instance.

    Returns:
        Total active puzzle count, or 0 if unavailable.
    """
    logger.info("Fetching total puzzle count from /status/...")
    html = client.fetch_page(f"{BASE_URL}/status/")
    if not html:
        logger.error("Failed to fetch /status/ page")
        return 0

    count = _extract_puzzle_count_from_status(html)
    logger.info(f"Total active puzzles: {count:,}")
    return count


def run_full_discovery(
    output_path: Path | None = None,
    delay: float = 3.0,
) -> DiscoveryCatalog:
    """Run complete BFS discovery of 101weiqi.com collections.

    Discovers:
    1. Total puzzle count (from /status/)
    2. Book tags (from /book/)
    3. Books per tag (BFS through each tag)
    4. Category page counts (BFS through each category)

    Progress is printed to the console after every HTTP request, and
    if ``output_path`` is given, the catalog is incrementally saved
    after each phase so no work is lost on a crash.

    Args:
        output_path: Path to save results as JSON (incremental writes).
        delay: Polite delay between requests (seconds).

    Returns:
        DiscoveryCatalog with all findings.
    """
    catalog = DiscoveryCatalog()

    def _save_incremental(phase: str) -> None:
        """Flush current catalog state to disk between phases."""
        if output_path:
            catalog.save(output_path)
            logger.info(f"Incremental save after {phase} → {output_path}")

    with WeiQiClient() as client:
        # 1. Total puzzle count
        print("[1/4] Fetching total puzzle count from /status/ ...")
        catalog.total_active_puzzles = discover_total_puzzles(client)
        print(f"       Total active puzzles: {catalog.total_active_puzzles:,}")
        _save_incremental("puzzle_count")
        time.sleep(delay)

        # 2. Discover book tags
        print("[2/4] Discovering book tags from /book/ ...")
        catalog.book_tags = discover_book_tags(client)
        print(f"       Found {len(catalog.book_tags)} book tags")
        _save_incremental("book_tags")
        time.sleep(delay)

        # 3. BFS: discover books under each tag
        print(f"[3/4] BFS: discovering books across {len(catalog.book_tags)} tags ...")
        all_books: dict[int, BookInfo] = {}
        for i, tag in enumerate(catalog.book_tags, 1):
            books = discover_books_by_tag(client, tag.tag_id, delay)
            for book in books:
                if book.book_id not in all_books:
                    all_books[book.book_id] = book
                all_books[book.book_id].tags.append(tag.name)
            print(
                f"       [{i}/{len(catalog.book_tags)}] Tag {tag.tag_id:3d} "
                f"'{tag.name}': {len(books)} books  "
                f"(total unique so far: {len(all_books)})"
            )
            # Incremental save every 5 tags
            catalog.books = sorted(all_books.values(), key=lambda b: b.book_id)
            if i % 5 == 0:
                _save_incremental(f"tag_{i}_of_{len(catalog.book_tags)}")
            time.sleep(delay)

        catalog.books = sorted(all_books.values(), key=lambda b: b.book_id)
        logger.info(f"Total unique books discovered: {len(catalog.books)}")
        print(f"       Total unique books: {len(catalog.books)}")
        _save_incremental("all_books")

        # 4. Discover category page counts
        print(f"[4/4] Probing {len(KNOWN_CATEGORIES)} category pages ...")
        catalog.categories = discover_category_pages(client, delay)
        for cat in catalog.categories:
            est = cat.page_count * 20
            print(f"       {cat.chinese_name} ({cat.slug:10s}): {cat.page_count:4d} pages (~{est:,} puzzles)")

    # Final save
    _save_incremental("complete")

    # Print summary
    print(f"\n{'=' * 60}")
    print("101weiqi.com Discovery Report")
    print(f"{'=' * 60}")
    print(f"Total active puzzles: {catalog.total_active_puzzles:,}")
    print(f"\nBook tags: {len(catalog.book_tags)}")
    for tag in catalog.book_tags:
        print(f"  [{tag.tag_id:3d}] {tag.name} / {tag.name_en} ({tag.book_count} books)")

    print(f"\nUnique books: {len(catalog.books)}")
    total_book_puzzles = sum(b.puzzle_count for b in catalog.books)
    print(f"Total book puzzles: {total_book_puzzles:,}")
    if catalog.books:
        print("\nTop 10 books by puzzle count:")
        for book in sorted(catalog.books, key=lambda b: b.puzzle_count, reverse=True)[:10]:
            print(f"  [{book.book_id:6d}] {book.name} / {book.name_en} — {book.puzzle_count} puzzles, {book.difficulty}")

    print("\nCategory page counts:")
    for cat in catalog.categories:
        est_puzzles = cat.page_count * 20  # ~20 puzzles per page
        print(f"  {cat.chinese_name} / {cat.name_en} ({cat.slug:10s}): {cat.page_count:4d} pages (~{est_puzzles:,} puzzles)")

    if output_path:
        print(f"\nCatalog saved → {output_path}")

    return catalog


def fetch_book_puzzle_ids(
    book_id: int,
    client: WeiQiClient,
    delay: float = 2.0,
) -> BookPuzzleIndex:
    """Fetch all puzzle IDs for a book from /book/levelorder/{book_id}/.

    Handles multi-page books by following pagination until no new IDs appear.
    Also extracts aggregate book metadata (view count, likes, completions) from
    the embedded JS on page 1 — no extra HTTP request needed.

    Args:
        book_id: Numeric book ID on 101weiqi.com.
        client: HTTP client instance.
        delay: Polite delay between page requests (seconds).

    Returns:
        BookPuzzleIndex with all discovered puzzle IDs and available metadata.
    """
    base_url = f"{BASE_URL}/book/levelorder/{book_id}/"
    logger.info(f"Fetching puzzle IDs for book {book_id}: {base_url}")

    all_ids: list[int] = []
    seen: set[int] = set()
    page = 1
    page1_html: str | None = None  # kept for metadata extraction after the loop

    while True:
        url = base_url if page == 1 else f"{base_url}?page={page}"
        html = client.fetch_page(url)
        if not html:
            logger.warning(f"Book {book_id} page {page}: failed to fetch")
            break

        if page == 1:
            page1_html = html  # store for metadata extraction below

        page_ids = _extract_puzzle_ids_from_levelorder(html)
        if not page_ids:
            if page == 1:
                logger.warning(f"Book {book_id}: no puzzle IDs found on page 1")
            break

        new_ids = [pid for pid in page_ids if pid not in seen]
        seen.update(new_ids)
        all_ids.extend(new_ids)
        logger.info(
            f"Book {book_id} page {page}: {len(page_ids)} IDs, "
            f"{len(new_ids)} new, {len(all_ids)} total"
        )

        total_pages = _extract_pagination(html)
        # Also try pagedata.qtotal / pagedata.qstep for more reliable pagination
        pagedata = _extract_js_var(html, "pagedata")
        if isinstance(pagedata, dict):
            qtotal = pagedata.get("qtotal", 0)
            qstep = pagedata.get("qstep", 60)
            if qtotal and qstep:
                total_pages = max(total_pages, -(-qtotal // qstep))  # ceil div
        if page >= total_pages or not new_ids:
            break
        page += 1
        time.sleep(delay)

    # Extract book metadata from page 1 HTML (zero extra requests)
    meta = _extract_book_meta_from_page(page1_html) if page1_html else {}
    book_info = _extract_book_info_from_levelorder(page1_html) if page1_html else {}

    result = BookPuzzleIndex(
        book_id=book_id,
        puzzle_ids=sorted(all_ids),
        book_name=book_info.get("name", ""),
        book_name_en=translate_chinese_text(book_info.get("name", "")),
        difficulty=book_info.get("difficulty", ""),
        discovered_at=datetime.now(UTC).isoformat(),
        view_count=meta.get("view_count", 0),
        like_count=meta.get("like_count", 0),
        finish_count=meta.get("finish_count", 0),
    )
    logger.info(
        f"Book {book_id}: {len(result.puzzle_ids)} puzzle IDs, "
        f"views={result.view_count}, likes={result.like_count}"
    )
    return result


# ---------- Chapter-based discovery (v14 YL support) ----------


@dataclass
class BookChapter:
    """A single chapter within a 101weiqi book."""

    chapter_id: int
    chapter_number: int  # 1-based position within book
    name: str = ""
    name_en: str = ""
    puzzle_ids: list[int] = field(default_factory=list)


@dataclass
class BookChapterIndex:
    """Puzzle IDs organized by chapter for a book.

    Used to generate YL entries with :CHAPTER/POSITION (chapter/position) format.
    """

    book_id: int
    chapters: list[BookChapter] = field(default_factory=list)
    book_name: str = ""
    book_name_en: str = ""
    discovered_at: str = ""

    def all_puzzle_ids(self) -> list[int]:
        """Return all puzzle IDs in chapter order."""
        ids: list[int] = []
        for ch in self.chapters:
            ids.extend(ch.puzzle_ids)
        return ids

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "book_name": self.book_name,
            "book_name_en": self.book_name_en,
            "puzzle_count": sum(len(ch.puzzle_ids) for ch in self.chapters),
            "chapter_count": len(self.chapters),
            "chapters": [
                {
                    "chapter_id": ch.chapter_id,
                    "chapter_number": ch.chapter_number,
                    "name": ch.name,
                    "name_en": ch.name_en,
                    "puzzle_ids": ch.puzzle_ids,
                }
                for ch in self.chapters
            ],
            "discovered_at": self.discovered_at,
        }


def _extract_chapters_from_book_page(html: str) -> list[dict]:
    """Extract chapter list from a /book/{id}/ page.

    The site embeds chapter data as a JS variable (e.g., ``var chapters = [...]``
    or within ``pagedata.chapters``).

    Returns:
        List of dicts with at least 'id' and optionally 'name'.
    """
    # Strategy 1: pagedata.chapters
    pagedata = _extract_js_var(html, "pagedata")
    if isinstance(pagedata, dict):
        chapters = pagedata.get("chapters") or pagedata.get("zjlist")
        if isinstance(chapters, list):
            result = []
            for entry in chapters:
                if isinstance(entry, dict):
                    cid = entry.get("id") or entry.get("zjid")
                    if cid:
                        result.append({
                            "id": int(cid),
                            "name": entry.get("name", ""),
                        })
            if result:
                return result

    # Strategy 2: bookdata.chapters (current site format for /book/{id}/ pages)
    bookdata = _extract_js_var(html, "bookdata")
    if isinstance(bookdata, dict):
        chapters = bookdata.get("chapters") or bookdata.get("zjlist")
        if isinstance(chapters, list):
            result = []
            for entry in chapters:
                if isinstance(entry, dict):
                    cid = entry.get("id") or entry.get("zjid")
                    if cid:
                        result.append({
                            "id": int(cid),
                            "name": entry.get("name", ""),
                        })
            if result:
                return result

    # Strategy 3: standalone var chapters
    for var_name in ("chapters", "zjlist"):
        data = _extract_js_var(html, var_name)
        if isinstance(data, list):
            result = []
            for entry in data:
                if isinstance(entry, dict):
                    cid = entry.get("id") or entry.get("zjid")
                    if cid:
                        result.append({
                            "id": int(cid),
                            "name": entry.get("name", ""),
                        })
            if result:
                return result

    # Strategy 4: href pattern /book/{id}/{chapter_id}/
    chapter_pattern = re.compile(r'/book/\d+/(\d+)/')
    chapter_ids = sorted({int(m.group(1)) for m in chapter_pattern.finditer(html)})
    return [{"id": cid, "name": ""} for cid in chapter_ids]


def _extract_puzzle_ids_from_chapter_page(html: str) -> list[int]:
    """Extract puzzle IDs from a /book/{book_id}/{chapter_id}/ page.

    Similar to levelorder extraction but for chapter-specific pages.
    """
    ids: set[int] = set()

    # Strategy 1: pagedata.qs[]
    pagedata = _extract_js_var(html, "pagedata")
    if isinstance(pagedata, dict):
        qs = pagedata.get("qs")
        if isinstance(qs, list):
            for entry in qs:
                if isinstance(entry, dict):
                    raw = entry.get("qid") or entry.get("publicid") or entry.get("id")
                    if raw:
                        try:
                            ids.add(int(raw))
                        except (ValueError, TypeError):
                            pass
            if ids:
                return sorted(ids)

    # Strategy 2: /question/{id}/ href patterns
    for m in re.finditer(r'/question/(\d+)/', html):
        ids.add(int(m.group(1)))

    return sorted(ids)


def _extract_chapter_puzzle_ids_paginated(
    book_id: int,
    chapter_id: int,
    client: WeiQiClient,
    delay: float,
) -> list[int]:
    """Fetch all puzzle IDs for a single chapter, following pagination."""
    base_url = f"{BASE_URL}/book/{book_id}/{chapter_id}/"
    all_ids: list[int] = []
    seen: set[int] = set()
    page = 1

    while True:
        url = base_url if page == 1 else f"{base_url}?page={page}"
        html = client.fetch_page(url)
        if not html:
            break

        page_ids = _extract_puzzle_ids_from_chapter_page(html)
        new_ids = [pid for pid in page_ids if pid not in seen]
        seen.update(new_ids)
        all_ids.extend(new_ids)

        if not page_ids or not new_ids:
            break

        # Determine max page from nodedata/pagedata
        pagedata = _extract_js_var(html, "pagedata")
        max_page = 1
        if isinstance(pagedata, dict):
            max_page = pagedata.get("maxpage", 1) or 1
        if page >= max_page:
            break
        page += 1
        time.sleep(delay)

    return all_ids


def fetch_book_puzzle_ids_by_chapter(
    book_id: int,
    client: WeiQiClient,
    delay: float = 2.0,
) -> BookChapterIndex:
    """Fetch puzzle IDs organized by chapter for a book.

    Scrapes /book/{book_id}/ to discover chapters, then fetches each
    chapter page (with pagination) to get puzzle IDs in chapter order.
    This preserves the author's intended learning sequence.

    Args:
        book_id: Numeric book ID on 101weiqi.com.
        client: HTTP client instance.
        delay: Polite delay between page requests (seconds).

    Returns:
        BookChapterIndex with puzzle IDs grouped by chapter.
    """
    book_url = f"{BASE_URL}/book/{book_id}/"
    logger.info(f"Fetching chapters for book {book_id}: {book_url}")

    html = client.fetch_page(book_url)
    if not html:
        logger.warning(f"Book {book_id}: failed to fetch book page")
        return BookChapterIndex(book_id=book_id)

    # Extract book name
    book_info = _extract_book_info_from_levelorder(html)
    book_name = book_info.get("name", "")

    # Extract chapter list
    raw_chapters = _extract_chapters_from_book_page(html)
    if not raw_chapters:
        logger.warning(f"Book {book_id}: no chapters found, falling back to flat list")
        return BookChapterIndex(book_id=book_id, book_name=book_name)

    chapters: list[BookChapter] = []
    for chapter_num, ch_data in enumerate(raw_chapters, start=1):
        chapter_id = ch_data["id"]
        chapter_name = ch_data.get("name", "")

        # Fetch puzzle IDs for this chapter (with pagination)
        time.sleep(delay)
        puzzle_ids = _extract_chapter_puzzle_ids_paginated(
            book_id, chapter_id, client, delay
        )

        chapters.append(BookChapter(
            chapter_id=chapter_id,
            chapter_number=chapter_num,
            name=chapter_name,
            name_en=translate_chinese_text(chapter_name) if chapter_name else "",
            puzzle_ids=puzzle_ids,
        ))
        logger.info(
            f"Book {book_id} ch.{chapter_num} ({chapter_name}): "
            f"{len(puzzle_ids)} puzzle IDs"
        )

    result = BookChapterIndex(
        book_id=book_id,
        chapters=chapters,
        book_name=book_name,
        book_name_en=translate_chinese_text(book_name) if book_name else "",
        discovered_at=datetime.now(UTC).isoformat(),
    )
    total = sum(len(ch.puzzle_ids) for ch in chapters)
    logger.info(
        f"Book {book_id}: {len(chapters)} chapters, {total} total puzzle IDs"
    )
    return result
