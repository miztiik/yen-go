"""CLI entry point for PDF-to-SGF import tool.

Provides granular step-by-step logging for each stage:
  1. Extract pages from PDF (with source tracking)
  2. Detect columns (multi-column layout)
  3. Detect board regions (with grid pre-filter)
  4. Recognize stones (with confidence scoring)
  5. Match problem-answer pairs
  6. Generate SGF (with solution tree)
  7. Validate SGF correctness
  8. Produce yield report for manual review

Every event is logged to JSONL telemetry with PDF source, page number,
and processing step. The final report shows yield rate, items needing
review, and per-page breakdown.

Usage:
    # Extract and recognize boards from a PDF
    python -m tools.pdf_to_sgf extract --pdf book.pdf --output-dir ./output/

    # Match problems with answers and generate SGF
    python -m tools.pdf_to_sgf convert --pdf problems.pdf --key answers.pdf --output-dir ./output/

    # Preview: show detected boards without generating SGF
    python -m tools.pdf_to_sgf preview --pdf book.pdf --pages 3-5
"""

from __future__ import annotations

import argparse
import logging
import re as _re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

# Ensure project root is on sys.path for imports
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from tools.core.image_to_board import (
    RecognitionConfig,
    format_position,
    recognize_position,
)
from tools.pdf_to_sgf.board_detector import detect_boards, detect_columns, DetectedBoard, DetectionConfig
from tools.pdf_to_sgf.models import (
    AnswerSectionDetectedEvent,
    BoardDetectedEvent,
    BoardRecognizedEvent,
    BoardSkippedEvent,
    ColumnDetectedEvent,
    ErrorEvent,
    ExtractionSource,
    PageExtractedEvent,
    MatchFoundEvent,
    RunStartEvent,
    SgfGeneratedEvent,
    SgfValidatedEvent,
    SgfRejectedEvent,
)
from tools.pdf_to_sgf.ocr import (
    detect_player_to_move,
    detect_problem_label,
    ensure_tesseract,
    find_answer_start,
)
from tools.pdf_to_sgf.pdf_extractor import extract_pages, ExtractionConfig
from tools.pdf_to_sgf.problem_matcher import compute_board_confidence
from tools.pdf_to_sgf.sgf_checker import validate_sgf, IssueSeverity
from tools.pdf_to_sgf.telemetry import RunLogger

log = logging.getLogger(__name__)

_PRESET_MAP = {
    "pdf": RecognitionConfig.for_pdf,
    "scan": RecognitionConfig.for_scan,
    "clean-pdf": RecognitionConfig.for_clean_pdf,
}


def _sanitize_label(raw_label: str) -> str:
    """Sanitize a problem label for use in filenames.

    Replaces filesystem-unsafe characters with underscores, collapses
    consecutive underscores, and strips leading/trailing underscores.
    Returns ``"unknown"`` if the result is empty.
    """
    result = _re.sub(r'[\s/\\:*?"<>|]+', "_", raw_label)
    result = _re.sub(r"_+", "_", result).strip("_")
    return result or "unknown"


def _make_output_stem(yield_number: int, book_label: str) -> str:
    """Build a filename stem from yield number and book label.

    Returns e.g. ``"001_Problem_5"`` — shared between SGF and crop files.
    """
    return f"{yield_number:03d}_{_sanitize_label(book_label)}"


def _player_comment(player: str) -> str:
    """Return a human-readable root comment for the player to move.

    *player* should be ``"B"`` or ``"W"``.
    """
    return "Black to play" if player == "B" else "White to play"


def _format_yl(slug: str, position: int, chapter: int | str = 0) -> str:
    """Format a YL collection value with chapter/position suffix.

    Follows the ``slug:CHAPTER/POSITION`` standard (v14).
    Chapter ``0`` means chapterless (global sequence).
    """
    return f"{slug}:{chapter}/{position}"


def _page_as_single_board(page_image: Image.Image) -> list[DetectedBoard]:
    """Wrap a full page image as a single :class:`DetectedBoard`.

    Used with ``--single-board-per-page`` to bypass board detection.
    """
    return [DetectedBoard(
        bbox=(0, 0, page_image.width, page_image.height),
        image=page_image,
        index=0,
        detection_confidence=1.0,
    )]


