"""
Unit tests for OptiScan custom exceptions and logging utilities.
"""

import logging
from pathlib import Path

import pytest

from src.utils.exceptions import (
    AlignmentError,
    EvaluationError,
    FiducialMarkerNotFoundError,
    ImageLoadError,
    ImageProcessingError,
    InvalidImageDimensionsError,
    OptiScanException,
    PerspectiveWarpError,
    ScoringError,
    StudentIdParsingError,
    TemplateError,
    TemplateMismatchError,
)
from src.utils.logger import get_logger


class TestExceptions:
    def test_base_exception(self):
        exc = OptiScanException("Base failure", error_code="TEST_CODE", details={"key": "val"})
        assert str(exc) == "[TEST_CODE] Base failure | Context: {'key': 'val'}"
        assert exc.error_code == "TEST_CODE"
        assert exc.details == {"key": "val"}

    def test_image_load_error(self):
        exc = ImageLoadError("Failed to open image", file_path="sample.png")
        assert issubclass(ImageLoadError, ImageProcessingError)
        assert issubclass(ImageLoadError, OptiScanException)
        assert exc.error_code == "IMAGE_LOAD_ERROR"
        assert exc.details["file_path"] == "sample.png"

    def test_invalid_dimensions_error(self):
        exc = InvalidImageDimensionsError("Resolution too low", shape=(800, 600))
        assert exc.error_code == "INVALID_IMAGE_DIMENSIONS"
        assert exc.details["shape"] == (800, 600)

    def test_fiducial_markers_error(self):
        exc = FiducialMarkerNotFoundError("Only 2 markers detected", markers_found=2)
        assert issubclass(FiducialMarkerNotFoundError, AlignmentError)
        assert exc.error_code == "FIDUCIAL_MARKERS_NOT_FOUND"
        assert exc.details["markers_found"] == 2

    def test_perspective_warp_error(self):
        exc = PerspectiveWarpError("Singular homography matrix")
        assert issubclass(PerspectiveWarpError, AlignmentError)
        assert exc.error_code == "PERSPECTIVE_WARP_ERROR"

    def test_template_mismatch_error(self):
        exc = TemplateMismatchError("Grid count mismatch", template_name="A4_100Q")
        assert issubclass(TemplateMismatchError, TemplateError)
        assert exc.error_code == "TEMPLATE_MISMATCH_ERROR"
        assert exc.details["template_name"] == "A4_100Q"

    def test_scoring_error(self):
        exc = ScoringError("Invalid option count in answer key")
        assert issubclass(ScoringError, EvaluationError)
        assert exc.error_code == "SCORING_ERROR"

    def test_student_id_parsing_error(self):
        exc = StudentIdParsingError("Column 3 has multi-marks")
        assert issubclass(StudentIdParsingError, EvaluationError)
        assert exc.error_code == "STUDENT_ID_PARSING_ERROR"


class TestLogger:
    def test_get_logger_basic(self):
        logger = get_logger("test_logger_1", level=logging.DEBUG)
        assert logger.name == "test_logger_1"
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) >= 1

    def test_logger_file_output(self, tmp_path: Path):
        log_file = tmp_path / "logs" / "test.log"
        logger = get_logger("test_logger_file", level=logging.INFO, log_file=log_file)
        
        test_message = "Test log entry for OptiScan verification"
        logger.info(test_message)

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert test_message in content
        assert "INFO" in content

    def test_logger_string_level(self):
        logger = get_logger("test_logger_str", level="warning")
        assert logger.level == logging.WARNING
