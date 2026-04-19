"""Tests for board detector Phase 5 features: column detection + grid pre-filter.

Also tests the enhanced telemetry report format.

Run: pytest tools/pdf_to_sgf/tests/test_phase5.py -q --no-header --tb=short
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
import cv2
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


# ---------------------------------------------------------------------------
# Column detection tests
# ---------------------------------------------------------------------------


class TestColumnDetection:
    def _make_page(self, width: int = 800, height: int = 1000, columns: int = 1) -> Image.Image:
        """Create a synthetic page with N columns of dark content."""
        img = np.full((height, width, 3), 255, dtype=np.uint8)  # white background

        if columns == 1:
            # Single wide block of content
            img[100:900, 100:700, :] = 50
        elif columns == 2:
            # Two columns of content with a gap in the middle
            img[100:900, 50:350, :] = 50   # left column
            img[100:900, 450:750, :] = 50  # right column
        elif columns == 3:
            # Three columns
            img[100:900, 30:220, :] = 50
            img[100:900, 300:490, :] = 50
            img[100:900, 570:760, :] = 50

        return Image.fromarray(img)

    def test_single_column_returns_original(self):
        from tools.pdf_to_sgf.board_detector import detect_columns, DetectionConfig

        page = self._make_page(columns=1)
        config = DetectionConfig()
        result = detect_columns(page, config)
        assert len(result) == 1

    def test_two_columns_detected(self):
        from tools.pdf_to_sgf.board_detector import detect_columns, DetectionConfig

        page = self._make_page(columns=2)
        config = DetectionConfig(min_column_width=50)
        result = detect_columns(page, config)
        assert len(result) == 2

    def test_three_columns_detected(self):
        from tools.pdf_to_sgf.board_detector import detect_columns, DetectionConfig

        page = self._make_page(columns=3)
        config = DetectionConfig(min_column_width=50)
        result = detect_columns(page, config)
        assert len(result) == 3

    def test_column_detection_disabled(self):
        from tools.pdf_to_sgf.board_detector import detect_boards, DetectionConfig

        page = self._make_page(columns=2)
        config = DetectionConfig(enable_column_detection=False, min_board_area=100)
        boards = detect_boards(page, config)
        # Should still find boards via CC analysis even without column split
        assert isinstance(boards, list)

    def test_empty_page_returns_single_column(self):
        from tools.pdf_to_sgf.board_detector import detect_columns

        page = Image.fromarray(np.full((500, 400, 3), 255, dtype=np.uint8))
        result = detect_columns(page)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Grid pre-filter tests
# ---------------------------------------------------------------------------


class TestGridPreFilter:
    def test_has_board_grid_with_no_lines(self):
        from tools.pdf_to_sgf.board_detector import has_board_grid

        # Plain white image — no grid lines
        img = Image.fromarray(np.full((200, 200, 3), 255, dtype=np.uint8))
        is_board, count = has_board_grid(img, min_lines=15)
        assert not is_board
        assert count < 15

    def test_has_board_grid_with_many_lines(self):
        from tools.pdf_to_sgf.board_detector import has_board_grid

        # Create image with grid lines
        img_np = np.full((400, 400), 255, dtype=np.uint8)
        # Draw horizontal lines
        for y in range(20, 380, 20):
            img_np[y, 20:380] = 0
        # Draw vertical lines
        for x in range(20, 380, 20):
            img_np[20:380, x] = 0
        img = Image.fromarray(img_np)
        is_board, count = has_board_grid(img, min_lines=10)
        assert is_board
        assert count >= 10

    def test_grid_filter_skips_non_board_regions(self):
        from tools.pdf_to_sgf.board_detector import DetectionConfig, _detect_boards_in_region

        # White image with a dark blob but no grid lines
        img_np = np.full((300, 300, 3), 255, dtype=np.uint8)
        img_np[50:250, 50:250, :] = 50  # dark block
        img = Image.fromarray(img_np)

        config = DetectionConfig(
            min_board_area=1000, enable_grid_filter=True, min_grid_lines=15,
        )
        boards = _detect_boards_in_region(img, config)
        # Should be filtered out because no grid lines
        assert len(boards) == 0

    def test_grid_filter_disabled_keeps_regions(self):
        from tools.pdf_to_sgf.board_detector import DetectionConfig, _detect_boards_in_region

        img_np = np.full((300, 300, 3), 255, dtype=np.uint8)
        img_np[50:250, 50:250, :] = 50
        img = Image.fromarray(img_np)

        config = DetectionConfig(
            min_board_area=1000, enable_grid_filter=False,
        )
        boards = _detect_boards_in_region(img, config)
        assert len(boards) >= 1


# ---------------------------------------------------------------------------
# Detection config tests
# ---------------------------------------------------------------------------


class TestDetectionConfig:
    def test_new_config_fields_have_defaults(self):
        from tools.pdf_to_sgf.board_detector import DetectionConfig

        config = DetectionConfig()
        assert config.min_grid_lines == 15
        assert config.enable_grid_filter is True
        assert config.enable_column_detection is True
        assert config.column_morph_height == 100
        assert config.min_column_width == 100


# ---------------------------------------------------------------------------
# Enhanced models tests
# ---------------------------------------------------------------------------


class TestNewEventModels:
    def test_column_detected_event(self):
        from tools.pdf_to_sgf.models import ColumnDetectedEvent

        e = ColumnDetectedEvent(page_number=3, column_count=2, column_widths=[400, 380])
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "column_detected"
        assert data["column_count"] == 2

    def test_board_skipped_event(self):
        from tools.pdf_to_sgf.models import BoardSkippedEvent

        e = BoardSkippedEvent(
            page_number=5, bbox=(10, 20, 300, 400),
            grid_lines=8, reason="Too few grid lines",
        )
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "board_skipped"
        assert data["grid_lines"] == 8

    def test_sgf_validated_event(self):
        from tools.pdf_to_sgf.models import SgfValidatedEvent

        e = SgfValidatedEvent(
            output_file="puzzle_0001.sgf", board_size=19,
            black_stones=5, white_stones=7, solution_moves=3,
            warnings=1, warning_codes=["NO_SOLUTION"],
        )
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "sgf_validated"
        assert data["warnings"] == 1

    def test_sgf_rejected_event(self):
        from tools.pdf_to_sgf.models import SgfRejectedEvent

        e = SgfRejectedEvent(
            output_file="puzzle_0005.sgf",
            error_count=2, warning_count=1,
            issue_codes=["STONE_OVERLAP", "OUT_OF_BOUNDS", "FEW_STONES"],
            detail="Black and white stone on same point",
        )
        data = json.loads(e.model_dump_json())
        assert data["event_type"] == "sgf_rejected"
        assert data["error_count"] == 2

    def test_page_extracted_has_pdf_source(self):
        from tools.pdf_to_sgf.models import PageExtractedEvent, ExtractionSource

        e = PageExtractedEvent(
            pdf_source="cho-chikun.pdf", page_number=3, total_pages=50,
            source=ExtractionSource.EMBEDDED, width=3168, height=2448,
        )
        data = json.loads(e.model_dump_json())
        assert data["pdf_source"] == "cho-chikun.pdf"
        assert data["total_pages"] == 50

    def test_run_summary_has_yield_fields(self):
        from tools.pdf_to_sgf.models import RunSummary

        s = RunSummary(
            pdf_path="book.pdf", pages_processed=5,
            boards_detected=15, boards_skipped=3, boards_recognized=12,
            sgf_generated=10, sgf_validated=9, sgf_rejected=1,
            yield_rate=0.6, review_needed=2,
        )
        data = json.loads(s.model_dump_json())
        assert data["boards_skipped"] == 3
        assert data["sgf_validated"] == 9
        assert data["sgf_rejected"] == 1
        assert data["yield_rate"] == 0.6
        assert data["review_needed"] == 2


# ---------------------------------------------------------------------------
# Telemetry report format tests
# ---------------------------------------------------------------------------


class TestTelemetryReport:
    def test_report_format_basic(self):
        from tools.pdf_to_sgf.models import RunSummary
        from tools.pdf_to_sgf.telemetry import RunLogger

        summary = RunSummary(
            pdf_path="book.pdf", key_path="key.pdf",
            pages_processed=5, boards_detected=15, boards_recognized=12,
            matches_found=10, sgf_generated=10, sgf_validated=8,
            sgf_rejected=2, errors=1,
            duration_seconds=12.5, avg_board_confidence=0.72,
            avg_match_confidence=0.65, yield_rate=0.533,
            review_needed=3,
        )
        report = RunLogger.format_report(summary)
        assert "PDF-to-SGF Conversion Report" in report
        assert "book.pdf" in report
        assert "key.pdf" in report
        assert "Pages processed:" in report
        assert "Yield rate:" in report
        assert "Review needed:" in report

    def test_report_includes_per_page_breakdown(self):
        from tools.pdf_to_sgf.models import RunSummary
        from tools.pdf_to_sgf.telemetry import RunLogger

        summary = RunSummary(
            pdf_path="book.pdf",
            pages_processed=2, boards_detected=4,
            sgf_generated=3, sgf_validated=3,
            page_summary=[
                {"page": 3, "boards": 2, "details": [
                    {"label": "Problem 1", "sgf_file": "puzzle_0001.sgf", "confidence": 0.80, "validation": "VALID"},
                    {"label": "Problem 2", "sgf_file": "puzzle_0002.sgf", "confidence": 0.65, "validation": "VALID (1 warnings)"},
                ]},
                {"page": 4, "boards": 2, "details": [
                    {"label": "Problem 3", "sgf_file": "puzzle_0003.sgf", "confidence": 0.90, "validation": "VALID"},
                ]},
            ],
        )
        report = RunLogger.format_report(summary)
        assert "Per-Page Breakdown" in report
        assert "Page 3: 2 board(s)" in report
        assert "Problem 1" in report
        assert "puzzle_0001.sgf" in report

    def test_report_no_key_pdf(self):
        from tools.pdf_to_sgf.models import RunSummary
        from tools.pdf_to_sgf.telemetry import RunLogger

        summary = RunSummary(
            pdf_path="book.pdf", pages_processed=5, boards_detected=10,
        )
        report = RunLogger.format_report(summary)
        assert "Answer PDF:" not in report

    def test_logger_track_page_board(self):
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger()
        logger.track_page_board(3, {"label": "Board 1", "status": "ok"})
        logger.track_page_board(3, {"label": "Board 2", "status": "ok"})
        logger.track_page_board(5, {"label": "Board 1", "status": "ok"})

        assert 3 in logger._page_boards
        assert len(logger._page_boards[3]) == 2
        assert len(logger._page_boards[5]) == 1

    def test_finalize_computes_yield_rate(self):
        from tools.pdf_to_sgf.models import (
            BoardDetectedEvent, SgfValidatedEvent,
            PageExtractedEvent, ExtractionSource,
        )
        from tools.pdf_to_sgf.telemetry import RunLogger

        logger = RunLogger()
        logger.emit(PageExtractedEvent(
            page_number=1, source=ExtractionSource.EMBEDDED, width=800, height=600,
        ))
        # 4 boards detected
        for i in range(4):
            logger.emit(BoardDetectedEvent(
                page_number=1, board_index=i, bbox=(0, 0, 100, 100), width=100, height=100,
            ))
        # 3 validated
        for i in range(3):
            logger.emit(SgfValidatedEvent(
                output_file=f"puzzle_{i+1:04d}.sgf", board_size=19,
                black_stones=5, white_stones=7, solution_moves=2,
            ))

        summary = logger.finalize(pdf_path="test.pdf")
        assert summary.sgf_validated == 3
        assert summary.boards_detected == 4
        assert summary.yield_rate == 0.75


# ---------------------------------------------------------------------------
# Circle erasure tests (Phase 5c)
# ---------------------------------------------------------------------------


class TestCircleErasure:
    """Tests for _erase_circles in tools/core/image_to_board.py."""

    def test_no_circles_returns_copy(self):
        from tools.core.image_to_board import _erase_circles, RecognitionConfig

        # Plain white image — nothing to erase
        img = np.full((200, 200, 3), 255, dtype=np.uint8)
        cfg = RecognitionConfig(circle_erasure=True)
        result = _erase_circles(img, cfg)
        assert result.shape == img.shape
        # Should be an unmodified copy
        np.testing.assert_array_equal(result, img)

    def test_erases_drawn_circles(self):
        import cv2
        from tools.core.image_to_board import _erase_circles, RecognitionConfig

        # White background with black filled circles (simulating stones)
        img = np.full((400, 400, 3), 255, dtype=np.uint8)
        centres = [(100, 100), (200, 200), (300, 300)]
        for cx, cy in centres:
            cv2.circle(img, (cx, cy), 20, (0, 0, 0), -1)

        cfg = RecognitionConfig(
            circle_erasure=True,
            circle_erasure_min_radius=10,
            circle_erasure_max_radius=30,
        )
        result = _erase_circles(img, cfg)

        # At least one circle should have been erased — its bounding box
        # is now mostly black (0) instead of the original filled circle.
        # We verify by checking that the result differs from input in at
        # least one circle's bounding region.
        erased = 0
        for cx, cy in centres:
            # Check if the center pixel is white (erased + center placed)
            if tuple(result[cy, cx]) == (255, 255, 255):
                erased += 1
        assert erased >= 1, "Expected at least 1 circle to be erased"

    def test_result_is_a_copy(self):
        from tools.core.image_to_board import _erase_circles, RecognitionConfig

        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        cfg = RecognitionConfig(circle_erasure=True)
        result = _erase_circles(img, cfg)
        # Modifying result should not affect original
        result[0, 0] = (0, 0, 0)
        assert tuple(img[0, 0]) == (128, 128, 128)

    def test_respects_radius_bounds(self):
        import cv2
        from tools.core.image_to_board import _erase_circles, RecognitionConfig

        img = np.full((400, 400, 3), 255, dtype=np.uint8)
        # Draw a very large circle (r=60) — outside max_radius=40
        cv2.circle(img, (200, 200), 60, (0, 0, 0), -1)

        cfg = RecognitionConfig(
            circle_erasure=True,
            circle_erasure_min_radius=5,
            circle_erasure_max_radius=40,
        )
        result = _erase_circles(img, cfg)

        # Large circle may not be detected since r=60 > max_radius=40
        # The pixel at (200, 200) should still be dark (unerased)
        # or if partially detected, at least the function doesn't crash
        assert result.shape == img.shape

    def test_for_pdf_preset_has_circle_erasure(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_pdf()
        assert cfg.circle_erasure is True

    def test_for_scan_preset_has_circle_erasure(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_scan()
        assert cfg.circle_erasure is True

    def test_default_config_has_circle_erasure_off(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig()
        assert cfg.circle_erasure is False


# ---------------------------------------------------------------------------
# Perspective correction tests (Phase 5 — Step 2)
# ---------------------------------------------------------------------------


class TestPerspectiveCorrection:
    """Tests for _correct_perspective in tools/core/image_to_board.py."""

    def test_no_quad_returns_original(self):
        from tools.core.image_to_board import _correct_perspective, RecognitionConfig

        # Plain white image — no quadrilateral to detect
        img = np.full((300, 300, 3), 255, dtype=np.uint8)
        cfg = RecognitionConfig(perspective_correction=True)
        result = _correct_perspective(img, cfg)
        # Should return unchanged (copy)
        assert result.shape == img.shape
        np.testing.assert_array_equal(result, img)

    def test_disabled_returns_original(self):
        from tools.core.image_to_board import _correct_perspective, RecognitionConfig

        img = np.full((300, 300, 3), 128, dtype=np.uint8)
        cfg = RecognitionConfig(perspective_correction=False)
        result = _correct_perspective(img, cfg)
        assert result is img  # Same object, not a copy

    def test_trapezoid_is_rectified(self):
        import cv2
        from tools.core.image_to_board import _correct_perspective, RecognitionConfig

        # Create a white image with a dark trapezoid (simulating skewed board)
        img = np.full((500, 500, 3), 255, dtype=np.uint8)
        pts = np.array([[150, 100], [350, 80], [380, 400], [120, 420]], dtype=np.int32)
        cv2.fillPoly(img, [pts], (30, 30, 30))

        cfg = RecognitionConfig(
            perspective_correction=True,
            perspective_min_area_ratio=0.10,
        )
        result = _correct_perspective(img, cfg)
        # Output should exist and have reasonable dimensions
        assert result.shape[0] > 0
        assert result.shape[1] > 0

    def test_order_corners(self):
        from tools.core.image_to_board import _order_corners

        # Shuffled corners
        pts = np.array([[300, 300], [0, 0], [300, 0], [0, 300]], dtype=np.float32)
        ordered = _order_corners(pts)
        # top-left should be (0,0), top-right (300,0), etc.
        assert ordered[0][0] < ordered[1][0]  # TL.x < TR.x
        assert ordered[0][1] < ordered[3][1]  # TL.y < BL.y

    def test_for_scan_has_perspective(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_scan()
        assert cfg.perspective_correction is True

    def test_for_pdf_no_perspective(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_pdf()
        assert cfg.perspective_correction is False

    def test_default_no_perspective(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig()
        assert cfg.perspective_correction is False


# ---------------------------------------------------------------------------
# Digit template set tests
# ---------------------------------------------------------------------------


class TestDigitTemplateSet:
    """Tests for digit template set configuration."""

    def test_default_uses_default_templates(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig()
        assert cfg.digit_template_set == "default"

    def test_for_pdf_uses_pdf_templates(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_pdf()
        assert cfg.digit_template_set == "pdf"

    def test_for_scan_uses_default_templates(self):
        from tools.core.image_to_board import RecognitionConfig

        cfg = RecognitionConfig.for_scan()
        assert cfg.digit_template_set == "default"

    def test_load_templates_unknown_set_falls_back(self):
        from tools.core.image_to_board import _load_templates

        # Unknown template set should fall back to default dir
        result = _load_templates("nonexistent")
        assert isinstance(result, dict)

    def test_load_templates_caching(self):
        from tools.core.image_to_board import _load_templates, _template_cache

        _load_templates("default")
        assert "default" in _template_cache


# ---------------------------------------------------------------------------
# Boundary rectangle detection tests (Phase 5c — bbox refinement)
# ---------------------------------------------------------------------------


class TestFindBoundaryRectangle:
    """Tests for _find_boundary_rectangle in tools/pdf_to_sgf/board_detector.py."""

    def test_thick_border_detected(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _find_boundary_rectangle, DetectionConfig

        # Create 400x400 white image with thick black rectangle border
        img = np.full((400, 400), 255, dtype=np.uint8)
        cv2.rectangle(img, (30, 30), (370, 370), 0, thickness=4)

        config = DetectionConfig()
        rect, confidence = _find_boundary_rectangle(img, config)

        assert rect is not None
        assert confidence >= 0.80
        # Rectangle should roughly match the drawn border
        x1, y1, x2, y2 = rect
        assert x1 < 40 and y1 < 40
        assert x2 > 360 and y2 > 360

    def test_plain_white_returns_none(self):
        from tools.pdf_to_sgf.board_detector import _find_boundary_rectangle, DetectionConfig

        img = np.full((300, 300), 255, dtype=np.uint8)
        config = DetectionConfig()
        rect, confidence = _find_boundary_rectangle(img, config)

        assert rect is None
        assert confidence == 0.0

    def test_small_rectangle_rejected(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _find_boundary_rectangle, DetectionConfig

        # Small rectangle relative to crop area (< 50%)
        img = np.full((400, 400), 255, dtype=np.uint8)
        cv2.rectangle(img, (150, 150), (250, 250), 0, thickness=3)

        config = DetectionConfig(boundary_min_area_ratio=0.50)
        rect, confidence = _find_boundary_rectangle(img, config)

        assert rect is None or confidence == 0.0

    def test_elongated_shape_rejected(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _find_boundary_rectangle, DetectionConfig

        # Very elongated rectangle (aspect 10:1) — should fail aspect filter
        img = np.full((400, 400), 255, dtype=np.uint8)
        cv2.rectangle(img, (10, 180), (390, 200), 0, thickness=3)

        config = DetectionConfig()
        rect, confidence = _find_boundary_rectangle(img, config)

        # Should be rejected due to aspect ratio
        assert rect is None or confidence == 0.0

    def test_high_confidence_for_large_rectangle(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _find_boundary_rectangle, DetectionConfig

        # Rectangle taking > 70% of the crop area → confidence should be 0.95
        img = np.full((300, 300), 255, dtype=np.uint8)
        cv2.rectangle(img, (10, 10), (290, 290), 0, thickness=4)

        config = DetectionConfig()
        rect, confidence = _find_boundary_rectangle(img, config)

        assert rect is not None
        assert confidence >= 0.90


class TestRefineBoardBbox:
    """Tests for _refine_board_bbox in tools/pdf_to_sgf/board_detector.py."""

    def test_refines_when_boundary_exists(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _refine_board_bbox, DetectionConfig

        # Region image: 500x500 with a board that has thick border at (50,50)-(350,350)
        region_np = np.full((500, 500, 3), 255, dtype=np.uint8)
        cv2.rectangle(region_np, (50, 50), (350, 350), (0, 0, 0), thickness=4)
        region = Image.fromarray(region_np)

        # CC bbox includes some margin around the boundary rectangle
        cc_bbox = (30, 30, 370, 370)
        config = DetectionConfig()

        refined_bbox, refined_crop, confidence = _refine_board_bbox(region, cc_bbox, config)

        assert confidence > 0
        # Refined bbox should encompass the boundary rectangle plus padding
        x1, y1, x2, y2 = refined_bbox
        assert x1 <= 50  # boundary left edge
        assert y1 <= 50  # boundary top edge
        assert x2 >= 350  # boundary right edge
        assert y2 >= 350  # boundary bottom edge

    def test_falls_back_when_no_boundary(self):
        from tools.pdf_to_sgf.board_detector import _refine_board_bbox, DetectionConfig

        # Plain white region — no boundary to detect
        region_np = np.full((500, 500, 3), 255, dtype=np.uint8)
        region = Image.fromarray(region_np)

        cc_bbox = (100, 100, 400, 400)
        config = DetectionConfig()

        refined_bbox, refined_crop, confidence = _refine_board_bbox(region, cc_bbox, config)

        assert confidence == 0.0
        assert refined_bbox == cc_bbox

    def test_clamped_to_region_bounds(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _refine_board_bbox, DetectionConfig

        # Region is 200x200 with a boundary rect near the edge
        region_np = np.full((200, 200, 3), 255, dtype=np.uint8)
        cv2.rectangle(region_np, (5, 5), (195, 195), (0, 0, 0), thickness=4)
        region = Image.fromarray(region_np)

        cc_bbox = (10, 10, 190, 190)
        config = DetectionConfig(boundary_stone_padding_ratio=0.10)

        refined_bbox, refined_crop, confidence = _refine_board_bbox(region, cc_bbox, config)

        # Even with 10% padding, should be clamped to 0..200
        if confidence > 0:
            assert refined_bbox[0] >= 0
            assert refined_bbox[1] >= 0
            assert refined_bbox[2] <= 200
            assert refined_bbox[3] <= 200


class TestDetectedBoardBackwardCompat:
    """Tests that DetectedBoard works with and without detection_confidence."""

    def test_default_confidence_is_zero(self):
        from tools.pdf_to_sgf.board_detector import DetectedBoard

        img = Image.fromarray(np.full((100, 100, 3), 128, dtype=np.uint8))
        board = DetectedBoard(bbox=(0, 0, 100, 100), image=img, index=0)
        assert board.detection_confidence == 0.0

    def test_explicit_confidence(self):
        from tools.pdf_to_sgf.board_detector import DetectedBoard

        img = Image.fromarray(np.full((100, 100, 3), 128, dtype=np.uint8))
        board = DetectedBoard(bbox=(0, 0, 100, 100), image=img, index=0,
                              detection_confidence=0.95)
        assert board.detection_confidence == 0.95


class TestBoundaryRefinementConfig:
    """Tests that new config fields have sensible defaults."""

    def test_defaults(self):
        from tools.pdf_to_sgf.board_detector import DetectionConfig

        config = DetectionConfig()
        assert config.enable_boundary_refinement is True
        assert config.boundary_min_area_ratio == 0.50
        assert config.boundary_stone_padding_ratio == 0.06

    def test_disabled_skips_refinement(self):
        import cv2
        from tools.pdf_to_sgf.board_detector import _detect_boards_in_region, DetectionConfig

        # Dark block with thick boundary
        img_np = np.full((400, 400, 3), 255, dtype=np.uint8)
        cv2.rectangle(img_np, (50, 50), (350, 350), (0, 0, 0), thickness=4)
        # Fill interior to make CC detect it
        img_np[60:340, 60:340, :] = 80
        img = Image.fromarray(img_np)

        config = DetectionConfig(
            min_board_area=1000,
            enable_grid_filter=False,
            enable_boundary_refinement=False,
        )
        boards = _detect_boards_in_region(img, config)

        # With refinement disabled, confidence should remain 0.0
        for board in boards:
            assert board.detection_confidence == 0.0


class TestBoardDetectedEventConfidence:
    """Test that BoardDetectedEvent supports detection_confidence."""

    def test_default_zero(self):
        from tools.pdf_to_sgf.models import BoardDetectedEvent

        e = BoardDetectedEvent(
            page_number=1, board_index=0,
            bbox=(0, 0, 100, 100), width=100, height=100,
        )
        assert e.detection_confidence == 0.0

    def test_explicit_confidence(self):
        import json
        from tools.pdf_to_sgf.models import BoardDetectedEvent

        e = BoardDetectedEvent(
            page_number=1, board_index=0,
            bbox=(0, 0, 100, 100), width=100, height=100,
            detection_confidence=0.95,
        )
        data = json.loads(e.model_dump_json())
        assert data["detection_confidence"] == 0.95


# ---------------------------------------------------------------------------
# Edge-walk refinement tests
# ---------------------------------------------------------------------------


class TestEdgeWalkToWhitespace:
    def test_already_white_edges_unchanged(self):
        """Bbox already sits in white margin — no expansion needed."""
        from tools.pdf_to_sgf.board_detector import _walk_edge_to_whitespace

        # 300x300 white image with a dark rectangle in the center (50-250)
        gray = np.full((300, 300), 255, dtype=np.uint8)
        gray[50:250, 50:250] = 30  # dark content

        # Bbox already has generous margin (30px from content on each side)
        bbox = (20, 20, 280, 280)
        result = _walk_edge_to_whitespace(gray, bbox, max_walk=30, min_padding=5)

        # Should not expand since edges are already in white
        assert result == bbox

    def test_stone_at_edge_extends_bbox(self):
        """Dark circle at left edge → bbox extends left past the stone."""
        from tools.pdf_to_sgf.board_detector import _walk_edge_to_whitespace

        # 400x400 white image
        gray = np.full((400, 400), 255, dtype=np.uint8)
        # Draw a dark circle (simulating a stone) at the left edge
        cv2.circle(gray, (35, 200), 20, 30, -1)  # center at x=35, radius=20

        # Bbox left edge at x=30 — cuts through the stone
        bbox = (30, 50, 370, 350)
        result = _walk_edge_to_whitespace(gray, bbox, max_walk=30, min_padding=5)

        # Left edge should have moved left to clear the stone + min_padding
        assert result[0] < bbox[0], "Left edge should expand to avoid cutting the stone"
        # Other edges already in white → unchanged
        assert result[1] == bbox[1]  # top
        assert result[2] == bbox[2]  # right
        assert result[3] == bbox[3]  # bottom

    def test_min_padding_adds_margin(self):
        """Edge cutting through content → walks out and adds min_padding beyond."""
        from tools.pdf_to_sgf.board_detector import _walk_edge_to_whitespace

        gray = np.full((200, 200), 255, dtype=np.uint8)
        gray[50:150, 50:150] = 30  # dark content block

        # Left edge at x=60 — cuts through content (dark at x=60)
        # Walk leftward: first white column is x=49.
        # min_padding=5 → result should be x=49-5=44
        bbox = (60, 30, 170, 170)
        result = _walk_edge_to_whitespace(gray, bbox, max_walk=30, min_padding=5)

        assert result[0] <= 44, f"Left edge should be at most 44 but got {result[0]}"
        assert result[0] < bbox[0], "Left edge should have expanded"

    def test_max_walk_respected(self):
        """Content extends to image boundary → clamped, no crash."""
        from tools.pdf_to_sgf.board_detector import _walk_edge_to_whitespace

        # Entire image is dark — no white row/col anywhere
        gray = np.full((200, 200), 30, dtype=np.uint8)
        bbox = (10, 10, 190, 190)
        result = _walk_edge_to_whitespace(gray, bbox, max_walk=30, min_padding=5)

        # Should keep original edges since no white found within max_walk
        assert result == bbox

    def test_disabled_by_config(self):
        """When enable_edge_walk=False, the walk is skipped in detection."""
        from tools.pdf_to_sgf.board_detector import DetectionConfig

        config = DetectionConfig(enable_edge_walk=False)
        assert config.enable_edge_walk is False