def _parse_page_range(s: str | None) -> tuple[int, int | None] | None:
    """Parse a page range string like '3-5', '3', or '50-' (open-ended)."""
    if not s:
        return None
    if "-" in s:
        parts = s.split("-", 1)
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else None
        return start, end
    n = int(s)
    return n, n


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract boards from PDF and show recognition results."""
    pdf_path = Path(args.pdf)
    pdf_name = pdf_path.name
    page_range = _parse_page_range(args.pages)
    output_dir = Path(args.output_dir) if args.output_dir else None
    telem = RunLogger(output_dir)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    telem.emit(RunStartEvent(
        pdf_path=str(pdf_path), pages=args.pages or "", preset=args.preset, command="extract",
    ))

    cfg = _PRESET_MAP[args.preset]() if args.preset in _PRESET_MAP else RecognitionConfig()

    print(f"[1/4] Extracting pages from {pdf_name}...")
    pages = extract_pages(pdf_path, page_range=page_range)
    print(f"       {len(pages)} page(s) extracted")

    total_boards = 0
    for page in pages:
        telem.emit(PageExtractedEvent(
            pdf_source=pdf_name,
            page_number=page.page_number,
            total_pages=len(pages),
            source=ExtractionSource(page.source),
            width=page.width, height=page.height,
        ))

        # Column detection
        det_config = DetectionConfig(enable_grid_filter=not args.verbose)
        columns = detect_columns(page.image, det_config)
        if len(columns) > 1:
            telem.emit(ColumnDetectedEvent(
                page_number=page.page_number,
                column_count=len(columns),
                column_widths=[c.width for c in columns],
            ))

        print(f"\n[2/4] Page {page.page_number}/{len(pages)}: "
              f"{page.width}x{page.height} ({page.source}), "
              f"{len(columns)} column(s)")

        boards = detect_boards(page.image, det_config)
        print(f"[3/4] Page {page.page_number}: {len(boards)} board(s) detected")

        for board in boards:
            telem.emit(BoardDetectedEvent(
                pdf_source=pdf_name,
                page_number=page.page_number, board_index=board.index,
                bbox=board.bbox, width=board.image.width, height=board.image.height,
                detection_confidence=board.detection_confidence,
            ))

            print(f"  [4/4] Recognizing board {board.index + 1}...")
            pos = recognize_position(board.image, config=cfg)
            bc, wc = pos.stone_count()
            conf = compute_board_confidence(pos)
            total_boards += 1

            telem.emit(BoardRecognizedEvent(
                page_number=page.page_number, board_index=board.index,
                grid_rows=pos.n_rows, grid_cols=pos.n_cols,
                black_stones=bc, white_stones=wc, confidence=conf,
            ))

            telem.track_page_board(page.page_number, {
                "label": f"Board {board.index + 1}",
                "grid": f"{pos.n_cols}x{pos.n_rows}",
                "stones": f"{bc}B/{wc}W",
                "confidence": conf.overall,
                "status": "recognized",
            })

            print(f"         {pos.n_cols}x{pos.n_rows} grid, "
                  f"{bc}B/{wc}W stones (conf={conf.overall:.0%}, det={board.detection_confidence:.2f})")

            if args.verbose:
                print(format_position(pos))
                print()

            if output_dir:
                board_file = output_dir / f"p{page.page_number:03d}_b{board.index + 1}.png"
                board.image.save(str(board_file))

    summary = telem.finalize(pdf_path=str(pdf_path))
    print(f"\n{RunLogger.format_report(summary)}")
    if telem._log_file:
        print(f"Telemetry: {telem._log_file}")
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    """Convert problem + answer PDFs to SGF files with full validation."""
    from tools.pdf_to_sgf.models import MatchStrategy, PuzzleConfidence
    from tools.pdf_to_sgf.problem_matcher import match_problems, position_to_sgf

    pdf_path = Path(args.pdf)
    pdf_name = pdf_path.name
    key_path = Path(args.key) if args.key else None
    key_name = key_path.name if key_path else ""
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    telem = RunLogger(output_dir)
    page_range = _parse_page_range(args.pages)
    cfg = _PRESET_MAP[args.preset]() if args.preset in _PRESET_MAP else RecognitionConfig()

    telem.emit(RunStartEvent(
        pdf_path=str(pdf_path), key_path=str(key_path) if key_path else "",
        pages=args.pages or "", preset=args.preset, command="convert",
    ))

    # ── Step 1: Extract problem boards ──
    print(f"[1/7] Extracting pages from {pdf_name}...")
    problem_pages = extract_pages(pdf_path, page_range=page_range)
    print(f"       {len(problem_pages)} page(s) extracted")

    problem_boards = []
    problem_page_map: list[int] = []  # which page each board came from
    problem_labels: dict[int, str] = {}   # detected labels
    problem_players: dict[int, str] = {}  # OCR-detected player-to-move
    problem_extended_crops: dict[int, Image.Image] = {}  # extended crops (board + label area)
    _ocr_available = False
    try:
        ensure_tesseract()
        _ocr_available = True
    except RuntimeError:
        log.debug("Tesseract not available — OCR features disabled")

    for page in problem_pages:
        telem.emit(PageExtractedEvent(
            pdf_source=pdf_name,
            page_number=page.page_number,
            total_pages=len(problem_pages),
            source=ExtractionSource(page.source),
            width=page.width, height=page.height,
        ))
        print(f"[2/7] Page {page.page_number}: {page.width}x{page.height} ({page.source})")

        if getattr(args, "single_board_per_page", False):
            page_boards = _page_as_single_board(page.image)
        else:
            page_boards = detect_boards(page.image)
        page_offset = len(problem_boards)  # global index offset

        # Try PDF text-layer extraction first (much more reliable than OCR)
        text_labels: list[str] = []
        if page_boards:
            from tools.pdf_to_sgf.ocr import extract_labels_from_pdf_text
            text_labels = extract_labels_from_pdf_text(
                pdf_path, page.page_number, len(page_boards),
            )

        for bi, board in enumerate(page_boards):
            telem.emit(BoardDetectedEvent(
                pdf_source=pdf_name,
                page_number=page.page_number, board_index=board.index,
                bbox=board.bbox, width=board.image.width, height=board.image.height,
                detection_confidence=board.detection_confidence,
            ))
            problem_boards.append(board.image)
            problem_page_map.append(page.page_number)
            _board_idx = len(problem_boards) - 1

            # Store extended crop (board + label area below) for --save-crops
            x1, y1, x2, y2 = board.bbox
            board_height = y2 - y1
            label_extend = int(board_height * 0.15)  # 15% extra below for label
            ext_y2 = min(y2 + label_extend, page.height)
            problem_extended_crops[_board_idx] = page.image.crop((x1, y1, x2, ext_y2))

            # Assign label: text-layer (positional) > Tesseract OCR > none
            if text_labels and bi < len(text_labels):
                problem_labels[_board_idx] = text_labels[bi]
            elif _ocr_available:
                _lbl = detect_problem_label(page.image, board.bbox)
                if _lbl:
                    problem_labels[_board_idx] = _lbl
            if _ocr_available:
                _ptm = detect_player_to_move(page.image, board.bbox)
                if _ptm:
                    problem_players[_board_idx] = _ptm

    print(f"       Found {len(problem_boards)} problem board(s)")

    if not problem_boards:
        telem.emit(ErrorEvent(stage="detection", detail="No boards detected in problem PDF"))
        summary = telem.finalize(pdf_path=str(pdf_path), key_path=str(key_path) if key_path else "")
        print(f"\n{RunLogger.format_report(summary)}")
        return 1

    # ── Handle --key-pages (answer section within same PDF) ──
    answer_boards: list = []
    text_solutions: dict = {}  # {problem_number: TextSolution} for text-based answers
    if not key_path and hasattr(args, 'key_pages') and args.key_pages:
        key_range = _parse_page_range(args.key_pages)
        print(f"\n[3/7] Extracting answer pages {args.key_pages} from {pdf_name}...")
        answer_pages = extract_pages(pdf_path, page_range=key_range)
        print(f"       {len(answer_pages)} answer page(s) extracted")

        for page in answer_pages:
            telem.emit(PageExtractedEvent(
                pdf_source=pdf_name,
                page_number=page.page_number,
                total_pages=len(answer_pages),
                source=ExtractionSource(page.source),
                width=page.width, height=page.height,
            ))
            _answer_page_boards = (
                _page_as_single_board(page.image)
                if getattr(args, "single_board_per_page", False)
                else detect_boards(page.image)
            )
            for board in _answer_page_boards:
                telem.emit(BoardDetectedEvent(
                    pdf_source=pdf_name,
                    page_number=page.page_number, board_index=board.index,
                    bbox=board.bbox, width=board.image.width, height=board.image.height,
                    detection_confidence=board.detection_confidence,
                ))
                answer_boards.append(board.image)

        print(f"       Found {len(answer_boards)} answer board(s)")

        # Text-based fallback: if no board diagrams on answer pages, try text extraction
        if not answer_boards and key_range:
            from tools.pdf_to_sgf.text_solution_parser import extract_text_solutions_from_pdf
            text_solutions = extract_text_solutions_from_pdf(pdf_path, key_range)
            print(f"       No board diagrams — found {len(text_solutions)} text-based solution(s)")
            if text_solutions:
                # Show a sample of what was parsed
                sample = list(text_solutions.values())[:3]
                for s in sample:
                    print(f"         ({s.problem_number}) {s.raw_text[:80]}")
                if len(text_solutions) > 3:
                    print(f"         ... and {len(text_solutions) - 3} more")

        key_path = pdf_path  # for report purposes
        key_name = f"{pdf_name} (pages {args.key_pages})"

    # ── Handle --auto-detect-solution ──
    elif not key_path and hasattr(args, 'auto_detect_solution') and args.auto_detect_solution:
        ensure_tesseract()
        print(f"\n[3/7] Scanning pages for answer section markers...")
        all_pages = extract_pages(pdf_path)
        page_images = [p.image for p in all_pages]
        page_nums = [p.page_number for p in all_pages]
        answer_start, marker = find_answer_start(page_images, page_nums)

        if answer_start:
            telem.emit(AnswerSectionDetectedEvent(
                page_number=answer_start, marker_text=marker,
            ))
            total = all_pages[-1].page_number if all_pages else 0
            print(f"       Detected answer section starting at page {answer_start} (marker: '{marker}')")
            print(f"       Recommendation: re-run with --key-pages {answer_start}-{total}")
            print(f"       Example:")
            print(f"         python -m tools.pdf_to_sgf convert --pdf {args.pdf} "
                  f"--key-pages {answer_start}-{total} --output-dir {output_dir}")
        else:
            print("       No answer section markers detected.")
            print("       Proceeding without solution tree.")

        summary = telem.finalize(pdf_path=str(pdf_path))
        print(f"\n{RunLogger.format_report(summary)}")
        return 0

    # ── Step 2: Extract answer boards (if key PDF provided and no text solutions) ──
    if key_path and not answer_boards and not text_solutions:
        print(f"\n[3/7] Extracting pages from {key_name}...")
        answer_pages = extract_pages(key_path, page_range=page_range)
        print(f"       {len(answer_pages)} page(s) extracted")

        answer_boards = []
        for page in answer_pages:
            telem.emit(PageExtractedEvent(
                pdf_source=key_name,
                page_number=page.page_number,
                total_pages=len(answer_pages),
                source=ExtractionSource(page.source),
                width=page.width, height=page.height,
            ))
            _key_page_boards = (
                _page_as_single_board(page.image)
                if getattr(args, "single_board_per_page", False)
                else detect_boards(page.image)
            )
            for board in _key_page_boards:
                telem.emit(BoardDetectedEvent(
                    pdf_source=key_name,
                    page_number=page.page_number, board_index=board.index,
                    bbox=board.bbox, width=board.image.width, height=board.image.height,
                    detection_confidence=board.detection_confidence,
                ))
                answer_boards.append(board.image)

        print(f"       Found {len(answer_boards)} answer board(s)")

    if text_solutions:
        # ── Text-solution path: match by problem number ──
        from tools.core.sgf_builder import SGFBuilder
        from tools.core.sgf_types import Color, Point
        from tools.core.image_to_board import BLACK, WHITE
        from tools.pdf_to_sgf.models import PuzzleConfidence

        ptm_str = getattr(args, "player", "B")
        ptm_color = Color.BLACK if ptm_str == "B" else Color.WHITE
        collection_slug = getattr(args, "collection", None)

        print(f"\n[4/7] Matching {len(problem_boards)} problems to {len(text_solutions)} text solutions...")
        _used_file_nums: set[int] = set()
        generated = 0
        matched = 0

        for idx, img in enumerate(problem_boards):
            page_num = problem_page_map[idx] if idx < len(problem_page_map) else 0
            print(f"  [5/7] Recognizing board {idx + 1} (page {page_num})...")

            pos = recognize_position(img, config=cfg)
            bc, wc = pos.stone_count()
            if bc + wc < 2:
                telem.emit(ErrorEvent(
                    stage="recognition", detail=f"Board {idx + 1}: too few stones ({bc + wc})",
                    page_number=page_num, board_index=idx,
                ))
                # Save crop for failed boards so they can be inspected
                if getattr(args, 'save_crops', False):
                    crops_dir = output_dir / "crops"
                    crops_dir.mkdir(exist_ok=True)
                    crop_img = problem_extended_crops.get(idx, img)
                    crop_file = crops_dir / f"FAILED_board{idx + 1:04d}.png"
                    crop_img.save(str(crop_file))
                    log.warning("Saved failed crop: %s (stones=%d)", crop_file.name, bc + wc)
                continue

            conf = compute_board_confidence(pos)
            telem.emit(BoardRecognizedEvent(
                page_number=page_num, board_index=idx,
                grid_rows=pos.n_rows, grid_cols=pos.n_cols,
                black_stones=bc, white_stones=wc, confidence=conf,
            ))

            # Get problem number from label
            ocr_label = problem_labels.get(idx)
            label = ocr_label if ocr_label else f"Problem {idx + 1}"
            _num_match = _re.search(r"(\d+)", label)
            file_num = int(_num_match.group(1)) if _num_match else (idx + 1)
            if file_num in _used_file_nums:
                log.warning("Duplicate label: board %d got num=%d, falling back to %d",
                            idx + 1, file_num, idx + 1)
                file_num = idx + 1
                label = f"Problem {idx + 1}"
            _used_file_nums.add(file_num)

            # Build SGF
            builder = SGFBuilder(board_size=19)
            for iy, row in enumerate(pos.board):
                for ix, cell in enumerate(row):
                    abs_row = pos.board_top + iy
                    abs_col = pos.board_left + ix
                    try:
                        pt = Point(abs_col, abs_row)
                    except ValueError:
                        continue
                    if cell == BLACK:
                        builder.add_black_stone(pt)
                    elif cell == WHITE:
                        builder.add_white_stone(pt)

            # Look up text solution by problem number
            sol = text_solutions.get(file_num)

            if sol:
                matched += 1
                builder.set_player_to_move(ptm_color)
                for i, move_pt in enumerate(sol.moves):
                    color = Color.BLACK if i % 2 == 0 else Color.WHITE
                    builder.add_solution_move(color, move_pt)
                gtp_moves = " ".join(m.to_gtp() for m in sol.moves)
                sgf_moves = " ".join(m.to_sgf() for m in sol.moves)
                log.info("Board %d: label=%r, solution=%d move(s), GTP=%s, SGF=%s",
                         idx + 1, label, len(sol.moves), gtp_moves, sgf_moves)
            else:
                builder.set_player_to_move(ptm_color)
                log.info("Board %d: label=%r, no text solution found", idx + 1, label)

            builder.set_comment(_player_comment(ptm_str))
            generated += 1
            if collection_slug:
                builder.add_collection(_format_yl(collection_slug, generated))
            sgf_str = builder.build()

            sgf_dir = output_dir / "sgf"
            sgf_dir.mkdir(exist_ok=True)
            stem = _make_output_stem(generated, label)
            out_file = sgf_dir / f"{stem}.sgf"
            out_file.write_text(sgf_str, encoding="utf-8")

            # Save crop image if requested (extended crop includes label area)
            if getattr(args, 'save_crops', False):
                crops_dir = output_dir / "crops"
                crops_dir.mkdir(exist_ok=True)
                crop_img = problem_extended_crops.get(idx, img)
                crop_file = crops_dir / f"{stem}.png"
                crop_img.save(str(crop_file))

            puzzle_conf = PuzzleConfidence(board=conf, overall=conf.overall)
            n_moves = len(sol.moves) if sol else 0

            log.info("Board %d: confidence=%.0f%%, file=%s",
                     idx + 1, conf.overall * 100, out_file.name)

            telem.emit(SgfGeneratedEvent(
                output_file=str(out_file.name), pdf_source=pdf_name,
                page_number=page_num,
                black_stones=bc, white_stones=wc,
                solution_moves=n_moves, has_solution_tree=sol is not None,
                problem_label=label,
                yield_number=generated,
                book_label=_sanitize_label(label),
                confidence=puzzle_conf,
            ))

            # Validate
            check = validate_sgf(sgf_str)
            validation_status = ""
            if check.is_valid:
                warning_codes = [i.code for i in check.issues if i.severity == IssueSeverity.WARNING]
                telem.emit(SgfValidatedEvent(
                    output_file=str(out_file.name),
                    board_size=check.board_size,
                    black_stones=check.black_stone_count,
                    white_stones=check.white_stone_count,
                    solution_moves=check.solution_move_count,
                    warnings=check.warning_count,
                    warning_codes=warning_codes,
                ))
                validation_status = "VALID" if check.warning_count == 0 else f"VALID ({check.warning_count} warnings)"
            else:
                warning_codes = []
                issue_codes = [i.code for i in check.issues]
                detail = "; ".join(i.message for i in check.issues if i.severity == IssueSeverity.ERROR)
                telem.emit(SgfRejectedEvent(
                    output_file=str(out_file.name),
                    error_count=check.error_count, warning_count=check.warning_count,
                    issue_codes=issue_codes, detail=detail,
                ))
                validation_status = f"REJECTED ({check.error_count} errors)"

            telem.track_page_board(page_num, {
                "label": label,
                "sgf_file": out_file.name,
                "stones": f"{bc}B/{wc}W",
                "moves": n_moves,
                "confidence": conf.overall,
                "validation": validation_status,
                "warning_codes": warning_codes,
                "yield_number": generated,
                "status": "text-solution" if sol else "no-solution",
            })

            sol_info = f"{n_moves} move(s)" if sol else "no solution"
            print(f"         {out_file.name}: {bc}B/{wc}W ({sol_info}) "
                  f"conf={conf.overall:.0%} [{validation_status}]")

        print(f"\n       Generated {generated} SGF(s), {matched}/{generated} with text solutions")

        summary = telem.finalize(pdf_path=str(pdf_path), key_path=str(key_path) if key_path else "")
        report = RunLogger.format_report(summary)
        print(f"\n{report}")

        report_file = output_dir / "report.txt"
        report_file.write_text(report, encoding="utf-8")
        print(f"Report:    {report_file}")
        if telem._log_file:
            print(f"Telemetry: {telem._log_file}")
        return 0

    if answer_boards:
        # ── Step 3: Match problems to answers ──
        print(f"\n[4/7] Matching {len(problem_boards)} problems to {len(answer_boards)} answers...")
        matches = match_problems(problem_boards, answer_boards, config=cfg)
        print(f"       {len(matches)} match(es) found")

        ptm_str = getattr(args, "player", "B")
        collection_slug = getattr(args, "collection", None)

        # ── Steps 4-7: Generate, validate, report ──
        generated = 0
        for match in matches:
            page_num = problem_page_map[match.problem_index] if match.problem_index < len(problem_page_map) else 0

            telem.emit(MatchFoundEvent(
                problem_index=match.problem_index, answer_index=match.answer_index,
                similarity=match.similarity, strategy=match.strategy,
                solution_moves=len(match.solution_moves),
                moves_with_order=sum(1 for m in match.solution_moves if m.order > 0),
                confidence=match.match_confidence, problem_label=match.problem_label,
            ))

            # Override label with OCR detection if available
            if match.problem_index in problem_labels:
                match.problem_label = problem_labels[match.problem_index]

            # Generate SGF (with OCR player-to-move if available, CLI as fallback)
            ptm = problem_players.get(match.problem_index) or ptm_str
            from tools.core.sgf_types import Color
            ptm_color = Color.BLACK if ptm == "B" else Color.WHITE
            generated += 1
            yl_value = _format_yl(collection_slug, generated) if collection_slug else None
            sgf_str = position_to_sgf(
                match,
                player_to_move=ptm,
                comment=_player_comment(ptm),
                collection=yl_value,
            )
            sgf_dir = output_dir / "sgf"
            sgf_dir.mkdir(exist_ok=True)
            label = match.problem_label or f"Problem {generated}"
            stem = _make_output_stem(generated, label)
            out_file = sgf_dir / f"{stem}.sgf"
            out_file.write_text(sgf_str, encoding="utf-8")
            bc, wc = match.problem_pos.stone_count()
            n_moves = len(match.solution_moves)
            ordered = sum(1 for m in match.solution_moves if m.order > 0)

            puzzle_conf = PuzzleConfidence(
                board=match.board_confidence, match=match.match_confidence,
                overall=round((match.board_confidence.overall + match.match_confidence.overall) / 2, 3),
            )

            telem.emit(SgfGeneratedEvent(
                output_file=str(out_file.name), pdf_source=pdf_name,
                page_number=page_num,
                black_stones=bc, white_stones=wc,
                solution_moves=n_moves, has_solution_tree=n_moves > 0,
                problem_label=label,
                yield_number=generated,
                book_label=_sanitize_label(label),
                confidence=puzzle_conf,
            ))

            # ── Step 6: Validate SGF ──
            check = validate_sgf(sgf_str)
            validation_status = ""
            if check.is_valid:
                warning_codes = [i.code for i in check.issues if i.severity == IssueSeverity.WARNING]
                telem.emit(SgfValidatedEvent(
                    output_file=str(out_file.name),
                    board_size=check.board_size,
                    black_stones=check.black_stone_count,
                    white_stones=check.white_stone_count,
                    solution_moves=check.solution_move_count,
                    warnings=check.warning_count,
                    warning_codes=warning_codes,
                ))
                if check.warning_count > 0:
                    validation_status = f"VALID ({check.warning_count} warnings)"
                else:
                    validation_status = "VALID"
            else:
                warning_codes = []
                issue_codes = [i.code for i in check.issues]
                detail = "; ".join(i.message for i in check.issues if i.severity == IssueSeverity.ERROR)
                telem.emit(SgfRejectedEvent(
                    output_file=str(out_file.name),
                    error_count=check.error_count,
                    warning_count=check.warning_count,
                    issue_codes=issue_codes,
                    detail=detail,
                ))
                validation_status = f"REJECTED ({check.error_count} errors)"

            # Track per-page
            telem.track_page_board(page_num, {
                "label": label,
                "sgf_file": out_file.name,
                "stones": f"{bc}B/{wc}W",
                "moves": n_moves,
                "ordered": ordered,
                "similarity": round(match.similarity, 2),
                "confidence": puzzle_conf.overall,
                "validation": validation_status,
                "warning_codes": warning_codes,
                "yield_number": generated,
                "status": "matched" if match.strategy.value == "jaccard" else "positional",
            })

            print(f"  [5/7] {out_file.name}: {bc}B/{wc}W, {n_moves} move(s) "
                  f"({ordered} ordered), sim={match.similarity:.2f}, "
                  f"conf={match.match_confidence.overall:.0%} [{validation_status}]")

        # ── Step 7: Final report ──
        summary = telem.finalize(pdf_path=str(pdf_path), key_path=str(key_path))
        report = RunLogger.format_report(summary)
        print(f"\n{report}")

        # Write report to file
        report_file = output_dir / "report.txt"
        report_file.write_text(report, encoding="utf-8")
        print(f"Report:    {report_file}")
        if telem._log_file:
            print(f"Telemetry: {telem._log_file}")
        return 0

    # ── No key: generate SGF from problem positions (no solution tree) ──
    print("\n[4/7] Generating SGF from problem positions (no solution tree)...")
    from tools.core.sgf_builder import SGFBuilder
    from tools.core.sgf_types import Color, Point
    from tools.core.image_to_board import BLACK, WHITE
    from tools.pdf_to_sgf.models import PuzzleConfidence

    ptm_str = getattr(args, "player", "B")
    ptm_color = Color.BLACK if ptm_str == "B" else Color.WHITE
    collection_slug = getattr(args, "collection", None)

    # Sanitize OCR labels: detect and discard duplicates / suspicious values
    _used_file_nums: set[int] = set()

    generated = 0
    for idx, img in enumerate(problem_boards):
        page_num = problem_page_map[idx] if idx < len(problem_page_map) else 0
        print(f"  [5/7] Recognizing board {idx + 1} (page {page_num})...")

        pos = recognize_position(img, config=cfg)
        bc, wc = pos.stone_count()
        if bc + wc < 2:
            telem.emit(ErrorEvent(
                stage="recognition", detail=f"Board {idx + 1}: too few stones ({bc + wc})",
                page_number=page_num, board_index=idx,
            ))
            # Save crop for failed boards so they can be inspected
            if getattr(args, 'save_crops', False):
                crops_dir = output_dir / "crops"
                crops_dir.mkdir(exist_ok=True)
                crop_img = problem_extended_crops.get(idx, img)
                crop_file = crops_dir / f"FAILED_board{idx + 1:04d}.png"
                crop_img.save(str(crop_file))
                log.warning("Saved failed crop: %s (stones=%d)", crop_file.name, bc + wc)
            continue

        conf = compute_board_confidence(pos)

        telem.emit(BoardRecognizedEvent(
            page_number=page_num, board_index=idx,
            grid_rows=pos.n_rows, grid_cols=pos.n_cols,
            black_stones=bc, white_stones=wc, confidence=conf,
        ))

        builder = SGFBuilder(board_size=19)
        for iy, row in enumerate(pos.board):
            for ix, cell in enumerate(row):
                abs_row = pos.board_top + iy
                abs_col = pos.board_left + ix
                try:
                    pt = Point(abs_col, abs_row)
                except ValueError:
                    continue
                if cell == BLACK:
                    builder.add_black_stone(pt)
                elif cell == WHITE:
                    builder.add_white_stone(pt)

        # Use OCR-detected label or fall back to sequential
        ocr_label = problem_labels.get(idx)
        label = ocr_label if ocr_label else f"Problem {idx + 1}"
        # Extract numeric part for label collision detection
        _num_match = _re.search(r"(\d+)", label)
        file_num = int(_num_match.group(1)) if _num_match else (idx + 1)

        # Guard against OCR misreads: if duplicate, fall back to sequential
        if file_num in _used_file_nums:
            log.warning("OCR duplicate: board %d got label %r (num=%d), "
                        "falling back to sequential %d",
                        idx + 1, ocr_label, file_num, idx + 1)
            file_num = idx + 1
            label = f"Problem {idx + 1}"
        _used_file_nums.add(file_num)

        generated += 1
        builder.set_player_to_move(ptm_color)
        builder.set_comment(_player_comment(ptm_str))
        if collection_slug:
            builder.add_collection(_format_yl(collection_slug, generated))
        sgf_str = builder.build()

        sgf_dir = output_dir / "sgf"
        sgf_dir.mkdir(exist_ok=True)
        stem = _make_output_stem(generated, label)
        out_file = sgf_dir / f"{stem}.sgf"
        out_file.write_text(sgf_str, encoding="utf-8")

        # Save crop image if requested (extended crop includes label area)
        if getattr(args, 'save_crops', False):
            crops_dir = output_dir / "crops"
            crops_dir.mkdir(exist_ok=True)
            crop_img = problem_extended_crops.get(idx, img)
            crop_file = crops_dir / f"{stem}.png"
            crop_img.save(str(crop_file))

        log.info("Board %d: label=%r, confidence=%.0f%%, file=%s",
                 idx + 1, label, conf.overall * 100, out_file.name)

        telem.emit(SgfGeneratedEvent(
            output_file=str(out_file.name), pdf_source=pdf_name,
            page_number=page_num,
            black_stones=bc, white_stones=wc,
            solution_moves=0, has_solution_tree=False,
            problem_label=label,
            yield_number=generated,
            book_label=_sanitize_label(label),
            confidence=PuzzleConfidence(board=conf, overall=conf.overall),
        ))

        # Validate
        check = validate_sgf(sgf_str)
        validation_status = ""
        if check.is_valid:
            warning_codes = [i.code for i in check.issues if i.severity == IssueSeverity.WARNING]
            telem.emit(SgfValidatedEvent(
                output_file=str(out_file.name),
                board_size=check.board_size,
                black_stones=check.black_stone_count,
                white_stones=check.white_stone_count,
                solution_moves=check.solution_move_count,
                warnings=check.warning_count,
                warning_codes=warning_codes,
            ))
            validation_status = "VALID" if check.warning_count == 0 else f"VALID ({check.warning_count} warnings)"
        else:
            warning_codes = []
            issue_codes = [i.code for i in check.issues]
            detail = "; ".join(i.message for i in check.issues if i.severity == IssueSeverity.ERROR)
            telem.emit(SgfRejectedEvent(
                output_file=str(out_file.name),
                error_count=check.error_count, warning_count=check.warning_count,
                issue_codes=issue_codes, detail=detail,
            ))
            validation_status = f"REJECTED ({check.error_count} errors)"

        telem.track_page_board(page_num, {
            "label": label,
            "sgf_file": out_file.name,
            "stones": f"{bc}B/{wc}W",
            "confidence": conf.overall,
            "validation": validation_status,
            "warning_codes": warning_codes,
            "yield_number": generated,
            "status": "no-solution",
        })

        print(f"         {out_file.name}: {bc}B/{wc}W (conf={conf.overall:.0%}) [{validation_status}]")

    summary = telem.finalize(pdf_path=str(pdf_path))
    report = RunLogger.format_report(summary)
    print(f"\n{report}")

    report_file = output_dir / "report.txt"
    report_file.write_text(report, encoding="utf-8")
    print(f"Report:    {report_file}")
    if telem._log_file:
        print(f"Telemetry: {telem._log_file}")
    return 0


def cmd_preview(args: argparse.Namespace) -> int:
    """Preview mode: show page/board structure without generating SGF."""
    pdf_path = Path(args.pdf)
    page_range = _parse_page_range(args.pages)

    pages = extract_pages(pdf_path, page_range=page_range)
    det_config = DetectionConfig()
    print(f"PDF: {pdf_path.name} ({len(pages)} pages)")

    for page in pages:
        columns = detect_columns(page.image, det_config)
        boards = detect_boards(page.image, det_config)
        print(f"\n  Page {page.page_number}: "
              f"{page.width}x{page.height} ({page.source}) — "
              f"{len(columns)} column(s), {len(boards)} board(s)")
        for board in boards:
            w, h = board.image.size
            print(f"    Board {board.index + 1}: {w}x{h} at "
                  f"({board.bbox[0]},{board.bbox[1]}) det={board.detection_confidence:.2f}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pdf_to_sgf",
        description="Import Go/Baduk tsumego puzzles from PDF books to SGF format.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show detailed recognition output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract
    p_extract = subparsers.add_parser(
        "extract", help="Extract and recognize boards from a PDF",
    )
    p_extract.add_argument("--pdf", required=True, help="Path to PDF file")
    p_extract.add_argument("--pages", help="Page range (e.g., '3-5' or '3')")
    p_extract.add_argument("--output-dir", help="Save board crops to this directory")
    p_extract.add_argument(
        "--preset", choices=["default", "pdf", "scan", "clean-pdf"], default="default",
        help="Recognition preset (default: default)",
    )

    # convert
    p_convert = subparsers.add_parser(
        "convert", help="Convert PDF to SGF files",
    )
    p_convert.add_argument("--pdf", required=True, help="Path to problem PDF")
    p_convert.add_argument("--key", help="Path to answer key PDF")
    p_convert.add_argument("--output-dir", required=True, help="Output directory for SGF files")
    p_convert.add_argument("--pages", help="Page range (e.g., '3-5' or '3')")
    p_convert.add_argument(
        "--preset", choices=["default", "pdf", "scan", "clean-pdf"], default="default",
        help="Recognition preset (default: default)",
    )
    p_convert.add_argument(
        "--auto-detect-solution", action="store_true",
        help="Scan pages for answer section markers (requires Tesseract OCR)",
    )
    p_convert.add_argument(
        "--key-pages",
        help="Page range within same PDF to treat as answers (e.g., '50-' or '50-68')",
    )
    p_convert.add_argument(
        "--save-crops", action="store_true",
        help="Save board crop images (PNG) alongside SGFs for visual validation",
    )
    p_convert.add_argument(
        "--player", choices=["B", "W"], default="B",
        help="Player to move (default: B = Black to play)",
    )
    p_convert.add_argument(
        "--collection",
        help="Collection slug for YL[] property (e.g., 'cho-chikun-life-death-elementary')",
    )
    p_convert.add_argument(
        "--single-board-per-page", action="store_true",
        help="Skip board detection and treat each page as a single board (troubleshooting)",
    )

    # preview
    p_preview = subparsers.add_parser(
        "preview", help="Preview PDF structure without generating SGF",
    )
    p_preview.add_argument("--pdf", required=True, help="Path to PDF file")
    p_preview.add_argument("--pages", help="Page range (e.g., '3-5' or '3')")

    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(message)s")

    handlers = {
        "extract": cmd_extract,
        "convert": cmd_convert,
        "preview": cmd_preview,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
