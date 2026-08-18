"""
Custom exception hierarchy for the OptiScan system.
"""

from typing import Any, Optional


class OptiScanException(Exception):
    """Base exception for all OptiScan specific runtime errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "OPTISCAN_ERROR",
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"[{self.error_code}] {self.message} | Context: {self.details}"
        return f"[{self.error_code}] {self.message}"


# --- Image Processing & Ingestion Errors ---

class ImageProcessingError(OptiScanException):
    """Raised when an error occurs during image ingestion or preprocessing."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="IMAGE_PROCESSING_ERROR", details=details)


class ImageLoadError(ImageProcessingError):
    """Raised when an image cannot be read, format is unsupported, or file is corrupted."""

    def __init__(self, message: str, file_path: Optional[str] = None, details: Optional[dict[str, Any]] = None) -> None:
        context = details or {}
        if file_path:
            context["file_path"] = file_path
        super().__init__(message, details=context)
        self.error_code = "IMAGE_LOAD_ERROR"


class InvalidImageDimensionsError(ImageProcessingError):
    """Raised when image resolution does not meet minimum quality criteria."""

    def __init__(self, message: str, shape: Optional[tuple] = None, details: Optional[dict[str, Any]] = None) -> None:
        context = details or {}
        if shape:
            context["shape"] = shape
        super().__init__(message, details=context)
        self.error_code = "INVALID_IMAGE_DIMENSIONS"


# --- Geometry, Registration & Warp Errors ---

class AlignmentError(OptiScanException):
    """Raised when geometric alignment, registration, or perspective warping fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="ALIGNMENT_ERROR", details=details)


class FiducialMarkerNotFoundError(AlignmentError):
    """Raised when the 4 corner fiducial markers cannot be reliably detected."""

    def __init__(self, message: str, markers_found: int = 0, details: Optional[dict[str, Any]] = None) -> None:
        context = details or {}
        context["markers_found"] = markers_found
        super().__init__(message, details=context)
        self.error_code = "FIDUCIAL_MARKERS_NOT_FOUND"


class PerspectiveWarpError(AlignmentError):
    """Raised when perspective transformation fails (e.g., collinear points or singular matrix)."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "PERSPECTIVE_WARP_ERROR"


# --- Template & Configuration Errors ---

class TemplateError(OptiScanException):
    """Raised when a template configuration is invalid or coordinates are out of bounds."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="TEMPLATE_ERROR", details=details)


class TemplateMismatchError(TemplateError):
    """Raised when a sheet layout does not match the provided template specification."""

    def __init__(self, message: str, template_name: Optional[str] = None, details: Optional[dict[str, Any]] = None) -> None:
        context = details or {}
        if template_name:
            context["template_name"] = template_name
        super().__init__(message, details=context)
        self.error_code = "TEMPLATE_MISMATCH_ERROR"


# --- Bubble Detection & Masking Errors ---

class BubbleDetectionError(OptiScanException):
    """Raised when bubble ROI slicing, mask generation, or fill detection fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="BUBBLE_DETECTION_ERROR", details=details)


class MaskGenerationError(BubbleDetectionError):
    """Raised when circular mask generation fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "MASK_GENERATION_ERROR"


# --- Scoring & Evaluation Errors ---

class EvaluationError(OptiScanException):
    """Raised when grading, answer key matching, or evaluation computation fails."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, error_code="EVALUATION_ERROR", details=details)


class ScoringError(EvaluationError):
    """Raised when grading rule application encounters inconsistent question counts or answers."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "SCORING_ERROR"


class StudentIdParsingError(EvaluationError):
    """Raised when roll number / student ID grid cannot be decoded unambiguously."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message, details=details)
        self.error_code = "STUDENT_ID_PARSING_ERROR"
